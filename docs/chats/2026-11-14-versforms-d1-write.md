# 2026-11-14 versforms D1 write: Series orders p002-p005

## Produced
- One D1 batch on `studio-documents-prod` applying the Series sort decided in journal PR 159 (issue 105): release docs
  p002 `{"pool":"series","order":1}`, p003 order 2, p004 order 3, p005 order 4. Statements are in
  `exports/studio-db-pre-series-order-2026-11-14/forward.sql`; one `vf_revs` bump per document, as the Studio writes.
- Pre-change snapshot, checksums and exact inverse SQL in `exports/studio-db-pre-series-order-2026-11-14/`.

## Author decisions
None in this session. Applied under the orchestrator's delegation of the PR 159 decisions.

## Read-back (live D1, 2026-11-15)
- vf_docs 56 to 60 rows (release 1 to 5; decisions 4, publish 12, reviews 38, versions 1 unchanged); vf_revs rows 5, release counter 3 to 7.
- p002-p005 data and orders equal the decision; revs 4, 5, 6, 7.
- Checksums of all non-release vf_docs rows, the release p001 row and the non-release vf_revs rows identical to the snapshot.
- Inverse SQL not needed and not run.
- Observation: the live database also holds a `publish` collection (12 docs: staging and production events, snapshots) that the
  decision file did not list; it is unchanged. No source-write fence document was present at write time.

## Status
D1 written (release collection only). No deploy; p001, p006-p010, GRUW untouched. Issue 105 sort for p002-p005 applied;
issue 106 unchanged (GRUW skip stays recorded; no filing).
