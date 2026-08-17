from __future__ import annotations

import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign084_features as features

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_084_research_record_v3.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v20_20260806.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260806_campaign084_verified_v2.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_084/research_attempt_ledger_v6.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_terminal_records_and_bindings_pass() -> None:
    for path in (RESEARCH, POLICY, STATE):
        result = bindings.validate_record(path)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_coverage_failure_stopped_before_comparators_or_returns() -> None:
    research = _load(RESEARCH)
    result = research["no_return_result"]
    assert result["median_coverage"] == 0.9945939627713977
    assert result["p05_coverage"] == 0.0
    assert result["p05_eligible_names"] == 0.0
    assert result["coverage_gate_passed_before_comparison_values"] is False
    assert result["numeric_comparison_count"] == 0
    assert result["comparison_values_read"] is False
    assert result["historical_daily_price_fields_read"] == []
    assert result["historical_forward_returns_read"] is False
    assert research["development_result"]["trial_count"] == 0
    assert research["development_result"]["stress_2024_2025_opened"] is False


def test_future_library_appends_campaign084_once() -> None:
    policy = _load(POLICY)
    item = {"name": features.FACTOR_NAME, "score_direction": "higher"}
    comparisons = features.reconstruct_comparisons() + [item]
    complete = features.reconstruct_complete_definitions() + [item]
    assert len(comparisons) == 114
    assert len(complete) == 116
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
    newly = policy["numerical_comparator_eligibility"]["newly_classified_definition"]
    assert newly["source_supported_sessions_with_at_least_50_names"] == 1378
    assert newly["numeric_comparator_eligible_for_campaign085"] is True
    assert newly["terminal_at_coverage_gate_but_numerically_available"] is True


def test_attempt_accounting_and_candidate49_boundaries() -> None:
    state = _load(STATE)
    ledger = _load(LEDGER)
    assert ledger["campaign084_attempt_count"] == 11
    assert ledger["campaign084_infrastructure_failure_count"] == 10
    assert ledger["campaign084_complete_factor_attempt_count"] == 1
    assert ledger["campaign084_return_reading_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 544
    assert ledger["cumulative_return_reading_development_trial_count"] == 284
    assert state["candidate49_future_only_layer"]["signal_ledger"]["entry_count"] == 0
    assert (
        state["candidate49_future_only_layer"]["execution_ledger"]["entry_count"] == 0
    )
    assert (
        state["historical_research_boundary"][
            "may_generate_current_score_selection_sizing_order_or_advice"
        ]
        is False
    )
    assert state["next_offline_research"]["campaign085_scouting_authorized"] is True
