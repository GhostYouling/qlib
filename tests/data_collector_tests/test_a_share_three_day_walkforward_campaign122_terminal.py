from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign121_features as features


ROOT = Path(__file__).resolve().parents[2]
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_122_terminal_result_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v120_20260814.json"
)
ATTEMPTS = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_122/research_attempt_ledger_v3.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign122_terminal_bindings_and_zero_candidate_semantics() -> None:
    assert bindings.validate_record(TERMINAL)["all_bindings_passed"] is True
    terminal = _load(TERMINAL)
    assert terminal["scientific_result"]["finite_catalog_size"] == 6
    assert terminal["scientific_result"]["selected_candidate_count"] == 0
    assert terminal["scientific_result"]["complete_factor_attempt_count"] == 0
    assert terminal["scientific_result"]["return_reading_development_trial_count"] == 0
    assert terminal["terminal_decision"]["terminal"] is True
    assert terminal["terminal_decision"]["retry_relabel_or_rescue_allowed"] is False


def test_campaign122_attempt_ledger_counts_every_failure_and_scientific_attempt() -> (
    None
):
    assert bindings.validate_record(ATTEMPTS)["all_bindings_passed"] is True
    attempts = _load(ATTEMPTS)
    assert attempts["attempt_count"] == 7
    assert attempts["ledger_entry_count"] == 7
    assert attempts["infrastructure_failure_count"] == 6
    assert attempts["prevalue_scientific_attempt_count"] == 1
    assert attempts["complete_factor_attempt_count"] == 0
    assert attempts["return_reading_complete_development_trial_count"] == 0
    assert attempts["cumulative_historical_research_attempt_count"] == 999
    assert attempts["cumulative_return_reading_development_trial_count"] == 306


def test_v120_preserves_v119_library_without_campaign122_append() -> None:
    assert bindings.validate_record(POLICY)["all_bindings_passed"] is True
    policy = _load(POLICY)
    complete = features.reconstruct_complete_definitions()
    numeric = features.reconstruct_comparisons() + [
        {"name": features.FACTOR_NAME, "score_direction": "higher"}
    ]
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 147
    )
    assert policy["complete_historical_feature_library"]["order_sha256"] == (
        features._order_digest(complete)
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 139
    )
    assert policy["numerical_comparator_eligibility"][
        "eligible_numeric_comparator_order_sha256"
    ] == features._order_digest(numeric)
    assert (
        policy["campaign122_terminal_classification"]["selected_candidate_count"] == 0
    )
    assert (
        policy["campaign122_terminal_classification"]["retry_relabel_or_rescue_allowed"]
        is False
    )


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
    boundary = terminal["research_boundary"]
    assert boundary["provider_request_issued"] is False
    assert boundary["candidate49_historical_backfill_performed"] is False
    assert boundary["candidate49_ledgers_changed"] is False
    assert (
        boundary["current_scoring_selection_sizing_positions_or_orders_performed"]
        is False
    )


def test_unified_reports_record_campaign122_terminal_result() -> None:
    for relative in (
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
        "docs/a_share_three_day_walkforward_campaign_122_terminal_report.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign122" in text
        assert "147/139" in text
        assert "997" in text
