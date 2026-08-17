#!/usr/bin/env python3
"""Additive Campaign108 publication-range recovery.

The candidate formula, endpoints, direction, source projection and gates are
unchanged.  This recovery changes only inherited output/manifest eligibility
from ``[0,1]`` to the preregistered ``[-1,1]`` range.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_IMPLEMENTATION = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign108_features.py"
)
BASE_IMPLEMENTATION_SHA256 = (
    "ea1263d86a6ba7d8299dbceb04a63cd1b300af3ade2da6470810466ea15f262f"
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _file_sha256(BASE_IMPLEMENTATION) != BASE_IMPLEMENTATION_SHA256:
    raise RuntimeError("frozen Campaign108 v1 feature implementation changed")


_source = BASE_IMPLEMENTATION.read_text(encoding="utf-8")
_needle = '_source = BASE_RUNNER.read_text(encoding="utf-8")'
_injection = "\n".join(
    [
        _needle,
        '_source = _source.replace("values.ge(0.0) & values.le(1.0)", "values.ge(-1.0) & values.le(1.0)")',
        '_source = _source.replace("{FACTOR_NAME: [0.0, 1.0]}", "{FACTOR_NAME: [-1.0, 1.0]}")',
    ]
)
if _source.count(_needle) != 1:
    raise RuntimeError("Campaign108 v1 generation hook changed")
_source = _source.replace(_needle, _injection)

_impl: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign108_features_v2_generated",
}
exec(compile(_source, str(BASE_IMPLEMENTATION), "exec"), _impl)

_generated = _impl["_generated"]
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_108_no_return_implementation_freeze_v3_20260808.json"
)
FEATURE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign108_features_v2.py"
)
AUDIT_RUNNER_PATH = (
    REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign108_no_return_audit_v2.py"
)
AUDIT_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign108_no_return_audit_v2.py"
)
for _name, _value in {
    "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
    "FEATURE_TEST_PATH": FEATURE_TEST_PATH,
    "AUDIT_RUNNER_PATH": AUDIT_RUNNER_PATH,
    "AUDIT_TEST_PATH": AUDIT_TEST_PATH,
}.items():
    _generated[_name] = _value


Campaign108FeatureError = _impl["Campaign108FeatureError"]
FACTOR_NAME = _impl["FACTOR_NAME"]
FACTOR_FORMULA = _impl["FACTOR_FORMULA"]
RAW_COLUMNS = _impl["RAW_COLUMNS"]
OUTPUT_RUN_ID = _impl["OUTPUT_RUN_ID"]
PROTOCOL_SHA256 = _impl["PROTOCOL_SHA256"]
NUMERIC_COMPARATOR_COUNT = _impl["NUMERIC_COMPARATOR_COUNT"]
NUMERIC_COMPARATOR_ORDER_SHA256 = _impl["NUMERIC_COMPARATOR_ORDER_SHA256"]
COMPLETE_DEFINITION_COUNT = _impl["COMPLETE_DEFINITION_COUNT"]
COMPLETE_DEFINITION_ORDER_SHA256 = _impl["COMPLETE_DEFINITION_ORDER_SHA256"]
DEFAULT_DATA_ROOT = _impl["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL = _impl["DEFAULT_PROTOCOL"]
SOURCE_BAR_COUNT = _impl["SOURCE_BAR_COUNT"]
SELECTED_BAR_COUNT = _impl["SELECTED_BAR_COUNT"]
CONTINUOUS_MINUTE_CODES = _impl["CONTINUOUS_MINUTE_CODES"]
SOURCE_MINUTE_CODE_SET = _impl["SOURCE_MINUTE_CODE_SET"]
IDENTITY_COLUMNS = _impl["IDENTITY_COLUMNS"]
OUTPUT_COLUMNS = _impl["OUTPUT_COLUMNS"]
EXPECTED_ROWS = _impl["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _impl["EXPECTED_PARTITIONS"]
CLEAN_MANIFEST_SHA256 = _impl["CLEAN_MANIFEST_SHA256"]
CLEAN_DATASET_SHA256 = _impl["CLEAN_DATASET_SHA256"]
bindings = _impl["bindings"]
source = _impl["source"]
load_protocol = _impl["load_protocol"]
reconstruct_comparisons = _impl["reconstruct_comparisons"]
reconstruct_complete_definitions = _impl["reconstruct_complete_definitions"]
extract_continuous_session_net_return_reversal = _impl[
    "extract_continuous_session_net_return_reversal"
]
validate_value_semantics = _impl["validate_value_semantics"]
finalize_feature_frame = _generated["finalize_feature_frame"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
empty_output_frame = _generated["empty_output_frame"]


def _validate_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign108FeatureError(
            "Campaign108 recovery implementation freeze is absent"
        )
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    expected_tests = {
        str(FEATURE_TEST_PATH.relative_to(REPO_ROOT)): _file_sha256(FEATURE_TEST_PATH),
        str(AUDIT_TEST_PATH.relative_to(REPO_ROOT)): _file_sha256(AUDIT_TEST_PATH),
    }
    observed_tests = {
        str(item.get("path")): str(item.get("sha256"))
        for item in record.get("synthetic_tests") or []
    }
    boundary = record.get("research_boundary") or {}
    recovery = record.get("recovery") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign108_no_return_implementation_freeze"
        and record.get("status")
        == "additive_range_recovery_frozen_before_snapshot_rebuild_coverage_or_comparator_values"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("feature_builder") or {}).get("sha256")
        == _file_sha256(Path(__file__).resolve())
        and (record.get("ordered_audit_runner") or {}).get("sha256")
        == _file_sha256(AUDIT_RUNNER_PATH)
        and observed_tests == expected_tests
        and record.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and record.get("complete_definition_count") == COMPLETE_DEFINITION_COUNT
        and recovery.get("only_change")
        == "publish and validate the preregistered [-1,1] range instead of inherited [0,1]"
        and recovery.get("candidate_formula_direction_endpoints_or_transform_changed")
        is False
        and boundary.get("failed_build_source_rows_and_candidate_values_read") is True
        and boundary.get("final_snapshot_published_before_recovery_freeze") is False
        and boundary.get("coverage_or_comparator_values_read_before_recovery_freeze")
        is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_recovery_freeze"
        )
        is False
        and boundary.get("provider_request_issued_before_recovery_freeze") is False
    ):
        raise Campaign108FeatureError(
            "Campaign108 recovery implementation freeze changed"
        )
    return record


_generated["_validate_implementation_freeze"] = _validate_implementation_freeze
_order_digest = _impl["_order_digest"]
_sha256 = _generated["_sha256"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
