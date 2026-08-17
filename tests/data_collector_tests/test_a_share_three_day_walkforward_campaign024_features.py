import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign024_features as FEATURES
import scripts.a_share_three_day_walkforward_campaign024 as WALKFORWARD
import scripts.a_share_three_day_preregistration_binding_validator as BINDINGS


REPO_ROOT = Path(__file__).resolve().parents[2]


def _ohlc_for_response(
    relation: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    bodies = np.zeros(FEATURES.SELECTED_BAR_COUNT, dtype=float)
    ranges = np.full(FEATURES.SELECTED_BAR_COUNT, 0.02, dtype=float)
    phase = np.linspace(-1.0, 1.0, FEATURES.WITHIN_HALF_TRANSITION_COUNT)
    current = 0.001 * phase
    response = 0.02 + relation * 4.0 * current
    bodies[:119] = current[:119]
    bodies[120:239] = current[119:]
    ranges[1:120] = response[:119]
    ranges[121:240] = response[119:]
    opens = np.ones(FEATURES.SELECTED_BAR_COUNT, dtype=float)
    closes = np.exp(bodies)
    lows = np.exp(-ranges / 2.0)
    highs = np.exp(ranges / 2.0)
    return (
        opens[None, :],
        highs[None, :],
        lows[None, :],
        closes[None, :],
    )


def test_positive_and_negative_response_hit_exact_endpoints() -> None:
    positive = _ohlc_for_response(1.0)
    negative = _ohlc_for_response(-1.0)
    values, eligible, quality = FEATURES.compute_factor_values(
        opens=np.vstack((positive[0], negative[0])),
        highs=np.vstack((positive[1], negative[1])),
        lows=np.vstack((positive[2], negative[2])),
        closes=np.vstack((positive[3], negative[3])),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([1.0, -1.0])
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 2


def test_lunch_and_half_endpoints_are_excluded() -> None:
    opens, highs, lows, closes = _ohlc_for_response(1.0)
    baseline, eligible, _ = FEATURES.compute_factor_values(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    altered_open = opens.copy()
    altered_high = highs.copy()
    altered_low = lows.copy()
    altered_close = closes.copy()
    for index in (119, 239):
        altered_close[0, index] = np.exp(0.008)
    for index in (0, 120):
        altered_high[0, index] = np.exp(0.2)
        altered_low[0, index] = np.exp(-0.2)
    changed, changed_eligible, _ = FEATURES.compute_factor_values(
        opens=altered_open,
        highs=altered_high,
        lows=altered_low,
        closes=altered_close,
    )
    assert changed_eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert changed[FEATURES.FACTOR_NAME] == pytest.approx(
        baseline[FEATURES.FACTOR_NAME]
    )


def test_zero_values_remain_and_degenerate_vectors_are_missing() -> None:
    opens, highs, lows, closes = _ohlc_for_response(1.0)
    flat_open = np.ones_like(opens)
    flat_close = np.ones_like(opens)
    flat_low = np.ones_like(opens)
    flat_high = np.ones_like(opens)
    values, eligible, quality = FEATURES.compute_factor_values(
        opens=np.vstack((opens, flat_open)),
        highs=np.vstack((highs, flat_high)),
        lows=np.vstack((lows, flat_low)),
        closes=np.vstack((closes, flat_close)),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][1])
    assert quality[f"{FEATURES.FACTOR_NAME}__zero_body_observations"] > 0
    assert quality[
        f"{FEATURES.FACTOR_NAME}__nonpositive_body_variance_rows"
    ] == 1
    assert quality[
        f"{FEATURES.FACTOR_NAME}__nonpositive_following_range_variance_rows"
    ] == 1


def test_invalid_shape_nonfinite_nonpositive_and_misordered_fail_closed() -> None:
    with pytest.raises(FEATURES.Campaign024FeatureError):
        FEATURES.compute_factor_values(
            opens=np.ones((1, 239)),
            highs=np.ones((1, 239)),
            lows=np.ones((1, 239)),
            closes=np.ones((1, 239)),
        )

    opens = np.ones((4, FEATURES.SELECTED_BAR_COUNT))
    highs = np.full_like(opens, 2.0)
    lows = np.full_like(opens, 0.5)
    closes = np.ones_like(opens)
    opens[0, 3] = np.nan
    lows[1, 4] = 0.0
    opens[2, 5] = 3.0
    closes[3, 6] = 0.4
    values, eligible, quality = FEATURES.compute_factor_values(
        opens=opens,
        highs=highs,
        lows=lows,
        closes=closes,
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False] * 4
    assert np.isnan(values[FEATURES.FACTOR_NAME]).all()
    assert quality["invalid_required_ohlc_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__nonpositive_ohlc_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__misordered_ohlc_rows"] == 2


def test_partition_reads_only_ohlc_and_excludes_0930() -> None:
    codes = [570] + list(FEATURES.market.CONTINUOUS_MINUTE_CODES)
    timestamps = [
        pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code))
        for code in codes
    ]
    opens, highs, lows, closes = _ohlc_for_response(1.0)
    raw = pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
            "open": [-1.0] + opens[0].tolist(),
            "high": [-1.0] + highs[0].tolist(),
            "low": [-1.0] + lows[0].tolist(),
            "close": [-1.0] + closes[0].tolist(),
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
        "open",
        "high",
        "low",
        "close",
    )


def test_protocol_and_mechanism_are_fingerprint_bound_before_values() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_024_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_024_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN023_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN023_FEATURE_RUNNER_SHA256
    )
    assert concept["research_boundary"]["candidate_values_read"] is False
    assert audit["selected_mechanism"]["name"] == FEATURES.FACTOR_NAME
    assert audit["selected_mechanism"]["direction"] == "higher"
    assert protocol["candidates"][0]["formula"] == FEATURES.FACTOR_FORMULA
    assert audit["decision"]["conceptually_independent"] is True
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 45
    assert comparisons[-1]["name"] == FEATURES.C23_FACTOR_NAMES[0]
    assert protocol["finite_post_admissibility_search"][
        "development_trial_count"
    ] == 1


def test_generated_source_records_ohlc_without_volume_or_benchmark() -> None:
    source = FEATURES._source
    assert '"minute_open_high_low_read_by_status": True' in source
    assert '"minute_open_read_by_status": True' in source
    assert '"minute_close_read_by_status": True' in source
    assert 'value["source_open_high_low_read"] = True' in source
    assert 'value["source_close_read"] = True' in source
    assert 'value["source_volume_read"] = False' in source
    assert "market_benchmark_fields_read" not in source


def test_walkforward_catalog_is_the_single_frozen_trial() -> None:
    campaign, campaign_sha256 = WALKFORWARD.load_campaign(
        WALKFORWARD.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert campaign_sha256 == (
        "07494e3490166325bd2cf48291eff557a4034c6ba0b32a0d27732d7d3fee13e1"
    )
    assert WALKFORWARD.build_trial_catalog(campaign) == [
        {
            "trial_id": (
                "wf024_single__intraday_directional_range_response_coupling_238p"
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
            / "docs/a_share_three_day_walkforward_campaign_024_research_record.json"
        ).read_text()
    )
    state = json.loads(
        (
            REPO_ROOT
            / (
                "docs/a_share_three_day_iteration_status_20260729_"
                "campaign024_binding_validator_ready.json"
            )
        ).read_text()
    )
    no_return_path = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_024"
        / "no_return/20260729T104150Z_campaign024_no_return_audit.json"
    )
    no_return = json.loads(no_return_path.read_text())
    ledger = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_024"
            / "walkforward/trial_ledger.json"
        ).read_text()
    )
    survivors = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_024"
            / "walkforward/development_survivors.json"
        ).read_text()
    )
    stress = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_024"
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
    assert manifest["source_close_read"] is True
    assert manifest["source_volume_read"] is False
    assert manifest["daily_price_fields_read"] == []
    assert manifest["forward_return_fields_read"] is False
    assert manifest["factor_eligible_rows"][FEATURES.FACTOR_NAME] == 7_695_318
    coverage = no_return["coverage_and_capacity"][FEATURES.FACTOR_NAME]
    uniqueness = no_return["uniqueness"][FEATURES.FACTOR_NAME]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == pytest.approx(0.998342305356559)
    assert coverage["p05_coverage"] == pytest.approx(0.9933243474380903)
    assert uniqueness["all_required_comparisons_passed"] is True
    assert len(uniqueness["comparisons"]) == 45
    assert uniqueness[
        "maximum_observed_absolute_median_daily_rank_correlation"
    ] == pytest.approx(0.4501044801739275)
    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["operationally_admissible"] is True
    assert decision["positive_mean_rank_ic_fold_count"] == 0
    assert decision["positive_normalized_return_fold_count"] == 2
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
    ] == 246
    assert state["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert state["active_prospective_candidate"]["execution_ledger"]["entry_count"] == 0
    assert state["decision"]["campaign025_concept_scouting_allowed_now"] is True
    assert state["decision"][
        "campaign025_candidate_values_allowed_before_binding_validation"
    ] is False


def test_preregistration_binding_discrepancy_is_additive_and_fail_closed() -> None:
    protocol_path = (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_024_no_return_preregistration.json"
    )
    discrepancy_path = (
        REPO_ROOT
        / (
            "docs/a_share_three_day_walkforward_campaign_024_"
            "preregistration_binding_discrepancy_20260729.json"
        )
    )
    state_path = (
        REPO_ROOT
        / (
            "docs/a_share_three_day_iteration_status_20260729_"
            "campaign024_binding_discrepancy.json"
        )
    )
    protocol = json.loads(protocol_path.read_text())
    discrepancy = json.loads(discrepancy_path.read_text())
    state = json.loads(state_path.read_text())
    declared = protocol["source_chain"]["campaign023_statistical_snapshot"]["sha256"]
    actual_path = Path(
        protocol["source_chain"]["campaign023_statistical_snapshot"]["path"]
    )
    observed = FEATURES._sha256(actual_path)
    assert FEATURES._sha256(protocol_path) == (
        "70d8e8f1fc6b0b74f3f19e41bc6a148e999eb57239ed5a156d75a3315edecb02"
    )
    assert declared == discrepancy["discrepancy"]["declared_sha256"]
    assert declared != observed
    assert observed == discrepancy["discrepancy"]["observed_sha256"]
    assert observed == FEATURES.C23_SNAPSHOT_SHA256
    assert discrepancy["frozen_protocol"]["unchanged_after_discovery"] is True
    assert discrepancy["impact_assessment"]["protocol_self_consistency_passed"] is False
    assert discrepancy["impact_assessment"][
        "campaign024_outputs_may_support_strategy_promotion"
    ] is False
    assert discrepancy["decision"]["rerun_campaign024_no_return_or_development"] is False
    assert state["campaign024_binding_discrepancy"][
        "campaign024_evidence_classification"
    ] == "terminal_diagnostic_with_disclosed_preregistration_binding_defect"
    assert state["decision"]["campaign024_strategy_promotion_allowed"] is False
    validation = BINDINGS.validate_record(
        protocol_path,
        data_root=Path("/Volumes/DIsk/qlib-a-share-tushare-1m"),
    )
    assert validation["binding_count"] == 14
    assert validation["passed_binding_count"] == 13
    assert validation["failed_binding_count"] == 1
    assert validation["all_bindings_passed"] is False
    assert validation["failed_bindings"][0]["json_pointer"] == (
        "/source_chain/campaign023_statistical_snapshot"
    )
    development_validation = BINDINGS.validate_record(
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_024_preregistration.json",
        data_root=Path("/Volumes/DIsk/qlib-a-share-tushare-1m"),
    )
    assert development_validation["all_bindings_passed"] is True
    activation = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_preregistration_binding_validator_activation_20260729.json"
        ).read_text()
    )
    assert FEATURES._sha256(REPO_ROOT / activation["implementation"]["path"]) == (
        activation["implementation"]["sha256"]
    )
    assert activation["campaign024_negative_control"]["failed_binding_count"] == 1
    assert activation["campaign024_negative_control"]["exit_code"] == 2
    assert activation["campaign024_positive_control"]["all_bindings_passed"] is True
