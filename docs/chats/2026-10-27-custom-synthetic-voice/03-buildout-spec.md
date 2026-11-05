# 03 · Voice Banks buildout spec (Claude Docs)

| | |
|---|---|
| Chat | https://claude.ai/chat/2f242443-6911-47d2-a361-dbb83d08ad18 |
| Exchange | 03 of 3 · 2026-10-27 |
| Issue | #24 |

## Asked
"Provide the full spec for buildout."

## Answered / produced
- Claude Docs document "Voice Banks: Buildout Spec", artifact `6eig11rh137yccC9A2YikU` (project container `2dc1e4f2-d1b8-4398-b450-d482c7aea5a5`), with an architecture diagram widget (build lane offline in Python, playback lane in browser JS).
- Sections: scope and goals (four modes: forward, mirror, Red Room software, Red Room performed); architecture and polyrepo layout (`voicebank` private, `voice-engine`, journal project `voice/`, `voice_build/`, `recording/`); ARPAbet phone set (39 + `pau`, `dx`), `lexicon.json` from CMUdict with author overrides, `.vmk` inline markup; forward script generator and session protocol (3–4 sessions, 48 kHz/24-bit, calibration takes, 50-prompt pilot); backward banks and reverser rules; MFA alignment, diphone cutting, pitch marks, QC gates; browser engine pipeline and API (TD-PSOLA, crossfaded joins, seeded determinism, timing map); bank package and `manifest.json` schema; integration with the merged piece (`1Pcbgrvp7BqfmcYhzZLEss`) and review studio (`MVognnZQrtRQ6QCMaF7341`); six phases, acceptance tests, risks, tool licences.
- Spec lists nine decisions reserved for the author.

## Author decisions
None in this exchange beyond the request.

## Plan
- **author**, open: make the nine reserved decisions (read style; carrier phrase; pronunciation authority, current vs 2014–2015; stressed/unstressed vowel split; performed Red Room scope; Red Room caption visibility; eSpeak NG fallback; voice licence terms and master publication; mic for main sessions).
- **Claude suggestion**, open: phase 1 pilot — script generator, prompter, alignment, cutter, minimal engine; author records 50 prompts (~1 h).
- **author**, open: phase 2 forward bank recording, 3–4 sessions (2.5–4 h).
- **Claude suggestion**, open: phase 3 engine v1 against the acceptance tests.
- **author**, open: phase 4 performed Red Room recording (1–3 h plus practice).
- **Claude suggestion**, open: phase 5 integration into the merged piece and studio voice tab.
- **Claude suggestion**, open: phase 6 release `voicebank-anthony-v1.0.0` and pin it in the journal project.
