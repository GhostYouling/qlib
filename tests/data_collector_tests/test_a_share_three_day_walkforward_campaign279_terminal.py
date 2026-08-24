from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_279_concept_scouting_20260824.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_279_prevalue_mechanism_frontier_result_20260824.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_279/research_attempt_ledger_v1.json"
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260824_campaign279_terminal.json"
)
REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_279_terminal_prevalue_report.md"
)
HANDOFF = ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign279.md"
SIGNAL = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
UNIFIED_REPORTS = (
    ROOT / "data/experiments/short_horizon/current_research_report.md",
    ROOT / "data/experiments/short_horizon/three_day_research_report.md",
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(path: str) -> Path:
    target = Path(path)
    return target if target.is_absolute() else ROOT / target


def _assert_bindings(bindings: dict) -> None:
    for binding in bindings.values():
        target = _resolve(binding["path"])
        assert target.is_file()
        assert _sha256(target) == binding["sha256"]


def _entry_hash(entry: dict) -> str:
    payload = "|".join(
        (
            "campaign279",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_catalog_freezes_seven_routes_before_targeted_inventory() -> None:
    assert _sha256(CATALOG) == (
        "608b59e4461d5c777356b0a0a477731c94fc7bb6bb7ca14ed53bf90542423419"
    )
    catalog = _load(CATALOG)
    _assert_bindings(
        {
            "authoritative_predecessor": catalog["authoritative_predecessor"],
            "historical_policy": catalog["historical_policy"],
        }
    )
    sequence = catalog["sequence_attestation"]
    assert (
        sequence["targeted_prior_definition_inventory_read_before_this_freeze"] is False
    )
    assert (
        sequence["targeted_source_frontier_inventory_read_before_this_freeze"] is False
    )
    assert sequence["provider_request_issued"] is False
    routes = catalog["concept_catalog"]
    assert [route["priority"] for route in routes] == list(range(1, 8))
    assert [route["concept_id"] for route in routes] == [
        "public_cultural_heritage_archaeological_clearance_project_state",
        "public_collective_bargaining_union_agreement_labor_dispute_state",
        "public_healthcare_reimbursement_formulary_tender_inclusion_state",
        "public_water_right_withdrawal_discharge_permit_allocation_state",
        "public_animal_health_quarantine_outbreak_culling_recovery_state",
        "public_export_control_end_use_license_entity_list_state",
        "public_product_ecolabel_energy_efficiency_registration_state",
    ]
    for route in routes:
        for field in (
            "formula",
            "direction",
            "provider",
            "source_fields",
            "availability_rule",
            "missing_zero_semantics",
        ):
            assert route[field] is None


def test_result_closes_six_overlaps_and_defers_one_source_contract() -> None:
    assert _sha256(RESULT) == (
        "3cce302ad78615cfc69d3efed199110921cd2a4ce8519f5d4a8dab2d9a0cc1db"
    )
    result = _load(RESULT)
    _assert_bindings(result["authoritative_inputs"])
    routes = result["route_results"]
    assert len(routes) == 7
    assert sum(route["economically_independent"] for route in routes) == 1
    assert all(route["source_contract_ready"] is False for route in routes)
    assert all(route["formula"] is None for route in routes)
    assert all(route["direction"] is None for route in routes)
    assert routes[1]["decision"] == (
        "deferred_source_admission_no_complete_collective_bargaining_labor_dispute_contract"
    )
    decision = result["decision"]
    assert decision["catalog_route_count"] == 7
    assert decision["economically_independent_route_count"] == 1
    assert decision["source_contract_ready_route_count"] == 0
    assert decision["selected_route_count"] == 0
    assert decision["complete_factor_definition_created"] is False
    assert decision["numeric_comparator_created"] is False
    assert decision["campaign279_terminalized"] is True


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    assert _sha256(LEDGER) == (
        "5e98cd6fda79397eefae01ace4dd5b039bf3b540806e6c1087190648b9e302db"
    )
    ledger = _load(LEDGER)
    _assert_bindings({"predecessor": ledger["authoritative_predecessor"]})
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    entries = ledger["entries"]
    assert len(entries) == 8
    for ordinal, entry in enumerate(entries, start=1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_comparator_value_read"] is False
        assert entry["return_reading_development_trial"] is False
        assert entry["complete_factor_attempt"] is False
        if ordinal == 1:
            assert entry["scientific_attempt"] is False
            assert entry["result_consumed"] is False
        else:
            assert entry["scientific_attempt"] is True
            assert entry["result_consumed"] is True
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 8
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 2851
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_state_keeps_goal_candidate49_and_credential_boundary() -> None:
    assert _sha256(STATE) == (
        "a2f272ce8b15b8a23c9ee35fa779242001317ec98655651701a52a6a8fba1ca8"
    )
    state = _load(STATE)
    immutable_bindings = {
        key: value
        for key, value in state["authoritative_inputs"].items()
        if key not in {"current_unified_report", "three_day_unified_report"}
    }
    _assert_bindings(immutable_bindings)
    assert state["active_data_root"] == "/Volumes/DIsk/Disk-Coding/qlib/data"
    assert state["goal"]["status"] == "active"
    assert state["goal"]["current_campaign"] == 279
    assert "Campaign280" in state["goal"]["next_safe_work"]
    assert state["credential_presence_only"] == {
        "env_is_regular_file": True,
        "env_mode_octal": "0600",
        "git_ignored": True,
        "nonempty_tushare_token_assignment_count": 1,
        "credential_value_or_digest_read": False,
    }
    candidate49 = state["candidate49"]
    assert candidate49["same_session_retry_allowed"] is False
    assert candidate49["campaign279_plan_or_run_executed"] is False
    assert candidate49["historical_backfill_performed"] is False
    assert _sha256(SIGNAL) == candidate49["signal_ledger_sha256"]
    assert _sha256(EXECUTION) == candidate49["execution_ledger_sha256"]
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []


def test_no_value_stress_or_current_use_boundary_is_closed() -> None:
    for artifact in (_load(RESULT), _load(LEDGER), _load(STATE)):
        boundary = artifact["research_boundary"]
        for key, value in boundary.items():
            if key == "repository_metadata_and_prior_terminal_history_read":
                assert value is True
            else:
                assert value is False


def test_reports_and_handoff_publish_one_terminal_result() -> None:
    report = REPORT.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    assert "7 条有限路线" in report
    assert "集体协商/工会协议/劳资争议虽经济独立" in handoff
    assert "持续目标保持 `active`" in handoff
    assert "不构成投资建议" in report
    title = "## Campaign279：既有机制重叠与集体协商来源缺口值前终止（2026-08-24）"
    for path in UNIFIED_REPORTS:
        text = path.read_text(encoding="utf-8")
        assert text.count(title) == 1
        section = text.split(title, maxsplit=1)[1]
        assert "累计历史尝试 2,851" in section
        assert "Candidate49 同日来源失败继续封口且账本 0/0" in section
        assert "Campaign280" in section


def test_library_and_historical_boundaries_remain_frozen() -> None:
    state = _load(STATE)
    library = state["library_state"]
    assert library["changed_by_campaign279"] is False
    assert library["complete_factor_definition_count"] == 162
    assert library["eligible_numeric_comparator_count"] == 143
    assert state["scientific_state"]["development_trial_count"] == 0
    assert state["scientific_state"]["stress_trial_count_2024_2025"] == 0
    assert state["scientific_state"]["predictive_claim_created"] is False
    assert state["candidate49"]["sole_active_prospective_candidate"] is True
