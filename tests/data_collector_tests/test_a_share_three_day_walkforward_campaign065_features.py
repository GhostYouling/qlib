"""Synthetic and pre-value boundary tests for Campaign065."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign065_features as campaign065


def _highs_lows_from_ranges(ranges: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(ranges, dtype=float)
    lows = np.full(values.shape, 10.0, dtype=float)
    highs = lows * np.exp(values)
    return highs, lows


def test_all_ties_are_valid_and_reversal_invariant() -> None:
    highs = np.full((1, 240), 10.0)
    lows = np.full((1, 240), 10.0)
    values, eligible, quality = campaign065.compute_factor_values(
        highs=highs,
        lows=lows,
    )
    assert eligible[campaign065.FACTOR_NAME].tolist() == [True]
    assert values[campaign065.FACTOR_NAME].tolist() == [0.0]
    assert quality[f"{campaign065.FACTOR_NAME}__exact_tie_triple_observations"] == 236
    assert quality[f"{campaign065.FACTOR_NAME}__zero_range_bar_observations"] == 240
    assert quality[f"{campaign065.FACTOR_NAME}__reversal_invariant_rows"] == 1


def test_strictly_increasing_halves_have_maximal_time_arrow() -> None:
    half = np.arange(120, dtype=float) * 1e-5
    highs, lows = _highs_lows_from_ranges(np.r_[half, half][None, :])
    values, eligible, quality = campaign065.compute_factor_values(
        highs=highs,
        lows=lows,
    )
    assert eligible[campaign065.FACTOR_NAME].tolist() == [True]
    assert values[campaign065.FACTOR_NAME][0] == pytest.approx(1.0, abs=1e-15)
    assert quality[f"{campaign065.FACTOR_NAME}__exact_tie_triple_observations"] == 0


def test_self_reversing_peak_and_valley_states_have_zero_divergence() -> None:
    half = np.tile(np.asarray([0.0, 1e-5]), 60)
    values, eligible, quality = campaign065._weak_order_time_reversal_divergence_from_ranges(
        np.r_[half, half][None, :]
    )
    assert eligible.tolist() == [True]
    assert values[0] == pytest.approx(0.0, abs=1e-15)
    assert quality["self_reversing_state_observations"] == 236


def test_reversing_each_half_preserves_symmetric_divergence() -> None:
    rng = np.random.default_rng(20260805)
    ranges = rng.uniform(0.0, 1e-3, size=(1, 240))
    reversed_ranges = np.concatenate(
        (ranges[:, :120][:, ::-1], ranges[:, 120:][:, ::-1]), axis=1
    )
    forward, forward_eligible, _ = (
        campaign065._weak_order_time_reversal_divergence_from_ranges(ranges)
    )
    backward, backward_eligible, _ = (
        campaign065._weak_order_time_reversal_divergence_from_ranges(reversed_ranges)
    )
    assert forward_eligible.tolist() == backward_eligible.tolist() == [True]
    assert forward[0] == pytest.approx(backward[0], abs=1e-15)


def test_halves_are_separate_and_no_lunch_triple_is_formed() -> None:
    morning = np.arange(120, dtype=float) * 1e-5
    afternoon = np.arange(120, dtype=float)[::-1] * 1e-5
    ranges_a = np.r_[morning, afternoon][None, :]
    ranges_b = ranges_a.copy()
    ranges_b[:, 120:] += 100.0
    value_a, eligible_a, _ = (
        campaign065._weak_order_time_reversal_divergence_from_ranges(ranges_a)
    )
    value_b, eligible_b, _ = (
        campaign065._weak_order_time_reversal_divergence_from_ranges(ranges_b)
    )
    assert eligible_a.tolist() == eligible_b.tolist() == [True]
    assert value_a[0] == pytest.approx(value_b[0], abs=1e-15)


def test_thirteen_states_and_reversal_involution_are_fixed() -> None:
    assert campaign065.WEAK_ORDER_CODES.tolist() == [
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
    assert campaign065.REVERSAL_INDEX.tolist() == [12, 7, 4, 3, 2, 11, 6, 1, 10, 9, 8, 5, 0]
    assert np.array_equal(
        campaign065.REVERSAL_INDEX[campaign065.REVERSAL_INDEX],
        np.arange(13),
    )


def test_nonfinite_nonpositive_low_misordering_and_shape_fail_closed() -> None:
    with pytest.raises(campaign065.Campaign065FeatureError):
        campaign065.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
        )
    highs = np.full((3, 240), 10.0)
    lows = np.full((3, 240), 9.0)
    highs[0, 5] = np.nan
    lows[1, 5] = 0.0
    highs[2, 5] = 8.0
    values, eligible, quality = campaign065.compute_factor_values(
        highs=highs,
        lows=lows,
    )
    assert eligible[campaign065.FACTOR_NAME].tolist() == [False, False, False]
    assert np.isnan(values[campaign065.FACTOR_NAME]).all()
    assert quality["invalid_required_high_low_rows"] == 1
    assert quality[f"{campaign065.FACTOR_NAME}__nonpositive_low_rows"] == 1
    assert quality[f"{campaign065.FACTOR_NAME}__misordered_high_low_rows"] == 1


def test_protocol_reconstructs_exact_full_and_numeric_orders() -> None:
    spec = campaign065.load_protocol()
    full = campaign065.reconstruct_complete_definitions(spec)
    numeric = campaign065.reconstruct_comparisons(spec)
    assert len(full) == 96
    assert len({item["name"] for item in full}) == 96
    assert campaign065._comparison_order_digest(full) == (
        campaign065.FULL_DEFINITION_ORDER_SHA256
    )
    assert len(numeric) == 95
    assert campaign065.STRUCTURALLY_NONNUMERIC_FACTOR in [item["name"] for item in full]
    assert campaign065.STRUCTURALLY_NONNUMERIC_FACTOR not in [
        item["name"] for item in numeric
    ]
    assert campaign065._comparison_order_digest(numeric) == (
        campaign065.COMPARISON_ORDER_SHA256
    )
    assert numeric[-1] == {
        "name": "intraday_range_weak_order_entropy_236t",
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
                for minute_code in campaign065.SOURCE_MINUTE_CODES
            ],
            "symbol": "SZ000001",
            "provider": "tushare",
            "high": 10.0,
            "low": 10.0,
        },
        columns=campaign065.RAW_COLUMNS,
    )
    base = pd.DataFrame(
        {
            "trade_date": [trade_date],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
        },
        columns=campaign065.BASE_COLUMNS,
    )
    profiles, source_quality = campaign065.extract_range_profiles(
        raw,
        symbol="SZ000001",
    )
    frame, factor_quality = campaign065.compute_output_frame(
        base,
        profiles,
        {},
        symbol="SZ000001",
    )
    quality = {**source_quality, **factor_quality}
    assert frame[campaign065.FACTOR_NAME].tolist() == [0.0]
    assert frame[f"{campaign065.FACTOR_NAME}_eligible"].tolist() == [True]
    assert quality["source_rows"] == 241
    assert quality[f"{campaign065.FACTOR_NAME}__exact_tie_triple_observations"] == 236


def test_exact_column_empty_partition_is_the_only_empty_repair() -> None:
    raw = pd.DataFrame(columns=campaign065.RAW_COLUMNS)
    base = pd.DataFrame(columns=campaign065.BASE_COLUMNS)
    profiles, source_quality = campaign065.extract_range_profiles(
        raw,
        symbol="SZ000001",
    )
    frame, factor_quality = campaign065.compute_output_frame(
        base,
        profiles,
        {},
        symbol="SZ000001",
    )
    quality = {**source_quality, **factor_quality}
    assert tuple(frame.columns) == campaign065.OUTPUT_COLUMNS
    assert frame.empty
    assert quality["source_rows"] == 0
    assert quality["manifest_declared_empty_partition_accepted"] == 1

    wrong = pd.DataFrame(columns=("datetime", "symbol", "provider", "high"))
    with pytest.raises(campaign065.Campaign065FeatureError):
        campaign065.extract_range_profiles(wrong, symbol="SZ000001")


def test_generated_publication_template_is_truthful_high_low_zero_lookback() -> None:
    generated_source = campaign065.GENERATED_PUBLICATION_SOURCE
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


def test_checkpoint_validator_accepts_only_current_exact_frozen_identity(tmp_path) -> None:
    frame_path = tmp_path / "2019.parquet"
    record_path = tmp_path / "2019.json"
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2019-01-02")],
            "symbol": ["SH600004"],
            "provider": ["tushare"],
            campaign065.FACTOR_NAME: [0.0],
            f"{campaign065.FACTOR_NAME}_eligible": [True],
        },
        columns=campaign065.OUTPUT_COLUMNS,
    )
    campaign065.foundation.atomic_write_frame(frame, frame_path)
    record = {
        "kind": "a_share_three_day_walkforward_campaign065_feature_partition",
        "symbol": "SH600004",
        "year": 2019,
        "protocol_sha256": campaign065.PROTOCOL_SHA256,
        "feature_runner_sha256": "f" * 64,
        "implementation_freeze_sha256": "e" * 64,
        "output_byte_sha256": campaign065._local_sha256(frame_path),
        "output_frame_sha256": campaign065.foundation.frame_digest(frame),
        "rows": 1,
    }
    record_path.write_text(json.dumps(record), encoding="utf-8")
    accepted = campaign065._validate_checkpoint(
        frame_path,
        record_path,
        symbol="SH600004",
        year=2019,
        runner_sha256="f" * 64,
        implementation_freeze_sha256="e" * 64,
    )
    assert accepted == record

    record["implementation_freeze_sha256"] = "d" * 64
    record_path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(campaign065.Campaign065FeatureError):
        campaign065._validate_checkpoint(
            frame_path,
            record_path,
            symbol="SH600004",
            year=2019,
            runner_sha256="f" * 64,
            implementation_freeze_sha256="e" * 64,
        )


def test_concept_and_overlap_records_remain_value_free_and_bound() -> None:
    for relative in (
        "docs/a_share_three_day_walkforward_campaign_065_concept_scouting.json",
        "docs/a_share_three_day_walkforward_campaign_065_mechanism_overlap_audit.json",
    ):
        path = campaign065.REPO_ROOT / relative
        report = campaign065.bindings.validate_record(
            path,
            data_root=campaign065.DEFAULT_DATA_ROOT,
        )
        assert report["all_bindings_passed"] is True
        record = json.loads(path.read_text(encoding="utf-8"))
        boundary = record["research_boundary"]
        assert boundary["campaign065_source_values_read"] is False
        assert boundary["campaign065_candidate_values_read"] is False
        assert boundary["historical_daily_price_fields_read"] == []
        assert boundary["historical_forward_return_fields_read"] is False
        assert boundary["provider_request_issued"] is False
