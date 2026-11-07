# Issue ledger — 2026-11-06 integration closeout

Companion to the merged tranche (PRs #119, #125, #126, #127, #128, #129, #130,
#131, #134, #135). Remote `main` at ledger time: `9939f2098fcf65e9fd009f9cf970c10064ea44b8`.
`tools/check.py` OK; `ci_local.py` RESULT: PASS (264 py, 92 node, 59 studio-cf-py, 83
studio-cf-node). No author decisions are taken here; author-held items remain open.

## Dispositions

| Issue | Title (short) | Disposition | Technical status |
|---|---|---|---|
| #102 | alive prototype (draft PR) | Left as draft; successor/disposition note recorded. Not merged without successor review. | `proto/alive/` present; #109 design questions pending. |
| #104 | studio Pages runtime Fail closed | Owner action (Cloudflare dashboard). Not automatable. | No code change; documented. |
| #105 | sort p001-p010 Series/Reserve/Archive | Owner decision. | Studio sort UI exists; awaiting author. |
| #106 | register batch 1 (GRUW) | Owner decision (cost/legal). | Runbook in `docs/posting.md`; gate enforced by posting script. |
| #108 | three posting-script build questions | Owner decision. | Questions documented; defaults accepted-as-written until answered. |
| #109 | six alive-prototype design questions | Owner decision. | Pending; prototype does not depend on them. |
| #111 | GitHub Actions billing | Owner action (billing). | `tools/ci_local.py --status` posts `local-ci` commit status as workaround. |
| #112 | studio polling rate | Deferred, low priority. | Backoff already implemented; no change. |
| #113 | runbook first post (p001) | Runbook; gated on #105, verification, #106, #101 re-check, #108. | All technical preconditions except author decisions met. |
| #121 | diary1 block 2 line/box count | Owner decides whether `site/data/j.json` may change; fix preparable as PR. | Finding confirmed (4 lines, 3 boxes). No automated fix applied (published data). |
| #123 | posting hardening | Resolved and merged (#131, #132). | `tools/post_poem.py` hardened; regression tests ported. |

## T01/T02/T04 recovery

- T01 (private persistence / studio entry): integrated via T05/T06 tranche; `studio/notes.html` and modules shipped; handoff at `docs/integration/t05-handoff.md`.
- T02 (media/source bindings): integrated in #135 (source-region consumers, realization packages); tests pass.
- T04 (recovery of older artifacts): no completed handoffs recovered beyond the recorded dispositions above; remaining open items are owner-held.

## Author decision packet (separate)

See `docs/integration/author-decision-packet-2026-11-06.md` for first-release candidates, previews, hashes and gates. No release is authorized by this ledger.
