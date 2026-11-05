# Per-chat breakdown: exchange documents, plan, issues

Run inside each claude.ai chat of the Project **journal-handwritten-web**, using the prompt for that
chat in `docs/chats/PROMPTS.md`. The chat works through its own conversation, one exchange at a time
(one author message + Claude's reply = one exchange), and writes into this repository,
`4444J99/journal-handwritten-web` (private).

## Output per chat
```
docs/chats/<record>.md                     existing record — update its Plan / next steps and Status
docs/chats/<record>/                       new folder, same name as the record without .md
  NN-<slug>.md                             one document per exchange, NN = 01, 02, … in order
```

## Exchange document (`NN-<slug>.md`)
```
# NN · <short technical title>

| | |
|---|---|
| Chat | <chat URL> |
| Exchange | NN of N · <date of the author's message, America/New_York> |
| Issue | #<number> (or "draft — see below" if creation failed) |

## Asked
What the author asked, in plain words. His own words may be quoted briefly.

## Answered / produced
What Claude answered or made: files, artifacts (with ids), reports, commits, links.

## Author decisions
Only what the author stated in this exchange. "None" if none.

## Plan
Next steps from this exchange. Mark each as **author**, **Claude**, or **Claude suggestion**,
and as **open** or **done** (done = later exchanges, the repo or the plan show it happened).
```

## GitHub issue — one per exchange
- Title: `[<record slug>] NN · <short technical title>`
- Body: link to the exchange document, then the Plan checklist (`- [ ] …` open, `- [x] …` done).
- Labels: `chat`, and `author` when any open step is his. Create a label if it does not exist.
- Before creating, search open and closed issues for the same title; update instead of duplicating.
- If every step is done or the exchange had nothing to act on, create it and close it as completed,
  so every exchange has an issue.
- If the session cannot create issues, write the issue text to
  `docs/chats/<record>/issues-draft.md` and say so in the reply.

## Rules
- Technical writing only. No creative or interpretive text about the poems; never draft lines, titles,
  captions, clues or notes for the work.
- Never reproduce copied passages from the journal or other copyrighted text. Cite by source and
  opening words, as the archive does.
- Real people other than the author: initials only. Flagged/private pages: page id only, no content.
- "Author decisions" holds only what he said. A Claude suggestion he answered with "sounds good" is
  "author accepted <gist>", not his decision on each detail.
- Don't change anything outside this chat's own folder and record, except one row in
  `docs/chats/README.md` if the status changed.
- Before pushing: `git pull --rebase origin main`; other chats push to the same repo. Retry once on conflict.
- Commit message: `docs(chats): <record slug> — exchanges, plan, issues`.
- End with a short reply: number of exchanges, documents written, issues created/updated (numbers),
  anything that failed.
