# T06 release-consumer and later press handoff

Prepared review handoff within the T06 identity and audience packet. Refreshed against accessible repository evidence on **2026-11-06 UTC**, following the **2026-11-05 America/New_York review baseline**. This document prepares private operational work; it grants no release, scheduling, account, spending, or outreach authority.

## 1. Verified state and limits

| Item | Observed status | Operational consequence |
|---|---|---|
| Repository `main` | `fab6a82b72f23efb16278b90cdc4f7790ca55713`, commit timestamp `2026-11-06T00:14:04Z`; tree `7f90d151f089596c9bd4da4f13652927fe154f7d`. Includes #122 documentation close-out. [S1] | T06 must be reconciled against this live base, rather than the earlier November 5 planning head. |
| Posting implementation #101 | Merged `2026-11-06T00:05:01Z` (November 5, 19:05 America/New_York), accepted head `15cad30cb923161716be51b2d075a6b98062cad4`, merge commit `06dccc0af91e563dc15e70d436569b7fe0cf9cba`. [S2] | Implementation is merged. A merge is not author clearance for a poem, asset, or press submission. |
| T03 packet #119 | Open draft, head `8d16284ba8b80f18398d08b8de931d8812f30429`; still stacked on `post-poem-gates` at `e5ae157ef556690e73047e30225cad61c5484cf9`. [S3] | Consume its explicitly proposed contract as a review interface; do not imply it is merged or constitutes a cleared release. |
| T03 verification | Receipt applies to code `6d1ff59fb6763f80828478e7819d9d879dd700e3` and the documented input/output hashes. Its docs head is `8d16284…`; later #101 and main changes are outside that receipt. [S4] | T03/integration owners must reconcile and rerun the appropriate acceptance work on the accepted stack before execution. T06 does not duplicate that gate or transfer old test results to new code. |
| #43 | Open, no assignees, zero issue comments observed. Archived exchange establishes the author's interest in press/critical attention. [S5, S6] | A later press preparation milestone is appropriate. Its date, framing, copy, targets, and outreach remain unapproved. |
| T07 media kit | No actual T07 media-kit manifest or production receipt was located in the bounded accessible repository/PR searches used for this draft. T03 contains consumer references to T07. | Do not label the kit ready or infer that it does not exist elsewhere. Use the finite intake below, and let T07 supply or identify its existing work. |

The shared packet `2026-10-16-v1.1` and projection `2026-10-16-v1.1-r2` in private project `g-p-6a10bcb4ada4819194e881431212101a` were inaccessible. No claim here is attributed to their unseen contents. The archived repository transcript is accessible evidence; its original private-chat link is provenance, not evidence that the private conversation was independently retrieved. Historical approvals do not authorize new actions.

## 2. T06 consumes the T03 contract

The existing interface is **`versforms.release-clearance.v1`**, documented in `docs/releases/release-clearance-contract.md`. It is a proposed interface for review. T06 should keep a reference to the canonical release record and its accepted revision, rather than introduce a second release database, duplicate clearance rules, or infer approval from a calendar entry. [S7]

| Canonical fields | What T06 needs from the owning workflow |
|---|---|
| `source_revision`, `builder_revision`, `reader_revision`, `input_manifest` | Exact accepted OIDs, code/input hashes, and a fresh T01 export of the six collections `reviews`, `decisions`, `versions`, `release`, `batches`, and `rconfig`. Recovered originals, preserved outputs, and reconstructed sources remain distinct. |
| `pieces[].piece_id`, `pieces[].versions[]`, `reviews` | Stable piece IDs and exact approved versions/source pages/block-line IDs. Display position, `n/100`, the last version, or a default selected version does not establish authority. Stale review inputs require reconciliation. |
| `pool_clearance`, `shared_scan_resolution`, `exposure_manifest` | Author decisions for all affected Series/Reserve/Archive material and every output byte. Include adjacent writing, facing pages, scan tiers, thumbnails, atlases, Hand/Font plates, metadata, and withheld identifiers. A visual crop alone does not prove byte exclusion. |
| `batch_workflow`, `filing_evidence` | The author's filed-versus-registered decision and exact supporting batch/version/deposit evidence. A string saying “filed” or “registered” is not a substitute for the record required by T03. T06 does not judge legal adequacy. |
| `identity_metadata` | Public title `versforms`, font name `ajp-scribbles`, and the exact approved description/reader wording/noindex configuration of the release. These technical identifiers do not supply author-written promotional copy. |
| `acceptance_receipt`, `author_clearance` | Current code/input/output hashes and required test evidence, plus a dated attributable author statement naming this specific output and its limits. Preserve any physical-device or deployed-header checks that remain separate gates. |
| `release_event_contract` | Agreed event fields, channel/type/URL/account semantics, version/output references, provenance, and publication classification. UI choices such as site/social are not automatically stored-event fields or legal conclusions. |
| `rollback_record` | Prior public commit/output, private whitelist, prepared revert, exposure history, and cancellation of downstream distribution. Withdrawal cannot promise recall of downloaded or cached copies. |

At the recorded T03 head, the packet is **`awaiting-author-and-evidence`**. Candidate `p001` and version `p001-diary1-0` are derived from recorded journal-page order; the whitelist change is unapplied. `author_clearance`, `filing_evidence`, `shared_scan_resolution`, `withheld_metadata_clearance`, and `first_confirmed_post_date` are null. `may_publish` and `may_schedule_external_actions` are false. The packet retains a seven-day cadence and does not set the first posting date. [S8]

The bounded preview passed the documented text/version and catalogued image exclusion checks, but **`complete_technical_exclusion` is false**: 13 withheld PALHF page identifiers/block structures remain in the inspected index. T03 requires an author ruling or an appropriate builder/reader change and renewed verification. Its private all-versions comparison contains withheld writing and is outside the proposed public output manifest. The whole packet is therefore not a deployable media kit. [S4, S7, S8]

The recorded real-data dry run exited **3** with no released documents. This is a hard stop, not a successful future release. T03 distinguishes forceable workflow failures from hard errors; neither a successful build nor `--force` nor `--accept-shared-scan` supplies author permission. [S4, S7]

One execution finding also needs T03 reconciliation: review `5793330932` / discussion `4487062599` identified multiple push-URL handling. The inspected #101 head calls `git remote get-url --push origin` without `--all`; the T06 integration audit observed the same call at current main `fab6a82…`. The merge alone must not be reported as resolving that finding. T06 adds no publishing code and does not independently certify actual push behavior. [S9]

**Later ownership refresh:** [issue #123](https://github.com/4444J99/journal-handwritten-web/issues/123) and merged [PR #124](https://github.com/4444J99/journal-handwritten-web/pull/124) now record the post-merge findings and existing `post-poem-hardening-wip` implementation work. That ownership remains intact; T03 should consume its accepted result. T06 has not rerun those adversarial tests. Main `038d01fb1862f2e569d231b5b3c4c3a4eb1aecda` changes only the other session's launch record, with no overlap in this packet. Earlier observations above remain dated evidence.

### Adapter for one future cleared release

1. **Prepare privately.** Reference an identified candidate, canonical T03 record, exact source revision, and existing T07 asset work. A private draft may carry pending fields; it must be clearly marked ineligible for external scheduling or publication.
2. **Receive the release receipt.** The owning release workflow supplies the completed canonical fields, specific author clearance, current acceptance, and current execution authority. Any unresolved required field remains a blocker. T06 records the receipt locator and hashes, rather than copying a second set of release logic.
3. **Receive T07 outputs.** Match every derivative to the approved version and exposure bounds. If a crop, full scan, screenshot, font specimen, avatar, or press rendition adds material absent from the cleared output, obtain the owning workflow's review and any needed renewed clearance before external use.
4. **Attach author copy.** The author supplies captions, hashtags, bios, project descriptions, press text, replies, and expressive alt text. T06 may check presence, links, character limits, and asset/copy pairing. It must not fill missing creative text.
5. **Fill the audience slot.** Use the subsequently selected weekly America/New_York slot and reply window. The SOP may hold a proposed private slot; no external queue is created under this task. Press timing is a separate optional milestone.
6. **Record actual execution only after later authorization.** When the responsible operator performs a separately authorized release, preserve actual URL, account, time, channel, and the approved output/version reference using the agreed `release_event_contract`. Do not record a proposed or scheduled action as completed exposure.
7. **Observe and reconcile.** Distribution/reply observations refer to the published output and remain separate from judgments of poem quality. Changed text, versions, reviews, pools, source pages, deposits, scan/atlas/font/reader content, whitelist, or output hashes invalidate the relevant receipt and return to the owning release workflow. Accidental exposure follows its rollback/history contract, with downstream cancellation, rather than inventing a T06 deletion-only procedure.

No automation is activated by this adapter. No account configuration, publication, external message, filing, or purchase is implied.

## 3. #43: a later press milestone with concrete entry criteria

The author's archived request distinguishes **people writing about the project** from a journal publishing a poem. That is the supported direction. The assistant's suggested press hooks, possible coverage beats, a first-month description exercise, and poem-10/25 timing are proposals. They must not appear as author-approved positioning or an agreed schedule. [S5, S6]

**Proposed milestone:** prepare a small, source-checked target sheet and an internally reviewable press packet after at least one specifically cleared public release exists and the author supplies the description. The author may choose an earlier or later readiness point. Poem 10 or 25 can be optional review reminders; neither is a prerequisite or commitment.

### Target criteria and required research fields

| Criterion | Evidence needed before a target is eligible | Consequence if absent |
|---|---|---|
| Demonstrated editorial fit | One or two dated examples of the outlet's own coverage of living poetry projects, digital literature, handwriting/type, archives, or relevant artistic practice. These are search categories, not approved project framing. | Keep as an unqualified lead; do not invent a fit claim. |
| Coverage of an existing public project | Current primary guidance or editorial examples showing suitability for project coverage, interview, review, or process reporting. | Distinguish an editorial pitch from a poem submission. Check any journal's own current prior-publication rules separately; do not generalize across venues. |
| Working submission route | Current official pitch/contact page, named department/role where stated, accepted formats, and any length or attachment limits; record URL and check date. | No guessed email addresses or unsolicited routing to unrelated staff. |
| No-spend compatibility | No required submission, placement, membership, advertorial, or asset-hosting fee for the proposed route. | Exclude or mark blocked under the existing no-spend constraint; do not purchase access. |
| Evidence and rights fit | Outlet requirements can be met using specifically cleared media and author-provided copy; requested reproductions are within approved limits. | Seek a smaller asset request or hold the target. No Reserve/unregistered material, full-scan exception, or extra reproduction right is inferred. |
| Author relevance and capacity | The author selects interest/priority and whether an interview or follow-up is feasible within the agreed reply window. | Keep the target as an option. The existence of a target sheet creates no outreach obligation. |

A practical proposed first pass is **three to five qualified targets**, each with: outlet; beat; coverage evidence URL/date; official route URL/check date; desired coverage form; required assets/copy; fee status; author priority; and next permitted action. This is a bounded research default, not an author decision. No named outlet is represented as currently verified by this draft, and no messages are sent.

## 4. T07 media-kit intake: finite assets, provenance, and acceptance

T07 owns production exports and its media-kit manifest. T06 consumes those outputs. This draft does not regenerate the avatar, substitute a new design, rename the font, create a competing kit, or draw from ETCETER4 materials.

| Asset request to T07 | Required inputs / acceptance | Current state |
|---|---|---|
| Existing avatar v2 and approved derivatives | Source artifact locator, original author/producer and date, source hash where retrievable, preview references, explicit arm-treatment decision, approved crop/background/export list. Identify an inaccessible original by its precise known locator; label a recovered preview as a preview. | Existing recovery/provenance work belongs to the T06 avatar handoff; production acceptance remains subject to the unresolved treatment decision and actual available sources. No substitute generated here. |
| One cleared poem's press/distribution assets | Exact piece/version IDs and canonical release receipt; approved rendition/crop/full-scan bounds; no additional adjacent or withheld content; output file hashes and dimensions. | No cleared release in the inspected T03 packet. Await the canonical receipt, then T07 exports. |
| Reader/site screenshots | Accepted reader revision and output manifest; author-approved visible text; exact viewport and capture date; screens exclude private controls, withholding leaks, and uncleared works. | May be drafted privately from a candidate, but no public-ready screenshot is certified here. |
| Font specimen, only if selected | Correct `ajp-scribbles` name, accepted font file/hash and metadata, cleared sample text, author-approved specimen wording. Font distribution/reuse must follow the actual agreed scope. | Optional; do not reuse historically named ETCETER4 font artifacts as though renamed or approved. |
| Author portrait, only if supplied/selected | Existing author-supplied asset and permission/credit instructions; exact chosen crop/export. | Optional input, not a request to synthesize a portrait. |
| Kit index and credits | Manifest linking exact outputs, source provenance, approval/receipt references, approved credit/attribution and reuse limits, and designated contact once chosen. | No accessible completed T07 kit receipt located. Request its existing locator or deliver these rows as intake. |

For each supplied asset, intake records **path/URL, SHA-256, byte size, format, dimensions, source artifact, piece/version where relevant, production revision, approval locator, permitted uses, credit, and author-supplied alt/caption text**. Missing author approval is a pending field; it is not filled with a derived default. Accessibility text can be checked for coverage and technical correctness, but author-owned expression stays with the author.

## 5. Author-copy placeholders and decisions

These are empty inputs, not drafted promotional language:

| Placeholder | Required author input | Used for |
|---|---|---|
| `[AUTHOR_PROJECT_DESCRIPTION]` | Project description in the author's own words; optional short/long variants if the author chooses. | Kit, target-fit review, any later pitch. |
| `[AUTHOR_BIO]` | Selected public name and bio, with facts the author is willing to publish. | Media-kit biographical field. |
| `[AUTHOR_PRESS_NOTE]` | What the author wants a particular outlet to understand, why contact it now, and any requested coverage form. | Later outlet-specific draft, only after that work is authorized. |
| `[AUTHOR_CAPTION]` / `[AUTHOR_HASHTAGS]` | The selected poem's exact caption and hashtag template/instance. | Distribution asset pairing. |
| `[AUTHOR_ALT_TEXT]` / `[AUTHOR_CREDITS]` | Accessible description and approved source/producer credit for each asset. | Kit and eventual posting interface. |
| `[AUTHOR_QUOTE_OR_INTERVIEW_LIMITS]` | Optional quotation, interview availability, subjects/uses the author approves. | Optional press follow-up. |
| `[AUTHOR_CONTACT_ROUTE]` | Chosen public contact address/route after account/email separation decisions. | Kit contact field; no guessed address or account linking. |

The integrated T06 decision register should hold the account/email/contact selection, whether full scans are permitted for a particular output, caption/hashtag template, weekly slot/reply capacity, and optional press milestone. T03 retains release/clearance decisions; T07 retains asset production. Do not duplicate these as a second set of author approvals.

## 6. Disposition and residual dependencies

**#43 — preparation completed in this draft; milestone proposed; execution unresolved.** The task now has concrete entry criteria, target qualification fields, asset intake, author-copy placeholders, and release/production interfaces. The issue should remain open pending author choices and the later authorized milestone. No closure, pitch, submission, purchase, or press announcement occurs.

**T03 — consumed, not replaced.** Remaining dependencies include current-stack acceptance; the existing pool/version/filing/shared-scan/withheld-metadata decisions; physical-device or deployed checks still required by the accepted contract; event semantics; and the unresolved execution finding noted above. T06 must not declare a release ready while the canonical record is blocked.

**T07 — handoff prepared; kit availability and export acceptance unresolved.** A bounded search did not locate a finished kit. The intake identifies what is required and preserves ownership, avatar provenance, and the arm-treatment decision. The producer can satisfy it with existing artifacts; recreation is not authorized by absence from this search.

**Superseded assumptions:** #101 is no longer an open implementation dependency; it is merged. An older T03 acceptance receipt still does not cover the later integrated code. Assistant-suggested poem-10/25 press timing is not an accepted author choice. Neither a private preview nor a build/test pass is a press-ready release.

## Source register

All sources below are accessible repository evidence unless expressly identified as a source gap. Source IDs in this section map to the immutable locators below; the consolidated [source register](source-register.json) also records the review observations.

- **S1 — live base:** [commit `fab6a82b72f23efb16278b90cdc4f7790ca55713`](https://github.com/4444J99/journal-handwritten-web/commit/fab6a82b72f23efb16278b90cdc4f7790ca55713), independently read through the GitHub API; [#122](https://github.com/4444J99/journal-handwritten-web/pull/122) close-out is included in that commit.
- **S2 — merged implementation:** [PR #101](https://github.com/4444J99/journal-handwritten-web/pull/101), live PR metadata read; accepted head `15cad30cb923161716be51b2d075a6b98062cad4`, merge `06dccc0af91e563dc15e70d436569b7fe0cf9cba`.
- **S3 — T03 review packet:** [PR #119](https://github.com/4444J99/journal-handwritten-web/pull/119), live metadata read; head `8d16284ba8b80f18398d08b8de931d8812f30429`, base `e5ae157ef556690e73047e30225cad61c5484cf9`.
- **S4 — revision-bound verification:** [T03 verification receipt](https://github.com/4444J99/journal-handwritten-web/blob/8d16284ba8b80f18398d08b8de931d8812f30429/docs/verification/t03-release-verification.md) and [integrator handoff](https://github.com/4444J99/journal-handwritten-web/blob/8d16284ba8b80f18398d08b8de931d8812f30429/docs/releases/t03-integrator-handoff.md); test-code revision `6d1ff59fb6763f80828478e7819d9d879dd700e3`. Tests are reported by the T03 receipt, not rerun by this research task.
- **S5 — scoped press issue:** [issue #43](https://github.com/4444J99/journal-handwritten-web/issues/43), created/updated `2026-11-05T16:54:33Z`, open, comments endpoint returned zero comments at review.
- **S6 — author/assistant exchange:** [2026-10-31, exchange 04, Press versus journals](https://github.com/4444J99/journal-handwritten-web/blob/d74df372ace00c8a7544ab3b5302cb05418d672c/docs/chats/2026-10-31-poetry-archive-relaunch-plan/04-press-versus-journals.md), blob `af91f1c1dde26848466f14ab5df1057ef3009131`. Original transcript provenance points to `https://claude.ai/chat/c10a57af-55de-43c7-8c3b-a18e6d171dc5`; private original not independently retrieved here.
- **S7 — canonical interface and procedure:** [release-clearance-contract.md](https://github.com/4444J99/journal-handwritten-web/blob/8d16284ba8b80f18398d08b8de931d8812f30429/docs/releases/release-clearance-contract.md), [t03-release-procedure.md](https://github.com/4444J99/journal-handwritten-web/blob/8d16284ba8b80f18398d08b8de931d8812f30429/docs/releases/t03-release-procedure.md), and [t03-author-decisions.md](https://github.com/4444J99/journal-handwritten-web/blob/8d16284ba8b80f18398d08b8de931d8812f30429/docs/releases/t03-author-decisions.md).
- **S8 — specific pending packet:** [packet.json](https://github.com/4444J99/journal-handwritten-web/blob/8d16284ba8b80f18398d08b8de931d8812f30429/release/packets/2026-11-05-t03-current/packet.json), private-review output inventory and status; do not publish the directory as a kit.
- **S9 — unresolved execution reconciliation:** [review `5793330932`](https://github.com/4444J99/journal-handwritten-web/pull/101#pullrequestreview-5793330932), [discussion `4487062599`](https://github.com/4444J99/journal-handwritten-web/pull/101#discussion_r4487062599), and [accepted-head posting code](https://github.com/4444J99/journal-handwritten-web/blob/15cad30cb923161716be51b2d075a6b98062cad4/tools/post_poem.py). The accepted-head call and current-main continuation were independently inspected during T06; actual remote push behavior was not exercised.
- **S10 — repository instructions:** `CLAUDE.md` read from the accessible checkout before drafting. Author/AI role boundary, dated chat logging, existing plan ownership, and ETCETER4 separation apply. The T06 branch includes the required log and plan addenda.
