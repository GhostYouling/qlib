import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign011_features as FEATURES


REPO_ROOT = Path(__file__).resolve().parents[2]


def _ranges(log_ranges: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(log_ranges, dtype=float)
    return np.exp(values), np.ones_like(values)


def test_range_entropy_has_frozen_uniform_endpoint() -> None:
    highs, lows = _ranges(np.ones(240))
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 1


def test_zero_range_bars_remain_in_fixed_240_support() -> None:
    log_ranges = np.concatenate([np.ones(120), np.zeros(120)])
    highs, lows = _ranges(log_ranges)
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    expected = np.log(120.0) / np.log(240.0)
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(expected)
    assert values[FEATURES.FACTOR_NAME][0] < 1.0


def test_entropy_uses_range_participation_not_absolute_scale() -> None:
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


def test_minimum_positive_range_bar_gate_is_fail_closed() -> None:
    boundary = _ranges(np.concatenate([np.ones(120), np.zeros(120)]))
    sparse = _ranges(np.concatenate([np.ones(119), np.zeros(121)]))
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=np.vstack([boundary[0], sparse[0]]),
        lows=np.vstack([boundary[1], sparse[1]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][1])
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__fewer_than_120_positive_range_bar_rows"
        ]
        == 1
    )


def test_low_high_ordering_violation_is_not_repaired() -> None:
    highs, lows = _ranges(np.ones(240))
    lows[7] = highs[7] * 2.0
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__low_high_ordering_violation_rows"
        ]
        == 1
    )


def test_invalid_shapes_and_values_are_rejected_or_ineligible() -> None:
    with pytest.raises(FEATURES.Campaign011FeatureError):
        FEATURES.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
        )
    highs, lows = _ranges(np.ones(240))
    highs[0] = np.nan
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality["invalid_required_high_low_rows"] == 1


def test_partition_reads_only_high_low_and_excludes_0930() -> None:
    highs, lows = _ranges(np.ones(240))
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


def test_empty_joint_base_returns_an_empty_partition() -> None:
    raw = pd.DataFrame(
        {
            "datetime": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
            "provider": pd.Series(dtype="string"),
            "high": pd.Series(dtype="float64"),
            "low": pd.Series(dtype="float64"),
        }
    ).loc[:, FEATURES.RAW_COLUMNS]
    base = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
        }
    )
    frame, quality = FEATURES.compute_partition_frame(
        raw,
        base,
        None,
        symbol="SH600145",
    )
    assert frame.empty
    assert tuple(frame.columns) == FEATURES.OUTPUT_COLUMNS
    assert quality == {"base_rows": 0}


def test_source_contract_records_no_values_or_returns() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_011_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_011_mechanism_overlap_audit.json"
        ).read_text()
    )
    assert concept["selected_concept"]["formula"] is None
    assert concept["selected_concept"]["direction"] is None
    assert concept["research_boundary"]["candidate_values_computed_or_read"] is False
    assert audit["candidate"]["name"] == FEATURES.FACTOR_NAME
    assert audit["candidate"]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["candidate"]["direction"] == "higher"
    assert audit["candidate"]["selected_bar_count"] == 240
    assert audit["candidate"]["minimum_positive_range_bars"] == 120
    assert audit["candidate"]["entropy_support_bar_count"] == 240
    assert audit["comparison_catalog"]["semantic_terminal_mechanism_count"] == 34
    assert audit["comparison_catalog"]["statistical_comparison_factor_count"] == 33
    assert audit["research_boundary"]["historical_forward_returns_read"] is False
    assert audit["source_schema_boundary"]["forbidden_source_fields"] == [
        "open",
        "close",
        "volume",
        "amount",
    ]


def test_no_return_protocol_is_fingerprint_bound_and_finite() -> None:
    protocol_path = (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_011_no_return_preregistration.json"
    )
    protocol = json.loads(protocol_path.read_text())
    assert FEATURES._sha256(protocol_path) == FEATURES.PROTOCOL_SHA256
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 33
    assert (
        comparisons[-1]["name"]
        == FEATURES.C10_FACTOR_NAMES[0]
    )
    assert (
        protocol["finite_post_admissibility_search"][
            "expected_trial_count_if_admitted"
        ]
        == 1
    )
    assert (
        protocol["research_boundary"]["forward_return_fields_read_before_admissibility"]
        is False
    )
