import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign009_features as FEATURES


REPO_ROOT = Path(__file__).resolve().parents[2]


def _ohlc(
    ratios: np.ndarray,
    *,
    ranges: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    ratios = np.asarray(ratios, dtype=float)
    if ranges is None:
        ranges = np.ones_like(ratios)
    ranges = np.asarray(ranges, dtype=float)
    opens = np.ones_like(ratios)
    lows = np.ones_like(ratios)
    highs = np.exp(ranges)
    closes = np.exp(ratios * ranges)
    return opens, highs, lows, closes


def test_body_range_formula_has_frozen_endpoints_and_midpoint() -> None:
    arrays = [
        _ohlc(np.full(240, ratio))
        for ratio in (1.0, 0.0, 0.5)
    ]
    values, eligible, quality = FEATURES.compute_factor_values(
        opens=np.vstack([item[0] for item in arrays]),
        highs=np.vstack([item[1] for item in arrays]),
        lows=np.vstack([item[2] for item in arrays]),
        closes=np.vstack([item[3] for item in arrays]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True, True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx(
        [1.0, 0.0, 0.5]
    )
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 3


def test_formula_is_ratio_of_sums_not_mean_of_bar_ratios() -> None:
    ranges = np.concatenate([np.ones(120), np.full(120, 3.0)])
    ratios = np.concatenate([np.ones(120), np.zeros(120)])
    opens, highs, lows, closes = _ohlc(ratios, ranges=ranges)
    values, eligible, _ = FEATURES.compute_factor_values(
        opens=opens.reshape(1, -1),
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
        closes=closes.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(0.25)
    assert values[FEATURES.FACTOR_NAME][0] != pytest.approx(0.5)


def test_zero_range_bars_are_valid_but_minimum_is_fail_closed() -> None:
    valid = _ohlc(np.ones(240))
    sparse = [item.copy() for item in valid]
    for array in sparse:
        array[119:] = 1.0
    boundary = [item.copy() for item in valid]
    for array in boundary:
        array[120:] = 1.0
    values, eligible, quality = FEATURES.compute_factor_values(
        opens=np.vstack([boundary[0], sparse[0]]),
        highs=np.vstack([boundary[1], sparse[1]]),
        lows=np.vstack([boundary[2], sparse[2]]),
        closes=np.vstack([boundary[3], sparse[3]]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, False]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(1.0)
    assert np.isnan(values[FEATURES.FACTOR_NAME][1])
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__fewer_than_120_positive_range_rows"
        ]
        == 1
    )


def test_ohlc_ordering_violation_is_not_repaired() -> None:
    opens, highs, lows, closes = _ohlc(np.full(240, 0.5))
    highs[7] = 0.9
    values, eligible, quality = FEATURES.compute_factor_values(
        opens=opens.reshape(1, -1),
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
        closes=closes.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__ohlc_ordering_violation_rows"] == 1
    )


def test_invalid_shapes_and_values_are_rejected_or_ineligible() -> None:
    with pytest.raises(FEATURES.Campaign009FeatureError):
        FEATURES.compute_factor_values(
            opens=np.ones((1, 239)),
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
            closes=np.ones((1, 239)),
        )
    opens, highs, lows, closes = _ohlc(np.full(240, 0.5))
    opens[0] = np.nan
    values, eligible, quality = FEATURES.compute_factor_values(
        opens=opens.reshape(1, -1),
        highs=highs.reshape(1, -1),
        lows=lows.reshape(1, -1),
        closes=closes.reshape(1, -1),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality["invalid_required_ohlc_rows"] == 1


def test_partition_reads_no_activity_and_excludes_0930() -> None:
    opens, highs, lows, closes = _ohlc(np.full(240, 0.5))
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
            "open": np.concatenate([[-1.0], opens]),
            "high": np.concatenate([[-1.0], highs]),
            "low": np.concatenate([[-1.0], lows]),
            "close": np.concatenate([[-1.0], closes]),
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
    assert frame[FEATURES.FACTOR_NAME].iloc[0] == pytest.approx(0.5)
    assert quality["base_rows"] == 1
    assert "volume" not in FEATURES.RAW_COLUMNS
    assert "amount" not in FEATURES.RAW_COLUMNS


def test_empty_joint_base_returns_an_empty_partition() -> None:
    raw = pd.DataFrame(
        {
            "datetime": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
            "provider": pd.Series(dtype="string"),
            "open": pd.Series(dtype="float64"),
            "high": pd.Series(dtype="float64"),
            "low": pd.Series(dtype="float64"),
            "close": pd.Series(dtype="float64"),
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
            / "docs/a_share_three_day_walkforward_campaign_009_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_009_mechanism_overlap_audit.json"
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
    assert audit["comparison_catalog"]["semantic_terminal_mechanism_count"] == 32
    assert audit["comparison_catalog"]["statistical_comparison_factor_count"] == 31
    assert audit["research_boundary"]["historical_forward_returns_read"] is False
    assert audit["source_schema_boundary"]["forbidden_source_fields"] == [
        "volume",
        "amount",
    ]


def test_protocol_is_hash_bound_before_external_values() -> None:
    assert (
        FEATURES.PROTOCOL_SHA256
        == "7080dae932fa3b35869ea39de1b4e3759ff968629ee20f422e368eb2e0799e19"
    )
    spec = FEATURES.load_protocol()
    assert spec["candidates"][0]["name"] == FEATURES.FACTOR_NAME
    assert spec["research_boundary"][
        "minute_open_high_low_fields_read_before_admissibility"
    ]
    assert spec["research_boundary"]["minute_close_field_read_before_admissibility"]
    assert (
        spec["research_boundary"]["minute_volume_field_read_before_admissibility"]
        is False
    )
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_admissibility"]
        is False
    )


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
    with pytest.raises(FEATURES.Campaign009FeatureError):
        FEATURES._validate_snapshot_manifest(
            manifest,
            require_fingerprint_constants=False,
        )
