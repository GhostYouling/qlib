from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign097_features as definitions


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_097/"
    "research_attempt_ledger_v4.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v43_20260807.json"
)
FREEZE = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_097_"
    "terminal_completion_freeze_20260807.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_effective_terminal_binding_chain_is_exact() -> None:
    assert _sha256(LEDGER) == (
        "7937de2084a2218a00a5f2fbe40395d706bf1f3865f56da969fc5a8dc35deddd"
    )
    assert _sha256(POLICY) == (
        "5f13ed6f376cd428195b9e5783f30651bad761dbec7feb77b86eb7274dcf034a"
    )
    assert _sha256(FREEZE) == (
        "692c542bb298cc7c2debe8cfd2a246177e88537c44a5793222277fd6f78af299"
    )
    for path in (LEDGER, POLICY, FREEZE):
        assert bindings.validate_record(path)["all_bindings_passed"] is True


def test_final_attempt_accounting_is_additive_and_science_is_unchanged() -> None:
    ledger = _load(LEDGER)
    predecessor = ledger["supersedes_without_rewriting"]
    assert predecessor["preserved_ledger_entry_count"] == 15
    assert predecessor["preserved_attempt_count"] == 12
    assert predecessor["scientific_result_changed"] is False
    assert [entry["ordinal"] for entry in ledger["entries_appended"]] == [16]
    assert ledger["entries_appended"][0]["research_attempt_count_increment"] == 1
    assert ledger["entries_appended"][0]["development_trial_count_increment"] == 0
    assert ledger["campaign097_attempt_count"] == 13
    assert ledger["campaign097_ledger_entry_count"] == 16
    assert ledger["campaign097_infrastructure_or_implementation_failure_count"] == 12
    assert ledger["campaign097_complete_factor_attempt_count"] == 1
    assert ledger["campaign097_return_reading_development_trial_count"] == 1
    assert ledger["campaign097_development_survivor_count"] == 0
    assert ledger["campaign097_stress_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 679
    assert ledger["cumulative_return_reading_development_trial_count"] == 292

    result = _load(FREEZE)["terminal_scientific_result"]
    assert result["coverage_gate_passed"] is True
    assert result["all_numeric_comparisons_passed"] is True
    assert result["development_survivor_count"] == 0
    assert result["stress_2024_2025_opened"] is False
    assert result["stress_2024_2025_return_fields_read"] is False
    assert result["same_campaign_rescue_allowed"] is False


def test_v43_appends_campaign097_to_complete_and_numeric_orders() -> None:
    policy = _load(POLICY)
    factor = {
        "name": "intraday_market_range_profile_synchronization_240m",
        "score_direction": "higher",
    }
    complete = definitions.reconstruct_complete_definitions() + [factor]
    numeric = definitions.reconstruct_comparisons() + [factor]
    complete_policy = policy["complete_historical_feature_library"]
    numeric_policy = policy["numerical_comparator_eligibility"]
    assert len(complete) == complete_policy["factor_definition_count"] == 129
    assert definitions._order_digest(complete) == complete_policy["order_sha256"]
    assert len(numeric) == numeric_policy["eligible_numeric_comparator_count"] == 126
    assert (
        definitions._order_digest(numeric)
        == numeric_policy["eligible_numeric_comparator_order_sha256"]
    )
    last = numeric_policy["last_comparator"]
    assert last["sessions_with_at_least_50_finite_names"] == 1623
    assert last["session_capacity_verified_with_frozen_stock_day_key_decoder"] is True
    assert last["numeric_comparator_eligible_for_campaign098"] is True


def test_reports_candidate49_and_current_action_boundaries_are_exact() -> None:
    freeze = _load(FREEZE)
    for key in (
        "campaign_report",
        "unified_report",
        "current_report",
        "data_pipeline_documentation",
    ):
        binding = freeze[key]
        report = ROOT / binding["path"]
        assert _sha256(report) == binding["sha256"]
        text = report.read_text(encoding="utf-8")
        assert "Campaign097" in text
        assert "679" in text
        assert "292" in text

    candidate49 = freeze["candidate49"]
    signal = ROOT / (
        "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = ROOT / (
        "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha256(signal) == candidate49["signal_ledger_sha256"]
    assert _sha256(execution) == candidate49["execution_ledger_sha256"]
    assert _load(signal)["entries"] == []
    assert _load(execution)["entries"] == []
    assert candidate49["historical_backfill_performed"] is False
    assert candidate49["remains_only_active_prospective_candidate"] is True
    assert freeze["provider_request_issued"] is False
    assert freeze["current_scoring_selection_sizing_or_orders_performed"] is False
    assert freeze["investment_advice"] is False
