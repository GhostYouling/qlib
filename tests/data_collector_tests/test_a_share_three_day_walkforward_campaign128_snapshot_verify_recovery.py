from __future__ import annotations

import copy

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign128_snapshot_verify_recovery as recovery,
)


def _manifest() -> dict:
    c128 = recovery.c128
    eligible = c128.EXPECTED_ROWS - 1
    return {
        "kind": "a_share_three_day_walkforward_campaign128_feature_snapshot",
        "status": "feature_library_complete_pending_ordered_no_return_gates",
        "output_run_id": c128.OUTPUT_RUN_ID,
        "dataset_sha256": "0" * 64,
        "partitions": c128.EXPECTED_PARTITIONS,
        "rows": c128.EXPECTED_ROWS,
        "files": [{}] * c128.EXPECTED_PARTITIONS,
        "factor_names": [c128.FACTOR_NAME],
        "factor_directions": {c128.FACTOR_NAME: "higher"},
        "factor_ranges": {c128.FACTOR_NAME: [-1.0, 1.0]},
        "factor_formulas": {c128.FACTOR_NAME: c128.FACTOR_FORMULA},
        "factor_eligible_rows": {c128.FACTOR_NAME: eligible},
        "quality": {
            "base_rows": c128.EXPECTED_ROWS,
            f"{c128.FACTOR_NAME}__eligible_rows": eligible,
            f"{c128.FACTOR_NAME}__missing_rows": 1,
        },
        "source_fields_read": list(c128.RAW_COLUMNS),
        "joint_clean_identity_fields_read": list(c128.IDENTITY_COLUMNS),
        "source_rows_required_per_session": c128.SOURCE_BAR_COUNT,
        "source_selected_bar_count": c128.SELECTED_BAR_COUNT,
        "source_half_bar_count": c128.formula.HALF_BAR_COUNT,
        "minimum_active_bars_per_half": c128.formula.MINIMUM_ACTIVE_BARS_PER_HALF,
        "joint_zero_volume_amount_policy": "inactive",
        "one_sided_zero_policy": "stock_day_invalid",
        "nonpositive_half_iqr_policy": "missing_without_epsilon_or_fallback",
        "raw_manifest_sha256": c128.RAW_MANIFEST_SHA256,
        "joint_clean_manifest_sha256": c128.CLEAN_MANIFEST_SHA256,
        "joint_clean_dataset_sha256": c128.CLEAN_DATASET_SHA256,
        "protocol_sha256": c128.PROTOCOL_SHA256,
        "formula_sha256": c128.FORMULA_SHA256,
        "implementation_freeze_sha256": c128._sha256(
            c128.DEFAULT_IMPLEMENTATION_FREEZE
        ),
        "daily_price_fields_read": [],
        "forward_return_fields_read": False,
        "comparison_factor_values_read": False,
        "candidate49_ledgers_changed": False,
        "provider_request_issued": False,
        "training_or_model_fitting_performed": False,
    }


def test_recovery_accepts_exact_bound_metadata_without_partition_reads() -> None:
    manifest = _manifest()
    recovery.validate_manifest_metadata(manifest)
    assert manifest["source_fields_read"] == [
        "datetime",
        "symbol",
        "provider",
        "volume",
        "amount",
    ]


@pytest.mark.parametrize(
    ("key", "changed"),
    [
        ("factor_ranges", {recovery.c128.FACTOR_NAME: [0.0, 1.0]}),
        ("minimum_active_bars_per_half", 59),
        ("source_fields_read", ["datetime", "symbol", "provider", "close"]),
        ("forward_return_fields_read", True),
        ("comparison_factor_values_read", True),
        ("provider_request_issued", True),
    ],
)
def test_recovery_rejects_formula_source_or_boundary_mutation(
    key: str, changed: object
) -> None:
    manifest = copy.deepcopy(_manifest())
    manifest[key] = changed
    with pytest.raises(recovery.Campaign128SnapshotRecoveryError):
        recovery.validate_manifest_metadata(manifest)


def test_recovery_manifest_path_is_exact_and_snapshot_absent_before_build() -> None:
    assert (
        recovery.MANIFEST_PATH
        == (
            recovery.c128.output_root(recovery.c128.DEFAULT_DATA_ROOT)
            / "snapshot_manifest.json"
        ).resolve()
    )
    assert recovery.MANIFEST_PATH.exists() is False
