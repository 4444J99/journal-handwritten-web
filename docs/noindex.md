# noindex on the public site

The public site (https://versforms.pages.dev, repository `4444J99/versforms`) asks search engines not to index it. It stays that way until the author decides otherwise (standing rule 7: changing `noindex` is the author's call). This note says where the setting lives and what removing it involves. Checked 2026-11-05.

## Where it lives

| Place | What it is | State on 2026-11-05 |
|---|---|---|
| `versforms` repo, `site/index.html` | `<meta name="robots" content="noindex">` in the page head | present; the live page serves it |
| `tools/build_public.py` (this repo), constant `SHELL` | the blank page the build writes when `release/public.json` has no pieces; carries the same tag | present |
| `tools/build_public.py`, non-empty release list | copies `site/index.html` from this repo, which has **no** robots tag | **on `main` today a non-empty build would drop `noindex`**; the post-poem script (`tools/post_poem.py`, separate PR) re-injects the tag and also writes a `_headers` rule `X-Robots-Tag: noindex` for that reason |

Cloudflare Pages itself adds no robots header (the live response headers were read on 2026-11-05: no `X-Robots-Tag`). There is no `robots.txt` file and no `_headers` file in the public repository yet. A request for `/robots.txt` is answered with the home page (200, `text/html`, 432 bytes, because Pages falls back to `index.html` for unknown paths), which crawlers read as "no rules"; the `noindex` tag in the page is what holds today.

## What removing it involves

1. The author decides (rule 7). Nothing in this repository removes it automatically; the post-poem script refuses to produce a build without it.
2. In `4444J99/versforms`, in one pull request:
   - remove the `<meta name="robots" content="noindex">` line from `site/index.html`;
   - once the post-poem script is merged, also remove the `_headers` rule and the injection step (the header alone keeps the pages out of search results even if the tag is gone).
3. Merge that pull request. Cloudflare Pages deploys the production site from the public repository's `main`; on 2026-11-05 a merged one-line change was live about 40 seconds later (observed with a fetch of the live page).
4. Verify with a fetch of the live page and its headers: no `noindex` in the body and no `X-Robots-Tag`.
5. Search engines then index the site when they next crawl it; there is no way to schedule that. Posted poems become findable by their text and by the page scans' file names.

## Undoing it

Re-add the tag (and the header) in a pull request and merge it. That stops new indexing but does not recall what was already indexed: search results and cached copies can persist until the engines recrawl, and removing them sooner means using each engine's removal tool. Treat removal as hard to reverse.

## Related

- Rule 4 is separate: pieces not marked posted never appear on the public site in any form, whatever `noindex` says. `noindex` is a request to well-behaved crawlers, not access control.
- Journal scans exist in other public repositories (see `docs/chats/2026-11-05-local-session-finish-and-launch.md`); `noindex` on this site does not affect them.
