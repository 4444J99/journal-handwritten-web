# 2026-11-06 — Integration execution (partial)

## Produced

- Merged PR #127 (T09 audio): widened `audio_pilot/serve.py` `SAMPLE_PATH` and `audio_pilot/app.js` filename regex to accept colon-containing request IDs (e.g. `forward:take1`), capped at 96 chars; preserved logical IDs. Head `982058e…` merged as `92202e3…`.
- Merged PR #128 (T10 script realizations): `source_fingerprint` now includes `breakBefore` (v2 logical-structure digest) while retaining `source_fingerprint_v1` for readable history/migration; validation accepts either. Head `f0a54a7…` merged as `8cd9872…`.
- Installed `fonttools`/`numpy` for default Python so `ci_local.py` runs; all suites pass on `main@8cd9872a`.
- Verification: `python3 tools/check.py` OK; `python3 tools/ci_local.py` PASS (210 py, 55 node, 54 studio-cf-py, 76 studio-cf-node).

## Author decisions

None newly captured. Author-held items remain per the handoff (publication, Series/Reserve/Archive, voice acquisition, language/script, glyph samples, etc.).

## Plan / next steps

- Posting hardening #123 WIP (`post-poem-hardening-wip`) remains unported; its tests-first changes require code fixes in `tools/post_poem.py`.
- T03/T05/T06/T07/T08 PRs (#119, #126, #125, #129, #130, #102) remain draft and need restack/review; not merged here.
- T01/T02/T04 recovery and broader integration remain open.

## Status

Partial. Remote `main` is `8cd9872acbccd28db9736c2340cdac9d1ba65f91`. Two PRs merged with verified fixes; remaining tranche work is documented as open.
