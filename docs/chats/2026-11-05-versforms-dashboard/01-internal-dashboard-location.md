# 01 · Location of the internal review dashboard

| | |
|---|---|
| Chat | https://claude.ai/chat/8956113b-5e3d-4219-8256-26c7236e8ae5 |
| Exchange | 01 of 4 · 2026-11-05 |
| Issue | #83 |

## Asked
Reported the public site live at https://versforms.pages.dev/ and asked where his dashboard with all the internal work is.

## Answered / produced
- Fetched the live site, read project memory and listed artifacts.
- The internal dashboard is the private "Journal Review" studio artifact (a5fc5ebb-3c06-4c0d-ae83-608e65cc8de6), unchanged by the launch.
- Advised keeping it off versforms.pages.dev: a Pages site is public, and the studio's saving depends on claude.ai artifact storage.
- Two options: (1) keep the artifact and update the Release tab for versforms; (2) port it to a private Cloudflare Pages project behind Cloudflare Access with D1 storage.

## Author decisions
- Reported the site live at versforms.pages.dev.

## Plan
- Update the Release tab so "Mark posted" defaults to versforms and the Exposure log records the site URL — **Claude suggestion**, **open** (folded into the Claude Code prompt in 03).
- Port the studio to a private Cloudflare project later — **Claude suggestion**, **open**.
