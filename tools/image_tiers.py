#!/usr/bin/env python3
"""Deterministic image tiers for 4444J99/journal-handwritten-web #25.

Implements the faithful (deterministic) half of the three-tier pipeline the
issue proposes: a checksummed master, a cleaned tier, and a display tier.
Only the cleaned tier is built here; the display tier needs an AI
super-resolution model (Real-ESRGAN / SwinIR weights), which is not
provisioned in this environment, so display entries stay "pending" and the
tier-separation check enforces that no super-resolved output can land in
master or cleaned. HTR (Transkribus / TrOCR) is likewise not run here: it
needs the author's Transkribus account or TrOCR model weights.

Cleanup (all deterministic, parameters recorded in the per-page recipe):
deskew (projection-profile search on a downscaled copy), lighting
flattening by division against an estimated background (which also
suppresses faint show-through), percentile contrast stretch, median
denoise, unsharp mask. The master is only ever read, never written;
the tool refuses an output path equal to the master path.

JHW #48 (2026-11-27) adds the crop tier: `crop` measures every p/ master
for its paper box (two-pass border-darkness measurement; the exchange doc's
"black bars" exist on only diary25/diary25a, and j.json already records
their box in each page's `c`), then derives one 4:5 cover per page from the
opening block's j.json line boxes (kit.py render_line rule: opening-block
crop contained on a 1080x1350 paper canvas, upper third; pages with no line
boxes fall back to the whole paper box, kit.py render_page rule) and writes
it to site/img/crop/<page>.jpg, recorded in images-crops.json. The crop
tier is a separate manifest from images-manifest.json so the #25 trial
entries keep their own verifier; tools/check.py verifies the crops manifest
with the standard library alone.

    python3 tools/image_tiers.py measure site/img/p/diary55a.jpg
    python3 tools/image_tiers.py clean site/img/p/diary55a.jpg images/cleaned/diary55a.jpg
    python3 tools/image_tiers.py trial [--out-dir images/cleaned]
    python3 tools/image_tiers.py verify-manifest [images-manifest.json]
    python3 tools/image_tiers.py crop [--out-dir site/img/crop]
    python3 tools/image_tiers.py verify-crops

Requires Pillow, numpy, scipy (local tooling only; tools/check.py verifies
the manifest with the standard library alone, so CI needs no new deps).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "images-manifest.json"
CROPS_MANIFEST = ROOT / "images-crops.json"
TOOL_VERSION = "2"  # v2 (JHW #48) adds the crop subcommand; v1 built the cleaned tier

# Crop tier (JHW #48). Values mirror production/kit/kit.py (W4/H4, MARGIN,
# PAPER_RGB, JPEG_QUALITY) so the per-page cover rule is the kit's
# render_line/render_page rule, not a second geometry. The kit pastes its
# cards with a shadow; the crop tier does not — the cover is a plain
# derivative the reader/template loads in place of a CSS crop, and a shadow
# would be baked into the image rather than chosen by the surface.
COVER_W, COVER_H = 1080, 1350
COVER_MARGIN = 72
COVER_PAD = (0.030, 0.020)  # kit.py render_line pad on the selection box
COVER_TOP_FRAC = 0.20  # kit.py render_line: cover sits in the upper third
PAPER_RGB = (247, 245, 239)
CROP_DIR = "site/img/crop"
# Paper-box measurement: a border is a "black bar" only when its rows/columns
# are almost entirely dark (value < 60). A paper row/column is mostly bright
# even with ink. Two passes because a vertical dark band (diary25: the dark
# surface left of the paper) defeats row-wise detection on its own.
CROP_DARK = 60
CROP_PAPER_FRAC = 0.5
CROP_SMALL_MAX = 500

# Trial pages, chosen 2026-11-24 from measured stats on the p/ tier
# (full page scans, 1086-1463 px wide): clean = high Laplacian variance +
# high contrast; hard = faint ink (low std, low Laplacian variance).
# See docs/image-tiers-trial.md for the numbers.
TRIAL_PAGES = {
    "diary55a": "clean",
    "diary56": "clean",
    "diary20": "clean",
    "diary23": "hard",
    "diary29": "hard",
    "diary32": "hard",
}

PARAMS = {
    "color_mode": "RGB",
    "deskew_search_deg": [-3.0, 3.0],
    "deskew_step_deg": 0.25,
    "deskew_min_deg": 0.25,
    "deskew_small_max_dim": 500,
    "background": {"method": "percentile-90", "small_max_dim": 400, "filter_size": 15},
    "contrast": {"method": "percentile-stretch", "lo": 1, "hi": 99},
    "denoise": {"method": "median", "size": 3},
    "sharpen": {"method": "unsharp", "amount": 0.5, "sigma": 2.0},
    "jpeg_quality": 92,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gray_stats(gray: np.ndarray) -> dict:
    """Measurement stats on a grayscale float array (0-255)."""
    lap = ndimage.laplace(gray)
    return {
        "mean": round(float(gray.mean()), 1),
        "std": round(float(gray.std()), 1),
        "lap_var": round(float(lap.var()), 1),
        "dark_frac": round(float((gray < 128).mean()), 4),
    }


def luminance(rgb: np.ndarray) -> np.ndarray:
    return 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]


def downscale(arr: np.ndarray, max_dim: int) -> np.ndarray:
    h, w = arr.shape[:2]
    s = min(1.0, max_dim / max(h, w))
    if s >= 1.0:
        return arr
    nh, nw = max(1, int(h * s)), max(1, int(w * s))
    return np.asarray(
        Image.fromarray(arr.astype(np.uint8)).resize((nw, nh), Image.LANCZOS)
    ).astype(np.float32)


def estimate_skew(gray: np.ndarray) -> float:
    """Best deskew angle by projection-profile variance on a small copy."""
    small = downscale(gray, PARAMS["deskew_small_max_dim"])
    ink = (small < 200).astype(np.float32)
    lo, hi, step = PARAMS["deskew_search_deg"][0], PARAMS["deskew_search_deg"][1], PARAMS["deskew_step_deg"]
    best_angle, best_score = 0.0, -1.0
    angle = lo
    while angle <= hi + 1e-9:
        rot = ndimage.rotate(ink, angle, reshape=False, order=0, mode="constant", cval=0.0)
        score = float(rot.sum(axis=1).var())
        if score > best_score:
            best_score, best_angle = score, angle
        angle += step
    return round(best_angle, 2)


def estimate_background(gray: np.ndarray) -> np.ndarray:
    """Paper background estimated on a small copy, upscaled to full size."""
    small = downscale(gray, PARAMS["background"]["small_max_dim"])
    bg_small = ndimage.percentile_filter(small, 90, size=PARAMS["background"]["filter_size"], mode="nearest")
    zoom = (gray.shape[0] / bg_small.shape[0], gray.shape[1] / bg_small.shape[1])
    bg = ndimage.zoom(bg_small, zoom, order=1)
    bg = bg[: gray.shape[0], : gray.shape[1]]
    if bg.shape != gray.shape:  # rounding guard
        bg = np.asarray(Image.fromarray(bg.astype(np.uint8)).resize((gray.shape[1], gray.shape[0]), Image.BILINEAR)).astype(np.float32)
    return np.clip(bg, 1.0, None)


def clean_array(rgb: np.ndarray) -> tuple[np.ndarray, dict]:
    """Run the deterministic cleanup; returns (cleaned RGB float array, measurements)."""
    before = gray_stats(luminance(rgb))
    gray = luminance(rgb)
    angle = estimate_skew(gray)
    applied_angle = 0.0
    work = rgb
    if abs(angle) >= PARAMS["deskew_min_deg"]:
        # ndimage.rotate rotates the (H, W) plane of each channel; reshape=False keeps size.
        work = ndimage.rotate(work, angle, axes=(0, 1), reshape=False, order=1, mode="nearest")
        applied_angle = angle
    flat_gray = luminance(work)
    bg = estimate_background(flat_gray)
    scale = float(np.clip(bg, 1, None).mean())
    work = np.clip(work / bg[:, :, None] * scale, 0, 255)
    lo, hi = np.percentile(work, [PARAMS["contrast"]["lo"], PARAMS["contrast"]["hi"]])
    if hi > lo:
        work = np.clip((work - lo) * 255.0 / (hi - lo), 0, 255)
    work = ndimage.median_filter(work, size=(3, 3, 1), mode="nearest")
    blur = ndimage.gaussian_filter(work, sigma=(PARAMS["sharpen"]["sigma"], PARAMS["sharpen"]["sigma"], 0))
    work = np.clip(work + PARAMS["sharpen"]["amount"] * (work - blur), 0, 255)
    after = gray_stats(luminance(work))
    measurements = {
        "before": before,
        "after": after,
        "deskew_deg": applied_angle,
        "deskew_estimated_deg": angle,
        "contrast_percentiles": [round(float(lo), 1), round(float(hi), 1)],
        "background_mean": round(scale, 1),
    }
    return work, measurements


def clean_file(master: Path, out: Path, grayscale: bool = False) -> dict:
    """Clean one master image; returns the recipe dict for the manifest."""
    master = master.resolve()
    out = out.resolve()
    if out == master:
        raise ValueError("refusing to write the cleaned tier over the master")
    if "images" not in out.parts:
        raise ValueError("cleaned output must live under images/")
    img = Image.open(master)
    if grayscale:
        img = img.convert("L").convert("RGB")
    else:
        img = img.convert("RGB")
    rgb = np.asarray(img).astype(np.float32)
    cleaned, measurements = clean_array(rgb)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(cleaned, 0, 255).astype(np.uint8)).save(
        out, format="JPEG", quality=PARAMS["jpeg_quality"]
    )
    recipe = {
        "color_mode": "L" if grayscale else PARAMS["color_mode"],
        "deskew_deg": measurements["deskew_deg"],
        "background": PARAMS["background"],
        "contrast": PARAMS["contrast"],
        "denoise": PARAMS["denoise"],
        "sharpen": PARAMS["sharpen"],
        "jpeg_quality": PARAMS["jpeg_quality"],
        "sr": None,
        "measurements": measurements,
    }
    return recipe


def manifest_entry(page_id: str, master_rel: str, cleaned_rel: str, recipe: dict) -> dict:
    master_path = ROOT / master_rel
    cleaned_path = ROOT / cleaned_rel
    return {
        "master": master_rel,
        "master_sha256": sha256(master_path),
        "cleaned": cleaned_rel,
        "cleaned_sha256": sha256(cleaned_path),
        "recipe": recipe,
        "display": {
            "status": "pending",
            "reason": "no super-resolution model provisioned "
            "(Real-ESRGAN / SwinIR weights not available in this environment); "
            "a display tier must record its sr model + version when built",
        },
    }


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {"version": 1, "tool": "tools/image_tiers.py", "tool_version": TOOL_VERSION, "pages": {}}


# ---------------------------------------------------------------------------
# Crop tier (JHW #48)
# ---------------------------------------------------------------------------

def _edge_inset(frac, from_start=True) -> int:
    """First row/column from one side whose dark fraction drops below paper.

    A row/column counts as paper when it and the next two (a run of three)
    are all below CROP_PAPER_FRAC dark — a single stray dark row from a
    smudge or the page-edge shadow must not move the box.
    """
    n = len(frac)
    idxs = range(n) if from_start else range(n - 1, -1, -1)
    for i in idxs:
        if from_start:
            window = [frac[j] for j in range(i, min(n, i + 3))]
        else:
            window = [frac[j] for j in range(max(0, i - 2), i + 1)]
        if all(f < CROP_PAPER_FRAC for f in window):
            return i if from_start else (n - 1 - i)
    return 0


def paper_box(gray: np.ndarray) -> dict:
    """Measure the paper bounding box of a scan as normalized [x0, y0, x1, y1].

    Two passes: column profiles over the full height give left/right, then
    row profiles restricted to the paper's column range give top/bottom.
    One pass fails on diary25, where a vertical dark band (the desk left of
    the paper) makes every full-width row >50% dark and the bottom inset
    walks to the top of the image. Returns the box plus pixel insets and the
    paper aspect; the box is the full frame when no bar is present.
    """
    small = downscale(gray, CROP_SMALL_MAX)
    h, w = small.shape[:2]
    dark = (small < CROP_DARK).astype(np.float32)
    col_frac = dark.mean(axis=0)
    left = _edge_inset(col_frac, True)
    right = _edge_inset(col_frac, False)
    sub = dark[:, left:w - right] if (w - right) > left else dark
    row_frac = sub.mean(axis=1)
    top = _edge_inset(row_frac, True)
    bottom = _edge_inset(row_frac, False)
    fw, fh = gray.shape[1] / w, gray.shape[0] / h
    x0, y0 = round(left * fw), round(top * fh)
    x1, y1 = round(gray.shape[1] - right * fw), round(gray.shape[0] - bottom * fh)
    box = [round(x0 / gray.shape[1], 4), round(y0 / gray.shape[0], 4),
           round(x1 / gray.shape[1], 4), round(y1 / gray.shape[0], 4)]
    return {
        "box_norm": box,
        "box_px": [x0, y0, x1, y1],
        "inset_px": {"top": round(top * fh), "bottom": round(bottom * fh),
                     "left": round(left * fw), "right": round(right * fw)},
        "aspect": round((x1 - x0) / max(1, y1 - y0), 3),
    }


def opening_block_box(page: dict) -> tuple[list | None, int | None]:
    """Union of the opening block's j.json line boxes, normalized.

    Returns (box, block) where block is the lowest-numbered block with line
    boxes. Block 0 is the opening block on most pages, but 13 pages carry
    line boxes only in a later block (their block 0 has no geometry — e.g. a
    header with no rows), so the opening block is the first block WITH
    geometry, not hardcoded 0. Returns (None, None) when the page has no
    `x` rows at all (23 pages: strips and the diary25 pair) — those fall
    back to the whole paper box. Block geometry lives only in `x`; `B`
    carries line text, not boxes.
    """
    rows = page.get("x") or []
    if not rows:
        return None, None
    first = min(r[0] for r in rows)
    block_rows = [r for r in rows if r[0] == first]
    box = [round(min(r[2] for r in block_rows), 4), round(min(r[3] for r in block_rows), 4),
           round(max(r[4] for r in block_rows), 4), round(max(r[5] for r in block_rows), 4)]
    return box, first


def _pad_box(box, pad_x, pad_y):
    x0, y0, x1, y1 = box
    return [max(0.0, x0 - pad_x), max(0.0, y0 - pad_y),
            min(1.0, x1 + pad_x), min(1.0, y1 + pad_y)]


def _intersect(a, b):
    return [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]


def _fit_contain_size(w, h, max_w, max_h):
    s = min(max_w / w, max_h / h)
    return max(1, round(w * s)), max(1, round(h * s))


def cover_image(master: Path, page: dict) -> tuple[Image.Image, dict]:
    """Derive one page's 4:5 cover (1080x1350) from its p/ master.

    Rule (the plan's step 3, kit.py's render_line/render_page geometry):
    crop the opening block's line-box union — the lowest-numbered block
    with line boxes, padded (0.030, 0.020) and clamped to the measured
    paper box — then contain it on a 1080x1350 paper canvas, upper third
    (y = 20% of height), centered horizontally. Pages with no line boxes
    use the whole paper box instead (kit.py render_page rule, centered
    both ways). The paper canvas is PAPER_RGB,
    the same paper the kit renders on; no shadow card — the kit's shadow is
    an export treatment, and the crop tier is a plain derivative the reader
    or template loads in place of a CSS crop. Never touches the master or
    j.json (both read-only here).
    """
    img = Image.open(master).convert("RGB")
    w, h = img.size
    gray = luminance(np.asarray(img).astype(np.float32))
    paper = paper_box(gray)
    block, block_no = opening_block_box(page)
    if block is not None:
        box = _intersect(_pad_box(block, *COVER_PAD), paper["box_norm"])
        source = "opening-block"
    else:
        box = paper["box_norm"]
        source = "whole-paper"
    if box[2] <= box[0] or box[3] <= box[1]:
        box, source, block_no = paper["box_norm"], "whole-paper", None
    crop = img.crop((round(box[0] * w), round(box[1] * h),
                     round(box[2] * w), round(box[3] * h)))
    max_w, max_h = COVER_W - 2 * COVER_MARGIN, COVER_H - 2 * COVER_MARGIN
    cw, ch = _fit_contain_size(crop.width, crop.height, max_w, max_h)
    content = crop.resize((cw, ch), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (COVER_W, COVER_H), PAPER_RGB)
    x = (COVER_W - cw) // 2
    # Upper third (kit.py render_line) when the block is short, but clamped
    # so a tall opening block never runs past the bottom margin: kit.py's
    # rule assumes line crops, which are short; a full opening block can be
    # 1206px tall after contain, and y=270 would clip 126px off its bottom
    # (caught by the diary55a side-by-side, JHW #48 step 6).
    if source == "opening-block":
        y = min(round(COVER_H * COVER_TOP_FRAC), COVER_H - COVER_MARGIN - ch)
    else:
        y = (COVER_H - ch) // 2
    canvas.paste(content, (x, y))
    record = {
        "source": source,
        "block": block_no if source == "opening-block" else None,
        "paper_box_norm": paper["box_norm"],
        "paper_box_px": paper["box_px"],
        "cover_box_norm": [round(v, 4) for v in box],
        "cover_size": [COVER_W, COVER_H],
    }
    return canvas, record


def crops_manifest_entry(page_id: str, master_rel: str, cover_rel: str, record: dict) -> dict:
    master_path = ROOT / master_rel
    cover_path = ROOT / cover_rel
    return {
        "master": master_rel,
        "master_sha256": sha256(master_path),
        "paper_box_norm": record["paper_box_norm"],
        "paper_box_px": record["paper_box_px"],
        "cover": {
            "file": cover_rel,
            "sha256": sha256(cover_path),
            "width": COVER_W,
            "height": COVER_H,
            "source": record["source"],
            "block": record["block"],
            "cover_box_norm": record["cover_box_norm"],
        },
    }


def load_crops_manifest() -> dict:
    if CROPS_MANIFEST.exists():
        return json.loads(CROPS_MANIFEST.read_text())
    return {"version": 1, "tool": "tools/image_tiers.py",
            "tool_version": TOOL_VERSION, "pages": {}}


def cmd_crop(args) -> int:
    """Measure every p/ master and write one 4:5 cover per page (JHW #48)."""
    import datetime
    out_dir = Path(args.out_dir)
    if out_dir.resolve() != (ROOT / CROP_DIR).resolve():
        raise ValueError(f"crop output must live under {CROP_DIR}")
    data = json.loads((ROOT / "site/data/j.json").read_text())
    manifest = load_crops_manifest()
    manifest["tool_version"] = TOOL_VERSION
    out_dir_abs = ROOT / out_dir
    out_dir_abs.mkdir(parents=True, exist_ok=True)
    for page in data["pages"]:
        pid = page["id"]
        master_rel = f"site/img/p/{pid}.jpg"
        cover_rel = f"{out_dir.as_posix()}/{pid}.jpg"
        master_path = ROOT / master_rel
        if not master_path.is_file():
            print(f"{pid}: SKIP master missing: {master_rel}")
            continue
        cover, record = cover_image(master_path, page)
        cover.save(ROOT / cover_rel, format="JPEG", quality=PARAMS["jpeg_quality"])
        manifest["pages"][pid] = crops_manifest_entry(pid, master_rel, cover_rel, record)
        pb = record["paper_box_px"]
        aspect = round((pb[2] - pb[0]) / max(1, pb[3] - pb[1]), 3)
        print(f"{pid}: {record['source']} paper_aspect={aspect} cover={cover_rel}")
    manifest["generated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    CROPS_MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"wrote {CROPS_MANIFEST} ({len(manifest['pages'])} pages)")
    return 0


def cmd_verify_crops(args) -> int:
    sys.path.insert(0, str(ROOT / "tools"))
    from check import verify_crops_manifest

    problems = verify_crops_manifest(ROOT)
    for p in problems:
        print(p)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def cmd_measure(args) -> int:
    img = Image.open(args.image).convert("RGB")
    arr = np.asarray(img).astype(np.float32)
    print(json.dumps({"image": args.image, **gray_stats(luminance(arr))}, indent=1))
    return 0


def cmd_clean(args) -> int:
    recipe = clean_file(Path(args.master), Path(args.out), grayscale=args.grayscale)
    print(json.dumps(recipe, indent=1))
    return 0


def cmd_trial(args) -> int:
    manifest = load_manifest()
    manifest["tool_version"] = TOOL_VERSION
    out_dir = Path(args.out_dir)
    for page_id, kind in TRIAL_PAGES.items():
        master_rel = f"site/img/p/{page_id}.jpg"
        cleaned_rel = f"{out_dir.as_posix()}/{page_id}.jpg"
        recipe = clean_file(ROOT / master_rel, ROOT / cleaned_rel)
        manifest["pages"][page_id] = manifest_entry(page_id, master_rel, cleaned_rel, recipe)
        m = recipe["measurements"]
        print(f"{page_id} ({kind}): deskew {m['deskew_deg']} deg | "
              f"std {m['before']['std']} -> {m['after']['std']} | "
              f"lap_var {m['before']['lap_var']} -> {m['after']['lap_var']} | "
              f"dark_frac {m['before']['dark_frac']} -> {m['after']['dark_frac']}")
    manifest["generated"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"wrote {MANIFEST} ({len(manifest['pages'])} pages)")
    return 0


def cmd_verify(args) -> int:
    sys.path.insert(0, str(ROOT / "tools"))
    from check import verify_images_manifest

    problems = verify_images_manifest(ROOT)
    for p in problems:
        print(p)
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic image tiers (JHW #25)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("measure")
    p.add_argument("image")
    p.set_defaults(fn=cmd_measure)
    p = sub.add_parser("clean")
    p.add_argument("master")
    p.add_argument("out")
    p.add_argument("--grayscale", action="store_true")
    p.set_defaults(fn=cmd_clean)
    p = sub.add_parser("trial")
    p.add_argument("--out-dir", default="images/cleaned")
    p.set_defaults(fn=cmd_trial)
    p = sub.add_parser("verify-manifest")
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("crop")
    p.add_argument("--out-dir", default=CROP_DIR)
    p.set_defaults(fn=cmd_crop)
    p = sub.add_parser("verify-crops")
    p.set_defaults(fn=cmd_verify_crops)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
