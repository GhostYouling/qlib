from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_156_credit_governance_source_scouting_20260815.json"
)
AUDIT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_156_credit_governance_source_admission_audit_20260815.json"
)
FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_156_ledger_hash_generation_shell_variable_failure_20260815.json"
)
FORMAT_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_156_focused_format_gate_failure_20260815.json"
)
PATCH_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_156_final_test_binding_patch_context_failure_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_156/research_attempt_ledger_v2.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_156_terminal_result_v2_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v219_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign156_prevalue_terminal_v2.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_156_terminal_report.md"
SIGNAL_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign156_finite_catalog_stops_before_source_rows_or_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_source_catalog"]
    assert len(catalog) == 6
    assert len({entry["catalog_id"] for entry in catalog}) == 6
    assert len({entry["name"] for entry in catalog}) == 6
    decisions = [entry["prevalue_decision"] for entry in catalog]
    assert sum(item.startswith("deferred_") for item in decisions) == 4
    assert sum(item.startswith("rejected_") for item in decisions) == 2
    assert scouting["selection"]["selected_candidate_count"] == 0
    assert (
        scouting["selection"][
            "deferred_for_future_separately_preregistered_source_verification_count"
        ]
        == 4
    )
    boundary = scouting["research_boundary"]
    assert boundary["source_row_or_response_values_read"] is False
    assert boundary["candidate_values_computed_or_read"] is False
    assert boundary["comparator_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False


def test_campaign156_source_gate_distinguishes_deferral_from_factor_failure() -> None:
    audit = _load(AUDIT)
    results = audit["proposal_gate_results"]
    assert len(results) == 6
    assert all(item["passed"] is False for item in results)
    classifications = [item["classification"] for item in results]
    assert classifications.count("source_admission_deferred_not_factor_failure") == 4
    assert classifications.count("terminal_source_family_overlap_rejection") == 2
    assert audit["gate_summary"]["all_gate_passers"] == 0
    assert audit["gate_summary"]["selected_candidate_count"] == 0
    interpretation = audit["scientific_interpretation"]
    assert interpretation["deferred_concepts_tested_for_predictive_value"] is False
    assert interpretation["deferred_concepts_declared_ineffective"] is False
    terminal = audit["terminal_decision"]
    assert terminal["formula_feature_adapter_or_model_created"] is False
    assert terminal["source_row_or_endpoint_response_value_read"] is False
    assert terminal["comparison_or_return_value_read"] is False


def test_campaign156_records_infrastructure_failures_without_masking() -> None:
    failure = _load(FAILURE)
    assert failure["failure"]["exit_code_nonzero"] is True
    assert failure["failure"]["exact_exit_code_not_captured"] is True
    assert failure["failure"]["ledger_written_before_failure"] is False
    assert failure["failure"]["entry_hash_printed_before_failure"] is False
    recovery = failure["safe_recovery"]
    assert "entry_status" in recovery["method"]
    assert recovery["failed_exit_code_bypassed_or_masked"] is False
    format_failure = _load(FORMAT_FAILURE)
    assert format_failure["failure"]["exit_code_nonzero"] is True
    assert format_failure["failure"]["ruff_run"] is False
    assert format_failure["failure"]["pytest_run"] is False
    assert format_failure["safe_recovery"]["test_assertion_semantics_changed"] is False
    patch_failure = _load(PATCH_FAILURE)
    assert patch_failure["failure"]["exit_code_nonzero"] is True
    assert patch_failure["failure"]["partial_edit_applied"] is False
    assert (
        patch_failure["safe_recovery"]["failed_exit_code_bypassed_or_masked"] is False
    )


def test_campaign156_attempt_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    predecessor = ledger["authoritative_predecessor"]
    assert predecessor["sha256"] == _sha(ROOT / predecessor["path"])
    assert predecessor["cumulative_historical_research_attempt_count"] == 1365
    previous = predecessor["chain_tip_sha256"]
    for entry in ledger["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign156",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == expected
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = expected
    assert len(ledger["delta_entries"]) == 2
    assert ledger["effective_entry_count"] == 9
    assert ledger["effective_prevalue_source_admission_attempt_count"] == 6
    assert ledger["effective_source_admission_deferral_count"] == 4
    assert ledger["effective_terminal_source_family_rejection_count"] == 2
    assert ledger["effective_infrastructure_failure_attempt_count"] == 3
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["cumulative_historical_research_attempt_count"] == 1367
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign156_preserves_library_orders() -> None:
    definitions = features.reconstruct_complete_definitions()
    comparisons = features.reconstruct_comparisons()
    assert len(definitions) == 157
    assert features._order_digest(definitions) == (
        "c39bb6ca969b5f469a9377a5b5ca743405cec9d8511297ed6a1c44188ef40b82"
    )
    assert len(comparisons) == 142
    assert features._order_digest(comparisons) == (
        "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )


def test_campaign156_publication_bindings_and_candidate49_boundary() -> None:
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    state = _load(STATE)
    for record in (terminal, policy, state):
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            assert _sha(ROOT / binding["path"]) == binding["sha256"]
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign156"]["terminal_result"]["sha256"] == _sha(TERMINAL)
    assert state["campaign156"]["attempt_ledger"]["sha256"] == _sha(LEDGER)
    assert state["reports"]["campaign156_terminal_report"]["sha256"] == _sha(REPORT)
    heading = "## Campaign156 信用与治理事件源准入值前终止"
    for report_key in ("current_research_report", "three_day_research_report"):
        report_binding = state["reports"][report_key]
        assert (
            report_binding["mutable_append_only_report_not_an_immutable_binding"]
            is True
        )
        assert len(report_binding["sha256_at_publication"]) == 64
        report_text = (ROOT / report_binding["path"]).read_text(encoding="utf-8")
        assert report_text.count(heading) == 1
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert len(_load(SIGNAL_LEDGER)["entries"]) == 0
    assert len(_load(EXECUTION_LEDGER)["entries"]) == 0
    assert state["candidate49"]["historical_backfill_performed"] is False
    assert state["candidate49"]["ledgers_changed"] is False
    assert state["candidate49_daily_20260815"]["accepted_local_trading_day"] is False


def test_campaign156_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (
        SCOUTING,
        AUDIT,
        FAILURE,
        FORMAT_FAILURE,
        PATCH_FAILURE,
        LEDGER,
        TERMINAL,
        POLICY,
        STATE,
    ):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at


def test_campaign156_reports_are_appended_once() -> None:
    heading = "## Campaign156 信用与治理事件源准入值前终止"
    assert "Campaign156" in REPORT.read_text(encoding="utf-8")
    for report_path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        assert report_path.read_text(encoding="utf-8").count(heading) == 1


def test_campaign156_goal_remains_active_and_campaign157_is_only_prevalue_authorized() -> (
    None
):
    state = _load(STATE)
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign156_scientific_decision_completed"] is True
    assert state["goal"]["campaign157_offline_scouting_authorized"] is True
    assert state["goal"]["campaign157_started"] is False
    assert state["goal"]["second_prospective_candidate_authorized"] is False
