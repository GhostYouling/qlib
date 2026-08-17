from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign061_features as c61


def _raw_session(date: str, closes: np.ndarray, symbol: str = "SZ000001") -> pd.DataFrame:
    codes = list(c61.SOURCE_MINUTE_CODES)
    assert len(codes) == 241
    assert len(closes) == 241
    day = pd.Timestamp(date)
    datetimes = [
        day + pd.Timedelta(hours=code // 60, minutes=code % 60) for code in codes
    ]
    return pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": symbol,
            "provider": "tushare",
            "close": closes,
        }
    )


def test_protocol_and_comparison_order_are_frozen() -> None:
    spec = c61.load_protocol()
    comparisons = c61.reconstruct_comparisons(spec)
    assert len(comparisons) == 92
    assert comparisons[-1] == {
        "name": "intraday_day_over_day_directional_return_agreement_238b",
        "score_direction": "higher",
    }
    assert c61._comparison_order_digest(comparisons) == c61.COMPARISON_ORDER_SHA256


def test_identical_realized_variance_scores_one() -> None:
    current = np.linspace(-2.0, 3.0, 238, dtype=float)[None, :]
    prior = -current[:, ::-1]
    values, eligible, quality = c61.compute_variance_stability_values(current, prior)
    assert eligible.tolist() == [True]
    assert values[0] == pytest.approx(1.0)
    assert quality["eligible_rows"] == 1


def test_four_to_one_variance_ratio_scores_two_fifths() -> None:
    current = np.ones((1, 238), dtype=float)
    prior = np.full((1, 238), 2.0, dtype=float)
    values, eligible, _ = c61.compute_variance_stability_values(current, prior)
    assert eligible.tolist() == [True]
    assert values[0] == pytest.approx(0.4)


def test_sign_and_clock_permutation_are_discarded() -> None:
    current = np.arange(1.0, 239.0, dtype=float)[None, :]
    prior = current.copy()
    transformed = -prior[:, ::-1]
    base, base_eligible, _ = c61.compute_variance_stability_values(current, prior)
    changed, changed_eligible, _ = c61.compute_variance_stability_values(
        current, transformed
    )
    assert base_eligible.tolist() == changed_eligible.tolist() == [True]
    assert changed[0] == pytest.approx(base[0])


def test_individual_zero_returns_are_allowed_but_zero_variance_day_is_missing() -> None:
    current = np.zeros((2, 238), dtype=float)
    prior = np.zeros((2, 238), dtype=float)
    current[0, 5] = 1.0
    prior[0, 7] = -1.0
    current[1, 5] = 1.0
    values, eligible, quality = c61.compute_variance_stability_values(current, prior)
    assert eligible.tolist() == [True, False]
    assert values[0] == pytest.approx(1.0)
    assert np.isnan(values[1])
    assert quality["nonpositive_or_nonfinite_prior_realized_variance_rows"] == 1


def test_signed_return_extraction_excludes_0930_and_lunch_transition() -> None:
    closes = np.full(241, 10.0, dtype=float)
    code_to_index = {code: i for i, code in enumerate(c61.SOURCE_MINUTE_CODES)}
    closes[code_to_index[570]] = 1.0
    closes[code_to_index[571]] = 10.0
    closes[code_to_index[690]] = 20.0
    closes[code_to_index[781]] = 80.0
    closes[code_to_index[782]] = 80.0
    raw = _raw_session("2020-01-02", closes)
    profiles, quality = c61.extract_signed_return_profiles(raw, symbol="SZ000001")
    vector = profiles[pd.Timestamp("2020-01-02")]
    assert vector.shape == (238,)
    assert vector[0] == 0.0
    assert vector[118] == pytest.approx(np.log(2.0))
    assert vector[119] == 0.0
    assert quality["source_sessions"] == 1


def test_output_frame_never_bridges_missing_previous_stock_session() -> None:
    current_date = pd.Timestamp("2020-01-03")
    prior_date = pd.Timestamp("2020-01-02")
    base = pd.DataFrame(
        {
            "trade_date": [current_date],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
        }
    )
    profiles = {current_date: np.ones(238, dtype=float)}
    frame, quality = c61.compute_output_frame(
        base,
        profiles,
        {current_date: prior_date},
        symbol="SZ000001",
    )
    assert not bool(frame[f"{c61.FACTOR_NAME}_eligible"].iloc[0])
    assert np.isnan(frame[c61.FACTOR_NAME].iloc[0])
    assert quality[f"{c61.FACTOR_NAME}__missing_prior_stock_session_rows"] == 1


def test_output_frame_uses_frozen_variance_formula() -> None:
    current_date = pd.Timestamp("2020-01-03")
    prior_date = pd.Timestamp("2020-01-02")
    base = pd.DataFrame(
        {
            "trade_date": [current_date],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
        }
    )
    profiles = {
        current_date: np.ones(238, dtype=float),
        prior_date: np.full(238, 2.0, dtype=float),
    }
    frame, _ = c61.compute_output_frame(
        base,
        profiles,
        {current_date: prior_date},
        symbol="SZ000001",
    )
    assert bool(frame[f"{c61.FACTOR_NAME}_eligible"].iloc[0])
    assert frame[c61.FACTOR_NAME].iloc[0] == pytest.approx(0.4)


def test_nonfinite_return_row_is_missing() -> None:
    current = np.ones((1, 238), dtype=float)
    prior = np.ones((1, 238), dtype=float)
    prior[0, 7] = np.nan
    values, eligible, quality = c61.compute_variance_stability_values(current, prior)
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])
    assert quality["nonfinite_prior_return_rows"] == 1
