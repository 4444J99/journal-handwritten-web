# 2026-11-14 Pre-rendered release (free-plan Worker CPU)

## Produced
- `studio-cf/prerender_release.mjs`: compiles a release with the Studio's own `buildCandidate` (all gates, stops and name-leak scans unchanged) and writes it as a static Pages site: the published files, a `_headers` file (noindex, nosniff, referrer policy, cache, and `Content-Type: image/png` for the lossless atlas tiles under `.jpg` routes), and no `functions/`, `_worker.js` or `_routes.json`. Every byte is checked against its recorded hash; a blocked candidate, a non-empty output directory or an unexpected file writes or passes nothing. Release id is a deterministic digest of the file list.
- `studio-cf/measure_release_cpu.mjs`: offline per-request CPU harness (Node `process.cpuUsage`, in-memory R2 stub) for the R2 reader Worker versus the pre-rendered site, with `--serve-check` that starts `wrangler pages dev` on the output.
- Tests: `prerender-release.unit.test.mjs` (7), `prerender-serve.test.mjs` (2, starts wrangler locally). README section "Pre-rendered release".
- Nothing deployed, no Cloudflare credential or call, no private content published; real-size measurements ran on scratch output that is not committed.

## Author decisions
None in this session. Owner words carried from the goals file: "is there a way to MacGyver it?"

## Plan / next steps
- Suggestion: the owner decides whether the public reader moves to a pre-rendered static Pages project (rollback = redeploy the previous output); the R2 reader and its pointer protocol are unchanged by this PR.
- Suggestion: wire the output to a deploy step once credentials and the Access/hosting decision exist.

## Status
Tool and tests merged-ready in this PR; hosted behaviour (real `wrangler pages deploy`) unobserved.
