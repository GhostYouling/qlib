from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign045_features as campaign045


def _manual_population_corr(x: np.ndarray, y: np.ndarray) -> float:
    xc = x - x.mean()
    yc = y - y.mean()
    return float(np.sum(xc * yc) / np.sqrt(np.sum(xc * xc) * np.sum(yc * yc)))


def _synthetic_rows() -> tuple[np.ndarray, np.ndarray]:
    index = np.arange(240, dtype=float)
    returns = 0.0003 * np.sin(index * 0.31) + 0.0002 * np.cos(index * 0.17)
    closes = 10.0 * np.exp(np.cumsum(returns))
    amounts = 1_000_000.0 + 300_000.0 * (1.0 + np.sin(index * 0.23))
    return closes[None, :], amounts[None, :]


def test_protocol_binds_exact_68_factor_library() -> None:
    spec = campaign045.load_protocol()
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 68
    assert len({item["name"] for item in comparisons}) == 68
    assert comparisons[-2]["name"] == "intraday_cumulative_vwap_crossing_rate_240m"
    assert comparisons[-1]["name"] == campaign045.C44_FACTOR_NAME


def test_formula_matches_manual_reactive_minus_anticipatory_correlations() -> None:
    closes, amounts = _synthetic_rows()
    values, eligible, quality = campaign045.compute_factor_values(
        closes=closes,
        amounts=amounts,
    )
    returns = np.concatenate(
        [
            np.diff(np.log(closes[:, :120]), axis=1),
            np.diff(np.log(closes[:, 120:]), axis=1),
        ],
        axis=1,
    )[0]
    activity = np.log1p(
        np.concatenate([amounts[:, 1:120], amounts[:, 121:240]], axis=1)
    )[0]
    magnitude = np.abs(returns)
    earlier_magnitude = np.concatenate([magnitude[:118], magnitude[119:237]])
    later_magnitude = np.concatenate([magnitude[1:119], magnitude[120:238]])
    earlier_activity = np.concatenate([activity[:118], activity[119:237]])
    later_activity = np.concatenate([activity[1:119], activity[120:238]])
    expected = _manual_population_corr(
        earlier_magnitude, later_activity
    ) - _manual_population_corr(earlier_activity, later_magnitude)
    assert eligible[campaign045.FACTOR_NAME].tolist() == [True]
    assert values[campaign045.FACTOR_NAME][0] == pytest.approx(expected)
    assert quality[f"{campaign045.FACTOR_NAME}__eligible_rows"] == 1


def test_exact_zero_returns_and_amounts_remain_in_fixed_support() -> None:
    closes, amounts = _synthetic_rows()
    closes[0, 40:43] = closes[0, 39]
    amounts[0, 80] = 0.0
    values, eligible, quality = campaign045.compute_factor_values(
        closes=closes,
        amounts=amounts,
    )
    assert eligible[campaign045.FACTOR_NAME].tolist() == [True]
    assert np.isfinite(values[campaign045.FACTOR_NAME][0])
    assert quality[f"{campaign045.FACTOR_NAME}__exact_zero_return_positions"] >= 3
    assert quality[f"{campaign045.FACTOR_NAME}__exact_zero_amount_positions"] == 1


def test_invalid_required_values_and_degenerate_correlations_are_missing() -> None:
    closes, amounts = _synthetic_rows()
    closes = np.repeat(closes, 4, axis=0)
    amounts = np.repeat(amounts, 4, axis=0)
    closes[0, 10] = 0.0
    closes[1, 10] = np.nan
    amounts[2, 10] = -1.0
    closes[3, :] = 10.0
    values, eligible, quality = campaign045.compute_factor_values(
        closes=closes,
        amounts=amounts,
    )
    assert eligible[campaign045.FACTOR_NAME].tolist() == [False] * 4
    assert np.isnan(values[campaign045.FACTOR_NAME]).all()
    assert quality[f"{campaign045.FACTOR_NAME}__nonpositive_close_rows"] == 1
    assert quality[f"{campaign045.FACTOR_NAME}__nonfinite_close_rows"] == 1
    assert quality[f"{campaign045.FACTOR_NAME}__negative_amount_rows"] == 1
    assert quality[f"{campaign045.FACTOR_NAME}__degenerate_reactive_correlation_rows"] >= 1


def test_partition_uses_exact_continuous_grid_and_excludes_0930() -> None:
    date = pd.Timestamp("2023-06-01")
    minute_codes = sorted(campaign045.market.SOURCE_MINUTE_CODE_SET)
    datetimes = [
        date + pd.Timedelta(minutes=code) for code in minute_codes
    ]
    raw = pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "SZ000001",
            "provider": "tushare",
            "close": 10.0 + np.arange(241) * 0.001,
            "amount": 1_000_000.0 + (np.arange(241) % 17) * 10_000.0,
        },
        columns=campaign045.RAW_COLUMNS,
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
        columns=campaign045.BASE_COLUMNS,
    )
    frame, quality = campaign045.compute_partition_frame(
        raw,
        base,
        None,
        symbol="SZ000001",
    )
    raw.loc[raw["datetime"].dt.strftime("%H:%M") == "09:30", "close"] = 999.0
    changed, changed_quality = campaign045.compute_partition_frame(
        raw,
        base,
        None,
        symbol="SZ000001",
    )
    pd.testing.assert_frame_equal(frame, changed)
    assert quality == changed_quality


def test_wrong_source_projection_fails_closed() -> None:
    with pytest.raises(campaign045.Campaign045FeatureError):
        campaign045.compute_partition_frame(
            pd.DataFrame(columns=["datetime", "symbol", "provider", "close"]),
            pd.DataFrame(columns=campaign045.BASE_COLUMNS),
            None,
            symbol="SZ000001",
        )
