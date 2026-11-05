# Locked Pages: Ciphers, Codes and Puzzle Play for the Handwritten Poetry Journal

The best way to add play to the journal is to make the artist's own hand the cipher alphabet: one scanned glyph sheet acts as "the key." Hang the puzzles off the weekly n/100 release so they unlock extras (marginalia, struck-through drafts, hidden lines, glyph lore) and never the poems themselves. Keep the Reserve completely offline, in any form, ciphered or not. The history backs this up. The ciphers that last (Z340, the Copiale, Kryptos) are handwritten or hand-made and turn out to be solvable. The artistic precedents that last (Masquerade, A Humument, Tunic) treat the puzzle as a second way of reading the art, not a toll gate in front of it.

## TL;DR

- **Build a "Key Sheet" system:** a substitution cipher drawn in his own handwriting, keyed to the fill-in glyph sheet. Add book ciphers keyed to journal page/line/word coordinates, an erasure layer over struck-through drafts, and a 100-poem metapuzzle. Every clue, key and hidden line is written by him. Code only handles checking and display.
- **Free work stays free; puzzles gate extras only.** Members get hints, solution archives and early keys. Print and Kickstarter editions get the physical layer (decoder card, cipher wheel, key booklet). No speed leaderboards. Solutions should be checked by encrypting the reveal content with the answer, so the answer never sits in page source.
- **Never encipher a Reserve poem online.** Strict journals count work that "appeared online for any reason" (Poetry) or "anything posted online," including Patreon-paywalled excerpts (Black Fox), as published. A cipher is just a reversible copy, and the Kryptos K4 saga shows that secrets leak through side doors. US copyright law is looser: display without authorized downloading generally isn't "publication." But that doesn't change what journals will do.

## Key Findings

1. **Handwritten ciphers are solvable and their solving is communal.** Z340 resisted for 51 years. On December 5, 2020 it fell to David Oranchak (US software developer), Sam Blake (Australian mathematician) and Jarl Van Eycke (Belgian programmer and author of AZdecrypt).\[1\] Blake generated 650,000 transposed variants of the ciphertext, which were run through AZdecrypt, and the FBI verified the result.\[1\]\[2\] The cipher was homophonic substitution layered with a diagonal transposition.\[3\] Discover Magazine reports Oranchak saying the cipher was "so computationally heavy … that no one in 1969 could likely have decoded the Zodiac's message — which suggests the killer didn't know just how difficult a code he'd created." For this project, that means a cipher built from his hand should combine one simple layer with one twist, not a wall.
2. **The "key" is what fascinates, and also what breaks.** Kryptos K4 (97 characters) was never cracked cryptographically.\[4\] In September 2025, journalists Jarett Kobek and Richard Byrne found the plaintext on taped-together scraps in Jim Sanborn's papers at the Smithsonian's Archives of American Art.\[5\]\[6\] According to RR Auction's own November 21, 2025 release, Sanborn's complete Kryptos archive, including the K4 solution (Lot #2001, "Decoding History" sale), sold for $962,500, well past its $300,000–$500,000 estimate. Anything locked online can be opened through a side door: source code, caches, a leaked key.\[7\] Design for that.
3. **Puzzle-art works that last use the puzzle as a lens.** Kit Williams' *Masquerade* (1979) sold over a million copies, but it also sent people digging up countryside, trespassing and stuck on cliffs.\[8\]\[9\] Its golden hare was claimed in 1982 by "Ken Thomas," a pseudonym for Dugald Thompson. The Sunday Times revealed in December 1988 that Thompson's business partner was dating Veronica Robertson, Williams' former girlfriend, who knew roughly where the hare was buried. In other words, it was found through insider information, not the intended solution. Physical treasure and cash prizes bring out the worst in a community. Tunic's collectible glyph manual and Chants of Sennaar's translation journal show the healthier pattern: decoding *is* the reading.\[10\]\[11\]
4. **Publication risk is asymmetric.** Rattle accepts self-posted poems but "does not accept work that includes machine-generated text," which fits his no-AI rule.\[12\] Poetry, Ploughshares, Kenyon and Black Fox treat any online appearance as publication.\[13\]\[14\]\[15\]\[16\] The Copyright Office generally does not treat display-only online posting as publication.\[17\] Plan for the strictest editor, not the copyright statute.
5. **The tooling is mature and open.** ipuz is an open JSON format with a cryptic-crossword kind.\[18\]\[19\] Exolve and frozenpandaman's *puz* play ipuz/.puz in the browser.\[20\]\[21\] Ingrid ships with the free Spread the Wordlist (302,841 scored answers, CC BY-NC-SA 4.0).\[22\]\[23\] WebCrypto handles answer-keyed encryption client-side.

## Details

### 1. Historical and cultural ground

**Vocabulary (for the interface and the footnotes).**
- *Plaintext* is the readable message. *Ciphertext* is its enciphered form.
- A *key* is the secret setting that turns one into the other.
- A *cipher* works on letters. A *code* replaces whole words or phrases via a *codebook*.
- A *nomenclator* is the early-modern hybrid: a cipher alphabet plus a short code list for names and common words.
- *Homophonic* substitution gives frequent letters several interchangeable symbols to flatten frequency analysis.
- *Transposition* keeps the letters but scrambles their order, for example along a *route* such as a spiral or diagonal.
- A *book cipher* points into a shared text by page/line/word numbers.
- *Steganography* hides the very existence of a message, for example inside an image.

**The Zodiac ciphers.** There are four ciphers attributed to the killer:
- Z408, solved in 1969 by Donald and Bettye Harden.\[3\]
- Z340, solved in 2020 (see above).\[24\]
- Z13 and Z32, still unsolved because they are too short to be determined uniquely.\[24\]

The Z340 solution was crowdsourced in the deep sense. The three solvers credited decades of others' groundwork, and Oranchak's long-running site and video series kept a public community working on it.\[25\] **Sensitivity:** these are communications from a man who murdered people, and the Z340 plaintext concerns "collecting slaves" for the afterlife.\[26\] Use the *look* of handwritten ciphertext as the influence: grids of strange glyphs, a single hand, a key. Do not use Zodiac iconography (the crosshair sign), Zodiac-style taunts, imitations of real ransom notes, or references to real victims. Cite the cipher history in an end note if needed, but don't brand the work with a killer.

**The Copiale cipher** is the closest historical cousin to this project: a beautiful handwritten book. Kevin Knight (USC), Beáta Megyesi and Christiane Schaefer (Uppsala) decoded it in 2011.\[27\] Their paper (ACL BUCC workshop, Portland, June 24, 2011) describes it as "105 pages long, containing about 75,000 handwritten characters," with "approximately 90 cipher letters" mixing Latin and Greek letters with invented glyphs. It turned out to be German homophonic substitution recording the rituals of an 18th-century "oculist" secret society.\[28\] Some tricks are worth borrowing:
- Unaccented Roman letters served as spaces (nulls).\[29\]
- "†" stood for the cluster "sch."\[30\]
- Special symbols stood for the society's own name, a nomenclator touch.\[30\]

**Voynich, Beale, Dorabella.**
- The Voynich manuscript (Beinecke MS 408, vellum carbon-dated to the early 15th century) is the archetype of the unreadable handwritten book. It is asemic in effect, whatever its origin.
- The Beale ciphers (pamphlet, 1885) consist of three number ciphers.\[31\] The second decodes as a book cipher keyed to the Declaration of Independence, which shows that numbers pointing into a text the reader already has form a natural cipher.
- Edward Elgar's Dorabella note (1897) is 87 little semicircle glyphs in one person's hand, written to a friend and still unsolved. It is the gentlest model of all: a private cipher between people who know each other.

**Somerton Man / Tamam Shud.** A man was found dead on Somerton beach, Adelaide, on 1 December 1948. A scrap in his fob pocket read "Tamám Shud" ("it is ended"), torn from a copy of FitzGerald's *Rubáiyát*. Pencilled letters in that copy remain undeciphered.\[32\] In 2022, Derek Abbott and genealogist Colleen Fitzpatrick identified him through DNA as Carl "Charles" Webb, though South Australia Police have not verified it.\[32\]\[33\] The poetic resonance is a poetry book carrying a code and the last words of a poem as a clue. But this is a real death, and it should be referenced, not played with.

**Ransom notes and cut-up collage.** The cut-and-pasted letter look is a visual idiom of anonymity: many hands, no hand. It descends from Dada collage and Burroughs/Gysin cut-ups. It inverts this project, which is one hand only. That inversion is usable: a "collage" puzzle that reassembles *his own* letters into a line. Avoid evoking real kidnapping cases.

**Cicada 3301 (2012–14).** It began on 4chan in January 2012.\[34\] The 2012 round chained several techniques:
- OutGuess steganography.\[35\]
- A book code on the *Mabinogion*.\[35\]
- A second book code on William Gibson's self-erasing poem *Agrippa*.\[34\]
- QR posters in cities on several continents.\[35\]
- PGP signatures (key 7A35090F) to authenticate every message.\[34\]

Two lessons follow. Signing or verifying official clues defeats impostors.\[36\] And "the first few there will receive the prize" bred leaks and resentment.\[37\]\[38\]

**Why handwriting reads as cryptic.** A personal hand is already a private cipher alphabet:
- Idiosyncratic letterforms (his weak X, Q, Z, V, K, G).
- Ambiguous pairs (u/n, a/o, l/1).
- Ligatures that hide letter boundaries.
- Strike-throughs that hide and reveal at once.

Legibility is a spectrum, and that spectrum is a difficulty dial. Transcriptions sit at one end, scans in the middle, glyph-only ciphers at the far end. The project's Hand↔Font view already *is* a decipherment interface.

### 2. Artists and writers who hid things

- **Armchair treasure hunts.** *Masquerade* (Jonathan Cape, 1979): a jewelled golden hare buried in Bedfordshire. The front of the book said "you must use your eyes." Physics teachers Mike Barker and John Rousseau solved it as intended.\[39\]\[40\] Byron Preiss's *The Secret* (1982) followed in the US with 12 buried casques. Only three have been found (Chicago 1983, Cleveland 2004, Boston 2019), and Wikipedia notes that "as of 2026, only three of the twelve boxes have been found." **Takeaway:** no buried objects, no cash, no geography.
- **Asemic and invented scripts.** Luigi Serafini's *Codex Seraphinianus* (1981) and Xu Bing's *Book from the Sky* (about 4,000 invented characters, hand-carved and printed, 1987–91) show that unreadable writing can be the art itself. That is the right frame for the later roots-and-glyphs phase.
- **Erasure and treated text.** Tom Phillips bought W. H. Mallock's *A Human Document* (1892) for threepence in 1966. He spent fifty years painting over its 367 pages to free a hidden story from the "wall of words," and the final edition came out from Thames & Hudson in 2016.\[41\]\[42\]\[43\] Mary Ruefle's erasures (*A Little White Shadow*) do the same with whiteout. His journal's own strike-throughs are a ready-made erasure substrate, and better, they are *his*.
- **Constraint and cipher in literature.**
  - Poe published cryptogram challenges and *The Gold-Bug* (1843).
  - Carroll closed *Through the Looking-Glass* with an acrostic poem spelling Alice Pleasance Liddell.
  - Oulipo (founded 1960) made constraint a generative method.
  - Nabokov's *Pale Fire* (1962) is a poem whose commentary becomes a hidden second story, a direct model for his footnotes and endnotes.
  - *S.* (Abrams/Dorst, 2013) and Nick Bantock's *Griffin & Sabine* (1991) put the plot in marginalia and removable inserts.
  - Jennifer Egan's PowerPoint chapter and serialized-tweet story show form as content.
- **Games.**
  - *Fez* (2012) hid an alphabet that the community decoded together.
  - *Tunic* (2022) scatters manual pages in a "trippy glyph language." Andrew Shouldice printed a real manual and then "folded it, ripped it, taped it, and stained it." Its pages are collectibles that teach.\[11\]\[44\]
  - *Chants of Sennaar* (Rundisc, 2023) auto-records each glyph in a journal and makes players confirm several translations at once to discourage brute force.\[10\]\[45\] That mechanic comes from *Return of the Obra Dinn*'s confirm-in-threes.\[46\] Its designers tuned difficulty by "the number of words that are likely to remain untranslated in the journal at any given time."\[47\]
  - *Heaven's Vault* (2019) inspired Sennaar's language mechanic.\[10\]
  - *The Witness* teaches a symbol grammar without words.
  - *Myst*'s journals and *Her Story*'s database search make reading the gameplay.
  - *Inscryption* extended into an ARG.
- **ARGs.** *I Love Bees* (2004) sent players to ringing payphones. *Year Zero* (2007) hid USB drives at concerts. They are powerful but logistically heavy, with safety and venue risks. A web journal can borrow the tone (found documents, time-released pages) without the field logistics.

### 3. Puzzle forms mapped to handwritten poems

| Form | How it uses the journal | Natural reveal |
|---|---|---|
| Monoalphabetic substitution in his glyphs | Each letter = a cropped glyph from his hand. The key = fill-in glyph sheet | A hidden marginal line or end-note sentence |
| Homophonic substitution | Several *real* instances of the same letter scanned from different pages act as homophones (Z340 / Copiale logic) | Hard-tier seasonal message |
| Transposition / route | Read a grid along the spiral or the page's own writing path | Order of a poem's drafts; a reordered stanza he writes |
| Book cipher | `page:line:word` coordinates into the 123 scanned pages, already addressable on the canvas | One sentence he composes from his own words |
| Erasure-reveal | Rub away overlay or strike-through to expose underlying words (Humument/Ruefle) | An erasure poem he makes from a draft |
| Crossword / cryptic | Grid fill from journal vocabulary. He writes every clue | Shaded squares spell the next poem's number or title |
| Acrostic / double-crostic | Clue answers' letters fill a quotation grid | A line from the week's poem; initials spell its title |
| Rebus | His drawings and doodles stand for syllables | Short phrase |
| Word search | Hidden words drawn from a poem's draft; leftover letters spell a message | Leftover-letter message |
| Anagram | Titles or lines scrambled; he chooses the anagram | Alternate title |
| Jigsaw / reassembly | Torn-edge fragments of the 2015 spreads | The complete spread plus its note |
| Redaction | Black bars over a transcription, lifted by solving | Withheld footnote |
| Metapuzzle / hunt | Each weekly answer feeds a seasonal meta (MIT Mystery Hunt structure) | Season title, print-edition reveal |

The **MIT Mystery Hunt** (begun around 1981 by Brad Schaefer) settled into rounds released over time since 1998. Each round's answers feed a metapuzzle, usually without instructions, and metas feed a final runaround. The 2014 Hunt had 115 puzzles and 10 metas.\[48\] The n/100 series maps neatly onto this: 10 "seasons" of 10 poems each, 10 metas, one metameta at poem 100.

**Cryptic clue conventions he should learn before writing any.** Ximenes (D. S. Macnutt, *Ximenes on the Art of the Crossword Puzzle*, 1966) holds that a fair clue has three parts: "a precise definition, a fair subsidiary indication, nothing else."\[49\]\[50\] Wordplay types each need an indicator: anagram, hidden word, container, reversal, homophone, charade, deletion, double definition, &lit. The definition sits at one end of the clue. Misleading surface meaning is fair; misleading grammar and punctuation are not.\[51\] US "Hexian" practice (Cox and Rathvon) adds concision.\[52\] His poetic ear is an asset here, because the surface reading of a cryptic clue is a tiny poem.

### 4. Game and interaction design

- **Locks tied to the weekly release.** Each poem ships free and whole. Alongside it ships one optional "lock": a puzzle whose solution opens a marginal layer, such as a struck-through line restored, a footnote, or a glyph added to the public key sheet. The key sheet visibly fills over the 100 weeks, Tunic-style, so the solving community literally assembles his alphabet.
- **Ethics of hiding.** Hide *apparatus*, never *art*. If a poem is only reachable by solving, the puzzle has become a paywall in costume and excludes the readers he most wants. Every lock should auto-open after a fixed window (say 4–8 weeks), so solvers get priority but no one is permanently shut out.
- **Difficulty curve and hints.** Run three tiers per week: an easy lock (book cipher), a medium one (crossword or crostic) and a rare hard one (homophonic). Use Sennaar's lever, the count of unknowns visible at once. Hints should be tiered nudges he writes in advance: "look at the margins" → "the numbers are page:line:word" → partial reveal. No free-text help bot, because that would put AI interpretive text on screen.
- **Community solving.** Z340, Fez and Cicada were all solved collectively. A Discord with per-puzzle spoiler channels and a delay before solutions are posted publicly suits this. Credit the first solvers by handle, opt-in, in the print edition's endnotes. That gives recognition without a race.
- **Leaderboards: no.** Speed boards reward spoiler-sharing and burnout, as Cicada's "first few" did. A personal, private "solved" stamp on the canvas is enough.
- **Participation.** Readers can submit solutions, and later their own ciphers *of his published poems* using the key sheet. That should wait until after poem 100 if the font stays exclusive: the key *sheet image* can be public while the font file stays private. A "cipher exchange" gallery lets the community write back in his alphabet.
- **Accessibility.**
  - Every glyph cipher also needs a token version, e.g. "glyph 14, glyph 3…", announced by screen readers. That keeps the logic identical without giving the plaintext away.
  - Crosswords need an ARIA grid that announces row, column, cell contents and clue. The APH accessible crossword is a working model.\[53\]
  - Never encode information only by colour.\[54\]
  - No timers.
  - A toggle from scan to clean type for dyslexic readers, applied to clues rather than to the cipher itself.
  - Full keyboard play.
  - The "menus hidden until tap" rule must also respond to keyboard focus and screen-reader landmarks.

### 5. Business model and publication rules

- **Member layer ($5/mo):** graduated hints, the full solution archive, early access to each week's key-sheet glyph, and the writing-circle's live "solve-along." The puzzles themselves stay free, so the free series remains whole.
- **Print editions:** each numbered print can carry a physical key. Options include a decoder card in his glyphs, a two-ring cipher wheel (his alphabet against A–Z), a translucent overlay that "erases" a printed page Humument-style, or a small key booklet. A **Kickstarter** after poem 100 is the natural home for a facsimile with a sealed key envelope and the full metameta solution.
- **Font exclusivity:** cipher puzzles can use *cropped scans* of his glyphs as images, so the font file never ships during the series.
- **Reserve poems: no cipher, no hint, no fragment online.** The strict-journal evidence:
  - Poetry magazine: "Work that has appeared online for any reason, including social media posts, is considered previously published."\[15\]
  - Ploughshares: "Material that has appeared in any publication, print or web, would be considered previously published. This includes self-published work."\[13\]
  - Black Fox, answering a question about Patreon-paywalled work: "this includes anything posted online." And on excerpts: "the excerpt is considered published."\[16\]
  - Writer's Digest (Robert Lee Brewer) warns that for many editors "a poem posted anywhere counts as publication, whether it's posted in a public forum or blog, or even a private, password-protected location online."\[55\]
  - No journal found addresses encrypted text. But a cipher is a reversible transformation of the full text, and the Kryptos K4 story shows solutions escape through archives and side doors.
  - Treat a ciphered Reserve poem as published.
- **US copyright (informational, not legal advice).** Compendium (Third) §1008.3 says the Office "considers a work 'published' when it is made available online if the copyright owner authorizes the end user to retain copies." It also says "the mere fact that a work is disclosed on the internet does not 'publish' the work." Factors include download buttons and technical barriers to copying.\[17\] So ciphered or display-only text likely isn't "published" for registration purposes. This matters for registration dates, not for journals. Register the n/100 series as it goes, using the Office's rules for published or unpublished works as appropriate.
- **Rattle** remains the friendly venue for poems that have appeared on his own site: "poems may be self-published on social media, blogs, or message boards."\[12\] It also bars machine-generated text, consistent with his rule.\[12\]

### 6. Implementation

- **Glyph rendering on canvas.** Build the cipher alphabet from *cropped scan sprites*: several per letter, taken from different pages, giving true homophones and true handwriting variation. A texture atlas plus a JSON map `{glyphId: [spriteRects]}` renders fast in the existing zoomable canvas. If font-based, put cipher glyphs in a separate small "key" font, mapping plaintext to Private Use Area codepoints, so canvas `fillText` works without relying on OpenType feature support in the Canvas 2D API. Keep `calt`/`salt` alternates for the HTML book side, where `font-feature-settings` is available. Subset and serve WOFF2. Load with `document.fonts.load()` before drawing.
- **Crosswords.**
  - Author in **Ingrid** (free desktop, ships Spread the Wordlist), **Phil** or **Crosshare** (browser), or paid **CrossFire**.\[56\]\[57\] Load a custom word list generated from his transcriptions so the fill comes from his vocabulary.\[22\]
  - Treat autofill as technical, but he should approve every entry and write every clue.
  - Export **ipuz** (open JSON, Creative Commons spec; crossword, cryptic and diagramless kinds).\[19\]\[58\]
  - Play it with **Exolve** (MIT-licensed; reads ipuz/.puz; has an embedder) or the *puz* fork (mobile layout, rebus cells).\[20\]\[21\]
  - Restyle the player to his hand, hidden chrome, tap-to-reveal.
- **Answer checking without leaking answers.**
  1. *Weak:* compare a salted SHA-256 hash client-side. Short answers can be brute-forced from a dictionary, so this suits only casual locks.
  2. *Recommended:* **answer-as-key**. Derive an AES-GCM key from the normalized answer (NFKC, lowercase, strip spaces) with PBKDF2 or Argon2 and a per-puzzle salt, and encrypt the reveal content. A wrong answer simply fails to decrypt, and the plaintext never appears in source. This is the same principle as a sealed envelope.
  3. *Metas and anything with credit:* a tiny server check (e.g., a serverless function) with rate limiting and logs. A public open-source puzzle project's issue tracker shows why: published hashes can be replayed by anyone who reads them, so bind checks to a session if credit matters.\[59\]\[60\]
  4. For trust, publish a salted answer fingerprint *before* release and the salt after, so solvers can verify the answer never changed (commit–reveal).\[61\]
- **Hints:** prewritten, time- or attempt-gated, served the same way (encrypted until unlocked).
- **Touch.** Long-press to inspect a glyph. Drag-to-place for jigsaw fragments with snap tolerance. A scrubbable erasure brush with an undo. A large-target letter wheel for cipher entry on phones. Avoid the native keyboard covering the grid by using an on-canvas keypad.

## Recommendations — ranked proposals

| # | Mechanic | What it reveals | Difficulty | Build effort | His authorship | Phase |
|---|---|---|---|---|---|---|
| 1 | **The Key Sheet**: weekly substitution cipher in his glyphs. Each solve adds one confirmed letter to a public key sheet | One hidden marginal sentence per week; the alphabet itself, assembled over 100 weeks | Easy → medium | Low–medium (sprite atlas, answer-as-key) | He writes every hidden sentence; he draws the missing glyphs on the fill-in sheet | Series launch |
| 2 | **Page:Line:Word book cipher** into the 123 scanned pages, solved by navigating the spiral canvas | A line he composes from his own 2014–15 words | Easy | Low (coordinates already exist) | He composes every message and number string | Launch / during |
| 3 | **Revisions dig**: erasure-reveal over struck-through drafts in version stacks; occasional Humument-style erasure poems | Restored struck lines; his erasure poems | Easy | Medium (mask/brush layer) | He chooses every erasure | During the 100 |
| 4 | **Ten seasons, ten metas, one metameta** (Mystery Hunt structure) | Season titles; at #100, the collected edition's title or Kickstarter launch | Medium–hard | Medium (state, server check) | He designs all metas and answers | Spans the 100 |
| 5 | **Monthly crossword** (plus occasional cryptic) from journal vocabulary, ipuz + Exolve | Shaded squares spell the next poem's number or a footnote | Medium | Low (existing tools) | All clues his; fill approved by him | During the 100 |
| 6 | **Double-crostic per season** | A line from that season's poems; initials spell its title | Medium | Medium | All clues his | During the 100 |
| 7 | **Torn 2015 spreads**: reassembly jigsaw | Complete spread plus his note | Easy–medium | Medium (fragment cutting, snapping) | Notes his | During / after |
| 8 | **Physical key**: decoder card / cipher wheel / overlay in numbered prints and Kickstarter tiers | Print-only layer unlocking an online bonus | Varies | Medium (production) | Designs his | After 100 (Kickstarter) |
| 9 | **The homophonic "hard" cipher**: multiple real instances per letter, plus a spiral transposition | A longer message he writes, the community's big collective solve | Hard | Medium | Message his | Once per season, from mid-series |
| 10 | **Glyph decipherment journal** (Sennaar-style) for the roots-and-glyphs phase with LingFrame | His language broken to roots; reader-built glossary | Medium–hard | High | All glyph meanings his | Later phase |

**Do first:** #1 and #2 at launch. They need only the existing canvas, the fill-in glyph sheet and an answer-as-key module, and they make his handwriting the protagonist.

## Caveats

- Several facts come from secondary sources. One Scientific American piece gives K4 as "79" letters, apparently a typo for the widely reported 97.\[62\] The Somerton identification is unverified by police.\[63\] The Paris Review policy came only via secondary quotes.\[64\] The Kryptos sale price ($962,500) comes from RR Auction's own release.
- Publication and copyright points are informational, not legal advice. Individual editors vary, so check each target journal's current guidelines before submitting.
- Client-side locks are only as strong as the answer is long. Assume any casual lock can be brute-forced and never lock anything he'd regret seeing early.
- Puzzle communities can generate harassment and entitlement. Williams received "tens of thousands of letters" from Masquerade hunters, and AP reported that Sanborn got so many Kryptos inquiries he started charging $50 per submission. Set boundaries publicly: no prizes, no geography, solutions auto-release.

## Open questions for the artist

1. Should locks ever be permanent, or should everything auto-open after a window? (Recommended: auto-open.)
2. Will the key sheet use scan sprites (font stays exclusive) or the font itself after poem 100?
3. How much true-crime resonance does he want named in end notes, versus keeping it as private inspiration?
4. Does the 100-poem metameta reveal something he'd otherwise announce (book title, Kickstarter date, new identity name)?
5. Is he willing to learn Ximenean cryptic clueing, or keep to American-style clues and crostics?
6. Should first solvers be credited in print editions (opt-in), and should member-tier hints exist at all?
7. May readers encipher his *published* poems in his alphabet, and when?
8. Which strike-throughs are off-limits? Some deletions may be private, and the Revisions dig needs his veto list.

## Sources

1. [FBI confirms Zodiac Killer's 340 cipher solved by trio of amateur math and software codebreakers](https://www.theregister.com/offbeat/2020/12/12/fbi-confirms-zodiac-killers-340-cipher-solved-by-trio-of-amateur-math-and-software-codebreakers/1506059)
2. [BREAKING NEWS: The Zodiac’s “340 Cipher” has been solved |](https://zodiackillerfacts.com/news-and-updates/breaking-news-the-zodiacs-340-cipher-has-been-solved/)
3. [Zodiac Cipher — The Cipher Museum](https://ciphermuseum.com/ciphers/zodiac.html)
4. [Kryptos K4 Solution: Reconstructed Plaintext](https://solvekryptos.com/solution)
5. [A Solution to the CIA’s Kryptos Code Is Found after 35 Years](https://www.scientificamerican.com/article/a-solution-to-the-cias-kryptos-code-is-found-after-35-years/)
6. [What Is Kryptos? The CIA Sculpture & Its Four Encrypted Messages](https://solvekryptos.com/about)
7. [How the CIA’s Kryptos Sculpture Gave Up Its Final Secret](https://www.scientificamerican.com/article/how-the-cias-kryptos-sculpture-gave-up-its-final-secret/)
8. [3 of History's Most Fascinating Armchair Treasure Hunts (Plus One You Can Try Yourself)](https://www.mentalfloss.com/history/historys-greatest-armchair-treasure-hunts)
9. [Masquerade (book)](<https://en.wikipedia.org/wiki/Masquerade_(book)>)
10. [The hero of this new video game is a translator](https://www.axios.com/2023/09/08/chants-of-sennaar-rundisc-interview)
11. [Tunic: The game's designer Andrew Shouldice interview](https://www.redbull.com/us-en/tunic-video-game-developer-interview)
12. [Regular Submission Guidelines - Rattle: Poetry](https://rattle.com/page/submissions/)
13. [FAQ - Ploughshares](https://pshares.org/faq/)
14. [The Kenyon Review](https://writersweekly.com/paying-markets/the-kenyon-review)
15. [How to Submit](https://www.poetryfoundation.org/poetrymagazine/submit)
16. [Submit](https://blackfoxlitmag.com/submit/)
17. <https://copyright.gov/comp3/chap1000/ch1000-websites.pdf>
18. [Exporting puzzles](https://www.crossword-compiler.com/en/help/html/exportingpuzzles.htm)
19. [IPUZ](http://www.ipuz.org/)
20. [GitHub - viresh-ratnakar/exolve: Online interactive crossword software in JavaScript · GitHub](https://github.com/viresh-ratnakar/exolve)
21. [GitHub - frozenpandaman/puz: In-browser crossword puzzle player · GitHub](https://github.com/frozenpandaman/puz)
22. [GitHub - rf-/ingrid\_core: Crossword-generating library and CLI tool · GitHub](https://github.com/rf-/ingrid_core)
23. [spread the word(list)](https://www.spreadthewordlist.com/)
24. [The Zodiac Killer Ciphers: How Z340 Was Solved After 51 Years](https://www.cipherdecipher.com/blog/zodiac-killer-ciphers)
25. [The Zodiac Killer’s Infamous Z340 Cipher Has Been Solved More Than 50 Years After His Chilling Murders Took Place](https://allthatsinteresting.com/zodiac-killer-z340-cipher-solved)
26. [Decoding the Zodiac Killer's Z340 Cipher](https://www.emergentmind.com/papers/2403.17350)
27. [Copiale Cipher (Germany, 1730-1760) — Translate Online](https://www.cipherchronicle.com/en/methods/copiale)
28. [Copiale Cipher — The Cipher Museum](https://ciphermuseum.com/ciphers/copiale.html)
29. [The Copiale Cipher\* Kevin Knight Beáta Megyesi and Christiane Schaefer](https://mt-archive.net/BUCC-2011-Knight-2.pdf)
30. [Copiale cipher](https://en.wikipedia.org/wiki/Copiale_cipher)
31. [Solving Historical Dictionary Codes with a Neural Language Model](https://arxiv.org/pdf/2010.04746)
32. [Somerton Man Code — The Cipher Museum](https://ciphermuseum.com/ciphers/somerton-man.html)
33. [Tamam Shud case](https://simple.wikipedia.org/wiki/Tamam_Shud_case)
34. [Cicada 3301 First Puzzle Walkthrough](https://www.boxentriq.com/guides/cicada-3301-first-puzzle-walkthrough)
35. [Cicada 3301 — The Cipher Museum](https://ciphermuseum.com/ciphers/cicada-3301.html)
36. [Cicada 3301: The Internet's Biggest Mystery](https://stationoneohone.substack.com/p/cicada-3301-the-internets-mystery)
37. [What Happened (2012)](<https://uncovering-cicada.fandom.com/wiki/What_Happened_(2012)>)
38. [Cicada 3301 Explained: Part 1, 2012 — Steemit](https://steemit.com/puzzle/@meus/cicada-3301-explained-part-1-2012)
39. [40 Years of Armchair Treasure Hunts and How the First One, Masquerade, Was Solved - Mysterious Writings](https://mysteriouswritings.com/the-masquerade-treasure-hunt-solution/)
40. [The Armchair Treasure Hunt Club - Masquerade](https://www.treasureclub.net/publichunts/masquerade/index.html)
41. [Tom Phillips: A Humument](https://www.oeln.net/tom-phillips-humument)
42. [A humument : a treated Victorian novel](https://search.worldcat.org/title/961308855)
43. [A Humument - Final Edition](https://www.flowersgallery.com/shop/publications/135-a-humument-final-edition-tom-phillips/)
44. [The creation of Tunic’s invaluable in-game manual](https://blog.playstation.com/2022/09/21/the-creation-of-tunics-invaluable-in-game-manual/)
45. [Chants of Sennaar: Julien Moya on Imaginary Language Design](https://berkeleyhistoricalsociety.org/chants-of-sennaar-creator/)
46. [Meaningless Magazine](https://meaninglessmagazine.substack.com/p/coming-soon)
47. [Immersing players in the culture of a people with language puzzler Chants of Sennaar](https://www.gamedeveloper.com/design/immersing-players-in-the-culture-of-a-people-with-language-puzzler-chants-of-sennaar)
48. [MIT Mystery Hunt - Wikiwand](https://www.wikiwand.com/en/MIT_Mystery_Hunt)
49. [Cryptic crossword](https://en.wikipedia.org/wiki/Cryptic_crossword)
50. [Cryptic Crossword Solver](https://www.cipherdecipher.com/tools/cryptic-crossword-solver)
51. [Point of order on a Ximenean principle by KT17](https://www.crosswordsolver.org/forum/735484/point-of-order-on-a-ximenean-principle/)
52. [Cryptic Crosswords Constructors' Glossary](https://www.leftfieldcryptics.com/glossary.html)
53. [APH Accessible Crossword Puzzle App Review](https://www.perkins.org/resource/aph-accessible-crossword-puzzle-app-review/)
54. [Puzzle Game Accessibility: Making Games Inclusive for All Players](https://onlinepuzzles.org/blog/puzzle-game-accessibility-making-games-inclusive-all-players)
55. [Poetry FAQs: When is something considered published?](https://www.writersdigest.com/personal-updates/poetry-faqs-when-is-something-considered-published)
56. [Tools for solving and construction - Signals](https://signals.mysteryleague.com/tools/)
57. [Resources](https://grid-alchemy.com/resources/)
58. [crosswords-js/docs/puzzle-formats/ipuz.md at main · dwmkerr/crosswords-js · GitHub](https://github.com/dwmkerr/crosswords-js/blob/main/docs/puzzle-formats/ipuz.md)
59. [feat(puzzles): add deterministic solution checker with rate limiting by Penielka · Pull Request #868 · UnityChainxx/StellarHunts · GitHub](https://github.com/UnityChainxx/StellarHunts/pull/868)
60. [hunty-core: submit\_answer\_with\_hash lets anyone who reads the ledger complete a clue without knowing the answer · Issue #810 · Samuel1-ona/Hunty-contract · GitHub](https://github.com/Samuel1-ona/Hunty-contract/issues/810)
61. [GitHub - ProofOfSolve/puzzles: BTC Puzzles · GitHub](https://github.com/ProofOfSolve/puzzles)
62. [CIA Kryptos Puzzle Creator Releases Final Clues](https://www.scientificamerican.com/article/cia-kryptos-puzzle-creator-releases-final-clues/)
63. [Derek Abbott](https://en.wikipedia.org/wiki/Derek_Abbott)
64. [Poetry Submissions: Top Places To Submit Your Poems in 2026](https://blog.reedsy.com/guide/poetry/submissions/)
