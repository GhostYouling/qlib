"""Synthetic and pre-value tests for Campaign036 frontier balance."""

from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


MODULE = importlib.import_module(
    "scripts.a_share_three_day_walkforward_campaign036_features"
)


def _base_high_low(rows: int = 1) -> tuple[np.ndarray, np.ndarray]:
    highs = np.full((rows, 240), 10.0, dtype=float)
    lows = np.full((rows, 240), 9.0, dtype=float)
    return highs, lows


def test_balanced_log_frontier_expansion_has_unit_score():
    highs, lows = _base_high_low()
    for start in (0, 120):
        path = np.linspace(0.0, 0.02, 120)
        highs[0, start : start + 120] = 10.0 * np.exp(path)
        lows[0, start : start + 120] = 9.0 * np.exp(-path)

    values, eligible, quality = MODULE.compute_factor_values(
        highs=highs,
        lows=lows,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(1.0, abs=1e-12)
    assert quality[f"{MODULE.FACTOR_NAME}__identity_mismatch_rows"] == 0
    assert (
        quality[f"{MODULE.FACTOR_NAME}__upward_expansion_observations"]
        == 238
    )
    assert (
        quality[f"{MODULE.FACTOR_NAME}__downward_expansion_observations"]
        == 238
    )


def test_one_sided_expansion_is_zero_and_no_expansion_is_missing():
    highs, lows = _base_high_low(rows=2)
    for start in (0, 120):
        path = np.linspace(0.0, 0.02, 120)
        highs[0, start : start + 120] = 10.0 * np.exp(path)

    values, eligible, quality = MODULE.compute_factor_values(
        highs=highs,
        lows=lows,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True, False]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(0.0, abs=1e-15)
    assert np.isnan(values[MODULE.FACTOR_NAME][1])
    assert quality[f"{MODULE.FACTOR_NAME}__zero_total_expansion_rows"] == 1


def test_frontier_resets_at_lunch_and_ignores_cross_lunch_scale_jump():
    highs, lows = _base_high_low()
    for start in (0, 120):
        path = np.linspace(0.0, 0.02, 120)
        highs[0, start : start + 120] = 10.0 * np.exp(path)
        lows[0, start : start + 120] = 9.0 * np.exp(-0.5 * path)
    shifted_highs = highs.copy()
    shifted_lows = lows.copy()
    shifted_highs[:, 120:] *= 100.0
    shifted_lows[:, 120:] *= 100.0

    first, first_eligible, _ = MODULE.compute_factor_values(
        highs=highs,
        lows=lows,
    )
    second, second_eligible, _ = MODULE.compute_factor_values(
        highs=shifted_highs,
        lows=shifted_lows,
    )

    assert first_eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert second_eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert first[MODULE.FACTOR_NAME][0] == pytest.approx(
        second[MODULE.FACTOR_NAME][0],
        abs=1e-12,
    )


def test_invalid_high_low_and_bad_shapes_fail_closed():
    with pytest.raises(MODULE.Campaign036FeatureError):
        MODULE.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
        )

    highs, lows = _base_high_low(rows=3)
    highs[0, 5] = np.nan
    lows[1, 5] = 0.0
    lows[2, 5] = 11.0
    values, eligible, quality = MODULE.compute_factor_values(
        highs=highs,
        lows=lows,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False, False, False]
    assert np.isnan(values[MODULE.FACTOR_NAME]).all()
    assert quality["invalid_required_high_low_rows"] == 1
    assert quality[f"{MODULE.FACTOR_NAME}__nonpositive_high_low_rows"] == 1
    assert quality[f"{MODULE.FACTOR_NAME}__misordered_high_low_rows"] == 1


def test_protocol_materializes_57_unique_comparisons_in_frozen_order():
    spec = MODULE.load_protocol()
    coverage = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]

    assert coverage["holding_period_sessions"] == 3
    assert len(comparisons) == 57
    assert len({item["name"] for item in comparisons}) == 57
    assert comparisons[-1] == {
        "name": "intraday_return_weak_order_entropy_234t",
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


def test_partition_builder_projects_only_high_low_and_uses_v1_output_root():
    trade_date = pd.Timestamp("2025-01-02")
    minute_codes = sorted(MODULE.market.SOURCE_MINUTE_CODE_SET)
    continuous_codes = list(MODULE.market.CONTINUOUS_MINUTE_CODES)
    path_by_code = {
        code: index for index, code in enumerate(continuous_codes)
    }
    highs = []
    lows = []
    for code in minute_codes:
        if code not in path_by_code:
            highs.append(10.0)
            lows.append(9.0)
            continue
        position = path_by_code[code]
        half_position = position if position < 120 else position - 120
        path = 0.02 * half_position / 119.0
        highs.append(10.0 * np.exp(path))
        lows.append(9.0 * np.exp(-path))
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
            "high": highs,
            "low": lows,
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
    assert MODULE.output_root(MODULE.DEFAULT_DATA_ROOT).name.endswith(
        "campaign036_feature_library_v1"
    )


def test_bound_snapshot_status_reads_no_comparison_values_or_returns():
    result = MODULE.status(
        MODULE.DEFAULT_DATA_ROOT,
        MODULE.DEFAULT_EXPERIMENT_ROOT,
    )

    assert result["protocol_sha256_bound"] is True
    assert result["snapshot_exists"] is True
    assert result["snapshot_sha256_bound"] is True
    assert result["audit_count"] == 1
    assert result["no_return_audit_sha256_bound"] is True
    assert result["source_fields_read_by_status"] == [
        "datetime",
        "symbol",
        "provider",
        "high",
        "low",
    ]
    assert result["forward_return_fields_read_by_status"] is False
    assert result["candidate49_historical_return_read"] is False
