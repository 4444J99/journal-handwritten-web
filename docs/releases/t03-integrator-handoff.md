# T03 integration handoff — November 5, 2026

This handoff accompanies an isolated T03 branch stacked on PR #101. It does not alter other workers' checkouts, assignments or studio files. Integration/merge, deployment and publication are outside this execution's authority.

## T01: studio and operational integration

- Preserve PR #89's existing Mark posted fields, URL validation, two-tap behavior, and Exposure shortcuts. The database-backed receipt belongs to the disposable local test database; none of its synthetic posted/exposure events belongs in production.
- The confirmed implementation mismatch is representational: a Mark posted entry uses `type: social` even when `where` is the Site URL; a Site Exposure entry uses `type: site`. Both currently carry `pub: false`. The author's desired semantics remain a decision. Do not silently change old records or make downstream legal classifications from either flag.
- A concrete schema/UI proposal for the integrator is to distinguish channel selection (`site`/`social`) from an independently sourced publication classification, preserve the original event payload and give new consumers an explicit unknown/unconfirmed state. This is a proposal, not an approved migration. The current test receipt records behavior without adopting this proposal.
- Before posting, export all six collections freshly and bind their hashes to the output manifest. The preserved 38-review export is sufficient for this bounded rehearsal; it does not prove live D1 freshness.
- Regenerate `MANIFEST.sha256` only if the integrator intentionally changes content under `site/` or `studio/`, then run `tools/check.py`. T03's preparation adds no such content changes.

## T02: source/build/deposit integration

Use [the release-clearance contract](release-clearance-contract.md) for exact stable IDs, review-original matching, correction provenance, asset hashes and deposit-version coverage. This packet consumes preserved outputs and records; it does not recover missing archival masters or historical generators. PR #103's restored documents do not themselves restore build scripts.

The new preparation helper calls PR #101's existing builder. Its image audit additionally inventories unselected drafts of the same piece, quotation blocks, neighbours, spread mates, atlas regions and downloadable font metadata. These findings are required inputs for any derivative/crop remedy. Re-run after a source reconstruction; do not reuse a previous preview hash.

No deposit is filed or certified here. Supply an author-titled deposit manifest with exact piece/version/source/review/output hashes, label reconstructed deposits as reconstructed, and leave filing-evidence fields unset until an actual record exists.

## T04: reader and phone acceptance

T03 inspected the accessible T04→T02 integration proposal and navigation contract in the active, separate T04 workspace. Its stable-ID and sole-reader-source requirements are consistent with this handoff. This is an acknowledgment of that technical contract, not acceptance of an uncommitted implementation or an integrated build.

T03's browser receipt uses the existing PR #101 reader source, desktop 1280×900 and phone-width/touch emulation 390×844. It checks loading, title, renamed font, noindex meta, information-panel opening, Journal rendering, document width, requested assets and withheld-image 404s. No physical iPhone test or full navigation/progress contract acceptance is claimed. T04's accepted reader revision must be rebuilt through the public transformation and tested again before its acceptance is transferred to a release.

The public output retains stable piece/version IDs and omits `p001-diary62a-0`. An omitted-version route must remain unavailable after T04 integration. The author confirms numbering/participation separately; neither is an identity key or a read-progress signal.

## T06/T07: release-clearance consumers

Consume only a specific cleared output manifest and attributable author statement. The whole private packet contains withheld material and is not a publication package. A candidate, successful dry build, derived decision, database status, exposure flag or command-line acceptance is not clearance. The current [contract record](release-clearance-contract.md) remains `awaiting-author-and-evidence`, with no confirmed post date.

## Main movement and plan update

Initial main: `d830d2a8f0556c50917d34528ab0b19cf7e0579a`. Refreshed main: `04168b1f68bc4579fae245f8411b0b337d064369` (PR #103 historical document import). PR #101 stayed at `5d111c13764655312c32ddf1b55390198bc7f70c`. Remote tree comparison confirmed identical `site/`, `studio/`, `exports/` and `studio-cf/` blobs between that PR snapshot and refreshed main. Main's builder still differs because PR #101 is unmerged; the packet explicitly depends on PR #101.

`docs/plan.md` carries this session's bounded addendum. `claude-plan-addendum.patch` is an unapplied matching update against restored `claude/plan.md` blob `e69db0c34376f25e827d99c5619466175fc1080b`. Apply it only after the integrator brings PR #103 and PR #101 into the same checkout and verifies that base blob or reconciles any newer plan edits. The zero-context patch preserves the historical body and adds a dated T03 section. After verifying the base blob, use `git apply --check --unidiff-zero docs/releases/claude-plan-addendum.patch`, then apply the same patch with `--unidiff-zero` in the integration checkout.

A subsequent refresh at 22:51 UTC observed main `cd6a00a830e142b4affa74dfc020438214b6bec7`, adding PR #114's stricter manifest checker. The same four runtime/data prefixes still match the PR #101 snapshot exactly. Both the branch's checker and the newer main checker were run against T03's unchanged content: 509 references, 511 checksums, exit 0. The newer checker was inspected and executed from a temporary local file; it was not copied into this stacked branch or counted as part of its 104-test suite.

## Completion boundary

The technical packet, source-linked decisions, reproducible checks, whitelist proposal and rollback procedure are prepared. Author clearance, pool/final-version decisions, filing evidence, event semantics, a fresh live export and physical-device acceptance remain explicit gates. No cross-tranche merge, studio deployment, first post, registration, account change, issue closure or external message is reported as complete.
