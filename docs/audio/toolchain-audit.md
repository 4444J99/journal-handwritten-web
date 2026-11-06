# T09 source and toolchain audit

Audit date: **2026-11-05 America/New_York**; tool receipt date: **2026-11-06 UTC**.
Scope: the **2026-11-05 review baseline**, refreshed repository head
`038d01fb1862f2e569d231b5b3c4c3a4eb1aecda`, and the bounded private pilot. The machine-readable
[source ledger](source-ledger.json) contains source IDs, hashes, attachment IDs and access limits.
An upstream version check is not an installation or a successful DSP run.

## Authority and acquisition reconciliation

The archived October 27 exchange establishes the author's own recorded voice, forward/backward
methods and reuse. The October 29 exchange establishes ambience derived from the author's voice.
The research reports and build specifications are engineering proposals. They do not by themselves
approve a carrier, pronunciation authority, performance, sound palette, microphone purchase,
voice license, raw-bank publication or iPhone silent-switch policy. The author-decision sheet keeps
those choices open. [T09-S01–S06]

The earlier speech specification proposes a 50-prompt probe, approximately one hour including
comparison of recording devices, before much larger acquisition. The ambience plan proposes
roughly 30 minutes of five vowels, five consonants, breath and whisper before selecting textures
by listening. These requests describe different evidence, not two mandatory sessions. The
[acquisition contract](acquisition-contract.md) now proposes **one 50-prompt, approximately
30-minute session using one existing device**: 2 calibration, 24 speech-transition calibration and
24 texture prompts. That division is a derived engineering proposal; the duration is a budget,
not a measured author recording time. Completion does not establish English diphone coverage.
Tooling and fixture verification precede requesting that session. [T09-S01–S04]

| Requirement | Concatenative speech | Voice-derived textures |
|---|---|---|
| Material | Short transitions and later author-approved carrier phrases | Stable vowels/consonants, breath and whisper |
| Labels | Spoken phone sequence, phone boundaries, original-frame diphone start/mid/end | Independent stable-region and attack/release boundaries |
| Direction | Forward, reversed opposite transition, and reverse-sequence/whole-buffer reversal remain separately named | Stretch/freeze/octave/convolution comparisons remain parameterized texture operations |
| Performed material | Author performance is a separate later acquisition; align the actually performed sequence before flipping audio and labels | A texture fixture is never attributed as an author performance |
| Evidence | Original hash, take/prompt identity, alignment method, segment frames and join parameters | The same source identity plus transform parameters, seed, preview/full duration and output hash |

Both tracks preserve untouched originals. Generated tone/noise fixtures are technical calibration
material, not an author's voice or perceptual validation. Forced alignment, pitch marks, TD-PSOLA,
full reversal heuristics and complete pronunciation coverage are not established merely because
the research proposes them. Imported labels must name their real origin. [T09-S01–S04]

## Runtime used by the bounded pilot

The execution environment was inspected by the T09 root task. Its receipts, rather than this
source audit, establish what code passed. The minimal implementation uses Python's standard
library and NumPy; there is no requirement to install the optional research stack to reproduce
the fixture. No dependency is upgraded by this audit.

| Component | Observed runtime | Role and license evidence | Qualification |
|---|---|---|---|
| Python | 3.12.14 | CLI, private loopback HTTP server, PCM WAV I/O, JSON and hashes through the standard library; upstream [license text](https://docs.python.org/3/license.html) is the redistribution reference | Runtime version is an environment observation; exact redistribution bundle was not audited |
| NumPy | 2.3.5 | Numeric/FFT processing; [NumPy 2.3 license](https://numpy.org/doc/2.3/license.html), BSD 3-Clause, independently checked by the root task | Pin the runtime; FFT/platform changes need a new reproducibility receipt |
| Node.js | 24.22.1 | Controller and browser test tooling; the listening server uses Python | No claim that this is the latest release; no Node binary redistributed |
| FFmpeg | 6.1.1-3ubuntu5, built with `--enable-gpl` | Optional explicit intake conversion only; [upstream licensing](https://ffmpeg.org/legal.html) distinguishes default LGPL 2.1-or-later from GPL-enabled builds | Not required for the PCM fixture; record actual build configuration and exact conversion command if used |

FFmpeg's code/build license is separate from the rights in input recordings and rendered output.
The same separation applies to wrappers, libraries, alignment models, dictionaries, voices and
author recordings. A permissive tool license cannot authorize release of the author's masters.
[T09-S20, S26]

## Proposed toolchain: current primary-source checks

These are **optional, untested integration candidates**, not dependencies exercised by the
current fixture. “Observed” means a version was visible in the linked upstream release/project
record during this audit; it is not an assurance about a subsequently changing latest release.

| Component | Observed version / license evidence | Consequence for this project |
|---|---|---|
| Montreal Forced Aligner | [3.4.3](https://pypi.org/project/Montreal-Forced-Aligner/), release record dated 2026-10-08; project metadata declares MIT. [MFA documentation](https://montreal-forced-aligner.readthedocs.io/en/latest/) says model formats changed starting with 3.4. | The older “MFA 3.x” proposal is insufficient to reproduce alignment. Pin tool, model archive, dictionary and hashes together and verify compatibility before a real run. [T09-S21] |
| English (US) ARPA acoustic model | [Model 3.0.0](https://mfa-models.readthedocs.io/en/latest/acoustic/English/English%20%28US%29%20ARPA%20acoustic%20model%20v3_0_0.html), trained 2024-02-10; page lists compatibility with MFA 3.0.0 and CC BY 4.0. | Do not infer compatibility with MFA 3.4.3. Model attribution and model rights are independent of MFA's MIT license. Actual download/archive hash is not acquired by this pilot. [T09-S22] |
| CMUdict | [Upstream license](https://github.com/cmusphinx/cmudict/blob/master/LICENSE) permits source/binary redistribution with notice/conditions/disclaimer retention; two-condition BSD-style text. | No dictionary snapshot is vendored by this pilot. A chosen snapshot requires a commit/hash and retained notice. Author pronunciation authority and corpus-specific unknown words remain open; no silent guessing. [T09-S23] |
| Praat | [Upstream releases](https://github.com/praat/praat.github.io/releases) showed 7.0.02, dated 2026-08-27. The [official license page](https://praat.org/manual/License.html) and [source page](https://praat.org/download_sources.html) specify GPL version 3 or later. | Not installed/tested here. No binary or exact build is selected; bundled libraries and distribution notices must be recorded if adopted. [T09-S24] |
| praat-parselmouth | [Project record](https://pypi.org/project/praat-parselmouth/) showed 0.4.7, dated 2025-11-27, with GPLv3-or-later metadata. | Not installed here. Record both wrapper version and its embedded `PRAAT_VERSION` / `PRAAT_VERSION_DATE`; current standalone Praat does not identify the bundled Praat. Redistribution needs the chosen package's license review. [T09-S25] |
| SoundFile / libsndfile | [SoundFile project](https://pypi.org/project/soundfile/) showed 0.14.0, dated 2026-06-06, BSD 3-Clause; its documentation identifies libsndfile as LGPL. [libsndfile releases](https://github.com/libsndfile/libsndfile/releases) showed 1.2.2. | Neither is used by the minimal PCM pilot. Wrapper version/license and bundled native-library version/license must be recorded separately; exact libsndfile license version/build remains to be pinned if adopted. [T09-S27] |
| eSpeak NG | [Upstream release page](https://github.com/espeak-ng/espeak-ng/releases) showed 1.52.0. The [official README](https://github.com/espeak-ng/espeak-ng#license-information) specifies GPL version 3 or later and separately identifies BSD-licensed compatibility code. | Fallback is an unresolved author choice and is disabled. No exact package, voice/data set or browser wrapper is selected or bundled; their component notices still need to be recorded if adopted. An eSpeak voice is not the author's recorded voice. [T09-S28] |
| Signalsmith Stretch | The [official README](https://github.com/Signalsmith-Audio/signalsmith-stretch) and [LICENSE.txt](https://github.com/Signalsmith-Audio/signalsmith-stretch/blob/main/LICENSE.txt) specify MIT, including notice retention. | Optional proposal only; no version/build pinned, installed, bundled or executed. The pilot does not implement or validate this engine. [T09-S30] |
| SoundTouch, Paulstretch/Csound and other optional DSP | Mentioned in research; no version pinned, installed or executed here. | Do not present the fixture's bounded FFT/resampling operations as implementations or quality validation of these engines. Verify the exact chosen implementation, license and parameters before adoption. [T09-S03, S04] |

Unknowns above are deliberate limits, not implied approvals. Before introducing an optional
dependency, record its immutable version or commit, source URL, checksum, license file, build
options, model/data dependencies and a successful bounded receipt. No generic claim that
“the audio stack is open source” substitutes for that record.

## Browser and release boundary

The root task independently checked the [Web Audio Working Draft](https://www.w3.org/TR/webaudio/)
(2026-09-22), [Audio Session Working Draft](https://www.w3.org/TR/audio-session/) (2024-11-13),
and [WebKit issue 237322](https://bugs.webkit.org/show_bug.cgi?id=237322), including the
2024-09-25 comment describing `playback` versus `ambient` behavior with iOS 17. These do not
establish behavior on the author's current iPhone. The pilot sets no artistic silent-switch policy;
device/OS tests and the author's choice remain gates. [T09-S29]

T02 owns stable source/version identity, T03 publication eligibility, T04 reader lifecycle and the
studio integrator the studio UI. A private master policy and permission to release exact rendered
audio are separate decisions. Browser defaults, interruption behavior and provenance can be
prepared privately before listening acceptance; enabling the journal integration follows that
acceptance. The journal identity remains separate from ETCETER4.

The private context packet `2026-10-16-v1.1` / projection `2026-10-16-v1.1-r2` in
`g-p-6a10bcb4ada4819194e881431212101a` was inaccessible. No claim in this audit is attributed to
its unseen contents. [T09-S00]
