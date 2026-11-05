# 01 · Research: generative audio from voice phonemes

| | |
|---|---|
| Chat | https://claude.ai/chat/861e410e-3441-482d-96bf-f7b54bbbfa76 |
| Exchange | 01 of 2 · 2026-10-28 |
| Issue | #34 |

## Asked
Research how to add natural, generative audio that responds to the text and to what the reader selects. The author proposed recording consonant and vowel sounds in his own voice and building ambience by heavily slowing, speeding and manipulating them, without lowering the quality of the experience.

## Answered / produced
- Launched an extended research task; result is a research report artifact (`compass_artifact_wf-b19b4f7b-832f-5186-84a6-6bf46edee09c`, version `01a184df-e58d-76b9-a4ba-4fb5d5268821`).
- Report sections: precedents in sound poetry and e-literature; technique comparison (Paulstretch, phase vocoder, granular, convolution); text/interaction-to-sound mapping; browser architecture; quality and iOS checklist; phoneme recording plan; rights and licences; five-phase prototype plan.
- Main technical recommendation: heavy processing offline (mostly Paulstretch) into small compressed stems; in the page, a light Web Audio mixer/granulator (Tone.js or AudioWorklet, MIT), sound off until tapped; phonemes computed at build time with the CMU dictionary and hand-corrected by the author.
- Licence notes: Rubber Band and eSpeak NG are GPL, so offline use only; Tone.js and Signalsmith Stretch are MIT.
- Caveat stated: iOS behaviour comes from WebKit bug threads and developer reports; numeric targets are starting points.

## Author decisions
- Sound source is his own recorded voice (consonants, vowels, vocal sounds), manipulated into ambience.
- Audio should be generative and respond to the text and the reader's selection.

## Plan
- **Claude** — turn the research into an implementation plan — **done** (exchange 02).
- Phased work (pilot recording, palette, build phases) is tracked in exchange 02.
