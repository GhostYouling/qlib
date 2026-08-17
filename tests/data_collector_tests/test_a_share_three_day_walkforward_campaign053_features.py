"""Pre-return tests for Campaign053 amount/price-discovery alignment."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign053_features as campaign


def closes_from_returns(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    return np.concatenate((np.exp(np.r_[0.0, np.cumsum(first)]), np.exp(np.r_[0.0, np.cumsum(second)])))[None, :]


def test_campaign053_protocol_is_exact_and_has_76_ordered_comparisons() -> None:
    protocol = campaign.load_protocol()
    candidate = protocol["candidate"]
    comparisons = protocol["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factors"]
    assert candidate["name"] == campaign.FACTOR_NAME
    assert candidate["direction"] == "higher"
    assert tuple(candidate["source_projection"]) == campaign.RAW_COLUMNS
    assert candidate["forbidden_source_columns"] == ["open", "high", "low", "volume"]
    assert len(comparisons) == 76
    assert comparisons[-1] == {"name": campaign.C52_FACTOR_NAME, "score_direction": "higher"}
    assert campaign._comparison_order_digest(comparisons) == campaign.COMPARISON_ORDER_SHA256


def test_campaign053_identical_amount_and_absolute_return_distributions_score_one() -> None:
    first = np.full(119, 0.001)
    second = np.full(119, -0.002)
    closes = closes_from_returns(first, second)
    amounts = np.r_[np.abs(first), np.abs(second)][None, :]
    values, eligible, quality = campaign.compute_factor_values(closes, amounts)
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(1.0)
    assert quality[f"{campaign.FACTOR_NAME}__eligible_rows"] == 1


def test_campaign053_disjoint_amount_and_return_mass_scores_zero() -> None:
    first = np.zeros(119)
    second = np.zeros(119)
    first[0] = 0.1
    closes = closes_from_returns(first, second)
    amounts = np.zeros((1, 238))
    amounts[0, -1] = 1.0
    values, eligible, _ = campaign.compute_factor_values(closes, amounts)
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(0.0, abs=1e-12)


def test_campaign053_rejects_zero_return_or_invalid_amount_stock_days() -> None:
    flat = np.ones((2, 240))
    amounts = np.ones((2, 238))
    amounts[1, 5] = -1.0
    values, eligible, quality = campaign.compute_factor_values(flat, amounts)
    assert eligible[campaign.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[campaign.FACTOR_NAME]).all()
    assert quality[f"{campaign.FACTOR_NAME}__zero_total_absolute_return_rows"] == 2
    assert quality[f"{campaign.FACTOR_NAME}__invalid_amount_rows"] == 1


def test_campaign053_partition_uses_exact_grid_close_and_endpoint_amount() -> None:
    date = pd.Timestamp("2024-01-02")
    minute_codes = [570] + [int(value) for value in campaign.market.CONTINUOUS_MINUTE_CODES]
    datetimes = [date + pd.Timedelta(minutes=code) for code in minute_codes]
    continuous_returns = np.r_[np.full(119, 0.001), np.full(119, -0.001)]
    continuous_closes = closes_from_returns(continuous_returns[:119], continuous_returns[119:])[0]
    close_by_code = {570: continuous_closes[0]}
    close_by_code.update(dict(zip(minute_codes[1:], continuous_closes, strict=True)))
    raw = pd.DataFrame({
        "datetime": datetimes,
        "symbol": "SH600000",
        "provider": "tushare",
        "close": [close_by_code[code] for code in minute_codes],
        "amount": 1.0,
    }).loc[:, campaign.RAW_COLUMNS]
    base = pd.DataFrame({"trade_date": [date], "symbol": ["SH600000"]})
    frame, quality = campaign.compute_partition_frame(raw, base, None, symbol="SH600000")
    assert list(frame.columns) == list(campaign.OUTPUT_COLUMNS)
    assert frame[f"{campaign.FACTOR_NAME}_eligible"].tolist() == [True]
    assert frame[campaign.FACTOR_NAME].iloc[0] == pytest.approx(1.0)
    assert quality["base_rows"] == 1


def test_campaign053_build_is_blocked_until_implementation_freeze_is_bound() -> None:
    with pytest.raises(campaign.Campaign053FeatureError, match="implementation freeze"):
        campaign.build_snapshot(data_root=Path("/tmp/not-used-campaign053"), workers=1)

