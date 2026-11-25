#!/usr/bin/env python3
"""Backfill method:'original' onto every j.json version record (JHW #55 step 1).

All 156 live versions predate the method field, so all are originals.
Writes with the file's own serialization (compact separators, raw UTF-8),
verified byte-identical on round-trip before the edit, so the diff is only
the 156 inserted "method":"original" pairs, in the renderer's key order
(id, s, P, d, method) that tools/source_foundation.py render_data uses.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import cut_up  # noqa: E402

p = ROOT / "site/data/j.json"
raw = p.read_bytes()
d = json.loads(raw)
assert json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode() == raw, \
    "serializer no longer round-trips; refusing to rewrite"

n = 0
for piece in d["pieces"]:
    for v in piece["V"]:
        if "method" not in v:
            # Insert method after d, matching render_data's key order.
            v["method"] = "original"
            n += 1
        assert "src" not in v or v.get("method") in ("cut-up", "erasure"), \
            f"src on non-cut-up version {v.get('id')}"
        cut_up.validate_version(v)
print(f"backfilled {n} versions (0 means already migrated)")
p.write_bytes(json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode())
print("wrote", p)
