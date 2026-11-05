# 01 · Research: atomic units, context sensing, tap animations

| | |
|---|---|
| Chat | https://claude.ai/chat/edb5991e-ea4f-4914-898b-13ab830315be |
| Exchange | 01 of 1 · 2026-10-28 |
| Issue | #32 |

## Asked
Launch a research plan on three things: treating the text as nested units (character, root/stem, word, sentence, verse, stanza, poem, whole piece), each open to modulation, remix, recursion and generative properties; making every visit different using location, time of day, weather, movement/gyroscope; and tap/click-triggered animations where letters, words or handwriting populate around the tapped poem or word.

## Answered / produced
- Launched an extended research task with the project context and the standing rules (no AI-written creative text; work alone on screen), asking for a comparative report by avenue with no poetic text.
- Research report artifact `compass_artifact_wf-25787ba2-9ca2-5e2a-a062-247e68b3cd12_text/markdown` (version `01a184d8-c643-73a9-9d5a-efdbfeec966a`), seven avenues:
  - Data model: stand-off "atom graph" linking every unit (glyph to archive) to transcribed text and a scan region; TEI facsimile/zone model; Kraken forced alignment for word/character regions; Morfessor / LingFrame for a morph layer.
  - Sensing: permission-free tier (seeded PRNG, time/date/season, touch velocity, dwell, return visits via localStorage) as the complete piece; gyroscope (iOS `requestPermission()` in a user gesture), coarse location and Open-Meteo weather as opt-in; skip ambient light and microphone.
  - Tap interaction: "concordance bloom" animating scan crops of the same glyph, word, version or root from elsewhere in the journal; scan-crop sprite atlases preferred over font or stroke reconstruction.
  - Generative rules graded by authorship risk: rearrangement, concordance, version morphing compliant; Queneau slots author-designed; Markov/n-gram a grey zone; LLM generation excluded.
  - Rendering: keep Canvas 2D, PixiJS v8 as upgrade path, DOM text layer for accessibility; iOS ~60 fps cap and Low Power throttling.
  - Accessibility/motion safety: reduced-motion fallbacks, hidden canonical text for screen readers, real-iPhone testing.
  - Release interactions: record release seeds for n/100; Reserve enforced at build time so no Reserve atom, statistic or model reaches the client; US Copyright Office Jan 2025 note; participation tiers.
- Feasibility vs. "aliveness" ranking table and seven open questions for the author.

## Author decisions
- Wants nested units from character up to the whole piece, each open to modulation, remix, recursion and generative properties.
- Wants every visit different, driven by parameters such as location, time of day, weather and movement/gyroscope.
- Wants tap/click on a poem or word to trigger animations of letters, words or handwriting around it.

## Plan
- **author** — answer the seven open questions (Markov/n-gram status; viewer vs. authored context; stroke reconstruction; scan crop vs. Etceter4 Diary font; struck-through/inserted words as atoms; revised versions in blooms; participation tier). **open**
- **Claude suggestion** — build the atom graph first (extend journal.json with stand-off units and scan regions; forced alignment below line level). **open**
- **Claude suggestion** — ship the permission-free variation tier (seed, time/season, touch, dwell, return visits) before opt-in sensors. **open**
- **Claude suggestion** — prototype concordance blooms from scan-crop sprite atlases. **open**
- **Claude suggestion** — enforce the Reserve at build time: atom extraction only over a published whitelist. **open**
- **Claude suggestion** — test on a real iPhone (permissions, 60 fps cap, Low Power Mode). **open**
