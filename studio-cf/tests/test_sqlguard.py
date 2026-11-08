"""Tests for sqlguard.py and the vf_-only rule. Synthetic data only. Run:
    python3 -m unittest discover -s studio-cf/tests -p 'test_*.py'
"""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import sqlguard  # noqa: E402
import import_export as ie  # noqa: E402


class AcceptTests(unittest.TestCase):
    def test_schema_file_passes(self):
        sqlguard.check((ROOT / "schema.sql").read_text())

    def test_studio_statements_pass(self):
        for sql in (
            "INSERT INTO vf_revs (collection, rev) VALUES (?1, 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1",
            "SELECT rev FROM vf_revs WHERE collection = ?1",
            "SELECT id, data FROM vf_docs WHERE collection = ?1 ORDER BY id",
            "DELETE FROM vf_docs WHERE collection = ?1 AND id = ?2",
            "INSERT OR REPLACE INTO vf_docs (collection, id, data, updated_at, rev) VALUES (?1, ?2, ?3, ?4, (SELECT rev FROM vf_revs WHERE collection = ?1))",
            "CREATE INDEX IF NOT EXISTS vf_docs_updated ON vf_docs (updated_at)",
            "SELECT d.id FROM vf_docs d JOIN vf_revs r ON r.collection = d.collection",
        ):
            self.assertEqual(sqlguard.violations(sql), [], sql)

    def test_json_data_with_dangerous_words_is_ignored(self):
        text = "x'); DROP TABLE submissions; -- FROM submissions"
        sql = "INSERT OR REPLACE INTO vf_docs (collection, id, data, updated_at, rev) VALUES ('reviews','a','" + text.replace("'", "''") + "','t',1);"
        self.assertEqual(sqlguard.violations(sql), [])

    def test_generated_import_sql_passes(self):
        docs = {c: {} for c in ie.COLLECTIONS}
        docs["reviews"]["a"] = {"text": "it's a \"test\"; DROP TABLE submissions; --\nline", "n": [1, 2]}
        docs["batches"]["b"] = {"x": "FROM submissions"}
        sqlguard.check(ie.build_sql(docs, "2026-01-01T00:00:00Z"))


class RejectTests(unittest.TestCase):
    def refused(self, sql):
        self.assertTrue(sqlguard.violations(sql), "should be refused: " + sql)
        with self.assertRaises(sqlguard.SqlGuardError):
            sqlguard.check(sql)

    def test_other_projects_table(self):
        for sql in (
            "SELECT * FROM submissions",
            "INSERT INTO submissions (a) VALUES (1)",
            "INSERT OR REPLACE INTO submissions (a) VALUES (1)",
            "DELETE FROM submissions",
            "DELETE FROM submissions WHERE 1",
            "CREATE TABLE IF NOT EXISTS submissions (a TEXT)",
            "CREATE TABLE submissions (a TEXT)",
            "CREATE TABLE IF NOT EXISTS docs (a TEXT)",
            "SELECT * FROM vf_docs, submissions",
            "SELECT * FROM vf_docs JOIN submissions ON 1",
            "SELECT * FROM vf_docs WHERE id IN (SELECT id FROM submissions)",
            "INSERT INTO vf_docs SELECT * FROM submissions",
            "CREATE INDEX IF NOT EXISTS vf_x ON submissions (a)",
            "CREATE INDEX IF NOT EXISTS other_x ON vf_docs (a)",
        ):
            self.refused(sql)

    def test_internal_and_qualified_and_quoted_names(self):
        for sql in (
            "SELECT * FROM _cf_KV",
            "SELECT * FROM sqlite_master",
            "SELECT * FROM main.vf_docs",
            "SELECT * FROM main.submissions",
            'SELECT * FROM "submissions"',
            'SELECT * FROM "vf_docs"',
            "SELECT * FROM `submissions`",
            "SELECT * FROM [submissions]",
            "INSERT INTO main.vf_docs (a) VALUES (1)",
            "SELECT * FROM vf_",
        ):
            self.refused(sql)

    def test_dangerous_statement_kinds(self):
        for sql in (
            "DROP TABLE vf_docs",
            "DROP TABLE submissions",
            "ALTER TABLE vf_docs ADD COLUMN x TEXT",
            "UPDATE vf_docs SET data = '{}'",
            "UPDATE submissions SET a = 1",
            "ATTACH DATABASE 'x' AS y",
            "PRAGMA writable_schema = 1",
            "VACUUM",
            "CREATE TRIGGER IF NOT EXISTS vf_t AFTER INSERT ON vf_docs BEGIN SELECT 1; END",
            "CREATE VIEW vf_v AS SELECT 1",
            "REINDEX",
            "CREATE TEMP TABLE IF NOT EXISTS vf_t (a TEXT)",
        ):
            self.refused(sql)

    def test_a_bad_statement_hidden_among_good_ones(self):
        good = "INSERT INTO vf_revs (collection, rev) VALUES ('reviews', 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1;\n"
        self.refused(good + "DELETE FROM submissions;\n" + good)
        self.refused(good + "/* comment */ DROP TABLE submissions;")

    def test_unterminated_input_is_refused(self):
        self.refused("SELECT 'abc FROM vf_docs")
        self.refused("SELECT * FROM vf_docs /* open")

    def test_message_does_not_echo_string_literals(self):
        secret = "synthetic-secret-literal"
        with self.assertRaises(sqlguard.SqlGuardError) as cm:
            sqlguard.check(f"INSERT INTO submissions (a) VALUES ('{secret}')")
        self.assertNotIn(secret, str(cm.exception))


class ImportRefusesTests(unittest.TestCase):
    def test_build_sql_refuses_if_the_schema_ever_names_another_object(self):
        original = ie.HERE
        import tempfile
        import os
        scratch = Path(os.environ.get("STUDIO_CF_SCRATCH", "/Volumes/Archive4T/Temporary/versforms-work/studio-cf"))
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch, prefix="guard-test-") as d:
            (Path(d) / "schema.sql").write_text("DROP TABLE submissions;\n")
            ie.HERE = Path(d)
            try:
                with self.assertRaises(sqlguard.SqlGuardError):
                    ie.build_sql({c: {} for c in ie.COLLECTIONS}, "t")
            finally:
                ie.HERE = original

    def test_main_returns_1_and_writes_nothing_when_the_guard_trips(self):
        import contextlib
        import io
        import os
        import tempfile
        from unittest import mock
        scratch = Path(os.environ.get("STUDIO_CF_SCRATCH", "/Volumes/Archive4T/Temporary/versforms-work/studio-cf"))
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch, prefix="guard-test-") as d:
            exp = Path(d) / "exp"
            (exp / "reviews").mkdir(parents=True)
            (exp / "reviews" / "a.json").write_text('{"x": 1}')
            out_sql = Path(d) / "out.sql"
            err = io.StringIO()
            with mock.patch.object(ie, "build_sql", side_effect=sqlguard.SqlGuardError("SQL refused")):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                    code = ie.main([str(exp), "--sql-out", str(out_sql), "--remote"])
            self.assertEqual(code, 1)
            self.assertFalse(out_sql.exists())
            self.assertIn("SQL refused", err.getvalue())


class SourceScanTests(unittest.TestCase):
    """Every SQL statement written in the studio's own source touches only vf_ objects."""

    SQL_START = re.compile(r"^\s*(SELECT|INSERT|DELETE|CREATE|UPDATE|DROP|ALTER|PRAGMA)\b", re.I)

    def js_sql_literals(self, path):
        text = path.read_text()
        for m in re.finditer(r"'((?:[^'\\\n]|\\.)*)'|`((?:[^`\\]|\\.)*)`", text):
            s = m.group(1) if m.group(1) is not None else m.group(2)
            if self.SQL_START.match(s) and re.search(r"\b(FROM|INTO|TABLE|INDEX)\b", s, re.I):
                yield s

    def test_api_js_sql_is_vf_only(self):
        found = list(self.js_sql_literals(ROOT / "lib" / "api.js"))
        self.assertGreaterEqual(len(found), 6, "the scan should find the API's statements")
        for s in found:
            self.assertEqual(sqlguard.violations(s), [], s)

    def test_no_js_source_touches_a_non_vf_object(self):
        for p in list((ROOT / "functions").rglob("*.js")) + list((ROOT / "lib").glob("*.js")):
            for s in self.js_sql_literals(p):
                self.assertEqual(sqlguard.violations(s), [], f"{p.name}: {s}")

    def test_schema_uses_if_not_exists_and_only_vf_names(self):
        text = (ROOT / "schema.sql").read_text()
        creates = re.findall(r"CREATE\s+(?:UNIQUE\s+)?(TABLE|INDEX)\s+(IF NOT EXISTS\s+)?(\w+)", text, re.I)
        self.assertGreaterEqual(len(creates), 2)
        for kind, ine, name in creates:
            self.assertTrue(ine, f"{kind} {name} lacks IF NOT EXISTS")
            self.assertTrue(name.startswith("vf_"), name)

    def test_wrangler_toml_names_the_shared_database(self):
        toml = (ROOT / "wrangler.toml").read_text()
        self.assertIn('database_name = "studio-documents-prod"', toml)
        self.assertIn('database_id = "68b1a11f-00a8-4bc7-923b-0931292980c7"', toml)
        self.assertIn('bucket_name = "versforms-studio-assets"', toml)


if __name__ == "__main__":
    unittest.main()
