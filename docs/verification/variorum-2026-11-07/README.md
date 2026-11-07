# Variorum and Builder delivery — 7 November 2026

Implemented on local feat/variorum-builder branches in the source and generated reader repositories. No deployment, remote database write, release selection or public activation was performed.

## Delivered

- Stand-off canonical source adapters, neutral provisional part maps, accepted occurrences, linked sources and similarity suggestions.
- Immutable mapping/composite revisions, source tokens, transactional head updates, idempotent retries, owner authorization and publication fencing.
- Integrated Studio Parts/Builder controls, copy fallback, touch/keyboard selection, mapping/composite history, re-materialization, content-addressed photo attachment and explicit promotion into Sort/Release.
- Reader spread, repeat-preserving pivot, label/provenance reveal, keyboard/pinch entry, native frozen typeset pages and thumbnails, photo fallback and lifecycle cleanup.
- Browser/server publication assembly, independent Python output parity, filtered provenance, authoritative verification/exposure/render gates and withheld-source rollback checks.
- Source-file imports preserve earlier content bytes. Backup/export includes new collections; restore supports explicit expected-head reconciliation and atomic file import.
- Cloudflare build gates and generated reader package with matching Studio shell pin.

## Validation

Source validation, notes source map, checksum integrity and Cloudflare production build pass. Focused API/model/publication/promotion/restore tests pass; independent reviewer approved implementation and attachment follow-up. Browser receipt/screenshots cover 1280×900 and 390×844 light/dark; actual Studio mapping-history restore/save and native derived rendering are included. A separate real Studio mobile test verifies promotion classification and reload persistence. Real local Pages/D1/R2 publication succeeds. Generated public package tests: 9 passed.

Full CI receipt is full-ci.json. Its Cloudflare Node importer failure was an environment PATH issue (Wrangler executable discovery); the corrected follow-up run passes all 157 tests (cloudflare-node.txt). Repository Node suite passes 128 tests; Cloudflare Python suite runs 68 with one skip and no failures.

Stable complete Python suite: 400 run, one skipped, one pre-existing failure in test_timeout_kills_the_whole_process_group. Reproduced from untouched c5e1194 tools and tests; see baseline-timeout.txt. Do not describe the whole repository CI as green. Earlier in-progress source-hash failures disappeared on a stable run; missing platform dependencies were addressed with a pinned local environment.

Environment: Node24, Chromium /usr/bin/chromium, pinned studio-cf requirements and audio requirements in a local venv. Existing reader-permalink test now supports CHROME_BIN to run on Linux.

## Package and operations

Reader commit: 037478ef425dd6a117948ec71cc137d10a1dedd8. Shell SHA-256: c4137a223ed2efe1b1e1a739be6e2c0305140cf8f6d9b04d96e31cf19155a1df. All generated file hashes are in reader-package.json. Source commits are recorded by git history on feat/variorum-builder.

Use the existing exact-output confirmation workflow for activation. Backend must be deployed before new Studio controls; the matching shell pin is required. Keep staging's private-source automatic deployment disabled. Staging remains public: private drafts stay behind Studio Access. Existing deployment IDs and bindings are recorded in ../../integration/2026-11-07-variorum-review.md.

Rollback restores a previous compatible package and valid snapshot pointer through the fenced publication recovery route; source history and content-addressed assets remain preserved. Rollback tests reject source dependencies moved to Reserve. Restore/import tests verify real local D1 atomic rollback on failure.

Physical iPhone acceptance and author glyph evidence were not invented or supplied. Production typeset eligibility remains gated; missing notebook/lyric sources remain unavailable. No transcription has been automatically certified.
