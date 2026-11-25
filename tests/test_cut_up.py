"""Cut-up version model + public-build provenance gate (journal-handwritten-web #55).

Synthetic fixtures only, reusing the private-repository and studio-export
builders from tests/test_post_poem.py: invented three-line pieces and
8-pixel jpgs. No real poem text.
Run from anywhere:  python3 -m unittest discover -s tests -v

The pool definition is #65's: every non-Series pool — reserve, archive,
unsorted (no release document), unknown (a non-exact pool value) — is
withheld. The plan forbids the Release warning and the build-time stop
drifting into two definitions of Reserve; both use pool_of()'s
exact-value rule and refuse all four.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
TOOLS = TESTS.parent / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TESTS))
import build_public  # noqa: E402
import cut_up  # noqa: E402
from test_post_poem import make_private, ready_db  # noqa: E402


def _sentinel_out(root):
    out = root / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "previous-output").write_bytes(b"keep the last successful build")
    return out


# Pages for flatten_lines / validate_version: one block of three lines each.
PAGES = {pg: {"B": [{"L": ["a", "b", "c"]}]} for pg in ("pg2", "pg3", "diary54")}


def _cut_version(src, method="cut-up"):
    return {"id": "p001-1", "s": "j", "d": None,
            "P": [["pg2", [0]]], "method": method, "src": src}


class CutUpModelTests(unittest.TestCase):
    def test_method_defaults_to_original_and_unknown_raises(self):
        self.assertEqual(cut_up.version_method({"id": "v"}), "original")
        for m in ("original", "cut-up", "erasure"):
            self.assertEqual(cut_up.version_method({"id": "v", "method": m}), m)
        with self.assertRaises(ValueError):
            cut_up.version_method({"id": "v", "method": "remix"})

    def test_flatten_lines_in_p_order(self):
        v = {"P": [["pg2", [0]], ["pg3", [0]]]}
        self.assertEqual(cut_up.flatten_lines(v),
                         [("pg2", 0), ("pg3", 0)])
        self.assertEqual(cut_up.flatten_lines(v, PAGES),
                         [("pg2", 0, 0), ("pg2", 0, 1), ("pg2", 0, 2),
                          ("pg3", 0, 0), ("pg3", 0, 1), ("pg3", 0, 2)])

    def test_validate_rejects_src_on_original_bad_entries_and_wrong_length(self):
        with self.assertRaises(ValueError):
            cut_up.validate_version(_cut_version([None] * 3, method="original"))
        with self.assertRaises(ValueError):
            cut_up.validate_version({**_cut_version([None] * 3), "src": "nope"})
        for bad in ({"piece": "p006"}, {"piece": "p006", "line": 0, "extra": 1}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                cut_up.validate_version(_cut_version([bad, None, None]))
        with self.assertRaises(ValueError):
            cut_up.validate_version(_cut_version([None] * 2), PAGES)
        self.assertEqual(cut_up.validate_version(_cut_version([None] * 3), PAGES), "cut-up")

    def test_reserve_sources_flags_every_non_series_pool(self):
        pools = {"p006": "reserve", "p004": "archive", "p007": "unsorted",
                 "p008": "unknown", "p003": "series"}
        v = {"id": "p001-1", "P": [["pg2", [0]], ["pg3", [0]]], "method": "cut-up",
             "src": [{"piece": "p006", "line": "diary54-0-0"},
                     {"piece": "p004", "line": "pg1-2-0"},
                     {"piece": "p007", "line": "pg5-0-0"},
                     {"piece": "p008", "line": "pg5-1-0"},
                     {"piece": "p003", "line": "pg3-0-0"},
                     None]}
        bad = cut_up.reserve_sources(v, lambda pid: pools[pid], PAGES)
        self.assertEqual([b["pool"] for b in bad],
                         ["reserve", "archive", "unsorted", "unknown"])
        self.assertEqual([b["src"]["piece"] for b in bad],
                         ["p006", "p004", "p007", "p008"])

    def test_reserve_sources_passes_series_and_own_lines(self):
        v = _cut_version([{"piece": "p003", "line": "pg3-0-0"}, None, None])
        self.assertEqual(cut_up.reserve_sources(v, lambda pid: "series", PAGES), [])
        self.assertEqual(cut_up.reserve_sources({"id": "v"}, lambda pid: "reserve"), [])

    def test_cut_up_record_requires_parallel_src(self):
        with self.assertRaises(ValueError):
            cut_up.cut_up_record("p001", ["a"], [None, None])
        rec = cut_up.cut_up_record("p001", ["pg2-0-0"], [None], at="2026-11-25T00:00:00Z",
                                   method="erasure", source_version="p001-0")
        self.assertEqual(rec["method"], "erasure")
        self.assertEqual(rec["sourceVersion"], "p001-0")
        self.assertNotIn("sourceVersion",
                         cut_up.cut_up_record("p001", ["pg2-0-0"], [None]))


class CutUpGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cutup-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = self.tmp / "private"
        self.db = self.tmp / "db"
        self.out = self.tmp / "out"

    def prepare(self, **dbkw):
        """p001 Series; p002 a Series co-resident on pg2 (accepted at build)."""
        make_private(self.root)
        ready_db(self.db, pids=("p001",), _root=self.root, **dbkw)

    def make_cut_up(self, src):
        """Rewrite p001's top version (V1, on pg2) as a cut-up with src."""
        jpath = self.root / "site" / "data" / "j.json"
        j = json.loads(jpath.read_text())
        pc = next(p for p in j["pieces"] if p["id"] == "p001")
        top = pc["V"][pc["top"]]
        top["method"] = "cut-up"
        top["src"] = src
        jpath.write_text(json.dumps(j))

    def build(self, **kw):
        kw.setdefault("site", self.root / "site")
        kw.setdefault("select", {"p001": [1]})
        kw.setdefault("rename_fonts", False)
        kw.setdefault("pool_db", self.db)
        kw.setdefault("accept_shared_scan", ["p002"])
        return build_public.build(self.out, ["p001"], **kw)

    def test_reserve_source_refuses_and_leaves_output_untouched(self):
        self.prepare(release={"p002": {"pool": "series"},
                              "p006": {"pool": "reserve"}})
        self.make_cut_up([{"piece": "p006", "line": "diary54-0-0"}, None, None])
        out = _sentinel_out(self.tmp)
        with self.assertRaises(SystemExit) as cm:
            self.build()
        self.assertRegex(str(cm.exception.code),
                         r"p001: cut-up version p001-1 reuses a withheld line: "
                         r"p006 line diary54-0-0 \(pool is reserve\).*output unchanged")
        self.assertEqual((out / "previous-output").read_bytes(),
                         b"keep the last successful build")
        self.assertEqual([p.name for p in out.iterdir()], ["previous-output"])

    def test_series_source_builds_and_publishes_method_and_src(self):
        self.prepare(release={"p002": {"pool": "series"},
                              "p003": {"pool": "series"}})
        self.make_cut_up([{"piece": "p003", "line": "pg3-0-0"}, None, None])
        res = self.build()
        self.assertEqual(res["pools"], {"p001": "series"})
        data = json.loads((self.out / "data" / "j.json").read_text())
        pc = next(p for p in data["pieces"] if p["id"] == "p001")
        top = pc["V"][pc["top"]]
        self.assertEqual(top["method"], "cut-up")
        self.assertEqual(top["src"], [{"piece": "p003", "line": "pg3-0-0"}, None, None])
