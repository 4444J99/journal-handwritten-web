# Exact output and private artifact integration

Date: 2026-11-06. Technical implementation; no author release record is supplied.

## One output contract

`tools/release_contract.py` and `studio/release-contract.mjs` validate
`versforms.release-output.v1`. Its digest covers the complete path/size/SHA-256
inventory, exact piece/version/source fingerprints, component revisions, code,
inputs and exposure record. An independently supplied
`versforms.release-clearance.v1` must name that digest and contain attributable
author, pool, filing-workflow, image-exposure, identity-metadata and device
evidence. The validator compares freshly resolved source bindings. The Python
entry point can also compare the actual output directory with the inventory.

Hashes identify bytes; they do not authenticate a person. Clearance record
validation never supplies execution authority. A valid record cannot schedule,
publish, deploy, post a message or change an account. Those actions remain
separately authorized operations. Synthetic positive controls exist only in
tests; no actual clearance is generated.

Each component contains `kind`, `id`, `pieceId`, `versionId`,
`sourceFingerprint`, `revisionDigest`, `fixture`, `path` and `sha256`. Its source
fingerprint must match the manifest source, and its path/hash must occur in the
output inventory. Technical fixtures are excluded. Changed text, permission,
credit, pronunciation, audio bank, region geometry, realization or glyph bytes
must produce a new revision and invalidate the former record.

| Consumer | Implemented boundary |
|---|---|
| T03 private preparation | `prepare_release_packet.py` writes `preview-manifest.json`; authentic missing release records still refuse posting. |
| T05 notes/contributions | `notes-release.mjs` appends a publication revision only after exact clearance and a separately supplied observed event. Public projection verifies that event, the revision graph, source, credit and contribution permission. |
| T06 weekly record | `audience_release.py --record FILE --context FILE` checks exact selected versions and media paths/hashes; scheduling and publication flags remain false. |
| T08 source regions | `source_regions.py check --release-context FILE` requires the shared output contract for either public scope, in addition to region policy, pool, borrowed-line and shared-scan checks. Region manifest changes invalidate its component revision. |
| T09 audio evidence | Immutable artifacts bind feedback to source, sample, render, pronunciation and bank hashes. A listening decision is a private observation, not release clearance. |
| T10 script realizations | Public projection needs the shared contract and every glyph asset in its output inventory. Public display data excludes private authorship/source-locator evidence. |

Historical Site/social records are read without rewriting their original type.
`eventChannels` reports physical channel separately and leaves publication
classification unresolved. An observed event must identify its exact output,
source, recorder, time and HTTPS URL; it records an action already observed.

## Private artifact persistence

`artifacts` is the ninth Studio collection. It shares the existing Access
authentication, writer permission, 64 KiB limit, `vf_` namespace and immutable
create-or-identical behavior used by notes and contributions. The six legacy
collections retain their existing replacement semantics. There is no schema
migration outside `vf_` and no mutation of another project's tables.

`studio/artifact-model.mjs` accepts `audio-feedback`, `pronunciation`,
`audio-render`, `realization` and `release-evidence` records. Every revision has a
stable record ID, new revision ID, parent references, exact source binding,
payload, fixture flag, actor/time/reason and digest. Source changes require an
explicit `source-rebind`; an existing fixture lineage cannot become author
material. A fork is preserved and reported rather than silently selecting a
winner. A stale source binding is reported without retargeting it.

`createArtifactStore` uses the same verified save/reload store as notes. It has
no localStorage fallback. Export waits for the initial snapshot, restore
preflights collisions, and an interrupted restore can be retried without
overwriting earlier revisions. Full Studio exports/imports include all nine
collections; notes-only backups keep their original format and scope.

Real local Wrangler verification writes all nine collections, restarts the
source database, exports it, restores into an independent database, retries
after a deliberately partial restore and tests a changed-ID collision. Notes
and artifact forks survive. An unrelated sentinel table remains unchanged in
both databases. This verifies local persistence; deployed Access, runtime
settings, account identities and physical devices remain separate evidence.

## Filtered reader metadata

The public builder retains a PAL/HF witness only when every referenced source
page/block is selected. Partial witnesses are removed, and a comparison needs
two complete witnesses. The reader handles empty tables. A nonempty filtered
build copies the same lifecycle module as the private reader. Private accepted
review records are omitted; public text comes from the explicitly validated
corrections supplied to the builder.

The preparation audit checks all output text files for withheld page
identifiers, verifies image and font metadata separately, and inventories the
actual files. It does not infer author approval from a passing check.

## Recovery provenance

`proto/alive/` is recovered from the existing private history, with its final
executable/data state at `eece4f56ffaae81500aaf94fd18852b2038e06d6` and precision
corrections/verification at `0561f712e0061db5317115097af72e874c9652d9` on PR #102.
The latter changes documentation and an opening code comment; it does not
replace the animation. Both original remote lineages are retained. The
prototype is private and opt-in. Pixel containment inside assigned polygons
does not resolve the documented crossing-stroke ownership errors, missing
author geometry or design choices in #109/#121.
