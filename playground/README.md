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
(same page without skeleton), `data/core.json`, `data/docs.json`, `reader/` (a copy of
`site/` without `_worker.js`: the merged piece, and the one store of full and mid-size scans
everything else points at), and the images, PDFs, media and snapshots it references.
About 870 files, 77 MB.

## claude.ai artifacts, kept natively

Nothing in the playground links to claude.ai. Each artifact has a copy here, listed in
`sources.json` with `open` (where it opens) and `origin` (where it came from, not shown):

| Artifact | Kept as |
|---|---|
| Journal, 2014–2015 (merged piece v4) | `reader/`, from `site/` |
| Journal Review | the Studio itself |
| First reader, canvas test, Minotaur Depths | `snapshots/<name>/` pages, run in the viewer; their own scan copies are replaced at build time by the shared ones (`SNAPSHOT_REWRITES` in `build.py`; same bytes, checked 2026-11-07) |
| Four design canvases | still renders in `designs/` |
| Control inventory, Publish implementation plan | Markdown exports in `snapshots/docs/`, shown under Research |
| Versforms progress | its six data files in `snapshots/versforms-progress/data/`, shown under Release |
| Mentor advisory, audio plan, state and gaps, voice banks | the PDFs in `claude/` |
| Keep the Page, Animate the Revision | the report `claude/Dynamic presentation of handwritten poetry.md` |

The first reader's embedded font is the private Etceter4 Diary build, as in `site/index.html`.

## Design boards

`designs/<canvas>/*.jpg` are still renders of each board of the four design canvases
(menu five takes, edge objects storyboard, icon matrix, forms_verse mockups), made on
2026-11-07 by loading each board's HTML in headless Chrome at its canvas size and
saving a JPEG at most 1400 px wide. `designs/boards.json` keeps each board's title and
size. One board (`forms-verse-mockups/A4-Grid`) uses the canvas runtime's template
loop and renders only its header. When a canvas changes, re-read its `project/*.dc.html`
files and re-render.

## Serving it

- **Cloudflare, behind Access** (the home): `studio-cf/build_dist.py` builds the playground
  into `dist/playground/`, so it is served at `versforms-studio.pages.dev/playground/` behind
  the Studio's Access login and its fail-closed middleware. It needs `Markdown` (pinned in
  `studio-cf/requirements-build.txt`).
- **claude.ai**: an earlier private artifact copy ("versforms Playground", 2026-11-07) is no
  longer updated; at 870 files the playground is past the artifact host's 511-file limit.

## Rules

- Private. Never copy `dist/` or any part of it to `4444J99/versforms`, Staging or Live.
- No creative or interpretive text is written into the page. Labels and descriptions are
  technical; poem text appears only as transcribed.
