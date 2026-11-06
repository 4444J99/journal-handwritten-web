# Local agent session: T08 shared source-region model and private pilot

| | |
|---|---|
| Session | local agent session (OpenCode, model Big Pickle), no claude.ai chat URL; task T08 |
| Last activity | 2026-11-05 (America/New_York) |
| Repository | `4444J99/journal-handwritten-web` |
| Branch / worktree | `t08/source-regions-pilot-2026-11-05` in `journal-handwritten-web--t08`, from `origin/main` at `038d01f` |
| Basis of this record | this session's own tool output and the files it wrote, read 2026-11-05; no unseen context packet is cited |
| Status | Pilot, contract, tests and evidence done; draft PR/hand-off only. Nothing merged, deployed, published or closed. |

## Produced

- **`tools/source_regions.py`** — shared contract builder, validator, lineage walker and eligibility
  engine. `verify` checks ids, regions, methods, assets, lineage closure, counts, integrity and the
  no-text rule; `check` evaluates `private-local`, `author-cut-private`, `public-release` and
  `cipher-public` against an external visibility policy. Exit codes: 0 allowed, 3 refused, 2 bad
  input.
- **`docs/contracts/source-regions.md`** — provisional shared contract: identity, regions, methods,
  lineage, reading versus deliberate misread, borrowed-line credit, combinations, visibility,
  T02/T03/T04/T05/studio interfaces, limits and privacy.
- **`docs/schemas/source-region-v1.schema.json` and `visibility-policy-v1.schema.json`** — readable
  schema companions to the executable validator.
- **`docs/pilots/t08-p001/`** — one private pilot: `p001` / `p001-diary1-0` / page `diary1`;
  441 atoms (1 poem, 6 stanzas, 22 lines, 86 words, 306 glyphs, 20 marks), 3 open uncertainties,
  centered line-length structure (`building_width_px = 1088`). The manifest has no poem text.
  Includes the derived (non-author) policy, generated check reports, synthetic fixtures, owner-lane
  evidence and a per-issue decision map.
- **`tests/test_source_regions.py`** — 30 tests: pilot validation, text injection, integrity,
  undeclared methods, closure/cycles, missing author box, withdrawn line 13, derived private/public
  results, a full-clearance positive control, Reserve inheritance, withheld assets/pages, version
  exclusions, scope-aware strike-through vetoes, shared scans, borrowed-line credit, deliberate
  misread, combination closure and CLI exit codes.
- **`tools/build_t08_combination_fixture.py`** — deterministic synthetic Cut/cipher/borrowed/misread
  fixture, no text.
- **`tools/t08_reproduce_alive.mjs`** — read-only headless reproduction of the owner lane. Result:
  page ready, `atlasLeak()` 0 outside pixels across 22 lines, all 22 `diary1-<block>-<line>` ids
  used, 22 polygons, no console errors. Raw JSON in `docs/pilots/t08-p001/evidence/`.
- **Follow-on contracts** — `docs/contracts/cut-workflow.md` and
  `docs/contracts/key-sheet-cipher.md`, both author-operated, both without author input, both
  staged through the studio integrator.
- **`docs/pilots/t08-p001/decision-map.md`** — author decisions, derived defaults, proposals,
  tested implementation, residual questions and explicitly-not-built items for #32 and #52–#56.

## Author decisions (stated by him)

No new author decision was made in this session. Existing recorded decisions and direction used
here, with their sources:

- No AI-written creative or interpretive text in any presentation; creative writing is the author's
  (`docs/plan.md`, standing rules).
- Controls hidden until requested; work alone on screen (`docs/plan.md`, standing rules).
- 100 full poems, every edit kept as a version; participation wanted in some form; later phase
  roots/glyphs (`docs/plan.md`, Decided).
- The centered line-length architecture/cityscape direction, multiple units, zoom, hidden selector
  and scan-derived animation (`docs/chats/2026-11-05-local-session-finish-and-launch.md`).

These are direction, not a settlement of crop, font, stroke, chance, credit, hint or pool choices.

## Derived defaults (not author decisions)

- `p001` pool `unassigned`; empty public whitelist; no clearance; no shared-scan resolution; no
  strike-through veto list and no version exclusion in the real policy. Each is labelled in
  `visibility-policy.json`.
- Public release is therefore refused, correctly. `reserve` is a synthetic fixture only.

## Hand-offs and blockers

- **T02** — no completed source/deposit/stable-ID contract or workspace was located. Atom ids reuse
  the existing `site/data/j.json` ids provisionally; the missing hand-off is recorded in the
  contract. The context packet `2026-10-16-v1.1` / `-r2` was inaccessible and is not cited.
- **T03** — draft PR #119 at `8d16284` is evidence, not authority; the clearance contract is not
  merged and no author clearance exists.
- **T04 / T05** — the reader and notes/provenance interfaces are described; neither is integrated.
- **Studio integrator** — Cut and Key Sheet UI are contracts only; no `studio/` edit.
- **Author input missing** — Cut sentence/pages, cipher plaintext/key sheet/source pages,
  strike-through veto list, lock/hint/solver-credit rules, Series/Reserve decisions.

## Plan / next steps

- Review the draft PR; merge only on the owner's decision.
- Get T02's identifier/deposit contract or confirm the provisional ids.
- Merge or replace T03's clearance contract; then an author clearance can bind a manifest digest.
- Author rulings: chance vs rule; struck/inserted atom handling; borrowed-line credit style; puzzle
  locks/hints/solver credit; participation; journal-vocabulary constraint; poem 100 from 1–99
  (`decision-map.md`).
- Studio integrator: stage Cut and Key Sheet against the contracts, keeping controls hidden.
- T04/T05: consume the eligibility report and `text_ref` rather than re-deriving visibility.
- Do not build Markov/n-gram text, sensors, location/weather, reconstructed strokes or an automatic
  misread generator; all remain unresolved.

## Status

Pilot, contract, fixtures, tests and runtime evidence are complete in the isolated worktree.
Nothing is merged, deployed, published, posted, spent or closed. The public path is refused by the
derived policy, which is the correct result for an unassigned piece with no clearance.
