# T05 integration handoff

Private notes, dated reflections and contribution review for issues #17, #18
and #64. This is a bounded implementation and integration proposal. It carries
no authority to publish a poem, invite contributors, open submissions or merge
another tranche.

## Evidence and ownership

Initial live main: `d74df372ace00c8a7544ab3b5302cb05418d672c`.
Refreshed integration base: `fab6a82b72f23efb16278b90cdc4f7790ca55713`.
PR #101 merged at `06dccc0af91e563dc15e70d436569b7fe0cf9cba` during T05.
The final base includes documentation-only main
`038d01fb1862f2e569d231b5b3c4c3a4eb1aecda`. Its #123 posting-hardening findings
remain with that owner; T05 neither executes posting nor claims those findings
resolved. The executable code remains the tested `fab6a82` baseline plus T05.
Issues #17/#18/#64 remained open with zero comments on the final pre-commit
refresh. T03 draft PR #119 remained open at
`8d16284ba8b80f18398d08b8de931d8812f30429`, based on `post-poem-gates`;
its integration with newly advanced main is not claimed here.

The shared packet `2026-10-16-v1.1` / projection `2026-10-16-v1.1-r2` in
`g-p-6a10bcb4ada4819194e881431212101a` was inaccessible. All technical findings
and historical provenance below come from accessible repository material.

T05 owns the new `studio/notes-*` modules/page/style, generated source map,
schema, tests, backup/source/verification tools, and the narrow additions to
the existing adapter/API/import/export contracts. `studio/index.html` and
`site/index.html` remain byte-identical to the base. No other checkout was
edited. The existing default branch and other workstreams retain their owners.

## T01 — private persistence and studio entry

The new page is `studio/notes.html`. Existing `build_dist.py` copies it and the
modules into a complete private studio build. With the existing local demo
running, open `http://127.0.0.1:8790/notes.html`. The page uses
`window.claude.use('db')` and `user.can('data.write')`, including the existing
Cloudflare adapter fallback; it creates no alternative storage service.

Collections `notes` and `contributions` contain immutable revision documents,
each keyed by `revisionId`. They use `vf_docs` and `vf_revs`; no SQL schema
migration is required. The existing six collections retain their semantics.
The API enforces create-or-identical semantics atomically and rejects deletes.
The content model supplies the full graph/source/review validation; the generic
API/importer intentionally validates only its minimal persistence envelope.

Apply or adapt [the staged studio entry patch](t05-studio-entry.patch) through
the single studio integrator. It adds one link after the existing tab navigation
without moving or replacing tab code. It passed `git apply --check`; T05 did
not apply it to the shared page. Integrating these files does not authorize a
deployment or writing a backup to the real database.

Before enabling the native Claude artifact path, resolve its 255-file package
budget and verify its backend's conditional-write semantics. The original map
already has 253 entries. Only Cloudflare D1's immutable backend is tested here.
Keep the full pre-change export; old six-collection exporters must not be used
to back up records they cannot enumerate.

## T02 — exact sources and proposed anchors

Existing piece/version/line identities are reused; no numbering or IDs are
invented for unmapped material:

| Identity | Accessible source | Example |
|---|---|---|
| Piece | `site/data/j.json`, `pieces[].id` | `p001` |
| Version | Exact `pieces[].V[].id`, with its `P` page/block membership | `p001-diary1-0` |
| Line | `studio/data/review.json` line ID in the matched page/block | `diary1-0-0` |
| Optional word/phrase | Exact quotation within the line plus optional zero-based Unicode code-point range; end exclusive | `{quote, start, end}` |

Review-array order and reader-stack position can differ. The mapping therefore
uses exact version membership, not paired array indices. Coordinates, image
boxes, crop positions, zoom and n/100 ordinals never enter the anchor.

`buildSourceCatalog(versionMap, review, {reviews})` constructs the effective
text. A stored review correction is applied only if its original still matches;
a stale correction blocks new anchors. Quotation blocks retain their source
text. `createAnchor()` captures the version fingerprint, membership, line text
and source provenance. Ambiguous repeated quotations need explicit offsets.
`validateAnchor()` returns `valid` or `invalidated` with reasons; it never moves
the record to a similar line.

These fingerprint/selector rules are **T05 proposals awaiting T02 acceptance**.
The accessible T02 directory was an older non-Git snapshot; no completed newer
identifier contract was located. This handoff does not fabricate agreement.
After either input changes, regenerate with `tools/notes_sources.py` and run
`--check` before packaging. Newly uploaded versions become anchorable only
after they have a verified source mapping; no guessed fallback is provided.

## T03 — visibility and publication

Separate states are deliberate:

| Stage | Stored meaning | Reader eligibility |
|---|---|---|
| Draft / held | Private authoring or a content edit | None |
| Editorially accepted | Review of the recorded content, with actor/date/digest | Still private |
| Cleared for release review | Separate revision-bound clearance | Private requested preview only |
| Released | A real publication event bound to clearance and exact output | Requires the full T03 gate plus T05 projection |

`transitionRevision()` does not offer a publish action. T03 must implement the
release adapter/event against its exact manifest and attributable author
clearance. Changing text, citation, anchor, credit or permission must invalidate
the relevant approval; reusing a status label is not enough.

For preview, call `projectRecords(allRevisions, catalog, {mode:'preview',
versions:[{pieceId,versionId}], allowFixtures:true})` inside private studio.
For public eligibility use `mode:'public'`, an explicit cleared version allowlist
and no fixture permission. Public results contain no exclusion diagnostics.
The DTO is limited to record/revision IDs, family/kind, exact source IDs and
word selector, text/citations, public credit, poem/note dates and fixture flag.
Private identities, permission evidence, source snapshots, revision ancestry,
drafts, dossiers and withheld-record metadata are excluded.

This local projector is an additional filter, not a substitute for
`versforms.release-clearance.v1`. T03 must hash the projected bytes, list every
shipped path in its exposure manifest, and preserve its source/code/reader
binding and whole-scan/font/metadata gates. The current public builder is
unchanged and does not ingest or ship the new private collections. Never copy
`studio/`, a private export, or raw revision documents into a reader build.

## T04 — requested reader behavior

`mountNotesReader(host, {records, pieceId, versionId})` accepts **only filtered
DTOs**. It returns `reveal(trigger)`, `hide()`, `setContext()`, `isOpen` and
`destroy()`. Mounting, hiding and context changes empty and hide the host.
Opening renders literal text nodes for the exact source; Escape inside the
panel closes it and restores focus. The component fetches nothing.

The inspected T04 reader head was
`00efd23c1fbf0852287f4813ea451d98b6ffc53c`. Its `focusedEntry()` yields stable
piece/version IDs. The single reader integrator must connect those IDs and the
filtered release data to this component, include it in `panelOpen`/`closePanels`,
and wire outside-click, UI timeout, source/version changes, and Escape when
focus is outside the notes panel. No note-specific hash route is introduced.

The workbench offers below-poem and margin-column placement previews. The
margin layout is a non-persisted proposal, not a line-coordinate anchor. Inline
word marks, final endnote placement, series-wide note numbering and reflection
reveal timing await author/T04 decisions. Desktop and phone-emulation images
are in the [verification receipt](../verification/t05-2026-11-05/README.md).

## Author review — concrete options remain inactive

The preview can be inspected without supplying creative filler. The saved
example is explicitly a technical fixture. The actual poem text already
belongs to the source; the note body only identifies the fixture revision.

| Choice to review | Concrete preview | Boundary |
|---|---|---|
| Note placement | The same cleared note below the poem or in a margin column, with exact source IDs | No placement policy is saved; inline marks pending |
| Reflection timing | Same-day and later-note date cards, labeled technical fixture dates | No reflection is written and no interval selected |
| Contribution type | Private typed record, contributor credit, source association and permission fields | Reading/music/hand-copy media handling pending |
| Invited participation | Identity → permission/credit → review → clearance | Invitation button disabled; no message sent |
| Open participation | Private intake/review path and explicit later release | Submission button disabled; no public intake endpoint |

The around-the-author's-100 default retains its Claude-derived provenance from
`exports/derived-decisions-2026-11-05/decisions/participation.json`, timestamp
`2026-11-05T20:03:35.000Z`. It sets `countsTowardsAuthor100:false` and
`format:'pending-author'`; it does not settle the participation format or grant
permission terms. No contribution writes the author poem/version/release/count
collections.

## Remaining integration limits

Forked revision graphs are retained and block projection; there is no UI merge
resolver. Restoration is resumable per document, not an archive-wide
transaction. Offline acknowledgement and instantaneous remote polling freshness
are not promised. Physical phones, deployed Access configuration and native
Claude artifact persistence were not tested. Schema JSON parses; no full
Draft 2020-12 validator was available. Runtime validation and its tests are the
executable contract for this draft.

See the [workflow and migration notes](../notes-workflow.md) for per-issue
residuals. Keep #17/#18/#64 open for those decisions and integration steps.
