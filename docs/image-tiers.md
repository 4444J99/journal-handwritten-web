# Image tiers — master, cleaned, display

Contract for `4444J99/journal-handwritten-web` #25
([2026-10-27-image-upscaling-methods] 01 · Image processing and upscaling
options for page scans). Implemented by `tools/image_tiers.py`; verified by
`tools/check.py` on every push/PR.

## The three tiers

| Tier | Location | What it is | Rule |
|---|---|---|---|
| **Master** | `site/img/**` (in place; the `p/` tier holds the full page scans) | The scan as published; checksummed in `MANIFEST.sha256` | Never written by the pipeline. The tool only reads it and refuses an output path equal to the master path. |
| **Cleaned** | `images/cleaned/<page>.jpg` | Deterministic cleanup of the master: deskew, lighting flattening (which also suppresses faint show-through), percentile contrast stretch, median denoise, unsharp mask | No AI, no invented pixels. Parameters + measurements recorded per page in `images-manifest.json`. Colour is kept (RGB) — the plan's cleanup list does not include desaturation, and least transformation is the most faithful choice. |
| **Display** | `images/display/<page>.jpg` | Cleaned tier + AI super-resolution (Real-ESRGAN / SwinIR), **display use only** | Must record its super-resolution model + version in the manifest. A display file with no recorded model is not a display tier. **Pending:** no SR model is provisioned in this environment, so no display files exist yet and every trial entry records `display.status: pending`. |

## Recipe schema (`images-manifest.json`)

One entry per trial page:

```json
{
  "master": "site/img/p/diary55a.jpg",
  "master_sha256": "<sha256 of the master>",
  "cleaned": "images/cleaned/diary55a.jpg",
  "cleaned_sha256": "<sha256 of the cleaned file>",
  "recipe": {
    "color_mode": "RGB",
    "deskew_deg": 0.0,
    "background": {"method": "percentile-90", "small_max_dim": 400, "filter_size": 15},
    "contrast": {"method": "percentile-stretch", "lo": 1, "hi": 99},
    "denoise": {"method": "median", "size": 3},
    "sharpen": {"method": "unsharp", "amount": 0.5, "sigma": 2.0},
    "jpeg_quality": 92,
    "sr": null,
    "measurements": {
      "before": {"mean": 220.8, "std": 62.7, "lap_var": 3566.8, "dark_frac": 0.151},
      "after": {"mean": 213.4, "std": 82.0, "lap_var": 5216.2, "dark_frac": 0.163},
      "deskew_deg": 0.0,
      "deskew_estimated_deg": 0.0,
      "contrast_percentiles": [12.0, 252.0],
      "background_mean": 248.0
    }
  },
  "display": {"status": "pending", "reason": "no super-resolution model provisioned ..."}
}
```

`measurements` are computed on the luminance channel at full resolution:
`mean` / `std` (brightness / contrast), `lap_var` (Laplacian variance —
sharpness), `dark_frac` (fraction of pixels below 128 — ink coverage).
`sr` is `null` in a cleaned recipe by construction; any entry claiming a
super-resolution model in `master` or `cleaned` fails `tools/check.py`.

## Determinism

Same master + same tool version produce byte-identical cleaned files
(verified 2026-11-24 by running the trial twice and comparing SHA-256).
Rebuilding a page is re-running `tools/image_tiers.py clean` with the
recorded recipe; a changed recipe is a new `tool_version`, not a silent edit.

## Rescan fork (author's decision)

Whether the notebook can be rescanned at 600 dpi or more is the author's
call. The pipeline accepts a new master drop without rework: the new master
is checksummed into `MANIFEST.sha256`, the cleanup is re-run, and the recipe
records the new master hash. Nothing in the cleaned or display tier assumes
a particular master resolution.

## Trial pages

The trial (see `docs/image-tiers-trial.md`) uses the in-repo `site/img/p/`
pages — the pipeline's master tier is this repo's images. The exchange doc's
suggestion of sample pages "from the etceter4 repo" is not used: those
originals are not in this repo, and pulling them in would be a new master
drop, which belongs to the rescan fork above.

## Running it

```sh
python3 tools/image_tiers.py measure site/img/p/diary55a.jpg
python3 tools/image_tiers.py clean site/img/p/diary55a.jpg images/cleaned/diary55a.jpg
python3 tools/image_tiers.py trial            # the six trial pages
python3 tools/image_tiers.py verify-manifest  # same checks CI runs
python3 tools/check.py                        # full integrity check incl. manifest
```

Requires Pillow, numpy, scipy (local tooling only). `tools/check.py`
verifies the manifest with the standard library alone, so CI needs no new
dependencies.
