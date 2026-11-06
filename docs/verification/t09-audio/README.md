# T09 verification receipt

Review baseline: **2026-11-05, America/New_York**. Execution receipts are dated 2026-11-06 UTC.
**PASS for the bounded fixture pilot. Author recordings, listening acceptance and the audio milestone remain open.**

## Results

| Check | Observed result | Evidence |
|---|---|---|
| Engine regression suite | 17 passed | [Python log](python-tests.log), [test receipt](tests.json) |
| Private server suite | 7 passed | Same Python log; allowlist, raw/traversal/encoding/host/write/symlink/hash/identity cases |
| Playback-controller suite | 13 passed | [Node log](playback-tests.log) |
| Real Chromium desktop | 18 checks passed, no console/network exceptions | [Browser receipt](browser.json), 1280 × 900 |
| Real Chromium touch viewport | 18 checks passed, no console/network exceptions | Same receipt, 390 × 844 touch emulation |
| Fixture source generation | 17 takes, 18 seconds of generated tone/noise | [Generation log](fixture-generation.log) |
| Fixture validation | Valid input identity, labels and unit coverage | [Validation log](fixture-validation.log) |
| Listening outputs | 13 mono PCM24 WAVs at 48 kHz; 56.340770833 seconds combined | [Reproducibility record](reproducibility.json) |
| Second manifest-driven render | All 28 output files byte-identical: 13 WAVs, 13 timing maps, receipt and SHA256SUMS | Same record contains both complete hash maps |
| Source preservation | All 17 raw hashes unchanged before/after each render | Render receipts; regression mutation tests |
| Actual CLI failure | Exit 2, `missing_pronunciation`, token and source retained, no substitute audio | [Diagnostic](missing-pronunciation.json), [CLI log](missing-pronunciation.log) |
| Repository integrity | 509 references checked, zero missing; 511 checksums; OK | [Integrity log](repository-integrity.log) |
| Protected baseline files | Reader, studio, source data, release policy, CLAUDE.md and MANIFEST.sha256 unchanged | `protected_files` in [tests.json](tests.json) |

The fixture's **mirror and literal software Red Room WAV hashes match**, while their timing-map
hashes differ. This is expected under neutral timing and symmetric joins; their transform
definitions and source-selection provenance remain separate. No artificial variation was added.

Manifest SHA-256:
`975b2cb31092c9470b311aeb4e4d8a71f7b2b1adbf88a932c4b1872101964bd4`

Listening receipt SHA-256:
`b25ba26b582e55f6d68f3a9ba8e0eb600ab34024fef92680c2cd896378b5a2f9`

The downloadable fixture output bundle supplied with the handoff contains that exact session
manifest, generated source WAVs, reviewed synthetic labels, all rendered comparisons and their
timing/processing receipts. These generated audio bytes are not added to the Git repository.
The code and checked-in recording packet reproduce them. No author voice appears in the bundle.

## Reproduce

Python 3.12.14, NumPy 2.3.5 and Node 24.22.1 were used. No packages, models, dictionaries or
voices were downloaded or upgraded. The fixture requires only the Python standard library and
the pinned NumPy dependency. FFmpeg was inspected but is not used by this run. Full runtime
and protected-input identities are in [environment.json](environment.json).

From the repository root, with a fresh working directory:

```sh
T09_WORK=$(mktemp -d /tmp/t09-verify.XXXXXX)
python3 -m unittest discover -s tests -p 'test_audio*.py' -v
node --test tests/test_audio_playback.mjs
python3 audio_build/render.py packet --out "$T09_WORK/packet"
python3 audio_build/render.py fixture --out "$T09_WORK/fixture-session"
python3 audio_build/render.py validate --manifest "$T09_WORK/fixture-session/session.json" --report "$T09_WORK/validation.json"
python3 audio_build/render.py run --manifest "$T09_WORK/fixture-session/session.json" --out "$T09_WORK/listening"
python3 audio_build/render.py run --manifest "$T09_WORK/fixture-session/session.json" --out "$T09_WORK/repeat"
diff -r "$T09_WORK/listening" "$T09_WORK/repeat"
python3 tools/check.py
```

For a manual private audition, run:

```sh
python3 audio_pilot/serve.py --renders "$T09_WORK/listening" --packet "$T09_WORK/packet" --port 8765
```

Open `http://127.0.0.1:8765/`, load the receipt and packet, choose a sample, load it and press
Start. Stop is explicit. The full prompter/intake workflow is in [recording/README.md](../../../recording/README.md).

For real-browser automation, provide an existing Chromium executable:

```sh
node tools/verify_audio_pilot.mjs --url http://127.0.0.1:8769/ \
  --renders "$T09_WORK/listening" --packet "$T09_WORK/packet" \
  --chrome /absolute/path/to/chromium \
  --out "$T09_WORK/browser.json" --shots "$T09_WORK/screenshots"
```

The verifier launches and stops its own loopback server and Chromium process. It reuses the
repository's existing CDP lifecycle utility and installs no browser or npm package. This run used
Chromium 153.0.8010.0 already available in the workspace. It records code hashes and each check.
Screenshots were inspected locally at desktop and touch sizes; their hashes remain in the receipt.
Screenshots are not included in the downloadable audio bundle.

## What the checks establish

The engine tests enforce exact recording/label/text/packet identities, reviewed frame boundaries,
midpoint cuts, direction math, deterministic seeds, private output paths, no overwrite, bounded
finite processing, explicit missing words/units and nonfinite JSON rejection. Mutation tests
change the manifest, raw audio and labels during processing and require failure. The supplied-
recording intake test uses a synthetic sine in the human-input shape; it is plumbing evidence,
not an author recording or identity verification.

The browser checks use real mouse/touch events and instrument the actual AudioBufferSourceNode
start/stop calls. They verify initial silence, no sample fetch before action, no autoplay on load,
explicit Start/Stop, stopping on sample-context change, visible fixture/provenance information,
prompter navigation, unanswered-decision gates, feedback without approval claims, and original
packet hashes retained across packet replacement. Export JSON is intercepted at the browser
Blob/download boundary for inspection; the test does not claim a physical download dialog result.
Only loopback application requests were observed, and no horizontal document overflow occurred.

The controller unit tests separately exercise pending fetch/decode/resume races, one-source
behavior, hidden pages, page exit, context interruptions, invalidation, memory bounds and disposal.
Server tests verify byte hashes and exact routes. The server preserves producer receipt metadata;
it does not redact arbitrary operator-supplied metadata or establish authorship.

## Limits and resolved findings

The first browser attempt could not reach a server launched in a separate execution session and
failed with connection refused. The verifier now starts the server in its own process context;
the final receipt above is the successful rerun. No failed attempt is counted as a pass.

Read-only review identified and the final code fixed: unchecked WAV identity in labels, unchecked
text snapshot hashes, manifest/source mutation during rendering, reversed overlap metadata,
incompatible decision-record shapes, missing receipt identity, and progress relabeling after
packet replacement. The final regressions cover these boundaries.

These results do **not** establish human phonetic alignment, intelligibility, acceptable joins,
voice quality, a selected sound palette, full diphone coverage, MFA compatibility, pitch marks,
TD-PSOLA, performed reverse speech, cross-platform bit identity or release eligibility. The
small spectral implementation is not Paulstretch; the source-only reverb is multitap, not
convolution; octave resampling changes duration and has no antialias filter.

Headless Chromium was muted. No perceptual audition, physical iPhone/Safari test, silent-switch
test, screen lock, call interruption, speaker/earbud routing or production reader/studio
integration is claimed. Those gates require real recordings, author listening and the owner
handoffs in [docs/audio/integration-handoff.md](../../audio/integration-handoff.md).

All primary issues remain open. The [baseline](baseline.json) records accessible evidence and
the inaccessible shared-context packet; historical approvals were not used as new authority.
