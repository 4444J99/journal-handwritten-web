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

    python3 tools/image_tiers.py measure site/img/p/diary55a.jpg
    python3 tools/image_tiers.py clean site/img/p/diary55a.jpg images/cleaned/diary55a.jpg
    python3 tools/image_tiers.py trial [--out-dir images/cleaned]
    python3 tools/image_tiers.py verify-manifest [images-manifest.json]

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
TOOL_VERSION = "1"

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
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
