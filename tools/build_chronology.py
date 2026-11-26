#!/usr/bin/env python3
"""Stage 3 chronological amalgamation for journal-handwritten-web.

Reads only confirmed links from ``source/witness_links.json`` plus the
authoritative physical page order in ``site/data/j.json`` and the preserved
masters in ``source/canonical.json``, then writes a public-safe
``source/chronology.json``.

Two-Clock Rule: ``digitized_at`` is scan-batch metadata only.  It is copied
verbatim into the output as provenance; it is NEVER read, parsed, or compared
while computing any composition window, estimate, anchor, or sort key.  All
composition dates come exclusively from confirmed photo ``witnessed_at``
values (and, for interleaving, confirmed note ``created_at`` values).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "versforms.chronology.v1"
DEFAULT_DIGITIZED_AT = "2015-09"

# Public-repo hygiene: these keys must never reach source/chronology.json.
FORBIDDEN_PUBLIC_KEYS = frozenset({
    "plaintext",
    "title",
    "folder",
    "local_path",
    "ocr_text",
    "text",
    "lines",
    "snippet",
    "snippets",
    "raw_text",
    "albums",
    "keywords",
    "original_filename",
})


def _parse_iso_dt(value: str) -> datetime:
    """Parse an ISO-8601 timestamp; tolerate a trailing Z and missing offset."""
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("empty timestamp")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _iso_seconds(dt: datetime) -> str:
    """Render a datetime as the sortable second-resolution prefix.

    The offset supplied by the witness is intentionally preserved in the
    rendered wall-clock time (the chronology contract uses naive sort keys).
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


class CorpusIndex:
    """Authoritative page/piece index built from j.json and canonical.json."""

    def __init__(self, j_path: Path, canonical_path: Path) -> None:
        if not j_path.is_file():
            raise FileNotFoundError(f"Missing corpus file: {j_path}")
        if not canonical_path.is_file():
            raise FileNotFoundError(f"Missing canonical file: {canonical_path}")
        self.j_data: dict[str, Any] = json.loads(j_path.read_text(encoding="utf-8"))
        self.canonical_data: dict[str, Any] = json.loads(
            canonical_path.read_text(encoding="utf-8")
        )
        if "pages" not in self.j_data or "pieces" not in self.j_data:
            raise ValueError("Malformed j.json: missing 'pages' or 'pieces'")

        self.pages: list[dict[str, Any]] = self.j_data["pages"]
        self.page_by_id: dict[str, dict[str, Any]] = {
            p["id"]: p for p in self.pages
        }
        self.page_order: dict[str, int] = {
            p["id"]: idx for idx, p in enumerate(self.pages)
        }
        self.pieces: list[dict[str, Any]] = self.j_data["pieces"]
        self.piece_by_id: dict[str, dict[str, Any]] = {
            p["id"]: p for p in self.pieces
        }

        self.canonical_masters: dict[str, str] = {
            a["pageId"]: a["sha256"]
            for a in self.canonical_data.get("assets", [])
            if a.get("role") == "preserved-jpeg-master" and a.get("pageId")
        }

        page_pieces: dict[str, set[str]] = {p["id"]: set() for p in self.pages}
        for piece in self.pieces:
            for version in piece.get("V", []):
                for page_id, _blocks in version.get("P", []):
                    if page_id in page_pieces:
                        page_pieces[page_id].add(piece["id"])
        self.multi_piece_pages: dict[str, list[str]] = {
            page_id: sorted(ids)
            for page_id, ids in page_pieces.items()
            if len(ids) > 1
        }

        self.spread_exposed_pages: dict[str, Any] = {}
        for page in self.pages:
            spread = page.get("sp") or {}
            if spread.get("f") or spread.get("s") == "whole spread" or spread.get("cb") is None:
                self.spread_exposed_pages[page["id"]] = spread

    def primary_surface(self, piece_id: str) -> str:
        """Primary codex surface for a piece (its preferred version's first page)."""
        piece = self.piece_by_id[piece_id]
        versions = piece.get("V", [])
        if not versions:
            raise ValueError(f"Piece {piece_id} has no versions")
        top_index = int(piece.get("top", 0))
        version = versions[top_index if 0 <= top_index < len(versions) else 0]
        placements = version.get("P", [])
        if not placements:
            raise ValueError(f"Piece {piece_id} preferred version has no page placement")
        return str(placements[0][0])

    def surface_index(self, surface_id: str) -> int:
        if surface_id not in self.page_order:
            raise ValueError(f"Unknown codex surface {surface_id!r}")
        return self.page_order[surface_id]

    def piece_block_bbox(
        self,
        piece_id: str,
        page_id: str,
        version_id: str | None = None,
        pad: int = 8,
    ) -> tuple[int, int, int, int] | None:
        """Pixel crop box [left, top, right, bottom] for a piece's blocks."""
        piece = self.piece_by_id[piece_id]
        versions = piece.get("V", [])
        version = None
        if version_id is not None:
            version = next((v for v in versions if v.get("id") == version_id), None)
        else:
            for candidate in versions:
                if any(p == page_id for p, _ in candidate.get("P", [])):
                    version = candidate
                    break
        if version is None:
            return None
        target_blocks: set[int] = set()
        for placed_page, block_indices in version.get("P", []):
            if placed_page == page_id:
                target_blocks.update(block_indices)
        page = self.page_by_id[page_id]
        iw, ih = int(page["iw"]), int(page["ih"])
        rows = [row for row in page.get("x", []) if row[0] in target_blocks]
        if not rows:
            return None
        x0 = max(0, int(min(r[2] for r in rows) * iw) - pad)
        y0 = max(0, int(min(r[3] for r in rows) * ih) - pad)
        x1 = min(iw, int(max(r[4] for r in rows) * iw) + pad)
        y1 = min(ih, int(max(r[5] for r in rows) * ih) + pad)
        if x1 <= x0 or y1 <= y0:
            return None
        return (x0, y0, x1, y1)


def validate_public_payload(obj: Any, path: str = "$") -> None:
    """Recursively reject keys that belong only to external private custody."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in FORBIDDEN_PUBLIC_KEYS:
                raise ValueError(f"privacy violation: forbidden key {key!r} at {path}")
            validate_public_payload(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            validate_public_payload(item, f"{path}[{idx}]")


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def load_links(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing links file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("witness_links.json must be a JSON object")
    for key in ("photo_links", "note_links"):
        if key in data and not isinstance(data[key], list):
            raise ValueError(f"witness_links.json {key} must be a list")
    return data


def collect_witnesses(links: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Collect only status=='confirmed' witnesses; drop all other fields.

    Returns (photos_by_piece, notes_by_piece, all_confirmed_notes).
    """
    photos_by_piece: dict[str, list[dict[str, Any]]] = {}
    for entry in links.get("photo_links", []):
        if entry.get("status") != "confirmed":
            continue
        piece_id = entry.get("confirmed_piece_id")
        if not isinstance(piece_id, str) or not piece_id:
            continue
        record = {
            "photo_id": str(entry.get("photo_id") or ""),
            "photo_uuid": str(entry.get("photo_uuid") or ""),
            "photo_sha256": str(entry.get("photo_sha256") or ""),
            "witnessed_at": str(entry.get("witnessed_at") or ""),
            "camera_model": str(entry.get("camera_model") or ""),
            "textual_state": str(entry.get("textual_state") or "matches_scan"),
        }
        photos_by_piece.setdefault(piece_id, []).append(record)

    notes_by_piece: dict[str, list[dict[str, Any]]] = {}
    confirmed_notes: list[dict[str, Any]] = []
    for entry in links.get("note_links", []):
        if entry.get("status") != "confirmed":
            continue
        record = {
            "note_id": str(entry.get("note_id") or ""),
            "created_at": str(entry.get("created_at") or ""),
            "modified_at": str(entry.get("modified_at") or ""),
            "relation": str(entry.get("relation") or "standalone_cohort"),
        }
        confirmed_notes.append(record)
        piece_id = entry.get("confirmed_piece_id")
        if isinstance(piece_id, str) and piece_id:
            notes_by_piece.setdefault(piece_id, []).append(record)
    return photos_by_piece, notes_by_piece, confirmed_notes


def build_chronology(
    links: dict[str, Any],
    corpus: CorpusIndex,
    digitized_at: str,
) -> dict[str, Any]:
    photos_by_piece, notes_by_piece, confirmed_notes = collect_witnesses(links)

    piece_surface: dict[str, str] = {}
    piece_index: dict[str, int] = {}
    for piece in corpus.pieces:
        piece_id = piece["id"]
        surface = corpus.primary_surface(piece_id)
        piece_surface[piece_id] = surface
        piece_index[piece_id] = corpus.surface_index(surface)

    # Page-level anchors come only from confirmed photos.
    anchors_by_index: dict[int, tuple[datetime, str]] = {}
    for piece_id, photo_witnesses in photos_by_piece.items():
        if piece_id not in piece_index:
            continue
        idx = piece_index[piece_id]
        dated = []
        for witness in photo_witnesses:
            try:
                dated.append((_parse_iso_dt(witness["witnessed_at"]), witness))
            except ValueError:
                continue
        if not dated:
            continue
        earliest_dt, earliest = min(dated, key=lambda pair: pair[0])
        if idx not in anchors_by_index or earliest_dt < anchors_by_index[idx][0]:
            anchors_by_index[idx] = (earliest_dt, earliest["photo_id"])

    sorted_anchors = sorted(anchors_by_index.items(), key=lambda pair: pair[0])
    velocity_days = 0.0
    if len(sorted_anchors) >= 2:
        first_idx, (first_dt, _) = sorted_anchors[0]
        last_idx, (last_dt, _) = sorted_anchors[-1]
        if last_idx > first_idx:
            raw_days = (last_dt - first_dt).total_seconds() / 86400.0
            velocity_days = max(0.0, raw_days / float(last_idx - first_idx))
        elif not math.isfinite(velocity_days):  # pragma: no cover - defensive
            velocity_days = 0.0

    codex_entries: list[dict[str, Any]] = []
    amalgamated: list[dict[str, Any]] = []

    ordered_pieces = sorted(
        corpus.pieces, key=lambda p: (piece_index[p["id"]], p["id"])
    )
    for piece in ordered_pieces:
        piece_id = piece["id"]
        surface = piece_surface[piece_id]
        idx = piece_index[piece_id]
        photo_witnesses = photos_by_piece.get(piece_id, [])
        linked_notes = notes_by_piece.get(piece_id, [])

        if idx in anchors_by_index:
            anchor_dt, anchor_id = anchors_by_index[idx]
            prev_anchor = next(
                (item[1][1] for item in reversed(sorted_anchors) if item[0] < idx),
                None,
            )
            next_anchor = next(
                (item[1][1] for item in sorted_anchors if item[0] > idx),
                None,
            )
            date_basis = "photo_anchored"
            est_start = (anchor_dt - timedelta(days=4)).strftime("%Y-%m-%d")
            est_end = anchor_dt.strftime("%Y-%m-%d")
            sort_timestamp = _iso_seconds(anchor_dt)
        elif not sorted_anchors:
            date_basis = "undated"
            est_start = None
            est_end = None
            prev_anchor = None
            next_anchor = None
            sort_timestamp = f"undated#{idx:03d}"
        else:
            previous = [item for item in sorted_anchors if item[0] < idx]
            following = [item for item in sorted_anchors if item[0] > idx]
            if previous and following:
                a_idx, (a_dt, a_id) = previous[-1]
                b_idx, (b_dt, b_id) = following[0]
                fraction = (idx - a_idx) / float(b_idx - a_idx)
                low_dt, high_dt = (a_dt, b_dt) if a_dt <= b_dt else (b_dt, a_dt)
                span = (high_dt - low_dt).total_seconds() * fraction
                estimate_dt = low_dt + timedelta(seconds=span)
                date_basis = "interpolated"
                est_start = low_dt.strftime("%Y-%m-%d")
                est_end = high_dt.strftime("%Y-%m-%d")
                prev_anchor = a_id
                next_anchor = b_id
                sort_timestamp = _iso_seconds(estimate_dt)
            elif following:
                b_idx, (b_dt, b_id) = following[0]
                date_basis = "extrapolated_head"
                prev_anchor = None
                next_anchor = b_id
                if len(sorted_anchors) >= 2:
                    estimate_dt = b_dt - timedelta(days=velocity_days * (b_idx - idx))
                    est_start = estimate_dt.strftime("%Y-%m-%d")
                    est_end = est_start
                    sort_timestamp = _iso_seconds(estimate_dt)
                else:
                    est_start = None
                    est_end = None
                    sort_timestamp = f"undated#{idx:03d}"
            else:
                a_idx, (a_dt, a_id) = previous[-1]
                date_basis = "extrapolated_tail"
                prev_anchor = a_id
                next_anchor = None
                if len(sorted_anchors) >= 2:
                    estimate_dt = a_dt + timedelta(days=velocity_days * (idx - a_idx))
                    est_start = estimate_dt.strftime("%Y-%m-%d")
                    est_end = est_start
                    sort_timestamp = _iso_seconds(estimate_dt)
                else:
                    est_start = None
                    est_end = None
                    sort_timestamp = f"undated#{idx:03d}"

        sort_key = f"{sort_timestamp}#{piece_id}"
        entry = {
            "piece_id": piece_id,
            "witnesses": {
                "codex_scan": {
                    "surface_id": surface,
                    "scan_sha256": corpus.canonical_masters.get(surface, ""),
                    "digitized_at": digitized_at,
                    "shared_surface": surface in corpus.multi_piece_pages,
                },
                "photo_witnesses": photo_witnesses,
                "linked_ios_notes": linked_notes,
            },
            "chronology": {
                "date_basis": date_basis,
                "est_start": est_start,
                "est_end": est_end,
                "anchor_prev": prev_anchor,
                "anchor_next": next_anchor,
                "amalgamated_sort_key": sort_key,
            },
        }
        codex_entries.append(entry)
        amalgamated.append(
            {
                "entry_type": "piece",
                "sort_key": sort_key,
                "piece_id": piece_id,
                "surface_id": surface,
                "date_basis": date_basis,
            }
        )

    note_piece_by_id = {
        str(entry.get("note_id") or ""): entry.get("confirmed_piece_id")
        for entry in links.get("note_links", [])
        if entry.get("status") == "confirmed"
    }
    for note in confirmed_notes:
        try:
            created = _iso_seconds(_parse_iso_dt(note["created_at"]))
        except ValueError:
            created = "undated"
        linked_piece = note_piece_by_id.get(note["note_id"])
        amalgamated.append(
            {
                "entry_type": "ios_note",
                "sort_key": f"{created}#{note['note_id']}",
                "note_id": note["note_id"],
                "piece_id": linked_piece if isinstance(linked_piece, str) and linked_piece else None,
                "relation": note["relation"],
            }
        )

    amalgamated.sort(
        key=lambda item: (
            1 if str(item["sort_key"]).startswith("undated#") else 0,
            str(item["sort_key"]),
        )
    )

    payload = {
        "schema": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "digitized_at": digitized_at,
        "physical_codex_order": codex_entries,
        "amalgamated_chronological_order": amalgamated,
    }
    validate_public_payload(payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--links",
        type=Path,
        default=ROOT / "source" / "witness_links.json",
        help="Public-safe witness links JSON (default: source/witness_links.json)",
    )
    parser.add_argument(
        "--j-json",
        type=Path,
        default=ROOT / "site" / "data" / "j.json",
        help="Physical codex corpus (default: site/data/j.json)",
    )
    parser.add_argument(
        "--canonical",
        type=Path,
        default=ROOT / "source" / "canonical.json",
        help="Preserved masters for scan digests (default: source/canonical.json)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "source" / "chronology.json",
        help="Output chronology JSON (default: source/chronology.json)",
    )
    parser.add_argument(
        "--digitized-at",
        default=DEFAULT_DIGITIZED_AT,
        help="Scan-batch provenance label; NEVER a composition bound",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        links = load_links(args.links)
        corpus = CorpusIndex(args.j_json, args.canonical)
        payload = build_chronology(links, corpus, args.digitized_at)
    except Exception as exc:
        print(f"error: failed to build chronology: {exc}", file=sys.stderr)
        return 2
    try:
        atomic_write_text(args.out, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    except OSError as exc:
        print(f"error: could not write {args.out}: {exc}", file=sys.stderr)
        return 2
    codex = payload["physical_codex_order"]
    bases: dict[str, int] = {}
    for entry in codex:
        basis = entry["chronology"]["date_basis"]
        bases[basis] = bases.get(basis, 0) + 1
    summary = ", ".join(f"{key}={value}" for key, value in sorted(bases.items()))
    print(f"Wrote {args.out}: {len(codex)} pieces ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
