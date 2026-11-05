# Posting a poem

`tools/post_poem.py` turns "post a poem" into one small, reviewable action. It checks the poem, builds the public site for it, commits that to a branch of the public repository (`4444J99/versforms`) and opens a pull request. It never merges. Technical document; it contains no editorial content.

## Prerequisites

- Python 3 with Pillow (the standard library is otherwise enough). `git`; `gh` (signed in) for the pull request.
- The font venv, used for one step only (renaming and checking the embedded font): a Python with `fontTools` and `brotli`, at `/Volumes/Archive4T/Runtime/tools/venvs/versforms-font/bin/python` or wherever the environment variable `VERSFORMS_FONT_PYTHON` points. `tools/post_poem.py` and `tools/build_public.py` themselves run under the plain `python3`; they start `tools/font_rename.py` as a subprocess with the venv python. Without the venv the font step cannot run (see "Embedded font" below).
- A studio database export: one JSON file per document at `EXPORT_DIR/COLLECTION/DOCID.json` for the collections `reviews`, `decisions`, `versions`, `release`, `batches`, `rconfig` (the format of the 2026-11-05 export, `exports/studio-db-2026-11-05/`). A collection with no documents may have no folder. `--db` also accepts the directory that contains `exports/<name>/`.
- A clone of `4444J99/versforms` (the public repository), clean, on `main`, level with `origin/main`. Do not use it for anything else while a post is open.
- The piece must exist in `site/data/j.json` (ids `p001` to `p126`).

## The command

```
python3 tools/post_poem.py PIECE_ID [PIECE_ID ...] --db EXPORT_DIR --public-repo PATH [options]
```

| Option | Effect |
|---|---|
| `--dry-run` | Runs every gate and hard stop and builds into the scratch directory; prints the version report, the checks, the reader-visible strings, the warnings, the file list and sizes. Writes nothing in the public repository, pushes nothing, leaves `release/public.json` alone. `--public-repo` is optional (without it the repository checks are skipped). |
| `--no-pr` | Commits the branch in the public clone but does not push or open a pull request. |
| `--force` | Overrides the three gates only (exit code 2 becomes a warning). Never overrides a hard stop. |
| `--include-versions` | Publishes the whole version stack. Needs the author's approval; the script says so. |
| `--accept-shared-scan IDS` | Comma separated ids of co-resident pieces, "other lines" items, or page ids (a facing page of a spread image), whose writing may show in a shared scan. |
| `--accept-embedded-font` | Only for the case where the embedded font cannot be decoded and checked (the font venv is missing) and the page does not name the old family: publish it unchecked. Not needed, and not used, when the check can run; it never covers a font known to carry the old name. |
| `--workdir DIR` | Scratch directory. Default: a new `post-poem-*` directory under `.post-poem-work/` in the private repository (git-ignored). The build is `DIR/build`, the pull request text `DIR/pr-body.md`. |
| `--source DIR` | Private repository root (default: the repository the script is in). |

Exit codes: `0` done; `2` a gate failed; `3` a hard stop; `64` usage error; `1` an operation failed part-way (the message says what was left).

Every post rebuilds the whole public site from `release/public.json` plus the new piece. Pieces that are already public are rebuilt with the same rules (final version only, corrections applied) unless they are listed under `all_versions` in `release/public.json`, which the script writes when `--include-versions` is used. They are not put through the three gates again, but the hard stops "own pool" and "shared scan" run over every piece in the rebuilt list, not only over the requested ones.

## Gates (exit code 2, `--force` can override)

Each prints `PASS` or `FAIL` with the reason. They run for the requested pieces.

1. **(a) In Series.** `release/PIECE.json` exists and its `pool` is `series`.
2. **(b) Fully verified.** Every line of every version block of the piece (`studio/data/review.json`: item, versions, blocks, lines) has a `reviews/LINEID.json` document whose `status` is `confirmed`, or `corrected` with a `text`. This covers all versions, including ones that are not published.
3. **(c) Filed.** The piece id is in the `items` of at least one batch whose `status` is `filed` or `registered` (a draft batch that also lists it does not matter when another batch is filed).

## Hard stops (exit code 3, `--force` cannot override)

- **Own pool: Reserve or Archive.** If the requested piece's own release pool is `reserve` or `archive`, the post is refused. The same stop applies to every piece already in `release/public.json` whose pool is now `reserve` or `archive`: it would be rebuilt and published again, so the stop names it; take it out of `release/public.json` (and decide how to retire it publicly) before posting anything else. A piece with no release document or an unknown pool is only a failed gate (a) for a requested piece, which `--force` can override, and a warning for an already-public piece.
- **(i) Shared scan.** A published page is a whole scan. For each page the published version(s) of each piece in the rebuilt list sit on, every other piece on that page is checked. A spread image is checked as well: when a published page has `sp.f`, the build copies `img/s/<f>.jpg`, the whole two-page spread, so the facing page counts too (pages with the same `sp.k` or `sp.f`, or the page the file is named after); findings there say "facing page of the spread image". A published page without `sp.f` copies no spread image, so its facing page is not involved. Already in `release/public.json` (or posted in the same run): fine. Pool `series` but not public yet: needs `--accept-shared-scan ID`. Pool `reserve`, `archive`, no release document (unsorted) or any other value: refused, and acceptance does not help. Non-piece "other lines" items from the review data on the page also need acceptance. A facing page with no piece and no review item cannot be shown to be blank: it is refused unless `--accept-shared-scan PAGE_ID` names that page. Only the pages of the published versions count, so with the default (final version only) the pages of drafts are not involved. Acceptances are not stored anywhere: every post rebuilds the whole list, so a piece that was posted with `--accept-shared-scan ID` is checked again on every later post, and each later post must pass the same ids again until the accepted piece itself is public.
- **(ii) Stale transcript.** A review document's `original` must equal the current machine reading in `site/data/j.json`. Otherwise the post is refused and the line ids are listed (never the text). Checked for the published blocks of every piece in the rebuilt list.
- **(iii) Unknown piece id.**
- **Public repository preconditions.** `remote.origin.url` names `4444J99/versforms`; the working tree is clean (untracked files count); the branch is `main`; local `HEAD` equals `origin/main` (checked with `git ls-remote`, which writes nothing); the branch `post/PIECE_ID` does not exist locally or on the remote (the detail says which). The working tree is read with `git --no-optional-locks status --porcelain`, so a dry run does not refresh `.git/index`.
- **The other project's name.** The output must not contain the name of the author's music project, in any letter case. Every file in the output is searched as text and as raw bytes (ASCII, which is also the Mac Roman spelling, UTF-16 big endian and little endian), and so is every file and directory name (the log says "output file N: its path" and never repeats the name). Every base64 `data:` URI in a text file is decoded; a font goes through `tools/font_rename.py check`, which searches the decoded `name` table (all platforms, encodings and languages), the CFF font name and top dictionary strings, glyph names, the WOFF2 metadata and the raw bytes of every table; any other payload gets the raw byte search. A compressed WOFF2 stream cannot be searched as raw bytes, so for a font the decoded tables are the authority. Any hit refuses the post. The pull request text is checked the same way before anything is committed.
- **Embedded font that cannot be checked.** Three different cases. (1) The font tool cannot run at all (the venv python is missing, or lacks `fontTools` or `brotli`) and the page does not name the old family: the font cannot be decoded, so the name check cannot cover it. The name check line is then printed as `UNCHECKED` (never `PASS`: the text and raw-byte search ran, the font tables did not). A real run refuses unless `--accept-embedded-font` is given; a dry run only warns (exit 0), because the flag is the way to accept that. (1b) The same, but the page's font family is the old name (as in the live site): the font file is then known to carry the old name and it was not renamed, so a real run is refused and `--accept-embedded-font` does not cover it; install the venv. A dry run fails the same way (exit 3), so a script that reads the exit status is not told that input a real run refuses is fine. With the venv in place the flag is never needed. (2) The venv runs and the font bytes do not parse as a font: nothing vouches for the file (a compressed WOFF2 stream cannot be searched as raw bytes), so this is a hard stop in a dry run and a real run alike, and `--accept-embedded-font` does not cover it.
- **Output checks.** The build must pass its own checks (noindex meta and header, exact title, font family, no source-repository provenance, expected pieces, all images present, no text of an unpublished block anywhere in the output). A failure here is a bug or a leak; nothing is written.

## What is published

- **Versions.** Only the final version: the version the author decided as final in the studio's Decisions tab (a `decisions/...-final` document whose `choice` names `PAGE-BLOCK` of that piece), otherwise the top of the piece's stack (`top`, which is also `st[0]`, the version the site shows first). `top` is not always the last entry of `V`; the engine labels `V` oldest to newest, so the last entry is the newest. For each requested piece the script prints which version it publishes (`V[i]` and its id), which is the newest in the stack (`V[n-1]`), which is the top, and how many lines carrying an author correction sit on versions that are not published; the last number is also a warning when it is not zero, because those corrections are not in the public data. `V` carries no dates, so "newest" cannot be derived from dates. A `layers` choice falls back to the top with a warning. Pages used only by unpublished versions are not copied. Blocks of unpublished versions and of other pieces on a published page lose their text, their piece link and their reading note; the scan image still shows the whole page.
- **Corrections.** For each published line whose review status is `corrected`, the line in `data/j.json` is replaced by the author's `text`. Confirmed lines keep the machine reading. Lines of quotation blocks stay withheld.
- **noindex.** `index.html` gets `<meta name="robots" content="noindex">` right after the viewport meta, and a `_headers` file sets `X-Robots-Tag: noindex` for `/*`. An existing robots meta that already contains `noindex` is left as it is (a stricter tag such as `noindex,nofollow` is not weakened); the output check accepts any robots meta containing `noindex`. The empty-release shell written by `tools/build_public.py` carries the same tag.
- **Title.** The built `index.html` has exactly one title element and its text is `versforms`. The empty-release shell has the same title. `site/index.html` in the source tree is not edited.
- **Font family.** In the built `index.html` every spelling of the old family name (any letter case, with a space, hyphen, underscore or nothing before "Diary", quoted or not: the `@font-face` rule, the hand-font custom property, plain `font-family` values, canvas font strings, the `document.fonts.load` call and visible text) becomes `ajp-scribbles`. The embedded WOFF2 file is renamed too, by `tools/font_rename.py` run with the venv python: name ids 1, 16 and 21 become `ajp-scribbles`, ids 4 and 18 `ajp-scribbles Regular`, id 6 `ajp-scribbles-Regular`, on every record of every platform; every other record or CFF string that carries the old name (ids 0, 3, 5, 7 and others, the CFF font name list and the CFF top dictionary strings) is rewritten; the CFF font name becomes the PostScript name. The font is re-encoded to WOFF2 and its data URI replaced; the font's own `head.modified` time is kept (not the current time), so building the same input twice gives the same bytes and a later post does not show `index.html` as changed when nothing else did. Outlines, cmap and advance widths are not touched (the tests decode the output and compare glyph count, glyph order, cmap, advance widths and table list). A font that does not carry the old name is left alone. The visible sentence in the info panel that names the typeface changes with it; that is reader-visible text, and it is listed in the audit.
- **Source provenance.** `prov.repo`, `prov.commit` and `prov.path` (they name the source repository) are removed from `data/j.json`; `tdate` and `verified` stay. The engine reads `DATA.prov` only in its info panel (`fillInfo`), with a fallback to an empty object and empty strings, so the data loads without them. Static reading only; not run in a browser. Side effects, printed as warnings and listed in the pull request: the info panel's "Scans:" line renders with an empty link and empty commit fields, and while `prov.verified` is false the panel says the machine transcription is "not yet checked by the author", even for a piece that passed gate (b). `index.html` is not edited beyond the title and the font family, so the author decides what that text should say.
- **Piece numbering.** Piece links in published blocks are renumbered to the public piece list.
- **Reader-visible strings.** The dry run and the real run list the title, `aria-label` and `alt` strings, font names (family, full name and the other name records of the renamed font), provenance keys and reading-note counts that the build would publish. It only lists them; the author decides.

Do not regenerate the public `site/` with the bare `python3 tools/build_public.py OUT_DIR`: it has no review database, so it publishes every version with the machine readings (it still keeps noindex, writes `_headers`, sets the title, renames the font, drops the source provenance and renumbers piece links). If the font venv is missing it prints a warning and exits with code 3, because the output would still carry the old font name inside the embedded font. Use `post_poem.py`.

## Does a dry run write nothing?

In the public repository: nothing. The repository checks use `git config`, `rev-parse`, `ls-remote` and `git --no-optional-locks status --porcelain`; none of them writes inside `.git`. The test `test_dry_run_leaves_the_git_index_file_untouched` and `test_dry_run_writes_nothing_and_pushes_nothing` compare the index, refs, working tree and the bare remote before and after. In the private repository: `release/public.json` is untouched; the build goes to the scratch directory (`--workdir`, default `.post-poem-work/`, git-ignored).

## What the pull request contains

Branch `post/PIECE_ID` (several ids are joined with `-`), one commit `Post PIECE_ID` that replaces `site/` with exactly the build output. The pull request body has three lists:

- **What changed**: piece, version published, newest version, top of the stack, corrections on unpublished versions, page ids, files added / changed / removed, bytes.
- **How verified**: every gate and hard-stop outcome once (a forced gate is marked), the output checks, line counts, the sha256 of `data/j.json`.
- **Not verified**: real-device rendering, a Cloudflare preview deploy, the author's sign-off on shared scans, the author's sign-off on the embedded font file's own metadata, font notes (a font that could not be decoded and was accepted unchecked), warnings, and the reader-visible strings list.

No poem text goes into the body, the commit message or the log, and the body never contains the other project's name (it is rendered and checked before the branch is committed; a hit refuses the post). Details about the old font name stay on the console. The name records of the font file (which can hold personal names and a description of where the font comes from) are listed on the console only, as `font file name` rows; the body says so and does not list them. The body marks a check that did not run as `UNCHECKED`.

After a successful run the script adds the piece id to `release/public.json` in the private repository (order kept, no duplicates) and prints the `git diff`. It does not commit or push the private repository: commit that file through the usual private-repository process.

## Merging

Review the pull request in `4444J99/versforms`, check the Cloudflare Pages preview when one exists, and merge it yourself. The script never merges.

## Rolling back

In the public repository: `git revert -m 1 MERGE_COMMIT` (or `git revert COMMIT` for a squash or rebase merge) on a new branch, and open a pull request. History is never rewritten or force-pushed. Also take the piece id out of `release/public.json` (and `all_versions`) in the private repository, or the next post will bring it back.

## Tests

`python3 -m unittest discover -s tests -v` (synthetic fixtures only; set `TMPDIR` if scratch files must stay on the external drive). Without the font venv a run on the standard fixture page is refused (its font is known to carry the old name and cannot be renamed), so a test that expected a different outcome is skipped, with a message, when the run it just made was refused for that reason; tests that stop earlier (a failing gate, an unknown piece) and tests that set `NO_VENV` on purpose run either way.
