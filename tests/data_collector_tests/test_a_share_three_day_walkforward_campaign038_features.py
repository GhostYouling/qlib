"""Synthetic and pre-value tests for Campaign038 chord adherence."""

from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


MODULE = importlib.import_module(
    "scripts.a_share_three_day_walkforward_campaign038_features"
)


def _closes_from_half_returns(
    morning_returns: np.ndarray,
    afternoon_returns: np.ndarray,
    *,
    afternoon_scale: float = 1.0,
) -> np.ndarray:
    assert morning_returns.shape == (119,)
    assert afternoon_returns.shape == (119,)
    morning = 10.0 * np.exp(
        np.concatenate(([0.0], np.cumsum(morning_returns)))
    )
    afternoon = 10.0 * afternoon_scale * np.exp(
        np.concatenate(([0.0], np.cumsum(afternoon_returns)))
    )
    return np.concatenate((morning, afternoon))[None, :]


def test_endpoint_chord_adherence_rewards_a_linear_half_session_path():
    linear = np.full(119, 0.001)
    wandering = np.resize(np.array([0.003, -0.001]), 119)

    low, low_eligible, _ = MODULE.compute_factor_values(
        closes=_closes_from_half_returns(wandering, wandering),
    )
    high, high_eligible, _ = MODULE.compute_factor_values(
        closes=_closes_from_half_returns(linear, linear),
    )

    assert low_eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert high_eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert high[MODULE.FACTOR_NAME][0] > low[MODULE.FACTOR_NAME][0]
    assert high[MODULE.FACTOR_NAME][0] == pytest.approx(1.0, abs=1e-12)
    assert 0.0 <= low[MODULE.FACTOR_NAME][0] <= MODULE.UPPER_BOUND
    assert 0.0 <= high[MODULE.FACTOR_NAME][0] <= MODULE.UPPER_BOUND


def test_adherence_is_scale_invariant_and_lunch_jump_is_excluded():
    returns = np.resize(np.array([0.003, -0.001]), 119)
    first, first_eligible, _ = MODULE.compute_factor_values(
        closes=_closes_from_half_returns(returns, returns),
    )
    shifted, shifted_eligible, _ = MODULE.compute_factor_values(
        closes=_closes_from_half_returns(
            returns,
            returns,
            afternoon_scale=100.0,
        ),
    )

    assert first_eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert shifted_eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert first[MODULE.FACTOR_NAME][0] == pytest.approx(
        shifted[MODULE.FACTOR_NAME][0],
        abs=1e-10,
    )


def test_zero_total_travel_is_missing_but_one_constant_half_is_allowed():
    constant = np.full((1, 240), 10.0)
    values, eligible, quality = MODULE.compute_factor_values(closes=constant)

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[MODULE.FACTOR_NAME][0])
    assert quality[f"{MODULE.FACTOR_NAME}__zero_total_travel_rows"] == 1

    morning = np.zeros(119)
    afternoon = np.full(119, 0.001)
    values, eligible, quality = MODULE.compute_factor_values(
        closes=_closes_from_half_returns(morning, afternoon),
    )
    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(1.0, abs=1e-12)
    assert (
        quality[f"{MODULE.FACTOR_NAME}__chord_deviation_observations"]
        == MODULE.DEVIATION_SUPPORT_COUNT
    )
    assert (
        quality[f"{MODULE.FACTOR_NAME}__within_half_return_observations"]
        == MODULE.RETURN_COUNT
    )


def test_invalid_closes_and_bad_shape_fail_closed():
    with pytest.raises(MODULE.Campaign038FeatureError):
        MODULE.compute_factor_values(closes=np.ones((1, 239)))

    returns = np.linspace(-0.001, 0.001, 119)
    closes = np.repeat(
        _closes_from_half_returns(returns, returns),
        2,
        axis=0,
    )
    closes[0, 5] = np.nan
    closes[1, 5] = 0.0
    values, eligible, quality = MODULE.compute_factor_values(closes=closes)

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[MODULE.FACTOR_NAME]).all()
    assert quality["invalid_required_close_rows"] == 1
    assert quality[f"{MODULE.FACTOR_NAME}__nonpositive_close_rows"] == 1


def test_protocol_materializes_59_unique_comparisons_in_frozen_order():
    spec = MODULE.load_protocol()
    coverage = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]

    assert coverage["holding_period_sessions"] == 3
    assert len(comparisons) == 59
    assert len({item["name"] for item in comparisons}) == 59
    assert comparisons[-1] == {
        "name": "intraday_five_minute_variance_ratio_230w",
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
    returns = np.full(119, 0.001)
    closes = _closes_from_half_returns(returns, returns)[0]
    raw_closes = [
        10.0
        if code not in position_by_code
        else closes[position_by_code[code]]
        for code in minute_codes
    ]
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
            "close": raw_closes,
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
    assert np.isfinite(frame[MODULE.FACTOR_NAME][0])
    assert quality[f"{MODULE.FACTOR_NAME}__eligible_rows"] == 1
    assert MODULE.RAW_COLUMNS == ("datetime", "symbol", "provider", "close")
    assert MODULE.output_root(MODULE.DEFAULT_DATA_ROOT).name.endswith(
        "campaign038_feature_library_v1"
    )


def test_status_reads_no_comparison_values_or_returns():
    result = MODULE.status(
        MODULE.DEFAULT_DATA_ROOT,
        MODULE.DEFAULT_EXPERIMENT_ROOT,
    )

    assert result["protocol_sha256_bound"] is True
    assert result["snapshot_sha256_bound"] is bool(
        MODULE.SNAPSHOT_MANIFEST_SHA256
    )
    assert result["no_return_audit_sha256_bound"] is bool(
        MODULE.NO_RETURN_AUDIT_SHA256
    )
    assert result["source_fields_read_by_status"] == [
        "datetime",
        "symbol",
        "provider",
        "close",
    ]
    assert result["forward_return_fields_read_by_status"] is False
    assert result["candidate49_historical_return_read"] is False
