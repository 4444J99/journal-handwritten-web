# journal-handwritten-web

Source of record for the handwritten-journal web piece and its review studio.
`journal-handwritten-web` is a working name; the project's public name is not chosen yet
(see `docs/plan.md`, Open item 1), and the repository will be renamed when it is.

This is not ETCETER4. Scans originate from `4444J99/etceter4` (commit `dfcbf0f`,
`img/photos/diary/`), recorded in `site/data/j.json` → `prov`.

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
studio/                   review studio (runs as a Claude artifact; see below)
  index.html              page + code (v2, with the Release tab)
  data/review.json        pages, pieces, flagged-page list
  img/thumbs/             thumbnails                              123
                          full scans and spreads are shared from site/img/p, site/img/s
docs/plan.md              project plan, versioned copy of the Project doc
tools/check.py            integrity check: every referenced file present + checksums
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

**Review studio (`studio/`)** — stays a Claude artifact (`MVognnZQrtRQ6QCMaF7341`) because its
reviews, decisions and release records are stored in that artifact's database, which only works
there. The repo holds its page and data, not its saved records. To republish it from the repo:
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
