import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_preregistration_binding_validator as BINDINGS
import scripts.a_share_three_day_walkforward_campaign025_features as FEATURES
import scripts.a_share_three_day_walkforward_campaign025 as WALKFORWARD


REPO_ROOT = Path(__file__).resolve().parents[2]


def _high_low(
    *,
    low_position: int,
    high_position: int,
) -> tuple[np.ndarray, np.ndarray]:
    lows = np.full((1, FEATURES.SELECTED_BAR_COUNT), 10.0)
    highs = np.full((1, FEATURES.SELECTED_BAR_COUNT), 11.0)
    lows[0, low_position] = 9.0
    highs[0, high_position] = 12.0
    return highs, lows


def test_extreme_order_exact_endpoints_and_zero() -> None:
    positive = _high_low(low_position=0, high_position=239)
    negative = _high_low(low_position=239, high_position=0)
    neutral = _high_low(low_position=80, high_position=80)
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=np.vstack((positive[0], negative[0], neutral[0])),
        lows=np.vstack((positive[1], negative[1], neutral[1])),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True, True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0, -1.0, 0.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__same_extreme_position_rows"] == 1


def test_first_exact_occurrence_is_the_frozen_tie_rule() -> None:
    highs, lows = _high_low(low_position=20, high_position=200)
    highs[0, 30] = 12.0
    lows[0, 10] = 9.0
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs,
        lows=lows,
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([(30 - 10) / 239])
    assert quality[f"{FEATURES.FACTOR_NAME}__multiple_global_high_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__multiple_global_low_rows"] == 1


def test_flat_invalid_nonpositive_and_misordered_rows_fail_closed() -> None:
    highs = np.full((4, FEATURES.SELECTED_BAR_COUNT), 11.0)
    lows = np.full_like(highs, 10.0)
    highs[0] = 10.0
    lows[0] = 10.0
    highs[1, 2] = np.nan
    lows[2, 3] = 0.0
    lows[3, 4] = 12.0
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs,
        lows=lows,
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False] * 4
    assert np.isnan(values[FEATURES.FACTOR_NAME]).all()
    assert quality[f"{FEATURES.FACTOR_NAME}__zero_global_range_rows"] == 1
    assert quality["invalid_required_high_low_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__nonpositive_high_low_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__misordered_high_low_rows"] == 1


def test_invalid_shape_is_rejected() -> None:
    with pytest.raises(FEATURES.Campaign025FeatureError):
        FEATURES.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
        )


def test_partition_reads_only_high_low_and_excludes_0930() -> None:
    codes = [570] + list(FEATURES.market.CONTINUOUS_MINUTE_CODES)
    timestamps = [
        pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code))
        for code in codes
    ]
    highs, lows = _high_low(low_position=0, high_position=239)
    raw = pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "high": [-100.0] + highs[0].tolist(),
            "low": [-100.0] + lows[0].tolist(),
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
    )


def test_all_preregistration_bindings_pass_before_values() -> None:
    records = [
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_025_concept_scouting.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_025_mechanism_overlap_audit.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_025_no_return_preregistration.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_025_preregistration.json",
    ]
    for record in records:
        result = BINDINGS.validate_record(record, data_root=FEATURES.DEFAULT_DATA_ROOT)
        assert result["all_bindings_passed"] is True
    protocol = FEATURES.load_protocol()
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 46
    assert comparisons[-1]["name"] == FEATURES.C24_FACTOR_NAMES[0]


def test_research_boundaries_remain_no_return() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_025_concept_scouting.json"
        ).read_text()
    )
    mechanism = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_025_mechanism_overlap_audit.json"
        ).read_text()
    )
    assert concept["research_boundary"]["candidate_values_read"] is False
    assert mechanism["research_boundary"]["comparison_values_read"] is False
    assert mechanism["decision"]["conceptually_independent"] is True
    assert FEATURES.engine_namespace["FACTOR_NAME"] == FEATURES.FACTOR_NAME


def test_walkforward_catalog_is_the_single_frozen_trial() -> None:
    campaign, campaign_sha256 = WALKFORWARD.load_campaign(
        WALKFORWARD.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert campaign_sha256 == (
        "5920146afef4a726fcd5e843e41e577bbd9cb0533d4386dbe8f0464d15f3b8cb"
    )
    assert WALKFORWARD.build_trial_catalog(campaign) == [
        {
            "trial_id": "wf025_single__intraday_extreme_arrival_order_240m",
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [FEATURES.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_terminal_record_state_and_report_preserve_closed_stress() -> None:
    no_return_path = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_025"
        / "no_return/20260729T122303Z_campaign025_no_return_audit.json"
    )
    no_return = json.loads(no_return_path.read_text())
    ledger = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_025"
            / "walkforward/trial_ledger.json"
        ).read_text()
    )
    survivors = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_025"
            / "walkforward/development_survivors.json"
        ).read_text()
    )
    stress = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_025"
            / "walkforward/exposed_stress_consumption_record.json"
        ).read_text()
    )
    record = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_025_research_record.json"
        ).read_text()
    )
    state_path = (
        REPO_ROOT
        / "docs/a_share_three_day_iteration_status_20260729_campaign025_verified.json"
    )
    state = json.loads(state_path.read_text())
    manifest = json.loads(
        (
            FEATURES.output_root(Path("/Volumes/DIsk/qlib-a-share-tushare-1m"))
            / "snapshot_manifest.json"
        ).read_text()
    )
    assert FEATURES._sha256(no_return_path) == FEATURES.NO_RETURN_AUDIT_SHA256
    assert manifest["source_fields_read"] == list(FEATURES.RAW_COLUMNS)
    assert manifest["daily_price_fields_read"] == []
    assert manifest["forward_return_fields_read"] is False
    assert manifest["factor_eligible_rows"][FEATURES.FACTOR_NAME] == 7_700_153
    coverage = no_return["coverage_and_capacity"][FEATURES.FACTOR_NAME]
    uniqueness = no_return["uniqueness"][FEATURES.FACTOR_NAME]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == pytest.approx(0.9985369414262841)
    assert coverage["p05_coverage"] == pytest.approx(0.9935483870967742)
    assert uniqueness["all_required_comparisons_passed"] is True
    assert len(uniqueness["comparisons"]) == 46
    assert uniqueness[
        "maximum_observed_absolute_median_daily_rank_correlation"
    ] == pytest.approx(0.7602194149269277)
    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["operationally_admissible"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 1
    assert decision["positive_normalized_return_fold_count"] == 0
    assert decision["positive_pilot_return_fold_count"] == 0
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert record["decision"]["factor_terminal"] is True
    assert record["development_result"]["development_survivor_count"] == 0
    assert state["research_counts"]["recorded_historical_development_trial_count"] == 247
    assert state["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert state["active_prospective_candidate"]["execution_ledger"]["entry_count"] == 0
    assert state["decision"]["campaign026_concept_scouting_allowed_now"] is True
    assert BINDINGS.validate_record(
        state_path,
        data_root=FEATURES.DEFAULT_DATA_ROOT,
    )["all_bindings_passed"] is True
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign025 权威追加" in report
    assert "2024–2025 压力区间未打开、未读取" in report
