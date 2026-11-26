#!/usr/bin/env python3
"""Release-gate suite for tools/ci_local.py (journal-handwritten-web #31).

Runs the release gate as a gate, not a report:
  1. Merge the checked-in Studio DB export fragments into one DB dir
     (tools/poem_record.py merge_export_fragments; later fragments win).
  2. Build a prepared source with studio-cf/prepare_publish.py (offline).
  3. Run node tools/release_readiness.mjs over the queued (Series) pieces.
  4. Build the per-poem record for each queued piece and cross-check the
     three fields the gate and the record both derive — pool, verified,
     gruw_filed — against the gate's own verdicts. A mismatch fails the suite.

The suite gates the machinery, not the queue: pieces blocked on verified (or
any other gate) are reported, not failed — the queue is the author's work, and
today p002-p005 are blocked on verified in the checked-in exports. What fails
the suite is the machinery disagreeing with itself, a crashed run, or a
missing prepared export. --require enforces the per-piece form: exit 1 when a
required piece is blocked (the scheduler uses this shape at publish time).

When no export fragment carries a release collection, the suite skips with a
named reason (never a silent pass) and exits 0.

Usage:
  python3 tools/release_gate.py [--root DIR] [--db DIR | --merge-exports]
      [--prepared DIR] [--pieces p001,p002] [--require p001] [--json FILE]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import poem_record  # noqa: E402


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def series_pieces(db):
    return sorted(pid for pid, doc in (db.get("release") or {}).items()
                  if isinstance(doc, dict) and doc.get("pool") == "series")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(ROOT), help="repository root")
    ap.add_argument("--db", help="Studio DB export directory (COLLECTION/ID.json)")
    ap.add_argument("--merge-exports", action="store_true",
                    help="merge the checked-in exports/ fragments (default)")
    ap.add_argument("--prepared", help="existing prepared directory (source.json + shell.html)")
    ap.add_argument("--pieces", help="comma-separated pieces to assess (default: Series pieces in the DB)")
    ap.add_argument("--require", help="comma-separated pieces that must be ready (exit 1 otherwise)")
    ap.add_argument("--json", help="write the receipt JSON here")
    a = ap.parse_args(argv)

    root = Path(a.root).resolve()
    tmp = Path(tempfile.mkdtemp(prefix="jhw-release-gate-"))

    # 1. DB: explicit dir, or the merged in-repo fragments.
    if a.db:
        db_dir, fragments = Path(a.db), ["--db " + a.db]
        db = poem_record.load_db(db_dir)
    else:
        db_dir, used = poem_record.merge_export_fragments(root, tmp / "db")
        fragments = used
        db = poem_record.load_db(db_dir)
    if not db.get("release"):
        print("release-gate: SKIP (no prepared DB export: no release collection in exports/)")
        return 0

    pieces = a.pieces.split(",") if a.pieces else series_pieces(db)
    pieces = [p for p in pieces if p]
    if not pieces:
        print("release-gate: SKIP (no Series pieces in the DB export)")
        return 0

    # 2. Prepared source, unless one was supplied.
    prepared = Path(a.prepared) if a.prepared else tmp / "prepared"
    if not a.prepared:
        code, out, err = run([sys.executable, str(root / "studio-cf" / "prepare_publish.py"),
                              "--root", str(root), "--out", str(prepared)], root)
        if code != 0:
            print(f"release-gate: FAIL (prepare_publish.py exit {code}):\n{err or out}")
            return 1

    # 3. The gate itself.
    json_out = tmp / "readiness.json"
    code, out, err = run(["node", str(root / "tools" / "release_readiness.mjs"),
                          "--prepared", str(prepared), "--db", str(db_dir),
                          "--pieces", ",".join(pieces), "--json", str(json_out)], root)
    if code not in (0, 1):
        print(f"release-gate: FAIL (release_readiness.mjs exit {code}):\n{err or out}")
        return 1
    try:
        report = json.loads(json_out.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"release-gate: FAIL (unreadable readiness JSON: {e})")
        return 1
    rows = {r["piece"]: r for r in report["pieces"]}

    # 4. Cross-check the record against the gate, per piece.
    try:
        schedule = poem_record.load_schedule(root)
    except ValueError as e:
        print(f"release-gate: FAIL (bad schedule: {e})")
        return 1
    mismatches = []
    for pid in pieces:
        row = rows.get(pid)
        if row is None:
            mismatches.append(f"{pid}: gate did not assess it")
            continue
        record = poem_record.build_record(root, db, schedule, pid)
        blocker_names = {b["name"].split(":")[0] for b in row.get("blockers", [])}
        # pool: the record carries the exact-value pool (post_poem.pool_of);
        # the gate's series/own_pool_not_series verdicts must agree with it.
        gate_series_ok = "series" not in blocker_names and "own_pool_not_series" not in blocker_names
        if (record["pool"] == "series") != gate_series_ok:
            mismatches.append(f"{pid}: record pool {record['pool']} but gate "
                              f"{'passes' if gate_series_ok else 'blocks'} series")
        if record["verified"] == ("verified" in blocker_names):
            mismatches.append(f"{pid}: record verified={record['verified']} but gate "
                              f"{'blocks' if 'verified' in blocker_names else 'passes'} verified")
        if record["gruw_filed"] == ("filed" in blocker_names):
            mismatches.append(f"{pid}: record gruw_filed={record['gruw_filed']} but gate "
                              f"{'blocks' if 'filed' in blocker_names else 'passes'} filed")
    if mismatches:
        print("release-gate: FAIL (record/gate mismatch):")
        for m in mismatches:
            print("  " + m)
        return 1

    required = [p for p in (a.require.split(",") if a.require else []) if p]
    missing = [p for p in required if not rows.get(p, {}).get("ready")]
    if missing:
        print(f"release-gate: FAIL (--require: blocked: {', '.join(missing)})")
        return 1

    summary = report["summary"]
    blocked_by = ", ".join(f"{k} x{v}" for k, v in sorted(summary["blockedBy"].items())) or "none"
    new_gates = {}
    for r in report["pieces"]:
        for b in r.get("blockers", []):
            if b["name"].split(":")[0] in ("alt_text", "note_anchors", "links"):
                new_gates[b["name"].split(":")[0]] = new_gates.get(b["name"].split(":")[0], 0) + 1
    new_gate_line = ("; new gates: " + ", ".join(f"{k} x{v}" for k, v in sorted(new_gates.items()))) if new_gates else "; new gates: 0 blocked"
    line = (f"release-gate: {summary['ready']}/{summary['pieces']} ready; blocked by {blocked_by}; "
            f"records agree {len(pieces)}/{len(pieces)}{new_gate_line}; "
            f"fragments: {', '.join(fragments)}")
    print(line)
    if a.json:
        Path(a.json).write_text(json.dumps({
            "summary": summary, "pieces": pieces, "fragments": fragments,
            "records_agree": len(pieces), "mismatches": mismatches,
            "required": required, "required_blocked": missing,
        }, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
