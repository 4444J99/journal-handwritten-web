# Current private source-region preview

This is the bounded November 6, 2026 integration correction to the T08 pilot. It
does not change the preserved prototype or assign uncertain handwriting to a
line. It exports one existing line-anchored atom for the shared private reader
lifecycle, with a **full source image, without cropping**. Public output and
author design choices remain separate.

## Export and revalidation

```sh
python3 tools/source_regions.py preview \
  --manifest docs/pilots/t08-p001/p001.source-regions.json \
  --policy docs/pilots/t08-p001/visibility-policy.json \
  --atom-id vf:atom:p001/p001-diary1-0/diary1/line-0-0 \
  --source-repo /path/to/current/private-checkout \
  --out /path/to/new/private-preview
```

The printed JSON is a reader `regions` descriptor. Resolve its relative
`package.manifestUrl` against the served preview directory. The directory must
be new, outside the source checkout and outside publishing inputs. Optional
`--source-db` supplies the current exported reviews/release collection. Optional
`--expected-descriptor` refuses an earlier descriptor if source, review,
geometry, media, policy or package bytes changed; it never silently rebinds it.
The selected `--source-repo` governs manifest preload, asset validation and
eligibility together; no stage falls back to the tool checkout. `verify` and
`lineage` accept the same optional source root. Omitting it retains the tool
checkout default. Unreadable or invalid selected assets fail during preload.

Before any output is written, the exporter validates the actual region
manifest, private eligibility, fresh T02 v2 source membership, canonical source
and rebuilt reader/Studio parity, current review/source policy, selected atom,
canonical line geometry, and actual JPEG bytes against both T08 and canonical
asset records. The regular private `check` command also resolves current v2
source bindings and verifies source-asset bytes; private scope no longer skips
that validation. Private inspection can retain known Reserve/Archive material
under the existing private contract; withheld sources/assets and explicit
scope/version/line vetoes refuse. A policy change requires fresh inspection.

This bounded reader route requires every atom and its source-line lineage to
belong to the selected current piece/version. The selected line's block index
must agree with both canonical membership and the current source snapshot. Its
atom ID uses `vf:atom:` followed by letters, digits, `_`, `.`, `/`, `:`, or `-`.
There must be exactly one `page-scan` asset at tier `p` on the selected page,
and it must be the selected atom's declared source image. Broader compositions
remain valid for the general T08 evaluator; this exporter refuses shapes the
bounded reader cannot display.

Each manifest piece needs an explicit known policy pool. Missing, null or
unknown pools are refused without normalization; known `withheld` and `deleted`
pools remain denied by eligibility. Withheld/veto identifier lists contain
nonempty strings. Exclusion and veto entries must be objects with array scopes
drawn from `all`, `private-local`, `author-cut-private`, `public-release`, and
`cipher-public`; absent or empty scopes retain the existing `all` default.
These shapes are checked even for unrelated target versions. General evaluator
defaults are unchanged.

Separate `release_gate` evidence is preserved in the original policy and is
not an additional private-inspection gate. Its permission flags neither grant
nor revoke this private route. The package remains nonpublishing, the manifest
scope stays `private-local` with `may_publish:false`, and
`policy.publication.enabled` must remain `false`.

## Package contract

`region-preview.json` has schema `versforms.private-region-preview.v1`, audience
`private`, `fixture:true`, `mayPublish:false`, scope `private-local`, exact
`source`, `sourcePolicy`, `atomId`, four revision digests, `sourceAnchor`, `image`
and an exhaustive `files` list. Each file record has a safe relative `path`,
integer `bytes` and strict `sha256:` hash. The manifest excludes itself; the
descriptor's `package.sha256` hashes the exact manifest bytes.

The exporter and reader share the same inclusive size limits: `region-preview.json`
is at most **64 KiB**; each declared payload is **1 byte through 16 MiB**; the
declared payloads total at most **32 MiB**. The separate manifest is excluded
from that total. The reader accepts 1 through 20 declared files; this region
format always exports the five listed below. JPEG width and height must be
positive integers whose product is at most **40,000,000 pixels**. The source
archive's larger generic read limit does not grant preview eligibility.

Every byte and image limit is checked before creating the output directory or
its parents. Refusal leaves source files and an existing destination untouched;
the CLI reports the violated budget and exits 2. The exporter does not resize,
recompress or truncate source material to make an oversized package fit.

| File | Verified content / top-level digest |
|---|---|
| `region-manifest.json` | Original complete selected T08 manifest / `manifestDigest` |
| `policy.json` | Original T08 scope and veto policy / `policyDigest` |
| `source.json` | Fresh logical `snapshot` and current `{pool,visibility}` `sourcePolicy` |
| `geometry.json` | Actual atom region/author-box provenance, canonical page geometry, current review geometry and exact source anchor / `geometryDigest` |
| `assets/source.jpg` | Original full source JPEG bytes / `mediaDigest` |

All four digests are **raw file SHA256**, not hashes of a browser's reserialized
JSON. The browser must verify every listed file before using it and compare the
package's source, atom, digests and policy to the supplied descriptor. It must
cross-check the selected atom and geometry proof against the original manifest,
the anchor against the canonical line and current Studio/reader geometry, and
the source against the actual selected version. An immutable package is not
proof that its source is still current.

`geometry.reviewPageGeometry` is derived from current `studio/data/review.json`:

```js
{
  pageId: page.id, width: page.w, height: page.h,
  blocks: page.blocks.map((block, index) => ({
    index,
    lines: block.lines.map(line => ({
      lineId: line.id,
      box: line.box ?? null,
      sourceAnchor: line.sourceAnchor ?? null
    }))
  }))
}
```

The consumer compares that projection with its independently loaded current
source, plus current `{pool,visibility}`. Coordinate-only edits therefore
invalidate the preview even when the logical source fingerprint is unchanged.
An unavailable canonical anchor has `box:null`; if any line in its block lacks
geometry, the whole block remains unavailable, matching the reader's refusal to
guess alignment from mismatched line/box counts. The old atom's inferred polygon
must never replace it. The package retains the source image for byte/provenance
verification, but an unavailable-anchor view displays the explicit unavailable
state instead of an image or substituted crop. Available views identify the
image as full source, not selected-region exclusion proof.

The browser route is explicitly enabled, private, same-origin, and lifecycle
controlled. It owns fetch cancellation and image URLs, clears them on source or
policy change/dismissal/unmount, and makes no posting or public-clearance claim.
