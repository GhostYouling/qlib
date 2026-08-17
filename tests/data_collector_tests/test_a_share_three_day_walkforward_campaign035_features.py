"""Synthetic and pre-value boundary tests for Campaign035 weak-order entropy."""

from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


MODULE = importlib.import_module(
    "scripts.a_share_three_day_walkforward_campaign035_features"
)


def _closes_from_half_returns(
    morning_returns: np.ndarray,
    afternoon_returns: np.ndarray,
) -> np.ndarray:
    assert morning_returns.shape == (119,)
    assert afternoon_returns.shape == (119,)
    morning = 10.0 * np.exp(np.r_[0.0, np.cumsum(morning_returns)])
    afternoon = 20.0 * np.exp(np.r_[0.0, np.cumsum(afternoon_returns)])
    return np.r_[morning, afternoon][None, :]


def test_constant_closes_retain_exact_ties_and_have_zero_entropy():
    closes = np.full((1, 240), 10.0, dtype=float)

    values, eligible, quality = MODULE.compute_factor_values(closes=closes)

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME].tolist() == [0.0]
    assert (
        quality[f"{MODULE.FACTOR_NAME}__exact_tie_tuple_observations"] == 234
    )
    assert quality[f"{MODULE.FACTOR_NAME}__state_count_mismatch_rows"] == 0


def test_strictly_increasing_returns_have_zero_entropy():
    returns = np.arange(119, dtype=float) * 1e-6
    closes = _closes_from_half_returns(returns, returns)

    values, eligible, quality = MODULE.compute_factor_values(closes=closes)

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(0.0, abs=1e-15)
    assert quality[f"{MODULE.FACTOR_NAME}__exact_tie_tuple_observations"] == 0


def test_morning_and_afternoon_are_separate_and_no_lunch_tuple_is_added():
    morning = np.zeros(119, dtype=float)
    afternoon = np.arange(119, dtype=float) * 1e-6
    closes_a = _closes_from_half_returns(morning, afternoon)
    closes_b = closes_a.copy()
    closes_b[0, 120:] *= 100.0

    values_a, eligible_a, quality_a = MODULE.compute_factor_values(
        closes=closes_a
    )
    values_b, eligible_b, quality_b = MODULE.compute_factor_values(
        closes=closes_b
    )

    assert eligible_a[MODULE.FACTOR_NAME].tolist() == [True]
    assert eligible_b[MODULE.FACTOR_NAME].tolist() == [True]
    assert values_a[MODULE.FACTOR_NAME][0] == pytest.approx(
        values_b[MODULE.FACTOR_NAME][0],
        abs=1e-15,
    )
    assert (
        quality_a[f"{MODULE.FACTOR_NAME}__exact_tie_tuple_observations"]
        == quality_b[f"{MODULE.FACTOR_NAME}__exact_tie_tuple_observations"]
        == 117
    )


def test_all_thirteen_weak_order_codes_are_frozen_and_transitive():
    assert MODULE.WEAK_ORDER_CODES.tolist() == [
        0,
        1,
        2,
        5,
        8,
        9,
        13,
        17,
        18,
        21,
        24,
        25,
        26,
    ]


def test_nonpositive_nonfinite_and_bad_shape_fail_closed():
    with pytest.raises(MODULE.Campaign035FeatureError):
        MODULE.compute_factor_values(closes=np.ones((1, 239)))

    closes = np.full((2, 240), 10.0, dtype=float)
    closes[0, 10] = 0.0
    closes[1, 10] = np.nan
    values, eligible, quality = MODULE.compute_factor_values(closes=closes)

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[MODULE.FACTOR_NAME]).all()
    assert quality[f"{MODULE.FACTOR_NAME}__nonpositive_close_rows"] == 1
    assert quality["invalid_required_close_rows"] == 1


def test_protocol_materializes_56_unique_comparisons_in_frozen_order():
    spec = MODULE.load_protocol()
    coverage = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]

    assert coverage["holding_period_sessions"] == 3
    assert len(comparisons) == 56
    assert len({item["name"] for item in comparisons}) == 56
    assert comparisons[-1] == {
        "name": "intraday_round_tenth_close_avoidance_240m",
        "score_direction": "higher",
    }
    assert spec["candidates"][0]["name"] == MODULE.FACTOR_NAME
    assert (
        spec["finite_post_admissibility_search"]["trial"]["factor"]
        == MODULE.FACTOR_NAME
    )


def test_partition_builder_uses_weak_order_formula_and_v1_output_root():
    partition_builder = MODULE._generated["compute_partition_frame"]
    assert (
        partition_builder.__globals__["compute_factor_values"]
        is MODULE.compute_factor_values
    )
    assert MODULE.output_root(MODULE.DEFAULT_DATA_ROOT).name.endswith(
        "campaign035_feature_library_v1"
    )

    trade_date = pd.Timestamp("2025-01-02")
    minute_codes = sorted(MODULE._generated["market"].SOURCE_MINUTE_CODE_SET)
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
            "close": 10.0,
        },
        columns=MODULE.RAW_COLUMNS,
    )
    base_frame = pd.DataFrame(
        {"trade_date": [trade_date], "symbol": ["SZ000001"]},
        columns=MODULE._generated["BASE_COLUMNS"],
    )

    frame, quality = partition_builder(
        raw,
        base_frame,
        None,
        symbol="SZ000001",
    )

    assert frame[MODULE.FACTOR_NAME].tolist() == [0.0]
    assert frame[f"{MODULE.FACTOR_NAME}_eligible"].tolist() == [True]
    assert (
        quality[f"{MODULE.FACTOR_NAME}__exact_tie_tuple_observations"] == 234
    )
    assert f"{MODULE.FACTOR_NAME}__round_tenth_close_observations" not in quality


def test_bound_snapshot_status_reads_no_comparison_values_or_returns():
    result = MODULE.status(
        MODULE.DEFAULT_DATA_ROOT,
        MODULE.DEFAULT_EXPERIMENT_ROOT,
    )

    assert result["protocol_sha256_bound"] is True
    assert result["snapshot_exists"] is True
    assert result["snapshot_sha256_bound"] is True
    assert result["audit_count"] == 1
    assert result["no_return_audit_sha256_bound"] is True
    assert result["forward_return_fields_read_by_status"] is False
    assert result["candidate49_historical_return_read"] is False
