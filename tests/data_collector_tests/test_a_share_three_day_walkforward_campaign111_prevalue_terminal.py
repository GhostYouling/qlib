from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign110_features as c110


ROOT = Path(__file__).resolve().parents[2]
CONCEPT = ROOT / "docs/a_share_three_day_walkforward_campaign_111_concept_scouting_20260809.json"
AUDIT = ROOT / "docs/a_share_three_day_walkforward_campaign_111_mechanism_frontier_audit_20260809.json"
FAILURES = ROOT / "docs/a_share_three_day_walkforward_campaign_111_prevalue_infrastructure_failures_20260809.json"
LEDGER = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_111/research_attempt_ledger_v1.json"
RESULT = ROOT / "docs/a_share_three_day_walkforward_campaign_111_prevalue_terminal_result_20260809.json"
POLICY = ROOT / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v73_20260809.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260809_campaign111_prevalue_terminal.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign111_core_artifact_hashes_are_exact() -> None:
    assert _sha256(CONCEPT) == "2f366400dfbf408e92528a434c02f0156731a6503adeb943c0764825d514d7dd"
    assert _sha256(AUDIT) == "8e4dd9f7451e3e5deb05bc9bb0d5f122b8c838027e275022fd92fae762a467d5"
    assert _sha256(FAILURES) == "ab85676339d72294eebb8c3100188f0eacc2635ce9714b181bb343ba35f2c66e"
    assert _sha256(LEDGER) == "6a87c3a191485fcba6996df84fbc713750345ed4ec40d23ca14bf4b418f0cd4b"
    assert _sha256(RESULT) == "999e4ee504a4cde06defea586c21b23a60311870e94b024453889e5c9d6dc8cf"
    assert _sha256(POLICY) == "4e6080a952e5bd4227dc5de60421cafbea325ddfbe022a87db3452739dd7b7b2"
    assert _sha256(STATE) == "90a9831c7100553dbd34e0e7724e683c5d073c9ec839c294ce3bdc5685803a9c"


def test_finite_catalog_terminalized_before_any_protected_value() -> None:
    concept = _load(CONCEPT)
    catalog = concept["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert all(item["decision"].startswith("rejected_before") for item in catalog)
    decision = concept["prevalue_decision"]
    assert decision["complete_logical_definitions_reviewed"] == 140
    assert decision["selected_candidate_count"] == 0
    assert decision["campaign111_source_or_candidate_values_may_be_read"] is False
    boundary = concept["research_boundary"]
    assert boundary["campaign111_source_rows_read"] is False
    assert boundary["campaign111_candidate_values_computed_or_read"] is False
    assert boundary["campaign111_comparator_values_read"] is False
    assert boundary["historical_forward_returns_read"] is False


def test_complete_semantic_and_support_review_stopped_before_values() -> None:
    audit = _load(AUDIT)
    complete = audit["complete_mechanism_review"]
    assert complete["all_140_frozen_logical_definitions_and_terminal_histories_reviewed"] is True
    assert complete["all_134_numeric_comparators_reserved_but_not_loaded"] is True
    gate = audit["mandatory_prevalue_support_predicate_gate"]
    assert gate["all_known_terminal_coverage_and_adapter_failures_through_campaign110_reviewed"] is True
    assert gate["candidate_support_predicate_admitted"] is False
    terminal = audit["terminal_decision"]
    assert terminal["campaign111_feature_snapshot_created"] is False
    assert terminal["campaign111_development_or_stress_trial_run"] is False


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    ledger = _load(LEDGER)
    assert ledger["attempt_count"] == len(ledger["entries"]) == 3
    assert ledger["infrastructure_failure_count"] == 2
    assert ledger["prevalue_scientific_attempt_count"] == 1
    assert ledger["complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 825
    assert ledger["cumulative_return_reading_development_trial_count"] == 302
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = (
            "campaign111|"
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


def test_v73_preserves_exact_v72_140_and_134_orders() -> None:
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
    assert policy["campaign111_terminal_classification"]["complete_factor_definition_count"] == 0


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


def test_unified_reports_record_zero_candidate_result_and_no_advice() -> None:
    for path in (
        ROOT / "docs/a_share_three_day_walkforward_campaign_111_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "Campaign111" in text
        assert "825" in text
        assert "302" in text
        assert "v73" in text
        assert "Candidate49" in text

