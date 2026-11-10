# Launch ledger, reconciled 2026-11-10

Evidence-bound reconciliation of the 2026-11-05 launch records. Each line names the command or source that
proved it. This document records state; it publishes nothing, adds no piece to `release/public.json`
(still `{"pieces": []}`), and changes no Cloudflare or GitHub setting.

## 1. Stale items in the 2026-11-05 handoff, corrected

| Handoff said | Evidence on 2026-11-10 |
|---|---|
| PR #73 open, needs merge | `gh pr view 73`: MERGED 2026-11-05T17:37:09Z |
| Tags `v2026.11.05`, `v2026.10.27` not on GitHub | `git ls-remote --tags origin`: `2744d7a` and `957584e` present (lightweight) |
| Issue #1 / PR #2 unreviewed | both CLOSED (#1 by #114, #2 superseded) |
| etceter4 read-only check pending | done: `4444J99/etceter4` and `4444J99/generative-multimedia-spatial-environment` are PUBLIC and each serves the 123 diary scans (tree of `img/photos/diary` has 124 entries in etceter4); report only, no change, per the author |
| Public site is a blank page | superseded, see section 2 |
| Re-run check workflow after billing fix | billing is not fixed; Actions still fail before starting (issue #111); `tools/ci_local.py --status` (`local-ci`) stands in |
| Issues #76, #86, #87, #90 open | their work is done or re-homed; #86 and #87 closed with a pointer here; #76 and #90 stay open because the GitHub Apps removal on `4444J99/versforms` is still the author's choice |

Still open and the author's alone: GitHub billing, GitHub Apps removal on `versforms`, GRUW (#106), the Pages
"Fail closed" switch (#104), name and handle availability, first-post date, offsite scan copy: done, see section 4.

## 2. Which host is which, and what each renders

| Host | What it is | Observed 2026-11-10 |
|---|---|---|
| `versforms.pages.dev` | Public reader. Pages project from `4444J99/versforms` (Functions read-only on R2 `versforms-public`) | HTTP 200, `x-robots-tag: noindex`. First paint is dark paper with a single menu control. `data/j.json` (2,304 bytes) is served and holds `p001` only (page `diary1`, six text blocks), pinned to snapshot `2df98fb5...bd5`. No scan images are reachable (`img/p/p001.jpg` and `img/s/diary1.jpg` return 404) |
| `versforms-staging.pages.dev` | Staging reader, binds only `versforms-staging` | HTTP 200, same single-piece data |
| `versforms-studio.pages.dev` | Private review/publish studio (direct upload, `studio-cf`) | HTTP 302 to the Cloudflare Access login on the team domain `4444j99.cloudflareaccess.com` (the memory note's `ivixivi` domain is outdated; the 2026-11-06 repair reset `ACCESS_TEAM_DOMAIN` from the account's authoritative organization) |
| the private repo's top-level `site/` | Raw source; not a deploy target | `site/_worker.js` returns an empty 403 on Pages for every route. A direct request that returned 403 came from this guard (or Access), not from the public reader |
| `4444J99/etceter4` | Music repo; also still hosts the original journal scans publicly | PUBLIC; not part of vers.forms |

**The public site is not blank any more, and the cause is recorded.** The Studio database
(`studio-documents-prod`, collection `publish`) shows the owner's own authenticated publications:
`p001` to staging 2026-11-07T01:57Z and 03:00Z, to production 2026-11-07T03:04Z (snapshot `23d77dda...`),
then production again 2026-11-07T04:36Z (snapshot `2df98fb5...`, current). The release document marks `p001`
pool `series`, order 0, with site exposures at staging and production. So the first public release of `p001` was
performed by the owner through the Studio on 2026-11-07; the Python posting path (`release/public.json`) was not
used and remains empty. This session performed none of it. Earlier docs that say "blank, nothing posted"
(handoff, README launch list) are corrected or superseded. No Instagram or other social post is recorded
anywhere in the repository or the database.

Two facts the owner should hold: `data/j.json` on a live public host contains the verbatim transcription of
`p001` page `diary1`, which is expected for a published piece; and the reader's `prov.verified` is `false`
for it. `p001`'s second version (`p001-diary62a-0`, carrying five author corrections) is unpublished; the live
snapshot is V[0] (`p001-diary1-0`).

## 3. Launch list status (supersedes the list in `docs/chats/README.md` where they differ)

1. v4 into `site/`, tag: done.
2. Scan backup: local custody copy verified (section 4); offsite copy made 2026-11-10 (section 4).
3. Name `vers.forms`, handle/domain availability: author, open.
4. Verify first poems in the Studio and sort into Series: only `p001` is verified (38 reviews) and sorted
   (`series`). `p002` onward have no line reviews and no pool.
5. GRUW: undecided (#106). The Studio path honors a recorded `gruw-policy` of exactly `skip`.
6. First poem: `p001` is live on the reader. Next pieces and the Instagram template: see the recommendation below.
7. Post (social): not recorded.

## 4. Scan preservation (nothing local-only)

- Originals: custody copy `Archives/versforms/journal-originals-2026-11-05/` (124 files, 103,971,563 bytes).
  `shasum -a 256 -c SHA256SUMS` re-run 2026-11-10: 0 failures. Each of the 123 page ids in `site/data/j.json`
  has a matching `<id>.jpg` there.
- The same originals are on GitHub in two public repos (etceter4 and generative-multimedia-spatial-environment).
- Derivatives: `origin/main` of this private repo tracks 123 files in `site/img/p/` and 123 in
  `studio/img/thumbs/`; the three `production/assets` scans compared equal to the custody originals by SHA-256.
  Local `main` equals `origin/main`.
- Claude.ai Project download: `Archives/versforms/claude-project-artifacts-2026-11-05/`, 0 checksum failures.
- Gap: the custody copy exists on one local volume; GitHub holds the originals but under the repositories the
  author has said should stop carrying them. An offsite copy (Dropbox/Drive/R2) is the open item in launch step 2.
  It was not made here because it was not asked and the author owns which store holds his scans.

- Offsite copy, 2026-11-10: Google Drive (rclone remote `gdrive`), folder
  `Archive/journal-scans-custody-20261110`, made with `rclone copy` (additive, nothing deleted). 126 objects,
  103,982,387 bytes. `rclone check <custody dir> gdrive:Archive/journal-scans-custody-20261110 --one-way`:
  0 differences, 126 matching files. Under the 5 GB threshold, so no restart note is needed.

## 5. First-release tranche: candidates and recommendation

`p001` is already released (above). The next tranche is the following pieces in journal-page order, from
`release/packets/2026-11-05-t03-current/first-release-queue.csv` (first four rows come from that file, p005 is read from `site/data/j.json`; default preview version = top of stack, no
decided final; no piece beyond `p001` has a Series pool or a filed batch):

| Piece | First page | Lines | Line reviews | Default version | Notes |
|---|---|---|---|---|---|
| p001 | diary1 | 22 (preview) | 38 of 38 (22 on diary1, 16 on diary62a) | p001-diary1-0 | live; 33 confirmed, 5 corrected, the corrections are on the unpublished diary62a version |
| p002 | diary2 | 14 | 0 | p002-diary2-2 | 3 versions |
| p003 | diary2a | 16 | 0 | p003-diary2a-0 | 1 version |
| p004 | diary3 | 20 | 0 | p004-diary3-1 | 3 versions |
| p005 | diary3a | not in the packet queue | 0 | p005-diary3a-0 | 1 version |

Only `p001` has first-five review material in the database: reviews exist for `diary1` and `diary62a` and for
no other page, so there is no review material for p002 to p005 beyond the transcription itself.

Recommendation (a suggestion, not a decision; selecting pieces is the author's):

1. Release p002 to p005 together as the second tranche, but only after he reads each page in the Studio and
   confirms its lines. That is the one gate nothing else can satisfy: the Studio's verification gate blocks
   a piece with no line reviews.
2. Before any of them go out, settle `p002`'s and `p004`'s version choice (each has three versions and the
   default is the top of the stack, not a chosen final) and sort all four into Series in the Studio (issue #105).
   Pieces whose pool is Reserve, Archive or unset are hard stops.
3. Decide GRUW (#106) once; the same decision covers the whole tranche.
4. Publish to staging first, look at it on a phone, then confirm production, as was done for `p001`.
5. Do not use `release/public.json`; the Studio publication path is the one in use.

## 6. Verification of this change

`python3 tools/check.py` passes (509 references, 0 missing). GitHub Actions cannot start runners (account
billing), so the remote `check` is not evidence; local verification is, and the merge uses
`--match-head-commit`.
