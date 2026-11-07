> Historical draft: superseded by the author implementation handoff and completed delivery at ../../verification/variorum-2026-11-07/README.md. Pending-choice language below records the earlier draft only.

# Variorum and Builder integration design

Status: proposed; author decisions 1–4 and design approval pending.

## Intent

Align a poem's existing versions by recurring parts, and let the author select, omit and reorder those parts into a preserved composite version. Only existing author text enters composites. Labels are numbers until author names are supplied. Preserve source transcripts, photos, provenance and every earlier version. No critique or generated interpretation enters presentation data.

## Approaches

Recommended: extend current canonical source, vf_docs/vf_revs storage, JWT middleware, publication fence and reader engine. This reuses deployed release controls without parallel tables.

Alternative: install separate vf_parts/vf_composites tables and the legacy exporter. This duplicates concurrency/release controls and requires conversion to current source.

Alternative: private standalone Builder exporting recipes for manual ingestion. This reduces initial integration but does not fulfill stack/reader integration. The recommendation is proposed, not an author decision.

## Data and persistence

Stand-off parts records contain stable piece/part IDs, optional author names, canonical_order, linked_pieces and per-version maps. A map has segments keyed by part, each containing contiguous occurrences with unique positive occurrence numbers and ordered line IDs; version_part_order retains source order. Empty occurrence lists mean absent; omitted keys mean untagged. References resolve only within the piece or explicitly linked pieces. Never invent segmentation.

Composite revisions preserve recipe, source version/occurrence/pinned lines, case, materialized text, source fingerprint, exposure and verification evidence. Every save preserves earlier revisions. UUID storage IDs obey the existing API character set; display version IDs may separately retain v: notation. Resolve derived fields from authoritative source rather than accepting browser eligibility booleans. Explicit re-materialization creates a new typeset revision; photo composites remain frozen.

Extend vf_docs with validated, bounded parts/composites collections. Reuse context.data.user.email and owner write authorization. Include both collections in source revision capture, fingerprints, source-write fence, frozen build inputs and reconciliation. Update fixed six-collection SQL and all callers/tests together. Preserve publication race protection. Keep DB and PHOTOS out of reader bindings; use immutable box keys.

## Studio

Builder review resolved these technical choices (implementation proposals, not author decisions): references use canonical version IDs such as p001-diary1-0, never ambiguous page IDs; adapters retain exact piece/block/line membership. version_part_order contains ordered {part, occurrence} references so interleaved refrains remain representable. Composite recipes pin the parts-map revision and source-line snapshot as well as line IDs, preserving provenance after retagging. Initial composites source only journal/notebook/lyric versions; composite-to-composite recipes are rejected to avoid cycles and incomplete transitive gate evaluation.

Ordinary vf_docs writes overwrite records, so merely adding collection names is insufficient. Store immutable revision documents plus explicit head records for parts and composites. Conditional head updates must compare the expected head and run transactionally with revision insertion and publication-fence checks; conflict returns 409 without changing head, feed or assets. Existing immutable notes/contributions/artifacts paths need extension rather than copying their currently unfenced behavior. Export/publication selects an explicit captured head while historical recipes resolve pinned revisions.

Mount Parts/Builder through the current Studio adapter using real canonical version/line IDs and current review evidence. Pointer selection supports mouse/touch; keyboard assignment/reorder controls remain available. Similarity suggestions require acceptance. Support absence, repeated occurrences, source tabs, omission, arrows and canonical/per-version presets. Preserve uncertainty markers. Use theme variables and textContent for all author/source content. Case controls transform chosen text; copy has a selectable-text fallback.

## Reader and publication

Retain sideways version navigation at poem depth. Proposed entry uses strip control and pinch beyond poem depth with keyboard equivalent. Spread aligns canonical rows and pivots to a tapped version's order, marking moves. Labels toggle on tap. Minimum columns near 260px pan horizontally with shared vertical scrolling. Hold and accessible controls reveal recipe provenance. Filter released versions before alignment; never reveal unreleased source text through a public spread.

Typeset from frozen materialized lines using measured embedded-font metrics and explicit fallback runs. Missing font/metrics fail eligibility. Proposed public gate holds typeset composites until photographed or the required glyph gate passes, in addition to verification, Reserve/exposure, copyright and exact-output clearance. Staging may show private typeset previews. Preserve noindex and immutable snapshots. Engine changes regenerate the reviewed reader package and matching Studio shell pin; do not hand-edit generated public files.

## Toolchain and delivery

Use source/canonical.json, tools/source_foundation.py, tools/build_public.py and studio-cf/prepare_publish.py. Integrate mandatory-input and recipe validation into current CI/Cloudflare checks. Exports need backup, dry-run and atomic replacement. Refuse unresolved lines; never silently rewrite saved text.

Before deployment, reconcile staging's source-root discrepancy and identify playground alias branch/commit. Preview bindings share production data, so local tests need isolated D1/R2. Remote migration/public activation requires a concrete reviewed result; this document performs neither.

## Verification

Regression cases: repeated/absent/untagged parts, linked-piece ownership, duplicate/missing/noncontiguous lines, stale fingerprints, frozen text, missing lyrics/fonts, explicit re-materialization, Reserve and verification gates, invalid recipes, write conflicts, read-only identity and publication races. Run existing Python/Node checks and integrity verification. Exercise 1280×900 and 390×844 in both themes, touch selection, injection strings and clipboard refusal. Confirm reader isolation, snapshot filtering and shell-pin parity. Real iPhone testing remains author work.

## Pending author choices

The attached plan expressly waits on 1–4. Proposed defaults: numbered parts; composites remain versions unless promoted; public typeset output waits for photo or passing glyph gate; both pinch and strip-button entry. Participation stays author-only. Lyric files remain author-supplied. No transcription certification, invented p001 map or resolution of the Knuckles, knees fragment question is included.
