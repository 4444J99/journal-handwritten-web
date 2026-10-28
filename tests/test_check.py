import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestCheckScript(unittest.TestCase):
    def run_check(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/check.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        return result

    def test_fully_covered_unchanged_content_exits_zero(self):
        result = self.run_check()
        self.assertEqual(
            result.returncode,
            0,
            msg=f"Expected exit code 0 when repository is clean. Output:\n{result.stdout}\n{result.stderr}",
        )
        self.assertIn("OK", result.stdout)

    def test_unmanifested_content_file_causes_failure(self):
        test_file_site = ROOT / "site" / "_test_unmanifested_file.txt"
        test_file_studio = ROOT / "studio" / "_test_unmanifested_file.txt"

        try:
            test_file_site.write_text("temporary test content for site")
            test_file_studio.write_text("temporary test content for studio")

            result = self.run_check()

            self.assertNotEqual(
                result.returncode,
                0,
                msg="Expected non-zero exit status when unmanifested content files exist.",
            )
            self.assertIn("site/_test_unmanifested_file.txt", result.stdout)
            self.assertIn("studio/_test_unmanifested_file.txt", result.stdout)

            # Ensure output clearly distinguishes NEW lines with exact relative paths
            site_rel = "site/_test_unmanifested_file.txt"
            studio_rel = "studio/_test_unmanifested_file.txt"

            found_site_new = False
            found_studio_new = False

            for line in result.stdout.splitlines():
                if line.startswith("NEW") and site_rel in line:
                    found_site_new = True
                if line.startswith("NEW") and studio_rel in line:
                    found_studio_new = True

            self.assertTrue(
                found_site_new,
                f"Expected line starting with 'NEW' containing relative path '{site_rel}'",
            )
            self.assertTrue(
                found_studio_new,
                f"Expected line starting with 'NEW' containing relative path '{studio_rel}'",
            )
            self.assertIn("2 problem(s)", result.stdout)

        finally:
            if test_file_site.exists():
                test_file_site.unlink()
            if test_file_studio.exists():
                test_file_studio.unlink()

        # Confirm after cleanup that check passes again without modifying real manifest
        cleanup_result = self.run_check()
        self.assertEqual(cleanup_result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
