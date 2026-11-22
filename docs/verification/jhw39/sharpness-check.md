# Sharpness check — web-size scan at phone resolution (#39)

**Issue:** 4444J99/journal-handwritten-web #39 ("Physical journal unavailable;
use scans"). **Plan:** implementation plan posted on #39 (comment 7076011206,
2026-11-22), executed here at main `447aad25`. **Check script:**
`tools/check_sharpness_jhw39.py` (deterministic; re-running it reproduces
`sharpness-check.json` byte-for-byte — verified by two runs this session).

## Question

From `docs/chats/2026-10-31-instagram-short-form-video/02-journal-unavailable-scans.md`:
zoom into one line of a web-sized scan at phone resolution; if soft, use the
2015 spread originals (`diary_originals.zip`) for close-ups.

## What was measured

Test line: diary1 block 0 line 0, **"The walls"** — the p001 Series
candidate, so the close-ups would actually be cut from this line. Line box
from `site/data/j.json`: `[0.0416, 0.0137, 0.3278, 0.0467]` (fractions of the
1135×1600 page). Source: the web-sized scan `site/img/i/diary1.jpg`
(851×1200). Phone scale: the page rendered at 390 px wide (page height
550 px), the same geometry `production/kit/kit.py::ink_metrics` uses.

| Measurement | Value | Rule |
|---|---|---|
| Box-geometry ink height at 390 px (kit's `ink_metrics`, same function the p001 QA uses) | **18.15 px** | ≥ 8 px |
| Pixel-measured ink height at 390 px (dark-pixel rows in the full-resolution crop, thresholds 96 / 128 / 160) | **17.87 / 18.33 / 18.33 px** | ≥ 8 px |
| Existing p001 QA for context (`production/exports/p001/qa/readability.json`, kit renders from the preserved source) | min 13.6–25.52 px at 390 | ≥ 8 px |

The two methods agree (18.15 vs 17.87–18.33 px), and the number is stable
across thresholds — the measurement is not a threshold artifact.

## Verdict: LEGIBLE — web-sized scans suffice for close-ups

"The walls" reads clearly in the phone-scale crop
(`diary1-block0-line0-phone390.png`, 112×18 px at true phone scale; the 4×
magnification is the same pixels enlarged for inspection). The web-sized
scan is **not soft** at phone resolution for this line.

**Branch taken (plan step 3a):** web-sized scans suffice for close-ups, and
the 2015 originals are **not needed for this purpose**. This does not answer
whether `diary_originals.zip` is reachable — that question is the author's
local machine, and it stays open in the exchange doc. If a close-up ever
needs more than the web file, the preserved scan
`production/assets/diary1.jpg` (1390×1959) is the next step up, not the zip.

## Observation: the recorded line box is tight (not a verdict-changer)

The recorded box clips glyph edges: ink touches the box's top and bottom
rows (dark pixels in rows 0 and 39 of the 40 px crop), the "T" crossbar
starts just left of the box, and the final "s" tail sits at its right edge.
A close-up cut from the raw box alone would shave the T and the s. This is
a property of the recorded box, not of the scan — the kit's own renders
already pad (`render_line` pads (0.030, 0.020), `render_detail` (0.025,
0.018)), so close-ups should keep using the padded render path, not the
raw box. No change to `j.json` is proposed here; the box is the line's
recorded geometry, and tightening/loosening it is a separate decision.

## Scope of this check

One line, one page, one verdict. It settles the binary question the
exchange doc asked for close-ups cut from diary1 — it does not certify
every page, and it is not a publishability claim. Physical-device review
is still required before anything ships (as the p001 QA record itself
states), and the p001 kit stays `may_publish: false` awaiting author
clearance.

## Evidence in this directory

- `diary1-block0-line0-phone390.png` — the line at true phone scale.
- `diary1-block0-line0-phone390-4x.png` — the same pixels, 4× magnification.
- `diary1-block0-line0-fullres.png` — the line crop from the web scan.
- `diary1-phone390-page.png` — the 390 px page render with the line box outlined.
- `sharpness-check.json` — all numbers + input hashes.
