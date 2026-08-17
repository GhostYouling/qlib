#!/usr/bin/env python3
"""Campaign109 additive recovery: bind the generated loader to the frozen extractor."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign109_features as base


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_109_no_return_implementation_freeze_v2_20260808.json"
)
FEATURE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign109_features_v2.py"
)
AUDIT_RUNNER_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign109_no_return_audit_v2.py"
)
AUDIT_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign109_no_return_audit_v2.py"
)


def _validate_recovery_implementation_freeze() -> dict[str, object]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise base.Campaign109FeatureError(
            "Campaign109 recovery implementation freeze is absent"
        )
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    tests = record.get("synthetic_tests") or []
    observed_tests = {
        str(item.get("path")): str(item.get("sha256")) for item in tests
    }
    expected_tests = {
        str(FEATURE_TEST_PATH.relative_to(REPO_ROOT)): base._sha256(FEATURE_TEST_PATH),
        str(AUDIT_TEST_PATH.relative_to(REPO_ROOT)): base._sha256(AUDIT_TEST_PATH),
    }
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign109_no_return_implementation_freeze"
        and record.get("status")
        == "additive_symbol_binding_recovery_frozen_after_failed_source_read_before_rebuild_coverage_or_comparator_values"
        and (record.get("protocol") or {}).get("sha256") == base.PROTOCOL_SHA256
        and (record.get("original_implementation_freeze") or {}).get("sha256")
        == "283787eee2a97053f7ee9af6ddc34a10a1f7d89d84b64002ace25610548ac72b"
        and (record.get("failed_build") or {}).get("sha256")
        == "f001229cb831bc829b591abdbd1bd6916673c438a971e15bfd09ed4554f3c6e6"
        and (record.get("feature_builder") or {}).get("sha256")
        == base._sha256(Path(__file__).resolve())
        and (record.get("ordered_audit_runner") or {}).get("sha256")
        == base._sha256(AUDIT_RUNNER_PATH)
        and observed_tests == expected_tests
        and record.get("numeric_comparator_count")
        == base.NUMERIC_COMPARATOR_COUNT
        and record.get("numeric_comparator_order_sha256")
        == base.NUMERIC_COMPARATOR_ORDER_SHA256
        and record.get("complete_definition_count")
        == base.COMPLETE_DEFINITION_COUNT
        and record.get("complete_definition_order_sha256")
        == base.COMPLETE_DEFINITION_ORDER_SHA256
        and boundary.get("candidate_source_rows_read_before_recovery_freeze") is True
        and boundary.get(
            "partial_candidate_values_may_have_been_computed_before_recovery_freeze"
        )
        is True
        and boundary.get("candidate_values_published_before_recovery_freeze")
        is False
        and boundary.get("coverage_or_comparator_values_read_before_recovery_freeze")
        is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_recovery_freeze"
        )
        is False
        and boundary.get("provider_request_issued_before_recovery_freeze") is False
    ):
        raise base.Campaign109FeatureError(
            "Campaign109 recovery implementation freeze changed"
        )
    return record


# The first frozen build exposed that the source-to-source rewrite had created this
# longer generated name before the intended replacement was applied.  Bind exactly
# that generated lookup to the already frozen Campaign109 implementation.
base._generated["extract_intrabar_body_magnitude_serial_persistence"] = (
    base.extract_body_magnitude_serial_persistence
)
base._generated["__file__"] = str(Path(__file__).resolve())
base._generated["DEFAULT_IMPLEMENTATION_FREEZE"] = DEFAULT_IMPLEMENTATION_FREEZE
base._generated["FEATURE_TEST_PATH"] = FEATURE_TEST_PATH
base._generated["AUDIT_RUNNER_PATH"] = AUDIT_RUNNER_PATH
base._generated["AUDIT_TEST_PATH"] = AUDIT_TEST_PATH
base._generated["_validate_implementation_freeze"] = (
    _validate_recovery_implementation_freeze
)

# Keep attributes observed by the no-return runner aligned with the generated
# function globals.  No scientific or data semantics are changed here.
base.DEFAULT_IMPLEMENTATION_FREEZE = DEFAULT_IMPLEMENTATION_FREEZE
base.FEATURE_TEST_PATH = FEATURE_TEST_PATH
base.AUDIT_RUNNER_PATH = AUDIT_RUNNER_PATH
base.AUDIT_TEST_PATH = AUDIT_TEST_PATH
base._validate_implementation_freeze = _validate_recovery_implementation_freeze


Campaign109FeatureError = base.Campaign109FeatureError
FACTOR_NAME = base.FACTOR_NAME
FACTOR_FORMULA = base.FACTOR_FORMULA
RAW_COLUMNS = base.RAW_COLUMNS
OUTPUT_RUN_ID = base.OUTPUT_RUN_ID
DEFAULT_PROTOCOL = base.DEFAULT_PROTOCOL
DEFAULT_DATA_ROOT = base.DEFAULT_DATA_ROOT
OUTPUT_COLUMNS = base.OUTPUT_COLUMNS
EXPECTED_ROWS = base.EXPECTED_ROWS
EXPECTED_PARTITIONS = base.EXPECTED_PARTITIONS
CLEAN_MANIFEST_SHA256 = base.CLEAN_MANIFEST_SHA256
CLEAN_DATASET_SHA256 = base.CLEAN_DATASET_SHA256
NUMERIC_COMPARATOR_COUNT = base.NUMERIC_COMPARATOR_COUNT
NUMERIC_COMPARATOR_ORDER_SHA256 = base.NUMERIC_COMPARATOR_ORDER_SHA256
COMPLETE_DEFINITION_COUNT = base.COMPLETE_DEFINITION_COUNT
COMPLETE_DEFINITION_ORDER_SHA256 = base.COMPLETE_DEFINITION_ORDER_SHA256
bindings = base.bindings
source = base.source
_generated = base._generated
_sha256 = base._sha256
load_protocol = base.load_protocol
reconstruct_comparisons = base.reconstruct_comparisons
reconstruct_complete_definitions = base.reconstruct_complete_definitions
compute_body_magnitude_serial_persistence = (
    base.compute_body_magnitude_serial_persistence
)
extract_body_magnitude_serial_persistence = (
    base.extract_body_magnitude_serial_persistence
)
validate_value_semantics = base.validate_value_semantics
output_root = base.output_root
build_snapshot = base.build_snapshot
verify_snapshot_files = base.verify_snapshot_files
_validate_implementation_freeze = _validate_recovery_implementation_freeze
status = base.status
main = base.main


if __name__ == "__main__":
    raise SystemExit(main())
