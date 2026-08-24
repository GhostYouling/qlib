from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_275_concept_scouting_20260824.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_275_prevalue_mechanism_frontier_result_20260824.json"
)
LEDGERS = tuple(
    ROOT
    / f"data/experiments/short_horizon/historical_walkforward/campaign_275/research_attempt_ledger_v{version}.json"
    for version in (1, 2, 3, 4, 5, 6, 7)
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260824_campaign275_terminal.json"
)
REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_275_terminal_prevalue_report.md"
)
HANDOFF = ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign275.md"
HANDOFF_V2 = ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign275_v2.md"
VALIDATION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_275_terminal_validation_20260824.json"
)
FINAL_STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260824_campaign275_final_validated.json"
)
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
            "campaign275",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_catalog_freezes_seven_priority_routes_before_targeted_inventory() -> None:
    assert _sha256(CATALOG) == (
        "da8e67fe06026fa3b721dc0c104fa17ba0b9e708fc9320b4ccdfa59c887c81c7"
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
        "public_recruitment_vacancy_skill_demand_state",
        "public_digital_product_release_withdrawal_state",
        "public_customs_shipment_network_activity_state",
        "public_utility_consumption_connection_state",
        "public_insurance_claim_loss_control_state",
        "public_warehouse_receipt_inventory_pledge_state",
        "public_domain_certificate_operational_surface_state",
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


def test_result_closes_all_routes_before_formula_source_rows_or_values() -> None:
    assert _sha256(RESULT) == (
        "0e67d896394155f73c4ebef6c8ea7ea42bb78c37f83a70976b0ee43c3a450244"
    )
    result = _load(RESULT)
    _assert_bindings(result["authoritative_inputs"])
    routes = result["route_results"]
    assert len(routes) == 7
    assert sum(route["economically_independent"] for route in routes) == 2
    assert all(route["source_contract_ready"] is False for route in routes)
    for route in routes:
        assert route["formula"] is None
        assert route["direction"] is None
        assert route["source_fields"] is None
    decision = result["decision"]
    assert decision["catalog_route_count"] == 7
    assert decision["source_contract_ready_route_count"] == 0
    assert decision["selected_route_count"] == 0
    assert decision["complete_factor_definition_created"] is False
    assert decision["numeric_comparator_created"] is False
    assert decision["campaign275_terminalized"] is True
    assert result["library_state"]["complete_factor_definition_count"] == 162
    assert result["library_state"]["eligible_numeric_comparator_count"] == 143


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    assert tuple(_sha256(path) for path in LEDGERS) == (
        "781a62d2608121b507788d3ea833e8cc53349ef1c46238fee8c46a90440f878d",
        "67967ac981eacc0fc57c3d4f9dd3aa5c02fd1102ec70ad74bbf22ea2774c861a",
        "87fd6a57431fa08dadac3c92d0eba742e6569bd618a42bbc48d5c2ff02d649b2",
        "f8608fbbcfca1e7eb48573e4bcb7d50b2ef0f948cc21f481a9c7212b105c9b12",
        "4fa5782cd6cbf92e4b2622d364c952b6f918a840f7f91958c42fec1792b396a6",
        "b964a28e631a34ef317c1fdd113ecd9ba02ec117b292ac5d0e71ca83d5a0b8b3",
        "9a80a5f1227cb4c13a630ed870b73b11ca0207be50e838429e26eeabf3b7a685",
    )
    ledgers = [_load(path) for path in LEDGERS]
    entries = [entry for ledger in ledgers for entry in ledger["entries"]]
    previous = ledgers[0]["authoritative_predecessor"]["chain_tip_sha256"]
    assert (
        previous == "537db758e85a33093db1a0a5e3473de45c470d723e20d3703a3f8e2865c0972f"
    )
    assert len(entries) == ledgers[-1]["effective_entry_count"] == 16
    for ordinal, entry in enumerate(entries, 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_comparator_value_read"] is False
        assert entry["return_reading_development_trial"] is False
        previous = entry["entry_sha256"]
    ledger = ledgers[-1]
    assert previous == ledger["chain_tip_sha256"]
    assert sum(entry["scientific_attempt"] for entry in entries) == 7
    assert sum(not entry["scientific_attempt"] for entry in entries) == 9
    assert sum(entry["result_consumed"] for entry in entries) == 7
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 9
    assert ledger["effective_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2809
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_state_keeps_goal_candidate49_and_credentials_boundary_unchanged() -> None:
    assert _sha256(STATE) == (
        "bd6ad7c001b99347b8c4236c27597e64e1f5da3e8cf7c14fe1b3383cbfaa1df4"
    )
    state = _load(STATE)
    _assert_bindings(
        {
            key: binding
            for key, binding in state["authoritative_inputs"].items()
            if key not in {"current_unified_report", "three_day_unified_report"}
        }
    )
    assert state["goal"]["status"] == "active"
    assert state["goal"]["continuous_iteration_confirmed"] is True
    assert state["goal"]["current_campaign"] == 275
    assert "Campaign276" in state["goal"]["next_safe_work"]
    assert state["credential_presence_only"] == {
        "env_is_regular_file": True,
        "env_mode_octal": "0600",
        "git_ignored": True,
        "nonempty_tushare_token_assignment_count": 1,
        "credential_value_or_digest_read": False,
    }
    candidate49 = state["candidate49"]
    assert candidate49["same_session_retry_allowed"] is False
    assert candidate49["campaign275_plan_or_run_executed"] is False
    assert candidate49["historical_backfill_performed"] is False
    assert _sha256(SIGNAL) == candidate49["signal_ledger_sha256"]
    assert _sha256(EXECUTION) == candidate49["execution_ledger_sha256"]
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []


def test_no_provider_value_stress_or_current_use_boundary_is_closed() -> None:
    artifacts = [_load(RESULT), _load(STATE)]
    artifacts.extend(_load(path) for path in LEDGERS)
    for artifact in artifacts:
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
    assert "持续目标保持 `active`" in handoff
    assert "不构成投资建议" in report
    title = "## Campaign275：外部经营活动与数字足迹路线值前终止（2026-08-24）"
    for path in UNIFIED_REPORTS:
        text = path.read_text(encoding="utf-8")
        assert text.count(title) == 1
        section = text.split(title, maxsplit=1)[1]
        assert "累计历史尝试 2,804" in section
        assert "Candidate49 同日来源失败继续封口且账本 0/0" in section
        assert "本结果不构成投资建议" in section
        assert "Campaign276" in section


def test_library_and_next_campaign_boundary_remain_frozen() -> None:
    state = _load(STATE)
    library = state["library_state"]
    assert library["changed_by_campaign275"] is False
    assert library["complete_factor_definition_count"] == 162
    assert library["eligible_numeric_comparator_count"] == 143
    assert state["scientific_state"]["development_trial_count"] == 0
    assert state["scientific_state"]["stress_trial_count_2024_2025"] == 0
    assert state["candidate49"]["sole_active_prospective_candidate"] is True


def test_optional_validation_and_final_state_bind_current_artifacts() -> None:
    if VALIDATION.exists():
        validation = _load(VALIDATION)
        _assert_bindings(validation["validated_artifacts"])
        assert validation["focused_test_result"]["passed"] == 8
        assert validation["json_validation"]["invalid_count"] == 0
        assert validation["cross_stage_result"]["failed"] == 0
    if FINAL_STATE.exists():
        final_state = _load(FINAL_STATE)
        _assert_bindings(final_state["authoritative_inputs"])
        assert final_state["goal"]["status"] == "active"
        assert final_state["goal"]["current_campaign"] == 275
        assert "Campaign276" in final_state["goal"]["next_safe_work"]
        assert (
            _sha256(HANDOFF_V2)
            == final_state["authoritative_inputs"]["campaign275_handoff_v2"]["sha256"]
        )
