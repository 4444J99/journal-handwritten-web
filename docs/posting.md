# Posting a poem

`tools/post_poem.py` turns "post a poem" into one small, reviewable action. It checks the poem, builds the public site for it, commits that to a branch of the public repository (`4444J99/versforms`) and opens a pull request. It never merges. Technical document; it contains no editorial content.

## Prerequisites

- Python 3 with Pillow (the standard library is otherwise enough). `git`; `gh` (signed in) for the pull request.
- A studio database export: one JSON file per document at `EXPORT_DIR/COLLECTION/DOCID.json` for the collections `reviews`, `decisions`, `versions`, `release`, `batches`, `rconfig` (the format of the 2026-11-05 export, `exports/studio-db-2026-11-05/`). A collection with no documents may have no folder. `--db` also accepts the directory that contains `exports/<name>/`.
- A clone of `4444J99/versforms` (the public repository), clean, on `main`, level with `origin/main`. Do not use it for anything else while a post is open.
- The piece must exist in `site/data/j.json` (ids `p001` to `p126`).

## The command

```
python3 tools/post_poem.py PIECE_ID [PIECE_ID ...] --db EXPORT_DIR --public-repo PATH [options]
```

| Option | Effect |
|---|---|
| `--dry-run` | Runs every gate and hard stop, builds into the scratch directory, prints the file list and sizes. Writes nothing in the public repository, pushes nothing, leaves `release/public.json` alone. `--public-repo` is optional (without it the repository checks are skipped). |
| `--no-pr` | Commits the branch in the public clone but does not push or open a pull request. |
| `--force` | Overrides the three gates only (exit code 2 becomes a warning). Never overrides a hard stop. |
| `--include-versions` | Publishes the whole version stack. Needs the author's approval; the script says so. |
| `--accept-shared-scan IDS` | Comma separated ids of co-resident pieces (or "other lines" items) whose writing may show in a shared scan. |
| `--accept-embedded-font` | Accepts that `index.html` embeds a downloadable font whose name becomes public. Required for a real run. |
| `--workdir DIR` | Scratch directory (default: a new temporary directory). The build is `DIR/build`, the pull request text `DIR/pr-body.md`. |
| `--source DIR` | Private repository root (default: the repository the script is in). |

Exit codes: `0` done; `2` a gate failed; `3` a hard stop; `64` usage error; `1` an operation failed part-way (the message says what was left).

Every post rebuilds the whole public site from `release/public.json` plus the new piece, so previously released pieces are rebuilt with the same rules (final version only, corrections applied) unless they are listed under `all_versions` in `release/public.json`, which the script writes when `--include-versions` is used.

## Gates (exit code 2, `--force` can override)

Each prints `PASS` or `FAIL` with the reason.

1. **In Series.** `release/PIECE.json` exists and its `pool` is `series`.
2. **Fully verified.** Every line of every version block of the piece (`studio/data/review.json`: item, versions, blocks, lines) has a `reviews/LINEID.json` document whose `status` is `confirmed`, or `corrected` with a `text`. This covers all versions, including ones that are not published.
3. **Filed.** The piece id is in the `items` of a batch whose `status` is `filed` or `registered`.

## Hard stops (exit code 3, `--force` cannot override)

- **(i) Shared scan.** A published page is a whole scan. For each page the published version(s) sit on, every other piece on that page is checked. Already in `release/public.json` (or posted in the same run): fine. Pool `series` but not public yet: needs `--accept-shared-scan ID`. Pool `reserve`, `archive`, no release document (unsorted) or any other value: refused, and acceptance does not help. Non-piece "other lines" items from the review data on the page also need acceptance. Only the pages of the published versions count, so with the default (final version only) the pages of drafts are not involved.
- **(ii) Stale transcript.** A review document's `original` must equal the current machine reading in `site/data/j.json`. Otherwise the post is refused and the line ids are listed (never the text). Checked for the published blocks.
- **(iii) Unknown piece id.**
- **Public repository preconditions.** `remote.origin.url` names `4444J99/versforms`; the working tree is clean (untracked files count); the branch is `main`; local `HEAD` equals `origin/main` (checked with `git ls-remote`, which writes nothing); the branch `post/PIECE_ID` does not exist locally or on the remote.
- **Embedded font.** `site/index.html` carries the handwriting font as a base64 data URI named `Etceter4 Diary`. A real run refuses unless `--accept-embedded-font` is given, because the font file becomes downloadable and its name becomes public. A dry run only warns.
- **Output checks.** The build must pass its own checks (noindex meta and header, no source-repository provenance, expected pieces, all images present, no text of an unpublished block anywhere in the output). A failure here is a bug or a leak; nothing is written.

## What is published

- **Versions.** Only the final version: the version the author decided as final in the studio's Decisions tab (a `decisions/...-final` document whose `choice` names `PAGE-BLOCK` of that piece), otherwise the top of the piece's stack (`top`, which is also `st[0]`; the newest). A `layers` choice falls back to the top with a warning. Pages used only by unpublished versions are not copied. Blocks of unpublished versions and of other pieces on a published page lose their text, their piece link and their reading note; the scan image still shows the whole page.
- **Corrections.** For each published line whose review status is `corrected`, the line in `data/j.json` is replaced by the author's `text`. Confirmed lines keep the machine reading. Lines of quotation blocks stay withheld.
- **noindex.** `index.html` gets `<meta name="robots" content="noindex">` right after the viewport meta, and a `_headers` file sets `X-Robots-Tag: noindex` for `/*`. The visible title is not changed; the script prints it as a warning.
- **Source provenance.** `prov.repo`, `prov.commit` and `prov.path` (they name the source repository) are removed from `data/j.json`; `tdate` and `verified` stay. The engine reads `DATA.prov` only in its info panel (`fillInfo`), with a fallback to an empty object and empty strings, so the data loads without them. Static reading only; not run in a browser. Side effect: the info panel's "Scans:" line renders with an empty link and empty commit fields.
- **Piece numbering.** Piece links in published blocks are renumbered to the public piece list.
- **Reader-visible strings.** The dry run and the real run list the title, `aria-label` and `alt` strings, font names and mentions of the font name, provenance keys and reading-note counts that the build would publish. It only lists them; the author decides.

## What the pull request contains

Branch `post/PIECE_ID` (several ids are joined with `-`), one commit `Post PIECE_ID` that replaces `site/` with exactly the build output. The pull request body has three lists:

- **What changed**: piece, versions, page ids, files added / changed / removed, bytes.
- **How verified**: every gate and hard-stop outcome (a forced gate is marked), the output checks, line counts, the sha256 of `data/j.json`.
- **Not verified**: real-device rendering, a Cloudflare preview deploy, the author's sign-off on shared scans and on the embedded font, warnings, and the reader-visible strings list.

No poem text goes into the body, the commit message or the log.

After a successful run the script adds the piece id to `release/public.json` in the private repository (order kept, no duplicates) and prints the `git diff`. It does not commit or push the private repository: commit that file through the usual private-repository process.

## Merging

Review the pull request in `4444J99/versforms`, check the Cloudflare Pages preview when one exists, and merge it yourself. The script never merges.

## Rolling back

In the public repository: `git revert -m 1 MERGE_COMMIT` (or `git revert COMMIT` for a squash or rebase merge) on a new branch, and open a pull request. History is never rewritten or force-pushed. Also take the piece id out of `release/public.json` (and `all_versions`) in the private repository, or the next post will bring it back.

## Tests

`python3 -m unittest discover -s tests -v` (synthetic fixtures only; set `TMPDIR` if scratch files must stay on the external drive).
