# Repository lifecycle reconciliation

Scope: 4444J99/journal-handwritten-web and 4444J99/versforms. Authority: author's 7 November request to reconcile/merge branches, get tests green and clean up, including Variorum work.

Initial inventory: source47 remote branches, reader4; no open PRs, no stashes, one worktree each, clean trees. Ancestry alone is insufficient because many completed PRs used squash merges. Inventory JSON records exact branch tips, accepted heads and merge IDs. Protection detail endpoint is inaccessible to this integration (403); live merge requirements must still be honored, never bypassed.

Preservation: full bundles were independently restored with all refs identical and fsck passing. Remote archive/branches-2026-11-07 tags preserve every inventoried original tip/history. Archive receipts map original refs to tips and the surviving archive commit. No LFS/submodules are configured; generated scratch and dependency caches are retained locally and excluded from retirement. Recovery bundles remain /workspace/repository-recovery/2026-11-07.

Dispositions: branches with exact accepted merged heads or proven target ancestry are completed. alive-prototype and its WIP snapshots are superseded by merged#134 (closed#102 explicitly records preservation). Old integrity-check bot branch is superseded/rejected in favor of merged#114 (closed#2 explains unsafe old tests). post-poem-hardening-wip is superseded by completed hardening#123/#133. Early t03 release-packet is superseded by merged#119 and its current source contract. Preserve original lineage in the recovery tag rather than merging old file contents over newer implementations. playground is retained active because the named preview deployment consumes it; its code is already on main.

CI findings: latest Actions check never started; GitHub annotation cites failed account payments/spending limit. Do not hide/disable it or treat local status as a hosted run. Local timeout regression false failure occurs because killed descendant remains zombie under this container PID1. Fixture now reaps its child on group termination while still detecting a live child if only the leader is killed. Existing browser-permalink test supports CHROME_BIN for Linux.

Status: in progress; exact merges, checks, retirement actions and final parity are recorded on closeout.
