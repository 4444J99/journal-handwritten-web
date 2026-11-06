# 2026-11-06 — Launch code completion and live-state reconciliation

## Produced

Rechecked the live repositories instead of treating the transcript handoff as current state. The initial private baseline was `ef3d263c455788c769547df9e1e6010a54b7719a`; the public baseline was `1fe6b507b24bbe20ba0d45a917031f42cc171b58`. The public repository had no open PR or posting/probe branch. Its other branch, `blank-title-versforms` at `d66006bb34c384792170c737ba8d10c72ad9be42`, belongs to already-merged PR #1 and was retained.

- PR #131 had already merged the first posting-hardening follow-up at `7371dc394403fbcf09fd32bab563f1eb62ff3684`, followed by regression tests at `dac66e11d15cc5549edade39c2f8f9b7bc2fa566`. The old tests-first proposal therefore did not need a duplicate PR. This session independently rechecked the implementation and corrected remaining defects: `GIT_CONFIG` could hide a second push destination; failure cleanup could delete a branch created after preflight; Git mirror values such as `on` were accepted; and pushing permanently rewrote `push.followTags`. The follow-up isolates all repository-local Git environment variables, validates native Git boolean values, preserves pre-existing or concurrently moved branches, compares exact committed bytes under the clean environment, and disables tag-following for the push alone. Regression cases failed before the corrections and passed afterward.
- Recovered the final prototype work from remote `alive-prototype-wip-final` at `eece4f56ffaae81500aaf94fd18852b2038e06d6`, including the README correction. PR #102 was still draft at `2664d104c114099aac0f901f084554dea8d5c2a1`. The existing branch was fast-forwarded to that recovered commit, then advanced to `0561f712e0061db5317115097af72e874c9652d9` with README/comment precision corrections and verification evidence. PR #102 remains draft for source/visual review. Its 12-case p001 rendering matrix passed, and atoms rebuilt byte for byte; all 384 source image/data inputs matched this session's main baseline. The recovery is private prototype work; it does not change the source data decision in #121 or any design decision in #109.
- Fixed an additional Release-tab defect: Exposure accepted unsafe URL schemes and made them clickable. It now applies the same optional absolute HTTP(S) validation as Mark posted, preserves invalid form drafts without saving, and renders existing unsafe values as non-clickable historical records without rewriting them.
- Extended `tools/verify-release-studio.mjs` to verify source identity, use real touch emulation and isolated local D1/JWKS, and cover Calendar/Mark posted, Exposure, persisted saves/reloads, phone and desktop light/dark layouts, and refusal of a correctly signed unlisted email. The run blocks external requests and never touches the deployed database.
- Removed committed normal/diff3 merge markers from both plan files and the chat index. All 35 pre-existing unique chat links and all substantive plan content were retained. A narrow `tools/check.py` preflight now refuses unresolved markers in those three integration records, including before `--write`.

The Release browser run passed all 17 checks on local commit `8d4e6bd4a216e9564924a8a02ed29f951dec1b27` (tree `f7105fde4599ee6fdbdc306229582bc51ddc5f8e`). Its exact source hashes and scope are retained in [the acceptance receipt](../verification/launch-2026-11-06/release-acceptance.json). The initial local CI receipt reported success across 264 Python tests, 94 Node tests, 59 studio Python tests and 83 studio Node tests, but did not expose skipped counts: font-dependent posting coverage in that early run was incomplete because Brotli was missing. This session supplied a separate font runtime, reran the real font/posting cases and changed local CI to report skips in its console, JSON receipt and status description. The later marker check independently passed all 9 manifest tests. The completion PR records the final accepted head and final integrated test results; these earlier receipts are dated evidence, not assertions about an arbitrary later head.

### Final code verification

The published completion commit `2e02761e752aba6a57a2ddbc834493e9c2c93e01` has tree `24682eb3f7d2f93c03c1e94667ddecbfa7f59172`, identical to the independently reviewed local commit `a458298221b51c9a679e30586e00c3dbaf89da86`. Both object IDs were verified; the differing commit IDs reflect the GitHub-created commit metadata, not different source bytes.

On that exact clean published commit, all five local CI suites passed: **275 Python tests (2 skips), 94 Node passes, 59 studio Python tests (1 skip), and 83 studio Node passes**. The two absent-default-path fixture tests were then run explicitly against the recovered, hash-matching atoms and the committed 38-review PR #73 export; both passed without skips. The one remaining skip is the existing test of an interpreter without fontTools, because the installed interpreter already contains fontTools. Font-dependent posting tests ran with both fontTools and Brotli. See [CI](../verification/launch-2026-11-06/local-ci-published.json) and [supplement](../verification/launch-2026-11-06/local-ci-supplement.json).

All **17 Release browser checks** were rerun and passed on the exact published commit; see [acceptance](../verification/launch-2026-11-06/release-acceptance-published.json). Independent reviewers also passed 13 focused posting regressions and the separate post-commit concurrency reproducer. The final evidence-record commit changes only documentation and receipts; its PR records the final accepted head. Hosted acceptance is still distinct from these local results.

### PR #119 provenance

GitHub showed #119 already merged at **2026-11-06 16:13:38 UTC** (11:13:38 America/New_York), before this session wrote to GitHub. Accepted head: `aff12fbb91ba56aeb6b0f2aac08aed8a96593f82`; merge: `ef3d263c455788c769547df9e1e6010a54b7719a`; previous main: `4063ec2d1b91e18b0ce7bad6e8fec56a531f398a`. The original T03 work is recorded in [the T03 session](2026-11-05-t03-release-preparation.md), with original commits `e40f1a0`, `6d1ff59`, `8d16284` and later main integrations `968314f`, `aff12fb`.

The net merge added 95 files and modified three documentation files; it did not replace runtime code or delete files. GitHub attributes creation and merge to the shared `4444J99` account. That identifies the account, not the human or agent controlling it. No explicit owner keep/discard decision was found. The merge used two parents; this session did not perform that merge and does not relabel it as a squash. Existing history is retained.

### Live Cloudflare observations and limits

The live public page was blank, title `versforms`, with a `noindex` robots value, no images and no links. The deployed studio redirected to the Cloudflare Access email-code login. The Cloudflare dashboard required sign-in.

These observations establish the public blank/noindex page and the presence of an Access gate. They do not establish the current Pages runtime mode, D1/R2 bindings, owner-only policy, deployed revision, hosted save behavior, or rejection of a real second account. The 17 local browser checks must not be described as deployed acceptance. Physical iOS/Android behavior also remains unverified. Chromium 153 reset touch emulation after full-page screenshots; the final phone checks use viewport screenshots and assert that touch remains active.

### Sources that were not accessible

The original Claude lead transcript `b8493a96` and fork files under `/Volumes/Archive4T/Runtime/agents/claude/projects/-Volumes-Archive4T/` were not mounted here. The private shared memory packet `2026-10-16-v1.1`, sanitized projection `2026-10-16-v1.1-r2`, and its `interpretation.md`, `cloud-master-context.md` and individual ledger records were not accessible. The supplied handoff and accessible repository evidence were used as leads and checked independently. Unseen instructions, approvals and decisions were not inferred.

## Author decisions

The current request authorizes finishing open code work on branches and PRs, with the main session alone performing remote writes and squash merges guarded by the full expected head SHA. It retains the standing prohibitions on public poem selection, publishing, changing noindex, spending, creating accounts, destructive cleanup and recreating the missing original builders.

No new poem classification, GRUW decision, public name/date decision, prototype design choice, source-box correction, Access policy change or runtime-mode change was made. Earlier agent recommendations are preserved as recommendations.

## Plan / next steps

- Integrate the independently verified code fixes through the completion PR. PR #102 has been updated with the recovered final prototype and precise limitations. The PR bodies identify exact heads, validation and limits.
- Complete authenticated deployed-studio and Cloudflare acceptance when a signed-in session is available. Saving must preserve the author's real state; a local fixture is not permission to mark a live poem posted or sort it.
- Keep the owner register below intact. Any future first post needs the author's specific content and timing decisions, plus the unresolved release gates.

| Issue | Verified subject / disposition |
|---|---|
| #104 | Owner changes the studio Pages runtime to Fail closed. Still open; current dashboard value unverified. |
| #105 | Owner sorts p001–p010 into Series / Reserve / Archive. Still open. |
| #106 | Owner decides GRUW filing before the first post or posting without it. Still open; a fork's recommendation is not a decision. |
| #107 | Missing original rebuild scripts: supply them or explicitly authorize a rewrite. Still open; no replacements written. |
| #108 | Three posting questions: page identifiers, font description records, and the verification sentence in the info panel. Still open. |
| #109 | Six alive-prototype design questions. Still open; the bounded scan-only prototype does not depend on them. |
| #110 | Optional font fill-in sheet photos. GitHub says closed at 2026-11-06 15:19:10 UTC; no accompanying evidence of receipt or ingestion was found, so fulfillment remains unverified. |
| #111 | Actions billing lock. Still open; local CI supplies execution evidence. A GitHub `local-ci` status could not be posted from this environment because authenticated `gh` is unavailable. |
| #112 | Polling deliberately deferred. Still open; not activated. |
| #113 | First-post p001 runbook. Still open; content clearance and date remain with the owner. |
| #121 | diary1 block 2: four lines versus three boxes. Still open; no source-data correction chosen. |

Removing noindex, confirming the first-post date/name, public Reserve exclusion and release clearance remain owner gates. The public repository and live data were not altered by this code-verification work.

## Status

The code changes are verified and recorded in the completion PR; #102 has been updated without rewriting its history. See the PR bodies for accepted heads and integration state. Hosted acceptance remains blocked by authentication at the time of this record. This is not a claim that the full launch or deployed save checks have passed. The public site still contains no posted poems in the observed state.
