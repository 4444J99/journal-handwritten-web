"""Tests for export_db.py, including the byte-for-byte round trip with import_export.py.
Synthetic documents only (the optional real-export check reads files but copies nothing). Run:
    python3 -m unittest discover -s studio-cf/tests -p 'test_*.py'
"""
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import export_db as ed  # noqa: E402
import import_export as ie  # noqa: E402
import sqlguard  # noqa: E402

SCRATCH = Path(os.environ.get("STUDIO_CF_SCRATCH", "/Volumes/Archive4T/Temporary/versforms-work/studio-cf"))
REAL_EXPORT = Path(os.environ.get("STUDIO_CF_REAL_EXPORT", str(SCRATCH / "pr73" / "exports" / "studio-db-2026-11-05")))


def tmpdir():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=SCRATCH, prefix="ed-test-")


def pr73_bytes(data):
    """The PR 73 file format: 2-space indent, no ASCII escaping, one trailing newline."""
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def write_doc(root, coll, doc_id, data):
    p = Path(root) / coll / f"{doc_id}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(pr73_bytes(data))


SYNTH = {
    "reviews": {
        "synth-0-0": {"at": "2026-01-01T00:00:00Z", "original": "synthetic [[struck: x]] line", "status": "corrected", "text": "synthetic line"},
        "synth-0-1": {"at": "2026-01-01T00:00:01Z", "original": "it's \"quoted\"\nsecond line\ttab \\ backslash", "status": "ok"},
        "synth-1-0": {"at": "t", "original": "café — 中文 \U0001f600", "nested": {"a": [1, 2.5, None, True], "b": {}}, "empty": []},
    },
    "decisions": {"d.1": {"choice": "keep"}},
    "batches": {"b_1": {"ids": ["synth-0-0", "synth-0-1"]}},
}


def make_export(root, docs=SYNTH):
    for coll, items in docs.items():
        for doc_id, data in items.items():
            write_doc(root, coll, doc_id, data)
    (Path(root) / "README.md").write_text("# synthetic export\n", encoding="utf-8")


def tree(root):
    """{relative path: bytes} for the collection files only (the README differs by design)."""
    root = Path(root)
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*.json"))}


def sqlite_with(sql_text, path):
    conn = sqlite3.connect(path)
    conn.executescript(sql_text)
    conn.commit()
    return conn


def run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = ed.main(argv)
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


def wrangler_json_from(conn):
    rows = [{"collection": c, "id": i, "data": d} for c, i, d in conn.execute(ed.QUERY)]
    return json.dumps([{"results": rows, "success": True, "meta": {"served_by": "synthetic"}}])


class RoundTripTests(unittest.TestCase):
    def import_to_sqlite(self, export_dir, db_path):
        docs, rejects = ie.scan(export_dir)
        self.assertEqual(rejects, [])
        sql = ie.build_sql(docs, "2026-11-05T00:00:00Z")
        return sqlite_with(sql, db_path)

    def test_import_then_export_json_reproduces_every_file_byte_for_byte(self):
        with tmpdir() as d:
            src, out = Path(d) / "src", Path(d) / "out"
            make_export(src)
            conn = self.import_to_sqlite(src, str(Path(d) / "db.sqlite"))
            js = Path(d) / "rows.json"
            js.write_text(wrangler_json_from(conn), encoding="utf-8")
            code, stdout, err = run_main(["--from-json", str(js), "--out", str(out), "--date", "2026-11-05"])
            self.assertEqual(code, 0, err)
            self.assertEqual(tree(out), tree(src))
            self.assertEqual(len(tree(out)), 5)

    def test_import_then_export_local_persist_dir_reproduces_byte_for_byte(self):
        with tmpdir() as d:
            src, out = Path(d) / "src", Path(d) / "out"
            make_export(src)
            persist = Path(d) / "persist" / "v3" / "d1" / "miniflare-D1DatabaseObject"
            persist.mkdir(parents=True)
            # wrangler also keeps a metadata.sqlite (and, in a shared database, other tables); both must be tolerated
            sqlite3.connect(str(persist / "metadata.sqlite")).close()
            conn = self.import_to_sqlite(src, str(persist / "abc123.sqlite"))
            conn.execute("CREATE TABLE submissions (id TEXT, body TEXT)")
            conn.execute("INSERT INTO submissions VALUES ('s1', 'other project row')")
            conn.commit()
            conn.close()
            code, stdout, err = run_main(["--local", str(Path(d) / "persist"), "--out", str(out), "--date", "2026-11-05"])
            self.assertEqual(code, 0, err)
            self.assertEqual(tree(out), tree(src))
            self.assertNotIn("submissions", stdout)

    def test_empty_collections_get_no_folder_and_readme_has_counts(self):
        with tmpdir() as d:
            src, out = Path(d) / "src", Path(d) / "out"
            make_export(src)
            conn = self.import_to_sqlite(src, str(Path(d) / "db.sqlite"))
            js = Path(d) / "rows.json"
            js.write_text(wrangler_json_from(conn), encoding="utf-8")
            run_main(["--from-json", str(js), "--out", str(out), "--date", "2026-11-05"])
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["README.md", "batches", "decisions", "reviews"])
            readme = (out / "README.md").read_text(encoding="utf-8")
            for line in ("| reviews | 3 |", "| decisions | 1 |", "| versions | 0 |", "| release | 0 |", "| batches | 1 |", "| rconfig | 0 |"):
                self.assertIn(line, readme)
            self.assertIn("2026-11-05", readme)
            # the export (README included) is a valid input for the importer again
            docs, rejects = ie.scan(out)
            self.assertEqual(rejects, [])
            self.assertEqual({c: len(v) for c, v in docs.items()}, {"reviews": 3, "decisions": 1, "versions": 0, "release": 0, "batches": 1, "rconfig": 0, "notes": 0, "contributions": 0, "artifacts": 0})

    def test_second_cycle_is_stable(self):
        with tmpdir() as d:
            src, out1, out2 = Path(d) / "src", Path(d) / "o1", Path(d) / "o2"
            make_export(src)
            c1 = self.import_to_sqlite(src, str(Path(d) / "db1.sqlite"))
            (Path(d) / "r1.json").write_text(wrangler_json_from(c1), encoding="utf-8")
            run_main(["--from-json", str(Path(d) / "r1.json"), "--out", str(out1)])
            c2 = self.import_to_sqlite(out1, str(Path(d) / "db2.sqlite"))
            (Path(d) / "r2.json").write_text(wrangler_json_from(c2), encoding="utf-8")
            run_main(["--from-json", str(Path(d) / "r2.json"), "--out", str(out2)])
            self.assertEqual(tree(out1), tree(src))
            self.assertEqual(tree(out2), tree(src))

    @unittest.skipUnless((REAL_EXPORT / "reviews").is_dir(), "the PR 73 export is not available in scratch")
    def test_real_pr73_export_round_trips_byte_for_byte(self):
        with tmpdir() as d:
            out = Path(d) / "out"
            conn = self.import_to_sqlite(REAL_EXPORT, str(Path(d) / "db.sqlite"))
            js = Path(d) / "rows.json"
            js.write_text(wrangler_json_from(conn), encoding="utf-8")
            code, stdout, err = run_main(["--from-json", str(js), "--out", str(out), "--date", "2026-11-05"])
            self.assertEqual(code, 0, err)
            a, b = tree(REAL_EXPORT), tree(out)
            self.assertEqual(len(a), 38)
            self.assertEqual(sorted(a), sorted(b))
            self.assertEqual([k for k in a if a[k] != b[k]], [])


class WranglerJsonShapeTests(unittest.TestCase):
    ROW = {"collection": "reviews", "id": "a", "data": '{"x":1}'}

    def test_accepted_shapes(self):
        for text in (
            json.dumps([{"results": [self.ROW], "success": True}]),
            json.dumps({"results": [self.ROW], "success": True}),
            json.dumps([self.ROW]),
            json.dumps([{"results": [self.ROW]}, {"results": []}]),
        ):
            self.assertEqual(ed.rows_from_wrangler_json(text), [self.ROW])

    def test_refused_shapes(self):
        for text in ("not json", '"string"', "[1]", json.dumps([{"results": "x"}]), json.dumps([{"results": [], "success": False}])):
            with self.assertRaises(SystemExit):
                ed.rows_from_wrangler_json(text)

    def test_data_may_already_be_an_object(self):
        docs, rejects = ed.collect([{"collection": "reviews", "id": "a", "data": {"x": 1}}])
        self.assertEqual((docs["reviews"], rejects), ({"a": {"x": 1}}, []))


class ValidationTests(unittest.TestCase):
    def rejected(self, rows):
        docs, rejects = ed.collect(rows)
        return docs, [str(r) for r in rejects]

    def test_rejects(self):
        big = json.dumps({"k": "x" * (ie.MAX_DOC_BYTES + 10)})
        rows = [
            {"collection": "nope", "id": "a", "data": "{}"},
            {"collection": "reviews", "id": "bad id", "data": "{}"},
            {"collection": "reviews", "id": "..", "data": "{}"},
            {"collection": "reviews", "id": "a" * 129, "data": "{}"},
            {"collection": "reviews", "id": "list", "data": "[1]"},
            {"collection": "reviews", "id": "broken", "data": "{"},
            {"collection": "reviews", "id": "big", "data": big},
            {"collection": "reviews", "data": "{}"},
            {"collection": "reviews", "id": "ok", "data": '{"fine": true}'},
            {"collection": "reviews", "id": "ok", "data": '{"fine": false}'},
        ]
        docs, rejects = self.rejected(rows)
        self.assertEqual(docs["reviews"], {"ok": {"fine": True}})
        self.assertEqual(len(rejects), 9)
        self.assertTrue(any("duplicate" in r for r in rejects))
        self.assertTrue(any("unknown collection" in r for r in rejects))

    def test_size_is_measured_on_the_compact_form_the_api_uses(self):
        # 44 KB compact, over 150 KB pretty-printed: the API accepts it, so the export must not reject it
        doc = {"n": [i % 10 for i in range(22000)]}
        self.assertGreater(len(ed.render(doc).encode()), ie.MAX_DOC_BYTES * 2)
        over = {"n": [i % 10 for i in range(33000)]}
        docs, rejects = self.rejected([
            {"collection": "release", "id": "pretty_big", "data": json.dumps(doc, separators=(",", ":"))},
            {"collection": "release", "id": "really_big", "data": json.dumps(over, separators=(",", ":"))},
        ])
        self.assertEqual(sorted(docs["release"]), ["pretty_big"])
        self.assertEqual(len(rejects), 1)
        self.assertIn("release/really_big", rejects[0])
        self.assertIn("compact", rejects[0])

    def test_a_document_that_is_large_only_when_pretty_survives_export_then_import(self):
        doc = {"n": [i % 10 for i in range(22000)]}
        with tmpdir() as d:
            out = Path(d) / "export"
            docs, rejects = ed.collect([{"collection": "release", "id": "pretty_big", "data": json.dumps(doc)}])
            self.assertEqual(rejects, [])
            ed.write_export(docs, out, "2026-11-05")
            self.assertGreater((out / "release" / "pretty_big.json").stat().st_size, ie.MAX_DOC_BYTES)
            back, back_rejects = ie.scan(out)
            self.assertEqual(back_rejects, [])
            self.assertEqual(back["release"]["pretty_big"], doc)

    def test_nan_and_infinity_rows_are_rejected(self):
        docs, rejects = self.rejected([
            {"collection": "reviews", "id": "nan", "data": '{"a": NaN}'},
            {"collection": "reviews", "id": "inf", "data": '{"a": [Infinity]}'},
            {"collection": "reviews", "id": "huge", "data": '{"a": 1e999}'},
            {"collection": "reviews", "id": "already_object", "data": {"a": float("nan")}},
            {"collection": "reviews", "id": "fine", "data": '{"a": 1.5}'},
        ])
        self.assertEqual(sorted(docs["reviews"]), ["fine"])
        self.assertEqual(len(rejects), 4)
        self.assertTrue(all("cannot hold" in r for r in rejects), rejects)

    def test_cli_refuses_to_write_with_rejects_unless_skipped(self):
        with tmpdir() as d:
            js = Path(d) / "rows.json"
            js.write_text(json.dumps([{"results": [
                {"collection": "reviews", "id": "good", "data": "{}"},
                {"collection": "other", "id": "x", "data": "{}"},
            ]}]), encoding="utf-8")
            out = Path(d) / "out"
            code, _, err = run_main(["--from-json", str(js), "--out", str(out)])
            self.assertEqual(code, 1)
            self.assertFalse(out.exists())
            code, _, _ = run_main(["--from-json", str(js), "--out", str(out), "--skip-rejects"])
            self.assertEqual(code, 0)
            self.assertTrue((out / "reviews" / "good.json").is_file())
            self.assertFalse((out / "other").exists())


class CliTests(unittest.TestCase):
    def rows_file(self, d, n=3):
        rows = [{"collection": "reviews", "id": f"s-{i}", "data": json.dumps({"i": i})} for i in range(n)]
        p = Path(d) / "rows.json"
        p.write_text(json.dumps([{"results": rows, "success": True}]), encoding="utf-8")
        return p

    def test_dry_run_prints_counts_and_writes_nothing(self):
        with tmpdir() as d:
            js = self.rows_file(d)
            out = Path(d) / "out"
            code, stdout, _ = run_main(["--from-json", str(js), "--dry-run", "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertFalse(out.exists())
            lines = {ln.split()[0]: ln.split()[1] for ln in stdout.splitlines() if ln.strip() and not ln.startswith(" ")}
            self.assertEqual(lines["reviews"], "3")
            for c in ("decisions", "versions", "release", "batches", "rconfig"):
                self.assertEqual(lines[c], "0")
            self.assertEqual(lines["rejects"], "0")

    def test_refuses_to_write_into_a_non_empty_directory_and_overwrites_nothing(self):
        with tmpdir() as d:
            js = self.rows_file(d)
            out = Path(d) / "out"
            out.mkdir()
            keep = out / "keep.txt"
            keep.write_text("existing")
            code, _, _ = run_main(["--from-json", str(js), "--out", str(out)])
            self.assertNotEqual(code, 0)
            self.assertEqual(keep.read_text(), "existing")
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["keep.txt"])

    def test_an_empty_existing_directory_is_accepted(self):
        with tmpdir() as d:
            js = self.rows_file(d, n=1)
            out = Path(d) / "out"
            out.mkdir()
            code, _, _ = run_main(["--from-json", str(js), "--out", str(out)])
            self.assertEqual(code, 0)

    def test_needs_an_action(self):
        with tmpdir() as d:
            js = self.rows_file(d)
            code, _, _ = run_main(["--from-json", str(js)])
            self.assertNotEqual(code, 0)

    def test_local_without_a_vf_docs_database_fails(self):
        with tmpdir() as d:
            p = Path(d) / "persist"
            p.mkdir()
            c = sqlite3.connect(str(p / "x.sqlite"))
            c.execute("CREATE TABLE submissions (id TEXT)")
            c.commit()
            c.close()
            code, _, _ = run_main(["--local", str(p), "--dry-run"])
            self.assertNotEqual(code, 0)

    def test_local_never_modifies_the_database(self):
        with tmpdir() as d:
            p = Path(d) / "persist"
            p.mkdir()
            c = sqlite3.connect(str(p / "x.sqlite"))
            c.executescript((HERE.parent / "schema.sql").read_text())
            c.commit()
            c.close()
            before = (p / "x.sqlite").read_bytes()
            run_main(["--local", str(p), "--dry-run"])
            self.assertEqual((p / "x.sqlite").read_bytes(), before)


class QueryGuardTests(unittest.TestCase):
    def test_query_and_printed_command_touch_only_vf_tables(self):
        self.assertEqual(sqlguard.violations(ed.QUERY), [])
        cmd = ed.remote_command()
        self.assertIn("wrangler d1 execute object-lessons-submissions --remote --json", cmd)
        self.assertIn("vf_docs", cmd)
        self.assertNotIn("submissions ", cmd.replace("object-lessons-submissions", ""))


if __name__ == "__main__":
    unittest.main()
