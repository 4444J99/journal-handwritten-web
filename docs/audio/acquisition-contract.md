# T09 acquisition contract · pilot v0.1

Status: **technical pilot; author recording and listening acceptance pending**. Review date:
2026-11-05 (America/New_York). This contract reconciles issues [#23](https://github.com/4444J99/journal-handwritten-web/issues/23),
[#24](https://github.com/4444J99/journal-handwritten-web/issues/24), and
[#35](https://github.com/4444J99/journal-handwritten-web/issues/35). It does not authorize a bank
release, public audio, a performed supplement, or repository changes outside this draft.

## Evidence and authority

The October 27 exchanges establish the author's own recorded voice, forward and backward
methods, and reuse in other projects. The October 28/29 exchanges establish voice-derived
ambience responsive to text and selection. Those are author decisions. The build specifications,
durations, processing palettes, targets and architecture are engineering proposals, except where
the exchange explicitly attributes a decision to the author. Sources and hashes are in
[source-ledger.json](source-ledger.json); current tool checks are in
[toolchain-audit.md](toolchain-audit.md).

The private shared packet `2026-10-16-v1.1` / projection `2026-10-16-v1.1-r2` in project
`g-p-6a10bcb4ada4819194e881431212101a` was inaccessible. No requirement or approval is inferred
from its unseen contents. Historical artifact identifiers and local archive paths are evidence
locators, not proof of current access or authority. No new `voicebank` or `voice-engine`
repository is created by this pilot; the earlier polyrepo plan remains a proposal.

## Two acquisition tracks, one session

| Track | Acquired material | Alignment and processing | What this pilot can establish |
|---|---|---|---|
| Concatenative speech | Short technical phone sequences, eventually wrapped in the author's chosen carrier | Explicit phone intervals; diphones run from the centre of the first phone to the centre of the second; joins retain their source coordinates | Reproducible cutting, lookup, direction transforms and join audition; intelligibility requires real recordings and listening |
| Phoneme textures | Sustained vowels and consonants, breath and whisper | Label the stable region separately from attacks/releases; render bounded stretch/freeze/octave/reverb comparisons offline | Reproducible parameter comparisons and browser playback; an artistic palette requires the author's listening |

A sustained vowel is not a replacement for a speech transition. A speech unit is not automatically
approved as an ambient stem. Both may cite the same raw take while retaining separate segment
and processing records. No generic TTS, downloaded speaker, cloned voice or other person's
recording substitutes for the author's future recordings. Generated tones/noise are deliberately
non-speech software fixtures and carry `fixture: true` throughout.

## One manageable recording request

**Proposal: 50 prompts total, within one approximately 30-minute session.** This replaces the
earlier two pilot requests; it does not add a one-hour speech session to a half-hour texture session.
The author may stop early and submit the retained takes. Prompt completion is not an acceptance
score, and no full-bank session begins from a fixture pass.

| Block | Prompt count | Suggested time | Purpose |
|---|---:|---:|---|
| Set up the existing recorder | 0 | 2 minutes | Choose one available microphone, fixed distance and gain, disable optional effects if the recorder permits |
| Calibration | 2 | 1 minute | Room-only baseline and a repeatable reference; preserve these alongside the session |
| Concatenative calibration | 24 | 10 minutes | Short technical phone chains covering several classes and opposite transition directions; incomplete English coverage is expected |
| Pause | 0 | 2 minutes | Keep the recorder settings and placement unchanged |
| Texture comparison | 24 | 10 minutes | Two takes for each of IY, AA, UW, ER, AH, M, N, S, SH, F, breath and whisper |
| Check files and retain originals | 0 | 5 minutes | Listen for clipping, missing starts/ends and obvious background interruptions; record retake IDs |
| **Total** | **50** | **30 minutes** | A pilot, not the former 1,000–1,400-prompt speech inventory or 250–350-take texture library |

The generated packet is the exact operational prompt list. Its technical labels are not poem text.
Select reading style, carrier, pronunciation authority and the existing microphone in the decision
sheet before an author session. For whisper, use the packet's technical sound/phone instruction,
or replace it with author-supplied material and record that revision. No author-written captions
or performed poem passages are required for this pilot.

The older specification proposed recording the pilot on both a phone and a USB microphone.
This contract proposes one existing device to keep the request bounded. If two devices are already
available and a comparison is wanted, repeat only the two calibration prompts on the second
device as an explicitly recorded optional supplement. Do not buy equipment to satisfy the pilot.

## Recording and immutable intake

1. Keep each original recording exactly as created by the recorder, with its original filename and
   SHA-256. Make a separate processing copy. Do not trim, normalize, denoise, reverse or overwrite
   an original. Local storage is not itself a backup; retain a separate copy through an existing
   approved storage practice before deleting anything. This task deletes nothing.
2. Preferred acquisition is mono PCM WAV, 48 kHz, 24 bit. Use a consistent device, gain, distance
   and room. The earlier absolute noise-floor and pitch targets are proposed full-bank QC gates,
   not verified characteristics of a phone or of this pilot.
3. A phone's native export may be another format. Keep that original; a canonical processing WAV
   must cite the original hash, recorder/export information, converter version and exact command.
   Converting a lower resolution file to 24 bit does not add fidelity. Lossy sources remain labeled
   lossy, and conversion is not a reason to discard the original.
4. Files, manifests and segment labels belong to one session ID and prompt-list revision. Record
   take number rather than replacing a previous take. A retake changes the selected take and
   output hashes; it does not erase the previous source.
5. Hash the immutable master before and after processing. A mismatch, wrong sample format,
   truncated data, unsupported channel layout, invalid duration, clipping or invalid labels must
   be visible. Do not silently downmix, resample, clamp metadata, guess labels or substitute a voice.
6. Keep raw masters out of the listening server and out of the deployment trees. During this
   task all author audio would remain private. The long-term master policy and permission to
   release a particular rendered file are separate, still-open author decisions.

## Identity and labels

Every usable take is tied to its prompt ID, prompt version, transcript/phone list, speaker or
fixture identity, acquisition settings, source hash and alignment provenance. Every render cites
the exact manifest hash, selected takes, segment frame boundaries, processing parameters and
output hash. Times use half-open frame intervals at the declared sample rate; milliseconds are
only a display conversion. The transform must retain the original frame coordinates even when
the rendered signal is reversed or stretched.

Journal bindings must use existing piece, version and line identifiers, plus the exact transcript
snapshot hash; display coordinates and stack position are not identity. At the reviewed baseline,
IDs such as `p001`, `p001-diary1-0` and `diary1-0-0` already exist. These examples document an
interface and do not select a poem for voicing. Technical fixtures use their own namespace. A
source correction invalidates the old binding for current playback; it does not rewrite historical
renders or silently transfer them to a new version. See [integration-handoff.md](integration-handoff.md).

Alignment evidence must say whether it is generated fixture ground truth, manually inspected,
or proposed by a named forced aligner/model/dictionary. An imported TextGrid is not proof that
MFA ran, and a plausible interval is not proof that a phone was spoken. Manual review must check
the actual sound and boundaries before an author take becomes a listening candidate. MFA,
pitch marks, PSOLA and a complete pronunciation inventory remain staged work unless a receipt
explicitly reports a completed run.

For diphones, store `start`, the phone boundary `mid`, and `end` in original frames. Steady-state
phone midpoints are a provisional cutter rule. Stops may need manually selected closure centres;
do not call arithmetic midpoints phonetic verification. Texture segments should cite their
independent stable-region selection. Corrections produce new labels/revisions and new hashes.

## Direction transforms and processing comparisons

- Forward: assemble the selected forward transitions in requested phone order.
- Mirror: for requested X–Y, reverse the available forward Y–X segment; reflect its local boundary.
- Software Red Room: assemble the reversed phone sequence, then reverse the assembled buffer.
  This is a software comparison, not a performed backward reading. The full phonetic reversal
  rules and author idiolect require later review.
- Performed Red Room: a future author recording, aligned in its actually performed phone order
  before audio and labels are flipped together. No fixture is labeled as this performance.
- Texture comparisons: retain a dry control and explicit parameterized transforms. The older
  10×/50×/200× stretch ratios are comparison values, not selected sound directions. A short
  preview must report the full implied duration and its preview cap; it cannot claim to contain
  the whole stretched take. Octave resampling changes duration as well as pitch unless a later
  method explicitly compensates. Any convolution kernel must itself derive from the supplied
  voice for author recordings; no foreign room impulse response is introduced silently.

At neutral timing and symmetric joins, mirror and reverse-then-reverse assembly can coincide.
Their definitions and provenance remain separate. Artificial variation is not added merely to
make a comparison sound different. A fixture proves numeric operations, not intelligibility,
performance authenticity, phonetic adequacy, absence of audible clicks or artistic quality.

## Gates and staged work

| Gate | Required evidence | Current disposition |
|---|---|---|
| Technical preparation | Reproducible fixture run, visible failures, provenance, usable prompt packet and private harness | See the verification receipt |
| Author pilot | Actual recordings, native originals, acquisition choices, reviewed labels | Open; no supplied voice recordings located |
| Listening decision | Named session/render hashes, devices used, selected/rejected comparisons and author's own notes | Open; fixture feedback cannot satisfy this gate |
| Larger acquisition | Listening decision plus revised coverage/recording list and confirmed master policy | Deferred |
| Reader/studio integration | T02 source contract, T04 lifecycle behavior, studio integrator handoff and accepted sound direction | Prepared interface only |
| Release | Exact rendered audio and transcript cleared through T03, independent master/reuse permissions, physical-device checks | Open; no release operation in this pilot |

Full-bank acceptance remains broader: verified corpus pronunciations, diphone coverage,
intelligibility, join listening, F0/loudness QC, performed supplements if chosen, timing/prosody,
codec offsets, size/performance, interop and real iPhone behavior. None follows automatically from
this pilot's tests.
