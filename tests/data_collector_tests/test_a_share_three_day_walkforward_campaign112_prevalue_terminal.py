from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign110_features as c110


ROOT = Path(__file__).resolve().parents[2]
CONCEPT = ROOT / "docs/a_share_three_day_walkforward_campaign_112_concept_scouting_20260809.json"
AUDIT = ROOT / "docs/a_share_three_day_walkforward_campaign_112_mechanism_source_frontier_audit_20260809.json"
FAILURES = ROOT / "docs/a_share_three_day_walkforward_campaign_112_prevalue_infrastructure_failures_20260809.json"
LEDGER = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_112/research_attempt_ledger_v1.json"
RESULT = ROOT / "docs/a_share_three_day_walkforward_campaign_112_prevalue_terminal_result_20260809.json"
POLICY = ROOT / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v74_20260809.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260809_campaign112_prevalue_terminal.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign112_core_artifact_hashes_are_exact() -> None:
    assert _sha256(CONCEPT) == "d8267ad6011c6c613bca9d3f3b2ea068c7894b5d1ec49986940419d8173fb7a0"
    assert _sha256(AUDIT) == "5788de0c78ab6c631ba152bf4a5df5476601c37b9cab937e28438a2447840658"
    assert _sha256(FAILURES) == "d5d6ad3cb26fae9cfd74ef4b141e395ae8b8463559f0ec8da614f12c6f577f0e"
    assert _sha256(LEDGER) == "04e461110d134ed076051ace5245acfe90fb5d9eb74ccbab92a0396b1d73cfde"
    assert _sha256(RESULT) == "7104d3c2d608b11d0b523b0a74278ef27d102cfbb09e9044f45dead9a72032fc"
    assert _sha256(POLICY) == "c5a2ca6f47ed86d95f867648475466a1a3ab5c5c2880f38f6df82ec49ed4aa4c"
    assert _sha256(STATE) == "a8b56171ec20a130a1485aa9316d72e030ad928900eb4b7368c30b79e95c53b8"


def test_finite_catalog_terminalized_before_any_protected_value() -> None:
    concept = _load(CONCEPT)
    catalog = concept["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert sum(item["decision"].startswith("rejected_before") for item in catalog) == 5
    assert sum(item["decision"].startswith("deferred_requires_new_source") for item in catalog) == 1
    decision = concept["prevalue_decision"]
    assert decision["complete_logical_definitions_reviewed"] == 140
    assert decision["selected_candidate_count"] == 0
    assert decision["campaign112_source_or_candidate_values_may_be_read"] is False
    boundary = concept["research_boundary"]
    assert boundary["campaign112_source_rows_read"] is False
    assert boundary["campaign112_candidate_values_computed_or_read"] is False
    assert boundary["campaign112_comparator_values_read"] is False
    assert boundary["historical_forward_returns_read"] is False


def test_semantic_support_and_source_frontier_stopped_before_values() -> None:
    audit = _load(AUDIT)
    complete = audit["complete_mechanism_review"]
    assert complete["all_140_frozen_logical_definitions_and_terminal_histories_reviewed"] is True
    assert complete["all_134_numeric_comparators_reserved_but_not_loaded"] is True
    gate = audit["mandatory_prevalue_support_and_source_gate"]
    assert gate["all_known_terminal_coverage_and_adapter_failures_through_campaign111_reviewed"] is True
    assert gate["top_list_historical_source_accepted"] is False
    assert gate["candidate_support_predicate_admitted"] is False
    terminal = audit["terminal_decision"]
    assert terminal["campaign112_feature_snapshot_created"] is False
    assert terminal["campaign112_development_or_stress_trial_run"] is False
    assert terminal["top_list_concept_is_active_or_preregistered"] is False


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    ledger = _load(LEDGER)
    assert ledger["attempt_count"] == len(ledger["entries"]) == 2
    assert ledger["infrastructure_failure_count"] == 1
    assert ledger["prevalue_scientific_attempt_count"] == 1
    assert ledger["complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 827
    assert ledger["cumulative_return_reading_development_trial_count"] == 302
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = (
            "campaign112|"
            + entry["attempt_id"]
            + "|"
            + previous
            + "|"
            + entry["phase"]
            + "|"
            + entry["status"]
        ).encode()
        assert hashlib.sha256(payload).hexdigest() == entry["entry_sha256"]
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]


def test_v74_preserves_exact_v73_140_and_134_orders() -> None:
    policy = _load(POLICY)
    complete = c110.reconstruct_complete_definitions() + [
        {"name": c110.FACTOR_NAME, "score_direction": "higher"}
    ]
    numeric = c110.reconstruct_comparisons() + [
        {"name": c110.FACTOR_NAME, "score_direction": "higher"}
    ]
    complete_policy = policy["complete_historical_feature_library"]
    numeric_policy = policy["numerical_comparator_eligibility"]
    assert len(complete) == complete_policy["factor_definition_count"] == 140
    assert c110._order_digest(complete) == complete_policy["order_sha256"]
    assert len(numeric) == numeric_policy["eligible_numeric_comparator_count"] == 134
    assert c110._order_digest(numeric) == numeric_policy["eligible_numeric_comparator_order_sha256"]
    assert policy["campaign112_terminal_classification"]["complete_factor_definition_count"] == 0


def test_state_preserves_candidate49_and_sunday_provider_boundary() -> None:
    state = _load(STATE)
    assert state["local_session_status"]["accepted_local_trading_day"] is False
    assert state["local_session_status"]["candidate49_provider_workflow_allowed_today"] is False
    assert state["candidate49"]["signal_ledger"]["entry_count"] == 0
    assert state["candidate49"]["execution_ledger"]["entry_count"] == 0
    assert state["candidate49"]["historical_backfill_performed"] is False
    assert state["provider_credential"]["tushare_token_entry_count"] == 1
    assert state["provider_credential"]["tushare_token_nonempty"] is True
    assert state["provider_credential"]["secret_printed_hashed_logged_or_persisted"] is False
    assert _sha256(ROOT / state["candidate49"]["signal_ledger"]["path"]) == state["candidate49"]["signal_ledger"]["sha256"]
    assert _sha256(ROOT / state["candidate49"]["execution_ledger"]["path"]) == state["candidate49"]["execution_ledger"]["sha256"]


def test_new_logical_timestamps_do_not_postdate_file_writes() -> None:
    for path in (CONCEPT, AUDIT, FAILURES, LEDGER, RESULT, POLICY, STATE):
        recorded = datetime.fromisoformat(_load(path)["recorded_at"].replace("Z", "+00:00"))
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        assert recorded <= modified


def test_unified_reports_record_frontier_result_and_no_advice() -> None:
    for path in (
        ROOT / "docs/a_share_three_day_walkforward_campaign_112_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "Campaign112" in text
        assert "827" in text
        assert "302" in text
        assert "v74" in text
        assert "Candidate49" in text
