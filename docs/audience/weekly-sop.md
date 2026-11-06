# Weekly audience SOP

**SOP:** `T06-WEEKLY-01` · **Version:** 1.0 proposal · **Owner:** Anthony · **Time zone:** `America/New_York` · **Cost ceiling:** $0 in new commitments.

This is an operational revision of #61's existing November 3 SOP, especially B0, B6, B8–B11 and B16. Its research and history remain intact in `claude/`. This version removes the unaccepted first-12-poems analytics mandate, routes release decisions through T03, and keeps every optional tool inactive. See [policy corrections](platform-policy.md), [decisions](decisions.md) and [clearance handoff](release-and-press.md).

## Roles and reusable inputs

Anthony chooses and clears the work and writes every caption, hashtag selection, alt text, bio, description and reply. T03 owns release eligibility, version selection, filing/exposure evidence, release numbering and the public builder. T07 supplies approved, provenance-preserving media derivatives and the media kit. T06 records logistics and distribution observations; it cannot infer literary quality, authorize posting or repair an image.

Use the existing studio and a private copy of [weekly-record-template.json](weekly-record-template.json). This record references canonical T03 and T07 receipts; it is not another release database. Keep identity and metrics metadata only. Do not copy unpublished poem text, Reserve lists, reader messages, credentials or contact lists into optional tools or public Git.

## One-page weekly procedure

| When | Action | Required record / stop condition |
|---|---|---|
| Before the weekly slot | Receive one T03-cleared piece/version with source revision, release number, destination, filing decision/evidence and exact approved media scope. Match T07 asset hashes to that clearance. | Missing, stale or ambiguous clearance means **HOLD**. Do not choose a convenient poem, use a force flag or infer approval from a preview. |
| Preparation, suggested 20–30 minutes | Anthony supplies caption, title/date presentation, hashtags and alt text. Check number against T03, asset dimensions against T07, frame order, phone legibility and all page margins/neighbors against clearance. | Copy text verbatim from author input. Record approval source/version privately. No AI public wording or generative image treatment. |
| Immediately before posting | Confirm visible destination is the approved `vers.forms` account, approved visibility, chosen slot and actual current UI limits. Verify files once more. | Wrong account, new asset hash, changed source, new fee or missing approval means **HOLD**. No default personal/ETCETER4 cross-post, Collab or connected-account action. |
| At the author-selected slot | Author posts manually only after current release authority exists. A site release, if included, is executed by the separately authorized T03 process. | Record actual local timestamp with UTC offset and time zone, version/asset IDs and public URL. No scheduled task or post is created by this SOP's preparation. |
| Immediately after | Author opens the live post once and checks visible image(s), order, number, caption, alt text, destination and link. | Record observed success or issue. A scheduled item, draft PR or local preview does not count as exposure. |
| Reply window and duration selected in D05 | Author reads and writes replies personally. Record only counts and next-action categories needed for operations. | No generated replies, automatic outreach, DMs copied to AI, or inferred promises to readers. Respect the chosen time limit; carry remaining work to the next window. |
| At +24 hours and +7 days, if D06 chooses the proposed weekly observation route | Record available native metrics and the exact observation window. End-of-week review may combine the +7-day snapshot with next preparation. | Record unavailable/hidden metrics as `null` with a reason. Do not pay for data history or invent numbers. Skip a missed window and record elapsed time. |
| Weekly review, suggested 15 minutes | Separate distribution, response and process. Choose at most one technical adjustment or one same-poem format comparison for an authorized later slot. | No poem ranking or quality conclusion from reach. No extra release number for a repeat of the same poem/version. |

One new poem per week is the recorded author cadence. Process/layer posts are optional and need their own clearance when they expose additional text, versions, recordings or scans. A missed week stays recorded as a missed week; rescheduling does not authorize a double release or a new first-post date.

## Observation definitions

| Field | Definition and limit |
|---|---|
| `observed_at`, `window_start`, `window_end`, `elapsed_hours` | ISO timestamps with offsets. Compare equal elapsed windows where possible. Record actual platform labels, because dashboard labels/availability may change. |
| `reach_accounts` | Native unique-account reach, if available. Keep separate from views/impressions, which may include repeat events. No substitution to make a rate computable. |
| `nonfollower_reach_accounts` / percentage | Native value and denominator exactly as provided. Do not infer a count from an unspecified percentage. |
| saves, shares, comments, post-attributed follows | Nonnegative event counts for this post and window, when available. They overlap; one person may create several events. Likes can be recorded separately but are not the primary diagnostic. |
| `response_events_per_100_reached` | `100 × (saves + shares + comments + post-attributed follows) / reach_accounts`, only when all four counts exist and reach is positive. This is an event rate, not a percentage of unique people; it can exceed 100. If any input is missing, leave it null. |
| `substantive_reader_responses` | Author-coded count of distinct responses that refer specifically to reading the work or ask a considered question. Do not infer sentiment/meaning with AI. No names or verbatim messages in the aggregate record. |
| `intensity_flag` | Only the rule selected in D06; report underlying counts. This is a signal to preserve reader contact/observe again, not a finding that a poem is better. |
| `operational_notes` | Format, legibility, missing fields, outage, changed timing, reshare, follower change or other confounder. Poem criticism belongs to the author in a separate private writing practice. |

Never add likes, saves and comments and call the total unique readers. Never turn unavailable Insights into zero reach. An account-level total cannot silently replace post-level data. DMs are excluded from automated data collection; an author may add a consent-respecting aggregate count manually.

## Weekly interpretation, with unresolved thresholds

Until D06 is accepted, record counts descriptively; no threshold classification is valid. The numeric examples in the register are planning options, not benchmarks for poetry accounts.

| Pattern after a chosen observation window | Permitted operational conclusion | Next action |
|---|---|---|
| Reach below chosen observation floor | Below the author-selected operational floor; keep observations descriptive under the selected rule. | Verify destination visibility, legibility and observed timing; retain cadence or propose a controlled format test. |
| Reach at/above floor, event rate below chosen floor | Recorded response events were low for the selected operational threshold; cause remains unknown. | Compare one packaging variable on the same poem/version. Do not rewrite or retire the poem on this evidence. |
| Author-coded responses or saves/shares meet chosen intensity rule | Some recorded responses deserve attention even if reach is low. | Author replies in the chosen window; preserve the format as a candidate for another observation. This flag can coexist with low reach. |
| Reach/response meet floors without intensity signal | No operational alarm under the chosen rule. | Continue; neither success nor artistic quality is established. |
| Missing data, changed clearance/version or incomparable windows | Inconclusive. | Correct the record or defer the comparison. |

## Controlled comparison using the same poem

1. Choose an **already cleared** poem/version. Reference its original release number, source hash and T03 receipt. Obtain approval for both exact media variants; new crops can reveal new writing and must not be assumed cleared.
2. T07 prepares two legible variants: for example one approved page image versus the same content split across an approved carousel. Choose **one format variable**. This is a whole-format comparison; slide count and physical text scale are inseparable consequences, so do not claim an isolated algorithm effect.
3. Keep poem text, source version, release number, destination account, author-supplied caption, hashtags, alt-text information, posting weekday/time and observation duration as constant as practical. Keep the author caption identical if its existing wording fits both; any author-required repeat notice is documented as a confounder, not silently changed.
4. Author schedules the comparison only after approving how it fits the weekly cadence. A repeat is not a second new poem. Do not create an extra series number, delete the first post, or publish an uncleared alternative version to obtain a cleaner experiment.
5. Collect both +24-hour and +7-day windows where D06 allows. Record order, calendar dates, follower changes, reshares, platform changes, any promotion (expected none) and missing metrics. Organic posts are not randomized experiments; equal slots cannot control who saw them.
6. Compare raw reach, raw response counts, event rates (only with valid denominators), and phone-legibility checks. If evidence is sparse or confounded, label the comparison inconclusive. At most choose the next format to try; do not declare a superior poem or a statistically established winner.

## Caption and reply inputs

The record contains slots for `author_copy.caption_ref`, `author_copy.hashtag_list`, `author_copy.alt_text_refs`, `author_copy.bio_ref` and `author_copy.project_description_ref`. References must identify an author-supplied version. There is no generated sample caption, hashtag wording, bio, project description or reply in this packet.

D07 chooses whether a fixed template includes number, author title/date, an optional author's end note or link. T03 supplies number/version facts; the author decides the words. The old 0–5 hashtag list is retained only as a bounded planning choice, subject to the verified account UI and current platform source.

## Accidental Reserve, private-page or unregistered exposure

The historical SOP's automatic delete/repost and automatic legal reclassification instructions are **not adopted**. D09 records the author's containment authority; the current T06 execution authorizes no external change.

1. Pause further distribution of the affected material. Record the URL, destination, exact observed media/version, first/last known visible time and who observed it; record uncertainty if first exposure time is unknown. Do not copy the offending scan to a public issue or send it to an optional tool.
2. Preserve the private source/version and evidence of exposure. Refer to the studio release document's `exposures[]`, canonical T03 receipt and `release_event_contract`; while Site/social semantics remain unresolved, record actual surface and event type explicitly in the sidecar until T03 resolves it.
3. Notify the author within the working session and follow only the containment action they have authorized. The prepared options are author-directed removal/hiding followed by verification, or holding while the author reviews. No action in this packet overrides the no-deletion/no-account-change boundaries.
4. T03 and the author assess filing/publication and target-journal eligibility from the actual exposure and current rules. Never silently mark the poem published, registered, retired or no longer Reserve. Removal does not prove that prior copies ceased to exist.
5. Record the authorized remedy, actual result and revised clearance. Resume only with a fresh release receipt; a correction does not automatically authorize a repost.

## Maintenance

At each use, recheck changed platform limits and the actual account's eligibility. At a monthly manual review, inspect linked-account/permission state if the author has adopted a tool. No recurring automation is installed. Keep historical decisions and source versions when replacing a policy; do not overwrite an old observation with a newer one.
