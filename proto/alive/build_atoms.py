#!/usr/bin/env python3
"""Build atoms-p001.json: poem p001 -> stanzas -> lines -> words -> glyphs.

Reads site/data/j.json (read-only), takes piece p001 version V[0] and ONLY its
blocks on page diary1, runs segment.py on site/img/p/diary1.jpg, aligns
transcription text to boxes only where counts agree, and writes the atoms file.

    build_atoms.py --out proto/alive/atoms-p001.json [--overlay-dir DIR] [--sweep]

Stdlib + Pillow.  Frame of every box: pixels of site/img/p/diary1.jpg (1135 x 1600).
"""
import argparse
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import segment as S  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PAGE_ID = "diary1"
PIECE_ID = "p001"
RULES = [("fixed", 0.8), ("fixed", 1.0), ("fixed", 1.25), ("fixed", 1.5), ("fixed", 2.0), ("ratio",)]


# Lines (index into the 22) whose word-box count equals the token count but whose boxes,
# checked by eye on the overlay, hold the wrong ink; text alignment is withdrawn for them.
EYE_REVIEW_WITHDRAWN = {13}


def rule_name(r):
    return "ratio" if r[0] == "ratio" else "fixed:%g" % r[1]


def load_poem(jpath):
    d = json.load(open(jpath))
    pc = next(p for p in d["pieces"] if p["id"] == PIECE_ID)
    ver = pc["V"][0]
    pages = [(pid, blocks) for pid, blocks in ver["P"] if pid == PAGE_ID]
    if len(pages) != 1:
        raise SystemExit("V[0] must carry exactly one diary1 entry")
    page = next(p for p in d["pages"] if p["id"] == PAGE_ID)
    stanzas = []
    for bi in pages[0][1]:
        stanzas.append({"block": bi, "lines": list(page["B"][bi]["L"])})
    author = {(e[0], e[1]): [e[2] * page["iw"], e[3] * page["ih"], e[4] * page["iw"], e[5] * page["ih"]] for e in page["x"]}
    xh = statistics.median(e[7] for e in page["x"]) * page["ih"]
    return d, page, ver, stanzas, author, xh


def tokens_of(text):
    return text.split()


def letters_of(text):
    return [c for c in text if c.isalpha()]


def exp_glyphs(tok):
    """Glyphs a token should leave: its letters; a punctuation-only token ('?', a dash) is one glyph."""
    n = len(letters_of(tok))
    return n if n else (1 if tok.strip() else 0)


def guided_words(glyphs, toks):
    """Text-guided split: cut at the len(toks)-1 widest gaps. Accepted by the caller only
    if every word's glyph count equals its token's expected glyph count (independent check)."""
    if len(toks) < 1 or len(glyphs) < len(toks):
        return None
    gaps = []
    reach = glyphs[0]["x1"]
    for k, g in enumerate(glyphs[1:], 1):
        gaps.append((g["x0"] - reach, k))
        reach = max(reach, g["x1"])
    cuts = sorted(k for _, k in sorted(gaps, reverse=True)[:len(toks) - 1])
    words, prev = [], 0
    for k in cuts + [len(glyphs)]:
        words.append(glyphs[prev:k])
        prev = k
    return words


def analyse(state, xh, rule, lines):
    """Segment and count against the transcription. Returns (rows, per-line stats).

    Each row gets r["final_words"] and r["align"]: "gap" (word-box count equals token count
    under the gap rule), "guided" (count differed, but the text-guided split gave per-word
    glyph counts equal to every token's expected glyph count) or None (unaligned)."""
    rows = S.segment_rows(state, xh, rule)
    stats = []
    for idx, (r, ln) in enumerate(zip(rows, lines)):
        ln = dict(ln, index=idx)
        nw = len(r["words"])
        toks = tokens_of(ln["text"])
        non_mark = [g for g in r["glyphs"] if not g["mark"]]
        lets = letters_of(ln["text"])
        exp_total = sum(exp_glyphs(t) for t in toks)
        r["final_words"], r["align"] = r["words"], None
        implausible = False
        if nw == len(toks):
            # Equal counts can be a coincidence (one split missed, one extra).  A per-word
            # glyph/letter-ratio filter was tried and rejected: it dropped two correct lines
            # and kept a wrong one.  Instead the eye review below withdraws known-wrong lines.
            implausible = ln["index"] in EYE_REVIEW_WITHDRAWN
            if not implausible:
                r["align"] = "gap"
        if r["align"] is None:
            gw = guided_words(non_mark, toks)
            if gw and all(len(w) == exp_glyphs(t) for w, t in zip(gw, toks)):
                r["final_words"], r["align"] = gw, "guided"
        wl = wl_eq = 0
        if r["align"]:
            for wd, tk in zip(r["final_words"], toks):
                nl = len(letters_of(tk))
                wl += nl
                if nl and len(wd) == nl:
                    wl_eq += nl
        stats.append({"boxes": nw, "tokens": len(toks), "word_eq": r["align"] == "gap", "align": r["align"],
                      "count_equal_rejected": implausible,
                      "glyphs": len(non_mark), "letters": len(lets), "glyph_eq": len(non_mark) == exp_total,
                      "letters_in_aligned_lines": wl, "letters_in_eq_words": wl_eq})
    return rows, stats


def summarise(stats):
    n = len(stats)
    we = sum(s["word_eq"] for s in stats)
    gd = sum(1 for s in stats if s["align"] == "guided")
    ge = sum(s["glyph_eq"] for s in stats)
    tot_l = sum(s["letters"] for s in stats)
    eq_gap = sum(s["letters_in_eq_words"] for s in stats if s["align"] == "gap")
    eq_gd = sum(s["letters_in_eq_words"] for s in stats if s["align"] == "guided")
    return {"lines": n,
            "word_lines_equal_gap_rule": we, "word_line_rate_gap_rule": round(we / n, 3),
            "word_lines_count_equal_but_withdrawn_by_eye_review": sum(1 for s in stats if s["count_equal_rejected"]),
            "word_lines_guided_verified": gd, "word_lines_unaligned": n - we - gd,
            "glyph_lines_equal_whole_line": ge, "glyph_line_rate": round(ge / n, 3),
            "letters_total": tot_l,
            "letters_in_count_equal_words_gap_tier": eq_gap,
            "letters_in_count_equal_words_guided_tier": eq_gd,
            "letter_alignment_rate_gap_tier": round(eq_gap / tot_l, 3),
            "letter_alignment_rate_incl_guided": round((eq_gap + eq_gd) / tot_l, 3),
            "boxes_total": sum(s["boxes"] for s in stats), "tokens_total": sum(s["tokens"] for s in stats),
            "glyphs_total": sum(s["glyphs"] for s in stats)}


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--overlay-dir")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--thresh", type=int, help="override the Otsu threshold")
    ap.add_argument("--rule", default=None, help="fixed word-gap rule to use, e.g. fixed:1.25 or ratio")
    a = ap.parse_args(argv)

    jpath = os.path.join(ROOT, "site/data/j.json")
    ppath = os.path.join(ROOT, "site/img/p/%s.jpg" % PAGE_ID)
    d, page, ver, stanzas, author, xh = load_poem(jpath)
    lines = []
    for si, st in enumerate(stanzas):
        for li, txt in enumerate(st["lines"]):
            lines.append({"stanza": si, "line": li, "block": st["block"], "text": txt})
    state = S.prepare(ppath, a.thresh, xh)

    sweep = []
    if a.sweep:
        for t in (110, 130, 150, state["thresh"], 190):
            stt = S.prepare(ppath, t, xh)
            for r in RULES:
                rows, stats = analyse(stt, xh, r, lines)
                sm = summarise(stats)
                sweep.append({"thresh": t, "gap_rule": rule_name(r), "rows": len(rows),
                              "word_line_rate": sm["word_line_rate_gap_rule"], "glyph_line_rate": sm["glyph_line_rate"],
                              "boxes": sm["boxes_total"], "tokens": sm["tokens_total"], "glyphs": sm["glyphs_total"],
                              "letter_alignment_rate": sm["letter_alignment_rate_gap_tier"]})
        best = max(sweep, key=lambda s: (s["thresh"] == state["thresh"], s["word_line_rate"], -abs(s["boxes"] - s["tokens"])))
        for s in sweep:
            print("T=%3d %-9s rows=%d word_lines=%.3f glyph_lines=%.3f boxes=%d/tokens=%d glyphs=%d letters_aligned=%.3f"
                  % (s["thresh"], s["gap_rule"], s["rows"], s["word_line_rate"], s["glyph_line_rate"], s["boxes"],
                     s["tokens"], s["glyphs"], s["letter_alignment_rate"]))
        chosen = ("ratio",) if best["gap_rule"] == "ratio" else ("fixed", float(best["gap_rule"].split(":")[1]))
    else:
        chosen = ("ratio",) if (a.rule or "fixed:1.25") == "ratio" else ("fixed", float((a.rule or "fixed:1.25").split(":")[1]))
    if a.rule:
        chosen = ("ratio",) if a.rule == "ratio" else ("fixed", float(a.rule.split(":")[1]))

    rows, stats = analyse(state, xh, chosen, lines)
    if len(rows) != len(lines):
        raise SystemExit("row count %d != line count %d" % (len(rows), len(lines)))
    summ = summarise(stats)

    out_st = []
    for si, st in enumerate(stanzas):
        out_st.append({"stanza": si, "block": st["block"], "lines": []})
    for idx, (ln, r, sx) in enumerate(zip(lines, rows, stats)):
        lbox = r["box"]
        # author boxes: expected key vs best-overlapping key
        exp = author.get((ln["block"], ln["line"]))
        best_key, best_iou = None, 0.0
        for k, b in author.items():
            v = S.iou(lbox, b)
            if v > best_iou:
                best_key, best_iou = k, v
        aligned_words = r["align"]
        toks = tokens_of(ln["text"])
        words = []
        for wi, wd in enumerate(r["final_words"]):
            wbox = S.obox(wd, state["size"])
            gl = []
            wtxt = toks[wi] if aligned_words else None
            lets = letters_of(wtxt) if wtxt else None
            glyph_aligned = bool(lets) and len(wd) == len(lets)
            for gi, g in enumerate(wd):
                ge = {"box": S.obox([g], state["size"]), "ink_px": g["n"], "components": g["parts"]}
                if glyph_aligned:
                    ge["text"] = lets[gi]
                gl.append(ge)
            we = {"box": wbox, "glyphs": gl, "glyphs_aligned": glyph_aligned}
            if aligned_words:
                we["text"] = wtxt
            words.append(we)
        marks = [{"box": S.obox([g], state["size"]), "ink_px": g["n"]} for g in r["glyphs"] if g["mark"]]
        abox = author.get(best_key) if best_key else None
        dx1 = round(lbox[2] - abox[2], 1) if abox else None
        line = {"stanza": ln["stanza"], "line": ln["line"], "index": idx, "box": lbox,
                "rule_row": r["row"],
                "text": ln["text"],
                "text_basis": "row order (22 ink rows = 22 transcription lines) + overlap with author box",
                "author_box_expected_key": "%d-%d" % (ln["block"], ln["line"]) if exp else None,
                "author_box_best_key": "%d-%d" % best_key if best_key else None,
                "author_box_best_iou": round(best_iou, 3),
                "ink_x1_minus_author_x1": dx1,
                "words_alignment": aligned_words,
                "n_word_boxes_gap_rule": sx["boxes"], "n_tokens": sx["tokens"],
                "glyphs_total": sx["glyphs"], "letters_total": sx["letters"],
                "words": words, "marks": marks}
        out_st[ln["stanza"]]["lines"].append(line)

    def union(boxes):
        return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
    for st in out_st:
        st["box"] = union([l["box"] for l in st["lines"]])
    poem_box = union([st["box"] for st in out_st])
    flagged = [l["index"] for st in out_st for l in st["lines"]
               if l["ink_x1_minus_author_x1"] is not None and abs(l["ink_x1_minus_author_x1"]) > 25]
    meta = {
        "poem": PIECE_ID, "poem_box": poem_box,
        "edge_check": {"rule": "|ink x1 - author x1| > 25 px", "flagged_line_indices": flagged,
                       "note": "author boxes are loose and block 2 is keyed off by one; flags are for review, not errors"},
 "version_index": 0, "version_id": ver["id"],
        "source_page": {"id": PAGE_ID, "image": "site/img/p/%s.jpg" % PAGE_ID, "size": [state["size"][0], state["size"][1]]},
        "frame": "pixels of site/img/p/diary1.jpg, [x0,y0,x1,y1], x1/y1 exclusive, origin top-left; analysis runs in a sheared frame and is mapped back (about +-1 px)",
        "parameters": {
            "skew_slope_dy_per_dx": round(state["slope"], 5), "rule_period_px": round(state["period"], 2),
            "rules_found": len(state["rules"]), "ink_threshold_gray": state["thresh"],
            "threshold_method": "Otsu split of the sheared page histogram outside the rule bands",
            "x_height_px": round(xh, 1), "x_height_source": "median of field 7 of pages[].x (author line records) * ih",
            "gap_rule": rule_name(chosen), "gap_rule_chosen_by": "best word-line match on these same 22 lines (optimistic; not held out)",
            "speck_px": 8, "rule_residue": "components <=3 px tall centred on a rule are dropped",
            "mark_rule": "dot/period: area<=0.12*xh^2 and size<=0.5*xh; comma-like: area<=0.45*xh^2, centroid at/below the rule, w<=0.7*xh, h<=1.1*xh",
            "glyph_merge": "marks merge into a host they sit over/under; nested or near-touching (<=3 px) fragments merge",
            "row_assignment": "ink-mass centroid vs rule rows (band up to rule + 0.3*period)", },
        "counts": {"stanzas": len(stanzas), "lines": len(lines), "ink_rows": len(rows)},
        "match": summ,
        "viable": {
            "stanza": {"viable": True, "basis": "stanza = block order in j.json; setbacks need only line boxes"},
            "line": {"viable": True, "basis": "22 ink rows = 22 lines; line boxes from ink; some boxes are contaminated by neighbouring descenders"},
            "word": {"viable": True, "basis": "word boxes are usable crops; text is attached only on lines whose box count equals the token count and that passed eye review"},
            "glyph": {"viable": True, "basis": "ink-component crops are usable pictures; they are NOT letters (counts do not match)"},
            "word_part": {"viable": False, "basis": "letters cannot be honestly aligned to glyph boxes: whole-line letter/glyph counts match on 4 of 22 lines"}},
        "eye_review": {"withdrawn_lines": sorted(EYE_REVIEW_WITHDRAWN),
                       "reason": "box count equals token count but the word boxes hold the wrong ink; text withdrawn"},
        "sweep": sweep,
        "notes": ["glyph = ink component group, not a letter; letters are spaced widely and some join or split",
                  "marks (commas, periods, dots) are listed per line in 'marks' and never form words",
                  "text appears only where a count check passed; 'text_basis' documents the line-level mapping",
                  "match rates are optimistic: the gap rule and threshold were picked on these same 22 lines",
                  "author line boxes for block 2: keys 2-1 and 2-2 hold the boxes of lines 2 and 3; line 1 has none (see author_box_* fields)"],
    }
    doc = {"meta": meta, "poem": PIECE_ID, "box": poem_box, "stanzas": out_st}
    with open(a.out, "w") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
    print("rule", rule_name(chosen), "thresh", state["thresh"], json.dumps(summ))
    for ln in (l for s in out_st for l in s["lines"]):
        print("%2d %d-%d boxes=%d tokens=%d glyphs=%d letters=%d align=%s best=%s iou=%.2f exp=%s" % (
            ln["index"], ln["stanza"], ln["line"], ln["n_word_boxes_gap_rule"], ln["n_tokens"], ln["glyphs_total"],
            ln["letters_total"], ln["words_alignment"], ln["author_box_best_key"], ln["author_box_best_iou"],
            ln["author_box_expected_key"]))
    if a.overlay_dir:
        os.makedirs(a.overlay_dir, exist_ok=True)
        for i, r in enumerate(rows):
            rr = dict(r, words=r["final_words"])
            S.draw_overlay(ppath, rr, os.path.join(a.overlay_dir, "line%02d.png" % i))


if __name__ == "__main__":
    main(sys.argv[1:])
