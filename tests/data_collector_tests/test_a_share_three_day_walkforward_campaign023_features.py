import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign023_features as FEATURES
import scripts.a_share_three_day_walkforward_campaign023 as WALKFORWARD


REPO_ROOT = Path(__file__).resolve().parents[2]


def _prices_from_logs(log_high: np.ndarray, log_low: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.exp(log_high)[None, :], np.exp(log_low)[None, :]


def test_parallel_and_opposite_boundary_translation_hit_exact_endpoints() -> None:
    phase = np.linspace(0.0, 4.0 * np.pi, FEATURES.SELECTED_BAR_COUNT)
    log_low_parallel = 1.0 + 0.1 * np.sin(phase)
    log_high_parallel = log_low_parallel + 0.5
    high_parallel, low_parallel = _prices_from_logs(
        log_high_parallel, log_low_parallel
    )

    log_low_opposite = 1.0 + 0.1 * np.sin(phase)
    log_high_opposite = 2.0 - 0.1 * np.sin(phase)
    high_opposite, low_opposite = _prices_from_logs(
        log_high_opposite, log_low_opposite
    )
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=np.vstack((high_parallel, high_opposite)),
        lows=np.vstack((low_parallel, low_opposite)),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0, -1.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 2


def test_lunch_jump_is_excluded_but_within_half_changes_are_retained() -> None:
    half_phase = np.linspace(0.0, 4.0 * np.pi, 120)
    morning = 1.0 + 0.1 * np.sin(half_phase)
    afternoon = 3.0 + 0.1 * np.sin(half_phase)
    log_low = np.concatenate((morning, afternoon))
    log_high = log_low + 0.4
    highs, lows = _prices_from_logs(log_high, log_low)
    values, eligible, _ = FEATURES.compute_factor_values(
        highs=highs,
        lows=lows,
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0])


def test_zero_changes_remain_and_degenerate_vectors_are_missing() -> None:
    log_low = np.ones(FEATURES.SELECTED_BAR_COUNT)
    log_high = np.full(FEATURES.SELECTED_BAR_COUNT, 1.5)
    log_low[10:20] = np.linspace(1.0, 1.1, 10)
    log_high[10:20] = log_low[10:20] + 0.5
    active_high, active_low = _prices_from_logs(log_high, log_low)
    flat_high = np.exp(np.full((1, FEATURES.SELECTED_BAR_COUNT), 1.5))
    flat_low = np.exp(np.ones((1, FEATURES.SELECTED_BAR_COUNT)))
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=np.vstack((active_high, flat_high)),
        lows=np.vstack((active_low, flat_low)),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, False]
    assert values[FEATURES.FACTOR_NAME][0] == pytest.approx(1.0)
    assert np.isnan(values[FEATURES.FACTOR_NAME][1])
    assert quality[
        f"{FEATURES.FACTOR_NAME}__nonpositive_high_change_variance_rows"
    ] == 1
    assert quality[
        f"{FEATURES.FACTOR_NAME}__nonpositive_low_change_variance_rows"
    ] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__zero_high_change_observations"] > 0
    assert quality[f"{FEATURES.FACTOR_NAME}__zero_low_change_observations"] > 0


def test_invalid_shape_nonfinite_nonpositive_and_misordered_fail_closed() -> None:
    with pytest.raises(FEATURES.Campaign023FeatureError):
        FEATURES.compute_factor_values(
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
        )

    highs = np.full((3, FEATURES.SELECTED_BAR_COUNT), 2.0)
    lows = np.ones_like(highs)
    highs[0, 3] = np.nan
    lows[1, 4] = 0.0
    lows[2, 5] = 3.0
    values, eligible, quality = FEATURES.compute_factor_values(
        highs=highs,
        lows=lows,
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False, False, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME]).all()
    assert quality["invalid_required_high_low_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__nonpositive_high_low_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__misordered_high_low_rows"] == 1


def test_partition_reads_only_high_low_and_excludes_0930() -> None:
    codes = [570] + list(FEATURES.market.CONTINUOUS_MINUTE_CODES)
    timestamps = [
        pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code))
        for code in codes
    ]
    phase = np.linspace(0.0, 4.0 * np.pi, FEATURES.SELECTED_BAR_COUNT)
    lows = np.exp(1.0 + 0.1 * np.sin(phase))
    highs = np.exp(1.5 + 0.1 * np.sin(phase))
    raw = pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "high": [-1.0] + highs.tolist(),
            "low": [-1.0] + lows.tolist(),
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


def test_protocol_and_mechanism_are_fingerprint_bound_before_values() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_023_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_023_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN022_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN022_FEATURE_RUNNER_SHA256
    )
    assert concept["research_boundary"]["candidate_values_read"] is False
    assert audit["selected_mechanism"]["name"] == FEATURES.FACTOR_NAME
    assert audit["selected_mechanism"]["direction"] == "higher"
    assert protocol["candidates"][0]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["decision"]["conceptually_independent"] is True
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 44
    assert comparisons[-1]["name"] == FEATURES.C22_FACTOR_NAMES[0]
    assert protocol["finite_post_admissibility_search"][
        "development_trial_count"
    ] == 1


def test_generated_source_records_high_low_without_close_or_benchmark() -> None:
    source = FEATURES._source
    assert '"minute_open_high_low_read_by_status": True' in source
    assert '"minute_open_read_by_status": False' in source
    assert '"minute_close_read_by_status": False' in source
    assert 'value["source_open_high_low_read"] = True' in source
    assert 'value["source_close_read"] = False' in source
    assert 'value["source_volume_read"] = False' in source
    assert "market_benchmark_fields_read" not in source


def test_walkforward_catalog_is_the_single_frozen_trial() -> None:
    campaign, campaign_sha256 = WALKFORWARD.load_campaign(
        WALKFORWARD.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert campaign_sha256 == (
        "0f78cea5e2e0814bf0e3214dbcb85078e149f2a30177bcb2e824e268635d0c6d"
    )
    assert WALKFORWARD.build_trial_catalog(campaign) == [
        {
            "trial_id": (
                "wf023_single__intraday_range_boundary_translation_coherence_238p"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [FEATURES.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_terminal_record_and_state_preserve_closed_stress() -> None:
    record = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_023_research_record.json"
        ).read_text()
    )
    state = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_iteration_status_20260729_campaign023.json"
        ).read_text()
    )
    no_return_path = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_023"
        / "no_return/20260729T084202Z_campaign023_no_return_audit.json"
    )
    no_return = json.loads(no_return_path.read_text())
    ledger = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_023"
            / "walkforward/trial_ledger.json"
        ).read_text()
    )
    survivors = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_023"
            / "walkforward/development_survivors.json"
        ).read_text()
    )
    stress = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_023"
            / "walkforward/exposed_stress_consumption_record.json"
        ).read_text()
    )
    manifest = json.loads(
        (
            FEATURES.output_root(Path("/Volumes/DIsk/qlib-a-share-tushare-1m"))
            / "snapshot_manifest.json"
        ).read_text()
    )
    assert FEATURES._sha256(no_return_path) == FEATURES.NO_RETURN_AUDIT_SHA256
    assert manifest["source_fields_read"] == list(FEATURES.RAW_COLUMNS)
    assert manifest["source_open_high_low_read"] is True
    assert manifest["source_close_read"] is False
    assert manifest["source_volume_read"] is False
    assert manifest["daily_price_fields_read"] == []
    assert manifest["forward_return_fields_read"] is False
    assert manifest["factor_eligible_rows"][FEATURES.FACTOR_NAME] == 7_692_348
    coverage = no_return["coverage_and_capacity"][FEATURES.FACTOR_NAME]
    uniqueness = no_return["uniqueness"][FEATURES.FACTOR_NAME]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == pytest.approx(0.9982339869790652)
    assert coverage["p05_coverage"] == pytest.approx(0.9927536231884058)
    assert uniqueness["all_required_comparisons_passed"] is True
    assert len(uniqueness["comparisons"]) == 44
    assert uniqueness[
        "maximum_observed_absolute_median_daily_rank_correlation"
    ] == pytest.approx(0.6135693402263568)
    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 0
    assert decision["positive_pilot_return_fold_count"] == 1
    assert survivors["selected_survivor_count"] == 0
    assert survivors["stress_return_fields_read"] is False
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert record["decision"]["factor_terminal"] is True
    assert record["development_result"]["development_survivor_count"] == 0
    assert state["research_counts"][
        "recorded_historical_development_trial_count"
    ] == 245
    assert state["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert state["active_prospective_candidate"]["execution_ledger"]["entry_count"] == 0
    assert state["decision"][
        "campaign024_concept_scouting_and_separate_no_return_research_allowed"
    ] is True
