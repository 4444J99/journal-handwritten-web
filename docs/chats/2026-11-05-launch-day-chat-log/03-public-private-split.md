# 03 · Split public and private repos

| | |
|---|---|
| Chat | https://claude.ai/code/session_015ajDsmCvzDKanHQh7r5as2 (this session) |
| Exchange | 03 of 11 · 2026-11-05 11:23 |
| Issue | #76 |

## Asked
The repo should be split into public and private parts in separate repos.

## Answered / produced
- Copied merged-piece v4 into `site/` (2744d7a).
- `tools/build_public.py` + `release/public.json` (1a6f8bc): exports only released pieces; blank page when none.
- Created public repo `4444J99/versforms` (browser, after his GitHub sign-in) and pushed the blank site.

## Author decisions
- Accepted creating `versforms` (said "cont" after signing in).

## Plan
- **author**, open: Tag pushes v2026.10.27 / v2026.11.05 refused by the session proxy — push from a local clone
- **author**, open: Check whether etceter4's `img/photos/diary/` scans are public; make private or remove if the split should hold
- **author**, open: Review the 14 GitHub Apps connected to `versforms` by the repo-creation default
