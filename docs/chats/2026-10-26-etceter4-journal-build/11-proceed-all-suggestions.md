# 11 · Build review studio, versions layer, font sheet, copyright prep, plan doc

| | |
|---|---|
| Chat | https://claude.ai/chat/137af404-03bc-4316-909d-46953fd70931 |
| Exchange | 11 of 12 · 2026-10-25 |
| Issue | #15 |

## Asked
The author said to proceed with all suggestions.

## Answered / produced
- Review studio published privately with db/user/assets capabilities (artifact `MVognnZQrtRQ6QCMaF7341`): line-by-line confirm/edit against scan crops, Decisions tab for open calls and 33 flagged pages, new-version photo inbox; save verified with a probe write/read/delete.
- `review_build/apply_reviews.py` (dry-run, backups) to write corrections into transcripts and `decisions.json`.
- Versions layer added to the merged piece (label "Versions layer"): 17 pieces as version stacks, swipe to peel back; `app_build/ingest_version.py` tested end to end on a synthetic phone photo (test version removed); `build.py` reads studio decisions.
- Font fill-in sheet `font/fillin/fillin_sheet.pdf` (Letter, A4 variant) with registration marks; `ingest_fillin.py` passed a simulated photo test into a separate test font.
- Copyright prep: checked current GRUW rules (copyright.gov); wrote `release/copyright/make_deposit.py` (one PDF per poem, refuses unverified pieces).
- Plan written to project doc `plan.md`, then updated as `claude/plan.md`.

## Author decisions
- Accepted all six of Claude's next-step suggestions.

## Plan
- **Claude**, done: Review studio, versions layer, font sheet, copyright script, plan doc
- **author**, open: Review transcripts in the studio (complete pieces first) and answer the Decisions tab
- **author**, open: Fill in and photograph the font sheet
- **author**, open: Real-iPhone test of the merged piece, including peeling a stack
- **author**, open: Provide name candidates; then check handle/domain availability
- **Claude suggestion**, open: Remove the folded transcriber-notes section from the studio if the author asks
