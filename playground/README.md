# playground/ — private companion to Studio, Staging and Live

Technical notes. The playground is a read-only web page that shows everything the
project holds in one place: all 123 pages, every piece and version with its scans and
line readings, every design board from the claude.ai design canvases, the prototypes,
the research reports and PDFs, every chat record with its exchanges, every technical
record, the production media kits and the release packet.

It changes nothing. Decisions, reviews and publishing stay in the Studio.

## Where it sits

```
Playground  (private, beside Studio)   reads the archive
Studio      versforms-studio.pages.dev  private, Cloudflare Access
Staging     versforms-staging.pages.dev public URL, noindex — a rehearsal of Live
Live        versforms.pages.dev         public, noindex — posted poems only
```

Staging is not a home for the playground: it binds only the `versforms-staging` bucket
and is meant to hold exactly what Live will hold. The playground carries every draft
and Reserve candidate, so it belongs on the Studio side.

## Build

    python3 playground/build.py            # -> playground/dist/ (git-ignored)

Inputs: `studio/data/review.json`, `site/data/j.json`, `studio/img/thumbs`,
`site/img/i`, `site/img/s`, `claude/`, `docs/`, `production/exports/`,
`release/packets/2026-11-05-t03-current/`, `release/public.json`, and in this folder
`sources.json` (deployments and claude.ai artifacts, hand-kept), `designs/` (board
renders) and `snapshots/` (copies of prototype artifacts).

Output: `index.html` (with document skeleton, for a static host), `artifact.html`
(same page without skeleton, for claude.ai), `data/core.json`, `data/docs.json`, and
the images, PDFs, media and snapshots it references. About 356 files, 33 MB.

## Design boards

`designs/<canvas>/*.jpg` are still renders of each board of the four design canvases
(menu five takes, edge objects storyboard, icon matrix, forms_verse mockups), made on
2026-11-07 by loading each board's HTML in headless Chrome at its canvas size and
saving a JPEG at most 1400 px wide. `designs/boards.json` keeps each board's title and
size. One board (`forms-verse-mockups/A4-Grid`) uses the canvas runtime's template
loop and renders only its header. When a canvas changes, re-read its `project/*.dc.html`
files and re-render.

## Serving it

- **claude.ai**: published as a private artifact ("versforms Playground") from
  `dist/artifact.html` in two batches (the host takes at most 255 files per publish).
- **Cloudflare, behind Access**: not wired yet. The intended route is a `/playground/`
  folder inside the studio's Pages output, so the existing Access policy covers it. That
  needs a step in `studio-cf/build_dist.py` that copies `playground/dist/` into
  `dist/playground/` and an owner redeploy. Do not create a separate Pages project for it
  unless an Access policy is attached first.

## Rules

- Private. Never copy `dist/` or any part of it to `4444J99/versforms`, Staging or Live.
- No creative or interpretive text is written into the page. Labels and descriptions are
  technical; poem text appears only as transcribed.
