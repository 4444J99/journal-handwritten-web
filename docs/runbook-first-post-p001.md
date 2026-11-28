# Runbook: first post (p001)

Technical checklist for issue #113. It tells whoever performs the first post what must be true, how to check it, what to do, and how to undo it. It posts nothing and decides nothing: what goes public, and when, is the author's call. Written 2026-11-28 from the repository state at that date; re-verify every "state" line below before acting, because each is a snapshot.

## Which path

Two posting paths exist. Use the first.

| Path | Status |
|---|---|
| **Studio** (private Studio at `versforms-studio.pages.dev`: Release tab, publish to staging, then production) | The path in use. `p001` was released this way by the author on 2026-11-07 ([launch ledger](launch-ledger-2026-11-10.md) section 2). Recommended by the 2026-11-16 orchestrator status on #113. |
| `tools/post_poem.py` (opens a pull request in `4444J99/versforms`) | Not used. `release/public.json` is still `{"pieces": []}`. Documented in [posting.md](posting.md); keep it as a fallback only if the author asks for it. |

**State of p001 on 2026-11-10 (ledger):** already live on production at snapshot `2df98fb5...`, version `p001-diary1-0`, pool `series`. So for `p001` this runbook doubles as a *re-verification and re-post* checklist (for example after a correction or a second version). For the next pieces use the same steps with their ids; the open gates for p002 to p005 are in the [ledger](launch-ledger-2026-11-10.md) section 5.

**Do not use `--force`, `--accept-shared-scan` or "Mark posted" as a substitute for a gate or for the author's clearance** ([clearance contract](releases/release-clearance-contract.md), "Consumer rule").

## Part 1. Gates

Tick each one only with evidence in hand. "Verify" is the command or place that gives it.

- [ ] **1. In Series.** `p001` has pool `series` (Reserve, Archive, unset and any other value are hard stops).
  Verify: `node tools/release_readiness.mjs --prepared P --db D --pieces p001` shows no `series` or `own_pool_not_series` blocker. Clear it in the Studio Release tab, Sort (issue #105).
- [ ] **2. Fully verified.** Every line of every version block of `p001` is confirmed or corrected by the author (38 reviews on the 2026-11-05 export: 22 on `diary1`, 16 on `diary62a`). An agent cannot satisfy this.
  Verify: no `verified` and no `stale_transcript:LINE` blocker in the same report. Clear it in the Studio Review tab.
- [ ] **3. Filed, or policy recorded.** Either a GRUW batch containing `p001` is `filed` or `registered`, or the author has recorded `gruw-policy` as exactly `skip` (the Studio honors that; issue #106 is the author's decision).
  Verify: no `filed` blocker. Copyright note: filing for unpublished works should happen *before* posting; once posted a work may no longer qualify as unpublished.
- [ ] **4. Version chosen.** The version to publish is the one the author means. By default it is the top of the stack, `p001-diary1-0`. The other version, `p001-diary62a-0`, carries five author corrections but also shares a page with unreleased `p126`, so it is not publishable by default.
  Verify: the readiness report shows which version the gate would publish and whether it is a decided final or just the top of the stack. Record a decision in the Studio Decisions tab if a final is wanted.
- [ ] **5. Shared scans resolved.** No other piece sits on the published page (and its facing page of the spread image) unless that exposure was ruled on by the author.
  Verify: no `shared_scan:*` blocker. Resolve by releasing the neighbour too or by the author's recorded acceptance; a flag alone is not evidence.
- [ ] **6. Exact output reviewed by the author.** Image exposure, embedded font metadata (family `ajp-scribbles`, title `versforms`), the information-panel wording ("not yet checked by the author" while `prov.verified` is false) and any visible metadata.
  Verify: the author's dated, attributable statement naming this version/output ([clearance contract](releases/release-clearance-contract.md), `author_clearance`). Historical approval of another output does not count.
- [ ] **7. Fresh evidence.** Prepared output and a fresh Studio database export made from the current source revision (changed input bytes invalidate earlier artifacts).
  Verify:
  ```sh
  python3 tools/check.py
  python3 studio-cf/prepare_publish.py --out /scratch/prepared   # private output
  node tools/release_readiness.mjs --prepared /scratch/prepared --db <fresh export dir> \
       --pieces p001 --require p001                              # exit 0 means releasable
  ```
  The report describes the export it was given, not the live database, so export again if in doubt.
- [ ] **8. Phone check plan.** A physical phone is available for the staging look in Part 2 (headless and emulated checks do not count).
- [ ] **9. Standing rules hold.** `noindex` stays ([noindex.md](noindex.md); removal is the author's separate decision). No AI-written creative or interpretive text is added anywhere in the presentation. The work is not ETCETER4: the output must not contain the name of the author's music project.

If any box is unticked, stop. Report which gate and which evidence is missing; do not route around it.

## Part 2. Posting steps (Studio path)

Only after Part 1 is fully ticked and the author says go. Performed by the author, or by an agent only if the author explicitly authorizes the act.

1. **Record the starting point.** Note the current production snapshot id, the current `data/j.json` size and its sha256, and the list of pieces served (today: `p001` only). This is the rollback reference.
   ```sh
   curl -sI https://versforms.pages.dev/ | grep -i x-robots-tag
   curl -s https://versforms.pages.dev/data/j.json | shasum -a 256
   ```
2. **Publish to staging.** In the Studio, publish the piece to `versforms-staging.pages.dev`. Staging binds only `versforms-staging`.
3. **Check staging.**
   - Page loads, HTTP 200, title is exactly `versforms`, font family `ajp-scribbles`.
   - `x-robots-tag: noindex` present and the `noindex` meta present.
   - `data/j.json` holds only the intended piece and version; no text from any other piece.
   - Only the intended scan images are reachable; unintended ones return 404.
   - Look at it on the **physical phone**: first paint, the single menu control, reading the piece, the information panel.
4. **Author confirms.** The author looks at staging and says to continue. Nothing proceeds on silence.
5. **Publish to production.** In the Studio, confirm production (`versforms.pages.dev`).
6. **Check production live.** Repeat the step 3 checks against `https://versforms.pages.dev`. Compare `data/j.json` with the staging file; they should match.
7. **Mark posted.** Studio, Release tab, "Mark posted": site `versforms.pages.dev`, account `vers.forms`, post URL if any. This is a record of what happened, not a permission. No social post is part of this runbook.
8. **Log it.** Add a record in `docs/chats/` and a row in `docs/chats/README.md` (see the repo `CLAUDE.md`), update `docs/plan.md` if the plan changed, and pass `python3 tools/check.py` before committing.

## Part 3. Rollback

Think of the three layers separately.

1. **Before production (staging only).** Nothing public happened. Re-publish staging from the previous prepared output, or leave it; staging is not the public reader.
2. **After production, undo the site change.** Re-publish production in the Studio from the previous snapshot recorded in step 1 of Part 2 (for a piece set that previously contained only `p001`, that is the prior `p001`-only snapshot). If the piece was new, publish the set without it. Then repeat the Part 2 step 3 checks on production and confirm the withdrawn piece's text and scans are gone from `data/j.json` and the image paths.
   *Gap, stated plainly:* the repository documents no one-click Studio "unpublish". The ledger shows production being re-published to a newer snapshot, so re-publishing a prior set is the expected mechanism, but confirm that in the Studio before relying on it, and note the result here.
3. **Fallback path only (`post_poem.py`).** If a post pull request was merged in `4444J99/versforms`: `git revert -m 1 <merge-commit>` for a merge commit, `git revert <commit>` for squash or rebase, on a new branch, via pull request. Never rewrite history or force-push. Also remove the piece id (and any `all_versions` entry) from `release/public.json` in this repository, or the next post restores it.
4. **Record, do not erase.** Withdrawal does not recall copies, caches or what a crawler already fetched; `noindex` is a request, not access control. Keep the exposure history: write a withdrawal event referencing the original publication rather than deleting it. Cancel any downstream scheduled posts that point at the withdrawn piece. Restore test databases from their own exports; never replay test posting records into live D1.
5. **If the Studio record says posted but the site does not:** trust the live fetch over the record; fix the record afterwards.

## Evidence trail

- Issue #113 and its 2026-11-16 status comment; [launch ledger](launch-ledger-2026-11-10.md); [release readiness](release-readiness.md); [T03 release procedure](releases/t03-release-procedure.md); [clearance contract](releases/release-clearance-contract.md); [posting.md](posting.md); [noindex.md](noindex.md).
- This runbook was written without running any Studio, Cloudflare or GitHub-public action. Gates 1 to 6 are the author's to confirm; the commands above are the checks to run, not results.
