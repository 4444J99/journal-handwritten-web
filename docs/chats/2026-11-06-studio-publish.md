# Studio publishing implementation - 2026-11-06

## Produced

- Implementation source plan: [.codex/plans/2026-11-06-studio-publish.md](../../.codex/plans/2026-11-06-studio-publish.md); progress and rulings in the adjacent ledger.
- Shared JavaScript publication compiler, deterministic private source/atlas preparation, pinned public-reader packaging, owner-only API, browser build and bounded server verifier, preview/confirm, history, rollback, and unpublish.
- Public reader has one read-only-in-code R2 binding. Studio retains D1 and PHOTOS and writes separately bound staging/production buckets. Every new SQL statement targets vf_ objects.
- Canonical real-p001 Python/JS data parity; matching hashes for all six non-atlas upload files, exact source pixels for two lossless atlas tiles, 22 retained line rectangles.
- Local Pages/D1/R2 end-to-end verification, including the separately configured public reader. Synthetic hosted timing exposes cold-start CPU limits rather than claiming a universal free-plan guarantee.
- Merged upstream PR #136 into this feature branch; its metadata and diary1 source fixes remain authoritative.

## Author decisions

- Implement the supplied Studio publishing plan.
- Proceed with the reviewed merge/deployment next steps.
- Strip unpublished page IDs from public output, blank optional font provenance/credit fields while preserving required license notices, and remove the public global verification-status line. Inspect the actual upload package, not only a filtered preview.
- The author identified the updated 1Password item 4444j99-cloudflare-api for Cloudflare access. No credential values were written to source or logs.
- The author asked whether the CPU limit can be MacGyvered. Implementation uses the plan's browser-build/bounded-server-verification fallback; no paid subscription was activated.
- The supplied plan records a standing GRUW skip decision; its recorded decision document remains the authority for passing the filing gate.

## Plan / next steps

Both repository changes are pushed: private PR #137 and public shell PR #2. The reviewed Studio implementation and blank staging reader are deployed; the public production shell awaits author review. Retain the Python posting fallback. The author confirms the first actual p001 snapshot in staging, checks a real iPhone and laptop, and then confirms production. Those physical-device and first-publication steps are not agent test results.

## Status

Publishing implementation, review fixes, real-source parity, Chrome preview/confirmation flow and local suites are verified. The follow-up repaired canonical bookmarks and bounded bulk recovery reads. Public PR #2 is merged and both public readers are deployed blank. Private integration was authorized; exact final merge and deployment receipts are maintained on [PR #137](https://github.com/4444J99/journal-handwritten-web/pull/137) and the [verification record](../verification/studio-publish-2026-11-06.md). The first full follow-up run had one unnamed Git-fixture failure; all 391 Python tests passed on the complete diagnostic rerun, with the existing environment skip. GitHub Actions cannot start because of account billing/spending. Hosted owner-session verification, first actual p001 confirmation and physical iPhone/laptop acceptance remain owner checks. No real poem was published by this session.
