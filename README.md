# journal-handwritten-web

Private source of record for **versforms**, its reader, review studio and release tools.
The public output lives in the separate `4444J99/versforms` repository. The earlier
working-name discussion is retained in the dated plan; the current identity is
`vers.forms` / `versforms`. This does not establish account or domain ownership.

This is not ETCETER4. Scans originate from `4444J99/etceter4` (commit `dfcbf0f`,
`img/photos/diary/`), recorded in `site/data/j.json` → `prov`.

## Current engineering state — November 6, 2026

The integration adds a reconstructed canonical source and deterministic data rebuild,
actual private Studio entry points for notes and artifact previews, shared reader
lifecycle and version navigation, immutable evidence storage, and exact-output
release checks. The original missing generators were not recovered. Their bounded
replacement preserves the current HTML templates, raw transcripts, stable identities
and image bytes. See the [source contract](docs/contracts/canonical-source.md),
[integration record](docs/chats/2026-11-06-integration-closeout.md), and
[release/artifact contract](docs/integration/exact-output-and-private-artifacts.md).

- Source: 123 pages, 126 pieces, 156 versions and 2,190 line IDs. All 38 preserved
  reviews are applied as overlays: 33 confirmations and five corrections. Raw
  originals remain available for stale-review checks.
- Reconstruction: `python3 tools/source_foundation.py validate`, followed by
  `rebuild` (dry run) or `rebuild --write`. `apply-reviews --help`, `backup --help`,
  `restore --help` and `ingest-photo --help` document controlled updates and recovery.
- Studio: the Cloudflare implementation is the tested persistence route. Its nine
  collections include append-only notes, contributions and artifacts. Local tests
  exercise save, reload, restart, export, independent restore, forks and unrelated
  table preservation. New studio links expose private workbenches through the same API.
- Reader: exact piece/version links, selected-version bounds and cleanup use one
  lifecycle. Missing line geometry retains page/text fallback; no author mapping is
  inferred. Audio and realization previews require explicit invocation.
- Publication: `release/public.json` remains empty. A private packet or passing
  technical check does not provide author clearance or execution authority.

The hosted studio was reported deployed behind Access in the November 5 record.
This integration's local acceptance does not establish deployed save/reload,
rejection of a second real identity, current dashboard configuration, or physical
phone acceptance. Those owner checks remain in #104. The native Claude artifact
route has an almost-full historical file map and unverified conditional writes;
it does not inherit the Cloudflare route's guarantees. GitHub runner state and
local test results are recorded separately; no billing or security setting is changed.

## Layout

```
site/                     the merged piece — a static site, deployable as-is
  index.html              page + code (handwriting font embedded as WOFF2)
  data/j.json             pages, line boxes, pieces, version stacks, provenance
  img/p/                  page scans, full (1600 px tall)        123
  img/i/                  page scans, mid (1200 px)               123
  img/m/                  page scans, small (600 px)              123
  img/s/                  2015 two-page spreads (recovered text)    6
  img/a/                  line atlases for the canvas (t0/t1, k0/k1)
  img/h/                  Hand↔Font plates                          3
studio/                   review studio and private workbenches (Cloudflare route below)
  index.html              page + code (v2, with the Release tab)
  data/review.json        pages, pieces, flagged-page list
  img/thumbs/             thumbnails                              123
                          full scans and spreads are shared from site/img/p, site/img/s
docs/plan.md              project plan, versioned copy of the Project doc
claude/                   the claude.ai Project's text documents: plan.md (the Project doc), 12 research reports, 5 PDFs
tools/check.py            integrity check: every referenced file present + checksums
tools/source_foundation.py canonical source, reviews, rebuild, photo staging, backup/restore
source/canonical.json     preserved identities, raw readings, reviews and asset lineage
tools/studio_files.py     file map for republishing the studio artifact
tools/build_public.py     builds the public site (released pieces only) for 4444J99/versforms
release/public.json       the released pieces — the only content that leaves this repository
exports/                  studio database exports, one JSON file per document (rebuild input)
docs/chats/               one plan record per Project chat
MANIFEST.sha256           SHA-256 of every file in site/ and studio/
CHANGELOG.md              one entry per tagged version
.github/workflows/        check (every push), pages (deploy site/, manual for now)
```

Every file in `site/` and `studio/` is referenced by one of the two pages; `tools/check.py`
fails if a reference is missing or a file's checksum changed without the manifest being updated.

## Versions

- Every change is a commit; each published state of the site is a tag `vYYYY.MM.DD[.n]`
  with a CHANGELOG entry.
- Poem versions (drafts and revisions behind the newest) live in the data, not in git history:
  `site/data/j.json` → `pieces[].V`. Git history versions the whole piece; the data versions
  each poem.
- New handwritten versions and review edits arrive through the studio, are applied to the data,
  committed, and tagged.

## Run locally

```
cd site && python3 -m http.server 8000      # http://localhost:8000
python3 tools/check.py                      # integrity check
python3 tools/check.py --write              # after an intended change: refresh MANIFEST.sha256
```

`site/` needs any static file server; it cannot be opened from `file://` because it fetches
`data/j.json`.

## Hosting

**Site (`site/`)** — GitHub Pages via `.github/workflows/pages.yml`. The workflow is manual-only
until the author decides the site is public: a GitHub Pages site is readable by anyone even when
the repository is private. A custom domain is added once the name is chosen (`site/CNAME` +
DNS).

**Review studio, historical artifact route** — the earlier artifact (`MVognnZQrtRQ6QCMaF7341`) keeps its
reviews, decisions and release records in that artifact's database. The current
Cloudflare route is documented in `studio-cf/README.md`; export each backend's saved
state explicitly. The older artifact publishing command is retained for reference:
`python3 tools/studio_files.py` prints the `files` map (published path → repo path).
Export the database collections (`reviews`, `decisions`, `versions`, `release`, `batches`,
`rconfig`) into the repo before any change to the studio that alters their keys.

## Load time

The repository by itself does not change load time; where and how the files are served does.
Measured 2026-10-27 by loading `site/` in a phone-sized headless browser: the first view of the
canvas downloads about 2.0 MB in 6 requests.

| Request | Size | Notes |
|---|---|---|
| `index.html` | 225 KB | includes the 40 KB font as base64, re-sent with every page change |
| `data/j.json` | 209 KB | fetched with `cache: "no-cache"`, so revalidated on every visit |
| canvas line atlases `k0`, `k1` | 817 + 764 KB | `img/a/`, needed for the first view |
| page scans | 4–430 KB each | loaded as they come into view |

Improvements available now that there is a build step (none applied yet):
font as a separate cached `.woff2`; WebP/AVIF scans (typically 25–50% smaller than these JPEGs);
content-hashed file names with long cache lifetimes so repeat visits load from cache; a service
worker for offline reading. GitHub Pages and Cloudflare Pages both serve from a CDN.

## Rebuild path

**Current replacement (November 6, 2026):** `tools/source_foundation.py` implements
the bounded reconstruction described above. Review application keeps originals
and provenance, requires a complete backup before mutation, and is idempotent.
Rebuild writes only data, leaving the accepted reader and Release-tab HTML intact.
Photo staging retains supplied bytes and marks transcription and anchors unavailable
until supplied and reviewed. Source backup and independent restore include every
export collection, including immutable history. See
[verification receipts](docs/verification/t02-source/README.md).

### Historical recovery inventory — November 5, 2026

**Status (checked 2026-11-05): the scripts that turn reviewed data back into published pages
are not in this repository and were not found on the author's machine.** The order below is the
documented one (`docs/plan.md`, "Rebuild order"). It cannot be run from the repository, with a
`--dry-run` or otherwise, until those folders are supplied. They are not recreated here; see
"Not in this repository yet".

| # | Step | Script | Reads | Writes | In repo |
|---|---|---|---|---|---|
| 1 | Back up, then apply the studio's reviews to the transcripts | `review_build/apply_reviews.py` (backs up first, `--dry-run`) | export of `reviews`, `decisions`, `versions`, `release`, `batches`, `rconfig` | transcripts and `archive/data/journal.json` | no |
| 2 | Build the studio data and page | `review_build/build_data.py`, then `review_build/assemble.py` | updated archive | `studio/data/review.json`, `studio/index.html` | no |
| 3 | Build the merged piece | `app_build/build.py`, then `app_build/assemble.py` | updated archive | `site/` (`index.html`, `data/j.json`, images) | no |
| 4 | Check and publish | `python3 tools/check.py` (`--write` after an intended change); `tools/studio_files.py` (studio artifact files map); `tools/build_public.py` (public site) | the repository | `MANIFEST.sha256`; the public build | yes |

New handwritten versions enter before step 1: `app_build/ingest_version.py PHOTO --piece PIECE_ID`
(or `--piece new`) straightens the photo, cleans it and finds line boxes, staged as
needs-transcription; then a transcription; then `--text-file`; then the rebuild. The copyright
deposit generator is `release/copyright/make_deposit.py` (up to 10 piece ids; it refuses
unverified pieces unless overridden). Neither script is in the repository.

Constraints any rebuild must keep:

- **The merged piece starts from `site/index.html`** (v4, 2026-10-28 interaction fixes), not from
  the older generator template, which lacks them. Verified 2026-11-05: `site/index.html` is
  byte-identical to artifact `1Pcbgrvp7BqfmcYhzZLEss` version `1793184934-ad80` (230,100 bytes,
  sha256 beginning `7c3e2862`). A step 3 that regenerates `site/index.html` from the old template
  drops v4.
- **The studio starts from `studio/index.html`** (the Release-tab page, version 2 of artifact
  `MVognnZQrtRQ6QCMaF7341`), not from the older `review/index.html`.

Export format (the input to step 1): one JSON file per document at `COLLECTION/DOCID.json`;
empty collections have no folder. The first export is `exports/studio-db-2026-11-05/` (38
reviews; the other five collections empty) and its own `README.md`. Back up the export
directory and every file a script rewrites before running an apply; never apply against the only
copy.

Where the missing folders were looked for on 2026-11-05: by folder name (`app_build`,
`review_build`) and by file name (`ingest_version.py`, `apply_reviews.py`, `make_deposit.py`,
`assemble.py`, `build_data.py`, `ingest_fillin.py`, `pieces.json`, `journal.json`) across the
working drive, Desktop, Documents, Downloads and iCloud Drive. None were found. The Google Drive
and OneDrive folders under `~/Library/CloudStorage` could not be read by the searching agent.
When copies are supplied, add them under `archive/`, `font/` and `tools/` and update this
section: mark each script as in the repository and record a `--dry-run` that was actually run.

## Not in this repository yet

The first build sessions' working folders — transcripts, `archive/` (journal.json, pieces.json,
manifest of originals), `font/` (OTF/WOFF2 sources, fill-in sheet), and the build/ingest scripts
(`app_build/`, `review_build/`, `release/copyright/make_deposit.py`) — were not preserved in
retrievable form. This repository was seeded from the published outputs of the two artifacts on
2026-10-27. If copies exist on the author's machine they belong in `archive/`, `font/`
and `tools/`; otherwise the tooling is rebuilt here against `site/data/j.json`.

## Rights

All poems, journal pages, handwriting and the handwriting font: © Anthony James Padavano.
All rights reserved. No license is granted for reuse, redistribution or model training.
Quoted reading notes in the journal belong to their authors and are recorded by source only.

## Public and private

This repository is **private** and holds everything: all scans, transcripts, the studio,
plans and chat records. The public site lives in **`4444J99/versforms`** and is deployed by
Cloudflare Pages. Only pieces listed in `release/public.json` go there:

```
python3 tools/build_public.py ../versforms/site     # then commit and push versforms
```

The build copies only the pages those pieces sit on, a fresh atlas holding only those pages,
and data for those pieces. Other pieces' text on a shared page is withheld, but the page scan
shows the whole page; the build lists such pages. With an empty list the public site is blank
paper.
