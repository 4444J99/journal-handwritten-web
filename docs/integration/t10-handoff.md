# T10 integration handoff — proposed interfaces, private fixture

**2026-11-05 review baseline; refreshed 2026-11-06 UTC.** This handoff records technical proposals and tested local behavior. It does not record acceptance by another tranche, a chosen study language, a finished translation, or release clearance.

## Ownership and dependencies

| Owner | Concrete handoff | Status and boundary |
|---|---|---|
| T02 — shared model and font interfaces | [Realization schema](../../schemas/script-realization.schema.json), exact editorial `pieceId`/`versionId`, existing line IDs, T05-compatible version fingerprint, immutable glyph asset `{id, kind, path, sha256, visibility, author, sourceLocator}`. | Proposed, awaiting T02 review. No T02 agreement or settled font expansion was found in the inspected repository/PR evidence. No shared model is modified. CSS uses `ajp-scribbles`; exact original OTF bytes and internal metadata remain private. |
| T03 — release clearance | Exact realized text/history selection, source binding, font/capture manifests and all shipped bytes must be included in `versforms.release-clearance.v1`. | [PR #119](https://github.com/4444J99/journal-handwritten-web/pull/119), inspected head `8d16284ba8b80f18398d08b8de931d8812f30429`, is draft and has no approved release. T10 emits an empty public DTO pending an actual adapter. It does not treat Series, `public-proposed`, or earlier source exposure as permission. |
| T05 — annotations/contributions | Sorted-key UTF-8 fingerprint of `{pieceId,versionId,members,lines:[{lineId,text,blockType}]}`. | Independently compared to [PR #126](https://github.com/4444J99/journal-handwritten-web/pull/126), head `c6930bb48f07fe81e23b3126aeaf5947fb4406e1`. The existing p001 vector matches. The contract remains proposed to T02; no edits to T05's files. |
| T08 — atoms | Optional future source-region locators on capture provenance, if an author actually selects a scanned glyph. | Inspected [PR #102](https://github.com/4444J99/journal-handwritten-web/pull/102), head `2664d104c114099aac0f901f084554dea8d5c2a1`, [prototype README](https://github.com/4444J99/journal-handwritten-web/blob/2664d104c114099aac0f901f084554dea8d5c2a1/proto/alive/README.md). Its glyph boxes are ink components, not letter identities. The existing-font fixture gains nothing from that dependency, so it is not coupled. |
| T04 — reader behavior | If a future reader consumes a cleared realization, accept the small projection DTO and preserve logical lines, `lang`, `dir`, whole shaping runs, and visible fallback attribution on request. | No reader edits or deployment. This pilot is a local private HTML preview. Native-details metadata follows the standing hidden-until-requested presentation rule. |
| T01 — integration/lifecycle | Isolated T10 branch, verified package, retained exact base and source hashes, scoped issue disposition. | Review and integration remain the existing owner's responsibility. No merges, issue closures, history rewrites, or repository restructuring. |

## LingFrame: inspected before coupling

The actual project located through the connected repository inventory is [`4444J99/linguistic-atomization-framework`](https://github.com/4444J99/linguistic-atomization-framework), whose README identifies it as LingFrame. The inspected `main` was **`bf36cbd553cc2981a02d516246722d3bb96a8471`** (2026-11-05T22:12:01Z). No other similarly named repository was substituted.

Read-only inspection covered the [README](https://github.com/4444J99/linguistic-atomization-framework/blob/bf36cbd553cc2981a02d516246722d3bb96a8471/README.md), [atomizer](https://github.com/4444J99/linguistic-atomization-framework/blob/bf36cbd553cc2981a02d516246722d3bb96a8471/framework/core/atomizer.py), [ontology](https://github.com/4444J99/linguistic-atomization-framework/blob/bf36cbd553cc2981a02d516246722d3bb96a8471/framework/core/ontology.py), [tokenizers](https://github.com/4444J99/linguistic-atomization-framework/blob/bf36cbd553cc2981a02d516246722d3bb96a8471/framework/core/tokenizers.py), [recursion module](https://github.com/4444J99/linguistic-atomization-framework/blob/bf36cbd553cc2981a02d516246722d3bb96a8471/framework/core/recursion.py), and [license](https://github.com/4444J99/linguistic-atomization-framework/blob/bf36cbd553cc2981a02d516246722d3bb96a8471/LICENSE).

Relevant observed behavior:

- Paragraph/sentence tokenization splits and strips text. Word tokenizers return token strings. They do not supply an exact journal line/offset contract.
- `LETTER` traversal iterates Python characters. A scalar is not necessarily a grapheme cluster, a shaped glyph, or a handwritten ink component.
- `Atom` stores generated IDs, levels, text, parents/children and context metadata. It has no canonical source start/end offsets or existing journal version/line identity.
- Generated IDs depend on the processor's naming/context, so they must not replace journal identity or T10 source fingerprints.
- MIT coverage for its code/docs does not license every corpus it can process. No LingFrame corpus is copied into this repository.

These are source-code observations, not a claim that its full runtime was installed or tested here. In particular, the general word/root/letter architecture does not establish a linguistically correct analyzer for whichever language the author eventually selects.

### Narrow optional interface proposal

Keep the repositories as independent versioned units. A later **local, private diagnostic adapter** can take an immutable input packet:

```json
{
  "contract": "versforms.linguistic-diagnostic.input.v1-proposed",
  "sourceRepository": "4444J99/journal-handwritten-web",
  "sourceCommit": "<exact commit>",
  "pieceId": "<existing piece>",
  "versionId": "<existing editorial version>",
  "sourceFingerprint": "sha256:<exact reading>",
  "language": "<author-selected tag>",
  "script": "<author-selected script>",
  "lines": [{"sourceLineId": "<existing line>", "text": "<unchanged source>"}],
  "processor": {"repository": "4444J99/linguistic-atomization-framework", "commit": "<pinned commit>", "configSha256": "<hash>"}
}
```

Return derivative diagnostics in a separate namespace, with processor/version/config identity, `sourceLineId`, codepoint start/end offsets and the exact corresponding source substring. Treat any external atom ID as processor-local. Validate every returned span against the exact input; once a script is selected, also check the relevant grapheme boundaries and segmentation conventions. Do not normalize, strip, rewrite, or regenerate the source to make a span match.

This adapter is **not implemented** because the inspected API lacks the required stable source-span guarantee and the selected language is pending. Do not wire the narrative/generation/recursive-rewriting paths into author presentation text. No network/model downloads, external text processing, dependency installation, or corpus sharing are prerequisites for the delivered fixture.

## Issue disposition

| Issue | Reconciled residual | Delivered here | Remains |
|---|---|---|---|
| [#12](https://github.com/4444J99/journal-handwritten-web/issues/12) | Earlier reader merge/hardening was already checked complete. Roots/glyphs remained author-owned. | Independent realization axis; reusable glyph capture/import; bounded LingFrame inspection and proposed adapter. | Author's first real input; optional roots analysis only after a language-specific interface is useful. Keep issue open and ownership unchanged. |
| [#33](https://github.com/4444J99/journal-handwritten-web/issues/33) | Research, suggestions, self-translation and grant follow-ups; no adopted Greek-first choice. | Exact-source Latin fixture; Unicode/rendering proof; private publication exclusion; sourced [policy follow-ups](../t10-policy-followups.md); optional blank [practice worksheet](../t10-weekly-practice.md). | Author selects language/script, exact poem/version and method, supplies text/glyphs, and names any venue/program/cycle. Keep issue open. |
| [#110](https://github.com/4444J99/journal-handwritten-web/issues/110) | Optional author font extension; historical importer absent. | New standalone bounded workflow and original-font provenance. | Fresh author handwriting and artistic approval; no claim to recover the old importer. |
| [#107](https://github.com/4444J99/journal-handwritten-web/issues/107), [#123](https://github.com/4444J99/journal-handwritten-web/issues/123) | Missing historical generators; posting hardening respectively. | No changes to their owned implementation paths. | Remain with their owners; T10 does not invoke posting. |

The dated verification receipt contains actual commands, rendering evidence, source-preservation hashes and observed limitations. The [minimum author input](../t10-author-decisions.md) makes the next decision finite without requiring a full translated poem or expanded font.
