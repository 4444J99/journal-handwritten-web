"""Cut-up versions-collection round-trip (journal-handwritten-web #55).

A cut-up version saved from the Cut tab (method + src provenance, plus
the source version it was cut from) survives export and restore intact,
following tests/test_revision_persistence.py. Synthetic data only.
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import import_export as ie
import export_db as ex


def documents():
    return {c: {} for c in ie.COLLECTIONS}


def cut_up_doc():
    return {"pieceId": "p001", "method": "erasure",
            "lines": ["pg2-0-0", "pg2-0-1"],
            "src": [{"piece": "p002", "line": "pg3-0-0"}, None],
            "at": "2026-11-25T00:00:00Z", "status": "new",
            "sourceVersion": "p001-0"}


class CutUpRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)

    def test_cut_up_version_round_trips_with_method_and_src(self):
        docs = documents()
        docs["versions"]["cut-abc"] = cut_up_doc()
        self.db.executescript(ie.build_sql(docs, "first-import"))
        rows = [{"collection": c, "id": i, "data": d} for c, i, d in self.db.execute(ex.QUERY)]
        exported, rejects = ex.collect(rows)
        self.assertEqual(rejects, [])
        self.assertEqual(exported, docs)
        with tempfile.TemporaryDirectory(prefix="t05-cut-up-") as root:
            ex.write_export(exported, root, "2026-11-25")
            restored, rejects = ie.scan(root)
        self.assertEqual(rejects, [])
        self.assertEqual(restored, docs)
        other = sqlite3.connect(":memory:")
        self.addCleanup(other.close)
        other.executescript(ie.build_sql(restored, "restore"))
        self.assertEqual(list(other.execute(ex.QUERY)), list(self.db.execute(ex.QUERY)))
