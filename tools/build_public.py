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
  - renumbers the piece links of published blocks to the published piece list,
  - sets the page title to "versforms" and renames the handwriting font family to
    "ajp-scribbles" in index.html (CSS, canvas font strings, the font-load call, visible text)
    and, through tools/font_rename.py run with the font venv python, inside the embedded
    WOFF2 itself (name table and CFF strings). site/index.html in the source tree is not edited.

An empty release list builds the engine with no pages.

tools/post_poem.py imports build() from here to publish a single poem (final version only,
with the author's corrections applied).
"""
import argparse, base64, json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

NOINDEX_META = '<meta name="robots" content="noindex">'
HEADERS = "/*\n  X-Robots-Tag: noindex\n"
PUBLIC_TITLE = "versforms"
PUBLIC_FONT_FAMILY = "ajp-scribbles"
PUBLIC_FONT_FULL = PUBLIC_FONT_FAMILY + " Regular"
PUBLIC_FONT_PS = PUBLIC_FONT_FAMILY + "-Regular"
# the name the source font carries; built from parts so this file is not itself a search hit
OLD_NAME = "etceter" + "4"
OLD_NAME_RE = re.compile(OLD_NAME, re.I)
OLD_FONT_RE = re.compile(OLD_NAME + r"[\s_-]*diary", re.I)
FONT_PYTHON_DEFAULT = "/Volumes/Archive4T/Runtime/tools/venvs/versforms-font/bin/python"
FONT_TOOL = Path(__file__).resolve().parent / "font_rename.py"
DATA_URI_RE = re.compile(r"data:([a-z0-9/+.-]+);base64,([A-Za-z0-9+/=]+)", re.I)
FONT_MAGIC = (b"wOF2", b"wOFF", b"OTTO", b"\x00\x01\x00\x00", b"true", b"ttcf")
PROV_KEEP = ("tdate", "verified")  # prov.repo / commit / path name the source repository and stay private


def filter_reader_metadata(html, pages, published):
    """Restrict template navigation metadata to exact published page/block membership.

    A revision witness is indivisible: a missing page or block removes that
    witness. A comparison needs at least two complete witnesses. This never
    converts an omitted version into a different available version.
    """
    by_id = {p["id"]: p for p in pages}
    allowed = {}
    for page, block in published:
        allowed.setdefault(page, set()).add(block)

    def literal(name):
        match = re.search(r"\bconst\s+" + name + r"\s*=\s*(\[[\s\S]*?\]);", html)
        if not match:
            return None, None
        # These two source constants contain only JSON values and bare object
        # keys. Refuse a changed grammar instead of evaluating JavaScript.
        value = re.sub(r'([,{]\s*)([A-Za-z_]\w*)\s*:', r'\1"\2":', match.group(1))
        try:
            return match, json.loads(value)
        except ValueError as exc:
            raise ValueError("Unsupported reader metadata literal: " + name) from exc

    def complete_member(member):
        if not isinstance(member, list) or len(member) != 2:
            return False
        page, blocks = member
        if page not in by_id or page not in allowed:
            return False
        if blocks == "all":
            blocks = list(range(len(by_id[page]["B"])))
        return (isinstance(blocks, list) and bool(blocks)
                and all(type(b) is int and b in allowed[page] for b in blocks))

    match, values = literal("PAL")
    if match:
        kept = []
        for value in values:
            if not isinstance(value, dict) or set(value) != {"id", "witnesses"}:
                raise ValueError("Unsupported PAL witness schema")
            witnesses = [w for w in value["witnesses"] if isinstance(w, list) and w
                         and all(complete_member(m) for m in w)]
            if len(witnesses) >= 2:
                kept.append({"id": value["id"], "witnesses": witnesses})
        html = html[:match.start(1)] + json.dumps(kept, separators=(",", ":")) + html[match.end(1):]
    match, values = literal("HF")
    if match:
        kept = [page for page in values if isinstance(page, str)
                and page in by_id and complete_member([page, "all"])]
        html = html[:match.start(1)] + json.dumps(kept, separators=(",", ":")) + html[match.end(1):]
    return html

SHELL = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>versforms</title>
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


def rebrand(html):
    """Public-site identity for index.html: the title element is exactly "versforms", and the
    handwriting font family (any spelling of the old name followed by "Diary", any letter case,
    quoted or not, in CSS, custom properties, canvas font strings, document.fonts calls and visible
    text) becomes "ajp-scribbles". Embedded font bytes are handled by rename_embedded_fonts()."""
    if not re.search(r"<title>.*?</title>", html, re.S | re.I):
        raise ValueError("index.html has no <title> element")
    html = re.sub(r"<title>.*?</title>", lambda m: f"<title>{PUBLIC_TITLE}</title>", html, count=1, flags=re.S | re.I)
    return OLD_FONT_RE.sub(lambda m: PUBLIC_FONT_FAMILY, html)


class FontToolError(Exception):
    """The font step cannot run (no venv python, fontTools or brotli missing) or the tool failed."""


class FontDecodeError(FontToolError):
    """The font tool ran but could not read these bytes as a font."""


def font_python():
    return os.environ.get("VERSFORMS_FONT_PYTHON") or FONT_PYTHON_DEFAULT


def run_font_tool(mode, data, *args):
    """Run tools/font_rename.py MODE with the venv python; font bytes in, parsed JSON out."""
    py = font_python()
    if not (os.path.isfile(py) and os.access(py, os.X_OK)):
        raise FontToolError(f"font python not found: {py} (set VERSFORMS_FONT_PYTHON to a python with fontTools and brotli)")
    try:
        r = subprocess.run([py, str(FONT_TOOL), mode, *args], input=data, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        # the tool ran and did not answer: nothing vouches for the font, which is a hard stop, not "cannot run here"
        raise FontDecodeError("font tool timed out after 120 s")
    except (OSError, subprocess.SubprocessError) as e:
        raise FontToolError(f"font tool could not run: {e}")
    try:
        doc = json.loads(r.stdout.decode("utf-8", "replace") or "null")
    except ValueError:
        doc = None
    if r.returncode != 0 or not isinstance(doc, dict) or "error" in doc:
        err = doc.get("error") if isinstance(doc, dict) else None
        if not err:
            err = r.stderr.decode("utf-8", "replace").strip().splitlines()[-1:] or ["no output"]
            err = err[0]
        if "No module named" in err or "ModuleNotFoundError" in err:
            raise FontToolError(f"{py} lacks fontTools or brotli: {err[:200]}")
        raise FontDecodeError(f"font tool failed: {err[:200]}")
    return doc


def is_font(mime, raw):
    return mime.lower().startswith("font/") or "font" in mime.lower() or raw[:4] in FONT_MAGIC


def rename_embedded_fonts(html):
    """Rename every embedded font that carries the old name; -> (html, [one report dict per font]).

    Raises FontToolError when there is such a font and the venv python cannot be used. Fonts that
    cannot be parsed are reported with error and left alone (the output check then decides)."""
    reports = []

    def one(m):
        mime, b64 = m.group(1), m.group(2)
        try:
            raw = base64.b64decode(b64, validate=True)
        except ValueError:
            return m.group(0)
        if not is_font(mime, raw):
            return m.group(0)
        try:
            info = run_font_tool("check", raw)
        except FontDecodeError as e:
            reports.append(dict(mime=mime, bytes=len(raw), error=str(e)))
            return m.group(0)
        needs_scrub = info.get("needs_public_scrub", False)
        if info.get("ok") and not needs_scrub:
            reports.append(dict(mime=mime, bytes=len(raw), renamed=False))
            return m.group(0)
        doc = run_font_tool("rename", raw, "--family", PUBLIC_FONT_FAMILY, "--full", PUBLIC_FONT_FULL, "--postscript", PUBLIC_FONT_PS, "--strip-journal-metadata")
        new = base64.b64decode(doc["font_b64"])
        reports.append(dict(mime=mime, bytes=len(raw), renamed=True, bytes_out=len(new), changed=doc["changed"], hits_after=doc["hits_after"], glyphs=doc["glyphs"]))
        return f"data:{mime};base64,{doc['font_b64']}"

    return DATA_URI_RE.sub(one, html), reports


def remove_public_transcription_status(html):
    """Omit the global review claim; publication uses the per-line verified gate."""
    html = re.sub(r'^\s*`Machine transcription \(.*?`,\s*\n', '', html, flags=re.M)
    if "Machine transcription (" in html or "not yet checked" in html:
        raise ValueError("Unsupported public transcription status template")
    return html


def load_release(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else {"pieces": []}


def build(out, want, site=SITE, select=None, corrections=None, strip_prov=True, rename_fonts=True, source_data=None, publication_source=None, publication_db=None, target="production", photo_assets=None):
    """Write the public site for the pieces in `want` into `out`; returns a summary dict.

    select       {piece id: [indices into the piece's V]} versions to publish; default all
    corrections  {(page id, block, line): text} replaces machine readings in published blocks
    strip_prov   drop prov.repo / commit / path from data/j.json
    rename_fonts rename the embedded font file (needs the font venv); when it cannot run, the
                 summary says so under "font_error" and the font bytes stay as they are
    """
    out, site = Path(out), Path(site)
    want = list(dict.fromkeys(want))
    select, corrections = select or {}, dict(corrections or {})
    d = json.loads(json.dumps(source_data)) if source_data is not None else json.loads((site / "data" / "j.json").read_text())
    pieces = {p["id"]: p for p in d["pieces"]}
    missing = [k for k in want if k not in pieces]
    if missing:
        sys.exit(f"unknown piece ids in release list: {missing}")

    # versions published, per piece (indices into V)
    chosen = {}
    source_pages = {page["id"]: page for page in d["pages"]}
    for k in want:
        n = len(pieces[k]["V"])
        sel = list(range(n)) if select.get(k) is None else sorted(set(select[k]))
        if not sel or any(not 0 <= i < n for i in sel):
            sys.exit(f"bad version selection for {k}: {sel}")
        for vi in sel:
            version = pieces[k]["V"][vi]
            if version.get('render'):
                if not isinstance(version.get('compositeEvidence'), dict):
                    raise ValueError('derived version requires authoritative evidence')
                from variorum_publication import check_composite
                if publication_source is None or publication_db is None:
                    raise ValueError('composite publication requires captured source and database')
                check_composite(version, publication_source, publication_db, target)
            if version.get("sourceStatus") == "staged-untranscribed":
                sys.exit(f"selected version {version['id']} is staged-untranscribed; output unchanged")
            for page_id, blocks in version["P"]:
                page = source_pages[page_id]
                if (page.get("sourceStatus") == "staged-untranscribed"
                        or not isinstance(page.get("a"), list) or len(page["a"]) != 5
                        or any(page["B"][bi].get("transcriptionStatus") == "untranscribed" for bi in blocks)):
                    sys.exit(f"selected source {page_id} is untranscribed or has no verified atlas; output unchanged")
            if vi not in pieces[k]["st"]:
                sys.exit(f"selected version {version['id']} has no established reading order; output unchanged")
        chosen[k] = sel

    # Refuse a broken module closure before replacing a previous output. The
    # package verifier is loaded by the feature adapter, not directly by HTML.
    reader_assets = ("reader-features.js", "reader-packages.js")
    if want:
        reader_text = (site / "index.html").read_text(encoding="utf-8")
        for asset in reader_assets:
            if (site / asset).is_file():
                reader_text += "\n" + (site / asset).read_text(encoding="utf-8")
        for asset in reader_assets:
            if asset in reader_text and not (site / asset).is_file():
                raise FileNotFoundError("Reader module is referenced but missing: " + asset)

    # published pieces with the chosen versions renumbered; owner[(page, block)] = (piece index, version, rank)
    keep, owner, out_pieces = {}, {}, []
    for npi, k in enumerate(want):
        pc, sel = pieces[k], chosen[k]
        newv = {old: new for new, old in enumerate(sel)}
        st = [newv[i] for i in pc["st"] if i in newv]
        top = newv[pc["top"]] if pc["top"] in newv else st[0]
        from variorum_publication import public_version, project_public_variorum
        projected = dict(pc, V=[public_version(pc["V"][i]) for i in sel], st=st, top=top)
        if pc.get('variorum'):
            projected['variorum'] = project_public_variorum(pc['variorum'], [pc['V'][i] for i in sel])
        out_pieces.append(projected)
        for old in sel:
            for pg, blocks in pc["V"][old]["P"]:
                keep.setdefault(pg, set()).update(blocks)
                for b in blocks:
                    owner[(pg, b)] = (npi, newv[old], st.index(newv[old]))
    pages = [p for p in d["pages"] if p["id"] in keep]

    # Resolve current accepted readings before creating any output. Explicit
    # corrections still win; preserved raw lines are never changed in place.
    effective_lines, version_lines = {}, {}
    for p in pages:
        selected_blocks = keep[p["id"]]
        for bi in selected_blocks:
            block = p["B"][bi]
            for li, original in enumerate(block["L"]):
                line_id = block.get("lineIds", [])[li] if "lineIds" in block else f"{p['id']}-{bi}-{li}"
                key = (p["id"], bi, li)
                if block.get("t") != 4:
                    if key not in corrections and line_id in d.get("acceptedReadings", {}):
                        corrections[key] = d["acceptedReadings"][line_id]
                    if key in corrections:
                        if not isinstance(corrections[key], str):
                            sys.exit(f"nontext correction for {line_id}; output unchanged")
                        effective_lines[line_id] = corrections[key]
                for k, selected in chosen.items():
                    for vi in selected:
                        version = pieces[k]["V"][vi]
                        if any(pg == p["id"] and bi in bs for pg, bs in version["P"]):
                            version_lines.setdefault((k, version["id"]), set()).add(line_id)
    unknown_corrections = set(corrections) - {
        (p["id"], bi, li) for p in pages for bi in keep[p["id"]]
        for li in range(len(p["B"][bi]["L"]))}
    if unknown_corrections:
        sys.exit(f"corrections for lines outside the published blocks: {sorted(unknown_corrections)[:5]}")

    # Generate current v2 bindings from preserved studio originals and the exact
    # output readings. Never copy a caller-supplied digest or a withheld version.
    bindings = {}
    if (site.parent / "studio/data/review.json").is_file():
        from script_realizations import source_snapshot
        from source_fingerprint import source_binding
        for (piece_id, version_id), line_ids in version_lines.items():
            snapshot = source_snapshot(site.parent, piece_id, version_id,
                correction_values={lid: value for lid, value in effective_lines.items() if lid in line_ids})
            bindings[f"{piece_id}/{version_id}"] = source_binding(snapshot)

    from variorum_publication import fingerprint
    for piece_id, selected in chosen.items():
        for vi in selected:
            v = pieces[piece_id]['V'][vi]
            if not v.get('render'):
                continue
            bindings[f"{piece_id}/{v['id']}"] = {'pieceId': piece_id, 'versionId': v['id'],
                'sourceFingerprint': fingerprint(piece_id, v['id'], [], [{**l, 'blockType': 'text'} for l in v['lines']])}

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

    prepared_photos = {}
    for piece_id, selected in chosen.items():
        for vi in selected:
            v = pieces[piece_id]['V'][vi]
            if v.get('render') == 'photo':
                photo = v['compositeEvidence']['photo']
                supplied = (photo_assets or {}).get(photo['assetId'])
                if supplied is None:
                    raise ValueError('missing composite photo bytes')
                data = Path(supplied).read_bytes() if isinstance(supplied, (str, Path)) else bytes(supplied)
                import hashlib
                if len(data) != photo['size'] or hashlib.sha256(data).hexdigest() != photo['sha256']:
                    raise ValueError('composite photo byte mismatch')
                prepared_photos[v['id']] = data
    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)

    atlas, applied = [], 0
    if pages:
        from PIL import Image
        pos, size = pack([(p["id"], p["a"][3], p["a"][4]) for p in pages])
        for kind in ("t", "k"):
            im = Image.new("RGB", size, "white")
            for p in pages:
                n, x, y, w, h = p["a"]
                with Image.open(site / "img" / "a" / f"{kind}{n}.jpg") as original:
                    im.paste(original.crop((x, y, x + w, y + h)), pos[p["id"]])
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
                    # not published: no text, no number of lines, no link to a piece or version, no reading note
                    b["L"] = []
                    for key in ("g", "v", "u", "lineIds", "transcriptionStatus", "sourceAnchor"):
                        b.pop(key, None)
                    continue
                if b.get("g"):
                    b["g"] = [own[0], own[2]] + list(b["g"][2:])
                if "v" in b:
                    b["v"] = own[1]
                for li in range(len(b["L"])):
                    text = corrections.pop((p["id"], bi, li), None)
                    if b.get("t") == 4:
                        continue  # a quotation block stays as it is (withheld); a correction on it is dropped, never published
                    if text is not None:
                        b["L"][li] = text
                        applied += 1
            p["u"] = []
            # per-line boxes of unpublished blocks are geometry of lines that are not published: keep only the published blocks'
            p["x"] = [e for e in p.get("x", []) if (p["id"], e[0]) in owner]
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
    for version_id, data in prepared_photos.items():
        dest = out / 'img/p' / (version_id + '.jpg')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
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
    if bindings:
        pub["sourceBindings"] = bindings
    selected_line_ids = set().union(*version_lines.values()) if version_lines else set()
    unavailable = {lid: {"status": "unavailable"} for lid, anchor in d.get("sourceAnchors", {}).items()
                   if lid in selected_line_ids and anchor.get("status") == "unavailable"}
    if unavailable:
        pub["sourceAnchors"] = unavailable
    (out / "data" / "j.json").write_text(json.dumps(pub, ensure_ascii=False, separators=(",", ":")))

    fonts, font_error = [], None
    if want:
        html = rebrand((site / "index.html").read_text(encoding="utf-8"))
        html = filter_reader_metadata(html, d["pages"], owner)
        html = remove_public_transcription_status(html)
        for asset in reader_assets:
            if (site / asset).is_file():
                shutil.copy2(site / asset, out / asset)
            elif asset in html:
                raise FileNotFoundError("Reader module is referenced but missing: " + asset)
        if rename_fonts:
            try:
                html, fonts = rename_embedded_fonts(html)
            except FontToolError as e:
                font_error = str(e)
        (out / "index.html").write_text(add_noindex(html), encoding="utf-8")
        (out / "_headers").write_text(HEADERS)
    else:
        # the engine needs at least one page; until poem 1 posts, serve blank paper only
        shutil.rmtree(out / "data")
        (out / "index.html").write_text(SHELL)
        (out / "_headers").write_text(HEADERS)

    return {"want": want, "pages": [p["id"] for p in pages], "shared": shared, "siblings": siblings,
            "applied": applied, "published": sorted(owner), "chosen": chosen, "fonts": fonts, "font_error": font_error}


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
    if res["font_error"]:
        print(f"  WARNING: the embedded font was not renamed: {res['font_error']}")
        print("  The output still carries the old font name inside the embedded font; do not publish it. Install the font venv (VERSFORMS_FONT_PYTHON) and run again.")
        sys.exit(3)


if __name__ == "__main__":
    main()
