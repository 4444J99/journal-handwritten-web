"""tools/poem_record.py: the per-poem record (journal-handwritten-web #31).

The live-source tests run against the real checkout (read-only) and the
merged in-repo DB exports; the synthetic tests build a minimal repository in
a temporary folder so a tampered record or a missing source fails loudly.
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import poem_record  # noqa: E402

REAL_RECORDS = ROOT / "studio" / "data" / "poem-records.json"


def sha256_file(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mini_repo(tmp):
    """A two-piece repository in the fixture shape (pages pg1/pg2, pieces
    p001/p002, one line each), with notes-versions provenance matching the
    files written."""
    root = Path(tmp)
    (root / "site" / "data").mkdir(parents=True)
    (root / "studio" / "data").mkdir(parents=True)
    (root / "release").mkdir(parents=True)
    pages = [
        {"id": "pg1", "iw": 100, "ih": 100, "W": 100, "H": 100, "c": [0, 0, 1, 1],
         "a": [0, 0, 0, 16, 16], "B": [{"t": 0, "L": ["machine-pg1"], "g": [0, 0, 0], "v": 0}],
         "x": [[0, 0, 0, 0, 1, 1]], "u": ["private-note"], "sp": {"k": "pg1", "cb": [0, 0, 1, 1]}},
        {"id": "pg2", "iw": 100, "ih": 100, "W": 100, "H": 100, "c": [0, 0, 1, 1],
         "a": [0, 16, 0, 16, 16], "B": [{"t": 0, "L": ["machine-pg2"], "g": [1, 0, 0], "v": 0}],
         "x": [[0, 0, 0, 0, 1, 1]], "u": [], "sp": {"k": "pg2", "cb": [0, 0, 1, 1]}},
    ]
    pieces = [{"id": "p001", "V": [{"id": "v0", "P": [["pg1", [0]]]}], "st": [0], "top": 0},
              {"id": "p002", "V": [{"id": "v1", "P": [["pg2", [0]]]}], "st": [0], "top": 0}]
    j = {"v": 2, "pages": pages, "pieces": pieces, "groups": [["pg1", "pg2"]],
         "atlas": [[48, 16]], "prov": {"repo": "private", "commit": "private",
         "path": "private", "tdate": "2026-01-01", "verified": False}}
    review = {"version": 1,
              "pages": [{"id": "pg1", "blocks": [{"t": "text", "lines": [{"id": "pg1-0-0", "tx": "machine-pg1"}]}]},
                        {"id": "pg2", "blocks": [{"t": "text", "lines": [{"id": "pg2-0-0", "tx": "machine-pg2"}]}]}],
              "items": [{"id": "p001", "first": "machine-pg1", "versions": [{"page": "pg1", "blocks": [0]}]},
                        {"id": "p002", "first": "machine-pg2", "versions": [{"page": "pg2", "blocks": [0]}]}]}
    (root / "site" / "data" / "j.json").write_text(json.dumps(j), encoding="utf-8")
    (root / "studio" / "data" / "review.json").write_text(json.dumps(review), encoding="utf-8")
    nv = {"format": "versforms-notes-versions", "version": 1,
          "provenance": {"kind": "derived-id-map", "sources": [
              {"path": "site/data/j.json", "sha256": sha256_file(root / "site" / "data" / "j.json")},
              {"path": "studio/data/review.json", "sha256": sha256_file(root / "studio" / "data" / "review.json")}]},
          "pieces": [{"id": "p001", "V": [{"id": "v0", "P": [["pg1", [0]]]}]},
                     {"id": "p002", "V": [{"id": "v1", "P": [["pg2", [0]]]}]}]}
    (root / "studio" / "data" / "notes-versions.json").write_text(json.dumps(nv), encoding="utf-8")
    (root / "release" / "schedule.json").write_text("{}", encoding="utf-8")
    return root


def mini_db(tmp, pool_p002="Reserve", reviews=True):
    db = Path(tmp) / "db"
    (db / "release").mkdir(parents=True)
    (db / "reviews").mkdir(parents=True)
    (db / "decisions").mkdir(parents=True)
    (db / "release" / "p001.json").write_text(json.dumps({"pool": "series", "num": 1}), encoding="utf-8")
    (db / "release" / "p002.json").write_text(json.dumps({"pool": pool_p002}), encoding="utf-8")
    if reviews:
        (db / "reviews" / "pg1-0-0.json").write_text(
            json.dumps({"status": "confirmed", "original": "machine-pg1"}), encoding="utf-8")
    (db / "decisions" / "gruw-policy.json").write_text(json.dumps({"choice": "skip"}), encoding="utf-8")
    return db


class PoemRecordLiveTest(unittest.TestCase):
    def setUp(self):
        self.db_dir, self.used = poem_record.merge_export_fragments(ROOT)
        self.db = poem_record.load_db(self.db_dir)
        self.schedule = poem_record.load_schedule(ROOT)

    def test_p001_matches_the_gate(self):
        """p001 is READY in the gate; its record must agree (verified, series, filed)."""
        r = poem_record.build_record(ROOT, self.db, self.schedule, "p001")
        poem_record.validate_record(r)
        self.assertEqual(r["pool"], "series")
        self.assertTrue(r["verified"])
        self.assertTrue(r["gruw_filed"])
        self.assertEqual(r["batch_status"], "skip")
        self.assertEqual(r["lines"], 38)  # the gate counts 38 reviewed lines
        self.assertEqual(r["lines_source"], "review")
        self.assertEqual(r["release_number"], 1)
        self.assertEqual(r["alt_text"], {"diary1": "Page 1", "diary62a": "Page 62a"})
        self.assertEqual(r["notes"]["author"], [])

    def test_p002_is_unverified_but_filed(self):
        r = poem_record.build_record(ROOT, self.db, self.schedule, "p002")
        self.assertEqual(r["pool"], "series")
        self.assertFalse(r["verified"])
        self.assertTrue(r["gruw_filed"])

    def test_generated_file_matches_live_source(self):
        self.assertEqual(poem_record.validate_file(REAL_RECORDS, ROOT, self.db, self.schedule), 126)

    def test_schema_required_matches_validator(self):
        schema = json.loads((ROOT / "schemas" / "poem-record.schema.json").read_text())
        self.assertEqual(sorted(schema["required"]), sorted(poem_record.REQUIRED))

    def test_tampered_sha_fails_validation(self):
        data = json.loads(REAL_RECORDS.read_text())
        tampered = copy.deepcopy(data)
        tampered["pieces"][0]["transcript_sha"] = "sha256:" + "0" * 64
        tmp = Path(tempfile.mkdtemp()) / "records.json"
        tmp.write_text(json.dumps(tampered), encoding="utf-8")
        with self.assertRaises(ValueError):
            poem_record.validate_file(tmp, ROOT, self.db, self.schedule)


class PoemRecordSyntheticTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = mini_repo(self._tmp.name)
        self.db = poem_record.load_db(mini_db(self._tmp.name))
        self.schedule = {}

    def tearDown(self):
        self._tmp.cleanup()

    def test_pool_exact_value_rule(self):
        """'Reserve' is not 'reserve': only the studio's exact values count."""
        r = poem_record.build_record(self.root, self.db, self.schedule, "p002")
        self.assertEqual(r["pool"], "unknown")
        db2 = poem_record.load_db(mini_db(os.path.join(self._tmp.name, "b"), pool_p002="reserve"))
        r2 = poem_record.build_record(self.root, db2, self.schedule, "p002")
        self.assertEqual(r2["pool"], "reserve")

    def test_unsorted_without_release_doc(self):
        db_dir = mini_db(os.path.join(self._tmp.name, "c"))
        (db_dir / "release" / "p002.json").unlink()
        db = poem_record.load_db(db_dir)
        r = poem_record.build_record(self.root, db, self.schedule, "p002")
        self.assertEqual(r["pool"], "unsorted")

    def test_unverified_without_reviews(self):
        db = poem_record.load_db(mini_db(os.path.join(self._tmp.name, "d"), reviews=False))
        r = poem_record.build_record(self.root, db, self.schedule, "p001")
        self.assertFalse(r["verified"])

    def test_missing_source_fails_loudly(self):
        (self.root / "studio" / "data" / "notes-versions.json").unlink()
        with self.assertRaises(ValueError):
            poem_record.build_record(self.root, self.db, self.schedule, "p001")

    def test_unknown_piece_fails_loudly(self):
        with self.assertRaises(ValueError):
            poem_record.build_record(self.root, self.db, self.schedule, "p999")

    def test_notes_versions_mismatch_fails_loudly(self):
        nv = json.loads((self.root / "studio" / "data" / "notes-versions.json").read_text())
        nv["pieces"][0]["V"][0]["id"] = "other-version"
        (self.root / "studio" / "data" / "notes-versions.json").write_text(json.dumps(nv), encoding="utf-8")
        with self.assertRaises(ValueError):
            poem_record.build_record(self.root, self.db, self.schedule, "p001")


if __name__ == "__main__":
    unittest.main()
