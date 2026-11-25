#!/usr/bin/env python3
"""Scheduled publishing: one poem per week, on the date the author set
(journal-handwritten-web #31).

The schedule is input, not invention: release/schedule.json maps piece ids to
publish dates ('YYYY-MM-DD'). The tool takes publish_at as input; it never
invents a cadence, a season length, or a release order — those stay the
author's decisions, as do the Reserve sort (#105) and the missed-week rule.

  python3 tools/schedule_publish.py --due [YYYY-MM-DD]   # list due pieces + gate verdicts
  python3 tools/schedule_publish.py --due DATE --publish [--public-repo DIR] [--dry-run]

--due lists every piece whose publish_at is due, with its pool and its gate
verdict at this moment. --publish publishes only pieces that pass the gate at
publish time, and refuses Reserve/Archive/unsorted pieces via the #65 gate
(the pool is the author's sort; the scheduler never guesses it). Actual
publication runs through tools/post_poem.py, which needs --public-repo (the
public versforms clone); without it, --publish refuses with a named reason —
publication is a deploy, outside the loop's standing go, so the loop never
supplies it. --dry-run rehearses the publish build (post_poem.py --dry-run)
and writes nothing. With no due pieces, both forms exit 0 and publish nothing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import poem_record  # noqa: E402


def today_iso():
    return dt.datetime.now(dt.timezone.utc).date().isoformat()


def gate_verdicts(root, prepared, db_dir, pieces):
    """Run the release gate over pieces; returns {pid: (ready, [blocker names])}."""
    tmp = Path(tempfile.mkdtemp(prefix="jhw-schedule-gate-"))
    json_out = tmp / "readiness.json"
    cmd = ["node", str(Path(__file__).resolve().parent / "release_readiness.mjs"),
           "--prepared", str(prepared), "--db", str(db_dir),
           "--pieces", ",".join(pieces), "--json", str(json_out)]
    r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    if r.returncode not in (0, 1):
        raise RuntimeError(f"release_readiness.mjs exit {r.returncode}: {(r.stderr or r.stdout).strip()[:500]}")
    report = json.loads(json_out.read_text(encoding="utf-8"))
    return {row["piece"]: (row["ready"], [b["name"] for b in row.get("blockers", [])])
            for row in report["pieces"]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(ROOT), help="repository root")
    ap.add_argument("--db", help="Studio DB export directory (COLLECTION/ID.json)")
    ap.add_argument("--merge-exports", action="store_true",
                    help="merge the checked-in exports/ fragments (default)")
    ap.add_argument("--prepared", help="existing prepared directory (source.json + shell.html)")
    ap.add_argument("--due", default=None, metavar="YYYY-MM-DD",
                    help="list pieces due on or before this date (default: today, UTC)")
    ap.add_argument("--publish", action="store_true", help="publish due pieces that pass the gate")
    ap.add_argument("--public-repo", help="public versforms clone (required for a real publish)")
    ap.add_argument("--dry-run", action="store_true", help="rehearse the publish build; write nothing")
    ap.add_argument("--json", help="write the due/publish report as JSON here")
    a = ap.parse_args(argv)

    root = Path(a.root).resolve()
    due = a.due or today_iso()
    if not poem_record.DATE_RE.match(due):
        print(f"refused: --due must be YYYY-MM-DD, got {due!r}", file=sys.stderr)
        return 2
    try:
        schedule = poem_record.load_schedule(root)
    except ValueError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    due_pieces = sorted(pid for pid, date in schedule.items() if date <= due)
    if not due_pieces:
        print(f"nothing due (schedule has {len(schedule)} dated piece(s); --due {due})")
        if a.json:
            Path(a.json).write_text(json.dumps({"due": due, "pieces": []}, indent=2) + "\n", encoding="utf-8")
        return 0

    # Unknown scheduled pieces are an author-input error: fail loudly.
    j = poem_record.load_json(root / "site" / "data" / "j.json", "site/data/j.json")
    known = {p["id"] for p in j["pieces"]}
    unknown = [pid for pid in due_pieces if pid not in known]
    if unknown:
        print(f"refused: schedule names unknown piece(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    # DB + prepared source, only when there is something due.
    tmp = Path(tempfile.mkdtemp(prefix="jhw-schedule-"))
    if a.db:
        db_dir = Path(a.db)
        db = poem_record.load_db(db_dir)
    else:
        db_dir, _used = poem_record.merge_export_fragments(root, tmp / "db")
        db = poem_record.load_db(db_dir)
    prepared = Path(a.prepared) if a.prepared else tmp / "prepared"
    if not a.prepared:
        r = subprocess.run([sys.executable, str(root / "studio-cf" / "prepare_publish.py"),
                            "--root", str(root), "--out", str(prepared)],
                           cwd=str(root), capture_output=True, text=True)
        if r.returncode != 0:
            print(f"refused: prepare_publish.py exit {r.returncode}:\n{(r.stderr or r.stdout).strip()[:1000]}", file=sys.stderr)
            return 1
    verdicts = gate_verdicts(root, prepared, db_dir, due_pieces)

    report = []
    for pid in due_pieces:
        record = poem_record.build_record(root, db, schedule, pid)
        ready, blockers = verdicts.get(pid, (False, ["not-assessed"]))
        entry = {"piece": pid, "publish_at": schedule[pid], "pool": record["pool"],
                 "ready": ready, "blockers": blockers, "action": None, "reason": None}
        if record["pool"] != "series":
            entry["action"], entry["reason"] = "refused", f"pool is {record['pool']} (the #65 gate: only Series publishes)"
        elif not ready:
            entry["action"], entry["reason"] = "refused", f"gate blocks: {', '.join(blockers)}"
        elif not a.publish:
            entry["action"], entry["reason"] = "due", "passes the gate; --publish to publish"
        elif not a.public_repo and not a.dry_run:
            entry["action"], entry["reason"] = "refused", ("publish needs --public-repo; publication is the author's "
                                                          "post_poem.py step (deploy), not the loop's")
        else:
            cmd = [sys.executable, str(Path(__file__).resolve().parent / "post_poem.py"),
                   "--db", str(db_dir), "--source", str(root), pid]
            if a.dry_run:
                cmd.append("--dry-run")
            else:
                cmd += ["--public-repo", a.public_repo]
            r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
            if r.returncode != 0:
                entry["action"], entry["reason"] = "failed", f"post_poem.py exit {r.returncode}: {(r.stderr or r.stdout).strip()[:300]}"
            else:
                entry["action"] = "published" if not a.dry_run else "dry-run-ok"
                entry["reason"] = "publish succeeded" if not a.dry_run else "publish build rehearsed; nothing written"
        report.append(entry)

    for e in report:
        print(f"{e['piece']}  {e['publish_at']}  {e['pool']:<9} {e['action']}"
              f"{('  ' + e['reason']) if e['reason'] else ''}")
    if a.json:
        Path(a.json).write_text(json.dumps({"due": due, "pieces": report}, indent=2) + "\n", encoding="utf-8")
    failed = [e for e in report if e["action"] == "failed"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
