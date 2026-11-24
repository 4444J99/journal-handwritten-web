# Studio collections inventory (journal-handwritten-web #29, step 2)

Inventoried 2026-11-24 against main `035baddd`. This is the record the issue's
own rule asks for — "export studio database collections into the repo before
any studio change that alters their keys" — so a later change can check what
is exported, what is not, and how to export it.

## Where the live collections live

The review studio reads from a live Cloudflare D1 database (`vf_docs`: one row
per document, `studio-cf/schema.sql`) through Pages Functions (`/api/db/*`,
`studio-cf/functions/`), polled about every 15 s by `studio/cf-adapter.js`.
Nothing in this repo is the live database; the repo holds version maps and
dated export snapshots (below).

## Collections read by the studio

`studio/cf-adapter.js` lists eleven collections:

`reviews`, `decisions`, `versions`, `release`, `batches`, `rconfig`,
`notes`, `contributions`, `artifacts`, `parts`, `composites`

The revision stores narrow that list:

- `studio/notes-store.mjs` (`NOTE_COLLECTIONS`): `notes`, `contributions`
- `studio/artifact-store.mjs`: `artifacts`

## What `studio/data/` holds (version maps, not exports)

- `studio/data/notes-versions.json` — a version map (`format` / `version` /
  `provenance` / `pieces`); its provenance sources are `site/data/j.json` and
  `studio/data/review.json`. Read by `studio/notes-workbench.mjs` and
  `studio/artifact-preview.mjs` to check the source version map is fresh.
- `studio/data/review.json` — review data (`version` / `pages` / `items` /
  `flagged` / `acceptedReviews`).

Neither file is a dump of a live collection. Do not mistake them for exports.

## Exports already in the repo (`exports/`)

| Export | Collections with documents |
|---|---|
| `studio-db-2026-11-05` | `reviews` 38 |
| `studio-db-delta-2026-11-14` | `decisions` 4, `release` 1, `versions` 1 |
| `studio-db-pre-series-order-2026-11-14` | `release` 1 (+ forward/inverse SQL) |
| `studio-db-pre-series-order-p006-p010-2026-11-15` | `release` 5 (+ forward/inverse SQL) |
| `derived-decisions-2026-11-05` | `decisions` 2 |

Latest export: **2026-11-15** — nine days before this inventory. The live
database has moved since (the Nov 14–15 snapshots are series-order writes).

## Never exported

`notes`, `contributions`, `artifacts`, `parts`, `composites`, `batches`,
`rconfig` have no per-document export anywhere in the repo. The three
revision-store collections (`notes`, `contributions`, `artifacts`) are the
gap that matters most: they are the studio's live working state, and no
snapshot of them exists to restore from.

## How to export (needs the author's Cloudflare access)

`studio-cf/export_db.py` is the exporter (stdlib only; it never talks to
Cloudflare itself). Give it exactly one source:

- `wrangler d1 execute studio-documents-prod --remote --json --command
  "SELECT collection, id, data FROM vf_docs ORDER BY collection, id" > FILE`,
  then `python3 studio-cf/export_db.py --from-json FILE --out
  exports/studio-db-DATE`, or
- a local wrangler D1 persist directory:
  `python3 studio-cf/export_db.py --local PERSIST_DIR --out
  exports/studio-db-DATE`.

`tools/notes_backup.mjs` is local-only conversion between a
`COLLECTION/DOCID.json` directory and a `versforms-notes-backup` envelope
(`pack` / `unpack`); it makes no database or network calls and cannot
produce an export on its own.

A fresh export is a provisioning step (Cloudflare credentials), not a code
change: it is recorded here as an open fork, not built in the #29 PR.
