#!/usr/bin/env python3
"""Standalone opaque-box E2E runner for the two-repo witness ingestion & chronology pipeline."""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import unittest
from pathlib import Path

# Support direct execution (`python3 tests/e2e_witness/run_e2e.py`) as well as `-m`
_SUITE_ROOT = Path(__file__).resolve().parents[2]
if str(_SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SUITE_ROOT))

from tests.e2e_witness.cli_adapters import (  # noqa: E402
    CliAdapter,
    TargetConfig,
    TargetContractError,
    set_target_config,
)
from tests.e2e_witness.tier1_features import Tier1FeatureTests  # noqa: E402
from tests.e2e_witness.tier2_boundaries import Tier2BoundaryTests  # noqa: E402
from tests.e2e_witness.tier3_4_pipelines import (  # noqa: E402
    NegativeControlTests,
    Tier3PairwiseTests,
    Tier4ScenarioTests,
)


def _filter_suite(suite: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    if not pattern:
        return suite
    filtered = unittest.TestSuite()
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            sub = _filter_suite(item, pattern)
            if sub.countTestCases() > 0:
                filtered.addTest(sub)
        elif pattern in item.id():
            filtered.addTest(item)
    return filtered


def build_suite(tier: str, name_filter: str | None = None) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    if tier in ("1", "all"):
        suite.addTests(loader.loadTestsFromTestCase(Tier1FeatureTests))
    if tier in ("2", "all"):
        suite.addTests(loader.loadTestsFromTestCase(Tier2BoundaryTests))
    if tier in ("3", "all"):
        suite.addTests(loader.loadTestsFromTestCase(Tier3PairwiseTests))
    if tier in ("4", "all"):
        suite.addTests(loader.loadTestsFromTestCase(Tier4ScenarioTests))
    if tier == "all":
        suite.addTests(loader.loadTestsFromTestCase(NegativeControlTests))
    return _filter_suite(suite, name_filter)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the opaque-box E2E witness suite (Tiers 1-4 + Negative Controls)."
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Validate suite using subprocess reference CLI stubs + real corpus/check.py",
    )
    parser.add_argument(
        "--tndc-dir",
        default=os.environ.get("E2E_TNDC_DIR") or None,
        help="Path to tool-notes-docs-capture checkout/worktree",
    )
    parser.add_argument(
        "--jhw-dir",
        default=os.environ.get("E2E_JHW_DIR") or None,
        help="Path to journal-handwritten-web checkout/worktree",
    )
    parser.add_argument(
        "--tndc-subcmd",
        default=os.environ.get("E2E_TNDC_SUBCMD") or None,
        help="Explicit TNDC witness subcommand name (auto-discovered if omitted)",
    )
    parser.add_argument(
        "--tndc-git-override-flag",
        default=os.environ.get("E2E_TNDC_GIT_OVERRIDE_FLAG") or None,
        help="Explicit TNDC git-tree test override flag",
    )
    parser.add_argument(
        "--jhw-python",
        default=os.environ.get("E2E_JHW_PYTHON") or None,
        help="Explicit JHW virtualenv python (default: <jhw-dir>/.venv/bin/python)",
    )
    parser.add_argument(
        "--tier",
        choices=("1", "2", "3", "4", "all"),
        default="all",
        help="Tier subset to run (default: all)",
    )
    parser.add_argument(
        "--filter",
        default=None,
        help="Substring filter on test ID (e.g. T1_F01_01)",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON summary")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose unittest output")
    args = parser.parse_args(argv)

    if args.self_check:
        jhw_path = Path(args.jhw_dir).resolve() if args.jhw_dir else _SUITE_ROOT
        tndc_path = Path(args.tndc_dir).resolve() if args.tndc_dir else None
        cfg = TargetConfig(
            self_check=True,
            jhw_dir=jhw_path,
            tndc_dir=tndc_path,
            tndc_subcmd=args.tndc_subcmd,
            tndc_git_override_flag=args.tndc_git_override_flag,
            jhw_python=Path(args.jhw_python) if args.jhw_python else None,
        )
    else:
        if not args.tndc_dir or not args.jhw_dir:
            sys.stderr.write(
                "ERROR: Strict target mode requires both --tndc-dir and --jhw-dir "
                "(or pass --self-check explicitly).\n"
            )
            return 2
        cfg = TargetConfig(
            self_check=False,
            jhw_dir=Path(args.jhw_dir).resolve(),
            tndc_dir=Path(args.tndc_dir).resolve(),
            tndc_subcmd=args.tndc_subcmd,
            tndc_git_override_flag=args.tndc_git_override_flag,
            jhw_python=Path(args.jhw_python) if args.jhw_python else None,
        )

    try:
        CliAdapter(cfg, suite_root=_SUITE_ROOT)
    except TargetContractError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}))
        else:
            sys.stderr.write(f"TARGET CONTRACT ERROR: {exc}\n")
        return 1

    set_target_config(cfg)
    suite = build_suite(args.tier, args.filter)

    stream = io.StringIO() if args.json else sys.stdout
    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(stream=stream, verbosity=verbosity)
    result = runner.run(suite)

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    skipped = len(result.skipped)
    passed = total - failed - skipped
    ok = result.wasSuccessful() and skipped == 0 and total > 0

    if args.json:
        summary = {
            "ok": ok,
            "mode": "self_check" if cfg.self_check else "real_target",
            "tier": args.tier,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "failures": [
                {"test": t.id(), "trace": tb} for t, tb in (result.failures + result.errors)
            ],
        }
        print(json.dumps(summary, indent=2))
    else:
        print(
            f"\nE2E SUMMARY ({'self-check' if cfg.self_check else 'real-target'}, tier={args.tier}): "
            f"total={total} passed={passed} failed={failed} skipped={skipped}"
        )

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
