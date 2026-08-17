import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign013_features as FEATURES


REPO_ROOT = Path(__file__).resolve().parents[2]


def _arrays(
    *,
    high: float = 12.0,
    low: float = 10.0,
    vwap: float = 10.5,
    volume: float = 100.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    highs = np.full(240, high, dtype=float)
    lows = np.full(240, low, dtype=float)
    volumes = np.full(240, volume, dtype=float)
    amounts = volumes * vwap
    return highs, lows, volumes, amounts


def _compute(
    arrays: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    return FEATURES.compute_factor_values(
        highs=arrays[0].reshape(1, -1),
        lows=arrays[1].reshape(1, -1),
        volumes=arrays[2].reshape(1, -1),
        amounts=arrays[3].reshape(1, -1),
    )


def _manual(high: float, low: float, vwap: float) -> float:
    upside = np.log(high / vwap)
    downside = np.log(vwap / low)
    return float((upside - downside) / (upside + downside))


def test_upside_dominant_envelope_is_positive() -> None:
    values, eligible, quality = _compute(_arrays(vwap=10.5))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx(
        [_manual(12.0, 10.0, 10.5)]
    )
    assert values[FEATURES.FACTOR_NAME][0] > 0.0
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 1


def test_geometric_midpoint_is_exactly_symmetric() -> None:
    midpoint = float(np.sqrt(120.0))
    values, eligible, _ = _compute(_arrays(vwap=midpoint))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([0.0], abs=1e-14)


def test_downside_dominant_envelope_is_negative() -> None:
    values, eligible, _ = _compute(_arrays(vwap=11.5))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx(
        [_manual(12.0, 10.0, 11.5)]
    )
    assert values[FEATURES.FACTOR_NAME][0] < 0.0


def test_common_price_and_activity_scales_do_not_change_value() -> None:
    first = _arrays(vwap=10.5, volume=100.0)
    second = tuple(
        value * scale
        for value, scale in zip(first, (7.0, 7.0, 13.0, 91.0), strict=True)
    )
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=np.vstack([first[0], second[0]]),
        lows=np.vstack([first[1], second[1]]),
        volumes=np.vstack([first[2], second[2]]),
        amounts=np.vstack([first[3], second[3]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(
        values[FEATURES.FACTOR_NAME][1]
    )


def test_joint_zero_bars_are_inactive_but_support_gate_remains_fixed() -> None:
    admitted = list(_arrays())
    rejected = [array.copy() for array in admitted]
    admitted[2][120:] = 0.0
    admitted[3][120:] = 0.0
    rejected[2][119:] = 0.0
    rejected[3][119:] = 0.0
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=np.vstack([admitted[0], rejected[0]]),
        lows=np.vstack([admitted[1], rejected[1]]),
        volumes=np.vstack([admitted[2], rejected[2]]),
        amounts=np.vstack([admitted[3], rejected[3]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][1])
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__fewer_than_120_informative_active_bar_rows"
        ]
        == 1
    )


def test_one_sided_zero_activity_is_missing_not_repaired() -> None:
    arrays = list(_arrays())
    arrays[2][7] = 0.0
    values, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality[f"{FEATURES.FACTOR_NAME}__one_sided_zero_activity_rows"] == 1


def test_active_vwap_outside_high_low_is_missing_not_clamped() -> None:
    arrays = list(_arrays())
    arrays[3][9] = arrays[2][9] * 12.01
    values, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__active_vwap_outside_high_low_rows"]
        == 1
    )


def test_zero_range_bars_do_not_count_as_informative() -> None:
    arrays = list(_arrays())
    arrays[0][119:] = 10.0
    arrays[1][119:] = 10.0
    arrays[3][119:] = arrays[2][119:] * 10.0
    values, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__fewer_than_120_informative_active_bar_rows"
        ]
        == 1
    )


def test_invalid_shapes_ordering_and_nonfinite_values_fail_closed() -> None:
    with pytest.raises(FEATURES.Campaign013FeatureError):
        FEATURES.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
            volumes=np.ones((1, 239)),
            amounts=np.ones((1, 239)),
        )
    arrays = list(_arrays())
    arrays[1][3] = arrays[0][3] + 1.0
    values, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__low_high_ordering_violation_rows"]
        == 1
    )
    arrays = list(_arrays())
    arrays[0][0] = np.nan
    _, eligible, quality = _compute(tuple(arrays))
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert quality["invalid_required_high_low_rows"] == 1


def test_partition_uses_only_frozen_fields_and_excludes_0930() -> None:
    arrays = _arrays()
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
            "volume": np.concatenate([[-3.0], arrays[2]]),
            "amount": np.concatenate([[-4.0], arrays[3]]),
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
    assert frame[FEATURES.FACTOR_NAME].iloc[0] == pytest.approx(
        _manual(12.0, 10.0, 10.5)
    )
    assert quality["base_rows"] == 1
    assert "open" not in FEATURES.RAW_COLUMNS
    assert "close" not in FEATURES.RAW_COLUMNS
    assert {"high", "low", "volume", "amount"}.issubset(FEATURES.RAW_COLUMNS)


def test_concept_audit_and_parent_are_fingerprint_bound() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_013_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_013_mechanism_overlap_audit.json"
        ).read_text()
    )
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN012_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN012_FEATURE_RUNNER_SHA256
    )
    assert concept["selected_concept"]["formula"] is None
    assert concept["selected_concept"]["direction"] is None
    assert concept["research_boundary"]["candidate_values_computed_or_read"] is False
    assert audit["candidate"]["name"] == FEATURES.FACTOR_NAME
    assert audit["candidate"]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["candidate"]["direction"] == "higher"
    assert audit["candidate"]["selected_bar_count"] == 240
    assert audit["candidate"]["minimum_informative_active_bars"] == 120
    assert audit["comparison_catalog"]["semantic_registered_mechanism_count"] == 36
    assert audit["comparison_catalog"]["statistical_comparison_factor_count"] == 35
    assert audit["research_boundary"]["historical_forward_returns_read"] is False
    assert audit["source_schema_boundary"]["forbidden_source_fields"] == [
        "open",
        "close",
    ]


def test_prepublication_manifest_accepts_inherited_missing_amount_flag() -> None:
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


def test_terminal_record_and_additive_state_preserve_no_return_boundary() -> None:
    record_path = (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_013_research_record.json"
    )
    state_path = (
        REPO_ROOT
        / "docs/a_share_three_day_iteration_status_20260729_campaign013.json"
    )
    record = json.loads(record_path.read_text())
    state = json.loads(state_path.read_text())
    assert (
        record["status"]
        == "completed_zero_no_return_admissible_factors_stop_before_historical_returns"
    )
    assert record["no_return_admission"]["audit"]["admissible_factor_count"] == 0
    assert (
        record["no_return_admission"]["audit"][
            "comparison_values_loaded_after_coverage_pass"
        ]
        is False
    )
    assert record["trial_accounting"]["development_trial_count"] == 0
    assert record["trial_accounting"]["stress_2024_2025_opened"] is False
    assert (
        record["candidate49_state_after_campaign"]["signal_ledger"]["entry_count"]
        == 0
    )
    assert (
        state["previous_authoritative_state"]["sha256"]
        == "e883ebde9d9b2c50368181d4a8aec15dde1c10625460abda060c1f601c284ffd"
    )
    assert (
        state["latest_campaign_research_record"]["sha256"]
        == FEATURES._sha256(record_path)
    )
    assert (
        state["research_counts"]["recorded_historical_development_trial_count"]
        == 236
    )
    assert state["campaign013_result_summary"]["statistical_comparison_values_read"] is False
    assert state["decision"]["campaign014_concept_scouting_and_separate_no_return_research_allowed"]
    assert state["decision"]["current_scoring_allowed"] is False
