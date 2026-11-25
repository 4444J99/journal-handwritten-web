#!/usr/bin/env python3
"""Stage 3 Round 1 projection helper for journal-handwritten-web.

Reads public-safe ``source/chronology.json`` plus ``site/data/j.json`` and
writes social-ready JPEGs into an output directory outside the repository.
Two safety invariants are enforced:

* every output is rebuilt from a fresh, metadata-free RGB image, so EXIF,
  XMP, GPS, ICC profiles, and embedded thumbnails cannot survive;
* co-tenanted and spread-exposed surfaces are isolated or blocked, so a
  neighbour's writing (e.g. ``p126`` on ``diary62a``) can never leak.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from build_chronology import CorpusIndex, validate_public_payload  # noqa: E402

ROOT = TOOLS_DIR.parent
SCHEMA_VERSION = "versforms.round1-projection.v1"

BLOCK_SHARED = "co_tenanted_surface_blocked_without_crop"
_BLOCK_BBOX = "missing_block_bbox_for_shared_surface"
BLOCK_SPREAD = "spread_exposed_surface_requires_isolation"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--chronology",
        type=Path,
        default=ROOT / "source" / "chronology.json",
        help="Public-safe chronology JSON (default: source/chronology.json)",
    )
    parser.add_argument(
        "--j-json",
        type=Path,
        default=ROOT / "site" / "data" / "j.json",
        help="Physical codex corpus (default: site/data/j.json)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory for projections (must be outside any git tree)",
    )
    parser.add_argument(
        "--piece",
        action="append",
        default=[],
        help="Piece ID to project; repeatable (default: p001)",
    )
    parser.add_argument(
        "--surface",
        default=None,
        help="Override the codex surface for the selected pieces",
    )
    parser.add_argument(
        "--override-image",
        type=Path,
        default=None,
        help="Use this source image instead of site/img/p/<surface>.jpg",
    )
    parser.add_argument(
        "--no-crop",
        action="store_true",
        help="Refuse to project a co-tenanted surface instead of cropping it",
    )
    parser.add_argument(
        "--allow-spread-crop",
        action="store_true",
        help="Permit projecting a spread-exposed surface",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when every requested piece was blocked",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    chronology_path = args.chronology
    j_path = args.j_json
    if not chronology_path.is_file() or not j_path.is_file():
        print("error: missing chronology.json or j.json", file=sys.stderr)
        return 1

    try:
        chronology = json.loads(chronology_path.read_text(encoding="utf-8"))
        corpus = CorpusIndex(j_path, ROOT / "source" / "canonical.json")
    except Exception as exc:
        print(f"error: failed to load inputs: {exc}", file=sys.stderr)
        return 1

    entry_map = {
        entry["piece_id"]: entry
        for entry in chronology.get("physical_codex_order", [])
    }
    from PIL import Image  # imported lazily so --help works without Pillow

    requested = args.piece or ["p001"]
    for piece_id in requested:
        if piece_id not in corpus.piece_by_id:
            print(f"error: unknown piece_id: {piece_id!r}", file=sys.stderr)
            return 1

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    exports: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    for piece_id in requested:
        entry = entry_map.get(piece_id)
        if entry is None:
            blocked.append(
                {
                    "piece_id": piece_id,
                    "surface_id": args.surface or "",
                    "reason": "piece_missing_from_chronology",
                }
            )
            continue
        surface = args.surface or entry["witnesses"]["codex_scan"]["surface_id"]
        if args.override_image is not None:
            source_image = args.override_image
        else:
            source_image = ROOT / "site" / "img" / "p" / f"{surface}.jpg"
        if not source_image.is_file():
            print(f"error: missing source scan: {source_image}", file=sys.stderr)
            return 1

        is_shared = surface in corpus.multi_piece_pages
        is_spread = surface in corpus.spread_exposed_pages
        if is_spread and not args.allow_spread_crop:
            blocked.append(
                {
                    "piece_id": piece_id,
                    "surface_id": surface,
                    "reason": BLOCK_SPREAD,
                }
            )
            continue

        with Image.open(source_image) as source:
            rgb = source.convert("RGB")
            crop_box = [0, 0, rgb.width, rgb.height]
            isolated_crop = False
            if is_shared:
                if args.no_crop:
                    blocked.append(
                        {
                            "piece_id": piece_id,
                            "surface_id": surface,
                            "reason": BLOCK_SHARED,
                        }
                    )
                    continue
                bbox = corpus.piece_block_bbox(piece_id, surface)
                if bbox is None:
                    blocked.append(
                        {
                            "piece_id": piece_id,
                            "surface_id": surface,
                            "reason": _BLOCK_BBOX,
                        }
                    )
                    continue
                rgb = rgb.crop(bbox)
                crop_box = list(bbox)
                isolated_crop = True

            # Fresh pixel buffer: no EXIF, XMP, GPS, ICC, or IFD1 thumbnail.
            clean = Image.new("RGB", rgb.size)
            clean.paste(rgb)
            output_name = f"{piece_id}_{surface}.jpg"
            output_file = out_dir / output_name
            clean.save(output_file, format="JPEG", quality=92)

        chron = entry["chronology"]
        exports.append(
            {
                "piece_id": piece_id,
                "surface_id": surface,
                "output_file": output_name,
                "sha256": _sha256_file(output_file),
                "shared_surface": is_shared,
                "isolated_crop": isolated_crop,
                "crop_box": crop_box,
                "dimensions": [clean.width, clean.height],
                "chronology_window": [chron.get("est_start"), chron.get("est_end")],
                "amalgamated_sort_key": chron.get("amalgamated_sort_key"),
            }
        )

    manifest = {
        "schema": SCHEMA_VERSION,
        "exports": exports,
        "blocked": blocked,
    }
    validate_public_payload(manifest)
    (out_dir / "projection_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(exports)} projections ({len(blocked)} blocked) to {out_dir}")
    if args.strict and blocked and not exports:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
