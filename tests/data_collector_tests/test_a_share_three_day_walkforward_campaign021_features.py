import json
from pathlib import Path

import numpy as np
import pytest

import scripts.a_share_three_day_walkforward_campaign021_features as FEATURES
import scripts.a_share_three_day_walkforward_campaign021 as WALKFORWARD


REPO_ROOT = Path(__file__).resolve().parents[2]


def _pair_vectors(
    stock: np.ndarray,
    market: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    stock_current = np.concatenate([stock[1:119], stock[120:238]])
    stock_previous = np.concatenate([stock[0:118], stock[119:237]])
    market_current = np.concatenate([market[1:119], market[120:238]])
    market_previous = np.concatenate([market[0:118], market[119:237]])
    return stock_current, stock_previous, market_current, market_previous


def test_exact_stock_lag_minus_stock_lead_correlations() -> None:
    rng = np.random.default_rng(20260729)
    market = rng.normal(size=FEATURES.RETURN_POSITIONS)
    stock = np.empty_like(market)
    stock[0] = 0.25
    stock[1:119] = market[:118]
    stock[119] = -0.25
    stock[120:238] = market[119:237]
    values, eligible, quality = FEATURES.compute_factor_values(
        within_half_returns=stock.reshape(1, -1),
        leave_one_out_market_returns=market.reshape(1, -1),
        sufficient_peers=np.array([True]),
    )
    stock_current, stock_previous, market_current, market_previous = (
        _pair_vectors(stock, market)
    )
    expected = np.corrcoef(stock_current, market_previous)[0, 1] - np.corrcoef(
        stock_previous,
        market_current,
    )[0, 1]
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx([expected])
    assert expected > 0.8
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 1


def test_exact_stock_lead_produces_negative_asymmetry() -> None:
    rng = np.random.default_rng(21)
    stock = rng.normal(size=FEATURES.RETURN_POSITIONS)
    market = np.empty_like(stock)
    market[0] = -0.1
    market[1:119] = stock[:118]
    market[119] = 0.1
    market[120:238] = stock[119:237]
    values, eligible, _ = FEATURES.compute_factor_values(
        within_half_returns=stock.reshape(1, -1),
        leave_one_out_market_returns=market.reshape(1, -1),
        sufficient_peers=np.array([True]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert values[FEATURES.FACTOR_NAME][0] < -0.8


def test_lunch_transition_is_excluded_from_both_correlations() -> None:
    rng = np.random.default_rng(236)
    market = rng.normal(size=FEATURES.RETURN_POSITIONS)
    stock_a = rng.normal(size=FEATURES.RETURN_POSITIONS)
    stock_b = stock_a.copy()
    stock_b[119] = stock_a[119] + 1_000_000.0
    market_b = market.copy()
    market_b[119] = market[119] - 1_000_000.0
    # Position 119 is the first afternoon return. It participates only with
    # position 120, never with the last morning return at position 118.
    values_a, eligible_a, _ = FEATURES.compute_factor_values(
        within_half_returns=stock_a.reshape(1, -1),
        leave_one_out_market_returns=market.reshape(1, -1),
        sufficient_peers=np.array([True]),
    )
    values_b, eligible_b, _ = FEATURES.compute_factor_values(
        within_half_returns=stock_b.reshape(1, -1),
        leave_one_out_market_returns=market_b.reshape(1, -1),
        sufficient_peers=np.array([True]),
    )
    assert eligible_a[FEATURES.FACTOR_NAME].tolist() == [True]
    assert eligible_b[FEATURES.FACTOR_NAME].tolist() == [True]
    assert np.isfinite(values_a[FEATURES.FACTOR_NAME][0])
    assert np.isfinite(values_b[FEATURES.FACTOR_NAME][0])


def test_degenerate_or_insufficient_rows_fail_closed() -> None:
    stock = np.ones((2, FEATURES.RETURN_POSITIONS), dtype=float)
    market = np.tile(
        np.arange(FEATURES.RETURN_POSITIONS, dtype=float),
        (2, 1),
    )
    values, eligible, quality = FEATURES.compute_factor_values(
        within_half_returns=stock,
        leave_one_out_market_returns=market,
        sufficient_peers=np.array([True, False]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[FEATURES.FACTOR_NAME]).all()
    assert quality[f"{FEATURES.FACTOR_NAME}__degenerate_correlation_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__insufficient_peer_rows"] == 1


def test_invalid_shapes_fail_closed() -> None:
    with pytest.raises(FEATURES.Campaign021FeatureError):
        FEATURES.compute_factor_values(
            within_half_returns=np.ones((1, 237)),
            leave_one_out_market_returns=np.ones((1, 237)),
            sufficient_peers=np.array([True]),
        )


def test_protocol_and_mechanism_are_fingerprint_bound_before_values() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_021_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_021_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN019_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN019_FEATURE_RUNNER_SHA256
    )
    assert concept["research_boundary"]["candidate_values_read"] is False
    assert audit["selected_mechanism"]["name"] == FEATURES.FACTOR_NAME
    assert audit["selected_mechanism"]["direction"] == "higher"
    assert audit["decision"]["conceptually_independent"] is True
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 42
    assert comparisons[-1]["name"] == "quarterly_announcement_freshness_60s"
    assert protocol["finite_post_admissibility_search"][
        "development_trial_count"
    ] == 1


def test_generated_source_records_close_and_benchmark_only_boundary() -> None:
    source = FEATURES._source
    assert '"minute_open_high_low_read_by_status": False' in source
    assert '"minute_open_read_by_status": False' in source
    assert '"minute_close_read_by_status": True' in source
    assert 'value["source_open_high_low_read"] = False' in source
    assert 'value["source_close_read"] = True' in source
    assert 'value["source_volume_read"] = False' in source
    assert '"market_benchmark_fields_read": list(market.BENCHMARK_COLUMNS)' in source


def test_walkforward_catalog_is_the_single_frozen_trial() -> None:
    campaign, campaign_sha256 = WALKFORWARD.load_campaign(
        WALKFORWARD.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert campaign_sha256 == (
        "150d5d694429b88ebe809872fe6b67793610c10638c326594e053d8561c60cb8"
    )
    assert WALKFORWARD.build_trial_catalog(campaign) == [
        {
            "trial_id": (
                "wf021_single__intraday_market_response_delay_asymmetry_236p"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [FEATURES.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_terminal_record_and_additive_state_preserve_closed_stress() -> None:
    record = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_021_research_record.json"
        ).read_text()
    )
    state = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_iteration_status_20260729_campaign021.json"
        ).read_text()
    )
    no_return = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_021"
            / "no_return/20260729T050900Z_campaign021_no_return_audit.json"
        ).read_text()
    )
    ledger = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_021"
            / "walkforward/trial_ledger.json"
        ).read_text()
    )
    survivors = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_021"
            / "walkforward/development_survivors.json"
        ).read_text()
    )
    stress = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_021"
            / "walkforward/exposed_stress_consumption_record.json"
        ).read_text()
    )
    manifest = json.loads(
        (
            FEATURES.output_root(Path("/Volumes/DIsk/qlib-a-share-tushare-1m"))
            / "snapshot_manifest.json"
        ).read_text()
    )
    assert manifest["source_fields_read"] == list(FEATURES.RAW_COLUMNS)
    assert manifest["source_open_high_low_read"] is False
    assert manifest["source_close_read"] is True
    assert manifest["source_volume_read"] is False
    assert manifest["market_benchmark_frame_sha256"] == (
        FEATURES.MARKET_BENCHMARK_FRAME_SHA256
    )
    assert manifest["daily_price_fields_read"] == []
    assert manifest["forward_return_fields_read"] is False
    assert no_return["admissible_factor_names"] == [FEATURES.FACTOR_NAME]
    uniqueness = no_return["uniqueness"][FEATURES.FACTOR_NAME]
    assert uniqueness["all_required_comparisons_passed"] is True
    assert len(uniqueness["comparisons"]) == 42
    assert uniqueness[
        "maximum_observed_absolute_median_daily_rank_correlation"
    ] == pytest.approx(0.1988150158542294)
    assert len(ledger["entries"]) == 1
    assert record["status"] == (
        "completed_zero_development_survivors_stress_interval_not_opened"
    )
    assert record["development_result"]["trial"][
        "development_survivor_gate_passed"
    ] is False
    assert record["development_result"]["trial"][
        "positive_validation_mean_rank_ic_fold_count"
    ] == 1
    assert record["development_result"]["trial"][
        "positive_validation_pilot_10bp_return_fold_count"
    ] == 0
    assert survivors["selected_survivor_count"] == 0
    assert survivors["stress_return_fields_read"] is False
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert state["research_counts"][
        "recorded_historical_development_trial_count"
    ] == 243
    assert state["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert state["active_prospective_candidate"]["execution_ledger"]["entry_count"] == 0
    assert state["decision"][
        "campaign022_concept_scouting_and_separate_no_return_research_allowed"
    ] is True
