#!/usr/bin/env python3
"""Integrity check for the repository.

Verifies that every image the two pages ask for is present, and that every
file still matches the checksum recorded in MANIFEST.sha256.

    python3 tools/check.py            # check references + checksums
    python3 tools/check.py --write    # rewrite MANIFEST.sha256 from the current tree

Exit status is non-zero on any missing file, any content file that is not in
MANIFEST.sha256, or any checksum mismatch.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "MANIFEST.sha256"
CONTENT_DIRS = ("site", "studio")  # checksummed; docs and tools may change freely
IGNORED_NAMES = {".DS_Store"}  # Finder litter: never content, never checksummed


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tracked_files():
    for d in CONTENT_DIRS:
        for p in sorted((ROOT / d).rglob("*")):
            if p.is_file() and p.name not in IGNORED_NAMES:
                yield p.relative_to(ROOT)


def site_references():
    """Files the merged piece (site/) loads, derived from site/data/j.json."""
    data = json.loads((ROOT / "site/data/j.json").read_text())
    refs = {"site/index.html", "site/data/j.json"}
    for page in data["pages"]:
        pid = page["id"]
        for tier in ("p", "i", "m"):
            refs.add(f"site/img/{tier}/{pid}.jpg")
        spread = page.get("sp") or {}
        if spread.get("f"):
            refs.add(f"site/img/s/{spread['f']}.jpg")
    # Hand<->Font plates: the page list is set in the page code (const HF = [...]).
    html = (ROOT / "site/index.html").read_text()
    m = re.search(r"HF\s*=\s*\[([^\]]*)\]", html)
    for pid in re.findall(r'"([^"]+)"', m.group(1) if m else ""):
        refs.add(f"site/img/h/{pid}.jpg")
    for n in range(len(data.get("atlas", []))):
        refs.add(f"site/img/a/t{n}.jpg")
        refs.add(f"site/img/a/k{n}.jpg")
    return refs


def studio_references():
    """Files the review studio loads. Full scans and spreads are shared with site/."""
    data = json.loads((ROOT / "studio/data/review.json").read_text())
    refs = {"studio/index.html", "studio/data/review.json"}
    for page in data["pages"]:
        refs.add(studio_source(page["img"]))
        refs.add(studio_source(page["thumb"]))
        if page.get("spread"):
            refs.add(studio_source(page["spread"]["img"]))
    return refs


def studio_source(published_path: str) -> str:
    """Map a path the studio requests (as published) to where it lives in the repo."""
    p = published_path.lstrip("./")
    if p.startswith("img/thumbs/"):
        return "studio/" + p
    if p.startswith("img/spreads/"):
        return "site/img/s/" + p.split("/")[-1]
    if p.startswith("img/"):
        return "site/img/p/" + p.split("/")[-1]
    return "studio/" + p


def main() -> int:
    if "--write" in sys.argv:
        lines = [f"{sha256(ROOT / rel)}  {rel.as_posix()}" for rel in tracked_files()]
        MANIFEST.write_text("\n".join(lines) + "\n")
        print(f"wrote {len(lines)} entries to MANIFEST.sha256")
        return 0

    problems = 0
    refs = site_references() | studio_references()
    missing = sorted(r for r in refs if not (ROOT / r).is_file())
    for r in missing:
        print(f"MISSING  {r}")
    problems += len(missing)
    print(f"references: {len(refs)} checked, {len(missing)} missing")

    if MANIFEST.exists():
        recorded = {}
        for line in MANIFEST.read_text().splitlines():
            digest, _, rel = line.partition("  ")
            recorded[rel] = digest
        current = {rel.as_posix() for rel in tracked_files()}
        for rel, digest in recorded.items():
            path = ROOT / rel
            if not path.is_file():
                print(f"GONE     {rel}")
                problems += 1
            elif sha256(path) != digest:
                print(f"CHANGED  {rel}")
                problems += 1
        new_files = sorted(current - recorded.keys())
        for rel in new_files:
            print(f"NEW      {rel}  (run --write after review)")
        problems += len(new_files)  # a content file the manifest omits is not covered by the integrity check
        print(f"checksums: {len(recorded)} recorded")
    else:
        print("no MANIFEST.sha256 yet (run --write)")

    print("OK" if problems == 0 else f"{problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
