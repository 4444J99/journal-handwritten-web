"""Unittest load_tests entrypoint for tools/ci_local.py and unittest discover."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

if __package__:
    from .cli_adapters import CliAdapter, TargetConfig, set_target_config
    from .tier1_features import Tier1FeatureTests
    from .tier2_boundaries import Tier2BoundaryTests
    from .tier3_4_pipelines import (
        NegativeControlTests,
        Tier3PairwiseTests,
        Tier4ScenarioTests,
    )
else:
    _SUITE_ROOT = Path(__file__).resolve().parents[2]
    if str(_SUITE_ROOT) not in sys.path:
        sys.path.insert(0, str(_SUITE_ROOT))
    from tests.e2e_witness.cli_adapters import CliAdapter, TargetConfig, set_target_config
    from tests.e2e_witness.tier1_features import Tier1FeatureTests
    from tests.e2e_witness.tier2_boundaries import Tier2BoundaryTests
    from tests.e2e_witness.tier3_4_pipelines import (
        NegativeControlTests,
        Tier3PairwiseTests,
        Tier4ScenarioTests,
    )


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    del tests, pattern
    suite_root = Path(__file__).resolve().parents[2]
    cfg = TargetConfig.from_env(suite_root)
    # Validate the target contract at discovery time: partial env, missing dirs,
    # missing CLIs, or a missing virtualenv must fail closed before any test runs.
    CliAdapter(cfg, suite_root=suite_root)
    set_target_config(cfg)

    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(Tier1FeatureTests))
    suite.addTests(loader.loadTestsFromTestCase(Tier2BoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(Tier3PairwiseTests))
    suite.addTests(loader.loadTestsFromTestCase(Tier4ScenarioTests))
    suite.addTests(loader.loadTestsFromTestCase(NegativeControlTests))
    return suite
