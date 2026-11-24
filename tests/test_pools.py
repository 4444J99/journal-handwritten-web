"""Tests for tools/pools.py (journal-handwritten-web #30).

The pool map is the reader's only pool source, so the generator must apply
post_poem.pool_of()'s exact-value rule and fail loudly on a damaged export:
a document that merely looks like Reserve must never read as Reserve, and a
piece absent from the map stays unknown (the reader never refuses on unknown).
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import pools  # noqa: E402


def write_export(base, release_docs):
    folder = Path(base) / "release"
    folder.mkdir(parents=True)
    for name, doc in release_docs.items():
        (folder / name).write_text(doc if isinstance(doc, str) else json.dumps(doc))


class TestPools(unittest.TestCase):
    def test_real_export(self):
        out = pools.build(ROOT / "exports/studio-db-pre-series-order-p006-p010-2026-11-15")
        self.assertEqual(out["generated_from"], "studio-db-pre-series-order-p006-p010-2026-11-15")
        self.assertEqual(set(out["pools"]), {"p001", "p002", "p003", "p004", "p005"})
        self.assertTrue(all(e["pool"] == "series" for e in out["pools"].values()))
        self.assertEqual(out["pools"]["p001"], {"pool": "series", "num": 1, "order": 0})
        self.assertEqual(out["pools"]["p002"], {"pool": "series", "order": 1})
        self.assertEqual(out["pools"]["p005"], {"pool": "series", "order": 4})

    def test_exact_value_rule(self):
        # p006-p010 are real piece ids in site/data/j.json, so the export
        # name check passes; only the pool VALUES differ.
        with tempfile.TemporaryDirectory() as tmp:
            write_export(tmp, {
                "p006.json": {"pool": "reserve"},
                "p007.json": {"pool": "Reserve"},
                "p008.json": {"pool": " reserve"},
                "p009.json": {},
                "p010.json": {"pool": ["series"]},
            })
            out = pools.build(tmp)
        self.assertEqual(out["pools"]["p006"]["pool"], "reserve")
        self.assertEqual(out["pools"]["p007"]["pool"], "unknown")
        self.assertEqual(out["pools"]["p008"]["pool"], "unknown")
        self.assertEqual(out["pools"]["p009"]["pool"], "unknown")
        self.assertEqual(out["pools"]["p010"]["pool"], "unknown")

    def test_damaged_export_fails_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_export(tmp, {"p006.json": "{not json"})
            out_path = Path(tmp) / "pools.json"
            rc = subprocess.run(
                [sys.executable, str(ROOT / "tools/pools.py"),
                 "--pool-db", tmp, "--out", str(out_path)],
                capture_output=True, text=True).returncode
            self.assertNotEqual(rc, 0)
            self.assertFalse(out_path.exists())

    def test_export_with_no_release_docs_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "release").mkdir()
            with self.assertRaises(Exception):
                pools.build(tmp)

    def test_absent_piece_is_unknown_not_refused(self):
        # The map only names what the export knows; absence is not a pool.
        out = pools.build(ROOT / "exports/studio-db-pre-series-order-p006-p010-2026-11-15")
        self.assertNotIn("p006", out["pools"])
        self.assertNotIn("p126", out["pools"])


if __name__ == "__main__":
    unittest.main()
