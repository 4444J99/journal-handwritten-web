# Owner lane evidence (`alive-prototype`)

2026-11-05. Read-only inspection and a headless run of the owner's prototype. T08 did **not** edit,
re-run or replace the owner lane.

## Inputs

| Item | Value |
|---|---|
| Local owner worktree | `/Volumes/Archive4T/Projects/journal-handwritten-web--alive-proto` |
| Branch / HEAD | `alive-prototype` / `eece4f56ffaae81500aaf94fd18852b2038e06d6` |
| Upstream relation | 5 commits ahead of `origin/alive-prototype`; same commit as `origin/alive-prototype-wip-final` |
| PR #102 head | `2664d10` (older than the local lane; the local lane is the evidence used here) |
| Atoms artifact | `proto/alive/atoms-p001.json`, sha256 `ed379ac4ccee98d06d392149e99299d8fd8d961d19e7c169513fcf45572ffca6` |
| Segmenter | `proto/alive/segment.py`, `build_atoms.py` (owner code, reused, not reimplemented) |
| Test hooks | `proto/alive/alive.js`, `window.__alive` |

Uncommitted owner changes were not touched. T08's worktree is a separate branch from `origin/main`.

## What the pilot reused

- 6 stanzas, 22 line boxes, 22 seam polygons, 86 word boxes, 306 glyph boxes, 20 marks.
- The owner's centered-line-length layout rule (building width = widest line; floors centered on the
  building axis), recorded as data in the pilot manifest's `structure` block.
- The owner's review states: line 13 crop withdrawn, word alignment in-sample only, glyphs are ink
  components rather than letters.

## What the pilot did not copy

- No `text` field from the owner atoms reaches the manifest. A recursive key check rejects
  `text`/`transcript`/`poem_text`/`line_text`/`word_text`.
- No owner code is vendored. The pilot references the artifact by path, commit and hash.
- No segmentation was re-run; the manifest records `reused_not_reimplemented: true`.

## Runtime reproduction

`node tools/t08_reproduce_alive.mjs` starts the owner's `serve.mjs` on `127.0.0.1` with a free port,
opens the prototype in headless Chrome through `tools/cdp_client.mjs`, freezes the reading animation
at several times and records the test hooks. Raw output:
`evidence/alive-runtime.json`.

Observed (Chrome/156 headless, 756×469, 2026-11-06 UTC):

| Check | Result |
|---|---|
| page ready | 214 ms |
| city | `p001`, no failed pieces |
| `atlasLeak()` | 22 lines, **0 outside pixels total**, all 22 have a region |
| `sourcesUsed()` | all 22 `diary1-<block>-<line>` ids, 0 unknown |
| `lineRegions()` | 22, all with polygons |
| `regionsRead()` | 22 rectangles |
| console/exceptions | none |

This reproduces the owner's claim that the seam partition owns every ink pixel and that line-level
crops do not leak outside their regions. It does not prove that a crossing stroke is assigned to the
right line; the owner's own note says the seam cuts a crossing stroke at the cheapest seam, and line
13 is withdrawn for exactly that reason.

## Limits carried into T08

- One page, 22 lines, in-sample parameters; no held-out page.
- Word alignment equals token count on 18 of 22 lines; one of those is withdrawn by eye review.
- Glyph boxes are component groups; whole-line counts match letters on 4 of 22 lines.
- Line boxes overlap; only seam polygons are disjoint.
- Block 2 in `site/data/j.json` is missing one author line box; the seam partition restores 4 lines
  where the author boxes give 3. The manifest records `missing-in-site-data` rather than repairing it
  silently.
- The prototype is private and local-only; it is not a product surface and was not modified.

## Attribution

The segmentation, word/glyph grouping, atlas construction and architecture renderer are the owner's
work on the `alive-prototype` lane (PR #102 and its `alive-prototype-wip-final` branch). T08's
contribution is the shared contract, the pilot normalisation, the eligibility engine, the tests and
this evidence record.
