from __future__ import annotations

import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign082_features as features


ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "docs/a_share_three_day_walkforward_campaign_082_research_record.json"
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v18_20260806.json"
)
FREEZE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_082_terminal_completion_freeze_20260806.json"
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260806_campaign082_verified.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_082/research_attempt_ledger_v4.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_terminal_records_and_all_bindings_pass() -> None:
    for path in (RESEARCH, POLICY, FREEZE, STATE):
        assert bindings.validate_record(path)["all_bindings_passed"] is True


def test_terminal_result_and_stress_remain_closed() -> None:
    research = _load(RESEARCH)
    decision = research["development_trial"]["survivor_decision"]
    assert research["status"] == "terminal_zero_development_survivors_stress_closed"
    assert decision["development_survivor_count"] == 0
    assert decision["development_aggregate_20bp_return"] == -0.11395294069859907
    assert research["stress_2024_2025"]["opened"] is False
    assert research["stress_2024_2025"]["return_fields_read"] is False


def test_future_library_order_appends_campaign082_once() -> None:
    policy = _load(POLICY)
    comparisons = features.reconstruct_comparisons() + [
        {"name": features.FACTOR_NAME, "score_direction": "higher"}
    ]
    complete = features.reconstruct_complete_definitions() + [
        {"name": features.FACTOR_NAME, "score_direction": "higher"}
    ]
    assert len(comparisons) == 112
    assert len(complete) == 114
    assert (
        features._comparison_order_digest(comparisons)
        == policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert (
        features._comparison_order_digest(complete)
        == policy["complete_historical_feature_library"]["order_sha256"]
    )


def test_attempt_accounting_and_candidate49_boundaries() -> None:
    state = _load(STATE)
    ledger = _load(LEDGER)
    accounting = state["attempt_accounting"]
    assert ledger["campaign082_infrastructure_failure_count"] == 5
    assert ledger["campaign082_return_reading_development_trial_count"] == 1
    assert accounting["cumulative_historical_research_attempts"] == 506
    assert accounting["cumulative_return_reading_development_trials"] == 283
    assert state["candidate49_future_only_layer"]["signal_ledger_entries"] == 0
    assert state["candidate49_future_only_layer"]["execution_ledger_entries"] == 0
    assert state["candidate49_future_only_layer"]["provider_request_issued"] is False
    assert (
        state["historical_research_boundary"][
            "may_generate_current_score_selection_sizing_order_or_advice"
        ]
        is False
    )
