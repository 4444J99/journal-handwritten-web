# Follow-on contract: author-operated Cut (T08 hand-off)

Status: **contract prepared, tool not built**. 2026-11-05. This is a hand-off to the studio
integrator (issue #55). It records the data shape and invariants a Cut tab must satisfy; it does not
add a UI, choose a chance rule, or write any poem.

## Why this shape

Issue #54 asks the author to decide chance versus rule per poem, how borrowed lines are credited,
whether version history is published, and when to stop using the method. Issue #55 proposes a Cut
tab (shuffle / strike / keep own lines, no language model, saves a new version). The shared
source-region contract already gives every line, word and derived combination one identity and one
lineage. Cut therefore needs no second model of the poem: it operates on atoms and writes
combination atoms.

## Boundary

- **Author-operated.** The author chooses the source lines, the operation, the order, what is kept,
  what is struck, and when to stop. The tool performs no language generation and no interpretation.
- **No language model.** Markov/n-gram generation remains unresolved and is not part of this
  contract (issues #55, #56, #109).
- **Private by default.** A Cut session is `author-cut-private`; nothing becomes public because it
  was cut. Publication is a separate `public-release` check against the T03-style policy.
- **One new version, not an edit in place.** Output is staged as a new version through the studio
  integrator. The source version and its atoms stay intact.
- **Creative text is author-supplied.** The tool may reorder, strike or fold existing atoms; it may
  not write a new line.

## Data flow

```
selection (atom ids, eligibility-checked)
  -> ordered steps (recorded, replayable)
  -> combination atoms (operation = cut | fold-in | erasure)
  -> new version record (studio integrator)
  -> eligibility check for the target scope
```

### Selection

- Inputs are atom ids from the shared manifest, never text.
- A private Cut may use Reserve/Archive/unassigned material; the eligibility report records
  `inherited_pool` and the tool may not promote it.
- `withheld`/`deleted` material and withheld assets are refused in every scope.
- A reader-operated Cut (not built) must exclude Reserve and requires the participation decision
  (issue #56 / plan open item 3).

### Steps (author-recorded, replayable)

```json
{
  "step": 3,
  "action": "strike",
  "target_atom_ids": ["vf:atom:p001/p001-diary1-0/diary1/line-0-2"],
  "reason": "author decision; not a machine judgement"
}
```

Allowed actions: `select`, `order`, `strike`, `keep`, `fold-in`, `stop`. An `order` step records
either an explicit sequence or `{ "chance": "seed", "seed": 17 }`. The author chooses chance or rule
per poem; the tool records which was used and never chooses on its own.

### Combination atom

Use the shared shape (see `docs/contracts/source-regions.md` §7):

```json
{
  "atom_id": "vf:atom:p001/p001-diary1-0/diary1/combination/cut-synthetic-1",
  "unit": "combination",
  "combination": {
    "operation": "cut",
    "input_atom_ids": ["…/line-0-0", "…/line-0-1"],
    "operator": "author",
    "rule": "reorder source lines, then keep or strike; author decides each step",
    "seed": null,
    "text_ref": null
  },
  "credit": { "origin_kind": "author", "credit_required": false, "credit_style": null }
}
```

This exact atom is in the synthetic fixture
`docs/pilots/t08-p001/fixtures/synthetic-combinations.source-regions.json`. It is a structural
placeholder; it is not a cut-up poem.

### New version

The studio integrator owns the version record. T08 only requires that the new version:

- has its own `version_id` and does not overwrite the source version;
- points at the combination atoms and their input atoms;
- keeps the source `line_id`s in `lineage.source_line_ids`;
- keeps borrowed-line credit fields;
- records the method (`method:cut-v1` or the studio's equivalent) with status and limits;
- is re-checked for the target scope before it is shown outside the private preview.

## Eligibility invariants (must be tested)

1. A Cut over `withheld` material is refused in every scope.
2. A private Cut over Reserve is allowed, with `inherited_pool: reserve`; a public Cut of the same
   material is refused.
3. A borrowed input with no `credit_style` is refused publicly.
4. A combination with a missing input or a lineage cycle is invalid.
5. A public Cut requires Series pool, whitelist membership and a clearance digest covering the new
   manifest. The old manifest's clearance does not carry over.
6. Open source uncertainties remain warnings; they are not silently resolved by cutting.
7. No atom in the new version carries text; `text_ref` stays separate.

The executable positive/negative controls are in `tests/test_source_regions.py`
(`combination`, `borrowed`, `reserve`, `shared scan`, `misread`, `cycle`).

## Open decisions (author)

- Chance versus rule per poem, and whether the seed is published (issue #54).
- Which revised, struck or inserted atoms survive into the version stack; whether struck text is
  shown as history or omitted (issues #32, #54).
- Borrowed-line credit style (plan open item 6; issue #55).
- Whether version history is public (issue #54).
- Participation: whether reader cuts count toward the 100 or sit around it (plan open item 3).
- When to stop using the method for a poem (issue #54).
- Whether a corpus-only Markov generator is allowed under the no-AI-text rule — **unresolved; do not
  build** (issues #55, #56).

## Integration

The Cut UI is staged through the studio integrator. T08 provides the atom shape, eligibility and
tests; it does not edit `studio/` or add a tab. Any UI must keep controls hidden until requested
(standing author rule) and must not display technical provenance text in the work surface.
