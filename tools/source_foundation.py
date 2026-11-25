#!/usr/bin/env python3
"""Reconstruct, review, rebuild and independently restore the private source.

No HTML, source photograph, font, author text, release decision or existing ID
is inferred. Raw transcripts remain the stale-review baseline. See the T02
contract for the distinction between preserved evidence and reconstructed data.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile

from source_fingerprint import source_fingerprint, source_binding

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "versforms.canonical-source.v1"
CANONICAL = "source/canonical.json"
SOURCE_FILES = ("site/data/j.json", "studio/data/review.json")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
MAX_FILE = 64 * 1024 * 1024


class Invalid(ValueError):
    pass


def sha(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def encoded(value, *, compact=False):
    opts = {"separators": (",", ":")} if compact else {"indent": 2}
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, **opts)
            + ("" if compact else "\n")).encode("utf-8")


def digest(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8"))


def no_links(path):
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise Invalid("symlink paths are not accepted")
    return path


def read_bytes(path):
    path = no_links(path)
    if not path.is_file() or path.stat().st_size > MAX_FILE:
        raise Invalid("expected a regular file of at most 64 MiB")
    return path.read_bytes()


def decode(data):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise Invalid("duplicate JSON key")
            out[key] = value
        return out
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(Invalid("non-finite JSON")))
    except (UnicodeError, ValueError, RecursionError) as error:
        raise Invalid("invalid UTF-8 JSON") from error


def read_json(path):
    return decode(read_bytes(path))


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise Invalid("invalid stable ID")
    return value


def index(items, what):
    out = {}
    for item in items:
        key = identifier(item.get("id"))
        if key in out:
            raise Invalid("duplicate " + what + " ID")
        out[key] = item
    return out


def relative(value):
    if not isinstance(value, str):
        raise Invalid("relative path must be a string")
    path = PurePosixPath(value)
    if not value or "\\" in value or path.is_absolute() or any(
            part in ("", ".", "..") for part in value.split("/")):
        raise Invalid("unsafe relative path")
    return path


def atomic_write(path, data):
    path = no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".source-write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def asset_record(path, data, *, page_id=None, source_ids=(), recipe=None, role=None):
    return {"id": "asset:" + path, "path": path, "sha256": sha(data), "bytes": len(data),
            "pageId": page_id, "role": role or "preserved-existing-asset",
            "sourceAssetIds": list(source_ids), "recipe": recipe or {
                "status": "historical-transformation-unrecovered", "operation": None},
            "evidence": "preserved bytes; not a new scan or archival-original claim",
            "clearance": None, "generative": False}


def reconstruct(root=ROOT):
    """Capture existing IDs once; ordering and geometry are separate fields."""
    root = Path(root)
    raw = [read_bytes(root / name) for name in SOURCE_FILES]
    reader, studio = map(decode, raw)
    if reader.get("acceptedReadings") or studio.get("acceptedReviews") or reader.get("acceptedReviews") or reader.get("sourceBindings"):
        raise Invalid("cannot recapture accepted overlays without canonical review history; restore the canonical source")
    rp, sp = index(reader["pages"], "page"), index(studio["pages"], "studio page")
    if set(rp) != set(sp):
        raise Invalid("reader/studio page membership differs")
    pages, blocks, lines = [], [], []
    for page_id, page in rp.items():
        review = sp[page_id]
        if len(page["B"]) != len(review["blocks"]):
            raise Invalid("reader/studio block count differs")
        source_page = {"id": page_id, "blockIds": [],
                       "reader": {k: v for k, v in page.items() if k not in ("B", "x")},
                       "studio": {k: v for k, v in review.items() if k != "blocks"},
                       "geometryOrder": [], "uncertainty": copy.deepcopy(review.get("uncertain", [])),
                       "origin": "preserved-existing-page", "cleanedImage": None}
        rows = {}
        for row in page.get("x", []):
            key = tuple(row[:2])
            if key in rows:
                raise Invalid("duplicate source line geometry")
            rows[key] = row
        row_ids = {}
        for bi, (block, review_block) in enumerate(zip(page["B"], review["blocks"])):
            block_id = page_id + "-block-" + str(bi)
            if len(block["L"]) != len(review_block["lines"]):
                raise Invalid("reader/studio line count differs")
            source_page["blockIds"].append(block_id)
            source_block = {"id": block_id, "pageId": page_id, "lineIds": [],
                            "type": review_block.get("t", "text"),
                            "readerKeyOrder": list(block),
                            "reader": {k: v for k, v in block.items() if k != "L"},
                            "studio": {k: v for k, v in review_block.items() if k != "lines"}}
            for li, (text, line) in enumerate(zip(block["L"], review_block["lines"])):
                line_id = identifier(line["id"])
                source_block["lineIds"].append(line_id)
                row_ids[(bi, li)] = line_id
                row, box = rows.get((bi, li)), line.get("box")
                available = row is not None and box is not None
                lines.append({"id": line_id, "pageId": page_id, "blockId": block_id,
                              "originalText": line["tx"], "readerOriginalText": text,
                              "transcriptionStatus": "existing-transcription-unverified",
                              "studio": {k: v for k, v in line.items() if k not in ("id", "tx", "box")},
                              "geometry": {"readerRow": row, "studioBox": box,
                                           "status": "available" if available else "unavailable",
                                           "reason": None if available else "no-source-line-geometry"}})
            blocks.append(source_block)
        if set(rows) - set(row_ids):
            raise Invalid("source geometry points outside transcript membership")
        source_page["geometryOrder"] = [row_ids[tuple(row[:2])] for row in page.get("x", [])]
        pages.append(source_page)
    page_map = index(pages, "page")
    pieces, versions = [], []
    for piece in reader["pieces"]:
        pieces.append({"id": piece["id"], "versionIds": [v["id"] for v in piece["V"]],
                       "reader": {k: v for k, v in piece.items() if k != "V"}})
        for version in piece["V"]:
            versions.append({"id": version["id"], "pieceId": piece["id"],
                             "members": [{"pageId": pid, "blockIds": [page_map[pid]["blockIds"][bi] for bi in bis]}
                                         for pid, bis in version["P"]],
                             "reader": {k: v for k, v in version.items() if k != "P"}})
    assets = []
    for folder in ("site/img", "studio/img"):
        for path in sorted((root / folder).rglob("*")):
            no_links(path)
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                page_id = path.stem if path.stem in page_map else None
                role = "preserved-jpeg-master" if rel.startswith("site/img/p/") else "existing-display-derivative"
                assets.append(asset_record(rel, read_bytes(path), page_id=page_id, role=role))
    for page in pages:
        page_assets = [a for a in assets if a["pageId"] == page["id"]]
        page["imageLineage"] = {
            "archivalOriginal": {"status": "unavailable", "assetId": None},
            "preservedMasterAssetId": next((a["id"] for a in page_assets if a["role"] == "preserved-jpeg-master"), None),
            "cleanedImage": {"status": "historical-transformation-unrecovered", "assetId": None},
            "displayAssetIds": [a["id"] for a in page_assets if a["role"] != "preserved-jpeg-master"],
            "relationship": "existing page-ID association; historical pixel transformation is unverified"}
    source = {"schema": SCHEMA, "fingerprintVersion": 2,
              "provenance": {"kind": "bounded-technical-reconstruction", "originalGenerator": "unrecovered",
                             "sourceFiles": [{"path": name, "sha256": sha(data)} for name, data in zip(SOURCE_FILES, raw)]},
              "pages": pages, "blocks": blocks, "lines": lines, "pieces": pieces, "versions": versions,
              "order": {"pages": list(rp), "studioPages": list(sp), "pieces": [p["id"] for p in pieces]},
              "reader": {k: v for k, v in reader.items() if k not in ("pages", "pieces", "acceptedReadings", "sourceAnchors", "sourceBindings")},
              "studio": {k: v for k, v in studio.items() if k not in ("pages", "acceptedReviews")},
              "reviews": {"current": {}, "history": []}, "assets": assets}
    validate(source)
    return source


def validate(source):
    if not isinstance(source, dict) or source.get("schema") != SCHEMA or source.get("fingerprintVersion") != 2:
        raise Invalid("unsupported canonical source contract")
    pages, blocks, lines, pieces, versions = [index(source[name], name) for name in ("pages", "blocks", "lines", "pieces", "versions")]
    for kind, order in (("pages", source["order"]["pages"]), ("pages", source["order"]["studioPages"]), ("pieces", source["order"]["pieces"])):
        expected = pages if kind == "pages" else pieces
        if len(order) != len(set(order)) or set(order) != set(expected):
            raise Invalid("reading order must contain every stable ID exactly once")
    seen_blocks, seen_lines, seen_versions = set(), set(), set()
    for page in pages.values():
        if page["reader"].get("id") != page["id"] or page["studio"].get("id") != page["id"]:
            raise Invalid("page compatibility identity differs from stable ID")
        for bid in page["blockIds"]:
            if bid in seen_blocks or bid not in blocks or blocks[bid]["pageId"] != page["id"]:
                raise Invalid("invalid block membership")
            seen_blocks.add(bid)
            for lid in blocks[bid]["lineIds"]:
                if lid in seen_lines or lid not in lines or lines[lid]["blockId"] != bid or lines[lid]["pageId"] != page["id"]:
                    raise Invalid("invalid line membership")
                seen_lines.add(lid)
                line = lines[lid]
                if line["transcriptionStatus"] == "untranscribed":
                    if line["originalText"] is not None or line["readerOriginalText"] is not None:
                        raise Invalid("untranscribed source must have null originals")
                elif not isinstance(line["originalText"], str) or not isinstance(line["readerOriginalText"], str):
                    raise Invalid("original transcripts must be strings")
                geometry = line["geometry"]
                if geometry["status"] not in ("available", "unavailable"):
                    raise Invalid("unsupported source anchor availability")
                if geometry["status"] == "unavailable" and not geometry.get("reason"):
                    raise Invalid("unavailable source geometry requires an explicit reason")
                if geometry["status"] == "available" and (geometry["readerRow"] is None or geometry["studioBox"] is None):
                    raise Invalid("available geometry must have both preserved anchors")
        expected_rows = {lid for bid in page["blockIds"] for lid in blocks[bid]["lineIds"] if lines[lid]["geometry"]["readerRow"] is not None}
        if set(page["geometryOrder"]) != expected_rows or len(page["geometryOrder"]) != len(expected_rows):
            raise Invalid("geometry order differs from source anchors")
    if seen_blocks != set(blocks) or seen_lines != set(lines):
        raise Invalid("orphan source block or line")
    for piece in pieces.values():
        if piece["reader"].get("id") != piece["id"]:
            raise Invalid("piece compatibility identity differs from stable ID")
        for vid in piece["versionIds"]:
            if vid in seen_versions or vid not in versions or versions[vid]["pieceId"] != piece["id"]:
                raise Invalid("invalid version membership")
            seen_versions.add(vid)
            if versions[vid]["reader"].get("id") != vid:
                raise Invalid("version compatibility identity differs from stable ID")
            used = set()
            for member in versions[vid]["members"]:
                if member["pageId"] not in pages or not member["blockIds"]:
                    raise Invalid("invalid version page membership")
                for bid in member["blockIds"]:
                    if bid in used or bid not in blocks or blocks[bid]["pageId"] != member["pageId"]:
                        raise Invalid("invalid version block membership")
                    used.add(bid)
    if seen_versions != set(versions):
        raise Invalid("orphan source version")
    for lid, document in source["reviews"]["current"].items():
        validate_review(lid, document, lines)
    latest_reviews = {}
    for event in source["reviews"]["history"]:
        validate_review(event["lineId"], event["document"], lines)
        if event["documentDigest"] != digest(event["document"]):
            raise Invalid("review history digest mismatch")
        relative(event["provenance"]["path"])
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", event["provenance"]["sha256"]):
            raise Invalid("invalid review provenance digest")
        latest_reviews[event["lineId"]] = event["document"]
    if latest_reviews != source["reviews"]["current"]:
        raise Invalid("current reviews must match the preserved history heads")
    seen_assets = set()
    for asset in source["assets"]:
        relative(asset["path"])
        if asset["path"] in seen_assets or asset["id"] != "asset:" + asset["path"] or not re.fullmatch(r"sha256:[0-9a-f]{64}", asset["sha256"]):
            raise Invalid("invalid image lineage")
        seen_assets.add(asset["path"])
    asset_ids = {a["id"] for a in source["assets"]}
    if any(set(a["sourceAssetIds"]) - asset_ids for a in source["assets"]):
        raise Invalid("image lineage refers to an absent asset")
    return {"pages": len(pages), "pieces": len(pieces), "versions": len(versions),
            "lines": len(lines), "reviews": len(source["reviews"]["current"]),
            "unavailableAnchors": sum(l["geometry"]["status"] == "unavailable" for l in lines.values())}


def validate_review(line_id, document, lines):
    if line_id not in lines or not isinstance(document, dict) or document.get("status") not in ("confirmed", "corrected"):
        raise Invalid("review must address an existing line with confirmed/corrected status")
    line = lines[line_id]
    if line["originalText"] is None or document.get("original") != line["originalText"]:
        raise Invalid("stale review original for " + line_id)
    if line["originalText"] != line["readerOriginalText"]:
        raise Invalid("review cannot rewrite a protected quotation marker")
    if not isinstance(document.get("at"), str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z", document["at"]):
        raise Invalid("review must preserve its recorded UTC instant")
    if document["status"] == "corrected" and not isinstance(document.get("text"), str):
        raise Invalid("corrected review needs explicit text")


def apply_reviews(source, db):
    """Pure validated proposal. The caller performs backup before any mutation."""
    validate(source)
    updated = copy.deepcopy(source)
    lines = index(source["lines"], "line")
    folder = no_links(Path(db) / "reviews")
    if not folder.is_dir():
        raise Invalid("review export has no reviews collection")
    changed, unchanged = [], []
    for path in sorted(folder.iterdir()):
        if path.suffix != ".json":
            raise Invalid("unexpected review export entry")
        lid = identifier(path.stem)
        raw = read_bytes(path)
        document = decode(raw)
        validate_review(lid, document, lines)
        previous = updated["reviews"]["current"].get(lid)
        if previous == document:
            unchanged.append(lid)
            continue
        updated["reviews"]["current"][lid] = document
        updated["reviews"]["history"].append({"lineId": lid, "document": document,
            "documentDigest": digest(document), "provenance": {"path": "reviews/" + path.name, "sha256": sha(raw)}})
        changed.append({"lineId": lid, "status": document["status"],
                        "previousDigest": digest(previous) if previous else None, "documentDigest": digest(document)})
    validate(updated)
    return updated, {"schema": "versforms.source-review-report.v1", "changed": changed,
                     "unchanged": unchanged, "rawOriginalsChanged": 0,
                     "before": digest(source), "after": digest(updated), "counts": validate(updated)}


def render_data(source, *, overlays=True):
    """Pure deterministic data reconstruction; current HTML is never a template input."""
    validate(source)
    pages, blocks, lines, pieces, versions = [index(source[name], name) for name in ("pages", "blocks", "lines", "pieces", "versions")]
    reader, studio = copy.deepcopy(source["reader"]), copy.deepcopy(source["studio"])
    rp, sp, missing, readings = {}, {}, {}, {}
    current = source["reviews"]["current"]
    for pid in source["order"]["pages"]:
        page = pages[pid]
        r, s = copy.deepcopy(page["reader"]), copy.deepcopy(page["studio"])
        r["B"], s["blocks"], geometry = [], [], {}
        for bi, bid in enumerate(page["blockIds"]):
            block = blocks[bid]
            rb, sb = copy.deepcopy(block["reader"]), copy.deepcopy(block["studio"])
            rb["L"], sb["lines"] = [], []
            explicit_ids = []
            for li, lid in enumerate(block["lineIds"]):
                line, review = lines[lid], current.get(lid)
                anchor_geometry = line["geometry"] if overlays else line.get("originalGeometry", line["geometry"])
                rb["L"].append(line["readerOriginalText"] if line["readerOriginalText"] is not None else "")
                sl = {"id": lid, "tx": line["originalText"] if line["originalText"] is not None else "", "box": copy.deepcopy(anchor_geometry["studioBox"])}
                sl.update(copy.deepcopy(line["studio"]))
                if line["transcriptionStatus"] == "untranscribed":
                    sl["transcriptionStatus"] = "untranscribed"
                    rb["transcriptionStatus"] = "untranscribed"
                if anchor_geometry["status"] == "unavailable" and overlays:
                    anchor = {"status": "unavailable", "reason": anchor_geometry["reason"]}
                    sl["sourceAnchor"] = anchor
                    missing[lid] = anchor
                sb["lines"].append(sl)
                row = anchor_geometry["readerRow"]
                if row is not None:
                    geometry[lid] = [bi, li, *row[2:]]
                explicit_ids.append(lid)
                if review and review["status"] == "corrected" and block["type"] != "quotation":
                    readings[lid] = review["text"]
            if overlays and explicit_ids != [pid + "-" + str(bi) + "-" + str(li) for li in range(len(explicit_ids))]:
                rb["lineIds"] = explicit_ids
            key_order = block.get("readerKeyOrder", [])
            rb = {k: rb[k] for k in key_order if k in rb} | {k: v for k, v in rb.items() if k not in key_order}
            r["B"].append(rb)
            s["blocks"].append(sb)
        r["x"] = [geometry[lid] for lid in (page["geometryOrder"] if overlays else page.get("originalGeometryOrder", page["geometryOrder"]))]
        # Reinsert at the historical key positions for a byte-identical no-op.
        original_reader_order = list(page["reader"])
        if "pl" in original_reader_order:
            r = {**{k: v for k, v in r.items() if k not in ("pl", "B", "x")}, "B": r["B"], "x": r["x"], "pl": r["pl"]}
        rp[pid], sp[pid] = r, s
    reader["pages"] = [rp[pid] for pid in source["order"]["pages"]]
    studio["pages"] = [sp[pid] for pid in source["order"]["studioPages"]]
    output_pieces = []
    for pid in source["order"]["pieces"]:
        piece = copy.deepcopy(pieces[pid]["reader"])
        piece["V"] = []
        for vid in pieces[pid]["versionIds"]:
            version = versions[vid]
            v = copy.deepcopy(version["reader"])
            members = [[m["pageId"], [pages[m["pageId"]]["blockIds"].index(bid) for bid in m["blockIds"]]] for m in version["members"]]
            v["P"] = members
            # Historical source order is id, s, P, d (retain all other fields).
            v = {k: v[k] for k in ("id", "s", "P", "d") if k in v} | {k: val for k, val in v.items() if k not in ("id", "s", "P", "d")}
            piece["V"].append(v)
        piece = {k: piece[k] for k in ("id", "V") if k in piece} | {k: val for k, val in piece.items() if k not in ("id", "V")}
        output_pieces.append(piece)
    reader["pieces"] = output_pieces
    # The captured top-level key order is part of the compatibility serializer.
    reader = {k: reader[k] for k in ("v", "pages", "groups", "atlas", "pieces", "prov") if k in reader} | {k: v for k, v in reader.items() if k not in ("v", "pages", "groups", "atlas", "pieces", "prov")}
    studio = {k: studio[k] for k in ("version", "pages", "items", "flagged") if k in studio} | {k: v for k, v in studio.items() if k not in ("version", "pages", "items", "flagged")}
    if overlays:
        if current:
            studio["acceptedReviews"] = copy.deepcopy(current)
        if readings:
            reader["acceptedReadings"] = readings
        if missing:
            reader["sourceAnchors"] = missing
        reader["sourceBindings"] = {}
        for piece in reader["pieces"]:
            for version in piece["V"]:
                snapshot = _logical_from_rendered(reader, studio, piece["id"], version["id"])
                if snapshot is not None:
                    reader["sourceBindings"][piece["id"] + "/" + version["id"]] = source_binding(snapshot)
    return reader, studio


def _logical_from_rendered(reader, studio, piece_id, version_id):
    piece = next((p for p in reader["pieces"] if p["id"] == piece_id), None)
    version = next((v for v in (piece or {}).get("V", []) if v["id"] == version_id), None)
    if version is None:
        raise Invalid("unknown exact piece/version")
    pages, rows = {p["id"]: p for p in studio["pages"]}, []
    for pid, indexes in version["P"]:
        for bi in indexes:
            block = pages[pid]["blocks"][bi]
            for li, line in enumerate(block["lines"]):
                if line.get("transcriptionStatus") == "untranscribed":
                    return None
                review = studio.get("acceptedReviews", {}).get(line["id"])
                text = review["text"] if review and review["status"] == "corrected" and block["t"] != "quotation" else line["tx"]
                rows.append({"lineId": line["id"], "text": text, "blockType": block["t"],
                             "breakBefore": line.get("breakBefore", bool(rows) and li == 0)})
    if not rows:
        return None
    return {"pieceId": piece_id, "versionId": version_id, "members": version["P"], "lines": rows}


def logical_snapshot(source, piece_id, version_id):
    reader, studio = render_data(source)
    out = _logical_from_rendered(reader, studio, piece_id, version_id)
    if out is None:
        raise Invalid("untranscribed source line; explicit transcription required")
    out["sourceFingerprint"] = source_fingerprint(out)
    return out


def geometry_fingerprint(source, page_id):
    page = next(p for p in source["pages"] if p["id"] == page_id)
    return digest({"pageId": page_id, "dimensions": {k: page["reader"].get(k) for k in ("iw", "ih", "W", "H", "c")},
                   "lines": [{"lineId": l["id"], "geometry": l["geometry"]} for l in sorted(source["lines"], key=lambda v: v["id"]) if l["pageId"] == page_id],
                   "assets": [{"id": a["id"], "sha256": a["sha256"]} for a in sorted(source["assets"], key=lambda v: v["id"]) if a.get("pageId") == page_id]})


def build_outputs(source):
    reader, studio = render_data(source)
    data = dict(zip(SOURCE_FILES, (encoded(reader, compact=True), encoded(studio, compact=True))))
    # The derived id-map carries the version's method/src (journal-handwritten-web
    # #55) so a rebuild reproduces the checked-in map byte-for-byte: the map is
    # an id-map, so it carries the fields without allocating new ids. Absent
    # method means "original"; src/sourceVersion appear only on cut-up/erasure
    # versions. This mirrors tools/notes_sources.py, which builds the same map.
    pieces = []
    for p in reader["pieces"]:
        vs = []
        for v in p["V"]:
            entry = {"id": v["id"], "P": v["P"], "d": v.get("d"),
                     "method": v.get("method", "original")}
            if "src" in v:
                entry["src"] = v["src"]
            if "sourceVersion" in v:
                entry["sourceVersion"] = v["sourceVersion"]
            vs.append(entry)
        pieces.append({"id": p["id"], "V": vs})
    notes = {"format": "versforms-notes-versions", "version": 1,
             "provenance": {"kind": "derived-id-map", "ids": "preserved; none allocated",
                            "sources": [{"path": name, "sha256": hashlib.sha256(data[name]).hexdigest()} for name in SOURCE_FILES]},
             "pieces": pieces}
    data["studio/data/notes-versions.json"] = encoded(notes)
    return data


def rebuild(source, root, *, write=False):
    outputs = build_outputs(source)
    changes = []
    for name, data in outputs.items():
        path = no_links(Path(root) / name)
        old = read_bytes(path) if path.exists() else None
        if old != data:
            changes.append({"path": name, "before": sha(old) if old is not None else None, "after": sha(data)})
    if write:
        for change in changes:
            atomic_write(Path(root) / change["path"], outputs[change["path"]])
    return {"schema": "versforms.source-build-report.v1", "write": write, "changed": changes,
            "counts": validate(source), "templatesModified": [], "imagesModified": [], "fontsModified": []}


def all_files(folder):
    folder = no_links(folder)
    if not folder.is_dir():
        raise Invalid("backup source must be a directory")
    for path in sorted(folder.rglob("*")):
        no_links(path)
        if path.is_file():
            yield path
        elif not path.is_dir():
            raise Invalid("non-regular backup source")


def backup(root, db, destination):
    """Preserve every exported collection, including future immutable history."""
    root, db, destination = map(no_links, (root, db, destination))
    if destination.exists() or destination.is_relative_to(root) or destination.is_relative_to(db):
        raise Invalid("backup needs a new independent destination")
    files = {}
    for folder in ("source", "site", "studio"):
        if (root / folder).exists():
            for path in all_files(root / folder):
                if path.name.endswith(".apply.lock"):
                    continue
                files["repository/" + path.relative_to(root).as_posix()] = path
    for name in ("source_foundation.py", "source_fingerprint.py"):
        if (root / "tools" / name).is_file():
            files["repository/tools/" + name] = root / "tools" / name
    for path in all_files(db):
        files["studio-state/" + path.relative_to(db).as_posix()] = path
    if "repository/" + CANONICAL not in files:
        raise Invalid("canonical source is required in the backup")
    records = [{"path": name, "sha256": sha(read_bytes(path)), "bytes": path.stat().st_size} for name, path in sorted(files.items())]
    manifest = {"schema": "versforms.source-state-backup.v1", "files": records,
                "collections": sorted(p.name for p in db.iterdir() if p.is_dir()), "authorClearance": None}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".source-backup-", dir=destination.parent))
    try:
        for record in records:
            target = temp / record["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = read_bytes(files[record["path"]])
            if sha(payload) != record["sha256"]:
                raise Invalid("source changed during backup")
            target.write_bytes(payload)
        (temp / "manifest.json").write_bytes(encoded(manifest))
        if destination.exists():
            raise Invalid("backup destination appeared concurrently")
        temp.rename(destination)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return {"path": str(destination), "files": len(records), "collections": manifest["collections"], "manifestDigest": digest(manifest)}


def restore(snapshot, destination):
    snapshot, destination = map(no_links, (snapshot, destination))
    if destination.exists() or destination.is_relative_to(snapshot):
        raise Invalid("restore needs a new independent destination")
    manifest = read_json(snapshot / "manifest.json")
    if manifest.get("schema") != "versforms.source-state-backup.v1":
        raise Invalid("unsupported backup schema")
    names = set()
    for record in manifest["files"]:
        path = relative(record["path"])
        if path.parts[0] not in ("repository", "studio-state") or str(path) in names:
            raise Invalid("invalid or duplicate backup member")
        names.add(str(path))
        data = read_bytes(snapshot / path)
        if len(data) != record["bytes"] or sha(data) != record["sha256"]:
            raise Invalid("backup integrity mismatch")
    actual = {p.relative_to(snapshot).as_posix() for p in all_files(snapshot)} - {"manifest.json"}
    if names != actual:
        raise Invalid("unlisted or missing backup file")
    validate(read_json(snapshot / "repository" / CANONICAL))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".source-restore-", dir=destination.parent))
    try:
        for record in manifest["files"]:
            path = temp / record["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            data = read_bytes(snapshot / record["path"])
            if sha(data) != record["sha256"]:
                raise Invalid("backup changed during restore")
            path.write_bytes(data)
        for collection in manifest["collections"]:
            identifier(collection)
            (temp / "studio-state" / collection).mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise Invalid("restore destination appeared concurrently")
        temp.rename(destination)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return {"path": str(destination), "verifiedFiles": len(names), "collections": manifest["collections"], "manifestDigest": digest(manifest)}


def commit_proposal(root, db, proposed, destination, *, assets=None, expected_digest=None):
    """Exclusive local writer; backup completes before the canonical swap."""
    root = Path(root)
    canonical = no_links(root / CANONICAL)
    before = read_bytes(canonical)
    if expected_digest is not None and digest(decode(before)) != expected_digest:
        raise Invalid("canonical source changed after the proposal")
    after = encoded(proposed)
    if before == after and not assets:
        return {"changed": False, "backup": None}
    validate(proposed)
    if destination is None:
        raise Invalid("application requires an independent backup destination")
    lock = canonical.with_suffix(".apply.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise Invalid("another source application holds the local lock") from error
    created = []
    try:
        if read_bytes(canonical) != before:
            raise Invalid("canonical source changed before application")
        for name in assets or {}:
            path = no_links(root / relative(name))
            if path.exists():
                raise Invalid("photo ingest would replace existing bytes")
        receipt = backup(root, db, destination)
        if read_bytes(canonical) != before:
            raise Invalid("canonical source changed during backup")
        for name, data in (assets or {}).items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            asset_fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            created.append(path)
            with os.fdopen(asset_fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        atomic_write(canonical, after)
        return {"changed": True, "backup": receipt, "canonicalDigest": sha(after)}
    except BaseException:
        for path in reversed(created):
            path.unlink()
        raise
    finally:
        os.close(fd)
        lock.unlink()


def stage_photo(source, descriptor, photo):
    """Explicit new IDs and unknown transcription, with reproducible derivatives."""
    from PIL import Image, __version__ as pillow_version
    validate(source)
    pid, vid, page_id, block_id, line_id = [identifier(descriptor[k]) for k in ("pieceId", "versionId", "pageId", "blockId", "lineId")]
    pieces = index(source["pieces"], "piece")
    if pid not in pieces:
        raise Invalid("photo ingest attaches only to an explicit existing piece")
    piece_index = source["order"]["pieces"].index(pid)
    version_index = len(pieces[pid]["versionIds"])
    for name, value in (("versions", vid), ("pages", page_id), ("blocks", block_id), ("lines", line_id)):
        if value in index(source[name], name):
            raise Invalid("photo ingest ID collision")
    raw = read_bytes(photo)
    with Image.open(io.BytesIO(raw)) as opened:
        if opened.format != "JPEG" or opened.width * opened.height > 40_000_000:
            raise Invalid("photo ingest requires a bounded JPEG")
        image = opened.convert("RGB")
        width, height = image.size
    updated = copy.deepcopy(source)
    master = "source/ingest/" + page_id + "/original.jpg"
    assets = {master: raw, "site/img/p/" + page_id + ".jpg": raw}
    master_id = "asset:" + master
    updated["assets"].append(asset_record(master, raw, page_id=page_id, role="preserved-photo-ingest",
                                         recipe={"operation": "byte-preserving-copy", "status": "known"}))
    updated["assets"].append(asset_record("site/img/p/" + page_id + ".jpg", raw, page_id=page_id,
                                         source_ids=[master_id], role="preserved-jpeg-master",
                                         recipe={"operation": "byte-preserving-copy", "status": "known"}))
    for folder, extent in (("site/img/i", 1600), ("site/img/m", 800), ("studio/img/thumbs", 240)):
        display = image.copy()
        display.thumbnail((extent, extent), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        display.save(buffer, "JPEG", quality=90, subsampling=0, optimize=False)
        path = folder + "/" + page_id + ".jpg"
        assets[path] = buffer.getvalue()
        updated["assets"].append(asset_record(path, assets[path], page_id=page_id, source_ids=[master_id], role="display-derivative",
            recipe={"operation": "RGB-thumbnail-JPEG", "maxExtent": extent, "resample": "LANCZOS", "quality": 90,
                    "subsampling": 0, "optimize": False, "metadata": "omitted", "pillow": pillow_version, "status": "known"}))
    updated["pages"].append({"id": page_id, "blockIds": [block_id], "geometryOrder": [],
        "reader": {"id": page_id, "iw": width, "ih": height, "W": width, "H": height, "c": [0, 0, 1, 1],
                   "sp": None, "u": [], "a": None, "pl": None, "sourceStatus": "staged-untranscribed"},
        "studio": {"id": page_id, "seq": len(source["pages"]) + 1, "w": width, "h": height,
                   "img": "img/" + page_id + ".jpg", "thumb": "img/thumbs/" + page_id + ".jpg", "spread": None,
                   "uncertain": [], "sourceStatus": "staged-untranscribed"},
        "origin": "technical-fixture" if descriptor.get("fixture") is True else "author-supplied-photo-awaiting-review",
        "uncertainty": ["Transcription and line geometry are unavailable."], "cleanedImage": None,
        "imageLineage": {"archivalOriginal": {"status": "supplied-photo-not-an-archival-claim", "assetId": master_id},
                         "preservedMasterAssetId": "asset:site/img/p/" + page_id + ".jpg",
                         "cleanedImage": {"status": "not-created", "assetId": None},
                         "displayAssetIds": ["asset:" + name for name in assets if name.startswith(("site/img/i/", "site/img/m/", "studio/img/thumbs/"))],
                         "relationship": "byte-preserved photo and recorded deterministic display recipes"}})
    updated["blocks"].append({"id": block_id, "pageId": page_id, "lineIds": [line_id], "type": "text",
                              "reader": {"t": 0, "g": [piece_index, version_index, 0], "v": version_index},
                              "studio": {"t": "text", "spread": False, "note": ""}})
    updated["lines"].append({"id": line_id, "pageId": page_id, "blockId": block_id, "originalText": None,
                             "readerOriginalText": None, "transcriptionStatus": "untranscribed", "studio": {},
                             "geometry": {"readerRow": None, "studioBox": None, "status": "unavailable", "reason": "unreviewed-photo-ingest"}})
    index(updated["pieces"], "piece")[pid]["versionIds"].append(vid)
    updated["versions"].append({"id": vid, "pieceId": pid, "members": [{"pageId": page_id, "blockIds": [block_id]}],
                                "reader": {"id": vid, "s": "j", "d": None, "sourceStatus": "staged-untranscribed"}})
    updated["order"]["pages"].append(page_id)
    updated["order"]["studioPages"].append(page_id)
    updated["reader"].setdefault("groups", []).append([page_id])
    for item in updated["studio"].get("items", []):
        if item.get("id") == pid:
            item.setdefault("versions", []).append({"page": page_id, "blocks": [0]})
    validate(updated)
    return updated, assets


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capture")
    sub.add_parser("validate")
    review = sub.add_parser("apply-reviews")
    review.add_argument("--db", type=Path, required=True)
    review.add_argument("--apply", action="store_true")
    review.add_argument("--backup", type=Path)
    build = sub.add_parser("rebuild")
    build.add_argument("--write", action="store_true")
    build.add_argument("--out", type=Path)
    save = sub.add_parser("backup")
    save.add_argument("--db", type=Path, required=True)
    save.add_argument("--out", type=Path, required=True)
    recover = sub.add_parser("restore")
    recover.add_argument("snapshot", type=Path)
    recover.add_argument("--out", type=Path, required=True)
    photo = sub.add_parser("ingest-photo")
    photo.add_argument("descriptor", type=Path)
    photo.add_argument("photo", type=Path)
    photo.add_argument("--db", type=Path, required=True)
    photo.add_argument("--apply", action="store_true")
    photo.add_argument("--backup", type=Path)
    args = parser.parse_args(argv)
    try:
        path = args.root / CANONICAL
        if args.command == "capture":
            if no_links(path).exists():
                raise Invalid("canonical source already exists; capture cannot replace it")
            source = reconstruct(args.root)
            atomic_write(path, encoded(source))
            result = {"captured": CANONICAL, "counts": validate(source)}
        elif args.command == "restore":
            result = restore(args.snapshot, args.out)
        else:
            source = read_json(path)
            if args.command == "validate":
                result = validate(source)
                for asset in source["assets"]:
                    if sha(read_bytes(args.root / asset["path"])) != asset["sha256"]:
                        raise Invalid("image lineage hash mismatch: " + asset["path"])
                result["verifiedAssets"] = len(source["assets"])
            elif args.command == "apply-reviews":
                updated, result = apply_reviews(source, args.db)
                result["mode"] = "apply" if args.apply else "dry-run"
                if args.apply:
                    result["application"] = commit_proposal(args.root, args.db, updated, args.backup, expected_digest=digest(source))
            elif args.command == "rebuild":
                result = rebuild(source, args.out or args.root, write=args.write)
            elif args.command == "backup":
                result = backup(args.root, args.db, args.out)
            elif args.command == "ingest-photo":
                updated, assets = stage_photo(source, read_json(args.descriptor), args.photo)
                result = {"mode": "apply" if args.apply else "dry-run", "counts": validate(updated),
                          "newAssets": [{"path": name, "sha256": sha(data)} for name, data in assets.items()], "authorClearance": None}
                if args.apply:
                    result["application"] = commit_proposal(args.root, args.db, updated, args.backup, assets=assets, expected_digest=digest(source))
        if args.report:
            atomic_write(args.report, encoded(result))
        print(encoded(result).decode("utf-8"), end="")
        return 0
    except (Invalid, OSError, KeyError, TypeError, ValueError) as error:
        print("Source operation refused: " + str(error), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
