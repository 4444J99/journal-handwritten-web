# T02 source foundation and independent recovery

## Produced

- Versioned `source/canonical.json` preserving 123 pages, 126 pieces, 156
  versions and 2,190 existing line IDs, original transcripts, quotation-marker
  differences, uncertainty and source image hashes.
- `tools/source_foundation.py`: deterministic reconstruction, dry-run review
  proposals, backup-before-application, append-only review evidence, explicit
  photo staging and independent source/all-collection restore.
- Actual application of 38 preserved reviews: 33 confirmed and five corrected.
  Raw originals remain unchanged. A second application and second rebuild are
  no-ops. The independent restored source's own CLI also rebuilds without changes.
- Shared Python/JS logical fingerprint v2, including stanza boundaries. Legacy
  note anchors remain readable and require explicit source rebind. Corrected
  text matching a changed raw original no longer bypasses stale-review checks.
- Explicit unavailable-anchor state for `diary1-2-3`, with its null review box
  retained. Existing source images and current HTML templates are unchanged.
- Synthetic correction/photo/new-version and history/restore tests, shared
  vectors, schema/contract documentation and private verification receipts.
- Follow-up integration repair: rebuilt reader data carries current v2
  `sourceBindings` for every transcribed version. A caller-supplied descriptor
  cannot establish freshness; the reader must compare with these loaded
  bindings. Untranscribed imports have no binding and remain unavailable.
- Independent combined review reproduced and repaired a T10 legacy-current
  bypass: a v1 current snapshot could conceal a stanza-only change. History is
  still readable; live projection now requires v2. Exact output correction
  overrides preserve quotation differences and reject raw source drift.
- T08 public eligibility resolves current v2 snapshots and explicit line IDs;
  T09 request bindings verify selected effective lines during validation and
  rendering. Shared vectors cover both adapters. Existing calibration input
  choices and DSP remain unchanged, with updated code provenance.

## Author decisions

The supplied task authorizes completion, verification and private integration.
No author wording, geometry mapping, script choice, new public release, external
filing or publication decision was made in this work. Historical review records
retain their original status, dates and evidence.

## Plan / next steps

Technical integration: the shared-file owner merges this bounded patch, rebuilds
the repository integrity manifest, and combines reader unavailable-anchor
fallbacks and T03 exact-output gates with the shared source contract. T08/T09
outputs must bind the same logical fingerprint and their own pixel/region
digests. Author-dependent content and publication choices remain pending.

## Status

The local source/review/rebuild/recovery implementation and its acceptance tests
are complete. Reports distinguish actual preserved reviews from synthetic
correction/photo/history fixtures. The private context packet sources remained
inaccessible; no account-wide or external-provider persistence is inferred.
