"""Synthetic and pre-value tests for Campaign043 transaction-VWAP consensus."""

from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


MODULE = importlib.import_module(
    "scripts.a_share_three_day_walkforward_campaign043_features"
)


def _activity(prices: np.ndarray | float = 10.0) -> tuple[np.ndarray, np.ndarray]:
    volumes = np.ones((1, MODULE.SELECTED_BAR_COUNT), dtype=float)
    price_array = np.broadcast_to(
        np.asarray(prices, dtype=float), volumes.shape
    ).copy()
    return volumes, volumes * price_array


def test_constant_transaction_price_scores_one():
    volumes, amounts = _activity()
    values, eligible, quality = MODULE.compute_factor_values(
        volumes=volumes,
        amounts=amounts,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(1.0)
    assert quality[f"{MODULE.FACTOR_NAME}__eligible_rows"] == 1


def test_dispersion_reduces_consensus_and_price_scale_is_invariant():
    prices = np.r_[np.full(120, 10.0), np.full(120, 20.0)][None, :]
    volumes, amounts = _activity(prices)
    values, eligible, _ = MODULE.compute_factor_values(
        volumes=volumes,
        amounts=amounts,
    )
    scaled, scaled_eligible, _ = MODULE.compute_factor_values(
        volumes=volumes,
        amounts=amounts * 7.0,
    )

    expected = np.sqrt(10.0 * 20.0) / 15.0
    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert scaled_eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(expected)
    assert scaled[MODULE.FACTOR_NAME][0] == pytest.approx(expected)


def test_joint_zero_bars_are_inactive_and_120_active_bars_are_sufficient():
    volumes, amounts = _activity()
    volumes[:, :120] = 0.0
    amounts[:, :120] = 0.0
    values, eligible, quality = MODULE.compute_factor_values(
        volumes=volumes,
        amounts=amounts,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [True]
    assert values[MODULE.FACTOR_NAME][0] == pytest.approx(1.0)
    assert quality[f"{MODULE.FACTOR_NAME}__joint_zero_bar_observations"] == 120
    assert quality[f"{MODULE.FACTOR_NAME}__insufficient_active_bar_rows"] == 0


def test_fewer_than_120_active_bars_is_missing():
    volumes, amounts = _activity()
    volumes[:, :121] = 0.0
    amounts[:, :121] = 0.0
    values, eligible, quality = MODULE.compute_factor_values(
        volumes=volumes,
        amounts=amounts,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[MODULE.FACTOR_NAME][0])
    assert quality[f"{MODULE.FACTOR_NAME}__insufficient_active_bar_rows"] == 1


def test_one_sided_zero_fails_the_whole_stock_day():
    volumes, amounts = _activity()
    volumes[0, 7] = 0.0
    values, eligible, quality = MODULE.compute_factor_values(
        volumes=volumes,
        amounts=amounts,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[MODULE.FACTOR_NAME][0])
    assert quality[f"{MODULE.FACTOR_NAME}__one_sided_zero_rows"] == 1


def test_invalid_shape_negative_and_nonfinite_inputs_fail_closed():
    with pytest.raises(MODULE.Campaign043FeatureError):
        MODULE.compute_factor_values(
            volumes=np.ones((1, 239)),
            amounts=np.ones((1, 239)),
        )

    volumes = np.ones((2, MODULE.SELECTED_BAR_COUNT), dtype=float)
    amounts = volumes * 10.0
    volumes[0, 4] = -1.0
    amounts[1, 4] = np.nan
    values, eligible, quality = MODULE.compute_factor_values(
        volumes=volumes,
        amounts=amounts,
    )

    assert eligible[MODULE.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[MODULE.FACTOR_NAME]).all()
    assert quality[f"{MODULE.FACTOR_NAME}__negative_volume_or_amount_rows"] == 1
    assert quality["invalid_required_volume_or_amount_rows"] == 1


def test_protocol_materializes_64_unique_comparisons_in_frozen_order():
    spec = MODULE.load_protocol()
    coverage = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]

    assert coverage["holding_period_sessions"] == 3
    assert len(comparisons) == 64
    assert len({item["name"] for item in comparisons}) == 64
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


def test_partition_builder_projects_only_volume_and_amount():
    trade_date = pd.Timestamp("2025-01-02")
    minute_codes = sorted(MODULE.market.SOURCE_MINUTE_CODE_SET)
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
            "volume": 100.0,
            "amount": 1000.0,
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
        "volume",
        "amount",
    )
    assert MODULE.output_root(MODULE.DEFAULT_DATA_ROOT).name.endswith(
        "campaign043_feature_library_v1"
    )


def test_status_reads_no_comparison_values_or_returns():
    result = MODULE.status(
        MODULE.DEFAULT_DATA_ROOT,
        MODULE.DEFAULT_EXPERIMENT_ROOT,
    )

    assert result["protocol_sha256_bound"] is True
    assert result["source_fields_read_by_status"] == list(MODULE.RAW_COLUMNS)
    assert result["minute_volume_and_amount_fields_read_by_status"] == [
        "volume",
        "amount",
    ]
    assert result["minute_open_high_low_or_close_fields_read_by_status"] == []
    assert result["daily_price_fields_read_by_status"] is False
    assert result["forward_return_fields_read_by_status"] is False
    assert result["candidate49_historical_return_read"] is False
