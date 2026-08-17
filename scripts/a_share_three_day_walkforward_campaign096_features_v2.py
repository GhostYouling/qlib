#!/usr/bin/env python3
"""Quality-schema compatibility adapter for frozen Campaign096 v1 values."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign096_features as v1

REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_096_feature_build_quality_alias_repair_protocol_20260807.json"
)
IMPLEMENTATION_FREEZE_V2 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_096_feature_implementation_freeze_v2_20260807.json"
)
TEST_PATH_V2 = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign096_features_v2.py"
)

_generated = v1._generated
_extract_v1 = v1.extract_intrabar_close_location_total_variation


def extract_intrabar_close_location_total_variation(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Return v1 values plus the one inherited quality-key compatibility alias."""

    frame, quality_v1 = _extract_v1(raw, symbol=symbol)
    quality = dict(quality_v1)
    if "zero_destination_range_pairs" in quality:
        raise v1.Campaign096FeatureError("Campaign096 v1 quality alias unexpectedly exists")
    if "zero_range_bars" not in quality:
        raise v1.Campaign096FeatureError("Campaign096 v1 zero-range quality count absent")
    quality["zero_destination_range_pairs"] = int(quality["zero_range_bars"])
    return frame, quality


_generated["extract_directional_amount_timing_spread"] = (
    extract_intrabar_close_location_total_variation
)
_generated["DEFAULT_IMPLEMENTATION_FREEZE"] = IMPLEMENTATION_FREEZE_V2
_generated["TEST_PATH"] = TEST_PATH_V2
_generated["__file__"] = str(Path(__file__).resolve())

Campaign096FeatureError = v1.Campaign096FeatureError
FACTOR_NAME = v1.FACTOR_NAME
FACTOR_FORMULA = v1.FACTOR_FORMULA
RAW_COLUMNS = v1.RAW_COLUMNS
SELECTED_BAR_COUNT = v1.SELECTED_BAR_COUNT
PAIR_OPPORTUNITY_COUNT = v1.PAIR_OPPORTUNITY_COUNT
MINIMUM_INFORMATIVE_PAIRS = v1.MINIMUM_INFORMATIVE_PAIRS
ENDPOINT_TOLERANCE = v1.ENDPOINT_TOLERANCE
C95_SEMANTIC_DEFINITION = v1.C95_SEMANTIC_DEFINITION
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL = _generated["DEFAULT_PROTOCOL"]
DEFAULT_IMPLEMENTATION_FREEZE = IMPLEMENTATION_FREEZE_V2
PROTOCOL_SHA256 = _generated["PROTOCOL_SHA256"]
MECHANISM_AUDIT_SHA256 = _generated["MECHANISM_AUDIT_SHA256"]
CURRENT_STATE_SHA256 = _generated["CURRENT_STATE_SHA256"]
NUMERIC_POLICY_SHA256 = _generated["NUMERIC_POLICY_SHA256"]
FULL_DEFINITION_COUNT = _generated["FULL_DEFINITION_COUNT"]
FULL_DEFINITION_ORDER_SHA256 = _generated["FULL_DEFINITION_ORDER_SHA256"]
COMPARISON_COUNT = _generated["COMPARISON_COUNT"]
COMPARISON_ORDER_SHA256 = _generated["COMPARISON_ORDER_SHA256"]
OUTPUT_COLUMNS = _generated["OUTPUT_COLUMNS"]
TEST_PATH = TEST_PATH_V2
compute_intrabar_close_location_total_variation = (
    v1.compute_intrabar_close_location_total_variation
)
load_protocol = v1.load_protocol
reconstruct_comparisons = v1.reconstruct_comparisons
reconstruct_complete_definitions = v1.reconstruct_complete_definitions
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
status = _generated["status"]
main = _generated["main"]
_comparison_order_digest = _generated["_comparison_order_digest"]


def __getattr__(name: str) -> Any:
    if name in _generated:
        return _generated[name]
    return getattr(v1, name)


if __name__ == "__main__":
    raise SystemExit(main())
