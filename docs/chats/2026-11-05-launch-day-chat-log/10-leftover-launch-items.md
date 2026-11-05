# 10 · Work the leftover launch items

| | |
|---|---|
| Chat | https://claude.ai/code/session_015ajDsmCvzDKanHQh7r5as2 (this session) |
| Exchange | 10 of 11 · 2026-11-05 |
| Issue | #87 |

## Asked
"proceed with all" — work every leftover item on the launch list.

## Answered / produced
- Tried to merge PR #73; the merge was blocked (needs the author's review). Not worked around.
- Tried again to push tags `v2026.11.05` and `v2026.10.27`; the session proxy drops tag pushes.
- Tried to attach `4444J99/etceter4` to check the diary scans; access was denied. Not checked.
- Found why Actions runs fail: GitHub reports a payment/spending-limit problem on the account.
- Listed the GitHub Apps installed on `4444J99/versforms` (only Cloudflare Workers and Pages is needed).
- Posted the findings and local tag commands as a follow-up comment on #76.

## Author decisions
- Proceed with all leftover launch items.

## Plan
- **author**, open: Review and merge PR #73.
- **author**, open: Fix the GitHub billing / spending limit so Actions can start.
- **author**, open: Decide which GitHub Apps to remove from `versforms`.
- **Claude**, open: Push the two tags from a local clone; check etceter4 visibility read-only (handed off in exchange 11).
