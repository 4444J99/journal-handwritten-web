#!/usr/bin/env python3
"""Run this repository's checks locally and, optionally, post the result as a commit status.

When a hosted job cannot run, its cause must be established separately from local results.
This script runs the same check plus every test suite it can find, prints a receipt, and
with --status posts one commit status (context "local-ci") on the exact commit that was tested,
so a pull request shows a real result instead of a failed, step-less job.

    python3 tools/ci_local.py                      # run everything, print the receipt
    python3 tools/ci_local.py --status             # also post the status (clean tree, pushed HEAD)
    python3 tools/ci_local.py --root PATH          # run against another checkout or worktree
    python3 tools/ci_local.py --skip studio-cf-node --json receipt.json

Suites (each runs only if its files exist):
    check           python3 tools/check.py
    py-tests        python3 -m unittest discover -s tests -p "test_*.py"
    node-tests      node --test tests/*.mjs
    studio-cf-py    python3 -m unittest discover -s studio-cf/tests -p "test_*.py"
    studio-cf-node  node --test --test-concurrency=1 studio-cf/tests/*.test.mjs   (starts wrangler dev)

Exit status: 0 every suite passed, 1 a suite failed, 2 refused (bad arguments, dirty tree,
HEAD not pushed). Nothing is written to the repository. A status is only ever posted for a
clean tree whose HEAD exists on the remote, because a status on a commit you did not test would
be a false claim.
"""
import argparse
import glob
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

SUITES = ["check", "py-tests", "node-tests", "studio-cf-py", "studio-cf-node"]
INFO = chr(0x2139)  # the information mark node's test reporter prints before counts


def kill_group(p):
    """Stop a suite and everything it started (a dev server, a browser), not only its first process."""
    # macOS answers EPERM, not ESRCH, when the only member left in a group is an unreaped zombie.
    gone = (ProcessLookupError, PermissionError)
    try:
        os.killpg(p.pid, signal.SIGTERM)
    except gone:
        pass
    try:
        p.wait(timeout=1.0)  # reap the leader so only real stragglers remain in the group
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(p.pid, signal.SIGKILL)  # whatever ignored SIGTERM
    except gone:
        pass
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def run(cmd, cwd, timeout, env):
    """Run one suite in its own process group; on timeout kill the whole group."""
    start = time.monotonic()
    try:
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    except FileNotFoundError as e:
        return 127, f"[command not found: {e.filename}]", time.monotonic() - start
    try:
        out, _ = p.communicate(timeout=timeout)
        return p.returncode, out or "", time.monotonic() - start
    except subprocess.TimeoutExpired:
        kill_group(p)
        try:
            out, _ = p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            out = ""
        return 124, (out or "") + "\n[timed out]", time.monotonic() - start


def count_unittest(out):
    m = re.search(r"Ran (\d+) tests?", out)
    return int(m.group(1)) if m else None


def count_node(out):
    ok = re.search(r"(?:%s|#)\s+pass\s+(\d+)" % INFO, out)
    bad = re.search(r"(?:%s|#)\s+fail\s+(\d+)" % INFO, out)
    return (int(ok.group(1)) if ok else None), (int(bad.group(1)) if bad else None)


def plan(root):
    """Return [(name, cmd, counter)] for the suites whose files exist under root."""
    out = [("check", [sys.executable, str(root / "tools" / "check.py")], None)]
    if glob.glob(str(root / "tests" / "test_*.py")):
        out.append(("py-tests", [sys.executable, "-m", "unittest", "discover", "-s", str(root / "tests"), "-p", "test_*.py"], "unittest"))
    node_files = sorted(glob.glob(str(root / "tests" / "*.mjs")))
    if node_files:
        out.append(("node-tests", ["node", "--test", *node_files], "node"))
    if glob.glob(str(root / "studio-cf" / "tests" / "test_*.py")):
        out.append(("studio-cf-py", [sys.executable, "-m", "unittest", "discover", "-s", str(root / "studio-cf" / "tests"), "-p", "test_*.py"], "unittest"))
    cf_node = sorted(glob.glob(str(root / "studio-cf" / "tests" / "*.test.mjs")))
    if cf_node:
        out.append(("studio-cf-node", ["node", "--test", "--test-concurrency=1", *cf_node], "node"))
    return out


def git(root, *args):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent), help="checkout or worktree to test")
    ap.add_argument("--skip", action="append", default=[], choices=SUITES, help="suite to skip (repeatable)")
    ap.add_argument("--only", action="append", default=[], choices=SUITES, help="run only these suites (repeatable)")
    ap.add_argument("--timeout", type=int, default=900, help="seconds per suite (default 900)")
    ap.add_argument("--tmpdir", help="directory for TMPDIR while tests run (keeps scratch off the system disk)")
    ap.add_argument("--json", dest="json_out", help="write the receipt as JSON to this path")
    ap.add_argument("--status", action="store_true", help='post one commit status, context "local-ci", on HEAD')
    a = ap.parse_args()

    root = Path(a.root).resolve()
    if not (root / "tools" / "check.py").exists():
        print(f"refused: {root} has no tools/check.py", file=sys.stderr)
        return 2

    rc, sha, _ = git(root, "rev-parse", "HEAD")
    if rc:
        print("refused: not a git checkout", file=sys.stderr)
        return 2
    _, branch, _ = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    _, dirty, _ = git(root, "status", "--porcelain")

    if a.status:
        if dirty:
            print("refused: the working tree is not clean, so the result would not describe the commit:\n" + dirty, file=sys.stderr)
            return 2
        _, contained, _ = git(root, "branch", "-r", "--contains", sha)
        if not contained:
            print(f"refused: HEAD {sha[:8]} is not on any remote branch; push it first", file=sys.stderr)
            return 2
        if not shutil.which("gh"):
            print("refused: gh is not installed", file=sys.stderr)
            return 2

    env = dict(os.environ)
    if a.tmpdir:
        tmpdir = Path(a.tmpdir).resolve()  # suites run with cwd=root, so a relative TMPDIR would point elsewhere
        tmpdir.mkdir(parents=True, exist_ok=True)
        env["TMPDIR"] = str(tmpdir)

    selected = [s for s in plan(root) if (not a.only or s[0] in a.only) and s[0] not in a.skip]
    results = []
    for name, cmd, counter in selected:
        code, out, secs = run(cmd, str(root), a.timeout, env)
        detail = ""
        skipped = 0
        if counter == "unittest":
            n = count_unittest(out)
            detail = f"{n} tests" if n is not None else ""
            skip_match = re.search(r"\bskipped=(\d+)", out)
            skipped = int(skip_match.group(1)) if skip_match else 0
        elif counter == "node":
            ok, bad = count_node(out)
            detail = f"{ok} pass, {bad} fail" if ok is not None else ""
            skip_match = re.search(r"(?:%s|#)\s+skipped\s+(\d+)" % INFO, out)
            skipped = int(skip_match.group(1)) if skip_match else 0
            if bad:
                code = code or 1
        elif name == "check":
            detail = out.strip().splitlines()[-1] if out.strip() else ""
        if skipped:
            detail += f", {skipped} skipped"
        results.append({"suite": name, "ok": code == 0, "exit": code, "seconds": round(secs, 1), "detail": detail,
                        "skipped": skipped, "tail": out.strip().splitlines()[-12:] if code else []})

    if not results:
        print("refused: no suite selected", file=sys.stderr)
        return 2
    passed = all(r["ok"] for r in results)

    print(f"local-ci  {branch}@{sha[:8]}  root={root}  tree={'dirty' if dirty else 'clean'}")
    for r in results:
        print(f"  {'PASS' if r['ok'] else 'FAIL'}  {r['suite']:<15} {r['detail']:<28} {r['seconds']:>6.1f}s")
        for line in r["tail"]:
            print("        " + line)
    total_skipped = sum(r["skipped"] for r in results)
    print("RESULT:", ("PASS" if passed else "FAIL") + (f" ({total_skipped} skipped)" if total_skipped else ""))

    receipt = {"sha": sha, "branch": branch, "tree": "dirty" if dirty else "clean", "passed": passed, "suites": results}
    if a.json_out:
        Path(a.json_out).write_text(json.dumps(receipt, indent=2) + "\n")

    if a.status:
        # The suites can run for minutes and may edit files or switch commits. Posting a result for
        # the SHA read before they ran would then describe a commit that was not what got tested.
        _, sha_after, _ = git(root, "rev-parse", "HEAD")
        _, dirty_after, _ = git(root, "status", "--porcelain")
        if sha_after != sha or dirty_after:
            what = dirty_after or f"HEAD {sha[:8]} -> {sha_after[:8]}"
            print("refused: the checkout changed while the suites ran, so the result would not describe a commit:\n" + what, file=sys.stderr)
            return 2
        rc, url, _ = git(root, "remote", "get-url", "origin")
        m = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?$", url or "")
        if not m:
            print(f"refused: cannot read owner/repo from origin {url!r}", file=sys.stderr)
            return 2
        desc = "; ".join(f"{r['suite']} {'ok' if r['ok'] else 'FAILED'}" + (f" ({r['detail']})" if r["detail"] and r["ok"] else "") for r in results)
        coverage = f" ({total_skipped} skipped)" if total_skipped else ""
        desc = (f"run locally{coverage}, not by GitHub Actions: " + desc)[:140]
        p = subprocess.run(["gh", "api", "-X", "POST", f"repos/{m.group(1)}/{m.group(2)}/statuses/{sha}", "-f", f"state={'success' if passed else 'failure'}", "-f", "context=local-ci", "-f", f"description={desc}", "--jq", ".url"], capture_output=True, text=True)
        if p.returncode:
            print("status NOT posted: " + (p.stderr or p.stdout).strip(), file=sys.stderr)
            return 2
        print("status posted:", p.stdout.strip())

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
