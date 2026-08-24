from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_281_concept_scouting_20260824.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_281_prevalue_mechanism_frontier_result_20260824.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_281/research_attempt_ledger_v1.json"
)
INVALID_LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_281/research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_281/research_attempt_ledger_v3.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_281/research_attempt_ledger_v4.json"
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260824_campaign281_terminal.json"
)
REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_281_terminal_prevalue_report.md"
)
HANDOFF = ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign281.md"
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


def _entry_hash(entry: dict, previous: str) -> str:
    payload = "|".join(
        (
            "campaign281",
            entry["attempt_id"],
            previous,
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_catalog_freezes_seven_routes_before_targeted_inventory() -> None:
    assert _sha256(CATALOG) == (
        "deff0f8f9cbccb73b150714ebfbe93d6ba8d0252d0b821ed3151e6ea07b68314"
    )
    catalog = _load(CATALOG)
    _assert_bindings(
        {
            "authoritative_predecessor": catalog["authoritative_predecessor"],
            "historical_policy": catalog["historical_policy"],
        }
    )
    sequence = catalog["sequence_attestation"]
    assert not sequence["targeted_prior_definition_inventory_read_before_this_freeze"]
    assert not sequence["targeted_source_frontier_inventory_read_before_this_freeze"]
    assert not sequence["provider_request_issued"]
    routes = catalog["concept_catalog"]
    assert [route["priority"] for route in routes] == list(range(1, 8))
    assert [route["concept_id"] for route in routes] == [
        "public_land_expropriation_resettlement_compensation_project_state",
        "public_customs_authorized_economic_operator_certification_state",
        "public_emergency_medical_facility_designation_mobilization_state",
        "public_maritime_salvage_wreck_removal_towage_award_state",
        "public_procurement_debarment_bid_protest_reinstatement_state",
        "public_geological_hazard_monitoring_evacuation_remediation_state",
        "public_radio_spectrum_interference_coordination_remediation_state",
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


def test_result_closes_all_routes_before_formula_direction_or_values() -> None:
    assert _sha256(RESULT) == (
        "92707d64b861dbd16ee410ec206d5bc3e2a5c387823779ad0f5f8b396bd0e85b"
    )
    result = _load(RESULT)
    _assert_bindings(result["authoritative_inputs"])
    routes = result["route_results"]
    assert len(routes) == 7
    assert sum(route["economically_independent"] for route in routes) == 0
    assert all(route["source_contract_ready"] is False for route in routes)
    assert all(route["formula"] is None for route in routes)
    assert all(route["direction"] is None for route in routes)
    assert all(route["source_fields"] is None for route in routes)
    decision = result["decision"]
    assert decision["catalog_route_count"] == 7
    assert decision["economically_independent_route_count"] == 0
    assert decision["source_contract_ready_route_count"] == 0
    assert decision["selected_route_count"] == 0
    assert decision["complete_factor_definition_created"] is False
    assert decision["numeric_comparator_created"] is False
    assert decision["campaign281_terminalized"] is True


def test_effective_attempt_chain_preserves_invalid_v2_and_exact_accounting() -> None:
    assert _sha256(LEDGER_V1) == (
        "da853005d10e21986963b4f7dc6621671506b72ca2bdf7c8485b87c77d6c622c"
    )
    assert _sha256(INVALID_LEDGER_V2) == (
        "c7ff03309eb4581d5ee0285cbacf82a9b21e8e21034d6d5a83ea28085e300440"
    )
    assert _sha256(LEDGER_V3) == (
        "2cb9bf52e86c6cc4023caf1e7983507a0cbb03dd9558893a629e062100399220"
    )
    assert _sha256(LEDGER) == (
        "4a0f9ff0aa8eb3038d96b84a3b5acb58e4fc781a5a1a9b72f1596d266d49be9a"
    )
    ledger_v1 = _load(LEDGER_V1)
    previous = ledger_v1["authoritative_predecessor"]["chain_tip_sha256"]
    for ordinal, entry in enumerate(ledger_v1["entries"], start=1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry, previous)
        assert entry["scientific_attempt"] is True
        assert entry["result_consumed"] is True
        previous = entry["entry_sha256"]
    assert previous == ledger_v1["chain_tip_sha256"]

    invalid = _load(INVALID_LEDGER_V2)
    invalid_entry = invalid["entries"][0]
    assert invalid_entry["entry_sha256"] != _entry_hash(
        invalid_entry, invalid_entry["previous_entry_sha256"]
    )

    ledger_v3 = _load(LEDGER_V3)
    _assert_bindings({"predecessor": ledger_v3["authoritative_predecessor"]})
    _assert_bindings({"invalid_v2": ledger_v3["supersedes_invalid_ledger"]})
    previous = ledger_v3["authoritative_predecessor"]["chain_tip_sha256"]
    for ordinal, entry in enumerate(ledger_v3["entries"], start=8):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry, previous)
        assert entry["scientific_attempt"] is False
        assert entry["result_consumed"] is False
        assert entry["candidate_or_comparator_value_read"] is False
        assert entry["return_reading_development_trial"] is False
        previous = entry["entry_sha256"]
    assert previous == ledger_v3["chain_tip_sha256"]
    assert ledger_v3["effective_entry_count"] == 9

    ledger = _load(LEDGER)
    _assert_bindings({"predecessor": ledger["authoritative_predecessor"]})
    assert len(ledger["entries"]) == 1
    entry = ledger["entries"][0]
    assert entry["ordinal"] == 10
    assert entry["previous_entry_sha256"] == ledger_v3["chain_tip_sha256"]
    assert entry["entry_sha256"] == _entry_hash(entry, entry["previous_entry_sha256"])
    assert entry["scientific_attempt"] is False
    assert entry["result_consumed"] is False
    assert ledger["chain_tip_sha256"] == entry["entry_sha256"]
    assert ledger["effective_entry_count"] == 10
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 3
    assert ledger["effective_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2874
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_state_keeps_goal_candidate49_and_credential_boundary() -> None:
    state = _load(STATE)
    _assert_bindings(state["authoritative_inputs"])
    assert state["active_data_root"] == "/Volumes/DIsk/Disk-Coding/qlib/data"
    assert state["goal"]["status"] == "active"
    assert state["goal"]["current_campaign"] == 281
    assert "Campaign282" in state["goal"]["next_safe_work"]
    assert state["credential_presence_only"] == {
        "env_is_regular_file": True,
        "env_mode_octal": "0600",
        "git_ignored": True,
        "nonempty_tushare_token_assignment_count": 1,
        "credential_value_or_digest_read": False,
    }
    candidate49 = state["candidate49"]
    assert candidate49["same_session_retry_allowed"] is False
    assert candidate49["campaign281_plan_or_run_executed"] is False
    assert candidate49["historical_backfill_performed"] is False
    assert _sha256(SIGNAL) == candidate49["signal_ledger_sha256"]
    assert _sha256(EXECUTION) == candidate49["execution_ledger_sha256"]
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []


def test_no_value_stress_or_current_use_boundary_is_closed() -> None:
    for artifact in (_load(RESULT), _load(LEDGER), _load(STATE)):
        boundary = artifact["research_boundary"]
        assert boundary["repository_metadata_and_prior_terminal_history_read"] is True
        for key in (
            "provider_or_web_request_issued",
            "provider_response_or_source_row_read",
            "provider_credential_value_or_digest_read",
            "candidate_or_comparator_value_read",
            "historical_daily_price_or_forward_return_value_read",
            "stress_2024_2025_opened",
            "candidate49_plan_or_run_executed_by_campaign281",
            "candidate49_historical_backfill_performed",
            "candidate49_ledgers_changed",
            "second_prospective_candidate_created",
            "current_scoring_selection_sizing_positions_or_orders_performed",
            "investment_advice",
        ):
            assert boundary[key] is False


def test_reports_and_handoff_publish_one_terminal_result() -> None:
    report = REPORT.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    assert "7 条有限路线" in report
    assert "全部与既有不可变终止机制重叠" in handoff
    assert "累计历史尝试 2,874" in handoff
    assert "持续目标保持 `active`" in handoff
    assert "不构成投资建议" in report
    title = "## Campaign281：七条公共外部状态路线全部机制重叠值前终止（2026-08-24）"
    for path in UNIFIED_REPORTS:
        text = path.read_text(encoding="utf-8")
        assert text.count(title) == 1
        section = text.split(title, maxsplit=1)[1]
        assert "累计历史尝试 2,874" in section
        assert "Candidate49 同日来源失败继续封口且账本 0/0" in section
        assert "Campaign282" in section


def test_library_and_historical_boundaries_remain_frozen() -> None:
    state = _load(STATE)
    library = state["library_state"]
    assert library["changed_by_campaign281"] is False
    assert library["complete_factor_definition_count"] == 162
    assert library["eligible_numeric_comparator_count"] == 143
    assert state["scientific_state"]["development_trial_count"] == 0
    assert state["scientific_state"]["stress_trial_count_2024_2025"] == 0
    assert state["scientific_state"]["predictive_claim_created"] is False
    assert state["candidate49"]["sole_active_prospective_candidate"] is True
