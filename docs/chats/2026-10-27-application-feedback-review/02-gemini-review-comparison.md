# 02 · Cross-check of Gemini's review and merged priority list

| | |
|---|---|
| Chat | https://claude.ai/chat/f5bdc78e-c6ef-4838-9a47-420827d81c58 |
| Exchange | 02 of 3 · 2026-10-27 |
| Issue | #20 |

## Asked
The author shared a review of the same recording from Gemini ("Well first here is feedback from Gemini") for comparison.

## Answered / produced
- Verified Gemini's claims against the recording by cropping the toolbar active-state dots at key timestamps.
- Confirmed from Gemini: a Spiral click apparently ignored during a camera move (~1:09); long poems open too small; hard to exit a focused poem (rejected its visible "Back" button as against the work-alone rule); loose draft versions shown; draft thumbnails indistinguishable.
- Disputed: no mode reset at 0:25 (overview vs. close-in mismatch instead); dim handwriting is a fade, not contrast; notched canvas is not only a theme-switch issue.
- Listed what Gemini missed (always-visible toolbar, strip over text, sideways jump, illegible dense scatter).
- Combined priority list: 1 auto-hiding, higher toolbar; 2 no dropped clicks during camera moves; 3 canvas fills on first draw/theme change; 4 reading view (reading size, scroll, no jump, strip clear, Esc/tap exit); 5 upright pages past a zoom threshold, capped zoom; 6 shorter fades, low-res first; 7 draft strip shows dates or n-of-n.

## Author decisions
None.

## Plan
- Implement priorities 1–7 in the merged piece — **Claude suggestion**, **done** (exchange 03).
- Decide final version vs. drafts-as-layers for loosely shown drafts (plan item 4) — **author**, **open**.
