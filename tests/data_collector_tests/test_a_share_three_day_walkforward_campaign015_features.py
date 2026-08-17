import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign015_features as FEATURES


REPO_ROOT = Path(__file__).resolve().parents[2]


def _path(
    *,
    morning_step: float,
    afternoon_step: float,
    half_spread: float = 0.005,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    log_close = np.concatenate(
        [
            np.arange(120, dtype=float) * morning_step,
            3.0 + np.arange(120, dtype=float) * afternoon_step,
        ]
    )
    close = np.exp(log_close)
    high = np.exp(log_close + half_spread)
    low = np.exp(log_close - half_spread)
    return high, low, close


def _compute(
    arrays: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    return FEATURES.compute_factor_values(
        highs=arrays[0].reshape(1, -1),
        lows=arrays[1].reshape(1, -1),
        closes=arrays[2].reshape(1, -1),
    )


def test_all_upward_and_all_downward_breakouts_hit_closed_endpoints() -> None:
    up = _path(morning_step=0.02, afternoon_step=0.02)
    down = _path(morning_step=-0.02, afternoon_step=-0.02)
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=np.vstack([up[0], down[0]]),
        lows=np.vstack([up[1], down[1]]),
        closes=np.vstack([up[2], down[2]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0, -1.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 2


def test_equal_upward_and_downward_excess_cancel() -> None:
    arrays = _path(morning_step=0.02, afternoon_step=-0.02)
    values, eligible, _ = _compute(arrays)
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([0.0], abs=1e-12)


def test_boundary_equality_is_inside_and_zero_denominator_is_missing() -> None:
    close = np.ones(240, dtype=float)
    high = np.ones(240, dtype=float)
    low = np.full(240, 0.9, dtype=float)
    values, eligible, quality = _compute((high, low, close))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality[f"{FEATURES.FACTOR_NAME}__zero_breakout_denominator_rows"] == 1


def test_lunch_gap_is_not_a_pair() -> None:
    close = np.concatenate([np.ones(120), np.full(120, 2.0)])
    high = close * 1.01
    low = close * 0.99
    values, eligible, quality = _compute((high, low, close))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality[f"{FEATURES.FACTOR_NAME}__zero_breakout_denominator_rows"] == 1


def test_same_close_path_can_change_when_prior_ranges_change() -> None:
    narrow = _path(morning_step=0.02, afternoon_step=0.02, half_spread=0.005)
    wide = _path(morning_step=0.02, afternoon_step=0.02, half_spread=0.03)
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=np.vstack([narrow[0], wide[0]]),
        lows=np.vstack([narrow[1], wide[1]]),
        closes=np.vstack([narrow[2], wide[2]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, False]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(1.0)
    assert np.isnan(values[FEATURES.FACTOR_NAME][1])


def test_invalid_shapes_ordering_containment_and_nonfinite_fail_closed() -> None:
    with pytest.raises(FEATURES.Campaign015FeatureError):
        FEATURES.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
            closes=np.ones((1, 239)),
        )
    arrays = [array.copy() for array in _path(morning_step=0.02, afternoon_step=0.02)]
    arrays[1][3] = arrays[0][3] + 1.0
    values, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality[f"{FEATURES.FACTOR_NAME}__low_high_ordering_violation_rows"] == 1
    arrays = [array.copy() for array in _path(morning_step=0.02, afternoon_step=0.02)]
    arrays[2][4] = arrays[0][4] + 1.0
    _, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert quality[f"{FEATURES.FACTOR_NAME}__own_bar_close_containment_violation_rows"] == 1
    arrays = [array.copy() for array in _path(morning_step=0.02, afternoon_step=0.02)]
    arrays[0][0] = np.nan
    _, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert quality["invalid_required_high_low_close_rows"] == 1


def test_partition_reads_only_high_low_close_and_excludes_0930() -> None:
    arrays = _path(morning_step=0.02, afternoon_step=0.02)
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
            "close": np.concatenate([[-3.0], arrays[2]]),
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
    assert frame[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])
    assert quality["base_rows"] == 1
    assert FEATURES.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "high",
        "low",
        "close",
    )


def test_concept_audit_parent_and_protocol_are_fingerprint_bound() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_015_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_015_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN014_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN014_FEATURE_RUNNER_SHA256
    )
    assert concept["selected_concept"]["formula"] is None
    assert concept["selected_concept"]["direction"] is None
    assert concept["research_boundary"]["candidate_values_computed_or_read"] is False
    assert audit["candidate"]["name"] == FEATURES.FACTOR_NAME
    assert audit["candidate"]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["candidate"]["direction"] == "higher"
    assert audit["candidate"]["within_half_pair_count"] == 238
    assert audit["comparison_catalog"]["semantic_registered_mechanism_count"] == 38
    assert audit["comparison_catalog"]["statistical_comparison_factor_count"] == 36
    assert audit["research_boundary"]["historical_forward_returns_read"] is False
    assert len(
        protocol["ordered_no_return_gates"][
            "uniqueness_after_coverage_only"
        ]["comparison_factors"]
    ) == 36
    assert (
        protocol["ordered_no_return_gates"][
            "uniqueness_after_coverage_only"
        ]["comparison_factors"][-1]["name"]
        == "intraday_global_price_range_revisit_240m"
    )
    assert protocol["finite_post_admissibility_search"]["expected_trial_count_if_admitted"] == 1


def test_prepublication_manifest_preserves_high_low_close_boundary() -> None:
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
        "source_close_read": True,
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
            / "docs/a_share_three_day_walkforward_campaign_015_research_record.json"
        ).read_text()
    )
    state = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_iteration_status_20260729_campaign015.json"
        ).read_text()
    )
    survivors = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_015"
            / "walkforward/development_survivors.json"
        ).read_text()
    )
    stress = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_015"
            / "walkforward/exposed_stress_consumption_record.json"
        ).read_text()
    )
    assert record["status"] == "completed_zero_development_survivors_stress_interval_not_opened"
    assert record["development_result"]["frozen_trial_count"] == 1
    assert record["development_result"]["trial"]["development_survivor_gate_passed"] is False
    assert record["development_result"]["trial"]["positive_validation_mean_rank_ic_fold_count"] == 0
    assert survivors["selected_survivor_count"] == 0
    assert survivors["stress_return_fields_read"] is False
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert state["research_counts"]["recorded_historical_development_trial_count"] == 238
    assert state["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert state["active_prospective_candidate"]["execution_ledger"]["entry_count"] == 0
    assert state["decision"]["campaign016_concept_scouting_and_separate_no_return_research_allowed"] is True
