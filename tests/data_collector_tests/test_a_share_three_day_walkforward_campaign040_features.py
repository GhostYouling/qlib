"""Synthetic and pre-value tests for Campaign040 range-profile similarity."""

from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


MODULE = importlib.import_module(
    "scripts.a_share_three_day_walkforward_campaign040_features"
)


def _high_low_from_ranges(ranges: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ranges = np.asarray(ranges, dtype=float)
    assert ranges.shape == (240,)
    lows = np.full((1, 240), 10.0)
    highs = lows * np.exp(ranges[None, :])
    return highs, lows


def test_identical_morning_and_afternoon_profiles_score_one():
    profile = np.linspace(0.0, 0.02, 120)
    highs, lows = _high_low_from_ranges(np.concatenate((profile, profile)))

    values, eligible, quality = MODULE.compute_factor_values(
        highs=highs,
        lows=lows,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(1.0, abs=1e-12)
    assert (
        quality[f"{MODULE.FACTOR_NAME}__range_bin_observations"] == 240
    )


def test_disjoint_profiles_score_zero_and_retain_zero_bins():
    morning = np.zeros(120)
    afternoon = np.zeros(120)
    morning[0] = 0.02
    afternoon[-1] = 0.03
    highs, lows = _high_low_from_ranges(
        np.concatenate((morning, afternoon))
    )

    values, eligible, _ = MODULE.compute_factor_values(
        highs=highs,
        lows=lows,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(0.0, abs=1e-12)


def test_separate_half_normalization_is_scale_invariant():
    morning = np.linspace(0.001, 0.02, 120)
    afternoon = np.linspace(0.02, 0.001, 120)
    first_highs, first_lows = _high_low_from_ranges(
        np.concatenate((morning, afternoon))
    )
    second_highs, second_lows = _high_low_from_ranges(
        np.concatenate((morning * 7.0, afternoon * 0.3))
    )

    first, first_eligible, _ = MODULE.compute_factor_values(
        highs=first_highs,
        lows=first_lows,
    )
    second, second_eligible, _ = MODULE.compute_factor_values(
        highs=second_highs,
        lows=second_lows,
    )

    assert first_eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert second_eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert first[MODULE.FACTOR_NAME][0] == pytest.approx(
        second[MODULE.FACTOR_NAME][0],
        abs=1e-12,
    )


def test_zero_total_in_either_half_is_missing():
    morning_zero = np.concatenate(
        (np.zeros(120), np.full(120, 0.01))
    )
    afternoon_zero = np.concatenate(
        (np.full(120, 0.01), np.zeros(120))
    )
    ranges = np.stack((morning_zero, afternoon_zero))
    lows = np.full((2, 240), 10.0)
    highs = lows * np.exp(ranges)

    values, eligible, quality = MODULE.compute_factor_values(
        highs=highs,
        lows=lows,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[MODULE.FACTOR_NAME]).all()
    assert quality[f"{MODULE.FACTOR_NAME}__zero_morning_total_range_rows"] == 1
    assert quality[f"{MODULE.FACTOR_NAME}__zero_afternoon_total_range_rows"] == 1


def test_invalid_high_low_and_bad_shape_fail_closed():
    with pytest.raises(MODULE.Campaign040FeatureError):
        MODULE.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
        )

    highs = np.full((3, 240), 10.1)
    lows = np.full((3, 240), 10.0)
    highs[0, 5] = np.nan
    lows[1, 5] = 0.0
    highs[2, 5] = 9.0
    values, eligible, quality = MODULE.compute_factor_values(
        highs=highs,
        lows=lows,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False, False, False]
    assert np.isnan(values[MODULE.FACTOR_NAME]).all()
    assert quality["invalid_required_high_low_rows"] == 1
    assert quality[f"{MODULE.FACTOR_NAME}__nonpositive_high_low_rows"] == 1
    assert quality[f"{MODULE.FACTOR_NAME}__misordered_high_low_rows"] == 1


def test_protocol_materializes_61_unique_comparisons_in_frozen_order():
    spec = MODULE.load_protocol()
    coverage = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]

    assert coverage["holding_period_sessions"] == 3
    assert len(comparisons) == 61
    assert len({item["name"] for item in comparisons}) == 61
    assert comparisons[-1] == {
        "name": "intraday_return_time_reversal_asymmetry_236p",
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


def test_partition_builder_projects_high_low_only_and_uses_v1_output_root():
    trade_date = pd.Timestamp("2025-01-02")
    minute_codes = sorted(MODULE.market.SOURCE_MINUTE_CODE_SET)
    continuous_codes = list(MODULE.market.CONTINUOUS_MINUTE_CODES)
    position_by_code = {
        code: index for index, code in enumerate(continuous_codes)
    }
    profile = np.linspace(0.001, 0.02, 120)
    ranges = np.concatenate((profile, profile))
    lows = np.full(240, 10.0)
    highs = lows * np.exp(ranges)
    raw_highs = [
        10.1
        if code not in position_by_code
        else highs[position_by_code[code]]
        for code in minute_codes
    ]
    raw_lows = [
        10.0
        if code not in position_by_code
        else lows[position_by_code[code]]
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
            "high": raw_highs,
            "low": raw_lows,
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
    assert frame[MODULE.FACTOR_NAME][0] == pytest.approx(1.0, abs=1e-12)
    assert quality[f"{MODULE.FACTOR_NAME}__eligible_rows"] == 1
    assert MODULE.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "high",
        "low",
    )
    assert MODULE.output_root(MODULE.DEFAULT_DATA_ROOT).name.endswith(
        "campaign040_feature_library_v1"
    )


def test_status_reads_no_comparison_values_or_returns():
    result = MODULE.status(
        MODULE.DEFAULT_DATA_ROOT,
        MODULE.DEFAULT_EXPERIMENT_ROOT,
    )

    assert result["protocol_sha256_bound"] is True
    assert result["snapshot_sha256_bound"] is bool(
        MODULE.SNAPSHOT_MANIFEST_SHA256
    )
    assert result["no_return_audit_sha256_bound"] is bool(
        MODULE.NO_RETURN_AUDIT_SHA256
    )
    assert result["source_fields_read_by_status"] == [
        "datetime",
        "symbol",
        "provider",
        "high",
        "low",
    ]
    assert result[
        "minute_open_high_low_volume_amount_fields_read_by_status"
    ] == ["high", "low"]
    assert result["forward_return_fields_read_by_status"] is False
    assert result["candidate49_historical_return_read"] is False


def test_bound_snapshot_manifest_truthfully_records_high_low_without_close():
    manifest_path = (
        MODULE.output_root(MODULE.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    )
    manifest = MODULE.json.loads(manifest_path.read_text(encoding="utf-8"))

    MODULE._validate_snapshot_manifest(
        manifest,
        require_fingerprint_constants=True,
    )
    assert manifest["source_fields_read"] == list(MODULE.RAW_COLUMNS)
    assert manifest["source_open_high_low_read"] is True
    assert manifest["source_close_read"] is False
    assert manifest["source_volume_read"] is False
    assert manifest["source_amount_read"] is False
    assert manifest["daily_price_fields_read"] == []
    assert manifest["forward_return_fields_read"] is False
    assert manifest["comparison_factor_values_read"] is False
