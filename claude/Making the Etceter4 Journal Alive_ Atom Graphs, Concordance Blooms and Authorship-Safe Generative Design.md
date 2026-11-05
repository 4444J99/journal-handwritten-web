# Making the Journal "Alive": Research Avenues for the Next Phase of the Etceter4 Journal Piece

The strongest next phase uses the author's own scans as the only source of material. Build one stand-off "atom graph" that links every unit, from glyph to archive, to both its transcribed text and its pixel region on the scan. Then add a seeded, rule-based modulation layer driven mostly by signals that need no permission prompt (time, date, season, touch, dwell, return visits). Make tap-triggered "concordance blooms" the signature interaction, built from crops of the same word, root or letter elsewhere in the journal. Gyroscope, weather and location work best as optional, opt-in enrichments, not as the foundation. iOS Safari blocks or limits most of them: motion needs a user-gesture permission prompt, the Generic Sensor and Ambient Light APIs are unavailable, and rendering is held near 60 fps and dropped to 30 fps in Low Power Mode.\[1\] The authorship rule draws a usable bright line. Permutation, selection and re-placement of his existing units keep every displayed string his. Markov chains and n-grams over his corpus produce sequences he never wrote, so they sit in a grey zone he must rule on explicitly. LLM generation is excluded outright.

## TL;DR

- **Build the data model first.** Make every unit, from glyph up to the whole archive, addressable, with stand-off annotation linking each to a scan region. This is the foundation that makes recursion, remix and "blooms" possible. TEI's facsimile/zone model and HTR forced alignment (Kraken) are the proven precedents, and the existing line-level bounding boxes are a strong starting point.
- **Make "alive" mostly permission-free.** Seeded randomness plus time, date and season, touch velocity, dwell time and return-visit state give per-visit difference with no prompts, as in Eno and Chilvers' *Reflection*, whose rules shift with the time of day. On iOS, gyroscope requires `DeviceOrientationEvent.requestPermission()` from a user gesture. AmbientLightSensor ships in no browser by default. Weather via Open-Meteo is keyless and CORS-enabled but needs coordinates, so coarse, opt-in location is the privacy-preserving route.
- **Keep generation to rearrangement.** Permutation, concordance selection and Queneau-style slot substitution draw only on his corpus. Rule now on whether Markov or n-gram recombination counts as "machine-authored", because it creates new word sequences. Enforce the Reserve at the data-build level so no Reserve atom ever ships to the client.

## Key Findings

1. **No single hierarchy will hold this text.** The OHCO thesis says text is "an ordered hierarchy of content objects". Its own authors retreated from it in 1993 because of overlapping hierarchies such as enjambment, where a sentence crosses the verse line.\[2\] A poem's sentence, verse, stanza, page and draft layers overlap. Stand-off annotation (each layer as ranges over one base sequence) is the right model, not nested XML or JSON trees.
2. **The scan-to-text link is a solved pattern at the line level, and a tractable one below it.** TEI's `<facsimile>/<surface>/<zone>` with `@facs` pointers lets "any element in a transcription" point to an image region.\[3\] Kraken outputs "word bounding boxes and character cuts" and supports forced alignment of a known transcription "producing approximate character locations".\[4\]\[5\] That suits a corpus already transcribed line by line.
3. **iOS Safari is the binding constraint.** Motion and orientation need a permission prompt that "must be called from within a user gesture".\[1\] The Generic Sensor API (Gyroscope, Accelerometer classes) is not supported in Safari.\[6\] Ambient Light "is not available by default in any browser engine".\[7\] WebGPU shipped in Safari 26.0 (September 2025), but Safari still renders "near 60fps" by default and throttles requestAnimationFrame to 30 fps in Low Power Mode.\[8\]\[9\]\[10\]
4. **Precedents favour constrained recombination of a fixed source.** Queneau (10 sonnets → 10^14 poems),\[11\]\[12\] Stefans' *The Dreamlife of Letters* (an alphabetised list of another writer's words, animated), Cayley's transliteral morphing (letter-by-letter transitions between texts he wrote or translated) and Eno's *Reflection* (rules that change with time of day) all generate variety without writing new language.\[13\]\[14\]\[15\]\[16\] Recent award-winning work moved toward LLMs. The ELO's 2025 announcement said of the Coover winner, benjamin escalonilla godayol's *Espejo de Carne*: "Artistically, the work uses LLMs well, though such tools bring with them their own implications within a work positioned as a feminist text." That makes this project's no-LLM stance a distinct position.
5. **Copyright favours his approach.** The US Copyright Office (Jan 2025) confirms protection for human-authored material that stays perceptible and for creative "selection, coordination, or arrangement".\[17\]\[18\] Purely machine-determined expression is excluded.\[19\] Rearrangements of his own text do not weaken registration of the source poems.

## Details by Avenue

### Avenue 1 — Data model: the nested "atom graph"

**What it is.** One canonical base layer per page: the transcribed character stream with stable offsets, plus scan pixel geometry. Every other unit is a stand-off annotation pointing into that base: glyph, grapheme, syllable, morph (root, stem, affix), word, line, sentence, verse, stanza, poem, piece, version, page and archive. Each annotation carries (a) a character range, (b) a scan region (bbox or polygon) and (c) a parent pointer for each hierarchy it belongs to. Overlap is allowed because each hierarchy is a separate annotation layer.

**Why stand-off rather than nesting.** DeRose, Durand, Mylonas and Renear argued in 1990 that text "is best represented as an ordered hierarchy of content object (OHCO), because that is what text really is".\[20\] The 1993 revision ("Refining our Notion of What Text Really Is") conceded that "there is no unique logical hierarchy" and listed enjambment among the counterexamples. Each perspective is its own OHCO, and perspectives overlap.\[21\]\[22\] Wendell Piez (Balisage 2013) notes that a data model imposing a single hierarchy hampers exactly the questions this piece wants to ask.\[23\] For a poetry journal, sentence vs. verse line, stanza vs. page break, and struck-through vs. inserted text are all overlapping structures.

**Scan linkage at every level.** TEI P5 chapter 11/12 ("Representation of Primary Sources") gives the vocabulary. `<surface>` defines a coordinate space for a page. `<zone>` defines any two-dimensional area within it, nestable and with polygon `@points`. The `facs` attribute "is used to associate any element in a transcription with an image of the corresponding part of the source". `<sourceDoc>` supports a documentary transcription organised by `<line>` and nested zones.\[3\]\[24\]\[25\] The existing journal.json (pages → blocks → lines with normalized boxes) already maps onto surface → zone → line. Strikeouts and insertions map to TEI `<del>`/`<add>`/`<subst>`, and uncertain or illegible readings to `<unclear>`/`<gap>`. TEI need not be the runtime format. It can be an export or archival format, with a compact JSON stand-off store for the browser.

**Getting below the line (word, letter, glyph regions).**
- *Forced alignment (recommended).* Kraken's Python API offers forced alignment: "aligning a given transcription to the output of a text recognition model, producing approximate character locations… e.g., to produce word bounding boxes for a known good transcription". Kraken outputs ALTO and PageXML with "word bounding boxes and character cuts" and is trainable on a single hand.\[5\]\[26\] Caveat from a 2026 open-source integration: CTC cuts mark "where a character was emitted, not its edges". In that project, naive boxes "clipped the first and last letter of 1,910 of 1,928 words".\[27\] Budget for padding, connected-component snapping and manual correction.
- *Transkribus / TrOCR.* Transkribus (hosted) and TrOCR (transformer line recognizer) can also recognise text. They are recognizers, though. Since the text is already transcribed, alignment matters more than recognition. Any recognizer used only to locate characters does not put machine text on screen, because the displayed text stays his transcription.
- *Manual glyph harvesting.* For the font fill-in and for sprite atlases, a semi-manual tool (click letter boundaries on a line crop) gives exact atoms for the highest-value pages first.

**Linguistic layers.** Morfessor 2.0 is an unsupervised, language-agnostic segmenter that "tends to undersegment" when trained on a large corpus.\[28\] A journal-sized corpus will need tuning and, ideally, semi-supervised annotations (Morfessor supports these). His LingFrame / linguistic-atomization repos can supply a curated root and stem layer, and that layer should be human-reviewed because it becomes part of the work's structure. A CMU Pronouncing Dictionary layer (phonemes, stress) supports syllable and rhyme atoms. Allison Parrish's phonetic feature-bigram vectors place words or lines in a "sound similarity" space, which is useful for selecting neighbours from his own corpus without producing new words.\[29\]\[30\]

**Recursion support.** Because every unit has an ID and a scan region, "a poem containing its own lines as zoomable sub-poems" is just a render rule: unit U displays children C, and any child can be expanded into its own field. Version stacks are another annotation layer (version-of links between line IDs across drafts).

**Effort:** Medium–High (alignment and QA dominate). **Fit:** excellent, since it extends journal.json without breaking v4. **Risk:** alignment errors on cursive joins, and morph segmentation quality. **Browser:** n/a (build-time).

### Avenue 2 — Sensing and context ("every visit different")

| Signal | API / source | Status late 2026 | Permission | Recommended role |
|---|---|---|---|---|
| Seeded randomness | PRNG seeded per visit (shareable seed in URL hash) | Universal | None | Foundation; enables reproducible or shareable visits |
| Time of day, date, season | `Date`, `Intl` timezone | Universal | None | Primary "alive" driver |
| Return-visit state | `localStorage` (counts, last seed; no PII) | Universal | None (disclose) | Piece "remembers" a returning viewer |
| Touch/scroll velocity, dwell | Pointer events, rAF timing | Universal | None | Primary interaction driver |
| Light/dark, reduced motion | `prefers-color-scheme`, `prefers-reduced-motion` | Widely supported | None | Must honour |
| Device orientation/motion | `DeviceOrientationEvent` / `DeviceMotionEvent` | Secure context only; iOS requires `requestPermission()` inside a user gesture\[1\]\[31\] | Prompt on iOS | Opt-in enrichment |
| Generic Sensor (Gyroscope, Accelerometer classes) | W3C Generic Sensor | Chrome-family only; not supported in Safari\[6\]\[32\] | — | Avoid |
| Ambient light | `AmbientLightSensor` | "not available by default in any browser engine" (W3C WD, May 2026)\[7\] | — | Do not plan on it |
| Microphone level | `getUserMedia` + Web Audio `AnalyserNode` | Supported | Prompt, high-friction | Optional, compute on-device, never record |
| Location | Geolocation API | Supported | Prompt | Opt-in; round coordinates |
| Weather | Open-Meteo | Keyless, CORS, free non-commercial <10,000 calls/day\[33\]\[34\] | Needs lat/long | Opt-in via coarse location, or a fixed author-chosen place |

**iOS specifics.** MDN states that both `requestPermission()` methods "return a Promise that resolves with 'granted' or 'denied', and both must be called from within a user gesture".\[1\] The W3C Device Orientation spec (CR Draft, Feb 2025) now restricts all interfaces to secure contexts and requires express permission.\[31\] A three.js GitHub issue (#17713, iOS 13 Safari) reports that "once you've permitted (or denied) controls, it won't ask again (even in new tabs) until you restart safari". An Apple Developer Forums thread (#128376) agrees: "On reloading the page the permission (granted, denied) is still cached." The first-tap moment matters for this reason. The piece already hides controls until tapped, so the first tap can double as the motion-permission gesture, with one revealable, author-written invitation. The tap must not produce machine-written text.

**Weather without exposing the viewer.** Open-Meteo requires no API key, supports CORS and sets "no ads, no tracking, not even cookies". It still needs latitude and longitude, and its terms note it "may collect non-personal information, such as IP addresses".\[33\]\[34\] Privacy-preserving patterns: (1) round coordinates to ~0.1° (~11 km) or a city grid before the request; (2) make the request client-side so your server never sees location; (3) never store it; (4) a no-permission alternative is the weather at a place the author chooses (for example where the journal was written). That replaces viewer-specific context with an authored one, and the trade-off is worth stating to the author. Server-side IP geolocation is coarse and needs no prompt, but it routes viewer IPs through your infrastructure, and the author should decide explicitly whether that is acceptable. Commercial use (for example a paid edition) would require an Open-Meteo subscription.\[34\]

**Precedents.** Eno and Chilvers' *Reflection* app: "the rules themselves could change with the time of day. The harmony is brighter in the morning, transitioning gradually over the afternoon to reach the original key by evening".\[15\] Chilvers later said the rules were fixed "at the end of 2017, once the first four seasons had played out".\[35\] *Bloom* (2008) pairs tap-to-create with a generative player "when Bloom is left idle".\[36\] That is a direct model for "alive at rest, responsive on tap". ELC Volume 4 (132 works, 31 languages) includes "geospatial storytelling via mobile phones", useful as a locative reference set.\[37\] Janet Cardiff's walks, Teri Rueb's GPS sound works, Björk's *Biophilia* and Radiohead's *PolyFauna* are commonly cited locative and generative-app references. They were not re-verified in this pass.

**Declined permissions.** Design the permissionless tier to be complete on its own: time, season, seed, touch physics, dwell and memory. Permissions should add texture, not unlock the "real" piece. If motion is declined, map pointer or touch drag to the same parallax and tilt parameters.

**Effort:** Low (time, seed, touch) to Medium (permission flows, weather). **Fit:** high, since v4 already regenerates arrangements per visit. **Risk:** permission fatigue, iOS caching of denial, motion sickness from tilt.

### Avenue 3 — Tap-triggered animations and "concordance blooms"

**Core idea.** On tap, query the atom graph for related units and animate them out from the tapped unit: other occurrences of the same word form, the same root or stem, the same letter or glyph, other versions of the same line, and phonetic neighbours. Every populated element is a crop of his scan or a render in his font. Nothing new is written.

**Bloom data sources, ranked by authorship safety:**
1. Same-glyph crops (all instances of a letter across 123 pages). Purely visual, safest.
2. Same word form or lemma occurrences, as line crops with the match highlighted.
3. Version-stack siblings (the same line in other drafts). Directly authored variation.
4. Same root or stem (needs the morph layer).
5. Phonetic or semantic neighbours. Still his words, but the selection is algorithmic, so document the rule.

**Rendering techniques.**
- *Scan-crop sprites (recommended primary).* Pack glyph and word crops into texture atlases and animate them as sprites. This keeps the real hand (ink texture, pressure, strikeouts) and is the most faithful option.
- *Handwriting stroke animation.* SVG `stroke-dashoffset` reveals need centerline paths. Potrace traces outlines, which "has a boundary along both sides". AutoTrace's `-centerline` mode, also built into Inkscape 1.x, traces single strokes. A 2026 survey notes classical tracers "often produce fragmented paths".\[38\]\[39\]\[40\] Stroke *order* cannot be recovered from a raster reliably, so any "being written" animation is a reconstruction and should be treated as an aesthetic choice, not a document of how he wrote.
- *Font-based (Etceter4 Diary).* Cheap, flexible and morphable. It is a stylisation of his hand, not the hand itself, and weak glyphs (X, digits, Q Z V K G) will be visible in blooms until the fill-in sheet is done.
- *Motion vocabularies.* Particles (letters as particles), boids or flocking, flow fields, physics (Matter.js or similar), L-system branching of units, and Cayley-style transliteral morphing. Cayley's morphs step through a sound-ordered 28-character loop, "fourteen steps" maximum per letter. Liza Daly's *A Physical Book* (ELC4) applies gravity and friction to a digitised book's letters and is a close precedent for physics-on-letters.\[14\]\[41\] Glyph-to-glyph morphing via path interpolation (flubber-style) needs vector outlines (font or traced).

**Effort:** Medium. **Fit:** high. v4 already has zoom down to the line level, so blooms extend that zoom downward. **Risk:** visual clutter, performance with many sprites, and crop quality.

### Avenue 4 — Generative and remix rules (authorship-graded)

| Technique | Output | Any new word sequence? | Status under "no AI-written text" | Notes |
|---|---|---|---|---|
| Re-arrangement in space (scatter, spiral, by-poem; current v4) | Original units relocated | No | Clearly compliant | Already shipped |
| Concordance selection (blooms) | Existing units retrieved by rule | No | Compliant | Rule is authored, content is his |
| Version cycling or morphing between his drafts | His existing variants | No (transitions only) | Compliant | Cayley transliteral morph precedent |
| Slot substitution (Queneau) | Lines swapped between parallel poems at matching positions | Yes, but from author-designed slots | Compliant if he designs the slots | Queneau: 10 sonnets × 14 lines = 10^14\[12\]\[42\]\[43\] |
| Alphabetic or sorted permutation (Stefans) | All words of a poem reordered by rule | Yes, but deterministic rearrangement | Probably compliant; author to decide | *Dreamlife*: alphabetised list of DuPlessis's words\[13\] |
| Markov / n-gram chains over his corpus | Statistically plausible new sequences | Yes, machine-chosen | **Grey zone — author must rule** | Words his; sequence machine-determined |
| LLM or neural generation (incl. fine-tuned on his text) | New language | Yes | **Excluded** | Jhave's *ReRites* (2022 Coover) is the counter-model\[44\] |

**Precedents and authorship handling.** A "Media Theory for the 21st Century" course blog post (21 Jan 2008) notes that "Stefans admits that all he's done is run a basic concordance program on 'Rachel's text' (to get the data) and then hit return a few times". The source text was another writer's, so authorship was shared and credited. Queneau's preface calls the book "une sorte de machine à fabriquer des poèmes, mais en nombre limité" (a kind of machine for making poems, but in limited number).\[45\] Wikipedia's article on the book records that "In 1997, a French court decision outlawed the publication of the original poem on the Internet, citing the Queneau estate and Gallimard publishing house's exclusive moral right", an early sign that combinatorial works carry rights in their source. Cayley's *riverIsland* (32 poems adapted from Wang Wei) morphs only between texts he authored or translated.\[46\] Nick Montfort's *Taroko Gorge* (2009) runs on JavaScript the ELO Directory describes as "under one thousand words long". Leonardo Flores (*I ♥ E-Poetry*, May 2012) says it "has been the subject of over 20 documented remixes", and ELC3 collects "seventeen variations". It is a model for a small, legible rule set. The 2025 Coover Award winner, *Espejo de Carne*, was praised for "the seeding and layering of multiple modes". The ELO announcement added: "Artistically, the work uses LLMs well, though such tools bring with them their own implications within a work positioned as a feminist text." The 2023 winner was Everest Pipkin's *Anonymous Animal* and the 2024 winner Halim Madi's *Borderline*.\[47\]

**Markov question, presented neutrally.** *Argument it is compliant:* every token is his and the algorithm writes nothing, much like cut-up methods, where chance does the selecting. *Argument it is not:* the sequence, which is where much of a poem's meaning lives, is chosen by a statistical model, so displayed lines would be machine-composed text he never wrote. A middle path: n-gram transitions only at line or verse boundaries (whole lines intact), or Markov output shown only as a visibly transient "weather" state that always resolves to the original.

**Seeded determinism.** Derive all randomness from one seed (visit seed plus context hash). Reproducible visits allow bug reports and shareable "states", and let the author audit any arrangement ever shown.

**Keeping the original recoverable.** Every modulated view should resolve back to the source, through a gesture or a settle-after-idle behaviour, and the canonical text should always be available to assistive technology (Avenue 6).

**Modulation architecture.** Model it as patching: *sources* (time, seed, touch, tilt, weather) → *modulators* (LFOs, envelopes, smoothing, random walks, thresholds) → *targets* at any level (glyph jitter, word spacing, line drift, stanza arrangement, poem selection). This is the Max/MSP or VCV Rack metaphor, and it lets the author author the mappings themselves, which is itself creative authorship. A single JSON "patch" file per poem or release can capture it.

### Avenue 5 — Rendering stack

| Option | Strengths | Weaknesses | Fit to v4 |
|---|---|---|---|
| Canvas 2D (current) | Already built; simple; good for few hundred sprites | CPU-bound with thousands of animated glyphs | Keep for base layer |
| PixiJS v8 (WebGL/WebGPU) | Sprite batching; BitmapText "tens of thousands of text objects"; MSDF/SDF fonts; WebGPU with WebGL fallback | MSDF needs atlas generation; a v8 bug report noted quality regressions vs v7\[48\]\[49\]\[50\] | Best upgrade path for blooms |
| Three.js / regl | Full 3D, shaders, depth "Unfold" | Heavier; more GPU cost on phones | If depth becomes central |
| p5.js | Fast prototyping | Performance ceiling | Sketching only |
| SVG + CSS | Stroke animation, accessibility-friendly DOM | Slows with many nodes | Small overlays, stroke reveals |

**iOS frame budget.** Safari holds page rendering "near 60fps" by default via a WebKit preference, reported by MacRumors and Tom's Guide.\[10\]\[51\]\[52\] Pages cannot change this.\[53\] That is a budget of about 16.7 ms per frame.\[10\] WebKit throttles requestAnimationFrame to 30 fps in Low Power Mode by design ("This is intentional").\[9\] Animations should be time-based, not frame-based, so they degrade gracefully. WebGPU shipped in Safari 26.0 for iOS, iPadOS, macOS and visionOS (WebKit, Sept 2025).\[54\] WebGL remains the safe baseline, and PixiJS v8 auto-falls back.\[50\]

**Effort:** Low (stay Canvas 2D, add sprite atlas) to Medium (port to PixiJS). **Recommendation:** hybrid. Keep Canvas 2D or Pixi for the field, and a transparent DOM text layer for accessibility and selection.

### Avenue 6 — Performance, accessibility, motion safety

- **Screen readers.** Keep a hidden-but-accessible DOM copy of the canonical poem text (in reading order, with version information) synchronised with the focused unit. The visuals vary; the accessible text does not.
- **Reduced motion.** WCAG 2.3.3 (AAA) requires that motion triggered by interaction "can be disabled, unless the animation is essential", and names parallax as a known trigger for vestibular disorders.\[55\]\[56\] Under `prefers-reduced-motion: reduce`, replace tilt parallax and flight with crossfades and static blooms.
- **Gyroscope parallax** is the highest motion-sickness risk. Use small amplitudes, heavy smoothing, and a toggle.
- **Battery.** Pause the animation loop on `visibilitychange`, idle-throttle after dwell, and keep sensor listeners off unless granted and in view.
- **Test on real iPhones**, as the plan notes. The headless Chromium tests cannot reproduce Safari's permission UX, 60 fps cap or Low Power throttling.

### Avenue 7 — Release plan, Reserve, copyright, participation

- **n/100 releases.** Treat each release as a fixed canonical unit set plus a versioned "patch" (modulation rules). Per-visit variation belongs to the rendering, not the poem. Record the release seed so "n/100 as first shown" is reproducible.
- **Version stacks.** Each edit is a new version node, and blooms can draw on all published versions but never on unpublished ones.
- **Reserve rule (critical).** Enforce it at build time. Atom extraction (glyph crops, word crops, concordance indices, phonetic vectors, Morfessor models) must run only over a published-whitelist corpus. Shipping a Reserve poem's letter crop, word, n-gram statistic or embedding to the client is a form of online appearance, even if never displayed. Treat any model trained on Reserve text as containing it. Concordance counts ("this word appears 7 times") can leak Reserve presence, so compute counts only over the published set.
- **Copyright.** The US Copyright Office's Part 2 report (29 Jan 2025) says protection covers human-authored works "perceptible in AI-generated outputs" and "creative selection, coordination, or arrangement". It excludes material "whose expressive elements are determined by a machine".\[17\]\[19\] Rule-based rearrangements of his poems don't change the registration of the source poems. If he wants to register the interactive piece as a whole, he should describe the human contributions (selection, rules, arrangement), as the Office advises.\[57\]\[58\]
- **Participation without mixing authorship.** Options in ascending risk: (a) visitors' inputs as parameters only (their tilt, time or tap patterns shape a state they can share by seed); (b) visitor annotations in a separate, clearly labelled layer, never interleaved with his text; (c) contributed handwriting as a distinct visual stratum (for example, visitors trace his letters, and their strokes are stored as theirs) with explicit licence terms. Keep contributed material out of the atom graph that feeds blooms unless he chooses otherwise.

## Ranked Avenues: Feasibility vs. "Aliveness"

| Avenue | Feasibility (1–5) | Aliveness (1–5) | Authorship risk | Suggested order |
|---|---|---|---|---|
| Seeded variation + time/season/return-visit | 5 | 3 | None | 1 |
| Concordance blooms from scan crops | 4 | 5 | None | 2 |
| Atom graph + forced alignment | 3 | Enabler | None | 2 (parallel) |
| Modulation patch system | 3 | 4 | None (rules authored) | 3 |
| Version morphing (transliteral) | 4 | 4 | None | 3 |
| Opt-in gyroscope/tilt | 3 | 4 | None; motion-safety risk | 4 |
| Opt-in weather (coarse) | 3 | 3 | None; privacy design needed | 5 |
| Stroke-reconstruction writing animation | 2 | 4 | Low (reconstructed, not documentary) | 5 |
| Queneau slot substitution | 3 | 3 | Author-designed | Author decision |
| Markov/n-gram recombination | 4 | 3 | Grey zone | Author decision |
| Microphone / ambient light | 2 / 1 | 3 | Privacy / unsupported | Skip |

## Open Questions for the Author

1. Does Markov or n-gram recombination of your own words count as "machine-authored" under your rule, and does a whole-line-only variant change the answer?
2. Should context be the viewer's (their weather or location) or authored (the weather where the journal was written)?
3. Should a "being written" stroke animation, which is a reconstruction and not a record, ever appear?
4. Is the display unit of the hand the scan crop only, or may the Etceter4 Diary font stand in for it?
5. Should struck-through and inserted words be first-class atoms in blooms?
6. Do published-but-later-revised versions stay available to blooms forever?
7. Which participation tier (parameters, annotations, contributed handwriting), if any?

## Caveats

- Browser support figures come from caniuse, MDN, WebKit and W3C as of 2025–2026. Several caniuse tables were read from search snippets, and Safari's 60 fps default is documented through WebKit preferences and tech press, not an Apple statement.
- Some precedents (Cardiff, Rueb, *Biophilia*, *PolyFauna*, Strickland's *Vniverse*, Morrissey's *The Jew's Daughter*, bpNichol's *First Screening*, Kac's holopoetry) were not re-verified in this pass.
- Copyright points are US-specific and not legal advice. Journals' "prior publication" policies vary, and the Reserve rule is the author's own stricter standard.

## Sources

1. [Detecting device orientation - Web APIs](https://developer.mozilla.org/en-US/docs/Web/API/Device_orientation_events/Detecting_device_orientation)
2. [XML and OHCO](https://pittsburgh-neh-institute.github.io/Institute-Materials-2017/schedule/week_2/ohco.html)
3. [12 Representation of Primary Sources - The TEI Guidelines](https://www.tei-c.org/release/doc/tei-p5-doc/en/html/PH.html)
4. [GitHub - mittagessen/kraken: OCR engine for all the languages · GitHub](https://github.com/mittagessen/kraken)
5. [Introduction to the Python API — kraken documentation](https://kraken.re/main/user_guide/api.html)
6. [Device Sensor Fingerprinting: Accelerometer & Gyroscope](https://browserinsight.net/blog/sensor-fingerprinting)
7. [Ambient Light Sensor](https://www.w3.org/TR/ambient-light/)
8. [WebKit Features for Safari 26.2](https://webkit.org/blog/17640/webkit-features-for-safari-26-2/)
9. [215745](https://bugs.webkit.org/show_bug.cgi?id=215745)
10. [Enable Smoother 120Hz Browsing in Safari - MacRumors](https://www.macrumors.com/how-to/enable-smoother-120hz-browsing-in-safari/)
11. [Raymond Queneau, Cent mille milliards, de poèmes, 1961](https://vimeo.com/1053867941)
12. [A Hundred Thousand Billion Poems](https://en.wikipedia.org/wiki/A_Hundred_Thousand_Billion_Poems)
13. [Brian Kim Stefans](https://en.m.wikipedia.org/wiki/Brian_Kim_Stefans)
14. [211 Noah Wardrip-Fruin Playable Media and Textual Instruments Abstract:](http://www.noahwf.com/texts/nwf-playable.pdf)
15. [Brian Eno : Reflection](http://www.peterchilvers.com/?p=137)
16. [100,000,000,000,000 Poems](https://directory.eliterature.org/individual-work/374)
17. [US Copyright Office Publishes Second Part of Report on AI Copyrightability — AI: The Washington Report](https://www.mintz.com/insights-center/viewpoints/54731/2025-02-07-us-copyright-office-publishes-second-part-report-ai)
18. [A federal report says prompts alone do not make an AI user an author](https://creativebriefroom.com/archive/copyright-office-part-2-copyrightability-2025/)
19. [NewsNet Issue 1060](https://www.copyright.gov/newsnet/2025/1060.html)
20. [What is Text, Really?](http://web.dfc.unibo.it/buzzetti/IUcorso2006-07/mdidattici/ohco.pdf)
21. [Allen H. Renear](https://www.semanticscholar.org/author/Allen-H.-Renear/2278731)
22. [(PDF) Refining our Notion of What Text Really Is: The Problem of Overlapping Hierarchies](https://www.academia.edu/76009249/Refining_our_Notion_of_What_Text_Really_Is_The_Problem_of_Overlapping_Hierarchies)
23. [Balisage: Hierarchies within range space](https://balisage.net/Proceedings/vol13/print/Piez01/BalisageVol13-Piez01.html)
24. [11 Representation of Primary Sources - The TEI Guidelines](https://www.tei-c.org/Vault/P5/3.6.0/doc/tei-p5-doc/ja/html/PH.html)
25. [11 Representation of Primary Sources - TEI P5: — Guidelines for Electronic Text Encoding and Interchange](https://www.tei-c.org/Vault/P5/2.0.1/doc/tei-p5-doc/en/html/PH.html)
26. [kraken/docs/index.rst at main · mittagessen/kraken · GitHub](https://github.com/mittagessen/kraken/blob/main/docs/index.rst)
27. [feat: read handwriting with a kraken OCR engine by martinszuc · Pull Request #78 · martinszuc/anonymizer · GitHub](https://github.com/martinszuc/anonymizer/pull/78)
28. [(PDF) Morfessor 2.0: Toolkit for statistical morphological segmentation](https://www.researchgate.net/publication/301404137_Morfessor_20_Toolkit_for_statistical_morphological_segmentation)
29. [Poetic Sound Similarity Vectors Using Phonetic Features](https://www.researchgate.net/publication/364468630_Poetic_Sound_Similarity_Vectors_Using_Phonetic_Features)
30. [PWESuite: Phonetic Word Embeddings and Tasks They Facilitate](https://arxiv.org/pdf/2304.02541)
31. [Device Orientation and Motion](https://www.w3.org/TR/orientation-event/)
32. [Gyroscope API](https://caniuse.com/mdn-api_gyroscope)
33. [GitHub - open-meteo/open-meteo: Free Weather Forecast API for non-commercial use · GitHub](https://github.com/open-meteo/open-meteo)
34. [🧑‍⚖️ Terms](https://open-meteo.com/en/terms)
35. [Classics: endless meditative music and art with Brian Eno : Reflection - TapSmart](https://www.tapsmart.com/features/classics-reflection/)
36. [Bloom App - App Store](https://apps.apple.com/us/app/bloom/id292792586)
37. ["Electronic Literature Collection Volume 4" by Kathi Inman Berens, John Murray et al.](https://pdxscholar.library.pdx.edu/eng_fac/125/)
38. [SVG360: Editable Multiview Vector Graphics from a Single SVG](https://arxiv.org/pdf/2511.16766)
39. [Lines, points and curves](https://im.snibgo.com/linptcv.htm)
40. [Inkscape tutorial: Tracing bitmaps](https://inkscape.org/doc/tutorials/tracing/tutorial-tracing.html)
41. [A Physical Book - Electronic Literature Collection Vol. 4](https://collection.eliterature.org/4/a-physical-book)
42. [A Game of Dice: Machine Learning and the Question Concerning Art](https://arxiv.org/pdf/1904.01957)
43. [Problem 21 Cent mille milliards de poèmes ... \[FREE SOLUTION\]](https://www.vaia.com/en-us/textbooks/math/precalculus-12-edition/chapter-11/problem-21-cent-mille-milliards-de-poemes-one-hundred-millio/)
44. [David Jhave Johnston](https://en.wikipedia.org/wiki/David_Jhave_Johnston)
45. [Cent mille milliards de poèmes by Raymond Queneau](https://www.goodreads.com/book/show/957696.Cent_mille_milliards_de_po_mes)
46. [(PDF) Morphing Into New Modes of Writing: John Cayley's riverIsland](https://www.academia.edu/740329/Morphing_Into_New_Modes_of_Writing_John_Cayleys_riverIsland)
47. [Past ELO Award Winners](https://eliterature.org/elo-award-winners/)
48. [Bug: V8 empty line skipping, in multiline text · Issue #10463 · pixijs/pixijs · GitHub](https://github.com/pixijs/pixijs/issues/10463)
49. [Bitmap Text](https://pixijs.com/8.x/guides/components/scene-objects/text/bitmap)
50. [v8.0.0 beta.0](https://github.com/pixijs/pixijs/releases/tag/v8.0.0-beta.0)
51. [Your iPhone can browse Safari at a smooth 120Hz, and this is the setting you need to change](https://www.tomsguide.com/phones/iphones/enable-120hz-safari-on-iphone)
52. [macOS: render WKWebView pages at the display's rate, not near 60 fps by ojowwalker77 · Pull Request #256 · kiwi-init/electrobun-livewire · GitHub](https://github.com/kiwi-init/electrobun-livewire/pull/256)
53. [JS-driven animations stay at 60 fps on 120 Hz iPhones (WebKit's 60fps rendering preference) · Issue #1864 · 0xMiden/wallet · GitHub](https://github.com/0xMiden/wallet/issues/1864)
54. [WebKit Features in Safari 26.0](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/)
55. [WCAG 2.2: 2.3.3 Animation from Interactions](https://callingallminds.com/resources/wcag/2.3.3-animation-from-interactions)
56. [Understanding SC 2.3.3: Animation from Interactions (Level AAA)](https://w3.org/WAI/WCAG21/Understanding/animation-from-interactions)
57. [US Copyright Office Issues Report on Copyrightability of Works Incorporating AI-Generated Material](https://www.jenner.com/en/news-insights/client-alerts/us-copyright-office-issues-report-on-copyrightability-of-works-incorporating-ai-generated-material)
58. [Copyright Office: Copyrighting AI-Generated Works Requires “Sufficient Human Control Over the Expressive Elements”](https://www.privacyworld.blog/2025/02/copyright-office-copyrighting-ai-generated-works-requires-sufficient-human-control-over-the-expressive-elements-prompts-are-not-enough/)
