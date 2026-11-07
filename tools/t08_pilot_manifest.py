#!/usr/bin/env python3
"""Write the pilot file inventory (paths, sizes, sha256) for T08.

    python3 tools/t08_pilot_manifest.py [--out PATH]

The inventory covers every file under docs/pilots/t08-p001/ except itself, plus
the source inputs the manifest depends on. It is deterministic: no timestamps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT_DIR = ROOT / "docs/pilots/t08-p001"
DEFAULT_OUT = PILOT_DIR / "pilot-manifest.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.out.resolve()

    files = []
    for path in sorted(PILOT_DIR.rglob("*")):
        if not path.is_file() or path.resolve() == out:
            continue
        if path.name == ".DS_Store":
            continue
        files.append({
            "path": path.relative_to(ROOT).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256(path),
        })

    manifest = json.loads((PILOT_DIR / "p001.source-regions.json").read_text(encoding="utf-8"))
    derivation = manifest["derivations"][0]
    source_asset = manifest["source_assets"][0]
    inventory = {
        "schema": "versforms.t08-pilot-inventory.v1",
        "pilot": {"piece_id": "p001", "version_id": "p001-diary1-0", "page_id": "diary1"},
        "status": "private-pilot-inventory-not-a-release-record",
        "source_inputs": {
            "owner_artifact_ref": derivation["artifact_ref"],
            "owner_artifact_commit": derivation["artifact_commit"],
            "owner_artifact_sha256": derivation["artifact_sha256"],
            "source_scan_path": source_asset["path"],
            "source_scan_sha256": source_asset["sha256"],
            "source_scan_size": source_asset["size"],
        },
        "manifest_content_sha256": manifest["integrity"]["content_sha256"],
        "files": files,
        "counts": {"files": len(files)},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.out} ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
