# 02 · Research: forward and backward concatenative voice banks

| | |
|---|---|
| Chat | https://claude.ai/chat/2f242443-6911-47d2-a361-dbb83d08ad18 |
| Exchange | 02 of 3 · 2026-10-27 |
| Issue | #23 |

## Asked
Research first. He wants both forward and backward banks, because he will replicate the method in other projects.

## Answered / produced
- Launched an extended research task (method-level brief: diphone vs unit selection, tools and licences, script design, forced alignment, joins/PSOLA, browser feasibility, Red Room technique).
- Research report artifact `compass_artifact_wf-772991b2-c95b-5140-bc4d-e8a8d5e7507c_text/markdown` (version `01a1802c-78b3-7569-83f6-1fc47099cabd`). Covered: sourced account of the Red Room method; three backward modes (mirror, software Red Room, performed); a self-written browser engine (CMUdict-based lexicon, smoothed joins, TD-PSOLA), estimated 4–6 MB; tool licences and maintenance, flagging eSpeak NG (GPL-3.0) and non-commercial voice-cloning models; a reusable bank package layout; a plan starting with a one-hour, 50-unit pilot.
- Caveats stated: recording-time and size figures are Festvox-based estimates; licence and version details to be re-checked at build time.

## Author decisions
- Build both forward and backward banks.
- The method is to be reusable in other projects.

## Plan
- **Claude**, done: research report delivered.
- **Claude suggestion**, open: re-check licence and version details before the build starts.
