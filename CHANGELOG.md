# Changelog

## v2026.11.05 — merged piece v4

- `site/index.html` replaced with merged-piece artifact `1Pcbgrvp7BqfmcYhzZLEss` version `1793184934-ad80` (v4 interaction fixes, listed in `docs/plan.md`). Data and images unchanged.
- `docs/chats/`: plan record for every Project chat; `CLAUDE.md`.

## v2026.10.27 — repository seeded

- Seeded from the published artifacts:
  - merged piece `1Pcbgrvp7BqfmcYhzZLEss`, version `1792955670-ab9e` → `site/`
  - review studio `MVognnZQrtRQ6QCMaF7341`, version `1793153798-80b3` (page) / `1792953621-84a2` (data, thumbnails; unchanged in the later version) → `studio/`
- Studio full scans and spreads de-duplicated against `site/img/p` and `site/img/s` (byte-identical).
- Added `tools/check.py`, `tools/studio_files.py`, `MANIFEST.sha256`, CI check, manual Pages workflow.
- Content unchanged from the artifacts: transcriptions remain unverified by the author.
