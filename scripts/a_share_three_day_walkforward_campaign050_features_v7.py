#!/usr/bin/env python3
"""Isolated-Campaign049-verifier-repaired Campaign050 audit entrypoint."""

from __future__ import annotations

import importlib.util
import sys

try:
    import scripts.a_share_three_day_walkforward_campaign050_features_v6 as failed
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign050_features_v6 as failed


runner = failed.runner
REPAIR_AUTHORIZATION = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_050_no_return_audit_infrastructure_failure_repair_20260801.json"
)
EXPECTED_FAILED_ENTRYPOINT_SHA256 = (
    "a55bfcd3f69a45502d87e53f64ababe05d311dfdc17705348d80544c22198171"
)
EXPECTED_REPAIR_AUTHORIZATION_SHA256 = (
    "97b21132e090aacaf5821833d35a50a4813dc0e67b5061359a978a936b94ea9f"
)
EXPECTED_CAMPAIGN049_RUNNER_SHA256 = (
    "981378510744bb53bb5353d1bf99ca9850b4f10c49bd8500d38d29994bdeff83"
)

if (
    runner._sha256(runner.Path(failed.__file__).resolve())
    != EXPECTED_FAILED_ENTRYPOINT_SHA256
):
    raise runner.Campaign050FeatureError("Campaign050 frozen v6 entrypoint changed")
if runner._sha256(REPAIR_AUTHORIZATION) != EXPECTED_REPAIR_AUTHORIZATION_SHA256:
    raise runner.Campaign050FeatureError(
        "Campaign050 audit infrastructure repair authorization changed"
    )
if runner._sha256(runner.BASE_FEATURE_RUNNER) != EXPECTED_CAMPAIGN049_RUNNER_SHA256:
    raise runner.Campaign050FeatureError("frozen Campaign049 runner changed")

_isolated_name = "a_share_three_day_campaign050_isolated_campaign049_verifier"
_isolated_spec = importlib.util.spec_from_file_location(
    _isolated_name,
    runner.BASE_FEATURE_RUNNER,
)
if _isolated_spec is None or _isolated_spec.loader is None:
    raise runner.Campaign050FeatureError("isolated Campaign049 verifier could not load")
isolated_campaign049 = importlib.util.module_from_spec(_isolated_spec)
sys.modules[_isolated_name] = isolated_campaign049
_isolated_spec.loader.exec_module(isolated_campaign049)

if (
    isolated_campaign049.FACTOR_NAME != runner.C49_FACTOR_NAME
    or tuple(isolated_campaign049.OUTPUT_COLUMNS)
    != (
        "trade_date",
        "symbol",
        "provider",
        runner.C49_FACTOR_NAME,
        f"{runner.C49_FACTOR_NAME}_eligible",
    )
):
    raise runner.Campaign050FeatureError(
        "isolated Campaign049 verifier semantics changed"
    )

runner._base.verify_snapshot_files = isolated_campaign049.verify_snapshot_files


if __name__ == "__main__":
    raise SystemExit(runner.main())
