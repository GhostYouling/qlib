"""Offline tests for the separate Tushare minute sentiment cleaning layer."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "a_share_tushare_one_minute_sentiment_clean.py"
)
SPEC = importlib.util.spec_from_file_location(
    "a_share_tushare_one_minute_sentiment_clean", SCRIPT_PATH
)
CLEAN = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = CLEAN
SPEC.loader.exec_module(CLEAN)


def source_frame(*, active_opening: bool) -> pd.DataFrame:
    trade_date = pd.Timestamp("2025-12-31")
    datetimes = [
        pd.Timestamp.combine(trade_date.date(), value)
        for value in CLEAN.expected_source_times()
    ]
    close = np.linspace(10.0, 10.24, 241)
    volume = np.full(241, 100.0)
    if not active_opening:
        close[0] = 8.0
        volume[0] = 0.0
    amount = close * volume
    return pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "SH600519",
            "source_symbol": "600519.SH",
            "provider": "tushare",
            "open": close,
            "high": close + 0.01,
            "low": close - 0.01,
            "close": close,
            "volume": volume,
            "amount": amount,
        }
    )


def daily_frame(source: pd.DataFrame, *, close_multiplier: float = 1.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp("2025-12-31")],
            "raw_close": [float(source["close"].iloc[-1]) * close_multiplier],
            "raw_volume": [float(source["volume"].sum()) / 100.0],
            "amount": [float(source["amount"].sum())],
            "price_basis": [CLEAN.REQUIRED_DAILY_PRICE_BASIS],
            # These intentionally disagree and must never enter the four features.
            "raw_open": [1.0],
            "raw_high": [999.0],
            "raw_low": [0.01],
        }
    )


def test_zero_activity_0930_is_dropped_without_using_its_price() -> None:
    source = source_frame(active_opening=False)
    result, quality = CLEAN.clean_partition_frame(
        source, daily_frame(source), symbol="SH600519"
    )

    assert len(result) == 1
    assert result.loc[0, "opening_row_role"] == "reference_placeholder"
    assert result.loc[0, "source_minute_bars"] == 241
    assert result.loc[0, "canonical_bars"] == 240
    canonical = source.iloc[1:].reset_index(drop=True)
    late_index = CLEAN.LATE_START_INDEX
    assert result.loc[0, "late_return_30m"] == pytest.approx(
        canonical["close"].iloc[-1] / canonical["close"].iloc[late_index] - 1.0
    )
    expected_rv = np.sqrt(np.square(np.diff(np.log(canonical["close"]))).sum())
    assert result.loc[0, "intraday_realized_volatility"] == pytest.approx(expected_rv)
    assert quality["eligible_reference_placeholder_sessions"] == 1
    assert quality["eligible_active_auction_sessions"] == 0


def test_active_0930_is_merged_into_0931_activity() -> None:
    source = source_frame(active_opening=True)
    result, quality = CLEAN.clean_partition_frame(
        source, daily_frame(source), symbol="SH600519"
    )

    assert len(result) == 1
    assert result.loc[0, "opening_row_role"] == "active_auction"
    assert result.loc[0, "volume_ratio_to_local_daily"] == pytest.approx(100.0)
    assert result.loc[0, "amount_ratio_to_local_daily"] == pytest.approx(1.0)
    assert quality["eligible_active_auction_sessions"] == 1


def test_daily_open_high_low_mismatch_does_not_reject_retained_features() -> None:
    source = source_frame(active_opening=False)
    daily = daily_frame(source)
    result, quality = CLEAN.clean_partition_frame(
        source, daily, symbol="SH600519"
    )

    assert len(result) == 1
    assert quality["eligible_sessions"] == 1
    assert set(CLEAN.FEATURE_COLUMNS).issubset(result.columns)


def test_bad_daily_close_reconciliation_is_rejected() -> None:
    source = source_frame(active_opening=True)
    result, quality = CLEAN.clean_partition_frame(
        source, daily_frame(source, close_multiplier=1.01), symbol="SH600519"
    )

    assert result.empty
    assert quality["close_reconciliation_failed_sessions"] == 1
    assert quality["eligible_sessions"] == 0


def test_duplicate_minute_is_not_treated_as_an_exact_grid() -> None:
    source = source_frame(active_opening=True)
    source.loc[1, "datetime"] = source.loc[0, "datetime"]
    result, quality = CLEAN.clean_partition_frame(
        source, daily_frame(source), symbol="SH600519"
    )

    assert result.empty
    assert quality["exact_source_grid_sessions"] == 0
    assert quality["incomplete_or_off_grid_sessions"] == 1


def test_zero_late_window_volume_is_rejected_as_nonfinite_feature() -> None:
    source = source_frame(active_opening=True)
    late_start = CLEAN.LATE_START_INDEX + 2  # source includes the leading 09:30 row
    source.loc[late_start:, "volume"] = 0.0
    source.loc[late_start:, "amount"] = 0.0
    result, quality = CLEAN.clean_partition_frame(
        source, daily_frame(source), symbol="SH600519"
    )

    assert result.empty
    assert quality["nonfinite_feature_sessions"] == 1
    assert quality["eligible_sessions"] == 0


def test_fieldwise_overlay_keeps_close_factors_when_daily_amount_misses() -> None:
    source = source_frame(active_opening=True)
    daily = daily_frame(source)
    daily.loc[0, "amount"] *= 1.01

    result, quality = CLEAN.fieldwise_overlay_frame(
        source, daily, symbol="SH600519"
    )

    assert len(result) == 1
    assert result.loc[0, "late_return_30m_eligible"]
    assert result.loc[0, "intraday_realized_volatility_eligible"]
    assert not result.loc[0, "late_amount_share_30m_eligible"]
    assert not result.loc[0, "late_vwap_to_day_vwap_30m_eligible"]
    assert np.isnan(result.loc[0, "late_amount_share_30m"])
    assert quality["late_return_30m_recovered_sessions"] == 1


def test_fieldwise_overlay_keeps_three_factors_when_late_volume_is_zero() -> None:
    source = source_frame(active_opening=True)
    late_start = CLEAN.LATE_START_INDEX + 2
    source.loc[late_start:, "volume"] = 0.0
    source.loc[late_start:, "amount"] = 0.0
    daily = daily_frame(source)

    result, quality = CLEAN.fieldwise_overlay_frame(
        source, daily, symbol="SH600519"
    )

    assert len(result) == 1
    assert result.loc[0, "late_return_30m_eligible"]
    assert result.loc[0, "late_amount_share_30m_eligible"]
    assert not result.loc[0, "late_vwap_to_day_vwap_30m_eligible"]
    assert result.loc[0, "intraday_realized_volatility_eligible"]
    assert result.loc[0, "late_amount_share_30m"] == pytest.approx(0.0)
    assert np.isnan(result.loc[0, "late_vwap_to_day_vwap_30m"])
    assert quality["overlay_rows"] == 1


def test_fieldwise_overlay_never_duplicates_a_joint_base_key() -> None:
    source = source_frame(active_opening=True)
    result, quality = CLEAN.fieldwise_overlay_frame(
        source,
        daily_frame(source),
        symbol="SH600519",
        base_dates=[pd.Timestamp("2025-12-31")],
    )

    assert result.empty
    assert quality["base_overlap_sessions"] == 1


def test_fieldwise_exception_selection_uses_only_frozen_quality_counts() -> None:
    manifest = {
        "files": [
            {
                "symbol": "SH600001",
                "year": 2020,
                "rows": 99,
                "quality": {
                    "exact_source_grid_sessions": 100,
                    "missing_local_daily_sessions": 0,
                    "amount_reconciliation_failed_sessions": 1,
                },
            },
            {
                "symbol": "SH600002",
                "year": 2020,
                "rows": 99,
                "quality": {
                    "exact_source_grid_sessions": 100,
                    "missing_local_daily_sessions": 0,
                    "amount_reconciliation_failed_sessions": 0,
                },
            },
            {
                "symbol": "SH600003",
                "year": 2020,
                "rows": 100,
                "quality": {
                    "exact_source_grid_sessions": 100,
                    "missing_local_daily_sessions": 0,
                    "amount_reconciliation_failed_sessions": 0,
                },
            },
        ]
    }

    selected = CLEAN.select_fieldwise_exception_partitions(manifest)

    assert [item["symbol"] for item in selected] == ["SH600001", "SH600002"]
