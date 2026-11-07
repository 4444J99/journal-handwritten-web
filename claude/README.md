# claude/ — the claude.ai Project's text documents

These are the documents from the claude.ai Project **journal-handwritten-web**, downloaded by the author on 2026-11-05 and committed here so they are versioned and not only on a disk. Technical and research writing; none of it is shown to readers of the site.

- `plan.md` is the **Project doc** itself (the working copy; the Project doc was last revised 2026-10-28). `docs/plan.md` is the versioned copy kept up to date in this repository; the original import differed by two lines (a header note, and the 2026-11-05 note about copying v4 into `site/`). Both copies now also carry the dated T06 identity/audience addendum, with relative links appropriate to each location. When the plan changes, update both (see `CLAUDE.md`).
- The twelve reports are the research outputs of the Project chats. The chat column below is derived from titles and topics (a suggestion, not a record) except where a chat record names the report. Per-chat records are in `docs/chats/`.
- The PDFs are the Project's other documents.

| File | Chat record |
|---|---|
| `Releasing the ETCETER4 Handwritten Journal_ Standards, Growth, Protection, Precedents and Innovation.md` | `2026-10-24-release-methods-and-standards` |
| `Dynamic presentation of handwritten poetry.md` | `2026-10-26-etceter4-journal-build` (named there) |
| `Annotation Devices in Literature and Adjacent Fields_ Precedents for a 100-Poem Annotated Series.md` | `2026-10-26-footnotes-and-endnotes` |
| `Business Models for a Numbered Handwritten-Poetry Series_ Audience, Income and Literary Credibility.md` | `2026-10-27-product-business-model` |
| `Faithful vs. Generative Image Processing for a Scanned Handwritten Journal_ 2026 Pipeline and Evidence Review.md` | `2026-10-27-image-upscaling-methods` |
| `Two Voices From One Throat_ Building Forward and Red Room Concatenative Voice Banks of Your Own Voice.md` | `2026-10-27-custom-synthetic-voice` |
| `Writing the World's Scripts Through 100 Poems_ Learning Roadmap, Rendering Modes and Rights Cautions.md` | `2026-10-28-learning-world-scripts` |
| `Making the Etceter4 Journal Alive_ Atom Graphs, Concordance Blooms and Authorship-Safe Generative Design.md` | `2026-10-28-generative-atomic-poetry` (likely); also the design input of `2026-11-05-local-session-finish-and-launch` |
| `Voice-Only Generative Sound for a Web Poetry Archive_ Precedents, Techniques, Browser Architecture and Recording Plan.md` | `2026-10-29-generative-audio-from-voice` |
| `The Cut-Up and Its Family_ Assembling New Writing From Existing Writing.md` | `2026-11-03-cut-up-technique-research` (named there) |
| `Locked Pages_ Ciphers, Codes and Puzzle Play for the Handwritten Poetry Journal.md` | `2026-11-03-cipher-puzzles-and-handwriting` |
| `SOP_ Using Meta Muse with Instagram for the n_100 Handwritten Poetry Series.md` | `2026-11-03-fear-of-unseen-posts` (named there) |
| `Audio implementation plan.pdf` | `2026-10-29-generative-audio-from-voice` |
| `Voice Banks Buildout Spec.pdf` | `2026-10-27-custom-synthetic-voice` |
| `vers.forms — Mentor Advisory.pdf` | `2026-11-05-project-advisory` |
| `fillin_sheet.pdf` | `2026-10-26-etceter4-journal-build` (named there) |
| `Journal project state, gaps and the weekly poem.pdf` | not matched to a record |

## What is not here, and where it is
The rest of the download (the two zip bundles of the published pages, the font source `Etceter4Diary-Regular.otf`, the mockups page, and the images) is on the archive volume, not in git, with an index and hashes:
`/Volumes/Archive4T/Archives/versforms/claude-project-artifacts-2026-11-05/` (`INDEX.md`, `SHA256SUMS`).
- Both zip bundles were compared byte for byte with `site/` and `studio/` here and add nothing the repository lacks.
- The font source stays out of git on purpose: its family name is "Etceter4 Diary", and public builds use the renamed `ajp-scribbles` (`tools/font_rename.py`).
- The download contains none of the build scripts the README's "Rebuild path" lists as missing.

## Rules
- Private repository only. Nothing here goes to the public repo `4444J99/versforms` (`tools/build_public.py` copies only released pieces).
- This work is not ETCETER4 (the author's music). Several file names carry the old name and are left as downloaded.
