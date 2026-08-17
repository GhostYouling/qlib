from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign108_features_v2 as recovery


def test_finalization_preserves_negative_zero_positive_and_missing_scores() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
            ),
            "symbol": ["000001.SZ"] * 4,
            "provider": ["tushare"] * 4,
            "continuous_session_net_return_reversal": [-0.5, 0.0, 0.5, np.nan],
        }
    )
    out = recovery.finalize_feature_frame(frame)
    assert out[recovery.FACTOR_NAME].tolist()[:3] == [-0.5, 0.0, 0.5]
    assert out[recovery.FACTOR_NAME].isna().tolist() == [False, False, False, True]
    assert out[f"{recovery.FACTOR_NAME}_eligible"].tolist() == [
        True,
        True,
        True,
        False,
    ]


def test_manifest_validator_requires_preregistered_negative_one_to_one_range() -> None:
    generated = recovery._generated
    old_partitions = generated["EXPECTED_PARTITIONS"]
    old_rows = generated["EXPECTED_ROWS"]
    generated["EXPECTED_PARTITIONS"] = 0
    generated["EXPECTED_ROWS"] = 0
    try:
        manifest = {
            "kind": "a_share_three_day_walkforward_campaign108_feature_snapshot",
            "status": "feature_library_complete_pending_ordered_no_return_gates",
            "output_run_id": recovery.OUTPUT_RUN_ID,
            "partitions": 0,
            "rows": 0,
            "files": [],
            "factor_names": [recovery.FACTOR_NAME],
            "factor_directions": {recovery.FACTOR_NAME: "higher"},
            "factor_ranges": {recovery.FACTOR_NAME: [-1.0, 1.0]},
            "factor_formulas": {recovery.FACTOR_NAME: recovery.FACTOR_FORMULA},
            "factor_eligible_rows": {recovery.FACTOR_NAME: 0},
            "source_fields_read": list(recovery.RAW_COLUMNS),
            "joint_clean_identity_fields_read": list(recovery.IDENTITY_COLUMNS),
            "source_rows_required_per_session": recovery.SOURCE_BAR_COUNT,
            "source_selected_bar_count": recovery.SELECTED_BAR_COUNT,
            "minimum_active_bar_count": 0,
            "positive_total_activity_required": False,
            "activity_magnitude_used": False,
            "raw_manifest_sha256": generated["RAW_MANIFEST_SHA256"],
            "joint_clean_manifest_sha256": recovery.CLEAN_MANIFEST_SHA256,
            "joint_clean_dataset_sha256": recovery.CLEAN_DATASET_SHA256,
            "protocol_sha256": recovery.PROTOCOL_SHA256,
            "mechanism_support_audit_sha256": generated["MECHANISM_AUDIT_SHA256"],
            "quality": {
                "base_rows": 0,
                f"{recovery.FACTOR_NAME}__eligible_rows": 0,
                f"{recovery.FACTOR_NAME}__missing_rows": 0,
            },
            "daily_price_fields_read": [],
            "forward_return_fields_read": False,
            "comparison_factor_values_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
        }
        generated["_validate_manifest"](manifest)
        manifest["factor_ranges"] = {recovery.FACTOR_NAME: [0.0, 1.0]}
        with pytest.raises(recovery.Campaign108FeatureError):
            generated["_validate_manifest"](manifest)
    finally:
        generated["EXPECTED_PARTITIONS"] = old_partitions
        generated["EXPECTED_ROWS"] = old_rows


def test_recovery_is_bound_to_preserved_failure_and_absent_snapshot() -> None:
    failure = (
        recovery.REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_108_negative_range_publication_failure_20260808.json"
    )
    record = json.loads(failure.read_text(encoding="utf-8"))
    assert (
        record["failed_implementation"]["sha256"] == recovery.BASE_IMPLEMENTATION_SHA256
    )
    assert record["failure_evidence"]["final_snapshot_root_published"] is False
    assert not recovery.output_root(recovery.DEFAULT_DATA_ROOT).exists()


def test_v2_implementation_freeze_is_live() -> None:
    freeze = recovery._validate_implementation_freeze()
    assert freeze["recovery"]["only_change"] == (
        "publish and validate the preregistered [-1,1] range instead of inherited [0,1]"
    )
    boundary = freeze["research_boundary"]
    assert boundary["failed_build_source_rows_and_candidate_values_read"] is True
    assert boundary["final_snapshot_published_before_recovery_freeze"] is False
    assert (
        boundary["coverage_or_comparator_values_read_before_recovery_freeze"] is False
    )
