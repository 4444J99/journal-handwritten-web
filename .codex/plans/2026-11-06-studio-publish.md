# versforms: Publish from the Studio — Implementation Plan

Nov 6, 2026 · @anthony james padavano

## Summary

Posting a poem becomes two taps in the studio — **Publish**, then **Confirm** — from any device, with no terminal, no GitHub step and no redeploy.

- **What changes:** the studio builds the public version of a poem itself, shows an exact preview, and on confirm writes an immutable snapshot to a public store. versforms.pages.dev serves only that store.
- **What it replaces:** `tools/post_poem.py`, the public-repo pull request and the per-post Cloudflare deploy. The Python build stays as the reference the new build must match.
- **What it keeps:** every gate and hard stop the posting script enforces today, `noindex`, the Reserve rule and the private/public split — made stronger, because the public site has no connection to the private database.
- **Cost:** about six to eight focused sessions of agent work plus a few owner clicks. Runs on the existing Cloudflare account; whether the free Workers plan's CPU limit is enough is the first thing Phase 0 measures.

Poem 1 does not have to wait: it can go up once through the current path as a bridge, or be the first use of the button.

## Where things stand today

Today a post takes seven steps across three systems, and four of them need a computer with a terminal.

1. Sort the poem into Series in the studio (phone or browser).
2. Export the studio database to files with `wrangler d1 execute` and `studio-cf/export_db.py` (terminal).
3. Dry-run `tools/post_poem.py` (terminal; needs `gh`, Pillow and a font-tools venv).
4. Real run: builds the site, pushes a branch and opens a PR on `4444J99/versforms` (terminal).
5. Merge the PR on GitHub; Cloudflare Pages redeploys the public site.
6. Commit the changed `release/public.json` in the private repo (terminal).
7. Mark posted in the studio.

The reason is structural. The public site is a separate static repository rebuilt from the private source on every post, so posting means running the whole build: filtering the data, cutting a new line atlas with Pillow, renaming the embedded font with fontTools, and shipping the result through git. The studio already runs on Cloudflare with its own database (D1 `object-lessons-submissions`, tables `vf_docs` and `vf_revs`) and photo bucket (R2 `versforms-studio-assets`), behind Cloudflare Access; it simply has no way to publish.

## Target architecture

Three parts, with a one-way door between them: the studio builds and writes, a public bucket holds what was confirmed, and the public site only reads that bucket.

&#91;embedded content: publish architecture · private studio, one public bucket, public reader\]

The studio function reads the private stores and writes snapshots to the public bucket; nothing on the public side can reach back. The public site function serves the engine page, its data and its images from whichever snapshot `current.json` names.

## Data and storage

Everything private stays where it is; one new public bucket is the only thing the public site can read.

| Store | Holds | Who can read | Who can write |
| --- | --- | --- | --- |
| D1 `object-lessons-submissions`, `vf_docs` (existing, shared with another project; `vf_` prefix only) | Reviews, decisions, release records, batches, settings; new `publish` documents (snapshot history) | Studio function only | Studio function only |
| Studio deployment (static, behind Access) | Engine source `site/data/j.json`, all scans (`img/p`, `i`, `m`, `s`, `h`), private atlases, `studio/data/review.json` | Studio, behind Access | Agent deploy only (rare: when source data changes) |
| R2 `versforms-studio-assets` (existing, bound as `PHOTOS`) | Phone photos; new: draft snapshots awaiting confirm, under `drafts/` | Studio function only | Studio function only |
| **R2 `versforms-public` (new)** | Confirmed snapshots under `snapshots/<id>/`, content-addressed images under `img/<sha256>.jpg`, and one pointer file `current.json` | Public site function (read-only in code) | Studio function only |
| Approved public shell (new, built once) | `index.html` with title `versforms`, `noindex`, renamed `ajp-scribbles` font, sha256 recorded | Public | One reviewed PR per engine change |

Sizes: the full scan set is about 40 MB and `j.json` 276 KB, far inside R2's free 10 GB. Images are stored by hash, so a poem that reuses a page already public copies nothing new.

**The font is renamed once, not per post.** That is the only step that needs Python's fontTools. The shell is built with the existing `tools/build_public.py` code, reviewed once, and its hash is pinned; a publish refuses if the shell does not match the pinned hash.

**The atlas** (line crops packed into a JPEG for the canvas) is the one remaining image operation. Preferred: precompute per-page atlas tiles once, deterministically, so a publish only selects files. Phase 0 confirms the engine can read several atlas tiles; the fallbacks are in Risks.

## The publish flow

From the author's side, a post is: Publish, look, Confirm. Everything below happens in the studio, on a phone or a laptop.

1. **Publish.** In Release → Calendar, each Series row gets a Publish button. Tapping it starts a candidate build.
2. **Gates.** The studio shows each gate as passed or failed: in Series; every line confirmed or corrected; in a filed batch, or the recorded GRUW policy is "skip". A failed gate shows what to fix and an explicit "publish anyway" (the old `--force`). A hard stop (Reserve, Archive, stale transcript, a leak) shows no override.
3. **Shared scans.** If another unposted Series piece is readable in the same scan, the studio lists it with a checkbox per piece (the old `--accept-shared-scan`). Unchecked means no publish.
4. **Preview.** The candidate opens in the real public engine, inside the studio, at phone size and desktop size. Under it: which version is published, the reader-visible strings (title, info-panel line, font name records), warnings such as corrections sitting on unpublished versions, and the file list.
5. **Confirm.** A second tap confirms exactly the previewed candidate (bound by its hash). The snapshot is copied to the public bucket and the pointer moves. The release record is written automatically: the appearance (type "site", today's date) and the n/100 number if numbering is set to "as posted".
6. **Done.** A link to the live page. The history list shows every snapshot; **Roll back** re-points to any earlier one; **Unpublish** builds a new snapshot without a poem.

One post takes about a minute. No export, no repository, no deploy.

## Porting the build

The new build is a JavaScript module, `studio-cf/lib/publish.js`, that reproduces what `tools/post_poem.py` and `tools/build_public.py` (about 1,860 lines together) do to the data, minus everything about git.

| Part | Today (Python) | New (studio function) |
| --- | --- | --- |
| Gate (a) in Series | `gate_series` | Same rule, read from `vf_docs` |
| Gate (b) fully verified | `gate_verified`, all versions | Same |
| Gate (c) filed | `gate_filed`, filed or registered batch | Same, plus a recorded GRUW policy of "skip" (new decision document) |
| Own pool not exactly `series` | Hard stop | Same; no override |
| Shared scan, incl. facing page of a spread | Hard stop unless `--accept-shared-scan` | Same; per-piece checkboxes in the preview |
| Stale transcript (review `original` ≠ current reading) | Hard stop | Same |
| Final version choice, corrections applied, quotation blocks withheld | `build()` | Same rules, same output |
| Unpublished blocks emptied, line boxes kept only for published blocks, provenance keys removed, piece links renumbered | `build()` | Same |
| Reader metadata (`PAL`, `HF` page lists) filtered to published pages | `filter_reader_metadata` | Same string operation on the pinned shell |
| Line atlas | Pillow, per build | Precomputed tiles, selected per build |
| Font rename + check | fontTools, per build | Once, at shell build; pinned hash checked per publish |
| Other project's name, in any case or encoding | Text, bytes, decoded font | Text and bytes of every output file; font covered by the pinned hash |
| Output checks (noindex, title, expected pieces, all images present, no unpublished line text) | After build | Same, on the candidate before confirm and again on the stored snapshot |
| Public repo preconditions, branch, worktree, push, PR | The git half of `post_poem.py` | Gone |

The structural check on `data/j.json` stays the authority: every unpublished block empty, every non-empty line a published reading or correction. The Python code is not deleted; it becomes the reference the JavaScript must match (see Verification).

## Public site changes

The public engine page is unchanged; only where its data and images come from changes.

- **`4444J99/versforms` holds the pinned shell plus a small function**, `functions/[[path]].js`, and a `wrangler.toml` binding the `versforms-public` bucket as `PUBLIC`. It stays a git-connected Pages project; it changes only when the engine changes, through a reviewed PR.
- **Same paths as today.** The function answers `/data/j.json` and `/img/...` from the snapshot named in `current.json`, so the engine code does not change. `/` serves the shell, with the snapshot's filtered `PAL`/`HF` lists.
- **Nothing published = blank paper.** No pointer, or an empty snapshot, serves the current blank page. A missing image is a 404, never a fallback to something else.
- **noindex twice.** The shell carries the meta tag, and every function response sets `X-Robots-Tag: noindex`. Removing it stays the author's decision (`docs/noindex.md`) and is out of scope here.
- **Caching.** Responses carry the snapshot id as their ETag and a short cache lifetime (60 s), so a confirm or roll back is live within about a minute.
- **Requests.** Every page view calls the function a few times (page, data, images). The free plan allows 100,000 function requests a day ([limits](https://developers.cloudflare.com/workers/platform/limits/)); if that ever matters, images can move to cached static serving.

## Security and privacy boundaries

The public site cannot leak what it cannot reach: it has no binding to the database, the studio deployment or the private bucket.

- **One-way door.** Only the studio function writes to `versforms-public`; the public function only reads it, and only the keys under the current snapshot and `img/`.
- **Behind Access.** The publish endpoints sit behind the same Cloudflare Access login and the studio's own token check (`functions/_middleware.js`, which fails closed), plus an owner-email allowlist checked in code.
- **Confirm publishes what was previewed.** The confirm request carries the candidate's id and hash; anything else is refused. Requests are POST with JSON, same-origin only.
- **Immutable snapshots.** A snapshot is written once and never edited. The pointer `current.json` is the only thing that changes, and every change is logged in `vf_docs` with who, when and from which snapshot.
- **Checked twice.** The output checks run on the candidate before preview and again on the stored copy before the pointer moves.
- **Shared database.** The studio's D1 database is shared with another project; every new query keeps to `vf_` tables and goes through the existing guard (`sqlguard.py` rules).
- **Unchanged rules.** Reserve and Archive never publish; `noindex` stays; no AI-written text is added to the reader-facing page — the info-panel and font wording remain the author's decisions (#108).

## Verification

The new build is accepted only when it produces the same public data as the Python build for the same inputs.

1. **Parity fixtures.** Run both builds on the existing posting test fixtures and on the real data with the real export, for `p001` and for several synthetic release lists. `data/j.json` must be byte-identical after canonical JSON formatting; the file list and image hashes must match, except the atlas, which is compared line by line (each published line's crop rectangle and pixels).
2. **Adversarial cases carried over.** Every gate and hard-stop test in the Python suite gets a JavaScript twin: Reserve and look-alike pool values, unsorted, shared scans and facing pages, stale transcripts, malformed batches, the other project's name in any case or encoding.
3. **Function tests.** Local `wrangler pages dev` with local D1 and R2: confirm needs the previewed hash; a second identity is refused; the public function never serves a key outside the current snapshot; empty state serves blank paper.
4. **Staging site.** A second public project, `versforms-staging`, with its own bucket and `noindex`, receives a real end-to-end publish of `p001` from the hosted studio before production does.
5. **Owner acceptance.** On a real iPhone and a laptop: the staging page loads and reads, controls appear on tap, the font renders; then the same on production after the first real publish.

What this does not prove: physical-device behavior beyond the phones tested, and Cloudflare's own availability.

## Phases

Six phases in order, each ending in something checkable; the button is usable after Phase 5.

| Phase | Work | Done when | Sessions |
| --- | --- | --- | --- |
| 0. Spike | Measure the build's CPU time in a Pages Function on the free plan; confirm the engine can read several atlas tiles; confirm R2 binding on the git-connected public project | A written go / fallback choice for CPU and atlas | 1 |
| 1. Pinned shell | Build the public shell once with the existing Python tools (title, noindex, renamed font, metadata policy from #108); precompute atlas tiles; one reviewed PR to `versforms` | Shell merged, hash recorded, live site still blank | 1 |
| 2. Port the build | `studio-cf/lib/publish.js`: gates, hard stops, filtering, output checks; parity and adversarial tests against the Python build | All parity fixtures byte-identical; all twin tests pass | 2 |
| 3. Storage and public reader | Create `versforms-public` and `versforms-staging` buckets and the staging project; public function; empty-state behavior | Staging and production both serve blank paper from the bucket | 1 |
| 4. Studio UI and API | Publish, gates, shared-scan checkboxes, preview, confirm, history, roll back, unpublish; automatic release record; GRUW policy decision | Local end-to-end passes; hosted publish to staging works | 1–2 |
| 5. First real publish | Owner publishes `p001` to staging, checks on iPhone, then to production | Live page verified; release record written | owner, \~15 min |

Total: about six to eight agent sessions plus the owner steps in the next section. The Python posting path stays working throughout as the fallback, and is retired from the docs only after Phase 5.

## Author decisions needed

Five decisions shape the build; the rest are clicks.

- [ ] **Approve the design**, including replacing the public-repo pull request with preview-and-confirm as the review step.
- [ ] **GRUW policy:** record "skip" as the standing policy in the studio, so gate (c) passes without a per-post override. (Stated in chat on 2026-11-06; not yet recorded.)
- [ ] **The three wording calls in #108**, now decided once for the pinned shell: page ids in `PAL`/`HF` (accept, or filter per snapshot as planned); the font's description records (sign off, or blank); the "not yet checked by the author" line (remove, or derive per piece).
- [ ] **CPU fallback, if Phase 0 needs one:** build in the studio page and verify on the server (free), or the Workers Paid plan ($5 a month).
- [ ] **Bridge for poem 1:** post it once through the current path, or wait for the button.

Owner clicks, when the phases reach them: approve the one shell PR; confirm the new buckets and bindings exist (an agent can create them if given access); publish `p001` to staging and production; check on a real iPhone.

## Risks, open questions, and what is not changing

The biggest risk is the free plan's 10 ms CPU limit per function request ([Cloudflare limits](https://developers.cloudflare.com/workers/platform/limits/)); Phase 0 measures it before anything else is built.

| Risk | Effect | Mitigation |
| --- | --- | --- |
| Build exceeds 10 ms CPU | Publish fails on the free plan | Precomputed per-piece index so the function reads a small slice; else build in the studio page and verify on the server; else Workers Paid ($5/month, 30 s default) |
| Free plan: 1,000 Cloudflare-service subrequests per invocation | Large image copies fail | Content-addressed images copy only what is new; copy in batches across requests |
| Engine cannot read several atlas tiles | Precomputed atlas does not work | Small engine change, or build the atlas in the studio page with canvas (geometry-checked, not byte-checked) |
| Two builds drift (Python and JavaScript) | Future fixes land in one only | Parity tests stay in CI; the JavaScript becomes the authority after Phase 5 |
| A bug publishes unpublished text | Reserve rule broken | Structural check on data, output checks twice, staging first, roll back in one tap |
| Access misconfiguration | Publish endpoint exposed | Middleware fails closed; owner allowlist in code; studio runtime set to Fail closed (confirmed by the author) |

**Open questions:** whether the public `versforms` project keeps its git connection or switches to direct upload; whether to keep a copy of each snapshot in the private repository for history (manual export, or later automated).

**Not changing:** the review studio's line review and decisions; the canonical source and its repository; the D1 schema beyond new `vf_docs` collections; the Reserve rule; `noindex`; the standing rules on AI-written text and chrome-on-tap presentation; this work being separate from ETCETER4.
