#!/usr/bin/env python3
"""Freeze the existing version IDs for the private notes workbench (no new IDs).

The studio already carries review.json. This small companion only retains the
reader's piece/version IDs and version-to-page/block membership; coordinates,
scans, release decisions and poem numbering are not copied. Run after a source
rebuild. --check fails if the companion no longer matches its source bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build(root=ROOT):
    site_bytes = (root / "site/data/j.json").read_bytes()
    review_bytes = (root / "studio/data/review.json").read_bytes()
    site = json.loads(site_bytes)
    pieces = []
    for piece in site["pieces"]:
        versions = []
        for version in piece["V"]:
            # method/src ride with the version record (JHW #55): the map is
            # an id-map, so it carries the fields without allocating new ids.
            # Absent method means "original"; src appears only on
            # cut-up/erasure versions.
            v = {"id": version["id"], "P": version["P"], "d": version.get("d"),
                 "method": version.get("method", "original")}
            if "src" in version:
                v["src"] = version["src"]
            if "sourceVersion" in version:
                v["sourceVersion"] = version["sourceVersion"]
            versions.append(v)
        entry = {"id": piece["id"], "V": versions}
        # `top` is the index of the top version in V. It is NOT always the last
        # entry (the last entry is only the "newest"): a cut made "from the
        # top version" must name V[top], so the Studio needs the field.
        if isinstance(piece.get("top"), int):
            entry["top"] = piece["top"]
        pieces.append(entry)
    return {
        "format": "versforms-notes-versions", "version": 1,
        "provenance": {
            "kind": "derived-id-map", "ids": "preserved; none allocated",
            "sources": [
                {"path": "site/data/j.json", "sha256": hashlib.sha256(site_bytes).hexdigest()},
                {"path": "studio/data/review.json", "sha256": hashlib.sha256(review_bytes).hexdigest()},
            ],
        },
        "pieces": pieces,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    dest = ROOT / "studio/data/notes-versions.json"
    text = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not dest.is_file() or dest.read_text() != text:
            raise SystemExit("Notes version map is stale. Run python3 tools/notes_sources.py after the source rebuild; existing note anchors must then be revalidated.")
        print("Notes version map matches both source files.")
    else:
        dest.write_text(text)
        print(f"Wrote {dest.relative_to(ROOT)}; original source data unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
