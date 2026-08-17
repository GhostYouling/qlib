from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign119_features as features


ROOT = Path(__file__).resolve().parents[2]
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_119_terminal_result_20260813.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v109_20260813.json"
)
ATTEMPTS = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_119/research_attempt_ledger_v4.json"
)
WALKFORWARD = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_119/walkforward"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_terminal_bindings_and_zero_survivor_semantics() -> None:
    assert bindings.validate_record(TERMINAL)["all_bindings_passed"] is True
    terminal = _load(TERMINAL)
    survivors = _load(WALKFORWARD / "development_survivors.json")
    stress = _load(WALKFORWARD / "exposed_stress_consumption_record.json")
    assert terminal["status"] == "terminal_zero_development_survivors_stress_not_opened"
    assert terminal["development_decision"]["survivor_count"] == 0
    assert survivors["selected_survivor_count"] == 0
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_frozen_rejection_reasons_and_metrics_are_preserved() -> None:
    terminal = _load(TERMINAL)
    decision = terminal["development_decision"]
    assert decision["positive_mean_rank_ic_fold_count"] == 1
    assert decision["positive_normalized_return_fold_count"] == 1
    assert decision["positive_pilot_return_fold_count"] == 1
    assert decision["development_aggregate_pilot_return_20bp"] == -0.05363866029691433
    assert decision["worst_validation_normalized_drawdown"] == -0.3070319184125526
    assert decision["operational_rejection_reasons"] == []
    assert decision["validation_quality_rejection_reasons"] == [
        "insufficient_positive_ic_folds",
        "median_validation_mean_rank_ic",
        "insufficient_positive_normalized_return_folds",
        "insufficient_positive_pilot_return_folds",
        "median_validation_pilot_return",
        "worst_validation_normalized_drawdown",
        "nonpositive_development_aggregate_20bp_return",
    ]


def test_attempt_ledger_advances_once_without_opening_stress() -> None:
    attempts = _load(ATTEMPTS)
    assert attempts["attempt_count"] == 21
    assert attempts["infrastructure_failure_count"] == 11
    assert attempts["return_reading_complete_development_trial_count"] == 1
    assert attempts["development_survivor_count"] == 0
    assert attempts["stress_trial_count"] == 0
    assert attempts["cumulative_historical_research_attempt_count"] == 935
    assert attempts["cumulative_return_reading_development_trial_count"] == 305
    prior_path = ROOT / attempts["supersedes_without_rewriting"]["path"]
    assert _sha(prior_path) == attempts["supersedes_without_rewriting"]["sha256"]


def test_v109_preserves_v108_definition_and_numeric_comparator_append() -> None:
    policy = _load(POLICY)
    complete = features.reconstruct_complete_definitions()
    numeric = features.reconstruct_comparisons() + [
        {"name": features.FACTOR_NAME, "score_direction": "higher"}
    ]
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 145
    )
    assert policy["complete_historical_feature_library"]["order_sha256"] == (
        features._order_digest(complete)
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 137
    )
    assert policy["numerical_comparator_eligibility"][
        "eligible_numeric_comparator_order_sha256"
    ] == features._order_digest(numeric)


def test_candidate49_and_current_action_boundaries_remain_closed() -> None:
    terminal = _load(TERMINAL)
    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha(signal) == terminal["candidate49"]["signal_ledger_sha256"]
    assert _sha(execution) == terminal["candidate49"]["execution_ledger_sha256"]
    boundary = terminal["terminal_boundary"]
    assert boundary["candidate49_historical_backfill_performed"] is False
    assert boundary["candidate49_ledgers_changed"] is False
    assert (
        boundary["current_scoring_selection_sizing_positions_or_orders_performed"]
        is False
    )


def test_unified_reports_record_campaign119_terminal_result() -> None:
    for relative in (
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
        "docs/a_share_three_day_walkforward_campaign_119_terminal_report.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign119" in text
        assert "-5.363866%" in text
        assert "2024–2025" in text
