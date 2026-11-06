# T09 · reproducible private audio pilot

**Preparation and fixture pilot; author voice/audio milestone remains open.**

This packet implements the bounded preparation for issues
[#23](https://github.com/4444J99/journal-handwritten-web/issues/23),
[#24](https://github.com/4444J99/journal-handwritten-web/issues/24), and
[#35](https://github.com/4444J99/journal-handwritten-web/issues/35). The supplied research and
build specifications are read together; [the source ledger](source-ledger.json) identifies their
versions and provenance. No author recording was found in the inspected material. Generated
tones/noise are explicitly labeled **fixtures**, with no claim of author performance, intelligibility
or artistic acceptance.

## Start here

| Need | Artifact |
|---|---|
| Run or inspect the technical pilot | [CLI/manifest interface](../../audio_build/INTERFACE.md) and [verification receipt](../verification/t09-audio/README.md) |
| Make the recording | [Acquisition contract](acquisition-contract.md), generated [prompt list](../../recording/packet/prompts.json) and [recording instructions](../../recording/README.md) |
| Make the reserved choices | [14-choice author sheet](author-decisions.md) and [blank machine-readable record](author-decisions.template.json) |
| Check dependencies and licenses | [Toolchain audit](toolchain-audit.md) |
| Coordinate reader/studio/release work | [Integration handoff](integration-handoff.md) |
| Review remaining issue work | [Issue dispositions](issue-disposition.md) |
| Review preservation, scope and branch state | [Closeout record](closeout.md) |

## Reproduce the fixture

From the repository root, using Python and the NumPy version named in the toolchain/verification
receipt, choose a fresh scratch directory. Existing outputs are refused to protect recordings and
make each run inspectable:

```sh
python3 audio_build/render.py packet --out /tmp/t09-packet
python3 audio_build/render.py fixture --out /tmp/t09-fixture
python3 audio_build/render.py validate --manifest /tmp/t09-fixture/session.json --report /tmp/t09-validation.json
python3 audio_build/render.py run --manifest /tmp/t09-fixture/session.json --out /tmp/t09-listening
python3 audio_build/render.py run --manifest /tmp/t09-fixture/session.json --out /tmp/t09-listening-repeat
```

Use different new paths if any example path already exists. The fixture session contains generated
calibration masters and their explicit labels. The listening output contains rendered samples and
receipts, without raw originals. Compare its sample hashes to the repeat run. Determinism is
verified for the recorded runtime; different NumPy/FFT/platform implementations require a new
receipt rather than an assumed byte match.

The local workbench under `audio_pilot/` serves a selected listening output and the prompt packet
on loopback:

```sh
python3 audio_pilot/serve.py --renders /tmp/t09-listening --packet /tmp/t09-packet --port 8765
```

Open `http://127.0.0.1:8765/`. It serves only explicit workbench/data
routes and listed rendered WAVs; it is not a general file server. Start and Stop are explicit. The
receipt exposes fixture status, inputs, processing parameters and hashes. Exported feedback is
private review material, not a signature, a public clearance or an instruction to acquire a full bank.

For actual recordings, generate the packet first, complete the small set of acquisition choices,
and follow `recording/README.md` and `audio_build/INTERFACE.md` to initialize a session from
immutable originals. Keep the raw/native files, canonical WAV derivatives, conversion evidence
and label revisions. Unknown words and missing units are visible failures; the engine does not
substitute a generic voice. Every real take and render must retain `fixture: false` honestly.

## What is and is not established

The implementation addresses reproducible input handling, explicit labels and cutting, minimal
concatenation/direction transforms, bounded texture comparisons, local playback controls and
failure reporting. The exact tested behavior is in the receipt; source and parameter hashes are
the evidence, not an old planning checkbox.

The author pilot, perceptual listening, chosen sound palette, pronunciation authority, performed
supplement, full-bank coverage/prosody, real-phone behavior and release remain open. Nothing
under `site/` or the shared studio is activated by this draft. The next request is one proposed
50-prompt/~30-minute author session after reviewing the recording choices. A real listening
decision precedes larger acquisition and the next browser integration.

The journal remains a distinct body of work in the wider `versforms` project; ETCETER4 remains the separate music project. The inaccessible
shared-context packet `2026-10-16-v1.1` / projection `2026-10-16-v1.1-r2` is recorded as an access
limit and supplies no unseen requirement or approval.
