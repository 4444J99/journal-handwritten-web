# 2026-11-24 E2E witness ingestion and chronology test suite

## Produced
- `tests/e2e_witness/` (10 files: `__init__.py`, `cli_adapters.py`, `fixtures.py`, `validators.py`, `stubs.py`, `tier1_features.py`, `tier2_boundaries.py`, `tier3_4_pipelines.py`, `run_e2e.py`, `test_e2e_witness.py`): Requirement-driven, opaque-box 4-tier E2E test suite (169 checks: 70 Tier 1, 68 Tier 2, 16 Tier 3, 8 Tier 4, 7 Negative Controls) covering `tool-notes-docs-capture` + `journal-handwritten-web` via subprocess CLIs and isolated temp sandboxes.

## Author decisions
- Keep device-level capture (`tool-notes-docs-capture`), external non-git custody (`/Volumes/Archive4T/Media/intake/versforms-witnesses/`), and public-safe site chronology (`journal-handwritten-web`) strictly separated.
- Enforce Two-Clock Rule (`digitized_at` never used as a composition bound), human-confirmation gating (`pending_review`), public-repo privacy hygiene, and Round 1 JPEG metadata stripping + shared-surface isolation (`diary62a`/`p126`, etc.), leaving `site/`, `studio/`, `MANIFEST.sha256`, `source/canonical.json`, and `release/public.json` unmodified.

## Plan / next steps
- Plan (suggested): Point `tests/e2e_witness/run_e2e.py --tndc-dir <path> --jhw-dir <path> --tier all` at the integrated M1 + M2 + M3 branches in the Final Milestone to verify 100% real-target pass before Tier 5 hardening.

## Status
Implemented and verified in `--self-check` mode (`169/169` checks passing, `0` skipped, `tools/check.py` `OK`, `0` bare browser launches) on isolated branch `test/e2e-witness-suite`.
