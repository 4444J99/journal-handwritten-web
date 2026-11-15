# 2026-11-15 versforms D1 write: Series orders p006-p010

## Produced
- One D1 batch on `studio-documents-prod` applying the Series sort decided in journal PR 163 (issue 105): release docs
  p006 `{"pool":"series","order":5}`, p007 6, p008 7, p009 8, p010 9. Statements in
  `exports/studio-db-pre-series-order-p006-p010-2026-11-15/forward.sql` (10 statements, one `wrangler d1 execute --file`, one `vf_revs` bump per document as the Studio writes). Snapshot, checksums and inverse SQL in the same folder, committed and pushed before the write.

## Author decisions
None in this session. Applied under the orchestrator's delegation of the PR 163 decisions.

## Read-back (live D1, 2026-11-15)
- Release rev re-read as 7 immediately before the write.
- vf_docs 60 to 65 rows (release 5 to 10; decisions 4, publish 12, reviews 38, versions 1 unchanged); vf_revs rows 5, release counter 7 to 12.
- p006-p010 data equal the decision; revs 8-12.
- Checksums identical to the snapshot: the 55 non-release vf_docs rows (3680c171...), release p001 (57c6e0da...), release p001-p005 as a group (543b8a55...), non-release vf_revs rows (ea7f63a2...).
- Inverse SQL not needed and not run.

## Status
D1 written (release collection only). No deploy; p001-p005 untouched, p011 onward unsorted, GRUW unchanged. Issue 105 sort for p006-p010 applied.
