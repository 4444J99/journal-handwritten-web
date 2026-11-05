#!/usr/bin/env python3
"""Data prep for the alive prototype. Writes two small JSON files next to this script:

  rules-diary1.json   ruled-line geometry of img/p/diary1.jpg (slope, pad, rule centres in the
                      sheared frame), from segment.py. alive.js uses it to key the ruled lines
                      out of p001's crops. Numbers only.
  city-all58.json     for the 58 complete pieces (group g == 1 in studio/data/review.json), the
                      version-0 line boxes of each piece, in journal page order. Boxes only:
                      no line text is written. Each box is clipped so that it does not intersect
                      any box that belongs to another item on the same page.

Run from anywhere:  python3 proto/alive/build_data.py
Reads (never writes) site/img/p/diary1.jpg, site/data/j.json, studio/data/review.json.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from PIL import Image  # noqa: E402
import segment  # noqa: E402


def write_rules():
    gray = Image.open(os.path.join(REPO, "site", "img", "p", "diary1.jpg")).convert("L")
    s = segment.fit_skew(gray)
    rules, period, _sh, pad = segment.fit_rules(gray, s)
    out = {"page": "diary1", "size": list(gray.size), "slope": round(s, 5), "pad": pad,
           "period": round(period, 2), "rules": [round(r, 2) for r in rules],
           "note": "rule k runs at y = rules[k] - pad + slope*x in the pixel frame of img/p/diary1.jpg"}
    with open(os.path.join(HERE, "rules-diary1.json"), "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("rules:", len(rules), "slope", out["slope"], "period", out["period"])


def inter(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def clip_away(box, others):
    """Shrink box (x0,y0,x1,y1) until it intersects none of `others`. Each step cuts the side
    that keeps the most area. Returns (box or None, clipped_flag)."""
    b = list(box)
    clipped = False
    for _ in range(40):
        hit = next((o for o in others if inter(b, o)), None)
        if hit is None:
            return b, clipped
        clipped = True
        cands = []
        # keep the part above, below, left, right of the obstacle
        cands.append([b[0], b[1], b[2], min(b[3], hit[1])])
        cands.append([b[0], max(b[1], hit[3]), b[2], b[3]])
        cands.append([b[0], b[1], min(b[2], hit[0]), b[3]])
        cands.append([max(b[0], hit[2]), b[1], b[2], b[3]])
        cands = [c for c in cands if c[2] - c[0] >= 8 and c[3] - c[1] >= 8]
        if not cands:
            return None, True
        b = max(cands, key=lambda c: (c[2] - c[0]) * (c[3] - c[1]))
    return None, True


def write_city():
    rv = json.load(open(os.path.join(REPO, "studio", "data", "review.json")))
    jj = json.load(open(os.path.join(REPO, "site", "data", "j.json")))
    jp = {p["id"]: p for p in jj["pages"]}
    pages = {p["id"]: p for p in rv["pages"]}
    items = rv["items"]
    # block -> owning item id, per page
    owner = {}
    for it in items:
        for v in it["versions"]:
            for bi in v["blocks"]:
                owner[(v["page"], bi)] = it["id"]
    g1 = [it for it in items if it["g"] == 1]
    out_pieces = []
    stats = {"pieces": 0, "lines": 0, "boxed": 0, "clipped": 0, "dropped_by_clip": 0}
    for it in g1:
        v = it["versions"][0]
        pg = pages[v["page"]]
        jr = jp[v["page"]]
        assert (pg["w"], pg["h"]) == (jr["iw"], jr["ih"]), v["page"]
        W, H = pg["w"], pg["h"]
        others = []
        for bi, blk in enumerate(pg["blocks"]):
            if owner.get((v["page"], bi)) == it["id"]:
                continue
            for ln in blk["lines"]:
                if ln.get("box"):
                    b = ln["box"]
                    others.append([b[0] * W, b[1] * H, b[2] * W, b[3] * H])
        lines = []
        nbox = 0
        total = 0
        for bi in v["blocks"]:
            blk = pg["blocks"][bi]
            for li, ln in enumerate(blk["lines"]):
                total += 1
                b = ln.get("box")
                if not b:
                    lines.append({"b": bi, "l": li, "box": None})
                    continue
                px = [b[0] * W, b[1] * H, b[2] * W, b[3] * H]
                cb, cl = clip_away(px, others)
                if cb is None:
                    stats["dropped_by_clip"] += 1
                    lines.append({"b": bi, "l": li, "box": None, "dropped": True})
                    continue
                nbox += 1
                if cl:
                    stats["clipped"] += 1
                lines.append({"b": bi, "l": li, "clipped": cl,
                              "box": [max(0, int(round(cb[0]))), max(0, int(round(cb[1]))),
                                      min(W, int(round(cb[2]))), min(H, int(round(cb[3])))]})
        stats["pieces"] += 1
        stats["lines"] += total
        stats["boxed"] += nbox
        out_pieces.append({"id": it["id"], "page": v["page"], "seq": pg["seq"], "size": [W, H],
                           "blocks": v["blocks"], "lines": lines})
    out_pieces.sort(key=lambda p: (p["seq"], p["blocks"][0]))
    doc = {"v": 1, "version_rule": "versions[0] of each item with g == 1 in studio/data/review.json",
           "clip_rule": "box shrunk so it intersects no box of another item (block owned by a different item) on the same page; lines of other items that have no box cannot be excluded",
           "stats": stats, "pieces": out_pieces}
    with open(os.path.join(HERE, "city-all58.json"), "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    print("city:", stats)


if __name__ == "__main__":
    write_rules()
    write_city()
