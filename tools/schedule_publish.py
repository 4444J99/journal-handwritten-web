#!/usr/bin/env python3
"""Scheduled publishing: one poem per week, on the date the author set
(journal-handwritten-web #31).

The schedule is input, not invention: release/schedule.json maps piece ids to
publish dates ('YYYY-MM-DD'), plus "_timezone": "Area/City" (an IANA zone) —
the zone those dates are calendar dates in. The tool takes publish_at as input;
it never invents a cadence, a season length, or a release order — those stay
the author's decisions, as do the Reserve sort (#105) and the missed-week rule.
Every date is calendar-validated: a malformed or impossible date is refused
(exit 2), never compared as text. When --due is omitted, "today" is the date in
the recorded _timezone; a schedule with dated pieces and no _timezone is
refused rather than guessed (pass --due to override).

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

Already-published memory and cadence. A due piece is skipped as
"already-published" when it is in release/public.json, in the scheduler's own
ledger release/schedule-log.json, or has a production exposure in the Studio
release document. The ledger ({"published": {piece: date}}) is written after
each real publish (never for --dry-run) and is what the one-per-week rule
reads: at most one piece is attempted per run (the earliest-dated due piece
that is not yet published; later ones are "deferred" and never skipped ahead of
it), and none within 7 days of a recorded publish date. A catch-up after a
missed week therefore publishes one piece, not several.

Exit codes: 0 all due pieces were handled or skipped (published, listed,
already-published, deferred); 1 a publish failed; 2 usage or schedule error;
3 a due piece was refused (pool, gate, or no --public-repo) — a wrapper can
tell that the week's poem did not go out.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import os
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import poem_record  # noqa: E402


WEEK_DAYS = 7
EXIT_FAILED, EXIT_USAGE, EXIT_REFUSED = 1, 2, 3
LEDGER = Path("release") / "schedule-log.json"


def today_in(tz_name, now=None):
    """Today's calendar date (YYYY-MM-DD) in the named IANA zone. `now` is an
    aware datetime (default: the current instant)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    return now.astimezone(ZoneInfo(tz_name)).date().isoformat()


def read_public_ids(root):
    """Piece ids already in release/public.json (pieces + all_versions)."""
    path = Path(root) / "release" / "public.json"
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = []
    if isinstance(data, dict):
        for key in ("pieces", "all_versions"):
            value = data.get(key, [])
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                raise ValueError(f"release/public.json: {key} must be a list of piece id strings")
            ids += value
    else:
        raise ValueError("release/public.json must be an object")
    return set(ids)


def read_ledger(root):
    """release/schedule-log.json -> {piece_id: 'YYYY-MM-DD'} (empty when absent)."""
    path = Path(root) / LEDGER
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    published = data.get("published") if isinstance(data, dict) else None
    if not isinstance(published, dict):
        raise ValueError(f"{LEDGER} must be an object {{\"published\": {{piece_id: 'YYYY-MM-DD'}}}}")
    for pid, date in published.items():
        poem_record.parse_date(date, f"{LEDGER}: bad date for {pid}")
    return dict(published)


def write_ledger(root, ledger):
    """Atomic write (temp file + rename in the same directory)."""
    path = Path(root) / LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".schedule-log.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps({"published": dict(sorted(ledger.items()))}, indent=2) + "\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def production_exposure(record):
    return any(isinstance(e, dict) and e.get("target") == "production" for e in record.get("exposures") or [])


def recent_publication(ledger, due_date):
    """(piece, date) of a ledgered publish within WEEK_DAYS of due_date, else None."""
    best = None
    for pid, date in ledger.items():
        d = poem_record.parse_date(date)
        if abs((due_date - d).days) < WEEK_DAYS and (best is None or d > best[1]):
            best = (pid, d)
    return best


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
                    help="list pieces due on or before this date (default: today in the schedule's _timezone)")
    ap.add_argument("--publish", action="store_true", help="publish due pieces that pass the gate")
    ap.add_argument("--public-repo", help="public versforms clone (required for a real publish)")
    ap.add_argument("--dry-run", action="store_true", help="rehearse the publish build; write nothing")
    ap.add_argument("--json", help="write the due/publish report as JSON here")
    a = ap.parse_args(argv)

    root = Path(a.root).resolve()
    try:
        schedule, tz_name = poem_record.read_schedule(root)
        if a.due:
            due = a.due
            poem_record.parse_date(due, "--due")
        elif not schedule:
            due = None
        elif tz_name is None:
            print('refused: release/schedule.json records no "_timezone"; add one (for example '
                  '"_timezone": "America/New_York") or pass --due YYYY-MM-DD', file=sys.stderr)
            return EXIT_USAGE
        else:
            due = today_in(tz_name)
        public_ids = read_public_ids(root)
        ledger = read_ledger(root)
    except ValueError as e:
        print(f"refused: {e}", file=sys.stderr)
        return EXIT_USAGE

    def write_report(pieces):
        if a.json:
            Path(a.json).write_text(json.dumps({"due": due, "timezone": tz_name, "pieces": pieces}, indent=2) + "\n",
                                    encoding="utf-8")

    due_pieces = sorted((pid for pid, date in schedule.items() if due is not None and date <= due),
                        key=lambda pid: (schedule[pid], pid))
    if not due_pieces:
        print(f"nothing due (schedule has {len(schedule)} dated piece(s); --due {due or 'n/a'})")
        write_report([])
        return 0

    # Unknown scheduled pieces are an author-input error: fail loudly.
    j = poem_record.load_json(root / "site" / "data" / "j.json", "site/data/j.json")
    known = {p["id"] for p in j["pieces"]}
    unknown = [pid for pid in due_pieces if pid not in known]
    if unknown:
        print(f"refused: schedule names unknown piece(s): {', '.join(unknown)}", file=sys.stderr)
        return EXIT_USAGE

    # DB + prepared source, only when there is something due.
    tmp = Path(tempfile.mkdtemp(prefix="jhw-schedule-"))
    if a.db:
        db_dir = Path(a.db)
        db = poem_record.load_db(db_dir)
    else:
        db_dir, _used = poem_record.merge_export_fragments(root, tmp / "db")
        db = poem_record.load_db(db_dir)

    # Already-published pieces are skipped, not retried; the first remaining
    # piece is the only candidate this run (one per run, in schedule order).
    records = {pid: poem_record.build_record(root, db, schedule, pid) for pid in due_pieces}
    report = []
    pending = []
    for pid in due_pieces:
        where = ("release/public.json" if pid in public_ids else
                 f"{LEDGER}" if pid in ledger else
                 "a production exposure" if production_exposure(records[pid]) else None)
        if where:
            report.append({"piece": pid, "publish_at": schedule[pid], "pool": records[pid]["pool"],
                           "ready": None, "blockers": [], "action": "already-published",
                           "reason": f"already published ({where})"})
        else:
            pending.append(pid)
    candidate = pending[0] if pending else None
    for pid in pending[1:]:
        report.append({"piece": pid, "publish_at": schedule[pid], "pool": records[pid]["pool"],
                       "ready": None, "blockers": [], "action": "deferred",
                       "reason": f"one piece per run, in schedule order: waiting on {candidate}"})

    if candidate is not None:
        prepared = Path(a.prepared) if a.prepared else tmp / "prepared"
        if not a.prepared:
            r = subprocess.run([sys.executable, str(root / "studio-cf" / "prepare_publish.py"),
                                "--root", str(root), "--out", str(prepared)],
                               cwd=str(root), capture_output=True, text=True)
            if r.returncode != 0:
                print(f"refused: prepare_publish.py exit {r.returncode}:\n{(r.stderr or r.stdout).strip()[:1000]}", file=sys.stderr)
                return EXIT_FAILED
        pid = candidate
        verdicts = gate_verdicts(root, prepared, db_dir, [pid])
        record = records[pid]
        ready, blockers = verdicts.get(pid, (False, ["not-assessed"]))
        entry = {"piece": pid, "publish_at": schedule[pid], "pool": record["pool"],
                 "ready": ready, "blockers": blockers, "action": None, "reason": None}
        recent = recent_publication(ledger, poem_record.parse_date(due))
        if record["pool"] != "series":
            entry["action"], entry["reason"] = "refused", f"pool is {record['pool']} (the #65 gate: only Series publishes)"
        elif not ready:
            entry["action"], entry["reason"] = "refused", f"gate blocks: {', '.join(blockers)}"
        elif recent is not None:
            entry["action"] = "deferred"
            entry["reason"] = (f"one piece per week: {recent[0]} published {recent[1].isoformat()}; "
                               f"next eligible {(recent[1] + dt.timedelta(days=WEEK_DAYS)).isoformat()}")
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
            elif a.dry_run:
                entry["action"], entry["reason"] = "dry-run-ok", "publish build rehearsed; nothing written"
            else:
                entry["action"], entry["reason"] = "published", "publish succeeded"
                try:
                    write_ledger(root, {**ledger, pid: due})
                except OSError as e:
                    entry["action"] = "failed"
                    entry["reason"] = f"published, but {LEDGER} could not be written ({e}); record it by hand before the next run"
        report.append(entry)

    report.sort(key=lambda e: (e["publish_at"], e["piece"]))
    for e in report:
        print(f"{e['piece']}  {e['publish_at']}  {e['pool']:<9} {e['action']}"
              f"{('  ' + e['reason']) if e['reason'] else ''}")
    write_report(report)
    if any(e["action"] == "failed" for e in report):
        return EXIT_FAILED
    if any(e["action"] == "refused" for e in report):
        return EXIT_REFUSED
    return 0


if __name__ == "__main__":
    sys.exit(main())
