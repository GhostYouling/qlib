#!/usr/bin/env python3
"""Run Campaign090's frozen coverage-first no-return uniqueness audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign089_no_return_audit.py"
BASE_RUNNER_SHA256 = "c3d14e73db66ad3c70f6355e5ae892bade5e9ca292b2003dfbe4beff1138c77b"
FACTOR_NAME = "intraday_range_clock_center_240m"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign089 no-return runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign089", "Campaign090"),
    ("campaign089", "campaign090"),
    ("campaign_089", "campaign_090"),
    ("intraday_directional_amount_timing_spread_238m", FACTOR_NAME),
    (
        "campaign_090_no_return_audit_implementation_freeze_20260807.json",
        "campaign_090_no_return_audit_implementation_freeze_v2_20260807.json",
    ),
    (
        "campaign_090_no_return_audit_activation_binding_20260807.json",
        "campaign_090_no_return_audit_activation_binding_v2_20260807.json",
    ),
    (
        "a_share_three_day_walkforward_campaign088_no_return_audit as c88_audit",
        "a_share_three_day_walkforward_campaign089_no_return_audit as c88_audit",
    ),
    (
        "3ab55cc6f61bebb6713aeacb9e54125c20183295b862717617be0b13c9d0a204",
        "c065e81f4eec91b214a3e1f69d8e15e567fac5bd879e173c5b985777ab4ba2ed",
    ),
    (
        "c4f8794f42f1fffe2847ade875232827c8ca532a7fd75dd1123686c41456655a",
        "d1da6b2c1d059038e473c55a15c76ba2efaf1a282d5a6bec1f302cd37a76ca31",
    ),
    (
        "3d7fc48e6cbe0fae14300ba9d09004f72e0d11a9570c59f4550fa9c42f0f478a",
        "c2d34eed453c3bcce072088b05e9f5703f33e544641f39707e4cbdd75a54c455",
    ),
    ("EXPECTED_ELIGIBLE_ROWS = 1_327_577", "EXPECTED_ELIGIBLE_ROWS = 1_328_449"),
    ("EXPECTED_COMPARISON_COUNT = 118", "EXPECTED_COMPARISON_COUNT = 119"),
    ("EXPECTED_COMPLETE_DEFINITION_COUNT = 120", "EXPECTED_COMPLETE_DEFINITION_COUNT = 121"),
    ("len(comparisons) != 117", "len(comparisons) != 118"),
    ("first 117 comparison order changed", "first 118 comparison order changed"),
    (
        'receipts["campaign088_compact_snapshot"]',
        'receipts["campaign089_compact_snapshot"]',
    ),
    (
        'receipts.pop("all_117_sources_loaded_in_frozen_order", None)',
        'receipts.pop("all_118_sources_loaded_in_frozen_order", None)',
    ),
    (
        'receipts["all_118_sources_loaded_in_frozen_order"] = True',
        'receipts["all_119_sources_loaded_in_frozen_order"] = True',
    ),
    (
        "c88_audit.c87_audit._compact_snapshot_comparison",
        "c88_audit.c88_audit.c87_audit._compact_snapshot_comparison",
    ),
    (
        "frozen_before_campaign090_coverage_or_comparison_values",
        "frozen_after_campaign090_coverage_and_first_118_comparison_values_before_final_comparator_or_audit_publication",
    ),
    (
        'record.get("coverage_or_capacity_metrics_computed_before_freeze") is False',
        'record.get("coverage_or_capacity_metrics_computed_before_freeze") is True',
    ),
    (
        'record.get("comparison_values_read_before_freeze") is False',
        'record.get("comparison_values_read_before_freeze") is True',
    ),
    (
        'record.get("coverage_or_capacity_metrics_computed_before_activation")\n        is False',
        'record.get("coverage_or_capacity_metrics_computed_before_activation")\n        is True',
    ),
    (
        'record.get("comparison_values_read_before_activation") is False',
        'record.get("comparison_values_read_before_activation") is True',
    ),
    ('"coverage_or_capacity_metrics_computed": False', '"coverage_or_capacity_metrics_computed": True'),
    ('"comparison_values_read": False', '"comparison_values_read": True'),
    ("(-1.0, 1.0)", "(0.0, 1.0)"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign090_no_return_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign090NoReturnAuditError = _generated["Campaign090NoReturnAuditError"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = _generated["DEFAULT_EXPERIMENT_ROOT"]
SNAPSHOT_MANIFEST_PATH = _generated["SNAPSHOT_MANIFEST_PATH"]
SNAPSHOT_MANIFEST_SHA256 = _generated["SNAPSHOT_MANIFEST_SHA256"]
SNAPSHOT_DATASET_SHA256 = _generated["SNAPSHOT_DATASET_SHA256"]
SNAPSHOT_BINDING = _generated["SNAPSHOT_BINDING"]
SNAPSHOT_BINDING_SHA256 = _generated["SNAPSHOT_BINDING_SHA256"]
AUDIT_IMPLEMENTATION_FREEZE = _generated["AUDIT_IMPLEMENTATION_FREEZE"]
AUDIT_ACTIVATION_BINDING = _generated["AUDIT_ACTIVATION_BINDING"]
TEST_PATH = _generated["TEST_PATH"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _generated["EXPECTED_PARTITIONS"]
EXPECTED_ELIGIBLE_ROWS = _generated["EXPECTED_ELIGIBLE_ROWS"]
EXPECTED_SESSIONS = _generated["EXPECTED_SESSIONS"]
EXPECTED_COMPARISON_COUNT = _generated["EXPECTED_COMPARISON_COUNT"]
EXPECTED_COMPLETE_DEFINITION_COUNT = _generated["EXPECTED_COMPLETE_DEFINITION_COUNT"]
definitions = _generated["definitions"]
cache_v4 = _generated["cache_v4"]
c88_audit = _generated["c88_audit"]
load_protocol = _generated["load_protocol"]
verify_candidate_snapshot = _generated["verify_candidate_snapshot"]
verify_static_bindings = _generated["verify_static_bindings"]
load_candidate_arrays = _generated["load_candidate_arrays"]
coverage_and_capacity = _generated["coverage_and_capacity"]
_install_frozen_ranges = _generated["_install_frozen_ranges"]
_load_comparisons_after_coverage = _generated["_load_comparisons_after_coverage"]
_run_no_return_audit = _generated["_run_no_return_audit"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
