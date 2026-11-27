# Reading notes — journal-handwritten-web #17

Reference file: `studio/data/reading-notes.json`, created 2026-11-27
from `site/data/j.json` at main `222a8b18` (sha256
`52ffba25ae850374a25049bdca880a2c5c19b000d4adb3108ba523a78b7178e9`).
Format: `versforms-notes-backup` v1 (the `notes-v1` schema's backup
envelope); validated by the notes-model `restoreEnvelope` round-trip in
`tests/test_notes_layer.mjs`. Kept out of every presentation path:
nothing under `site/` reads it.

## What is in the file

Nothing yet. The envelope holds zero records — `notes: []`,
`contributions: []` — and that is deliberate, not a gap in the build.

## Why it is empty

The plan asked for the file to be sourced "strictly from the author's
own copied reading notes in the journal". Searched at the build head:

- No transcribed reading notes exist anywhere in the repository. The
  author's copied reading notes live in the handwritten journal pages
  themselves, which are not transcribed as text anywhere in the repo —
  `review.json` and `j.json` transcribe the poems, not the reading
  notes. Copying them in would mean transcribing handwriting from page
  images, which the plan forbids doing by guessing ("where a citation
  is uncertain, record the uncertainty rather than guessing").
- "Possible echoes (open item 6)" — the other raw material the proposal
  names — is not citations. It is the borrowed-line credit-style
  decision from the cut-up work (`#55`, `docs/contracts/cut-workflow.md`),
  still open and still the author's to decide.
- Page dates and positions are catalog metadata, already frozen in
  `studio/data/notes-versions.json`; they are not reading notes.

So there is nothing in-repo to copy into the file, and nothing was
invented to fill it. The T05 rule stands: do not seed notes.

## How it fills

The author writes notes in the review studio's Notes tab (which loads
the `studio/notes.html` workbench), and exports the private backup;
that export is the committed copy of this file. The public sidecar
(`site/data/notes.json`) is a separate projection: only notes the author
has editorially accepted and cleared for release review reach it, via
the notes-model projection. The reference file itself never reaches
`site/`.

## Still the author's call

- The notes themselves — what his reading notes say, which echoes to
  credit, and when a reflection is written.
- Whether the critical layer stays author-only or opens to invited
  writers (the build defaults to author-only, per the #17 plan, and
  builds no invitation or submission machinery).
