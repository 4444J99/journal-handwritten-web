# 2026-11-25 E2E witness suite remediation

## Produced
- Hardened `tests/e2e_witness/`: shared-surface isolation now validates crop geometry,
  on-disk JPEG size and co-tenant raw-box non-overlap; `TargetConfig.from_env()` fails
  closed on partial target env and `jhw_python()` refuses a bare system interpreter;
  Two-Clock `T1-F11-03` invariants, crash/traceback rejection in `T2-F08-03`/`T3-P06`,
  and fail-closed ephemeral provider shims (`tndc_shims.py`) for real-target fixture runs.
- Added `TEST_INFRA.md` with the target CLI / `projection_manifest.json` contracts.
- Replaced private owner-identifying fixture strings and rewrote the branch to one clean
  commit off `origin/main` (`b2b92b7`).

## Author decisions
- No new author decisions in this session; remediation followed the evidence reports from
  the adversarial challenge and two explorer investigations.

## Plan / next steps
- Plan (suggested): run the integrated M1 + M2 + M3 real-target pass in the Final Milestone;
  the ephemeral shims must be exercised against the final TNDC CLI shape before release.

## Status
- Self-check green (169/169, 0 skipped), `tools/check.py` OK, unittest discovery OK,
  partial-env probe fails closed with `TargetContractError`, owner strings absent from
  `git diff origin/main..HEAD` and `git log -p origin/main..HEAD`.
