from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_157_cross_asset_source_scouting_20260815.json"
)
AUDIT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_157_cross_asset_source_admission_audit_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_157/research_attempt_ledger_v1.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_157_terminal_result_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v220_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign157_prevalue_terminal.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_157_terminal_report.md"
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


def test_campaign157_finite_catalog_stops_before_cross_asset_rows() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_source_catalog"]
    assert len(catalog) == 6
    assert len({entry["catalog_id"] for entry in catalog}) == 6
    assert len({entry["name"] for entry in catalog}) == 6
    decisions = [entry["prevalue_decision"] for entry in catalog]
    assert sum(item.startswith("deferred_") for item in decisions) == 4
    assert sum(item.startswith("rejected_") for item in decisions) == 2
    assert scouting["selection"]["selected_candidate_count"] == 0
    assert scouting["selection"]["source_admission_deferrals_not_factor_failures"] == 4
    boundary = scouting["research_boundary"]
    assert boundary["source_row_or_response_values_read"] is False
    assert boundary["candidate_values_computed_or_read"] is False
    assert boundary["comparator_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False


def test_campaign157_source_gate_distinguishes_deferral_from_recombination() -> None:
    audit = _load(AUDIT)
    results = audit["proposal_gate_results"]
    assert len(results) == 6
    assert all(item["passed"] is False for item in results)
    classifications = [item["classification"] for item in results]
    assert classifications.count("source_admission_deferred_not_factor_failure") == 4
    assert classifications.count("terminal_source_recombination_rejection") == 1
    assert (
        classifications.count(
            "terminal_model_and_market_relative_recombination_rejection"
        )
        == 1
    )
    assert audit["gate_summary"]["all_gate_passers"] == 0
    assert audit["gate_summary"]["selected_candidate_count"] == 0
    interpretation = audit["scientific_interpretation"]
    assert interpretation["deferred_concepts_tested_for_predictive_value"] is False
    assert interpretation["deferred_concepts_declared_ineffective"] is False


def test_campaign157_terminal_result_preserves_source_deferral_semantics() -> None:
    terminal = _load(TERMINAL)
    classification = terminal["terminal_classification"]
    assert classification["terminal"] is True
    assert classification["selected_candidate_count"] == 0
    assert classification["source_admission_deferrals_not_factor_failures"] == 4
    assert classification["terminal_or_structural_recombination_rejections"] == 2
    assert classification["formula_feature_adapter_or_model_created"] is False
    assert (
        classification[
            "source_row_endpoint_response_candidate_comparator_daily_price_or_forward_return_values_read"
        ]
        is False
    )
    assert (
        classification["unverified_endpoint_field_mapping_or_schema_assumed"] is False
    )


def test_campaign157_attempt_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    predecessor = ledger["authoritative_predecessor"]
    assert predecessor["sha256"] == _sha(ROOT / predecessor["path"])
    assert predecessor["cumulative_historical_research_attempt_count"] == 1367
    previous = "0" * 64
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign157",
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
    assert len(ledger["entries"]) == 6
    assert ledger["effective_prevalue_source_admission_attempt_count"] == 6
    assert ledger["effective_source_admission_deferral_count"] == 4
    assert ledger["effective_terminal_or_structural_recombination_rejection_count"] == 2
    assert ledger["effective_infrastructure_failure_attempt_count"] == 0
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["cumulative_historical_research_attempt_count"] == 1373
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign157_preserves_library_orders() -> None:
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


def test_campaign157_publication_bindings_and_candidate49_boundary() -> None:
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    state = _load(STATE)
    for record in (terminal, policy, state):
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            assert _sha(ROOT / binding["path"]) == binding["sha256"]
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign157"]["terminal_result"]["sha256"] == _sha(TERMINAL)
    assert state["campaign157"]["attempt_ledger"]["sha256"] == _sha(LEDGER)
    assert state["reports"]["campaign157_terminal_report"]["sha256"] == _sha(REPORT)
    heading = "## Campaign157 跨资产来源准入值前终止"
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


def test_campaign157_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (SCOUTING, AUDIT, LEDGER, TERMINAL, POLICY, STATE):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at


def test_campaign157_reports_are_appended_once() -> None:
    heading = "## Campaign157 跨资产来源准入值前终止"
    assert "Campaign157" in REPORT.read_text(encoding="utf-8")
    for report_path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        assert report_path.read_text(encoding="utf-8").count(heading) == 1


def test_campaign157_goal_remains_active_and_campaign158_is_only_prevalue_authorized() -> (
    None
):
    state = _load(STATE)
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign157_scientific_decision_completed"] is True
    assert state["goal"]["campaign158_offline_scouting_authorized"] is True
    assert state["goal"]["campaign158_started"] is False
    assert state["goal"]["second_prospective_candidate_authorized"] is False
