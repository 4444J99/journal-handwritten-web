#!/usr/bin/env python3
"""Assemble the complete review-studio site into studio-cf/dist/ (git-ignored).

studio/ in the repository holds the page, data/review.json and the thumbnails.
The studio's full scans and spreads (img/<page>.jpg, img/spreads/...) are stored
once, under site/img/p and site/img/s, and are mapped back by tools/check.py's
studio_source(). Deploying studio/ alone would leave the page viewer with 404s
for every full-size image, so a real deploy publishes this assembled directory:

    python3 studio-cf/build_dist.py
    (cd studio-cf && wrangler pages deploy dist --project-name versforms-studio)

Nothing is uploaded by this script. Publication preparation also needs the pinned
Pillow/fontTools/brotli build dependencies.
"""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))
from check import studio_source  # noqa: E402
from prepare_publish import prepare  # noqa: E402


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
    # One lifecycle implementation serves the reader and private Studio adapters.
    for asset in ("reader-features.js", "reader-packages.js"):
        published["site/" + asset] = ROOT / "site" / asset
    data = json.loads((ROOT / "studio/data/review.json").read_text())
    for page in data["pages"]:
        for pub in filter(None, [page["img"], page["thumb"], (page.get("spread") or {}).get("img")]):
            pub = pub.lstrip("./")
            published.setdefault(pub, ROOT / studio_source(pub))

    missing = sorted(k for k, v in published.items() if not v.is_file())
    for m in missing:
        print(f"MISSING {m}")
    if missing:
        return 1
    n = 0
    out.parent.mkdir(parents=True, exist_ok=True)
    # Keep the last successful deployment intact until all source and font/atlas
    # preparation succeeds. Staging lives on the same filesystem as the output.
    try:
        with tempfile.TemporaryDirectory(prefix=".dist-build-", dir=out.parent) as temporary:
            staged = Path(temporary) / "dist"
            staged.mkdir()
            for pub, src in published.items():
                dest = staged / pub
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                n += 1
            prepared = prepare(ROOT, staged / "publish")
            previous = Path(temporary) / "previous"
            if out.exists():
                out.replace(previous)
            try:
                staged.replace(out)
            except Exception:
                if previous.exists() and not out.exists():
                    previous.replace(out)
                raise
    except Exception as exc:
        print(f"Studio preparation failed ({type(exc).__name__}); previous output retained", file=sys.stderr)
        return 1
    print(f"publisher shell sha256 {prepared['shellSha256']}")
    print(f"{n} files written to {out} ({len(missing)} missing)")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
