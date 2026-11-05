# 03 · Merged piece v4: all seven fixes implemented and published

| | |
|---|---|
| Chat | https://claude.ai/chat/f5bdc78e-c6ef-4838-9a47-420827d81c58 |
| Exchange | 03 of 3 · 2026-10-27 |
| Issue | #21 |

## Asked
"Proceed with all suggestions."

## Answered / produced
- Source build folders were not in the workspace, so Claude worked from the published `index.html` of artifact `1Pcbgrvp7BqfmcYhzZLEss`, downloading its data (`data/j.json`) and images for local testing.
- Headless-browser tests at laptop and phone sizes, light and dark; fixed a self-introduced font-fallback bug before publishing.
- Republished the artifact as version 4 (label "Review fixes: hidden bar, reading view"); only `index.html` changed.
- Changes: toolbar hidden until the pointer rests on its area, 34px higher, hides ~3 s after use and when a poem opens; Unfold-view dimming bug (cause of dark stretches) fixed; unready canvas areas drawn immediately, theme switch cross-fades; zoom capped at about one line, pages/lines upright when close; long poems open at reading size and scroll (wheel/drag/arrows), vertical swipe scrolls on long poems, versions via strip or `[` `]`; Esc or tap outside exits; version strip shows date or n/N.
- Corrections: dropped Spiral click not reproducible (buttons now act instantly, cause unconfirmed); 0:25 behaviour is by design.
- Updated Project doc `claude/plan.md` with the v4 change list and the rebuild warning.
- Follow-up message: local test server timed out; no effect on the published piece.

## Author decisions
- Accepted all seven suggested fixes.

## Plan
- Copy v4 `index.html` into the repository's `site/` (or port changes into the `app_build` generator) before any rebuild — **Claude suggestion**, **open**.
- Test v4 on a real iPhone — **author**, **open**.
- Confirm on device whether the dropped-click issue is gone — **author**, **open**.


_Update 2026-11-05 (launch-day chat): merged-piece v4 copied into `site/` (commit 2744d7a); public site split to `4444J99/versforms`, Cloudflare Pages link in progress._
