# T09 author decision sheet

Fourteen bounded choices; no option has been selected by this engineering packet. Record the
choice, date, source and any author-supplied material in the session decision record. The existing
decision to use the author's own voice is retained. Technical safety defaults for this draft—local
only, fixture labels, sound off initially, and no publication—do not settle artistic preferences or
long-term rights.

For a machine-readable session, copy the template’s `decisions` list into the packet or session
configuration’s `author_decisions` field. Each resolved entry needs its own nonblank `choice`,
`author` and `source`; keep `author_text` and `decided_at` where relevant. Top-level author metadata
does not automatically resolve individual choices. The generated packet provides the equivalent
map keyed by D01–D14. Leave deferred entries blank.

## Before the author pilot

| ID | Choice | Practical options and consequence | Input needed |
|---|---|---|---|
| D01 | Reading style | **Even/near-monotone:** easier joins and later prosody control. **Slightly natural:** more living inflection, potentially less reusable transitions. **Short A/B within the pilot:** repeat a few calibration chains in each style and label them separately. | Style or A/B instruction; no style inferred from the old protocol |
| D02 | Carrier phrase | **A fixed technical carrier**, such as `Say ___ again`; **a different author-specified carrier**; **isolated chains for pilot only**, with a full-bank carrier decided later. Carriers affect adjacent sounds and cutting. | Exact wording, or explicit isolated-pilot choice |
| D03 | Pronunciation authority | **Present-day speech**; **remembered 2014–2015 pronunciations**; **present-day base with word-specific historical overrides**. A dictionary is a technical aid; it cannot choose the author's idiolect. | Authority and any known word exceptions; historical uncertainty stays recorded |
| D04 | Vowel stress inventory | **One vowel unit with stress tags**; **separate stressed/unstressed units now**; **pilot one set, revisit after listening**. A split increases acquisition/coverage work; preserving stress metadata does not decide the unit inventory. | Inventory choice before full-bank script generation |
| D10 | Microphone | **Existing phone**; **already-owned USB/XLR setup**; **two calibration takes on both existing devices**. Do not purchase equipment for this pilot. Record model/app/export settings and fixed placement. | Device and native export format; identify the equipment rather than assuming it is available |

The proposed 50-prompt/~30-minute scope is in [acquisition-contract.md](acquisition-contract.md).
The prompter supplies technical calibration text. It does not supply creative writing or pretend
that unsettled decisions are complete.

## At listening, before more acquisition

| ID | Choice | Practical options and demonstration | Input needed |
|---|---|---|---|
| D05 | Performed material | **Defer performed backward recordings**; **chosen words/transitions only**; **author-selected full lines later**. The software preview demonstrates reversal mechanics; it is not a performed reading. | Scope and exact author-selected material after accepting the pilot |
| D06 | Captions | **Author's existing forward text on request**; **author's existing forward text always while a reversed passage plays**; **no captions for an ambient-only mode**. Any new explanatory or creative captions must be supplied by the author. | Visibility plus exact text/version; blank until supplied |
| D07 | Missing-pronunciation fallback | **Stop and queue author pronunciation**; **explicit silence decision for a specific token**; **evaluate an eSpeak NG phonemizer later**. Generic eSpeak speech would conflict with the recorded-own-voice requirement; a phonemizer and an audio voice are different choices. The pilot visibly refuses unknown words. | Scope of fallback permission and later tool/license review if chosen |
| D11 | Sound palette | Compare **dry voice/joins**, **10×/50×/200× spectral stretch**, **freeze**, **octave resampling**, and **voice-derived reverb** using the same take. Keep/reject/defer by exact render ID and parameter set. It is valid to choose no ambient layer. | Real-recording listening decisions, devices used, and author's own notes |
| D12 | Struck words | **Silent**; **audible as their recorded reading**; **author-approved ghost treatment**. A strike is editorial evidence; sound treatment must not silently restore withdrawn text. | Decision tied to the exact version/line; ghost treatment is an unaccepted historical proposal |
| D13 | Illegible words | **Remain silent and flagged**; **author supplies a reading/pronunciation**; **author chooses an explicitly nonverbal event**. No invented word or automatic substitute. | Exact source selector and decision; uncertainty survives |

Fixture listening only answers whether the harness works. It cannot select an author's voice,
intelligibility target or palette. Exported listening feedback is evidence for review; it is not a
publication or full-bank approval.

## Before integration or distribution

| ID | Choice | Practical options and consequence | Input needed |
|---|---|---|---|
| D08 | Voice reuse/licensing | **Use in the author's own projects only**; **specific written permissions**; **a separately reviewed public reuse license**. Code, pronunciation data, acoustic models, raw recordings and rendered audio have separate provenance/terms. | Author's intended reuse terms; no license is invented by this packet |
| D09 | Master privacy | **Keep raw masters and cut units private**; **release selected units separately later**; **publish selected masters under an explicit later decision**. Approval of a rendered poem never implies approval of a bank or raw recordings. | Scope, asset hashes and recipients/audience for any later release; all held private in this task |
| D14 | iPhone silent-switch behavior | **Respect the physical silent setting**; **allow playback through it only after explicit Start**; **defer integration until both behaviors are tried on the actual phone**. Web Audio/platform behavior must be measured; no silent keepalive or other bypass is introduced by the pilot. | Desired behavior and real-device on/off/interruption results |

After a real-recording listening selection, the next engineering step is one bounded reader
playback integration coordinated with T04 and the studio integrator. The current implementation
prepares a standalone local controller; it does not change the live reader or studio.
