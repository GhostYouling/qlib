"""Synthetic and pre-value boundary tests for Campaign064."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign064_features as campaign064


def _highs_lows_from_ranges(ranges: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(ranges, dtype=float)
    lows = np.full(values.shape, 10.0, dtype=float)
    highs = lows * np.exp(values)
    return highs, lows


def test_exact_ties_are_retained_and_all_one_state_has_zero_entropy() -> None:
    highs = np.full((1, 240), 10.0)
    lows = np.full((1, 240), 10.0)
    values, eligible, quality = campaign064.compute_factor_values(
        highs=highs,
        lows=lows,
    )
    assert eligible[campaign064.FACTOR_NAME].tolist() == [True]
    assert values[campaign064.FACTOR_NAME].tolist() == [0.0]
    assert quality[f"{campaign064.FACTOR_NAME}__exact_tie_triple_observations"] == 236
    assert quality[f"{campaign064.FACTOR_NAME}__zero_range_bar_observations"] == 240


def test_strictly_increasing_range_in_each_half_has_zero_entropy() -> None:
    half = np.arange(120, dtype=float) * 1e-5
    highs, lows = _highs_lows_from_ranges(np.r_[half, half][None, :])
    values, eligible, quality = campaign064.compute_factor_values(
        highs=highs,
        lows=lows,
    )
    assert eligible[campaign064.FACTOR_NAME].tolist() == [True]
    assert values[campaign064.FACTOR_NAME][0] == pytest.approx(0.0, abs=1e-15)
    assert quality[f"{campaign064.FACTOR_NAME}__exact_tie_triple_observations"] == 0


def test_halves_are_separate_and_no_lunch_triple_is_formed() -> None:
    morning = np.zeros(120, dtype=float)
    afternoon = np.arange(120, dtype=float) * 1e-5
    ranges_a = np.r_[morning, afternoon][None, :]
    ranges_b = ranges_a.copy()
    ranges_b[:, 120:] += 100.0
    value_a, eligible_a, quality_a = campaign064._weak_order_entropy_from_ranges(ranges_a)
    value_b, eligible_b, quality_b = campaign064._weak_order_entropy_from_ranges(ranges_b)
    assert eligible_a.tolist() == eligible_b.tolist() == [True]
    assert value_a[0] == pytest.approx(value_b[0], abs=1e-15)
    assert quality_a["exact_tie_triple_observations"] == 118
    assert quality_b["exact_tie_triple_observations"] == 118


def test_thirteen_transitive_weak_order_codes_are_fixed() -> None:
    assert campaign064.WEAK_ORDER_CODES.tolist() == [
        0,
        1,
        2,
        5,
        8,
        9,
        13,
        17,
        18,
        21,
        24,
        25,
        26,
    ]


def test_nonfinite_nonpositive_low_misordering_and_shape_fail_closed() -> None:
    with pytest.raises(campaign064.Campaign064FeatureError):
        campaign064.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
        )
    highs = np.full((3, 240), 10.0)
    lows = np.full((3, 240), 9.0)
    highs[0, 5] = np.nan
    lows[1, 5] = 0.0
    highs[2, 5] = 8.0
    values, eligible, quality = campaign064.compute_factor_values(
        highs=highs,
        lows=lows,
    )
    assert eligible[campaign064.FACTOR_NAME].tolist() == [False, False, False]
    assert np.isnan(values[campaign064.FACTOR_NAME]).all()
    assert quality["invalid_required_high_low_rows"] == 1
    assert quality[f"{campaign064.FACTOR_NAME}__nonpositive_low_rows"] == 1
    assert quality[f"{campaign064.FACTOR_NAME}__misordered_high_low_rows"] == 1


def test_protocol_reconstructs_exact_95_factor_order() -> None:
    spec = campaign064.load_protocol()
    comparisons = campaign064.reconstruct_comparisons(spec)
    assert len(comparisons) == 95
    assert len({item["name"] for item in comparisons}) == 95
    assert campaign064._comparison_order_digest(comparisons) == campaign064.COMPARISON_ORDER_SHA256
    assert comparisons[-1] == {
        "name": "intraday_cross_sectional_standardized_return_state_stability_236p",
        "score_direction": "higher",
    }
    assert spec["finite_development_catalog_if_admitted"]["complexity"] == 1


def test_partition_builder_uses_high_low_only_and_exact_grid() -> None:
    trade_date = pd.Timestamp("2025-01-02")
    raw = pd.DataFrame(
        {
            "datetime": [
                trade_date
                + pd.Timedelta(hours=minute_code // 60)
                + pd.Timedelta(minutes=minute_code % 60)
                for minute_code in campaign064.SOURCE_MINUTE_CODES
            ],
            "symbol": "SZ000001",
            "provider": "tushare",
            "high": 10.0,
            "low": 10.0,
        },
        columns=campaign064.RAW_COLUMNS,
    )
    base = pd.DataFrame(
        {
            "trade_date": [trade_date],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
        },
        columns=campaign064.BASE_COLUMNS,
    )
    profiles, source_quality = campaign064.extract_range_profiles(
        raw,
        symbol="SZ000001",
    )
    frame, factor_quality = campaign064.compute_output_frame(
        base,
        profiles,
        {},
        symbol="SZ000001",
    )
    quality = {**source_quality, **factor_quality}
    assert frame[campaign064.FACTOR_NAME].tolist() == [0.0]
    assert frame[f"{campaign064.FACTOR_NAME}_eligible"].tolist() == [True]
    assert quality["source_rows"] == 241
    assert quality[f"{campaign064.FACTOR_NAME}__exact_tie_triple_observations"] == 236


def test_exact_column_empty_partition_is_the_only_empty_repair() -> None:
    raw = pd.DataFrame(columns=campaign064.RAW_COLUMNS)
    base = pd.DataFrame(columns=campaign064.BASE_COLUMNS)
    profiles, source_quality = campaign064.extract_range_profiles(
        raw,
        symbol="SZ000001",
    )
    frame, factor_quality = campaign064.compute_output_frame(
        base,
        profiles,
        {},
        symbol="SZ000001",
    )
    quality = {**source_quality, **factor_quality}
    assert tuple(frame.columns) == campaign064.OUTPUT_COLUMNS
    assert frame.empty
    assert quality["source_rows"] == 0
    assert quality["manifest_declared_empty_partition_accepted"] == 1

    wrong = pd.DataFrame(columns=("datetime", "symbol", "provider", "high"))
    with pytest.raises(campaign064.Campaign064FeatureError):
        campaign064.extract_range_profiles(wrong, symbol="SZ000001")


def test_generated_publication_template_is_truthful_high_low_zero_lookback() -> None:
    generated_source = campaign064._runtime["_source"]
    expected = (
        '            "source_fields_read": list(RAW_COLUMNS),\n'
        '            "source_open_high_low_close_volume_read": True,\n'
        '            "source_high_low_read": True,\n'
        '            "source_close_read": False,\n'
        '            "source_amount_read": False,\n'
        '            "cross_session_lookback": 0,\n'
    )
    assert expected in generated_source
    assert generated_source.count(expected) == 1


def test_checkpoint_validator_accepts_only_exact_frozen_identity_pairs(tmp_path) -> None:
    frame_path = tmp_path / "2019.parquet"
    record_path = tmp_path / "2019.json"
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2019-01-02")],
            "symbol": ["SH600004"],
            "provider": ["tushare"],
            campaign064.FACTOR_NAME: [0.0],
            f"{campaign064.FACTOR_NAME}_eligible": [True],
        },
        columns=campaign064.OUTPUT_COLUMNS,
    )
    campaign064.foundation.atomic_write_frame(frame, frame_path)
    record = {
        "kind": "a_share_three_day_walkforward_campaign064_feature_partition",
        "symbol": "SH600004",
        "year": 2019,
        "protocol_sha256": campaign064.PROTOCOL_SHA256,
        "feature_runner_sha256": campaign064.PRE_MANIFEST_REPAIR_RUNNER_SHA256,
        "implementation_freeze_sha256": (
            campaign064.PRE_MANIFEST_REPAIR_IMPLEMENTATION_FREEZE_SHA256
        ),
        "output_byte_sha256": campaign064._local_sha256(frame_path),
        "output_frame_sha256": campaign064.foundation.frame_digest(frame),
        "rows": 1,
    }
    record_path.write_text(json.dumps(record), encoding="utf-8")
    validator = campaign064._engine["_validate_checkpoint"]
    accepted = validator(
        frame_path,
        record_path,
        symbol="SH600004",
        year=2019,
        runner_sha256="f" * 64,
        implementation_freeze_sha256="e" * 64,
    )
    assert accepted == record

    record["implementation_freeze_sha256"] = "e" * 64
    record_path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(campaign064.Campaign064FeatureError):
        validator(
            frame_path,
            record_path,
            symbol="SH600004",
            year=2019,
            runner_sha256="f" * 64,
            implementation_freeze_sha256="e" * 64,
        )
