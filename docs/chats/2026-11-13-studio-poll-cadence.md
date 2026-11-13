# 2026-11-13 Studio poll cadence (issue 112)

## Produced
- `studio/cf-adapter.js`: `POLL_MS` 4000 to 15000. The studio now has 11 collections, so the old cadence was about 2.75 requests per second while visible; it is now about 0.7. Backoff is 15 s, 30 s, then the 60 s cap. Pause while hidden and the immediate poll after the page's own write are unchanged.
- `studio-cf/tests/adapter.unit.test.mjs`: cadence tests re-timed (26 of 26 pass).
- `studio-cf/README.md` and `MANIFEST.sha256` updated. Needs a studio redeploy (fresh clone of main, `build_dist.py`, `wrangler pages deploy`) to take effect; not done here (credentials and owner timing).

## Author decisions
None in this session.

## Plan / next steps
- Suggestion: redeploy the studio with the next batch of changes.
- Integration tests: 7 failures in `studio-cf/tests/*.test.mjs` are identical on origin/main without this change (123 pass, 7 fail both ways).

## Status
Issue 112 addressed by this PR.
