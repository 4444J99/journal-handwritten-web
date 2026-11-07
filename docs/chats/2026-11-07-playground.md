# Playground: everything in the project as one private web app

| | |
|---|---|
| Chat | claude.ai Project chat, 2026-11-07 (session https://claude.ai/code/session_015ajDshq2Y3afyt2Yr3sTCX) |
| Last activity | 2026-11-07 (America/New_York) |
| Repository | `4444J99/journal-handwritten-web` (branch `playground`) |
| Status | Built and published as a private claude.ai artifact; Cloudflare route behind Access not wired. |

## Produced
- `playground/` — build script, page, hand-kept source list, design-board renders and the Minotaur Depths snapshot. See `playground/README.md`.
- 37 board renders from the four design canvases (menu five takes, edge objects storyboard, icon matrix, forms_verse mockups).
- Private claude.ai artifact "versforms Playground" (https://claude.ai/artifact/EBg2PqLFywvVnQfJz7Wuny), 356 files: Overview with the Studio > Staging > Live ladder, Works (every piece and version beside its scan), Pages, Designs, Research, Process (44 chat records, 86 exchanges, 69 records), Media, Release, and search across lines and records.
- Checked: `versforms-staging.pages.dev` loads without a login (2026-11-07).

## Author decisions
- Wants everything in the project (all versions, drafts, design variations, research reports) presented as an interactive web app, a companion to the live sites, possibly called "the playground".
- Named the current deployments as Studio > Staging > Live, and asked whether the playground fits into Staging or should be something else.

## Plan / next steps
- **Claude suggestion**: the playground lives on the Studio side, not in Staging (Staging is a rehearsal of Live and is publicly reachable); source in this repository's `playground/`.
- **Claude suggestion**: serve it at `/playground/` inside the studio's Pages output so the existing Access policy covers it (needs a copy step in `studio-cf/build_dist.py` and an owner redeploy).
- Re-render the design boards when a canvas changes; add new claude.ai artifacts to `playground/sources.json`.

## Status
Private artifact live; PR open on `playground`. No public or Staging deployment touched.
