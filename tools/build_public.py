#!/usr/bin/env python3
"""Build the public site from the private one, carrying only released pieces.

    python3 tools/build_public.py OUT_DIR [--release release/public.json]

The release list (release/public.json) names the pieces that have been posted:
    {"pieces": ["p001", ...]}
Nothing else leaves this repository. For the released pieces the build copies:
  - the pages their versions sit on (full, mid and small scans; spreads and
    Hand<->Font plates when those pages have them),
  - a new line atlas holding only those pages (the private atlases hold every page),
  - data/j.json with only those pages, pieces and page groups.
On a released page, text blocks that belong to unreleased pieces are emptied and the
uncertain-reading notes are dropped. The scan itself is a whole page: anything else
written on that page is visible in the image. The build prints those pieces so the
author can decide before posting.

An empty release list builds the engine with no pages.
"""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"


SHELL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>vers.forms</title>
<meta name="robots" content="noindex">
<style>
:root{--paper:#e6dfd2;color-scheme:light}
@media (prefers-color-scheme: dark){:root{--paper:#16171a;color-scheme:dark}}
html,body{margin:0;height:100%;background:var(--paper)}
</style></head><body></body></html>
"""


def pack(rects, width=2048):
    """Shelf-pack (key, w, h) rectangles; returns {key: (x, y)}, (W, H)."""
    pos, x, y, row = {}, 0, 0, 0
    for k, w, h in sorted(rects, key=lambda r: -r[2]):
        if x + w > width:
            x, y, row = 0, y + row, 0
        pos[k] = (x, y)
        x += w
        row = max(row, h)
    return pos, (width, max(1, y + row))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--release", default=str(ROOT / "release" / "public.json"))
    a = ap.parse_args()
    out = Path(a.out)

    rel = json.loads(Path(a.release).read_text()) if Path(a.release).exists() else {"pieces": []}
    want = list(dict.fromkeys(rel.get("pieces", [])))
    d = json.loads((SITE / "data" / "j.json").read_text())
    pieces = {p["id"]: p for p in d["pieces"]}
    missing = [k for k in want if k not in pieces]
    if missing:
        sys.exit(f"unknown piece ids in release list: {missing}")

    # blocks used by released pieces, per page
    keep = {}
    for k in want:
        for v in pieces[k]["V"]:
            for pg, blocks in v["P"]:
                keep.setdefault(pg, set()).update(blocks)
    pages = [p for p in d["pages"] if p["id"] in keep]

    # which unreleased pieces share a released page
    shared = {}
    for p in d["pieces"]:
        if p["id"] in want:
            continue
        for v in p["V"]:
            for pg, _ in v["P"]:
                if pg in keep:
                    shared.setdefault(pg, set()).add(p["id"])

    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)
    shutil.copy2(SITE / "index.html", out / "index.html")

    atlas = []
    if pages:
        from PIL import Image
        srcs = {kind: [Image.open(SITE / "img" / "a" / f"{kind}{n}.jpg") for n in range(len(d["atlas"]))] for kind in ("t", "k")}
        pos, size = pack([(p["id"], p["a"][3], p["a"][4]) for p in pages])
        for kind in ("t", "k"):
            im = Image.new("RGB", size, "white")
            for p in pages:
                n, x, y, w, h = p["a"]
                im.paste(srcs[kind][n].crop((x, y, x + w, y + h)), pos[p["id"]])
            (out / "img" / "a").mkdir(parents=True, exist_ok=True)
            im.save(out / "img" / "a" / f"{kind}0.jpg", quality=90)
        atlas = [list(size)]
        new_pages = []
        for p in pages:
            p = json.loads(json.dumps(p))
            n, x, y, w, h = p["a"]
            p["a"] = [0, pos[p["id"]][0], pos[p["id"]][1], w, h]
            for bi, b in enumerate(p["B"]):
                if bi not in keep[p["id"]]:
                    b["L"] = ["" for _ in b["L"]]
            p["u"] = []
            new_pages.append(p)
            for sub in ("p", "i", "m"):
                (out / "img" / sub).mkdir(parents=True, exist_ok=True)
                shutil.copy2(SITE / "img" / sub / f"{p['id']}.jpg", out / "img" / sub / f"{p['id']}.jpg")
            sp = p.get("sp") or {}
            if sp.get("f"):
                (out / "img" / "s").mkdir(parents=True, exist_ok=True)
                shutil.copy2(SITE / "img" / "s" / f"{sp['f']}.jpg", out / "img" / "s" / f"{sp['f']}.jpg")
            plate = SITE / "img" / "h" / f"{p['id']}.jpg"
            if plate.exists():
                (out / "img" / "h").mkdir(parents=True, exist_ok=True)
                shutil.copy2(plate, out / "img" / "h" / plate.name)
        pages = new_pages

    ids = {p["id"] for p in pages}
    pub = {
        "v": d["v"],
        "pages": pages,
        "groups": [g for g in ([[x for x in g if x in ids] for g in d["groups"]]) if g],
        "atlas": atlas,
        "pieces": [pieces[k] for k in want],
        "prov": d["prov"],
    }
    (out / "data" / "j.json").write_text(json.dumps(pub, ensure_ascii=False, separators=(",", ":")))

    if not want:
        # the engine needs at least one page; until poem 1 posts, serve blank paper only
        shutil.rmtree(out / "data")
        (out / "index.html").write_text(SHELL)

    print(f"released pieces: {len(want)}; pages: {len(pages)}")
    for pg in sorted(shared):
        print(f"  note: {pg} also carries unreleased {sorted(shared[pg])} — visible in the scan, text withheld")


if __name__ == "__main__":
    main()
