# Handwritten journal: plan and state

Working document for the journal-handwritten-web project. Last updated 2026-10-27.

> Repository copy of the claude.ai Project doc `claude/plan.md` as of 2026-10-27. The Project doc is the working copy; this file is versioned here so each revision of the plan is kept.

## Source
- 123 scanned journal pages, c. 2014–2015, from github.com/4444J99/etceter4 (commit dfcbf0f, `img/photos/diary/`); 63 two-page spreads scanned September 2015 (`diary_originals.zip`).
- The published page crops cut off writing on 8 pages (37, 37a, 43, 48, 53a, 59, 59a, 60a). That text was recovered from the 2015 spreads.
- `diary6` in the zip duplicates the 8/8a spread; `diary25`/`25a` are a partly covered second scan of `26a`. No text is missing.

## What exists
| Thing | State | Where |
|---|---|---|
| Transcription | All 123 pages + recovered spread text; machine transcription, **not yet verified by the author**; 306 uncertain-reading notes | `archive/data/journal.json`, `transcripts/` |
| Copied reading notes | Recorded by source and opening words only (Lowry, Homer, Emerson, Bryant, Frost, Robinson, Bradstreet, Aeschylus, Shelley, Bowie, Manson, Talking Heads, etc.) | same |
| Piece catalog | 126 pieces: 54 complete poems, 4 complete songs, 42 drafts/fragments, 7 prose/letters, 19 note pieces | `archive/data/pieces.json` |
| Archive bundle | Web images, plain/markdown text, manifest with SHA-256 of originals | `archive/` |
| Handwriting font | Etceter4 Diary (OTF/WOFF2); weak: X, digits, Q Z V K G ! ; " ( ) & | `font/` |
| Merged piece | Canvas (12 combos, fresh layouts each visit) + book side (Journal, Study, Revisions, Hand↔Font) + version stacks (17 pieces with several drafts) | artifact `1Pcbgrvp7BqfmcYhzZLEss`; `app/`, `app_build/` |
| Review studio | Line-by-line verification, decisions, new-version photo inbox, **Release tab (v2, 2026-10-27)**; saves to the page's database | artifact `MVognnZQrtRQ6QCMaF7341`; `review/`, `review_build/` |
| Font fill-in sheet | 2-page template (Letter/A4) + `ingest_fillin.py`; trial builds go to `font/fillin/test/out/` | `font/fillin/` |
| Business-model research | Report comparing all monetization routes (2026-10-27) | research report in the chat of that date |
| Repository | Private `4444J99/journal-handwritten-web` (working name), seeded 2026-10-27 from both artifacts: `site/` (merged piece, deployable), `studio/`, `tools/check.py`, checksums, CI + manual Pages workflow. Source of record from here on | github.com/4444J99/journal-handwritten-web |
| Earlier prototypes | Reader (`9hrwYckEYpMQFqkbBT4eX4`), canvas test (`1ppNwGfhEi1qMmUWhpKPXA`), research report (`EzChFp1LM3f5jp4ZitWFFF`) | superseded by the merged piece |

Note (2026-10-27): the repository now holds the published outputs. The build folders above (`archive/`, `app_build/`, `review_build/`, `font/`, `release/`) lived in earlier cloud sessions. Their current location on the author's machine is not yet confirmed; the two artifacts hold the published data.

## Standing rules (author)
- No AI-written creative or interpretive text visible in any presentation; creative writing is his. Technical writing may be AI-generated.
- Presentation interfaces: the work alone on screen; menus and other text hidden until revealed on tap.
- This work is **not ETCETER4** (that is his music). It gets its own new identity and social presence, mentioned from his personal profile.

## Decided
- Goal: **100 full poems**, numbered n/100. Journal poems are edited and new poems written; every edit is kept as a version behind the newest on the canvas.
- Participation by others is wanted in some form.
- Free arrangements (scatter, by poem) are new every time; the spiral is notebook order.
- Later phase: break the language down to roots and glyphs, using his linguistics repos (e.g. LingFrame).
- Leaning: **one poem per week** (each needs edits, response end note, footnotes, endnotes, citations, academic note, social content).

## Business model (from the 2026-10-27 research; recommendations, not decisions)
- Post the n/100 series free to build the audience. Keep the interactive web piece free (e-lit prizes reward open work).
- Hold a **Reserve** of 15–30 strongest poems that never appear online in any form, for journals that count any online appearance (including paywalls, drafts, fragments, scans) as published. *Rattle* accepts self-posted work, so posted poems can still go there.
- Income: membership for the version and notes layers (~$5/mo) plus a live writing-circle tier; small numbered print editions per poem; Kickstarter for the collected and facsimile editions after poem 100.
- Font: keep exclusive during the series; license later (letterforms are not copyrightable in the US, font software is).
- Avoid: NFTs as a core model, paywalling the core work, selling the original notebook, self-publishing the full collection before trying contests with a different manuscript.
- Two meanings of "published": copyright (display-only posts usually unpublished; sold copies/downloads published) vs journals (any online appearance).

## Open (author's call)
1. **Name** of the new identity. Blocks handles, domain and the site's home (which moves off etceter4 to the new domain).
2. Numbering fixed in advance vs assigned as each poem posts.
3. Participation: counts toward the 100 vs sits around it (research suggests a separate layer under a contributor license).
4. "Nothing shines quite as brightly": final version or drafts as layers.
5. Possible pairs: "why DO" (61a) / "In JUST" (62); "I can only stand myself in" (56a) / "Different day. Different mirror." (57).
6. Lines that may echo other sources: "She was / A Beauty / In A Cage" (37), "distracted prophet" (53a), "are we: Fated / Faithful / Fatal?" (60a), red-carpet lines (59), diary46 lines.
7. Public/private for flagged pages (list in `archive/MANIFEST.md`).
8. Which pieces go to Series / Reserve / Archive.
9. First posting date.

Items 2–9 are answerable in the review studio (Decisions and Release tabs).

## Release tab (review studio, v2)
Sections, all saved to the studio database:
- **Sort**: assign each piece (journal items and "New poem" uploads) to Series, Reserve or Archive. Warns when a Reserve piece has a logged appearance.
- **Calendar**: Series queue, one per week from a chosen first-post date; reorder; per-poem prep checklist (edits, response end note, footnotes, endnotes, citations, academic note, social post); gates for verified, GRUW filed, prep complete; Mark posted (asks for a second tap if not ready). Number shown per the numbering decision.
- **Copyright**: GRUW batches of up to 10 Series pieces; draft → filed (date, case number) → registered (reg. number, effective date); shows the `make_deposit.py` command for the batch.
- **Exposure**: log of every place any version appeared (social, own site, member layer, recording, sold, download, journal, anthology); flags types that count as publication for copyright.
- **Submissions**: journal/contest submissions per piece with sent/accepted/declined/withdrawn; flags pieces still pending elsewhere after an acceptance.

Database shape: `release/{pieceKey}` = {pool, order, num, prep{}, exposures[], subs[], at}; `batches/{id}` = {items[], status, filed, sr, reg, eff, created, at}; `rconfig/settings` = {start}. pieceKey is the item id (`p001`…) or the version id for a new poem.

## Waiting on the author (2026-10-27)
- Review in the studio (start with the 58 complete pieces) and the Decisions tab.
- Release tab → Sort: pick Series / Reserve / Archive; choose a first-post date.
- Name candidates (then handle/domain availability checks).
- Fill in and photograph the font sheet.
- Real-iPhone test of the merged piece.
- Decide whether the site goes public (Pages sites are public even from a private repo; putting all poems online conflicts with the Reserve).
- Check why Actions won't start runners on the private repo (billing/minutes setting).
- Confirm where the local build folders live (or connect that folder) so the rebuild scripts can run.

## New handwritten versions (technical)
Photo → `app_build/ingest_version.py <photo> --piece <id|new>` (straighten, clean, line boxes; staged as needs-transcription) → transcription → `--text-file` → rebuild. The newest version goes on top of the piece's stack; a decided final version overrides.

## Copyright prep (informational, not legal advice; verify before filing)
- Group registration for unpublished works (GRUW): up to 10 unpublished works, same author(s) as claimant(s), same administrative class (poems are literary works), one file per work with file name matching its title, no collection title; fee $85. Sources: copyright.gov/gruw, Circular 24, copyright.gov/about/fees.html.
- Register each batch of 10 **before** posting. Log which version each filing covered; later revisions add new material.
- Group registration for two-dimensional artwork exists (2–20 *published* works, same calendar year, $85; available since 17 Feb 2026). Relevant only if the handwritten pages are registered as visual art after posting.
- Deposit generator: `release/copyright/make_deposit.py <up to 10 piece ids>` builds one PDF per poem (text + page scan) and a manifest; refuses unverified pieces unless overridden. The Release tab prints this command per batch.

## Rebuild order (technical)
1. Export the studio's `reviews`, `decisions`, `versions`, `release`, `batches`, `rconfig` collections → `review_build/apply_reviews.py` (backs up first; `--dry-run`) → transcripts and `archive/data/journal.json` updated.
2. Archive build → `review_build/build_data.py` + `assemble.py` (republish studio) and `app_build/build.py` → `app_build/assemble.py` → publish `app/index.html` to artifact `1Pcbgrvp7BqfmcYhzZLEss` (≤255 files per publish, ≤511 per version). The studio page source with the Release tab is version 2 of `MVognnZQrtRQ6QCMaF7341`; a rebuild must start from that page, not the older `review/index.html`.
