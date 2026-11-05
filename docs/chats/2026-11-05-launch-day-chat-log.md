# Launch day: log every chat to the repository

| | |
|---|---|
| Chat | (this chat — launch day) |
| Last activity | 2026-11-05 (America/New_York) |
| Repository | `4444J99/journal-handwritten-web` |
| Basis of this record | this session |
| Status | In progress — public repo live on GitHub; Cloudflare Pages link waiting on Cloudflare sign-in. |

## Produced
- This folder: one plan record per Project chat, plus `CLAUDE.md` asking every future session to add its own record.

## Author decisions (stated by him)
- Host on his Cloudflare account; the site should be live.
- Split into a public repo and this private repo.
- Live site carries posted poems only (chosen 2026-11-05).
- Public name / repo: `versforms`; connect Cloudflare by dashboard Git link.
- Today is launch day; every chat in the Project gets a plan and is logged in this repository.

## Plan / next steps
- Done: merged piece v4 into `site/` (commit 2744d7a); `tools/build_public.py` + `release/public.json` (empty) (commit 1a6f8bc); public repo `4444J99/versforms` created and seeded with the blank site.
- Next: Cloudflare Pages project `versforms` linked to `4444J99/versforms`, output dir `site`, no build command; then point the domain when chosen.
- To release a poem: add its id to `release/public.json`, run `tools/build_public.py ../versforms/site`, push `versforms`.
- Check: etceter4's `img/photos/diary/` scans appear publicly reachable; tags `v2026.10.27`/`v2026.11.05` could not be pushed from the session.
- Work the launch list in `README.md` of this folder.
