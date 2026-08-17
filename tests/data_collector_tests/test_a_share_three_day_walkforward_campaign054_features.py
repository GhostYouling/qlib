"""Pre-value tests for Campaign054 transaction-price Bowley skew."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign054_features as campaign


def _four_block_log_prices(last: float = 10.0) -> np.ndarray:
    return np.r_[
        np.zeros(60),
        np.ones(60),
        np.full(59, 2.0),
        np.full(61, last),
    ]


def test_campaign054_protocol_is_exact_and_has_77_ordered_comparisons() -> None:
    protocol = campaign.load_protocol()
    candidate = protocol["candidate"]
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert candidate["name"] == campaign.FACTOR_NAME
    assert candidate["direction"] == "higher"
    assert tuple(candidate["source_projection"]) == campaign.RAW_COLUMNS
    assert candidate["forbidden_source_columns"] == [
        "open",
        "high",
        "low",
        "close",
    ]
    assert candidate["quantile_probabilities"] == [0.25, 0.5, 0.75]
    assert candidate["minimum_active_bars"] == 120
    assert len(comparisons) == 77
    assert comparisons[-1] == {
        "name": "intraday_amount_price_discovery_alignment_js_238p",
        "score_direction": "higher",
    }
    assert (
        campaign._comparison_order_digest(comparisons)
        == campaign.COMPARISON_ORDER_SHA256
    )


def test_campaign054_right_and_left_skew_have_frozen_sign() -> None:
    right = _four_block_log_prices()
    left = -right[::-1]
    volumes = np.ones((2, 240))
    amounts = np.exp(np.vstack([right, left]))
    values, eligible, quality = campaign.compute_factor_values(volumes, amounts)
    assert eligible[campaign.FACTOR_NAME].tolist() == [True, True]
    # The frozen left-continuous empirical inverse is intentionally discrete:
    # the reflected block masses put Q25/Q50/Q75 at -10/-2/-1, hence -7/9.
    assert values[campaign.FACTOR_NAME].tolist() == pytest.approx([0.8, -7.0 / 9.0])
    assert quality[f"{campaign.FACTOR_NAME}__eligible_rows"] == 2


def test_campaign054_log_price_unit_shift_cancels() -> None:
    log_prices = _four_block_log_prices()
    volumes = np.linspace(1.0, 3.0, 240)[None, :]
    amounts = volumes * np.exp(log_prices)[None, :]
    shifted = amounts * 1000.0
    first, first_eligible, _ = campaign.compute_factor_values(volumes, amounts)
    second, second_eligible, _ = campaign.compute_factor_values(volumes, shifted)
    assert first_eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert second_eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert second[campaign.FACTOR_NAME] == pytest.approx(
        first[campaign.FACTOR_NAME], abs=1e-12
    )


def test_campaign054_joint_zero_is_inactive_but_one_sided_zero_is_invalid() -> None:
    volumes = np.zeros((2, 240))
    amounts = np.zeros((2, 240))
    active_log_prices = np.linspace(0.0, 2.0, 120)
    volumes[:, :120] = 1.0
    amounts[:, :120] = np.exp(active_log_prices)
    amounts[1, 120] = 1.0
    values, eligible, quality = campaign.compute_factor_values(volumes, amounts)
    assert eligible[campaign.FACTOR_NAME].tolist() == [True, False]
    assert np.isfinite(values[campaign.FACTOR_NAME][0])
    assert np.isnan(values[campaign.FACTOR_NAME][1])
    assert quality[f"{campaign.FACTOR_NAME}__one_sided_zero_rows"] == 1


def test_campaign054_rejects_fewer_than_120_active_bars_and_flat_quantiles() -> None:
    volumes = np.zeros((2, 240))
    amounts = np.zeros((2, 240))
    volumes[0, :119] = 1.0
    amounts[0, :119] = np.exp(np.linspace(0.0, 2.0, 119))
    volumes[1, :120] = 1.0
    amounts[1, :120] = 5.0
    values, eligible, quality = campaign.compute_factor_values(volumes, amounts)
    assert eligible[campaign.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[campaign.FACTOR_NAME]).all()
    assert quality[f"{campaign.FACTOR_NAME}__insufficient_active_bar_rows"] == 1
    assert quality[f"{campaign.FACTOR_NAME}__nonpositive_quantile_spread_rows"] == 1


def test_campaign054_rejects_negative_or_nonfinite_raw_inputs() -> None:
    volumes = np.ones((2, 240))
    amounts = np.exp(np.vstack([_four_block_log_prices(), _four_block_log_prices()]))
    volumes[0, 7] = -1.0
    amounts[1, 8] = np.nan
    values, eligible, quality = campaign.compute_factor_values(volumes, amounts)
    assert eligible[campaign.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[campaign.FACTOR_NAME]).all()
    assert quality[f"{campaign.FACTOR_NAME}__invalid_raw_rows"] == 2


def test_campaign054_partition_uses_240_continuous_volume_amount_bars() -> None:
    date = pd.Timestamp("2024-01-02")
    minute_codes = [570] + [
        int(value) for value in campaign.market.CONTINUOUS_MINUTE_CODES
    ]
    datetimes = [date + pd.Timedelta(minutes=code) for code in minute_codes]
    log_prices = _four_block_log_prices()
    price_by_code = {570: 1.0}
    price_by_code.update(
        dict(zip(minute_codes[1:], np.exp(log_prices), strict=True))
    )
    raw = pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "SH600000",
            "provider": "tushare",
            "volume": 1.0,
            "amount": [price_by_code[code] for code in minute_codes],
        }
    ).loc[:, campaign.RAW_COLUMNS]
    base = pd.DataFrame({"trade_date": [date], "symbol": ["SH600000"]})
    frame, quality = campaign.compute_partition_frame(
        raw, base, None, symbol="SH600000"
    )
    assert list(frame.columns) == list(campaign.OUTPUT_COLUMNS)
    assert frame[f"{campaign.FACTOR_NAME}_eligible"].tolist() == [True]
    assert frame[campaign.FACTOR_NAME].iloc[0] == pytest.approx(0.8)
    assert quality["base_rows"] == 1


def test_campaign054_build_is_blocked_until_implementation_freeze_is_bound() -> None:
    with pytest.raises(
        campaign.Campaign054FeatureError, match="implementation freeze"
    ):
        campaign.build_snapshot(
            data_root=Path("/tmp/not-used-campaign054"), workers=1
        )
