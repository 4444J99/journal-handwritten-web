# Studio publish implementation ledger

Source plan: .codex/plans/2026-11-06-studio-publish.md
Base: 9939f2098fcf65e9fd009f9cf970c10064ea44b8
Branch: feat/studio-publish-20261106

Pre-flight: shell hash and atlas format produced in phases 0/1 are consumed by the builder, validator, preview, and public reader. The source index and review IDs must preserve Python parity. Confirmation must bind all files, target, source revisions, and previous pointer; release records require retry-safe recovery.

Ruling: implementation authorization covers the supplied architecture; author wording choices and first-poem confirmation remain explicit owner actions. Preserve current authored wording, filter PAL/HF per snapshot, retain Python fallback, and do not publish a poem on the author's behalf.

Phase 0: investigating existing atlas support, free-plan CPU, authenticated Cloudflare access, and existing bindings.

Phase 0 evidence: synthetic hosted Pages spike a4d2343a-4d83-4d1d-bb32-9208d9d4d301 measured 24 ms CPU for one published page and 166 ms for 123. Signed-in dashboard shows Workers Free. Operator asked whether it can be MacGyvered; proceeding with browser compilation and per-piece/per-page server verification, no billing change.

Ruling: atlas tiles retain exact decoded source pixels using PNG bytes under the engine's existing .jpg routes, served as image/png. This avoids a second lossy JPEG encoding; canonical data parity normalizes only the planned atlas layout. Cost if wrong: a client that ignores MIME/magic cannot decode tiles; real browser and Pages checks are required.

Upstream reconciliation: merged origin/main 1c48ff5 (PR 136) into the feature branch. Reused its public metadata policy and diary1 mapping fix, avoiding duplicate implementations. Author explicitly chose filtering unpublished page IDs, blank optional font provenance while preserving license notices, and removal of the global public status line.

Local checks: compiler gate/adversarial tests, five synthetic Python/JS release-list parity cases, metadata/privacy package tests, immutable history export/restore, client sequencing, storage races/tamper/forged-browser-output tests pass. Local actual Pages + D1/R2 flow passes through browser compile, bounded verification, preview, confirm, automatic staging exposure, and a separately configured public reader.

Root cause resolved: Pages redirects shell.html to /publish/shell (308); use the canonical URL. Nested staging imports made the local compiler select the parent production configuration; standalone staging library and package root produce the correct staging bucket. Hosted staging bindings were independently verified as staging throughout.

Remaining: real-export parity receipt, hosted bounded CPU traces, browser UI verification, final review, PRs and deployed Studio; owner-only first-poem confirm and physical-device acceptance remain separate.
