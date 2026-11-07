# Release-clearance contract for T01/T02/T03/T04/T06/T07

Contract version: `versforms.release-clearance.v1`. Status: **proposed interface for review; no cleared release record exists**. This is a technical handoff and a record of required evidence, not an author decision or a legal determination.

## Implementation update — November 6, 2026

The implemented contract is described in
[`exact-output-and-private-artifacts.md`](../integration/exact-output-and-private-artifacts.md).
Python and JavaScript validate the same typed canonical digest, exact file inventory,
current source bindings, component revisions, attributable author evidence and
observed publication events. Adapters cover notes/contributions, source regions,
script realizations and weekly records. Fixture provenance remains ineligible;
validation returns `execution_authority:false` even for a synthetic positive test.
This implementation supplies no real clearance record.

The public builder now filters PAL/HF metadata to complete selected witnesses.
The earlier 13-identifier leak below describes the historical November 5 packet;
it is not a current passing result. Use the newly generated integration packet's
checks and exact manifest for current bytes. The all-versions comparison still
exposes neighbouring p126 writing through diary62a and remains excluded from the
bounded candidate output. Shared-scan, source geometry, font/info wording, filing
and physical-phone acceptance remain exact-output author checkpoints.

The rest of this document preserves the original proposal and its dated findings.

## Consumer rule

T06/T07 may prepare private drafts from an identified candidate. They must not treat a successful build, `pool=series`, a `filed`/`registered` string, a derived decision, a scheduled date, `Mark posted`, `--force`, or `--accept-shared-scan` as permission to publish or redistribute. They receive a specific output manifest and the author's explicit, source-linked clearance for that manifest. The actual posting and any later outward communication require their own current execution authority.

The weekly cadence is preserved. The first confirmed date is currently null. No spending, account change, filing, domain purchase or new service is authorized by this contract.

## Required record

| Field | Required evidence and owner |
|---|---|
| `source_revision`, `builder_revision`, `reader_revision` | Full accepted Git OIDs plus actual code hashes; T01 integrates, T02 owns source/build, T03 posting dependency, T04 reader. |
| `input_manifest` | Hashes of `site/data/j.json`, `studio/data/review.json`, image/font sources and a fresh T01 export of reviews/decisions/versions/release/batches/rconfig. Distinguish a preserved output from a recovered original or reconstructed source. |
| `pieces[].piece_id` | Existing stable ID; no n/100 renumbering as identity. |
| `pieces[].versions[]` | Exact existing version IDs, source pages and block/line IDs; explicit final-version or layer decision with its source. `top`/last-in-`V` is a default, not sign-off. |
| `reviews` | Original readings, correction text, review status and provenance; reject stale `original` values. Retain uncertain readings rather than silently resolving them. |
| `pool_clearance` | Author's Series/Reserve/Archive decision for every affected piece, including scan neighbours and any already-public pieces rebuilt. No automated classifier supplies this. |
| `exposure_manifest` | Every file path, SHA-256 and size; piece/version/text set; page image tiers, spreads/facing pages, Hand↔Font plates, atlas source/output rectangles, embedded font metadata, withheld-page identifiers/PAL/HF block structure and any other bundled bytes. Content-only exclusion is not complete technical exclusion. |
| `shared_scan_resolution` | Exact page/block/version exposures, author ruling and remedy, if any. A command-line flag is not evidence. Withheld same-piece drafts count too. Any accepted neighbour needs its own clearance; Reserve/Archive/unsorted material is excluded. |
| `batch_workflow` | Confirmed handling of `filed` and `registered`; keep the present documented gate pending the author's decision. |
| `filing_evidence` | Accessible batch reference/date, filing or registration evidence, deposit manifest hash, and which exact version was covered. The technical check verifies the linked record; it does not establish legal adequacy or invent a filing. |
| `identity_metadata` | Exact title, font family plus downloadable font-name/description metadata, noindex meta and header policy, and all changed reader-visible wording. |
| `acceptance_receipt` | Code/input/output hashes; exclusion and reproducibility results; actual browser/viewport; a separate physical-phone result or explicit remaining gate. |
| `author_clearance` | Dated, attributable author statement naming this version/output and any limits; null while missing. Historical approval of another output is insufficient. |
| `release_event_contract` | Agreed event channel/type, URL/account meanings, version/output references and publication-classification provenance. Site/social `false` classifications are values in a UI enum, not stored `pub` event fields and not an external legal rule. |
| `rollback_record` | Prior public commit/output and private whitelist; prepared revert approach; retained exposure history and downstream cancellation scope. |

The [prepared first-release packet](t03-release-procedure.md) uses the following unresolved state. It deliberately does not encode a true approval field:

```json
{
  "schema": "versforms.release-clearance.v1",
  "status": "awaiting-author-and-evidence",
  "candidate": "p001",
  "candidate_provenance": "derived from recorded journal-page order",
  "proposed_version_ids": ["p001-diary1-0"],
  "public_whitelist_change_applied": false,
  "author_clearance": null,
  "filing_evidence": null,
  "shared_scan_resolution": null,
  "withheld_metadata_clearance": null,
  "withheld_page_id_count": 13,
  "complete_technical_exclusion": false,
  "first_confirmed_post_date": null,
  "cadence_days": 7,
  "may_publish": false,
  "may_schedule_external_actions": false
}
```

The bounded diary1 preview excludes catalogued neighbour text/version data and images; the null shared-scan ruling still blocks any later output that relies on accepting shared exposure. This is not a complete exclusion proof: 13 withheld-page identifiers and PAL/HF block structures remain in `index.html`, requiring an explicit author metadata rule or a T04/builder fix and a new check. The private all-versions comparison is explicitly outside the proposed output manifest.

## T02 source and deposit boundary

T03 consumes the existing `j.json`/review JSON and exported document interface. It does not restore missing historical generators. Any T02 reconstruction must retain page/piece/version/line identifiers and review originals, publish a lineage manifest, and report which bytes are recovered, preserved or reconstructed. A new photo in `versions` is not automatically part of `j.json`; incorporate and review it explicitly before release.

A deposit handoff must list work/title identifiers as chosen by the author, the exact selected version(s), review snapshot/hash, source page/image hashes, generated file hashes and generator revision. Preserve original transcription separately from author corrections. No synthetic batch status or “filed” marker is created during deposit preparation. A generated deposit is neither a recovered historical deposit nor proof that filing occurred.

T02 must account for every derivative if implementing a scan remedy. Removing p126 from a transcript or hiding it with CSS leaves it readable in raw image bytes. Crop/mask derivatives require an author-reviewed bound and regenerated page tiers, thumbnails/atlases, plates and any spread whose facing page would expose the writing. Rerun image/metadata and byte-inventory checks afterward.

## T01 studio boundary

Test writes belong in a disposable local database. A release document persists `posted`, `exposures`, pool and numbering alongside other state; test those fields through write/read/reload, and retain the pre-test export. Stage shared `studio/index.html`, adapter or schema changes through the integrator; T03 has not edited them.

Do not collapse physical channel and publication classification. The reviewed implementation records Mark posted as `type: social` even with a Site URL, while the Site quick choice uses `type: site`; both choices have `false` publication classifications in the UI enum. These are **not stored `pub` fields** on the event payloads. Record what actually happened and obtain the author's semantic decision before a downstream consumer uses the event types or UI enum as a rule. No legal conclusion follows from those values.

## T04 reader boundary

Use the accepted `site/index.html` as the sole source, preserving T04's reader fixes. T03's public transformation is limited to the reconciled title/font/noindex/provenance behavior. Compare the resulting code against the accepted T04 revision, rerun its full interaction matrix on the nonempty filtered output, and test an omitted-version route as unavailable. Stable IDs survive filtering; numeric array references are remapped without changing referents. No progress/completion behavior should depend on unpublished candidates or unconfirmed n/100 numbering.

The local D1 receipt has 12 passing checks and includes a narrow desktop viewport of 390 pixels; it supplies no touch or phone acceptance. The release-preview browser receipt separately uses touch emulation. Neither is a physical iPhone result or acceptance by T04 of the integrated build.

## Invalidation and withdrawal

Any changed text, review, final-version selection, pool, source/deposit evidence, scan derivative, atlas region, embedded font, reader code, whitelist or public output hash invalidates the corresponding clearance. Rebuild and obtain a clearance covering the changed output; do not transfer approval by piece ID alone.

Exclusion from this prepared output establishes only the contents of this output. It does not establish that a poem has never appeared elsewhere. Earlier external exposure and source-repository visibility remain separate historical evidence for the author to assess. Withdrawal preserves that history and cannot promise recall of downloaded or cached copies.

## Current implementation and execution boundary

The current base is PR #101 `e5ae157ef556690e73047e30225cad61c5484cf9`. Its CLI exits 3 for the authentic 38-review/0-release export at the empty-release loader; the helper's private `studio-cf/import_export.scan` audit separately evaluates the existing review/Series/batch gates. No fake release records are introduced. Historical results at `5d111c1` / `e0177fa` remain in the baseline packet and are not current acceptance.

PR #101 [discussion 4487062599](https://github.com/4444J99/journal-handwritten-web/pull/101#discussion_r4487062599), concerning multiple push URLs, remains a separate non-dry-run execution gate. This contract provides no authority to perform that execution.
