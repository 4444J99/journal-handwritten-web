# 01 · UX review of a screen recording of the merged piece

| | |
|---|---|
| Chat | https://claude.ai/chat/f5bdc78e-c6ef-4838-9a47-420827d81c58 |
| Exchange | 01 of 3 · 2026-10-27 |
| Issue | #19 |

## Asked
The author uploaded an 85-second screen recording (2026-10-26) of himself using the merged piece and asked for a review of his interactions and suggestions for improvement.

## Answered / produced
- Extracted frames at 1 fps with ffmpeg, tiled contact sheets and cropped the toolbar; read `claude/plan.md`. Recording only, no code inspected.
- Bugs: canvas drawn as a notched block before filling (~0:44, ~1:09, after theme switch); a focused page left rotated 180° (~0:41).
- Rule conflict: toolbar visible almost the whole time, against the work-alone rule; too near the bottom edge (macOS Dock overlapped it); twelve unlabeled icons, faint active-state dots — suggested three groups.
- Transitions/zoom: 2–3 s near-black fades; zoom depth too deep with rotated close-ups; dense arrangements illegible at a distance.
- Reading view: long poem runs under the bars and the version strip; poem jumps sideways on open; version thumbnails tiny with no newest marker.
- Offered to fix in priority order; noted the open real-iPhone test.

## Author decisions
None.

## Plan
- Fix the two bugs, then auto-hiding toolbar, then reading view — **Claude suggestion**, **done** (v4, exchange 03).
- Test on a real iPhone — **author**, **open**.
