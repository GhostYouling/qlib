"""Pre-value tests for Campaign055 price-update clock entropy."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign055_features as campaign


def _closes_from_updates(
    morning: np.ndarray,
    afternoon: np.ndarray,
    *,
    signed: bool = False,
    afternoon_start: float = 100.0,
) -> np.ndarray:
    assert morning.shape == (119,)
    assert afternoon.shape == (119,)
    halves: list[np.ndarray] = []
    for half_index, updates in enumerate((morning, afternoon)):
        values = [100.0 if half_index == 0 else afternoon_start]
        event_number = 0
        for update in updates:
            if update:
                event_number += 1
                step = 0.01
                if signed and event_number % 2 == 0:
                    step = -0.005
                values.append(values[-1] + step)
            else:
                values.append(values[-1])
        halves.append(np.asarray(values, dtype=float))
    return np.concatenate(halves)


def _two_events_per_bin() -> tuple[np.ndarray, np.ndarray]:
    morning = np.zeros(119, dtype=bool)
    afternoon = np.zeros(119, dtype=bool)
    for half, offset in ((morning, 0), (afternoon, 5)):
        for bin_index in range(offset, offset + 5):
            positions = np.flatnonzero(
                campaign.TRANSITION_BIN_INDEX[:119] == bin_index - offset
            )
            half[positions[:2]] = True
    return morning, afternoon


def test_campaign055_protocol_is_exact_and_has_78_ordered_comparisons() -> None:
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
        "volume",
        "amount",
    ]
    assert candidate["clock_bin_count"] == 10
    assert candidate["minimum_update_events"] == 20
    assert len(comparisons) == 78
    assert comparisons[-1] == {
        "name": "intraday_volume_weighted_transaction_price_bowley_skew_240m",
        "score_direction": "higher",
    }
    assert (
        campaign._comparison_order_digest(comparisons)
        == campaign.COMPARISON_ORDER_SHA256
    )


def test_campaign055_fixed_bin_mapping_covers_each_transition_once() -> None:
    assert campaign.TRANSITION_BIN_INDEX.shape == (238,)
    assert campaign.TRANSITION_BIN_INDEX.min() == 0
    assert campaign.TRANSITION_BIN_INDEX.max() == 9
    assert np.bincount(
        campaign.TRANSITION_BIN_INDEX, minlength=10
    ).tolist() == [24, 24, 24, 24, 23, 24, 24, 24, 24, 23]


def test_campaign055_uniform_clock_updates_score_one() -> None:
    morning, afternoon = _two_events_per_bin()
    closes = _closes_from_updates(morning, afternoon)[None, :]
    values, eligible, quality = campaign.compute_factor_values(closes)
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME].tolist() == pytest.approx([1.0])
    assert quality[f"{campaign.FACTOR_NAME}__eligible_rows"] == 1
    assert quality[f"{campaign.FACTOR_NAME}__eligible_update_events"] == 20
    assert quality[f"{campaign.FACTOR_NAME}__eligible_empty_bin_positions"] == 0


def test_campaign055_concentrated_updates_score_zero() -> None:
    morning = np.zeros(119, dtype=bool)
    afternoon = np.zeros(119, dtype=bool)
    positions = np.flatnonzero(campaign.TRANSITION_BIN_INDEX[:119] == 0)
    morning[positions[:20]] = True
    closes = _closes_from_updates(morning, afternoon)[None, :]
    values, eligible, quality = campaign.compute_factor_values(closes)
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME].tolist() == pytest.approx([0.0])
    assert quality[f"{campaign.FACTOR_NAME}__eligible_empty_bin_positions"] == 9


def test_campaign055_requires_at_least_twenty_updates() -> None:
    morning, afternoon = _two_events_per_bin()
    valid = _closes_from_updates(morning, afternoon)
    morning[np.flatnonzero(morning)[0]] = False
    invalid = _closes_from_updates(morning, afternoon)
    values, eligible, quality = campaign.compute_factor_values(
        np.vstack([invalid, valid])
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [False, True]
    assert np.isnan(values[campaign.FACTOR_NAME][0])
    assert np.isfinite(values[campaign.FACTOR_NAME][1])
    assert quality[f"{campaign.FACTOR_NAME}__insufficient_update_event_rows"] == 1


def test_campaign055_ignores_lunch_jump_update_sign_and_magnitude() -> None:
    morning, afternoon = _two_events_per_bin()
    unsigned = _closes_from_updates(
        morning, afternoon, signed=False, afternoon_start=100.0
    )
    signed_with_lunch_jump = _closes_from_updates(
        morning, afternoon, signed=True, afternoon_start=300.0
    )
    values, eligible, _ = campaign.compute_factor_values(
        np.vstack([unsigned, signed_with_lunch_jump])
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True, True]
    assert values[campaign.FACTOR_NAME].tolist() == pytest.approx([1.0, 1.0])


def test_campaign055_rejects_nonfinite_or_nonpositive_closes() -> None:
    morning, afternoon = _two_events_per_bin()
    closes = np.vstack(
        [
            _closes_from_updates(morning, afternoon),
            _closes_from_updates(morning, afternoon),
        ]
    )
    closes[0, 4] = np.nan
    closes[1, 5] = 0.0
    values, eligible, quality = campaign.compute_factor_values(closes)
    assert eligible[campaign.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[campaign.FACTOR_NAME]).all()
    assert quality[f"{campaign.FACTOR_NAME}__nonfinite_close_rows"] == 1
    assert quality[f"{campaign.FACTOR_NAME}__nonpositive_close_rows"] == 1


def test_campaign055_partition_uses_only_240_continuous_closes() -> None:
    date = pd.Timestamp("2024-01-02")
    minute_codes = [570] + [
        int(value) for value in campaign.market.CONTINUOUS_MINUTE_CODES
    ]
    datetimes = [date + pd.Timedelta(minutes=code) for code in minute_codes]
    morning, afternoon = _two_events_per_bin()
    closes = _closes_from_updates(
        morning, afternoon, signed=True, afternoon_start=250.0
    )
    raw = pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "SH600000",
            "provider": "tushare",
            "close": np.r_[9999.0, closes],
        }
    ).loc[:, campaign.RAW_COLUMNS]
    base = pd.DataFrame({"trade_date": [date], "symbol": ["SH600000"]})
    frame, quality = campaign.compute_partition_frame(
        raw, base, None, symbol="SH600000"
    )
    assert list(frame.columns) == list(campaign.OUTPUT_COLUMNS)
    assert frame[f"{campaign.FACTOR_NAME}_eligible"].tolist() == [True]
    assert frame[campaign.FACTOR_NAME].iloc[0] == pytest.approx(1.0)
    assert quality["base_rows"] == 1


def test_campaign055_build_is_blocked_until_implementation_freeze_is_bound() -> None:
    with pytest.raises(
        campaign.Campaign055FeatureError, match="implementation freeze"
    ):
        campaign.build_snapshot(
            data_root=Path("/tmp/not-used-campaign055"), workers=1
        )
