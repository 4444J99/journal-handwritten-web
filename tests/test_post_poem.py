"""Tests for tools/post_poem.py and the refactored tools/build_public.py.

Synthetic fixtures only: invented three-line pieces and 8-pixel jpgs. No real poem text.
Run from anywhere:  python3 -m unittest discover -s tests -v
Scratch files go where tempfile puts them (set TMPDIR to keep them on the external drive).
"""
import contextlib, io, json, os, re, shutil, stat, subprocess, sys, tempfile, unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
TOOLS = TESTS.parent / "tools"
sys.path.insert(0, str(TOOLS))
import build_public  # noqa: E402
import post_poem  # noqa: E402
from PIL import Image  # noqa: E402

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
}

INDEX_HTML = (
    '<!doctype html><html><head><meta charset=utf8>'
    '<meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">'
    '<style>:root{--a:1}</style>\n<title>Fixture Title</title>\n'
    '<style>@font-face{font-family:"Test Diary";src:url(data:font/woff2;base64,' + "QUJD" * 40 + ')}</style>'
    '</head><body><canvas id="cv" aria-label="Fixture canvas"></canvas><p>set in Test Diary</p></body></html>\n'
)

# page -> list of (block owner piece id or None); piece -> versions as [(page, [blocks])]
# p001: V0 on pg1, V1 on pg2 (top = V1). p002 shares pg2. p004 shares pg1. p003 stands alone.
# p006 has two versions on diary53 / diary54 (the page names the studio's final decision refers to).
PIECES = {
    "p001": dict(V=[[("pg1", [0, 1])], [("pg2", [0])]], top=1),
    "p002": dict(V=[[("pg2", [1])]], top=0),
    "p003": dict(V=[[("pg3", [0])]], top=0),
    "p004": dict(V=[[("pg1", [2])]], top=0),
    "p006": dict(V=[[("diary53", [0])], [("diary54", [0])]], top=1),
    "p007": dict(V=[[("pg5", [0])], [("pg5", [1])]], top=0),  # top of the stack is not the last entry of V
}
ORDER = ["p001", "p002", "p003", "p004", "p006", "p007"]


def line_text(pid, vi, bi, li):
    return f"SENTINEL-{pid} v{vi} b{bi} l{li}" if pid != "p001" else f"mach-{pid} v{vi} b{bi} l{li}"


def make_private(root, other_items=None, extra_public=None):
    """Write a synthetic private repository tree; returns nothing."""
    root = Path(root)
    (root / "site" / "data").mkdir(parents=True)
    (root / "studio" / "data").mkdir(parents=True)
    (root / "release").mkdir()
    pages, rpages = {}, {}
    owner = {}
    for pi, pid in enumerate(ORDER):
        pc = PIECES[pid]
        st = list(range(len(pc["V"])))
        st.sort(key=lambda i: (i != pc["top"], i))
        for vi, v in enumerate(pc["V"]):
            for pg, blocks in v:
                for b in blocks:
                    owner[(pg, b)] = (pi, vi, st.index(vi), pid)
    for pg in ("pg1", "pg2", "pg3", "diary53", "diary54", "pg5"):
        nb = 1 + max(b for (p, b) in owner if p == pg)
        B, RB = [], []
        for bi in range(nb):
            pi, vi, rank, pid = owner[(pg, bi)]
            L = [line_text(pid, vi, bi, li) for li in range(3)]
            B.append({"t": 0, "L": L, "g": [pi, rank, 0], "v": vi})
            RB.append({"t": "text", "spread": None, "note": None,
                       "lines": [{"id": f"{pg}-{bi}-{li}", "tx": L[li], "box": [0, 0, 1, 1]} for li in range(3)]})
        pages[pg] = {"id": pg, "iw": 100, "ih": 150, "W": 100, "H": 150, "c": [0, 0, 1, 1],
                     "sp": {"s": "right", "cb": [0, 0, 1, 1], "f": None, "k": pg + ".jpg"},
                     "u": [f"SENTINEL-note-{pg}"], "a": [0, 16 * len(pages), 0, 16, 16], "B": B, "x": [], "pl": None}
        rpages[pg] = {"id": pg, "seq": len(rpages), "blocks": RB}
    # an "other lines" review item (not a piece), optionally placed on a page
    items = []
    for pid in ORDER:
        vers = [{"page": pg, "blocks": bl} for v in PIECES[pid]["V"] for pg, bl in v]
        items.append({"id": pid, "first": "x", "kind": "poem", "status": "", "g": 1, "versions": vers})
    for oid, pg, bi in (other_items or []):
        rpages[pg]["blocks"].append({"t": "text", "spread": None, "note": None, "lines": [{"id": f"{pg}-{len(rpages[pg]['blocks'])}-0", "tx": "other", "box": [0, 0, 1, 1]}]})
        pages[pg]["B"].append({"t": 0, "L": ["other"]})
        items.append({"id": oid, "first": "", "kind": "other", "status": "", "g": 4, "versions": [{"page": pg, "blocks": [len(pages[pg]["B"]) - 1]}]})
    j = {"v": 2, "pages": list(pages.values()), "groups": [["pg1", "pg2"], ["pg3"], ["diary53", "diary54"]], "atlas": [[16 * 8, 16]],
         "pieces": [{"id": pid, "top": PIECES[pid]["top"],
                     "st": sorted(range(len(PIECES[pid]["V"])), key=lambda i: (i != PIECES[pid]["top"], i)),
                     "V": [{"id": f"{pid}-{k}", "s": "j", "d": None, "P": [[pg, bl] for pg, bl in v]} for k, v in enumerate(PIECES[pid]["V"])]}
                    for pid in ORDER],
         "prov": {"repo": "https://example.invalid/private-source", "commit": "0" * 40, "path": "private/path", "tdate": "2026-01-01", "verified": False}}
    (root / "site" / "data" / "j.json").write_text(json.dumps(j))
    (root / "studio" / "data" / "review.json").write_text(json.dumps({"version": 1, "flagged": [], "items": items, "pages": list(rpages.values())}))
    (root / "site" / "index.html").write_text(INDEX_HTML)
    for sub in ("p", "i", "m"):
        (root / "site" / "img" / sub).mkdir(parents=True)
        for pg in pages:
            Image.new("RGB", (8, 8), (200, 190, 180)).save(root / "site" / "img" / sub / f"{pg}.jpg")
    (root / "site" / "img" / "a").mkdir(parents=True)
    for k in ("t", "k"):
        Image.new("RGB", (128, 16), (100, 100, 100)).save(root / "site" / "img" / "a" / f"{k}0.jpg")
    (root / "release" / "public.json").write_text(json.dumps({"pieces": list(extra_public or [])}, indent=2) + "\n")


def write_db(base, release=None, reviews=None, batches=None, decisions=None, versions=None):
    base = Path(base)
    for coll, docs in (("release", release), ("reviews", reviews), ("batches", batches), ("decisions", decisions), ("versions", versions)):
        for did, doc in (docs or {}).items():
            (base / coll).mkdir(parents=True, exist_ok=True)
            (base / coll / f"{did}.json").write_text(json.dumps(doc))
    base.mkdir(parents=True, exist_ok=True)


def ready_db(base, pids=("p001",), skip_review=(), **over):
    """Everything in order for the given pieces: Series, every line confirmed, filed batch."""
    j = json.loads(Path(over.pop("_root")).joinpath("site/data/j.json").read_text())
    pages = {p["id"]: p for p in j["pages"]}
    release = {p: {"pool": "series", "order": i} for i, p in enumerate(pids)}
    reviews = {}
    for p in j["pieces"]:
        if p["id"] not in pids:
            continue
        for v in p["V"]:
            for pg, bl in v["P"]:
                for b in bl:
                    for li, tx in enumerate(pages[pg]["B"][b]["L"]):
                        lid = f"{pg}-{b}-{li}"
                        if lid not in skip_review:
                            reviews[lid] = {"status": "confirmed", "original": tx, "at": "2026-11-05T00:00:00Z"}
    batches = {"b-1": {"items": list(pids), "status": "filed", "filed": "2026-11-01", "sr": "x", "created": "2026-11-01", "at": "2026-11-01"}}
    release.update(over.pop("release", {}))
    reviews.update(over.pop("reviews", {}))
    batches.update(over.pop("batches", {}))
    write_db(base, release=release, reviews=reviews, batches=batches, **over)


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def make_public(base):
    """Throwaway clone of a fake 4444J99/versforms, backed by a local bare repository."""
    base = Path(base)
    bare, seed, clone = base / "origin.git", base / "seed", base / "public"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], check=True)
    (seed / "site").mkdir()
    (seed / "site" / "index.html").write_text(build_public.SHELL)
    (seed / "README.md").write_text("public\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "seed")
    git(seed, "remote", "add", "origin", str(bare))
    git(seed, "push", "-q", "origin", "main")
    subprocess.run(["git", "clone", "-q", str(bare), str(clone)], check=True)
    git(clone, "remote", "set-url", "origin", "https://github.com/4444J99/versforms.git")
    git(clone, "config", f"url.{bare}.insteadOf", "https://github.com/4444J99/versforms.git")
    return clone, bare


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env = {k: os.environ.get(k) for k in GIT_ENV}
        os.environ.update(GIT_ENV)

    @classmethod
    def tearDownClass(cls):
        for k, v in cls._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pp-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "private"
        self.db = self.tmp / "db"
        self.work = self.tmp / "work"

    def prepare(self, pids=("p001",), other_items=None, public=("p002",), **dbkw):
        """p002 shares p001's published page, so by default it is already public (a fine co-resident)."""
        make_private(self.root, other_items=other_items, extra_public=public)
        ready_db(self.db, pids=pids, _root=self.root, **dbkw)

    def go(self, *args, dry=True, public=None, db=None):
        argv = list(args) + ["--db", str(db or self.db), "--source", str(self.root), "--workdir", str(self.work)]
        if dry:
            argv.append("--dry-run")
        if public:
            argv += ["--public-repo", str(public)]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = post_poem.main(argv)
        self.out = buf.getvalue()
        return code

    def pubjson(self):
        return json.loads((self.work / "build" / "data" / "j.json").read_text())

    def pc(self, pid):
        return next(p for p in self.pubjson()["pieces"] if p["id"] == pid)

    def all_text(self, root):
        return "\n".join(p.read_text(errors="ignore") for p in Path(root).rglob("*") if p.is_file() and p.suffix != ".jpg")


class GateTests(Base):
    def test_all_gates_pass(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0, self.out)
        for g in ("(a) in Series", "(b) every line", "(c) in a filed"):
            self.assertRegex(self.out, "PASS  gate +" + re.escape(g))
        self.assertNotIn("is not the last entry of V", self.out)  # p001's top is its last entry in the fixture

    def test_gate_a_fails_for_reserve_and_missing_doc(self):
        for release in ({"p001": {"pool": "reserve"}}, {"p001": {"pool": "archive"}}):
            with self.subTest(release=release):
                shutil.rmtree(self.tmp, ignore_errors=True)
                self.setUp()
                self.prepare(release=release)
                self.assertEqual(self.go("p001"), 2, self.out)
                self.assertIn("FAIL  gate (a) in Series", self.out)
        self.setUp()
        self.prepare()
        (self.db / "release" / "p001.json").unlink()
        self.assertEqual(self.go("p001"), 2)
        self.assertIn("no release document", self.out)

    def test_gate_b_fails_when_a_line_is_unreviewed_or_status_unknown(self):
        self.prepare(skip_review=("pg1-0-1",))
        self.assertEqual(self.go("p001"), 2, self.out)
        self.assertIn("FAIL  gate (b)", self.out)
        self.assertIn("pg1-0-1", self.out)
        self.setUp()
        self.prepare(reviews={"pg1-0-1": {"status": "skipped", "original": "x"}})
        self.assertEqual(self.go("p001"), 2)

    def test_gate_b_covers_every_version_even_unpublished_ones(self):
        self.prepare(skip_review=("pg1-0-0",))  # pg1 holds V0, which is not the published version
        self.assertEqual(self.go("p001"), 2, self.out)

    def test_gate_c_fails_for_no_batch_and_draft_batch(self):
        self.prepare(batches={"b-1": {"items": ["p001"], "status": "draft"}})
        self.assertEqual(self.go("p001"), 2, self.out)
        self.assertIn("FAIL  gate (c)", self.out)
        self.setUp()
        self.prepare()
        (self.db / "batches" / "b-1.json").unlink()
        self.assertEqual(self.go("p001"), 2)
        self.assertIn("not listed in any batch", self.out)

    def test_registered_batch_passes(self):
        self.prepare(batches={"b-1": {"items": ["p001"], "status": "registered"}})
        self.assertEqual(self.go("p001"), 0, self.out)

    def test_force_overrides_gates_only(self):
        self.prepare(release={"p001": {"pool": "reserve"}}, skip_review=("pg2-0-0",))
        self.assertEqual(self.go("p001", "--force"), 0, self.out)
        self.assertIn("FORCED past 2 failed gate(s)", self.out)

    def test_unknown_piece_is_a_hard_stop(self):
        self.prepare()
        self.assertEqual(self.go("p999", "--force"), 3, self.out)
        self.assertIn("unknown piece id", self.out)


class HardStopTests(Base):
    def test_shared_scan_refuses_reserve_archive_unsorted_and_unknown_pool(self):
        for label, rel in (("reserve", {"p002": {"pool": "reserve"}}), ("archive", {"p002": {"pool": "archive"}}),
                           ("unsorted", {}), ("unknown", {"p002": {"pool": "weird"}})):
            with self.subTest(label):
                shutil.rmtree(self.tmp, ignore_errors=True)
                self.setUp()
                self.prepare(release=rel, public=())
                self.assertEqual(self.go("p001"), 3, self.out)
                self.assertIn("(i) shared scan", self.out)
                self.assertEqual(self.go("p001", "--force"), 3)  # force never overrides
                self.assertEqual(self.go("p001", "--force", "--accept-shared-scan", "p002"), 3)  # accept never helps non-series

    def test_series_coresident_needs_accept_shared_scan(self):
        self.prepare(release={"p002": {"pool": "series"}}, public=())
        self.assertEqual(self.go("p001"), 3, self.out)
        self.assertIn("--accept-shared-scan p002", self.out)
        self.assertEqual(self.go("p001", "--accept-shared-scan", "p002"), 0, self.out)
        self.assertIn("accepted shared scan: p002", self.out)
        self.assertEqual(self.go("p001", "--accept-shared-scan", "p003,p002"), 0)

    def test_coresident_already_public_is_fine(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0, self.out)
        self.assertEqual([p["id"] for p in self.pubjson()["pieces"]], ["p002", "p001"])

    def test_other_lines_item_needs_accept(self):
        self.prepare(release={"p002": {"pool": "series"}}, other_items=[("x-pg2", "pg2", 0)], public=())
        self.assertEqual(self.go("p001", "--accept-shared-scan", "p002"), 3, self.out)
        self.assertIn("x-pg2", self.out)
        self.assertEqual(self.go("p001", "--accept-shared-scan", "p002,x-pg2"), 0, self.out)
        text = self.all_text(self.work / "build")
        self.assertNotIn("SENTINEL-p002", text)
        self.assertNotIn("other", json.dumps(self.pubjson()["pages"][0]["B"][2]["L"]))  # the other-lines block is emptied
        self.assertEqual(self.pubjson()["pages"][0]["B"][2]["L"], [""])

    def test_only_published_version_pages_count(self):
        # p004 shares pg1, which only the unpublished V0 uses: no stop by default, a stop with the whole stack
        self.prepare()
        self.assertEqual(self.go("p001"), 0, self.out)
        self.assertEqual(self.go("p001", "--include-versions"), 3, self.out)
        self.assertEqual(self.go("p001", "--include-versions", "--accept-shared-scan", "p004") , 3)  # p004 unsorted
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.setUp()
        self.prepare(release={"p004": {"pool": "series"}})
        self.assertEqual(self.go("p001", "--include-versions", "--accept-shared-scan", "p004"), 0, self.out)

    def test_stale_transcript_refused_even_with_force(self):
        self.prepare(reviews={"pg2-0-1": {"status": "confirmed", "original": "an older machine reading"}})
        self.assertEqual(self.go("p001"), 3, self.out)
        self.assertIn("pg2-0-1", self.out)
        self.assertNotIn("an older machine reading", self.out)
        self.assertEqual(self.go("p001", "--force"), 3)

    def test_stale_in_unpublished_version_does_not_block(self):
        self.prepare(reviews={"pg1-0-1": {"status": "confirmed", "original": "an older machine reading"}})
        self.assertEqual(self.go("p001"), 0, self.out)

    def test_public_repo_preconditions(self):
        self.prepare()
        clone, bare = make_public(self.tmp)
        self.assertEqual(self.go("p001", public=clone), 0, self.out)
        # wrong remote
        git(clone, "remote", "set-url", "origin", "https://github.com/someone/else.git")
        self.assertEqual(self.go("p001", "--force", public=clone), 3, self.out)
        self.assertIn("remote origin is 4444J99/versforms", self.out)
        git(clone, "remote", "set-url", "origin", "https://github.com/4444J99/versforms.git")
        # dirty tree
        (clone / "stray.txt").write_text("x")
        self.assertEqual(self.go("p001", public=clone), 3)
        self.assertIn("working tree clean", self.out)
        (clone / "stray.txt").unlink()
        # not on main
        git(clone, "checkout", "-q", "-b", "elsewhere")
        self.assertEqual(self.go("p001", public=clone), 3)
        self.assertIn("on branch main", self.out)
        git(clone, "checkout", "-q", "main")
        # behind origin
        other = self.tmp / "other"
        subprocess.run(["git", "clone", "-q", str(bare), str(other)], check=True)
        (other / "README.md").write_text("newer\n")
        git(other, "commit", "-q", "-am", "newer")
        git(other, "push", "-q", "origin", "main")
        self.assertEqual(self.go("p001", public=clone), 3)
        self.assertIn("main is fetched", self.out)

    def test_branch_that_exists_is_a_hard_stop(self):
        self.prepare()
        clone, _ = make_public(self.tmp)
        git(clone, "branch", "post/p001")
        self.assertEqual(self.go("p001", public=clone), 3, self.out)

    def test_real_run_requires_public_repo(self):
        self.prepare()
        self.assertEqual(self.go("p001", "--accept-embedded-font", dry=False), 64, self.out)

    def test_embedded_font_needs_acceptance_in_a_real_run(self):
        self.prepare()
        clone, _ = make_public(self.tmp)
        head = git(clone, "rev-parse", "HEAD")
        self.assertEqual(self.go("p001", "--no-pr", dry=False, public=clone), 3, self.out)
        self.assertIn("Test Diary", self.out)
        self.assertIn("downloadable", self.out)
        self.assertEqual(git(clone, "rev-parse", "HEAD"), head)
        self.assertEqual(self.go("p001", "--no-pr", "--force", dry=False, public=clone), 3)  # force does not help
        self.assertEqual(self.go("p001", "--no-pr", "--accept-embedded-font", dry=False, public=clone), 0, self.out)

    def test_dry_run_only_warns_about_the_font(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0, self.out)
        self.assertIn("WARN  stop embedded font", self.out)
        self.assertIn("--accept-embedded-font", self.out)


class BuildTests(Base):
    def test_only_final_version_published_by_default(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0, self.out)
        j = self.pubjson()
        self.assertEqual(len(self.pc("p001")["V"]), 1)
        self.assertEqual(self.pc("p001")["V"][0]["id"], "p001-1")
        self.assertEqual([p["id"] for p in j["pages"]], ["pg2"])
        self.assertFalse((self.work / "build" / "img" / "p" / "pg1.jpg").exists())
        self.assertEqual((self.pc("p001")["st"], self.pc("p001")["top"]), ([0], 0))

    def test_include_versions_publishes_the_stack_and_says_it_needs_approval(self):
        self.prepare(release={"p004": {"pool": "series"}})
        self.assertEqual(self.go("p001", "--include-versions", "--accept-shared-scan", "p004"), 0, self.out)
        self.assertIn("needs the author's approval", self.out)
        j = self.pubjson()
        self.assertEqual(len(self.pc("p001")["V"]), 2)
        self.assertEqual(sorted(p["id"] for p in j["pages"]), ["pg1", "pg2"])
        self.assertEqual((self.pc("p001")["st"], self.pc("p001")["top"]), ([1, 0], 1))

    def test_decided_final_overrides_the_top_of_the_stack(self):
        self.prepare(pids=("p006",), public=(), decisions={"nothing-shines-final": {"choice": "diary53-0", "note": "", "at": "x"}})
        self.assertEqual(self.go("p006"), 0, self.out)
        j = self.pubjson()
        self.assertEqual([v["id"] for v in self.pc("p006")["V"]], ["p006-0"])
        self.assertEqual([p["id"] for p in j["pages"]], ["diary53"])
        self.assertIn("decided final", self.out)

    def test_layers_decision_falls_back_to_top_with_a_warning(self):
        self.prepare(pids=("p006",), public=(), decisions={"nothing-shines-final": {"choice": "layers", "note": "", "at": "x"}})
        self.assertEqual(self.go("p006"), 0, self.out)
        self.assertEqual([v["id"] for v in self.pc("p006")["V"]], ["p006-1"])
        self.assertIn("keep drafts as layers", self.out)

    def test_corrections_applied_and_confirmed_lines_keep_machine_reading(self):
        fixed = "AUTHOR-CORRECTION one"
        orig = line_text("p001", 1, 0, 1)
        self.prepare(reviews={"pg2-0-1": {"status": "corrected", "text": fixed, "original": orig}})
        self.assertEqual(self.go("p001"), 0, self.out)
        L = self.pubjson()["pages"][0]["B"][0]["L"]
        self.assertEqual(L, [line_text("p001", 1, 0, 0), fixed, line_text("p001", 1, 0, 2)])
        self.assertIn("1 correction(s) applied", self.out)
        self.assertNotIn(fixed, self.out)  # text is never printed

    def test_top_of_stack_that_is_not_the_last_version_is_published_with_a_warning(self):
        self.prepare(pids=("p007",), public=())
        self.assertEqual(self.go("p007"), 0, self.out)
        self.assertEqual([v["id"] for v in self.pc("p007")["V"]], ["p007-0"])
        self.assertIn("WARNING  p007: the top of the stack (V[0]) is not the last entry of V (V[1])", self.out)

    def test_info_panel_sentences_from_prov_are_listed_as_warnings(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0, self.out)
        self.assertIn("WARNING  info panel text produced from prov: Machine transcription (2026-01-01), not yet checked by the author", self.out)
        self.assertIn("empty link, empty commit and empty path", self.out)

    def test_correction_without_text_does_not_pass_gate_b(self):
        self.prepare(reviews={"pg2-0-1": {"status": "corrected", "original": line_text("p001", 1, 0, 1)}})
        self.assertEqual(self.go("p001"), 2, self.out)

    def test_noindex_in_index_and_headers(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0, self.out)
        html = (self.work / "build" / "index.html").read_text()
        self.assertIn('<meta name="robots" content="noindex">', html)
        vp = html.index("<meta name=viewport")
        self.assertEqual(html.index('<meta name="robots"'), html.index(">", vp) + 1)
        self.assertEqual((self.work / "build" / "_headers").read_text(), "/*\n  X-Robots-Tag: noindex\n")
        self.assertIn("<title>Fixture Title</title>", html)  # title untouched
        self.assertIn("WARNING  visible title is 'Fixture Title'", self.out)

    def test_prov_source_keys_removed(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0, self.out)
        prov = self.pubjson()["prov"]
        self.assertFalse({"repo", "commit", "path"} & set(prov))
        self.assertEqual(set(prov), {"tdate", "verified"})
        self.assertNotIn("private-source", self.all_text(self.work / "build"))

    def test_nothing_from_unreleased_pieces_in_the_output_tree(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0, self.out)
        text =self.all_text(self.work / "build")
        self.assertNotIn("SENTINEL-p003", text)
        self.assertNotIn("SENTINEL-p004", text)
        self.assertNotIn("SENTINEL-note", text)  # page reading notes
        self.assertNotIn("v0 b", text.replace("SENTINEL-p002 v0 b", ""))  # unpublished p001 version
        j = self.pubjson()
        pg2 = j["pages"][0]
        self.assertEqual(len(pg2["B"]), 2)
        for b in pg2["B"]:
            self.assertEqual(b["g"][0] in (0, 1), True)

    def test_blocks_not_published_lose_text_and_links(self):
        self.prepare(release={"p002": {"pool": "series"}}, public=())
        self.assertEqual(self.go("p001", "--accept-shared-scan", "p002"), 0, self.out)
        b1 = self.pubjson()["pages"][0]["B"][1]  # p002's block on the shared page
        self.assertEqual(b1["L"], ["", "", ""])
        self.assertNotIn("g", b1)
        self.assertNotIn("v", b1)
        self.assertIn("also carries ['p002']", self.out)
        self.assertNotIn("SENTINEL-p002", self.all_text(self.work / "build"))  # the shared page's other piece: no text anywhere

    def test_piece_links_are_renumbered(self):
        # p003 is index 2 in the source data; alone it must be index 0 in the public data
        self.prepare(pids=("p003",), public=())
        self.assertEqual(self.go("p003"), 0, self.out)
        j = self.pubjson()
        self.assertEqual([p["id"] for p in j["pieces"]], ["p003"])
        self.assertEqual(j["pages"][0]["B"][0]["g"][0], 0)
        self.assertEqual(j["pages"][0]["B"][0]["v"], 0)

    def test_leak_check_catches_unpublished_text(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0)
        src = post_poem.Source(self.root)
        out = self.work / "build"
        published = {("pg2", 0), ("pg2", 1)}
        ok = {s for pg, bi in published for s in src.jpages[pg]["B"][bi]["L"]}
        self.assertEqual(post_poem.leak_check(src, out, published, ok), [])
        # text of an unpublished piece turning up in a stray output file
        (out / "data" / "extra.json").write_text(json.dumps([line_text("p003", 0, 0, 0)]))
        self.assertIn(line_text("p003", 0, 0, 0), post_poem.leak_check(src, out, published, ok))
        (out / "data" / "extra.json").unlink()
        # an unpublished block that kept its text in the data
        j = json.loads((out / "data" / "j.json").read_text())
        j["pages"][0]["B"][1]["L"][0] = "something unpublished"
        (out / "data" / "j.json").write_text(json.dumps(j))
        self.assertIn("something unpublished", post_poem.leak_check(src, out, {("pg2", 0)}, ok))

    def test_audit_lists_strings_without_judging(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0)
        rows = post_poem.audit_strings(self.work / "build")
        kinds = {k for k, _ in rows}
        self.assertTrue({"title", "aria-label", "font embedded", "prov keys", "block notes"} <= kinds)
        self.assertIn(("title", "Fixture Title"), rows)
        self.assertIn(("aria-label", "Fixture canvas"), rows)
        self.assertIn(("prov keys", "tdate, verified"), rows)
        self.assertTrue(any(k == "font embedded" and "Test Diary" in v for k, v in rows))

    def test_dry_run_prints_file_list_with_sizes(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0)
        self.assertIn("file list:", self.out)
        self.assertRegex(self.out, r"\d+  data/j\.json")
        self.assertRegex(self.out, r"\d+  _headers")


class DryRunWritesNothing(Base):
    def snapshot(self, path):
        return {str(p.relative_to(path)): p.read_bytes() for p in sorted(Path(path).rglob("*")) if p.is_file() and ".git/" not in p.as_posix()}

    def test_dry_run_writes_nothing_and_pushes_nothing(self):
        self.prepare()
        clone, bare = make_public(self.tmp)
        before_clone, before_bare = self.snapshot(clone), git(bare, "for-each-ref")
        before_git = git(clone, "for-each-ref")
        before_private = self.snapshot(self.root)
        self.assertEqual(self.go("p001", "--force", public=clone), 0, self.out)
        self.assertEqual(self.snapshot(clone), before_clone)
        self.assertEqual(git(clone, "for-each-ref"), before_git)
        self.assertEqual(git(clone, "status", "--porcelain"), "")
        self.assertEqual(git(bare, "for-each-ref"), before_bare)
        self.assertEqual(self.snapshot(self.root), before_private)  # release/public.json untouched
        self.assertIn("DRY RUN", self.out)


class RealRunTests(Base):
    def run_real(self, *extra, **kw):
        self.clone, self.bare = make_public(self.tmp)
        return self.go("p001", "--accept-embedded-font", *extra, dry=False, public=self.clone, **kw)

    def test_no_pr_commits_a_branch_with_exactly_the_build_output(self):
        self.prepare()
        self.assertEqual(self.run_real("--no-pr"), 0, self.out)
        self.assertEqual(git(self.clone, "rev-parse", "--abbrev-ref", "HEAD"), "post/p001")
        self.assertEqual(git(self.clone, "log", "-1", "--format=%s"), "Post p001")
        self.assertEqual(git(self.clone, "status", "--porcelain"), "")
        self.assertEqual(post_poem.tree_hashes(self.clone / "site"), post_poem.tree_hashes(self.work / "build"))
        self.assertEqual(git(self.bare, "branch", "--list", "post/p001"), "")  # not pushed
        self.assertEqual(git(self.clone, "rev-parse", "main"), git(self.clone, "rev-parse", "origin/main"))  # main untouched
        self.assertEqual(json.loads((self.root / "release" / "public.json").read_text()), {"pieces": ["p002", "p001"]})
        self.assertIn('+    "p001"', self.out)
        body = (self.work / "pr-body.md").read_text()
        for h in ("## What changed", "## How verified", "## Not verified"):
            self.assertIn(h, body)
        self.assertIn("sha256 of data/j.json", body)
        self.assertNotIn("SENTINEL", body + self.out)
        self.assertNotIn("mach-p001 v", body + self.out)

    def test_all_versions_are_remembered_in_the_release_list(self):
        self.prepare(release={"p004": {"pool": "series"}})
        self.assertEqual(self.run_real("--no-pr", "--include-versions", "--accept-shared-scan", "p004"), 0, self.out)
        self.assertEqual(json.loads((self.root / "release" / "public.json").read_text()), {"pieces": ["p002", "p001"], "all_versions": ["p001"]})

    def test_pull_request_path_pushes_and_calls_gh(self):
        self.prepare()
        fake = self.tmp / "bin"
        fake.mkdir()
        log = self.tmp / "gh.log"
        gh = fake / "gh"
        gh.write_text(f"#!{sys.executable}\nimport sys, json\nopen({str(log)!r}, 'w').write(json.dumps(sys.argv[1:]))\nprint('https://example.invalid/pr/1')\n")
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        old = os.environ["PATH"]
        os.environ["PATH"] = f"{fake}{os.pathsep}{old}"
        self.addCleanup(os.environ.__setitem__, "PATH", old)
        self.assertEqual(self.run_real(), 0, self.out)
        self.assertIn("pull request: https://example.invalid/pr/1", self.out)
        args = json.loads(log.read_text())
        self.assertEqual(args[:2], ["pr", "create"])
        self.assertEqual(args[args.index("--repo") + 1], "4444J99/versforms")
        self.assertEqual(args[args.index("--head") + 1], "post/p001")
        self.assertEqual(args[args.index("--base") + 1], "main")
        self.assertIn("post/p001", git(self.bare, "branch", "--list", "post/p001"))
        self.assertNotIn("merge", args)

    def test_hard_stop_leaves_everything_untouched(self):
        self.prepare()
        self.clone, self.bare = make_public(self.tmp)
        before = git(self.clone, "for-each-ref")
        self.assertEqual(self.go("p001", dry=False, public=self.clone), 3)  # font not accepted
        self.assertEqual(git(self.clone, "for-each-ref"), before)
        self.assertEqual(json.loads((self.root / "release" / "public.json").read_text()), {"pieces": ["p002"]})


class BuildPublicCompat(Base):
    def test_empty_release_list_builds_blank_paper_with_noindex(self):
        make_private(self.root)
        out = self.tmp / "out"
        res = build_public.build(out, [], site=self.root / "site")
        self.assertEqual((out / "index.html").read_text(), build_public.SHELL)
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["index.html"])
        self.assertIn('<meta name="robots" content="noindex">', build_public.SHELL)
        self.assertEqual(res["pages"], [])

    def test_cli_still_takes_out_dir_and_release_option(self):
        make_private(self.root, extra_public=["p003"])
        out = self.tmp / "out"
        env = dict(os.environ)
        # run the real script against the synthetic site by copying it next to it
        shutil.copytree(TOOLS, self.root / "tools")
        r = subprocess.run([sys.executable, str(self.root / "tools" / "build_public.py"), str(out), "--release", str(self.root / "release" / "public.json")],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("released pieces: 1; pages: 1", r.stdout)
        self.assertIn('content="noindex"', (out / "index.html").read_text())

    def test_add_noindex_variants(self):
        n = build_public.NOINDEX_META
        self.assertEqual(build_public.add_noindex('<meta name=viewport content="a">x'), '<meta name=viewport content="a">' + n + "x")
        self.assertEqual(build_public.add_noindex('<meta name="viewport" content="a">x'), '<meta name="viewport" content="a">' + n + "x")
        self.assertEqual(build_public.add_noindex('<head><meta name="robots" content="all">'), "<head>" + n)
        self.assertEqual(build_public.add_noindex("<head>x"), "<head>" + n + "x")
        with self.assertRaises(ValueError):
            build_public.add_noindex("no head here")


if __name__ == "__main__":
    unittest.main()
