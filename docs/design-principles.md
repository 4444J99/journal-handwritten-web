# Design principles for every versforms site

Technical notes. These apply to every site the project runs: Live (versforms.pages.dev),
Staging (versforms-staging.pages.dev), the Studio (versforms-studio.pages.dev) and the
Playground (`/playground/` inside the Studio). Recorded 2026-11-07, after the author asked
that all sites follow the same design principles. The values below are read from the
existing pages; nothing here is a new style.

## Two kinds of page, one family

| Kind | Sites | Rule |
|---|---|---|
| Presentation | Live, Staging (the reader, `site/index.html`) | The work alone on screen. Menus and other text stay hidden until tapped. No AI-written creative or interpretive text. |
| Workbench | Studio, Playground | Built for the author to operate. Labels and technical text are allowed; still no AI-written creative or interpretive text about the poems. |

Both kinds share one material: paper, ink and a single warm accent. A workbench never
introduces a colour family the reader does not have.

## Colour

Warm paper neutrals and near-black ink, light and dark, plus one accent.

| Role | Reader (`site/index.html`) | Studio and Playground (`studio/index.html`) |
|---|---|---|
| Ground | `--desk` #e6e0d2 / #121110 | `--bg` #f5f3ed / #141619 |
| Sheet | `--sheet` #f7f4ec / #1c1a17 | `--surface` #fffdf8 / #1b1e22 |
| Ink | `--ink` #2b2a27 / #e7dfcd | `--ink` #1d2129 / #e6e2d8 |
| Secondary ink | `--ink-2` #7a7262 / #9d968a | `--muted` #666b74 / #a2a5ab |
| Accent | `--amber` #b67f14 / #e0a526 | `--margin` #c0503a / #d9735e (margin red) |
| Insertions | `--ink-ins` #3d5a94 / #a9bce6 | — |

- No blue as an accent. Blue appears only where the manuscript has it (the reader's
  insertion ink) and as the browser focus ring.
- Every colour is a token with a light and a dark value; both themes follow the system
  setting and the explicit toggle.
- Semantic green (`--ok`) and amber (`--warn`) are for state only (reviewed, needs attention).

## Type

- Reader: the author's handwriting font (Etceter4 Diary in private builds, renamed
  `ajp-scribbles` in public ones) for the work; a standard face only on request.
- Workbench: Source Serif 4 for reading text and headings, IBM Plex Mono for labels, ids and
  dates, the system sans for controls. No other families.
- Headings are set in serif weight 600 at modest sizes; no display faces.

## Layout and behaviour

- Rules and hairlines (`--rule`) separate things; cards are for objects you open, not for
  every block.
- Ids, page numbers and dates sit in mono, small, in secondary ink.
- Every page works at phone width (390 px) and on desktop, in both themes.
- A link that leaves the project's own sites opens in a new tab. Nothing links to claude.ai:
  every claude.ai artifact has a native copy in the Playground.

## Open differences (the author's call)

- The reader's ground is a deeper paper (#e6e0d2) than the Studio's (#f5f3ed), and their
  accents differ (amber vs margin red). Aligning them means editing one of the two pages; neither
  has been changed.
