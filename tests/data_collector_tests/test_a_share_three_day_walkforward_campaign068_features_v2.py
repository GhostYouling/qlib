from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign068_features_v2 as repair


def _frame(values: list[float], eligible: list[bool]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04"] * len(values)),
            "symbol": [f"SH{600000 + index:06d}" for index in range(len(values))],
            "provider": ["eastmoney_quarterly_quality"] * len(values),
            repair.v1.FACTOR_NAME: values,
            f"{repair.v1.FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, list(repair.v1.OUTPUT_COLUMNS)]


def test_campaign068_v2_protocol_freezes_only_signed_range_repair() -> None:
    spec = repair.load_repair_protocol()
    assert spec["recorded_v1_failure"]["v1_snapshot_accepted"] is False
    assert spec["recorded_v1_failure"]["v1_snapshot_files_reusable_for_v2"] is False
    assert spec["sole_repair"]["old_incorrect_eligible_value_range"] == [0.0, 1.0]
    assert spec["sole_repair"]["new_required_eligible_value_range"] == [-1.0, 1.0]
    assert spec["frozen_v1_generator"]["candidate_value_generation_changed"] is False
    assert spec["v2_output"]["fresh_source_read_and_fresh_partition_build_required"] is True


def test_campaign068_v2_signed_range_accepts_negative_values() -> None:
    rows, eligible = repair.validate_value_semantics(
        _frame([-1.0, -0.25, 0.0, 0.75, 1.0, np.nan], [True] * 5 + [False])
    )
    assert rows == 6
    assert eligible == 5


def test_campaign068_v2_signed_range_rejects_out_of_range_or_mismatched_missingness() -> None:
    with pytest.raises(repair.Campaign068FeatureV2Error):
        repair.validate_value_semantics(_frame([-1.01], [True]))
    with pytest.raises(repair.Campaign068FeatureV2Error):
        repair.validate_value_semantics(_frame([1.01], [True]))
    with pytest.raises(repair.Campaign068FeatureV2Error):
        repair.validate_value_semantics(_frame([0.0], [False]))
    with pytest.raises(repair.Campaign068FeatureV2Error):
        repair.validate_value_semantics(_frame([np.nan], [True]))


def test_campaign068_v2_status_does_not_accept_v1_snapshot() -> None:
    payload = repair.status()
    assert payload["status"] == "snapshot_absent_pre_build"
    assert payload["v1_failed_snapshot_accepted"] is False
    assert payload["candidate_or_comparison_values_read_by_status"] is False
    assert payload["historical_forward_return_fields_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False
