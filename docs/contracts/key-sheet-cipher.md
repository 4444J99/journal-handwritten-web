# Follow-on contract: Key Sheet and page:line:word book cipher (T08 hand-off)

Status: **contract prepared, tool not built**. 2026-11-05. This is a hand-off to the studio
integrator (issue #52 / #53). It defines the key, the enciphering operation and the eligibility
rules. It contains no plaintext, no key sheet, no clue and no solution, because none has been
supplied by the author.

## Boundary

- **Author-supplied material only.** The plaintext sentence, the source pages, the key sheet and the
  hints come from the author. The tool may construct the index and show the result; it may not
  invent a message, a key or a clue.
- **Book cipher first.** The suggested first build is the Key Sheet plus a `page:line:word` book
  cipher (issue #52). Other mechanics in the research report are not settled.
- **No prizes, leaderboards or Zodiac imagery.** These were Claude suggestions in issue #53, not
  author decisions; none is implemented.
- **Private until cleared.** Enciphering a published poem is a new public use. It needs its own
  `cipher-public` eligibility check and clearance; publication of the poem does not imply permission
  to encipher it.
- **Locks/hints/credit unresolved.** Auto-opening locks after a few weeks, clue style, solver credit
  and hint policy are author decisions (issues #52, #53).

## Key model

A key sheet is an ordered mapping from symbols to source positions. Positions are the shared atom
coordinates, never copied text:

```json
{
  "key_id": "synthetic-key-fixture-not-a-real-key",
  "status": "synthetic-fixture-not-authored",
  "source_piece_id": "p001",
  "source_version_id": "p001-diary1-0",
  "alphabet": ["a", "b", "c"],
  "entries": [
    {
      "symbol": "a",
      "page_id": "diary1",
      "line_id": "diary1-0-0",
      "word_ordinal": 0,
      "atom_id": "vf:atom:p001/p001-diary1-0/diary1/line-0-0/word-0"
    }
  ]
}
```

Rules:

- Each entry points at a word/glyph atom that exists in the shared manifest.
- The key sheet may be printed and kept private; its public hints are a separate, author-supplied
  list.
- A key sheet may not use withheld material, a withheld version, or a line under a strike-through
  veto.
- The alphabet and ordering are author choices. Duplicate symbols are allowed only if the author
  records the disambiguation rule.

## Enciphering operation

```
plaintext (author-supplied, private)
  + key sheet (author-supplied, private)
  -> sequence of source atoms (one per symbol)
  -> cipher combination atoms (operation = cipher)
  -> cipher-public eligibility check
```

- The plaintext is never committed to this repository. It lives in the author's private store,
  referenced by `text_ref`; the manifest stores only the resulting atom ids.
- If a symbol has no key entry, the operation stops and reports the gap. It does not guess.
- The result is a `combination` atom with `operation: "cipher"` and the key entry's atom as its
  input. Its lineage carries the source `line_id`s and root assets.
- Reusing a word from a Reserve/Archive piece is refused for `cipher-public`, even when the key
  sheet is private.
- A cipher over an author's own Series poem still requires clearance for the exact manifest digest
  and a shared-scan resolution if the page is shared.

## Solver credit and hints (unresolved)

Before any public puzzle ships the author must decide:

- whether solvers are credited, in what style, and where (issue #52);
- hint style and timing, and whether locks auto-open (issues #52, #53);
- whether the ciphertext reuses a published poem or a private/Reserve page (issue #53);
- the veto list of private strike-throughs that must never be dug up (issue #53);
- whether "puzzle" joins the Release tab's prep checklist (issue #53, suggestion only).

None of these has a recorded author decision, so no hint text, lock timer, credit surface or
leaderboard exists in this contract.

## Synthetic fixture

`docs/pilots/t08-p001/fixtures/synthetic-combinations.source-regions.json` contains one cipher
combination:

```
vf:atom:p001/p001-diary1-0/diary1/combination/cipher-synthetic-1
  operation: cipher
  input: one word atom
  method: method:key-sheet-fixture-v1
```

It is labelled synthetic, has no plaintext and no solution, and exists only to exercise lineage and
eligibility. The private pilot policy allows it privately; a public cipher scope would refuse it
because the pilot piece is `unassigned` and not cleared.

## Eligibility invariants (must be tested)

1. `cipher-public` refuses `reserve`, `archive`, `withheld` and `unassigned` pools.
2. A withheld asset or withheld page is refused in every scope, including private key construction.
3. A version excluded from `cipher-public` cannot be used, even if it is allowed privately.
4. A strike-through veto that covers `cipher-public` removes the line from the key.
5. A public cipher needs a clearance digest covering the cipher manifest and, on a shared scan, every
   neighbour cleared or a page-level remedy.
6. A key entry whose atom is missing or whose lineage does not close is invalid.
7. No plaintext, clue or solution field is present in any committed manifest.

The engine-level controls for 1–6 are in `tests/test_source_regions.py`; the key-entry checks are
part of this hand-off and must be added with the studio implementation.

## Integration

The Key Sheet generator and any puzzle surface are staged through the studio integrator. T08
supplies the coordinate contract and eligibility; it does not add a tab, a lock, a hint or a public
page. Keep the work surface free of technical provenance text and hidden controls until requested.
