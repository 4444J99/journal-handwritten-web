#!/usr/bin/env python3
"""Validate the public notes sidecar (journal-handwritten-web #17).

The sidecar (site/data/notes.json) is the public projection of cleared
notes: only records the author wrote in the studio Notes tab, had
editorially accepted, and cleared for release review reach it, via the
notes-model projectPreview allowlist. This tool is the build-time gate
for that file -- the same --check semantics as tools/notes_sources.py:

    python3 tools/notes_sidecar.py --check

Checks, in order:
  1. Envelope shape: format "versforms-notes-sidecar", version 1, records list.
  2. Record shape: only the projected public fields; family "note";
     kind footnote / endnote / critical-note ("essay" in the #17 plan is the
     schema's critical-note kind -- notes-v1 has no "essay" kind, so the
     sidecar does not invent one); fixture must be false; research dossiers
     never project.
  3. Anchors: footnote/endnote records anchor to a version AND a line that
     exist in studio/data/notes-versions.json and studio/data/review.json;
     a word selector must satisfy text[start:end] == quote on that line
     (offsets are zero-based Unicode code points, the model's convention).
     Critical-notes anchor to a line, to a whole version (lineId null), or
     to the whole series (pieceId/versionId/lineId all null, the
     series-introduction apparatus); no other null combination is valid.
  4. Citations: each has a non-empty label; a URL, when present, is http(s)
     with no credentials. Text/credit non-empty; dates are real calendar
     dates; poemDate certainty is unknown / recorded / approximate.
  5. Staleness: provenance.sources sha256 values must match the current
     bytes of studio/data/notes-versions.json and site/data/j.json, so a
     sidecar built against moved lines fails loudly instead of pointing
     at the wrong source. (Rebuild the projection, then re-run --check.)

No record is ever invented here: an empty records list is valid, and the
reader renders exactly as before when there are no records.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIDECAR = ROOT / "site/data/notes.json"
VERSIONS = ROOT / "studio/data/notes-versions.json"
REVIEW = ROOT / "studio/data/review.json"
CATALOG = ROOT / "site/data/j.json"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
POEM_DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
URL_RE = re.compile(r"^https?://", re.IGNORECASE)

FIELDS = {
    "id", "revisionId", "family", "kind", "pieceId", "versionId", "lineId",
    "word", "text", "citations", "credit", "poemDate", "noteDate", "fixture",
}
KINDS = {"footnote", "endnote", "critical-note"}
CERTAINTIES = {"unknown", "recorded", "approximate"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text())


def build_anchor_index():
    """(pieceId, versionId) -> set of lineIds, and lineId -> line text.

    From the frozen id-map (which versions exist, which pages/blocks they
    cover) joined to review.json (which line ids each block holds).
    """
    versions = load_json(VERSIONS)
    review = load_json(REVIEW)
    pages = {p["id"]: p for p in review.get("pages", [])}
    index = {}
    texts = {}
    for piece in versions.get("pieces", []):
        for version in piece.get("V", []):
            lines = set()
            for page_id, blocks in version.get("P", []):
                page = pages.get(page_id)
                if page is None:
                    continue
                for bi in blocks:
                    if bi >= len(page.get("blocks", [])):
                        continue
                    for line in page["blocks"][bi].get("lines", []):
                        lines.add(line["id"])
                        texts[line["id"]] = line.get("tx", "")
            index[(piece["id"], version["id"])] = lines
    return index, texts


def check_date(value, field, errors):
    if not isinstance(value, str) or not DATE_RE.match(value):
        errors.append(f"{field}: not a YYYY-MM-DD date: {value!r}")
        return
    try:
        date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field}: not a real calendar date: {value!r}")


def check_record(rec, index, texts, seen_ids, errors):
    where = f"record {rec.get('id', '?')!r}"
    if not isinstance(rec, dict):
        errors.append(f"{where}: not an object")
        return
    extra = sorted(set(rec) - FIELDS)
    if extra:
        errors.append(f"{where}: unknown fields: {extra}")
    for key in ("id", "revisionId"):
        if not isinstance(rec.get(key), str) or not ID_RE.match(rec[key]):
            errors.append(f"{where}: bad {key}: {rec.get(key)!r}")
    if rec.get("id") in seen_ids:
        errors.append(f"{where}: duplicate record id")
    seen_ids.add(rec.get("id"))
    if rec.get("family") != "note":
        errors.append(f"{where}: family must be 'note', got {rec.get('family')!r}")
    kind = rec.get("kind")
    if kind not in KINDS:
        errors.append(f"{where}: kind must be one of {sorted(KINDS)}, got {kind!r}")
        return
    if rec.get("fixture") is not False:
        errors.append(f"{where}: fixture must be false in the public sidecar")
    if not isinstance(rec.get("text"), str) or not rec["text"].strip():
        errors.append(f"{where}: text must be non-empty")
    if not isinstance(rec.get("credit"), str) or not rec["credit"].strip():
        errors.append(f"{where}: credit must be non-empty")
    check_date(rec.get("noteDate"), f"{where} noteDate", errors)
    poem_date = rec.get("poemDate")
    if not isinstance(poem_date, dict) or poem_date.get("certainty") not in CERTAINTIES:
        errors.append(f"{where}: poemDate certainty must be one of {sorted(CERTAINTIES)}")
    elif poem_date.get("value") is not None:
        if not isinstance(poem_date["value"], str) or not POEM_DATE_RE.match(poem_date["value"]):
            errors.append(f"{where}: poemDate value must be YYYY, YYYY-MM or YYYY-MM-DD")
    citations = rec.get("citations")
    if not isinstance(citations, list):
        errors.append(f"{where}: citations must be a list")
    else:
        for c in citations:
            if not isinstance(c, dict) or set(c) - {"label", "url", "locator"}:
                errors.append(f"{where}: citation has unknown fields: {c!r}")
                continue
            if not isinstance(c.get("label"), str) or not c["label"].strip():
                errors.append(f"{where}: citation label must be non-empty")
            url = c.get("url")
            if url is not None:
                if not isinstance(url, str) or not URL_RE.match(url) or "@" in url.split("://", 1)[1].split("/", 1)[0]:
                    errors.append(f"{where}: citation url must be http(s) without credentials: {url!r}")
    # Anchors.
    piece, version, line = rec.get("pieceId"), rec.get("versionId"), rec.get("lineId")
    word = rec.get("word")
    if kind in ("footnote", "endnote"):
        if not isinstance(piece, str) or not isinstance(version, str):
            errors.append(f"{where}: {kind} needs pieceId and versionId")
            return
        if (piece, version) not in index:
            errors.append(f"{where}: unknown piece/version anchor: {piece}/{version}")
            return
        if not isinstance(line, str):
            errors.append(f"{where}: {kind} needs a lineId anchor")
            return
        if line not in index[(piece, version)]:
            errors.append(f"{where}: line {line!r} is not a member of {piece}/{version}")
            return
    else:  # critical-note: line, whole version, or whole series.
        if piece is None and version is None and line is None:
            pass  # series-introduction apparatus
        elif isinstance(piece, str) and isinstance(version, str):
            if (piece, version) not in index:
                errors.append(f"{where}: unknown piece/version anchor: {piece}/{version}")
                return
            if line is not None and line not in index[(piece, version)]:
                errors.append(f"{where}: line {line!r} is not a member of {piece}/{version}")
                return
        else:
            errors.append(f"{where}: critical-note anchor must be line, whole version, or whole series")
            return
    if word is not None:
        if not isinstance(word, dict) or set(word) != {"quote", "start", "end"}:
            errors.append(f"{where}: word must be {{quote, start, end}}")
        elif line is None:
            errors.append(f"{where}: a word selector needs a line anchor")
        else:
            quote, start, end = word.get("quote"), word.get("start"), word.get("end")
            if not isinstance(quote, str) or not quote:
                errors.append(f"{where}: word quote must be non-empty")
            elif not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
                errors.append(f"{where}: word offsets must satisfy 0 <= start < end")
            else:
                text = texts.get(line, "")
                if text[start:end] != quote:
                    errors.append(
                        f"{where}: word selector does not match the anchored line: "
                        f"text[{start}:{end}] is {text[start:end]!r}, not {quote!r}"
                    )


def check(root=ROOT):
    errors = []
    try:
        sidecar = load_json(SIDECAR)
    except (OSError, ValueError) as exc:
        return [f"sidecar unreadable: {exc}"]
    if not isinstance(sidecar, dict):
        return ["sidecar is not an object"]
    if sidecar.get("format") != "versforms-notes-sidecar":
        errors.append(f"format must be 'versforms-notes-sidecar', got {sidecar.get('format')!r}")
    if sidecar.get("version") != 1:
        errors.append(f"version must be 1, got {sidecar.get('version')!r}")
    records = sidecar.get("records")
    if not isinstance(records, list):
        errors.append("records must be a list")
        records = []
    prov = sidecar.get("provenance") or {}
    sources = prov.get("sources") or []
    expected = {"studio/data/notes-versions.json": VERSIONS, "site/data/j.json": CATALOG}
    seen_sources = set()
    for src in sources:
        path = src.get("path") if isinstance(src, dict) else None
        if path in expected:
            seen_sources.add(path)
            want = sha256(expected[path])
            if src.get("sha256") != want:
                errors.append(
                    f"stale provenance: {path} is now {want[:12]}..., "
                    f"sidecar records {str(src.get('sha256'))[:12]}... -- rebuild the projection"
                )
    for path in expected:
        if path not in seen_sources:
            errors.append(f"provenance is missing a source entry for {path}")
    try:
        index, texts = build_anchor_index()
    except (OSError, ValueError, KeyError) as exc:
        return errors + [f"anchor index unreadable: {exc}"]
    seen_ids = set()
    for rec in records:
        check_record(rec, index, texts, seen_ids, errors)
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Fail if the sidecar is invalid or stale (default action).")
    parser.parse_args(argv)
    errors = check()
    if errors:
        print("notes sidecar INVALID:")
        for error in errors:
            print(" -", error)
        return 1
    print("Notes sidecar OK: site/data/notes.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
