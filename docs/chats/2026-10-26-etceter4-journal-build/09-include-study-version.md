# 09 · Fold in all three versions; publish merged piece

| | |
|---|---|
| Chat | https://claude.ai/chat/137af404-03bc-4316-909d-46953fd70931 |
| Exchange | 09 of 12 · 2026-10-25 |
| Issue | #13 |

## Asked
The author pointed out there were three versions and wants all three.

## Answered / produced
- Sent a scope addition to the merge agent: the first study view (scan beside transcription, linked lines, revisions/clean, spread toggle) as a third linear view, stripped of AI-written text.
- Published the merged piece privately (artifact `1Pcbgrvp7BqfmcYhzZLEss`): canvas first; book side with Journal, Study, Revisions, Hand-to-Font; long-press/book icon to open at a line, pinch closed to return; search on both sides.
- Measured: worst desktop frame stalls down from ~0.4 s to ~0.03 s; touch gestures passed on emulated iPhone and Pixel.
- Untested: a real iPhone; off-thread image work inside the live host. Arrangement switching was lab-measured 2026-11-24 (loop PR, issue #13): every spiral switch computed synchronously on the main thread before the fix; after it, all switches are worker-first with zero sync layouts. Real-iPhone confirmation of the switch fix is still untested (author).

## Author decisions
- All three versions go into the merged piece.

## Plan
- **Claude**, done: Include study view and publish merged piece
- **author**, open: Test the merged piece on a real iPhone
- **Claude**, done: Measure and fix arrangement-switch stutter on real phones — lab-measured and fixed 2026-11-24 (loop PR, issue #13): spiral routed through the layout worker, spiral pre-rolled, prefetch eager after first paint, worker failures now counted in `stats.workerFallbacks` instead of silently falling back. Real-iPhone confirmation remains the author's open item above.
