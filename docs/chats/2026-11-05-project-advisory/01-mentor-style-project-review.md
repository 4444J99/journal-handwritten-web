# 01 · Mentor-style project review

| | |
|---|---|
| Chat | https://claude.ai/chat/fa895241-d28c-4ce0-b51f-5163f8b202fb |
| Exchange | 01 of 2 · 2026-11-03 |
| Issue | #71 |

## Asked
The author asked Claude to answer as an expert who has already shipped a project like this one: what is missing, what he has not considered, what the blockers are — a full top-to-bottom advisory review.

## Answered / produced
- Read two project memory files (journal release plan, social-presence plan) for context. No files, artifacts or commits produced.
- A 14-point advisory, in order of priority:
  1. Main blocker is starting; open items should not be launch preconditions. Suggested posting within ten days.
  2. Verification is at 0 of 123 pages (306 uncertain readings) and the physical book is unavailable, so the 2015 scans are now the originals: back them up three ways (R2, Dropbox, local); verify only the next five poems.
  3. Scope covers several products (weekly poem + apparatus, version-stacked web piece, font, synthetic voice, ambience, Instagram template, participation, glyph phase, app). Suggested shipping the poem weekly and letting apparatus accrue, with its completeness shown on the site; voice deferred to 2027.
  4. The Reserve (15–30 strongest poems held for journals) conflicts with his stated position on gatekeepers; cut to 5–6, made of new poems.
  5. Copyright registration should not gate launch: file one GRUW batch (~$85) for the first ten and post while pending (flagged as not legal advice; verify current rules).
  6. Settle the name in one session: check handles across platforms, domain and a USPTO search; move the site off etceter4 before links accumulate.
  7. No audience plan: build a seed list of personal contacts, message them directly for poem 1; add an email signup (e.g. Buttondown/Substack) from day one. Positioning: lead with the handwritten, versioned archive.
  8. Make the kinetic Instagram story a reusable template (Remotion, p5 export or Keynote) so each takes ~10 minutes.
  9. Privacy: one rule everywhere — real people get initials or changed names unless they agreed; decide how raw present-day reflections may be.
  10. Use the Fall 2027 doctoral application deadlines as the forcing function; a live site with several poems is a stronger portfolio piece.
  11. Defer participation until after poem 20; when built it needs a contributor license, moderation, attribution and provenance labels.
  12. Technical debt: copy v4 from the artifact into the repo (`site/index.html` is stale); locate local build folders and commit the generators; move hosting to Cloudflare Pages (private-repo Pages/Actions limits); export the studio review database to the repo on a schedule; put the transcription in the page as text for search and accessibility.
  13. Define success metrics before poem 1 (example targets by poem 25/40/50).
  14. Number poems as posted, not fixed in advance; sort only the first ten into Series now.
- Week-one list: back up scans three ways; copy v4 into the repo; pick and claim the name; verify five poems; email field; Instagram template; file one GRUW batch; post poem 1 with a personal-profile message and direct messages.
- Offered to turn the advice into a doc beside `plan.md`.

## Author decisions
None. The content is Claude's advice; the author did not accept or reject any item in this chat.

## Plan
- **Claude suggestion** — back up the scans in three places (R2, Dropbox, local). **open**
- **Claude suggestion** — copy v4 from the artifact into the repo and commit. **open**
- **Claude suggestion** — locate the local build folders and commit the generator scripts. **open**
- **Claude suggestion** — pick the name and claim handles + domain in one sitting; move the site off etceter4. **open**
- **Claude suggestion** — verify the transcription of the first five poems to post. **open**
- **Claude suggestion** — add an email signup to the site. **open**
- **Claude suggestion** — build a reusable Instagram story template. **open**
- **Claude suggestion** — file one GRUW copyright batch for the first ten poems. **open**
- **Claude suggestion** — post poem 1 with a personal-profile message and direct messages to a seed list. **open**
- **Claude suggestion** — shrink the Reserve to 5–6 new poems. **open**
- **Claude suggestion** — number as posted; sort only the first ten into Series. **open**
- **Claude suggestion** — move hosting to Cloudflare Pages. **open**
- **Claude suggestion** — export the studio review database to the repo regularly. **open**
- **Claude suggestion** — include transcriptions as page text for search and accessibility. **open**
- **Claude suggestion** — set a privacy rule for real people (initials unless consent). **open**
- **Claude suggestion** — define success metrics before poem 1. **open**


_Update 2026-11-05 (launch-day chat): merged-piece v4 copied into `site/` (commit 2744d7a); public site split to `4444J99/versforms`, Cloudflare Pages link in progress._
