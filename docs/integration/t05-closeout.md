# T05 repository closeout record

## Requested terminal state

An isolated, reviewable private branch and draft PR for #17/#18/#64, containing
the private versioned workflow, schema, migration notes, verification and
integration handoff. Shared-page wiring and author choices remain explicit
residuals. No merge, deployment, poem publication, issue closure, account
change, external message or repository restructuring is part of this closeout.

## Scope and authoritative state

Only `4444J99/journal-handwritten-web` is changed. Its private GitHub API and
exact Git object IDs are the remote authority. The starting main was
`d74df372ace00c8a7544ab3b5302cb05418d672c`; the refreshed base is
`fab6a82b72f23efb16278b90cdc4f7790ca55713`, tree
`7f90d151f089596c9bd4da4f13652927fe154f7d`. PR #101 merged during work; the T05
commit was reconciled onto the newer main without a conflict or modification
to upstream posting code.

The final base additionally preserves documentation-only main
`038d01fb1862f2e569d231b5b3c4c3a4eb1aecda`, tree
`61618a204611a0e5dafb5485c6d99007ef679554`. It adds the upstream account of
deferred posting findings on #123; T05 leaves their status and ownership intact.

The review branch is `t05/private-notes-contributions-2026-11-05`.
The executable checkpoint is `994c6903b0b5d02dd0be361e969b2b3a916eff35`.
The final PR/response records the exact resulting remote head and tree after
the documentation/evidence commit is transferred and read back. Code hashes
are in `docs/verification/t05-2026-11-05/tested-files.sha256.json`; verification
is not inferred from a branch name.

## Preservation and dispositions

| Resource | Disposition and evidence |
|---|---|
| Original author sources, shared reader/studio pages, release whitelist | Preserved byte-for-byte; SHA-256s recorded in acceptance.json |
| Existing six persistence collections | Replacement/deletion behavior retained; backward-compatibility tests pass |
| Notes and contributions | New append-only collections; source snapshots, dates and complete revision history preserved |
| Initial T05 checkpoint | Retained locally as `t05/checkpoint-before-live-reconcile-2026-11-05`, commit `402fb9c`; no other branch rewritten |
| T01 checkout | Read-only inspection; head `d830d2a8f0556c50917d34528ab0b19cf7e0579a`, clean at final inspection |
| T03 checkout | Read-only inspection; head `8d16284ba8b80f18398d08b8de931d8812f30429`, clean at final inspection |
| T04 checkout | Read-only inspection; head `00efd23c1fbf0852287f4813ea451d98b6ffc53c`, clean at final inspection |
| T02 directory | Older non-Git snapshot inspected; no new contract or completed agreement claimed |
| Shared studio entry | A patch handed to its single integrator; shared HTML untouched |
| Temporary databases/browser | Disposable local fixtures only; verification servers/browser stopped by the harness |
| Repository cleanup | No branches, worktrees, remote refs, issues or author data retired/deleted |

The local checkout has deliberately shallow history. The exact base/current
trees and commits were verified by their Git hashes; this is not a claim to
hold a complete history backup. Direct GitHub CLI transport was unavailable,
so the connected GitHub interface is used for immutable object transfer and
remote ref/PR read-back. Historical author approvals are evidence only.

## Verification and residual state

See the [verification receipt](../verification/t05-2026-11-05/README.md) for
commands, timestamps, pass/skip counts, initial failed attempts and their
resolution. The per-issue residual map is in
[notes-workflow.md](../notes-workflow.md); the exact T01/T02/T03/T04 interfaces
are in [t05-handoff.md](t05-handoff.md).

Independent private workflow work is complete for draft review. Integrated
reader placement, source-contract acceptance, real release-event wiring,
physical devices/native artifact support and participation activation remain
pending. The shared context packet was inaccessible throughout, and no claim
of account-wide memory or another provider's persistence is made.
