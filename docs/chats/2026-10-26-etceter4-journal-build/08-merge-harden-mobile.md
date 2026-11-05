# 08 · Merge canvas and reader; harden, smooth, fix mobile; fresh layouts

| | |
|---|---|
| Chat | https://claude.ai/chat/137af404-03bc-4316-909d-46953fd70931 |
| Exchange | 08 of 12 · 2026-10-25 |
| Issue | #12 |

## Asked
The author liked the canvas and asked to harden it, make it smoother, fix mobile controls, combine the earlier revisions/study versions as the other side of the coin, and make non-linear arrangements new every time. Later he wants to break the language down to roots and glyphs using his linguistics repos.

## Answered / produced
- Started a merge agent: canvas as non-linear side, reader (Journal, Revisions, Hand-to-Font) as linear side, anchored transition between them, Spiral as the hinge.
- Scatter/By poem get a fresh seed per visit and switch, reproducible via a hash token; Spiral stays fixed.
- Hardening brief: render on demand, spatial index, off-thread sprite cutting, LOD, memory caps, context-loss recovery, file budget; phone bottom bar and gesture fixes.
- Data kept structured (line and word positions) for a later roots/glyphs phase.

## Author decisions
- Likes the whole canvas direction.
- Harden it, make it run smoother, fix the mobile controls.
- Combine the earlier versions (revisions/study) as the other side of the coin.
- When not in linear order, arrangements must be new every time.
- Later: break the language down to roots and glyphs using his linguistics/language repos.

## Plan
- **Claude**, done: Merge, harden, fix mobile, fresh seeds
- **author**, open: Roots-and-glyphs phase with linguistics repos (e.g. LingFrame)
