# T09 private recording packet

**Preparation is complete; the audio milestone remains open.** No author recordings or listening approval were available for this pilot. The reproducible demonstration contains generated tones/noise, not the author's voice. Neither its phone labels nor its output establishes intelligibility, pronunciation, alignment accuracy, an accepted sound direction, or a finished voice bank.

The checked-in [packet](packet/recording-script.md) is one **proposed** request: 50 prompts total, up to 30 minutes, replacing the earlier 50-prompt and roughly 30-minute alternatives. It contains two room/reference prompts, 24 short transition chains, and 24 texture prompts (12 categories, two takes each). Prompt time is 21 minutes; setup, breaks and logging have nine minutes. Stop at the timebox and log omitted takes. The timebox excludes subsequent engineering alignment/review. Full-bank acquisition and performed supplements follow the author's listening decision.

## 1. Reproduce the fixture before asking for a recording

Run from the repository root with Python 3.12 and the verified NumPy 2.3.5 environment. `audio_build/requirements.txt` records the single dependency; no model, voice, dictionary or sample download is needed. Choose new output locations. These commands never replace existing output directories.

```bash
T09_WORK=$(mktemp -d /tmp/t09-audio.XXXXXX)
python3 audio_build/render.py fixture --out "$T09_WORK/fixture-session"
python3 audio_build/render.py validate --manifest "$T09_WORK/fixture-session/session.json" --report "$T09_WORK/fixture-validation.json"
python3 audio_build/render.py run --manifest "$T09_WORK/fixture-session/session.json" --out "$T09_WORK/fixture-listening"
python3 audio_build/render.py packet --out "$T09_WORK/packet"
python3 audio_pilot/serve.py --renders "$T09_WORK/fixture-listening" --packet "$T09_WORK/packet" --port 8765
```

Open the server's loopback URL. It serves only the private harness, the selected packet, receipt and rendered samples. Inspect full timing maps in the listening output directory; the receipt retains their hashes and source intervals. It does not serve raw banks. Sound begins off and requires an explicit start. Keep volume comfortable. Browser preparation does not settle the pending physical iPhone silent-switch test or authorize public reader/studio integration.

The fixture has 17 deterministic takes and 13 comparisons: forward, true mirror, literal software Red Room, a dry texture reference, 10×/50×/200× spectral textures at both 0.25-second and 1-second windows, freeze, octave down and source-only multitap reverb. Every preview lasts at most six seconds. A second `run` into another new directory produces the same hashes in the tested environment. `SHA256SUMS` covers the receipt, WAV files and timing JSON; the receipt hashes the source manifest and each output. Raw hashes are checked before and after processing.

## 2. Record the finite author choices without inventing answers

Use [the decision sheet](../docs/audio/author-decisions.md) and [its template](../docs/audio/author-decisions.template.json). D01 reading style, D02 carrier phrase, D03 pronunciation authority and D10 microphone require an explicit nonblank `choice`, `author` and `source` before acquisition. An explicit choice of no carrier is valid; a missing answer is not. The other choices remain pending until their stated gates; D04 vowel split is required before the full bank. No creative reading, carrier, palette, captions, fallback voice or release choice has been selected by this tooling.

Keep the original blank packet. Copy the finite sheet into your private work area and record the author's answers there. Then use this projection helper to create a **new** packet with the same decision records in the prompter and intake configuration and the correct packet hash. It expects the finite sheet's `decisions` list; it does not inherit top-level authorship or fill answers.

```bash
cp docs/audio/author-decisions.template.json "$T09_WORK/author-decisions.json"
# After the author records the required choices in that private copy:
python3 - "$T09_WORK/packet" "$T09_WORK/author-decisions.json" "$T09_WORK/decisioned-packet" <<'PY'
import hashlib, json, pathlib, shutil, sys
original, sheet_path, target = map(pathlib.Path, sys.argv[1:])
sheet = json.loads(sheet_path.read_text())
decisions = sheet["decisions"]
by_id = {record["id"]: record for record in decisions}
for key in ("D01", "D02", "D03", "D10"):
    for field in ("choice", "author", "source"):
        value = by_id[key].get(field)
        if not isinstance(value, str) or not value.strip():
            raise SystemExit(f"Author answer missing: {key}.{field}")
prompts = json.loads((original / "prompts.json").read_text())
config = json.loads((original / "session-request.template.json").read_text())
prompts["author_decisions"] = decisions
config["author_decisions"] = decisions
config["packet_path"] = "prompts.json"
target.mkdir(parents=True, exist_ok=False)
def write(name, value):
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()
    with (target / name).open("xb") as stream:
        stream.write(data)
write("prompts.json", prompts)
digest = hashlib.sha256((target / "prompts.json").read_bytes()).hexdigest()
for reference in config["source_refs"]:
    if "packet_sha256" in reference:
        reference["packet_sha256"] = digest
write("session-request.json", config)
shutil.copy2(original / "recording-script.md", target / "recording-script.md")
(target / "README.txt").write_text(
    "Decisioned private pilot packet. Keep the original blank packet.\n"
    "Use prompts.json with the prompter and session-request.json for init-session.\n"
    "See the repository recording/README.md for capture, labels and processing.\n"
)
print(target / "session-request.json")
PY
```

Point the prompter's `--packet` at this new `decisioned-packet` directory. Its decision gate and the intake then read the same records. If any answer or prompt later changes, prepare another packet/version before recording; keep the packet used for each take. Do not reuse a stale prompter progress log across different packet hashes. The intake captures the actual packet, its SHA-256, its decisions, and each selected prompt's complete snapshot in the session.

## 3. Capture and preserve the originals

The script provides plain-language pronunciation guides alongside phone chains and precise `C01.wav`–`C50.wav` filenames. Respellings are aids to be checked against D03, not an imposed pronunciation authority. Texture categories such as breath and whisper remain separate from transition-chain recording. No poetry or performed journal text is requested.

Use the selected available microphone and record a dry signal without music. Keep microphone position, gain and room consistent; log changes, discomfort, slips, omitted prompts and retakes. Choose a comfortable pitch rather than a prescribed note. Preserve every original capture and store retakes separately; never overwrite a first take to make the names fit. Select one explicit version for processing and retain the mapping to its original filename.

The processing contract is **48,000 Hz, mono, uncompressed PCM24 WAV**. Only explicitly marked synthetic fixtures may use PCM16. The technical validator rejects peaks at or above −1 dBFS and non-room RMS below −100 dBFS. These are bounded pilot checks, not a measurement of perceptual quality or a certified recording noise floor. The room reference is intentionally exempt from the silence rejection and cannot become a voice source.

If an existing phone/app produces another format, retain that original and create a separate processing master. For example, after inspecting the actual input's channels and sample rate:

```bash
ffmpeg -version
ffprobe -v error -show_streams -show_format /absolute/private/original.m4a
ffmpeg -n -i /absolute/private/original.m4a -ar 48000 -ac 1 -c:a pcm_s24le /absolute/private/processing/C27.wav
```

`-n` prevents overwrite. Converting a compressed or lower-bit-depth original does not add fidelity. Record the exact command, FFmpeg version/build, original SHA-256 and processing-master SHA-256 in the take's `conversion` field when using explicit `takes` records. Never imply that a converted master was captured as native PCM24. No conversion is performed implicitly by this pilot.

## 4. Review boundaries, then import

The pilot uses explicit reviewed frame intervals. It does not claim to run a forced aligner. At 48 kHz, frame number is time in seconds multiplied by 48,000, rounded to an integer. Listen and inspect the actual waveform; do not divide human speech into equal durations. Boundaries must touch, and intentional pauses must be labelled `pau`. Leading/trailing frames outside the selected labelled region are recorded as exclusions.

For the first sustained ee take, C27, generate an unreviewed template:

```bash
python3 audio_build/render.py labels-template --wav /absolute/private/processing/C27.wav --phones 'pau IY pau' --take-id C27 --out /absolute/private/reviewed-labels/C27.json
```

Replace each `null` start/end with the reviewed frame boundaries, set `reviewed` to `true`, and name the actual reviewer. `p00` is the leading pause, `p01` the sustained vowel, and `p02` the trailing pause in this example. Keep the generated WAV hash, frame count and sample rate unchanged. If the capture differs from the proposed labels, revise the label sequence to match the actual sound. The supplied example is an annotation workflow, not an assertion that C27 exists.

For a transition take, include the actual phones and carrier selected by the author. For example, the C03 transition region contains `AA M AA`; annotate any actual carrier as well or explicitly select the transition-only region. A diphone cut starts at the integer midpoint of the first phone and ends at the midpoint of the second; the phone boundary is separately retained. No pitch marks, TD-PSOLA or professional alignment accuracy is claimed.

Alternatively, manually review a Praat **long-text** TextGrid with one `IntervalTier` named `phones`. Use explicit supported unstressed ARPAbet labels, `pau`, or `dx`; review blank intervals rather than importing them as silence automatically. Importing with `--reviewer` is an explicit assertion that every boundary was reviewed:

```bash
python3 audio_build/render.py import-textgrid --textgrid /absolute/private/C27.TextGrid --wav /absolute/private/processing/C27.wav --take-id C27 --reviewer 'ACTUAL REVIEWER' --out /absolute/private/reviewed-labels/C27.json
```

The importer retains the TextGrid hash, original seconds, rounding errors and WAV identity. Breath and whisper remain texture categories in the prompt/take metadata; use explicitly reviewed supported phone labels for their intervals rather than silently extending the phone inventory.

## 5. Turn the actual recordings into a private session

Edit the newly generated `decisioned-packet/session-request.json`. Set `recordings_directory` and `labels_directory` to absolute private paths and `take_ids` to the actual selected recordings. A first dry-reference run can select just `["C27"]`; its default request uses `p01` from the template above. Do not list absent takes. Match request label IDs to the actual reviewed labels. A partial recording session is acceptable and must remain identified as partial.

```bash
python3 audio_build/render.py init-session --config "$T09_WORK/decisioned-packet/session-request.json" --out "$T09_WORK/author-session"
python3 audio_build/render.py validate --manifest "$T09_WORK/author-session/session.json" --report "$T09_WORK/author-validation.json"
python3 audio_build/render.py run --manifest "$T09_WORK/author-session/session.json" --out "$T09_WORK/author-listening"
python3 audio_pilot/serve.py --renders "$T09_WORK/author-listening" --packet "$T09_WORK/decisioned-packet" --port 8765
```

`init-session` validates the originals, copies them into a new private session and checks original/copy hashes. It retains selected prompt snapshots, packet bytes, recording metadata, reviewed alignment, decisions and repository source references. The manifest paths are contained within the session. `run` uses a manifest snapshot, rechecks the manifest and sources, and emits a visible `diagnostic.json` on pilot validation/processing failures. Missing words and diphones stop synthesis; no generic TTS or substitute unit is used. Unsupported Unicode/digit/illegible tokens are visible errors; basic punctuation around supported words is stripped explicitly. No empty-text success is emitted.

`validate` checks structure, source hashes, audio format/quality, reviewed labels, text identity and required units. The DSP parameter whitelist and numeric bounds are checked by `run` before successful samples are written; a structural validation receipt alone does not claim DSP preflight or author listening acceptance.

To compare textures on a supplied reviewed segment, copy its dry request into additional entries with unique IDs and `mode`/`parameters` matching the fixture's requests. For concatenation, explicitly supply the actual text, its source ID/version, exact UTF-8 `text_sha256`, and a reviewed lexicon. The packet's `calibration` lexicon entry is a technical chain lookup example, not a pronunciation claim for the English word. Do not reuse it for journal text. Missing coverage is a useful result of this bounded pilot.

## Processing limits and interpretation

| Comparison | Tested implementation | Practical limit |
| --- | --- | --- |
| Forward | First explicit midpoint-diphone candidate; equal-power joins | No prosody model or TD-PSOLA |
| True mirror | Reverse the waveform for the opposite forward transition | Distinct source-selection semantics from ordinary reversed audio |
| Software Red Room | Reverse the literal phone sequence, concatenate, reverse the whole buffer | No performed reverse speech or expansion/prosody rules; may equal mirror under neutral timing and symmetric joins |
| Stretch / freeze | Seeded magnitude-spectrum overlap/add retaining frequency-bin positions | Local texture experiment, not the external Paulstretch application or proven perceptual equivalent; actual window frames and full implied duration reported |
| Octave | Linear interpolation at half/double rate | Changes duration; no antialias filter, so audition only |
| Reverb | Twelve seeded delayed taps of the selected source | Source-only multitap effect, no convolver or external impulse response |

Each preview is capped at six seconds; total output is capped at 90 seconds. Takes are capped at 60 seconds/10 MiB, a session at 100 takes/ten minutes of decoded audio, and a request at 256 phones/30 seconds of pre-trim concatenation. Processing uses bounded seeds/parameters, a symmetric edge fade and a peak ceiling that never boosts quiet sources. No cross-platform bit identity has been established; replay is tested in the recorded Python/NumPy environment.

All 14 author decisions remain separate from these engineering limits. Private raw masters, private pilot listening and future rendered release are different states. The acquisition tool only accepts private masters, local listening and undecided rendered release. It rejects outputs in the repository's deployment/export trees. Reader/studio publication requires the author listening decision and the T02/T03/T04/studio handoff described in [the integration plan](../docs/audio/integration-handoff.md).

## Regression receipt

```bash
python3 -m unittest discover -s tests -p test_audio_pilot.py -v
```

The tests cover deterministic fixture replay and raw preservation, exact recording/text/packet identity, manifest/raw/alignment mutation, missing pronunciations/units and unsupported tokens, privacy/path restrictions, bounded finite DSP, direction semantics, frame boundaries, the TextGrid import, finite prompt counts and the supplied-recording intake shape. The latter uses a synthetic sine for plumbing tests; it does not constitute an author recording or listening approval.
