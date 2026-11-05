# Working in this repository

This repository is the source of record for the claude.ai Project **journal-handwritten-web**.

## Every session logs itself
Before a session that touches this project ends, add or update its record in `docs/chats/`:
- One file per chat: `docs/chats/YYYY-MM-DD-<slug>.md` (date = last activity, America/New_York),
  using the same sections as the existing records: Produced, Author decisions, Plan / next steps, Status.
- Add a row to the table in `docs/chats/README.md`.
- "Author decisions" holds only what the author stated. Claude's suggestions go under "Plan", labelled as suggestions.
- If the session changed the plan, also update `docs/plan.md` (and the Project doc `claude/plan.md`).

## Standing rules (author)
- No AI-written creative or interpretive text in any presentation. Technical writing (docs, READMEs) may be AI-written.
- Presentation interfaces show the work alone; menus and text hidden until tapped.
- This work is not ETCETER4 (his music).

## Checks
- `python3 tools/check.py` must pass before committing; after an intended content change, `python3 tools/check.py --write`.
