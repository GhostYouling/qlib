from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign109_features as campaign109


ROOT = Path(__file__).resolve().parents[2]
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_109_terminal_result_binding_20260808.json"
)
LEDGERS = [
    ROOT
    / f"data/experiments/short_horizon/historical_walkforward/campaign_109/research_attempt_ledger_v{version}.json"
    for version in range(1, 6)
]
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v70_20260808.json"
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260808_campaign109_terminal.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_terminal_result_bindings_and_scientific_stop_are_exact() -> None:
    result = _load(RESULT)
    bindings = [
        result["no_return_result"],
        result["development_trial_ledger"],
        result["development_survivors"],
        result["exposed_stress_record"],
        result["campaign_report"],
        result["research_attempt_ledger"],
        *result["preserved_failures"],
    ]
    for binding in bindings:
        assert _sha(ROOT / binding["path"]) == binding["sha256"]
    scientific = result["scientific_terminal_semantics"]
    assert scientific["coverage_gate_passed"] is True
    assert scientific["numeric_comparisons_completed"] == 132
    assert scientific["numeric_comparisons_passed"] == 132
    assert scientific["development_trial_count"] == 1
    assert scientific["development_survivor_count"] == 0
    assert scientific["scientific_result"] == (
        "rejected_by_frozen_2019_2023_development_survivor_gates"
    )
    assert scientific["stress_2024_2025_opened"] is False


def test_append_only_research_ledger_chain_and_accounting_reconcile() -> None:
    ledgers = [_load(path) for path in LEDGERS]
    for previous_path, current in zip(LEDGERS[:-1], ledgers[1:], strict=True):
        assert _sha(previous_path) == current["supersedes_without_rewriting"][
            "sha256"
        ]
    entries = [*ledgers[0]["entries"]]
    for ledger in ledgers[1:]:
        entries.extend(ledger["appended_entries"])
    previous = ledgers[0]["chain_genesis"]
    for entry in entries:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign109",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode()).hexdigest()
        assert entry["entry_sha256"] == previous
    final = ledgers[-1]
    assert final["chain_tip_sha256"] == previous
    assert len(entries) == final["ledger_entry_count"] == 8
    assert final["attempt_count"] == 8
    assert final["infrastructure_failure_count"] == 7
    assert final["complete_factor_attempt_count"] == 1
    assert final["scientifically_decided_factor_attempt_count"] == 1
    assert final["return_reading_complete_development_trial_count"] == 1
    assert final["cumulative_historical_research_attempt_count"] == 809
    assert final["cumulative_return_reading_development_trial_count"] == 301


def test_no_return_gate_passed_all_132_before_development() -> None:
    audit = _load(ROOT / _load(RESULT)["no_return_result"]["path"])
    factor = campaign109.FACTOR_NAME
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9983169704145587
    assert coverage["p05_coverage"] == 0.9933243474380903
    assert uniqueness["comparison_factor_count"] == 132
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_numeric_comparisons_passed"] is True
    assert uniqueness["maximum_observed_absolute_median_daily_rank_correlation"] == (
        0.7554105598815716
    )
    assert audit["admissible_factor_count"] == 1
    assert audit["historical_forward_return_fields_read"] is False


def test_development_failed_quality_gates_and_stress_remained_closed() -> None:
    result = _load(RESULT)
    ledger = _load(ROOT / result["development_trial_ledger"]["path"])
    survivors = _load(ROOT / result["development_survivors"]["path"])
    stress = _load(ROOT / result["exposed_stress_record"]["path"])
    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["positive_mean_rank_ic_fold_count"] == 0
    assert decision["positive_normalized_return_fold_count"] == 1
    assert decision["positive_pilot_return_fold_count"] == 1
    assert decision["median_validation_mean_rank_ic"] == -0.03756579859633194
    assert decision["development_aggregate_20bp_return"] == -0.12524724385260444
    assert decision["development_survivor_gate_passed"] is False
    assert survivors["selected_survivor_count"] == 0
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_v70_appends_definition_and_numeric_comparator_once() -> None:
    policy = _load(POLICY)
    append = {"name": campaign109.FACTOR_NAME, "score_direction": "higher"}
    complete = campaign109.reconstruct_complete_definitions() + [append]
    numeric = campaign109.reconstruct_comparisons() + [append]
    assert len(complete) == 139
    assert campaign109._order_digest(complete) == policy[
        "complete_historical_feature_library"
    ]["order_sha256"]
    assert len(numeric) == 133
    assert campaign109._order_digest(numeric) == policy[
        "numerical_comparator_eligibility"
    ]["eligible_numeric_comparator_order_sha256"]
    assert policy["campaign109_terminal_classification"][
        "numeric_comparator_eligible"
    ] is True


def test_current_state_bindings_candidate49_and_weekend_boundary() -> None:
    state = _load(STATE)
    bindings = [
        state["supersedes_without_rewriting"],
        state["campaign109_terminal"]["terminal_result"],
        state["campaign109_terminal"]["research_attempt_ledger"],
        state["campaign109_terminal"]["no_return_audit"],
        state["campaign109_terminal"]["development_trial_ledger"],
        state["campaign109_terminal"]["development_survivors"],
        state["campaign109_terminal"]["exposed_stress_record"],
        state["effective_future_numeric_policy"],
        state["candidate49"]["signal_ledger"],
        state["candidate49"]["execution_ledger"],
        state["candidate49"]["latest_preserved_source_failure"],
        *state["reports"].values(),
    ]
    for binding in bindings:
        assert _sha(ROOT / binding["path"]) == binding["sha256"]
    assert state["candidate49"]["signal_ledger"]["entry_count"] == 0
    assert state["candidate49"]["execution_ledger"]["entry_count"] == 0
    assert state["provider_credential"]["repository_dotenv_mode"] == "0600"
    assert state["provider_credential"]["tushare_token_nonempty"] is True
    assert state["provider_credential"][
        "secret_printed_hashed_logged_or_persisted"
    ] is False
    assert state["weekend_boundary"]["candidate49_plan_or_run_executed"] is False
    assert state["research_boundary"]["stress_2024_2025_opened_by_campaign109"] is False
