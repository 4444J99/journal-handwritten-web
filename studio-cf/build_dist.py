#!/usr/bin/env python3
"""Assemble the complete review-studio site into studio-cf/dist/ (git-ignored).

studio/ in the repository holds the page, data/review.json and the thumbnails.
The studio's full scans and spreads (img/<page>.jpg, img/spreads/...) are stored
once, under site/img/p and site/img/s, and are mapped back by tools/check.py's
studio_source(). Deploying studio/ alone would leave the page viewer with 404s
for every full-size image, so a real deploy publishes this assembled directory:

    python3 studio-cf/build_dist.py
    (cd studio-cf && wrangler pages deploy dist --project-name versforms-studio)

Nothing is uploaded by this script. Stdlib only.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "tools"))
from check import studio_source  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / "dist"), help="output directory (default studio-cf/dist)")
    args = ap.parse_args(argv)
    out = Path(args.out).resolve()
    # The only directory this script ever empties is its own generated, git-ignored
    # studio-cf/dist. Any other --out must not exist yet or must be empty.
    if out.exists() and out != HERE / "dist" and any(out.iterdir()):
        raise SystemExit(f"refusing to write into a non-empty directory other than {HERE / 'dist'}: {out}")

    published = {}  # published path -> source path
    for p in sorted((ROOT / "studio").rglob("*")):
        if p.is_file():
            published[p.relative_to(ROOT / "studio").as_posix()] = p
    data = json.loads((ROOT / "studio/data/review.json").read_text())
    for page in data["pages"]:
        for pub in filter(None, [page["img"], page["thumb"], (page.get("spread") or {}).get("img")]):
            pub = pub.lstrip("./")
            published.setdefault(pub, ROOT / studio_source(pub))

    missing = sorted(k for k, v in published.items() if not v.is_file())
    for m in missing:
        print(f"MISSING {m}")
    if out.exists():
        shutil.rmtree(out)
    n = 0
    for pub, src in published.items():
        if not src.is_file():
            continue
        dest = out / pub
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        n += 1
    print(f"{n} files written to {out} ({len(missing)} missing)")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
