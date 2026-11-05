# Chat log

Every chat in the claude.ai Project **journal-handwritten-web** gets one record here: what it produced,
what the author decided, and its plan / next steps. Records are technical; no creative or interpretive
text about the poems belongs in this folder.

Conventions
- One file per chat: `YYYY-MM-DD-<slug>.md`, date = the chat's last activity (America/New_York).
- "Author decisions" holds only what Anthony stated. Claude's suggestions go under "Plan" and are labelled.
- Each record now has an Exchanges table: one document per exchange in `docs/chats/<record>/` and one GitHub issue each (#3–#72), made from the full transcripts on 2026-11-05.
  Correct a record by editing it in a new commit; history keeps the earlier wording.
- New chats: add a record before the session ends (see `CLAUDE.md` at the repo root).
- Per-exchange breakdown: each chat runs its prompt from `PROMPTS.md`, which follows `PROCESS.md` and writes `docs/chats/<record>/NN-*.md` plus one GitHub issue per exchange.

## Chats

| Date | Chat | Status |
|---|---|---|
| 2026-10-24 | [Release methods and standards](2026-10-24-release-methods-and-standards.md) | Superseded by the naming chats; name/handle claim still open. |
| 2026-10-26 | [Etceter4 journal (main build)](2026-10-26-etceter4-journal-build.md) | Open — the two feature proposals have not been built. |
| 2026-10-26 | [Footnotes and endnotes for poetry](2026-10-26-footnotes-and-endnotes.md) | Open — placement of notes undecided. |
| 2026-10-27 | [Review feedback and open questions](2026-10-27-review-feedback-and-open-questions.md) | Waiting on the author — no response to the report recorded. |
| 2026-10-27 | [Custom synthetic voice](2026-10-27-custom-synthetic-voice.md) | Open — spec delivered, no recording yet. |
| 2026-10-27 | [Product business model](2026-10-27-product-business-model.md) | Built; decisions open. |
| 2026-10-27 | [Repository build and deployment](2026-10-27-repository-build-and-deployment.md) | Partly open — tag missing, build folders missing. |
| 2026-10-27 | [Image upscaling methods](2026-10-27-image-upscaling-methods.md) | Open — offer not taken up. |
| 2026-10-27 | [Application feedback review (merged piece v4)](2026-10-27-application-feedback-review.md) | Open — repo copy of v4 outstanding. |
| 2026-10-28 | [Learning world scripts through poetry](2026-10-28-learning-world-scripts.md) | Research only; no build. |
| 2026-10-28 | [Generative atomic poetry system](2026-10-28-generative-atomic-poetry.md) | Research only; decisions open. |
| 2026-10-29 | [Generative audio from voice samples](2026-10-29-generative-audio-from-voice.md) | Open — waiting on the pilot recording. |
| 2026-10-31 | [Handle and title meaning](2026-10-31-handle-and-title-meaning.md) | Superseded — the account is now `vers.forms` (2026-11-04). |
| 2026-10-31 | [Poetry archive relaunch plan](2026-10-31-poetry-archive-relaunch-plan.md) | Partly superseded; GRUW question open. |
| 2026-10-31 | [Instagram short-form video content](2026-10-31-instagram-short-form-video.md) | Open — template not built. |
| 2026-11-03 | [Widget photo-page format ideas](2026-11-03-widget-photo-page-format.md) | Waiting on the author (clips). |
| 2026-11-03 | [Poetry release plan](2026-11-03-poetry-release-plan.md) | Open — participation and numbering undecided. |
| 2026-11-03 | [Fear of unseen posts](2026-11-03-fear-of-unseen-posts.md) | Open — Muse not configured. |
| 2026-11-03 | [Cipher puzzles and handwriting](2026-11-03-cipher-puzzles-and-handwriting.md) | Research only; decisions open. |
| 2026-11-03 | [Cut-up technique research report](2026-11-03-cut-up-technique-research.md) | Research only. |
| 2026-11-04 | [Profile picture edit](2026-11-04-profile-picture-edit.md) | Open — handle/domain checks outstanding. |
| 2026-11-05 | [Project advisory request](2026-11-05-project-advisory.md) | Open — this is the launch checklist. |
| 2026-11-05 | [Launch day: log every chat to the repository](2026-11-05-launch-day-chat-log.md) | In progress — Cloudflare link pending |

## Repository state (checked 2026-11-05)
- `main` at `957584e` (docs: record the repository in the plan).
- Tag `v2026.10.27` from the seeding chat is **not** on GitHub.
- CI check workflow runs (last success 2026-11-01).
- Open issue #1 and PR #2 (not from a chat) ("Fail integrity check when content files are missing from MANIFEST.sha256", opened 2026-10-28) — not from a Project chat; unreviewed.
- `site/index.html` predates merged-piece v4 (artifact `1Pcbgrvp7BqfmcYhzZLEss`).

## Launch list (consolidated from the open plans above)
Owner in brackets. Order follows the 2026-11-05 advisory.
1. [Claude] Copy merged-piece v4 `index.html` from the artifact into `site/`, refresh the manifest, commit, tag.
2. [Claude + author] Back up the scans and spreads outside the artifact store (R2 / Dropbox / local).
3. [author] Confirm the name (`vers.forms`); [Claude] check handle and domain availability.
4. [author] Verify the first poems in the review studio; sort them into Series.
5. [author] Decide GRUW: file one batch before posting, or post without (both were Claude suggestions; no decision yet).
6. [author] Pick poem 1 and the first-post date; [Claude] build the Instagram template from his material.
7. [author] Post.
