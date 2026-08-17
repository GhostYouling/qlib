import json
from pathlib import Path

import numpy as np
import pytest

import scripts.a_share_three_day_preregistration_binding_validator as BINDINGS
import scripts.a_share_three_day_walkforward_campaign026_features as FEATURES


REPO_ROOT = Path(__file__).resolve().parents[2]


def _market_path() -> np.ndarray:
    up = np.linspace(0.0001, 0.012, 119)
    down = -np.linspace(0.0001, 0.012, 119)
    return np.concatenate([up, down])


def test_up_minus_down_correlation_exact_endpoints_and_zero() -> None:
    market = _market_path()
    stocks = np.vstack(
        [
            np.concatenate([market[:119], -market[119:]]),
            np.concatenate([-market[:119], market[119:]]),
            market,
        ]
    )
    markets = np.tile(market, (3, 1))
    values, eligible, quality = FEATURES.compute_factor_values(
        within_half_returns=stocks,
        leave_one_out_market_returns=markets,
        sufficient_peers=np.ones(3, dtype=bool),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True, True]
    assert values[FEATURES.FACTOR_NAME].tolist() == pytest.approx(
        [2.0, -2.0, 0.0]
    )
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 3


def test_market_zero_positions_are_excluded_but_stock_zeros_are_retained() -> None:
    market = _market_path()
    market[10:20] = 0.0
    stock = market.copy()
    stock[30:40] = 0.0
    values, eligible, quality = FEATURES.compute_factor_values(
        within_half_returns=stock[None, :],
        leave_one_out_market_returns=market[None, :],
        sufficient_peers=np.array([True]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert np.isfinite(values[FEATURES.FACTOR_NAME]).all()
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__exact_zero_market_return_positions"]
        == 10
    )


def test_support_peer_variance_and_finite_gates_fail_closed() -> None:
    market = _market_path()
    insufficient_sign = -np.linspace(0.0001, 0.012, FEATURES.RETURN_POSITIONS)
    insufficient_sign[:29] *= -1.0
    constant_stock = np.concatenate(
        [np.zeros(119), market[119:]],
    )
    invalid_stock = market.copy()
    invalid_stock[0] = np.nan
    stocks = np.vstack([market, market, constant_stock, invalid_stock])
    markets = np.vstack([market, insufficient_sign, market, market])
    values, eligible, quality = FEATURES.compute_factor_values(
        within_half_returns=stocks,
        leave_one_out_market_returns=markets,
        sufficient_peers=np.array([False, True, True, True]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False] * 4
    assert np.isnan(values[FEATURES.FACTOR_NAME]).all()
    assert quality[f"{FEATURES.FACTOR_NAME}__insufficient_peer_rows"] == 1
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__insufficient_market_sign_support_rows"
        ]
        == 1
    )
    assert quality[f"{FEATURES.FACTOR_NAME}__degenerate_correlation_rows"] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__invalid_stock_or_market_return_rows"] == 1


def test_invalid_array_shape_is_rejected() -> None:
    with pytest.raises(FEATURES.Campaign026FeatureError):
        FEATURES.compute_factor_values(
            within_half_returns=np.ones((1, 237)),
            leave_one_out_market_returns=np.ones((1, 237)),
            sufficient_peers=np.array([True]),
        )


def test_all_campaign026_preregistration_bindings_pass_before_values() -> None:
    records = [
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_026_concept_scouting.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_026_mechanism_overlap_audit.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_026_no_return_preregistration.json",
    ]
    for record in records:
        result = BINDINGS.validate_record(
            record,
            data_root=FEATURES.DEFAULT_DATA_ROOT,
        )
        assert result["all_bindings_passed"] is True
    protocol = FEATURES.load_protocol()
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 47
    assert comparisons[-1]["name"] == FEATURES.C25_FACTOR_NAMES[0]


def test_campaign026_research_boundaries_remain_no_return() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_026_concept_scouting.json"
        ).read_text()
    )
    mechanism = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_026_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert concept["research_boundary"]["candidate_values_read"] is False
    assert mechanism["research_boundary"]["frozen_market_benchmark_values_read"] is False
    assert mechanism["decision"]["conceptually_independent"] is True
    assert protocol["research_boundary"]["daily_price_fields_read_before_admissibility"] is False
    assert protocol["research_boundary"]["forward_return_fields_read_before_admissibility"] is False
    assert FEATURES.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "close",
    )


def test_campaign026_terminal_record_preserves_closed_stress() -> None:
    audit_path = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_026"
        / "no_return/20260730T042053Z_campaign026_no_return_audit.json"
    )
    walkforward = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_026"
        / "walkforward"
    )
    audit = json.loads(audit_path.read_text())
    ledger = json.loads((walkforward / "trial_ledger.json").read_text())
    survivors = json.loads(
        (walkforward / "development_survivors.json").read_text()
    )
    stress = json.loads(
        (walkforward / "exposed_stress_consumption_record.json").read_text()
    )
    record_path = (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_026_research_record.json"
    )
    record = json.loads(record_path.read_text())
    coverage = audit["coverage_and_capacity"][FEATURES.FACTOR_NAME]
    uniqueness = audit["uniqueness"][FEATURES.FACTOR_NAME]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == pytest.approx(0.9979487157908911)
    assert uniqueness["all_required_comparisons_passed"] is True
    assert len(uniqueness["comparisons"]) == 47
    assert uniqueness[
        "maximum_observed_absolute_median_daily_rank_correlation"
    ] == pytest.approx(0.27684609118784903)
    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 1
    assert decision["positive_normalized_return_fold_count"] == 2
    assert decision["positive_pilot_return_fold_count"] == 1
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert record["decision"]["factor_terminal"] is True
    assert record["decision"]["candidate49_remains_only_prospective_candidate"] is True
    assert BINDINGS.validate_record(
        record_path,
        data_root=FEATURES.DEFAULT_DATA_ROOT,
    )["all_bindings_passed"] is True
