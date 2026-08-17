import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign010_features as FEATURES


REPO_ROOT = Path(__file__).resolve().parents[2]


def _intervals(
    log_lows: np.ndarray,
    log_highs: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    return np.exp(np.asarray(log_highs, dtype=float)), np.exp(
        np.asarray(log_lows, dtype=float)
    )


def test_overlap_formula_has_frozen_endpoints() -> None:
    full = _intervals(np.zeros(240), np.ones(240))
    alternating_lows = np.tile([0.0, 2.0], 120)
    alternating_highs = alternating_lows + 1.0
    disjoint = _intervals(alternating_lows, alternating_highs)
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=np.vstack([full[0], disjoint[0]]),
        lows=np.vstack([full[1], disjoint[1]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0, 0.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 2


def test_formula_is_ratio_of_sums_not_mean_of_pair_ratios() -> None:
    morning_lows = np.zeros(120)
    morning_highs = np.ones(120)
    afternoon_lows = np.tile([0.0, 2.0], 60)
    afternoon_highs = np.tile([3.0, 3.0], 60)
    highs, lows = _intervals(
        np.concatenate([morning_lows, afternoon_lows]),
        np.concatenate([morning_highs, afternoon_highs]),
    )
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(0.5)
    assert values[FEATURES.FACTOR_NAME][0] != pytest.approx(2.0 / 3.0)


def test_zero_union_pairs_are_inactive_and_minimum_is_fail_closed() -> None:
    boundary_points = np.ones(240)
    boundary_points[:120] = np.arange(1.0, 121.0)
    boundary_points[120] = 1.0
    boundary_points[121:] = 2.0
    sparse_points = boundary_points.copy()
    sparse_points[120:] = 2.0
    boundary = _intervals(np.log(boundary_points), np.log(boundary_points))
    sparse = _intervals(np.log(sparse_points), np.log(sparse_points))
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=np.vstack([boundary[0], sparse[0]]),
        lows=np.vstack([boundary[1], sparse[1]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, False]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(0.0)
    assert np.isnan(values[FEATURES.FACTOR_NAME][1])
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__fewer_than_120_positive_union_pair_rows"
        ]
        == 1
    )


def test_lunch_transition_is_not_an_adjacent_pair() -> None:
    point_logs = np.concatenate([np.zeros(120), np.ones(120)])
    highs, lows = _intervals(point_logs, point_logs)
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__fewer_than_120_positive_union_pair_rows"
        ]
        == 1
    )


def test_low_high_ordering_violation_is_not_repaired() -> None:
    highs, lows = _intervals(np.zeros(240), np.ones(240))
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
    with pytest.raises(FEATURES.Campaign010FeatureError):
        FEATURES.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
        )
    highs, lows = _intervals(np.zeros(240), np.ones(240))
    highs[0] = np.nan
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality["invalid_required_high_low_rows"] == 1


def test_partition_reads_only_high_low_and_excludes_0930() -> None:
    highs, lows = _intervals(np.zeros(240), np.ones(240))
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
            "low": np.concatenate([[-1.0], lows]),
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
            / "docs/a_share_three_day_walkforward_campaign_010_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_010_mechanism_overlap_audit.json"
        ).read_text()
    )
    assert concept["selected_concept"]["formula"] is None
    assert concept["selected_concept"]["direction"] is None
    assert concept["research_boundary"]["candidate_values_computed_or_read"] is False
    assert audit["candidate"]["name"] == FEATURES.FACTOR_NAME
    assert audit["candidate"]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["candidate"]["direction"] == "higher"
    assert audit["candidate"]["selected_bar_count"] == 240
    assert audit["candidate"]["maximum_within_half_adjacent_pairs"] == 238
    assert audit["candidate"]["minimum_positive_union_pairs"] == 120
    assert audit["comparison_catalog"]["semantic_terminal_mechanism_count"] == 33
    assert audit["comparison_catalog"]["statistical_comparison_factor_count"] == 32
    assert audit["research_boundary"]["historical_forward_returns_read"] is False
    assert audit["source_schema_boundary"]["forbidden_source_fields"] == [
        "open",
        "close",
        "volume",
        "amount",
    ]


def test_protocol_is_hash_bound_before_external_values() -> None:
    assert (
        FEATURES.PROTOCOL_SHA256
        == "0981e5915f0ba5eff8f779b7ad594324bccfd75b0fb76f22916ed734d6443a53"
    )
    spec = FEATURES.load_protocol()
    assert spec["candidates"][0]["name"] == FEATURES.FACTOR_NAME
    assert spec["research_boundary"][
        "minute_open_high_low_fields_read_before_admissibility"
    ]
    assert spec["research_boundary"]["minute_close_field_read_before_admissibility"] is False
    assert (
        spec["research_boundary"]["minute_volume_field_read_before_admissibility"]
        is False
    )
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_admissibility"]
        is False
    )
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 32
    assert comparisons[-1]["name"] == FEATURES.C9_FACTOR_NAMES[0]


def test_prepublication_manifest_accepts_only_inherited_phase_flags() -> None:
    ns = FEATURES.engine_namespace
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign006_feature_snapshot",
        "status": "feature_library_complete_pending_ordered_no_return_gates",
        "protocol_sha256": FEATURES.PROTOCOL_SHA256,
        "mechanism_overlap_audit_sha256": FEATURES.MECHANISM_AUDIT_SHA256,
        "raw_manifest_sha256": ns["market"].RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": ns["market"].JOINT_MANIFEST_SHA256,
        "output_run_id": ns["OUTPUT_RUN_ID"],
        "factor_names": list(ns["FACTOR_NAMES"]),
        "factor_directions": ns["FACTOR_DIRECTIONS"],
        "factor_formulas": ns["FACTOR_FORMULAS"],
        "partitions": ns["EXPECTED_PARTITIONS"],
        "rows": ns["EXPECTED_ROWS"],
        "files": [None] * ns["EXPECTED_PARTITIONS"],
        "factor_eligible_rows": {FEATURES.FACTOR_NAME: 1},
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
    manifest["source_open_high_low_read"] = True
    manifest["source_volume_read"] = False
    with pytest.raises(FEATURES.Campaign010FeatureError):
        FEATURES._validate_snapshot_manifest(
            manifest,
            require_fingerprint_constants=False,
        )


def test_published_snapshot_requires_campaign010_field_flags() -> None:
    manifest_path = (
        Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
        / "derived/a_share/rich/tushare/minute_walkforward_campaign010_feature_library"
        / "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign010_feature_library_v1"
        / "snapshot_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())
    FEATURES._validate_snapshot_manifest(
        manifest,
        require_fingerprint_constants=True,
    )
    changed = dict(manifest)
    changed["source_close_read"] = True
    with pytest.raises(FEATURES.Campaign010FeatureError):
        FEATURES._validate_snapshot_manifest(
            changed,
            require_fingerprint_constants=True,
        )
