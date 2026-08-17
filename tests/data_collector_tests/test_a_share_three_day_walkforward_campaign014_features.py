import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign014_features as FEATURES


REPO_ROOT = Path(__file__).resolve().parents[2]


def _constant_intervals(
    *,
    high: float = 12.0,
    low: float = 10.0,
) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.full(240, high, dtype=float),
        np.full(240, low, dtype=float),
    )


def _compute(
    arrays: tuple[np.ndarray, np.ndarray],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    return FEATURES.compute_factor_values(
        highs=arrays[0].reshape(1, -1),
        lows=arrays[1].reshape(1, -1),
    )


def test_identical_intervals_have_exact_revisit_ratio() -> None:
    values, eligible, quality = _compute(_constant_intervals())
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([239.0 / 240.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 1


def test_disjoint_intervals_have_zero_revisit() -> None:
    log_lows = np.arange(240, dtype=float) * 0.02
    lows = np.exp(log_lows)
    highs = np.exp(log_lows + 0.01)
    values, eligible, quality = _compute((highs, lows))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([0.0], abs=1e-12)
    assert quality[f"{FEATURES.FACTOR_NAME}__range_or_nonfinite_rows"] == 0


def test_two_revisited_disjoint_clusters_use_exact_union_not_convex_hull() -> None:
    highs = np.concatenate(
        [np.full(120, 11.0), np.full(120, 22.0)]
    )
    lows = np.concatenate(
        [np.full(120, 10.0), np.full(120, 20.0)]
    )
    values, eligible, _ = _compute((highs, lows))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([119.0 / 120.0])


def test_bar_order_is_irrelevant_to_spatial_union() -> None:
    log_lows = np.arange(240, dtype=float) * 0.005
    lows = np.exp(log_lows)
    highs = np.exp(log_lows + 0.02)
    permutation = np.random.default_rng(20260729).permutation(240)
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=np.vstack([highs, highs[permutation]]),
        lows=np.vstack([lows, lows[permutation]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(
        values[FEATURES.FACTOR_NAME][1]
    )


def test_same_range_magnitudes_can_have_different_spatial_revisit() -> None:
    identical = _constant_intervals(high=np.e, low=1.0)
    disjoint_lows = np.exp(np.arange(240, dtype=float) * 1.1)
    disjoint_highs = disjoint_lows * np.e
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=np.vstack([identical[0], disjoint_highs]),
        lows=np.vstack([identical[1], disjoint_lows]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME][0] > 0.99
    assert values[FEATURES.FACTOR_NAME][1] == pytest.approx(0.0, abs=1e-12)


def test_positive_range_support_gate_is_exactly_120() -> None:
    admitted = list(_constant_intervals())
    rejected = [array.copy() for array in admitted]
    admitted[0][120:] = 10.0
    admitted[1][120:] = 10.0
    rejected[0][119:] = 10.0
    rejected[1][119:] = 10.0
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=np.vstack([admitted[0], rejected[0]]),
        lows=np.vstack([admitted[1], rejected[1]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][1])
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__fewer_than_120_positive_range_bar_rows"]
        == 1
    )


def test_invalid_shapes_ordering_and_nonfinite_values_fail_closed() -> None:
    with pytest.raises(FEATURES.Campaign014FeatureError):
        FEATURES.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
        )
    arrays = list(_constant_intervals())
    arrays[1][3] = arrays[0][3] + 1.0
    values, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__low_high_ordering_violation_rows"]
        == 1
    )
    arrays = list(_constant_intervals())
    arrays[0][0] = np.nan
    _, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert quality["invalid_required_high_low_rows"] == 1


def test_partition_uses_only_high_low_and_excludes_0930() -> None:
    arrays = _constant_intervals()
    codes = [570] + list(FEATURES.market.CONTINUOUS_MINUTE_CODES)
    timestamps = [
        pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code))
        for code in codes
    ]
    raw = pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "high": np.concatenate([[-1.0], arrays[0]]),
            "low": np.concatenate([[-2.0], arrays[1]]),
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
    assert frame[FEATURES.FACTOR_NAME].iloc[0] == pytest.approx(239.0 / 240.0)
    assert quality["base_rows"] == 1
    assert FEATURES.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "high",
        "low",
    )


def test_concept_audit_and_parent_are_fingerprint_bound() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_014_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_014_mechanism_overlap_audit.json"
        ).read_text()
    )
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN013_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN013_FEATURE_RUNNER_SHA256
    )
    assert concept["selected_concept"]["formula"] is None
    assert concept["selected_concept"]["direction"] is None
    assert concept["research_boundary"]["candidate_values_computed_or_read"] is False
    assert audit["candidate"]["name"] == FEATURES.FACTOR_NAME
    assert audit["candidate"]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["candidate"]["direction"] == "higher"
    assert audit["candidate"]["selected_bar_count"] == 240
    assert audit["candidate"]["minimum_positive_range_bars"] == 120
    assert audit["comparison_catalog"]["semantic_registered_mechanism_count"] == 37
    assert audit["comparison_catalog"]["statistical_comparison_factor_count"] == 35
    assert audit["research_boundary"]["historical_forward_returns_read"] is False
    assert audit["source_schema_boundary"]["forbidden_source_fields"] == [
        "open",
        "close",
        "volume",
        "amount",
    ]


def test_no_return_protocol_is_hash_bound_and_finite() -> None:
    protocol = FEATURES.load_protocol()
    assert len(protocol["candidates"]) == 1
    assert protocol["candidates"][0]["name"] == FEATURES.FACTOR_NAME
    assert (
        len(
            protocol["ordered_no_return_gates"][
                "uniqueness_after_coverage_only"
            ]["comparison_factors"]
        )
        == 35
    )
    search = protocol["finite_post_admissibility_search"]
    assert search["expected_trial_count_if_admitted"] == 1
    assert search["pair_or_higher_order_combinations"] is False
    assert protocol["research_boundary"]["forward_return_fields_read_before_admissibility"] is False


def test_prepublication_manifest_preserves_high_low_only_boundary() -> None:
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign006_feature_snapshot",
        "status": "feature_library_complete_pending_ordered_no_return_gates",
        "protocol_sha256": FEATURES.PROTOCOL_SHA256,
        "mechanism_overlap_audit_sha256": FEATURES.MECHANISM_AUDIT_SHA256,
        "raw_manifest_sha256": FEATURES.market.RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": FEATURES.market.JOINT_MANIFEST_SHA256,
        "output_run_id": FEATURES.engine_namespace["OUTPUT_RUN_ID"],
        "factor_names": list(FEATURES.FACTOR_NAMES),
        "factor_directions": FEATURES.FACTOR_DIRECTIONS,
        "factor_formulas": FEATURES.FACTOR_FORMULAS,
        "factor_eligible_rows": {FEATURES.FACTOR_NAME: 1},
        "partitions": FEATURES.engine_namespace["EXPECTED_PARTITIONS"],
        "rows": FEATURES.engine_namespace["EXPECTED_ROWS"],
        "files": [None] * FEATURES.engine_namespace["EXPECTED_PARTITIONS"],
        "source_fields_read": list(FEATURES.RAW_COLUMNS),
        "source_open_high_low_read": False,
        "source_volume_read": True,
        "daily_price_fields_read": [],
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    FEATURES._validate_snapshot_manifest(
        manifest,
        require_fingerprint_constants=False,
    )


def test_terminal_record_and_additive_state_preserve_closed_stress() -> None:
    record = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_014_research_record.json"
        ).read_text()
    )
    state = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_iteration_status_20260729_campaign014.json"
        ).read_text()
    )
    survivors = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_014"
            / "walkforward/development_survivors.json"
        ).read_text()
    )
    stress = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_014"
            / "walkforward/exposed_stress_consumption_record.json"
        ).read_text()
    )
    assert record["status"] == "completed_zero_development_survivors_stress_interval_not_opened"
    assert record["development_result"]["frozen_trial_count"] == 1
    assert record["development_result"]["trial"]["development_survivor_gate_passed"] is False
    assert survivors["selected_survivor_count"] == 0
    assert survivors["stress_return_fields_read"] is False
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert state["research_counts"]["recorded_historical_development_trial_count"] == 237
    assert state["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert state["active_prospective_candidate"]["execution_ledger"]["entry_count"] == 0
    assert state["decision"]["campaign015_concept_scouting_and_separate_no_return_research_allowed"] is True
