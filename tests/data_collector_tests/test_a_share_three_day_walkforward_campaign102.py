from __future__ import annotations

import json

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign102 as campaign


def test_frozen_trial_catalog_matches_protocol() -> None:
    protocol = json.loads(campaign.DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    observed = [
        {"trial_id": trial_id, "lambda": regularization}
        for trial_id, regularization in campaign.TRIALS
    ]
    assert observed == protocol["finite_development_catalog"]
    assert campaign.LOWER_WEIGHT == 0.25 / 130
    assert campaign.UPPER_WEIGHT == 4.0 / 130


def test_target_percentiles_use_average_ties_and_minimum_session_names() -> None:
    dates = pd.Series(
        [pd.Timestamp("2020-01-02")] * 50 + [pd.Timestamp("2020-01-03")] * 49
    )
    values = pd.Series(list(range(48)) + [48, 48] + list(range(49)), dtype=float)
    ranked = campaign.target_percentiles(dates, values)
    assert np.isfinite(ranked[:50]).all()
    assert np.isnan(ranked[50:]).all()
    assert ranked[48] == ranked[49] == 49.5 / 50.0


def test_session_equal_sufficient_statistics_and_deterministic_bounded_fit() -> None:
    rng = np.random.default_rng(7)
    first = rng.uniform(0.1, 1.0, size=(50, 130))
    second = rng.uniform(0.1, 1.0, size=(100, 130))
    matrix = np.vstack([first, second])
    true_weights = np.full(130, 1.0 / 130)
    target = matrix @ true_weights
    sessions = np.array([1] * 50 + [2] * 100)
    a, b, stats = campaign.sufficient_statistics(matrix, target, sessions)
    assert stats["training_sessions"] == 2
    assert stats["session_equal_row_weight_sum"] == 1.0
    left = campaign.fit_weights(a, b, 0.1)
    right = campaign.fit_weights(a, b, 0.1)
    weights = np.asarray(left["weights"])
    assert left["weights_sha256"] == right["weights_sha256"]
    assert abs(weights.sum() - 1.0) < 1e-8
    assert weights.min() >= campaign.LOWER_WEIGHT - 1e-8
    assert weights.max() <= campaign.UPPER_WEIGHT + 1e-8


def test_model_scores_zero_impute_only_supported_rows() -> None:
    matrix = np.full((2, 130), 0.5)
    matrix[0, 0] = np.nan
    matrix[1, :40] = np.nan
    eligible = np.array([True, False])
    weights = np.full(130, 1.0 / 130)
    scores = campaign.model_scores(matrix, eligible, weights)
    assert np.isclose(scores[0], 129 * 0.5 / 130)
    assert np.isnan(scores[1])


def test_uniqueness_rejects_an_exact_component_synonym() -> None:
    rng = np.random.default_rng(19)
    sessions = 100
    names = 50
    keys = []
    matrix = np.empty((sessions * names, 130), dtype=np.float64)
    for session in range(sessions):
        base = np.arange(1, names + 1, dtype=float) / names
        start = session * names
        stop = start + names
        keys.extend([(20_000 + session) * 4_000_000 + 1_000_000 + code for code in range(names)])
        matrix[start:stop, 0] = base
        for column in range(1, 130):
            matrix[start:stop, column] = base[rng.permutation(names)]
    scores = matrix[:, 0].copy()
    audit = campaign.uniqueness_audit(
        np.asarray(keys, dtype=np.int64), matrix, scores, [f"f{index}" for index in range(130)]
    )
    assert audit["comparison_count"] == 130
    assert audit["comparisons"][0]["pairwise_sessions"] == 100
    assert np.isclose(
        audit["comparisons"][0]["median_daily_rank_correlation"], 1.0
    )
    assert audit["comparisons"][0]["gate_passed"] is False
    assert audit["all_required_comparisons_passed"] is False


def _validation_metric(return_value: float = 0.05) -> dict[str, object]:
    return {
        "association": {
            "cohorts": 70,
            "mean_rank_ic": 0.03,
            "mean_top3_minus_bottom3_gross_return": 0.01,
        },
        "normalized_execution": {
            "net_cumulative_return": return_value,
            "maximum_drawdown": -0.1,
            "terminal_unresolved_position_count": 0,
        },
        "pilot_execution_primary_10bp": {
            "net_cumulative_return": return_value - 0.01,
            "board_lot_affordability_rate": 0.95,
            "maximum_filled_trade_daily_amount_participation": 0.005,
            "terminal_unresolved_position_count": 0,
        },
        "pilot_slippage_sensitivity": {
            "0.0020": {"net_cumulative_return": return_value - 0.02}
        },
    }


def test_survivor_decision_requires_all_three_positive_consistent_folds() -> None:
    decision = campaign.survivor_decision(
        {"validation_metrics": [_validation_metric(), _validation_metric(), _validation_metric()]}
    )
    assert decision["passed"] is True
    assert decision["positive_mean_rank_ic_fold_count"] == 3
    assert decision["development_aggregate"]["pilot_20bp_return"] > 0


def test_status_is_read_only(tmp_path) -> None:
    args = type("Args", (), {"output_root": str(tmp_path)})()
    payload = campaign.status(args)
    assert payload["status"] == "frozen_pending_development"
    assert payload["historical_daily_price_or_return_values_read_by_status"] is False
    assert payload["candidate49_ledgers_changed_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False
