# 02 · Six-phase audio implementation plan

| | |
|---|---|
| Chat | https://claude.ai/chat/861e410e-3441-482d-96bf-f7b54bbbfa76 |
| Exchange | 02 of 2 · 2026-10-29 |
| Issue | #35 |

## Asked
Devise a plan for implementing the voice-based audio.

## Answered / produced
- A six-phase plan (in the chat reply; no files written), with a split of roles: author records, listens, fixes pronunciations and makes creative calls; Claude writes scripts, the sound engine, wiring and tests.
- Phase 0: ~30-minute pilot recording (five vowels, M, N, S, SH, F, breath, whisper); Claude writes `audio_build/render.py` (offline stretches at 10×/50×/200×, freezes, octave shifts, voice reverbs) and a hidden listening page in the review studio. Gate: author picks palette and stretch settings.
- Phase 1: full session (~250–350 takes), cleanup, per-category loudness matching, manifest.
- Phase 2: `audio.js` in the merged piece from v4 `index.html`; sound off by default, one-glyph toggle among hidden controls (M key on desktop), iOS interruption handling, one bed per arrangement with crossfades, ~40 MB decoded budget. Gate: canvas frame rate unchanged; clean on a real iPhone with silent switch on and off.
- Phase 3: CMU-dictionary pronunciation build script; unknown words go to a new "Sound" check in the review studio; granulator fed by the visible line; zoom mapping; slow glides, no per-tap sounds, one-off sounds ≥ ~8 s apart.
- Phase 4: version-peel smear, struck-word ghost layer, Hand vs. Font contrast, idle drift after ~20 s.
- Phase 5: per-poem pronunciation file and optional bed as a step in the Release tab checklist; roots-and-glyphs mapping deferred.
- Offered to add the plan to the project plan document.

## Author decisions
- None stated in this exchange beyond the request for a plan.

## Plan
- **author** — record the ~30-minute pilot set (Phase 0) — **open**.
- **Claude** — build `audio_build/render.py` and the hidden listening page once pilot files are available — **open**.
- **author** — decide: sound palette (after Phase 0) — **open**.
- **author** — decide: respect the iPhone silent switch or play through it once enabled — **open**.
- **author** — decide: whether the raw phoneme library stays private — **open**.
- **author** — decide: how struck and illegible words sound, or whether they stay silent — **open**.
- **Claude** — Phases 1–5 (full session processing, `audio.js`, pronunciation pipeline and Sound check, version/revision layers, weekly workflow) — **open**.
- **Claude suggestion** — add this plan to `docs/plan.md` / project plan — **open** (not in the plan as of 2026-11-05 per the record).
