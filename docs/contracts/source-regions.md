# Shared source-region contract (T08, v1)

Status: **provisional working contract**, 2026-11-05. It is implemented and tested in
`tools/source_regions.py` and `tests/test_source_regions.py`, but it is not an author decision and
does not settle any artistic question. Identifier ownership belongs to T02; publication clearance
belongs to T03.

The contract gives every picture the system can show one shared answer to four questions:

1. **What is it?** — a stable atom identity for a poem, stanza, line, word, glyph, mark or derived
   combination.
2. **Where is it?** — a region in the source scan's pixel frame, with the method that produced it.
3. **Where did it come from?** — a closed lineage to source assets and source line ids.
4. **May it be shown?** — a separate, dateable visibility policy evaluated for a named scope.

It does not render, generate language, choose crops, choose fonts or strokes, decide chance versus
rule, or approve publication.

## 1. Files

| File | Role |
|---|---|
| `docs/schemas/source-region-v1.schema.json` | readable shape of a manifest |
| `docs/schemas/visibility-policy-v1.schema.json` | readable shape of a policy |
| `tools/source_regions.py` | builder, validator, lineage walker, eligibility engine |
| `docs/pilots/t08-p001/p001.source-regions.json` | the one private pilot manifest |
| `docs/pilots/t08-p001/visibility-policy.json` | derived pilot defaults (**not** author decisions) |
| `docs/pilots/t08-p001/fixtures/` | synthetic rejection and combination fixtures |
| `tests/test_source_regions.py` | executable contract tests |

`python3 tools/source_regions.py verify` is the executable validator. The JSON Schema files are the
readable companion; if they disagree, the validator and this document win until the schema is fixed.

## 2. Identity

```
vf:atom:<piece>/<version>/<page>/poem
vf:atom:<piece>/<version>/<page>/stanza-<n>
vf:atom:<piece>/<version>/<page>/line-<block>-<line>
           <line atom>/word-<n>
           <word atom>/glyph-<n>
           <line atom>/mark-<n>
vf:atom:<piece>/<version>/<page>/combination/<id>
```

- `piece_id`, `version_id`, `page_id` and `line_id` reuse the stable identifiers already in
  `site/data/j.json`. `line_id` is `<page>-<block>-<line>` (for example `diary1-3-2`).
- **T02 handoff is missing.** No completed T02 source/deposit/stable-ID contract was found in the
  repository or the context packet. The identities above are therefore *provisional*: they are the
  existing published ids, not a T02 sign-off. If T02 later renames an id, this contract needs a
  migration map, not a silent rewrite.
- `source_ids` carries the human-readable coordinate set (`line_id`, `block_index`, `line_index`,
  `global_line_index`, word/glyph/mark ordinals). `atom_id` is the canonical key.
- A version-specific exclusion names a `version_id`; never infer that a rule about one version
  applies to another.

## 3. Regions and units

All `region.frame` values are `source-pixels` in the page image recorded by the manifest's
`source_assets` entry (origin top-left, `x1`/`y1` exclusive). Each region carries the `method_id`
that produced it.

| Unit | Region authority | Notes |
|---|---|---|
| poem | union box | no polygon; use child line regions for ink |
| stanza | union box of its line boxes | stanza order follows `j.json` block order |
| line | owner seam-partition polygon + box | polygons are authoritative: adjacent line boxes overlap, polygons do not |
| word | gap-rule box | a word box is a usable crop, not a verified token |
| glyph | connected-component box | an ink component, **not** a letter or character |
| mark | connected-component box | commas/dots; never a word |
| combination | union box of inputs | derived; carries `combination.input_atom_ids` |

Rules:

- A `bbox` is never enough on its own to claim ink ownership when polygons exist.
- A line's box may overlap its neighbours; its `polygon` may not.
- Word alignment is in-sample only (18 of 22 lines in this pilot). Glyph boxes are pictures.
- `author_box.state` makes a missing author box explicit rather than silently repaired. In this
  pilot, `diary1-2-3` has no author box in `site/data/j.json`; the owner's seam partition restores
  the line, and the manifest says so.

## 4. Methods and lineage

Every method is declared once:

```json
{
  "method_id": "method:seam-partition-v1",
  "kind": "ink-partition",
  "implementation": "proto/alive/segment.py (owner branch)",
  "implementation_commit": "eece4f5…",
  "status": "owner-tested-in-sample",
  "parameters": {},
  "limits": ["one page, 22 lines, in-sample parameters; no held-out page"]
}
```

Every atom carries a closed `lineage`:

- `parent_atom_id` — containment (glyph → word → line → stanza → poem).
- `input_atom_ids` — derivation inputs for a combination (the only field combinations use).
- `root_source_asset_ids` — the scan/font/derived asset ids, all declared in `source_assets`.
- `source_line_ids` — every source `line_id` the atom's ink came from, including borrowed lines.
- `method_id` — must match a declared method.
- `derivation_ids` — declared in `derivations`.

The validator checks closure: missing parents/inputs, undeclared assets or methods, and cycles are
errors. `lineage` prints the full closure for one atom:

```
python3 tools/source_regions.py lineage \
  --manifest docs/pilots/t08-p001/p001.source-regions.json \
  --atom-id 'vf:atom:p001/p001-diary1-0/diary1/line-0-1'
```

The pilot reuses the owner's `atoms-p001.json` (commit `eece4f5`, sha256 `ed379ac4…`) and does **not**
re-run segmentation. The manifest records the artifact hash and says `reused_not_reimplemented`.

## 5. Reading, uncertainty and deliberate misread

These are three different things and must never be collapsed:

| State | Field | Meaning |
|---|---|---|
| transcription | `reading.transcription_state` | what text store, if any, is attached; `not-attached-in-this-contract` by default |
| source uncertainty | `reading.uncertainty_ids` → `uncertainties[]` | the scan/transcription is genuinely unclear; status stays `open` until the author resolves it |
| deliberate misread | `reading.deliberate_misread` | a machine/intentional misreading kept as a labelled artistic state, with its own unresolved rule |

- No atom stores poem text. `reading.text_ref` points at a separate author-reviewed store. The
  validator rejects any `text`, `transcript`, `poem_text`, `line_text` or `word_text` field with a
  non-empty value anywhere in the manifest.
- Open uncertainties are warnings, never automatic permissions or automatic refusals.
- A deliberate misread is refused for public output while `machine_misread.status` is not
  `cleared`. No author rule exists today (issue #109 question 1 / issue #56).
- The owner withdrew line 13 (`diary1-3-2`) after eye review. The manifest records
  `crop-withdrawn-by-owner-eye-review`; it does not pretend the crop is correct.

## 6. Credit and borrowed lines

`credit.origin_kind` is one of `author`, `borrowed`, `reader`, `community`, `public-domain`.

- `origin_kind: "borrowed"` requires non-empty `source_atom_ids` and, for public output, a chosen
  `credit_style`. A borrowed line with no credit style is refused.
- All derived tools (Cut, fold-in, erasure, cipher) use the same credit fields and the same
  `source_line_ids`, so a line cannot acquire credit in one tool and lose it in another.
- Credit is an author decision. The engine can refuse an incomplete record; it cannot choose the
  wording.

## 7. Combinations (Cut, fold-in, erasure, cipher, misread)

A combination is a derived atom with `unit: "combination"` and:

```json
"combination": {
  "operation": "cut | fold-in | erasure | cipher | misread | borrowed",
  "input_atom_ids": ["…"],
  "operator": "author | external",
  "rule": "chance or rule as the author recorded it",
  "seed": null,
  "text_ref": null
}
```

- Inputs must exist in the same manifest. Missing inputs and cycles are contract errors.
- The operation record distinguishes chance from rule; the tool never chooses for the author.
- Combinations inherit their inputs' root assets and source line ids. Borrowed inputs keep the
  borrowed credit requirement.
- A combination remains private/local until the visibility policy allows the named scope.
- The synthetic fixture `fixtures/synthetic-combinations.source-regions.json` contains one Cut, one
  borrowed-line, one cipher and one deliberate-misread atom. It contains no poem text and no puzzle
  message. Regenerate it with `python3 tools/build_t08_combination_fixture.py`.

## 8. Visibility and eligibility

Eligibility is external to the manifest. A policy names:

- `publication.enabled` (must be false for private previews);
- `author_clearance` — `status`, plus `covers_manifest_sha256`, the exact digest it covers;
- `machine_misread.status`;
- `shared_scan_resolution` — page-level remedies when pieces share a scan;
- `public_whitelist` — the only pieces allowed publicly;
- `withheld_pages` and `withheld_assets` — refused in every scope;
- `pieces[piece].pool` — `series`, `reserve`, `archive`, `withheld`, `deleted`, `unassigned`;
- `withheld_versions`, `excluded_versions` (scope-aware), `strike_through_vetoes`,
  `piece_vetoes`.

Scopes:

| Scope | Meaning |
|---|---|
| `private-local` | local preview of any pool except withheld/deleted; records `inherited_pool` |
| `author-cut-private` | author-operated Cut over private source material |
| `public-release` | public presentation of a Series piece with clearance and whitelist |
| `cipher-public` | public puzzle/cipher output; never over Reserve/Archive/withheld/unassigned |

Behaviour:

- Public output requires pool `series`, whitelist membership, a dated clearance that names the exact
  manifest digest, and every neighbour on a shared scan cleared (or an author-approved page remedy).
- Private output may inherit Reserve/Archive/unassigned material, but the report records the
  inherited pool and the tool never promotes it. `withheld`/`deleted` is refused in all scopes.
- Strike-through vetoes are author-private records: they respect `scopes` and can block a private
  build.
- Version exclusions respect `scopes`; a rule about one version never leaks to another.
- A successful `check` is **not** artistic approval, publication clearance or a release decision.

Commands:

```
python3 tools/source_regions.py verify --manifest … --out checks/verify.json
python3 tools/source_regions.py check --manifest … --policy … --scope private-local
python3 tools/source_regions.py check --manifest … --policy … --scope public-release
```

`check` exits `0` allowed, `3` refused, `2` bad invocation/unreadable input. `--out` writes the full
report, including per-atom reasons and required actions.

## 9. T03 release-clearance alignment

T03's draft `versforms.release-clearance.v1` remains evidence, not authority (PR #119 at `8d16284`,
not merged). T08 implements the part that can be checked against a manifest and leaves the rest to
T03:

| T03 field | T08 handling |
|---|---|
| exact piece/version/page/line ids | required in every atom; eligible only if the version is not excluded |
| input/asset hashes | `source_assets[]` and `derivations[]`; verified against bytes on disk |
| review originals / uncertain readings | carried as open `uncertainties[]`; never silently resolved |
| `pool_clearance` | `pieces[].pool`; only `series` may publish |
| `exposure_manifest` | out of scope; T08 records asset hashes, not a complete exposure proof |
| `shared_scan_resolution` | required for every page carrying more than one piece unless resolved |
| `filing_evidence` | optional `release_gate.filing_evidence_ref`; T08 does not create or interpret it |
| `acceptance_receipt` | optional `release_gate.acceptance_receipt_ref`; T08 does not run browser/phone acceptance |
| `author_clearance` | dated status plus `covers_manifest_sha256`; bound to the exact digest |
| `rollback_record` | optional `release_gate.rollback_record_ref`; T03 owns the revert |
| invalidation | any changed manifest changes the digest, so an old clearance no longer covers it |

When a policy carries `release_gate`, public output requires `status: cleared` and
`may_publish: true`. A missing gate is treated as not implemented, not as permission; the clearance
and pool checks still apply. A successful T08 check never substitutes for T03's record or for the
author's dated statement.

## 10. Interfaces

| Owner | Interface | T08 provides | T08 needs |
|---|---|---|---|
| T02 | identifiers, source/deposit record | atom ids and asset hashes, provisional ids from `j.json` | a completed ID/deposit contract; none located, recorded as missing |
| T03 | publication/release clearance | manifest digest binding, pool/whitelist/shared-scan checks | the merged clearance contract; draft PR #119 is evidence, not authority |
| T04 | reader | `may_publish`, whitelist and per-atom reasons | the reader's own eligibility call; T08 does not replace it |
| T05 | notes/provenance | lineage ids, method/derivation refs, `text_ref` | note/endnote attachment rules |
| studio integrator | Cut UI | combination atom shape and credit fields | a staged UI change through the studio owner; no UI is built here |

The reader and studio must not re-derive visibility from `release/public.json` alone. They should
call the same policy evaluation, or consume its report, so two surfaces cannot disagree.

## 11. Known limits and unresolved questions

Recorded as limits, not built into the product:

- One page, 22 lines, one owner spike. No held-out page; the gap rule and seam parameters are
  in-sample and optimistic.
- Word alignment is 18/22 lines; glyphs are ink components, not letters.
- Line 13's crop is withdrawn; crossing strokes are cut by the cheapest seam, not by whose stroke
  they are.
- The pilot's pool is `unassigned` because no Series/Reserve/Archive decision exists.
- `site/data/j.json` block 2 lacks one author line box; the seam partition restores the line.
- No completed T02 contract; no merged T03 clearance contract; no author-supplied Cut sentence,
  cipher plaintext/pages, strike-through veto list or solver-credit rule.
- Unresolved artistic questions are mapped in
  [`docs/pilots/t08-p001/decision-map.md`](../pilots/t08-p001/decision-map.md). Markov/n-gram text,
  sensors, location/weather, reconstructed strokes and an automatic misread generator are **not**
  built here and must not be inferred from this contract.

## 12. Privacy

The manifest contains geometry, ids, methods, states and hashes only. It must never commit poem
text, cipher plaintext, puzzle answers, or the owner's private veto list. The pilot policy is
private-local; serving it is `127.0.0.1` only. The source scan is already a private repository
asset and is referenced by path and hash, not copied.
