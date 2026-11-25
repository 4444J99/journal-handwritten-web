"""tools/schedule_publish.py: the weekly scheduler (journal-handwritten-web #31).

Runs the real script as a subprocess against a minimal synthetic repository
(same two-piece shape as tests/test_poem_record.py) plus a hand-built prepared
directory in the publish-fixture shape, so the gate verdicts are real but
nothing touches the live tree.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_poem_record import mini_db, mini_repo  # noqa: E402

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
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("p002", r.stdout)
        self.assertIn("refused", r.stdout)
        self.assertIn("pool is reserve", r.stdout)

    def test_unsorted_due_is_refused(self):
        db_dir = mini_db(self.base / "db3")
        (db_dir / "release" / "p001.json").unlink()
        self.set_schedule({"p001": "2026-11-20"})
        r = self.run_sched("--due", "2026-11-24", db=db_dir)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("refused", r.stdout)
        self.assertIn("pool is unsorted", r.stdout)

    def test_gate_failing_due_is_refused(self):
        db = mini_db(self.base / "db4", reviews=False)
        self.set_schedule({"p001": "2026-11-20"})
        r = self.run_sched("--due", "2026-11-24", db=db)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
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
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
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


if __name__ == "__main__":
    unittest.main()
