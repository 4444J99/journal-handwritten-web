# Witness chronology and Round 1 projection integration

Date: 2026-11-25 (America/New_York). Repo: `journal-handwritten-web`, branch
`feat/witness-matcher` (Stage 2 matcher plus Stage 3 chronology and projection).

## Produced

- Verified the existing Stage 2 matcher at `922876b` against R4 and the public-repo privacy
  rules: no device-capture code, no `digitized_at` use, forbidden public keys rejected,
  new links default to `pending_review`, confirmed links preserved on re-run.
- Re-ran `python3 tools/check.py` (`OK`: 509 references, 539 checksums, 0 bare launches).
- Re-ran `python3 tools/ci_local.py`: all five suites passed on `922876b`
  (`check`, 443 py-tests / 1 skipped, 138 node pass / 12 skipped, 68 studio-cf-py /
  2 skipped, 178 studio-cf-node). The previously reported PID-file timing race in
  `test_verify_site_cleanup.mjs` did not reproduce; no failure needed attributing to `origin/main`.
- Added `tools/build_chronology.py`: confirmed-only Stage 3 amalgamation from
  `source/witness_links.json` + `site/data/j.json` + `source/canonical.json` into
  `source/chronology.json`. Supports `photo_anchored`, `interpolated`,
  `extrapolated_head`, `extrapolated_tail` (and `undated` with no anchors), dual sort
  orders, and shared-surface flags. `digitized_at` is provenance metadata only and is
  never consulted when computing a window, estimate, anchor, or sort key.
- Added `tools/export_round1_projection.py`: Round 1 JPEG projections rebuilt from a
  fresh pixel buffer (no EXIF/XMP/GPS/ICC/thumbnail), with isolated crops for
  co-tenanted pages and blocking for spread-exposed pages.
- Added `tests/test_build_chronology.py` (10 tests) and
  `tests/test_export_round1_projection.py` (7 tests), all using temporary output
  directories and leaving protected paths untouched.
- Rebased onto `origin/main` at `dea3fe0`. Its full Python suite had two failures
  reproduced on a clean `origin/main` worktree: a font-renaming test mock with the
  old one-argument signature, and `tests/test_image_tiers.py` importing
  `tools/image_tiers.py` (which needs optional `scipy`) before its own skip guard.
  Both were repaired in test files only; no production code was changed for them.

## Author decisions

- The author approved the two-repository design: device-level capture stays in the
  private `tool-notes-docs-capture`; raw exports stay in non-git custody at
  `/Volumes/Archive4T/Media/intake/versforms-witnesses/`; only public-safe metadata
  enters `journal-handwritten-web`.
- The author requires: read-only capture, no auto-confirmation, the Two-Clock Rule,
  public-repo privacy hygiene, and a passing `tools/check.py` before finishing.
- The author gated the live harvest and link confirmation behind their own choice of
  album/folder/year and their review; those steps were not performed here.

## Plan / next steps

- Suggestion: keep Stage 3 on this branch so M2 and M3 land together off `origin/main`;
  run the full E2E Tiers 1–4 suite against the integrated worktrees, then open the PR.
- Suggestion: the author still needs to choose `PHOTOS_ALBUM`, `NOTES_FOLDER` and
  `MAX_YEAR`, run the live harvest, and manually confirm links before any real
  `source/witness_links.json` / `source/chronology.json` is generated in the site repo.
- Open question for the author: whether `journal-handwritten-web` should be private
  (GitHub reports public; the README says private).
- Open question for the author: whether standalone iOS Notes need a third siglum `N` or
  an `S` tagged `source_medium=ios_note`.

## Status

- `tools/check.py` passed after all edits; new unit tests passed (10 + 7).
- Full `ci_local.py` re-run after Stage 3 edits passed all five suites: `check` OK;
  460 py-tests / 1 skipped; 138 node pass / 12 skipped; 68 studio-cf-py / 2 skipped;
  178 studio-cf-node pass. The PID-file timing race did not reproduce.
- Nothing about the live harvest, link confirmation, repository visibility, or remote
  state is claimed here.
