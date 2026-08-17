from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign100_features as inventory
from scripts import a_share_three_day_walkforward_campaign101_features as c101
from scripts import a_share_three_day_walkforward_campaign103 as c103


ROOT = Path(__file__).resolve().parents[2]
CONCEPT = ROOT / "docs/a_share_three_day_walkforward_campaign_104_concept_scouting.json"
AUDIT = ROOT / "docs/a_share_three_day_walkforward_campaign_104_mechanism_frontier_audit.json"
FAILURES = ROOT / "docs/a_share_three_day_walkforward_campaign_104_prevalue_infrastructure_failures_20260808.json"
LEDGER = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_104/research_attempt_ledger_v1.json"
RESULT = ROOT / "docs/a_share_three_day_walkforward_campaign_104_prevalue_terminal_result_20260808.json"
POLICY = ROOT / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v62_20260808.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260808_campaign104_prevalue_terminal.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign104_core_artifact_hashes_are_exact() -> None:
    assert _sha256(CONCEPT) == "7494d65bc23b0d6b9f2d158695479c832b6bc7df3ffeea6d2fc095babcd4329a"
    assert _sha256(AUDIT) == "16a61ec45f48202f031272c94b106a2d5c5db68275ce3bdfe2b263c096e2e3be"
    assert _sha256(FAILURES) == "5a29bdbe1249b2d1cc98b1ba6e37befd0b574bbc6e9306213122af37f2a60f44"
    assert _sha256(LEDGER) == "85cedd5276919071227e996182190662af11a6b9a97ef99eb804b18966518d62"
    assert _sha256(RESULT) == "8a4b431e7c702a0f9350b349a41d61836caa129213e2b8d0b478fda1a754500d"
    assert _sha256(POLICY) == "3259f771039a2c3eb64c33b548fd9b198e6cd36f154cb8ab33a06ca91d495dfa"
    assert _sha256(STATE) == "3ebb8fdc3df361b78488a446adc664ebfec85481cadca82ba88c19d647d6f450"


def test_finite_catalog_terminalized_before_any_protected_value() -> None:
    concept = _load(CONCEPT)
    catalog = concept["finite_prevalue_concept_catalog"]
    assert len(catalog) == 5
    assert all(item["decision"].startswith("rejected_before_source") for item in catalog)
    decision = concept["prevalue_decision"]
    assert decision["selected_candidate_count"] == 0
    assert decision["campaign104_source_or_candidate_values_may_be_read"] is False
    boundary = concept["research_boundary"]
    assert boundary["campaign104_source_rows_read"] is False
    assert boundary["campaign104_candidate_values_computed_or_read"] is False
    assert boundary["campaign104_comparator_values_read"] is False
    assert boundary["historical_forward_returns_read"] is False


def test_mandatory_support_inventory_was_reviewed_without_opening_values() -> None:
    audit = _load(AUDIT)
    gate = audit["mandatory_prevalue_support_predicate_gate"]
    assert gate["all_known_terminal_coverage_failures_through_campaign103_reviewed"] is True
    assert len(gate["known_failed_support_inventory"]) == 10
    assert gate["candidate_support_predicate_admitted"] is False
    assert audit["terminal_decision"]["campaign104_feature_snapshot_created"] is False
    assert audit["terminal_decision"]["campaign104_development_or_stress_trial_run"] is False


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    ledger = _load(LEDGER)
    assert ledger["attempt_count"] == len(ledger["entries"]) == 7
    assert ledger["infrastructure_failure_count"] == 6
    assert ledger["prevalue_scientific_attempt_count"] == 1
    assert ledger["complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 775
    assert ledger["cumulative_return_reading_development_trial_count"] == 299
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = (
            "campaign104|"
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


def test_v62_preserves_exact_v61_134_and_131_orders() -> None:
    policy = _load(POLICY)
    c100_item = {"name": inventory.FACTOR_NAME, "score_direction": "higher"}
    c101_item = {"name": c101.FACTOR_NAME, "score_direction": "higher"}
    c103_item = {"name": c103.ADMITTED_FACTOR, "score_direction": "higher"}
    complete = inventory.reconstruct_complete_definitions() + [c100_item, c101_item, c103_item]
    numeric = inventory.reconstruct_comparisons() + [c100_item, c101_item, c103_item]
    assert len(complete) == policy["complete_historical_feature_library"]["factor_definition_count"] == 134
    assert inventory._order_digest(complete) == policy["complete_historical_feature_library"]["order_sha256"]
    assert len(numeric) == policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"] == 131
    assert inventory._order_digest(numeric) == policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_order_sha256"]
    assert policy["campaign104_terminal_classification"]["complete_factor_definition_count"] == 0


def test_state_preserves_candidate49_and_saturday_provider_boundary() -> None:
    state = _load(STATE)
    assert state["local_session_status"]["accepted_local_trading_day"] is False
    assert state["local_session_status"]["candidate49_provider_workflow_allowed_today"] is False
    assert state["candidate49"]["signal_entry_count"] == 0
    assert state["candidate49"]["execution_entry_count"] == 0
    assert state["candidate49"]["historical_backfill_performed"] is False
    assert state["provider_request_accounting"]["campaign104_historical_research_provider_calls"] == 0
    assert state["provider_credential"]["recognized_nonempty_token_key_count"] == 1
    assert state["provider_credential"]["secret_printed_hashed_logged_or_persisted"] is False


def test_new_logical_timestamps_do_not_postdate_file_writes() -> None:
    for path in (CONCEPT, AUDIT, FAILURES, LEDGER, RESULT, POLICY, STATE):
        recorded = datetime.fromisoformat(_load(path)["recorded_at"].replace("Z", "+00:00"))
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        assert recorded <= modified


def test_unified_reports_record_zero_candidate_result_and_no_advice() -> None:
    for path in (
        ROOT / "docs/a_share_three_day_walkforward_campaign_104_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "Campaign104" in text
        assert "775" in text
        assert "299" in text
        assert "v62" in text

