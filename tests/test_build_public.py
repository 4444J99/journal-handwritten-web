"""tools/build_public.py pool gate (issue #65): Reserve poems stay out of public site builds.

Synthetic fixtures only, reusing the private-repository and studio-export builders from
tests/test_post_poem.py: invented three-line pieces and 8-pixel jpgs. No real poem text.
Run from anywhere:  python3 -m unittest discover -s tests -v

The gate is opt-in: build(..., pool_db=<studio export>) enforces it; without pool_db the
build behaves exactly as before. The one deliberate deviation from the issue #65 plan is
in test_shared_scan_reserve_coresident_is_never_accepted: the plan's step 5(c) says a
Series piece sharing a scan with a Reserve piece "passes with --accept-shared-scan",
but post_poem.py's own shared_scan() — which the plan says to import, not re-implement —
returns status "stop" for any non-Series co-resident and never consults the accepted set
for it ("accept never helps non-series", test_post_poem.py). The imported rule wins:
a Reserve co-resident is an unconditional stop.
"""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
TOOLS = TESTS.parent / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TESTS))
import build_public  # noqa: E402
from test_post_poem import FONT_BYTES, NO_VENV, make_private, ready_db  # noqa: E402
from PIL import Image  # noqa: E402

RENAMED_FONT_BYTES = b"renamed-font-bytes"
FONT_DATA_URI_RE = re.compile(r"src:url\(data:font/woff2;base64,[A-Za-z0-9+/=]+\)")


def _external_font_site(root):
    """Swap the fixture's embedded @font-face data URI for a file reference,
    and write the font bytes as site/fonts/handwriting.woff2 (the #29 shape)."""
    site = Path(root) / "site"
    html = (site / "index.html").read_text()
    html, n = FONT_DATA_URI_RE.subn('src:url("fonts/handwriting.woff2")', html)
    assert n == 1, "fixture @font-face data URI not found"
    (site / "index.html").write_text(html)
    (site / "fonts").mkdir(exist_ok=True)
    (site / "fonts" / "handwriting.woff2").write_bytes(FONT_BYTES)


def _fake_font_tool(mode, data, *args):
    """Stand-in for the venv font tool: the fixture font carries the old name
    and needs renaming; rename returns fixed bytes."""
    if mode == "check":
        return {"ok": False, "needs_public_scrub": True, "hits": ["name id1 platform3: old"]}
    if mode == "rename":
        return {"font_b64": base64.b64encode(RENAMED_FONT_BYTES).decode("ascii"),
                "changed": ["name id1"], "hits_after": [], "glyphs": 12}
    raise AssertionError(mode)


class ExternalFontTests(unittest.TestCase):
    """@font-face referencing a font file (journal-handwritten-web #29):
    the publish build resolves it, renames it the same way, and re-embeds
    it, so the published page stays standalone and the rename gate applies."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="bp-extfont-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "private"
        self.db = self.tmp / "db"
        self.out = self.tmp / "out"

    def prepare(self):
        make_private(self.root, extra_public=("p001",))
        ready_db(self.db, pids=("p001",), _root=self.root)
        _external_font_site(self.root)

    def build(self, **kw):
        kw.setdefault("site", self.root / "site")
        kw.setdefault("select", {"p001": [1]})
        kw.setdefault("rename_fonts", True)
        kw.setdefault("pool_db", None)
        return build_public.build(self.out, ["p001"], **kw)

    def test_external_font_is_renamed_and_reembedded(self):
        self.prepare()
        with mock.patch.object(build_public, "run_font_tool", side_effect=_fake_font_tool):
            res = self.build()
        self.assertIsNone(res["font_error"])
        self.assertEqual(len(res["fonts"]), 1)
        report = res["fonts"][0]
        self.assertTrue(report["renamed"])
        self.assertEqual(report["source"], "fonts/handwriting.woff2")
        self.assertEqual(report["bytes"], len(FONT_BYTES))
        self.assertEqual(report["bytes_out"], len(RENAMED_FONT_BYTES))
        published = (self.out / "index.html").read_text()
        self.assertIn("data:font/woff2;base64," + base64.b64encode(RENAMED_FONT_BYTES).decode("ascii"), published)
        self.assertNotIn("fonts/handwriting.woff2", published)

    def test_external_font_already_clean_is_reembedded_unchanged(self):
        self.prepare()

        def clean_tool(mode, data, *args):
            if mode == "check":
                return {"ok": True, "needs_public_scrub": False, "hits": []}
            raise AssertionError(mode)

        with mock.patch.object(build_public, "run_font_tool", side_effect=clean_tool):
            res = self.build()
        self.assertIsNone(res["font_error"])
        self.assertEqual(len(res["fonts"]), 1)
        self.assertFalse(res["fonts"][0]["renamed"])
        self.assertEqual(res["fonts"][0]["source"], "fonts/handwriting.woff2")
        published = (self.out / "index.html").read_text()
        self.assertIn("data:font/woff2;base64," + base64.b64encode(FONT_BYTES).decode("ascii"), published)
        self.assertNotIn("fonts/handwriting.woff2", published)

    def test_external_font_file_missing_fails_loudly(self):
        self.prepare()
        (self.root / "site" / "fonts" / "handwriting.woff2").unlink()
        with mock.patch.object(build_public, "run_font_tool", side_effect=_fake_font_tool):
            with self.assertRaises(FileNotFoundError):
                self.build()

    def test_external_font_without_venv_blocks_the_build(self):
        self.prepare()
        with mock.patch.dict(os.environ, NO_VENV):
            res = self.build()
        self.assertIn("font python not found", res["font_error"])
        self.assertEqual(res["fonts"], [])


def _sentinel_out(root):
    out = root / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "previous-output").write_bytes(b"keep the last successful build")
    return out


class PoolGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="bp-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "private"
        self.db = self.tmp / "db"
        self.out = self.tmp / "out"

    def prepare(self, pids=("p001",), public=(), **dbkw):
        """Synthetic private repo + studio export. p001's top version V1 sits on pg2,
        shared with p002; p004 shares pg1, which only the unpublished V0 uses."""
        make_private(self.root, extra_public=public)
        ready_db(self.db, pids=pids, _root=self.root, **dbkw)

    def build(self, want, **kw):
        kw.setdefault("site", self.root / "site")
        kw.setdefault("select", {"p001": [1]} if "p001" in want else {})
        kw.setdefault("rename_fonts", False)
        kw.setdefault("pool_db", self.db)
        return build_public.build(self.out, want, **kw)

    def assert_refused(self, want, pattern, **kw):
        out = _sentinel_out(self.tmp)
        with self.assertRaises(SystemExit) as cm:
            self.build(want, **kw)
        self.assertRegex(str(cm.exception.code), pattern)
        self.assertEqual((out / "previous-output").read_bytes(), b"keep the last successful build")
        self.assertEqual([p.name for p in out.iterdir()], ["previous-output"])

    def test_whitelisted_reserve_piece_refuses_and_leaves_output_untouched(self):
        self.prepare(release={"p001": {"pool": "reserve"}})
        self.assert_refused(["p001"], r"p001: pool is reserve.*Take it out of release/public\.json")

    def test_whitelisted_archive_and_unknown_pools_refuse(self):
        for label, pool in (("archive", "archive"), ("capitalised", "Reserve"), ("null", None)):
            with self.subTest(label=label):
                shutil.rmtree(self.tmp, ignore_errors=True)
                self.setUp()
                self.prepare(release={"p001": {"pool": pool}})
                self.assert_refused(["p001"], r"p001: .*Take it out of release/public\.json")

    def test_shared_scan_reserve_coresident_is_never_accepted(self):
        # p002 shares p001's published page pg2. Reserve there is a stop, and
        # --accept-shared-scan does not help a non-Series co-resident (post_poem
        # shared_scan: only Series mates can be "accepted"). This corrects the
        # issue #65 plan step 5(c), which said this case "passes with it".
        self.prepare(release={"p002": {"pool": "reserve"}})
        self.assert_refused(["p001"], r"p001: shared scan refused: p002 on pg2: pool is reserve")
        self.assert_refused(["p001"], r"p001: shared scan refused: p002 on pg2: pool is reserve",
                            accept_shared_scan=["p002"])

    def test_series_coresident_needs_accept_shared_scan(self):
        self.prepare(release={"p002": {"pool": "series"}})
        self.assert_refused(["p001"], r"p001: shared scan refused: p002 on pg2: .*--accept-shared-scan p002")
        res = self.build(["p001"], accept_shared_scan=["p002"])
        self.assertEqual(res["pools"], {"p001": "series"})
        data = json.loads((self.out / "data" / "j.json").read_text())
        self.assertEqual([p["id"] for p in data["pieces"]], ["p001"])
        self.assertNotIn("SENTINEL-p002", (self.out / "data" / "j.json").read_text())

    def test_series_only_whitelist_builds_and_publishes_only_those_pieces(self):
        # p004 is Reserve but sits on pg1, which no published version uses: it must
        # neither block the build nor leak into the output.
        self.prepare(pids=("p001", "p002"), release={"p004": {"pool": "reserve"}})
        res = self.build(["p001", "p002"], select={"p001": [1], "p002": [0]})
        self.assertEqual(res["pools"], {"p001": "series", "p002": "series"})
        data = json.loads((self.out / "data" / "j.json").read_text())
        self.assertEqual([p["id"] for p in data["pieces"]], ["p001", "p002"])
        tree = "\n".join(p.read_text(errors="ignore") for p in self.out.rglob("*") if p.is_file() and p.suffix != ".jpg")
        self.assertNotIn("SENTINEL-p004", tree)
        self.assertNotIn("p004", json.dumps(data["pieces"]))

    def test_spread_image_facing_reserve_piece_refuses(self):
        # The published page carries sp.f, so the whole spread image is copied and
        # the facing page (pg5, carrying p007) counts as a shared scan.
        self.prepare(pids=("p003",), release={"p007": {"pool": "reserve"}})
        jp = self.root / "site" / "data" / "j.json"
        j = json.loads(jp.read_text())
        for p in j["pages"]:
            if p["id"] in ("pg3", "pg5"):
                p["sp"] = {"s": "left" if p["id"] == "pg3" else "right", "cb": [0, 0, 1, 1],
                           "f": "spr" if p["id"] == "pg3" else None, "k": "spr.jpg"}
        jp.write_text(json.dumps(j))
        (self.root / "site" / "img" / "s").mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8), (10, 10, 10)).save(self.root / "site" / "img" / "s" / "spr.jpg")
        self.assert_refused(["p003"], r"p003: shared scan refused: p007 on pg5: .*facing page of the spread image",
                            select={"p003": [0]})

    def test_missing_pool_database_fails_loudly_instead_of_building_blind(self):
        self.prepare()
        out = _sentinel_out(self.tmp)
        with self.assertRaises(SystemExit) as cm:
            self.build(["p001"], pool_db=self.tmp / "no-such-export")
        self.assertRegex(str(cm.exception.code), r"pool database cannot be loaded")
        self.assertEqual((out / "previous-output").read_bytes(), b"keep the last successful build")

    def test_no_pool_db_builds_exactly_as_before(self):
        # Without pool_db the gate is off: p002 is unsorted and shares pg2, which
        # used to build fine and still does (the plan makes the flag opt-in).
        self.prepare()
        res = self.build(["p001"], pool_db=None)
        self.assertIsNone(res["pools"])
        self.assertEqual([p["id"] for p in json.loads((self.out / "data" / "j.json").read_text())["pieces"]],
                         ["p001"])

    def test_cli_refuses_reserve_piece_and_missing_pool_db(self):
        # CLI-level acceptance checks against the real repository (only the
        # own-pool refusal fires before any shared-scan or build step).
        root = TESTS.parent
        release = self.tmp / "release.json"
        release.write_text(json.dumps({"pieces": ["p001"]}))
        db = self.tmp / "cli-db"
        ready_db(db, pids=("p001",), _root=root, release={"p001": {"pool": "reserve"}})
        out = self.tmp / "cli-out"
        r = subprocess.run([sys.executable, str(root / "tools" / "build_public.py"), str(out),
                            "--release", str(release), "--pool-db", str(db)],
                           capture_output=True, text=True, timeout=120)
        self.assertNotEqual(r.returncode, 0)
        self.assertRegex(r.stdout + r.stderr, r"p001: pool is reserve")
        self.assertFalse(out.exists())
        r = subprocess.run([sys.executable, str(root / "tools" / "build_public.py"), str(out),
                            "--release", str(release), "--pool-db", str(self.tmp / "no-such-export")],
                           capture_output=True, text=True, timeout=120)
        self.assertNotEqual(r.returncode, 0)
        self.assertRegex(r.stdout + r.stderr, r"pool database cannot be loaded")
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
