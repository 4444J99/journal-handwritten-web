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
PROJECT_RECORDS = ("docs/plan.md", "claude/plan.md", "docs/chats/README.md")
MERGE_MARKER = re.compile(r"^(?:<{7}(?:\s|$)|\|{7}(?:\s|$)|>{7}(?:\s|$)|={7}$)")


def record_conflicts():
    """Catch unresolved normal/diff3 markers in the shared integration records."""
    found = []
    for rel in PROJECT_RECORDS:
        path = ROOT / rel
        if path.is_file():
            for line_no, line in enumerate(path.read_text().splitlines(), 1):
                if MERGE_MARKER.match(line):
                    found.append((rel, line_no))
    return found


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


IMAGES_MANIFEST = "images-manifest.json"
RECIPE_KEYS = ("color_mode", "deskew_deg", "background", "contrast", "denoise",
               "sharpen", "jpeg_quality", "sr", "measurements")


def verify_images_manifest(root: Path) -> list[str]:
    """Verify the image-tier companion manifest (JHW #25).

    Stdlib only, so CI needs no new dependencies. Checks per page: the
    master exists, is checksummed in MANIFEST.sha256, and matches the
    recorded hash; the cleaned file exists and matches its recorded hash;
    the recipe is complete and records no super-resolution model in the
    cleaned tier; a built display tier records its SR model + version.
    Returns a list of problem strings (empty when clean). Absent manifest
    means no trial pages yet, which is not a problem.
    """
    problems: list[str] = []
    path = root / IMAGES_MANIFEST
    if not path.is_file():
        return problems
    try:
        manifest = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return [f"IMAGES-MANIFEST unreadable: {e}"]
    recorded = {}
    manifest_path = root / "MANIFEST.sha256"
    if manifest_path.is_file():
        for line in manifest_path.read_text().splitlines():
            digest, _, rel = line.partition("  ")
            recorded[rel] = digest
    for page_id, entry in sorted((manifest.get("pages") or {}).items()):
        tag = f"images-manifest[{page_id}]"
        master_rel = entry.get("master", "")
        master = root / master_rel
        if not master.is_file():
            problems.append(f"{tag} master missing: {master_rel}")
        elif sha256(master) != entry.get("master_sha256"):
            problems.append(f"{tag} master hash mismatch: {master_rel}")
        elif recorded.get(master_rel) not in (None, entry.get("master_sha256")):
            problems.append(f"{tag} master not the MANIFEST.sha256 master: {master_rel}")
        cleaned_rel = entry.get("cleaned", "")
        cleaned = root / cleaned_rel
        if not cleaned.is_file():
            problems.append(f"{tag} cleaned missing: {cleaned_rel}")
        elif sha256(cleaned) != entry.get("cleaned_sha256"):
            problems.append(f"{tag} cleaned hash mismatch: {cleaned_rel}")
        recipe = entry.get("recipe") or {}
        missing_keys = [k for k in RECIPE_KEYS if k not in recipe]
        if missing_keys:
            problems.append(f"{tag} recipe incomplete, missing: {','.join(missing_keys)}")
        if recipe.get("sr") is not None:
            problems.append(f"{tag} super-resolution recorded in the cleaned tier")
        display = entry.get("display") or {}
        if display.get("status") == "built":
            if not display.get("file") or not display.get("sha256"):
                problems.append(f"{tag} built display tier without file/hash")
            sr = display.get("sr") or {}
            if not sr.get("model") or not sr.get("version"):
                problems.append(f"{tag} built display tier without sr model+version")
        elif display.get("status") != "pending":
            problems.append(f"{tag} display status is neither built nor pending")
    return problems


def main() -> int:
    conflicts = record_conflicts()
    if conflicts:
        for rel, line_no in conflicts:
            print(f"CONFLICT {rel}:{line_no}")
        print(f"{len(conflicts)} unresolved merge marker(s) in project records")
        return 1
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

    image_problems = verify_images_manifest(ROOT)
    for p in image_problems:
        print(f"IMAGES  {p}")
    problems += len(image_problems)
    print(f"image tiers: {len(image_problems)} problem(s)")

    sys.path.insert(0, str(ROOT / "tools"))
    from silent_launch_lint import scan  # no run may make a sound: every browser launch goes through the helper
    bare = scan(ROOT)
    for item in bare:
        print(f"BARE LAUNCH  {item}  (use tools/silent_browser.cjs: silentLaunch / silentChromeArgs)")
    problems += len(bare)
    print(f"silent launches: {len(bare)} bare")

    print("OK" if problems == 0 else f"{problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
