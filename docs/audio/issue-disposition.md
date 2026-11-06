# T09 issue-by-issue disposition

Overall: **preparation and fixture pilot; voice/audio milestone remains open**. No author audio
was available in the inspected repository, supplied files or ZIP inventories. No listening decision
was supplied. Keep all three issues open; this draft contains no closing keyword or issue mutation.

Source status at intake: [baseline receipt](../verification/t09-audio/baseline.json).
Verification results belong to [the test receipt](../verification/t09-audio/README.md).
Author choices are in [the finite decision sheet](author-decisions.md); practical acquisition is
in [the contract](acquisition-contract.md).

## #23 · research and toolchain

Source: [issue #23](https://github.com/4444J99/journal-handwritten-web/issues/23), with no comments
at intake. Its forward/backward research report is preserved in `claude/` and was read together
with both implementation plans. The earlier delivered-research checkbox is historical evidence,
not a claim that its tool versions remain current.

| Checklist item | T09 disposition | Evidence / remaining action |
|---|---|---|
| Research report delivered | Previously delivered; reused | October 27 exchange, supplied/repository report with matching hashes in the source ledger |
| Recheck licenses and versions | Audit prepared from primary documentation | [Toolchain audit](toolchain-audit.md) separates installed runtime, current upstream observations, optional uninstalled tools and model/voice licenses; unresolved versions are explicit |

No actual voice-bank coverage, MFA alignment or intelligibility result follows from this issue's
research completion. Review the audit with the pilot draft; issue administration remains unchanged.

## #24 · concatenative voice-bank build

Source: [issue #24](https://github.com/4444J99/journal-handwritten-web/issues/24), with no comments
at intake. Current ownership is retained: author performance and choices; engineering acquisition,
alignment/cutting, rendering and integration. The generated technical fixture is not a surrogate
author performance.

| Checklist item | T09 disposition | Evidence / remaining action |
|---|---|---|
| Nine reserved spec decisions | Expanded into a finite, combined 14-choice sheet; unresolved | D01–D10 retain the original choices; D11–D14 cover the texture/reader questions, with struck/illegible and rights/privacy kept separate |
| Phase 1: script, prompter, alignment, cutter, minimal engine, 50 prompts | Technical pilot implemented and verified only to the scope of the receipt; author recording/listening open | Reproducible fixture run, packet, explicit interval alignment/cutter and private listening workbench; no claim of a completed forced-aligner run or of an intelligible poem line |
| Phase 2: full forward bank, 3–4 sessions | Deferred behind real pilot and listening | The historical 2.5–4-hour estimate is not a current recording request; actual coverage/work estimate follows the accepted method |
| Phase 3: engine v1 | Not complete | Full-corpus pronunciation/coverage, pitch marks, TD-PSOLA/prosody, codec offsets, interop, listening and device performance remain later work |
| Phase 4: performed Red Room supplement | Deferred, author owned | Software reversal is labeled separately; no performed material was generated or requested |
| Phase 5: reader and studio integration | Staged owner contracts | [Integration handoff](integration-handoff.md); live reader/studio wiring waits for accepted real sound direction and the respective integrators |
| Phase 6: `voicebank-anthony-v1.0.0` release and pin | Not started | No bank release, new repository, license grant or publication; exact output and permissions need separate later decisions |

The mirror and software Red Room modes retain distinct transform definitions and provenance.
The pilot's bounded DSP is not the full phonetic reverser or a substitute for author listening.

## #35 · voice-derived textures and browser audio

Source: [issue #35](https://github.com/4444J99/journal-handwritten-web/issues/35), with no comments
at intake. The earlier proposed sequence waited for recordings before writing the renderer. The
current T09 request explicitly reverses that dependency: prepare and test the tools first.

| Checklist item | T09 disposition | Evidence / remaining action |
|---|---|---|
| Phase 0 ~30-minute phoneme pilot | Reconciled with #24 into one proposed session | 50 total prompts; 24 texture takes cover two of each of 12 categories; actual recordings absent |
| `audio_build/render.py` and hidden listening page | Bounded private tooling prepared before acquisition | Local harness is outside deployment roots; fixture comparisons and immutable receipts; workbench controls are technical UI, not reader presentation |
| Palette after listening | Open, author owned | D11; dry/processed comparisons retain parameters and hashes; no selected palette |
| iPhone silent-switch choice | Open, author owned and device dependent | D14; no forced `playback` session policy or silent-media bypass; no real iPhone acceptance claimed |
| Raw-library privacy | Private hold during this task; long-term choice open | D09 separate from voice reuse D08 and release of a rendered poem |
| Struck/illegible treatment | Open; separate choices | D12/D13; no ghost-layer default, inferred pronunciation or silently omitted unknown word |
| Phases 1–5: full session, `audio.js`, pronunciation/Sound review, versions, weekly workflow | Staged beyond listening gate | Acquisition/identity/lifecycle/release contracts prepared; no live `audio.js`, bank or studio collection is claimed delivered |
| Add the plan to both plan copies | Dated T09 addenda | `docs/plan.md` and `claude/plan.md` retain their earlier text and add this current bounded plan |

## What unblocks the next milestone

The author selects the acquisition choices and records the combined pilot with an existing
device. Engineering validates the immutable originals, reviews labels and produces comparable
samples with exact provenance. The author then selects or rejects the real sound direction by
render ID. That decision precedes full acquisition, performed supplements and one bounded
reader/studio integration. Publication requires T03's independent exact-output clearance and
current execution authority.

These are concrete remaining inputs, not requests for permission to finish already-authorized
tooling. The separate shared-context packet remains inaccessible and supplies no approval.
