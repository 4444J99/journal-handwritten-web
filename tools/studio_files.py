#!/usr/bin/env python3
"""Print the file map for republishing the review studio as a Claude artifact.

The studio's full scans and spreads are the same files as the merged piece's
(site/img/p and site/img/s), so the repo stores them once. When the studio is
republished, each path it requests is mapped back to its source here.

    python3 tools/studio_files.py > /tmp/studio_files.json

Output: {"<published path>": "<repo path>", ...}, for the Artifact tool's `files`
input (page itself = studio/index.html). The studio's saved reviews and decisions
live in the artifact's own database, not in this repo; export them before any
change that would affect their keys.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from check import studio_source  # noqa: E402


def main() -> None:
    data = json.loads((ROOT / "studio/data/review.json").read_text())
    files = {"data/review.json": "studio/data/review.json"}
    for page in data["pages"]:
        paths = [page["img"], page["thumb"]]
        if page.get("spread"):
            paths.append(page["spread"]["img"])
        for published in paths:
            files[published] = studio_source(published)
    json.dump(dict(sorted(files.items())), sys.stdout, indent=1)
    sys.stdout.write("\n")
    print(f"{len(files)} files (limit 255 per publish)", file=sys.stderr)


if __name__ == "__main__":
    main()
