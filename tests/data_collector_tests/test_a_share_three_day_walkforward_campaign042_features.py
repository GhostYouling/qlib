"""Synthetic and pre-value tests for Campaign042 lunch repricing persistence."""

from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


MODULE = importlib.import_module(
    "scripts.a_share_three_day_walkforward_campaign042_features"
)


def _closes(lunch_return: float, afternoon_return: float) -> np.ndarray:
    closes = np.full((1, MODULE.SELECTED_BAR_COUNT), 10.0, dtype=float)
    closes[0, MODULE.LUNCH_PRE_INDEX] = 10.0
    closes[0, MODULE.AFTERNOON_OPEN_INDEX] = 10.0 * np.exp(lunch_return)
    closes[0, MODULE.AFTERNOON_CLOSE_INDEX] = (
        closes[0, MODULE.AFTERNOON_OPEN_INDEX] * np.exp(afternoon_return)
    )
    return closes


def test_equal_same_sign_components_score_one():
    values, eligible, quality = MODULE.compute_factor_values(
        closes=_closes(0.01, 0.01)
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(1.0)
    assert quality[f"{MODULE.FACTOR_NAME}__eligible_rows"] == 1


def test_equal_opposite_sign_components_score_minus_one():
    values, eligible, _ = MODULE.compute_factor_values(
        closes=_closes(0.01, -0.01)
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(-1.0)


def test_one_zero_component_is_retained_as_zero():
    values, eligible, quality = MODULE.compute_factor_values(
        closes=_closes(0.0, 0.02)
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(0.0)
    assert (
        quality[f"{MODULE.FACTOR_NAME}__exact_zero_lunch_return_rows"] == 1
    )
    assert quality[f"{MODULE.FACTOR_NAME}__both_components_zero_rows"] == 0


def test_both_zero_components_are_missing():
    values, eligible, quality = MODULE.compute_factor_values(
        closes=_closes(0.0, 0.0)
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[MODULE.FACTOR_NAME][0])
    assert quality[f"{MODULE.FACTOR_NAME}__both_components_zero_rows"] == 1


def test_invalid_shape_nonfinite_and_nonpositive_close_fail_closed():
    with pytest.raises(MODULE.Campaign042FeatureError):
        MODULE.compute_factor_values(closes=np.ones((1, 239)))

    rows = np.repeat(_closes(0.01, 0.01), 2, axis=0)
    rows[0, 5] = np.nan
    rows[1, 5] = 0.0
    values, eligible, quality = MODULE.compute_factor_values(closes=rows)

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[MODULE.FACTOR_NAME]).all()
    assert quality["invalid_required_close_rows"] == 1
    assert quality[f"{MODULE.FACTOR_NAME}__nonpositive_close_rows"] == 1


def test_protocol_materializes_63_unique_comparisons_in_frozen_order():
    spec = MODULE.load_protocol()
    coverage = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]

    assert coverage["holding_period_sessions"] == 3
    assert len(comparisons) == 63
    assert len({item["name"] for item in comparisons}) == 63
    assert comparisons[-1] == {
        "name": MODULE.OLD_FACTOR,
        "score_direction": "higher",
    }
    assert (
        MODULE._comparison_order_digest(comparisons)
        == MODULE.COMPARISON_ORDER_SHA256
    )
    assert spec["candidates"][0]["name"] == MODULE.FACTOR_NAME
    assert (
        spec["finite_post_admissibility_search"]["trial"]["factor"]
        == MODULE.FACTOR_NAME
    )


def test_partition_builder_projects_close_only_and_uses_v1_output_root():
    trade_date = pd.Timestamp("2025-01-02")
    minute_codes = sorted(MODULE.market.SOURCE_MINUTE_CODE_SET)
    continuous_codes = list(MODULE.market.CONTINUOUS_MINUTE_CODES)
    position_by_code = {
        code: index for index, code in enumerate(continuous_codes)
    }
    closes = _closes(0.01, 0.01)
    raw = pd.DataFrame(
        {
            "datetime": [
                trade_date
                + pd.Timedelta(hours=minute_code // 60)
                + pd.Timedelta(minutes=minute_code % 60)
                for minute_code in minute_codes
            ],
            "symbol": "SZ000001",
            "provider": "tushare",
            "close": [
                10.0
                if code not in position_by_code
                else float(closes[0, position_by_code[code]])
                for code in minute_codes
            ],
        },
        columns=MODULE.RAW_COLUMNS,
    )
    base_frame = pd.DataFrame(
        {"trade_date": [trade_date], "symbol": ["SZ000001"]},
        columns=MODULE.BASE_COLUMNS,
    )

    frame, quality = MODULE.compute_partition_frame(
        raw,
        base_frame,
        None,
        symbol="SZ000001",
    )

    assert frame[f"{MODULE.FACTOR_NAME}_eligible"].tolist() == [True]
    assert frame[MODULE.FACTOR_NAME][0] == pytest.approx(1.0)
    assert quality[f"{MODULE.FACTOR_NAME}__eligible_rows"] == 1
    assert MODULE.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "close",
    )
    assert MODULE.output_root(MODULE.DEFAULT_DATA_ROOT).name.endswith(
        "campaign042_feature_library_v1"
    )


def test_status_reads_no_comparison_values_or_returns():
    result = MODULE.status(
        MODULE.DEFAULT_DATA_ROOT,
        MODULE.DEFAULT_EXPERIMENT_ROOT,
    )

    assert result["protocol_sha256_bound"] is True
    assert result["source_fields_read_by_status"] == list(MODULE.RAW_COLUMNS)
    assert result["minute_close_fields_read_by_status"] == ["close"]
    assert (
        result["minute_open_high_low_volume_or_amount_fields_read_by_status"]
        == []
    )
    assert result["daily_price_fields_read_by_status"] is False
    assert result["forward_return_fields_read_by_status"] is False
    assert result["candidate49_historical_return_read"] is False
