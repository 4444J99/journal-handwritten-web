#!/usr/bin/env python3
"""Build a tiny synthetic CFF font and write it to stdout (WOFF2, or TTF/OTF with --flavor).

Test helper: run with the font venv python (fontTools + brotli). Its name table, CFF names and
copyright carry NAME on both the Macintosh and the Windows platform, so the rename and the search can
be tested without the real font. Glyph outlines are plain boxes of different widths.

    make_test_font.py NAME [--flavor woff2|woff|none]
"""
import argparse, io, sys

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen


def build(name, flavor):
    ps = name.replace(" ", "") + "-Regular"
    order = [".notdef", "space", "A", "B", "C", "a.alt1"]
    cmap = {32: "space", 65: "A", 66: "B", 67: "C"}
    widths = {".notdef": 500, "space": 300, "A": 610, "B": 640, "C": 580, "a.alt1": 555}
    fb = FontBuilder(1000, isTTF=False)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    strings = {}
    for g in order:
        pen = T2CharStringPen(widths[g], None)
        if g not in ("space",):
            w = widths[g]
            pen.moveTo((50, 0)); pen.lineTo((50, 600)); pen.lineTo((w - 50, 600)); pen.lineTo((w - 50, 0)); pen.closePath()
        strings[g] = pen.getCharString()
    fb.setupCFF(ps, {"FullName": name + " Regular", "FamilyName": name, "Notice": "(c) test " + name}, strings, {})
    fb.setupHorizontalMetrics({g: (widths[g], 50) for g in order})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": name, "styleName": "Regular", "uniqueFontIdentifier": ps + "-1.0",
                       "fullName": name + " Regular", "psName": ps, "version": "Version 1.000",
                       "copyright": "Test font by nobody (" + name + ")"}, mac=True)
    fb.setupOS2(sTypoAscender=800, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    if flavor != "none":
        fb.font.flavor = flavor
    buf = io.BytesIO()
    fb.save(buf)
    return buf.getvalue()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--flavor", default="woff2", choices=("woff2", "woff", "none"))
    a = ap.parse_args()
    sys.stdout.buffer.write(build(a.name, a.flavor))
