# 01 · Research report: learning world scripts via the poem series

| | |
|---|---|
| Chat | https://claude.ai/chat/e2eeb2e1-d30a-4d6f-ac84-3ef45548ea86 |
| Exchange | 01 of 1 · 2026-10-28 |
| Issue | #33 |

## Asked
Anthony asked for a research report on learning the world's writing systems (he named kanji, Hebrew, Sanskrit, Cyrillic, Greek) and using the poem series as the vehicle, rendering the poems into other scripts as part of the process. He also wants to translate other work later.

## Answered / produced
- Launched an extended research task with a brief covering project context, standing rules (translations count as his creative writing; no AI-supplied text), release/Reserve constraints and seven research questions.
- Research report artifact `compass_artifact_wf-f7b97f4f-9697-5179-b290-8197dd9b3fc0_text/markdown` (version `01a184d7-2c67-7011-9f25-a7536d79c2fc`), covering:
  - script vs. language distinctions and writing-system typology as the organizing lens;
  - a 12-script learning order (Greek first, kanji as a slow parallel track) and a Year 1 schedule;
  - rendering modes by stage (transliteration, homophonic, calligraphic, invented script; self-translation later; credited collaborator layers);
  - collaboration/ethics notes, including limits on AI use (drills, checks, lookups only);
  - technical notes: RTL (`dir`, bidi isolation), vertical `writing-mode`, complex shaping, Noto fallbacks, per-script glyph counts for extending the handwriting font;
  - data-model suggestion: `Poem → Version → Rendering {mode, script, language, author, status, date, publicStatus}`, renderings pinned to a version and flagged stale;
  - rights notes (informational): some journals treat online translations as prior publication; register originals (GRUW) before posting; keep Reserve poems offline in every script;
  - funding pointers; per-script time estimates labelled as extrapolations.

## Author decisions
- Wants to learn writing systems and use the poem series as the vehicle; wants to translate other work later.

## Plan
- **Claude suggestion** (open): pick one deep language (Greek suggested) and follow the weekly practice cycle aligned to one poem per week.
- **Claude suggestion** (open): model script renderings as an axis separate from edit versions, each tied to its source version, with a `publicStatus` field blocking export of Reserve poems.
- **Claude suggestion** (open): extend the handwriting font to Greek, Cyrillic, Hebrew first.
- **author** (open): verify journal self-translation policies and grant deadlines directly before relying on them.
