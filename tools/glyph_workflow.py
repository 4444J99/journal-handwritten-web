#!/usr/bin/env python3
"""Private, provenance-preserving glyph capture utilities (no font generation).

This is deliberately separate from the publication pipeline. A capture sheet is
an empty author worksheet; a crop label is a declaration, never OCR inference.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import unicodedata

SCHEMA_VERSION = 1
MAX_BYTES = 16 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_GLYPHS = 1024
FORBIDDEN_OUTPUT_PARTS = {"site", "studio", "release", "releases", "dist", "public"}
ID_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
SCRIPT_RE = re.compile(r"[A-Z][a-z]{3}\Z")
LANGUAGE_RE = re.compile(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*\Z")


class ValidationError(ValueError):
    """A manifest or asset failed validation; no import was written."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _no_symlinks(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    for parent in [absolute, *absolute.parents]:
        if parent.is_symlink():
            raise ValidationError("symlinks are not allowed")


def _read(path: Path) -> bytes:
    _no_symlinks(path)
    if not path.is_file():
        raise ValidationError("source must be a regular file")
    if path.stat().st_size > MAX_BYTES:
        raise ValidationError("source exceeds 16 MiB")
    with path.open("rb") as handle:
        data = handle.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValidationError("source exceeds 16 MiB")
    return data


def _record(path: Path) -> dict:
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValidationError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValidationError("nonfinite JSON numbers are not allowed")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValidationError("nonfinite JSON numbers are not allowed")
        return number

    try:
        value = json.loads(_read(path).decode("utf-8"), object_pairs_hook=object_pairs,
                           parse_constant=reject_constant, parse_float=finite_float)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError("manifest must be UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValidationError("manifest must be an object")
    return value


def _string(value, name: str, limit: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValidationError(f"{name} must be a nonempty string (at most {limit} characters)")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValidationError(f"{name} contains a non-scalar surrogate")
    return value


def _identifier(value, name: str) -> str:
    value = _string(value, name, 80)
    if not ID_RE.fullmatch(value) or value in {".", ".."}:
        raise ValidationError(f"invalid {name}")
    return value


def _sha_value(value, name: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ValidationError(f"{name} must be lowercase SHA-256")
    return value


def _language_script(language: str, script: str, direction: str) -> None:
    if not isinstance(language, str) or not LANGUAGE_RE.fullmatch(language):
        raise ValidationError("language must have supported language-tag syntax (registry validity is not checked)")
    if not isinstance(script, str) or not SCRIPT_RE.fullmatch(script):
        raise ValidationError("script must have four-letter ISO 15924 code syntax (registry validity is not checked)")
    if direction not in {"ltr", "rtl"}:
        raise ValidationError("direction must be ltr or rtl")


def _provenance(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValidationError("provenance must be an object")
    # This derivative workflow does not override the source's publication state.
    # It does not govern separate private backups or preservation workflows.
    source = value.get("source")
    authorship = value.get("authorship")
    if not isinstance(source, dict) or not isinstance(authorship, dict):
        raise ValidationError("source and authorship declarations are required")
    if value.get("visibility") != "private":
        raise ValidationError("only private output is supported; withheld assets are excluded")
    if source.get("visibility") not in {"public", "private"}:
        raise ValidationError("withheld or unknown source visibility is excluded")
    collection = _string(source.get("collection"), "source.collection", 80)
    if collection not in {"series", "reserve", "archive", "unsorted"}:
        raise ValidationError("source.collection must be series, reserve, archive or unsorted (exact spelling)")
    if collection in {"reserve", "archive"}:
        raise ValidationError("Reserve and Archive source material is excluded from derivative previews")
    for key in ("piece_id", "version_id", "locator"):
        _string(source.get(key), f"source.{key}")
    _sha_value(source.get("sha256"), "source.sha256")
    for key in ("actor", "evidence", "role"):
        _string(authorship.get(key), f"authorship.{key}")
    # Return only understood fields, rather than propagating arbitrary paths or
    # hidden source text from a caller's manifest into generated preview files.
    return {
        "visibility": "private",
        "source": {key: source[key] for key in ("piece_id", "version_id", "sha256", "visibility", "collection", "locator")},
        "authorship": {key: authorship[key] for key in ("actor", "role", "evidence")},
    }


def verify_source(provenance: dict, repo, db) -> dict:
    """Bind a declaration to the current exact version and canonical export policy.

    Low-level derivative APIs require caller-verified provenance. The CLI always
    calls this guard against an explicitly selected studio export before writes.
    The successful return value is the checked, understood provenance fields.
    """
    import script_realizations as realizations
    import post_poem

    checked = _provenance(provenance)
    if db is None:
        raise ValidationError("an explicit studio export is required to verify the source")
    repo, db = Path(repo), Path(db)
    _no_symlinks(repo)
    _no_symlinks(db)
    source = checked["source"]
    try:
        policy = realizations.release_policy(repo, source["piece_id"], db)
    except (realizations.Invalid, post_poem.Stop, OSError, KeyError, TypeError, ValueError) as exc:
        raise ValidationError("source policy cannot be resolved from repository/export") from exc
    if policy["pool"] in {"reserve", "archive"} or policy["visibility"] == "withheld":
        raise ValidationError("actual source is Reserve, Archive or withheld; derivative output is excluded")
    if source["collection"] != policy["pool"] or source["visibility"] != policy["visibility"]:
        raise ValidationError("declared source collection/visibility differs from actual canonical export policy")
    try:
        snapshot = realizations.source_snapshot(repo, source["piece_id"], source["version_id"], db)
    except (realizations.Invalid, post_poem.Stop, OSError, KeyError, TypeError, ValueError) as exc:
        raise ValidationError("exact source version cannot be resolved from repository/export") from exc
    if snapshot["versionFingerprint"] != "sha256:" + source["sha256"]:
        raise ValidationError("declared source fingerprint is stale or differs from the current exact version")
    return checked


def _destination(path: Path) -> Path:
    _no_symlinks(path)
    absolute = Path(os.path.abspath(path))
    if any(part.casefold() in FORBIDDEN_OUTPUT_PARTS for part in absolute.parts):
        raise ValidationError("output may not be inside site, studio, release, dist or public directories")
    if path.exists():
        raise ValidationError("destination already exists; choose a new private destination")
    return absolute


def _commit_directory(out_dir: Path, writer) -> None:
    # Validation happens before this function. The staging directory sits on the
    # same filesystem, so rename produces a complete bundle in one operation.
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".glyph-stage-", dir=out_dir.parent))
    try:
        writer(staging)
        staging.rename(out_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def scalar_label(sequence: str) -> str:
    return " ".join(f"U+{ord(char):04X}" for char in sequence)


def _sequence(sequence) -> str:
    sequence = _string(sequence, "glyph.sequence", 32)
    if any(unicodedata.category(char) in {"Cc", "Cs", "Cf", "Zl", "Zp"} for char in sequence):
        raise ValidationError("glyph.sequence contains a control or directional-format character")
    return sequence


def _sheet_sequences(text: str) -> list[str]:
    """Base-plus-combining slots, not a universal grapheme/shaping segmenter."""
    if not isinstance(text, str) or len(text) > 100_000:
        raise ValidationError("text must be a string of at most 100000 characters")
    sequences: list[str] = []
    previous_is_base = False
    for char in text:
        category = unicodedata.category(char)
        if 0xD800 <= ord(char) <= 0xDFFF:
            raise ValidationError("text contains a non-scalar surrogate")
        if char in "\n\r\t " or char == "\u00a0":
            previous_is_base = False
            continue
        if category in {"Cc", "Cf", "Zl", "Zp"}:
            raise ValidationError("worksheet text contains unsupported control characters")
        if category.startswith("M"):
            if not previous_is_base:
                raise ValidationError("worksheet contains an orphan combining mark; supply explicit capture sequence labels")
            sequences[-1] += char
            if len(sequences[-1]) > 32:
                raise ValidationError("worksheet sequence exceeds 32 scalars")
        else:
            sequences.append(char)
            previous_is_base = True
    unique = list(dict.fromkeys(sequences))
    if not unique or len(unique) > MAX_GLYPHS:
        raise ValidationError("worksheet requires 1–1024 distinct sequences")
    return unique


def _escape(value) -> str:
    return html.escape(str(value), quote=True)


CSS = """
@page { size: A4; margin: 12mm; }
* { box-sizing: border-box; }
body { color: #17202a; background: #fff; margin: 24px auto; max-width: 980px; padding: 0 18px; font: 15px/1.5 sans-serif; }
h1 { font-size: 26px; line-height: 1.15; } h2 { font-size: 18px; }
.notice { border: 2px solid #354b64; padding: 10px 14px; margin: 16px 0; }
.meta { overflow-wrap: anywhere; } code { font-size: 12px; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; }
th,td { border: 1px solid #bac1c9; padding: 8px; vertical-align: top; }
tr { break-inside: avoid; } th { text-align: left; background: #eef1f4; }
.glyph-label { font: 25px/1.2 serif; unicode-bidi: isolate; overflow-wrap: anywhere; }
.slot { height: 80px; background: linear-gradient(to bottom, transparent 19px, #ddd 20px, transparent 21px, transparent 49px, #7f8d9c 50px, transparent 51px, transparent 65px, #ddd 66px, transparent 67px); }
.caption { font-size: 12px; overflow-wrap: anywhere; }
.crop { max-width: 100%; max-height: 120px; image-rendering: auto; }
.specimen { white-space: pre-wrap; overflow-wrap: anywhere; font: 32px/1.8 ajp-scribbles, serif; unicode-bidi: plaintext; }
@media print { body { margin: 0; max-width: none; padding: 0; font-size: 10pt; } .notice { font-size: 10pt; } thead { display: table-header-group; } }
"""


def _page(title: str, body: str, language="en", extra_css="") -> str:
    return ("<!doctype html>\n<html lang=\"" + _escape(language) + "\"><head><meta charset=\"utf-8\">"
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,nofollow">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\' data:; font-src \'self\'; style-src \'unsafe-inline\'; base-uri \'none\'">'
            "<title>" + _escape(title) + "</title><style>" + CSS + extra_css + "</style></head><body>" + body + "</body></html>\n")


def _provenance_html(provenance: dict) -> str:
    source, author = provenance["source"], provenance["authorship"]
    fields = [
        ("Piece / editorial version", source["piece_id"] + " / " + source["version_id"]),
        ("Source SHA-256", source["sha256"]), ("Source locator", source["locator"]),
        ("Source visibility / collection", source["visibility"] + " / " + source["collection"]),
        ("Declared actor / role", author["actor"] + " / " + author["role"]),
        ("Evidence declaration", author["evidence"]),
    ]
    return '<dl class="meta">' + "".join(f"<dt><b>{_escape(key)}</b></dt><dd>{_escape(value)}</dd>" for key, value in fields) + "</dl>"


def make_sheet(text: str, script: str, language: str, destination, *, provenance: dict, direction="ltr") -> dict:
    """Write an empty, printable author worksheet, preserving exact sequences.

    Provenance requires a stable piece/version and source hash. This utility does
    not assert that the supplied text belongs to that version; the realization
    resolver must verify that association before calling it. Direct API callers
    must use verify_source or an equivalent current source/policy resolution.
    """
    provenance = _provenance(provenance)
    _language_script(language, script, direction)
    sequences = _sheet_sequences(text)
    destination = _destination(Path(destination))
    rows = []
    for index, sequence in enumerate(sequences, 1):
        rows.append(f'<tr><td><b>g{index:03d}</b><div class="glyph-label" dir="{direction}">{_escape(sequence)}</div><code>{scalar_label(sequence)}</code></td>'
                    + '<td class="slot"></td>' * 3 + '</tr>')
    body = '<h1>Author glyph capture sheet</h1><div class="notice"><b>PRIVATE · BLANK AUTHOR WORKSHEET</b><br>No glyphs have been generated. Labels identify requested scalar sequences. Draw each sequence three times. The middle guide is the baseline; upper/lower guides are alignment aids.</div>'
    body += f'<p>Language: <b>{_escape(language)}</b> · Script: <b>{_escape(script)}</b> · Direction: <b>{direction}</b></p>'
    body += _provenance_html(provenance)
    body += '<p>Author name: ____________________ Capture date: ____________________</p><p>Source scan/file ID: ____________________ Permission and intended use: ____________________</p>'
    body += '<p>These are base-plus-combining slots, not a full shaping inventory. Joined scripts need contextual forms, marks and spacing reviewed by the author and type engineer before any font work. Keep exact labels; do not normalize the source silently.</p>'
    body += '<table><thead><tr><th>Sequence / exact scalars</th><th>Drawing 1</th><th>Drawing 2</th><th>Drawing 3</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table>'
    body += '<p>After scanning, record each selected rectangle and its exact declared sequence in a capture manifest. Crops remain unreviewed until the author confirms them. This sheet grants no publication permission.</p>'
    encoded = _page("Private author glyph capture sheet", body, language).encode("utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write(encoded)
    return {"path": str(destination), "sha256": _sha(encoded), "sequences": sequences, "visibility": "private", "review_status": "blank-author-work-required"}


def inspect_font(path) -> dict:
    """Audit actual font bytes. Coverage and table presence are not quality proof."""
    from fontTools.ttLib import TTFont
    path = Path(path)
    data = _read(path)
    try:
        font = TTFont(io.BytesIO(data), lazy=False, recalcTimestamp=False)
        cmap = font.getBestCmap() or {}
        names = {}
        for name_id, key in ((1, "family"), (2, "style"), (4, "full_name"), (6, "postscript_name")):
            record = font["name"].getDebugName(name_id) if "name" in font else None
            names[key] = record
        shaping = {}
        for tag in ("GSUB", "GPOS"):
            scripts = []
            if tag in font:
                script_list = getattr(font[tag].table, "ScriptList", None)
                scripts = [record.ScriptTag for record in script_list.ScriptRecord] if script_list else []
            shaping[tag] = {"present": tag in font, "script_tags": sorted(scripts)}
        result = {
            "schema_version": SCHEMA_VERSION, "filename": path.name, "sha256": _sha(data), "byte_size": len(data),
            "names": names, "glyph_count": len(font.getGlyphOrder()), "cmap_count": len(cmap),
            "codepoints": sorted(cmap), "scalar_labels": [f"U+{cp:04X}" for cp in sorted(cmap)],
            "tables": sorted(tag for tag in font.keys() if tag != "GlyphOrder"), "shaping": shaping,
            "limits": ["A cmap entry is not proof of a correct visible glyph or mark attachment.",
                       "GSUB/GPOS presence is not proof that a script shapes correctly.",
                       "Contextual shaping, joining, bidi, line layout and fallback require browser specimen review.",
                       "Internal family names and source bytes are preserved; public font changes belong to T02/T03."],
        }
        font.close()
        return result
    except Exception as exc:
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError("source is not a readable supported font") from exc


def import_font(path, out_dir, *, provenance: dict, text: str, language="en", script="Latn", direction="ltr", asset_id="author-font") -> dict:
    """Copy an author font unchanged; provenance must already be source-verified."""
    provenance = _provenance(provenance)
    _language_script(language, script, direction)
    _identifier(asset_id, "asset_id")
    _string(text, "text", 100_000)
    path = Path(path)
    data = _read(path)
    audit = inspect_font(path)
    if _sha(data) != audit["sha256"]:
        raise ValidationError("font changed during validation")
    out_dir = _destination(Path(out_dir))
    extension = path.suffix.lower()
    if extension not in {".otf", ".ttf", ".woff", ".woff2"}:
        raise ValidationError("font extension must be .otf, .ttf, .woff or .woff2")
    filename = "source-font" + extension
    missing = sorted({ord(char) for char in text if char not in "\n\r\t"} - set(audit["codepoints"]))
    report = {"schema_version": SCHEMA_VERSION, "id": asset_id, "kind": "font", "visibility": "private", "review_status": "unreviewed-technical-fixture", **provenance,
              "language": language, "script": script, "direction": direction,
              "asset": {"path": filename, "sha256": audit["sha256"], "byte_size": len(data), "original_filename": path.name},
              "audit": audit, "fallback_scalars": [f"U+{cp:04X}" for cp in missing]}
    extra_css = f'@font-face{{font-family:ajp-scribbles;src:url("{filename}");font-display:swap;}}'
    body = '<h1>Private author font preview</h1><div class="notice"><b>PRIVATE · UNREVIEWED TECHNICAL FIXTURE</b><br>Source font copied byte for byte. This is no new glyph work, translation or author acceptance of a script. The CSS alias does not rename the font internally.</div>'
    body += _provenance_html(provenance)
    body += '<p>Original family: ' + _escape(audit["names"]["family"]) + '. CSS alias: <code>ajp-scribbles</code>. Fallback: system serif.</p>'
    body += '<p>Scalars absent from cmap: ' + (_escape(", ".join(report["fallback_scalars"])) or "none") + '.</p>'
    body += f'<div class="specimen" dir="{direction}" lang="{_escape(language)}">{_escape(text)}</div>'
    def write(stage):
        (stage / filename).write_bytes(data)
        (stage / "manifest.json").write_bytes(_json_bytes(report))
        (stage / "preview.html").write_text(_page("Private author font preview", body, language, extra_css), encoding="utf-8")
    _commit_directory(out_dir, write)
    return {**report, "output_dir": str(out_dir), "manifest_sha256": _sha(_json_bytes(report))}


def import_capture(manifest_path, out_dir) -> dict:
    """Validate an explicitly labeled PNG capture and atomically write crops.

    All visibility/provenance/geometry/image validation precedes output. Withheld
    assets and Reserve sources are rejected, not emitted into a proofsheet.
    Direct API callers must first bind provenance with verify_source or their
    equivalent current source resolver; the standalone CLI always does so.
    """
    from PIL import Image, UnidentifiedImageError
    manifest_path = Path(manifest_path)
    manifest = _record(manifest_path)
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != SCHEMA_VERSION:
        raise ValidationError("unsupported schema_version")
    manifest_id = _identifier(manifest.get("id"), "id")
    provenance = _provenance(manifest)
    language, script, direction = manifest.get("language"), manifest.get("script"), manifest.get("direction", "ltr")
    _language_script(language, script, direction)
    capture = manifest.get("capture")
    if not isinstance(capture, dict):
        raise ValidationError("capture declaration required")
    relative = _string(capture.get("path"), "capture.path", 255)
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts or "\\" in relative or ":" in relative:
        raise ValidationError("capture.path must stay beneath the manifest directory")
    capture_path = manifest_path.parent / relative_path
    _no_symlinks(capture_path)
    try:
        capture_path.resolve().relative_to(manifest_path.parent.resolve())
    except ValueError as exc:
        raise ValidationError("capture.path escapes manifest directory") from exc
    source_bytes = _read(capture_path)
    source_hash = _sha(source_bytes)
    if source_hash != _sha_value(capture.get("sha256"), "capture.sha256"):
        raise ValidationError("capture SHA-256 mismatch")
    for key in ("locator", "source_id"):
        _string(capture.get(key), f"capture.{key}")
    for key in ("width", "height"):
        if type(capture.get(key)) is not int or capture[key] <= 0:
            raise ValidationError("capture dimensions must be positive integers")
    if capture["width"] * capture["height"] > MAX_PIXELS:
        raise ValidationError("capture exceeds 40 million pixels")
    try:
        with Image.open(io.BytesIO(source_bytes)) as probe:
            if probe.format != "PNG" or getattr(probe, "n_frames", 1) != 1:
                raise ValidationError("capture must be a single-frame PNG")
            if probe.size != (capture["width"], capture["height"]):
                raise ValidationError("capture dimensions mismatch")
            probe.verify()
        with Image.open(io.BytesIO(source_bytes)) as decoded:
            decoded.load()
            image = decoded.convert("RGBA")
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValidationError("capture is corrupt or unsafe PNG") from exc
    glyphs = manifest.get("glyphs")
    if not isinstance(glyphs, list) or not 1 <= len(glyphs) <= MAX_GLYPHS:
        raise ValidationError("glyphs must contain 1–1024 declarations")
    seen = set()
    validated = []
    for glyph in glyphs:
        if not isinstance(glyph, dict):
            raise ValidationError("each glyph must be an object")
        glyph_id = _identifier(glyph.get("id"), "glyph.id")
        if glyph_id in seen:
            raise ValidationError("duplicate glyph.id")
        seen.add(glyph_id)
        if glyph.get("visibility") != "private":
            raise ValidationError("withheld or nonprivate glyphs are excluded")
        sequence = _sequence(glyph.get("sequence"))
        if "scalars" in glyph and glyph["scalars"] != scalar_label(sequence).split():
            raise ValidationError("glyph scalar labels do not match exact sequence")
        rect = glyph.get("rect")
        if not isinstance(rect, list) or len(rect) != 4 or any(type(n) is not int for n in rect):
            raise ValidationError("rect must be four finite integer pixels [x, y, width, height]")
        x, y, width, height = rect
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > image.width or y + height > image.height:
            raise ValidationError("glyph rectangle is empty or out of bounds")
        validated.append((glyph_id, sequence, rect))
    out_dir = _destination(Path(out_dir))
    report = {"schema_version": SCHEMA_VERSION, "id": manifest_id, "kind": "glyph-capture", **provenance,
              "review_status": "unreviewed-supplied-labels", "language": language, "script": script, "direction": direction,
              "capture": {"sha256": source_hash, "byte_size": len(source_bytes), "width": image.width, "height": image.height,
                          "locator": capture["locator"], "source_id": capture["source_id"], "original_path": relative}, "glyphs": []}
    crop_bytes = {}
    for glyph_id, sequence, rect in validated:
        x, y, width, height = rect
        buffer = io.BytesIO()
        crop = image.crop((x, y, x + width, y + height))
        crop.info.clear()  # Crops retain pixels, not hidden PNG metadata.
        crop.save(buffer, format="PNG", compress_level=9)
        encoded = buffer.getvalue()
        filename = f"{glyph_id}.png"
        crop_bytes[filename] = encoded
        report["glyphs"].append({"id": glyph_id, "sequence": sequence, "scalars": scalar_label(sequence).split(), "rect": rect,
                                 "path": filename, "sha256": _sha(encoded), "source_sha256": source_hash,
                                 "visibility": "private", "review_status": "unreviewed-supplied-labels"})
    rows = []
    for glyph in report["glyphs"]:
        rows.append(f'<tr><td>{_escape(glyph["id"])}<div class="glyph-label" dir="{direction}">{_escape(glyph["sequence"])}</div><code>{_escape(" ".join(glyph["scalars"]))}</code></td><td><img class="crop" src="{glyph["path"]}" alt="Unreviewed crop {_escape(glyph["id"])}"></td><td class="caption">Source rectangle {_escape(glyph["rect"])}<br>Crop SHA-256 {_escape(glyph["sha256"])}</td></tr>')
    body = '<h1>Private glyph proofsheet</h1><div class="notice"><b>PRIVATE · UNREVIEWED SUPPLIED LABELS</b><br>These are crops of supplied pixels. Supplied sequence declarations are not character recognition or author acceptance. Shape, sequence mapping, authorship and permission require review before font construction or publication.</div>'
    body += _provenance_html(provenance)
    body += f'<p class="meta">Capture source: {_escape(capture["source_id"])} · {_escape(capture["locator"])}<br>Capture SHA-256: {source_hash}</p>'
    body += '<table><thead><tr><th>Declared sequence</th><th>Original crop</th><th>Provenance</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table>'
    def write(stage):
        for name, data in crop_bytes.items():
            (stage / name).write_bytes(data)
        (stage / "manifest.json").write_bytes(_json_bytes(report))
        (stage / "preview.html").write_text(_page("Private glyph proofsheet", body, language), encoding="utf-8")
    _commit_directory(out_dir, write)
    return {**report, "output_dir": str(out_dir), "manifest_sha256": _sha(_json_bytes(report))}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("inspect-font")
    audit.add_argument("font")
    capture = sub.add_parser("import-capture")
    capture.add_argument("manifest")
    capture.add_argument("out_dir")
    def source_arguments(command):
        command.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1],
                             help="source checkout (default: this tool's checkout)")
        command.add_argument("--db", type=Path, required=True,
                             help="explicit current studio export for source/policy verification")
    source_arguments(capture)
    for name in ("sheet", "import-font"):
        command = sub.add_parser(name)
        if name == "import-font":
            command.add_argument("font")
        command.add_argument("destination")
        command.add_argument("--text-file", required=True)
        command.add_argument("--provenance", required=True)
        command.add_argument("--language", required=True)
        command.add_argument("--script", required=True)
        command.add_argument("--direction", choices=("ltr", "rtl"), default="ltr")
        source_arguments(command)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect-font":
            result = inspect_font(args.font)
        elif args.command == "import-capture":
            verify_source(_record(Path(args.manifest)), args.repo, args.db)
            result = import_capture(args.manifest, args.out_dir)
        else:
            provenance = verify_source(_record(Path(args.provenance)), args.repo, args.db)
            try:
                text = _read(Path(args.text_file)).decode("utf-8")
            except UnicodeError as exc:
                raise ValidationError("text file must be UTF-8") from exc
            if args.command == "sheet":
                result = make_sheet(text, args.script, args.language, args.destination, provenance=provenance, direction=args.direction)
            else:
                result = import_font(args.font, args.destination, provenance=provenance, text=text, language=args.language, script=args.script, direction=args.direction)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (ValidationError, OSError) as exc:
        parser.exit(2, f"glyph workflow: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
