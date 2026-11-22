---
title: "versforms Notebook Externalization — Master Index & Cross-Repo Agent Handoff"
source_notebook: "versforms"
export_date: "2026-11-22"
branch: "docs/notebook-export-index-20261122"
affected_repos:
  - 4444J99/journal-handwritten-web
  - 4444J99/versforms
  - 4444J99/discourse-of-course
  - 4444J99/chaucer-canterbury
  - 4444J99/chaucer
  - 4444J99/linguistic-atomization-framework
  - 4444J99/narratological-algorithmic-lenses
  - 4444J99/hand-script
  - 4444J99/atomic-substrata
  - 4444J99/media-ark
privacy: "private-source-of-record"
---

# `versforms` Notebook Externalization — Master Index & Cross-Repo Agent Handoff

Externalized on `2026-11-22` from the `versforms` research notebook into `4444J99/journal-handwritten-web` (private source of record) so coding agents (Claude Code, Codex, OpenCode) can work directly from the architectural research, locked decisions, and cross-repo contracts.

Each notebook chat was committed on its own isolated branch and PR with disjoint file paths under `docs/chats/2026-11-22-versforms-notebook-externalization/`, allowing all PRs to merge cleanly into `main` with zero merge conflicts while preserving per-chat branch provenance.

---

## 1. Exported Sessions

| # | Branch | File | Completeness | Core Scope |
| :--- | :--- | :--- | :--- | :--- |
| 01 | `docs/notebook-chat-01-variorum-coordinates` | [`01-variorum-coordinates-and-schema.md`](2026-11-22-versforms-notebook-externalization/01-variorum-coordinates-and-schema.md) | `partial-excerpt` | 7-layer variorum coordinate grammar (`P.S.L.W.m/s.C`), 100-poem Century slots, SQLite/D1 + JSON AST schema, live `JHW.001-C01` test |
| 02 | `docs/notebook-chat-02-post-metadata-ast-tei` | [`02-post-metadata-captures-and-tei.md`](2026-11-22-versforms-notebook-externalization/02-post-metadata-captures-and-tei.md) | `partial-excerpt` | Post metadata derivation, `C`/`S` siglum lock, MorphSeg surface/canonical alignment, multi-witness SQLite schema (`surfaces`/`strata`/`apparatus_notes`), TEI P5 emitter |
| 03 | `docs/notebook-chat-03-generative-audio-scores` | [`03-generative-audio-from-variorum-metadata.md`](2026-11-22-versforms-notebook-externalization/03-generative-audio-from-variorum-metadata.md) | `verbatim-retrieved` | Deterministic generative audio score projections from genesis class, strata, capture hashes, bounding boxes, enjambment, `.m`/`.s` sub-words, and bipartite diffs |
| 04 | `docs/notebook-chat-04-repo-ecosystem-map` | [`04-cross-repo-ecosystem-map.md`](2026-11-22-versforms-notebook-externalization/04-cross-repo-ecosystem-map.md) | `verbatim-retrieved` | 4-layer map of 9 core interacting repos + 16 adjacent `4444J99` repos + structural seams & boundaries to reconcile |
| 05 | `docs/notebook-chat-05-archival-civilization-witnesses` | [`05-archival-civilization-and-witness-pipeline.md`](2026-11-22-versforms-notebook-externalization/05-archival-civilization-and-witness-pipeline.md) | `verbatim-complete` | Three-layer "archival civilization", Composition Clock vs. Digitization Clock amalgamation (single-day scans + much-earlier phone photos + iOS Notes), canonizing an unknown, parameterized critic-operators, local macOS `osxphotos` + Notes JXA pipeline |

See [`PROVENANCE.md`](2026-11-22-versforms-notebook-externalization/PROVENANCE.md) for completeness details and upgrade instructions for partial excerpts.

---

## 2. Locked Architectural Decisions (Read Before Coding)

1. **Genesis Sigla Are Locked to `C` / `S`:** `C` = Codex (original lost physical notebook), `S` = Supplementum (interpolations written to complete the 100-poem Century). `A`/`I` is retired. Original-era iOS Notes require an explicit author decision on whether standalone contemporary notes use a third siglum (`N`) or `S` tagged with `source_medium = 'ios_note'` and historical `epoch_year`.
2. **Two Clocks Must Never Be Mixed:**
   * **Digitization Clock (`digitized_at`):** All diary scans were captured on a single batch day after the notebook was completed. Never use the scan timestamp as a drafting bound or caption "photographed" date.
   * **Composition Clock (`witnessed_at` / `created_at`):** Sparse phone photos (`EXIF DateTimeOriginal`) and iOS Notes (`created_at`) greatly predate the scans. Phone photos pin chronological intervals along the physical diary spine; interior spans interpolate between consecutive photo anchors; unanchored head/tail spans extrapolate from observed days-per-page velocity (never pulled toward scan day); iOS Notes interleave chronologically by `created_at`.
3. **Phone Photos Are Potential Earlier Textual Witnesses:** Because phone photos predate the scans by years, a photo may capture a page *before* later ink edits (`r0.i2`). Decouple `stratum_witnesses` (1:N) from `strata` rather than assuming a 1:1 `surface_id`.
4. **Repository Safety Invariants (`journal-handwritten-web`):**
   * Do not modify checksummed `site/` or `studio/` assets without running `python3 tools/check.py` and updating `MANIFEST.sha256` where required.
   * Stage local macOS photo/note intakes under `archive/intake/` (outside `site/`, `studio/`, and `release/public.json`).
   * Preserve shared-surface isolation (never publish unmasked full scans of multi-piece pages like `diary62a`).
   * Strip all EXIF/XMP/GPS/thumbnails from exported public social images *after* harvesting raw EXIF into local provenance records.
   * No author mapping is inferred automatically; OCR/fuzzy witness matches must pass a human confirmation gate (`pending_review` → confirmed).
5. **Parameterized Critic-Operators, Not Generic Persona Prompts:** Critical output in `discourse-of-course` must follow the `chaucer-canterbury` mathematical operator methodology—deriving empirical parameter vectors (`CRITIC_DEFINITION`) from primary critical corpora, validating on blind holdouts (`EVALUATION_ONLY`), and feeding structured variorum telemetry (7-layer AST + LingFrame rhetoric metrics + bipartite `r0 → r1` diffs).

---

## 3. Agent Workstreams (Ready for Local Execution)

### Track A — Local macOS Witness Intake & Chronology (`journal-handwritten-web`)
1. Implement `tools/harvest_macos_witnesses.py` (read-only `osxphotos` + Apple Notes JXA) targeting `archive/intake/` (spec in Chat 05).
2. Implement `tools/match_witnesses.py` using macOS Vision (`VNRecognizeTextRequest`) + fuzzy match against the 126 verified transcripts in `site/data/j.json`, emitting `source/witness_links.json` (`pending_review`).
3. Implement `tools/build_chronology.py` computing dual sort orders (**Physical Codex Order** + **Amalgamated Chronological Order**) into `source/chronology.json`.
4. Update social projection tooling so Round 1 Instagram posts pair **Slide 1 (Codex scan, cropped/masked, amalgamated date window)** with **Slide 2+ (paired earlier phone photo, EXIF-scrubbed, exact `witnessed_at` date)**.

### Track B — Variorum AST, Coordinate Validator & TEI P5 (`journal-handwritten-web` + `linguistic-atomization-framework`)
1. Freeze `validate_coord.py` regex and AST node resolver for `JHW.001-C01.r0 : P01.S01.L01.W01.m1.C01`.
2. Build deterministic 7-layer AST builder (MorphSeg `.m` + CMU/`pyphen` `.s` + spaCy UD `upos`/`feats`) and TEI P5 `<facsimile>` + `<app>` exporter (spec in Chats 01–02).

### Track C — Generative Audio & Visual Projections (`journal-handwritten-web` + `vox` / `speech-score-engine`)
1. Wire deterministic `audio_realization` score generator keyed to `scan_sha256` / `ast_sha256`, witness deltas (scan vs. photo), `studio_box` geometry, enjambment suspension, `.m`/`.s` sub-words, and bipartite diffs (spec in Chat 03).

### Track D — Parameterized Critic-Operators (`discourse-of-course` + `chaucer-canterbury` + `narratological-algorithmic-lenses`)
1. Port the blind-holdout `AUTHOR_DEFINITION` / `EVALUATION_ONLY` harness pattern from `chaucer-canterbury` into `discourse-of-course` as a `CRITIC_DEFINITION` calibration & holdout pipeline (pilot target: Harold Bloom).
2. Define the shared JSON contract (candidate home: `4444J99/schema-definitions`) linking `journal-handwritten-web` variorum telemetry + LingFrame metrics into `discourse-of-course` critic-operators.
3. Reconcile scope drift documented in Chat 04 (`versforms` description in `chaucer-canterbury` README; overlap between `chaucer` and `chaucer-canterbury`).
