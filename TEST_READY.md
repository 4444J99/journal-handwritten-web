# TEST_READY — opaque-box witness E2E suite

Suite: `tests/e2e_witness/` (169 checks: 70 Tier 1, 68 Tier 2, 16 Tier 3 pipelines,
8 Tier 4 scenarios, 7 negative controls).

## Verified green

Interpreter prerequisite: the suite's `ci_local.py` cases need a JHW virtualenv with
`rapidfuzz` installed. The main checkout's `.venv` does not have it, so the verified
runs set `E2E_JHW_PYTHON` to a prepared JHW virtualenv (the matcher worktree's `.venv`).
Run from this worktree with `/Volumes/Archive4T/Projects/journal-handwritten-web/.venv/bin/python`
as the runner and `E2E_JHW_PYTHON=/Volumes/Archive4T/Projects/.worktrees/jhw-m2-witness-matcher/.venv/bin/python`:

- `python tools/check.py` — `OK` (511 references, 0 missing; 544 checksums; image tiers 0 problems; 0 bare silent launches).
- `python tests/e2e_witness/run_e2e.py --self-check --tier all --json` — exit 0,
  `total 169, passed 169, failed 0, skipped 0`.
- `E2E_JHW_PYTHON=... python -m unittest discover -s tests/e2e_witness -p "test_*.py"` —
  `Ran 169 tests`, `OK`, 0 skipped.
- Partial-target contract: `env -u E2E_JHW_DIR E2E_TNDC_DIR=/nonexistent/tndc python -m unittest ...`
  fails closed with `TargetContractError` (no silent stub fallback).
- Source hygiene: zero owner-identifying fixture strings in the branch diff/history;
  no modifications to `site/`, `studio/`, `MANIFEST.sha256`, `source/canonical.json`,
  or `release/public.json`.

## Findings closed

1. Shared-surface isolation: crop geometry and on-disk JPEG dimensions are checked against
   co-tenant raw boxes; near-full-page crops and manifest-spoofed uncropped exports are rejected.
2. Partial target environment: `TargetConfig.from_env()` raises on exactly one of
   `E2E_TNDC_DIR`/`E2E_JHW_DIR`; `jhw_python()` no longer falls back to a bare system interpreter.
3. Weak target assertions: Two-Clock invariance is asserted in `T1-F11-03`, tracebacks are
   rejected in `T2-F08-03`/`T3-P06`, permissive permission-denial fallbacks were removed, and
   target CLI/manifest contracts are documented in `TEST_INFRA.md`.
4. Stub-env coupling / live-provider risk: ephemeral `tndc_shims.py` injects synthetic
   provider templates only in real-target mode when fixture env vars are present, so no test
   harvests the host's live Photos or Notes library.

## Scope of this readiness claim

This file certifies the **self-check and fail-closed target-contract** modes listed above.
It does **not** claim a green real-target run against integrated M1+M2+M3: that run would
require the author's live harvest choice, and the fake `osascript` is an interface-modeled
JXA-output stand-in rather than a full interpreter. `T1-F04-*`, `T1-F05-*`, and
`T3-P01..03` still assert fixture-specific values through that stand-in; they must be
exercised against the final capture CLI shape before a full real-target claim is made.

No live harvest, link confirmation, or remote state is claimed by this document.
