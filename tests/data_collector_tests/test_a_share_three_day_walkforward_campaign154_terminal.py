from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_154_concept_scouting_20260815.json"
)
AUDIT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_154_mechanism_source_frontier_audit_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_154/research_attempt_ledger_v3.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_154_terminal_result_v3_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v216_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign154_prevalue_terminal_v3.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_154_terminal_report.md"
SW_CONTRACT = ROOT / "docs/a_share_tushare_sw_industry_breadth_data_contract.json"
SW_SNAPSHOT_MANIFEST = (
    ROOT
    / "data/metadata/rich_data/runs/20260716T114724Z_tushare_sw2021_l1_membership_92ef71fe.json"
)
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


def _ledger_entries(path: Path) -> list[dict]:
    ledger = _load(path)
    if "entries" in ledger:
        return ledger["entries"]
    predecessor = ledger["authoritative_predecessor"]
    return _ledger_entries(ROOT / predecessor["path"]) + ledger["delta_entries"]


def test_campaign154_finite_catalog_stops_before_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert len({entry["catalog_id"] for entry in catalog}) == 6
    assert len({entry["name"] for entry in catalog}) == 6
    assert all(entry["prevalue_decision"].startswith("rejected_") for entry in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    boundary = scouting["research_boundary"]
    assert boundary["membership_rows_or_column_values_read"] is False
    assert boundary["campaign154_candidate_values_computed_or_read"] is False
    assert boundary["campaign154_comparator_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False
    assert boundary["stress_2024_2025_opened"] is False


def test_campaign154_original_sw_contract_permits_only_terminal_breadth() -> None:
    contract = _load(SW_CONTRACT)
    assert contract["mechanism_identity"]["independent_factor_count"] == 1
    assert contract["factor"]["name"] == "sw1_three_session_leave_one_out_breadth"
    failed_gate_policy = contract["no_return_gates"]["failed_gate_policy"]
    assert "industry price momentum" in failed_gate_policy
    assert contract["selection_or_promotion_allowed"] is False
    snapshot = _load(SW_SNAPSHOT_MANIFEST)
    assert snapshot["factor_values_constructed"] is False
    assert snapshot["forward_return_fields_read"] is False
    assert snapshot["files"][0]["rows"] == 7803
    assert snapshot["files"][0]["sha256"] == (
        "474bbfcd7da4bb4d1a7c1f6b30e7c26e19230782ddee2769af4539cc3eab5c88"
    )


def test_campaign154_source_and_mechanism_gate_rejects_every_proposal() -> None:
    audit = _load(AUDIT)
    results = audit["proposal_gate_results"]
    assert len(results) == 6
    assert all(
        item["accepted_historical_source_and_original_contract_permits_inputs"] is False
        for item in results
    )
    assert (
        sum(item["semantically_independent_from_terminal_library"] for item in results)
        == 1
    )
    assert all(item["passed"] is False for item in results)
    assert audit["gate_summary"]["selected_candidate_count"] == 0
    assert (
        audit["terminal_decision"][
            "campaign154_source_acceptance_coverage_uniqueness_or_return_audit_run"
        ]
        is False
    )


def test_campaign154_attempt_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    predecessor = ledger["authoritative_predecessor"]
    assert predecessor["sha256"] == _sha(ROOT / predecessor["path"])
    assert predecessor["cumulative_historical_research_attempt_count"] == 1350
    previous = "0" * 64
    entries = _ledger_entries(LEDGER)
    for entry in entries:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign154",
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
    assert len(entries) == 8
    assert ledger["effective_attempt_count"] == 8
    assert ledger["effective_infrastructure_failure_attempt_count"] == 2
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["cumulative_historical_research_attempt_count"] == 1351
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign154_preserves_library_orders() -> None:
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


def test_campaign154_publication_bindings_and_candidate49_boundary() -> None:
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    state = _load(STATE)
    for record in (terminal, policy, state):
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            bound = ROOT / binding["path"]
            assert _sha(bound) == binding["sha256"]
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign154"]["terminal_result"]["sha256"] == _sha(TERMINAL)
    assert state["campaign154"]["attempt_ledger"]["sha256"] == _sha(LEDGER)
    assert state["reports"]["campaign154_terminal_report"]["sha256"] == _sha(REPORT)
    for report_key in ("current_research_report", "three_day_research_report"):
        report_binding = state["reports"][report_key]
        assert (
            report_binding["mutable_append_only_report_not_an_immutable_binding"]
            is True
        )
        assert len(report_binding["sha256_at_publication"]) == 64
        report_text = (ROOT / report_binding["path"]).read_text(encoding="utf-8")
        assert report_text.count("## Campaign154 行业成员原始合同前沿值前终止") == 1
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


def test_campaign154_records_use_reached_wall_clock_timestamps() -> None:
    for path in (SCOUTING, AUDIT, LEDGER, TERMINAL, POLICY, STATE):
        recorded_at = datetime.fromisoformat(_load(path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at


def test_campaign154_reports_are_appended_once() -> None:
    heading = "## Campaign154 行业成员原始合同前沿值前终止"
    assert "Campaign154" in REPORT.read_text(encoding="utf-8")
    for path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        assert (ROOT / path).read_text(encoding="utf-8").count(heading) == 1


def test_campaign154_goal_remains_active_and_campaign155_is_only_prevalue_authorized() -> (
    None
):
    state = _load(STATE)
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign154_scientific_decision_completed"] is True
    assert state["goal"]["campaign155_offline_scouting_authorized"] is True
    assert state["goal"]["campaign155_started"] is False
    assert state["goal"]["second_prospective_candidate_authorized"] is False
