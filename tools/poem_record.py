#!/usr/bin/env python3
"""Per-poem record: one canonical record per piece (journal-handwritten-web #31).

The record joins the four stores that today hold a poem's facts apart:
site/data/j.json (transcript), studio/data/review.json (page review, uncertain
readings), studio/data/notes-versions.json (version pointers), and the Studio DB
export (release/pool, reviews, GRUW batches/decisions, notes). It is derived
read-only: no source is written, and the record fails loudly on a missing source
or a sha mismatch (the same fail-loud pattern as tools/release_contract.py).

The record is private: it lives under studio/data/ and is never emitted into
build_public.py output, because its notes.textual field is the per-poem private
factual source dossier (transcription-derived notes, kept apart from the
author's explanatory notes).

Field names are compatible with the #62 tracker packet schema: the tracker
consumes title, pool, verified, batch_status (filed/registered) and exposures.

Usage:
  python3 tools/poem_record.py --piece p001 [--db DIR | --merge-exports] [--root DIR]
  python3 tools/poem_record.py --all [--db DIR | --merge-exports] [--out FILE]
  python3 tools/poem_record.py --validate FILE [--db DIR | --merge-exports]
  python3 tools/poem_record.py --check FILE
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

SCHEMA_ID = "versforms.poem-record.v1"
COLLECTION_ID = "versforms.poem-record-collection.v1"
DB_COLLECTIONS = ["release", "reviews", "batches", "decisions", "versions",
                  "rconfig", "parts", "composites", "notes"]
EXPORT_FRAGMENTS = ["exports/studio-db-2026-11-05",
                    "exports/derived-decisions-2026-11-05",
                    "exports/studio-db-delta-2026-11-14",
                    "exports/studio-db-pre-series-order-2026-11-14",
                    "exports/studio-db-pre-series-order-p006-p010-2026-11-15"]
SCHEMA_PATH = ROOT / "schemas" / "poem-record.schema.json"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
NOTE_KINDS = ("footnote", "endnote", "reflection", "research-dossier",
              "critical-note", "factual-citation")
AUTHOR_KINDS = ("footnote", "endnote", "reflection", "critical-note")
REQUIRED = ["schema", "id", "pool", "transcript_sha", "verified", "versions",
            "notes", "alt_text", "gruw_filed", "publish_at", "release_number",
            "sources"]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_digest(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path, what):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"missing source: {what} ({path})")
    return json.loads(path.read_text(encoding="utf-8"))


def page_label(page_id):
    """The reader's label: site/index.html `id.replace(/^diary/, '')`."""
    return re.sub(r"^diary", "", page_id)


def load_db(db_dir):
    """COLLECTION/ID.json layout, as tools/release_readiness.mjs loadDb reads it."""
    db = {c: {} for c in DB_COLLECTIONS}
    db_dir = Path(db_dir)
    if not db_dir.is_dir():
        raise ValueError(f"missing DB export directory: {db_dir}")
    for coll in DB_COLLECTIONS:
        d = db_dir / coll
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            db[coll][f.stem] = json.loads(f.read_text(encoding="utf-8"))
    return db


def merge_export_fragments(root, out_dir=None):
    """Merge the checked-in Studio DB export fragments into one DB dir.

    Fragments are partial snapshots (one has reviews, another the release
    docs); later fragments win on conflicting documents. Returns
    (out_dir, [fragment names used]). The merged DB is only as fresh as the
    newest fragment, and says so in the record's db_fragments.
    """
    root = Path(root)
    dest = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="jhw-merged-db-"))
    used = []
    for frag in EXPORT_FRAGMENTS:
        src = root / frag
        if not src.is_dir():
            continue
        used.append(frag)
        for coll in src.iterdir():
            if not coll.is_dir():
                continue
            target = dest / coll.name
            target.mkdir(parents=True, exist_ok=True)
            for doc in sorted(coll.glob("*.json")):
                (target / doc.name).write_bytes(doc.read_bytes())
    return dest, used


def load_schedule(root):
    """release/schedule.json: {piece_id: 'YYYY-MM-DD'}; empty when nothing is scheduled."""
    path = Path(root) / "release" / "schedule.json"
    if not path.is_file():
        raise ValueError(f"missing source: release/schedule.json ({path})")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("release/schedule.json must be an object {piece_id: 'YYYY-MM-DD'}")
    for pid, date in data.items():
        if not isinstance(date, str) or not DATE_RE.match(date):
            raise ValueError(f"release/schedule.json: bad publish_at for {pid}: {date!r}")
    return data


def line_set(j, review, pid):
    """The reviewed line set for a piece, mirroring tools/release_readiness.mjs
    reviewProgress: the review item's versions list the reviewed blocks; fall
    back to the j.json top version when the piece has no review item."""
    pages = {p["id"]: p for p in j["pages"]}
    item = next((i for i in review.get("items", []) if i["id"] == pid), None)
    if item is not None:
        rpages = {p["id"]: p for p in review["pages"]}
        lines = []
        for v in item["versions"]:
            rp = rpages.get(v["page"])
            if rp is None:
                raise ValueError(f"{pid}: review item names missing page {v['page']}")
            for b in v["blocks"]:
                block = rp["blocks"][b]
                for line in block["lines"]:
                    lines.append((v["page"], b, line["id"]))
        return lines, "review", (item.get("first") or "")
    piece = next((p for p in j["pieces"] if p["id"] == pid), None)
    if piece is None:
        raise ValueError(f"unknown piece: {pid}")
    top = piece["V"][piece["top"]]
    lines = []
    for pg, blocks in top["P"]:
        page = pages.get(pg)
        if page is None:
            raise ValueError(f"{pid}: top version names missing page {pg}")
        for b in blocks:
            for li in range(len(page["B"][b]["L"])):
                lines.append((pg, b, f"{pg}-{b}-{li}"))
    return lines, "top-version", ""


def build_record(root, db, schedule, pid):
    from post_poem import pool_of

    root = Path(root)
    j_path = root / "site" / "data" / "j.json"
    review_path = root / "studio" / "data" / "review.json"
    nv_path = root / "studio" / "data" / "notes-versions.json"
    j = load_json(j_path, "site/data/j.json")
    review = load_json(review_path, "studio/data/review.json")
    notes_versions = load_json(nv_path, "studio/data/notes-versions.json")

    piece = next((p for p in j["pieces"] if p["id"] == pid), None)
    if piece is None:
        raise ValueError(f"unknown piece: {pid}")
    if pid in schedule:
        pass  # scheduled pieces are built like any other; publish_at is input
    pages = {p["id"]: p for p in j["pages"]}
    rpages = {p["id"]: p for p in review["pages"]}

    # versions: j.json is authoritative; notes-versions.json must agree.
    version_ids = [v["id"] for v in piece["V"]]
    nv_piece = next((p for p in notes_versions["pieces"] if p["id"] == pid), None)
    if nv_piece is None:
        raise ValueError(f"{pid}: missing from studio/data/notes-versions.json")
    nv_ids = [v["id"] for v in nv_piece["V"]]
    if nv_ids != version_ids:
        raise ValueError(f"{pid}: notes-versions versions {nv_ids} != j.json versions {version_ids}")

    lines, lines_source, first = line_set(j, review, pid)
    seen = set()
    transcript_lines = []
    confirmed = 0
    for pg, b, line_id in lines:
        if line_id in seen:
            continue
        seen.add(line_id)
        page = pages.get(pg)
        if page is None:
            raise ValueError(f"{pid}: line set names missing page {pg}")
        try:
            text = page["B"][b]["L"][int(line_id.rsplit("-", 1)[1])]
        except (IndexError, ValueError):
            raise ValueError(f"{pid}: line {line_id} not in site/data/j.json")
        doc = (db or {}).get("reviews", {}).get(line_id)
        if doc is not None and doc.get("status") in ("confirmed", "corrected"):
            if doc.get("status") == "corrected":
                if not isinstance(doc.get("text"), str):
                    raise ValueError(f"{pid}: corrected review {line_id} has no text")
                text = doc["text"]
            confirmed += 1
        transcript_lines.append({"lineId": line_id, "text": text})
    transcript_sha = digest({"id": pid, "lines_source": lines_source, "lines": transcript_lines})

    verified = bool(db) and confirmed == len(transcript_lines) and len(transcript_lines) > 0
    if db is None:
        verified_source = "none"
    else:
        verified_source = "db"

    # pool: the Studio's exact values only, via post_poem.pool_of (the #65 rule).
    if db is None:
        pool, pool_source = "unsorted", "none"
    else:
        pool, pool_source = pool_of(db, pid), "db"

    # GRUW: a filed/registered batch, or the recorded gruw-policy skip.
    gruw_filed, batch_status = False, "none"
    if db is not None:
        if (db.get("decisions", {}).get("gruw-policy") or {}).get("choice") == "skip":
            gruw_filed, batch_status = True, "skip"
        else:
            for b in db.get("batches", {}).values():
                if isinstance(b, dict) and pid in (b.get("items") or []) and b.get("status") in ("filed", "registered"):
                    gruw_filed, batch_status = True, b["status"]
                    break

    # alt text: one derived label per page in the line set.
    page_ids = sorted({pg for pg, _, _ in lines})
    alt_text = {}
    for pg in page_ids:
        label = page_label(pg)
        if not label:
            raise ValueError(f"{pid}: page {pg} has no alt label")
        alt_text[pg] = f"Page {label}"

    # notes: generated textual half (the private dossier) vs author-written half.
    textual = []
    for pg in page_ids:
        for note in (rpages.get(pg) or {}).get("uncertain") or []:
            textual.append({"kind": "factual-citation", "page": pg, "text": note})
        for line in transcript_lines:
            if line["lineId"].startswith(pg + "-"):
                textual.append({"kind": "research-dossier", "lineId": line["lineId"],
                                "page": pg, "text": line["text"]})
    author = []
    if db is not None:
        for doc in (db.get("notes") or {}).values():
            if not isinstance(doc, dict):
                continue
            anchor = doc.get("anchor") or {}
            if (anchor.get("pieceId") or doc.get("pieceId")) != pid:
                continue
            kind = doc.get("kind")
            if kind in AUTHOR_KINDS:
                author.append({"kind": kind, "lineId": anchor.get("lineId"),
                               "text": doc.get("text") or doc.get("body") or ""})

    release_doc = (db or {}).get("release", {}).get(pid) or {}
    record = {
        "schema": SCHEMA_ID,
        "id": pid,
        "pool": pool,
        "pool_source": pool_source,
        "transcript_sha": transcript_sha,
        "verified": verified,
        "verified_source": verified_source,
        "versions": version_ids,
        "lines": len(transcript_lines),
        "lines_source": lines_source,
        "title": first,
        "notes": {"textual": textual, "author": author},
        "alt_text": alt_text,
        "gruw_filed": gruw_filed,
        "batch_status": batch_status,
        "publish_at": schedule.get(pid),
        "release_number": release_doc.get("num"),
        "exposures": release_doc.get("exposures", []),
        "sources": {
            "site/data/j.json": file_digest(j_path),
            "studio/data/review.json": file_digest(review_path),
            "studio/data/notes-versions.json": file_digest(nv_path),
        },
    }
    return record


def validate_record(record, schema=None):
    """Shape check against the record contract (mirrors the JSON Schema file)."""
    if not isinstance(record, dict):
        raise ValueError("record is not an object")
    for key in REQUIRED:
        if key not in record:
            raise ValueError(f"record {record.get('id')}: missing required {key}")
    if record["schema"] != SCHEMA_ID:
        raise ValueError(f"record {record.get('id')}: bad schema {record['schema']!r}")
    if not re.match(r"^p[0-9]+$", record["id"] or ""):
        raise ValueError(f"bad piece id {record['id']!r}")
    if record["pool"] not in ("series", "reserve", "archive", "unsorted", "unknown"):
        raise ValueError(f"record {record['id']}: bad pool {record['pool']!r}")
    if not SHA_RE.match(record["transcript_sha"] or ""):
        raise ValueError(f"record {record['id']}: bad transcript_sha")
    if not isinstance(record["verified"], bool) or not isinstance(record["gruw_filed"], bool):
        raise ValueError(f"record {record['id']}: verified/gruw_filed must be booleans")
    if record["batch_status"] not in ("filed", "registered", "skip", "none"):
        raise ValueError(f"record {record['id']}: bad batch_status")
    if record["publish_at"] is not None and not DATE_RE.match(record["publish_at"]):
        raise ValueError(f"record {record['id']}: bad publish_at")
    notes = record["notes"]
    if set(notes) != {"textual", "author"}:
        raise ValueError(f"record {record['id']}: notes must have textual + author")
    for entry in notes["textual"]:
        if entry.get("kind") not in ("factual-citation", "research-dossier"):
            raise ValueError(f"record {record['id']}: bad textual note kind {entry.get('kind')!r}")
    for entry in notes["author"]:
        if entry.get("kind") not in AUTHOR_KINDS:
            raise ValueError(f"record {record['id']}: bad author note kind {entry.get('kind')!r}")
    for pg, alt in record["alt_text"].items():
        if not isinstance(alt, str) or not alt:
            raise ValueError(f"record {record['id']}: empty alt text for {pg}")
    for path, sha in record["sources"].items():
        if not SHA_RE.match(sha or ""):
            raise ValueError(f"record {record['id']}: bad source sha for {path}")
    if schema is not None:
        if sorted(schema.get("required", [])) != sorted(REQUIRED):
            raise ValueError("schemas/poem-record.schema.json required[] drifted from this validator")
    return True


def build_all(root, db, schedule):
    j = load_json(Path(root) / "site" / "data" / "j.json", "site/data/j.json")
    records = [build_record(root, db, schedule, p["id"]) for p in j["pieces"]]
    sources = {path: file_digest(Path(root) / path) for path in
               ("site/data/j.json", "studio/data/review.json", "studio/data/notes-versions.json")}
    return {"schema": COLLECTION_ID, "generated_from": sources,
            "pieces": records}


def validate_file(path, root, db, schedule):
    data = load_json(path, "poem records file")
    if data.get("schema") != COLLECTION_ID:
        raise ValueError(f"{path}: bad collection schema {data.get('schema')!r}")
    schema = load_json(SCHEMA_PATH, "schemas/poem-record.schema.json")
    mismatches = []
    for record in data["pieces"]:
        validate_record(record, schema)
        rebuilt = build_record(root, db, schedule, record["id"])
        if canonical(rebuilt) != canonical(record):
            keys = [k for k in record if canonical(record.get(k)) != canonical(rebuilt.get(k))]
            mismatches.append(f"{record['id']}: differs in {keys}")
    if mismatches:
        raise ValueError("records do not match live source:\n" + "\n".join(mismatches))
    return len(data["pieces"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(ROOT), help="repository root")
    ap.add_argument("--db", help="Studio DB export directory (COLLECTION/ID.json)")
    ap.add_argument("--merge-exports", action="store_true",
                    help="merge the checked-in exports/ fragments into a temp DB dir and use it")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--piece", help="build the record for one piece (prints JSON)")
    group.add_argument("--all", action="store_true", help="build records for all pieces")
    group.add_argument("--validate", metavar="FILE", help="recompute every record in FILE and fail on mismatch")
    group.add_argument("--check", metavar="FILE", help="validate the shape of every record in FILE")
    ap.add_argument("--out", help="write output here (default: stdout for --piece, studio/data/poem-records.json for --all)")
    a = ap.parse_args(argv)

    root = Path(a.root).resolve()
    db = None
    if a.merge_exports:
        db_dir, used = merge_export_fragments(root)
        db = load_db(db_dir)
        print(f"merged DB from: {', '.join(used)}", file=sys.stderr)
    elif a.db:
        db = load_db(a.db)
    schedule = load_schedule(root)

    if a.piece:
        record = build_record(root, db, schedule, a.piece)
        validate_record(record)
        out = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        if a.out:
            Path(a.out).write_text(out, encoding="utf-8")
        else:
            print(out, end="")
        return 0
    if a.all:
        data = build_all(root, db, schedule)
        for record in data["pieces"]:
            validate_record(record)
        out = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        dest = Path(a.out) if a.out else root / "studio" / "data" / "poem-records.json"
        dest.write_text(out, encoding="utf-8")
        print(f"wrote {len(data['pieces'])} records to {dest}")
        return 0
    if a.validate:
        n = validate_file(a.validate, root, db, schedule)
        print(f"OK: {n} records match live source")
        return 0
    if a.check:
        data = load_json(a.check, "poem records file")
        schema = load_json(SCHEMA_PATH, "schemas/poem-record.schema.json")
        for record in data["pieces"]:
            validate_record(record, schema)
        print(f"OK: {len(data['pieces'])} records well-formed")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
