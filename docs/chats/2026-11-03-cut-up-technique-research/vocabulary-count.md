# Vocabulary count — journal-handwritten-web #56

Counted 2026-11-27 from `site/data/j.json` at main `0530a67a`
(sha256 `52ffba25ae850374a25049bdca880a2c5c19b000d4adb3108ba523a78b7178e9`).
Tool: `tools/vocabulary.py`; generated file: `studio/data/vocabulary.json`;
tests: `tests/test_vocabulary.py` (20 tests).

## The two counts

- **Confirmed-only vocabulary: 1,975 distinct word forms** — the transcribed
  `L` lines as they stand (2,190 lines, 123 pages).
- **With-uncertain vocabulary: 2,107 distinct word forms** — confirmed plus
  132 words appearing only in the per-page `u` uncertain-reading notes
  (312 notes, 669 quoted candidate readings), listed separately as
  `uncertain_only` in the generated file and never merged into the
  confirmed count.

## Counting rules

Lowercase fold; split on whitespace (em/en-dash split too); surrounding
punctuation stripped; apostrophes kept mid-word, stripped at the edges;
hyphenated words are single forms; a form counts only if it contains a
letter. 24 non-letter forms (numbers, ranges, dates, lone punctuation)
were excluded and are listed in the file's `notes`. 10 confirmed forms
carry the transcription's own `[[struck` / `]]` markup fragments and 16
carry an internal `/` or `#` (alternative readings such as `d/c`); both
are kept exactly as they appear, with examples in the file's `notes`.

## The pool guard

`reader_cut_pool()` in the same module keeps only pieces whose pool is
exactly `"series"`, using `cut_up.WITHHELD_POOLS` (reserve, archive,
unsorted, unknown) — the same definition #65's shared-scan rule and #55's
cut-up model use. It ships as the helper plus a unit test against fixture
data; no reader-cut pool exists yet, so nothing is wired into a pool.
`in_vocabulary()` answers from the committed word list and is the single
oracle #55's Cut tab uses to mark out-of-vocabulary words.

## Still the author's call

- Adopting idea 2 (new poems limited to journal vocabulary) and idea 4
  (poem 100 assembled only from poems 1–99).
- Whether machine-misread uncertain readings count under the no-AI-text
  rule — this file reports both counts instead of choosing.
