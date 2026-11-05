# Release-clearance contract for T01/T02/T03/T04/T06/T07

Contract version: `versforms.release-clearance.v1`. Status: **proposed interface for review; no cleared release record exists**. This is a technical handoff and a record of required evidence, not an author decision or a legal determination.

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
| `exposure_manifest` | Every file path, SHA-256 and size; piece/version/text set; page image tiers, spreads/facing pages, Hand↔Font plates, atlas source/output rectangles, embedded font metadata and any other bundled bytes. |
| `shared_scan_resolution` | Exact page/block/version exposures, author ruling and remedy, if any. A command-line flag is not evidence. Withheld same-piece drafts count too. Any accepted neighbour needs its own clearance; Reserve/Archive/unsorted material is excluded. |
| `batch_workflow` | Confirmed handling of `filed` and `registered`; keep the present documented gate pending the author's decision. |
| `filing_evidence` | Accessible batch reference/date, filing or registration evidence, deposit manifest hash, and which exact version was covered. The technical check verifies the linked record; it does not establish legal adequacy or invent a filing. |
| `identity_metadata` | Exact title, font family plus downloadable font-name/description metadata, noindex meta and header policy, and all changed reader-visible wording. |
| `acceptance_receipt` | Code/input/output hashes; exclusion and reproducibility results; actual browser/viewport; a separate physical-phone result or explicit remaining gate. |
| `author_clearance` | Dated, attributable author statement naming this version/output and any limits; null while missing. Historical approval of another output is insufficient. |
| `release_event_contract` | Agreed event channel/type, URL/account meanings, version/output references and publication-classification provenance. Current Site/social flags are not an external legal rule. |
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
  "first_confirmed_post_date": null,
  "cadence_days": 7,
  "may_publish": false,
  "may_schedule_external_actions": false
}
```

The null shared-scan ruling does not block the bounded diary1 preview's exclusion proof: that output contains no catalogued neighbour. It does block any later output that relies on accepting shared exposure. The private all-versions comparison is explicitly outside the proposed output manifest.

## T02 source and deposit boundary

T03 consumes the existing `j.json`/review JSON and exported document interface. It does not restore missing historical generators. Any T02 reconstruction must retain page/piece/version/line identifiers and review originals, publish a lineage manifest, and report which bytes are recovered, preserved or reconstructed. A new photo in `versions` is not automatically part of `j.json`; incorporate and review it explicitly before release.

A deposit handoff must list work/title identifiers as chosen by the author, the exact selected version(s), review snapshot/hash, source page/image hashes, generated file hashes and generator revision. Preserve original transcription separately from author corrections. No synthetic batch status or “filed” marker is created during deposit preparation. A generated deposit is neither a recovered historical deposit nor proof that filing occurred.

T02 must account for every derivative if implementing a scan remedy. Removing p126 from a transcript or hiding it with CSS leaves it readable in raw image bytes. Crop/mask derivatives require an author-reviewed bound and regenerated page tiers, thumbnails/atlases, plates and any spread whose facing page would expose the writing. Rerun image/metadata and byte-inventory checks afterward.

## T01 studio boundary

Test writes belong in a disposable local database. A release document persists `posted`, `exposures`, pool and numbering alongside other state; test those fields through write/read/reload, and retain the pre-test export. Stage shared `studio/index.html`, adapter or schema changes through the integrator; T03 has not edited them.

Do not collapse physical channel and publication classification. The reviewed implementation records Mark posted as `type: social` even with a Site URL, while the Site quick choice uses `type: site`; both have `pub: false`. Record what actually happened and obtain the author's semantic decision before a downstream consumer uses these fields as a rule. No legal conclusion follows from those booleans.

## T04 reader boundary

Use the accepted `site/index.html` as the sole source, preserving T04's reader fixes. T03's public transformation is limited to the reconciled title/font/noindex/provenance behavior. Compare the resulting code against the accepted T04 revision, rerun its full interaction matrix on the nonempty filtered output, and test an omitted-version route as unavailable. Stable IDs survive filtering; numeric array references are remapped without changing referents. No progress/completion behavior should depend on unpublished candidates or unconfirmed n/100 numbering.

T03's phone-width headless check is a bounded preview test. It does not satisfy the real-iPhone gate or claim T04 has accepted the integrated build.

## Invalidation and withdrawal

Any changed text, review, final-version selection, pool, source/deposit evidence, scan derivative, atlas region, embedded font, reader code, whitelist or public output hash invalidates the corresponding clearance. Rebuild and obtain a clearance covering the changed output; do not transfer approval by piece ID alone.

Exclusion from this prepared output establishes only the contents of this output. It does not establish that a poem has never appeared elsewhere. Earlier external exposure and source-repository visibility remain separate historical evidence for the author to assess. Withdrawal preserves that history and cannot promise recall of downloaded or cached copies.
