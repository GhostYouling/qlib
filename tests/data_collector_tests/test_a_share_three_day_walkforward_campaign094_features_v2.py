"""Tests for Campaign094's additive feature quality-schema repair."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign094_features as v1
from scripts import a_share_three_day_walkforward_campaign094_features_v2 as v2


def test_v1_and_repair_inputs_are_immutable() -> None:
    assert v2._sha256(Path(v1.__file__).resolve()) == v2.V1_RUNNER_SHA256
    assert v2._sha256(v2.V1_FREEZE) == v2.V1_FREEZE_SHA256
    assert v2._sha256(v2.FAILURE_RECORD) == v2.FAILURE_RECORD_SHA256
    assert v2._sha256(v2.REPAIR_PROTOCOL) == v2.REPAIR_PROTOCOL_SHA256


def test_quality_adapter_adds_only_inherited_alias(monkeypatch) -> None:
    values = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-02"]),
            v1.FACTOR_NAME: [0.125],
        }
    )
    quality = {
        "source_rows": 242,
        "source_sessions": 1,
        "valid_range_local_peak_clock_dispersion_sessions": 1,
        "invalid_selected_source_sessions": 0,
        "insufficient_strict_local_peak_sessions": 0,
        "invalid_ordered_hl_sessions": 0,
        "morning_strict_local_peaks": 10,
        "afternoon_strict_local_peaks": 11,
        "zero_range_bars": 12,
    }
    monkeypatch.setattr(
        v1,
        "extract_range_local_peak_clock_dispersion",
        lambda raw, *, symbol: (values, quality),
    )
    actual_values, actual_quality = v2._quality_compatible_extract(
        pd.DataFrame(), symbol="SH600000"
    )
    pd.testing.assert_frame_equal(actual_values, values)
    assert actual_quality["zero_range_bars"] == 12
    assert actual_quality["zero_destination_range_pairs"] == 12
    assert actual_quality["endpoint_canonicalized_sessions"] == 0
    assert len(actual_quality) == len(quality) + 2


def test_v2_status_is_read_only_and_snapshot_absent() -> None:
    report = v2.status()
    assert report["status"] == "snapshot_absent_pre_v2_retry"
    assert report["source_or_candidate_values_read_by_status"] is False
    assert report["comparison_values_read_by_status"] is False
    assert (
        report["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert report["provider_request_issued_by_status"] is False


def test_repair_does_not_change_factor_or_range_contract() -> None:
    assert v1.FACTOR_NAME == "intraday_range_local_peak_clock_dispersion_236p"
    assert v1.RAW_COLUMNS == ("datetime", "symbol", "provider", "high", "low")
    assert v1.MAXIMUM_SCORE == 0.25
    assert v2.OUTPUT_COLUMNS == (
        "stock_day_key",
        v1.FACTOR_NAME,
        f"{v1.FACTOR_NAME}_eligible",
    )
