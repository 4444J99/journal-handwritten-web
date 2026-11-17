# PR / Issue Evolution Report — `journal-handwritten-web`

**Date:** 2026-11-17  
**Stream:** B (PR / Issue Evolution) of the Autonomous Ecosystem Retirement & Enrichment plan  
**Method:** full remote inventory via `gh` (all states), heuristic supersession detection, local git/oss evidence. Machine-readable evidence: `.opencode/plans/stream-b/2026-11-17-pr-issue-data.json`  
**Staging run:** `09_Engineering/custody-staging/run-20261117-104235-session-retirement/`

> Supersession links below are **evidence-backed candidates**, not licensed merges. No remote PR was closed and no history was rewritten by this pass. Destructive actions are listed as ready-to-run commands for the owner or the orchestration stream.

## 1. Repository state

| Field | Value |
|---|---|
| Local path | `/Volumes/Archive4T/Projects/journal-handwritten-web` |
| GitHub remote | `4444J99/journal-handwritten-web` |
| Upstream archived | no |
| Default branch (remote) | main |
| Local branch | `main` |
| Dirty files | 0 |
| Linked worktrees | 1 (canonical checkout) |
| Last commit | 2026-11-15T21:27:49 — Silent launch: Firefox media.volume_scale=0.0 pref (issue 171) (#172) |
| Plan surfaces | .codex/plans |

## 2. PR inventory

| Metric | Count |
|---|---|
| PRs (all states) | 67 |
| Merged | 64 |
| Open | 0 |
| Closed unmerged | 3 |

Closed-unmerged classification:

| Class | Count |
|---|---|
| closed without successor | 3 |

## 3. Evolution decisions (old → new)

_No supersession links detected: no closed-unmerged PR in this repo has a traced successor._

## 4. Items marked archived

- **64 merged PRs** — resolved, no action; history is the archive.
- **3 PRs closed without a traced successor** — archived as abandoned. Titles are retained in the evidence file in case a later re-cut needs the original scope.

## 5. Open PR triage

_No open PRs._
## 6. Issues

| Metric | Count |
|---|---|
| Issues (all states) | 105 |
| Open | 65 |
| Open and idle > 45 days | 0 |

Most common labels on open issues: `author` (47), `chat` (57).

## 7. Follow-up flags

- No open PRs; the 7 Nov 2026 housekeeping closeout (`docs/verification/repository-housekeeping-2026-11-07/`) already retired 55 branches and deliberately **retained 68 open issues** as exchange records and owner decisions.
- Read the 65 open issues as retained-by-design, not stale debt. Re-triage only if the ledger is reopened.

## 8. Provenance and limits

- PR/issue inventory: `gh pr list`/`gh issue list --state all` for `4444J99/journal-handwritten-web`, captured 2026-11-17.
- Supersession classes: explicit `supersedes #N` in title; dependency retry (same package + directory, newer bump merged); rewrite series (identical title stem, later PR merged); producer retirement (Limen/Jules branch, no successor); otherwise abandoned.
- Heuristic limit: a title-stem match can link two genuinely different changes. Treat §3 as a review queue, not as settled provenance.
- No remote mutation was performed: no PR closed, no issue closed, no branch deleted.
