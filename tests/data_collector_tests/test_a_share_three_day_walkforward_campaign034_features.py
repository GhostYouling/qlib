"""Synthetic and pre-value boundary tests for Campaign034 price clustering."""

from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


MODULE = importlib.import_module(
    "scripts.a_share_three_day_walkforward_campaign034_features"
)


def test_all_round_tenths_have_zero_avoidance():
    closes = np.full((1, 240), 10.10, dtype=float)

    values, eligible, quality = MODULE.compute_factor_values(closes=closes)

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME].tolist() == [0.0]
    assert quality[f"{MODULE.FACTOR_NAME}__round_tenth_close_observations"] == 240


def test_all_non_round_fen_prices_have_unit_avoidance():
    closes = np.full((1, 240), 10.01, dtype=float)

    values, eligible, quality = MODULE.compute_factor_values(closes=closes)

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME].tolist() == [1.0]
    assert quality[f"{MODULE.FACTOR_NAME}__round_tenth_close_observations"] == 0


def test_fixed_support_counts_repeated_closes_without_deduplication():
    closes = np.full((1, 240), 10.01, dtype=float)
    closes[0, :60] = 10.20

    values, eligible, _ = MODULE.compute_factor_values(closes=closes)

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(0.75)


def test_non_tick_nonpositive_nonfinite_and_bad_shape_fail_closed():
    with pytest.raises(MODULE.Campaign034FeatureError):
        MODULE.compute_factor_values(closes=np.ones((1, 239)))

    closes = np.full((3, 240), 10.01, dtype=float)
    closes[0, 10] = 10.015
    closes[1, 10] = 0.0
    closes[2, 10] = np.nan
    values, eligible, quality = MODULE.compute_factor_values(closes=closes)

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False, False, False]
    assert np.isnan(values[MODULE.FACTOR_NAME]).all()
    assert quality[f"{MODULE.FACTOR_NAME}__non_tick_grid_close_rows"] == 1


def test_protocol_freezes_one_candidate_and_55_unique_comparisons():
    spec = MODULE.load_protocol()
    coverage = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]

    assert coverage["holding_period_sessions"] == 3
    assert len(comparisons) == 55
    assert len({item["name"] for item in comparisons}) == 55
    assert comparisons[-1]["name"] == "intraday_return_spectral_entropy_59f"
    assert spec["candidates"][0]["name"] == MODULE.FACTOR_NAME
    assert (
        spec["finite_post_admissibility_search"]["trial"]["factor"]
        == MODULE.FACTOR_NAME
    )


def test_partition_builder_uses_round_grid_formula_and_v2_output_root():
    partition_builder = MODULE._generated["compute_partition_frame"]
    assert (
        partition_builder.__globals__["compute_factor_values"]
        is MODULE.compute_factor_values
    )
    assert MODULE.output_root(MODULE.DEFAULT_DATA_ROOT).name.endswith(
        "campaign034_feature_library_v2"
    )

    trade_date = pd.Timestamp("2025-01-02")
    minute_codes = sorted(MODULE._generated["market"].SOURCE_MINUTE_CODE_SET)
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
            "close": 10.01,
        },
        columns=MODULE.RAW_COLUMNS,
    )
    base_frame = pd.DataFrame(
        {"trade_date": [trade_date], "symbol": ["SZ000001"]},
        columns=MODULE._generated["BASE_COLUMNS"],
    )

    frame, quality = partition_builder(
        raw,
        base_frame,
        None,
        symbol="SZ000001",
    )

    assert frame[MODULE.FACTOR_NAME].tolist() == [1.0]
    assert frame[f"{MODULE.FACTOR_NAME}_eligible"].tolist() == [True]
    assert (
        quality[f"{MODULE.FACTOR_NAME}__round_tenth_close_observations"] == 0
    )
    assert f"{MODULE.FACTOR_NAME}__nonfinite_power_rows" not in quality


def test_bound_snapshot_status_has_no_return_or_audit_side_effect():
    result = MODULE.status(
        MODULE.DEFAULT_DATA_ROOT,
        MODULE.DEFAULT_EXPERIMENT_ROOT,
    )

    assert result["protocol_sha256_bound"] is True
    assert result["snapshot_exists"] is True
    assert result["snapshot_sha256_bound"] is True
    assert result["audit_count"] == 1
    assert result["no_return_audit_sha256_bound"] is True
    assert result["forward_return_fields_read_by_status"] is False
    assert result["candidate49_historical_return_read"] is False
