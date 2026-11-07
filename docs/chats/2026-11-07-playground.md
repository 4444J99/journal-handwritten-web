# Playground: everything in the project as one private web app

| | |
|---|---|
| Chat | claude.ai Project chat, 2026-11-07 (session https://claude.ai/code/session_015ajDshq2Y3afyt2Yr3sTCX) |
| Last activity | 2026-11-07 (America/New_York) |
| Repository | `4444J99/journal-handwritten-web` (branch `playground`) |
| Status | Served from the Studio at /playground behind Access (after merge and Cloudflare build); every claude.ai artifact kept natively. |

## Produced
- `playground/` — build script, page, hand-kept source list, design-board renders and the Minotaur Depths snapshot. See `playground/README.md`.
- 37 board renders from the four design canvases (menu five takes, edge objects storyboard, icon matrix, forms_verse mockups).
- Private claude.ai artifact "versforms Playground" (https://claude.ai/artifact/EBg2PqLFywvVnQfJz7Wuny), 356 files: Overview with the Studio > Staging > Live ladder, Works (every piece and version beside its scan), Pages, Designs, Research, Process (44 chat records, 86 exchanges, 69 records), Media, Release, and search across lines and records.
- Checked: `versforms-staging.pages.dev` loads without a login (2026-11-07).

- Later the same day: playground moved onto the Studio's tokens and fonts; `docs/design-principles.md` records the shared rules for all four sites; every claude.ai artifact copied in natively (reader, first reader, canvas test, Minotaur Depths, design boards, two exported documents, progress data, PDFs); `studio-cf/build_dist.py` builds it into `/playground/`.

## Author decisions
- Wants everything in the project (all versions, drafts, design variations, research reports) presented as an interactive web app, a companion to the live sites, possibly called "the playground".
- Named the current deployments as Studio > Staging > Live, and asked whether the playground fits into Staging or should be something else.
- Asked for all of the above to be completed (merge, Studio build step, redeploy).
- All the sites need to follow the same design principles.
- Wants the claude.ai artifacts natively part of the playground, with no links that bounce to a claude.ai URL.

## Plan / next steps
- **Claude suggestion**: the playground lives on the Studio side, not in Staging (Staging is a rehearsal of Live and is publicly reachable); source in this repository's `playground/`.
- **Claude suggestion**: serve it at `/playground/` inside the studio's Pages output so the existing Access policy covers it (needs a copy step in `studio-cf/build_dist.py` and an owner redeploy).
- Re-render the design boards when a canvas changes; add new claude.ai artifacts to `playground/sources.json`.

## Status
PR #140 merged; production Studio build via the Git-connected Pages project. Live and Staging untouched. The old claude.ai artifact copy is no longer updated.
Follow-up after merge: Codex flagged that `playground/build.py --out DIR` deleted any existing DIR. Fixed on `playground-out-guard`: only the default `playground/dist/` is cleared; any other non-empty directory is refused, as `studio-cf/build_dist.py` does.
Author, 2026-11-07: the GitHub billing lock will not change for a long time; run CI off GitHub billing. Done on `ci-on-cloudflare`: `studio-cf/build_cloudflare.py` runs `tools/check.py` before every Cloudflare Pages build (each push and PR, reported on GitHub). A failed check fails the build, and nothing is deployed. PR #141 (output guard) merged.
