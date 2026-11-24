#!/usr/bin/env python3
"""Generate the reader's pool map (site/data/pools.json) from a studio DB export.

The reader (site/index.html) has no database access, so the Reserve gate in
journal-handwritten-web #30 reads a generated map instead of the live pool.
The map is built with post_poem.py's own pool_of() exact-value rule, imported
not re-implemented: only the studio's exact 'series' / 'reserve' / 'archive'
values count; anything else reads as 'unknown', and a piece absent from the
map has unknown pool. The reader never refuses a deep link, a ghost slot, a
line card or a reel export on an unknown pool -- refusal needs positive
evidence of Reserve (see the pool gate in site/index.html).

The map is only as fresh as the export it was generated from. A fresh export
needs `wrangler d1 execute --remote`, which is the author's Cloudflare
provisioning (JHW #29); regenerate this file whenever a fresh export lands.

    python3 tools/pools.py --pool-db exports/<export-dir> [--out site/data/pools.json]

A damaged export, a release document naming no piece in site/data/j.json,
or an export with no release documents at all is a hard stop (post_poem's
own checks); nothing is written then.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import post_poem  # noqa: E402


def piece_ids():
    data = json.loads((ROOT / "site/data/j.json").read_text())
    return {p["id"] for p in data["pieces"]}


def build(pool_db):
    root, db = post_poem.load_db_with_root(pool_db, piece_ids())
    pools = {}
    for pid in sorted(db["release"]):
        doc = db["release"][pid] or {}
        entry = {"pool": post_poem.pool_of(db, pid)}
        if isinstance(doc.get("num"), int):
            entry["num"] = doc["num"]
        if isinstance(doc.get("order"), int):
            entry["order"] = doc["order"]
        pools[pid] = entry
    return {
        "generated_from": root.name,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_by": "tools/pools.py (journal-handwritten-web #30)",
        "note": ("Pools are only as fresh as the export named in generated_from; "
                 "regenerate from a fresh studio DB export when one lands. "
                 "A piece absent from pools has unknown pool; the reader never "
                 "refuses on unknown -- only an exact 'reserve' refuses."),
        "pools": pools,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pool-db", required=True,
                    help="studio database export directory (COLLECTION/DOCID.json)")
    ap.add_argument("--out", default=str(ROOT / "site/data/pools.json"))
    a = ap.parse_args()
    try:
        out = build(a.pool_db)
    except post_poem.Stop as e:
        print(f"pools: {e}", file=sys.stderr)
        return 1
    dest = Path(a.out)
    dest.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    counts = {}
    for entry in out["pools"].values():
        counts[entry["pool"]] = counts.get(entry["pool"], 0) + 1
    print(f"pools: {len(out['pools'])} pieces from {out['generated_from']}: "
          + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
          + f" -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
