# 02 · Project inventory, gap research and weekly per-poem workflow

| | |
|---|---|
| Chat | https://claude.ai/chat/6db7c92a-0f3c-4aea-a594-7225f9859941 |
| Exchange | 02 of 2 · 2026-10-27 |
| Issue | #31 |

## Asked
The author said he likes much of the feedback and Claude's sorting, and wants to expand the project. He proposed probably one poem per week, each needing edits, his written response as an endnote, footnotes, endnotes, citations, an academic layer, and social media content. He asked for an overview of everything done so far and research across all the project's domains: what is lacking, what to improve, how to make it run better.

## Answered / produced
- Claude Docs project document "Journal project: state, gaps and the weekly poem" (container id `0e39a7a9-7c83-4754-a1a6-29af7434e073`, opened as artifact `2ktApJHKd1ixLkZHKFDAF4`). Sections: Summary, Inventory, The weekly poem, Gaps by domain, Running it better (pipeline), Decisions that are yours, Sources.
- Four research subagents run in parallel: notes apparatus, weekly cadence, social/audience/journals, publishing pipeline tech.
- Weekly poem: nine deliverables per release, six the author's own work, three technical (transcription, citation dossier, generated social assets).
- Suggested five seasons of 20 poems with 2–3 week breaks, a bank of 8–12 finished releases before launch, a missed-week rule (slot moves, numbering holds), optional note layers per poem, and logging hours on the first four poems.
- Pipeline recommendations: one git folder per poem with Astro content collections; Cloudflare hosting with scans in R2; static IIIF tiles; scheduled go-live via `publishAt` plus cron; Playwright + WebCodecs + ffmpeg reel export at 1080×1920; image cards via Satori (OTF) or screenshot; DPUB-ARIA roles and Popover API for tap-to-reveal notes; quote-anchored note anchors; Buttondown email; cookieless analytics; 3-2-1 backups; a CI release gate (verified transcription, copyright filing before publish, alt text, note anchors, link check).
- Gaps named: 0 of 126 pieces verified; journal reserve not chosen (several journals count any online appearance as published); pages with copied lyrics; notes system unbuilt; no buffer; no name/handles/newsletter; social volume and platform link limits; participation terms; alt text; seven unbuilt interface fixes; font gaps; business-model and voice reports not yet folded in.
- Not checked: the `_memory` packet (not accessible) and one journal's submission page (blocked).

## Author decisions
- One poem released per week ("probably just one").
- Each poem carries edits, his written response as an endnote, footnotes, endnotes, citations, an academic layer, and social media content.
- Broadly accepted Claude's sorting of the review feedback (said he likes what was separated).

## Plan
- **author**, open: verify the first 20 poems in the review studio (blocks copyright filing and release).
- **author**, open: choose the journal-reserve poems and remove them from canvas, archive and alt text before any public launch.
- **author**, open: choose the name; claim handles and domain the same day.
- **author**, open: set cadence rules (fixed day, season length, break length, missed-week rule) and release order.
- **author**, open: decide which note layers are required per poem, reflection timing, participation model, and handling of pages with copied lyrics.
- **author**, open: fill in and photograph the font sheet.
- **Claude suggestion**, open: five seasons of 20 with breaks; bank 8–12 finished releases before launch; log hours on the first four.
- **Claude suggestion**, open: build the per-poem content model, scheduled publishing and CI release gate.
- **Claude suggestion**, open: build the notes layer (generated textual notes separate from the author's explanatory notes) and a private factual source dossier.
- **Claude suggestion**, open: set up Buttondown as the owned email channel.
- **Claude suggestion**, open: build interface fixes 1–3 from the screen-recording review, then test on a real iPhone.
- **Claude suggestion**, open: read the business-model and voice research reports before deciding products or audio.
