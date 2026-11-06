# T08 residual decision map — #32, #52–#56

2026-11-05. This file separates four things that are easy to blur:

- **Author decision** — stated by Anthony, with the place it is recorded.
- **Derived default** — a choice T08 had to make to run the pilot. It is **not** an author decision.
- **Proposal** — a Claude suggestion or research recommendation. It is not built and not approved.
- **Tested implementation** — code and checks that actually ran in this branch.

Anything not in the first column remains open. No issue is closed by this map.

## Cross-cutting decisions

| Topic | Status | What exists now | What is still needed |
|---|---|---|---|
| Chance vs rule | **Open** | `combination.rule` / `seed` records whichever the author used; the tool never chooses | Author ruling per poem (#54) |
| Revised / struck / inserted atoms | **Open** | Atoms and versions are separate; vetoes and exclusions can target a version or line | Whether struck text appears as history, is omitted, or counts as a new atom (#32, #54) |
| Borrowed-line credit | **Open** | Public output refuses a borrowed atom without `credit_style` | Author chooses the style and wording (plan open item 6; #55) |
| Puzzle locks / hints / solver credit | **Open** | None built; no hint, lock or credit surface exists | Author rules on locks, hints, auto-open and solver credit (#52, #53) |
| Participation | **Open** | No reader cut pool; Reserve exclusion is recorded as a requirement | Whether participation counts toward the 100 or sits around it (plan open item 3; #56) |
| Journal-vocabulary constraint | **Open** | Nothing enforces a vocabulary; combinations can use declared atoms only | Author decides whether new poems are limited to journal vocabulary; a counter is only a suggestion (#56) |
| Poem 100 from poems 1–99 | **Open** | No generator, no structural rule, no text | Author decision on whether to attempt it and by what method (#56) |
| Markov / n-gram text | **Open — not built** | Nothing generates language | Author ruling under the no-AI-text rule (#55, #56, #109) |
| Sensors, location, weather | **Open — not built** | Nothing reads sensors or context | Permission-free variation was a suggestion; no author decision (#32) |
| Reconstructed strokes | **Open — not built** | Regions and seam partitions only; no skeleton or stroke reconstruction | Owner decision; owner has withdrawn line 13 pending traced waypoints (#32, owner lane) |
| Scan crop vs font | **Open** | Pilot/owner lane uses scan crops; the handwriting font is never used there | Author decision about when, if ever, the font stands in for a crop (#32) |
| Publication authority | **Blocked** | Derived policy says no clearance; T03 draft PR #119 is evidence only | Merged T03 clearance contract and an author clearance naming the exact manifest digest |
| Identifier authority | **Provisional** | Existing `j.json` ids reused under `vf:atom:…` | Completed T02 source/deposit/stable-ID contract; none located |
| Reader integration | **Not started** | Eligibility report is available for T04 | T04 must consume the same policy result, not re-derive it |
| Notes/provenance integration | **Not started** | `text_ref`, lineage and method refs exist | T05 attachment rules for notes/endnotes |
| Cut UI / Key Sheet UI | **Not built** | Contracts and synthetic fixtures only | Studio integrator stages the UI; author supplies inputs |

## #32 — atomic units, context sensing, tap animations

**Author decisions already recorded**
- Later phase: break language down to roots and glyphs (plan, Decided).
- Participation is wanted in some form (form still open; plan, Decided).
- Controls stay hidden until requested; no AI-written creative text in the work (standing rules).
- The architecture/cityscape direction: centered line-length structure, multiple units, zoom,
  hidden selector, scan-derived animation (`docs/chats/2026-11-05-local-session-finish-and-launch.md`).

**Derived / implemented (tested)**
- Source-backed atoms with stable ids, regions, methods, lineage and credit.
- A line can carry a seam-partition polygon; boxes may overlap, polygons may not.
- The pilot manifest normalises 441 atoms from the owner lane and verifies with no poem text.
- Eligibility can refuse withheld/Reserve material; the owner prototype's `atlasLeak()` is reproduced
  in `evidence/` (see the pilot README).

**Proposals, not decisions**
- Permission-free variation tier (seed, time/season, touch, dwell, return visits).
- Concordance blooms from scan-crop sprite atlases.
- Reserve enforcement at build time.
- Real-iPhone motion/permission test.

**Residual questions from the issue**
1. Markov/n-gram status — open, not built.
2. Viewer context vs authored context — open.
3. Stroke reconstruction — open, not built.
4. Scan crop vs font — open.
5. Struck-through/inserted words as atoms — open (the contract can carry them; no rule yet).
6. Revised versions in blooms — open.
7. Participation tier — open.

**Explicitly not built:** Markov text, sensors, location/weather, reconstructed strokes, any
automatic interpretation.

## #52 — cipher research

**Author decisions already recorded**
- None of the report's eight open questions has an answer in the repository.

**Derived / implemented (tested)**
- `page:line:word` positions use the same atom coordinates as every other tool.
- A synthetic cipher combination atom exists and closes its lineage.
- `cipher-public` refuses Reserve/Archive/withheld/unassigned material; private key construction
  respects withheld assets and version exclusions.
- A Key Sheet contract is written at `docs/contracts/key-sheet-cipher.md`.

**Proposals, not decisions**
- Start with the Key Sheet and the book cipher (also a suggestion in the issue).
- Locks auto-open after a few weeks; no prizes, leaderboards or Zodiac imagery.

**Residual questions from the issue**
1. Lock behaviour and timing — open.
2. Key sheet source pages — **author supply missing**.
3. True-crime references — open.
4. Metameta reveal — open.
5. Clue style — open.
6. Solver credit and hints — open.
7. Enciphering published poems — open; publication does not imply permission.
8. Off-limits strike-throughs — **author veto list missing**.

**Explicitly not built:** plaintext, key sheet, clues, solutions, locks, leaderboards.

## #53 — incorporating the puzzle layer

**Author decisions already recorded**
- None. The issue asks for one test sentence and the page to crop glyphs from; neither was supplied.
- The private strike-through veto list was requested; none was supplied.

**Derived / implemented (tested)**
- The cipher can be represented as a derived combination with complete lineage.
- Public cipher output is refused without Series pool, whitelist, clearance and shared-scan
  resolution.
- A version excluded from `cipher-public` is refused even if allowed privately.

**Proposals, not decisions**
- Add "puzzle" to the Release tab's prep checklist.
- Fold-in/erasure/tap-to-source behaviours for the web piece.

**Residual**
- Supply the test sentence and source page(s) — author.
- Supply the veto list — author.
- Decide locks, hints, credit and checklist integration — author.
- Stage any UI through the studio integrator — not started.

**Explicitly not built:** puzzle UI, clue surface, lock timer, answer checking.

## #54 — cut-up research

**Author decisions already recorded**
- None of the four framing questions has a recorded answer.

**Derived / implemented (tested)**
- A Cut is represented as combination atoms over existing source atoms, with a replayable rule/seed
  record and no language model.
- Private Cut may inherit Reserve/Archive material; the report records the inherited pool and the
  tool never promotes it.
- Public output refuses a borrowed input without a credit style.
- Missing inputs and lineage cycles are contract errors.

**Proposals, not decisions**
- Any suggestion in the research report remains a proposal.

**Residual**
- Chance vs rule per poem.
- How borrowed lines are credited.
- Whether version history is published.
- When to stop using the method.
- Whether a corpus-only Markov generator is allowed — open, **not built**.

**Explicitly not built:** the Cut UI, a reader cut, any generator.

## #55 — incorporating cut-up methods

**Author decisions already recorded**
- No decision on the proposed studio tab, reader features or Markov question.

**Derived / implemented (tested)**
- Per-version method and line-level provenance exist in the contract.
- The Cut contract (`docs/contracts/cut-workflow.md`) records selection, steps, combination atoms,
  credit and the new-version boundary.
- The Release-tab warning about Series poems reusing Reserve lines is expressible as an eligibility
  refusal; the tab itself is not edited.

**Proposals, not decisions**
- Add a Cut tab (shuffle/strike/keep, no language model, saves a new version).
- Add a Release-tab warning.
- Fold-in view, erasure version type, tap-a-line-to-see-source-page, hidden until tapped.
- Add a credit-style choice to the Decisions tab.

**Residual**
- Studio integrator: stage any UI change.
- Author: credit style; whether the web views ship.
- Author: Markov ruling — **not built**.

**Explicitly not built:** studio tab, reader cut pool, web fold-in/erasure surface.

## #56 — structural cut-up ideas

**Author decisions already recorded**
- None on the three questions.

**Derived / implemented (tested)**
- Combinations can only reference declared atoms in the same manifest; lineage closes.
- A deliberate machine misread is a separate labelled state, refused publicly until an author rule
  is recorded.
- Reserve/Archive material is refused for public cipher output; a reader pool could reuse the same
  rule if it is ever built.

**Proposals, not decisions**
- Count the journal's vocabulary.
- Exclude Reserve poems from any reader-cut pool.
- Idea 2 (new poems limited to journal vocabulary) and idea 4 (poem 100 from poems 1–99).

**Residual**
- Journal-vocabulary constraint: yes/no, and what counts.
- Poem 100 from poems 1–99: yes/no, and by what method.
- Whether machine-misread uncertain readings count under the no-AI-text rule.
- Participation structure.
- Reader-cut Reserve exclusion if reader cuts are built.

**Explicitly not built:** poem-100 generator, vocabulary counter, reader cut, any machine-misread
generator.

## What this branch actually proves

- The shared contract validates; 441 pilot atoms close their lineage; no poem text is stored.
- The derived policy allows a private-local preview and refuses a public release for the recorded
  reasons (unassigned pool, no whitelist, no clearance).
- Synthetic controls prove refusals for Reserve, withheld assets/pages, excluded versions,
  strike-through vetoes, shared scans, borrowed lines without credit and deliberate misreads without
  a rule.
- The owner prototype's segmentation/atlas behaviour is reproducible on this machine (see the pilot
  README and `evidence/`).

It does **not** prove artistic fitness, publication clearance, ID ownership or any answer to the
open questions above.
