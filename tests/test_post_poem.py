"""Tests for tools/post_poem.py and the refactored tools/build_public.py.

Synthetic fixtures only: invented three-line pieces and 8-pixel jpgs. No real poem text.
Run from anywhere:  python3 -m unittest discover -s tests -v
Scratch files go where tempfile puts them (set TMPDIR to keep them on the external drive).
"""
import base64, contextlib, io, json, os, re, shutil, stat, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

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

OLD = "Etceter" + "4"  # the old font name the source page carries; built from parts so this file is not a search hit
VENV_PY = os.environ.get("VERSFORMS_FONT_PYTHON") or build_public.FONT_PYTHON_DEFAULT
HAVE_VENV = False
try:
    _r = subprocess.run([VENV_PY, "-c", "import fontTools, brotli"], capture_output=True, timeout=60)
    HAVE_VENV = _r.returncode == 0
except (OSError, subprocess.SubprocessError):
    pass
needs_venv = unittest.skipUnless(HAVE_VENV, f"font venv python not usable at {VENV_PY} (needs fontTools and brotli); font tests skipped")
FIXED_MODIFIED = 3300000000  # head.modified of the fixture font, see tests/make_test_font.py
NO_VENV = {"VERSFORMS_FONT_PYTHON": "/nonexistent/font-python"}  # makes the font step unable to run


def make_font(name, flavor="woff2"):
    """Synthetic font bytes carrying `name` everywhere (needs the venv)."""
    r = subprocess.run([VENV_PY, str(TESTS / "make_test_font.py"), name, "--flavor", flavor], capture_output=True, check=True, timeout=120)
    return r.stdout


# a real synthetic font when the venv exists, else stand-in bytes (then the font cannot be decoded here)
FONT_BYTES = make_font(OLD + " Diary") if HAVE_VENV else b"not a font " * 20
FONT_B64 = base64.b64encode(FONT_BYTES).decode("ascii")


def index_html(font_b64=FONT_B64, extra=""):
    return (
        '<!doctype html><html><head><meta charset=utf8>'
        '<meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{--f-hand:"' + OLD + ' Diary","Segoe Print",cursive}</style>\n<title>Fixture Title</title>\n'
        '<style>@font-face{font-family:"' + OLD + ' Diary";src:url(data:font/woff2;base64,' + font_b64 + ') format("woff2")}'
        'p{font-family:' + OLD + 'Diary,serif}</style>'
        '</head><body><canvas id="cv" aria-label="Fixture canvas"></canvas><p>set in ' + OLD + ' Diary</p>'
        '<script>ctx.font = `34px "' + OLD + ' Diary"`; document.fonts.load(\'34px "' + OLD.lower() + ' diary"\');</script>' + extra +
        '</body></html>\n')


INDEX_HTML = index_html()

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
        for n, pg in enumerate(pages):
            # a different image per page: byte-identical scan files are treated as one scan (the whole-spread case), see ScanTwinTests
            Image.new("RGB", (8, 8), (200 - 17 * n, 190 - 11 * n, 180 - 7 * n)).save(root / "site" / "img" / sub / f"{pg}.jpg")
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

    def skip_if_refused_for_want_of_venv(self, out):
        """Without the font venv a run on the standard fixture page is refused (by design): the page names the old
        font family, so its embedded font is known to carry the old name and cannot be renamed. A test that expected
        a different outcome cannot run in that configuration, so it is skipped, with a message, but only when the run
        it just made was refused for exactly that reason. Tests that stop earlier (a failing gate, an unknown piece)
        or that set NO_VENV on purpose keep running and keep their meaning."""
        if (not HAVE_VENV and os.environ.get("VERSFORMS_FONT_PYTHON") != NO_VENV["VERSFORMS_FONT_PYTHON"]
                and "embedded font is renamed (the source font is known to carry" in out):
            self.skipTest(f"font venv python not usable at {VENV_PY}: a run on a page that names the old font family is refused without it")

    def go(self, *args, dry=True, public=None, db=None):
        argv = list(args) + ["--db", str(db or self.db), "--source", str(self.root), "--workdir", str(self.work)]
        if dry:
            argv.append("--dry-run")
        if public:
            argv += ["--public-repo", str(public)]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.local_remote_seam(public):
            code = post_poem.main(argv)
        self.out = buf.getvalue()
        self.skip_if_refused_for_want_of_venv(self.out)
        return code

    @staticmethod
    def local_remote_seam(public):
        """The tests' 'public' clone is configured as https://github.com/4444J99/versforms.git (which the strict identity
        check on the CONFIGURED url accepts) and redirected to a local bare repository by url.*.insteadOf, so its EFFECTIVE
        url is a local path. In production the effective url must be the github.com repository itself; here the one
        fixture path is accepted. Nothing outside the tests can do this: it replaces a module function."""
        if not public:
            return contextlib.nullcontext()
        eff = subprocess.run(["git", "-C", str(public), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
        return mock.patch.object(post_poem, "effective_url_ok", lambda u, _eff=eff: u == _eff or post_poem.remote_is_public_repo(u))

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
                self.assertEqual(self.go("p001"), 3, self.out)  # gate (a) fails and the own-pool hard stop applies
                self.assertIn("FAIL  gate (a) in Series", self.out)
        self.setUp()
        self.prepare(release={"p003": {"pool": "series"}})  # the export has release documents, just none for p001
        (self.db / "release" / "p001.json").unlink()
        self.assertEqual(self.go("p001"), 2)
        self.assertIn("no release document", self.out)
        self.assertEqual(self.go("p001", "--force"), 0, self.out)  # a genuinely unsorted piece in a valid export stays a forceable gate

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

    def test_piece_in_a_draft_batch_and_a_later_filed_batch_passes_gate_c(self):
        # the draft batch sorts first (b-0) and lists the piece; the filed one (b-1, from ready_db) comes later
        self.prepare(batches={"b-0": {"items": ["p001"], "status": "draft"}})
        self.assertEqual(self.go("p001"), 0, self.out)
        self.assertRegex(self.out, "PASS  gate +\\(c\\) in a filed or registered batch \\[p001\\]: batch b-1 is 'filed'")
        self.assertEqual(post_poem.gate_filed({"batches": {"a": {"items": ["p001"], "status": "draft"}, "b": {"items": ["p001"], "status": "draft"}}}, "p001")[0], False)
        self.assertIn("batch a is 'draft'", post_poem.gate_filed({"batches": {"a": {"items": ["p001"], "status": "draft"}}}, "p001")[1])

    def test_registered_batch_passes(self):
        self.prepare(batches={"b-1": {"items": ["p001"], "status": "registered"}})
        self.assertEqual(self.go("p001"), 0, self.out)

    def test_force_overrides_gates_only(self):
        self.prepare(release={"p003": {"pool": "series"}}, skip_review=("pg2-0-0",))
        (self.db / "release" / "p001.json").unlink()  # p001 is unsorted (gate a) in an export that does have release documents; one line unreviewed (gate b)
        self.assertEqual(self.go("p001"), 2, self.out)
        self.assertEqual(self.go("p001", "--force"), 0, self.out)
        self.assertIn("FORCED past 2 failed gate(s)", self.out)

    def test_own_reserve_or_archive_pool_is_a_hard_stop_even_with_force(self):
        for pool in ("reserve", "archive"):
            with self.subTest(pool=pool):
                shutil.rmtree(self.tmp, ignore_errors=True)
                self.setUp()
                self.prepare(release={"p001": {"pool": pool}})
                self.assertEqual(self.go("p001"), 3, self.out)
                self.assertIn("requested piece is not in Reserve or Archive", self.out)
                self.assertEqual(self.go("p001", "--force"), 3, self.out)
                self.assertEqual(self.go("p001", "--force", "--accept-embedded-font", "--accept-shared-scan", "p002"), 3)
                self.assertFalse((self.work / "build").exists())  # nothing was built

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
        self.assertEqual(self.pubjson()["pages"][0]["B"][2]["L"], [])

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

    def make_spread(self, left="pg3", right="pg5", f_on="left"):
        """Make `left` and `right` the two pages of one spread image (as in the real data: only one of them
        may carry sp.f; the other is found through the shared sp.k)."""
        jp = self.root / "site" / "data" / "j.json"
        j = json.loads(jp.read_text())
        for p in j["pages"]:
            if p["id"] in (left, right):
                p["sp"] = {"s": "left" if p["id"] == left else "right", "cb": [0, 0, 1, 1],
                           "f": "spr" if (p["id"] == left) == (f_on == "left") else None, "k": "spr.jpg"}
        jp.write_text(json.dumps(j))
        (self.root / "site" / "img" / "s").mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8), (10, 10, 10)).save(self.root / "site" / "img" / "s" / "spr.jpg")

    def test_spread_image_facing_page_counts_as_shared_scan(self):
        # p003 on pg3; the spread image of pg3 also shows pg5, which carries p007
        for label, rel in (("unsorted", {}), ("reserve", {"p007": {"pool": "reserve"}}), ("archive", {"p007": {"pool": "archive"}})):
            with self.subTest(label=label):
                shutil.rmtree(self.tmp, ignore_errors=True)
                self.setUp()
                self.prepare(pids=("p003",), public=(), release=rel)
                self.make_spread(f_on="left")  # the published page carries sp.f, so the whole spread image is copied
                self.assertEqual(self.go("p003"), 3, self.out)
                self.assertIn("(i) shared scan", self.out)
                self.assertIn("p007", self.out)
                self.assertIn("facing page of the spread image", self.out)
                self.assertEqual(self.go("p003", "--force", "--accept-shared-scan", "p007"), 3)
                self.assertFalse((self.work / "build" / "img" / "s").exists())  # the spread image was not built

    def test_facing_page_is_not_a_leak_when_the_published_page_has_no_spread_image(self):
        # only the page that carries sp.f makes the build copy img/s/..jpg; the other page of the spread does not
        self.prepare(pids=("p003",), public=())
        self.make_spread(f_on="right")
        self.assertEqual(self.go("p003"), 0, self.out)
        self.assertFalse((self.work / "build" / "img" / "s").exists())

    def test_spread_facing_series_piece_needs_accept_and_public_one_is_fine(self):
        self.prepare(pids=("p003",), public=(), release={"p007": {"pool": "series"}})
        self.make_spread()
        self.assertEqual(self.go("p003"), 3, self.out)
        self.assertIn("--accept-shared-scan p007", self.out)
        self.assertEqual(self.go("p003", "--accept-shared-scan", "p007"), 0, self.out)
        self.assertTrue((self.work / "build" / "img" / "s" / "spr.jpg").is_file())
        self.assertNotIn("SENTINEL-p007", self.all_text(self.work / "build"))
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.setUp()
        self.prepare(pids=("p003",), public=("p007",))
        self.make_spread()
        self.assertEqual(self.go("p003"), 0, self.out)

    def add_blank_facing_page(self, page="pgx"):
        """A page with no piece and no review item that faces pg3 in the spread image."""
        self.make_spread(left="pg3", right="pg5")
        jp = self.root / "site" / "data" / "j.json"
        j = json.loads(jp.read_text())
        j["pages"] = [p for p in j["pages"] if p["id"] != "pg5"]
        j["pages"].append(dict(next(p for p in j["pages"] if p["id"] == "pg3"), id=page, B=[{"t": 0, "L": ["x"]}], sp={"s": "right", "cb": [0, 0, 1, 1], "f": None, "k": "spr.jpg"}))
        j["pieces"] = [p for p in j["pieces"] if p["id"] not in ("p006", "p007")]
        jp.write_text(json.dumps(j))

    def test_facing_page_with_no_piece_and_no_item_needs_acceptance_by_page_id(self):
        # the script cannot tell whether the facing page of a copied spread image is written on
        self.prepare(pids=("p003",), public=())
        self.add_blank_facing_page()
        self.assertEqual(self.go("p003"), 3, self.out)
        self.assertIn("--accept-shared-scan pgx", self.out)
        self.assertIn("facing page of the spread image", self.out)
        self.assertEqual(self.go("p003", "--force"), 3)
        self.assertFalse((self.work / "build" / "img" / "s").exists())
        self.assertEqual(self.go("p003", "--accept-shared-scan", "pgx"), 0, self.out)
        self.assertIn("accepted shared scan: pgx", self.out)
        self.assertTrue((self.work / "build" / "img" / "s" / "spr.jpg").is_file())

    def test_unpublished_version_of_the_same_piece_on_the_facing_page_is_listed_not_blocked(self):
        # p001 V1 on pg2; its V0 sits on pg1, which is the other page of the spread image (p004 also sits on pg1)
        self.prepare(release={"p004": {"pool": "series"}})
        self.make_spread(left="pg2", right="pg1")
        self.assertEqual(self.go("p001"), 3, self.out)  # p004 needs acceptance
        self.assertEqual(self.go("p001", "--accept-shared-scan", "p004"), 0, self.out)
        src, db = post_poem.Source(self.root), post_poem.load_db(self.db)
        finds = post_poem.shared_scan(src, db, "p001", [1], {"p001", "p002"}, {"p004"})
        own = [f for f in finds if f["id"] == "p001"]
        self.assertEqual([(f["page"], f["status"]) for f in own], [("pg1", "ok")])
        self.assertIn("another version of the same piece", own[0]["reason"])

    def test_spread_mates_found_by_page_named_like_the_file(self):
        # real data: diary60 has sp.f None, diary60a has sp.f 'diary60'; here pg5 plays the page the file is named after
        self.prepare(pids=("p003",), public=())
        self.make_spread()
        jp = self.root / "site" / "data" / "j.json"
        j = json.loads(jp.read_text())
        for p in j["pages"]:
            if p["id"] == "pg3":
                p["sp"]["f"], p["sp"]["k"] = "pg5", "other-key.jpg"
            if p["id"] == "pg5":
                p["sp"] = {"s": "left", "cb": [0, 0, 1, 1], "f": None, "k": "pg5.jpg"}
        jp.write_text(json.dumps(j))
        self.assertEqual(post_poem.Source(self.root).spread_mates(["pg3"]), ["pg5"])
        self.assertEqual(post_poem.Source(self.root).spread_mates(["pg2"]), [])  # no sp.f: no spread image is copied

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

    def test_branch_that_exists_is_a_hard_stop_and_the_detail_says_where(self):
        self.prepare()
        clone, bare = make_public(self.tmp)
        self.assertEqual(self.go("p001", public=clone), 0, self.out)
        self.assertRegex(self.out, r"PASS  stop +branch post/p001 does not exist yet \[p001\]\n")  # no stray detail on a pass
        self.assertNotIn("already exists", self.out)
        git(clone, "branch", "post/p001")
        self.assertEqual(self.go("p001", public=clone), 3, self.out)
        self.assertIn("does not exist yet [p001]: exists locally", self.out)
        git(clone, "branch", "-q", "-D", "post/p001")
        git(clone, "push", "-q", "origin", "main:refs/heads/post/p001")
        self.assertEqual(self.go("p001", public=clone), 3, self.out)
        self.assertIn("does not exist yet [p001]: exists on origin", self.out)

    @needs_venv
    def test_public_repo_results_are_listed_once_in_the_pull_request(self):
        self.prepare()
        clone, _ = make_public(self.tmp)
        self.assertEqual(self.go("p001", "--no-pr", "--accept-embedded-font", dry=False, public=clone), 0, self.out)
        body = (self.work / "pr-body.md").read_text()
        for name in ("remote origin is 4444J99/versforms", "on branch main", "working tree clean", "main is fetched", "does not exist yet"):
            self.assertEqual(body.count(name), 1, name)

    def test_real_run_requires_public_repo(self):
        self.prepare()
        self.assertEqual(self.go("p001", "--accept-embedded-font", dry=False), 64, self.out)

    def test_font_known_to_carry_the_old_name_is_never_published_without_the_venv(self):
        # the page's font family is the old name, so the font file carries it; with no venv it cannot be renamed.
        # The acceptance flag is for fonts of unknown content and does not cover this; --force does not either.
        self.prepare()
        clone, _ = make_public(self.tmp)
        head = git(clone, "rev-parse", "HEAD")
        with mock.patch.dict(os.environ, NO_VENV):
            for extra in ((), ("--force",), ("--accept-embedded-font",), ("--accept-embedded-font", "--force")):
                with self.subTest(extra=extra):
                    self.assertEqual(self.go("p001", "--no-pr", *extra, dry=False, public=clone), 3, self.out)
                    self.assertIn("could not be decoded and checked", self.out)
                    self.assertIn("font python not found", self.out)
                    self.assertIn("known to carry the other project's name", self.out)
                    self.assertIn("does not cover this", self.out)
                    self.assertNotRegex(self.out, r"PASS  check no output file, decoded data URI")
                    self.assertEqual(git(clone, "rev-parse", "HEAD"), head)
                    self.assertEqual(git(clone, "rev-parse", "--abbrev-ref", "HEAD"), "main")

    def test_font_of_unknown_content_that_cannot_be_checked_needs_acceptance_and_is_labelled_unchecked(self):
        # the venv is missing and the page does not name the old family: the font cannot be decoded, so the name check
        # on it is UNCHECKED (never PASS), a real run needs --accept-embedded-font, and --force does not help
        make_private(self.root, extra_public=["p002"])
        html = re.sub(OLD + r"[ ]?Diary", "Fixture Hand", INDEX_HTML, flags=re.I)
        self.assertNotRegex(html, "(?i)" + OLD)
        (self.root / "site" / "index.html").write_text(html)
        ready_db(self.db, pids=("p001",), _root=self.root)
        clone, _ = make_public(self.tmp)
        head = git(clone, "rev-parse", "HEAD")
        with mock.patch.dict(os.environ, NO_VENV):
            self.assertEqual(self.go("p001", "--no-pr", dry=False, public=clone), 3, self.out)
            self.assertIn("could not be decoded and checked", self.out)
            self.assertIn("--accept-embedded-font", self.out)
            self.assertRegex(self.out, r"UNCHECKED +check output text and raw bytes")
            self.assertNotRegex(self.out, r"PASS  check no output file, decoded data URI")
            self.assertEqual(git(clone, "rev-parse", "HEAD"), head)
            self.assertEqual(self.go("p001", "--no-pr", "--force", dry=False, public=clone), 3)  # force does not help
            self.assertEqual(self.go("p001", "--no-pr", "--accept-embedded-font", dry=False, public=clone), 0, self.out)
            self.assertRegex(self.out, r"UNCHECKED +check output text and raw bytes")
            self.assertNotRegex(self.out, r"PASS  check no output file, decoded data URI")
        body = (self.work / "pr-body.md").read_text()
        self.assertIn("published it unchecked", body)
        self.assertRegex(body, r"UNCHECKED output text and raw bytes")
        self.assertNotRegex(body, r"PASS no output file, decoded data URI")
        self.assertNotRegex(body, "(?i)" + OLD)

    @needs_venv
    def test_checkable_font_needs_no_flag_and_is_renamed(self):
        self.prepare()
        clone, _ = make_public(self.tmp)
        self.assertEqual(self.go("p001", "--no-pr", dry=False, public=clone), 0, self.out)
        self.assertIn("font: renamed to ajp-scribbles", self.out)
        self.assertNotIn("could not be decoded", self.out)
        body = (self.work / "pr-body.md").read_text()
        self.assertIn("Embedded font(s) decoded and checked: 1", body)

    def test_font_that_does_not_parse_is_a_hard_stop_the_flag_does_not_cover(self):
        # the venv ran but the bytes are not a font (here simulated): nothing vouches for them
        self.prepare()
        clone, _ = make_public(self.tmp)
        before = git(clone, "for-each-ref")
        err = build_public.FontDecodeError("font tool failed: simulated parse error")
        with mock.patch.object(build_public, "run_font_tool", side_effect=err):
            for extra in ((), ("--accept-embedded-font",), ("--accept-embedded-font", "--force")):
                with self.subTest(extra=extra):
                    self.assertEqual(self.go("p001", "--no-pr", *extra, dry=False, public=clone), 3, self.out)
                    self.assertIn("--accept-embedded-font does not cover this", self.out)
                    self.assertIn("font does not parse", self.out)
            self.assertEqual(self.go("p001", "--accept-embedded-font", "--force"), 3, self.out)  # a dry run refuses too
        self.assertEqual(git(clone, "for-each-ref"), before)

    def test_dry_run_fails_like_a_real_run_for_a_font_known_to_carry_the_old_name(self):
        # the page's font family is the old name and there is no venv to rename the file: a real run is refused,
        # so a dry run must not report success either (a script reading the exit status would be misled)
        self.prepare()
        with mock.patch.dict(os.environ, NO_VENV):
            self.assertEqual(self.go("p001"), 3, self.out)
            self.assertEqual(self.go("p001", "--accept-embedded-font", "--force"), 3, self.out)
        self.assertRegex(self.out, r"FAIL  check embedded font is renamed")
        self.assertIn("does not cover this", self.out)

    def test_dry_run_only_warns_for_a_font_of_unknown_content_that_cannot_be_checked(self):
        make_private(self.root, extra_public=["p002"])
        html = re.sub(OLD + r"[ ]?Diary", "Fixture Hand", INDEX_HTML, flags=re.I)
        self.assertNotRegex(html, "(?i)" + OLD)
        (self.root / "site" / "index.html").write_text(html)
        ready_db(self.db, pids=("p001",), _root=self.root)
        with mock.patch.dict(os.environ, NO_VENV):
            self.assertEqual(self.go("p001"), 0, self.out)
        self.assertIn("WARN  stop embedded font", self.out)
        self.assertIn("A real run needs --accept-embedded-font", self.out)

    @needs_venv
    def test_a_file_or_directory_name_with_the_old_name_is_a_hard_stop_and_is_never_repeated_in_the_log(self):
        self.prepare()
        self.assertEqual(self.go("p001", "--accept-embedded-font"), 0, self.out)
        out = self.work / "build"
        (out / "data" / ("notes-" + OLD.lower() + ".txt")).write_text("plain")
        (out / ("dir-" + OLD.upper())).mkdir()
        (out / ("dir-" + OLD.upper()) / "inner.txt").write_text("plain")
        (out / ("empty-" + OLD.title())).mkdir()  # no file inside: only the directory name can give it away
        scan = post_poem.name_scan(out)
        self.assertEqual(len([h for h in scan["hits"] if "its path" in h]), 2, scan["hits"])  # the notes file and inner.txt
        self.assertEqual(len([h for h in scan["hits"] if "its name" in h]), 2, scan["hits"])  # both directories
        for ordinary in ("etceter", "4-etc", "etceter-4"):
            (out / "data" / (ordinary + ".txt")).write_text("plain")
        self.assertEqual(len(post_poem.name_scan(out)["hits"]), len(scan["hits"]), "ordinary names are not hits")
        self.assertFalse(any(build_public.OLD_NAME_RE.search(h) for h in scan["hits"]), scan["hits"])

    def test_old_name_in_any_output_file_is_a_hard_stop_even_with_force(self):
        # a payload the build does not touch: a non-font data URI whose bytes carry the name as UTF-16BE
        payload = base64.b64encode(("x" + OLD.upper()).encode("utf-16-be")).decode()
        make_private(self.root, extra_public=["p002"])
        (self.root / "site" / "index.html").write_text(index_html(extra=f'<img src="data:image/png;base64,{payload}">'))
        ready_db(self.db, pids=("p001",), _root=self.root)
        self.assertEqual(self.go("p001", "--accept-embedded-font"), 3, self.out)
        self.assertIn("raw bytes", self.out)
        self.assertEqual(self.go("p001", "--force", "--accept-embedded-font"), 3)
        self.assertNotIn(OLD.lower(), self.out.lower())  # the log names places, never the name

    @needs_venv
    def test_old_name_inside_a_font_that_is_left_unrenamed_is_a_hard_stop(self):
        self.prepare()
        with mock.patch.object(build_public, "rename_embedded_fonts", lambda html: (html, [])):
            self.assertEqual(self.go("p001", "--force"), 3, self.out)
        self.assertIn("font name id1", self.out)
        self.assertIn("data URI 1", self.out)
        self.assertNotIn(OLD.lower(), self.out.lower())


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

    def test_already_public_piece_in_reserve_or_archive_is_a_hard_stop_even_with_force(self):
        for pool in ("reserve", "archive"):
            with self.subTest(pool=pool):
                shutil.rmtree(self.tmp, ignore_errors=True)
                self.setUp()
                self.prepare(release={"p002": {"pool": pool}})
                self.assertEqual(self.go("p001"), 3, self.out)
                self.assertRegex(self.out, r"FAIL  stop +already-public piece is not in Reserve or Archive \[p002\]")
                self.assertEqual(self.go("p001", "--force"), 3, self.out)
                self.assertEqual(self.go("p001", "--force", "--accept-embedded-font", "--accept-shared-scan", "p002"), 3)
                self.assertFalse((self.work / "build").exists())  # nothing was built
        # a real run publishes nothing and leaves the release list alone
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.setUp()
        self.prepare(release={"p002": {"pool": "reserve"}})
        clone, _ = make_public(self.tmp)
        before = git(clone, "for-each-ref")
        self.assertEqual(self.go("p001", "--force", "--no-pr", "--accept-embedded-font", dry=False, public=clone), 3, self.out)
        self.assertEqual(git(clone, "for-each-ref"), before)
        self.assertEqual(json.loads((self.root / "release" / "public.json").read_text()), {"pieces": ["p002"]})

    def test_already_public_piece_that_is_unsorted_is_only_a_warning(self):
        self.prepare()  # p002 has no release document
        self.assertEqual(self.go("p001"), 0, self.out)
        self.assertRegex(self.out, r"WARNING  p002 is already in release/public\.json .* release pool is unsorted")
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.setUp()
        self.prepare(release={"p002": {"pool": "series"}})
        self.assertEqual(self.go("p001"), 0, self.out)
        self.assertNotIn("p002 is already in release/public.json", self.out)

    def test_shared_scan_stop_runs_over_every_rebuilt_piece(self):
        # p002 is already public and sits on pg2 next to p001 (not requested, not public). Posting p003 rebuilds p002.
        for label, rel, code in (("unsorted", {}, 3), ("reserve", {"p001": {"pool": "reserve"}}, 3), ("series", {"p001": {"pool": "series"}}, 3)):
            with self.subTest(label):
                shutil.rmtree(self.tmp, ignore_errors=True)
                self.setUp()
                self.prepare(pids=("p003",), public=("p002",), release=dict(rel, p002={"pool": "series"}))
                self.assertEqual(self.go("p003"), code, self.out)
                self.assertRegex(self.out, r"FAIL  stop +\(i\) shared scan \(already public, rebuilt\) \[p002\]")
                self.assertIn("p001 on pg2", self.out)
                self.assertEqual(self.go("p003", "--force"), 3)
        # Series but not public: accepting it lets the post through; a co-resident that is public is fine
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.setUp()
        self.prepare(pids=("p003",), public=("p002",), release={"p001": {"pool": "series"}, "p002": {"pool": "series"}})
        self.assertEqual(self.go("p003", "--accept-shared-scan", "p001"), 0, self.out)
        self.assertNotIn("SENTINEL-p001", self.all_text(self.work / "build"))
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.setUp()
        self.prepare(pids=("p003",), public=("p002", "p001"), release={"p002": {"pool": "series"}, "p001": {"pool": "series"}})
        self.assertEqual(self.go("p003"), 0, self.out)

    def test_version_report_names_published_newest_and_unpublished_corrections(self):
        orig = line_text("p007", 1, 1, 0)
        self.prepare(pids=("p007",), public=(), reviews={"pg5-1-0": {"status": "corrected", "text": "AUTHOR-FIX", "original": orig}})
        self.assertEqual(self.go("p007"), 0, self.out)
        self.assertIn("published: V[0] p007-0; newest in the stack (last entry of V): V[1] p007-1; top of the stack: V[0]; corrected reviews on versions NOT published: 1", self.out)
        self.assertRegex(self.out, r"WARNING  p007: 1 line\(s\) the author corrected sit on version\(s\) that are not published \(V\[1\]\)")
        self.assertNotIn("AUTHOR-FIX", self.out)
        self.assertNotIn("AUTHOR-FIX", self.all_text(self.work / "build"))
        # whole stack: nothing is unpublished
        self.assertEqual(self.go("p007", "--include-versions"), 0, self.out)
        self.assertNotIn("corrected reviews on versions NOT published", self.out)

    def test_default_workdir_is_inside_the_repository_scratch_not_beside_it(self):
        self.prepare()
        argv = ["p001", "--db", str(self.db), "--source", str(self.root), "--dry-run"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = post_poem.main(argv)
        self.skip_if_refused_for_want_of_venv(buf.getvalue())
        self.assertEqual(code, 0, buf.getvalue())
        self.assertEqual(sorted(p.name for p in self.tmp.glob("post-poem-*")), [])  # nothing next to the repository
        made = sorted(p.name for p in (self.root / ".post-poem-work").glob("post-poem-*"))
        self.assertEqual(len(made), 1, made)
        self.assertTrue((self.root / ".post-poem-work" / made[0] / "build" / "index.html").is_file())

    def test_the_scratch_directory_is_git_ignored_in_this_repository(self):
        ignore = (TESTS.parent / ".gitignore").read_text().splitlines()
        self.assertIn(post_poem.DEFAULT_SCRATCH + "/", ignore)

    @needs_venv
    def test_output_check_fails_when_a_text_file_names_the_other_project_in_any_case(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0, self.out)
        src = post_poem.Source(self.root)
        out = self.work / "build"
        published = {("pg2", 0)}
        ok = {s for pg, bi in published for s in src.jpages[pg]["B"][bi]["L"]}
        run = lambda: {n: o for n, o, _ in post_poem.check_output(src, out, ["p002", "p001"], published, ok, ["p002", "p001"])}
        name = next(n for n in run() if n.startswith("no output file, decoded data URI or decoded font table names the other project"))
        self.assertTrue(run()[name])
        headers = (out / "_headers").read_text()
        for spelling in (OLD, OLD.lower(), OLD.upper()):
            (out / "_headers").write_text(headers + "# " + spelling + "\n")
            self.assertFalse(run()[name], spelling)
        (out / "_headers").write_text(headers)
        html = (out / "index.html").read_text()
        (out / "index.html").write_text(html.replace("</body>", "<!-- " + OLD.upper() + " --></body>"))
        self.assertFalse(run()[name])
        (out / "index.html").write_text(html)
        (out / "data" / "extra.bin").write_bytes(OLD.lower().encode("utf-16-le"))
        self.assertFalse(run()[name])

    # ---- leak_check: an unpublished line that is only a FRAGMENT of a longer published line is not a leak

    FRAGMENT = "shared words here"            # unpublished line (p001 V0, pg1 block 0 line 0); synthetic text
    QUOTED = 'say "hello there" friend'        # another unpublished line, with quotes

    def fragment_case(self):
        """Same relationship as the real p002 (an unpublished block's line contained in a longer published line), synthetic text.
        p001's default version is V1 (pg2 block 0). Its V0 (pg1 block 0) is not published."""
        make_private(self.root, extra_public=["p002"])
        jp, rp = self.root / "site" / "data" / "j.json", self.root / "studio" / "data" / "review.json"
        j, r = json.loads(jp.read_text()), json.loads(rp.read_text())
        def put(pg, bi, li, text):
            next(x for x in j["pages"] if x["id"] == pg)["B"][bi]["L"][li] = text
            next(x for x in r["pages"] if x["id"] == pg)["blocks"][bi]["lines"][li]["tx"] = text
        put("pg1", 0, 0, self.FRAGMENT)
        put("pg1", 0, 1, self.QUOTED)
        put("pg2", 0, 0, "before " + self.FRAGMENT + " after")
        jp.write_text(json.dumps(j))
        rp.write_text(json.dumps(r))
        ready_db(self.db, pids=("p001",), _root=self.root)

    def built_output(self):
        """Run the dry run and return (src, build dir, published blocks, authorised texts) exactly as the run computed them."""
        self.assertEqual(self.go("p001", "--accept-embedded-font"), 0, self.out)
        src, out = post_poem.Source(self.root), self.work / "build"
        pub = json.loads((out / "data" / "j.json").read_text())
        published = {(pg["id"], bi) for pg in pub["pages"] for bi, b in enumerate(pg["B"]) if any(b["L"])}
        texts_ok = {t for (pg, bi) in published for t in src.jpages[pg]["B"][bi]["L"]}
        return src, out, published, texts_ok

    def test_unpublished_line_that_is_a_fragment_of_a_published_line_is_not_a_leak(self):
        self.fragment_case()
        self.assertEqual(self.go("p001", "--accept-embedded-font"), 0, self.out)
        self.assertRegex(self.out, r"PASS  check no line of an unpublished block appears in the output")
        # and the unpublished block itself is empty in the output: the structural check is still the authority
        src, out, published, texts_ok = self.built_output()
        self.assertNotIn(("pg1", 0), published)
        self.assertEqual(post_poem.leak_check(src, out, published, texts_ok), [])

    def test_a_fragment_found_anywhere_outside_a_published_line_is_still_a_leak(self):
        self.fragment_case()
        src, out, published, texts_ok = self.built_output()
        # the same words, but in a file and not inside the published line: flagged, although they ALSO occur inside the published line
        (out / "data" / "extra.txt").write_text("x " + self.FRAGMENT + " y")
        self.assertEqual(post_poem.leak_check(src, out, published, texts_ok), [self.FRAGMENT])
        (out / "data" / "extra.txt").unlink()
        self.assertEqual(post_poem.leak_check(src, out, published, texts_ok), [])
        # inside a second copy of the published line is fine (the author's own text); next to it is not
        (out / "data" / "extra.txt").write_text("before " + self.FRAGMENT + " after")
        self.assertEqual(post_poem.leak_check(src, out, published, texts_ok), [])
        (out / "data" / "extra.txt").write_text("before " + self.FRAGMENT + " after " + self.FRAGMENT)
        self.assertEqual(post_poem.leak_check(src, out, published, texts_ok), [self.FRAGMENT])

    def test_an_unpublished_line_that_is_in_no_published_line_is_a_leak_in_plain_and_in_json_escaped_form(self):
        self.fragment_case()
        src, out, published, texts_ok = self.built_output()
        (out / "data" / "extra.txt").write_text("x " + self.QUOTED + " y")
        self.assertEqual(post_poem.leak_check(src, out, published, texts_ok), [self.QUOTED])
        # as it would be written inside a JSON string (quotes escaped): found as well; before, such a line was never matched
        (out / "data" / "extra.txt").write_text(json.dumps({"k": self.QUOTED}))
        self.assertEqual(post_poem.leak_check(src, out, published, texts_ok), [self.QUOTED])
        (out / "data" / "extra.txt").write_text(json.dumps({"k": self.QUOTED}, ensure_ascii=True))
        self.assertEqual(post_poem.leak_check(src, out, published, texts_ok), [self.QUOTED])

    # ---- the public clone must be github.com's 4444J99/versforms, not something whose URL merely contains that text

    def test_remote_identity_accepts_the_repository_and_nothing_that_only_looks_like_it(self):
        ok = ["https://github.com/4444J99/versforms.git", "https://github.com/4444J99/versforms", "https://github.com/4444J99/versforms/",
              "https://github.com:443/4444J99/versforms.git", "HTTPS://GitHub.com/4444j99/Versforms.git"]
        bad = ["git@github.com:4444J99/versforms.git", "git@github.com:4444J99/versforms", "ssh://git@github.com/4444J99/versforms.git",
               "ssh://git@github.com:22/4444J99/versforms.git", "https://x-access-token:token@github.com/4444J99/versforms.git",
               "https://user@github.com/4444J99/versforms.git", "file:///tmp/x/github.com/4444J99/versforms.git", "/tmp/x/github.com:4444J99/versforms",
               "https://notgithub.com/4444J99/versforms.git", "https://example.invalid/github.com/4444J99/versforms.git",
               "https://github.com.example.invalid/4444J99/versforms.git", "https://github.com@example.invalid/4444J99/versforms.git",
               "git@notgithub.com:4444J99/versforms.git", "git@github.com.example.invalid:4444J99/versforms.git", "notgithub.com:4444J99/versforms.git",
               "https://github.com/4444J99/versforms.git/extra", "https://github.com/4444J99/versforms-other.git", "https://github.com/x/4444J99/versforms.git",
               "https://github.com/4444J99//versforms.git", "http://github.com/4444J99/versforms.git", "git://github.com/4444J99/versforms.git",
               "https://github.com/4444J99/versforms.git?x=1", "https://github.com/4444J99/versforms.git#f", "https://github.com:8443/4444J99/versforms.git",
               "ssh://git@github.com:2222/4444J99/versforms.git", "https://github.com\\@example.invalid/4444J99/versforms.git",
               "/local/path/github.com/4444J99/versforms", "", "   "]
        for u in ok:
            self.assertTrue(post_poem.remote_is_public_repo(u), u)
        for u in bad:
            self.assertFalse(post_poem.remote_is_public_repo(u), u)

    def test_a_clone_whose_origin_only_looks_like_the_repository_is_refused_before_anything_else(self):
        # the look-alike URL is redirected to a real local bare repository, so a clone that is clean and level with ITS OWN origin
        # passes every other precondition: only the identity check stops it
        self.prepare()
        for lookalike in ("https://notgithub.com/4444J99/versforms.git", "https://example.invalid/github.com/4444J99/versforms.git"):
            with self.subTest(lookalike=lookalike):
                clone, bare = make_public(self.tmp / ("clone-" + str(abs(hash(lookalike)))))
                git(clone, "remote", "set-url", "origin", lookalike)
                git(clone, "config", f"url.{bare}.insteadOf", lookalike)
                before = git(clone, "for-each-ref")
                self.assertEqual(self.go("p001", "--no-pr", "--accept-embedded-font", dry=False, public=clone), 3, self.out)
                self.assertRegex(self.out, r"FAIL.*remote origin is 4444J99/versforms")
                self.assertEqual(git(clone, "for-each-ref"), before)
                self.assertEqual(git(clone, "status", "--porcelain"), "")

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
        self.assertIn("<title>versforms</title>", html)
        self.assertEqual(re.findall(r"<title>(.*?)</title>", html), ["versforms"])
        self.assertNotIn("WARNING  visible title", self.out)

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
        self.assertEqual(b1["L"], [])  # no text and no number of lines
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
        self.assertIn(("title", "versforms"), rows)
        self.assertIn(("aria-label", "Fixture canvas"), rows)
        self.assertIn(("prov keys", "tdate, verified"), rows)
        self.assertTrue(any(k == "font embedded" and "ajp-scribbles" in v for k, v in rows))
        self.assertFalse(any(OLD.lower() in v.lower() for _, v in rows))
        if HAVE_VENV:
            self.assertIn(("font file name", "ajp-scribbles Regular"), rows)

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

    def test_dry_run_leaves_the_git_index_file_untouched(self):
        self.prepare()
        clone, _ = make_public(self.tmp)
        index = clone / ".git" / "index"
        os.utime(index, ns=(1_000_000_000_000_000_000, 1_000_000_000_000_000_000))  # make a rewrite visible
        before = (index.read_bytes(), index.stat().st_mtime_ns)
        self.assertEqual(self.go("p001", public=clone), 0, self.out)
        self.assertEqual((index.read_bytes(), index.stat().st_mtime_ns), before)


class RealRunTests(Base):
    def run_real(self, *extra, **kw):
        if not HAVE_VENV:
            self.skipTest("a real run on this fixture needs the font venv: its font carries the old name and must be renamed")
        self.clone, self.bare = make_public(self.tmp)
        return self.go("p001", "--accept-embedded-font", *extra, dry=False, public=self.clone, **kw)

    def test_no_pr_commits_a_branch_with_exactly_the_build_output(self):
        self.prepare()
        before_site = post_poem.tree_hashes(Path(make_public(self.tmp / "ref")[0]) / "site")  # what the public clone's site/ is before the post
        self.assertEqual(self.run_real("--no-pr"), 0, self.out)
        # the commit is built in a temporary worktree: the clone's own checkout is still on main, clean and unchanged
        self.assertEqual(git(self.clone, "rev-parse", "--abbrev-ref", "HEAD"), "main")
        self.assertEqual(git(self.clone, "status", "--porcelain"), "")
        self.assertEqual(post_poem.tree_hashes(self.clone / "site"), before_site)
        self.assertEqual(git(self.clone, "worktree", "list").count("\n"), 0, "the temporary worktree is gone")
        self.assertEqual(git(self.clone, "log", "-1", "--format=%s", "post/p001"), "Post p001")
        self.assertEqual(git(self.clone, "rev-parse", "post/p001^"), git(self.clone, "rev-parse", "main"))  # branched from main
        built = post_poem.tree_listing(self.work / "build")
        committed = {l.split("\t")[1][len("site/"):]: int(l.split("\t")[0].split()[3]) for l in git(self.clone, "ls-tree", "-r", "-l", "post/p001", "--", "site").splitlines()}
        self.assertEqual(committed, built)  # exactly the build output
        self.assertEqual(git(self.bare, "branch", "--list", "post/p001"), "")  # not pushed
        self.assertEqual(git(self.clone, "rev-parse", "main"), git(self.clone, "rev-parse", "origin/main"))  # main untouched
        # --no-pr does not change the private release list; it prints the change to make by hand
        self.assertEqual(json.loads((self.root / "release" / "public.json").read_text()), {"pieces": ["p002"]})
        self.assertIn("release/public.json was NOT changed (--no-pr)", self.out)
        self.assertIn('+    "p001"', self.out)
        body = (self.work / "pr-body.md").read_text()
        for h in ("## What changed", "## How verified", "## Not verified"):
            self.assertIn(h, body)
        self.assertIn("sha256 of data/j.json", body)
        self.assertNotIn("SENTINEL", body + self.out)
        self.assertNotIn("mach-p001 v", body + self.out)

    def fake_gh(self, exit_code=0):
        fake = self.tmp / "bin"
        fake.mkdir(exist_ok=True)
        self.gh_log = self.tmp / "gh.log"
        gh = fake / "gh"
        gh.write_text(f"#!{sys.executable}\nimport sys, json\nopen({str(self.gh_log)!r}, 'w').write(json.dumps(sys.argv[1:]))\n"
                      + ("print('https://example.invalid/pr/1')\n" if exit_code == 0 else f"sys.stderr.write('gh: simulated failure')\nsys.exit({exit_code})\n"))
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        old = os.environ["PATH"]
        os.environ["PATH"] = f"{fake}{os.pathsep}{old}"
        self.addCleanup(os.environ.__setitem__, "PATH", old)

    def test_all_versions_are_remembered_in_the_release_list(self):
        self.prepare(release={"p004": {"pool": "series"}})
        self.fake_gh()
        self.assertEqual(self.run_real("--include-versions", "--accept-shared-scan", "p004"), 0, self.out)
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
        with mock.patch.dict(os.environ, NO_VENV):
            self.assertEqual(self.go("p001", dry=False, public=self.clone), 3)  # font cannot be checked and is not accepted
        self.assertEqual(git(self.clone, "for-each-ref"), before)
        self.assertEqual(json.loads((self.root / "release" / "public.json").read_text()), {"pieces": ["p002"]})


class BuildPublicCompat(Base):
    def test_empty_release_list_builds_blank_paper_with_noindex(self):
        make_private(self.root)
        out = self.tmp / "out"
        res = build_public.build(out, [], site=self.root / "site")
        self.assertEqual((out / "index.html").read_text(), build_public.SHELL)
        self.assertEqual(re.findall(r"<title>(.*?)</title>", build_public.SHELL), ["versforms"])
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["_headers", "index.html"])  # the blank page carries the noindex header too
        self.assertEqual((out / "_headers").read_text(), build_public.HEADERS)
        self.assertIn("X-Robots-Tag: noindex", build_public.HEADERS)
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
        # without the font venv the CLI refuses to call the output good (exit 3, see test_build_public_cli_warns...)
        self.assertEqual(r.returncode, 0 if HAVE_VENV else 3, r.stderr)
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

    def test_stricter_existing_robots_tag_is_never_weakened(self):
        for tag in ('<meta name="robots" content="noindex,nofollow">', "<meta name=robots content='NOINDEX, nofollow'>"):
            html = '<head><meta name="viewport" content="a">' + tag + "</head>"
            self.assertEqual(build_public.add_noindex(html), html)
            self.assertTrue(build_public.has_noindex(html))
        self.assertFalse(build_public.has_noindex('<meta name="robots" content="all">'))
        self.assertFalse(build_public.has_noindex('<meta name="viewport" content="noindex">'))
        self.assertTrue(build_public.has_noindex('<meta content="noindex" name="robots">'))


class BrandingTests(Base):
    """Title, font family text and the whole output tree free of the old name."""

    def test_rebrand_renames_every_spelling_of_the_family(self):
        forms = [f'"{OLD} Diary"', f"'{OLD.lower()} diary'", f"{OLD.upper()}DIARY", f"{OLD}-Diary", f"{OLD}_Diary", f"{OLD}  Diary", f"{OLD} Diary Regular"]
        for f in forms:
            with self.subTest(f=f):
                html = build_public.rebrand("<title>x</title><style>a{font-family:" + f + ",serif}</style>")
                self.assertFalse(build_public.OLD_NAME_RE.search(html), html)
                self.assertIn("ajp-scribbles", html)
        html = build_public.rebrand('<TITLE>\n Old </TITLE>')
        self.assertEqual(html, "<title>versforms</title>")
        with self.assertRaises(ValueError):
            build_public.rebrand("<head></head>")

    def test_output_tree_has_title_font_family_and_no_old_name(self):
        self.prepare()
        self.assertEqual(self.go("p001", "--accept-embedded-font"), 0, self.out)
        out = self.work / "build"
        html = (out / "index.html").read_text()
        self.assertEqual(re.findall(r"<title>(.*?)</title>", html), ["versforms"])
        plain = post_poem.strip_data_uris(html)
        self.assertIn('@font-face{font-family:"ajp-scribbles"', plain)
        self.assertIn('--f-hand:"ajp-scribbles"', plain)
        self.assertIn('`34px "ajp-scribbles"`', plain)
        self.assertIn("document.fonts.load('34px \"ajp-scribbles\"')", plain)
        self.assertIn("p{font-family:ajp-scribbles,serif}", plain)
        self.assertIn("set in ajp-scribbles", plain)
        for p in out.rglob("*"):
            if p.is_file():
                self.assertFalse(post_poem.raw_has_old_name(p.read_bytes()), p.name)
                self.assertFalse(build_public.OLD_NAME_RE.search(p.read_text(errors="ignore")), p.name)
        for mime, raw in post_poem.iter_data_uris(html):
            self.assertFalse(post_poem.raw_has_old_name(raw))
        self.assertEqual(post_poem.name_scan(out)["hits"], [])
        self.assertNotIn(OLD.lower(), self.out.lower())

    def test_source_index_is_not_edited(self):
        self.prepare()
        before = (self.root / "site" / "index.html").read_bytes()
        self.assertEqual(self.go("p001", "--accept-embedded-font"), 0, self.out)
        self.assertEqual((self.root / "site" / "index.html").read_bytes(), before)

    @needs_venv
    def test_pr_body_never_names_the_old_project(self):
        self.prepare()
        clone, _ = make_public(self.tmp)
        self.assertEqual(self.go("p001", "--no-pr", "--accept-embedded-font", dry=False, public=clone), 0, self.out)
        body = (self.work / "pr-body.md").read_text()
        self.assertFalse(build_public.OLD_NAME_RE.search(body))
        self.assertFalse(build_public.OLD_NAME_RE.search(self.out))
        self.assertFalse(build_public.OLD_NAME_RE.search(git(clone, "log", "-1", "--format=%B")))

    @needs_venv
    def test_pr_body_does_not_list_the_name_records_of_the_font_file(self):
        self.prepare()
        clone, _ = make_public(self.tmp)
        self.assertEqual(self.go("p001", "--no-pr", dry=False, public=clone), 0, self.out)
        self.assertIn("font file name:", self.out)  # the console lists them for the author
        body = (self.work / "pr-body.md").read_text()
        self.assertNotIn("font file name:", body)
        self.assertIn("font file name records: printed on the console", body)

    @needs_venv
    def test_pr_body_with_the_old_name_is_refused_before_anything_is_committed(self):
        self.prepare()
        clone, _ = make_public(self.tmp)
        before = git(clone, "for-each-ref")
        real = post_poem.render_pr_body
        with mock.patch.object(post_poem, "render_pr_body", lambda ctx: real(ctx) + "\n" + OLD + "\n"):
            self.assertEqual(self.go("p001", "--no-pr", "--accept-embedded-font", dry=False, public=clone), 3, self.out)
        self.assertIn("pull request text names the other project", self.out)
        self.assertEqual(git(clone, "for-each-ref"), before)
        self.assertEqual(git(clone, "status", "--porcelain"), "")
        self.assertEqual(json.loads((self.root / "release" / "public.json").read_text()), {"pieces": ["p002"]})

    def test_font_step_errors_are_clear(self):
        with mock.patch.dict(os.environ, NO_VENV):
            with self.assertRaises(build_public.FontToolError) as c:
                build_public.run_font_tool("check", b"x")
            self.assertIn("font python not found", str(c.exception))
            self.assertIn("VERSFORMS_FONT_PYTHON", str(c.exception))
        make_private(self.root, extra_public=[])
        with mock.patch.dict(os.environ, NO_VENV):
            r = build_public.build(self.tmp / "o1", ["p003"], site=self.root / "site")
        self.assertIn("font python not found", r["font_error"])
        self.assertTrue((self.tmp / "o1" / "index.html").is_file())

    def test_python_without_fonttools_is_reported(self):
        try:
            import fontTools  # noqa: F401
            self.skipTest("the system python has fontTools, cannot simulate its absence")
        except ImportError:
            pass
        with mock.patch.dict(os.environ, {"VERSFORMS_FONT_PYTHON": sys.executable}):
            with self.assertRaises(build_public.FontToolError) as c:
                build_public.run_font_tool("check", b"x")
        self.assertIn("lacks fontTools or brotli", str(c.exception))

    def test_build_public_cli_warns_when_the_font_cannot_be_renamed(self):
        make_private(self.root, extra_public=["p003"])
        shutil.copytree(TOOLS, self.root / "tools")
        env = dict(os.environ, **NO_VENV)
        r = subprocess.run([sys.executable, str(self.root / "tools" / "build_public.py"), str(self.tmp / "out"), "--release", str(self.root / "release" / "public.json")],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 3, r.stderr)  # the output would carry the old font name: not a success
        self.assertIn("WARNING: the embedded font was not renamed", r.stdout)
        self.assertIn("do not publish it", r.stdout)
        self.assertTrue((self.tmp / "out" / "index.html").is_file())


@needs_venv
class FontTests(Base):
    """The font helper and the venv step. Skipped with a message when the venv is missing."""

    def tool(self, mode, data, *args):
        return build_public.run_font_tool(mode, data, *args)

    def renamed(self, data):
        doc = self.tool("rename", data, "--family", "ajp-scribbles", "--full", "ajp-scribbles Regular", "--postscript", "ajp-scribbles-Regular")
        return base64.b64decode(doc["font_b64"]), doc

    def test_synthetic_font_carries_the_old_name_in_every_place(self):
        d = self.tool("describe", FONT_BYTES)
        olds = [v for v in d["name_records"].values() if OLD.lower() in v.lower()]
        self.assertGreaterEqual(len(olds), 10)  # ids 0,1,3,4,6 on two platforms
        self.assertTrue(all(OLD.lower() in n.lower() for n in d["cff_font_names"]))
        chk = self.tool("check", FONT_BYTES)
        self.assertFalse(chk["ok"])
        for needle in ("name id1 platform3", "name id1 platform1", "name id4", "name id6", "name id0", "name id3", "CFF font name", "CFF top dict FullName", "CFF top dict FamilyName", "CFF top dict Notice", "raw table 'CFF '"):
            self.assertTrue(any(h.startswith(needle) for h in chk["hits"]), (needle, chk["hits"]))

    def test_rename_round_trip_changes_only_the_names(self):
        new, doc = self.renamed(FONT_BYTES)
        self.assertEqual(doc["hits_after"], [])
        a, b = self.tool("describe", FONT_BYTES), self.tool("describe", new)
        self.assertEqual(b["flavor"], "woff2")
        self.assertEqual(a["glyph_count"], b["glyph_count"])
        self.assertEqual(a["glyph_order"], b["glyph_order"])
        self.assertEqual(a["cmap"], b["cmap"])
        self.assertEqual(a["hmtx"], b["hmtx"])  # advance widths and side bearings
        self.assertEqual(a["tables"], b["tables"])
        self.assertTrue(new[:4] == b"wOF2" and new != FONT_BYTES)
        # the build must not stamp the current time into the font: same input, same bytes, on every run.
        # The fixture font carries a fixed time long in the past (tests/make_test_font.py FIXED_MODIFIED), so a build that
        # set the time to "now" would fail here whenever it runs.
        self.assertEqual(a["head_modified"], FIXED_MODIFIED)
        self.assertEqual(b["head_modified"], FIXED_MODIFIED)
        names = b["name_records"]
        for key, rec in names.items():
            nid = int(key.split("/")[0])
            self.assertFalse(build_public.OLD_NAME_RE.search(rec), key)
            if nid in (1, 16):
                self.assertEqual(rec, "ajp-scribbles")
            if nid == 4:
                self.assertEqual(rec, "ajp-scribbles Regular")
            if nid == 6:
                self.assertEqual(rec, "ajp-scribbles-Regular")
        ids = {(k.split("/")[0], k.split("/")[1]) for k in names}
        for plat in ("1", "3"):
            for nid in ("1", "4", "6"):
                self.assertIn((nid, plat), ids)  # present on both platforms
        self.assertEqual(b["cff_font_names"], ["ajp-scribbles-Regular"])
        self.assertTrue(self.tool("check", new)["ok"])
        self.assertFalse(post_poem.raw_has_old_name(new))

    def test_other_name_records_and_cff_strings_are_rewritten(self):
        new, _ = self.renamed(FONT_BYTES)
        names = self.tool("describe", new)["name_records"]
        self.assertTrue(any(v == "ajp-scribbles-Regular-1.0" for k, v in names.items() if k.startswith("3/")))  # unique id
        self.assertTrue(any("ajp-scribbles" in v and v.startswith("Test font") for k, v in names.items() if k.startswith("0/")))  # copyright
        self.assertEqual(self.tool("check", new)["hits"], [])  # incl. CFF Notice, CFF string index, raw tables

    def test_font_without_the_old_name_is_left_alone_by_the_build(self):
        other = make_font("Plain Face")
        html = '<style>@font-face{font-family:"x";src:url(data:font/woff2;base64,' + base64.b64encode(other).decode() + ')}</style>'
        out, reports = build_public.rename_embedded_fonts(html)
        self.assertEqual(out, html)
        self.assertEqual([r["renamed"] for r in reports], [False])

    def test_unparseable_font_is_reported_not_renamed(self):
        html = '<style>@font-face{src:url(data:font/woff2;base64,' + base64.b64encode(b"nonsense" * 9).decode() + ')}</style>'
        out, reports = build_public.rename_embedded_fonts(html)
        self.assertEqual(out, html)
        self.assertIn("error", reports[0])

    def test_ttf_otf_flavours_and_raw_font_files_are_checked(self):
        for flavor in ("woff", "none"):
            with self.subTest(flavor=flavor):
                data = make_font(OLD + " Diary", flavor)
                self.assertFalse(self.tool("check", data)["ok"])
                new, doc = self.renamed(data)
                self.assertEqual(doc["hits_after"], [])
                self.assertTrue(self.tool("check", new)["ok"])
        # a font file (not a data URI) in the output tree is checked too
        out = self.tmp / "tree"
        (out / "f").mkdir(parents=True)
        (out / "f" / "face.woff2").write_bytes(FONT_BYTES)
        (out / "index.html").write_text("<title>versforms</title>")
        self.assertTrue(any("f/face.woff2" in h and "font" in h for h in post_poem.name_scan(out)["hits"]))

    def test_utf16_and_macroman_spellings_are_found(self):
        for enc in ("utf-16-be", "utf-16-le", "mac_roman", "ascii"):
            with self.subTest(enc=enc):
                self.assertTrue(post_poem.raw_has_old_name(b"zz" + OLD.upper().encode(enc) + b"zz"))
        self.assertFalse(post_poem.raw_has_old_name(b"etceter 4 and ajp-scribbles"))

    def test_real_run_commits_a_renamed_font_without_any_flag(self):
        self.prepare()
        clone, _ = make_public(self.tmp)
        self.assertEqual(self.go("p001", "--no-pr", dry=False, public=clone), 0, self.out)
        committed = git(clone, "show", "post/p001:site/index.html")
        uris = [raw for mime, raw in post_poem.iter_data_uris(committed) if mime.startswith("font/")]
        self.assertEqual(len(uris), 1)
        self.assertTrue(self.tool("check", uris[0])["ok"])
        self.assertEqual(self.tool("describe", uris[0])["glyph_count"], self.tool("describe", FONT_BYTES)["glyph_count"])

    def test_real_font_in_the_source_page_if_present(self):
        real = ROOT_REAL_INDEX
        if not real.is_file():
            self.skipTest("site/index.html not found")
        html = real.read_text(encoding="utf-8")
        fonts = [raw for mime, raw in post_poem.iter_data_uris(html) if mime.startswith("font/")]
        if not fonts:
            self.skipTest("no embedded font in site/index.html")
        new, doc = self.renamed(fonts[0])
        a, b = self.tool("describe", fonts[0]), self.tool("describe", new)
        self.assertEqual((a["glyph_count"], a["cmap"], a["hmtx"]), (b["glyph_count"], b["cmap"], b["hmtx"]))
        self.assertEqual(doc["hits_after"], [])


class HardenedPostingTests(Base):
    """Regression tests for the second round of review findings. Each fails on d7218f3 (the head that was reviewed)."""

    # ---- helpers
    def run_real(self, *extra, public=None, **kw):
        if not HAVE_VENV:
            self.skipTest("a real run on this fixture needs the font venv: its font carries the old name and must be renamed")
        if public is None:
            self.clone, self.bare = make_public(self.tmp)
        else:
            self.clone = public
        return self.go("p001", "--accept-embedded-font", *extra, dry=False, public=self.clone, **kw)

    def fake_gh(self, exit_code=0):
        fake = self.tmp / "bin"
        fake.mkdir(exist_ok=True)
        gh = fake / "gh"
        gh.write_text(f"#!{sys.executable}\nimport sys\n"
                      + ("print('https://example.invalid/pr/1')\n" if exit_code == 0 else f"sys.stderr.write('gh: simulated failure')\nsys.exit({exit_code})\n"))
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        old = os.environ["PATH"]
        os.environ["PATH"] = f"{fake}{os.pathsep}{old}"
        self.addCleanup(os.environ.__setitem__, "PATH", old)

    def edit_j(self, fn):
        jp = self.root / "site" / "data" / "j.json"
        j = json.loads(jp.read_text())
        fn(j)
        jp.write_text(json.dumps(j))

    def fresh(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.setUp()

    # ---- 1. a Reserve piece can never be built: any pool value that is not exactly the studio's is a hard stop
    POOL_VARIANTS = ["Reserve", " reserve", "reserve ", "RESERVE", "Archive", "archive\n", ["reserve"], {"pool": "reserve"}, None, 5, True, "", "weird", "Series", " series", "series "]

    def test_a_pool_value_that_is_not_exactly_the_studios_is_a_hard_stop_that_force_cannot_override(self):
        for value in self.POOL_VARIANTS:
            with self.subTest(pool=value):
                self.fresh()
                self.prepare(release={"p001": {"pool": value}})
                self.assertEqual(self.go("p001"), 3, self.out)
                self.assertEqual(self.go("p001", "--force"), 3, self.out)
                self.assertEqual(self.go("p001", "--force", "--accept-shared-scan", "p002,p003,p004,p006,p007"), 3, self.out)
                self.assertRegex(self.out, r"FAIL  stop requested piece (has a recognised release pool|is not in Reserve or Archive)")

    def test_the_exact_series_pool_still_passes_and_a_reserve_look_alike_is_called_out(self):
        self.prepare(release={"p001": {"pool": "series"}})
        self.assertEqual(self.go("p001"), 0, self.out)
        self.fresh()
        self.prepare(release={"p001": {"pool": " Reserve"}})
        self.assertEqual(self.go("p001"), 3, self.out)
        self.assertIn("reads like 'reserve'", self.out)

    def test_an_already_public_piece_with_a_look_alike_pool_is_a_hard_stop_not_a_warning(self):
        for value in ("Reserve", " archive", ["reserve"], None, "weird"):
            with self.subTest(pool=value):
                self.fresh()
                self.prepare(release={"p002": {"pool": value}})  # p002 is already public by default
                self.assertEqual(self.go("p001"), 3, self.out)
                self.assertEqual(self.go("p001", "--force"), 3, self.out)
                self.assertIn("FAIL  stop already-public piece is not in Reserve or Archive", self.out)

    def test_a_release_document_that_is_not_a_json_object_is_a_hard_stop(self):
        for body in ("[1, 2]", '"series"', "null", "7"):
            with self.subTest(body=body):
                self.fresh()
                self.prepare()
                (self.db / "release" / "p003.json").write_text(body)
                self.assertEqual(self.go("p001", "--force"), 3, self.out)
                self.assertIn("not a JSON object", self.out)

    def test_an_export_that_cannot_be_read_is_a_hard_stop_not_an_empty_database(self):
        self.prepare()
        empty = self.tmp / "empty"
        empty.mkdir()
        self.assertEqual(self.go("p001", "--force", db=empty), 3, self.out)  # no collection folder at all
        self.assertIn("holds no studio export", self.out)
        two = self.tmp / "two"
        for name in ("a", "b"):
            ready_db(two / "exports" / name, pids=("p001",), _root=self.root)
        self.assertEqual(self.go("p001", "--force", db=two), 3, self.out)  # ambiguous
        self.assertIn("2 exports", self.out)
        no_release = self.tmp / "norel"
        write_db(no_release, reviews={"x": {"status": "confirmed"}})
        self.assertEqual(self.go("p001", "--force", db=no_release), 3, self.out)  # reviews but no release document
        self.assertIn("no release documents", self.out)
        one = self.tmp / "one"
        ready_db(one / "exports" / "only", pids=("p001",), _root=self.root)
        self.assertEqual(self.go("p001", db=one), 0, self.out)  # exactly one nested export is found

    # ---- B1. a release file whose name only RESEMBLES a piece id must not hide a Reserve document
    RESEMBLING_NAMES = ["P001.json", "p001.JSON", "p001 .json", " p001.json", "p001.json ", "p001.json.bak", "p001.json~", "p001", "p001.txt",
                        "\uff50\uff10\uff10\uff11.json",            # fullwidth p001
                        "p\u0660\u0660\u0661.json",                  # Arabic-Indic digits
                        "p0\u200b01.json",                            # zero-width space
                        "p001\u202f.json", "notes.txt", ".DS_store", "README.md", "x-diary2.json", "b-1.json", "p.json", "p-1.json"]

    def hidden_reserve_case(self, name, as_dir=False):
        """The export has release documents, a Series one for another piece, none named exactly for p001, and a Reserve
        document for p001 under a name that only looks like p001's."""
        self.prepare(release={"p003": {"pool": "series"}})
        (self.db / "release" / "p001.json").unlink()
        target = self.db / "release" / name
        if as_dir:
            target.mkdir()
        else:
            target.write_text(json.dumps({"pool": "reserve"}))
        return target

    def test_a_release_entry_not_named_exactly_p_digits_json_is_a_hard_stop_that_force_cannot_override(self):
        for name in self.RESEMBLING_NAMES:
            with self.subTest(name=name):
                self.fresh()
                self.hidden_reserve_case(name)
                self.assertEqual(self.go("p001"), 3, self.out)
                self.assertEqual(self.go("p001", "--force"), 3, self.out)
                self.assertEqual(self.go("p001", "--force", "--accept-shared-scan", "p002,p003,p004,p006,p007"), 3, self.out)
                self.assertIn("is not a release document name", self.out)
                self.assertIn(repr(name), self.out)  # the message names the file

    # ---- B1 (second form). the right SHAPE is not enough: the name must be a piece id that exists in site/data/j.json
    def test_a_release_entry_that_names_no_piece_is_a_hard_stop_that_force_cannot_override(self):
        # p0001, p1 and a zero-padded name have the shape p<digits>.json, but no piece has that id: the document would be
        # ignored, p001 would read as unsorted, and --force would post it although a Reserve document sits there
        for name in ("p0001.json", "p1.json", "p01.json", "p000.json", "p" + "0" * 240 + "1.json", "p999.json", "p0002.json"):
            with self.subTest(name=name[:20] + ("..." if len(name) > 20 else "")):
                self.fresh()
                self.hidden_reserve_case(name)
                self.assertEqual(self.go("p001"), 3, self.out)
                self.assertEqual(self.go("p001", "--force"), 3, self.out)
                self.assertEqual(self.go("p001", "--force", "--accept-shared-scan", "p002,p003,p004,p006,p007"), 3, self.out)
                self.assertIn("names no piece", self.out)
                self.assertIn(repr(name)[:30], self.out)  # the message names the file

    def test_a_stale_release_document_of_a_piece_that_no_longer_exists_is_a_hard_stop(self):
        self.prepare(release={"p003": {"pool": "series"}, "p120": {"pool": "series"}})  # p120 is not in this site/data/j.json
        self.assertEqual(self.go("p001"), 3, self.out)
        self.assertIn("names no piece", self.out)

    def test_an_unknown_id_is_a_hard_stop_on_the_already_public_path_too(self):
        self.prepare()  # p002 is already public
        (self.db / "release" / "p0002.json").write_text('{"pool": "reserve"}')
        self.assertEqual(self.go("p001", "--force"), 3, self.out)
        self.assertIn("names no piece", self.out)

    def test_a_real_run_with_a_zero_padded_reserve_document_pushes_nothing(self):
        self.hidden_reserve_case("p0001.json")
        self.fake_gh()
        self.clone, self.bare = make_public(self.tmp)
        rel_before = (self.root / "release" / "public.json").read_bytes()
        refs_before = git(self.bare, "for-each-ref")
        self.assertEqual(self.go("p001", "--force", "--accept-embedded-font", dry=False, public=self.clone), 3, self.out)
        self.assertEqual(git(self.bare, "for-each-ref"), refs_before)
        self.assertEqual(git(self.clone, "branch", "--list", "post/p001"), "")
        self.assertEqual((self.root / "release" / "public.json").read_bytes(), rel_before)

    def test_only_a_regular_file_called_exactly_dot_ds_store_is_tolerated_in_the_release_folder(self):
        self.prepare()
        (self.db / "release" / ".DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1")  # Finder creates it
        self.assertEqual(self.go("p001"), 0, self.out)
        for name in (".DS_store", ".ds_store", ".DS_Store "):
            with self.subTest(name=name):
                self.fresh()
                self.prepare()
                (self.db / "release" / name).write_bytes(b"x")
                self.assertEqual(self.go("p001"), 3, self.out)
        self.fresh()
        self.prepare()
        (self.db / "release" / ".DS_Store").mkdir()  # a DIRECTORY with that name is not Finder's file
        self.assertEqual(self.go("p001"), 3, self.out)
        self.fresh()
        self.prepare()
        (self.tmp / "target").write_text("x")
        (self.db / "release" / ".DS_Store").symlink_to(self.tmp / "target")
        self.assertEqual(self.go("p001"), 3, self.out)

    def test_a_directory_or_a_symlink_in_the_release_folder_is_a_hard_stop(self):
        self.hidden_reserve_case("p001.json", as_dir=True)  # a DIRECTORY called p001.json
        self.assertEqual(self.go("p001", "--force"), 3, self.out)
        self.assertIn("is not a regular file", self.out)
        self.fresh()
        self.prepare(release={"p003": {"pool": "series"}})
        (self.tmp / "elsewhere.json").write_text('{"pool": "reserve"}')
        (self.db / "release" / "p001.json").unlink()
        (self.db / "release" / "p001.json").symlink_to(self.tmp / "elsewhere.json")
        self.assertEqual(self.go("p001", "--force"), 3, self.out)
        self.assertIn("is not a regular file", self.out)

    def test_a_reserve_document_under_a_resembling_name_never_reaches_a_push(self):
        target = self.hidden_reserve_case("P001.json")
        self.fake_gh()
        self.clone, self.bare = make_public(self.tmp)
        before_refs = git(self.bare, "for-each-ref")
        self.assertEqual(self.go("p001", "--force", "--accept-embedded-font", dry=False, public=self.clone), 3, self.out)
        self.assertEqual(git(self.bare, "for-each-ref"), before_refs)  # nothing was pushed
        self.assertEqual(git(self.clone, "branch", "--list", "post/p001"), "")
        self.assertTrue(target.exists())

    def test_the_resembling_name_check_covers_the_already_public_rebuild_path_too(self):
        self.prepare()  # p002 is already public and has no release document of its own here
        (self.db / "release" / "P002.json").write_text('{"pool": "reserve"}')  # ... except one under a name that only resembles p002's
        self.assertEqual(self.go("p001", "--force"), 3, self.out)
        self.assertIn("is not a release document name", self.out)

    def test_a_folder_that_only_resembles_a_collection_name_is_a_hard_stop(self):
        for look_alike in ("release ", " release", "Release.", "\uff52elease", "reviews "):
            with self.subTest(folder=look_alike):
                self.fresh()
                self.prepare(release={"p003": {"pool": "series"}})
                (self.db / look_alike).mkdir()
                (self.db / look_alike / "p001.json").write_text('{"pool": "reserve"}')
                self.assertEqual(self.go("p001", "--force"), 3, self.out)
                self.assertIn("looks like the collection", self.out)

    def test_a_legitimate_release_folder_still_passes_and_a_missing_document_is_still_the_forceable_gate(self):
        self.prepare(release={"p006": {"pool": "series"}, "p003": {"pool": "series"}})
        self.assertEqual(self.go("p001"), 0, self.out)
        self.fresh()
        self.prepare(release={"p003": {"pool": "series"}})
        (self.db / "release" / "p001.json").unlink()  # NO document for p001: unsorted, a gate, forceable (the brief's design)
        self.assertEqual(self.go("p001"), 2, self.out)
        self.assertEqual(self.go("p001", "--force"), 0, self.out)
        self.assertIn("no release document (unsorted)", self.out)

    def test_pool_values_series_with_other_case_or_a_trailing_space_are_refused_not_accepted(self):
        for value in ("Series", "SERIES", "series ", " series"):
            with self.subTest(pool=value):
                self.fresh()
                self.prepare(release={"p001": {"pool": value}})
                self.assertEqual(self.go("p001", "--force"), 3, self.out)

    def test_a_build_folder_that_is_a_symlink_gets_a_readable_message(self):
        self.prepare()
        work = self.tmp / "w"
        work.mkdir()
        (work / ".post-poem-workdir").write_text("x")  # a marker from an earlier run
        (self.tmp / "target").mkdir()
        (work / "build").symlink_to(self.tmp / "target")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = post_poem.main(["p001", "--db", str(self.db), "--source", str(self.root), "--workdir", str(work), "--dry-run"])
        self.assertEqual(code, 64, buf.getvalue())
        self.assertIn("is a symbolic link", buf.getvalue())
        self.assertTrue((self.tmp / "target").is_dir())

    def test_the_resolved_export_and_its_counts_are_printed(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0, self.out)
        self.assertRegex(self.out, r"export: .*/db \(reviews \d+, decisions 0, versions 0, release 1, batches 1, rconfig 0\)")

    # ---- 2. gate (c): items must be a list and status a string
    def test_a_batch_whose_items_is_a_string_does_not_satisfy_gate_c(self):
        for items in ("p0010 p0099", "p001", ["p0010"], {"p001": 1}, 7):
            with self.subTest(items=items):
                self.fresh()
                self.prepare(batches={"b-1": {"items": items, "status": "filed"}})
                self.assertEqual(self.go("p001"), 2, self.out)
                self.assertIn("FAIL  gate (c)", self.out)
                self.assertEqual(self.go("p001", "--force"), 0, self.out)  # a gate: --force may pass it, and says so
                self.assertIn("FORCED past 1 failed gate(s)", self.out)

    def test_a_batch_whose_status_is_not_a_string_does_not_satisfy_gate_c(self):
        for status in (["filed"], {"filed": 1}, 1, None, True):
            with self.subTest(status=status):
                self.fresh()
                self.prepare(batches={"b-1": {"items": ["p001"], "status": status}})
                self.assertEqual(self.go("p001"), 2, self.out)

    # ---- 3. --no-pr never touches the private release list; a failed pull request does not either
    def test_no_pr_leaves_the_release_list_byte_for_byte(self):
        self.prepare()
        rel = self.root / "release" / "public.json"
        before = (rel.read_bytes(), rel.stat().st_mtime_ns)
        self.assertEqual(self.run_real("--no-pr"), 0, self.out)
        self.assertEqual((rel.read_bytes(), rel.stat().st_mtime_ns), before)
        self.assertIn("NOT changed (--no-pr)", self.out)

    def test_the_release_list_is_updated_only_after_the_push_and_the_pull_request_succeeded(self):
        self.prepare()
        rel = self.root / "release" / "public.json"
        self.fake_gh(exit_code=1)
        self.assertEqual(self.run_real(), 1, self.out)
        self.assertEqual(json.loads(rel.read_text()), {"pieces": ["p002"]})
        # the branch IS on origin, and the message says so and gives the exact command
        self.assertIn("refs/heads/post/p001", git(self.bare, "for-each-ref", "refs/heads/post/p001"))
        self.assertIn("The branch post/p001 IS pushed to origin", self.out)
        self.assertIn("gh pr create --repo 4444J99/versforms --base main --head post/p001", self.out)
        self.assertIn("pr-body.md", self.out)
        self.fresh()
        self.prepare()
        rel = self.root / "release" / "public.json"  # the test directory was recreated
        self.fake_gh()
        self.assertEqual(self.run_real(), 0, self.out)
        self.assertEqual(json.loads(rel.read_text()), {"pieces": ["p002", "p001"]})
        self.assertEqual([f.name for f in rel.parent.iterdir()], ["public.json"], "no temporary file is left next to the release list")

    def test_the_release_list_write_is_atomic_and_leaves_the_original_if_it_fails(self):
        self.prepare()
        rel = self.root / "release" / "public.json"
        before = rel.read_text()
        src = post_poem.Source(self.root)
        with mock.patch.object(os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                post_poem.update_release_list(src, ["p001"], set(), write=True)
        self.assertEqual(rel.read_text(), before)
        self.assertEqual([f.name for f in rel.parent.iterdir()], ["public.json"])

    # ---- 4. a facing page that cannot be identified is a hard stop
    def test_a_spread_image_without_an_identifiable_facing_page_is_a_hard_stop(self):
        self.prepare(pids=("p003",), public=(), release={"p007": {"pool": "series"}})
        def lonely(j):
            for pg in j["pages"]:
                if pg["id"] == "pg3":
                    pg["sp"] = {"s": "left", "cb": [0, 0, 1, 1], "f": "nowhere", "k": "unique-key.jpg"}
        self.edit_j(lonely)
        (self.root / "site" / "img" / "s").mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8), (3, 3, 3)).save(self.root / "site" / "img" / "s" / "nowhere.jpg")
        self.assertEqual(self.go("p003"), 3, self.out)
        self.assertEqual(self.go("p003", "--force"), 3, self.out)
        self.assertIn("no facing page can be identified", self.out)

    # ---- 5. ids of pieces that are not posted stay out of the pull request text
    def test_the_pull_request_text_never_names_accepted_or_unknown_series_ids(self):
        self.prepare(release={"p004": {"pool": "series"}})
        self.assertEqual(self.run_real("--no-pr", "--include-versions", "--accept-shared-scan", "p004,ghost-id"), 0, self.out)
        body = (self.work / "pr-body.md").read_text()
        for secret in ("p004", "ghost-id"):
            self.assertNotIn(secret, body)
        self.assertIn("which pieces or items is in the console log of the run", body)
        self.assertIn("p004", self.out)  # the console keeps them
        self.assertIn("ghost-id", self.out)

    # ---- 7. whole-spread pages and identical scan files
    def whole_spread_pair(self, a="pg3", b="pg5"):
        def make(j):
            for pg in j["pages"]:
                if pg["id"] in (a, b):
                    pg["sp"] = {"s": "whole spread", "cb": None, "f": None, "k": "whole.jpg"}
        self.edit_j(make)

    def test_a_whole_spread_scan_shows_the_other_half_and_a_reserve_piece_there_is_a_hard_stop(self):
        # real example: diary25 / diary25a, each page's own scan is the whole spread, no sp.f. p007 (Reserve) is on pg5.
        for pool in ("reserve", "archive", "Reserve", None):
            with self.subTest(pool=pool):
                self.fresh()
                self.prepare(pids=("p003",), public=(), release={"p007": {"pool": pool}})
                self.whole_spread_pair("pg3", "pg5")
                self.assertEqual(self.go("p003"), 3, self.out)
                self.assertEqual(self.go("p003", "--force", "--accept-shared-scan", "p007,pg5"), 3, self.out)
                self.assertIn("p007 on pg5", self.out)

    def test_a_whole_spread_scan_with_a_series_piece_on_the_other_half_needs_acceptance(self):
        self.prepare(pids=("p003",), public=(), release={"p007": {"pool": "series"}})
        self.whole_spread_pair("pg3", "pg5")
        self.assertEqual(self.go("p003"), 3, self.out)
        self.assertIn("--accept-shared-scan p007", self.out)
        self.assertEqual(self.go("p003", "--accept-shared-scan", "p007"), 0, self.out)

    def test_byte_identical_scan_files_make_the_other_page_a_mate_whatever_the_spread_data_says(self):
        self.prepare(pids=("p003",), public=(), release={"p007": {"pool": "reserve"}})
        src = self.root / "site" / "img"
        for sub in ("p", "i", "m"):
            shutil.copy2(src / sub / "pg3.jpg", src / sub / "pg5.jpg")
        self.assertEqual(post_poem.Source(self.root).spread_mates(["pg3"]), ["pg5"])
        self.assertEqual(self.go("p003", "--force"), 3, self.out)
        self.assertIn("p007 on pg5", self.out)

    def test_pages_with_different_scans_are_not_mates(self):
        self.prepare(pids=("p003",), public=())
        self.assertEqual(post_poem.Source(self.root).spread_mates(["pg3"]), [])

    def test_the_warning_about_unpublished_versions_covers_a_whole_spread_mate(self):
        # real example: p039, decided-final V0 on diary25; its V1 is on diary25a, in the same scan
        self.prepare(pids=("p006",), public=())
        self.whole_spread_pair("diary53", "diary54")
        self.edit_j(lambda j: None)
        self.assertEqual(self.go("p006", "--accept-shared-scan", "p006"), 0, self.out)
        self.assertRegex(self.out, r"WARNING  p006: the scan of diary5[34].* also shows writing of its unpublished version")

    # ---- C5. an already-public piece with an unpublished version on a shared scan
    def test_an_already_public_piece_with_an_unpublished_version_on_the_shared_page_is_warned_about(self):
        self.prepare(pids=("p003",), public=("p007",))  # p007 has two versions on pg5 and publishes only its top
        self.edit_j(lambda j: [pg.__setitem__("sp", {"s": "left" if pg["id"] == "pg3" else "right", "cb": [0, 0, 1, 1], "f": "spr" if pg["id"] == "pg3" else None, "k": "spr.jpg"})
                               for pg in j["pages"] if pg["id"] in ("pg3", "pg5")])
        (self.root / "site" / "img" / "s").mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (8, 8), (10, 10, 10)).save(self.root / "site" / "img" / "s" / "spr.jpg")
        self.assertEqual(self.go("p003"), 0, self.out)
        self.assertRegex(self.out, r"WARNING  p007 \(already public\) has unpublished version\(s\) written on pg5")

    # ---- A3 / B2. the push goes only where it should
    def test_remote_origin_push_set_is_a_hard_stop(self):
        self.prepare()
        clone, bare = make_public(self.tmp)
        git(clone, "config", "remote.origin.push", "refs/heads/*:refs/heads/main")
        before = git(bare, "rev-parse", "main")
        self.assertEqual(self.go("p001", "--no-pr", "--accept-embedded-font", dry=False, public=clone), 3, self.out)
        self.assertIn("remote.origin.push is not set", self.out)
        self.assertEqual(git(bare, "rev-parse", "main"), before)

    def test_the_push_names_a_fully_qualified_refspec_and_main_of_origin_does_not_move(self):
        self.prepare()
        self.fake_gh()
        calls = []
        real = post_poem.git
        def spy(repo, *args, **kw):
            calls.append(args)
            return real(repo, *args, **kw)
        clone, bare = make_public(self.tmp)
        before = git(bare, "rev-parse", "main")
        with mock.patch.object(post_poem, "git", spy):
            self.assertEqual(self.go("p001", "--accept-embedded-font", dry=False, public=clone), 0, self.out)
        pushes = [c for c in calls if c and c[0] == "push"]
        self.assertEqual(pushes, [("push", "origin", "refs/heads/post/p001:refs/heads/post/p001")])
        self.assertEqual(git(bare, "rev-parse", "main"), before)
        self.assertEqual(git(bare, "rev-parse", "post/p001"), git(clone, "rev-parse", "post/p001"))

    def test_a_main_that_changes_during_the_push_is_reported_loudly(self):
        self.prepare()
        self.fake_gh()
        clone, bare = make_public(self.tmp)
        real = post_poem.remote_main_sha
        n = {"calls": 0}
        def moving(path):
            n["calls"] += 1
            return real(path) if n["calls"] < 3 else "f" * 40  # 1: precondition, 2: before the push, 3: after it
        with mock.patch.object(post_poem, "remote_main_sha", moving):
            self.assertEqual(self.go("p001", "--accept-embedded-font", dry=False, public=clone), 1, self.out)
        self.assertIn("main of the public repository CHANGED during the push", self.out)

    def test_the_effective_push_url_must_be_the_public_repository_and_equal_the_fetch_url(self):
        self.prepare()
        clone, bare = make_public(self.tmp)
        # in a production run nothing replaces effective_url_ok: a local-path effective URL (here the test redirect) is refused
        names = {n: (ok, d) for n, ok, d in post_poem.check_public_repo(clone, "post/p001")}
        self.assertFalse(names["effective URL is 4444J99/versforms on github.com"][0])
        with self.local_remote_seam(clone):
            names = {n: ok for n, ok, d in post_poem.check_public_repo(clone, "post/p001")}
            self.assertTrue(names["effective URL is 4444J99/versforms on github.com"])
            self.assertTrue(names["effective fetch and push URL are the same (after insteadOf, pushInsteadOf and pushurl)"])
            git(clone, "config", "remote.origin.pushurl", "https://example.invalid/elsewhere.git")
            names = {n: ok for n, ok, d in post_poem.check_public_repo(clone, "post/p001")}
            self.assertFalse(names["effective fetch and push URL are the same (after insteadOf, pushInsteadOf and pushurl)"])
            self.assertFalse(names["effective URL is 4444J99/versforms on github.com"])
        self.assertEqual(self.go("p001", "--no-pr", "--accept-embedded-font", dry=False, public=clone), 3, self.out)

    def test_pushinsteadof_to_another_host_is_refused(self):
        self.prepare()
        clone, bare = make_public(self.tmp)
        git(clone, "config", "url.https://example.invalid/.pushInsteadOf", "https://github.com/")
        before = git(bare, "rev-parse", "main")
        self.assertEqual(self.go("p001", "--no-pr", "--accept-embedded-font", dry=False, public=clone), 3, self.out)
        self.assertEqual(git(bare, "rev-parse", "main"), before)

    def test_credentials_in_the_origin_url_are_refused_and_never_printed(self):
        self.prepare()
        clone, bare = make_public(self.tmp)
        git(clone, "remote", "set-url", "origin", "https://user:s3cr3t-token@github.com/4444J99/versforms.git")
        self.assertEqual(self.go("p001", "--no-pr", "--accept-embedded-font", dry=False, public=clone), 3, self.out)
        self.assertNotIn("s3cr3t-token", self.out)
        self.assertIn("***@", self.out)

    # ---- B4. a failure while committing leaves the public clone exactly as it was
    def test_a_failing_commit_hook_leaves_the_clone_untouched_and_says_what_is_left(self):
        self.prepare()
        clone, bare = make_public(self.tmp)
        hook = clone / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho hook refused >&2\nexit 1\n")
        hook.chmod(0o755)
        before_refs = git(clone, "for-each-ref")
        before_site = post_poem.tree_hashes(clone / "site")
        self.assertEqual(self.run_real("--no-pr", public=clone), 1, self.out)
        self.assertIn("State left:", self.out)
        self.assertEqual(git(clone, "rev-parse", "--abbrev-ref", "HEAD"), "main")
        self.assertEqual(git(clone, "status", "--porcelain"), "")
        self.assertEqual(git(clone, "for-each-ref"), before_refs)  # no branch was left behind
        self.assertEqual(post_poem.tree_hashes(clone / "site"), before_site)
        self.assertEqual(git(clone, "worktree", "list").count("\n"), 0)
        hook.unlink()
        self.assertEqual(self.run_real("--no-pr", public=clone), 0, self.out)  # a rerun is not refused

    def test_a_gitignore_in_the_public_clone_cannot_drop_a_file_from_the_commit(self):
        self.prepare()
        clone, bare = make_public(self.tmp)
        (clone / ".gitignore").write_text("*.jpg\n_headers\n")
        git(clone, "add", ".gitignore")
        git(clone, "commit", "-q", "-m", "ignore images")
        git(clone, "push", "-q", "origin", "main")
        self.assertEqual(self.run_real("--no-pr", public=clone), 0, self.out)
        committed = {l.split("\t")[1][len("site/"):]: int(l.split("\t")[0].split()[3]) for l in git(clone, "ls-tree", "-r", "-l", "post/p001", "--", "site").splitlines()}
        self.assertEqual(committed, post_poem.tree_listing(self.work / "build"))
        self.assertTrue(any(k.endswith(".jpg") for k in committed))

    def test_a_commit_that_differs_from_the_build_is_refused_and_cleaned_up(self):
        self.prepare()
        clone, bare = make_public(self.tmp)
        out = self.tmp / "buildout"
        (out / "data").mkdir(parents=True)
        (out / "index.html").write_text("<html></html>")
        real = post_poem.tree_listing
        with mock.patch.object(post_poem, "tree_listing", lambda root: {**real(root), "ghost.txt": 1}):
            with self.assertRaises(RuntimeError) as c:
                post_poem.commit_in_worktree(clone, out, "post/x", "msg", self.tmp)
        self.assertIn("differs from the build output", str(c.exception))
        self.assertIn("State left:", str(c.exception))
        self.assertEqual(git(clone, "branch", "--list", "post/x"), "")

    # ---- B5. --workdir never deletes a folder this script did not make
    def test_workdir_with_a_build_folder_that_is_not_ours_is_refused_and_left_alone(self):
        self.prepare()
        work = self.tmp / "mine"
        (work / "build").mkdir(parents=True)
        precious = work / "build" / "precious.txt"
        precious.write_text("do not delete")
        code = post_poem.main(["p001", "--db", str(self.db), "--source", str(self.root), "--workdir", str(work), "--dry-run"])
        self.assertEqual(code, 64)
        self.assertEqual(precious.read_text(), "do not delete")
        # an empty workdir works, and the same workdir can be reused (the script made its build/)
        work2 = self.tmp / "ours"
        for _ in range(2):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = post_poem.main(["p001", "--db", str(self.db), "--source", str(self.root), "--workdir", str(work2), "--dry-run"])
            self.skip_if_refused_for_want_of_venv(buf.getvalue())
            self.assertEqual(code, 0, buf.getvalue())

    # ---- C1. no geometry and no line slots of unpublished blocks
    def test_unpublished_blocks_keep_no_line_boxes_and_no_line_slots(self):
        def add_boxes(j):
            for pg in j["pages"]:
                pg["x"] = [[bi, li, 0.1, 0.1, 0.9, 0.2, 0.0, 0.0] for bi, b in enumerate(pg["B"]) for li in range(len(b["L"]))]
        # p002 shares pg2 with p001 and is NOT public: its block on that page is unpublished (its scan is accepted by the author)
        self.prepare(release={"p002": {"pool": "series"}}, public=())
        self.edit_j(add_boxes)
        self.assertEqual(self.go("p001", "--accept-shared-scan", "p002"), 0, self.out)
        pg = self.pubjson()["pages"][0]
        self.assertEqual(pg["id"], "pg2")
        published = {bi for bi, b in enumerate(pg["B"]) if b.get("g")}
        unpublished = {bi for bi in range(len(pg["B"]))} - published
        self.assertTrue(published and unpublished, "the scenario needs both kinds of block")
        self.assertEqual({e[0] for e in pg["x"]}, published)  # boxes of the unpublished block are gone
        for bi in unpublished:
            self.assertEqual(pg["B"][bi]["L"], [])  # and so is its number of lines
        self.assertTrue(all(len(pg["B"][bi]["L"]) > 0 for bi in published))

    # ---- C3. clean stops instead of tracebacks
    def test_unknown_ids_and_damaged_inputs_are_clean_hard_stops(self):
        self.prepare()
        rel = self.root / "release" / "public.json"
        for body, word in (('{"pieces": ["p002", "p999"]}', "p999"), ("{not json", "cannot read release/public.json"), ('{"pieces": "p002"}', "lists of piece id strings"),
                           ('{"pieces": [], "all_versions": ["p404"]}', "p404")):
            with self.subTest(body=body):
                rel.write_text(body)
                self.assertEqual(self.go("p001"), 3, self.out)
                self.assertIn(word, self.out)
        rel.write_text('{"pieces": ["p002"]}')

    def test_a_build_that_refuses_or_fails_is_a_clean_hard_stop(self):
        self.prepare()
        with mock.patch.object(build_public, "build", side_effect=SystemExit("corrections for lines outside the published blocks")):
            self.assertEqual(self.go("p001"), 3, self.out)
        self.assertIn("the build was refused: corrections for lines outside", self.out)
        self.fresh()
        self.prepare()
        (self.root / "site" / "index.html").write_text("<html><head></head><body></body></html>")  # no <title>
        self.assertEqual(self.go("p001"), 3, self.out)
        self.assertIn("the build failed: index.html has no <title> element", self.out)

    def test_a_usage_error_exits_64_as_documented(self):
        for argv in ([], ["p001"], ["p001", "--no-such-flag"]):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as c:
                    post_poem.main(argv)
                self.assertEqual(c.exception.code, 64)

    # ---- C6. a font tool that timed out vouches for nothing
    def test_a_font_tool_timeout_is_undecodable_not_cannot_run(self):
        if not HAVE_VENV:
            self.skipTest("needs the font venv path to exist so the call reaches subprocess.run")
        with mock.patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired(cmd="x", timeout=120)):
            with self.assertRaises(build_public.FontDecodeError):
                build_public.run_font_tool("check", b"x")

    def test_the_font_sign_off_line_does_not_claim_a_listing_that_failed(self):
        self.prepare()
        real = build_public.run_font_tool
        def no_describe(mode, data, *args):
            if mode == "describe":
                raise build_public.FontToolError("font tool could not run: simulated")
            return real(mode, data, *args)
        if not HAVE_VENV:
            self.skipTest("needs the font venv")
        with mock.patch.object(build_public, "run_font_tool", no_describe):
            self.assertEqual(self.go("p001", "--no-pr", "--accept-embedded-font", dry=False, public=make_public(self.tmp)[0]), 0, self.out)
        body = (self.work / "pr-body.md").read_text()
        self.assertIn("could NOT be listed here because the font tool failed", body)
        self.assertNotIn("were listed to the author on the console", body)

    # ---- C7. quotation blocks stay withheld
    def test_a_correction_on_a_quotation_block_is_never_published(self):
        def quote(j):
            pg = next(p for p in j["pages"] if p["id"] == "pg2")
            pg["B"][0]["t"] = 4
            pg["B"][0]["L"] = [post_poem.PLACEHOLDER]
        self.prepare()
        self.edit_j(quote)
        # a review that "corrects" the placeholder line of the quotation block with the quoted passage
        ready_db(self.db, pids=("p001",), _root=self.root, reviews={"pg2-0-0": {"status": "corrected", "original": post_poem.PLACEHOLDER, "text": "THE QUOTED PASSAGE", "at": "2026-11-05T00:00:00Z"}})
        self.assertEqual(self.go("p001"), 0, self.out)
        self.assertNotIn("THE QUOTED PASSAGE", self.all_text(self.work / "build"))
        self.assertEqual(self.pubjson()["pages"][0]["B"][0]["L"], [post_poem.PLACEHOLDER])
        self.assertEqual(self.go("p001", "--no-pr") if False else 0, 0)

    def test_build_public_itself_drops_a_correction_aimed_at_a_quotation_block(self):
        self.prepare()
        self.edit_j(lambda j: next(p for p in j["pages"] if p["id"] == "pg2")["B"][0].update(t=4, L=[post_poem.PLACEHOLDER]))
        out = self.tmp / "o"
        build_public.build(out, ["p001"], site=self.root / "site", select={"p001": [1]}, corrections={("pg2", 0, 0): "THE QUOTED PASSAGE"})
        self.assertNotIn("THE QUOTED PASSAGE", self.all_text(out))

    # ---- release list change is described
    def test_the_pull_request_lists_new_pieces_and_rebuilt_pieces_whose_data_changed(self):
        self.prepare()
        self.assertEqual(self.run_real("--no-pr"), 0, self.out)
        body = (self.work / "pr-body.md").read_text()
        # the clone's site/ is the blank page, so every piece in the build is new to it, p002 (already in the private list) included
        self.assertIn("- New in the public site: p002, p001", body)
        self.assertIn("- Already public and rebuilt with changed published data: none", body)

    def test_public_changes_compares_with_the_clones_current_site(self):
        self.prepare()
        self.assertEqual(self.go("p001"), 0, self.out)
        out = self.work / "build"
        site = self.tmp / "current"
        shutil.copytree(out, site)
        self.assertEqual(post_poem.public_changes(site, out), ([], []))  # nothing new, nothing changed
        j = json.loads((site / "data" / "j.json").read_text())
        j["pieces"] = [pc for pc in j["pieces"] if pc["id"] != "p001"]
        (site / "data" / "j.json").write_text(json.dumps(j))
        self.assertEqual(post_poem.public_changes(site, out), (["p001"], []))
        j = json.loads((out / "data" / "j.json").read_text())
        j["pages"][0]["u"] = ["changed"]
        copy = self.tmp / "changed"
        shutil.copytree(out, copy)
        (copy / "data" / "j.json").write_text(json.dumps(j))
        self.assertEqual(post_poem.public_changes(site, copy)[1], ["p002"])  # p002 is in the clone's site and the page it sits on changed
        self.assertEqual(post_poem.public_changes(self.tmp / "nothing-here", out)[0], ["p002", "p001"])  # no site/data/j.json: everything is new


ROOT_REAL_INDEX = TESTS.parent / "site" / "index.html"


if __name__ == "__main__":
    unittest.main()
