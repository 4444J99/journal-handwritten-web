# Variorum and Builder operations

The 7 November 2026 author handoff governs implementation. No deployment or release is implied by a saved composite. Existing Studio Access and owner write permission apply. Public staging retains disabled private repository automatic deployment.

## Storage and API

No new D1 tables are required. `vf_docs` collections `parts` and `composites` contain immutable `r.<operationUUID>` revisions and mutable `h.<recordId>` pointers; promotion documents use `promotion.<operationUUID>`. Titles are display data. `vf_revs` includes both collections in source capture and publication fencing.

Authenticated routes are GET `/api/variorum/pieces/:pieceId`, PUT `/api/variorum/parts/:pieceId`, POST `/api/variorum/composites`, and POST `/api/variorum/composites/:recordId/{rematerialize,photo,promote}`. Every write carries `operationId` (UUID), `sourceToken`, and `expectedHead` (revision ID or null). Parts saves carry structural `parts`; composites carry `pieceId`, `partsRevisionId`, `recipe` and `caseMode`. Photo carries an already authenticated-uploaded `assetId`; attachment hashes immutable bytes and preserves the old recipe/text. Promotion creates an independent piece/release record and leaves the originating stack intact.

Success returns `{ok,head,revision}`; identical retries return the same revision with `replayed:true`. A conflicting operation/head/source or publication fence returns 409. The 64 KiB body and materialized-document limit returns 413. Browser text, verification and geometry never authorize a save. Parts acceptance and source verification remain separate.

Parts specify `pieceId`, `parts` (id and optional supplied name), `canonicalOrder`, `linkedPieces`, and `maps`. Maps have `segments[partId]` occurrences `{occurrence,lines,accepted}` plus occurrence-key `version_part_order`. An empty segment list means absent; no segment means untagged. Recipes reference `{partId,occurrence,from}` and pin immutable maps/snapshots. A line run is contiguous and accepted lines cannot overlap. Case modes preserve whitespace and punctuation.

## Source imports

Author-supplied UTF-8 files belong under private `source/external/`. `python3 tools/variorum_sources.py --help` describes dry-run-first import. Imported originals are retained by content hash under `.versions/`; source correction appends a revision without changing earlier line IDs or recipes. Empty `source/variorum.json` supplements are valid; missing author text remains unavailable. Import does not certify transcription.

Production typeset output requires approved, prepared `source/variorum-font-evidence.json` with `approved:true`, `coversShellSha256`, exact `codepoints`, and `approvalRef`. A technical font measurement is not author approval. Corrected sources require explicit rematerialization; photo revisions cannot be rematerialized.

## Export, recovery and rollout

Existing `export_db.py` and `import_export.py` now include both collections and immutable history. Import rejects conflicting immutable revisions. Head movement requires explicit `--reconcile-heads FILE`, a JSON object mapping `collection/h.recordId` to its expected current revision (or null); the target revision must be present in imported history. Publication fencing applies during restore. Export assets referenced by history along with documents; preserve existing immutable PHOTOS objects and snapshot pointers.

Build and review the backend before enabling Studio controls. `build_cloudflare.py` runs repository integrity plus focused Variorum model/publication validation. `build_reader.py` emits the blank reader package, shell hash and isolated staging configuration from prepared output; it includes no private poems. Copy only reviewed generated files into the reader repository. Activation follows the existing exact-output confirmation workflow.

Rollback restores previous reviewed Studio/reader packages and a known snapshot pointer through the fenced recovery path, and disables new entry points. Preserve new collections, revisions, imported originals and assets. Never recover by deleting author work. Current evidence and package hashes live in `/workspace/scratch/variorum-delivery/`; no physical iPhone test has been performed.
