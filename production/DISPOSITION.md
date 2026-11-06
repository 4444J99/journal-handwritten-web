# T07 per-issue disposition

Status of every issue in scope. None is closed by this kit; T03/PR #101 owns
posting and public-build mechanics.

| Issue | Disposition | Where |
|---|---|---|
| #38 | Reel template delivered as 6 s silent 1080×1920 soft wipe between two preserved versions, no overlay copy. Paired with the same candidate's carousel. | `production/exports/p001/reel/`, `production/kit/kit.py::make_reel` |
| #39 | Physical journal unavailable is not a blocker: the kit sources preserved scans and preserves source identity per crop. Original Live Photo/video close-ups remain missing and are listed, not fabricated. | `production/assets/`, `production/exports/p001/manifest.json` |
| #45 | Three comparable 4:5 cover treatments delivered: A1 stack, A2 page, A3 opening line, all from one source package at 1080×1350. | `production/exports/p001/4x5/`, `production/kit/templates/frame-4x5.html` |
| #47 | Fixed 4:5 carousel frame and grid consistency: same margins, paper tone, card shadow and identity chip across all stills; contact sheet for grid review. | `production/exports/p001/qa/contact-sheet.jpg` |
| #48 | Scans cropped to paper; tall pages get a cover crop for 4:5; handle `forms_verse` retained from T06 (no change here). | `production/kit/kit.py::render_*` |
| #66 | Widget path turned into a real scan-based kit: private tiles in 1×1, 2×2, 2×1 and wide sizes, with a private zip and device-test record. Shared-album behaviour remains untested and is named. | `production/exports/p001/widget/`, `production/device/` |
| #67 | Mockups recovered from the bundled design canvas into inspectable boards and converted into a real scan-based widget/download kit. Recovered boards are design evidence only, not releasable assets. | `production/reference/mockups/`, `production/tools/recover_mockups.py` |
| #68 | 9:16 assembly prepared: 9 s, write-on page (4.5 s) + hold, two looping layers as slots. Finished sample still needs the author's original Live Photo/video clips; reconstructed stroke animation is left as an artistic decision. | `production/exports/p001/story/`, `production/kit/templates/story-9x16.html` |

## Cross-cutting

- T03 clearance applied to every scan, crop, screenshot, version and downloadable
  file: `may_publish: false`, `author_clearance: null`, per-asset hashes.
- Private previews stay private; no public build was made.
- Cleared poem ID alone is not sufficient; outputs are invalidated by any
  changed text, review, final-version selection, pool, source or scan derivative.
- Target-journal treatment of Stories is researched, not assumed; see
  `production/reference/target-journal-stories-2026-11-06.md`.
- Second-piece substitution demonstrated and checked:
  `production/exports/substitution-check.json`.
- Missing inputs documented in each manifest's `missing` array and in
  `production/device/`.
