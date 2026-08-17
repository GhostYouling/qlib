from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign046_features as campaign046


def _closes_from_half_returns(morning: np.ndarray, afternoon: np.ndarray) -> np.ndarray:
    return np.concatenate(
        [
            10.0 * np.exp(np.r_[0.0, np.cumsum(morning)]),
            11.0 * np.exp(np.r_[0.0, np.cumsum(afternoon)]),
        ]
    )[None, :]


def test_protocol_binds_exact_69_factor_library() -> None:
    spec = campaign046.load_protocol()
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 69
    assert len({item["name"] for item in comparisons}) == 69
    assert comparisons[-1] == {
        "name": campaign046.C45_FACTOR_NAME,
        "score_direction": "higher",
    }


def test_formula_matches_manual_reversal_energy_share() -> None:
    morning = 0.0005 * np.sin(np.arange(119) * 0.37)
    afternoon = 0.0007 * np.cos(np.arange(119) * 0.23)
    closes = _closes_from_half_returns(morning, afternoon)
    values, eligible, quality = campaign046.compute_factor_values(closes=closes)
    products = np.concatenate(
        [morning[:-1] * morning[1:], afternoon[:-1] * afternoon[1:]]
    )
    expected = np.abs(products[products < 0.0]).sum() / np.abs(products).sum()
    assert eligible[campaign046.FACTOR_NAME].tolist() == [True]
    assert values[campaign046.FACTOR_NAME][0] == pytest.approx(expected)
    assert quality[f"{campaign046.FACTOR_NAME}__eligible_rows"] == 1


def test_pure_alternation_and_continuation_hit_frozen_endpoints() -> None:
    alternating = np.tile(np.array([0.01, -0.01]), 60)[:119]
    continuing = np.full(119, 0.01)
    closes = np.concatenate(
        [
            _closes_from_half_returns(alternating, alternating),
            _closes_from_half_returns(continuing, continuing),
        ]
    )
    values, eligible, _ = campaign046.compute_factor_values(closes=closes)
    assert eligible[campaign046.FACTOR_NAME].tolist() == [True, True]
    assert values[campaign046.FACTOR_NAME].tolist() == pytest.approx([1.0, 0.0])


def test_exact_zero_returns_remain_without_bridging() -> None:
    returns = np.tile(np.array([0.01, 0.0, -0.01, 0.01]), 30)[:119]
    closes = _closes_from_half_returns(returns, returns)
    values, eligible, quality = campaign046.compute_factor_values(closes=closes)
    assert eligible[campaign046.FACTOR_NAME].tolist() == [True]
    assert np.isfinite(values[campaign046.FACTOR_NAME][0])
    assert quality[f"{campaign046.FACTOR_NAME}__exact_zero_return_positions"] > 0
    assert quality[f"{campaign046.FACTOR_NAME}__exact_zero_product_positions"] > 0


def test_invalid_close_and_zero_denominator_are_missing() -> None:
    valid = np.full(119, 0.01)
    closes = np.repeat(_closes_from_half_returns(valid, valid), 3, axis=0)
    closes[0, 10] = 0.0
    closes[1, 10] = np.nan
    closes[2, :] = 10.0
    values, eligible, quality = campaign046.compute_factor_values(closes=closes)
    assert eligible[campaign046.FACTOR_NAME].tolist() == [False, False, False]
    assert np.isnan(values[campaign046.FACTOR_NAME]).all()
    assert quality[f"{campaign046.FACTOR_NAME}__nonpositive_close_rows"] == 1
    assert quality[f"{campaign046.FACTOR_NAME}__nonfinite_close_rows"] == 1
    assert quality[f"{campaign046.FACTOR_NAME}__zero_denominator_rows"] >= 1


def test_partition_uses_close_only_and_excludes_0930() -> None:
    date = pd.Timestamp("2023-06-01")
    minute_codes = sorted(campaign046.market.SOURCE_MINUTE_CODE_SET)
    raw = pd.DataFrame(
        {
            "datetime": [date + pd.Timedelta(minutes=code) for code in minute_codes],
            "symbol": "SZ000001",
            "provider": "tushare",
            "close": 10.0 + np.sin(np.arange(241) * 0.21) * 0.05,
        },
        columns=campaign046.RAW_COLUMNS,
    )
    base = pd.DataFrame(
        {
            "trade_date": [date],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
            "late_return_30m": [0.0],
            "late_return_30m_eligible": [True],
            "late_amount_share_30m": [0.0],
            "late_amount_share_30m_eligible": [True],
            "late_vwap_to_day_vwap_30m": [0.0],
            "late_vwap_to_day_vwap_30m_eligible": [True],
            "intraday_realized_volatility": [0.0],
            "intraday_realized_volatility_eligible": [True],
        },
        columns=campaign046.BASE_COLUMNS,
    )
    frame, quality = campaign046.compute_partition_frame(
        raw, base, None, symbol="SZ000001"
    )
    raw.loc[raw["datetime"].dt.strftime("%H:%M") == "09:30", "close"] = 999.0
    changed, changed_quality = campaign046.compute_partition_frame(
        raw, base, None, symbol="SZ000001"
    )
    pd.testing.assert_frame_equal(frame, changed)
    assert quality == changed_quality


def test_wrong_source_projection_fails_closed() -> None:
    with pytest.raises(campaign046.Campaign046FeatureError):
        campaign046.compute_partition_frame(
            pd.DataFrame(
                columns=["datetime", "symbol", "provider", "close", "amount"]
            ),
            pd.DataFrame(columns=campaign046.BASE_COLUMNS),
            None,
            symbol="SZ000001",
        )
