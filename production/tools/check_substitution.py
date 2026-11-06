#!/usr/bin/env python3
"""Check that the second piece really went through the same kit.

Compares the p001 and p004 export manifests: same builder, same roles, correct
per-piece paths, no carried-over ids/numbering, no identical output bytes,
clearance still false, readability geometry present.

Usage:
  python3 production/tools/check_substitution.py \
      --primary production/exports/p001 --substitute production/exports/p004
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROLES = {"still", "carousel", "reel", "story", "widget-tile", "downloadable-kit"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(root: Path) -> dict:
    with open(root / "manifest.json", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", default="production/exports/p001")
    ap.add_argument("--substitute", default="production/exports/p004")
    ap.add_argument("--out", default="production/exports/substitution-check.json")
    args = ap.parse_args()

    a_root, b_root = Path(args.primary), Path(args.substitute)
    a, b = load(a_root), load(b_root)
    checks = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    check("same kit version", a["kit_version"] == b["kit_version"],
          f"{a['kit_version']} / {b['kit_version']}")
    check("same generator bytes",
          a["builder"]["kit_py_sha256"] == b["builder"]["kit_py_sha256"],
          "kit.py hash differs")
    check("same clearance schema",
          a["clearance"]["schema"] == b["clearance"]["schema"])
    check("both private",
          a["clearance"]["may_publish"] is False
          and b["clearance"]["may_publish"] is False)
    check("different piece ids",
          a["candidate"]["piece_id"] != b["candidate"]["piece_id"],
          f"{a['candidate']['piece_id']} / {b['candidate']['piece_id']}")
    check("different version ids",
          a["candidate"]["version_id"] != b["candidate"]["version_id"])

    roles_a = {e["role"] for e in a["assets"]}
    roles_b = {e["role"] for e in b["assets"]}
    check("comparable roles", ROLES.issubset(roles_a) and ROLES.issubset(roles_b),
          f"missing: {sorted(ROLES - (roles_a & roles_b))}")

    # Paths and source chains must name their own piece, not the other one.
    bad = []
    for label, m, root, own, other in [
        ("primary", a, a_root, a["candidate"], b["candidate"]),
        ("substitute", b, b_root, b["candidate"], a["candidate"]),
    ]:
        own_id, other_id = own["piece_id"], other["piece_id"]
        own_version, other_version = own["version_id"], other["version_id"]
        for e in m["assets"]:
            if other_id in e["path"] or other_version in e["path"]:
                bad.append(f"{label}: stale id in path {e['path']}")
            chain = " ".join(e.get("source_chain", []))
            if other_id in chain or other_version in chain:
                bad.append(f"{label}: stale id in chain {e['path']}")
            if e["role"] != "downloadable-kit" and (
                own_id not in chain and own_id not in e["path"]
            ):
                bad.append(f"{label}: own id absent from {e['path']}")
            p = root / e["path"]
            if not p.exists():
                bad.append(f"{label}: missing {e['path']}")
                continue
            if sha256(p) != e["sha256"]:
                bad.append(f"{label}: hash mismatch {e['path']}")
    check("paths, chains and hashes", not bad, "; ".join(bad[:6]))

    # No output should be byte-identical across the two pieces.
    hashes_a = {e["sha256"]: e["path"] for e in a["assets"]}
    shared = [f"{e['path']} == {hashes_a[e['sha256']]}" for e in b["assets"]
              if e["sha256"] in hashes_a]
    check("no shared output bytes", not shared, "; ".join(shared[:4]))

    # Numbering: numeric n/100 is not identity. Neither manifest should carry
    # an `n` field or a `NN/100` label in the candidate block.
    numbering = []
    for label, m in [("primary", a), ("substitute", b)]:
        if "n" in m["candidate"] or "number" in m["candidate"]:
            numbering.append(f"{label}: numeric candidate field")
        blob = json.dumps(m["candidate"]).lower()
        if "/100" in blob:
            numbering.append(f"{label}: n/100 label in candidate")
    check("no n/100 identity", not numbering, "; ".join(numbering))

    # Phone-size geometry: every measured target must pass the 8 px rule.
    geom = []
    for label, m in [("primary", a), ("substitute", b)]:
        targets = m.get("qa", {}).get("targets", {})
        if not targets:
            geom.append(f"{label}: no QA targets")
        for name, t in targets.items():
            if t.get("geometry_readable_at_390") is not True:
                geom.append(f"{label}:{name} below 8 px")
    check("phone-size geometry", not geom, "; ".join(geom))

    # Same shape per role. Two intentional differences: the optional
    # carousel-05 slot is `version` vs `detail`, and a single-block substitute
    # skips duplicate widget tiles (>= 4 instead of 6).
    def by_role(m):
        out = {}
        for e in m["assets"]:
            out.setdefault(e["role"], []).append(e)
        return out

    ra, rb = by_role(a), by_role(b)
    shape = []
    for role in ("still", "carousel", "reel", "story", "downloadable-kit"):
        if len(ra.get(role, [])) != len(rb.get(role, [])):
            shape.append(f"{role}: {len(ra.get(role, []))} vs {len(rb.get(role, []))}")
    if len(ra.get("widget-tile", [])) < 4 or len(rb.get("widget-tile", [])) < 4:
        shape.append("widget-tile: fewer than four tiles")
    resize = {e["width"] for e in ra["still"]} == {e["width"] for e in rb["still"]}
    if not resize:
        shape.append("still widths differ")
    check("same output shape", not shape, "; ".join(shape))

    ok = all(c["ok"] for c in checks)
    report = {
        "schema": "t07.substitution-check.v1",
        "primary": str(a_root),
        "substitute": str(b_root),
        "result": "pass" if ok else "fail",
        "checks": checks,
        "note": (
            "Structural and hash check of two exports from the same generator. "
            "Re-run each config with production/kit/kit.py to reproduce. "
            "A pass is not a clearance."
        ),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for c in checks:
        print(f"{'PASS' if c['ok'] else 'FAIL'}  {c['check']}"
              + (f" — {c['detail']}" if not c["ok"] and c["detail"] else ""))
    print(f"{report['result']}: {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
