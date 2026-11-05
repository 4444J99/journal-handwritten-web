# Local Claude Code session: finish the outstanding work and launch

| | |
|---|---|
| Chat | local Claude Code session on the author's Mac (not a claude.ai chat); a forked session carries the build lanes |
| Last activity | 2026-11-05 (America/New_York) |
| Repository | `4444J99/journal-handwritten-web` (private) and `4444J99/versforms` (public) |
| Basis of this record | this session's own commands and their output, checked against GitHub and Cloudflare where stated |
| Status | In progress — see Status |

## Produced
Pull requests (private repo unless noted):
- [#89](https://github.com/4444J99/journal-handwritten-web/pull/89) Release tab, both bullets of Step 5: Mark posted defaults (`where` `versforms.pages.dev`, `account` `vers.forms`) and post URL, plus Exposure log quick choices for the site and the Instagram account. 14 node tests pass; the Exposure form was driven in a browser against a local server. Not verified: logging an entry (the studio ran without a database), the Mark posted flow in a browser, phone layout.
- [#92](https://github.com/4444J99/journal-handwritten-web/pull/92) README "Rebuild path" (Step 6): the documented order, with the missing scripts stated as missing.
- [#93](https://github.com/4444J99/journal-handwritten-web/pull/93) `pages.yml` now needs an explicit confirmation input before it can publish the private `site/`.
- [#94](https://github.com/4444J99/journal-handwritten-web/pull/94) `tools/ci_local.py`: runs the repository checks locally and posts a `local-ci` commit status (Actions is billing-blocked). `local-ci` statuses are posted on the heads of #89, #92, #93 and #94; the #89 one was read back from GitHub.
- `4444J99/versforms` [#1](https://github.com/4444J99/versforms/pull/1), merged `1fe6b507` at 18:23:33Z: blank page title `versforms`. Production fetched afterwards: `<title>versforms</title>`, `noindex` unchanged.

Cloudflare (account `CF-4444j99`, `e0921b84…`; the account of the `versforms` Pages project, the connector and `wrangler` were confirmed to be the same by matching `d1 list` output):
- R2 bucket `versforms-studio-assets` created. Empty Pages project `versforms-studio` created with no deployment.
- A new D1 database could not be created (limit of 10 per account reached).

Other:
- Font tooling venv at `/Volumes/Archive4T/Runtime/tools/venvs/versforms-font` (Python 3.13, fonttools 4.68.0, brotli 1.2.1). It opens the embedded WOFF2; "Etceter4 Diary" is in name IDs 1, 4 and 6.
- Exposure audit (read-only): `4444J99/etceter4` (public, Pages on) and `4444J99/generative-multimedia-spatial-environment` serve all 123 journal scans and `diary_originals.zip` without login.
- Inventory: `tools/check.py` OK (509 references, 510 checksums); `shasum -c MANIFEST.sha256` exit 0; `site/index.html` and `studio/index.html` byte-identical to the live artifacts' current versions; build folders not found.
- Lanes in the forked session (branches not pushed when this was written): `post-poem-gates`, `studio-cloudflare`, `site-v4-verification`.

## Author decisions (stated by him)
- Studio storage while D1 is capped: prefixed tables in an existing database.
- Cloudflare login: he runs `wrangler login`; he also ran `gh auth refresh -s workflow`; both worked.
- Public font family name: `ajp-scribbles` (his words: "it is my handwriting ... something like my name").
- Public page title: `versforms`; the blank page matches.
- Embedded font file: install the tooling in a venv so its internal name can be renamed.
- The etceter4 scan exposure: report only.
- Step 5, second bullet: "Exposure log: the site and the Instagram account are both choices." Step 6 (rebuild path) as written in his brief.
- Posting goes "in order of the pages of the journal".
- GitHub billing "won't be fixed for weeks"; asked for a way around it.
- Delegated to logic: whether to merge versforms#1; numbering; whether participation counts toward the 100.

## Plan / next steps
Derived by Claude at the author's instruction (labelled; he can overrule any of them):
- **Claude (derived):** versforms#1 merged — title only, preview verified, clean and approved, his chosen title.
- **Claude (derived):** numbering "assigned as each poem posts" (`decisions/release-numbering` = `as-posted`). The studio's fixed mode numbers by queue position, so a reorder or a move to Reserve would renumber poems already public; and only 58 complete pieces exist, so there is no list of 100 to fix in advance.
- **Claude (derived):** participation "sits around the 100" (`decisions/participation` = `around`). The goal is 100 of his poems; group registration needs the same claimant on every work in a batch; the plan's own research points to a separate layer under a contributor licence. To be written into the studio's Decisions when the Cloudflare studio is live.
- **Claude (derived):** first poem by page order is `p001` (page `diary1`, a second version on `diary62a`); the studio's item order equals page order. By default only the `diary1` version is publishable: `diary62a` also carries unreleased `p126`.
- **Claude:** no GitHub runner is needed to merge: `main` has no branch protection. `tools/ci_local.py` supplies evidence on each PR.
- **author:** Access click-through (Cloudflare dashboard) before the studio deploys; `wrangler`'s login has no Access scope.
- **Claude (forked session):** push and open PRs for the three lanes once their verifiers pass, then the cross-branch integration check.
- **Claude:** seed the two decisions above and move the studio data into `vf_` tables in `object-lessons-submissions` once the studio API is verified; deploy only after he confirms Access.
- **author:** Series / Reserve / Archive sort, GRUW batch filing (a real copyright step), before any post.
- **open, nobody:** Step 6 cannot be met until `apply_reviews.py`, `build_data.py`, `assemble.py` and `app_build/build.py` exist. They were not found on this machine; they lived in earlier cloud sessions.
- **open, author:** the font fill-in sheet needs `ingest_fillin.py`, which is also missing; not needed for launch.

## Status
In progress. Merged: versforms#1 (verified live). Open and unmerged: #89, #92, #93, #94 (each with the verification and gaps in its description). The three lanes are running in the forked session and were not pushed when this record was written; none is claimed as verified here.
