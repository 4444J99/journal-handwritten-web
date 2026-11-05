"""Tests for import_export.py. Synthetic documents only. Run:
    python3 -m unittest discover -s studio-cf/tests -p 'test_*.py'
Temporary files go under STUDIO_CF_SCRATCH (default: the lane's scratch directory on the external drive).
"""
import contextlib
import io
import json
import os
import sqlite3
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import import_export as ie  # noqa: E402

SCRATCH = Path(os.environ.get("STUDIO_CF_SCRATCH", "/Volumes/Archive4T/Temporary/versforms-work/studio-cf"))
SCHEMA = (HERE.parent / "schema.sql").read_text()


def tmpdir():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=SCRATCH, prefix="ie-test-")


def write(root, rel, content):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return p


def make_export(root, reviews=38, extra=None):
    """Same shape as the real export: reviews/ID.json, no folders for empty collections."""
    for i in range(reviews):
        write(root, f"reviews/synthetic-{i // 4}-{i % 4}.json", {"at": "2026-01-01T00:00:00Z", "original": f"synthetic line {i}", "status": "ok"})
    write(root, "README.md", "# synthetic export\n")
    for rel, content in (extra or {}).items():
        write(root, rel, content)


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = ie.main(argv)
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


class ScanTests(unittest.TestCase):
    def test_counts_match_the_real_export_shape(self):
        with tmpdir() as d:
            make_export(d)
            docs, rejects = ie.scan(d)
            self.assertEqual({c: len(v) for c, v in docs.items()},
                             {"reviews": 38, "decisions": 0, "versions": 0, "release": 0, "batches": 0, "rconfig": 0})
            self.assertEqual(rejects, [])

    def test_dry_run_prints_every_collection_and_writes_nothing(self):
        with tmpdir() as d:
            make_export(d)
            before = sorted(p.name for p in Path(d).rglob("*"))
            code, out, _ = run_main([d, "--dry-run"])
            self.assertEqual(code, 0)
            for line in ("reviews    38", "decisions  0", "versions   0", "release    0", "batches    0", "rconfig    0", "total      38", "rejects    0"):
                self.assertIn(line, out)
            self.assertEqual(before, sorted(p.name for p in Path(d).rglob("*")))

    def test_rejects(self):
        with tmpdir() as d:
            make_export(d, reviews=1, extra={
                "secrets/a.json": {"x": 1},                       # unknown collection
                "decisions/bad id.json": {"x": 1},                # space in id
                "decisions/semi;colon.json": {"x": 1},
                "decisions/" + "a" * 129 + ".json": {"x": 1},     # too long
                "decisions/..json": {"x": 1},                     # id is "." -> reserved
                "decisions/list.json": [1, 2, 3],                 # not an object
                "decisions/null.json": "null",
                "decisions/broken.json": "{not json",
                "decisions/big.json": {"s": "x" * 70000},         # over 64 KiB
                "decisions/notes.txt": "hello",                   # not .json
                "versions/ok_one.json": {"fine": True},
                "stray.json": {"x": 1},                           # file at top level
            })
            (Path(d) / "decisions" / "unié.json").write_text("{}", encoding="utf-8")
            docs, rejects = ie.scan(d)
            reasons = {r.path: r.reason for r in rejects}
            self.assertIn("secrets/", reasons)
            self.assertEqual(reasons["decisions/bad id.json"], "invalid document id")
            self.assertEqual(reasons["decisions/semi;colon.json"], "invalid document id")
            self.assertEqual(reasons["decisions/" + "a" * 129 + ".json"], "invalid document id")
            self.assertEqual(reasons["decisions/unié.json"], "invalid document id")
            self.assertEqual(reasons["decisions/list.json"], "top level is not a JSON object")
            self.assertEqual(reasons["decisions/null.json"], "top level is not a JSON object")
            self.assertTrue(reasons["decisions/broken.json"].startswith("not valid UTF-8 JSON"))
            self.assertTrue(reasons["decisions/big.json"].startswith("larger than 65536"))
            self.assertEqual(reasons["decisions/notes.txt"], "not a .json file")
            self.assertEqual(reasons["stray.json"], "not a collection directory")
            self.assertEqual(len(docs["decisions"]), 0)
            self.assertEqual(sorted(docs["versions"]), ["ok_one"])
            self.assertEqual(len(docs["reviews"]), 1)

    def test_size_limit_is_in_bytes_and_inclusive(self):
        with tmpdir() as d:
            overhead = len(json.dumps({"s": ""}).encode())
            write(d, "rconfig/exact.json", json.dumps({"s": "x" * (65536 - overhead)}))
            write(d, "rconfig/over.json", json.dumps({"s": "x" * (65536 - overhead + 1)}))
            docs, rejects = ie.scan(d)
            self.assertIn("exact", docs["rconfig"])
            self.assertEqual([r.path for r in rejects], ["rconfig/over.json"])

    def test_rejects_block_writing_unless_skipped(self):
        with tmpdir() as d:
            make_export(d, reviews=2, extra={"decisions/bad id.json": {"x": 1}})
            sql = Path(d).parent / "blocked.sql"
            code, _, err = run_main([d, "--sql-out", str(sql)])
            self.assertEqual(code, 1)
            self.assertFalse(sql.exists())
            self.assertIn("refusing", err)
            code, out, _ = run_main([d, "--sql-out", str(sql), "--skip-rejects"])
            self.assertEqual(code, 0)
            self.assertTrue(sql.exists())
            sql.unlink()

    def test_no_action_is_an_error(self):
        with tmpdir() as d:
            code, _, _ = run_main([d])
            self.assertNotEqual(code, 0)


class EscapingTests(unittest.TestCase):
    def test_sql_string(self):
        self.assertEqual(ie.sql_string("it's"), "'it''s'")
        self.assertEqual(ie.sql_string("'; DROP TABLE docs;--"), "'''; DROP TABLE docs;--'")
        with self.assertRaises(ValueError):
            ie.sql_string("a\x00b")

    NASTY = {
        "quote": "it's a \"test\"",
        "inject": "'); DROP TABLE docs; --",
        "backslash": "back\\slash \\n not a newline",
        "newline": "line one\nline two\r\nline three\ttab",
        "unicode": "café — 中文 \U0001f600",
        "nul": "before\u0000after",
        "ctrl": "\u0001\u001f\u007f",
        "semicolon": "a;b;c",
        "percent": "100% _ wild",
        "nested": {"list": [1, 2.5, None, True, "x'y"], "empty": {}},
    }

    def load(self, conn, sql):
        conn.executescript(sql)

    def test_round_trip_through_sqlite(self):
        docs = {c: {} for c in ie.COLLECTIONS}
        docs["reviews"]["nasty"] = self.NASTY
        docs["decisions"]["a.b-c_d"] = {"k": "v"}
        sql = ie.build_sql(docs, "2026-11-05T00:00:00Z")
        sql.encode("ascii")  # pure ASCII
        for line in sql.splitlines():
            self.assertNotIn("\r", line)
        conn = sqlite3.connect(":memory:")
        self.load(conn, sql)
        row = conn.execute("SELECT data FROM docs WHERE collection='reviews' AND id='nasty'").fetchone()
        self.assertEqual(json.loads(row[0]), self.NASTY)
        self.assertEqual(conn.execute("SELECT count(*) FROM docs").fetchone()[0], 2)
        self.assertEqual(dict(conn.execute("SELECT collection, rev FROM revs").fetchall()), {"reviews": 1, "decisions": 1})

    def test_idempotent_and_bumps_each_collection_once_per_run(self):
        docs = {c: {} for c in ie.COLLECTIONS}
        for i in range(5):
            docs["reviews"][f"r{i}"] = {"i": i}
        docs["batches"]["b"] = {"x": 1}
        sql = ie.build_sql(docs, "2026-11-05T00:00:00Z")
        conn = sqlite3.connect(":memory:")
        self.load(conn, sql)
        self.assertEqual(dict(conn.execute("SELECT collection, rev FROM revs").fetchall()), {"reviews": 1, "batches": 1})
        self.assertEqual(conn.execute("SELECT count(*) FROM docs").fetchone()[0], 6)
        self.load(conn, sql)  # second run: same rows, rev bumped once more
        self.assertEqual(conn.execute("SELECT count(*) FROM docs").fetchone()[0], 6)
        self.assertEqual(dict(conn.execute("SELECT collection, rev FROM revs").fetchall()), {"reviews": 2, "batches": 2})
        self.assertEqual(set(r[0] for r in conn.execute("SELECT rev FROM docs WHERE collection='reviews'")), {2})

    def test_existing_docs_are_replaced_not_merged(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(SCHEMA)
        conn.execute("INSERT INTO docs VALUES ('reviews','d1','{\"old\":1,\"keep\":2}','t',1)")
        conn.execute("INSERT INTO revs VALUES ('reviews',7)")
        docs = {c: {} for c in ie.COLLECTIONS}; docs["reviews"]["d1"] = {"new": 1}
        conn.executescript(ie.build_sql(docs, "t2", include_schema=False))
        self.assertEqual(json.loads(conn.execute("SELECT data FROM docs WHERE id='d1'").fetchone()[0]), {"new": 1})
        self.assertEqual(conn.execute("SELECT rev FROM revs WHERE collection='reviews'").fetchone()[0], 8)

    def test_empty_import_changes_nothing(self):
        docs = {c: {} for c in ie.COLLECTIONS}
        conn = sqlite3.connect(":memory:")
        conn.executescript(ie.build_sql(docs, "t"))
        self.assertEqual(conn.execute("SELECT count(*) FROM revs").fetchone()[0], 0)

    def test_full_cli_to_sql_for_the_expected_export(self):
        with tmpdir() as d:
            make_export(d)
            out_sql = Path(d).parent / "cli-import.sql"
            code, out, _ = run_main([d, "--sql-out", str(out_sql), "--now", "2026-11-05T00:00:00Z"])
            self.assertEqual(code, 0)
            conn = sqlite3.connect(":memory:")
            conn.executescript(out_sql.read_text())
            self.assertEqual(conn.execute("SELECT count(*) FROM docs WHERE collection='reviews'").fetchone()[0], 38)
            self.assertEqual(conn.execute("SELECT count(*) FROM docs WHERE collection<>'reviews'").fetchone()[0], 0)
            self.assertEqual(dict(conn.execute("SELECT collection, rev FROM revs").fetchall()), {"reviews": 1})
            out_sql.unlink()


class RemoteAndLocalTests(unittest.TestCase):
    def test_remote_only_prints_the_command(self):
        with tmpdir() as d:
            make_export(d, reviews=3)
            sql = Path(d).parent / "remote.sql"
            with mock.patch.object(ie.subprocess, "Popen", side_effect=AssertionError("must not execute")), \
                 mock.patch.object(ie.subprocess, "run", side_effect=AssertionError("must not execute")):
                code, out, _ = run_main([d, "--sql-out", str(sql), "--remote"])
            self.assertEqual(code, 0)
            self.assertIn("NOT executed", out)
            self.assertIn("wrangler d1 execute versforms-studio --remote", out)
            self.assertIn(str(sql.resolve()), out)
            sql.unlink()

    def test_remote_requires_sql_out(self):
        with tmpdir() as d:
            make_export(d, reviews=1)
            code, _, _ = run_main([d, "--remote"])
            self.assertNotEqual(code, 0)

    def test_local_calls_wrangler_with_local_flags_and_stops_it_after_success(self):
        with tmpdir() as d:
            make_export(d, reviews=3)
            fake = Path(d).parent / "fake-wrangler.py"
            argv_log = Path(d).parent / "fake-wrangler.argv"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import sys, time, json\n"
                f"open({str(argv_log)!r}, 'w').write(json.dumps(sys.argv[1:]))\n"
                "print('Resource location: local')\n"
                "print('1 command executed successfully.')\n"
                "print('[')\nprint('  {}')\nprint(']', flush=True)\n"
                "time.sleep(300)\n"  # like wrangler 4.104: result printed, process lingers
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            persist = Path(d).parent / "persist-for-test"
            code, out, err = run_main([d, "--local", str(persist), "--wrangler", str(fake), "--timeout", "20"])
            self.assertEqual(code, 0, err)
            argv = json.loads(argv_log.read_text())
            self.assertEqual(argv[:3], ["d1", "execute", "versforms-studio"])
            self.assertIn("--local", argv)
            self.assertNotIn("--remote", argv)
            self.assertEqual(argv[argv.index("--persist-to") + 1], str(persist.resolve()))
            self.assertIn("--file", argv)
            self.assertFalse(list(persist.parent.glob("studio-import-*.sql")), "temporary SQL file is removed")
            fake.unlink(); argv_log.unlink()
            try:
                persist.rmdir()
            except OSError:
                pass

    def test_local_failure_is_reported(self):
        with tmpdir() as d:
            make_export(d, reviews=1)
            fake = Path(d).parent / "failing-wrangler.py"
            fake.write_text("#!/usr/bin/env python3\nimport sys\nprint('ERROR boom')\nsys.exit(1)\n")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            persist = Path(d).parent / "persist-for-test-2"
            code, _, _ = run_main([d, "--local", str(persist), "--wrangler", str(fake), "--timeout", "20"])
            self.assertNotEqual(code, 0)
            fake.unlink()
            try:
                persist.rmdir()
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
