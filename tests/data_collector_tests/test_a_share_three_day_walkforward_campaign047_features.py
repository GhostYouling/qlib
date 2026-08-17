from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign047_features as campaign047


def _half_from_bodies_and_gaps(
    bodies: np.ndarray, gaps: np.ndarray, *, start: float
) -> tuple[np.ndarray, np.ndarray]:
    assert bodies.shape == gaps.shape == (119,)
    opens = np.empty(120, dtype=float)
    closes = np.empty(120, dtype=float)
    opens[0] = start
    for index in range(119):
        closes[index] = opens[index] * np.exp(bodies[index])
        opens[index + 1] = closes[index] * np.exp(gaps[index])
    closes[119] = opens[119]
    return opens, closes


def _session_from_bodies_and_gaps(
    bodies: np.ndarray, gaps: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    morning_open, morning_close = _half_from_bodies_and_gaps(
        bodies, gaps, start=10.0
    )
    afternoon_open, afternoon_close = _half_from_bodies_and_gaps(
        bodies[::-1], gaps[::-1], start=11.0
    )
    return (
        np.concatenate([morning_open, afternoon_open])[None, :],
        np.concatenate([morning_close, afternoon_close])[None, :],
    )


def test_protocol_binds_exact_70_factor_library() -> None:
    spec = campaign047.load_protocol()
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 70
    assert len({item["name"] for item in comparisons}) == 70
    assert comparisons[-1] == {
        "name": campaign047.C46_FACTOR_NAME,
        "score_direction": "higher",
    }


def test_formula_matches_manual_negative_population_correlation() -> None:
    bodies = 0.001 * np.sin(np.arange(119) * 0.17)
    gaps = 0.0007 * np.cos(np.arange(119) * 0.29)
    opens, closes = _session_from_bodies_and_gaps(bodies, gaps)
    values, eligible, quality = campaign047.compute_factor_values(
        opens=opens, closes=closes
    )
    pooled_bodies = np.concatenate([bodies, bodies[::-1]])
    pooled_gaps = np.concatenate([gaps, gaps[::-1]])
    expected = -np.corrcoef(pooled_bodies, pooled_gaps)[0, 1]
    assert eligible[campaign047.FACTOR_NAME].tolist() == [True]
    assert values[campaign047.FACTOR_NAME][0] == pytest.approx(expected)
    assert quality[f"{campaign047.FACTOR_NAME}__eligible_rows"] == 1


def test_exact_reversal_and_confirmation_hit_frozen_endpoints() -> None:
    bodies = 0.001 * np.sin(np.arange(119) * 0.19)
    reversed_open, reversed_close = _session_from_bodies_and_gaps(bodies, -bodies)
    confirmed_open, confirmed_close = _session_from_bodies_and_gaps(bodies, bodies)
    opens = np.concatenate([reversed_open, confirmed_open], axis=0)
    closes = np.concatenate([reversed_close, confirmed_close], axis=0)
    values, eligible, _ = campaign047.compute_factor_values(
        opens=opens, closes=closes
    )
    assert eligible[campaign047.FACTOR_NAME].tolist() == [True, True]
    assert values[campaign047.FACTOR_NAME].tolist() == pytest.approx([1.0, -1.0])


def test_exact_zero_body_and_gap_positions_remain_in_fixed_support() -> None:
    bodies = 0.001 * np.sin(np.arange(119) * 0.23)
    gaps = -0.4 * bodies
    bodies[::7] = 0.0
    gaps[::11] = 0.0
    opens, closes = _session_from_bodies_and_gaps(bodies, gaps)
    values, eligible, quality = campaign047.compute_factor_values(
        opens=opens, closes=closes
    )
    assert eligible[campaign047.FACTOR_NAME].tolist() == [True]
    assert np.isfinite(values[campaign047.FACTOR_NAME][0])
    assert quality[f"{campaign047.FACTOR_NAME}__exact_zero_body_positions"] > 0
    assert quality[f"{campaign047.FACTOR_NAME}__exact_zero_following_gap_positions"] > 0


def test_invalid_open_close_and_degenerate_vectors_are_missing() -> None:
    bodies = 0.001 * np.sin(np.arange(119) * 0.17)
    gaps = -0.5 * bodies
    opens, closes = _session_from_bodies_and_gaps(bodies, gaps)
    opens = np.repeat(opens, 3, axis=0)
    closes = np.repeat(closes, 3, axis=0)
    opens[0, 10] = 0.0
    closes[1, 10] = np.nan
    opens[2, :] = 10.0
    closes[2, :] = 10.0
    values, eligible, quality = campaign047.compute_factor_values(
        opens=opens, closes=closes
    )
    assert eligible[campaign047.FACTOR_NAME].tolist() == [False, False, False]
    assert np.isnan(values[campaign047.FACTOR_NAME]).all()
    assert quality[f"{campaign047.FACTOR_NAME}__nonpositive_open_rows"] == 1
    assert quality[f"{campaign047.FACTOR_NAME}__nonfinite_close_rows"] == 1
    assert quality[f"{campaign047.FACTOR_NAME}__zero_body_variance_rows"] >= 1


def test_partition_uses_open_close_only_and_excludes_0930() -> None:
    date = pd.Timestamp("2023-06-01")
    minute_codes = sorted(campaign047.market.SOURCE_MINUTE_CODE_SET)
    raw = pd.DataFrame(
        {
            "datetime": [date + pd.Timedelta(minutes=code) for code in minute_codes],
            "symbol": "SZ000001",
            "provider": "tushare",
            "open": 10.0 + np.sin(np.arange(241) * 0.17) * 0.04,
            "close": 10.0 + np.sin(np.arange(241) * 0.17 + 0.09) * 0.04,
        },
        columns=campaign047.RAW_COLUMNS,
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
        columns=campaign047.BASE_COLUMNS,
    )
    frame, quality = campaign047.compute_partition_frame(
        raw, base, None, symbol="SZ000001"
    )
    at_0930 = raw["datetime"].dt.strftime("%H:%M") == "09:30"
    raw.loc[at_0930, ["open", "close"]] = 999.0
    changed, changed_quality = campaign047.compute_partition_frame(
        raw, base, None, symbol="SZ000001"
    )
    pd.testing.assert_frame_equal(frame, changed)
    assert quality == changed_quality


def test_wrong_source_projection_fails_closed() -> None:
    with pytest.raises(campaign047.Campaign047FeatureError):
        campaign047.compute_partition_frame(
            pd.DataFrame(
                columns=["datetime", "symbol", "provider", "open", "close", "amount"]
            ),
            pd.DataFrame(columns=campaign047.BASE_COLUMNS),
            None,
            symbol="SZ000001",
        )
