from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign060_features as c60


def _raw_session(date: str, closes: np.ndarray, symbol: str = "SZ000001") -> pd.DataFrame:
    codes = list(c60.SOURCE_MINUTE_CODES)
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
    spec = c60.load_protocol()
    comparisons = c60.reconstruct_comparisons(spec)
    assert len(comparisons) == 91
    assert comparisons[-1] == {
        "name": "intraday_market_directional_sign_agreement_238m",
        "score_direction": "higher",
    }
    assert c60._comparison_order_digest(comparisons) == c60.COMPARISON_ORDER_SHA256


def test_identical_nonzero_signs_score_one() -> None:
    current = np.ones((1, 238), dtype=float)
    prior = np.linspace(1.0, 2.0, 238, dtype=float)[None, :]
    values, eligible, quality = c60.compute_directional_agreement_values(
        current, prior
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [1.0]
    assert quality["eligible_directional_agreements"] == 238


def test_opposite_nonzero_signs_score_zero() -> None:
    current = np.ones((1, 238), dtype=float)
    prior = -np.ones((1, 238), dtype=float)
    values, eligible, _ = c60.compute_directional_agreement_values(current, prior)
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]


def test_magnitude_is_discarded_and_zeros_are_noninformative() -> None:
    current = np.zeros((1, 238), dtype=float)
    prior = np.zeros((1, 238), dtype=float)
    current[0, :80] = np.r_[np.ones(40), -np.ones(40)]
    prior[0, :80] = np.r_[np.full(40, 1e9), np.full(40, 1e-9)]
    values, eligible, quality = c60.compute_directional_agreement_values(
        current, prior
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.5]
    assert quality["eligible_informative_positions"] == 80


def test_minimum_jointly_nonzero_support_is_exactly_sixty() -> None:
    current = np.zeros((2, 238), dtype=float)
    prior = np.zeros((2, 238), dtype=float)
    current[0, :59] = prior[0, :59] = 1.0
    current[1, :60] = prior[1, :60] = 1.0
    values, eligible, quality = c60.compute_directional_agreement_values(
        current, prior
    )
    assert eligible.tolist() == [False, True]
    assert np.isnan(values[0])
    assert values[1] == 1.0
    assert quality["insufficient_informative_position_rows"] == 1


def test_signed_return_extraction_excludes_0930_and_lunch_transition() -> None:
    closes = np.full(241, 10.0, dtype=float)
    code_to_index = {code: i for i, code in enumerate(c60.SOURCE_MINUTE_CODES)}
    closes[code_to_index[570]] = 1.0
    closes[code_to_index[571]] = 10.0
    closes[code_to_index[690]] = 20.0
    closes[code_to_index[781]] = 80.0
    closes[code_to_index[782]] = 80.0
    raw = _raw_session("2020-01-02", closes)
    profiles, quality = c60.extract_signed_return_profiles(raw, symbol="SZ000001")
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
    frame, quality = c60.compute_output_frame(
        base,
        profiles,
        {current_date: prior_date},
        symbol="SZ000001",
    )
    assert not bool(frame[f"{c60.FACTOR_NAME}_eligible"].iloc[0])
    assert np.isnan(frame[c60.FACTOR_NAME].iloc[0])
    assert quality[f"{c60.FACTOR_NAME}__missing_prior_stock_session_rows"] == 1


def test_nonfinite_return_row_is_missing() -> None:
    current = np.ones((1, 238), dtype=float)
    prior = np.ones((1, 238), dtype=float)
    prior[0, 7] = np.nan
    values, eligible, quality = c60.compute_directional_agreement_values(
        current, prior
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])
    assert quality["nonfinite_prior_return_rows"] == 1
