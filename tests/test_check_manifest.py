"""tools/check.py must fail when a content file is missing from MANIFEST.sha256.

Each test builds a tiny repository in a temporary folder (a copy of tools/check.py plus
the minimum site/ and studio/ it needs) so nothing under the real site/ or studio/ is touched.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# CHECK_PY lets the same tests run against another copy of check.py (for example the version
# before this fix, to prove these tests fail on it).
REAL_CHECK = Path(os.environ.get("CHECK_PY") or Path(__file__).resolve().parent.parent / "tools" / "check.py")


class CheckManifestTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "tools").mkdir()
        shutil.copy2(REAL_CHECK, self.root / "tools" / "check.py")
        (self.root / "site" / "data").mkdir(parents=True)
        (self.root / "studio" / "data").mkdir(parents=True)
        (self.root / "site" / "index.html").write_text("<html>site</html>")
        (self.root / "site" / "data" / "j.json").write_text(json.dumps({"pages": [], "atlas": []}))
        (self.root / "studio" / "index.html").write_text("<html>studio</html>")
        (self.root / "studio" / "data" / "review.json").write_text(json.dumps({"pages": []}))
        self.run_check("--write")

    def tearDown(self):
        self._tmp.cleanup()

    def run_check(self, *args):
        return subprocess.run(
            [sys.executable, str(self.root / "tools" / "check.py"), *args],
            cwd=str(self.root), capture_output=True, text=True,
        )

    def test_clean_tree_passes(self):
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)

    def test_unmanifested_site_file_fails(self):
        (self.root / "site" / "extra.txt").write_text("not in the manifest")
        r = self.run_check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("NEW      site/extra.txt", r.stdout)
        self.assertIn("1 problem(s)", r.stdout)

    def test_unmanifested_studio_file_fails(self):
        (self.root / "studio" / "extra.txt").write_text("not in the manifest")
        r = self.run_check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("NEW      studio/extra.txt", r.stdout)

    def test_each_unmanifested_file_counts(self):
        (self.root / "site" / "a.txt").write_text("a")
        (self.root / "studio" / "b.txt").write_text("b")
        r = self.run_check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("2 problem(s)", r.stdout)

    def test_write_after_review_makes_it_pass_again(self):
        (self.root / "site" / "extra.txt").write_text("reviewed")
        self.assertEqual(self.run_check().returncode, 1)
        self.assertEqual(self.run_check("--write").returncode, 0)
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_finder_litter_is_not_content(self):
        (self.root / "site" / ".DS_Store").write_bytes(b"\x00\x01")
        (self.root / "studio" / "data" / ".DS_Store").write_bytes(b"\x00\x01")
        r = self.run_check()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.run_check("--write")
        self.assertNotIn(".DS_Store", (self.root / "MANIFEST.sha256").read_text())

    def test_changed_file_still_fails(self):
        (self.root / "site" / "index.html").write_text("<html>edited</html>")
        r = self.run_check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("CHANGED  site/index.html", r.stdout)

    def test_removed_file_still_fails(self):
        (self.root / "studio" / "index.html").unlink()
        r = self.run_check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("GONE     studio/index.html", r.stdout)

    def test_merge_markers_in_shared_records_fail_even_with_a_valid_manifest(self):
        for rel in ["docs/plan.md", "claude/plan.md", "docs/chats/README.md"]:
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            for marker in ["<<<<<<< HEAD", "||||||| 038d01f", "=======", ">>>>>>> origin/main"]:
                with self.subTest(path=rel, marker=marker):
                    p.write_text("# Record\n" + marker + "\n")
                    r = self.run_check()
                    self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
                    self.assertIn("CONFLICT " + rel + ":2", r.stdout)
                    self.assertEqual(self.run_check("--write").returncode, 1)
            p.write_text("# Record\n| Date | Work |\n|---|---|\n")
        self.assertEqual(self.run_check().returncode, 0)


if __name__ == "__main__":
    unittest.main()
