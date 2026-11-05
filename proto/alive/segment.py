#!/usr/bin/env python3
"""Segment a scan of ruled-paper handwriting into rows, words and ink glyphs.

Stdlib + Pillow only (no numpy).  Pipeline, all on one page image:

  1. fit_skew      the ruled lines run at a small angle; a vertical shear
                   (Y = y - s*x + pad) that maximises the variance of the
                   row-mean profile makes them horizontal.  Rule centres are the
                   sharp dips of that profile (fit_rules).
  2. binarise      ink = sheared grey < T.  T is the Otsu split of the page
                   histogram taken outside the rule bands (otsu_threshold).
  3. strip_rules   rule pixels (band of +-rule_half rows around each rule centre)
                   are erased only where there is no ink `probe` rows above AND
                   below in the 3 neighbouring columns, so strokes that cross a
                   rule are left whole.
  4. label         8-connected components (pure-python flood fill) with area,
                   sheared-frame box and original-frame y extent.
  5. assign_rows   each component goes to the rule row whose band holds its
                   ink-mass centroid (band = rule centre - P + beta .. + beta,
                   P = rule period, beta = descender allowance).  This only
                   decides WHICH rule rows carry text (>= min_ink ink px); it is
                   the "before" of step 5b.
  5b. partition    adjacent handwritten lines overlap vertically (descenders of
                   line N touch ascenders of line N+1), so 8-connected components
                   merge across rows and a centroid hands whole strokes to the
                   wrong line.  partition() replaces the centroid ownership: one
                   seam per adjacent text-line pair (a min-cost path, one boundary
                   row per column, found by dynamic programming over the sheared
                   ink mask; cost = 8-neighbour ink-ink adjacencies the seam
                   separates + a straightness term + a centring tie-break).  Every
                   ink pixel belongs to exactly one line; components are relabelled
                   inside each line.  The region of a line is the closed polygon
                   between its two seams (region_polygon).  Optional author
                   waypoints (hard constraints, data not code) override the seam.
  6. glyphs        per row: drop specks, merge small marks (dots) into a host
                   component they sit over/under, merge near-touching or nested
                   fragments.  A glyph is an ink component group, NOT a letter.
  7. words         per row: gaps between glyph x-extents; a gap that passes the
                   chosen rule splits a word (rule "fixed:K" = gap >= K*xh,
                   rule "ratio" = largest relative jump among the line's gaps
                   between a floor and a ceiling).

Seam parameters (SEAM_PARAMS) were fixed after looking at the 22 lines of the one page
this was built on: they are in-sample, not validated on held-out pages.

All reported boxes are [x0, y0, x1, y1] integer pixels in the ORIGINAL page
frame (x1, y1 exclusive).  Analysis runs in the sheared frame; boxes are mapped
back by the inverse shear, so they carry roughly +-1 px resampling error.

Library use: see segment_page().  CLI (writes JSON for one page, optional
overlay PNGs):  segment.py PAGE.jpg --out rows.json [--thresh T] [--gap ratio]
"""
import json
import math
import sys
from PIL import Image, ImageDraw


# ---------------------------------------------------------------- shear / rules

def shear(img, s):
    """Return (sheared L image, pad).  Sheared Y = y - s*x + pad."""
    w, h = img.size
    pad = int(abs(s) * w) + 3
    out = img.transform((w, h + 2 * pad), Image.AFFINE, (1, 0, 0, s, 1, -pad),
                        Image.BILINEAR, fillcolor=255)
    return out, pad


def row_means(img):
    w, h = img.size
    return list(img.resize((1, h), Image.BOX).get_flattened_data()) \
        if hasattr(img, "get_flattened_data") else list(img.resize((1, h), Image.BOX).getdata())


def fit_skew(gray, lo=-0.01, hi=0.04):
    """Slope s (dy/dx of the ruled lines) by maximising row-profile variance."""
    def score(s):
        m = row_means(shear(gray, s)[0])
        mu = sum(m) / len(m)
        return sum((v - mu) ** 2 for v in m) / len(m)
    n = int(round((hi - lo) / 0.002))
    best = max((score(lo + i * 0.002), lo + i * 0.002) for i in range(n + 1))[1]
    best = max((score(best + k * 0.0001), best + k * 0.0001) for k in range(-20, 21, 2))[1]
    return best


def fit_rules(gray, s, min_depth=40.0):
    """Rule centres (sheared Y, sub-pixel), the period, and the sheared image/pad."""
    sh, pad = shear(gray, s)
    m = row_means(sh)
    n = len(m)
    d = [0.0] * n
    for y in range(9, n - 9):
        d[y] = (sum(m[y - 8:y - 3]) + sum(m[y + 4:y + 9])) / 10.0 - m[y]
    cen = []
    for y in range(9, n - 9):
        if d[y] >= min_depth and d[y] >= max(d[y - 4:y + 5]):
            ws = [(max(d[k], 0.0), k) for k in range(y - 3, y + 4)]
            tw = sum(w for w, _ in ws)
            cen.append(sum(w * k for w, k in ws) / tw)
    gaps = sorted(cen[i + 1] - cen[i] for i in range(len(cen) - 1))
    period = gaps[len(gaps) // 2] if gaps else 58.0
    return cen, period, sh, pad


def otsu_threshold(img, skip_rows):
    """Otsu split of grey values, ignoring rows in skip_rows (a set)."""
    w, h = img.size
    hist = [0] * 256
    for y in range(h):
        if y in skip_rows:
            continue
        for v, c in enumerate(img.crop((0, y, w, y + 1)).histogram()):
            hist[v] += c
    tot = sum(hist)
    sm = sum(i * c for i, c in enumerate(hist))
    wb = sb = 0
    best = (-1.0, 128)
    for t in range(256):
        wb += hist[t]
        if not wb:
            continue
        wf = tot - wb
        if not wf:
            break
        sb += t * hist[t]
        mb, mf = sb / wb, (sm - sb) / wf
        var = wb * wf * (mb - mf) ** 2
        if var > best[0]:
            best = (var, t)
    return best[1]


# ---------------------------------------------------------------- mask / components

def binarise(sh, thresh, rules, rule_half=2, probe=3):
    """Padded bytearray mask (stride W+2): 1 = ink, with rule bands stripped."""
    w, h = sh.size
    px = sh.tobytes()
    wp = w + 2
    mask = bytearray((h + 2) * wp)
    for y in range(h):
        row = px[y * w:(y + 1) * w]
        base = (y + 1) * wp + 1
        for x, v in enumerate(row):
            if v < thresh:
                mask[base + x] = 1
    removed = 0
    for c in rules:
        cy = int(round(c))
        up, dn = cy - rule_half - probe, cy + rule_half + probe
        if up < 1 or dn > h:
            continue
        ru, rd = (up + 1) * wp + 1, (dn + 1) * wp + 1
        # snapshot probes first so erasing a band never changes the test
        keep = [mask[ru + x - 1] | mask[ru + x] | mask[ru + x + 1] |
                mask[rd + x - 1] | mask[rd + x] | mask[rd + x + 1] for x in range(w)]
        for y in range(cy - rule_half, cy + rule_half + 1):
            b = (y + 1) * wp + 1
            for x in range(w):
                if mask[b + x] and not keep[x]:
                    mask[b + x] = 0
                    removed += 1
    return mask, removed


def label(mask, w, h, s, pad, owner=None, split=False):
    """8-connected components. Each: dict(n, x0, x1, Y0, Y1, sy, oy0, oy1).

    owner: optional padded bytearray (same layout as mask) of a line ordinal per pixel.
    split=False: neighbours connect only when their owners are equal (relabelling inside
    each line); each component then carries "owner".  split=True: connectivity ignores the
    owner and each component carries "owners" (the sorted set of owners its pixels have)."""
    wp = w + 2
    seen = bytearray(len(mask))
    nb = (-1, 1, -wp, wp, -wp - 1, -wp + 1, wp - 1, wp + 1)
    comps = []
    for i in range(wp, len(mask) - wp):
        if not mask[i] or seen[i]:
            continue
        seen[i] = 1
        st = [i]
        n = sy = 0
        x0 = y0 = 1 << 30
        x1 = y1 = -1
        oy0, oy1 = 1e9, -1e9
        ow = owner[i] if owner is not None else None
        ows = {ow} if (owner is not None and split) else None
        link = owner is not None and not split
        while st:
            p = st.pop()
            y, x = divmod(p, wp)
            y -= 1
            x -= 1
            n += 1
            sy += y
            if x < x0: x0 = x
            if x > x1: x1 = x
            if y < y0: y0 = y
            if y > y1: y1 = y
            oy = y - pad + s * x
            if oy < oy0: oy0 = oy
            if oy > oy1: oy1 = oy
            for o in nb:
                q = p + o
                if mask[q] and not seen[q]:
                    if link and owner[q] != ow:
                        continue
                    seen[q] = 1
                    if ows is not None:
                        ows.add(owner[q])
                    st.append(q)
        c = {"n": n, "x0": x0, "x1": x1 + 1, "Y0": y0, "Y1": y1 + 1,
             "sy": sy / n, "oy0": oy0, "oy1": oy1 + 1}
        if link:
            c["owner"] = ow
        if ows is not None:
            c["owners"] = sorted(ows)
        comps.append(c)
    return comps


# ---------------------------------------------------------------- rows, glyphs, words

def assign_rows(comps, rules, period, beta):
    """Row index per component. Returns {row: [comps]}.

    Ink-mass centroid: row k owns centroids up to rules[k] + beta.  (A tried
    correction that pulled tall components up by their top edge merged adjacent
    lines in tightly written stanzas and was removed.)
    """
    rows = {}
    for c in comps:
        k = None
        for i, r in enumerate(rules):
            if c["sy"] <= r + beta:
                k = i
                break
        if k is None:
            k = len(rules) - 1
        c["row"] = k
        c["tall"] = (c["Y1"] - c["Y0"]) > 0.95 * period
        rows.setdefault(k, []).append(c)
    return rows


def _union(a, b):
    n = a["n"] + b["n"]
    return {"n": n, "x0": min(a["x0"], b["x0"]), "x1": max(a["x1"], b["x1"]),
            "Y0": min(a["Y0"], b["Y0"]), "Y1": max(a["Y1"], b["Y1"]),
            "sy": (a["sy"] * a["n"] + b["sy"] * b["n"]) / n,
            "oy0": min(a["oy0"], b["oy0"]), "oy1": max(a["oy1"], b["oy1"]),
            "row": a["row"], "tall": a["tall"] or b["tall"],
            "parts": a.get("parts", 1) + b.get("parts", 1)}


def glyphs_for_row(comps, xh, rule_y, width, speck=8, dot_area=0.12, dot_dim=0.5, near=3, rules=None):
    """Merge a row's components into glyphs. Returns (glyphs, dropped).

    Dropped: specks (< `speck` px), rule residue (<= 3 px tall, centred on a
    rule: the row's own, or with `rules` any rule, because the seam partition hands a line the
    residue lying on an empty neighbouring rule) and page-border slivers (touching the
    left/right image edge, <= 12 px wide).
    """
    resid = rules if rules else [rule_y]
    def junk(c):
        h = c["Y1"] - c["Y0"]
        w = c["x1"] - c["x0"]
        if c["n"] < speck:
            return True
        if h <= 3 and min(abs(c["sy"] - r) for r in resid) <= 2.5:
            return True
        # page-edge shadow / column line: thin sliver within 8 px of the left or right image edge
        return (c["x1"] >= width - 8 or c["x0"] <= 8) and w <= 4 or \
            ((c["x1"] >= width - 2 or c["x0"] <= 1) and w <= 12)
    gl = [dict(c, parts=1) for c in comps if not junk(c)]
    dropped = len(comps) - len(gl)
    dmax = dot_area * xh * xh

    def small(c):
        w, h = c["x1"] - c["x0"], c["Y1"] - c["Y0"]
        if c["n"] <= dmax and max(w, h) <= dot_dim * xh:  # dot, period, speck-like mark
            return True
        # comma-like: a narrow short stroke centred at or below the baseline
        return c["n"] <= 0.45 * xh * xh and c["sy"] >= rule_y - 2 and w <= 0.7 * xh and h <= 1.1 * xh

    changed = True
    while changed:
        changed = False
        gl.sort(key=lambda c: c["x0"])
        for i, a in enumerate(gl):
            for j, b in enumerate(gl):
                if i >= j:
                    continue
                if b["x0"] > a["x1"] + 2 * xh and b["x0"] > a["x1"]:
                    # sorted by x0: later ones are further right; keep scanning only if overlap possible
                    pass
                ox = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
                narrow = min(a["x1"] - a["x0"], b["x1"] - b["x0"])
                vgap = max(a["Y0"], b["Y0"]) - min(a["Y1"], b["Y1"])  # >0 gap, <0 overlap
                merge = False
                if small(a) != small(b):  # a dot and a host
                    d, h = (a, b) if small(a) else (b, a)
                    cx = (d["x0"] + d["x1"]) / 2
                    merge = (h["x0"] - 0.3 * xh <= cx <= h["x1"] + 0.3 * xh) and vgap <= 0.9 * xh
                elif not small(a) and not small(b):
                    inner = (min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]) > 0 and
                             min(a["Y1"], b["Y1"]) - max(a["Y0"], b["Y0"]) > 0)
                    if inner:  # nested: one box (almost) inside the other
                        ia = (min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])) * (min(a["Y1"], b["Y1"]) - max(a["Y0"], b["Y0"]))
                        sa = min((a["x1"] - a["x0"]) * (a["Y1"] - a["Y0"]), (b["x1"] - b["x0"]) * (b["Y1"] - b["Y0"]))
                        merge = ia >= 0.8 * sa
                    if not merge and narrow > 0 and ox >= 0.5 * narrow and 0 <= vgap <= near:
                        merge = True
                if merge:
                    gl[i] = _union(a, b)
                    del gl[j]
                    changed = True
                    break
            if changed:
                break
    gl.sort(key=lambda c: c["x0"])
    for g in gl:
        g["mark"] = small(g)
    return gl, dropped


def words_for_row(glyphs, xh, rule):
    """Group x-sorted glyphs into words. rule: ('fixed', K) or ('ratio',). Returns [[glyph,...],...]."""
    if not glyphs:
        return []
    gaps = []
    reach = glyphs[0]["x1"]
    for g in glyphs[1:]:
        gaps.append(g["x0"] - reach)
        reach = max(reach, g["x1"])
    if rule[0] == "fixed":
        cut = [gp >= rule[1] * xh for gp in gaps]
    else:  # ratio: floor 0.8xh never split, >=2.2xh always split, between: largest jump
        floor, ceil = 0.8 * xh, 2.2 * xh
        cut = [gp >= ceil for gp in gaps]
        mid = sorted(gp for gp in gaps if floor <= gp < ceil)
        thr = None
        if mid:
            base = sorted(gp for gp in gaps if gp < floor) or [floor / 2]
            seq = [base[-1]] + mid
            jumps = [(seq[k + 1] / max(seq[k], 1.0), k) for k in range(len(seq) - 1)]
            jr, jk = max(jumps)
            if jr >= 1.6:
                thr = seq[jk + 1]
        if thr is not None:
            cut = [c or gp >= thr for c, gp in zip(cut, gaps)]
    words = [[glyphs[0]]]
    for g, c in zip(glyphs[1:], cut):
        if c:
            words.append([g])
        else:
            words[-1].append(g)
    return words


# ---------------------------------------------------------------- boxes

def obox(items, size=None):
    """Original-frame box of component-like items (x from sheared == original).
    size=(w, h) clamps the box to the image."""
    x0 = min(i["x0"] for i in items)
    x1 = max(i["x1"] for i in items)
    y0 = int(math.floor(min(i["oy0"] for i in items)))
    y1 = int(math.ceil(max(i["oy1"] for i in items)))
    if size:
        x0, x1 = max(0, x0), min(size[0], x1)
        y0, y1 = max(0, y0), min(size[1], y1)
    return [x0, y0, x1, y1]


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u else 0.0


# ---------------------------------------------------------------- seam partition

# Fixed after looking at the 22 lines of diary1 (in-sample; see README.md / DATA.md).
#  step          max change of the seam row between adjacent columns (px)
#  straightness  cost per px of that change
#  centring      tie-break cost per px away from the middle of the band
#  descender_xh  band depth below the upper baseline, in x-heights; 1.6 * 23.68 = 37.9 px is
#                just above the deepest single-line descender measured on diary1 (35.8 px)
#  ascender_px   highest ascender above the baseline measured on diary1 (53.7 px); only used
#                to widen the band across an empty ruled row
#  body_bottom   the band starts this many rows below the upper rule centre (measured median)
SEAM_PARAMS = {"step": 6, "straightness": 0.05, "centring": 0.002, "descender_xh": 1.6,
               "ascender_px": 53.7, "body_bottom": 1}
BIG = 1e6


def _window_cols(mask, w, Hs, y_first, y_last):
    """Per-column tuples of the ink flags of sheared rows y_first..y_last (inclusive)."""
    wp = w + 2
    rows = []
    for Y in range(y_first, y_last + 1):
        if 0 <= Y < Hs:
            rows.append(mask[(Y + 1) * wp + 1:(Y + 1) * wp + 1 + w])
        else:
            rows.append(bytes(w))
    return list(zip(*rows))


def seam_dp(cols, lo, hi, yc, step, lam, eps, forced=None):
    """Min-cost seam through candidate boundary rows lo..hi (sheared frame), one per column.

    cols[x] holds the ink flags of rows lo-1..hi (index i <-> row lo-1+i).  A seam value y at a
    column puts rows < y on the upper line and rows >= y on the lower one.  Cost: the number of
    8-neighbour ink-ink adjacencies the seam separates (vertical ones at the column itself,
    horizontal and diagonal ones between neighbouring columns) + lam * |change| + eps * |y - yc|.
    forced: optional {x: (ymin, ymax)} hard windows.  Returns (seam list, total cost).
    Pure python; the separated-pair count per column pair is closed-form from prefix sums."""
    w = len(cols)
    m = hi - lo + 1
    cen = [eps * abs(y - yc) for y in range(lo, hi + 1)]

    def node(x):
        c = cols[x]
        nd = [float(c[k] & c[k + 1]) for k in range(m)]
        if forced and x in forced:
            a, b = forced[x]
            for k in range(m):
                if not (a <= lo + k <= b):
                    nd[k] += BIG
        return nd

    nd = node(0)
    dp = [nd[k] + cen[k] for k in range(m)]
    back = [None] * w
    for x in range(1, w):
        cl, cr = cols[x - 1], cols[x]
        nd = node(x)
        if any(cl) and any(cr):
            n1 = m + 1
            ei = [0] * n1
            ej = [0] * n1
            for i in range(n1):
                if cl[i]:
                    ei[i] = (cr[i - 1] if i else 0) + cr[i] + (cr[i + 1] if i + 1 < n1 else 0)
                if cr[i]:
                    ej[i] = (cl[i - 1] if i else 0) + cl[i] + (cl[i + 1] if i + 1 < n1 else 0)
            rowtot, coltot = [0] * m, [0] * m
            r = c = 0
            for k in range(m):
                r += ei[k]
                c += ej[k]
                rowtot[k] = r
                coltot[k] = c
            diag = [(cl[k] & cr[k + 1]) + (cl[k + 1] & cr[k]) for k in range(m)]
            new, bk = [0.0] * m, [0] * m
            for l in range(m):
                best, bkk = float("inf"), 0
                for k in range(max(0, l - step), min(m - 1, l + step) + 1):
                    cut = coltot[l] - rowtot[k] if l > k else (diag[k] if l == k else rowtot[k] - coltot[l])
                    v = (dp[k] + cut) + lam * abs(k - l)
                    if v < best:
                        best, bkk = v, k
                new[l] = (best + nd[l]) + cen[l]
                bk[l] = bkk
        else:
            new, bk = [0.0] * m, [0] * m
            for l in range(m):
                best, bkk = float("inf"), 0
                for k in range(max(0, l - step), min(m - 1, l + step) + 1):
                    v = (dp[k] + 0) + lam * abs(k - l)
                    if v < best:
                        best, bkk = v, k
                new[l] = (best + nd[l]) + cen[l]
                bk[l] = bkk
        dp = new
        back[x] = bk
    k = min(range(m), key=lambda i: (dp[i], i))
    cost = dp[k]
    seam = [0] * w
    for x in range(w - 1, -1, -1):
        seam[x] = lo + k
        if x:
            k = back[x][k]
    return seam, cost


def text_rows_of(rows, min_ink=400):
    """Rule rows that carry text: >= min_ink ink pixels under the centroid assignment."""
    return [k for k in sorted(rows) if sum(c["n"] for c in rows[k]) >= min_ink]


def seam_band(rules, ra, rb, xh, prm):
    """Band (lo, hi) of candidate seam rows and the centring row for the pair of text rows ra < rb."""
    Ba, Bb = rules[ra], rules[rb]
    lo = int(round(Ba)) + prm["body_bottom"]
    c_lo = Ba + prm["descender_xh"] * xh
    c_hi = Bb - prm["ascender_px"]
    hi = int(round(max(c_lo, c_hi)))
    yc = (c_lo + c_hi) / 2.0 if c_hi > c_lo else (lo + hi) / 2.0
    return lo, hi, yc


def forced_windows(waypoints, pair, w, pad, s):
    """{x: (ymin, ymax)} sheared-row windows for the author waypoints of one pair.
    A waypoint record: {"pair": k, "points": [[x, y_page], ...], "tol": px}; the polyline is in
    page pixels (x right, y down), the seam must stay within tol of it on its x range."""
    out = {}
    for wp_ in waypoints or []:
        if wp_["pair"] != pair:
            continue
        pts = sorted(wp_["points"])
        tol = float(wp_.get("tol", 1.0))
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            for x in range(int(math.ceil(xa)), int(math.floor(xb)) + 1):
                if not 0 <= x < w:
                    continue
                t = (x - xa) / (xb - xa) if xb > xa else 0.0
                yp = ya + t * (yb - ya)
                Y = yp + pad - s * (x + 0.5)
                out[x] = (int(math.ceil(Y - tol)), int(math.floor(Y + tol)))
    return out


def owner_array(seams, w, Hs):
    """Padded bytearray (stride w+2): line ordinal per pixel, rows < seam0 -> 0, ... 255 on the pad."""
    wp = w + 2
    own = bytearray(b"\xff" * ((Hs + 2) * wp))
    n = len(seams)
    for x in range(w):
        b = [0] + [sm[x] for sm in seams] + [Hs]
        for j in range(n + 1):
            y0, y1 = b[j], b[j + 1]
            if y1 > y0:
                own[(y0 + 1) * wp + x + 1:(y1 + 1) * wp + x + 1:wp] = bytes([j]) * (y1 - y0)
    return own


def cut_pairs(mask, own, w):
    """8-neighbour ink-ink pairs whose owners differ: list of (Y, x) of the first pixel of each."""
    wp = w + 2
    pts = []
    for i, v in enumerate(mask):
        if not v:
            continue
        oi = own[i]
        for o in (1, wp, wp + 1, wp - 1):
            q = i + o
            if q < len(mask) and mask[q] and own[q] != oi:
                y, x = divmod(i, wp)
                pts.append((y - 1, x - 1))
    return pts


def cluster_sites(pts, radius=3):
    """Single-linkage groups of points at Chebyshev distance <= radius."""
    seen = [False] * len(pts)
    sites = []
    for i in range(len(pts)):
        if seen[i]:
            continue
        seen[i] = True
        grp, st = [i], [i]
        while st:
            j = st.pop()
            for q in range(len(pts)):
                if not seen[q] and max(abs(pts[q][0] - pts[j][0]), abs(pts[q][1] - pts[j][1])) <= radius:
                    seen[q] = True
                    grp.append(q)
                    st.append(q)
        sites.append(grp)
    return sites


def partition(state, xh, min_ink=400, params=None, waypoints=None):
    """Replace the centroid row assignment by the seam partition (see module docstring, 5b).

    Needs the state of prepare().  Sets state["rows"] (rule row -> components owned by that line),
    state["text_rows"], state["seams"] (one list of sheared boundary rows per adjacent text-line
    pair), state["rows_centroid"] (the replaced assignment, kept for before/after) and
    state["partition"] (parameters, bands, conservation and cut counts).  Asserts that every ink
    pixel keeps exactly one owner and that the seams are strictly ordered."""
    prm = dict(SEAM_PARAMS, **(params or {}))
    w, h = state["size"]
    Hs, pad, s = state["Hs"], state["pad"], state["slope"]
    mask, rules = state["mask"], state["rules"]
    cent = state["rows"]
    trows = text_rows_of(cent, min_ink)
    seams, costs, bands = [], [], []
    for i in range(len(trows) - 1):
        lo, hi, yc = seam_band(rules, trows[i], trows[i + 1], xh, prm)
        hi = min(hi, Hs - 1)
        forced = forced_windows(waypoints, i, w, pad, s)
        if forced and any(not (lo <= a <= b <= hi) for a, b in forced.values()):
            raise SystemExit("waypoint window outside the band of pair %d" % i)
        cols = _window_cols(mask, w, Hs, lo - 1, hi)
        sm, cost = seam_dp(cols, lo, hi, yc, prm["step"], prm["straightness"], prm["centring"], forced)
        seams.append(sm)
        costs.append(round(cost, 3))
        bands.append([lo, hi])
    for a, b in zip(seams, seams[1:]):
        if not all(p < q for p, q in zip(a, b)):
            raise SystemExit("seams are not strictly ordered")
    own = owner_array(seams, w, Hs)
    comps = label(mask, w, h, s, pad, owner=own)
    ink_total = sum(c["n"] for c in state["comps"])
    if sum(c["n"] for c in comps) != ink_total:
        raise SystemExit("ink not conserved by the partition")
    rows = {}
    for c in comps:
        k = trows[c["owner"]]
        c["row"] = k
        c["tall"] = (c["Y1"] - c["Y0"]) > 0.95 * state["period"]
        rows.setdefault(k, []).append(c)
    pts = cut_pairs(mask, own, w)
    sites = cluster_sites(pts)
    merged = [c for c in label(mask, w, h, s, pad, owner=own, split=True) if len(c["owners"]) > 1]
    state["rows_centroid"] = cent
    state["rows"] = rows
    state["text_rows"] = trows
    state["seams"] = seams
    state["partition"] = {
        "params": prm, "bands": bands, "costs": costs, "ink_total": ink_total, "ink_after": sum(c["n"] for c in comps),
        "ink_per_line": [sum(c["n"] for c in rows.get(k, [])) for k in trows],
        "cut_adjacencies": len(pts), "cut_sites": len(sites),
        "merged_components_split": len(merged),
        "waypoints_used": sorted({wp_["pair"] for wp_ in waypoints or []}),
    }
    return state


def region_polygon(state, line, ndigits=2):
    """Closed polygon (page pixels, clamped to the page) of the area between line's two seams.

    Vertex x is the column centre (x + 0.5); y of a seam value Y is Y - pad + slope * x_centre.
    Collinear runs are collapsed.  Half-open reading: a page pixel belongs to the region when its
    centre has top <= y < bottom."""
    w, h = state["size"]
    pad, s, seams = state["pad"], state["slope"], state["seams"]

    def curve(sm):
        pts = [(0.0, sm[0] - pad + s * 0.0)]
        pts += [(x + 0.5, sm[x] - pad + s * (x + 0.5)) for x in range(w)]
        pts.append((float(w), sm[w - 1] - pad + s * w))
        return pts

    def flat(y):
        return [(0.0, y), (float(w), y)]

    def thin(pts):
        out = [pts[0]]
        for a, b, c in zip(pts, pts[1:], pts[2:]):
            if abs((b[1] - a[1]) * (c[0] - b[0]) - (c[1] - b[1]) * (b[0] - a[0])) > 1e-7:
                out.append(b)
        out.append(pts[-1])
        return out
    top = flat(0.0) if line == 0 else thin(curve(seams[line - 1]))
    bot = flat(float(h)) if line == len(seams) else thin(curve(seams[line]))
    poly = top + bot[::-1]
    return [[round(x, ndigits), round(min(max(y, 0.0), float(h)), ndigits)] for x, y in poly]


# ---------------------------------------------------------------- driver

def prepare(page_path, thresh=None, xh=22.4, beta_frac=0.3):
    """Load a page and return the shared analysis state (ink components per row)."""
    gray = Image.open(page_path).convert("L")
    w, h = gray.size
    s = fit_skew(gray)
    rules, period, sh, pad = fit_rules(gray, s)
    skip = set()
    for r in rules:
        for y in range(int(r) - 3, int(r) + 4):
            skip.add(y)
    t = thresh if thresh is not None else otsu_threshold(sh, skip)
    mask, removed = binarise(sh, t, rules)
    comps = label(mask, w, sh.size[1], s, pad)
    beta = beta_frac * period
    rows = assign_rows(comps, rules, period, beta)
    return {"size": (w, h), "slope": s, "pad": pad, "rules": rules, "period": period,
            "thresh": t, "rule_px_removed": removed, "comps": comps, "rows": rows, "beta": beta,
            "mask": mask, "Hs": sh.size[1]}


def segment_rows(state, xh, gap_rule, min_ink=400, rows=None):
    """Glyphs and words for every row that carries >= min_ink ink pixels.
    rows: the {rule row: components} assignment to use (default state["rows"], which is the seam
    partition once partition() has run; pass state["rows_centroid"] for the centroid 'before')."""
    out = []
    rows = state["rows"] if rows is None else rows
    for k in sorted(rows):
        cs = rows[k]
        if sum(c["n"] for c in cs) < min_ink:
            continue
        gl, dropped = glyphs_for_row(cs, xh, state["rules"][k], state["size"][0], rules=state["rules"])
        # marks (dots, commas, periods) stay out of the gap analysis: they are
        # reported as glyphs flagged "mark" but never form or extend a word
        words = words_for_row([g for g in gl if not g["mark"]], xh, gap_rule)
        out.append({"row": k, "rule_y": state["rules"][k], "glyphs": gl, "words": words,
                    "specks": dropped, "ink": sum(c["n"] for c in cs),
                    "box": obox(gl, state["size"]) if gl else None})
    return out


def draw_overlay(page_path, row, path, scale=2, pad=14):
    """Word boxes (red) and glyph boxes (blue) over the row crop, upscaled."""
    im = Image.open(page_path).convert("RGB")
    bx = row["box"]
    cx0, cy0 = max(0, bx[0] - pad), max(0, bx[1] - pad)
    cx1, cy1 = min(im.size[0], bx[2] + pad), min(im.size[1], bx[3] + pad)
    cr = im.crop((cx0, cy0, cx1, cy1)).resize(((cx1 - cx0) * scale, (cy1 - cy0) * scale), Image.LANCZOS)
    d = ImageDraw.Draw(cr)

    def R(b, col, wd):
        d.rectangle([(b[0] - cx0) * scale, (b[1] - cy0) * scale, (b[2] - cx0) * scale - 1, (b[3] - cy0) * scale - 1],
                    outline=col, width=wd)
    for g in row["glyphs"]:
        R(obox([g]), (0, 90, 255) if not g["mark"] else (0, 170, 90), 1)
    for wd in row["words"]:
        R(obox(wd), (255, 0, 0), 2)
    cr.save(path)


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("page")
    ap.add_argument("--out", required=True)
    ap.add_argument("--thresh", type=int)
    ap.add_argument("--xh", type=float, default=22.4)
    ap.add_argument("--gap", default="ratio", help="ratio | fixed:K")
    ap.add_argument("--overlay-dir")
    ap.add_argument("--no-seams", action="store_true", help="keep the centroid row assignment (no seam partition)")
    ap.add_argument("--waypoints", help="JSON list of author seam waypoints (see forced_windows)")
    a = ap.parse_args(argv)
    st = prepare(a.page, a.thresh, a.xh)
    if not a.no_seams:
        partition(st, a.xh, waypoints=json.load(open(a.waypoints)) if a.waypoints else None)
    rule = ("ratio",) if a.gap == "ratio" else ("fixed", float(a.gap.split(":")[1]))
    rows = segment_rows(st, a.xh, rule)
    res = {"slope": st["slope"], "thresh": st["thresh"], "period": st["period"],
           "rows": [{"row": r["row"], "box": r["box"], "words": [obox(w) for w in r["words"]],
                     "glyphs": [obox([g]) for g in r["glyphs"]]} for r in rows]}
    if not a.no_seams:
        res["partition"] = st["partition"]
        res["seams"] = st["seams"]
    json.dump(res, open(a.out, "w"))
    if a.overlay_dir:
        for i, r in enumerate(rows):
            draw_overlay(a.page, r, "%s/row%02d.png" % (a.overlay_dir, i))
    print(len(rows), "rows; slope %.4f; thresh %d" % (st["slope"], st["thresh"]))


if __name__ == "__main__":
    main(sys.argv[1:])
