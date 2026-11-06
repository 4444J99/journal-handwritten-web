"""Immutable note/contribution restore and legacy compatibility; synthetic data only."""
import copy
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import import_export as ie
import export_db as ex
import sqlguard


def revision(collection, revision_id="fixture-revision-1"):
    return {"schemaVersion": 1, "family": "note" if collection == "notes" else "contribution",
            "recordId": "fixture-record", "revisionId": revision_id, "parents": [],
            "author": {"id": "fixture-author", "name": "Technical fixture"},
            "poemDate": "2020-01-01", "noteDate": "2026-11-05",
            "source": {"pieceId": "fixture-piece", "versionId": "fixture-version", "lineId": "fixture-line"},
            "text": "Technical persistence fixture — café", "visibility": "private",
            "nested": {"b": [1, True, None], "a": "test", 'key.with.\"quote': "nul\u0000value"}}


def documents():
    return {c: {} for c in ie.COLLECTIONS}


class ImmutableRestoreTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)

    def test_all_eight_collections_export_restore_and_revision_history(self):
        docs = documents()
        for c in ie.COLLECTIONS:
            if c in ie.IMMUTABLE_COLLECTIONS:
                first = revision(c)
                second = {**copy.deepcopy(first), "revisionId": "fixture-revision-2",
                          "parents": [first["revisionId"]], "noteDate": "2026-11-06", "text": "Revised technical fixture"}
                docs[c] = {d["revisionId"]: d for d in [first, second]}
            else:
                docs[c]["existing-without-notes"] = {"original": "Technical legacy fixture", "at": "2020-01-01"}
        self.db.executescript(ie.build_sql(docs, "first-import"))
        rows = [{"collection": c, "id": i, "data": d} for c, i, d in self.db.execute(ex.QUERY)]
        exported, rejects = ex.collect(rows)
        self.assertEqual(rejects, [])
        self.assertEqual(exported, docs)
        with tempfile.TemporaryDirectory(prefix="t05-revisions-") as root:
            ex.write_export(exported, root, "2026-11-05")
            restored, rejects = ie.scan(root)
        self.assertEqual(rejects, [])
        self.assertEqual(restored, docs)
        other = sqlite3.connect(":memory:")
        self.addCleanup(other.close)
        other.executescript(ie.build_sql(restored, "restore"))
        self.assertEqual(list(other.execute(ex.QUERY)), list(self.db.execute(ex.QUERY)))
        # Retrying the restore retains every immutable row byte-for-byte, including
        # database timestamps/revs, while legacy collection semantics remain intact.
        before = list(self.db.execute("SELECT * FROM vf_docs WHERE collection IN ('notes','contributions') ORDER BY collection,id"))
        self.db.executescript(ie.build_sql(restored, "retry"))
        after = list(self.db.execute("SELECT * FROM vf_docs WHERE collection IN ('notes','contributions') ORDER BY collection,id"))
        self.assertEqual(after, before)
        self.assertEqual(dict(self.db.execute("SELECT collection,rev FROM vf_revs")),
                         {c: 1 if c in ie.IMMUTABLE_COLLECTIONS else 2 for c in ie.COLLECTIONS})

    def test_api_style_json_and_reordered_pretty_export_are_identical_retries(self):
        self.db.executescript((ie.HERE / "schema.sql").read_text())
        doc = revision("notes")
        api_text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
        self.db.execute("INSERT INTO vf_revs VALUES ('notes', 1)")
        self.db.execute("INSERT INTO vf_docs VALUES ('notes', ?, ?, 'original-time', 1)", (doc["revisionId"], api_text))
        docs = documents()
        docs["notes"][doc["revisionId"]] = dict(reversed(list(doc.items())))
        docs["notes"][doc["revisionId"]]["nested"] = dict(reversed(list(doc["nested"].items())))
        self.db.executescript(ie.build_sql(docs, "retry-time"))
        row = self.db.execute("SELECT data,updated_at,rev FROM vf_docs").fetchone()
        self.assertEqual(row, (api_text, "original-time", 1))

    def test_changed_same_id_is_rejected_without_mutating_stored_history(self):
        for collection in ie.IMMUTABLE_COLLECTIONS:
            docs = documents()
            doc = revision(collection)
            docs[collection][doc["revisionId"]] = doc
            self.db.executescript(ie.build_sql(docs, "original"))
            original = self.db.execute("SELECT * FROM vf_docs WHERE collection=?", (collection,)).fetchall()
            for change in ["body", "nested-type", "array-order", "missing-key", "extra-key"]:
                bad = copy.deepcopy(doc)
                if change == "body": bad["text"] = "Changed technical fixture"
                if change == "nested-type": bad["nested"]["b"][1] = 1
                if change == "array-order": bad["nested"]["b"].reverse()
                if change == "missing-key": del bad["nested"]["a"]
                if change == "extra-key": bad["nested"]["new"] = None
                docs[collection][doc["revisionId"]] = bad
                with self.subTest(collection=collection, change=change), self.assertRaises(sqlite3.IntegrityError):
                    self.db.executescript(ie.build_sql(docs, "collision"))
                self.assertEqual(self.db.execute("SELECT * FROM vf_docs WHERE collection=?", (collection,)).fetchall(), original)

    def test_bad_revision_envelopes_are_rejected_before_sql(self):
        with tempfile.TemporaryDirectory(prefix="t05-revision-reject-") as root:
            folder = Path(root) / "notes"
            folder.mkdir()
            (folder / "bad.json").write_text(json.dumps(revision("contributions")), encoding="utf8")
            docs, rejects = ie.scan(root)
            self.assertEqual(docs["notes"], {})
            self.assertEqual(len(rejects), 1)
            self.assertIn("revision envelope", rejects[0].reason)


class JsonTreeGuardTests(unittest.TestCase):
    def test_only_read_only_json_tree_calls_are_added(self):
        sqlguard.check("SELECT atom FROM json_tree('{\"x\":1}')")
        sqlguard.check("SELECT atom FROM json_tree(vf_docs.data) JOIN vf_docs ON 1")
        for sql in [
            "SELECT * FROM json_tree('{}'), submissions",
            "SELECT * FROM json_tree('{}') AS j, submissions",
            "SELECT * FROM json_tree('{}') JOIN submissions ON 1",
            "SELECT * FROM json_tree((SELECT data FROM submissions))",
            "SELECT * FROM json_tree",
            "SELECT * FROM main.json_tree('{}')",
            "SELECT * FROM json_each('{}')",
            "INSERT INTO json_tree VALUES ('{}')",
            "SELECT * FROM json_tree('{}'), sqlite_master",
        ]:
            with self.subTest(sql=sql), self.assertRaises(sqlguard.SqlGuardError):
                sqlguard.check(sql)


if __name__ == "__main__":
    unittest.main()
