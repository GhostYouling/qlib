"""Synthetic and protocol tests for Campaign073 affordability features."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign073_features as candidate


def _raw_frame(
    *, symbol: str = "SH600000", dates: tuple[str, ...] = ("2025-01-02",)
) -> pd.DataFrame:
    rows = []
    for day_index, raw_date in enumerate(dates):
        date = pd.Timestamp(raw_date)
        for position, minute_code in enumerate(candidate.SOURCE_MINUTE_CODES):
            rows.append(
                {
                    "datetime": date
                    + pd.Timedelta(
                        hours=minute_code // 60, minutes=minute_code % 60
                    ),
                    "symbol": symbol,
                    "provider": "tushare",
                    "close": 10.0 + day_index + position / 1000.0,
                }
            )
    return pd.DataFrame(rows, columns=candidate.RAW_COLUMNS)


def test_campaign073_frozen_grid_has_241_source_and_240_selected_bars() -> None:
    assert len(candidate.SOURCE_MINUTE_CODES) == 241
    assert len(candidate.CONTINUOUS_MINUTE_CODES) == 240
    assert candidate.SOURCE_MINUTE_CODES[0] == 9 * 60 + 30
    assert candidate.CONTINUOUS_MINUTE_CODES[0] == 9 * 60 + 31
    assert candidate.CONTINUOUS_MINUTE_CODES[119] == 11 * 60 + 30
    assert candidate.CONTINUOUS_MINUTE_CODES[120] == 13 * 60 + 1
    assert candidate.CONTINUOUS_MINUTE_CODES[-1] == 15 * 60


def test_extract_terminal_closes_uses_exact_1500_close() -> None:
    raw = _raw_frame(dates=("2025-01-02", "2025-01-03"))
    terminals, quality = candidate.extract_terminal_closes(raw, symbol="SH600000")
    expected = (
        raw.loc[
            raw["datetime"].dt.hour.eq(15) & raw["datetime"].dt.minute.eq(0)
        ]
        .sort_values("datetime")["close"]
        .to_numpy()
    )
    assert terminals["trade_date"].tolist() == [
        pd.Timestamp("2025-01-02"),
        pd.Timestamp("2025-01-03"),
    ]
    assert terminals["terminal_close"].to_numpy() == pytest.approx(expected)
    assert quality == {
        "source_rows": 482,
        "source_sessions": 2,
        "valid_terminal_sessions": 2,
        "invalid_close_grid_sessions": 0,
    }


def test_extract_terminal_closes_marks_whole_session_missing_on_invalid_close() -> None:
    raw = _raw_frame()
    raw.loc[raw["datetime"].dt.time == pd.Timestamp("10:00").time(), "close"] = 0.0
    terminals, quality = candidate.extract_terminal_closes(raw, symbol="SH600000")
    assert np.isnan(terminals.loc[0, "terminal_close"])
    assert quality["valid_terminal_sessions"] == 0
    assert quality["invalid_close_grid_sessions"] == 1


def test_extract_terminal_closes_fails_closed_on_wrong_grid() -> None:
    raw = _raw_frame().iloc[:-1].copy()
    with pytest.raises(candidate.Campaign073FeatureError, match="minute grid changed"):
        candidate.extract_terminal_closes(raw, symbol="SH600000")


def test_attach_terminal_closes_requires_exact_identity_dates() -> None:
    identity = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2025-01-02", "2025-01-03"]),
            "symbol": ["SH600000", "SH600000"],
            "provider": ["tushare", "tushare"],
        }
    )
    terminals = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2025-01-02"]),
            "terminal_close": [10.0],
        }
    )
    with pytest.raises(candidate.Campaign073FeatureError, match="absent from raw"):
        candidate.attach_terminal_closes(
            identity, terminals, symbol="SH600000"
        )


def test_rank_affordability_uses_average_ties_and_one_minus_rank() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2025-01-02"] * 5),
            "symbol": ["SH600000", "SH600001", "SH600002", "SH600003", "SH600004"],
            "provider": ["tushare"] * 5,
            "terminal_close": [10.0, 20.0, 10.0, 40.0, np.nan],
        }
    )
    ranked = candidate.rank_affordability_year_frame(frame)
    assert ranked[candidate.FACTOR_NAME].to_numpy()[:4] == pytest.approx(
        [0.625, 0.25, 0.625, 0.0]
    )
    assert np.isnan(ranked[candidate.FACTOR_NAME].iloc[4])
    assert ranked[f"{candidate.FACTOR_NAME}_eligible"].tolist() == [
        True,
        True,
        True,
        True,
        False,
    ]


def test_validate_value_semantics_enforces_exclusive_upper_endpoint() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2025-01-02"]),
            "symbol": ["SH600000"],
            "provider": ["tushare"],
            candidate.FACTOR_NAME: [1.0],
            f"{candidate.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, candidate.OUTPUT_COLUMNS]
    with pytest.raises(candidate.Campaign073FeatureError, match="value semantics"):
        candidate.validate_value_semantics(frame)


def test_campaign073_protocol_and_frozen_definition_orders_validate_without_values() -> None:
    spec = candidate.load_protocol()
    comparisons = candidate.reconstruct_comparisons()
    complete = candidate.reconstruct_complete_definitions()
    assert spec["candidate"]["name"] == candidate.FACTOR_NAME
    assert len(comparisons) == 103
    assert comparisons[-1] == {
        "name": "quarterly_joint_profit_revenue_growth_floor_rank",
        "score_direction": "higher",
    }
    assert len(complete) == 104
    assert candidate._comparison_order_digest(comparisons) == candidate.COMPARISON_ORDER_SHA256
    assert candidate._comparison_order_digest(complete) == candidate.FULL_DEFINITION_ORDER_SHA256
