#!/usr/bin/env python3
"""Rename the embedded handwriting font for the public build, and search a font for a name.

Needs fontTools and brotli, so it is NOT run with the system python3: tools/build_public.py and
tools/post_poem.py start it as a subprocess with the python of the font venv
(environment variable VERSFORMS_FONT_PYTHON, default
/Volumes/Archive4T/Runtime/tools/venvs/versforms-font/bin/python). Font bytes arrive on stdin and
one JSON document leaves on stdout; nothing is written to disk.

    font_rename.py check                      search the font for the old name
    font_rename.py rename --family F --full N --postscript P
                                              rename it, re-encode (same container), search again
    font_rename.py describe                   glyph count, cmap, advance widths, table list

What "the old name" covers (case-insensitive, with the letters as ASCII, UTF-16 big endian, UTF-16
little endian, and as Mac Roman, which is ASCII for these letters):
  - every record of the 'name' table, on every platform and in every language, decoded and raw,
  - the CFF font name list and the CFF top dictionary strings (FullName, FamilyName, Notice, ...),
  - glyph names,
  - the WOFF2 metadata and private blocks,
  - the raw bytes of every table of the decompressed font (the final search, after re-encoding).

rename sets nameID 1, 16 and 21 to the family, 4 and 18 to the full name, 6 to the PostScript name on
every record, and rewrites every other record or CFF string that carries the old name; the CFF font
name becomes the PostScript name and the CFF FullName / FamilyName follow. Outlines, cmap and metrics
are not touched.
"""
import argparse, base64, io, json, re, sys

OLD = "etceter" + "4"  # the old name, built from parts so this file is not itself a search hit
OLD_RE = re.compile(OLD, re.I)
FORMS = [OLD.encode("ascii"), OLD.encode("utf-16-be"), OLD.encode("utf-16-le")]


def raw_hit(data):
    low = bytes(data).lower()
    return any(f in low for f in FORMS)


def text_hit(s):
    return bool(OLD_RE.search(s)) if isinstance(s, str) else raw_hit(s)


def rewrite(s, family, full, ps):
    """Replace the old name inside a string that is not one of the explicitly named fields."""
    s = re.sub(OLD + r"diary-regular", lambda m: ps, s, flags=re.I)
    s = re.sub(OLD + r"[ _]diary[ _]regular", lambda m: full, s, flags=re.I)
    s = re.sub(OLD + r"[ _-]?diary", lambda m: family, s, flags=re.I)
    return OLD_RE.sub(lambda m: family, s)


def load(data):
    from fontTools.ttLib import TTFont
    return TTFont(io.BytesIO(data))


def scan(font, raw=True):
    """-> list of short location strings where the old name occurs (never the text around it)."""
    hits = []
    for rec in font["name"].names:
        where = f"name id{rec.nameID} platform{rec.platformID}/{rec.platEncID}/{rec.langID}"
        try:
            decoded = rec.toUnicode()
        except Exception:
            decoded = ""
        if text_hit(decoded) or raw_hit(rec.string if isinstance(rec.string, (bytes, bytearray)) else str(rec.string).encode("utf-16-be")):
            hits.append(where)
    if "CFF " in font:
        cff = font["CFF "].cff
        if any(text_hit(str(n)) for n in cff.fontNames):
            hits.append("CFF font name")
        for i, top in enumerate(cff.topDictIndex):
            for key in ("FullName", "FamilyName", "Notice", "Copyright", "version", "Weight", "PostScript", "BaseFontName"):
                v = getattr(top, key, None)
                if isinstance(v, str) and text_hit(v):
                    hits.append(f"CFF top dict {key}")
        for s in cff.strings.strings if hasattr(cff.strings, "strings") else []:
            if text_hit(str(s)):
                hits.append("CFF string index")
                break
    for g in font.getGlyphOrder():
        if text_hit(g):
            hits.append("glyph name " + str(font.getGlyphID(g)))
    fd = getattr(font, "flavorData", None)
    for attr in ("metaData", "privData"):
        blob = getattr(fd, attr, None) if fd else None
        if blob and raw_hit(blob):
            hits.append("woff2 " + attr)
    if raw:
        for tag in font.reader.keys():
            if raw_hit(font.reader[tag]):
                hits.append(f"raw table {tag!r}")
    return hits


def do_rename(data, family, full, ps):
    from fontTools.ttLib import TTFont
    font = load(data)
    flavor = font.flavor
    before = scan(font)
    changed = 0
    name = font["name"]
    explicit = {1: family, 16: family, 21: family, 4: full, 18: full, 6: ps}
    for rec in list(name.names):
        old = rec.toUnicode()
        if rec.nameID in explicit:
            new = explicit[rec.nameID]
        else:
            new = rewrite(old, family, full, ps)
        if new != old:
            name.setName(new, rec.nameID, rec.platformID, rec.platEncID, rec.langID)
            changed += 1
    if "CFF " in font:
        cff = font["CFF "].cff
        cff.fontNames = [ps for _ in cff.fontNames]
        changed += 1
        for top in cff.topDictIndex:
            top.FullName = full
            if getattr(top, "FamilyName", None) is not None:
                top.FamilyName = family
            for key in ("Notice", "Copyright", "version", "Weight", "PostScript", "BaseFontName"):
                v = getattr(top, key, None)
                if isinstance(v, str) and text_hit(v):
                    setattr(top, key, rewrite(v, family, full, ps))
                    changed += 1
    fd = getattr(font, "flavorData", None)
    for attr in ("metaData", "privData"):
        blob = getattr(fd, attr, None) if fd else None
        if blob and raw_hit(blob):
            text = bytes(blob).decode("utf-8", "ignore")
            setattr(fd, attr, rewrite(text, family, full, ps).encode("utf-8"))
            changed += 1
    out = io.BytesIO()
    font.flavor = flavor
    font.save(out)
    result = out.getvalue()
    after_font = load(result)
    after = scan(after_font)
    return result, dict(changed=changed, before=len(before), hits_after=after, flavor=flavor,
                        glyphs=len(after_font.getGlyphOrder()), bytes_in=len(data), bytes_out=len(result))


def describe(data):
    font = load(data)
    names = {}
    for rec in font["name"].names:
        names[f"{rec.nameID}/{rec.platformID}/{rec.platEncID}/{rec.langID}"] = rec.toUnicode()
    cff_names = [str(n) for n in font["CFF "].cff.fontNames] if "CFF " in font else []
    return dict(flavor=font.flavor, glyph_count=len(font.getGlyphOrder()), glyph_order=font.getGlyphOrder(),
                cmap={str(k): v for k, v in sorted(font.getBestCmap().items())},
                hmtx={g: list(m) for g, m in font["hmtx"].metrics.items()},
                tables=sorted(font.reader.keys()), name_records=names, cff_font_names=cff_names)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=("check", "rename", "describe"))
    ap.add_argument("--family")
    ap.add_argument("--full")
    ap.add_argument("--postscript")
    a = ap.parse_args(argv)
    data = sys.stdin.buffer.read()
    try:
        if a.mode == "check":
            font = load(data)
            hits = scan(font)
            doc = dict(ok=not hits, hits=hits, glyphs=len(font.getGlyphOrder()), flavor=font.flavor)
        elif a.mode == "describe":
            doc = describe(data)
        else:
            if not (a.family and a.full and a.postscript):
                ap.error("rename needs --family, --full and --postscript")
            out, info = do_rename(data, a.family, a.full, a.postscript)
            doc = dict(info, font_b64=base64.b64encode(out).decode("ascii"))
    except Exception as e:  # report, never a traceback that could carry font strings
        sys.stdout.write(json.dumps(dict(error=f"{type(e).__name__}: {e}"[:300])))
        return 1
    sys.stdout.write(json.dumps(doc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
