# Per-poem record and scheduler: update onto main

Date: 2026-11-26 (America/New_York).

## Produced

- Merged `origin/main` (which now holds the witness-suite, chronology and `j.json` /
  `notes-versions.json` changes) into the per-poem record / scheduled publishing branch. The
  one conflict was `MANIFEST.sha256`; it was regenerated with `python3 tools/check.py --write`,
  not hand-merged.
- Regenerated `studio/data/poem-records.json` with `python3 tools/poem_record.py --all
  --merge-exports`: the recorded source shas were stale after `site/data/j.json` and
  `studio/data/notes-versions.json` were rewritten on main. The file again matches live source
  (126 records) and carries 0 author notes and 0 `publish_at` values.
- `release/schedule-log.json`, the scheduler's already-published ledger, is now a tracked file
  (committed empty, not git-ignored). A publish run must commit it, or a fresh checkout loses
  the one-per-week memory; `tools/schedule_publish.py` says so in its docstring and in the
  publish result line.
- The ledger now records `due_date` (the `--due` input) and `published_on` (the actual run
  date, in the schedule's timezone, UTC when none is recorded) apart. The 7-day window reads
  `published_on` against the actual run date, so a back-dated `--due` does not reopen the week.
  Legacy bare-date entries still read as both.
- `publishable_note_heads` in `tools/poem_record.py` now also requires the approval objects
  behind the statuses (`editorial.approval`, `release.clearance`), naming a revision of the
  record's own chain, an approver, an instant and a content digest, matching the Studio rule in
  `studio/notes-model.mjs`. A hand-written status string with no approval never reaches the
  tracked file.
- Tests for each change in `tests/test_poem_record.py` and `tests/test_schedule_publish.py`.

## Author decisions

- None stated in this session. The cadence, the schedule and the release order remain the
  author's.

## Plan / next steps

- Suggestion: the first real publish run should commit `release/schedule-log.json` in the same
  change as the publish.
- Suggestion: the Studio's digest binding (`verifiedApproval`) is verified in JavaScript; if
  the tracked record ever needs the same proof in Python, port `contentDigest` with a
  cross-language fixture.

## Status

- Gates and test counts are in the PR description and the CI run. Nothing was published or
  scheduled; the PR was left in its existing state.
