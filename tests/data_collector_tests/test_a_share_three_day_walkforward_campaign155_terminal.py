from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_155_concept_scouting_20260815.json"
)
AUDIT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_155_mechanism_source_frontier_audit_20260815.json"
)
FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_155_universe_snapshot_shape_test_failure_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_155/research_attempt_ledger_v1.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_155_terminal_result_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v217_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign155_prevalue_terminal.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_155_terminal_report.md"
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


def test_campaign155_finite_catalog_stops_before_row_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert len({entry["catalog_id"] for entry in catalog}) == 6
    assert len({entry["name"] for entry in catalog}) == 6
    assert all(entry["prevalue_decision"].startswith("rejected_") for entry in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    assert scouting["schema_only_observation"]["field_values_read"] is False
    boundary = scouting["research_boundary"]
    assert boundary["current_universe_row_values_read"] is False
    assert boundary["candidate_values_computed_or_read"] is False
    assert boundary["comparator_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False


def test_campaign155_point_in_time_and_economic_state_gate_rejects_all() -> None:
    audit = _load(AUDIT)
    results = audit["proposal_gate_results"]
    assert len(results) == 6
    assert all(item["passed"] is False for item in results)
    assert audit["gate_summary"]["all_gate_passers"] == 0
    assert audit["gate_summary"]["selected_candidate_count"] == 0
    terminal = audit["terminal_decision"]
    assert terminal["formula_feature_adapter_or_model_created"] is False
    assert terminal["source_row_or_candidate_value_read"] is False
    assert terminal["comparison_or_return_value_read"] is False
    assert (
        terminal["current_universe_snapshot_reuse_for_historical_scoring_allowed"]
        is False
    )


def test_campaign155_records_schema_inspection_failure_without_masking() -> None:
    failure = _load(FAILURE)
    assert failure["exit_code_nonzero"] is True
    assert failure["exact_exit_code_not_captured"] is True
    assert failure["safe_repair"]["repaired_result"]["container_type"] == "array"
    assert failure["safe_repair"]["repaired_result"]["row_count"] == 5536
    assert failure["safe_repair"]["repaired_exit_code"] == 0
    boundary = failure["research_boundary"]
    assert boundary["universe_row_values_read"] is False
    assert boundary["failed_exit_code_bypassed_or_masked"] is False


def test_campaign155_attempt_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    predecessor = ledger["authoritative_predecessor"]
    assert predecessor["sha256"] == _sha(ROOT / predecessor["path"])
    assert predecessor["cumulative_historical_research_attempt_count"] == 1351
    previous = "0" * 64
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign155",
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
    assert len(ledger["entries"]) == 7
    assert ledger["effective_prevalue_concept_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 1
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["cumulative_historical_research_attempt_count"] == 1358
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign155_preserves_library_orders() -> None:
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


def test_campaign155_publication_bindings_and_candidate49_boundary() -> None:
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    state = _load(STATE)
    for record in (terminal, policy, state):
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            assert _sha(ROOT / binding["path"]) == binding["sha256"]
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign155"]["terminal_result"]["sha256"] == _sha(TERMINAL)
    assert state["campaign155"]["attempt_ledger"]["sha256"] == _sha(LEDGER)
    assert state["reports"]["campaign155_terminal_report"]["sha256"] == _sha(REPORT)
    for report_key in ("current_research_report", "three_day_research_report"):
        report_binding = state["reports"][report_key]
        assert (
            report_binding["mutable_append_only_report_not_an_immutable_binding"]
            is True
        )
        assert len(report_binding["sha256_at_publication"]) == 64
        report_text = (ROOT / report_binding["path"]).read_text(encoding="utf-8")
        assert (
            report_text.count("## Campaign155 当前快照与运营元数据泄漏前沿值前终止")
            == 1
        )
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


def test_campaign155_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (SCOUTING, AUDIT, FAILURE, LEDGER, TERMINAL, POLICY, STATE):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at


def test_campaign155_reports_are_appended_once() -> None:
    heading = "## Campaign155 当前快照与运营元数据泄漏前沿值前终止"
    assert "Campaign155" in REPORT.read_text(encoding="utf-8")
    for report_path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        assert report_path.read_text(encoding="utf-8").count(heading) == 1


def test_campaign155_goal_remains_active_and_campaign156_is_only_prevalue_authorized() -> (
    None
):
    state = _load(STATE)
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign155_scientific_decision_completed"] is True
    assert state["goal"]["campaign156_offline_scouting_authorized"] is True
    assert state["goal"]["campaign156_started"] is False
    assert state["goal"]["second_prospective_candidate_authorized"] is False
