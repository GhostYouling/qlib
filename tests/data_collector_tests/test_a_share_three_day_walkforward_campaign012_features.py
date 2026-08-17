import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign012_features as FEATURES


REPO_ROOT = Path(__file__).resolve().parents[2]


def _ranges(log_ranges: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(log_ranges, dtype=float)
    return np.exp(values), np.ones_like(values)


def _manual_value(log_ranges: np.ndarray) -> float:
    lags = np.concatenate((log_ranges[:119], log_ranges[120:239]))
    leads = np.concatenate((log_ranges[1:120], log_ranges[121:240]))
    return -float(np.corrcoef(lags, leads)[0, 1])


def test_range_reversal_has_frozen_alternating_endpoint() -> None:
    pattern = np.tile(np.array([0.1, 1.0]), 120)
    highs, lows = _ranges(pattern)
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 1


def test_range_persistence_is_negative_after_frozen_direction() -> None:
    half = np.concatenate((np.full(60, 0.1), np.full(60, 1.0)))
    pattern = np.concatenate((half, half))
    highs, lows = _ranges(pattern)
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME][0] < -0.95


def test_correlation_is_invariant_to_positive_range_scale() -> None:
    pattern = np.linspace(0.1, 1.0, 240)
    first = _ranges(pattern)
    second = _ranges(pattern * 2.0)
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=np.vstack([first[0], second[0]]),
        lows=np.vstack([first[1], second[1]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(
        values[FEATURES.FACTOR_NAME][1]
    )


def test_lunch_transition_is_never_formed() -> None:
    morning = np.linspace(0.1, 0.9, 120)
    afternoon = np.linspace(2.0, 1.0, 120)
    pattern = np.concatenate((morning, afternoon))
    highs, lows = _ranges(pattern)
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    expected = _manual_value(pattern)
    with_lunch = -float(np.corrcoef(pattern[:-1], pattern[1:])[0, 1])
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(expected)
    assert abs(values[FEATURES.FACTOR_NAME][0] - with_lunch) > 0.005


def test_minimum_informative_pair_gate_is_fail_closed() -> None:
    boundary = np.zeros(240)
    boundary[:120] = np.linspace(0.1, 1.0, 120)
    boundary[120] = 0.5
    sparse = np.zeros(240)
    sparse[:119] = np.linspace(0.1, 1.0, 119)
    first = _ranges(boundary)
    second = _ranges(sparse)
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=np.vstack([first[0], second[0]]),
        lows=np.vstack([first[1], second[1]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][1])
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__fewer_than_120_informative_pair_rows"]
        == 1
    )


def test_zero_zero_pairs_remain_in_fixed_correlation_arrays() -> None:
    pattern = np.zeros(240)
    pattern[:120] = np.linspace(0.1, 1.0, 120)
    pattern[120] = 0.5
    highs, lows = _ranges(pattern)
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(
        _manual_value(pattern)
    )


def test_constant_pair_arrays_are_missing_not_zero() -> None:
    highs, lows = _ranges(np.ones(240))
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__degenerate_lag_or_lead_variance_rows"]
        == 1
    )


def test_low_high_ordering_violation_is_not_repaired() -> None:
    highs, lows = _ranges(np.linspace(0.1, 1.0, 240))
    lows[7] = highs[7] * 2.0
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__low_high_ordering_violation_rows"]
        == 1
    )


def test_invalid_shapes_and_values_are_rejected_or_ineligible() -> None:
    with pytest.raises(FEATURES.Campaign012FeatureError):
        FEATURES.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
        )
    highs, lows = _ranges(np.linspace(0.1, 1.0, 240))
    highs[0] = np.nan
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality["invalid_required_high_low_rows"] == 1


def test_partition_reads_only_high_low_and_excludes_0930() -> None:
    pattern = np.tile(np.array([0.1, 1.0]), 120)
    highs, lows = _ranges(pattern)
    codes = [570] + list(FEATURES.market.CONTINUOUS_MINUTE_CODES)
    timestamp = [
        pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code))
        for code in codes
    ]
    raw = pd.DataFrame(
        {
            "datetime": timestamp,
            "symbol": "SH600000",
            "provider": "tushare",
            "high": np.concatenate([[-1.0], highs]),
            "low": np.concatenate([[-2.0], lows]),
        }
    ).loc[:, FEATURES.RAW_COLUMNS]
    base = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2020-01-02")],
            "symbol": ["SH600000"],
        }
    )
    frame, quality = FEATURES.compute_partition_frame(
        raw,
        base,
        None,
        symbol="SH600000",
    )
    assert tuple(frame.columns) == FEATURES.OUTPUT_COLUMNS
    assert frame[f"{FEATURES.FACTOR_NAME}_eligible"].tolist() == [True]
    assert frame[FEATURES.FACTOR_NAME].iloc[0] == pytest.approx(1.0)
    assert quality["base_rows"] == 1
    assert "open" not in FEATURES.RAW_COLUMNS
    assert "close" not in FEATURES.RAW_COLUMNS
    assert "volume" not in FEATURES.RAW_COLUMNS
    assert "amount" not in FEATURES.RAW_COLUMNS


def test_source_contract_and_parent_are_fingerprint_bound() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_012_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_012_mechanism_overlap_audit.json"
        ).read_text()
    )
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN011_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN011_FEATURE_RUNNER_SHA256
    )
    assert concept["selected_concept"]["formula"] is None
    assert concept["selected_concept"]["direction"] is None
    assert concept["research_boundary"]["candidate_values_computed_or_read"] is False
    assert audit["candidate"]["name"] == FEATURES.FACTOR_NAME
    assert audit["candidate"]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["candidate"]["direction"] == "higher"
    assert audit["candidate"]["selected_bar_count"] == 240
    assert audit["candidate"]["adjacent_pair_count"] == 238
    assert audit["candidate"]["minimum_informative_pairs"] == 120
    assert audit["comparison_catalog"]["semantic_terminal_mechanism_count"] == 35
    assert audit["comparison_catalog"]["statistical_comparison_factor_count"] == 34
    assert audit["research_boundary"]["historical_forward_returns_read"] is False
    assert audit["source_schema_boundary"]["forbidden_source_fields"] == [
        "open",
        "close",
        "volume",
        "amount",
    ]
