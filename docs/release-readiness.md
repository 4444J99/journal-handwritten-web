# Release readiness report

`tools/release_readiness.mjs` answers "what stands between piece N and a release?" without opening
the Studio. It calls the same `buildCandidate` the Publish tab uses (`studio/publish-compiler.mjs`),
one piece at a time for the chosen target, and lists every gate or hard stop that fails. It never
forces a gate, never accepts a shared scan, and writes nothing except an optional `--json` file.

```
python3 studio-cf/prepare_publish.py --out /scratch/prepared            # once per source change; private output
node tools/release_readiness.mjs --prepared /scratch/prepared --db exports/studio-db-2026-11-05
node tools/release_readiness.mjs --prepared P --db D --pieces p002,p003,p004,p005
node tools/release_readiness.mjs --prepared P --db D --pieces p002 --require p002   # exit 1 unless releasable
node tools/release_readiness.mjs --prepared P --db D --summary --json report.json
```

`--db` is a directory laid out `COLLECTION/ID.json`: an `exports/studio-db-*` directory, or the output of
`studio-cf/export_db.py` run on a `wrangler d1 execute ... --json` dump of the live database. Absent
collections count as empty. The report describes the export it was given; it is evidence about that
export, not about the live database. Run it on a fresh export to see the current state.
Without `--pieces` it reports every piece that has a review, a release record or a batch entry, then
the first `--limit` (default 12) pieces in source order.

Exit status: 0 report written (and every `--require` piece is releasable), 1 a `--require` piece is
blocked, 2 bad arguments or an unassessed `--require` piece.

## What each blocker means and which Studio step clears it

| Blocker | Meaning | Step |
|---|---|---|
| `series` / `own_pool_not_series` | the piece has no Series pool (Reserve, Archive and unset are hard stops) | Release tab: sort into Series |
| `verified` | N lines of the chosen versions lack a confirm or correction | Review tab: read each page, confirm or correct |
| `filed` | no GRUW batch is filed or registered for it, and `gruw-policy` is not `skip` | Release tab batches, or record the policy decision |
| `shared_scan:pNNN` | a page of the chosen version also belongs to another piece | release that piece too, or accept the shared scan |
| `shared_scan:x-pageid` | the page also carries lines outside any piece | accept the shared scan after looking at them |
| `stale_transcript:LINE` | the transcript changed after that line was reviewed | re-confirm the line |

The report also shows the version the gate would publish and whether it came from a decided final or
the top of the stack, so a piece with several versions shows that choice is still open.
