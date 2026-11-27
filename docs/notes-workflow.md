# T05 · private notes and contribution workflow

Scope: issues [#17](https://github.com/4444J99/journal-handwritten-web/issues/17),
[#18](https://github.com/4444J99/journal-handwritten-web/issues/18), and
[#64](https://github.com/4444J99/journal-handwritten-web/issues/64). This is an
isolated implementation for review. It does not publish, invite contributors,
open submissions, alter poem numbering, or establish a first-release date.

The starting revision is `d74df372ace00c8a7544ab3b5302cb05418d672c` (November 5,
2026). During implementation, PR #101 merged and main advanced to
`fab6a82b72f23efb16278b90cdc4f7790ca55713`; this isolated branch was reconciled
onto that exact live head before final verification. `CLAUDE.md` governs the
work. The shared packet `2026-10-16-v1.1` and
projection `2026-10-16-v1.1-r2` in private project
`g-p-6a10bcb4ada4819194e881431212101a` were not accessed; no claim here relies
on their unseen contents. Historical approvals in repository records are
evidence, not authority to execute a new action.

The final remote refresh found the documentation-only main commit
`038d01fb1862f2e569d231b5b3c4c3a4eb1aecda`; its upstream session-log update is
preserved in the final PR base. It records deferred posting findings in #123.
Those findings are not fixed or independently verified by T05, and passing
workflow tests are not a posting approval.

## Decisions and provenance

| Basis | Supported statement | Treatment here |
|---|---|---|
| Author, [October 26 notes exchange](chats/2026-10-26-footnotes-and-endnotes/01-notes-layers-proposal.md) | Wants footnotes, endnotes and a critical/context layer; placement undecided. | Separate typed records; private placement preview. |
| Author, [October 26 reflection exchange](chats/2026-10-26-footnotes-and-endnotes/02-dated-reflection-notes.md) | Wants personal reflection on who/where he was when writing; retrospective for old poems, current for new ones. | Empty authoring fields; no generated reflection. |
| Claude suggestions in those exchanges | Dual dates, accruing revisions, reflections as endnotes, short word/line footnotes, private interpretation-free references. | Implemented as a reviewable technical workflow; no claim that the author settled placement or timing. |
| Author, [participation exchange](chats/2026-11-03-poetry-release-plan/03-participation-from-others.md), exchange dated October 24, chat last active November 3 | Wants others to participate in some form. | Private contribution records; no intake or invitation service. |
| [Derived decision](../exports/derived-decisions-2026-11-05/decisions/participation.json), `2026-11-05T20:03:35.000Z`; [PR #98](https://github.com/4444J99/journal-handwritten-web/pull/98) | `around`, derived by Claude from the plan at the author's request; explicitly not selected by the author. | Preserved with provenance. A contribution cannot increment, allocate, or change an n/100 number. |
| Current scoped T05 request | Build a private versioned workflow and concrete previews, preserve source data, stage shared-page integration. | Authority for this isolated implementation and draft handoff only. |

Contributor types, invited versus open participation, permission terms, and
reflection timing remain decisions. The interface previews their consequences;
selecting metadata for a private record does not activate an intake route.

## Source identity and invalidation

Use the existing piece IDs from `site/data/j.json` (`p001`, etc.), the exact
`pieces[].V[].id` version IDs (`p001-diary1-0`, etc.), and the existing line IDs
from `studio/data/review.json` (`diary1-0-0`, etc.). A displayed ordinal, n/100
number, stack position, page coordinate, crop rectangle, or array index is not
an anchor. No IDs are allocated for source records that lack a verified mapping.

`tools/notes_sources.py` builds `studio/data/notes-versions.json` from those
preserved inputs. It carries only existing IDs, page/block membership, source
dates, and input SHA-256s. It never changes the inputs. The companion is a
derived map, not a recovered archival source. Run `--check` after each rebuild;
a stale map is an integration failure.

Each note binds to a source version and a captured textual state. The model
checks membership and text, independently of display geometry. A source change
can invalidate an anchor; the original anchor and all older
revisions remain available. Re-anchoring is an explicit new revision. The
system does not search for a similar line and silently move a note there.

The accessible T02 workspace was an older source snapshot; no completed T02
identifier contract was located. Existing IDs are verified repository facts.
T05's textual fingerprints and word selector are proposed extensions awaiting
T02 integration review, not an agreement attributed to that tranche.

Word/phrase selections use a line ID, an exact quotation and, when supplied,
explicit boundaries counted as zero-based Unicode code points, with an
exclusive end offset. Repeated matches without a disambiguating
selection are blocked. The UI explains the counting convention; renderer
coordinates remain disposable view state.

## Records, history, and storage

Notes distinguish footnotes, endnotes, personal reflections, factual citations,
critical notes and private research dossiers. Dates describe different facts:
the poem date may be unknown or approximate; the note date belongs to the
note's author; the revision timestamp records the edit. None substitutes for
another. Authorship and credit belong to the stored record, not an inferred
logged-in display name.

The [JSON Schema](schemas/notes-v1.schema.json) describes a revision or private
backup envelope. Runtime validation additionally checks actual calendar dates,
source fingerprints, same-record graph ancestry and approval digests. A schema
validator alone cannot establish these live or cross-record facts.

Contributions live in a separate collection. Each records the contributor,
contribution type, source association, permission state and scope, public
credit, editorial status and release state. Permission evidence remains
private. An editorial acceptance is not permission to publish.

`notes/{revisionId}` and `contributions/{revisionId}` use the existing studio
collection/document interface over `vf_docs`/`vf_revs`. Revisions append; they
do not replace a prior revision's body. Parent references preserve branches of
history. A concurrent fork is visible and blocks projection until explicitly
resolved. The existing six collections keep their behavior. There is no
table migration and no change to another project's tables.

The browser store has no localStorage substitute for persistence. An
unavailable database remains unavailable, a failed write is not shown as
saved, and a confirmed revision is checked by reading it back. Two editors
can create two different child revision IDs without erasing either edit.

Cloudflare D1 enforces immutable insertion atomically. A native Claude artifact
provider only receives client preflight/read-back checks here; its cross-client
immutability guarantees have not been established. The API and Python importer
validate a minimal persistence envelope; the workbench and backup CLI apply the
full model. Malformed direct low-level writes are blocked from the workbench and
projection rather than repaired into author data. Forks are preserved and
blocked; this workbench does not include a merge-resolution UI.

## Private authoring and preview

Open `notes.html` on the existing private/local workbench origin. Choose a
piece, its exact source version and optionally a line or phrase. Enter the
author's own text, dates, attribution and citations. Save a new revision;
select it again to inspect its history or make a later revision.

Review and clearance have separate controls. An explicit content edit or
re-anchoring creates a new draft with release held. An external source correction
leaves historical revisions and statuses unchanged but invalidates their
anchors and blocks preview/new clearance. A research dossier stays private
even if a malformed imported record claims a public intent. Technical
fixtures are visibly marked and are never eligible for public output.

The reader extension mounts empty and hidden. An explicit request reveals
the already-filtered records for the exact current piece/version. Hiding or
changing source context removes the rendered notes. The renderer uses text
nodes; stored HTML is displayed literally. It never fetches the private
collections. The main reader and studio page remain owned by their single
integrators; their wiring is a staged handoff, not an unreviewed edit.

The private workbench compares a below-poem region with a margin-column
proposal using the same cleared records; neither layout saves a placement
decision. Both display source IDs, not inline word marks. The margin column
stacks on small screens. Date-only technical cards compare same-day and later
reflection dates without supplying a reflection or selecting a delay. The type
selector and disabled invited/open cards preview contribution metadata and the
review process. Reading, music and hand-copy records currently hold text/source
references; media handling and contributor intake are not implemented.

## Release boundary (T03)

T03's `versforms.release-clearance.v1` is a proposed interface, not an approved
release. The inspected T03 head is `8d16284ba8b80f18398d08b8de931d8812f30429`,
[draft PR #119](https://github.com/4444J99/journal-handwritten-web/pull/119).
Its [release-clearance contract](https://github.com/4444J99/journal-handwritten-web/blob/8d16284ba8b80f18398d08b8de931d8812f30429/docs/releases/release-clearance-contract.md)
requires exact input/code/output manifests and attributable author clearance.
No such cleared release is supplied by this work.

T05 projection is an additional exclusion gate. It admits only an unambiguous
current revision, a valid anchor, the exact selected piece/version, appropriate
authorship, editorial acceptance, revision-bound clearance, an explicit
release state, and contributor permission/credit where relevant. It emits a
small allowlisted DTO, never the stored document, private dossier, contact or
permission evidence, draft, or revision history. A local cleared preview is
distinct from public output.

The model has no publish transition. T03 still needs a release adapter/event
bound to its actual clearance and output manifest before a real record can
be released. A manually supplied `released` label alone is insufficient.

The public builder remains T03's existing builder. No second posting or
deployment implementation is introduced. T03 must add the exact projected
bytes to its exposure manifest, invalidate prior clearance when those bytes
change, and retain its whole-scan/font/metadata gates. A hidden DOM element,
CSS rule, `noindex`, or accepted editorial state does not make private data
safe to ship.

## Export, restore, and backward compatibility

An existing poem with no notes requires no migration and renders exactly as
before. Existing author data, review originals, release records, decisions,
version IDs and poem numbering are preserved. Missing new collections mean
no notes; they do not trigger seeded content.

The workbench exports a private JSON envelope containing both new collections
and every revision. Restore preflights validation and ID collisions before
adding anything. Identical revisions are idempotent. Different bytes under an
existing revision ID are refused. A failed or interrupted restore retains
the revisions already saved and can be retried with the same backup; it does
not roll back by deleting history. The existing `studio-cf/import_export.py`
and `export_db.py` use their per-document `COLLECTION/DOCID.json` layout with
the two additional collection names. Test restores use disposable databases.

Do not use an older six-collection exporter after introducing notes: it must
reject unknown collections rather than silently omit them. Keep the complete
pre-change export. The Cloudflare middleware continues to protect all static
files and API routes. `build_dist.py` already includes added studio modules;
no deployment was performed. The Claude artifact's existing file map already
has 253 entries against its documented 255-file limit, so artifact packaging
of this extension is a separate integration task, not claimed as tested.

### Migration sequence (local/private)

1. Keep the original eight-collection export, or the complete pre-notes
   six-collection export. Missing notes/contributions remain empty.
2. Update the model, adapter, API and import/export allowlists together. Apply
   no table migration. Do not seed notes or alter author source files.
3. Regenerate `notes-versions.json` after either source input changes:
   `python3 tools/notes_sources.py`, then `python3 tools/notes_sources.py --check`.
   Build-time checking covers both `j.json` and `review.json`; the browser also
   checks the review-file digest when it loads.
4. Restore a copied backup into disposable local storage first and inspect the
   full graph, dates, source validity and counts. Re-anchor invalid sources only
   by an explicit new revision; keep the old history.
5. Retain the unmodified original backup alongside the verified new export.
   Rollback means keeping those archives and restoring the previous application;
   it does not delete the newly introduced history or make old exporters safe.

Local conversion between formats, with new output paths:

```bash
node tools/notes_backup.mjs pack /path/to/private-export /path/to/notes-private.json
node tools/notes_backup.mjs unpack /path/to/notes-private.json /path/to/new-private-export
```

The CLI refuses existing destinations, linked inputs, malformed UTF-8, invalid
graphs and conflicting IDs. Browser and CLI envelopes have a matching 32 MiB
limit; individual revisions retain the existing 64 KiB limit. Use the complete
per-document export for larger archives. A browser download is a private backup,
not a public release artifact.

## Per-issue residual map

| Issue | Delivered scope | Residual and owner |
|---|---|---|
| #17 | Typed private notes/citations/dossiers, exact anchors, editing/history, export/restore and requested-only preview. | Author supplies notes and decides critical-layer authorship; T01 integrates the studio entry; T04 integrates reader controls/placement. |
| #18 | Separate poem/note/revision dates; revisions preserve earlier reflections; invalid anchors remain inspectable. | Author chooses immediate versus delayed reflection and approves placement; no reflection has been generated. |
| #64 | Around-the-100 provenance; contributor/type/source/permission/credit/review/release fields; private reviewed fixture without count changes. | Author selects participation types, invited/open format and permission terms; intake, invitations and publication remain inactive. |

Verification commands, exact results and immutable source hashes are recorded
in the [T05 verification receipt](verification/t05-2026-11-05/README.md).
The [integration handoff](integration/t05-handoff.md) names the remaining owners
and interfaces. A passing fixture is implementation evidence,
not the author's acceptance of a real note or contribution.

### Addendum — 2026-11-27 (journal-handwritten-web #17 build)

The #17 layer is built: the private reference file
(`studio/data/reading-notes.json`, an empty schema-valid backup envelope —
no transcribed reading notes exist in-repo to copy into it, see
`docs/chats/2026-10-26-footnotes-and-endnotes/reading-notes.md`), the
public sidecar (`site/data/notes.json`, validated by
`tools/notes_sidecar.py --check`), the Notes tab in the review studio
shell (loads the `studio/notes.html` workbench), tap-to-reveal marks on
canvas and book (`site/notes-layer.mjs`), and the critical-apparatus
section in the Study view. The sidecar is empty until the author clears
a note for release review; the reader renders exactly as before with no
records. Residual, unchanged: the author supplies the notes and decides
critical-layer authorship.
