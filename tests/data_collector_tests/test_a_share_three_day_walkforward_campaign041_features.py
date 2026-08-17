"""Synthetic and pre-value tests for Campaign041 microgap absorption."""

from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


MODULE = importlib.import_module(
    "scripts.a_share_three_day_walkforward_campaign041_features"
)


def _ohlc_from_absorption(
    absorbed_flags: list[bool | None],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    assert len(absorbed_flags) == MODULE.FIXED_TRANSITION_COUNT
    opens = np.empty(240, dtype=float)
    highs = np.empty(240, dtype=float)
    lows = np.empty(240, dtype=float)
    closes = np.empty(240, dtype=float)
    flag_index = 0
    for half_start in (0, 120):
        price = 10.0
        opens[half_start] = price
        highs[half_start] = price * 1.001
        lows[half_start] = price * 0.999
        closes[half_start] = price
        for index in range(half_start + 1, half_start + 120):
            previous = closes[index - 1]
            flag = absorbed_flags[flag_index]
            flag_index += 1
            if flag is None:
                current_open = previous
                current_low = previous * 0.999
            elif flag:
                current_open = previous * 1.01
                current_low = previous * 0.999
            else:
                current_open = previous * 1.01
                current_low = previous * 1.005
            opens[index] = current_open
            lows[index] = current_low
            closes[index] = current_open
            highs[index] = current_open * 1.001
    return (
        opens[None, :],
        highs[None, :],
        lows[None, :],
        closes[None, :],
    )


def test_all_nonzero_microgaps_absorbed_score_one():
    opens, highs, lows, closes = _ohlc_from_absorption([True] * 238)

    values, eligible, quality = MODULE.compute_factor_values(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(1.0)
    assert (
        quality[
            f"{MODULE.FACTOR_NAME}__informative_nonzero_gap_observations"
        ]
        == 238
    )
    assert (
        quality[
            f"{MODULE.FACTOR_NAME}__absorbed_informative_gap_observations"
        ]
        == 238
    )


def test_half_absorbed_score_one_half_and_zero_gaps_are_excluded():
    flags: list[bool | None] = [True] * 60 + [False] * 60
    flags.extend([None] * (238 - len(flags)))
    opens, highs, lows, closes = _ohlc_from_absorption(flags)

    values, eligible, quality = MODULE.compute_factor_values(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(0.5)
    assert (
        quality[
            f"{MODULE.FACTOR_NAME}__informative_nonzero_gap_observations"
        ]
        == 120
    )


def test_minimum_thirty_informative_gaps_is_exact():
    failing = [True] * 29 + [None] * 209
    passing = [True] * 30 + [None] * 208
    rows = [
        _ohlc_from_absorption(flags)
        for flags in (failing, passing)
    ]
    opens = np.concatenate([row[0] for row in rows], axis=0)
    highs = np.concatenate([row[1] for row in rows], axis=0)
    lows = np.concatenate([row[2] for row in rows], axis=0)
    closes = np.concatenate([row[3] for row in rows], axis=0)

    values, eligible, quality = MODULE.compute_factor_values(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False, True]
    assert np.isnan(values[MODULE.FACTOR_NAME][0])
    assert values[MODULE.FACTOR_NAME][1] == pytest.approx(1.0)
    assert (
        quality[
            f"{MODULE.FACTOR_NAME}__insufficient_informative_gap_rows"
        ]
        == 1
    )


def test_lunch_transition_is_not_a_factor_pair():
    flags: list[bool | None] = [True] * 238
    opens, highs, lows, closes = _ohlc_from_absorption(flags)
    opens[0, 120] = 1000.0
    highs[0, 120] = 1001.0
    lows[0, 120] = 9.0

    values, eligible, quality = MODULE.compute_factor_values(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(1.0)
    assert (
        quality[f"{MODULE.FACTOR_NAME}__fixed_transition_observations"]
        == 238
    )


def test_invalid_shape_nonpositive_and_misordered_ohlc_fail_closed():
    with pytest.raises(MODULE.Campaign041FeatureError):
        MODULE.compute_factor_values(
            opens=np.ones((1, 239)),
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
            closes=np.ones((1, 239)),
        )

    base = _ohlc_from_absorption([True] * 238)
    rows = [np.repeat(array, 3, axis=0) for array in base]
    opens, highs, lows, closes = rows
    opens[0, 5] = np.nan
    lows[1, 5] = 0.0
    highs[2, 5] = opens[2, 5] * 0.5

    values, eligible, quality = MODULE.compute_factor_values(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False, False, False]
    assert np.isnan(values[MODULE.FACTOR_NAME]).all()
    assert quality["invalid_required_ohlc_rows"] == 1
    assert quality[f"{MODULE.FACTOR_NAME}__nonpositive_ohlc_rows"] == 1
    assert quality[f"{MODULE.FACTOR_NAME}__misordered_ohlc_rows"] == 1


def test_protocol_materializes_62_unique_comparisons_in_frozen_order():
    spec = MODULE.load_protocol()
    coverage = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]

    assert coverage["holding_period_sessions"] == 3
    assert len(comparisons) == 62
    assert len({item["name"] for item in comparisons}) == 62
    assert comparisons[-1] == {
        "name": MODULE.OLD_FACTOR,
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


def test_partition_builder_projects_ohlc_only_and_uses_v1_output_root():
    trade_date = pd.Timestamp("2025-01-02")
    minute_codes = sorted(MODULE.market.SOURCE_MINUTE_CODE_SET)
    continuous_codes = list(MODULE.market.CONTINUOUS_MINUTE_CODES)
    position_by_code = {
        code: index for index, code in enumerate(continuous_codes)
    }
    opens, highs, lows, closes = _ohlc_from_absorption([True] * 238)

    def values_for(column: np.ndarray, fallback: float) -> list[float]:
        return [
            fallback
            if code not in position_by_code
            else float(column[0, position_by_code[code]])
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
            "open": values_for(opens, 10.0),
            "high": values_for(highs, 10.01),
            "low": values_for(lows, 9.99),
            "close": values_for(closes, 10.0),
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
    assert frame[MODULE.FACTOR_NAME][0] == pytest.approx(1.0)
    assert quality[f"{MODULE.FACTOR_NAME}__eligible_rows"] == 1
    assert MODULE.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "open",
        "high",
        "low",
        "close",
    )
    assert MODULE.output_root(MODULE.DEFAULT_DATA_ROOT).name.endswith(
        "campaign041_feature_library_v1"
    )


def test_status_reads_no_comparison_values_or_returns():
    result = MODULE.status(
        MODULE.DEFAULT_DATA_ROOT,
        MODULE.DEFAULT_EXPERIMENT_ROOT,
    )

    assert result["protocol_sha256_bound"] is True
    assert result["source_fields_read_by_status"] == list(MODULE.RAW_COLUMNS)
    assert result["minute_volume_or_amount_fields_read_by_status"] == []
    assert result["daily_price_fields_read_by_status"] is False
    assert result["forward_return_fields_read_by_status"] is False
    assert result["candidate49_historical_return_read"] is False
