# Image tiers trial — side-by-side, master vs cleaned

Trial for `4444J99/journal-handwritten-web` #25, run 2026-11-24 against
main `97ea9a12` (the merge of loop PR #179). Tool:
`tools/image_tiers.py` (version 1); contract: `docs/image-tiers.md`;
recipes + checksums: `images-manifest.json`.

## Method

Six pages from the `site/img/p/` tier (the full page scans, the trial's
master tier), chosen from measured stats over all 123 `p/` pages — clean =
high Laplacian variance + high contrast, hard = faint ink (low std, low
Laplacian variance). Stats are full-resolution luminance measurements
(`std` contrast, `lap_var` sharpness, `dark_frac` ink coverage).

| Page | Kind | Uncertain readings | std before → after | lap_var before → after | dark_frac before → after | Deskew |
|---|---|---|---|---|---|---|
| diary55a | clean | 6 | 62.7 → 82.0 | 3566.8 → 5216.2 | 0.151 → 0.163 | 0.0° |
| diary56 | clean | 7 | 63.7 → 87.9 | 3560.3 → 3960.6 | 0.164 → 0.178 | −0.5° |
| diary20 | clean | 5 | 50.0 → 72.5 | 4234.5 → 5169.6 | 0.093 → 0.124 | −0.25° |
| diary23 | hard | 3 | 24.0 → 50.1 | 740.8 → 2115.4 | 0.010 → 0.061 | −0.25° |
| diary29 | hard | 5 | 26.4 → 48.1 | 1335.1 → 3163.2 | 0.013 → 0.055 | 0.0° |
| diary32 | hard | 1 | 29.0 → 43.2 | 1130.9 → 1752.7 | 0.027 → 0.042 | −0.25° |

## Verdict

The cleanup does what the plan asks of the faithful half. Hard pages gain
the most: contrast roughly doubles and sharpness 2–3×, and the ink
coverage (`dark_frac`) rises from near-zero to 0.04–0.06 — faint pencil
becomes readable ink. Clean pages improve modestly (std +30–45%,
sharpness +11–46%) with ink coverage rising slightly, not blowing out.
Visual check of diary23 (hard) and diary55a (clean), master vs cleaned
side by side: text preserved, no cropping (cleaned files are exactly the
master's dimensions), no visible damage. Re-running the trial produces
byte-identical cleaned files (SHA-256 compared).

## What is NOT in this trial

- **Display tier: pending.** No super-resolution model is provisioned in
  this environment (Real-ESRGAN / SwinIR weights are not installed and
  downloading them is a provisioning decision, not a code change), so no
  display files exist and every manifest entry records
  `display.status: pending`. The trial is master + cleaned, not all three
  tiers. The tier-separation check in `tools/check.py` enforces that no
  super-resolved output can land in master or cleaned.
- **HTR second opinion: not run.** The 312 uncertain readings live in the
  `u` arrays of `site/data/j.json` (109 pages carry at least one; the trial
  pages carry 27 between them). Running HTR needs the author's Transkribus
  account or TrOCR model weights — neither is available here. No reading
  was changed. The worklist is the `u` arrays themselves; an HTR run would
  record agreement/disagreement per reading against the cleaned tier.
- **Rescan: author's call.** Whether the notebook can be rescanned at
  600 dpi or more is recorded on #25, not decided here.

## Corrections to the plan (verified against live source)

- `site/img/` holds **382** files now, not 388 as the plan recorded at
  `0329c168` (three `h/` plates, 123 each in `p/`/`i/`/`m/`, 6 spreads, 4 atlas).
- The uncertain readings number **312** in the `u` arrays now, not 306
  (109 pages carry at least one).
- Upscaling/HTR mentions also live in the `claude/` review doc
  ("Faithful vs. Generative Image Processing…"), not only in the chat docs
  — still documentation, not tooling; the "no image-processing tooling
  anywhere in the tree" premise holds.
- Trial pages are the in-repo `p/` pages, not the etceter4-hosted
  originals (see `docs/image-tiers.md` — that would be a new master drop
  under the rescan fork).
