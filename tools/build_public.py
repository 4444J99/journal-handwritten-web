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
On a released page, text blocks that belong to unreleased pieces (or to versions that are
not published) are emptied, lose their piece link, and the uncertain-reading notes are
dropped. The scan itself is a whole page: anything else written on that page is visible in
the image. The build prints those pieces so the author can decide before posting.

A non-empty build also
  - keeps the noindex robots meta in index.html and writes a _headers file with
    X-Robots-Tag: noindex,
  - drops prov.repo, prov.commit and prov.path from data/j.json (the engine only prints
    them in the info panel and tolerates their absence),
  - renumbers the piece links of published blocks to the published piece list.

An empty release list builds the engine with no pages.

tools/post_poem.py imports build() from here to publish a single poem (final version only,
with the author's corrections applied).
"""
import argparse, json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

NOINDEX_META = '<meta name="robots" content="noindex">'
HEADERS = "/*\n  X-Robots-Tag: noindex\n"
PROV_KEEP = ("tdate", "verified")  # prov.repo / commit / path name the source repository and stay private

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


def add_noindex(html):
    """Return html carrying <meta name="robots" content="noindex">.

    An existing robots meta that already says noindex is kept as it is (a stricter tag such as
    "noindex,nofollow" is never weakened); an existing robots meta without noindex is replaced;
    otherwise the tag goes right after the viewport meta (quoted or unquoted attributes), or after
    <head> when there is no viewport meta."""
    robots = re.search(r"<meta\s+name=[\"']?robots[\"']?[^>]*>", html, re.I)
    if robots:
        if re.search(r"noindex", robots.group(0), re.I):
            return html
        return html[:robots.start()] + NOINDEX_META + html[robots.end():]
    viewport = re.search(r"<meta\s+name=[\"']?viewport[\"']?[^>]*>", html, re.I)
    if viewport:
        return html[:viewport.end()] + NOINDEX_META + html[viewport.end():]
    head = re.search(r"<head[^>]*>", html, re.I)
    if head:
        return html[:head.end()] + NOINDEX_META + html[head.end():]
    raise ValueError("index.html has no viewport meta and no <head>: cannot place the noindex tag")


def has_noindex(html):
    """True when some robots meta tag in html contains noindex."""
    return any(re.search(r"name=[\"']?robots[\"']?", t, re.I) and re.search(r"noindex", t, re.I)
               for t in re.findall(r"<meta\b[^>]*>", html, re.I))


def load_release(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else {"pieces": []}


def build(out, want, site=SITE, select=None, corrections=None, strip_prov=True):
    """Write the public site for the pieces in `want` into `out`; returns a summary dict.

    select       {piece id: [indices into the piece's V]} versions to publish; default all
    corrections  {(page id, block, line): text} replaces machine readings in published blocks
    strip_prov   drop prov.repo / commit / path from data/j.json
    """
    out, site = Path(out), Path(site)
    want = list(dict.fromkeys(want))
    select, corrections = select or {}, dict(corrections or {})
    d = json.loads((site / "data" / "j.json").read_text())
    pieces = {p["id"]: p for p in d["pieces"]}
    missing = [k for k in want if k not in pieces]
    if missing:
        sys.exit(f"unknown piece ids in release list: {missing}")

    # versions published, per piece (indices into V)
    chosen = {}
    for k in want:
        n = len(pieces[k]["V"])
        sel = list(range(n)) if select.get(k) is None else sorted(set(select[k]))
        if not sel or any(not 0 <= i < n for i in sel):
            sys.exit(f"bad version selection for {k}: {sel}")
        chosen[k] = sel

    # published pieces with the chosen versions renumbered; owner[(page, block)] = (piece index, version, rank)
    keep, owner, out_pieces = {}, {}, []
    for npi, k in enumerate(want):
        pc, sel = pieces[k], chosen[k]
        newv = {old: new for new, old in enumerate(sel)}
        st = [newv[i] for i in pc["st"] if i in newv]
        top = newv[pc["top"]] if pc["top"] in newv else st[0]
        out_pieces.append(dict(pc, V=[pc["V"][i] for i in sel], st=st, top=top))
        for old in sel:
            for pg, blocks in pc["V"][old]["P"]:
                keep.setdefault(pg, set()).update(blocks)
                for b in blocks:
                    owner[(pg, b)] = (npi, newv[old], st.index(newv[old]))
    pages = [p for p in d["pages"] if p["id"] in keep]

    # which other pieces (and unpublished versions of published pieces) share a published page
    shared, siblings = {}, {}
    for p in d["pieces"]:
        for vi, v in enumerate(p["V"]):
            for pg, _ in v["P"]:
                if pg not in keep:
                    continue
                if p["id"] not in want:
                    shared.setdefault(pg, set()).add(p["id"])
                elif vi not in chosen[p["id"]]:
                    siblings.setdefault(pg, set()).add(p["id"])

    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)

    atlas, applied = [], 0
    if pages:
        from PIL import Image
        srcs = {kind: [Image.open(site / "img" / "a" / f"{kind}{n}.jpg") for n in range(len(d["atlas"]))] for kind in ("t", "k")}
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
                own = owner.get((p["id"], bi))
                if own is None:
                    # not published: no text, no link to a piece or version, no reading note
                    b["L"] = ["" for _ in b["L"]]
                    for key in ("g", "v", "u"):
                        b.pop(key, None)
                    continue
                if b.get("g"):
                    b["g"] = [own[0], own[2]] + list(b["g"][2:])
                if "v" in b:
                    b["v"] = own[1]
                for li in range(len(b["L"])):
                    text = corrections.pop((p["id"], bi, li), None)
                    if text is not None:
                        b["L"][li] = text
                        applied += 1
            p["u"] = []
            new_pages.append(p)
            for sub in ("p", "i", "m"):
                (out / "img" / sub).mkdir(parents=True, exist_ok=True)
                shutil.copy2(site / "img" / sub / f"{p['id']}.jpg", out / "img" / sub / f"{p['id']}.jpg")
            sp = p.get("sp") or {}
            if sp.get("f"):
                (out / "img" / "s").mkdir(parents=True, exist_ok=True)
                shutil.copy2(site / "img" / "s" / f"{sp['f']}.jpg", out / "img" / "s" / f"{sp['f']}.jpg")
            plate = site / "img" / "h" / f"{p['id']}.jpg"
            if plate.exists():
                (out / "img" / "h").mkdir(parents=True, exist_ok=True)
                shutil.copy2(plate, out / "img" / "h" / plate.name)
        pages = new_pages
    if corrections:
        sys.exit(f"corrections for lines outside the published blocks: {sorted(corrections)[:5]}")

    ids = {p["id"] for p in pages}
    prov = d["prov"]
    if strip_prov:
        prov = {k: v for k, v in prov.items() if k in PROV_KEEP}
    pub = {
        "v": d["v"],
        "pages": pages,
        "groups": [g for g in ([[x for x in g if x in ids] for g in d["groups"]]) if g],
        "atlas": atlas,
        "pieces": out_pieces,
        "prov": prov,
    }
    (out / "data" / "j.json").write_text(json.dumps(pub, ensure_ascii=False, separators=(",", ":")))

    if want:
        (out / "index.html").write_text(add_noindex((site / "index.html").read_text(encoding="utf-8")), encoding="utf-8")
        (out / "_headers").write_text(HEADERS)
    else:
        # the engine needs at least one page; until poem 1 posts, serve blank paper only
        shutil.rmtree(out / "data")
        (out / "index.html").write_text(SHELL)

    return {"want": want, "pages": [p["id"] for p in pages], "shared": shared, "siblings": siblings,
            "applied": applied, "published": sorted(owner), "chosen": chosen}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--release", default=str(ROOT / "release" / "public.json"))
    a = ap.parse_args()

    want = list(dict.fromkeys(load_release(a.release).get("pieces", [])))
    res = build(a.out, want)
    print(f"released pieces: {len(want)}; pages: {len(res['pages'])}")
    for pg in sorted(res["shared"]):
        print(f"  note: {pg} also carries unreleased {sorted(res['shared'][pg])} — visible in the scan, text withheld")


if __name__ == "__main__":
    main()
