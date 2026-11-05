# Two Voices From One Throat: A Reusable Method for Building Forward and "Red Room" Concatenative Voice Banks of Your Own Voice

The best approach is to record one ARPAbet diphone bank of your own voice: about 1,600 theoretical units, with roughly 1,000–1,400 nonsense-word prompts actually spoken. Build the backward bank mostly from that recording. A Lynch-style reversed diphone X–Y is the forward-recorded transition Y–X played backwards, so time-reversing the forward bank gives you a complete backward inventory without new recording. You then add a smaller, actually performed "Red Room" supplement for the uncanny texture that only a live reversed performance produces.

## TL;DR

- **Use diphones in ARPAbet as the unit for both banks.** One phone set links CMUdict (text→phonemes), Montreal Forced Aligner's `english_us_arpa` model (segmentation) and UTAU/OpenUtau's ARPAsing ecosystem (interoperability). Festvox's tutorial says English "has around 40 phonemes giving rise to about 1600 diphones." Expect about 2.5–4 hours at the mic across 3–4 sessions, and a compressed unit set of roughly 2 MB, well inside a 16 MB page.
- **Lynch's technique is a two-pass time reversal, and you can run it in software or with your body.** Per Dean Hurley and Ron Eng, actors said lines into a Dictaphone, learned the reversed playback phonetically, performed it, and the dailies were reversed.\[1\] In your system, a backward unit X–Y = reverse(forward unit Y–X). "Red Room mode" means synthesizing the reversed phoneme string and then reversing the whole output buffer. Accounts differ on who coached whom, on prompting, and on whether the actors also moved backwards; this is flagged below.
- **Assemble everything in the browser with code you control.** Use a precomputed CMUdict-based lexicon for the poems, with eSpeak NG WebAssembly (GPL-3.0) as an optional fallback for unknown words. Join units with cross-correlation-aligned crossfades at phone midpoints and do prosody with TD-PSOLA from pitch marks computed offline. Signalsmith Stretch (MIT, WASM/AudioWorklet) handles global pitch and time effects. A neural clone is optional and secondary. Piper (now GPL-3.0 under the Open Home Foundation) is the only mainstream route that trains purely on your recordings. F5-TTS and XTTS v2 weights are non-commercial and pretrained on other people's voices.

## Key Findings

1. **Diphones are the right unit for this project.** Festvox's tutorial "Speech Synthesis in Festival" (§7.1) states that "Japanese has around 25 phones giving rise to about 625 diphones while English has around 40 phonemes giving rise to about 1600 diphones"; the number of diphones is roughly the square of the number of phones. A diphone database records only one occurrence of each diphone.\[2\] Unit selection, by contrast, picks among many occurrences in a large natural corpus; MaryTTS, for example, concatenates "halfphone-sized snippets."\[3\] Unit selection sounds more natural but needs hours of read speech, and the units are not visible or one-of-each the way a font's glyphs are. Diphones are the closest audio analogue of your handwriting font: a fixed, enumerable inventory where every unit is a decomposable piece of you.
2. **The recording method is well established and reusable.** Festvox recommends nonsense words in a fixed carrier, such as `pau t aa C V t aa pau`,\[4\] with the target diphone in a middle syllable.\[5\] Following OGI's method, it advises recording "as a monotone with near fixed durations and near constant power,"\[4\] with 50–100 nonsense words per file. It notes that labelling nonsense words is "*much* easier than labelling continuous speech."\[5\]
3. **The size is small.** Festival's manual (§21.3, group files) states: "A full English LPC plus residual database at 8k ulaw is about 3 megabytes, while a full 16 bit version at 16k is about 8 megabytes." Compressed to Opus, the unit audio drops to the low single-digit megabytes.
4. **The backward bank mostly derives from the forward bank.** Reversing a recording reverses the order of phones and also the dynamics inside each transition. So a backward-bank X–Y unit is identical in kind to reverse(Y–X from the forward bank). Since a complete forward diphone bank contains every Y–X, the backward inventory is complete for free. What the forward bank cannot supply is the performed quality of reversed speech: reversed phrase prosody, breath, and the speaker's imperfect attempts at reversing affricates, diphthongs and aspiration. That is what a small recorded supplement adds.
5. **The primary accounts of Lynch's process mostly agree on the core and disagree on details.** The core is to record, reverse, imitate phonetically, perform, then reverse the footage. The details in dispute are a hired trainer versus Michael J. Anderson as on-set coach, a hidden prompter (hearsay), an iPhone app in 2017, and whether the actors moved backwards.
6. **The tools are healthy as of late 2026, with license traps.** MBROLA has been AGPL since 24 October 2018 (last tagged release 3.3, December 2019).\[6\]\[7\] Festival's last release is 2.5 (December 2017), under a permissive BSD/MIT-like license.\[8\] OpenUtau is MIT-licensed and actively releasing (alphas through September 2026).\[9\]\[10\] Montreal Forced Aligner is MIT, with CC BY 4.0 models and an Interspeech 2026 paper.\[11\]\[12\]\[13\] Piper's original MIT repo was archived on 6 October 2025, and development continues as GPL-3.0 `piper1-gpl`.\[14\]

## Details

### 1. Unit types and tradeoffs

| Unit | What it is | Recording burden | Quality | Size | Fit for this project |
|---|---|---|---|---|---|
| Phoneme-only | ~40 isolated sounds | Minutes | Poor; transitions (coarticulation) are lost, which is the main cause of "robot" speech | Tiny | Only as an aesthetic choice ("typewriter" voice) |
| Diphone | Midpoint of phone A → midpoint of phone B; ~1,600 for English | ~1,000–1,400 nonsense words, 2.5–4 h | Intelligible and clearly synthetic; joins fall in stable vowel and consonant centres | ~2 MB compressed | **Primary choice** |
| Demisyllable / CVVC / VCV (UTAU-style) | Half-syllables or vowel-consonant-vowel chunks | ARPAsing lists: 220–697 samples | Smoother; UTAU VCV banks are about seven times the size of a CV bank in oto lines\[15\] | Small to medium | Good alternative or companion; built for singing |
| Unit selection | Many natural occurrences, chosen by cost functions | Hours of read speech | Most natural when coverage is good | 10s–100s MB | Breaks the "visible units" concept and the page budget |

Festvox also notes that adding one phone adds about 2n diphones.\[5\] Variants such as stressed versus unstressed vowels or cluster /r/ versus lone /r/ are "well worth considering," but each one increases recording time, labelling time and size.\[16\] A practical middle path is one vowel set with lexical stress handled by prosody, plus a few targeted extras such as the flap [dx] and syllabic consonants.

### 2. Tool landscape (license and maintenance status)

| Tool | Role | License | Status (as of Oct 2026) | Recommendation |
|---|---|---|---|---|
| Festival / FestVox | Diphone and unit-selection voice building; diphone-list generation (`diphlist.scm`), auto-labelling, `make_diph_index` | Permissive, BSD/MIT-like | Mature; last Festival release 2.5 (Dec 2017) | **Reference methodology**; use its US diphone schema to generate your prompt list |
| MBROLA + MBROLATOR | Diphone engine (Multi-Band Resynthesis OverLap Add) and database builder | AGPL-3.0 (open-sourced 24 Oct 2018; MBROLATOR 23 Jan 2019)\[6\] | Release 3.3, Dec 2019;\[7\] low activity | Optional offline tool for normalizing a bank; voice-database licenses are separate, so check the repository |
| eSpeak NG (+ WASM ports) | Text→phoneme (IPA) and formant TTS | GPL-3.0-or-later | Active; several 2026 WASM ports (`espeak-phonemizer`, Spellophone, `espeak-ng-wasm` with IPA input)\[17\]\[18\]\[19\] | Fallback G2P for unknown words only |
| MaryTTS | Java unit selection (halfphones) and HMM voices; Gradle voice-building plugins | Open source (LGPL core; voice licenses vary) | Legacy; voice-building pipeline published 2018 | Reference only |
| UTAU / OpenUtau | Concatenative singing synthesis; `oto.ini` banks; English ARPAsing phonemizer | UTAU freeware; OpenUtau MIT | OpenUtau stable 0.1.568 (Mar 2026), alphas into Sep 2026\[9\]\[20\] | **Interoperability target and labelling ecosystem** |
| Montreal Forced Aligner | Forced alignment to Praat TextGrids | MIT; `english_us_arpa` acoustic model v3.0.0 is CC BY 4.0, General American, ARPA phone set\[11\]\[21\] | Active (3.4.x; Interspeech 2026 paper) | **Primary aligner** |
| CMU Pronouncing Dictionary | Lexicon with stress digits | BSD-2-Clause | 0.7b (19 Nov 2014) plus unversioned GitHub updates; "over 134,000 words" per the CMU Speech Group | **Primary lexicon** |
| Signalsmith Stretch | Pitch and time stretching; official WASM/AudioWorklet build | MIT | npm 1.3.2\[22\] | **Global pitch and time effects in browser** |
| audiojs `pitch-shift` / `shift` | Pure-JS OLA, WSOLA and PSOLA implementations | Open source (check repo) | Active 2026 | Reference code for your own PSOLA |
| SoundTouchJS | WSOLA-family tempo and pitch AudioWorklet | Derived from LGPL SoundTouch (verify the package license) | Active | Alternative to Signalsmith |
| Piper (`piper1-gpl`) | Small VITS neural TTS, ONNX | GPL-3.0-or-later (old `rhasspy/piper` MIT, archived 6 Oct 2025)\[14\] | Active (v1.8.0 reported Sep 2026)\[23\] | Optional neural track |
| Kokoro-82M / `kokoro-js` | Neural TTS in browser (WASM/WebGPU) | Apache-2.0 | Active | Not suitable: preset voices, no cloning\[24\] |
| F5-TTS / XTTS v2 | Zero-shot cloning | F5: MIT code, CC BY-NC weights; XTTS v2: CPML, non-commercial\[25\]\[26\] | — | Avoid for this project (other people's voices underneath, NC terms) |

### 3. The forward bank: recording script

**Generate the list rather than writing it by hand.** Festvox's walkthrough generates nonsense words from a schema (`festival -b festvox/diphlist.scm festvox/us_schema.scm ...`), labels them automatically, and builds a diphone index.\[2\] Its example carrier `pau t aa C V t aa pau` surrounds the target with neutral context so the target diphone sits in a stressed middle syllable.\[4\] Festvox's "Building Synthetic Voices" explains that "the DARPAbet example produces consonant-vowel and vowel-consonant diphones in the same nonsense word, which reduces the number of words to be spoken quite significantly." You can follow the classic "say ___ again" convention using your own carrier, as long as it stays fixed.

**Practical recipe:**
1. Fix the phone set: CMUdict's 39 ARPAbet phonemes (the CMU Speech Group: "The current phoneme set has 39 phonemes, not counting varia due to lexical stress") plus silence (`pau`) and a flap (`dx`).
2. Enumerate C–V, V–C, V–V, C–C and silence–X / X–silence pairs. Prune impossible pairs only if you are sure you will never need them. One commercial diphone system kept all combinations precisely because "names, places and nonsense words can have strange combinations of sounds."\[27\] Your poems and their later root-and-glyph decompositions in LingFrame will produce exactly such strange sequences, so keep them.
3. Embed each target (or a CV+VC pair) in a fixed carrier and print the prompts with both a spelling hint and the phone string. ARPAsing reclists use the same "word + phonetic hint" convention, for example `live[l ih v]`.\[28\]
4. Record them in files of 50–100 items, as Festvox suggests,\[5\] or one item per file with a prompter tool. The VoCreatures ENG-ARPA reclist recommends the OREMO recorder at 100 BPM, with vLabeler for configuration.\[29\]

**Existing lists you can reuse or adapt:**
- Festvox's US English diphone schema, the most directly suited because it is speech-oriented.
- The VoCreatures ENG-ARPA reclist: 188 CVVC lines + 70 VCV vowel lines + 127 CC lines + 5 vocal-fry lines.\[29\]
- Kanru Hua's original 220-sample ARPAsing 0.1.0 reclist.\[30\]
- deadbyte's 526-sample phoneme-based ARPAsing list.\[31\]

UTAU reclists assume sung, pitched delivery. For speech, use Festvox's monotone spoken carrier and export an `oto.ini` as a secondary format.

### 4. The backward bank: the Red Room technique and how to make it concatenative

#### 4a. What is documented about Lynch's process

- **The origin, 1971.** In *Lynch on Lynch* (ed. Chris Rodley), Lynch describes having Alan Splet record him saying "I want pencils," reversing it, learning it "phonetically backwards," recording that, and reversing it again into "a beautifully strange version of the original."\[32\] This quote is second-hand via a blog transcription; verify it against the book. Lynch also says the Red Room scene "leapt into my mind. 'Little Mike' was there, and he was speaking backwards."\[33\]
- **Twin Peaks, 1990–91, from Michael J. Anderson (first-hand, FanBolt interview, c. 2007).** Lynch "gives me the script and tells me, learn this backwards. He had made arrangements to take me into a studio and teach me how to do it, and when he discovered that this was a skill that I already had... he not only added more backward lines for me to say, he started adding backward lines for other characters and had me teach them. I became the reverse dialog coach on the set."\[34\] Anderson had learned "phonetic reversal" as a "secret language" at school.\[34\]
- **A divergent account (Wikipedia, citing older press).** Anderson spoke into a recorder, the recording was reversed, and he "was directed to repeat the reversed original." Lynch "had hired a trainer" and then "cancelled the trainer."\[35\]\[36\] Anderson's own account mentions studio arrangements but neither a trainer nor a record-and-imitate loop.
- **Hearsay about a hidden prompter (Welcome to Twin Peaks, 2017).** "As the story goes, a prompter hid behind the vintage seats and whispered the backwards lines."\[37\] This is unconfirmed.
- **Twin Peaks: The Return, 2017, from the sound supervisors (Dean Hurley and Ron Eng, *A Sound Effect*, Oct 2017).** "They are quite literally talking backwards... He had the actors say their lines into a little Dictaphone. Then, he'd play that back in reverse and the actors would learn their lines in reverse phonetically, and then perform the scene with that phonetic reversal. Then the dailies were reversed so that when the performance played it had that stilted, slurred speech quality... some actors are better than others at it."\[1\] Separately, script supervisor Cori Glazer reportedly rehearsed actors with the iPhone app "Reverse talk" (Proctele AB).\[37\] Anderson did not return for 2017.\[36\]\[38\]
- **Movement and subtitles.** Secondary sources disagree: some say the actors moved backwards, others say they moved normally and the reversal of the footage produced the jerky motion.\[39\]\[40\]\[41\] IMDb transcriptions mark the lines "[talking backwards; subtitled]."\[42\]
- **Sheryl Lee and Kyle MacLachlan.** No first-hand description of the method was found. A widely repeated line that Lee recited "repooC tnegA, olleH" is a journalist's illustration,\[43\] and it is letter reversal, which is not what phonetic reversal is.

#### 4b. Why it sounds uncanny

Marburg phonetician Mathias Scharinger's 2026 systematic review in *Psychonomic Bulletin & Review* distinguishes **subjectively reversed speech**, produced backwards by skilled speakers, from **objectively reversed speech**, which is playback reversal.\[44\]\[45\] The Red Room stacks both. The review notes that the processes of speech production "are very hard to reverse in time." A backward talker turns "laughter" into "rethgual" with a letter strategy or "retfal" with a sound strategy. Principled reversal is "limited to short sequences."\[45\]

When the performance is flipped, several things happen at once:
- Every gesture the mouth could not truly reverse comes out backwards. Anticipatory coarticulation becomes carry-over, stop bursts and aspiration arrive before their closures, and decays become swells.
- Breath and phrase prosody invert. Final lengthening and the downward drift of pitch move to the wrong end of the phrase unless the performer compensates.
- Room reverberation precedes each word. Michel Chion describes words "preceded by their end reverberations so that the words pop up like little bubbles."\[32\]

Perception research explains why the result stays half-intelligible. Saberi and Perrott (*Nature* 398:760, 1999) found that speech survives local time reversal in short windows: "Listeners report perfect intelligibility of the sentence for segment durations up to 50 ms, and partial intelligibility for segment durations exceeding 100 ms... with 50% intelligibility occurring at about 130 ms." Diphone-sized reversed units last about 100–250 ms, which puts them in the "eerie but partly decodable" zone. That is why Lynch needed subtitles,\[43\] and it is why your page should show them, in your handwriting font.

#### 4c. Writing phonetic-reversal scripts (pitfalls)

Reverse the phones, not the letters. The pipeline is text → CMUdict ARPAbet → reverse the sequence → apply rewrite rules → respell for reading aloud. The rules to apply:
- **Affricates.** CH = [t+ʃ] and JH = [d+ʒ] reverse to [ʃ+t] and [ʒ+d]. The spea.cc Phonetic Reverser turns "jug" into "g-uh-zszh" for this reason.\[46\]
- **Diphthongs.** AY, EY, OY, AW and OW reverse their glide direction; AY becomes roughly "ee-ah."
- **Aspiration and stop releases.** In English a voiceless stop's aspiration follows its release. Reversed, the breath must come *before* the stop. Performers approximate this with a breathy onset, and the imperfection is part of the sound.
- **R-coloured vowels, flaps and syllabic consonants.** These have no clean reversal.
- **Vowel reduction and stress.** Schwas and stress placement must be re-decided in the reversed string, because English stress rules applied to the reversed "word" will put stress in different places. The review notes that reversal can produce phonotactically illegal clusters, such as [dl] from "bald."\[47\]

Existing script tools: the spea.cc Phonetic Reverser (tuned to its author's American accent), R2bEEaton's Phonetic Reverser, the "Reverse talk" app used on *The Return*, and browser record/reverse practice tools such as SpeakBackwards.\[46\]\[48\]\[49\] None is a citable, versioned, open tool. Writing your own roughly 100-line rule-based reverser on top of your CMUdict lexicon is the reusable route, and it plugs straight into LingFrame.

#### 4d. Making the backward bank: three modes, one pipeline

| Mode | How it's made | Recording | Character |
|---|---|---|---|
| **Mirror** (derived bank) | For target X–Y, play `reverse(forward[Y–X])`; concatenate in forward text order; apply normal forward prosody | None | Phones in the right order, transitions reversed; uncanny but steady |
| **Red Room (software)** | Reverse the target phoneme string with the rewrite rules, synthesize it *forward* with the forward bank and its own prosody, then reverse the whole output buffer | None | Closest digital analogue of Lynch: prosody, envelopes and breath all inverted |
| **Red Room (performed)** | Record a reversed script, align it in its recorded direction, flip audio and labels, index as units | 1–3 h plus practice | Authentic: carries your bodily failure to reverse, which is the actual Lynch texture |

**What a reversed diphone is.** It is a unit whose phone identities read X→Y after flipping, but whose acoustic trajectory is the Y→X articulation running backwards. Joins at phone midpoints still work, because a vowel's steady centre reversed is still a steady centre. The inventory therefore does not need to be designed differently for Mirror or software Red Room modes.

**For the performed supplement, design differently.** Do not try to perform 1,600 reversed diphones. Instead:
- (a) Perform reversed carrier sentences for a high-value subset, such as vowel–vowel and vowel–sonorant transitions where reversal is most audible.
- (b) Perform whole reversed words for the most frequent words in the 126 poems, stored as whole-word units with diphone fallback, the way one commercial diphone system used whole-word recordings when available.\[27\]

**Segmentation of reversed audio.** Align the performed take *before* flipping it, against its reversed phone string, using MFA. The un-flipped recording is ordinary English-like articulation, so the English acoustic model has a chance. Then flip both the audio and the labels with t′ = T − t. Aligning already-flipped audio with a model trained on forward speech is likely to fail.

**Blending and switching at playback.** Treat bank choice as a per-unit attribute in the playlist. You can switch per line, per word or per stanza. You can crossfade the same utterance rendered in both banks, since both use identical durations when Mirror mode shares the forward prosody plan. Or you can let LingFrame tags such as `<rev>` mark spans.

### 5. Segmentation and labelling workflow

1. **Forced alignment.** Run MFA with `english_us_arpa` (v3.0.0, trained 2024-02-10, CC BY 4.0) against the known prompt phone strings. Add any nonsense-word pronunciations to the dictionary, which MFA allows "as long as no additional phones are introduced."\[21\] The output is Praat TextGrids.\[50\] Festvox's own aligner is the historical alternative. Gentle, WebMAUS and wav2vec2 phoneme aligners also exist but were not evaluated for this report.
2. **Diphone boundaries.** Following Festvox's `make_diph_index`, each diphone is defined by start (middle of phone 1), mid (the phone boundary) and end (middle of phone 2). Festival's dictionary format is exactly `name file start mid end` in milliseconds.\[51\] For stops, put the "middle" in the closure silence rather than in the burst; this is the cleanest place to cut.
3. **Correction.** Festvox warns that "the autolabelling is unlikely to work completely": listen to many diphones, or resynthesize every nonsense word, to find the bad ones.\[2\]\[5\] Fix TextGrids in Praat, or use an `oto.ini` editor such as vLabeler or OpenUtau's built-in oto editor if you also export UTAU format.\[52\]\[53\]
4. **Pitch marks.** Compute glottal pulse marks offline with Praat's PointProcess or an equivalent, and store them per unit for PSOLA. Festival notes that high-quality pitch marks ideally come from laryngograph data; the KAL diphone sets were recorded at 32 kHz with an electroglottograph.\[51\]\[54\] Acoustic pitch marking is adequate for an artistic voice.

### 6. Joining and prosody in the browser

- **Joins.** Because the bank is recorded in monotone at constant power, a 5–20 ms equal-power crossfade at phone midpoints covers most joins. Choose the exact overlap by cross-correlation within plus or minus one pitch period (a WSOLA-style search) so periods line up and do not phase-cancel. Normalize loudness per unit offline.
- **Pitch and duration.** Implement TD-PSOLA yourself in JavaScript. With precomputed pitch marks it is a few hundred lines: window two-period Hann grains at each mark, then re-space them for pitch and repeat or drop them for duration. The audiojs `psola` implementation is a readable reference; it detects periods by autocorrelation and uses "two-period Hann grains... at pitch-synchronous intervals."\[55\] Run it in an AudioWorklet or render ahead into an `AudioBuffer`. Pre-rendering the line before playback is simpler and fully deterministic.
- **Global effects.** Signalsmith Stretch (MIT; official WASM/AudioWorklet node with `semitones`, formant and scheduling controls) handles whole-utterance pitch and time shifts.\[56\]\[57\] It sounds best between 0.75× and 1.5× time-stretch.\[58\]
- **MBROLA-style resynthesis.** MBROLA normalizes pitch and phase across the database so joins are smoother, and unlike PSOLA it does not need pitch marks.\[6\] Use MBROLATOR offline as a bank-conditioning experiment rather than shipping AGPL code in the page.
- **Intonation.** Start with a rule-based contour: declination across the line, a pitch accent on CMUdict primary-stress (`1`) vowels, and a final fall or rise by punctuation. Let markup override it. A per-poem hand-drawn contour fits the handwriting metaphor well.

### 7. Text-to-phoneme front end

- **Primary:** a build-time lexicon. Run every word of the 126 poems through CMUdict ("over 134,000 words" per the CMU Speech Group, BSD-2, ARPAbet with stress digits). Hand-correct the result to your own pronunciation and ship the subset as JSON, typically tens of KB. Your own pronunciation decisions are authorial, like glyph choices in the font.
- **Fallback for new or unusual words:** eSpeak NG compiled to WASM (`espeak-phonemizer`, Spellophone, `espeak-ng-wasm`), with an IPA→ARPAbet map. All are GPL-3.0,\[17\]\[18\]\[19\] which makes a shipped page a GPL combined work. Alternatively, keep a "spell it phonetically" input box and avoid GPL entirely.
- **Markup:** a minimal inline syntax for phone overrides (`{K AA1 F IY0}`), stress, pauses, bank switches (`<rev>…</rev>`) and pitch targets. This also becomes LingFrame's handoff format for roots and glyphs.

### 8. Optional neural track

The neural track is worth it only as a second, clearly labelled voice, and only if trained on your own recordings alone.
- **Piper:** the realistic candidate. It is small, VITS-based and ONNX, and community WASM and phonemizer ports exist for browsers. The engine is now GPL-3.0 (`piper1-gpl`).\[59\] The amount of data and GPU time needed to train a Piper voice from scratch was not verified here; Piper voices are usually fine-tuned from a pretrained base, which reintroduces other speakers.
- **Kokoro-82M:** runs fully in the browser via `kokoro-js` (Apache-2.0; the q8 model is about 86 MB). It has preset voices and no cloning,\[24\]\[60\]\[61\] and it would exceed a 16 MB page anyway.
- **F5-TTS (CC BY-NC weights) and XTTS v2 (CPML):** zero-shot cloners built on large multi-speaker corpora.\[26\] They imitate your voice rather than being made of it, which contradicts the project's premise.
- **RVC and StyleTTS2:** not researched in this pass.

Conclusion: keep concatenation as the art object and treat neural smoothing as a possible post-filter experiment.

### 9. Recording practice for a solo artist

This section is practitioner guidance, not drawn from a single primary source.
- **Microphone and room.** A USB or XLR cardioid microphone in a small, soft-furnished space (a closet of clothes works) beats a condenser in an untreated room. A phone is fine for a pilot. Record dry: any room reverb will be smeared into every join, and in the backward bank it will precede each word.
- **Consistency.** Keep a fixed mouth-to-mic distance (marked with a pop filter) and a fixed gain. Start each session with a reference: the same sustained "aa" against a tuner pitch and the same calibration sentence. Read in near-monotone at a comfortable pitch with even pacing; Festvox's voice-building guide asks that "the words should be pronounced with consistent vocal effort, with as little prosodic variation as possible."
- **Sessions.** About 45–60 minutes of reading with breaks; stop when your voice changes. Record at 48 kHz/24-bit WAV and derive 22.05–24 kHz delivery files.
- **Quality control.** Use a checklist per take: clipping, noise floor, mispronounced target, pitch drift against the reference. Re-record failures in a "fixes" session that starts with the calibration routine. After alignment, auto-play every diphone in an "all units" page and flag bad ones.

### 10. Reusable packaging format

The reference formats are Festival (`dic/` index, `wave/`, `pm/` pitch marks, with an optional single "group file"),\[51\] MBROLA (a single database file) and UTAU (WAVs plus `oto.ini` lines `file.wav=alias,offset,consonant,cutoff,preutterance,overlap`,\[15\]\[62\] which OpenUtau reads alongside its phonemizers).\[52\]\[63\]\[64\]\[65\] A good bank layout combines them:

```
voicebank-anthony-v1.0.0/
  manifest.json          # identity, version, license, provenance, phone set, hashes
  phoneset.json          # ARPAbet + IPA + articulatory features (for LingFrame)
  lexicon.json           # hand-corrected pronunciations
  src/                   # 48k/24-bit masters + TextGrids (archival, not shipped)
  units/forward.opus     # all diphones concatenated with padding ("sprite")
  units/forward.index.json   # {"AA-B": {start, mid, end, pm:[...], gain}, ...}
  units/redroom.opus     # performed backward supplement (optional)
  units/redroom.index.json
  export/oto.ini         # OpenUtau/UTAU interop
  export/festival.est    # Festival diphone index interop
  LICENSE-VOICE.md       # terms for your voice
  CHANGELOG.md
```

`manifest.json` should record:
- semantic version;
- recording dates, microphone, room and sample rates;
- reclist name and version;
- aligner name, version and model license (MFA `english_us_arpa` v3.0.0, CC BY 4.0);
- a SHA-256 for every file;
- `"derived": {"mirror": "reverse(forward[Y-X])"}`, so the backward bank is declared as a transformation rather than stored twice;
- a statement that no AI-generated text or voice is included.

Version the bank independently of any one project and pin it per project.

### 11. Browser playback architecture and budget

**Pipeline:** text → tokenizer → lexicon/G2P → ARPAbet + stress → (reverse + rewrite rules if Red Room) → diphone sequence → unit lookup (forward / mirror / performed) → prosody plan (durations, F0) → PSOLA per unit → aligned crossfade joins → (reverse whole buffer if Red Room) → `AudioBuffer` → Web Audio graph (gain, optional Signalsmith node) → output, with subtitles drawn in your handwriting font in sync.

**Budget estimate:** about 1,600 units × about 250 ms with padding gives about 400 s of audio. At about 32 kbps mono Opus that is about 1.6 MB, or about 2.1 MB if base64-inlined in a single self-contained file. Add a lexicon in the tens of KB, your JS, and Signalsmith's WASM. The forward bank, Mirror mode, the Red Room supplement and the font together plausibly fit in 4–6 MB, far under 16 MB. eSpeak NG WASM plus its language data would be the largest optional item; measure it before including it.

**Gotcha:** lossy codecs add encoder delay and padding, so offsets measured on the WAV will drift in an Opus sprite. Either measure offsets after decoding at build time, or pad each unit with 50 ms of silence and locate it by cross-correlation once on load.

### 12. Rights and safety (brief)

Publishing a concatenative bank of your voice lets anyone make "you" say things. Mitigations:
- A custom voice license (for example, permitting use only in your works, with no impersonation, no political or commercial speech, and attribution required).
- Not publishing raw source masters.
- Embedding provenance in the manifest and audio metadata.
- Stating clearly in the work that the voice is synthetic.

A concatenative voice is also easier to recognize as synthetic than a neural clone. Platform policies and voice-likeness legislation (for example, proposed US federal "digital replica" bills) and audio watermarking were not researched in this pass; review them before any wider release.

## Recommendations

1. **Week 1: pilot (about 1 hour).** Record 50 diphone carriers on your phone and USB microphone. Align them with MFA, build Mirror and Red Room (software) modes on this mini-bank, and test one poem line in the browser. This tests the whole method before the big session.
2. **Forward bank (2.5–4 h at the mic over 3–4 sessions; this is my estimate).** Generate the diphone nonsense-word list from Festvox's US schema. Expect roughly 1,000–1,400 prompts after packing CV and VC pairs into shared words; verify the count when you generate it. Record monotone, align, correct and pitch-mark. Labelling and QC take another 4–8 h.
3. **Backward bank, derived (0 h recording).** Ship Mirror and Red Room (software) modes immediately.
4. **Backward bank, performed (1–3 h plus practice).** Use your own phonetic reverser to script reversed whole words for the poems' most frequent words and a subset of reversed carriers. Rehearse with a reverse-playback tool, the way Lynch's 2017 team used a Dictaphone or app. Align before flipping.
5. **Front end.** Build a hand-corrected CMUdict lexicon for the 126 poems, add an override markup, and decide on GPL eSpeak NG fallback later.
6. **Engine.** Write your own JS: lexicon → units → PSOLA → aligned crossfades, with Signalsmith Stretch for global effects. Render ahead and play.
7. **Package** as `voicebank-anthony-vX.Y.Z` with manifest, hashes, license, and `oto.ini`/Festival exports, so the same bank can sing in OpenUtau or feed another project unchanged.
8. **Neural track:** park it, and revisit only with Piper trained on your own data.

## Decisions that remain yours, and open questions

- **Read style:** strict monotone (cleanest joins, most "machine") or a slightly natural read (warmer, more join artefacts).
- **Stress inventory:** one vowel set, or separate stressed and unstressed vowels, which Festvox's tutorial warns "will almost double the number of diphones in your list."
- **Performed Red Room scope:** how much of the backward voice must be bodily performed to count as authentic for you, versus derived in software.
- **Pronunciation authority:** your own idiolect, including how you said these words in 2014–2015, versus dictionary norms.
- **Subtitles:** whether Red Room passages are always subtitled (Lynch did) and in which hand.\[40\]
- **GPL exposure:** accept GPL-3.0 eSpeak NG in the page or stay with lexicon-only.
- **Voice license terms** and whether the source masters are ever published.
- **Open questions:** the exact Festvox US prompt count for your chosen phone set; the actual WASM sizes of the optional components; and whether MFA aligns your reversed performances well enough, which the pilot should answer.

## Caveats

- Lynch's process comes from a few interviews plus secondary retellings. The Hurley/Eng and Anderson accounts are first-hand. The trainer, recorder-imitation, hidden-prompter and backwards-movement details come from secondary or hearsay sources and conflict in places. The *Lynch on Lynch* quote was read second-hand.
- Recording-time and size figures are engineering estimates built on Festvox's numbers, not measured on your voice.
- Some maintenance and license details come from package registries and third-party summaries rather than the projects' own pages: Piper's v1.8.0 date, SoundTouchJS's license, and MBROLA voice licenses. Re-check them at build time.
- Recording practice and rights guidance here are general practitioner advice, not legal advice.

## Sources

1. [Behind the weird, wonderful sound of 'Twin Peaks: The Return' - with Dean Hurley and Ron Eng:](https://www.asoundeffect.com/twin-peaks-sound/)
2. [Building Voices in the Festival Speech Synthesis System - 8 Diphone databases](http://festvox.org/festvox-1.2/festvox_8.html)
3. [Creating New Language and Voice Components for the Updated MaryTTS](https://aclanthology.org/L18-1501.pdf)
4. [Speech Synthesis in Festival - 7 Waveform synthesis](http://festvox.org/festtut/notes/festtut_7.html)
5. [Building Voices in the Festival Speech Synthesis System - 5 Diphone databases](http://www.festvox.org/festvox-1.1/festvox_5.html)
6. [MBROLA](https://en.wikipedia.org/wiki/MBROLA)
7. [MBROLA - Wikidata](https://www.wikidata.org/wiki/Q3095934)
8. [Festival Speech Synthesis System](https://en.wikipedia.org/wiki/Festival_Speech_Synthesis_System)
9. [openutau/OpenUtau on GitHub](https://releasealert.dev/github/openutau/OpenUtau)
10. [OpenUtau download and guide: open source UTAU successor](https://hysenlabs.com/en/projects/openutau-openutau)
11. [montreal-forced-aligner - conda-forge](https://anaconda.org/conda-forge/montreal-forced-aligner)
12. [GitHub - MontrealCorpusTools/Montreal-Forced-Aligner: Command line utility for forced alignment using Kaldi · GitHub](https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner)
13. [GitHub - MontrealCorpusTools/mfa-models: Collection of pretrained models for the Montreal Forced Aligner · GitHub](https://github.com/MontrealCorpusTools/mfa-models)
14. [Piper TTS Review: Fast Local Neural TTS](https://www.promptquorum.com/power-local-llm/piper-tts-review)
15. [Utau](https://en.wikipedia.org/wiki/Utau)
16. [Diphone databases](http://festvox.org/bsv/c2265.html)
17. [GitHub - classical-cat-dh-lab/espeak-ng-wasm: Reproducible WebAssembly builds of eSpeak NG for browser-based IPA-input speech synthesis · GitHub](https://github.com/classical-cat-dh-lab/espeak-ng-wasm)
18. [espeak-phonemizer CDN by jsDelivr - A CDN for npm and GitHub](https://www.jsdelivr.com/package/npm/espeak-phonemizer)
19. [GitHub - Spelling-Creator/spellophone: A WebAssembly port of espeak-ng. · GitHub](https://github.com/Spelling-Creator/spellophone)
20. [Releases · stakira/OpenUtau - GitHub](https://releasealert.dev/github/stakira/OpenUtau)
21. [English (US) ARPA acoustic model v3.0.0 — mfa model 3.1.2 documentation](<https://mfa-models.readthedocs.io/en/latest/acoustic/English/English%20(US)%20ARPA%20acoustic%20model%20v3_0_0.html>)
22. [signalsmith-stretch - npm](https://www.npmjs.com/package/signalsmith-stretch)
23. [Piper TTS Setup: Install on Windows, Linux & Raspberry Pi](https://localaimaster.com/blog/piper-tts-setup-guide)
24. [Local TTS Models: Capabilities, Code and Weight Licenses](https://www.codesota.com/guides/tts-models)
25. [Best Local TTS Models 2026: 8 Open-Source Voices Tested](https://localaimaster.com/blog/best-local-tts-models)
26. [Official Coqui XTTS v2 License (CPML): Commercial Use 2026](https://www.promptquorum.com/power-local-llm/local-tts-voice-cloning-piper-coqui-xtts)
27. [Method for producing a speech rendition of text from diphone sounds](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6879957)
28. [Phonemizers · openutau/OpenUtau Wiki · GitHub](https://github.com/openutau/OpenUtau/wiki/Phonemizers)
29. [GitHub - VoCreatures/ENG-ARPA-Reclist: Repository for English Arpasing list with original strings for full VCV vowels and new CCs. · GitHub](https://github.com/VoCreatures/ENG-ARPA-Reclist)
30. [Reclists](https://arpasing.tubs.wtf/en/directories/reclists)
31. [deadbyte's carrd](https://deadbyte.carrd.co/)
32. [Lynch’s ‘backwards voice’](https://danny260blogblog.wordpress.com/2015/11/15/lynchs-backwards-voice/)
33. [List of Twin Peaks characters](https://en.wikipedia.org/wiki/List_of_Twin_Peaks_characters)
34. [Interview: Michael J. Andersen from Twin Peaks - FanBolt](https://www.fanbolt.com/5959/interview-michael-j-andersen-from-twin-peaks/)
35. [The Man from Another Place](https://en.wikipedia.org/wiki/The_Man_from_Another_Place)
36. [Michael J. Anderson](https://en.wikipedia.org/wiki/Michael_J._Anderson)
37. [First Look: Twin Peaks Actor Carel Struycken Rehearses His Lines In Reverse Using iPhone App (Video)](https://welcometotwinpeaks.com/behind-the-scenes/carel-struycken-red-room-backwards-speech-iphone-app/)
38. [Michael J. Anderson](https://twinpeaks.fandom.com/wiki/Michael_J._Anderson)
39. [An Analysis of the Unfolding of 'Twin Peaks: The Return' - Part 1](https://idyllopuspress.com/idyllopus/film/tpr1.htm)
40. [Twin Peaks' Red Room Was Created To Serve A Surprisingly Practical Purpose - SlashFilm](https://www.slashfilm.com/836610/twin-peaks-red-room-was-created-to-serve-a-surprisingly-practical-purpose/)
41. [Shooting in Reverse: Nightmares in Red from Twin Peaks](https://synkroniciti.com/shooting-in-reverse-nightmares-in-red-from-twin-peaks/)
42. ["Twin Peaks" Beyond Life and Death (TV Episode 1991) - Michael J. Anderson as Man From Another Place](https://www.imdb.com/title/tt0734815/characters/nm0027199/)
43. [How 'Twin Peaks' created the Red Room dialogue effect](https://faroutmagazine.co.uk/strange-dialogue-twin-peaks-red-room/)
44. [Rückwärtssprache: Eine besondere Begabung gibt Einblicke in die Sprachverarbeitung](https://www.fcmh.de/de/nachrichten/20260902rueckwaertssprache)
45. [Back in time: Reversed speech as a window into cognitive language processing—A systematic review - Psychonomic Bulletin & Review](https://link.springer.com/article/10.3758/s13423-026-02952-1)
46. [Phonetic Reverser](https://spea.cc/backwards)
47. [Back in time: Reversed speech as a window into cognitive language processing—A systematic review - PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13506624/)
48. [SpeakBackwards — Reverse Audio Challenge](https://speakbackwards.com/)
49. [R2bEEaton's Phonetic Reverser - Bored Hoard](https://boredhoard.com/discover/r2beeatons-phonetic-reverser/)
50. [Training-Free Cross-Lingual Dysarthria Severity Assessment via Phonological Subspace Analysis in Self-Supervised Speech Representations](https://arxiv.org/pdf/2604.10123)
51. [Festival Speech Synthesis System: 21. Diphone synthesizer](http://www.festvox.org/docs/manual-2.4.0/festival_21.html)
52. [Voicebank development · openutau/OpenUtau Wiki · GitHub](https://github.com/openutau/OpenUtau/wiki/Voicebank-development)
53. [How to make an oto.ini BASIC TUTORIAL](http://camilamelodia.blogspot.com/2010/08/how-to-make-otoini-basic-tutorial.html)
54. [(PDF) Diphone Collection And Synthesis](https://www.researchgate.net/publication/2891551_Diphone_Collection_And_Synthesis)
55. [GitHub - audiojs/pitch-shift: Pitch shift algorithms · GitHub](https://github.com/audiojs/pitch-shift)
56. [\[Audio\] Add independently pitched and time-warped sound-seed playback with a latency-aware owned stretch adapter · Issue #1186 · doublemover/LemmingsJS-MIDI · GitHub](https://github.com/doublemover/LemmingsJS-MIDI/issues/1186)
57. [signalsmith-stretch - npmx](https://npmx.dev/package/signalsmith-stretch)
58. [GitHub - Signalsmith-Audio/signalsmith-stretch: C++ polyphonic pitch/time library (GitHub mirror) · GitHub](https://github.com/Signalsmith-Audio/signalsmith-stretch)
59. [Piper vs Chatterbox TTS (2026): Which One?](https://www.promptquorum.com/power-local-llm/piper-vs-chatterbox-tts)
60. [kokoro-js - npm](https://www.npmjs.com/package/kokoro-js)
61. [@Xenova on Hugging Face: "Introducing Kokoro.js, a new JavaScript library for running Kokoro TTS, an 82…"](https://huggingface.co/posts/Xenova/503648859052804)
62. [OTO thingie-](https://utau.fandom.com/f/p/4400000000000055369)
63. [Base OTO Guide](https://utau.felinewasteland.com/ref/baseoto)
64. [Oto Editing](https://deepwiki.com/chenjunr/OpenUtau/6.3-oto-editing)
65. [OtoIni Handling](https://deepwiki.com/oatsu-gh/utaupy/5.1-otoini-handling)
