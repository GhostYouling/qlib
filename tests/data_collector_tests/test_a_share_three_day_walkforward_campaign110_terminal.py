from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign110_features as campaign110


ROOT = Path(__file__).resolve().parents[2]
TERMINAL = ROOT / "docs/a_share_three_day_walkforward_campaign_110_terminal_result_binding_v2_20260808.json"
POLICY = ROOT / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v72_20260808.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260808_campaign110_terminal.json"
LEDGERS = [
    ROOT
    / f"data/experiments/short_horizon/historical_walkforward/campaign_110/research_attempt_ledger_v{version}.json"
    for version in range(1, 5)
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_binding(binding: dict) -> None:
    path = Path(binding["path"])
    if not path.is_absolute():
        path = ROOT / path
    assert _sha(path) == binding["sha256"]


def test_terminal_v2_preserves_scientific_outputs_and_corrected_ledger() -> None:
    terminal = _load(TERMINAL)
    _assert_binding(terminal["supersedes_without_rewriting"])
    _assert_binding(terminal["research_attempt_ledger"])
    for binding in terminal["preserved_scientific_outputs"].values():
        _assert_binding(binding)
    for binding in terminal["reports"].values():
        _assert_binding(binding)
    assert terminal["scientific_result"] == (
        "rejected_by_frozen_2019_2023_development_survivor_gates"
    )
    assert terminal["development_survivor_count"] == 0
    assert terminal["stress_2024_2025_opened"] is False


def test_additive_attempt_ledgers_reconcile_without_rewriting() -> None:
    ledgers = [_load(path) for path in LEDGERS]
    for previous_path, current in zip(LEDGERS[:-1], ledgers[1:], strict=True):
        assert _sha(previous_path) == current["supersedes_without_rewriting"]["sha256"]
    assert len(ledgers[0]["attempts"]) == 11
    assert len(ledgers[1]["appended_entries"]) == 1
    assert len(ledgers[2]["appended_entries"]) == 0
    assert len(ledgers[3]["appended_entries"]) == 1
    final = ledgers[-1]
    assert final["attempt_count"] == final["ledger_entry_count"] == 13
    assert final["infrastructure_failure_count"] == 12
    assert final["complete_factor_attempt_count"] == 1
    assert final["scientifically_decided_factor_attempt_count"] == 1
    assert final["return_reading_complete_development_trial_count"] == 1
    assert final["cumulative_historical_research_attempt_count"] == 822
    assert final["cumulative_return_reading_development_trial_count"] == 302


def test_all_133_no_return_gates_passed_before_development() -> None:
    terminal = _load(TERMINAL)
    audit = _load(ROOT / terminal["preserved_scientific_outputs"]["no_return_audit"]["path"])
    factor = campaign110.FACTOR_NAME
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert uniqueness["comparison_factor_count"] == 133
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_numeric_comparisons_passed"] is True
    assert uniqueness["maximum_observed_absolute_median_daily_rank_correlation"] == 0.719725962987115
    assert audit["historical_forward_return_fields_read"] is False


def test_development_rejection_and_closed_stress_are_exact() -> None:
    terminal = _load(TERMINAL)
    outputs = terminal["preserved_scientific_outputs"]
    survivors = _load(ROOT / outputs["development_survivors"]["path"])
    stress = _load(ROOT / outputs["exposed_stress_record"]["path"])
    decision = survivors["trial_decisions"][0]
    assert decision["positive_mean_rank_ic_fold_count"] == 1
    assert decision["positive_normalized_return_fold_count"] == 1
    assert decision["positive_pilot_return_fold_count"] == 0
    assert decision["median_validation_mean_rank_ic"] == -0.005767443993476971
    assert decision["development_aggregate_20bp_return"] == -0.19211693358371162
    assert decision["development_survivor_gate_passed"] is False
    assert survivors["selected_survivor_count"] == 0
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_v72_preserves_v71_library_and_appends_campaign110_once() -> None:
    policy = _load(POLICY)
    _assert_binding(policy["supersedes_without_rewriting"])
    for binding in policy["authoritative_inputs"].values():
        _assert_binding(binding)
    appended = {"name": campaign110.FACTOR_NAME, "score_direction": "higher"}
    complete = campaign110.reconstruct_complete_definitions() + [appended]
    numeric = campaign110.reconstruct_comparisons() + [appended]
    assert len(complete) == 140
    assert campaign110._order_digest(complete) == policy[
        "complete_historical_feature_library"
    ]["order_sha256"]
    assert len(numeric) == 134
    assert campaign110._order_digest(numeric) == policy[
        "numerical_comparator_eligibility"
    ]["eligible_numeric_comparator_order_sha256"]


def test_state_bindings_candidate49_and_weekend_boundary() -> None:
    state = _load(STATE)
    bindings = [
        state["supersedes_without_rewriting"],
        state["campaign110_terminal"]["terminal_result"],
        state["campaign110_terminal"]["research_attempt_ledger"],
        state["campaign110_terminal"]["no_return_audit"],
        state["campaign110_terminal"]["development_trial_ledger"],
        state["campaign110_terminal"]["development_survivors"],
        state["campaign110_terminal"]["exposed_stress_record"],
        state["effective_future_numeric_policy"],
        state["candidate49"]["signal_ledger"],
        state["candidate49"]["execution_ledger"],
        state["candidate49"]["latest_preserved_source_failure"],
        *state["reports"].values(),
    ]
    for binding in bindings:
        _assert_binding(binding)
    assert state["candidate49"]["signal_ledger"]["entry_count"] == 0
    assert state["candidate49"]["execution_ledger"]["entry_count"] == 0
    assert state["provider_credential"]["repository_dotenv_mode"] == "0600"
    assert state["provider_credential"]["tushare_token_nonempty"] is True
    assert state["provider_credential"]["secret_printed_hashed_logged_or_persisted"] is False
    assert state["weekend_boundary"]["accepted_local_trading_day"] is False
    assert state["weekend_boundary"]["candidate49_plan_or_run_executed"] is False
    assert state["research_boundary"]["stress_2024_2025_opened_by_campaign110"] is False
