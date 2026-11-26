"""tools/schedule_publish.py: the weekly scheduler (journal-handwritten-web #31).

Runs the real script as a subprocess against a minimal synthetic repository
(same two-piece shape as tests/test_poem_record.py) plus a hand-built prepared
directory in the publish-fixture shape, so the gate verdicts are real but
nothing touches the live tree.
"""
import contextlib
import datetime as dt
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "tools"))
from test_poem_record import mini_db, mini_repo  # noqa: E402
import schedule_publish  # noqa: E402

SCHEDULER = ROOT / "tools" / "schedule_publish.py"


def mini_prepared(tmp, root):
    """A prepared directory in the publish-fixture shape for the mini repo."""
    prepared = Path(tmp) / "prepared"
    prepared.mkdir(parents=True)
    j = json.loads((root / "site" / "data" / "j.json").read_text())
    review = json.loads((root / "studio" / "data" / "review.json").read_text())
    assets = {}
    for p in j["pages"]:
        for k in ("p", "i", "m"):
            assets[f"img/{k}/{p['id']}.jpg"] = {"sha256": "a" * 64, "size": 4, "contentType": "image/jpeg"}
        for k in ("t", "k"):
            assets[f"tiles/{k}-{p['id']}.jpg"] = {"sha256": "b" * 64, "size": 4, "contentType": "image/jpeg"}
    source = {"j": j, "review": review, "twins": {},
              "tiles": {p["id"]: {"size": [16, 16],
                                  "files": {"t": f"tiles/t-{p['id']}.jpg", "k": f"tiles/k-{p['id']}.jpg"}}
                        for p in j["pages"]},
              "assets": assets, "metadata": {"PAL": [], "HF": []}}
    (prepared / "source.json").write_text(json.dumps(source), encoding="utf-8")
    (prepared / "shell.html").write_text(
        '<!doctype html><html><head><title>versforms</title><meta name="robots" content="noindex"></head>'
        '<body><img src="img/p/pg1.jpg" alt="Page 1"></body></html>', encoding="utf-8")
    return prepared


class SchedulePublishTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.root = mini_repo(self.base / "repo")
        self.db = mini_db(self.base / "db1")
        self.prepared = mini_prepared(self.base / "prep1", self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def set_schedule(self, schedule):
        (self.root / "release" / "schedule.json").write_text(json.dumps(schedule), encoding="utf-8")

    def run_sched(self, *args, db=None, prepared=None):
        cmd = [sys.executable, str(SCHEDULER), "--root", str(self.root),
               "--db", str(db or self.db), "--prepared", str(prepared or self.prepared), *args]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_nothing_due(self):
        r = self.run_sched("--due", "2026-11-24")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("nothing due", r.stdout)

    def test_reserve_due_is_refused(self):
        db = mini_db(self.base / "db2", pool_p002="reserve")
        self.set_schedule({"p002": "2026-11-20"})
        r = self.run_sched("--due", "2026-11-24", db=db)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("p002", r.stdout)
        self.assertIn("refused", r.stdout)
        self.assertIn("pool is reserve", r.stdout)

    def test_unsorted_due_is_refused(self):
        db_dir = mini_db(self.base / "db3")
        (db_dir / "release" / "p001.json").unlink()
        self.set_schedule({"p001": "2026-11-20"})
        r = self.run_sched("--due", "2026-11-24", db=db_dir)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("refused", r.stdout)
        self.assertIn("pool is unsorted", r.stdout)

    def test_gate_failing_due_is_refused(self):
        db = mini_db(self.base / "db4", reviews=False)
        self.set_schedule({"p001": "2026-11-20"})
        r = self.run_sched("--due", "2026-11-24", db=db)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("refused", r.stdout)
        self.assertIn("verified", r.stdout)

    def test_passing_due_is_listed_not_published(self):
        self.set_schedule({"p001": "2026-11-20"})
        r = self.run_sched("--due", "2026-11-24")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("p001", r.stdout)
        self.assertIn("due", r.stdout)
        self.assertNotIn("published", r.stdout)

    def test_publish_without_public_repo_is_refused(self):
        self.set_schedule({"p001": "2026-11-20"})
        r = self.run_sched("--due", "2026-11-24", "--publish")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("refused", r.stdout)
        self.assertIn("--public-repo", r.stdout)

    def test_bad_schedule_date_is_a_usage_error(self):
        self.set_schedule({"p001": "next Friday"})
        r = self.run_sched("--due", "2026-11-24")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_unknown_scheduled_piece_is_a_usage_error(self):
        self.set_schedule({"p999": "2026-11-20"})
        r = self.run_sched("--due", "2026-11-24")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)


    # --- F9: a refused due piece is a non-zero exit, distinct from a failed publish
    def test_refused_exit_code_is_distinct_from_failed(self):
        db = mini_db(self.base / "db5", pool_p002="reserve")
        self.set_schedule({"p002": "2026-11-20"})
        self.assertEqual(self.run_sched("--due", "2026-11-24", db=db).returncode, 3)

    # --- F4: impossible dates, trailing newline and non-ASCII digits fail loudly
    def test_impossible_and_malformed_schedule_dates_are_usage_errors(self):
        for bad in ("2026-02-31", "2026-13-01", "2026-00-00", "2026-03-01\n", "\u0662\u0660\u0662\u0666-03-01"):
            self.set_schedule({"p001": bad})
            r = self.run_sched("--due", "2026-12-31")
            self.assertEqual(r.returncode, 2, f"{bad!r}: {r.stdout}{r.stderr}")
            self.assertIn("refused", r.stderr)

    def test_bad_due_argument_is_a_usage_error(self):
        self.set_schedule({"p001": "2026-11-20"})
        for bad in ("2026-02-31", "2026-03-01\n", "tomorrow"):
            r = self.run_sched("--due", bad)
            self.assertEqual(r.returncode, 2, f"{bad!r}: {r.stdout}{r.stderr}")

    # --- F3: the due date is a calendar date in the recorded timezone
    def test_default_due_needs_a_recorded_timezone(self):
        self.set_schedule({"p001": "2026-11-20"})
        r = self.run_sched()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("_timezone", r.stderr)

    def test_unknown_timezone_is_a_usage_error(self):
        self.set_schedule({"p001": "2026-11-20", "_timezone": "Mars/Olympus"})
        r = self.run_sched("--due", "2026-11-24")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("timezone", r.stderr)

    def test_empty_schedule_needs_no_timezone(self):
        r = self.run_sched()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("nothing due", r.stdout)

    def test_today_is_the_calendar_date_in_the_schedule_timezone(self):
        # 2026-12-01 00:30 UTC is still the evening of 2026-11-30 in New York.
        now = dt.datetime(2026, 12, 1, 0, 30, tzinfo=dt.timezone.utc)
        self.assertEqual(schedule_publish.today_in("UTC", now), "2026-12-01")
        self.assertEqual(schedule_publish.today_in("America/New_York", now), "2026-11-30")

    def test_default_due_honours_the_timezone(self):
        now = dt.datetime(2026, 12, 1, 0, 30, tzinfo=dt.timezone.utc)
        real = schedule_publish.today_in
        schedule_publish.today_in = lambda tz, n=None: real(tz, now)
        try:
            self.set_schedule({"p001": "2026-12-01", "_timezone": "America/New_York"})
            code, out, _err = self.run_inprocess("--db", str(self.db), "--prepared", str(self.prepared))
            self.assertEqual(code, 0)
            self.assertIn("nothing due", out)  # 2026-11-30 in New York: not yet
            self.set_schedule({"p001": "2026-12-01", "_timezone": "UTC"})
            code, out, _err = self.run_inprocess("--db", str(self.db), "--prepared", str(self.prepared))
            self.assertEqual(code, 0)
            self.assertIn("p001", out)
        finally:
            schedule_publish.today_in = real

    # --- F1: already-published memory and one piece per week
    def run_inprocess(self, *args, post_poem=None):
        """main() in this process; post_poem.py is replaced by `post_poem(cmd)`
        (returns an exit code) so a real publish needs no public repository."""
        real_run = subprocess.run
        calls = []

        def fake_run(cmd, *a, **kw):
            if len(cmd) > 1 and str(cmd[1]).endswith("post_poem.py"):
                calls.append(cmd)
                return subprocess.CompletedProcess(cmd, post_poem(cmd) if post_poem else 0, "", "boom")
            return real_run(cmd, *a, **kw)

        out, err = io.StringIO(), io.StringIO()
        subprocess.run = fake_run
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = schedule_publish.main(["--root", str(self.root), *args])
        finally:
            subprocess.run = real_run
        self.calls = calls
        return code, out.getvalue(), err.getvalue()

    def series_pair_db(self):
        db = mini_db(self.base / "dbs", pool_p002="series")
        (db / "reviews" / "pg2-0-0.json").write_text(
            json.dumps({"status": "confirmed", "original": "machine-pg2"}), encoding="utf-8")
        return db

    def ledger(self):
        path = self.root / "release" / "schedule-log.json"
        return json.loads(path.read_text()) if path.exists() else None

    def test_public_json_piece_is_skipped_not_retried(self):
        (self.root / "release" / "public.json").write_text(json.dumps({"pieces": ["p001"]}), encoding="utf-8")
        self.set_schedule({"p001": "2026-11-10"})
        code, out, _ = self.run_inprocess("--due", "2026-11-24", "--publish", "--public-repo", "X",
                                          "--db", str(self.db), "--prepared", str(self.prepared))
        self.assertEqual(code, 0, out)
        self.assertIn("already-published", out)
        self.assertEqual(self.calls, [])

    def test_production_exposure_counts_as_published(self):
        db = mini_db(self.base / "dbx")
        doc = json.loads((db / "release" / "p001.json").read_text())
        doc["exposures"] = [{"target": "production", "date": "2026-11-06"}]
        (db / "release" / "p001.json").write_text(json.dumps(doc), encoding="utf-8")
        self.set_schedule({"p001": "2026-11-10"})
        code, out, _ = self.run_inprocess("--due", "2026-11-24", "--publish", "--public-repo", "X",
                                          "--db", str(db), "--prepared", str(self.prepared))
        self.assertEqual(code, 0, out)
        self.assertIn("already-published", out)
        self.assertEqual(self.calls, [])

    def test_catch_up_publishes_one_piece_and_remembers_it(self):
        db = self.series_pair_db()
        self.set_schedule({"p001": "2026-11-17", "p002": "2026-11-20"})
        common = ("--publish", "--public-repo", "X", "--db", str(db), "--prepared", str(self.prepared))
        code, out, _ = self.run_inprocess("--due", "2026-11-24", *common)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("p001", self.calls[0])
        self.assertIn("deferred", out)
        self.assertEqual(self.ledger(), {"published": {"p001": "2026-11-24"}})
        # Two days later: p001 is remembered; p002 waits out the week.
        code, out, _ = self.run_inprocess("--due", "2026-11-26", *common)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.calls, [])
        self.assertIn("already-published", out)
        self.assertIn("one piece per week", out)
        # A full week after the recorded publish, p002 goes out.
        code, out, _ = self.run_inprocess("--due", "2026-12-01", *common)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("p002", self.calls[0])
        self.assertEqual(self.ledger(), {"published": {"p001": "2026-11-24", "p002": "2026-12-01"}})

    def test_dry_run_and_failed_publish_do_not_write_the_ledger(self):
        self.set_schedule({"p001": "2026-11-20"})
        base = ("--due", "2026-11-24", "--publish", "--db", str(self.db), "--prepared", str(self.prepared))
        code, out, _ = self.run_inprocess(*base, "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("dry-run-ok", out)
        self.assertIsNone(self.ledger())
        code, out, _ = self.run_inprocess(*base, "--public-repo", "X", post_poem=lambda cmd: 1)
        self.assertEqual(code, 1, out)
        self.assertIn("failed", out)
        self.assertIsNone(self.ledger())

    def test_a_blocked_earliest_piece_holds_later_ones(self):
        # p001 (earliest) is blocked on the gate; p002 must not jump the queue.
        db = mini_db(self.base / "dbb", pool_p002="series", reviews=False)
        self.set_schedule({"p001": "2026-11-17", "p002": "2026-11-20"})
        code, out, _ = self.run_inprocess("--due", "2026-11-24", "--publish", "--public-repo", "X",
                                          "--db", str(db), "--prepared", str(self.prepared))
        self.assertEqual(code, 3, out)
        self.assertEqual(self.calls, [])
        self.assertIn("deferred", out)


if __name__ == "__main__":
    unittest.main()
