import json
from pathlib import Path

import numpy as np
import pytest

import scripts.a_share_three_day_preregistration_binding_validator as BINDINGS
import scripts.a_share_three_day_walkforward_campaign030_features as FEATURES
import scripts.a_share_three_day_walkforward_campaign030 as WALKFORWARD


REPO_ROOT = Path(__file__).resolve().parents[2]


def _varying_half() -> np.ndarray:
    return np.linspace(-0.012, 0.013, FEATURES.POSITIONS_PER_HALF)


def test_morning_minus_afternoon_correlation_exact_endpoints() -> None:
    market_half = _varying_half()
    inverse_half = -market_half
    market = np.concatenate((market_half, market_half))
    stocks = np.vstack(
        (
            np.concatenate((market_half, inverse_half)),
            np.concatenate((inverse_half, market_half)),
            np.concatenate((market_half, market_half)),
        )
    )
    markets = np.vstack((market, market, -market))
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


def test_exact_zero_signed_returns_remain_in_support() -> None:
    stock = np.concatenate((_varying_half(), _varying_half()))
    market = stock.copy()
    stock[10:20] = 0.0
    market[140:155] = 0.0
    values, eligible, quality = FEATURES.compute_factor_values(
        within_half_returns=stock[None, :],
        leave_one_out_market_returns=market[None, :],
        sufficient_peers=np.array([True]),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True]
    assert np.isfinite(values[FEATURES.FACTOR_NAME]).all()
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__exact_zero_stock_return_positions"]
        == 10
    )
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__exact_zero_market_return_positions"]
        == 15
    )


def test_peer_half_variance_and_finite_gates_fail_closed() -> None:
    half = _varying_half()
    varying = np.concatenate((half, half))
    invalid = varying.copy()
    invalid[0] = np.nan
    constant_morning = np.concatenate((np.ones(119), half))
    constant_afternoon_market = np.concatenate((half, np.ones(119)))
    stocks = np.vstack((varying, constant_morning, varying, invalid))
    markets = np.vstack((varying, varying, constant_afternoon_market, varying))
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
            f"{FEATURES.FACTOR_NAME}__degenerate_morning_stock_variance_rows"
        ]
        == 1
    )
    assert (
        quality[
            f"{FEATURES.FACTOR_NAME}__degenerate_afternoon_market_variance_rows"
        ]
        == 1
    )
    assert (
        quality[f"{FEATURES.FACTOR_NAME}__invalid_stock_or_market_return_rows"]
        == 1
    )


def test_invalid_array_shape_is_rejected() -> None:
    with pytest.raises(FEATURES.Campaign030FeatureError):
        FEATURES.compute_factor_values(
            within_half_returns=np.ones((1, 237)),
            leave_one_out_market_returns=np.ones((1, 237)),
            sufficient_peers=np.array([True]),
        )


def test_all_campaign030_freeze_bindings_pass_before_values() -> None:
    records = [
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_030_concept_scouting.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_030_mechanism_overlap_audit.json",
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_030_no_return_preregistration.json",
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
    assert len(comparisons) == 51
    assert comparisons[-1]["name"] == FEATURES.C29_FACTOR_NAMES[0]


def test_campaign030_boundaries_remain_no_return() -> None:
    mechanism = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_030_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert mechanism["research_boundary"]["candidate_values_read"] is False
    assert mechanism["research_boundary"]["frozen_market_benchmark_values_read"] is False
    assert mechanism["decision"]["conceptually_independent"] is True
    assert (
        protocol["research_boundary"]["daily_price_fields_read_before_admissibility"]
        is False
    )
    assert (
        protocol["research_boundary"]["forward_return_fields_read_before_admissibility"]
        is False
    )
    assert FEATURES.RAW_COLUMNS == ("datetime", "symbol", "provider", "close")


def test_walkforward_catalog_is_the_single_frozen_trial() -> None:
    campaign, campaign_sha256 = WALKFORWARD.load_campaign(
        WALKFORWARD.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert campaign_sha256 == (
        "b3e73ab138e21bed849479f10babe4de4ab5e3795cb8b2b2a6ee1af7de23bb48"
    )
    assert WALKFORWARD.build_trial_catalog(campaign) == [
        {
            "trial_id": (
                "wf030_single__"
                "intraday_market_correlation_resolution_119p"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [FEATURES.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_terminal_record_preserves_closed_stress_and_candidate49() -> None:
    root = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_030"
        / "walkforward"
    )
    record_path = (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_030_research_record.json"
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/"
            "campaign_030/no_return/20260730T112347Z_campaign030_no_return_audit.json"
        ).read_text()
    )
    ledger = json.loads((root / "trial_ledger.json").read_text())
    survivors = json.loads((root / "development_survivors.json").read_text())
    stress = json.loads(
        (root / "exposed_stress_consumption_record.json").read_text()
    )
    record = json.loads(record_path.read_text())
    coverage = audit["coverage_and_capacity"][FEATURES.FACTOR_NAME]
    uniqueness = audit["uniqueness"][FEATURES.FACTOR_NAME]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == pytest.approx(0.9935888543513072)
    assert uniqueness["all_required_comparisons_passed"] is True
    assert len(uniqueness["comparisons"]) == 51
    assert uniqueness[
        "maximum_observed_absolute_median_daily_rank_correlation"
    ] == pytest.approx(0.3402292857080516)
    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 2
    assert decision["positive_normalized_return_fold_count"] == 0
    assert decision["positive_pilot_return_fold_count"] == 0
    assert decision["validation_quality_rejection_reasons"] == [
        "median_validation_spread",
        "insufficient_positive_normalized_return_folds",
        "insufficient_positive_pilot_return_folds",
        "median_validation_pilot_return",
        "worst_validation_normalized_drawdown",
        "nonpositive_development_aggregate_20bp_return",
    ]
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert record["decision"]["factor_terminal"] is True
    assert record["decision"]["candidate49_remains_only_prospective_candidate"]
    assert BINDINGS.validate_record(
        record_path,
        data_root=FEATURES.DEFAULT_DATA_ROOT,
    )["all_bindings_passed"] is True


def test_unified_report_contains_campaign030_terminal_result() -> None:
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign030 权威追加" in report
    assert "最大绝对中位日秩相关为 0.340229" in report
    assert "20bp 纸面收益为 -8.851180%/-12.617061%/-17.787345%/-24.528441%" in report
