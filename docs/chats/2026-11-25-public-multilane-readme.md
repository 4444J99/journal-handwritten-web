# Public-by-design README and multi-lane framing

Date: 2026-11-25 (America/New_York).

## Produced

- Fast-forwarded both main checkouts to `origin/main`: `tool-notes-docs-capture` to `321f32d`
  and `journal-handwritten-web` to `7e8be90`. Bootstrapped the JHW `.venv` (`rapidfuzz`
  installed) and created the capture `.venv` with the `dev` and `witness` extras.
- Rewrote the README's repository description and its "Public and private" section so they
  state that this repository is public by design and explain the custody boundaries that keep
  personal data out: private capture repo, non-git external intake directory, public-safe
  metadata only in `source/`.
- Added a "Corpus lanes and the Grand Chronology" section: `C` (Codex notebook), `N` (standalone
  original-era Apple Notes), `P` (unmatched photo witnesses), with further lanes possible and no
  fixed `001..100` ceiling; `source/chronology.json` as the Grand Chronology and curated
  100-piece arrangements/Round 1 schedules as downstream projections.
- Documented `tools/match_witnesses.py`, `tools/build_chronology.py` and
  `tools/export_round1_projection.py` plus their generated `source/` outputs in the Layout
  section, and added `rapidfuzz` to the local-gate dependency list.
- Added dated plan addenda to `docs/plan.md` and `claude/plan.md`, superseding the older
  "private repository" and "100 full poems, numbered n/100" framing without rewriting history.

## Author decisions

- `journal-handwritten-web` is intentionally public; isolation is architectural (device capture
  in the private repo, raw exports outside git, public-safe metadata only).
- The corpus is multi-lane and unbounded: `C`, `N`, `P`, and future lanes. Piece identities are
  not capped at 100. The Grand Chronology spans all lanes; curated arrangements and editions,
  including any 100-poem selection or Instagram Round 1 schedule, are separate projections.
- `digitized_at` is scan provenance and never a composition-date bound.
- Live Stage 1 harvest, link confirmation and writing `source/witness_links.json` /
  `source/chronology.json` remain author-gated and were not performed.

## Plan / next steps

- Suggestion: after this docs PR merges, run Stage 0 discovery from the private repo and use
  its album/folder listing to choose `PHOTOS_ALBUM`, `NOTES_FOLDER` and optional `MAX_YEAR`.
- Suggestion: keep curated edition/schedule outputs separate from `source/chronology.json` so
  the Grand Chronology stays an honest, unbounded timeline.

## Status

- Gates run before commit: `python3 tools/check.py` OK (511 references, 544 checksums, image
  tiers 0 problems, 0 bare launches); capture pytest 135 passed / 6 skipped / 34 subtests;
  JHW `unittest tests.test_build_chronology tests.test_export_round1_projection` 17 tests OK.
- Protected paths (`site/`, `studio/`, `MANIFEST.sha256`, `source/canonical.json`,
  `release/public.json`) are unmodified. No live harvest, link confirmation or raw data in the
  public repository is claimed here. PR/merge outcome is reported separately.
