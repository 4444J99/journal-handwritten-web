"""Sharpness check for 4444J99/journal-handwritten-web #39.

Question (from docs/chats/2026-10-31-instagram-short-form-video/
02-journal-unavailable-scans.md): zoom into one line of a web-sized scan at
phone resolution; if soft, use the 2015 spread originals
(`diary_originals.zip`) for close-ups.

Method (per the implementation plan posted on #39, comment 7076011206):
  - Test line: diary1 block 0 line 0 ("The walls"), line box from
    site/data/j.json, cropped from the web-sized scan
    site/img/i/diary1.jpg (851x1200) with the kit's own crop_norm.
  - Phone scale: the page rendered at 390 px wide, the same geometry
    production/kit/kit.py::ink_metrics uses. The box-geometry ink height is
    computed with the kit's own ink_metrics (via a minimal adapter exposing
    rows()/src_h), so the number is directly comparable with the p001 QA
    record (production/exports/p001/qa/readability.json).
  - Pixel measurement: dark-pixel rows inside the full-resolution line crop,
    scaled to 390 px page width, at three thresholds (96/128/160) so the
    number's threshold-sensitivity is visible instead of hidden.
  - Readability rule (readability.json): readable at 390 px when the
    smallest ink box is at least 8 px high.

Outputs (docs/verification/jhw39/ — not a checksummed dir, so
MANIFEST.sha256 is untouched):
  - diary1-block0-line0-phone390.png — the line as it appears on a phone
    (exact phone-scale pixels, cropped from the 390 px page render).
  - diary1-block0-line0-phone390-4x.png — the same pixels magnified 4x for
    human inspection (labelled as a magnification, not a re-render).
  - diary1-block0-line0-fullres.png — the line crop from the web scan.
  - diary1-phone390-page.png — the 390 px page render with the line box
    outlined, so the line can be located.
  - sharpness-check.json — all measured numbers + input hashes.
  - sharpness-check.md — the human record (method, numbers, verdict).

Deterministic: same inputs produce byte-identical JSON (verified by
running twice and diffing). No network, no author input, no writes
outside docs/verification/jhw39/.

Usage: python3 tools/check_sharpness_jhw39.py [--out docs/verification/jhw39]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "production" / "kit"))
import kit as kitmod  # noqa: E402  (reuse crop_norm / phone_preview / ink_metrics)

PAGE_ID = "diary1"
BLOCK_ID = 0
LINE_INDEX = 0
EXPECTED_TEXT = "The walls"
DISPLAY_W = 390
READABILITY_MIN_PX = 8.0
THRESHOLDS = (96, 128, 160)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _LineAdapter:
    """Minimal stand-in for kit.SourcePackage exposing only what
    kit.ink_metrics needs: rows(block_ids) and src_h. The single row is
    diary1 block 0 line 0, so ink_metrics reports that line alone."""

    def __init__(self, row, src_h):
        self._row = row
        self.src_h = src_h

    def rows(self, block_ids):
        return [self._row] if BLOCK_ID in block_ids else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/verification/jhw39")
    args = ap.parse_args()
    out = REPO / args.out
    out.mkdir(parents=True, exist_ok=True)

    j_path = REPO / "site" / "data" / "j.json"
    web_path = REPO / "site" / "img" / "i" / "diary1.jpg"
    j = json.loads(j_path.read_text())
    page = next(p for p in j["pages"] if p["id"] == PAGE_ID)
    assert (page["iw"], page["ih"]) == (1135, 1600), page
    line_text = page["B"][BLOCK_ID]["L"][LINE_INDEX]
    assert line_text == EXPECTED_TEXT, line_text
    row = next(r for r in page["x"] if r[0] == BLOCK_ID and r[1] == LINE_INDEX)
    _, _, x0, y0, x1, y1, _, _ = row
    box = (x0, y0, x1, y1)

    web = Image.open(web_path)
    assert web.size == (851, 1200), web.size
    # Same aspect check the kit enforces (kit.py SourcePackage._validate).
    want = page["iw"] / page["ih"]
    got = web.size[0] / web.size[1]
    assert abs(want - got) <= 0.01, (want, got)

    # --- box-geometry ink height at 390 px, via the kit's own function ---
    page_h_at_390 = round(DISPLAY_W * web.size[1] / web.size[0])
    adapter = _LineAdapter(tuple(row), src_h=web.size[1])
    geom = kitmod.ink_metrics(
        adapter, [BLOCK_ID], card_height_px=page_h_at_390,
        canvas_w=DISPLAY_W, display_w=DISPLAY_W,
        page_px_h=web.size[1], src_h=web.size[1],
    )
    box_ink_px_at_390 = geom["min_ink_height_px_at_390"]

    # --- pixel measurement on the full-resolution line crop ---
    fullres = kitmod.crop_norm(web, box)
    gray = fullres.convert("L")
    px = gray.load()
    w, h = gray.size
    pixel_rows = {}
    for thr in THRESHOLDS:
        ink_rows = [y for y in range(h)
                    if any(px[x, y] < thr for x in range(w))]
        if ink_rows:
            ink_h_web = max(ink_rows) - min(ink_rows) + 1
        else:
            ink_h_web = 0
        pixel_rows[str(thr)] = {
            "ink_height_px_web": ink_h_web,
            "ink_height_px_at_390": round(ink_h_web * DISPLAY_W / web.size[0], 2),
            "ink_rows_first_last": [min(ink_rows), max(ink_rows)] if ink_rows else [],
        }

    # --- evidence renders ---
    page390 = kitmod.phone_preview(web, DISPLAY_W)
    assert page390.size == (DISPLAY_W, page_h_at_390), page390.size
    phone_crop = kitmod.crop_norm(page390, box)
    page_marked = page390.convert("RGB")
    d = ImageDraw.Draw(page_marked)
    d.rectangle([round(x0 * DISPLAY_W), round(y0 * page_h_at_390),
                 round(x1 * DISPLAY_W), round(y1 * page_h_at_390)],
                outline=(200, 30, 30), width=2)
    phone_crop_4x = phone_crop.resize(
        (phone_crop.size[0] * 4, phone_crop.size[1] * 4), Image.LANCZOS)

    phone_crop.save(out / "diary1-block0-line0-phone390.png")
    phone_crop_4x.save(out / "diary1-block0-line0-phone390-4x.png")
    fullres.save(out / "diary1-block0-line0-fullres.png")
    page_marked.save(out / "diary1-phone390-page.png")

    record = {
        "issue": "4444J99/journal-handwritten-web#39",
        "method": "kit.py ink_metrics (box geometry) + dark-pixel rows in the "
                  "full-resolution line crop, both at 390 px page width",
        "readability_rule_px_at_390": READABILITY_MIN_PX,
        "inputs": {
            "j_json": {"path": "site/data/j.json",
                       "sha256": sha256(j_path)},
            "web_scan": {"path": "site/img/i/diary1.jpg",
                         "size_px": list(web.size),
                         "sha256": sha256(web_path)},
            "preserved_scan_for_reference": {
                "path": "production/assets/diary1.jpg"},
            "kit_head": "main 447aad25",
        },
        "line": {
            "page": PAGE_ID, "block": BLOCK_ID, "line": LINE_INDEX,
            "text": line_text,
            "box_norm": [x0, y0, x1, y1],
            "box_px_web": [round(x0 * web.size[0]), round(y0 * web.size[1]),
                           round(x1 * web.size[0]), round(y1 * web.size[1])],
            "box_px_at_390": [round(x0 * DISPLAY_W), round(y0 * page_h_at_390),
                              round(x1 * DISPLAY_W), round(y1 * page_h_at_390)],
        },
        "box_geometry_ink_height_px_at_390": box_ink_px_at_390,
        "pixel_ink_height_by_threshold": pixel_rows,
        "geometry_readable_at_390": box_ink_px_at_390 >= READABILITY_MIN_PX,
        "pixel_readable_at_390": all(
            v["ink_height_px_at_390"] >= READABILITY_MIN_PX
            for v in pixel_rows.values()),
        "existing_qa_for_context": {
            "source": "production/exports/p001/qa/readability.json",
            "note": "p001 kit renders (preserved source) min ink 13.6-25.52 px "
                    "at 390, all geometry-readable; those are kit renders, "
                    "not the web-sized scan — this check measures the web scan.",
        },
        "evidence": [
            "diary1-block0-line0-phone390.png",
            "diary1-block0-line0-phone390-4x.png",
            "diary1-block0-line0-fullres.png",
            "diary1-phone390-page.png",
        ],
    }
    (out / "sharpness-check.json").write_text(
        json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    print(f"geometry readable at 390: {record['geometry_readable_at_390']} "
          f"({box_ink_px_at_390} px >= {READABILITY_MIN_PX} px rule)")
    print(f"pixel readable at 390 (all thresholds): "
          f"{record['pixel_readable_at_390']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
