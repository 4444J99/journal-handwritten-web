# 02 · Public/private repo split and private hosting

| | |
|---|---|
| Chat | https://claude.ai/chat/8956113b-5e3d-4219-8256-26c7236e8ae5 |
| Exchange | 02 of 4 · 2026-11-05 |
| Issue | #84 |

## Asked
Stated that the public and private repos are the public/private split.

## Answered / produced
- Confirmed: versforms (public) vs the private archive repo; studio source sits in the private repo's `studio/`.
- Warned that repo privacy does not carry over to a Pages site built from it.
- Outlined a private deployment: Pages project serving `studio/`, Cloudflare Access policy (author's email only, set in dashboard), D1 database and API, data migration from the artifact.

## Author decisions
- The public/private split is the two repositories (public `versforms`, private archive repo).

## Plan
- Do not connect the private repo to Pages until an Access policy is in place — **Claude suggestion**, **open**.
- Add the Cloudflare Access policy in the dashboard — **author**, **open**.
- Create D1, API, storage swap, data import (steps 3–4) — **Claude suggestion**, **open**.
