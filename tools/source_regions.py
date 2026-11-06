#!/usr/bin/env python3
"""Shared source-region contract, pilot builder and eligibility checks (T08).

The contract is deliberately narrower than the finished product: it describes
source-backed units (poem, stanza, line, word, glyph, mark, combination) with a
piece/version/page/line identity, a scan region, a method and a complete lineage
to the source assets. It does not render anything and does not decide artistic
questions.

    python3 tools/source_regions.py build --atoms PATH [--out PATH]
    python3 tools/source_regions.py verify --manifest PATH [--out PATH]
    python3 tools/source_regions.py lineage --manifest PATH --atom-id ID
    python3 tools/source_regions.py check --manifest PATH --policy PATH \
        --scope private-local [--out PATH] [--require-allowed]

`check` exits 0 when the scope is allowed, 3 when it is refused and 2 on a bad
invocation or unreadable input. `build` never copies transcribed poem text: the
owner's atoms file is read only for boxes, regions, alignments and methods.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable
from source_fingerprint import source_binding

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_SCHEMA = "versforms.source-region-manifest.v1"
POLICY_SCHEMA = "versforms.visibility-policy.v1"
REPORT_SCHEMA = "versforms.source-eligibility-report.v1"
PRIVATE_PREVIEW_SCHEMA = "versforms.private-region-preview.v1"
SCOPES = ("private-local", "author-cut-private", "public-release", "cipher-public")
PRIVATE_SCOPES = {"private-local", "author-cut-private"}
PUBLIC_SCOPES = {"public-release", "cipher-public"}
FORBIDDEN_TEXT_KEYS = {"text", "transcript", "poem_text", "line_text", "word_text"}
# A combination is a derived unit made only from declared source atoms. The
# operation is a record of what the author did, not a generator.
COMBINATION_OPERATIONS = {"cut", "fold-in", "erasure", "cipher", "misread", "borrowed"}
UNITS = {"poem", "stanza", "line", "word", "glyph", "mark", "combination"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def manifest_digest(manifest: dict) -> str:
    """Digest of the whole manifest as written (used for clearance binding)."""
    return canonical_sha256(manifest)


def _source_asset(asset_id: str, path: Path, kind: str, tier: str | None,
                  page_id: str) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    asset = {
        "asset_id": asset_id,
        "kind": kind,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
        "visibility": "private-source",
        "owner": "T02 canonical source contract: docs/contracts/canonical-source.md (2026-11-06)",
        "page_id": page_id,
    }
    if tier:
        asset["tier"] = tier
    return asset


def _bbox(points: Iterable[Iterable[float]]) -> list[float]:
    """Bounding box of points ([x, y], ...)."""
    pts = [tuple(p) for p in points]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return [min(xs), min(ys), max(xs), max(ys)]


def _union_bbox(boxes: Iterable[Iterable[float]]) -> list[float]:
    """Union of [x0, y0, x1, y1] boxes."""
    boxes = [tuple(b) for b in boxes]
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _line_atom_id(piece: str, version: str, page: str, block: int, line: int) -> str:
    return f"vf:atom:{piece}/{version}/{page}/line-{block}-{line}"


def _word_atom_id(line: str, ordinal: int) -> str:
    return f"{line}/word-{ordinal}"


def _glyph_atom_id(word: str, ordinal: int) -> str:
    return f"{word}/glyph-{ordinal}"


def _mark_atom_id(line: str, ordinal: int) -> str:
    return f"{line}/mark-{ordinal}"


def _stanza_atom_id(piece: str, version: str, page: str, stanza: int) -> str:
    return f"vf:atom:{piece}/{version}/{page}/stanza-{stanza}"


def _poem_atom_id(piece: str, version: str) -> str:
    return f"vf:atom:{piece}/{version}/poem"


def _author_boxes(page: dict) -> dict[tuple[int, int], list[float]]:
    iw, ih = page["iw"], page["ih"]
    out: dict[tuple[int, int], list[float]] = {}
    for row in page.get("x", []):
        block, line = int(row[0]), int(row[1])
        out[(block, line)] = [
            round(row[2] * iw, 2), round(row[3] * ih, 2),
            round(row[4] * iw, 2), round(row[5] * ih, 2),
        ]
    return out


def build_manifest(atoms_path: Path, *, atoms_ref: str, atoms_commit: str | None,
                   piece_id: str = "p001", version_id: str | None = None,
                   version_index: int = 0) -> dict:
    """Build a region-only manifest from the owner's atoms artifact.

    Only geometry, identifiers, methods and review/uncertainty *states* cross
    over. Every `text` field in the owner file is dropped here.
    """
    atoms = read_json(atoms_path)
    j = read_json(ROOT / "site/data/j.json")
    piece = next((p for p in j["pieces"] if p["id"] == piece_id), None)
    if piece is None:
        raise ValueError(f"piece {piece_id!r} not in site/data/j.json")
    version = piece["V"][version_index]
    if version_id and version["id"] != version_id:
        raise ValueError(f"version {version_id!r} is not at index {version_index}: {version['id']!r}")
    version_id = version["id"]
    if len(version["P"]) != 1:
        raise ValueError("pilot builder expects one source page per version")
    page_id, blocks = version["P"][0]
    page = next((p for p in j["pages"] if p["id"] == page_id), None)
    if page is None:
        raise ValueError(f"page {page_id!r} not in site/data/j.json")
    meta = atoms.get("meta", {})
    if meta.get("poem") != piece_id or meta.get("version_id") != version_id:
        raise ValueError("atoms artifact does not describe the requested piece/version")

    source_asset_id = f"scan:p/{page_id}"
    source_assets = [
        _source_asset(source_asset_id, ROOT / "site/img/p" / f"{page_id}.jpg",
                      "page-scan", "p", page_id),
    ]
    derivation_id = "derivation:seam-partition-v1"
    methods = [
        {
            "method_id": "method:seam-partition-v1",
            "kind": "ink-partition",
            "implementation": "proto/alive/segment.py (owner branch alive-prototype-wip-final)",
            "implementation_commit": atoms_commit,
            "status": "owner-tested-in-sample",
            "parameters": meta.get("partition", {}).get("parameters", {}),
            "limits": [
                "one page, 22 lines, in-sample parameters; no held-out page",
                "cuts a crossing stroke at the cheapest seam, not at the pen's line",
                "owner withdrew word text on global line 13 until waypoints are traced",
            ],
        },
        {
            "method_id": "method:gap-rule-v1",
            "kind": "word-segmentation",
            "implementation": "proto/alive/build_atoms.py / segment.py (owner branch)",
            "implementation_commit": atoms_commit,
            "status": "owner-tested-in-sample",
            "parameters": {
                "x_height_px": meta.get("parameters", {}).get("x_height_px"),
                "gap_rule": meta.get("parameters", {}).get("gap_rule"),
                "gap_rule_chosen_by": meta.get("parameters", {}).get("gap_rule_chosen_by"),
            },
            "limits": ["18 of 22 lines have word-box count equal to token count; optimistic"],
        },
        {
            "method_id": "method:connected-components-v1",
            "kind": "ink-component-grouping",
            "implementation": "proto/alive/segment.py (owner branch)",
            "implementation_commit": atoms_commit,
            "status": "owner-tested-in-sample",
            "parameters": {
                "speck_px": meta.get("parameters", {}).get("speck_px"),
                "mark_rule": meta.get("parameters", {}).get("mark_rule"),
                "glyph_merge": meta.get("parameters", {}).get("glyph_merge"),
            },
            "limits": ["a glyph is an ink-component group, not a character or a letter"],
        },
        {
            "method_id": "method:union-box-v1",
            "kind": "containment",
            "implementation": "tools/source_regions.py",
            "status": "t08-contract-code",
            "parameters": {"region": "bounding box of child line boxes"},
            "limits": ["no polygon for poem/stanza; use the child line regions for ink"],
        },
    ]

    uncertainties = []
    page_notes = page.get("u") or []
    for i, _note in enumerate(page_notes):
        uncertainties.append({
            "uncertainty_id": f"{page_id}-u{i}",
            "page_id": page_id,
            "line_id": None,
            "kind": "uncertain-reading",
            "status": "open",
            "evidence_ref": f"site/data/j.json#/pages[id={page_id}]/u/{i}",
            "note_scope": "page",
            "mapping_status": "not mapped to a line by T08; the author note names its own place",
        })

    author_boxes = _author_boxes(page)
    poem_atom = _poem_atom_id(piece_id, version_id)
    poem_box = atoms.get("box") or [0, 0, page["iw"], page["ih"]]
    atom_list: list[dict] = [{
        "atom_id": poem_atom,
        "unit": "poem",
        "piece_id": piece_id,
        "version_id": version_id,
        "page_id": page_id,
        "parent_atom_id": None,
        "source_ids": {"piece_id": piece_id, "version_id": version_id},
        "region": {"frame": "source-pixels", "bbox": poem_box, "polygon": None,
                   "method_id": "method:union-box-v1"},
        "source_asset_ids": [source_asset_id],
        "lineage": {
            "parent_atom_id": None,
            "input_atom_ids": [],
            "root_source_asset_ids": [source_asset_id],
            "source_line_ids": [],
            "method_id": "method:union-box-v1",
            "derivation_ids": [derivation_id],
        },
        "reading": {
            "transcription_state": "machine-transcription-unverified",
            "review_state": "not-reviewed-by-author",
            "uncertainty_ids": [u["uncertainty_id"] for u in uncertainties],
            "deliberate_misread": None,
            "text_ref": None,
        },
        "credit": {"origin_kind": "author", "source_atom_ids": [],
                   "credit_required": False, "credit_style": None},
    }]

    structure_floors: list[dict] = []
    global_index = 0
    for stanza_index, stanza in enumerate(atoms.get("stanzas", [])):
        stanza_atom = _stanza_atom_id(piece_id, version_id, page_id, stanza_index)
        line_boxes = [ln["box"] for ln in stanza.get("lines", [])]
        if line_boxes:
            stanza_box = [min(b[0] for b in line_boxes), min(b[1] for b in line_boxes),
                          max(b[2] for b in line_boxes), max(b[3] for b in line_boxes)]
        else:
            stanza_box = [0, 0, 0, 0]
        atom_list.append({
            "atom_id": stanza_atom,
            "unit": "stanza",
            "piece_id": piece_id,
            "version_id": version_id,
            "page_id": page_id,
            "parent_atom_id": poem_atom,
            "source_ids": {"piece_id": piece_id, "version_id": version_id,
                           "page_id": page_id, "block_index": stanza.get("block"),
                           "stanza_index": stanza_index},
            "region": {"frame": "source-pixels", "bbox": stanza_box, "polygon": None,
                       "method_id": "method:union-box-v1"},
            "source_asset_ids": [source_asset_id],
            "lineage": {
                "parent_atom_id": poem_atom,
                "input_atom_ids": [],
                "root_source_asset_ids": [source_asset_id],
                "source_line_ids": [],
                "method_id": "method:union-box-v1",
                "derivation_ids": [derivation_id],
            },
            "reading": {
                "transcription_state": "machine-transcription-unverified",
                "review_state": "not-reviewed-by-author",
                "uncertainty_ids": [],
                "deliberate_misread": None,
                "text_ref": None,
            },
            "credit": {"origin_kind": "author", "source_atom_ids": [],
                       "credit_required": False, "credit_style": None},
        })

        first_line_of_stanza = True
        for owner_line in stanza.get("lines", []):
            block = int(stanza.get("block"))
            line_no = int(owner_line.get("line"))
            line_id = f"{page_id}-{block}-{line_no}"
            line_atom = _line_atom_id(piece_id, version_id, page_id, block, line_no)
            expected_key = owner_line.get("author_box_expected_key")
            author_box = author_boxes.get((block, line_no))
            review_state = "not-reviewed-by-author"
            if owner_line.get("index") == 13:
                review_state = "crop-withdrawn-by-owner-eye-review"
            elif owner_line.get("words_alignment") is None:
                review_state = "word-alignment-unaligned-in-owner-spike"
            else:
                review_state = "word-alignment-in-sample-only"

            atom_list.append({
                "atom_id": line_atom,
                "unit": "line",
                "piece_id": piece_id,
                "version_id": version_id,
                "page_id": page_id,
                "parent_atom_id": stanza_atom,
                "source_ids": {
                    "piece_id": piece_id,
                    "version_id": version_id,
                    "page_id": page_id,
                    "line_id": line_id,
                    "block_index": block,
                    "line_index": line_no,
                    "global_line_index": int(owner_line.get("index")),
                    "author_box_key": expected_key,
                    "owner_atom_ref": f"{atoms_ref}#/stanzas/{stanza_index}/lines/{owner_line.get('line')}",
                },
                "region": {
                    "frame": "source-pixels",
                    "bbox": owner_line["box"],
                    "polygon": owner_line.get("region"),
                    "polygon_frame": "source-pixels",
                    "ink_px": owner_line.get("ink_px"),
                    "method_id": "method:seam-partition-v1",
                },
                "author_box": {
                    "bbox": author_box,
                    "state": "present-in-site-data" if author_box else "missing-in-site-data",
                    "iou_with_owner_box": owner_line.get("author_box_best_iou"),
                    "ink_x1_minus_author_x1": owner_line.get("ink_x1_minus_author_x1"),
                },
                "source_asset_ids": [source_asset_id],
                "lineage": {
                    "parent_atom_id": stanza_atom,
                    "input_atom_ids": [],
                    "root_source_asset_ids": [source_asset_id],
                    "source_line_ids": [line_id],
                    "method_id": "method:seam-partition-v1",
                    "derivation_ids": [derivation_id],
                },
                "reading": {
                    "transcription_state": "machine-transcription-unverified",
                    "review_state": review_state,
                    "uncertainty_ids": [],
                    "deliberate_misread": None,
                    "text_ref": None,
                },
                "credit": {"origin_kind": "author", "source_atom_ids": [],
                           "credit_required": False, "credit_style": None},
                "structure": {
                    "global_line_index": int(owner_line.get("index")),
                    "stanza_index": stanza_index,
                    "stanza_break_before": not first_line_of_stanza,
                    "width_px": round(owner_line["box"][2] - owner_line["box"][0], 2),
                    "height_px": round(owner_line["box"][3] - owner_line["box"][1], 2),
                    "floor_world_height": 64,
                    "floor_gap_world": 2,
                    "stanza_setback_world": 34,
                },
            })
            first_line_of_stanza = False

            for word_index, owner_word in enumerate(owner_line.get("words", [])):
                word_id = _word_atom_id(line_atom, word_index)
                word_state = review_state
                atom_list.append({
                    "atom_id": word_id,
                    "unit": "word",
                    "piece_id": piece_id,
                    "version_id": version_id,
                    "page_id": page_id,
                    "parent_atom_id": line_atom,
                    "source_ids": {"line_id": line_id, "word_ordinal": word_index},
                    "region": {
                        "frame": "source-pixels",
                        "bbox": owner_word["box"],
                        "polygon": None,
                        "method_id": "method:gap-rule-v1",
                    },
                    "source_asset_ids": [source_asset_id],
                    "lineage": {
                        "parent_atom_id": line_atom,
                        "input_atom_ids": [],
                        "root_source_asset_ids": [source_asset_id],
                        "source_line_ids": [line_id],
                        "method_id": "method:gap-rule-v1",
                        "derivation_ids": [derivation_id],
                    },
                    "reading": {
                        "transcription_state": "not-attached-in-this-contract",
                        "review_state": word_state,
                        "uncertainty_ids": [],
                        "deliberate_misread": None,
                        "text_ref": None,
                    },
                    "credit": {"origin_kind": "author", "source_atom_ids": [],
                               "credit_required": False, "credit_style": None},
                })
                for glyph_index, owner_glyph in enumerate(owner_word.get("glyphs", [])):
                    atom_list.append({
                        "atom_id": _glyph_atom_id(word_id, glyph_index),
                        "unit": "glyph",
                        "piece_id": piece_id,
                        "version_id": version_id,
                        "page_id": page_id,
                        "parent_atom_id": word_id,
                        "source_ids": {"line_id": line_id, "word_ordinal": word_index,
                                       "glyph_ordinal": glyph_index},
                        "region": {
                            "frame": "source-pixels",
                            "bbox": owner_glyph["box"],
                            "polygon": None,
                            "ink_px": owner_glyph.get("ink_px"),
                            "components": owner_glyph.get("components"),
                            "method_id": "method:connected-components-v1",
                        },
                        "source_asset_ids": [source_asset_id],
                        "lineage": {
                            "parent_atom_id": word_id,
                            "input_atom_ids": [],
                            "root_source_asset_ids": [source_asset_id],
                            "source_line_ids": [line_id],
                            "method_id": "method:connected-components-v1",
                            "derivation_ids": [derivation_id],
                        },
                        "reading": {
                            "transcription_state": "not-attached-in-this-contract",
                            "review_state": "ink-component-not-a-character",
                            "uncertainty_ids": [],
                            "deliberate_misread": None,
                            "text_ref": None,
                        },
                        "credit": {"origin_kind": "author", "source_atom_ids": [],
                                   "credit_required": False, "credit_style": None},
                    })
            for mark_index, owner_mark in enumerate(owner_line.get("marks", [])):
                atom_list.append({
                    "atom_id": _mark_atom_id(line_atom, mark_index),
                    "unit": "mark",
                    "piece_id": piece_id,
                    "version_id": version_id,
                    "page_id": page_id,
                    "parent_atom_id": line_atom,
                    "source_ids": {"line_id": line_id, "mark_ordinal": mark_index},
                    "region": {
                        "frame": "source-pixels",
                        "bbox": owner_mark["box"],
                        "polygon": None,
                        "ink_px": owner_mark.get("ink_px"),
                        "method_id": "method:connected-components-v1",
                    },
                    "source_asset_ids": [source_asset_id],
                    "lineage": {
                        "parent_atom_id": line_atom,
                        "input_atom_ids": [],
                        "root_source_asset_ids": [source_asset_id],
                        "source_line_ids": [line_id],
                        "method_id": "method:connected-components-v1",
                        "derivation_ids": [derivation_id],
                    },
                    "reading": {
                        "transcription_state": "not-attached-in-this-contract",
                        "review_state": "ink-mark",
                        "uncertainty_ids": [],
                        "deliberate_misread": None,
                        "text_ref": None,
                    },
                    "credit": {"origin_kind": "author", "source_atom_ids": [],
                               "credit_required": False, "credit_style": None},
                })
            global_index += 1

    # Centered line-length structure from the owner's architecture rule: the
    # building width is the widest line; every floor is that line's width,
    # centered on the building axis. This is data, not a second renderer.
    line_atoms = [a for a in atom_list if a["unit"] == "line"]
    building_width = max(a["structure"]["width_px"] for a in line_atoms)
    for atom in line_atoms:
        st = atom["structure"]
        st["building_width_px"] = building_width
        st["floor_left_px"] = round((building_width - st["width_px"]) / 2, 2)
        st["floor_right_px"] = round(st["floor_left_px"] + st["width_px"], 2)
        st["axis"] = "building-center"
        structure_floors.append({
            "line_atom_id": atom["atom_id"],
            "line_id": atom["source_ids"]["line_id"],
            "global_line_index": st["global_line_index"],
            "stanza_index": st["stanza_index"],
            "stanza_break_before": st["stanza_break_before"],
            "width_px": st["width_px"],
            "height_px": st["height_px"],
            "floor_left_px": st["floor_left_px"],
            "floor_right_px": st["floor_right_px"],
        })

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": "private-pilot",
        "scope": {
            "distribution": "private-local",
            "may_publish": False,
            "serve_on": "127.0.0.1 only",
            "note": "The pilot is evidence, not a release candidate or a product surface.",
        },
        "piece": {
            "piece_id": piece_id,
            "version_id": version_id,
            "version_index": version_index,
            "page_id": page_id,
            "pool": "not-recorded-here",
            "pool_source": "visibility is external, in the T03-style policy file; no author pool decision is invented here",
        },
        "source_assets": source_assets,
        "derivations": [{
            "derivation_id": derivation_id,
            "kind": "ink-partition",
            "artifact_ref": atoms_ref,
            "artifact_commit": atoms_commit,
            "artifact_sha256": sha256_file(atoms_path),
            "owner": "alive-prototype lane (PR #102 / branch alive-prototype-wip-final)",
            "reused_not_reimplemented": True,
            "t08_note": "T08 did not re-run segmentation; it normalises the owner artifact into the shared contract.",
        }],
        "methods": methods,
        "uncertainties": uncertainties,
        "atoms": atom_list,
        "structure": {
            "model": "centered-line-length-v1",
            "author_direction_ref": "docs/chats/2026-11-05-local-session-finish-and-launch.md, Design direction, 2026-11-05",
            "owner_implementation_ref": "proto/alive/alive.js (branch alive-prototype-wip-final), layoutBuildings()",
            "status": "author-directed shape, owner-tested prototype; not a decision about every future crop/font/stroke",
            "axis": "building-center",
            "building_width_px": building_width,
            "floor_world_height": 64,
            "floor_gap_world": 2,
            "stanza_setback_world": 34,
            "floors": structure_floors,
        },
        "counts": {
            "atoms": len(atom_list),
            "poems": 1,
            "stanzas": len(atoms.get("stanzas", [])),
            "lines": len(line_atoms),
            "words": sum(1 for a in atom_list if a["unit"] == "word"),
            "glyphs": sum(1 for a in atom_list if a["unit"] == "glyph"),
            "marks": sum(1 for a in atom_list if a["unit"] == "mark"),
            "uncertainties": len(uncertainties),
        },
    }
    manifest["integrity"] = {"content_sha256": canonical_sha256(manifest)}
    return manifest


def make_combination_atom(manifest: dict, *, atom_id: str, input_atom_ids: list[str],
                          operation: str, method_id: str, origin_kind: str = "author",
                          credit_required: bool = False, credit_style: str | None = None,
                          source_atom_ids: list[str] | None = None,
                          deliberate_misread: dict | None = None,
                          rule: str | None = None, seed: int | None = None,
                          piece_id: str | None = None, version_id: str | None = None,
                          page_id: str | None = None) -> dict:
    """Build one derived `combination` atom from declared source atoms.

    This is the contract shape used by the Cut and Key Sheet follow-on fixtures.
    It never contains text. The caller is responsible for adding the returned
    atom to a manifest with `add_combinations`.
    """
    if operation not in COMBINATION_OPERATIONS:
        raise ValueError(f"unknown combination operation {operation!r}")
    by_id = {a["atom_id"]: a for a in manifest.get("atoms", [])}
    inputs = []
    for input_id in input_atom_ids:
        atom = by_id.get(input_id)
        if atom is None:
            raise KeyError(f"combination input {input_id!r} is not in the manifest")
        inputs.append(atom)
    if not inputs:
        raise ValueError("a combination needs at least one input atom")
    boxes = [a["region"]["bbox"] for a in inputs]
    first = inputs[0]
    roots = sorted({r for a in inputs for r in (a.get("lineage") or {}).get("root_source_asset_ids", [])})
    line_ids = sorted({r for a in inputs for r in (a.get("lineage") or {}).get("source_line_ids", [])})
    uncertainty_ids = sorted({u for a in inputs for u in (a.get("reading") or {}).get("uncertainty_ids", [])})
    atom = {
        "atom_id": atom_id,
        "unit": "combination",
        "piece_id": piece_id or first["piece_id"],
        "version_id": version_id or first["version_id"],
        "page_id": page_id or first["page_id"],
        "parent_atom_id": None,
        "source_ids": {
            "piece_id": piece_id or first["piece_id"],
            "version_id": version_id or first["version_id"],
            "page_id": page_id or first["page_id"],
        },
        "region": {"frame": "source-pixels", "bbox": _union_bbox(boxes), "polygon": None,
                   "method_id": method_id},
        "source_asset_ids": roots,
        "lineage": {
            "parent_atom_id": None,
            "input_atom_ids": list(input_atom_ids),
            "root_source_asset_ids": roots,
            "source_line_ids": line_ids,
            "method_id": method_id,
            "derivation_ids": ["derivation:combination-fixture-v1"],
        },
        "reading": {
            "transcription_state": "not-attached-in-this-contract",
            "review_state": "derived-combination",
            "uncertainty_ids": uncertainty_ids,
            "deliberate_misread": deliberate_misread,
            "text_ref": None,
        },
        "credit": {
            "origin_kind": origin_kind,
            "source_atom_ids": list(source_atom_ids or input_atom_ids),
            "credit_required": credit_required,
            "credit_style": credit_style,
        },
        "combination": {
            "operation": operation,
            "input_atom_ids": list(input_atom_ids),
            "operator": "author" if origin_kind == "author" else "external",
            "rule": rule,
            "seed": seed,
            "text_ref": None,
        },
    }
    return atom


def add_combinations(manifest: dict, atoms: list[dict],
                     methods: list[dict] | None = None) -> dict:
    """Return a copy of a manifest with added combination atoms and methods.

    Counts and the content digest are recomputed so the result is a valid,
    self-contained manifest. Used for the synthetic follow-on fixtures and the
    lineage/credit tests.
    """
    import copy

    out = copy.deepcopy(manifest)
    existing = {m["method_id"] for m in out.get("methods", [])}
    for method in methods or []:
        if method["method_id"] not in existing:
            out.setdefault("methods", []).append(copy.deepcopy(method))
            existing.add(method["method_id"])
    out.setdefault("atoms", []).extend(copy.deepcopy(atoms))
    out["counts"]["atoms"] = len(out["atoms"])
    out.pop("integrity", None)
    out["integrity"] = {"content_sha256": canonical_sha256(out)}
    return out


def _walk_keys(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield f"{path}.{key}", child
            yield from _walk_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from _walk_keys(child, f"{path}[{i}]")


def verify_manifest(manifest: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append(f"schema is {manifest.get('schema')!r}, expected {MANIFEST_SCHEMA!r}")
    for path, child in _walk_keys(manifest):
        key = path.rsplit(".", 1)[-1]
        if key in FORBIDDEN_TEXT_KEYS and child not in (None, ""):
            errors.append(f"transcribed text field present at {path}")
    atoms = manifest.get("atoms") or []
    if not isinstance(atoms, list) or not atoms:
        errors.append("atoms must be a non-empty list")
        return {"ok": False, "errors": errors, "warnings": warnings, "counts": {}}
    by_id: dict[str, dict] = {}
    methods = {m.get("method_id") for m in manifest.get("methods", [])}
    assets = {a.get("asset_id"): a for a in manifest.get("source_assets", [])}
    for atom in atoms:
        atom_id = atom.get("atom_id")
        if not atom_id:
            errors.append("atom without atom_id")
            continue
        if atom_id in by_id:
            errors.append(f"duplicate atom_id {atom_id}")
        by_id[atom_id] = atom
        for field in ("unit", "piece_id", "version_id", "page_id", "region", "lineage", "reading", "credit"):
            if field not in atom:
                errors.append(f"{atom_id}: missing {field}")
        if atom.get("unit") not in UNITS:
            errors.append(f"{atom_id}: unknown unit {atom.get('unit')!r}")
        region = atom.get("region") or {}
        bbox = region.get("bbox")
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(v, (int, float)) for v in bbox)):
            errors.append(f"{atom_id}: region.bbox must be four numbers")
        elif not (bbox[0] <= bbox[2] and bbox[1] <= bbox[3]):
            errors.append(f"{atom_id}: region.bbox is inverted")
        if region.get("frame") != "source-pixels":
            errors.append(f"{atom_id}: region.frame must be source-pixels")
        lineage = atom.get("lineage") or {}
        parent = lineage.get("parent_atom_id")
        if atom.get("unit") == "poem":
            if parent is not None:
                errors.append(f"{atom_id}: poem atom must have a null parent")
        if atom.get("parent_atom_id") is not None and parent is not None and atom["parent_atom_id"] != parent:
            errors.append(f"{atom_id}: parent_atom_id disagrees with lineage.parent_atom_id")
        if not lineage.get("root_source_asset_ids"):
            errors.append(f"{atom_id}: no root source asset")
        method_id = lineage.get("method_id")
        if not method_id:
            errors.append(f"{atom_id}: no method_id")
        elif method_id not in methods:
            errors.append(f"{atom_id}: method {method_id} is not declared")
        for asset_id in atom.get("source_asset_ids", []):
            if asset_id not in assets:
                errors.append(f"{atom_id}: source asset {asset_id} not declared")
        if atom.get("unit") == "combination":
            combination = atom.get("combination") or {}
            if not combination.get("input_atom_ids"):
                errors.append(f"{atom_id}: combination has no input_atom_ids")
            if combination.get("operation") not in COMBINATION_OPERATIONS:
                errors.append(f"{atom_id}: unknown combination operation {combination.get('operation')!r}")
    for atom in atoms:
        atom_id = atom.get("atom_id", "?")
        lineage = atom.get("lineage") or {}
        parent = lineage.get("parent_atom_id")
        if parent is not None and parent not in by_id:
            errors.append(f"{atom_id}: parent {parent} not in manifest")
        for asset_id in lineage.get("root_source_asset_ids", []):
            if asset_id not in assets:
                errors.append(f"{atom_id}: root asset {asset_id} not declared")
        if atom.get("unit") == "combination":
            for input_id in (atom.get("combination") or {}).get("input_atom_ids") or []:
                if input_id not in by_id:
                    errors.append(f"{atom_id}: combination input {input_id} not in manifest")
        # Closure is checked atom by atom: missing parents/inputs and cycles are
        # contract errors, not merely eligibility warnings.
        try:
            lineage_closure(manifest, atom_id)
        except (KeyError, ValueError) as exc:
            errors.append(f"{atom_id}: lineage does not close: {exc}")
    # Region frames: every region is in page pixels; verify against the scan size.
    for asset in assets.values():
        if asset.get("kind") != "page-scan":
            continue
        path = ROOT / asset["path"]
        if not path.is_file():
            errors.append(f"source asset missing on disk: {asset['path']}")
        elif sha256_file(path) != asset.get("sha256"):
            errors.append(f"source asset hash changed: {asset['path']}")
    integrity = manifest.get("integrity") or {}
    unhashed = {k: v for k, v in manifest.items() if k != "integrity"}
    expected = canonical_sha256(unhashed)
    if integrity.get("content_sha256") != expected:
        errors.append("integrity.content_sha256 does not match the manifest content")
    counts = manifest.get("counts") or {}
    for unit, key in (("line", "lines"), ("word", "words"), ("glyph", "glyphs"), ("mark", "marks")):
        actual = sum(1 for a in atoms if a.get("unit") == unit)
        if counts.get(key) != actual:
            errors.append(f"counts.{key} is {counts.get(key)}, actual {actual}")
    if counts.get("atoms") != len(atoms):
        errors.append(f"counts.atoms is {counts.get('atoms')}, actual {len(atoms)}")
    if any(a.get("unit") == "line" and not (a.get("region") or {}).get("polygon") for a in atoms):
        warnings.append("one or more line atoms have no polygon (box-only region)")
    if any((a.get("reading") or {}).get("uncertainty_ids") for a in atoms):
        warnings.append("uncertain readings are carried as open states, not resolved")
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "counts": counts, "atoms": len(atoms), "assets": len(assets)}


def lineage_closure(manifest: dict, atom_id: str) -> dict:
    by_id = {a["atom_id"]: a for a in manifest.get("atoms", [])}
    if atom_id not in by_id:
        raise KeyError(atom_id)
    seen: set[str] = set()
    order: list[str] = []
    roots: set[str] = set()
    source_lines: set[str] = set()
    methods: list[str] = []

    def visit(current: str, stack: tuple[str, ...]) -> None:
        if current in stack:
            raise ValueError(f"lineage cycle: {' -> '.join(stack + (current,))}")
        if current in seen:
            return
        atom = by_id.get(current)
        if atom is None:
            raise KeyError(f"lineage refers to missing atom {current}")
        seen.add(current)
        order.append(current)
        lineage = atom.get("lineage") or {}
        roots.update(lineage.get("root_source_asset_ids") or [])
        source_lines.update(lineage.get("source_line_ids") or [])
        method = lineage.get("method_id")
        if method and method not in methods:
            methods.append(method)
        for input_id in (atom.get("combination") or {}).get("input_atom_ids") or []:
            visit(input_id, stack + (current,))
        parent = lineage.get("parent_atom_id")
        if parent:
            visit(parent, stack + (current,))

    visit(atom_id, ())
    return {"atom_id": atom_id, "atoms": order, "root_source_asset_ids": sorted(roots),
            "source_line_ids": sorted(source_lines), "methods": methods}


def _policy_piece(policy: dict, piece_id: str) -> dict | None:
    return (policy.get("pieces") or {}).get(piece_id)


def _veto_applies_to_scope(veto: dict, scope: str) -> bool:
    scopes = veto.get("scopes") or ["all"]
    return "all" in scopes or scope in scopes


def _veto_matches(veto: dict, atom: dict, version_id: str, scope: str) -> bool:
    if not _veto_applies_to_scope(veto, scope):
        return False
    if veto.get("version_id") and veto["version_id"] != version_id:
        return False
    atom_id = atom.get("atom_id")
    line_ids = set((atom.get("lineage") or {}).get("source_line_ids") or [])
    source_ids = atom.get("source_ids") or {}
    if source_ids.get("line_id"):
        line_ids.add(source_ids["line_id"])
    if atom_id in (veto.get("atom_ids") or []):
        return True
    if any(line in (veto.get("line_ids") or []) for line in line_ids):
        return True
    if not (veto.get("atom_ids") or veto.get("line_ids")):
        return True
    return False


def region_component_id(piece_id, version_id):
    return "regions:" + piece_id + ":" + version_id


def current_source_bindings(manifest, *, snapshots=None, repo=ROOT, db=None, additional_pairs=()):
    """Fresh v2 logical bindings, with exact source line-ID membership checks.

    Preserved manifests remain readable; this does not silently rewrite them.
    API callers may provide current snapshots. The CLI resolves the live source
    files itself, rather than trusting saved binding strings in a context file.
    """
    from script_realizations import source_snapshot
    pairs = sorted({(a["piece_id"], a["version_id"]) for a in manifest.get("atoms", [])} | set(additional_pairs))
    if snapshots is None:
        snapshots = [source_snapshot(repo, piece, version, db) for piece, version in pairs]
    by_key = {}
    for snapshot in snapshots:
        binding = source_binding(snapshot)
        key = (binding["pieceId"], binding["versionId"])
        if key in by_key:
            raise ValueError("duplicate current source snapshot")
        by_key[key] = (binding, {line["lineId"] for line in snapshot["lines"]})
    if any(key not in by_key for key in pairs):
        raise ValueError("missing current source snapshot")
    all_lines = set().union(*(by_key[key][1] for key in pairs)) if pairs else set()
    for atom in manifest.get("atoms", []):
        line_id = (atom.get("source_ids") or {}).get("line_id")
        if line_id is not None and line_id not in by_key[(atom["piece_id"], atom["version_id"])][1]:
            raise ValueError("region source line is not in its exact current version")
        if set((atom.get("lineage") or {}).get("source_line_ids") or []) - all_lines:
            raise ValueError("region lineage contains an unavailable source line")
    return [by_key[key][0] for key in pairs]


def _checked_source_assets(manifest, repo):
    """Read the declared current bytes; a recorded hash alone is not proof."""
    from source_foundation import read_bytes, relative
    result = {}
    for asset in manifest.get("source_assets", []):
        aid, name, expected = asset.get("asset_id"), asset.get("path"), asset.get("sha256")
        if not isinstance(aid, str) or aid in result or not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
            raise ValueError("source-asset identity or hash is invalid")
        try:
            data = read_bytes(Path(repo) / relative(name))
        except (OSError, ValueError, TypeError) as error:
            raise ValueError("source-asset unavailable or unsafe: " + str(aid)) from error
        if type(asset.get("size")) is not int or len(data) != asset["size"] or hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("source-asset bytes changed: " + aid)
        result[aid] = (asset, data)
    if not result:
        raise ValueError("source-asset set is empty")
    return result


def evaluate(manifest: dict, policy: dict, scope: str, *, release_context=None) -> dict:
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}; expected one of {', '.join(SCOPES)}")
    if policy.get("schema") != POLICY_SCHEMA:
        raise ValueError(f"policy schema is {policy.get('schema')!r}, expected {POLICY_SCHEMA!r}")
    digest = manifest_digest(manifest)
    manifest_reasons: list[str] = []
    warnings: set[str] = set()
    atom_reasons: dict[str, list[str]] = {}
    atom_warnings: dict[str, list[str]] = {}
    inherited_pools: dict[str, str] = {}
    private_bindings = []

    if scope in PRIVATE_SCOPES:
        if (manifest.get("scope") or {}).get("distribution") != "private-local" or (manifest.get("scope") or {}).get("may_publish") is not False:
            manifest_reasons.append("scope:not-private-local")
        if (policy.get("publication") or {}).get("enabled") is not False:
            manifest_reasons.append("policy:publication-must-stay-disabled-for-private-preview")
        context = release_context or {}
        try:
            private_bindings = current_source_bindings(manifest,
                snapshots=context.get("source_snapshots"), repo=context.get("source_repo", ROOT), db=context.get("source_db"))
            if context.get("current_sources") is not None and context["current_sources"] != private_bindings:
                manifest_reasons.append("source-binding:declared-current-source-mismatch")
        except (ValueError, KeyError, TypeError, OSError):
            manifest_reasons.append("source-binding:current-v2-source-unavailable")

    # Current source pixels are required in every scope, independently of an
    # unchanged logical fingerprint or a valid exact-output clearance record.
    try:
        _checked_source_assets(manifest, (release_context or {}).get("source_repo", ROOT))
    except (ValueError, TypeError, OSError) as error:
        manifest_reasons.append(str(error))

    clearance = policy.get("author_clearance") or {}
    if scope in PUBLIC_SCOPES:
        import release_contract
        context = release_context or {}
        output_manifest = context.get("manifest")
        bindings = None
        try:
            selected = (output_manifest or {}).get("sources", [])
            resolved = current_source_bindings(manifest, snapshots=context.get("source_snapshots"),
                repo=context.get("source_repo", ROOT), db=context.get("source_db"),
                additional_pairs=[(s["pieceId"], s["versionId"]) for s in selected])
            by_key = {(s["pieceId"], s["versionId"]): s for s in resolved}
            bindings = [by_key[(s["pieceId"], s["versionId"])] for s in selected]
            if context.get("current_sources") is not None and context["current_sources"] != bindings:
                manifest_reasons.append("source-binding:declared-current-source-mismatch")
        except (ValueError, KeyError, TypeError, OSError):
            manifest_reasons.append("source-binding:current-v2-source-unavailable")
        checked = release_contract.evaluate(output_manifest, context.get("clearance"),
            current_sources=bindings, root=context.get("output_root"))
        manifest_reasons.extend("release-contract:" + r for r in checked["reasons"])
        if checked["eligible"]:
            by_source = {(s["pieceId"], s["versionId"]): s for s in bindings}
            for piece_id, version_id in sorted({(a["piece_id"], a["version_id"]) for a in manifest.get("atoms", [])}):
                component_id = region_component_id(piece_id, version_id)
                approved = next((c for c in output_manifest["components"]
                                 if c.get("kind") == "regions" and c.get("id") == component_id), None)
                source = by_source.get((piece_id, version_id))
                if approved is None or source is None:
                    manifest_reasons.append("release-contract:missing-region-component")
                    continue
                component = {**approved, **source, "revisionDigest": "sha256:" + digest}
                result = release_contract.evaluate(output_manifest, context.get("clearance"),
                    current_sources=bindings, component=component)
                manifest_reasons.extend("release-contract:" + r for r in result["reasons"])
        if clearance.get("status") != "cleared":
            manifest_reasons.append("author-clearance:missing")
        elif clearance.get("covers_manifest_sha256") != digest:
            manifest_reasons.append("author-clearance:does-not-cover-this-manifest")
        # T03's release record is a separate evidence bundle. When a policy
        # carries one, public output needs it cleared and publishable; T08 does
        # not create or interpret the filing/acceptance evidence itself.
        gate = policy.get("release_gate")
        if gate is not None and (gate.get("status") != "cleared" or gate.get("may_publish") is not True):
            manifest_reasons.append("release-gate:not-cleared")
        if policy.get("machine_misread", {}).get("status") != "cleared":
            warnings.add("machine-misread-rule-unresolved")

    assets = {a["asset_id"]: a for a in manifest.get("source_assets", [])}
    withheld_assets = set(policy.get("withheld_assets") or [])
    withheld_pages = set(policy.get("withheld_pages") or [])
    whitelist = set(policy.get("public_whitelist") or [])
    for asset_id, asset in assets.items():
        if asset_id in withheld_assets or asset.get("path") in withheld_assets:
            manifest_reasons.append(f"source-asset:withheld:{asset_id}")
        if asset.get("withheld") is True:
            manifest_reasons.append(f"source-asset:marked-withheld:{asset_id}")
    manifest_pages = {a.get("page_id") for a in manifest.get("atoms", [])}
    for page_id in sorted(withheld_pages & manifest_pages):
        manifest_reasons.append(f"page:withheld:{page_id}")

    pages_to_pieces: dict[str, set[str]] = {}
    atom_ids = [a["atom_id"] for a in manifest.get("atoms", [])]
    for atom in manifest.get("atoms", []):
        aid = atom["atom_id"]
        reasons: list[str] = []
        piece_policy = _policy_piece(policy, atom["piece_id"])
        if piece_policy is None:
            reasons.append(f"piece:no-visibility-record:{atom['piece_id']}")
            pool = "unassigned"
        else:
            pool = piece_policy.get("pool", "unassigned")
        inherited_pools[aid] = pool
        version_id = atom["version_id"]
        page_id = atom["page_id"]
        pages_to_pieces.setdefault(page_id, set()).add(atom["piece_id"])

        if pool in ("withheld", "deleted"):
            reasons.append(f"pool:{pool}")
        if scope in PUBLIC_SCOPES:
            if pool != "series":
                reasons.append(f"pool:{pool}-is-not-series")
            if atom["piece_id"] not in whitelist:
                reasons.append("public-whitelist:piece-not-listed")
        if scope == "cipher-public" and pool in ("reserve", "archive", "withheld", "unassigned"):
            reasons.append(f"cipher:pool-{pool}-never-enciphered")
        if page_id in withheld_pages:
            reasons.append(f"page:withheld:{page_id}")
        if version_id in set(piece_policy.get("withheld_versions", []) if piece_policy else []):
            reasons.append(f"version:withheld:{version_id}")
        for exclusion in (piece_policy or {}).get("excluded_versions", []):
            scopes = exclusion.get("scopes") or ["all"]
            if "all" in scopes or scope in scopes:
                if exclusion.get("version_id") == version_id:
                    reasons.append(f"version:excluded-for-{scope}:{version_id}")
        for veto in (piece_policy or {}).get("strike_through_vetoes", []):
            if _veto_matches(veto, atom, version_id, scope):
                reasons.append(f"strike-through-veto:{veto.get('veto_id', 'unnamed')}")
                break
        # A piece-level veto without atom ids applies to the whole piece.
        for veto in (piece_policy or {}).get("piece_vetoes", []):
            if _veto_applies_to_scope(veto, scope) and veto.get("version_id") in (None, version_id):
                reasons.append(f"piece-veto:{veto.get('veto_id', 'unnamed')}")
                break
        reading = atom.get("reading") or {}
        if reading.get("uncertainty_ids"):
            warnings.add("reading:open-uncertainty-present")
        if reading.get("deliberate_misread") and scope in PUBLIC_SCOPES:
            if (policy.get("machine_misread") or {}).get("status") != "cleared":
                reasons.append("machine-misread:unresolved-author-rule")
        credit = atom.get("credit") or {}
        if scope in PUBLIC_SCOPES and credit.get("origin_kind") == "borrowed":
            if credit.get("credit_required") and not credit.get("credit_style"):
                reasons.append("borrowed-line:credit-style-unresolved")
            if not credit.get("source_atom_ids"):
                reasons.append("borrowed-line:no-source-atom")
        lineage = atom.get("lineage") or {}
        if not lineage.get("root_source_asset_ids"):
            reasons.append("lineage:no-root-source")
        if atom.get("unit") == "combination":
            inputs = (atom.get("combination") or {}).get("input_atom_ids") or []
            if not inputs:
                reasons.append("combination:no-inputs")
            for input_id in inputs:
                if input_id not in atom_ids:
                    reasons.append(f"combination:input-not-in-manifest:{input_id}")
        if reasons:
            atom_reasons[aid] = sorted(set(reasons))
        atom_warnings[aid] = sorted(w for w in (
            "reading:open-uncertainty" if reading.get("uncertainty_ids") else None,
            "reading:owner-withdrawn-crop" if reading.get("review_state") == "crop-withdrawn-by-owner-eye-review" else None,
        ) if w)

    # Shared scan: a public/cipher output over a page that carries another piece
    # needs either that neighbour's clearance or a page-level resolution.
    if scope in PUBLIC_SCOPES:
        resolution = (policy.get("shared_scan_resolution") or {})
        resolved_pages = set((resolution.get("pages") or {}).keys()) if resolution.get("status") == "cleared" else set()
        for page, pieces in pages_to_pieces.items():
            if len(pieces) < 2:
                continue
            if page in resolved_pages:
                continue
            # Every piece on the page must be a cleared Series piece. Skipping an
            # arbitrary "first" piece would let the neighbour that needs the
            # resolution be the one that is never checked.
            for other in sorted(pieces):
                other_policy = _policy_piece(policy, other)
                if not other_policy or other_policy.get("pool") != "series" or other not in whitelist:
                    manifest_reasons.append(f"shared-scan:unresolved-neighbour:{page}:{other}")

    # Lineage closure must resolve for every atom, and every root asset must exist.
    closures: dict[str, dict] = {}
    for atom in manifest.get("atoms", []):
        try:
            closures[atom["atom_id"]] = lineage_closure(manifest, atom["atom_id"])
        except (KeyError, ValueError) as exc:
            atom_reasons.setdefault(atom["atom_id"], []).append(f"lineage:{exc}")

    # Inheritance: private tools may work on Reserve/Archive material, but the
    # output may never be promoted by the tool. Public scopes expose it as a
    # rejection above; private scopes record the inherited pool.
    inherited = "series"
    order = ["series", "unassigned", "archive", "reserve", "withheld"]
    if scope in PRIVATE_SCOPES:
        for pool in inherited_pools.values():
            if pool in order and order.index(pool) > order.index(inherited):
                inherited = pool
        if inherited == "withheld":
            manifest_reasons.append("inherited-pool:withheld")
    elif scope in PUBLIC_SCOPES:
        inherited = "series" if not atom_reasons else "blocked"

    allowed = not manifest_reasons and not atom_reasons
    reason_counts: dict[str, int] = {}
    for reasons in atom_reasons.values():
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    required_actions = []
    all_atom_reasons = [r for reasons in atom_reasons.values() for r in reasons]
    if "author-clearance:missing" in manifest_reasons or "author-clearance:does-not-cover-this-manifest" in manifest_reasons:
        required_actions.append("Obtain a dated, source-linked author clearance that names this manifest digest.")
    if "release-gate:not-cleared" in manifest_reasons:
        required_actions.append("Complete the T03 release record (input/exposure hashes, filing evidence, acceptance receipt, rollback) and clear it.")
    if any("public-whitelist" in r for r in manifest_reasons + all_atom_reasons):
        required_actions.append("Record the author's Series/Reserve/Archive decision and add the piece to the public whitelist.")
    if any("machine-misread" in r for r in manifest_reasons + all_atom_reasons):
        required_actions.append("Get the author's rule on machine misreads before publishing a misread atom.")
    if any("version:excluded" in r for r in manifest_reasons + all_atom_reasons):
        required_actions.append("Use a version the author has not excluded for this scope.")
    if any("shared-scan" in r for r in manifest_reasons):
        required_actions.append("Resolve the shared page: clear every neighbour piece or provide an author-approved page-level remedy.")
    if any("borrowed-line" in r for r in atom_reasons.values() for r in r):
        required_actions.append("Choose the borrowed-line credit style before publication.")
    if any("strike-through-veto" in r for r in atom_reasons.values() for r in r):
        required_actions.append("Remove the vetoed source atoms from the derivative.")
    return {
        "schema": REPORT_SCHEMA,
        "scope": scope,
        "policy_id": policy.get("policy_id"),
        "manifest_sha256": digest,
        "source_bindings": private_bindings,
        "allowed": allowed,
        "summary": {
            "atoms": len(atom_ids),
            "atoms_rejected": len(atom_reasons),
            "reason_counts": reason_counts,
            "inherited_pool": inherited,
        },
        "manifest_reasons": sorted(set(manifest_reasons)),
        "atom_reasons": atom_reasons,
        "warnings": sorted(warnings),
        "atom_warnings": {k: v for k, v in atom_warnings.items() if v},
        "required_actions": required_actions,
        "closures_checked": len(closures),
    }


def review_page_geometry(page):
    """Text-free projection also derived live by the Studio preview consumer."""
    return {"pageId": page["id"], "width": page["w"], "height": page["h"],
            "blocks": [{"index": index, "lines": [{"lineId": line["id"],
                "box": copy.deepcopy(line.get("box")), "sourceAnchor": copy.deepcopy(line.get("sourceAnchor"))}
                for line in block["lines"]]} for index, block in enumerate(page["blocks"])]}


def export_private_preview(manifest, policy, atom_id, output, *, repo=ROOT, db=None, expected=None):
    """Export one real region's private full-image preview, without inventing a crop.

    All validation precedes output creation. A supplied earlier descriptor is a
    stale-work guard, never authority. Current source, canonical geometry, live
    review export, policy and actual source pixels are independently rechecked.
    """
    from PIL import Image
    import source_foundation as foundation
    from script_realizations import source_snapshot, release_policy, private_destination

    result = verify_manifest(manifest)
    if not result["ok"]:
        raise ValueError("invalid region manifest: " + "; ".join(result["errors"][:4]))
    if not isinstance(atom_id, str):
        raise ValueError("selected region identity must be a string")
    selected = [a for a in manifest["atoms"] if a["atom_id"] == atom_id]
    if len(selected) != 1:
        raise ValueError("selected region is unavailable")
    atom = selected[0]
    line_id = atom.get("source_ids", {}).get("line_id")
    if not isinstance(line_id, str):
        raise ValueError("private preview requires a line-anchored region")
    repo = foundation.no_links(repo)
    canonical = foundation.read_json(repo / "source/canonical.json")
    foundation.validate(canonical)
    if foundation.rebuild(canonical, repo)["changed"]:
        raise ValueError("canonical source and current reader/studio outputs differ; rebuild before preview")
    report = evaluate(manifest, policy, "private-local", release_context={"source_repo": repo, "source_db": db})
    if not report["allowed"]:
        reasons = report["manifest_reasons"] + [r for group in report["atom_reasons"].values() for r in group]
        raise ValueError("private region is ineligible: " + "; ".join(sorted(set(reasons))[:8]))

    snapshot = source_snapshot(repo, atom["piece_id"], atom["version_id"], db)
    source = source_binding(snapshot)
    source_policy = release_policy(repo, atom["piece_id"], db)
    if source_policy["visibility"] == "withheld":
        raise ValueError("current source policy withholds this private preview")
    lines = {line["id"]: line for line in canonical["lines"]}
    line = lines.get(line_id)
    if not line or line["pageId"] != atom["page_id"] or line_id not in {l["lineId"] for l in snapshot["lines"]}:
        raise ValueError("region does not belong to the current canonical source line")
    page = next(p for p in canonical["pages"] if p["id"] == atom["page_id"])
    review = foundation.read_json(repo / "studio/data/review.json")
    review_page = next(p for p in review["pages"] if p["id"] == atom["page_id"])
    anchor_geometry = line["geometry"]
    anchor = {"lineId": line_id, "pageId": page["id"], "status": anchor_geometry["status"],
              "box": copy.deepcopy(anchor_geometry["studioBox"]) if anchor_geometry["status"] == "available" else None,
              "reason": anchor_geometry.get("reason")}
    # A partially aligned block cannot establish which surviving box belongs to
    # each transcript line. Match the current reader's whole-block fallback.
    block = next(b for b in canonical["blocks"] if b["id"] == line["blockId"])
    if any(lines[lid]["geometry"]["status"] != "available" for lid in block["lineIds"]):
        anchor.update(status="unavailable", box=None)
        if not anchor["reason"]:
            anchor["reason"] = "block-source-geometry-incomplete"
    if anchor["status"] == "available":
        box = anchor["box"]
        if not isinstance(box, list) or len(box) != 4 or any(type(v) not in (int, float) for v in box) or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
            raise ValueError("canonical source anchor is invalid")
    assets = _checked_source_assets(manifest, repo)
    asset_ids = atom.get("source_asset_ids", [])
    if len(asset_ids) != 1 or asset_ids[0] not in assets:
        raise ValueError("bounded private preview requires one declared source image")
    asset, image_bytes = assets[asset_ids[0]]
    current_asset = next((a for a in canonical["assets"] if a["path"] == asset["path"]), None)
    media_digest = "sha256:" + hashlib.sha256(image_bytes).hexdigest()
    if asset.get("page_id") != page["id"] or not current_asset or current_asset.get("pageId") != page["id"] or current_asset["sha256"] != media_digest or current_asset["bytes"] != len(image_bytes):
        raise ValueError("source-asset differs from current canonical image lineage")
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.format != "JPEG" or image.size != (review_page["w"], review_page["h"]):
            raise ValueError("source-asset is not the declared full JPEG page")
        image.verify()
    geometry = {"atomId": atom_id, "region": copy.deepcopy(atom["region"]),
        "authorBox": copy.deepcopy(atom.get("author_box")), "sourceAnchor": anchor,
        "reviewPageGeometry": review_page_geometry(review_page),
        "canonicalPage": {"pageId": page["id"], "dimensions": {"width": review_page["w"], "height": review_page["h"]},
            "lines": [{"lineId": l["id"], "geometry": copy.deepcopy(l["geometry"])} for l in canonical["lines"] if l["pageId"] == page["id"]],
            "assets": [{"id": a["id"], "sha256": a["sha256"]} for a in canonical["assets"] if a.get("pageId") == page["id"]]}}
    # These JSON files are raw-byte hashed; consumers need no float-serialization
    # assumptions when verifying the original manifest or geometry proof.
    encode = lambda value: (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
    files = {"region-manifest.json": encode(manifest), "policy.json": encode(policy),
             "source.json": encode({"snapshot": snapshot, "sourcePolicy": source_policy}),
             "geometry.json": encode(geometry), "assets/source.jpg": image_bytes}
    hashes = {name: "sha256:" + hashlib.sha256(data).hexdigest() for name, data in files.items()}
    package = {"schema": PRIVATE_PREVIEW_SCHEMA, "audience": "private", "fixture": True,
        "mayPublish": False, "scope": "private-local", "source": source, "sourcePolicy": source_policy,
        "atomId": atom_id, "manifestDigest": hashes["region-manifest.json"], "geometryDigest": hashes["geometry.json"],
        "mediaDigest": media_digest, "policyDigest": hashes["policy.json"], "sourceAnchor": anchor,
        "image": {"path": "assets/source.jpg", "width": review_page["w"], "height": review_page["h"], "display": "full-source-image-no-crop"},
        "files": [{"path": name, "sha256": hashes[name], "bytes": len(files[name])} for name in sorted(files)]}
    package_bytes = encode(package)
    descriptor = {key: copy.deepcopy(package[key]) for key in ("source", "sourcePolicy", "atomId", "manifestDigest", "geometryDigest", "mediaDigest", "policyDigest")}
    descriptor["package"] = {"manifestUrl": "region-preview.json", "sha256": "sha256:" + hashlib.sha256(package_bytes).hexdigest()}
    if expected is not None and (not isinstance(expected, dict) or not isinstance(expected.get("package"), dict) or any(expected.get(key) != value for key, value in descriptor.items() if key != "package") or expected["package"].get("sha256") != descriptor["package"]["sha256"]):
        raise ValueError("stale private region descriptor; explicitly re-export current source/geometry/media/policy")
    output = private_destination(output)
    if output.exists() or output.is_relative_to(repo):
        raise ValueError("private region preview must be a new directory outside the source checkout")
    output.mkdir(parents=True)
    for name, data in {**files, "region-preview.json": package_bytes}.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(data)
    return descriptor


def _load_manifest(path: Path) -> dict:
    manifest = read_json(path)
    result = verify_manifest(manifest)
    if not result["ok"]:
        raise ValueError("manifest is invalid: " + "; ".join(result["errors"][:8]))
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="build a region-only manifest from owner atoms")
    p_build.add_argument("--atoms", required=True, type=Path)
    p_build.add_argument("--atoms-ref", default="proto/alive/atoms-p001.json")
    p_build.add_argument("--atoms-commit", default=None)
    p_build.add_argument("--piece", default="p001")
    p_build.add_argument("--version-id", default=None)
    p_build.add_argument("--version-index", type=int, default=0)
    p_build.add_argument("--out", type=Path, default=ROOT / "docs/pilots/t08-p001/p001.source-regions.json")

    p_verify = sub.add_parser("verify", help="verify a manifest's structure and hashes")
    p_verify.add_argument("--manifest", required=True, type=Path)
    p_verify.add_argument("--out", type=Path, default=None)

    p_lineage = sub.add_parser("lineage", help="print the closure for one atom")
    p_lineage.add_argument("--manifest", required=True, type=Path)
    p_lineage.add_argument("--atom-id", required=True)

    p_check = sub.add_parser("check", help="evaluate a scope against a visibility policy")
    p_check.add_argument("--manifest", required=True, type=Path)
    p_check.add_argument("--policy", required=True, type=Path)
    p_check.add_argument("--scope", required=True, choices=SCOPES)
    p_check.add_argument("--release-context", type=Path, help="Exact output manifest, attributable clearance and freshly resolved current_sources; required for public scopes")
    p_check.add_argument("--source-repo", type=Path, default=ROOT, help="Current canonical reader/studio source checkout")
    p_check.add_argument("--source-db", type=Path, help="Optional current review export")
    p_check.add_argument("--out", type=Path, default=None)
    p_check.add_argument("--require-allowed", action="store_true")

    p_preview = sub.add_parser("preview", help="export a current-source-bound private region/image package")
    p_preview.add_argument("--manifest", required=True, type=Path)
    p_preview.add_argument("--policy", required=True, type=Path)
    p_preview.add_argument("--atom-id", required=True)
    p_preview.add_argument("--source-repo", type=Path, default=ROOT)
    p_preview.add_argument("--source-db", type=Path)
    p_preview.add_argument("--expected-descriptor", type=Path, help="earlier descriptor; refuse any stale identity instead of silently rebinding")
    p_preview.add_argument("--out", required=True, type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            manifest = build_manifest(args.atoms, atoms_ref=args.atoms_ref,
                                      atoms_commit=args.atoms_commit,
                                      piece_id=args.piece, version_id=args.version_id,
                                      version_index=args.version_index)
            result = verify_manifest(manifest)
            if not result["ok"]:
                print(json.dumps(result, indent=2))
                return 1
            write_json(args.out, manifest)
            print(json.dumps({"out": str(args.out), "counts": manifest["counts"],
                              "content_sha256": manifest["integrity"]["content_sha256"]}, indent=2))
            return 0
        if args.command == "verify":
            manifest = read_json(args.manifest)
            result = verify_manifest(manifest)
            if args.out:
                write_json(args.out, result)
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1
        if args.command == "lineage":
            manifest = _load_manifest(args.manifest)
            print(json.dumps(lineage_closure(manifest, args.atom_id), indent=2))
            return 0
        if args.command == "check":
            manifest = _load_manifest(args.manifest)
            policy = read_json(args.policy)
            context = read_json(args.release_context) if args.release_context else {}
            # Context files retain evidence; their snapshots are historical.
            # Resolve current source in private scopes too, using this checkout.
            context.pop("source_snapshots", None)
            context["source_repo"] = args.source_repo
            context["source_db"] = args.source_db
            report = evaluate(manifest, policy, args.scope,
                              release_context=context)
            if args.out:
                write_json(args.out, report)
            print(json.dumps({k: report[k] for k in ("scope", "allowed", "summary",
                                                     "manifest_reasons", "required_actions")}, indent=2))
            return 0 if report["allowed"] else 3
        if args.command == "preview":
            descriptor = export_private_preview(_load_manifest(args.manifest), read_json(args.policy),
                args.atom_id, args.out, repo=args.source_repo, db=args.source_db,
                expected=read_json(args.expected_descriptor) if args.expected_descriptor else None)
            print(json.dumps(descriptor, indent=2))
            return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
