"""Regression tests for tools/ci_local.py. Throwaway git repositories and a fake `gh` only:
nothing here can reach GitHub.

    python3 -m unittest discover -s tests -p "test_ci_local.py"

CI_LOCAL_TOOLS may point at another copy of the tools directory (used to prove the tests fail
against the version before the fixes).
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

TOOLS = Path(os.environ.get("CI_LOCAL_TOOLS") or Path(__file__).resolve().parent.parent / "tools")
sys.path.insert(0, str(TOOLS))
import ci_local  # noqa: E402


def sh(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def make_repo(base, check_py):
    """A git repo whose tools/check.py is `check_py`, with HEAD pushed to a local bare origin."""
    repo = Path(base) / "repo"
    (repo / "tools").mkdir(parents=True)
    (repo / "tools" / "check.py").write_text(check_py)
    (repo / "tracked.txt").write_text("one\n")
    origin = Path(base) / "origin.git"
    sh("git", "init", "-q", "--bare", str(origin))
    sh("git", "init", "-q", "-b", "main", cwd=repo)
    sh("git", "config", "user.email", "t@example.test", cwd=repo)
    sh("git", "config", "user.name", "t", cwd=repo)
    sh("git", "add", "-A", cwd=repo)
    sh("git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "init", cwd=repo)
    sh("git", "remote", "add", "origin", str(origin), cwd=repo)
    sh("git", "push", "-q", "origin", "main", cwd=repo)
    return repo


def fake_gh(base):
    """A `gh` that only records that it was called. Returns (env, marker path)."""
    fakebin = Path(base) / "bin"
    fakebin.mkdir()
    marker = Path(base) / "gh-called"
    gh = fakebin / "gh"
    gh.write_text('#!/bin/sh\ntouch "$GH_MARKER"\nexit 0\n')
    gh.chmod(0o755)
    env = dict(os.environ, PATH=str(fakebin) + os.pathsep + os.environ["PATH"], GH_MARKER=str(marker))
    return env, marker


class TimeoutKillsDescendants(unittest.TestCase):
    def test_timeout_kills_the_whole_process_group(self):
        code = "import subprocess,time;p=subprocess.Popen(['sleep','60']);print(p.pid,flush=True);time.sleep(60)"
        rc, out, _ = ci_local.run([sys.executable, "-c", code], os.getcwd(), 2, dict(os.environ))
        self.assertEqual(rc, 124)
        pid = int(out.split()[0])
        deadline, alive = time.time() + 5, True
        while time.time() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                alive = False
                break
            time.sleep(0.2)
        if alive:
            os.kill(pid, 9)  # do not leave a stray process behind when the test fails
        self.assertFalse(alive, "a process started by the suite survived the timeout")


class TmpdirIsAbsolute(unittest.TestCase):
    def test_relative_tmpdir_resolves_against_the_caller(self):
        with tempfile.TemporaryDirectory() as base:
            repo = make_repo(base, "import os\nprint('TMP=' + os.environ.get('TMPDIR', ''))\n")
            caller = Path(base) / "caller"
            caller.mkdir()
            receipt = Path(base) / "r.json"
            p = subprocess.run([sys.executable, str(TOOLS / "ci_local.py"), "--root", str(repo), "--tmpdir", "scratch", "--json", str(receipt)],
                               cwd=caller, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertTrue((caller / "scratch").is_dir())
            detail = json.loads(receipt.read_text())["suites"][0]["detail"]
            self.assertEqual(detail, "TMP=" + str((caller / "scratch").resolve()))


class StatusNeedsAnUnchangedCheckout(unittest.TestCase):
    def run_status(self, check_py):
        with tempfile.TemporaryDirectory() as base:
            repo = make_repo(base, check_py)
            env, marker = fake_gh(base)
            p = subprocess.run([sys.executable, str(TOOLS / "ci_local.py"), "--root", str(repo), "--status"], capture_output=True, text=True, env=env)
            return p, marker.exists()

    def test_nothing_is_posted_when_the_suites_change_the_tree(self):
        p, gh_called = self.run_status("from pathlib import Path\nPath('tracked.txt').write_text('two\\n')\nprint('OK')\n")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("changed while the suites ran", p.stderr)
        self.assertFalse(gh_called, "gh was called although the checkout changed during the run")

    def test_nothing_is_posted_when_the_suites_switch_commit(self):
        code = ("import subprocess\n"
                "subprocess.run(['git','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null','-c','user.email=t@example.test','-c','user.name=t','commit','-q','--allow-empty','-m','x'], check=True)\n"
                "print('OK')\n")
        p, gh_called = self.run_status(code)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("changed while the suites ran", p.stderr)
        self.assertFalse(gh_called)

    def test_control_an_unchanged_checkout_is_not_refused_for_that_reason(self):
        p, _ = self.run_status("print('OK')\n")
        self.assertNotIn("changed while the suites ran", p.stderr)


class SkippedCoverageIsVisible(unittest.TestCase):
    def test_successful_suites_report_skips_in_console_and_receipt(self):
        with tempfile.TemporaryDirectory() as base:
            repo = make_repo(base, "print('OK')\n")
            tests = repo / "tests"
            tests.mkdir()
            (tests / "test_fixture.py").write_text(
                "import unittest\nclass Fixture(unittest.TestCase):\n"
                " def test_pass(self): pass\n"
                " @unittest.skip('fixture dependency is absent')\n"
                " def test_skip(self): pass\n")
            (tests / "fixture.mjs").write_text(
                "import {test} from 'node:test';\n"
                "test('runs',()=>{}); test.skip('dependency absent',()=>{});\n")
            receipt = Path(base) / "receipt.json"
            p = subprocess.run([sys.executable, str(TOOLS / "ci_local.py"), "--root", str(repo),
                                "--only", "py-tests", "--only", "node-tests", "--json", str(receipt)],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("2 tests, 1 skipped", p.stdout)
            self.assertIn("1 pass, 0 fail, 1 skipped", p.stdout)
            self.assertIn("RESULT: PASS (2 skipped)", p.stdout)
            self.assertEqual([r["skipped"] for r in json.loads(receipt.read_text())["suites"]], [1, 1])


if __name__ == "__main__":
    unittest.main()
