# 2026-11-14 Pre-rendered release at full-release scale

## Produced
- Measured the pre-rendered path and the R2 reader Worker against the whole 126-piece export (518 files, 44.8 MB) instead of p001 only; results in `studio-cf/README.md` ("Pre-rendered release").
- `measure_release_cpu.mjs --accept ID,...` so a whole-release candidate with shared scans can be built for measurement (still in memory, forced gates, nothing written or published).
- No Cloudflare credential, no deploy, no private content published.

## Author decisions
None in this session.

## Plan / next steps
- Suggestion: deploy the pre-rendered output as a staging Pages project once the owner decides the hosting and Access question; hosted behaviour remains unobserved.

## Status
Measured locally only.
