# Voice-Only Generative Sound for a Web Poetry Archive: Field Survey, Techniques, Architecture and Recording Plan

**Recommended approach: do the heavy voice transformation offline. Render the extreme stretches, drones and textures from Anthony's phoneme recordings into a small set of compressed stems. In the browser, run a light, gesture-unlocked Web Audio mixer that crossfades, re-pitches and grains those stems in response to what the reader is looking at.** This is how the strongest precedents work, from Cayley/Perring's *translation* to Eno's generative systems: the sound keeps reacting, but it never has to compute anything expensive in real time on an iPhone.

## TL;DR

- **Field and aesthetics:** The best precedents treat voice as raw material that changes slowly. Examples are Henri Chopin's slowed and accelerated tape "micro-articulations", Trevor Wishart's *Vox-5* voice morphs, Leif Inge's 24-hour *9 Beet Stretch*, and John Cayley's *translation* with Giles Perring's sung alphabets. Their responsiveness works at the level of state and texture. They don't use a "beep per click" model. That is the model to follow if the sound is not to mar the experience.
- **Technique and stack:** Stretch long sustained vowels, nasals and fricatives offline with Paulstretch (random phase, very large windows). Build reverbs by convolving with his own voice. In the browser, use plain Web Audio plus a small AudioWorklet granulator, or Tone.js's GrainPlayer (MIT). Add Signalsmith Stretch (MIT, WASM/AudioWorklet) only if live pitch or formant shifting is needed. Avoid GPL engines (Rubber Band, eSpeak NG) in the shipped page.
- **Mobile and quality:** Sound starts off and is unlocked on the first tap. Recover from Safari's `interrupted` state. Opt into `navigator.audioSession.type = "playback"` only after the reader turns sound on. Ramp every parameter. Keep decoded audio small: about 23 MB per minute of 48 kHz stereo. Pre-compute phonemes per poem at build time, hand-corrected by the artist, so spelling quirks and struck words are his decisions and no algorithm's.

## Key Findings

### 1. The field: what to learn from precedents

**Sound poetry and text-sound composition.** In the mid-twentieth century, voice-as-material took off once tape recorders became available.\[1\] Henri Chopin's *poésie sonore* was built from "his mouth, magnetic tape, and microphones."\[2\] The 43-minute documentary *Vibrant Spaces – Henri Chopin's Sound Poetry* (soundscentral.org, with poet and curator Enzo Minarelli) states that "the restriction to tape-modified material and his use of extremely accelerated or slowed-down micro-articles make Henri Chopin a pioneer of sound poetry in the late 1950s." That is the direct ancestor of the slowing and speeding of phonemes Anthony proposes. Around 1967, Lars-Gunnar Bodin and Bengt Emil Johnson in Sweden coined the term "text-sound composition."\[3\] In 1973 Charles Amirkhanian released *10+2: 12 American Text Sound Pieces*, which Music & Literature's "Restless Minimalism" (2017) describes as "widely considered to be the first major album of American text-sound compositions" (some sources date the release 1974/75). Amirkhanian said his text-sound pieces "are really finally done while listening to the sounds on tape and are not pre-composed." That matters here: the material should be tuned by ear, not specified up front.

**Voice-derived electroacoustic music.** Trevor Wishart's *Vox-5* (made at IRCAM in 1986) centres on "a (super)human voice that metamorphoses into many recognizable sonic images, such as the sounds of crowds, bees, a horse, or bells."\[4\]\[5\] He did it through phase-vocoder spectral interpolation. In "The Composition of 'Vox-5'" (*Computer Music Journal* vol. 12, 1988), Wishart wrote that "one aesthetic aim has been to retain the 'source credibility' of the resulting sounds; that is, they must always be believably vocal or naturalistic." He wanted transformations "without any intervening artefacts which might suggest some other physicality / causality, or even betray the technical process involved." That is the clearest statement in the literature of the line between "natural" and "gimmicky": the listener should hear a voice becoming something else, not hear a plugin.

**Extreme time-stretching.** Leif Inge's *9 Beet Stretch* (2002) stretches Beethoven's Ninth to 24 hours "with no distortion or pitch shifting."\[6\]\[7\] It was first realized in 2002 at NOTAM by Anders Vinjar, Kjetil Matheussen, Leif Inge and Bjarne Kvinnesland, using Snd/CLM granulation at "several hundred to several thousand grains per second," with stretch ratios of roughly 19–23× depending on the length of the source recording. A later re-make by mathr used a "custom phase vocoder with audio input blocks of 8192 samples" and took "5.3 weeks of CPU time (0.51 weeks elapsed time) on a 16-thread desktop processor." That cost is the reason to render extreme stretches offline. Inge's own listening instruction fits ambient poetry well: "This trance feeling, letting the sound just go on without trying to expect anything, is really the way to listen to it."\[8\]

**Electronic literature with generative sound.** John Cayley's *translation* (2004, *Electronic Literature Collection* Vol. 1) is the closest precedent. It is an "ambient time-based" text in which passages surface into and sink out of legibility, with generative music by Giles Perring, who did "the composition, sound design, performance and recording of the sung alphabets."\[9\]\[10\]\[11\] The ELC tags it as a "Textual Instrument," and Milligan's "Locked in Translation" (*Hyperrhiz* 20) notes that "it allows interactors to warp Perring's soundtrack through the text as a type of instrument." The lessons: a voice-derived alphabet library, sound tied to the *legibility state* of text, and time-based ambience rather than event sounds. Jörg Piringer's *abcdefghijklmnopqrstuvwxyz* (iOS, honorary mention at Prix Ars Electronica 2010) gives each letter a voiced sound ("'a' sounds like 'ahh'"), and letters "stick to each other and create a blended sound."\[12\]\[13\] It shows how direct letter-to-voice mapping can work, but it works because the piece is openly a *sound toy*. In a reading-focused archive the same one-to-one mapping would compete with the text.

**Text-to-sound installations.** Mark Hansen and Ben Rubin's *Listening Post* (2002–06; 2004 Golden Nica, Ars Electronica) culls text from "thousands of unrestricted Internet chat rooms" onto "a suspended grid of more than two hundred small electronic screens," and cycles through "six movements, each a different arrangement of visual, aural, and musical elements, each with its own data processing logic." Its structure, with distinct sonic "modes" tied to display modes, maps neatly onto the scatter, by-poem and spiral arrangements. One description notes "with each changing word comes a clicking sound."\[14\] That works in a gallery but would become a tic in a personal reading interface.

**Generative and adaptive music.** Eno described generative music as one where the composer "'designs' the processes that make the music". Koan used "'probabilistic' rules — defined by the composer — to determine which notes will be played, so each performance is unique."\[15\] In Bloom (Eno and Chilvers), the app takes over when the user goes idle, which is a good model for what happens when the reader stops touching the piece.\[16\] Game audio supplies the engineering vocabulary. *Vertical layering* adds or removes stems by intensity, and *horizontal re-sequencing* moves between sections at musical boundaries. Both exist partly to fight "repetition and ear fatigue."\[17\]\[18\]

**What separates strong examples from annoying ones (synthesis).** Strong works share four traits. Sound responds to *state* (which text is legible, which mode is active), not to every input event. Change is slow and continuous. The source stays recognizable (Wishart's credibility). Silence and idling are designed. Weak examples tend to fire a sound on every interaction, loop audibly, process the source until it sounds like an effect preset, or hold one loudness level. This is my reading of the precedents above, not a finding from a formal study.

### 2. Techniques: natural vs. gimmicky

| Technique | What it does to voice | "Natural" when… | Gimmicky when… | Where to run it |
|---|---|---|---|---|
| **Paulstretch** (FFT, randomized phase, windows in seconds) | Turns a 1 s vowel into a minutes-long breath-like pad | Source is a sustained vowel, nasal or fricative; window ≈0.25–1 s | Applied to plosives or speech (smear), or below 2× ("washed out")\[19\] | Offline |
| **Phase vocoder stretch** (Rubber Band, Signalsmith) | Keeps formant and pitch identity at moderate stretch | 0.75×–4× on vowels\[20\] | Large factors → "phasiness" and metallic artefacts\[21\] | Offline, or live (Signalsmith) |
| **Granular synthesis** | Clouds, stutters and freezes from short grains | Grains 30–150 ms with jittered position and envelope; slow density changes | Audible grain rate, fixed periodic grains ("machine-gun") | Live (cheap) |
| **Pitch shift by resampling** (`playbackRate`) | Chopin-style tape speed: lower and darker, or higher and smaller | Octave/fifth transpositions of already-stretched pads; slow glides | Chipmunk/demon voice on raw speech | Live (free) |
| **Formant-preserving / shifting pitch** | Changes pitch without "size" change, or vice versa | Subtle: ±3 semitones, small formant offsets for "another throat" | Large formant shifts → cartoon | Offline; live via Signalsmith |
| **Spectral freeze** | Holds one spectral frame indefinitely | Frozen vowel as a drone bed | Static for long periods → fatigue | Offline (render) |
| **Convolution with own voice as IR** | His whisper or "sss" becomes the "room" of other sounds | Short, decaying IRs; low wet mix | Long tonal IRs → mud | Live `ConvolverNode` (moderate cost) |
| **Cross-synthesis / vocoding** | One phoneme's spectrum shapes another | Vowel envelope on fricative noise ("whispered vowel") | Classic robot-vocoder sound | Offline |
| **Layered drones and filtering** | Stacks of stretched vowels tuned to intervals | Few layers, slow detune drift | Too many layers → generic pad | Live mix of pre-rendered stems |

Paulstretch is built for very large factors. Audacity's manual calls it "not a general-purpose time stretcher" with a default factor of 10 and a 0.25 s time resolution. "Short windows keep more of the original rhythm and transients but sound grainier; long windows smooth everything into a sustained pad and lose all trace of the attack."\[22\] Its method is to randomize the phase where a phase vocoder would unwrap it. That avoids the "phasiness" of phase-vocoder stretches.\[23\] A magnetosphere sonification study notes it is not suitable for compression (factors below 1).\[24\] "Hundreds of percent" (2–10×) sits where phase vocoders and Paulstretch overlap. For the ambient layer, factors of 20–200× are where Paulstretch is at its most beautiful.\[25\] The artist should audition both.

### 3. Mapping text and interaction to sound

**Getting phonemes.** Because the 100 poems are fixed, authored texts, the best solution is **build-time G2P with hand correction**, not live G2P:

- Use the CMU Pronouncing Dictionary (134,000+ words in ARPAbet, 39 phonemes, stress marked 0/1/2) through `cmu-pronouncing-dictionary` (npm, ISC) or Allison Parrish's `pronouncing` (JS port of her Python module).\[26\]\[27\]\[28\] These produce a phoneme file per poem and version, e.g. `poem-042.v3.phon.json`.
- For words the dictionary lacks (handwritten coinages, misspellings, archaic or nonstandard forms), the build script flags them.\[29\] Anthony types the pronunciation he intends, or marks the word as "unvoiced." This keeps interpretation in his hands, consistent with the no-AI-text rule. The phoneme data is never displayed.
- **Struck-through words** get a flag, not deletion. One option is to render their phonemes through a muffled, quieter, reversed or "under-layer" path, so revisions are audible as ghosting.
- **Uncertain readings** (illegible words) can map to a deliberately indeterminate sound, such as noise grains from fricatives with no vowel colour.
- eSpeak NG compiled to WASM exists, but it is GPL-3.0 and 2–3 MB, so it is a poor fit for the client. Use it offline only if at all.\[30\]\[31\]\[32\]

**Mapping layers (concrete options, all suggestions):**

| Interface/text feature | Sound parameter | Example |
|---|---|---|
| Arrangement mode (scatter / by-poem / spiral) | Which stem "movement" plays (horizontal re-sequencing, à la *Listening Post*) | Scatter = sparse grains of many vowels; spiral = one continuous drone that advances through notebook order; by-poem = drone built from that poem's dominant vowels |
| Zoom level | Grain size, density, filter brightness, dry/wet | Whole page = distant, reverberant, low-passed bed; one line across the screen = closer, drier, individual phonemes become audible |
| Visible/selected line's phonemes | Which phoneme samples feed the granulator | Line rich in /iː/ and /s/ → bright, hissing texture; /uː/, /m/, /n/ → dark hum |
| Vowel/consonant ratio | Pad vs. noise balance | Consonant-heavy line raises fricative noise layer |
| Stress pattern (CMU 0/1/2) | Slow amplitude pulse or grain-onset rhythm | Iambic line → gentle weak-strong breathing at ~1/4 of reading pace |
| Sound repetition (alliteration, assonance, rhyme) | Reinforcement: a repeated phoneme gets a sustained, louder voice in the drone | Repeated /l/ across a line → a stretched "lll" partial emerges |
| Line length | Phrase length of grain gestures | Long lines → longer swells |
| Word frequency (rare words) | Rare "events" | A rare word under the finger releases a single stretched breath of that word's stressed vowel |
| Version stack peeling | Crossfade between versions' phoneme sets, with the old version's sound briefly smeared (freeze → fade) | The sound "remembers" the previous draft for a few seconds |
| Hand ↔ Font view | Rough/close-miked vs. smoother/more distant processing | Hand = drier, more breath noise; Font = more reverb, more tonal |
| Idle reader | Bloom-style autonomous drift | After ~20 s idle, slowly re-sequence among the page's phonemes |

**Avoiding mickey-mousing.** Rules of thumb: (1) map interaction to *targets* that parameters glide toward over 0.5–5 s, never to instant triggers; (2) quantize events to a slow clock (e.g., new grains may only start on a 1–2 s grid); (3) rate-limit "event" sounds (e.g., at most one per 8 s); (4) let some mappings be many-to-one, so the sound tracks the poem's overall character rather than each touch; (5) add seeded randomness per visit, matching the "new arrangement every visit" logic of the canvas. The sound should be *felt to correspond*. It should not be legible as a code.

### 4. Browser architecture

**Library comparison**

| Option | Licence | Fit | Notes |
|---|---|---|---|
| Plain Web Audio (AudioBufferSourceNode, GainNode, BiquadFilter, ConvolverNode) | Browser API | **Core recommendation** | Zero bundle; resampling-based pitch via `playbackRate`/`detune` |
| Custom granular AudioWorklet | Your own code | **Recommended** for live granulation | A few hundred lines; full control over grain envelopes and allocation |
| Tone.js (incl. `GrainPlayer`) | MIT | Good for prototyping | `GrainPlayer` "enables you to adjust pitch and playback rate independently"; larger bundle than needed in production\[33\]\[34\] |
| Signalsmith Stretch Web | MIT | Optional live pitch/formant/stretch | Official WASM/AudioWorklet release, ~232 kB install, 0 deps; pitch/formant controls and latency reporting\[35\]\[36\] |
| Rubber Band (WASM ports) | GPL-2.0 or commercial | Offline only | Excellent quality, but GPL obliges releasing the whole app under GPL unless licensed commercially\[37\]\[38\] |
| SoundTouch | LGPL-2.1 | Not recommended | Tuned for tempo-change, not extreme ambient work\[39\] |
| RNBO (Max → web) | Generated code dual-licensed (Cycling '74 export licence or GPLv3); engine MIT | Good if Anthony patches in Max | Noncommercial use free; commercial use needs a licence; RNBO itself costs $10/mo, $100/yr or $299\[40\]\[41\] |
| Faust → WASM | Compiler GPL; generated code usable under your own terms (check current Faust licence notes) | Good for custom DSP | Efficient, sample-level DSP\[42\] |
| Csound WASM / WebPd | LGPL / various | Possible | Csound even has a `paulstretch` opcode; heavier runtime\[43\] |

**Offline vs. live split (recommendation)**

*Offline (on the artist's machine, any tools he likes: Audacity Paulstretch, PaulXStretch, CDP/Sound Loom, Csound, Rubber Band CLI):*
1. Clean and trim the phoneme library (see §6).
2. Render for each phoneme or phoneme family: (a) a 30–90 s Paulstretch pad at two or three window sizes, (b) spectral freezes, (c) a couple of formant-shifted and octave variants, (d) short IRs (whispers, fricatives, breaths) for convolution.
3. Render 6–12 "movement" beds for the arrangement modes, built entirely from those materials.
4. Export compressed stems, plus a JSON manifest mapping phonemes to files.

*Live (browser):*
- A **mixer** of 3–6 looping stem voices with slow equal-power crossfades.
- A **granulator** (AudioWorklet) reading the short raw phoneme buffers (small, so cheap to decode), driven by the visible text's phoneme list.
- One `ConvolverNode` with a voice-IR, plus filter, master limiter and gain.
- A **control layer** on the main thread that turns UI state (zoom, mode, selection, version) into parameter *targets*, sent at no more than ~10 Hz.

This split keeps CPU low and the bundle tiny. Per-visit generativity still comes from which stems, which grains, and when.

### 5. Quality and mobile-performance checklist

**Unlock and session**
- Create or resume the AudioContext synchronously inside a tap or click handler (not after an `await`), and play a one-sample silent buffer. Listen on `click`/`touchend`/`keydown`. `touchstart` is not a WebKit activation event.\[44\]\[45\]\[46\]
- Handle Safari's non-standard `interrupted` state. MDN notes that when an iOS user switches tabs, minimizes, or locks the screen, "the audio context's state changes to 'interrupted' and needs to be resumed." Resume on any non-running, non-closed state, on the next gesture, and on `visibilitychange`/`pageshow`.\[47\]\[48\]
- **Silent switch:** iOS treats Web Audio as "ambient," which the ring/silent switch mutes. Setting `navigator.audioSession.type = "playback"` (Safari 17+) makes it audible "at the cost of pausing other apps' audio."\[49\]\[50\]\[51\] Recommendation: set it only after the reader explicitly turns sound on. Respecting the switch by default is defensible too. That is the artist's call.
- **Sample rate:** don't force `sampleRate: 44100` on iOS. WebKit bug 154538 documented severe distortion when the rate flipped from 44.1 to 48 kHz. Apple's Jer Noble noted the iPhone 6S speaker supports only 48 kHz and that developers "can't assume that the output sample rate will always be 44.1kHz."\[52\] Bug 274507 recorded an iPadOS 17.5 regression with distortion when using a 44.1 kHz context with an AudioWorklet (fixed May 2024).\[53\] Let the context use the native rate. Ship assets at 48 kHz, because WebKit's built-in resampling is linear and "low quality" (Paul Adenot).\[54\]

**Memory and loading**
- Decoded AudioBuffers are 32-bit float. At 48 kHz stereo that is 384,000 bytes/s, about 23 MB per minute (my arithmetic from the spec's float format). Ten minutes of stereo stems decoded at once is about 230 MB, which is risky on iPhone. WebKit is killed by "jetsam reason highwater" when it exceeds its limit, and there are anecdotal reports of a 9 MB MP3 crashing iOS Safari.\[55\]\[56\] Apple publishes no tab memory limit.
- Mitigations: make most beds **mono** (half the cost) and short (30–60 s loops with randomized loop points). Decode lazily per arrangement mode and per poem. Free buffers you no longer need. Stream the longest bed through a media element routed by `MediaElementAudioSourceNode` instead of decoding it. Share one decoded buffer across many source nodes.\[54\]
- **Formats:** AAC in `.m4a` is the safe universal baseline. WebM/Opus decodes through `decodeAudioData` on iOS, and Safari 17.4 made WebM Opus support consistent. But a related WebKit issue (245428) was still reported as blocking, so test before relying on Opus.\[57\] Target 96–128 kbps stereo or 64 kbps mono for pads; the raw phoneme library can ship at higher quality since it is small.
- Load audio *after* the canvas is interactive. The first sound should be a bed that is already decoded (small), so pressing "sound on" responds instantly.

**Glitch-free DSP and frame rate**
- Audio renders in 128-frame quanta (≈2.67 ms at 48 kHz), and Web Audio 1.1 drafts make this configurable, so never assume a block size.\[58\]\[59\]\[60\] Hongchan Choi (Google): allocation in the audio thread "eventually triggers a garbage collection which synchronously blocks the thread… it results in glitches." Allocate grain pools up front. Avoid `new` and closures in `process()`.\[61\]
- Keep all DSP in the AudioWorklet or native nodes, never on the main thread, so the canvas's `requestAnimationFrame` loop is untouched. Send control messages through `port.postMessage` at a low rate. SharedArrayBuffer ring buffers need cross-origin isolation (COOP `same-origin` plus COEP `require-corp`), which can complicate static hosting.\[62\]\[63\] Avoid them unless necessary.
- **Zipper noise and clicks:** never set `.value` directly on audible params. Chrome has applied `.value` instantly since version 64. Use `setTargetAtTime` (spec author Chris Rogers called it "a convenient way to achieve de-zippering") or `setValueAtTime` + `linearRampToValueAtTime`.\[64\]\[65\] Give every grain and loop a window (Hann or Tukey). Start and stop sources with 10–50 ms fades.
- WebKit scans automation event lists linearly, so many scheduled events on one param add up. Periodically swap in fresh GainNodes for long-running voices (Adenot).\[54\]
- Put a gentle limiter (DynamicsCompressorNode with high ratio and slow release) on the master to catch build-ups from granular density.

**Loudness, fatigue, defaults, control**
- Mix quietly. Treat the sound as a room tone, not a soundtrack. Suggested: master around −24 to −20 LUFS integrated with peaks below −3 dBTP. Avoid sustained energy at 2–5 kHz (sibilant fricatives), where fatigue is worst. Low-pass the "s/sh" layers.
- Build in breathing room: the system should regularly thin out to near-silence for tens of seconds.
- **Default off.** iOS forces this anyway. Make the very first tap that reveals the hidden menu also offer a single sound glyph. On desktop, add an `M` key toggle. Remember the choice in `localStorage`. Fade out on `visibilitychange` hidden and on device lock.
- Accessibility: honour the reader's control, never auto-raise volume, and consider treating `prefers-reduced-motion: reduce` as a signal to also reduce sonic activity (lower density, no event sounds). That is a design analogy, not a standard.

### 6. Phoneme recording plan

**Inventory.** Use the 39 ARPAbet phonemes the CMU dictionary uses (15 vowels/diphthongs: AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW; 24 consonants), plus extras that suit stretching:
- **Sustainables (priority for ambience):** all vowels held 4–8 s at a steady pitch; nasals M, N, NG; liquids L, R; fricatives S, Z, SH, ZH, F, V, TH, DH, HH; glides W, Y held as transitions.
- **Diphthongs (AY, AW, OY, EY, OW):** record both held and slowly gliding, 3–4 s.
- **Plosives and affricates (P B T D K G CH JH):** short takes with 1–2 s of room tail, recorded with and without aspiration. Use them as grain triggers and rhythm, not stretched pads.
- **Vocal sounds:** inhale, exhale, whisper of each vowel, hum, vocal fry, breathy onset, the "unvoiced" versions. Breath and whisper are the most flexible stretch and IR material.

**Takes and variants.** For each sustainable: three takes at his natural speaking pitch, one lower and one higher (about ±4 semitones), plus soft and moderate dynamics. That gives 5–7 takes × ~30 sustainables. Including short phonemes and vocal sounds, expect about 250–350 files, roughly two to three hours of session time with breaks. Also consider reading each of the first poems once, slowly, as source for later phase work. This keeps everything in his voice.

**Mic, room and settings.**
- A quiet, *dead* room matters more than the microphone: closets of clothes, duvets, or a reflection filter. Room reverb gets magnified hundreds of times by stretching. Turn off fridges and fans, because stretching turns hum into tones.
- Large-diaphragm condenser or good dynamic, 15–25 cm from the mouth, slightly off-axis to soften plosives, pop filter.
- Record 48 kHz / 24-bit mono WAV, peaks around −12 dBFS, and no processing at capture (no compression, no noise reduction).
- Record 10 s of room tone per session for denoising profiles and to match silence.

**Editing and loudness.**
- Trim to the steady portion of each sustain and keep separate onset files. Apply 5–20 ms fades. High-pass at around 60–80 Hz. Use light, manual de-noising only.
- Normalize *per category*, not per file. Peak normalization will make fricatives too loud relative to vowels. Match perceived loudness (e.g., about −20 LUFS short-term for sustains) by ear.
- Keep un-normalized originals archived.

**Naming and metadata.** `AJ_<ARPAbet>_<type>_<pitch>_<dyn>_<take>.wav`, e.g. `AJ_IY_sus_mid_soft_02.wav`, `AJ_S_sus_mid_mod_01.wav`, `AJ_T_onset_mid_mod_03.wav`. Keep a CSV/JSON sidecar with phoneme, IPA, type, pitch estimate, duration, date, mic, and notes. Embed artist and copyright in BWF/iXML metadata so ownership travels with the files.

### 7. Rights and ownership

- The approach above uses **only his recorded voice**. Paulstretch, phase vocoders, granulation and convolution are deterministic signal processing of his recordings, not generative AI voice. Every IR should be recorded from his own voice too, not from commercial reverb IR libraries.
- No third-party samples, no TTS. eSpeak and CMU are used only to *compute* phoneme labels, which are hand-corrected by him and never voiced or shown.
- Licences: Tone.js MIT; Signalsmith Stretch MIT (keep the copyright notice); CMU dictionary package ISC; Rubber Band GPL/commercial and eSpeak NG GPL-3.0 (offline tools only, which does not create obligations for the web page as long as they are not distributed with it);\[66\]\[67\] RNBO export under the Cycling '74 licence, with commercial use needing a licence; SoundTouch LGPL-2.1.\[27\]\[38\]\[39\]\[40\]\[68\]\[69\] Confirm the licence of any `pronouncing` JS port before shipping it.\[70\]
- Note that GitHub hosting of the page source implies public audio files. If he wants the raw phoneme library to stay private, ship only processed stems and grain-sized excerpts.

## Recommendations: Phased Prototype Plan

1. **Phase 0, sound sketch (1–2 weeks, no code).** Record a pilot set: five vowels (IY, AA, UW, ER, AH), M, N, S, SH, F, breath and whisper. Render Paulstretch at 10×, 50× and 200× with 0.25 s and 1 s windows. Listen on iPhone speaker and earbuds. Decide the aesthetic palette by ear, following Amirkhanian's practice of composing while listening.
2. **Phase 1, static bed + controls.** Add a single tap-to-enable bed per arrangement mode with crossfades, the iOS unlock/interrupted/visibility handling, the hidden sound toggle, and mute persistence. Measure memory in Safari Web Inspector and check that canvas FPS is unchanged.
3. **Phase 2, text-aware layer.** Build the build-time G2P pipeline with Anthony's override file. Add the granulator worklet fed by the visible line's phonemes. Add zoom → density/brightness mapping, with all changes as slow targets.
4. **Phase 3, versions and revisions.** Add version-peel smear and crossfade, the struck-word ghost layer, and the Hand↔Font contrast.
5. **Phase 4, weekly-poem workflow.** Add a per-poem script that produces the phoneme JSON and optionally one poem-specific bed (its dominant vowels), so each weekly release has its own sonic fingerprint at a few hundred KB.
6. **Phase 5, roots and glyphs.** When the linguistic breakdown phase arrives, map roots and morphemes to stem families and glyph strokes to grain envelopes. The phoneme library and manifest already support this.

Test each phase on a real iPhone with the silent switch both on and off, with headphones, after a phone call interruption, and after 20 minutes of use (heat, battery).

## Caveats

- Several mobile-Safari behaviours (silent switch, `interrupted` recovery, Opus support) come from WebKit bug threads, MDN and developer reports rather than Apple documentation. They change between iOS releases, so re-test on each major iOS update.
- The memory figures are computed from the 32-bit float PCM format. Real usage can be higher, and Apple publishes no Safari memory ceiling.
- The loudness targets, grain sizes, rate limits and recording counts are practitioner recommendations, not standards. They are starting points for the artist's ears.
- The judgement about which precedents "work" or "annoy" is my critical synthesis, not the result of user research.
- Licence notes are summaries. Read the actual licence files before shipping, especially for RNBO commercial use and Faust-generated code.

## Sources

1. [Ode To Gravity: Three French Sound Poets, 1972 : Free Borrow & Streaming : Internet Archive](https://archive.org/details/OTG_1972_09_27_c1)
2. [JACK PATTERSON Henri Chopin From the Paper Civilization to the Electronic Age](https://monoskop.org/images/8/87/Patterson_Jack_2022_Henri_Chopin_From_the_Paper_Civilization_to_the_Electronic_Age.pdf)
3. [Sound Poetry: I. History of Electro-Acoustic Approaches II. ...](https://textinart.wordpress.com/wp-content/uploads/2018/10/soundpoetry.pdf)
4. [Trevor Wishart: Chemistry Of Sound • Digicult](https://digicult.it/digimag/issue-041/trevor-wishart-chemistry-of-sound/)
5. [The Composition of "Vox-5"](https://www.semanticscholar.org/paper/The-Composition-of-%22Vox-5%22-Wishart/5e5a3296043d67e7d31f5e52afcbd4b9cd9a28d7)
6. [9 Beet Stretch :: mathr](https://mathr.co.uk/web/9-beet-stretch.html)
7. [9 Beet Stretch](https://www.coalescesionrecords.com/product/9-beet-stretch/)
8. [9 Beet Stretch: an avant-garde experiment in sound perception](https://faroutmagazine.co.uk/9-beet-stretch-experiment/)
9. [Locked in Translation: “Digital” Literature and the Embodied Frameworks of Language](https://hyperrhiz.io/hyperrhiz20/interfaces/2-milligan-locked-translation.html)
10. [Electronic Literature Collection Volume One](https://collection.eliterature.org/1/index.html)
11. [Screen Writing: A Practice‐based, EuroRelative Introduction to Electronic Literature and Poetics: Third Text: Vol 21, No 5](https://www.tandfonline.com/doi/abs/10.1080/09528820701599743)
12. [Abcdefghijklmnopqrstuvwxyz](https://directory.eliterature.org/individual-work/466)
13. [abcdefghijklmnopqrstuvwxyz - App Store - Apple](https://apps.apple.com/us/app/abcdefghijklmnopqrstuvwxyz/id358824534)
14. [The Listening Post — 21st Century Digital Art](http://www.digiart21.org/art/the-listening-post)
15. [koan plus generative music 1](https://www.moredarkthanshark.org/eno_int_sos-jun96.html)
16. [Bloom (software)](<https://en.wikipedia.org/wiki/Bloom_(software)>)
17. [What is Adaptive Music?. I. Linear adaptive music.](https://medium.com/@clauderuellemusic/what-is-adaptive-music-db3a4a15f1b5)
18. [Video Game Music: How It Is Composed and Implemented](https://aplusgamesstudio.com/blog/video-game-music-how-its-made)
19. [GitHub - audiojs/stretch: Time stretch algorithms · GitHub](https://github.com/audiojs/stretch)
20. [Signalsmith Stretch: How Modern Pitch-Shifting Actually Works - PracticeSession](https://www.practicesession.app/blog/signalsmith-stretch-deep-dive/)
21. [Extreme Audio Time Stretching Using Neural Synthesis](https://arxiv.org/pdf/2211.16992)
22. [Paulstretch](https://www.audacityteam.org/manual/effects/pitch-and-tempo/paulstretch/)
23. [Timbral effects the Paulstretch audio time-stretching algorithm - ADS](https://ui.adsabs.harvard.edu/abs/2022ASAJ..151A.158M/abstract)
24. [Listening to the magnetosphere: How best to make ULF waves audible](https://arxiv.org/pdf/2206.04279)
25. [What Is Paulstretch and How Does It Work? Explained](https://reverie.parallel-minds.studio/en/blog/paulstretch-explained)
26. [GitHub - aparrish/pronouncingjs: a simple javascript interface to the CMU pronouncing dictionary (for node and browser!) · GitHub](https://github.com/aparrish/pronouncingjs)
27. [cmu-pronouncing-dictionary - npm](https://www.npmjs.com/package/cmu-pronouncing-dictionary)
28. [gen-text-workshop/cmu\_pronouncing\_dictionary\_notes.md at master · aparrish/gen-text-workshop · GitHub](https://github.com/aparrish/gen-text-workshop/blob/master/cmu_pronouncing_dictionary_notes.md)
29. [cmudict - npm](https://www.npmjs.com/package/cmudict)
30. [LIVE voice without espeak-ng (GPL): transformers.js + misaki G2P port by Senft5 · Pull Request #13 · Senft5/ApexNav · GitHub](https://github.com/Senft5/ApexNav/pull/13)
31. [Invalid license · Issue #6 · xenova/phonemizer.js · GitHub](https://github.com/xenova/phonemizer.js/issues/6)
32. [GitHub - pettarin/espeakng.js-cdn: CDN files for espeakng.js, the Javascript port of eSpeak-ng TTS · GitHub](https://github.com/pettarin/espeakng.js-cdn)
33. [GrainPlayer](https://tonejs.github.io/docs/15.0.4/classes/GrainPlayer.html)
34. [Tonejs repositories · GitHub](https://github.com/orgs/Tonejs/repositories)
35. [\[Audio\] Add independently pitched and time-warped sound-seed playback with a latency-aware owned stretch adapter · Issue #1186 · doublemover/LemmingsJS-MIDI · GitHub](https://github.com/doublemover/LemmingsJS-MIDI/issues/1186)
36. [signalsmith-stretch - npmx](https://npmx.dev/package/signalsmith-stretch)
37. [GitHub - Daninet/rubberband-wasm: Webassembly build of the audio time-stretching and pitch-shifting Rubber Band Library. · GitHub](https://github.com/Daninet/rubberband-wasm)
38. [GitHub - breakfastquay/rubberband: Official mirror of Rubber Band Library, an audio time-stretching and pitch-shifting library. · GitHub](https://github.com/breakfastquay/rubberband)
39. [SoundTouch Sound Processing Library](https://www.surina.net/soundtouch/license.html)
40. [RNBO Export Licensing FAQ](https://support.cycling74.com/hc/en-us/articles/10730637742483-RNBO-Export-Licensing-FAQ)
41. [RNBO ("rainbow"): Start in Max's UI, deliver to plug-ins, Web browsers, hardware, any OS - CDM Create Digital Music](https://cdm.link/rnbo-max-for-web-hardware-plugin/)
42. [github.com](https://github.com/openAVproductions/faust)
43. [Paulstretch - Csound 7 Manual](https://csound.com/manual/opcodes/paulstretch/)
44. [Fix iPhone Safari: pad tap now unlocks audio and plays notes by miguelpdm · Pull Request #35 · miguelpdm/fictional-octo-rotary-phone · GitHub](https://github.com/miguelpdm/fictional-octo-rotary-phone/pull/35)
45. [M01: audio unlock lifecycle for iOS Safari / Teams iPhone by trinhbuikhang · Pull Request #66 · trinhbuikhang/Snake · GitHub](https://github.com/trinhbuikhang/Snake/pull/66)
46. [Rebuilding Apple Watch's "Water Lock" Tone in the Browser (and 3 iOS Safari Gotchas) - DEV Community](https://dev.to/nayeem_software/rebuilding-apple-watchs-water-lock-tone-in-the-browser-and-3-ios-safari-gotchas-d0b)
47. [BaseAudioContext: state property - Web APIs](https://developer.mozilla.org/en-US/docs/Web/API/BaseAudioContext/state)
48. [Playback silent on iOS Safari — AudioContext left "interrupted" never recovers · Issue #106 · unfoldingWord/tc-mobile · GitHub](https://github.com/unfoldingWord/tc-mobile/issues/106)
49. [Add a play-in-silent-mode setting using the Audio Session API by nulltask · Pull Request #285 · nulltask/be-music · GitHub](https://github.com/nulltask/be-music/pull/285)
50. [Play audio with the iPhone silent switch on by systemfreund · Pull Request #57 · systemfreund/grooph · GitHub](https://github.com/systemfreund/grooph/pull/57)
51. [Avoiding unmuting iOS devices for the Web Audio API • blog - nattog.dev](https://nattog.dev/blog/web-audio-ios-unmute)
52. [154538 – Web Audio becomes distorted after sample rate changes](https://bugs.webkit.org/show_bug.cgi?id=154538)
53. [274507 – REGRESSION (iPadOS 17.5): Audio distortion occurs when using AudioContext with a sample rate of 44100Hz and an AudioWorklet](https://bugs.webkit.org/show_bug.cgi?id=274507)
54. [Web Audio API performance and debugging notes](https://padenot.github.io/web-audio-perf/)
55. [Large Audio ArrayBuffers Crashing iOS Safari - Bugs - Babylon.js](https://forum.babylonjs.com/t/large-audio-arraybuffers-crashing-ios-safari/35576)
56. [Safari/WKWebView memory-related crashes on a webpage](https://developer.apple.com/forums/thread/678318)
57. [238546](https://bugs.webkit.org/show_bug.cgi?id=238546)
58. [Web Audio API 1.1](https://www.w3.org/TR/webaudio-1.1/)
59. [AudioWorkletProcessor: process() method - Web APIs](https://developer.mozilla.org/en-US/docs/Web/API/AudioWorkletProcessor/process)
60. [\- From: Chris Lilley \<chris@w3.org\>](https://lists.w3.org/Archives/Public/public-privacy/2018JanMar/0012.html)
61. [Profiling Web Audio apps in Chrome | Articles | web.dev](https://web.dev/articles/profiling-web-audio-apps-in-chrome)
62. [Cross-Origin-Embedder-Policy (COEP) header - HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cross-Origin-Embedder-Policy)
63. [Cross-Origin-Embedder-Policy: securing embedded resources: Understanding cross-origin security headers - Part 3](https://andrewlock.net/understanding-security-headers-part-3-cross-origin-embedder-policy/)
64. [AudioParam: value property - Web APIs](https://www-igm.univ-mlv.fr/~forax/MDN/developer.mozilla.org/en-US/docs/Web/API/AudioParam/value.html)
65. [\- From: Chris Rogers \<crogers@google.com\>](https://lists.w3.org/Archives/Public/public-audio/2012OctDec/0615.html)
66. [The eSpeak-NG speech synthesis engine on Chrome OS](https://chromium.googlesource.com/chromium/src/+/refs/tags/74.0.3729.5/docs/accessibility/espeak.md)
67. [ESpeak](https://en.wikipedia.org/wiki/ESpeak)
68. [signalsmith-stretch/LICENSE.txt at main · Signalsmith-Audio/signalsmith-stretch · GitHub](https://github.com/Signalsmith-Audio/signalsmith-stretch/blob/main/LICENSE.txt)
69. [Tone.js.LICENSE.txt - jsDelivr](https://cdn.jsdelivr.net/npm/tone@15.0.4/build/Tone.js.LICENSE.txt)
70. [pronouncing CDN by jsDelivr - A CDN for npm and GitHub](https://www.jsdelivr.com/package/npm/pronouncing)
