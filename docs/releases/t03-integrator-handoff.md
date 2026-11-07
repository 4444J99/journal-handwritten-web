# T03 integration handoff — November 5, 2026

This handoff accompanies an isolated T03 branch stacked on PR #101. It does not alter other workers' checkouts, assignments or studio files. Integration/merge, deployment and publication are outside this execution's authority.

## T01: studio and operational integration

- Preserve PR #89's existing Mark posted fields, URL validation, two-tap behavior, and Exposure shortcuts. The database-backed receipt belongs to the disposable local test database; none of its synthetic posted/exposure events belongs in production.
- The confirmed implementation mismatch is representational: a Mark posted entry uses `type: social` even when `where` is the Site URL; a Site Exposure entry uses `type: site`. Both choices have `false` publication classifications in the UI enum; these are **not stored `pub` fields** on the event payloads. The author's desired semantics remain a decision. Do not silently change old records or make downstream legal classifications from either enum value.
- A concrete schema/UI proposal for the integrator is to distinguish channel selection (`site`/`social`) from an independently sourced publication classification, preserve the original event payload and give new consumers an explicit unknown/unconfirmed state. This is a proposal, not an approved migration. The current test receipt records behavior without adopting this proposal.
- Before posting, export all six collections freshly and bind their hashes to the output manifest. The preserved 38-review/0-release export is sufficient for the bounded private audit through `studio-cf/import_export.scan`; it does not prove live D1 freshness. The current posting CLI stops at exit 3 in the empty-release loader. Existing gates evaluated separately show 38 reviews pass, Series false and batch false; no release rows are fabricated.
- Regenerate `MANIFEST.sha256` only if the integrator intentionally changes content under `site/` or `studio/`, then run `tools/check.py`. T03's preparation adds no such content changes.

## T02: source/build/deposit integration

Use [the release-clearance contract](release-clearance-contract.md) for exact stable IDs, review-original matching, correction provenance, asset hashes and deposit-version coverage. This packet consumes preserved outputs and records; it does not recover missing archival masters or historical generators. PR #103's restored documents do not themselves restore build scripts.

The new preparation helper privately reads the preserved export using `studio-cf/import_export.scan` and calls PR #101's existing builder. Its image audit additionally inventories unselected drafts of the same piece, quotation blocks, neighbours, spread mates, atlas regions and downloadable font metadata. These findings are required inputs for any derivative/crop remedy. Re-run after a source reconstruction; do not reuse a previous preview hash. Current text/version-data and image exclusion checks pass, but `index.html` retains 13 withheld-page identifiers and PAL/HF block structures. Complete technical exclusion is false; an author metadata rule or a T04/builder remedy and new check are required.

No deposit is filed or certified here. Supply an author-titled deposit manifest with exact piece/version/source/review/output hashes, label reconstructed deposits as reconstructed, and leave filing-evidence fields unset until an actual record exists.

There is an existing source-geometry defect to reconcile with T04: diary1 block 2 contains four transcript lines but only three `x` entries in `site/data/j.json`; `studio/data/review.json` gives `diary1-2-3` a null box. Root confirmed those counts directly, consistent with the warning in PR #102. Whole-page scans remain present, but line highlighting/crops cannot be certified as aligned from this packet. T03 does not guess replacement geometry or edit the author text. T02 should supply the corrected source geometry and T04 should check its rendered result before acceptance transfers.

## T04: reader and phone acceptance

T03 inspected the accessible T04→T02 integration proposal and navigation contract in the active, separate T04 workspace. Its stable-ID and sole-reader-source requirements are consistent with this handoff. This is an acknowledgment of that technical contract, not acceptance of an uncommitted implementation or an integrated build.

The 12-check local D1 receipt includes a narrow desktop 390-pixel viewport; it is not a touch or phone result. T03's separate release-browser receipt uses the PR #101 reader source, desktop 1280×900 and touch emulation 390×844. It checks loading, title, renamed font, noindex meta, information-panel opening, Journal rendering, document width, requested assets and withheld-image 404s. No physical iPhone test or full navigation/progress contract acceptance is claimed. T04's accepted reader revision must be rebuilt through the public transformation and tested again before its acceptance is transferred to a release.

The public output retains stable piece/version IDs and omits `p001-diary62a-0`. An omitted-version route must remain unavailable after T04 integration. The author confirms numbering/participation separately; neither is an identity key or a read-progress signal.

## T06/T07: release-clearance consumers

Consume only a specific cleared output manifest and attributable author statement. The whole private packet contains withheld material and is not a publication package. A candidate, successful dry build, derived decision, database status, exposure flag or command-line acceptance is not clearance. The current [contract record](release-clearance-contract.md) remains `awaiting-author-and-evidence`, with no confirmed post date.

## Main movement, baseline and plan update

The initial refresh observed main `d830d2a8f0556c50917d34528ab0b19cf7e0579a`. Main later advanced through `04168b1f68bc4579fae245f8411b0b337d064369` (PR #103 historical document import) to `cd6a00a830e142b4affa74dfc020438214b6bec7` (PR #114 manifest checking). At those earlier comparisons, PR #101 was `5d111c13764655312c32ddf1b55390198bc7f70c` and the four inspected runtime/data prefixes matched. That comparison and the old 104-test suite belong to the baseline; they are not evidence for the late head.

The current isolated checkout is based on PR #101 **`e5ae157ef556690e73047e30225cad61c5484cf9`**. The original eight-file rehearsal at `5d111c1` / T03 `e0177fa8a53ee41eda31a90253fbab3cc798556e` remains under `release/packets/2026-11-05-t03-baseline/`; the regenerated current packet uses `release/packets/2026-11-05-t03-current/`. Current checks and commit identities are recorded separately by the integrator in the verification receipt.

Both `docs/plan.md` and the restored `claude/plan.md` now carry the current dated addendum in this checkout. The older `claude-plan-addendum.patch` was already applied and is retained as a reproducible historical handoff artifact, not a pending patch to apply again. It does not update the inaccessible private project memory packet.

The active multiple-push-URL [review discussion 4487062599](https://github.com/4444J99/journal-handwritten-web/pull/101#discussion_r4487062599) remains a gate for non-dry-run posting. No authority for that action is supplied here.

## Completion boundary

The technical packet, source-linked decisions, reproducible checks, whitelist proposal and rollback procedure are prepared. Author clearance, pool/final-version decisions, the 13-ID/PAL/HF metadata rule or verified remedy, filing evidence, event semantics, a fresh live export and physical-device acceptance remain explicit gates. The exit-3 public CLI result is separate from the private audit; complete technical exclusion is not claimed. No cross-tranche merge, studio deployment, first post, registration, account change, issue closure or external message is reported as complete.
