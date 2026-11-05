# Releasing the ETCETER4 Handwritten Journal: Standards, Offense, Defense, Precedents and Innovation (October 2026)

The best way to release the n/100 series is to treat each diary page as a versioned archival object you control: a high-resolution master scan, your own transcription, and metadata, all hosted canonically on etceter4. Copyright-register poems in batches *before* they go public. Then push lower-resolution derivatives out to social platforms as numbered, original-format posts that point back home. The prior-publication question is the decision with the biggest consequences: once a poem appears on Instagram or your site, the most prestigious journals (Poetry, Palette) will treat it as published. So decide now which poems belong to the public 100 and which you hold back for journal submission.

## TL;DR

- **Standards and defense first, posting second.** Scan masters at roughly FADGI 4-star (400 ppi, 16-bit color TIFF for manuscripts) and transcribe to TEI-style diplomatic plus reading texts. Register each batch of up to 10 unpublished poems with the US Copyright Office's GRUW option ($85) before posting, because the cheaper post-publication GRTX option excludes works under 50 words. Set machine-readable AI-training opt-outs (robots.txt, Content Signals, TDM reservation) on your own domain. Treat Glaze/Nightshade as weak deterrents only.
- **Your contemporaries show what works.** Serial numbering (Tyler Knott Gregson's Typewriter Series has passed #3,084), a visible analog process (typewriter poets, Kate Baer's erasures, Austin Kleon's blackouts), and a newsletter plus a product as the home base. They also show the failure modes: paywalling poems too early, algorithm dependence, and the "Instapoetry" craft critique.
- **Your historical peers, and the opening for innovation.** Dickinson's fascicles and envelopes, Whitman's six-edition revision of *Leaves of Grass*, Blake's hand-made copies that each differ, Tom Phillips's *A Humument* reissued in six editions, Mayer's *Memory*. Together they show that the manuscript, the revision history and the hand-made edition can *be* the work. Your clearest opening is a "living variorum": git-versioned poems with visible diffs between handwritten states, IIIF deep zoom, tap-to-reveal transcription, and numbered physical pages linked to their exact digital version, labeled as human-made and AI-free.

## Key Findings

1. **Prior publication cuts off part of the journal market.** Poetry magazine says that "Work that has appeared online for any reason, including social media posts, is considered previously published."\[1\] Palette Poetry excludes poems published "on a blog, or on social media."\[2\] Rattle and New Verse Review use a "previously curated" standard instead: self-posting is fine there.\[3\]\[4\] Book publishers generally accept previously published poems in collections.\[5\]
2. **Copyright registration has to be timed around posting.** GRUW covers up to 10 *unpublished* works for $85. GRTX covers 2–50 *published* short online works for $65, but each must be 50–17,500 words, and all must be first published online within a three-calendar-month window.\[6\]\[7\]\[8\] Many diary-page poems will be under 50 words, so GRUW-before-posting is the reliable route.
3. **AI-scraping defenses are mostly signals, not locks.** Cloudflare's July 1, 2025 press release says it became "the first Internet infrastructure provider to block AI crawlers accessing content without permission or compensation, by default," with every new domain asked whether to allow AI crawlers, and its Content Signals extension to robots.txt can express `ai-train=no`. In the EU, a machine-readable reservation is what removes your work from the commercial text-and-data-mining exception.\[9\] Image "cloaks" have been broken in peer-reviewed research.\[10\]\[11\]
4. **Platform tailwind for originals.** Instagram's April 30, 2026 update extended its reach penalty to photos and carousels: per Instagram's announcement (reported by MediaPost), "accounts that primarily post unoriginal content in photos or carousel posts, in addition to reels, will no longer be shown in places where we recommend content." That favors original handwritten-page carousels and penalizes aggregator accounts that repost your pages.
5. **Precedent strongly supports process-as-work.** Major digital editions (Whitman Archive, Dickinson facsimiles) present all versions rather than one "final" text.\[12\] Your versioning idea sits squarely in the scholarly-edition tradition, not outside it.

## 1. Methods and Standards

### Image capture

- **Masters.** The US federal FADGI guidelines are the reference standard. The College of Charleston's Lowcountry Digital Library guidelines (January 2026), which state that they "follow the FADGI 4-star recommendations," specify "Manuscripts or Handwritten Documents, 400 ppi, 16-bit RGB color TIFFs" for pages under 8×10 inches and 600 ppi for larger ones. FADGI's 4-star level also bans retouching of master files and software de-skew: shoot square, keep within ±1°, and include a margin beyond the page edge.\[13\]\[14\] Color space: Adobe RGB 1998 or eciRGBv2 for masters.\[15\] Shoot with a color/gray target in frame for at least one session so color can be verified later.
- **Practical recommendation.** For a notebook, use a copy-stand camera or flatbed at 400 ppi minimum and 600 ppi if you plan deep zoom or large prints. Save uncompressed or losslessly compressed TIFF masters and never edit them. Make *derivatives* for everything else: cropped, color-managed sRGB JPEG/WebP for web and social, and PDF/A for print files. JPEG 2000 is an accepted archival/access format if you run an image server, but static tiles work too (see IIIF).
- **Capture everything as data.** Photograph page versos, covers, inserts and blank pages. Later genetic or versioning views depend on knowing what surrounded each poem.

### IIIF (deep zoom and interoperability)

- The International Image Interoperability Framework has two layers: an Image API that serves zoomable tiles, and a Presentation API (v3.0) whose "manifest" describes a work's pages, order and labels. You don't need a server. "Level 0" static tiles can be generated once and hosted on GitHub Pages, S3 or Cloudflare.\[16\] Viewers include Mirador (built for comparison and annotation), Universal Viewer, and lightweight React options such as Clover.\[17\]\[18\]
- For your minimal aesthetic, build a custom full-bleed OpenSeadragon/Clover-style view with no chrome, and offer Mirador only as a "scholar mode" for side-by-side version comparison.

### Transcription and encoding

- **Two layers per poem.** (a) A *diplomatic* transcription that records line breaks, strike-throughs, insertions and illegible spots as they appear. (b) A *reading* (normalized) text. TEI, the Text Encoding Initiative, is the scholarly standard. Its transcription module marks `<add>`, `<del>`, `<subst>` (a deletion plus addition counted as one intervention), `<unclear>` and `<gap>`. Its `<sourceDoc>`/`<surface>`/`<zone>`/`<line>` elements record where text sits on the page.\[19\]\[20\] TEI's genetic-editing model is designed to sequence "revision campaigns," which matches your versioning plan directly.\[21\]
- **Practical recommendation.** You don't need full TEI on day one. Keep a plain-text or Markdown diplomatic transcription with a small, consistent markup convention, plus a TEI export, in the repo. All transcription is your own text, which also keeps the human-only provenance clean.

### Accessibility (WCAG)

- Images of handwriting need text alternatives (WCAG 1.1.1). WCAG's "Images of Text" criterion (1.4.5) exempts cases where the particular presentation is essential, and handwriting counts. But you still owe screen-reader users the words. Alt text should be short ("Handwritten journal page, poem 37/100, ink with two crossed-out lines"), with the full transcription one tap away and programmatically linked, for example via `aria-describedby` or an adjacent expandable region.
- **Tension with tap-to-reveal.** Hidden menus are compatible with WCAG 2.2 only if they are keyboard-reachable, announced to screen readers, have visible focus states, and respect `prefers-reduced-motion`. "Visually hidden until tapped" must not mean "absent from the accessibility tree."

### Metadata

- **Dublin Core** (15 core elements: title, creator, date, format, identifier, rights, relation, etc.) for archive deposits.
- **schema.org** JSON-LD on each web page: use `CreativeWork` (I did not confirm a widely adopted dedicated "Poem" type), with `genre: poetry`, `position` (n of 100), `isPartOf` (the series), `version`, `dateCreated` vs. `datePublished`, `isBasedOn` (previous version), `associatedMedia` (the scan), `license`, `creator`. This helps search engines and future archivists alike.
- Track per poem: diary date, page/notebook ID, scan IDs, version list, publication venues and dates (essential for submission and registration records), rights status, and any privacy notes.

### Versioning and edition practice

- **Genetic criticism** (critique génétique) studies the writing process through drafts. **Variorum editions** collate every variant. The Whitman Archive "has not chosen to privilege one particular edition," presenting all six US editions plus the annotated "Blue Book."\[12\] That is a direct model for showing your iterations as legitimate versions rather than "corrections."
- **Git-based publishing.** Keep one repository (you already work in GitHub as 4444J99) with a folder per poem (`037/`) holding scans, transcriptions (`v1.md`, `v2.md`…), metadata and the IIIF manifest. Use tagged releases (`037-v2`) so every public version has a permanent address. Plain-text transcriptions make `git diff` meaningful. Scans belong in Git LFS or external storage.
- **Version naming.** Distinguish *states* of the handwritten page (the same physical page, revised in ink later) from *versions* (new drafts on new pages, or typed revisions). Editorial scholars draw this line, and readers will understand it.

### Persistent identifiers and preservation

- **Rule of thumb:** 3 copies, 2 media types, 1 off-site ("LOCKSS": Lots Of Copies Keep Stuff Safe). Masters go on two local drives plus cloud cold storage.
- **Zenodo** (CERN-run) issues DOIs and supports versioned deposits: one "concept" DOI for the series plus a DOI per version. That makes it well suited to depositing each batch of the 100 with masters. Zenodo deposits are public, so deposit at or after publication, not before.
- **Internet Archive** for public access copies and Wayback snapshots of your site. **Software Heritage** archives public git repositories. Consider an ORCID iD, as an academic, to tie the DOIs together.
- These public archives make work *more* visible to crawlers. That is an explicit trade-off between preservation and AI exposure. Deposit access derivatives publicly; keep 600-ppi masters private.

### Numbered and limited editions

- Convention: state the edition size up front (e.g., "edition of 100"), number each copy "n/100," sign, and add a colophon (date, paper, printing method, edition size, artist's proofs marked "AP" outside the count). Never reprint a closed limited edition in the same form, because that breaks collector trust. Your series title "n/100" already reads as an edition statement, so keep the *poem number* and any *print edition number* visibly distinct (e.g., "Poem 37/100 — print 4/25").

### ISBN, print-on-demand vs. small press/zine

- An ISBN is needed for bookstore and library distribution, not for zines sold directly. In the US, ISBNs come from Bowker. POD platforms (Amazon KDP, IngramSpark) offer distribution, and KDP's free ISBN lists the platform as publisher of record, which matters for how you present yourself. For an art-object edition, offset or riso printing in a small numbered run, sold direct and through zine fairs and art-book stores, carries more cultural weight than POD. A pragmatic hybrid: a numbered riso or zine edition now, and a trade facsimile book (ISBN) after the series completes.

### Handwriting font creation and licensing

- Calligraphr turns a filled-in template into a font. The free tier caps fonts at 75 glyphs; Pro allows up to 480 characters per font, ligatures, and random variants (multiple versions of each letter, which reduces the "fake handwriting" look). Its FAQ says creations are "your sole property" and can be used under "any terms you wish."\[22\]\[23\] Alternatives: FontForge or Glyphs for hand-tuned results.
- **Licensing:** in the US, typeface *designs* are generally not copyrightable, but font *software* is. Ship the webfont under your own EULA, or the SIL Open Font License if you want it open.
- **Strategic caution:** a font of your hand also lets anyone fake "handwritten ETCETER4" pages. Use the font for interface and supporting text, never for the poems. Keep the scan as the only authentic carrier of each poem.

## 2. Offensives (Growth and Distribution)

### Platform strategy as of late 2026

- **Instagram remains the native home for handwriting images.** Mosseri has named watch time, sends per reach and likes per reach as the key ranking signals; DM sends are reported as the strongest signal for reaching non-followers.\[24\] Instagram's April 30, 2026 update means "accounts that primarily post unoriginal content in photos or carousel posts, in addition to reels, will no longer be shown in places where we recommend content" (Instagram announcement, via MediaPost). Your original page scans benefit, and reposters of your work get demoted. Third-party guides (not Meta) report carousels of up to 20 frames and a suggested cadence of roughly 2 Reels plus 3–5 feed posts per week.\[24\]\[25\] Treat those as industry lore, not policy.
- **Format suggestion:** a carousel per poem: frame 1 the full page, frames 2–3 detail crops (a crossing-out, a marginal note), and a final frame with the number, date and a short link line. An optional Reel shows the page being turned or zoomed with your own voice reading it.
- **TikTok/Reels** reward voice and face more than images. A short reading over the page scan is the bridge. Social poetry's commercial engine is now video. Whitney Hanson's TikTok readings gathered more than 78 million likes before a Penguin Random House deal.\[26\]
- **Substack/newsletter** is your owned channel. Poetry newsletters can reach real scale: Pádraig Ó Tuama's Poetry Unbound shows "over 133,000 subscribers."\[27\] Substack takes 10% of paid subscriptions.\[28\] Use it for the "making-of" layer (dates, revisions, scans, audio) while the poems stay free on your site.
- **Bluesky, Threads, Tumblr:** low-cost cross-posting that reaches literary and art communities, with Tumblr's long history of image-poetry reblogging. I did not verify current 2026 reach data for these, so treat them as secondary.

### Numbered-series and countdown tactics

- Numbering creates a collection instinct, an implied completion date and a natural archive. Gregson's Typewriter Series has run since March 2012 and passed #3,084, and the number itself became the brand.\[29\]\[30\] For a closed set of 100, publish the schedule (e.g., two per week, so about a year), mark milestones (10/100, 50/100), and save the final 10 for a live event or print launch. A visible "grid of 100" on etceter4 that fills in as poems release does more than any countdown sticker.
- Release in the same order as the diary (chronological honesty) or deliberately out of order (curatorial). Either works; say which one you chose.

### Newsletter, community, events

- Collect email from day one. The site's grid page should have one quiet "notify me" field, revealed on tap in keeping with your interface preference.
- Launch readings: reading from the physical notebook in front of an audience gives the handwritten premise a public form. Bernadette Mayer's *Memory* was first shown in 1972 as a wall installation with a six-hour audio reading, a model for a gallery or reading-series version of the 100.\[31\]\[32\]

### Products

- **Ladder:** (1) free poems online; (2) open-edition postcards or riso prints of selected pages; (3) signed, numbered limited prints of single pages (n/25); (4) a numbered zine or facsimile of the complete 100; (5) unique items, such as original journal pages, only if you're willing to part with them. Patreon/Ko-fi/Substack paid tiers fund the process layer. Bandcamp works for audio readings bundled with physical zines.
- **A caution from Gregson's experience:** in 2026 he moved new Typewriter poems behind a paywall and reported that sign-ups had "dramatically stalled."\[33\] Poet-newsletter advice reinforces this: "asking people to pay for your online poetry is unlikely to be successful."\[34\] Charge for objects, process and access, not for reading the poems.

### Journals, contests and prior publication

- Policies vary, so decide per poem:
  - **Strict:** Poetry magazine, which pays $500 per poem: anything online "for any reason, including social media posts" counts as published.\[1\] Palette Poetry and its Ouroboros Prize; The Shore.\[2\]\[35\]
  - **Lenient ("previously curated" standard):** Rattle, which accepts work "self-published to blogs, message boards, or social media" and pays $200/poem in print;\[3\] New Verse Review (social-media drafts OK);\[4\] magazines on Lit Mag News's "uncurated" list, e.g., Stanchion.\[36\]
  - **Books:** previously published poems are generally fine in a collection, and prior journal credits help.\[5\]
- **Implication for you:** a draft posted as a *version* arguably makes later versions "previously published" at strict venues. Keep a separate **reserve pool** of strong poems that never appear online, for strict journals and contests. Use the n/100 series for work you want to live publicly in its manuscript form.

### Grants and residencies

- Funders matching a handwriting + web + versioning project include electronic-literature and media-art channels (ELO conference and prizes, Rhizome-type net-art commissions), book-arts and artist-book residencies, and poetry fellowships. US federal arts funding has been volatile in 2025–26, so verify current NEA availability before planning around it. Poets & Writers' grants database is the standard listing. (I did not verify specific 2026–27 deadlines.)

## 3. Defensives (Protection and Risk)

*Informational only, not legal advice. Verify current rules with the Copyright Office or an attorney.*

### Copyright registration

- Copyright exists on fixation, but in the US registration is generally required before suing,\[37\] and statutory damages and attorney's fees depend on timely registration.
- **GRUW (unpublished works):** up to 10 works, same author, completed in the same year, $85 online.\[8\]\[38\] Ideal: register each batch of 10 poems *before* they are posted. All 100 cost about $850 across 10 filings.
- **GRTX (short online literary works):** 2–50 works first published online within three calendar months, each 50–17,500 words, $65.\[6\]\[7\] Useful only for longer pieces (e.g., the essay or prose layer of a newsletter).
- **Visual element:** registration of poems covers the text. The handwritten page as a visual work could also be protected as two-dimensional artwork. The Copyright Office finalized a group option for two-dimensional artwork in December 2025 ($85);\[39\] check its per-group limits and whether it suits page images.
- **Versions:** a later revised version is a derivative work. Registering the original version protects the core text; substantial new versions can be registered later if they matter commercially.

### Licensing choice

- **Default recommendation:** all rights reserved for poems and scans, with an explicit permission note ("Share with credit and a link; no commercial use or AI training without permission"). Optionally put the *transcription markup, code and metadata schema* under an open license (CC BY or MIT). Many scholarly archives do this; the Whitman Archive publishes under a Creative Commons license.\[40\] CC BY-NC-ND is a middle path for the scans if you want legal clarity for sharers, but any CC license makes control over reuse harder later.

### AI scraping and training

- **On your domain:** (1) robots.txt disallow rules for named AI training crawlers (RFC 9309 is now the formal robots standard);\[9\] (2) Cloudflare's AI-bot blocking (per Cloudflare's July 1, 2025 press release, "every new domain will now be asked if they want to allow AI crawlers," with blocking the default) and its Content Signals directive, e.g., `Content-Signal: search=yes, ai-train=no`, published September 2025; (3) a TDM reservation (TDMRep header/`tdmrep.json`) plus a plain-language terms page.\[41\]
- **Why it matters legally:** in the EU, commercial text-and-data mining is allowed unless the rightsholder reserves rights "in an appropriate manner, such as machine-readable means."\[9\] The EU GPAI Code of Practice (July 10, 2025) commits signatories to honoring robots.txt and other machine-readable reservations.\[41\]\[42\] A Hamburg appeals court reportedly held in December 2025 that natural-language terms alone are insufficient (secondary reporting; verify).\[43\] The Commission ran a consultation (Dec 2025–Jan 2026) toward a list of "generally-agreed" opt-out protocols.\[42\] Check whether it has been published by the time you launch.
- **Limits:** robots.txt and content signals are requests. Crawlers that don't comply ignore them, which is why network-level blocking exists.\[44\]\[45\] Your *transcriptions* are the most trainable asset. You can't publish accessible text and make it unscrapable. Accept that trade-off, or render transcriptions client-side behind interaction (slightly harder to scrape, but it must stay screen-reader accessible).
- **Glaze/Nightshade:** built to stop *style mimicry* of artwork, not text extraction from handwriting. LightShed (Foerster, Behrouzi, Rieger, Jadliwala and Sadeghi, 34th USENIX Security Symposium, 2025) detected Nightshade-protected images with a 99.98% true-positive rate and a 100% true-negative rate, then removed the perturbations (the 99.98% is a detection rate, not a removal-success rate). Hönig et al. (ICLR 2025) found such cloaks "ineffective when faced with simple robust mimicry methods."\[10\] Low value for your use case; skip them unless you're also posting drawings.
- **Platforms:** social platform terms grant broad licenses to posted content, and AI-training policies on public posts have changed repeatedly. Check each platform's current AI-training settings and opt-outs at launch, and post only derivatives (≤1080–1440 px) there.

### Image theft, reposting and watermarking

- Embed IPTC/XMP metadata (creator, copyright, URL, "n/100") in every derivative. Many platforms strip it, but your site copies keep it.
- **Watermarks:** a large overlay ruins the object-on-screen aesthetic and is easily cropped. A small, consistent corner mark (series number plus domain) gives attribution without vandalism. The number "37/100" is itself a quiet watermark. Instagram's 2026 originality rules already demote aggregators, and its repost/collab tools give credit natively.\[46\]\[47\]
- Keep a takedown kit: a DMCA notice template, platform IP-report links, and your registration numbers, which strengthen any claim.

### Privacy and real people in diary content

- Diary poems often name or identify partners, family and friends. In the US the main risks are *public disclosure of private facts*, *false light* and *defamation* (truth defeats defamation but not necessarily private-facts claims). Beyond law, there is relational and ethical harm. Precedent: Diane Middlebrook's 1991 Anne Sexton biography drew controversy for using Sexton's psychiatrist's therapy tapes. Ted Hughes's handling of Plath's journals, including destroying one, became a decades-long debate about who controls a diarist's record.
- **Protocol:** before each release, check whether anyone is identifiable by name, initials, place or unique detail. Redact in the *digital derivative only* (an honest, visible redaction mark, never altering the master). Seek consent where someone is plainly identifiable, and keep a private log of redaction decisions. Also check for your own sensitive data: addresses, phone numbers, health information, and other people's handwriting on the page.

### First-publication rights

- Posting gives away first North American serial rights for strict venues. Publishing on your own site first is usually more defensible and portable than publishing on a platform first, but strict journals count both. Track the first public appearance date for each poem and version.

### Backup and platform dependency

- Canonical home: etceter4 (your domain, your repo). Social posts are announcements. Export your email list monthly. Never let a platform hold the only copy of the work, the comments you value, or the audience list.

## 4. Contemporaries (2023–2026)

| Who | What they do | What works | Caveats/critiques |
|---|---|---|---|
| **Tyler Knott Gregson** | One-take Typewriter Series poems on found book pages since 2012; now serialized on Substack with audio and "deep dive" essays; prints sold\[29\]\[30\] | Numbering (#3,084+) as brand; analog constraint reads as authenticity; *Chasers of the Light* (Penguin/Perigee, 2014) grew out of the series\[48\]\[49\] | Paywall move in 2026 coincided with "dramatically stalled" sign-ups\[33\] |
| **Kate Baer** | Erasure poems made from critical DMs and emails; Instagram carousels showing original, then erasure\[50\] | Process visible in two frames; *I Hope This Finds You Well* (Harper Perennial, 2021) was an instant NYT bestseller\[51\] | 2023–26 metrics not verified |
| **Austin Kleon** | Newspaper blackout poems since 2005, regularly opening his newsletter\[52\]\[53\] | Tumblr peaked at about 140,000 readers; his Substack page shows "over 308,000 subscribers" | Poems are a side practice inside a larger creativity brand |
| **Sasha Stiles / theVERSEverse** | Poetry-NFT gallery co-founded 2021 by Stiles, Ana Maria Caballero and Kalen Iwamoto; Stiles uses her own handwriting and "Cursive Binary"\[54\]\[55\] | MoMA showed *Sasha Stiles: A LIVING POEM* (Sept 2025–Mar 2026), a generative poem that rewrites itself hourly\[56\]\[57\] | Uses GPT-4 output, the opposite of your AI-free stance; Lit Hub mocked NFT poetry;\[56\]\[58\] post-2022 sales not verified |
| **Typewriter street poets** | Zach Houston's "poemstore" (since 2005, "Your Topic, Your Price"); Kay "Kro" Kroger (10,000+ on-demand poems); the Haikuists agency (125 poets, 25 cities)\[59\]\[60\]\[61\]\[62\] | Live, made-for-you handwriting/typing as performance and income | Commissions, not a body of work |
| **Marion Fritsch (France)** | Instagram poems styled as handwriting on aged paper since 2023\[26\] | About 450,000 followers; book *Les fragments du coeur* (2024)\[26\]\[63\] | Simulated handwriting aesthetic, a warning about the "handwritten look" becoming a commodity style |
| **Jen Bervin** | Book artist; co-edited Dickinson's *The Gorgeous Nothings*\[64\] | Shows that facsimile plus diagrammed transcription can be a major publication\[64\]\[65\] | Precedent rather than serial poster |
| **Commercial mainstream (Donna Ashworth, Lucas Jones, Rupi Kaur)** | Social-first accessible verse | Andrews McMeel says Kaur's *milk and honey* (self-published 2014) "has sold more than 6 million copies globally, becoming the highest-selling book of poetry in the 21st century" | Rebecca Watts's 2018 *PN Review* polemic "The Cult of the Noble Amateur" attacked "the open denigration of intellectual engagement and rejection of craft";\[66\]\[67\] 2024–26 critiques continue mostly in student papers and Substacks |

**What this means for you:** the market rewards visible process and serial rhythm. Critics punish frictionless, aphoristic content. Handwritten diary pages with real revisions and dates sit on the "process" side of that line, provided the presentation emphasizes the page as an artifact rather than a quote card. The Fritsch case shows "handwritten-looking" is already a stylistic genre. Your differentiator is *verifiable* authenticity: real scans, real versions, a public revision history.

## 5. Historical Peers and Lessons

- **Emily Dickinson.** Wrote about 1,800 poems, published fewer than a dozen in her lifetime,\[68\] and bound many into hand-sewn fascicles. Her late envelope writings (52 in *The Gorgeous Nothings*, 2013, the first full-color facsimile edition of her manuscripts) show spatial arrangement and variant words as part of meaning.\[64\]\[69\] A reviewer noted they show that "spatial arrangement, gestural punctuation, and eccentric word design are central to meaning."\[64\] *Lesson:* normalized typeset text erased Dickinson's page for a century, so always ship the scan and the diplomatic transcription together.
- **Walt Whitman.** Self-published *Leaves of Grass* in 1855, then revised it through editions of 1856, 1860, 1867, 1871 and 1881, plus the 1891–92 "Deathbed" edition.\[70\]\[71\] The Whitman Archive publishes all versions in TEI, including his hand-annotated "Blue Book."\[12\]\[40\] *Lesson:* lifelong revision becomes the work's identity. Publish your versions as editions, not errata.
- **William Blake.** Illuminated printing: relief-etched plates printed and hand-colored by Blake and Catherine Blake, so each copy of a book differs. The William Blake Archive presents copies comparatively. *Lesson:* the "copy" is a unit of meaning. Your numbered physical pages can differ on purpose, with each one documented.
- **Frank O'Hara, *Lunch Poems* (City Lights, 1964).** Poems written on lunch hours, dated and occasional. *Lesson:* the date and circumstance of composition is content. Show diary dates.
- **Joe Brainard, *I Remember* (1970).** A serial, accretive form of memory sentences, expanded in later editions. *Lesson:* a simple repeating frame (like n/100) can carry a large body of work.
- **Bernadette Mayer, *Memory* (1971).** One roll of 35mm film a day plus a journal for July 1971: over 1,100 photographs, about 200 pages of text and six hours of audio.\[72\] Shown in 1972 at Holly Solomon's gallery, it went largely unseen until Siglio's complete edition in 2020.\[31\] *Lesson:* a diary project can be an installation, a book and an audio work. Plan the complete edition from the start, because the full object can disappear for decades if you don't.
- **Ted Berrigan and the mimeograph revolution.** Berrigan's *The Sonnets* came out of *C* magazine and press (1960s), cheap stapled mimeo publications circulated within a community. *Lesson:* cheap, fast, numbered, community-distributed print builds lasting reputations. Today's riso zine is the equivalent.
- **Plath and Sexton journals.** Plath's *Unabridged Journals* (2000) restored material earlier editions cut, which shows how editorial control over a diary shapes reputation. *Lesson:* decide your own redaction and release policy now, in writing, so you remain the editor of your diary.
- **Fluxus and mail art.** Fluxus multiples (cheap boxed editions) and Ray Johnson's New York Correspondence School made distribution and participation part of the artwork. *Lesson:* audience participation works best when the rules are simple and the artist sets the frame.
- **Concrete poetry** (Gomringer, Noigandres, Ian Hamilton Finlay). The visual arrangement *is* the poem. *Lesson:* treat the page layout, including crossings-out, as composition.
- **Dieter Roth.** Artist books, editions and "literature sausages" treated the book as material. *Lesson:* the printed object can comment on the text.
- **Tom Phillips, *A Humument*.** From 1966 he painted over pages of W.H. Mallock's Victorian novel *A Human Document*, publishing revised editions from 1970 to a final sixth edition in 2016, replacing pages each time, and an app edition. *Lesson:* the closest precedent for a lifelong, versioned, page-based work released in editions.
- **Raymond Pettibon.** Handwritten text-and-image drawings, plus self-made photocopied zines and SST flyers. *Lesson:* handwriting plus cheap reproduction plus a scene can reach far beyond the literary world.
- **Sei Shōnagon, *The Pillow Book* (around 1000 CE).** Court diary of lists, observations and judgments circulated in manuscript. *Lesson:* the diary as public literary form is roughly a thousand years old. The "private" frame adds intimacy, not illegitimacy.
- **Net.art, early e-lit and blog-era poetry.** The Electronic Literature Organization (founded 1999) and its *Electronic Literature Collection* volumes preserve web-native poetry. Much Flash-era work (e.g., Young-Hae Chang Heavy Industries) needed rescue as platforms died. Blog-era poets (flarf, alt-lit) built communities on blogs that have since vanished. *Lesson:* build on open standards (HTML, IIIF, TEI, plain text), not proprietary runtimes, and deposit to archives.

## 6. Innovation Opportunities (Feasibility and Risk)

| Idea | What it is | Feasibility | Risks/notes |
|---|---|---|---|
| **Living variorum (git-versioned poems)** | Each poem has a version timeline; readers tap to step v1→v2→v3 of scans *and* transcriptions | High; you already work in git; static site plus JSON | Versions posted publicly affect prior-publication eligibility; decide policy first |
| **Visual diffs of handwriting** | Text diffs of transcriptions (deletions/insertions highlighted), plus image overlays aligning two page states | Text diff: high. Image alignment: medium (manual registration or OpenCV) | Keep the diff visual quiet; it should read as an edition apparatus, not a code review |
| **IIIF deep zoom, chrome-free** | Full-bleed page; pinch to the nib; tap reveals transcription, number, date | High with static Level 0 tiles plus OpenSeadragon/Clover\[16\]\[18\] | Accessibility of hidden UI (see WCAG); test with VoiceOver/TalkBack |
| **Handwriting font for the interface** | Menus, captions and metadata set in your hand | High (Calligraphr Pro: 480 glyphs, ligatures, variants)\[22\] | Forgery/authenticity: never set poems in the font |
| **Audio layer** | Your reading of each page, synced to line zones (TEI `<zone>`) for highlight-as-you-listen | Medium | Extra rights and time; audio is also scrapable |
| **Participation: annotations** | W3C Web Annotation/Hypothesis or IIIF annotations on pages | Medium | Moderation burden; others' words appear next to yours. Keep it opt-in and separate from the "work alone" view |
| **Participation: numbered responses** | Readers submit their own handwritten page responding to "n," numbered n.1, n.2… in a separate gallery | Medium | Rights and consent forms for contributors; must never blur authorship of your 100 |
| **Physical–digital hybrid** | Numbered prints carry a QR code or short URL to that poem's *exact version* (tagged release) | High | Links rot unless you control the domain; also deposit to Zenodo/IA |
| **Edition certificates and provenance** | Signed certificate per print; optional C2PA "Content Credentials" metadata on images; optional on-chain token | Certificates: high. C2PA: medium. NFT: medium | NFTs remain polarizing in literary circles (Lit Hub's "lyric poster for the digital dorm room");\[58\] Ethereum's 2022 move to proof-of-stake reduced the energy objection, but market collapse and scams are still reputational risks |
| **AI-free provenance label** | A public statement plus per-poem "made by hand, transcribed by the author, no generative AI" and a process page showing scans and dates | High | A claim, not proof; the version history and scans are the evidence. Poetry magazine's "We only publish human-written poetry" shows the value is recognized\[1\] |
| **Generative presentation (non-AI)** | Deterministic interfaces: daily-rotating poem, random walk through pages, grid that fills by date | High | Keep generation in *arrangement*, not text, so all creative text remains yours |

**Assessment:** the strongest and most distinctive package is the living variorum, chrome-free IIIF deep zoom, numbered prints linked to their exact versions, and an AI-free provenance page. It is technically cheap for you, grounded in precedent (Whitman, Phillips, Dickinson facsimiles), and hard for Instapoetry imitators to copy, because it depends on real manuscripts and real revision history. Annotation and participation should come in phase two, after the series has an audience and you have moderation rules.

## Caveats

- Platform algorithm details come mostly from Meta statements reported by trade press and third-party marketing guides; they change frequently. The April 2026 originality update is well reported; cadence and carousel-frame claims are secondary.
- Copyright Office fees and group options were current per Office documents and 2025–26 reporting; confirm on copyright.gov before filing. The December 2025 two-dimensional artwork group option should be checked for its limits.
- EU AI-opt-out law is still being implemented; the Hamburg ruling is reported secondhand. US law offers no equivalent statutory opt-out; US AI-training copyright litigation was ongoing and unresolved as of this writing.
- Some contemporary metrics (Gregson's subscriber tier, Baer's current activity, theVERSEverse's sales since 2022) could not be verified. UK poetry-sales "boom" figures conflict between sources (£12m vs. £14.4m for 2023).\[73\]\[74\]
- Nothing here is legal advice; privacy and defamation questions about specific poems deserve a lawyer's review if real people are identifiable.

## Prioritized Action Checklist

1. **Decide the split:** which poems are in the public n/100, and which go to a never-posted reserve pool for strict journals and contests. Write a one-paragraph release policy covering versions, redaction and order.
2. **Scan all candidate pages** at 400–600 ppi, 16-bit TIFF, no retouching; make sRGB web derivatives; store masters 3-2-1.
3. **Privacy pass:** log identifiable people and data per page; redact derivatives only; seek consent where needed.
4. **Register before posting:** file GRUW in batches of 10 unpublished poems ($85 each) and keep registration numbers in your metadata.
5. **Build the repo structure:** a folder per poem with scans, diplomatic plus reading transcriptions (your own text), metadata JSON (schema.org `CreativeWork`), and version tags.
6. **Lock down the domain:** robots.txt AI-crawler rules, Cloudflare AI-bot blocking plus Content Signals (`ai-train=no`), TDMRep, and a rights/terms page with an "all rights reserved, share with credit" note.
7. **Ship the site MVP:** a grid of 100 that fills as poems release; a chrome-free deep-zoom page view; tap-to-reveal number, date, transcription and version history; tested with screen readers and keyboard.
8. **Start the email list** and a Substack (or equivalent) for the process layer; keep the poems free.
9. **Announce the schedule** (e.g., 2 per week) and start releasing original-format Instagram carousels plus occasional voice Reels; cross-post to Bluesky, Threads and Tumblr; always link home.
10. **Deposit milestones** (every 25 poems) to Zenodo (versioned DOIs) and the Internet Archive; archive the repo via Software Heritage.
11. **Prototype the product:** a small numbered riso/zine edition or n/25 prints with colophon, certificate and a QR code to the exact version; plan the complete facsimile book (ISBN) for after 100/100.
12. **Phase two:** add the visual diff/variorum view, audio readings, and (optionally) moderated participation such as a separate numbered response gallery; decide on C2PA or NFT provenance only after weighing reputational fit.
13. **Apply** to e-lit, net-art and book-arts opportunities with the working site as your portfolio; verify current deadlines and funding status.

## Sources

1. [How to Submit](https://www.poetryfoundation.org/poetrymagazine/submit)
2. [Submit - Palette Poetry](https://www.palettepoetry.com/submit/)
3. [Regular Submission Guidelines - Rattle: Poetry](https://rattle.com/page/submissions/)
4. [submissions 3d8](https://newversereview.substack.com/p/submissions-3d8)
5. [When is something considered published?](https://www.writersdigest.com/personal-updates/poetry-faqs-when-is-something-considered-published)
6. [Copyright Office Implements Mass Registration for Short Online Literary Works](https://btlaw.com/en/insights/alerts/2020/copyright-office-implements-mass-registration-for-short-online-literary-works)
7. [New Group Copyright Registration Option Raises Questions Around Definition of ‘Published’ in the Digital Age](https://ipwatchdog.com/2020/09/01/new-group-copyright-registration-option-raises-questions-around-definition-published-digital-age/)
8. [Copyright Registration Cost in 2026: \$45 to \$125](https://outsideipcounsel.com/guides/copyright-registration-cost/)
9. [robots.txt, AI Opt-Outs and Reservation Signals: What Web Data Collectors Should Honour in 2026](https://shifter.io/blog/robots-txt-ai-opt-outs-reservation-signals)
10. [Glaze and Nightshade, explained — poisoning.ai](https://poisoning.ai/articles/glaze-and-nightshade-explained/)
11. [Can Glaze and Nightshade be bypassed? — poisoning.ai](https://poisoning.ai/articles/can-glaze-nightshade-be-bypassed/)
12. [Re-Scripting Walt Whitman](https://whitmanarchive.org/item/anc.00152)
13. [i June 2022 DRAFT 3.5 Technical Guidelines for Digitizing](https://www.digitizationguidelines.gov/guidelines/DRAFT%20Technical%20Guidelines%20for%20Digitizing%20Cultural%20Heritage%20Materials%20-%203rd%20Edition.pdf)
14. [Technical Guidelines for Digitizing Cultural Heritage ...](https://www.digitizationguidelines.gov/guidelines/FADGI_Still_Image_Tech_Guidelines_2016.pdf)
15. [DRAFT September 2, 2015 Technical Guidelines for Digitizing Cultural](https://www.digitizationguidelines.gov/guidelines/FADGI_Still_Image_Tech_Guidelines_2015-09-02_v4.pdf)
16. [Awesome International Image Interoperability Framework (IIIF)](http://iiif.github.io/awesome-iiif/)
17. [Implementation of the IIIF Presentation API 3.0 based on Software Support](https://arxiv.org/html/2312.11116v2)
18. [GitHub - D-Groenewegen/awesome-iiif: Awesome IIIF-related resources · GitHub](https://github.com/D-Groenewegen/awesome-iiif)
19. [TEI BASIC STRUCTURE AND CORE COMPONENTS Martina Scholger](https://gams.uni-graz.at/o:dhoxss2016-tei-structure)
20. [TEI for Transcription](https://slides.com/jamescummings/tei-for-primary-sources)
21. [An Encoding Model for Genetic Editions](https://tei-c.org/Vault/TC/tcw19.html)
22. [How to Turn Your Handwriting Into a Font](https://www.makeuseof.com/tag/how-to-turn-your-handwriting-into-a-font/)
23. [Calligraphr - Create your own fonts.](https://www.calligraphr.com/en/docs/faq/)
24. [How the Instagram Algorithm Works in 2026](https://www.eclincher.com/articles/how-the-instagram-algorithm-works-in-2026)
25. [What Actually Works on Instagram in 2026: The Definitive Guide](https://www.aureliusmedia.co/blog/what-works-on-instagram-2026)
26. [Newsletter Newsletters Events Events Podcasts Videos Africanews](https://www.euronews.com/culture/2025/03/21/world-poetry-day-on-instagram-and-tiktok-poetry-finds-a-new-lease-of-life)
27. [Poetry Unbound](https://poetryunbound.substack.com/)
28. [A Special Thank You Letter](https://creativeseeds.substack.com/p/thank-you-f65)
29. [Typewriter Series #3084 - Signal Fire](https://www.tylerknott.com/p/typewriter-series-3084)
30. [Thirteen Years of Typewriter Series Poetry | 3.30.25](https://www.tylerknott.com/p/thirteen-years-of-typewriter-series)
31. [Bernadette Mayer: Memory - Announcements - e-flux](https://www.e-flux.com/announcements/320027/bernadette-mayermemory)
32. [Bernadette Mayer Predicted Our Obsession with Self Documentation - ELEPHANT](https://elephant.art/bernadette-mayer-photography-memory-book-10052020/)
33. [Typewriter Series #3083 - Signal Fire](https://www.tylerknott.com/p/typewriter-series-3083)
34. [Should you submit the poem or post it?](https://alixklingenberg.substack.com/p/should-you-submit-the-poem-or-post)
35. [THE SHORE](https://www.theshorepoetry.org/)
36. [lit mags that use uncurated in the](https://litmagnews.substack.com/p/lit-mags-that-use-uncurated-in-the)
37. [How to Register a Song: Copyright Office and PROs](https://orphiq.com/resources/how-to-register-a-song-copyright)
38. [Copyright Office Introduces Option for Group Registration of Unpublished Works](https://powleygibson.com/1901-2/)
39. [Federal Register :: Group Registration of Two-Dimensional Artwork](https://www.federalregister.gov/documents/2025/12/19/2025-23402/group-registration-of-two-dimensional-artwork)
40. [Published Writings](https://whitmanarchive.org/published-writings)
41. [AI Crawler Control: A Compliant TDM Opt-Out in 2026](https://www.xictron.com/en/blog/ai-crawler-control-tdm-opt-out-2026/)
42. [Commission launches consultation on protocols for reserving rights from text and data mining under the AI Act and the GPAI Code of Practice](https://digital-strategy.ec.europa.eu/en/consultations/commission-launches-consultation-protocols-reserving-rights-text-and-data-mining-under-ai-act-and)
43. [robots.txt and AI: EU Legal Situation and TDM Opt-out](https://blckalpaca.at/en/knowledge-base/seo-geo/technical-seo/robotstxt-and-ai-eu-legal-situation-and-tdm-opt-out)
44. [Cloudflare will now block AI bots from crawling its clients' websites by default](https://www.technologyreview.com/2025/07/01/1119498/cloudflare-will-now-by-default-block-ai-bots-from-crawling-its-clients-websites/)
45. [Cloudflare Blocks AI Crawlers by Default in 2026: What Changed and What to Do - Crawlora](https://crawlora.net/blog/cloudflare-ai-crawler-block-2026)
46. [New Instagram Policies Target Reposted Content](https://petapixel.com/2026/04/30/new-instagram-policies-target-reposted-content/)
47. [Instagram updates algorithm to benefit original creators](https://www.socialmediatoday.com/news/instagram-updates-algorithm-to-benefit-original-creators/819016/)
48. [Tyler Knott Gregson](https://en.wikipedia.org/wiki/Tyler_Knott_Gregson)
49. [Chasers of the light : poems from the typewriter series : Gregson, Tyler Knott, author : Free Download, Borrow, and Streaming : Internet Archive](https://archive.org/details/chasersoflightpo0000greg)
50. [Kate Baer takes critical Instagram messages and turns them into poetry](https://www.today.com/tmrw/kate-baer-takes-critical-instagram-messages-turns-them-poetry-t238081)
51. [I Hope This Finds You Well: Poems by Kate Baer, Paperback](https://www.barnesandnoble.com/w/i-hope-this-finds-you-well-kate-baer/1138786744)
52. [A brief history of my newspaper blackout poems](https://austinkleon.com/2014/04/29/a-brief-history-of-my-newspaper-blackout-poems/)
53. [Come on, world - Austin Kleon](https://austinkleon.com/category/newspaper-blackout-poems/page/2/)
54. [Episode XV. Poetry is the Original Blockchain](https://flash---art.com/2022/07/poetry-is-the-original-blockchain/)
55. [Sasha Stiles](https://en.wikipedia.org/wiki/Sasha_Stiles)
56. [Sasha Stiles](https://www.moma.org/artists/140170-sasha-stiles)
57. [🔁 AI-trained poet creates infinite poem that rewrites itself every hour](https://www.warpnews.org/artificial-intelligence/ai-trained-poet-creates-infinite-poem-that-rewrites-itself-every-hour/)
58. [Literary Hub » NFT poetry is definitely a thing coming to a blockchain near you.](https://lithub.com/nft-poetry-is-definitely-a-thing-coming-to-a-blockchain-near-you/)
59. [Where We Started & Where We’re Going](https://haikuists.com/pages/about-us)
60. [About 2 — The Traveling Typist](https://www.thetravelingtypist.com/extended-bio)
61. [A Poem Store Open For Business, In The Open Air](https://www.wamc.org/2012-04-17/a-poem-store-open-for-business-in-the-open-air)
62. [Artist Produces Poetry on Demand for Nelson-Atkins Museum](https://nelson-atkins.org/zach-houston/)
63. [World Poetry Day: On Instagram and TikTok, poetry finds a new lease of life - Yahoo News Singapore](https://sg.news.yahoo.com/world-poetry-day-instagram-tiktok-080052570.html)
64. [The Gorgeous Nothings by Emily Dickinson](https://www.ndbooks.com/book/the-gorgeous-nothings/)
65. [The Gorgeous Nothings by Emily Dickinson - The Rumpus](https://therumpus.net/2013/12/07/the-gorgeous-nothings-by-emily-dickinson/)
66. [In defense of Rupi Kaur and Instagram's “pop poets” - Quartz](https://qz.com/quartzy/1192915/in-defense-of-rupi-kaur-and-instagrams-pop-poets)
67. [Let’s Talk: Rupi Kaur, Instapoetry, and The Academy](https://wildwillowmagazine.com/2021/04/07/lets-talk-rupi-kaur-instapoetry-and-the-academy/)
68. [mitpressbookstore.mit.edu](https://mitpressbookstore.mit.edu/book/9780811221757)
69. [Studies in Scale](https://www.poetryfoundation.org/poetrymagazine/articles/70065/studies-in-scale)
70. [Leaves of Grass, Variorum Edition](https://whitmanarchive.org/item/encyclopedia_entry516)
71. [Leaves of Grass](https://en.wikipedia.org/wiki/Leaves_of_Grass)
72. [Memory](https://sigliopress.com/titles/memory-bernadette-mayer/)
73. [Poetry Has Found A New Audience On Social Media. You Shouldn't Sneer](https://www.countryandtownhouse.com/culture/poetry-gen-z-social-media/)
74. [Poetry sales soar as political millennials search for clarity](https://flipboard.com/@TheGuardian/poetry-sales-soar-as-political-millennials-search-for-clarity/f-fbf7f2577d%2Ftheguardian.com)
