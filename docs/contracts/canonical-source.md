# Canonical source and reproducible review data — T02 v1

The private source of truth is `source/canonical.json`, identified by
`versforms.canonical-source.v1`. `tools/source_foundation.py` captures the
preserved source once, validates it, applies exported reviews, reconstructs the
current reader/studio data, and backs up or restores the source with all exported
studio state. It does not generate a new reader or studio interface.

The reconstruction preserves **123 page IDs, 126 piece IDs, 156 version IDs and
2,190 line IDs**. These are source inventory counts. They do not establish
publication readiness. The available export contains 38 line reviews: 33
confirmed and five corrected. It has no real release or batch records.

## Evidence and reconstruction boundary

The bounded search covered the current tools and the retained posting, journal,
T05, T09 and T10 clones. It recovered the source JSON, image assets, font/glyph
tools and exported reviews, but no original complete page/studio generator. The
new implementation is a technical reconstruction of those preserved inputs.
`provenance.sourceFiles` records their exact input hashes. The original generator
and historical image transformation recipes remain explicitly unrecovered.

Without accepted overlays, the compatibility serializer reproduces both captured
JSON files byte for byte. Their original hashes are retained in the canonical
record and tested. The five accepted readings and unavailable-anchor declarations
are additive generated fields. No raw original, image byte, embedded font or HTML
template is rewritten by review application or rebuilding.

The private context packet `2026-10-16-v1.1` and projection
`2026-10-16-v1.1-r2` were referenced by the handoff; their private project sources
were inaccessible in this session. Historical approvals are evidence only. This
implementation does not create an author decision, public approval or filing.

## Identity, order and original transcripts

The canonical arrays contain explicit records for pages, blocks, lines, pieces
and versions. Their IDs are keys, not array indexes. The `order` lists determine
page and piece presentation order; `page.blockIds`, `block.lineIds`, and
`piece.versionIds` retain local reading order. Reordering the entity arrays does
not change generated data. Legacy block IDs are allocated once at capture and
then retained; a new import must supply its own explicit unused IDs.

A version names its exact piece and member page/block IDs. The builder derives
the existing `V[].P` page/index mapping for compatibility. Neither `n/100`
numbering nor image coordinates allocate or rename identities.

Each line retains `originalText` from the studio and `readerOriginalText` from
the preserved reader. Most are identical. The 177 quotation blocks have an
intentional distinction: the private studio may carry an attributed descriptive
marker, while the reader has its abbreviated quotation marker. Both originals
remain intact. Review application refuses to rewrite these differing markers.

Existing transcriptions retain an unverified status. A staged photo has null
originals and `transcriptionStatus: "untranscribed"`. The compatibility JSON uses
an empty string plus that explicit status, allowing existing data readers to
load the page without claiming that it has been transcribed.

## Review application

From the repository root:

```sh
python3 tools/source_foundation.py validate
python3 tools/source_foundation.py --report /tmp/review-proposal.json apply-reviews \
  --db exports/studio-db-2026-11-05
python3 tools/source_foundation.py --report /tmp/review-applied.json apply-reviews \
  --db exports/studio-db-2026-11-05 --apply --backup /tmp/unique-source-backup
python3 tools/source_foundation.py rebuild --write
```

The default review operation is a dry run. It validates every filename, stable
line ID, status, recorded time, original transcript and correction before making
a proposal. `original` must equal the retained raw original. A correction whose
`text` happens to equal the current raw original cannot bypass that check.

Application requires a new independent backup destination. It takes an exclusive
local writer lock, verifies that the canonical source has not changed since the
proposal, completes the backup, then atomically replaces the canonical JSON.
The change report identifies every changed or unchanged review and its document
digest. `reviews.history` retains each accepted document, source filename, file
hash and recorded review time; `reviews.current` must match its latest entries.
A repeated identical application is a no-op and creates no extra backup or
history revision.

The builder writes only `site/data/j.json`, `studio/data/review.json`, and
`studio/data/notes-versions.json`. It preserves raw `B.L` and `line.tx` so
`post_poem.load_corrections` continues to detect stale originals.

| Generated field | Consumer and meaning |
| --- | --- |
| `review.acceptedReviews` | Private imported review documents, used by the notes and script source adapters unless an explicit live export supplies a later current record. |
| `j.acceptedReadings` | Five accepted correction strings keyed by stable line ID for the private reader; no review provenance is copied into this map. |
| `j.sourceBindings` | Current v2 `{pieceId, versionId, sourceFingerprint}` bindings keyed by `pieceId/versionId`, computed from effective accepted readings. Untranscribed versions are omitted; feature mounting must compare against this loaded current binding. |
| `j.sourceAnchors` | Explicit unavailable source anchors, keyed by stable line ID. |
| `review.pages[].blocks[].lines[].sourceAnchor` | The same unavailable-anchor state alongside the existing nullable box. |
| `B.lineIds` | Explicit IDs when an imported block's line IDs cannot be represented by the historical page/index convention. |

The public builder must continue using its explicit output allowlist and
publication-selected corrections. The private overlays themselves are not
release clearance. `capture` refuses existing accepted overlays when the
canonical history is absent; restore the canonical backup instead of silently
recapturing and discarding accepted state.

## Logical source fingerprint v2

`tools/source_fingerprint.py` and `studio/source-fingerprint.mjs` implement the
same SHA-256 payload, encoded as compact UTF-8 JSON with sorted object keys:

```json
{
  "pieceId": "exact-piece-id",
  "versionId": "exact-version-id",
  "members": [["exact-page-id", [0, 1]]],
  "lines": [
    {"lineId": "exact-line-id", "text": "effective source text",
     "blockType": "text", "breakBefore": false}
  ]
}
```

The version is a contract identifier, not an extra field in the hashed payload;
this preserves T10's already established v2 digest. `breakBefore` is an explicit
boolean. Coordinates, image dimensions, asset hashes and display numbering are
excluded. The ordered membership and ordered line list remain part of the
logical source structure.

The Python API exposes `source_fingerprint`, `source_fingerprint_v1`, and
`source_binding`. The latter returns
`{pieceId, versionId, sourceFingerprint}` for exact output binding. The notes
catalog exposes `fingerprint`, the identical `sourceFingerprint` alias,
`fingerprintVersion: 2`, and a historical `legacyFingerprint`. T10's
`source_snapshot` retains its existing `versionFingerprint` field and uses the
same shared implementation.

New note anchors carry `fingerprintVersion: 2`. Older anchors remain readable
and structurally valid, including their original hashes and revision history.
They are ineligible for live output until a new explicit source rebind is made;
there is no automatic migration. A stanza-only change invalidates a v2 anchor.

The shared vectors in `tests/fixtures/source-fingerprint-vectors.json` cover
Unicode, text, block type, membership and stanza changes, together with a
geometry-only change. Python/T10 and JS/T05 consume the same vectors. T08/T09
integration should consume `source_binding` when binding a rendered output.

## Geometry, photos and image lineage

Line geometry and image bytes have a separate digest through
`geometry_fingerprint(source, pageId)`. Moving a box or changing pixels leaves
the logical text digest unchanged and changes the geometry/media digest. Source
asset records retain exact byte hashes, sizes, page associations, transformation
status and null clearance. Generative assets do not belong in this source-ink
contract.

For preserved pages, `imageLineage` names the existing JPEG master and display
assets. The archival original, cleaned-image recipe and historical pixel
transformation are explicitly unavailable when unrecovered. A preserved JPEG
does not become evidence of a new archival scan.

For `diary1-2-3`, the fourth transcript line in block 2, the source has no fourth
line box. Its studio box remains null; `sourceAnchor.status` is `unavailable`.
No coordinate or ink-to-text mapping is invented. Consumers must use a scan or
text fallback and must not treat an inferred atom rectangle as a verified source
anchor. The availability inventory also includes other existing unboxed
quotation/drawing/text lines; its count is not a count of newly discovered
geometry defects.

Photo staging is a local explicit-ID operation:

```sh
python3 tools/source_foundation.py ingest-photo descriptor.json supplied.jpg \
  --db /path/to/current-export
python3 tools/source_foundation.py ingest-photo descriptor.json supplied.jpg \
  --db /path/to/current-export --apply --backup /tmp/unique-pre-ingest-backup
python3 tools/source_foundation.py rebuild --write
```

The descriptor must name `pieceId`, a new `versionId`, `pageId`, `blockId`, and
`lineId`. The supplied JPEG is retained byte for byte. The preserved page image
is a byte copy; display sizes record the Pillow version, resize method, quality,
subsampling, metadata omission and output hashes. A cleaned source and atlas
cell are not invented. The page/version stays `staged-untranscribed`, with
unknown transcription and unavailable anchors. Tests use a synthetic technical
image in a temporary destination, never an author-supplied photo or new wording.

## Existing font and exact-version deposit routes

The existing `tools/glyph_workflow.py` remains the font route: `sheet` creates an
empty source-bound worksheet, `import-capture` validates declared author labels
and source evidence, and `import-font` records the supplied font and its coverage.
The tests exercise those routes alongside T10. This source reconstruction does
not supply missing author-drawn characters or choose an author script.

The existing `tools/prepare_release_packet.py` prepares an exact-version release
evidence packet with source bindings, review inputs, image lineage and output
hashes. These are technical inputs for a later author-selected deposit workflow;
the command does not claim to reproduce the missing historical deposit generator
or a filing service's required format. Generating a local packet is not a filing
or publication. T03 owns the exact-output approval and observed publication-event
gates; #106 retains the actual filing/workflow decision and evidence.

## Independent backup and restore

```sh
python3 tools/source_foundation.py backup --db /path/to/current-export \
  --out /tmp/unique-complete-source-backup
python3 tools/source_foundation.py restore /tmp/unique-complete-source-backup \
  --out /tmp/unique-independent-restore
python3 /tmp/unique-independent-restore/repository/tools/source_foundation.py rebuild
```

The backup includes canonical source, every source/reader/studio file, the two
reconstruction modules, and every file in every exported studio collection. It
discovers collections dynamically, so `notes`, `contributions`, `artifacts`,
their complete histories, and future collections are not omitted by an outdated
fixed list. Empty collection directories are retained too.

The manifest hashes every file. Restore verifies all hashes, rejects extra or
missing files, linked paths and traversal, and refuses an existing destination.
It validates the canonical source before installing the restored tree. No live
database or unrelated project table is modified. The restored source can run
its own copied CLI and reproduce the same three data files.

Receipts for the actual 38-review application, repeat no-ops, full backup and
independent restored rebuild are in `docs/verification/t02-source/`.
