from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_280_concept_scouting_20260824.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_280_prevalue_mechanism_frontier_result_20260824.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_280/research_attempt_ledger_v2.json"
)
LEDGER_APPEND = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_280/research_attempt_ledger_v3.json"
)
LEDGER_APPEND_2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_280/research_attempt_ledger_v4.json"
)
LEDGER_APPEND_3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_280/research_attempt_ledger_v5.json"
)
CORRECTION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_280_ledger_hash_correction_20260824.json"
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260824_campaign280_terminal.json"
)
REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_280_terminal_prevalue_report.md"
)
HANDOFF = ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign280.md"
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
            "campaign280",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_catalog_freezes_seven_routes_before_targeted_inventory() -> None:
    assert _sha256(CATALOG) == (
        "a4afab496b6ea5693249bbd70fe33794e853b8ace317714a89c7c32f3bfdfff5"
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
        "public_indigenous_community_consultation_consent_benefit_sharing_project_state",
        "public_disability_accessibility_compliance_remediation_state",
        "public_space_launch_payload_license_mission_anomaly_state",
        "public_seed_variety_registration_plant_breeder_right_state",
        "public_fisheries_catch_quota_vessel_license_traceability_state",
        "public_telecom_interconnection_number_portability_quality_state",
        "public_biodiversity_habitat_offset_conservation_obligation_state",
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
        "6f510ec31704667f76cc1ae43070a49808e6d2e795d223b4b005e292ada3fe3c"
    )
    result = _load(RESULT)
    _assert_bindings(result["authoritative_inputs"])
    routes = result["route_results"]
    assert len(routes) == 7
    assert sum(route["economically_independent"] for route in routes) == 1
    assert all(route["source_contract_ready"] is False for route in routes)
    assert all(route["formula"] is None for route in routes)
    assert all(route["direction"] is None for route in routes)
    assert routes[0]["decision"] == (
        "deferred_source_admission_no_complete_indigenous_community_consent_contract"
    )
    decision = result["decision"]
    assert decision["catalog_route_count"] == 7
    assert decision["economically_independent_route_count"] == 1
    assert decision["source_contract_ready_route_count"] == 0
    assert decision["selected_route_count"] == 0
    assert decision["complete_factor_definition_created"] is False
    assert decision["numeric_comparator_created"] is False
    assert decision["campaign280_terminalized"] is True


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    assert _sha256(LEDGER) == (
        "097b28c1c0c2a8aed72e24657242188da03b79594b0c3d300b39f377810e5ffa"
    )
    ledger = _load(LEDGER)
    _assert_bindings({"predecessor": ledger["authoritative_predecessor"]})
    _assert_bindings({"invalid_v1": ledger["supersedes_invalid_ledger"]})
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    entries = ledger["entries"]
    assert len(entries) == 9
    for ordinal, entry in enumerate(entries, start=1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_comparator_value_read"] is False
        assert entry["return_reading_development_trial"] is False
        assert entry["complete_factor_attempt"] is False
        if ordinal in {1, 9}:
            assert entry["scientific_attempt"] is False
            assert entry["result_consumed"] is False
        else:
            assert entry["scientific_attempt"] is True
            assert entry["result_consumed"] is True
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 9
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 2
    assert ledger["cumulative_historical_research_attempt_count"] == 2860
    assert ledger["cumulative_return_reading_development_trial_count"] == 315
    correction = _load(CORRECTION)
    _assert_bindings(correction["immutable_failed_evidence"])
    _assert_bindings(correction["effective_evidence"])
    assert correction["repair"]["v1_rewritten_or_deleted"] is False
    assert correction["repair"]["validation_failure_appended_as_ninth_attempt"]
    ledger_append = _load(LEDGER_APPEND)
    _assert_bindings({"v2": ledger_append["authoritative_predecessor"]})
    append_entries = ledger_append["entries"]
    assert len(append_entries) == 1
    append_entry = append_entries[0]
    assert append_entry["ordinal"] == 10
    assert append_entry["previous_entry_sha256"] == ledger["chain_tip_sha256"]
    assert append_entry["entry_sha256"] == _entry_hash(append_entry)
    assert append_entry["scientific_attempt"] is False
    assert append_entry["candidate_or_comparator_value_read"] is False
    assert append_entry["return_reading_development_trial"] is False
    assert ledger_append["effective_entry_count"] == 10
    assert ledger_append["effective_infrastructure_failure_attempt_count"] == 3
    assert ledger_append["cumulative_historical_research_attempt_count"] == 2861
    assert ledger_append["chain_tip_sha256"] == append_entry["entry_sha256"]
    ledger_append_2 = _load(LEDGER_APPEND_2)
    _assert_bindings({"v3": ledger_append_2["authoritative_predecessor"]})
    append_entries_2 = ledger_append_2["entries"]
    assert len(append_entries_2) == 1
    append_entry_2 = append_entries_2[0]
    assert append_entry_2["ordinal"] == 11
    assert append_entry_2["previous_entry_sha256"] == ledger_append["chain_tip_sha256"]
    assert append_entry_2["entry_sha256"] == _entry_hash(append_entry_2)
    assert append_entry_2["scientific_attempt"] is False
    assert append_entry_2["candidate_or_comparator_value_read"] is False
    assert append_entry_2["return_reading_development_trial"] is False
    assert ledger_append_2["effective_entry_count"] == 11
    assert ledger_append_2["effective_infrastructure_failure_attempt_count"] == 4
    assert ledger_append_2["cumulative_historical_research_attempt_count"] == 2862
    assert ledger_append_2["chain_tip_sha256"] == append_entry_2["entry_sha256"]
    ledger_append_3 = _load(LEDGER_APPEND_3)
    _assert_bindings({"v4": ledger_append_3["authoritative_predecessor"]})
    append_entries_3 = ledger_append_3["entries"]
    assert len(append_entries_3) == 1
    append_entry_3 = append_entries_3[0]
    assert append_entry_3["ordinal"] == 12
    assert (
        append_entry_3["previous_entry_sha256"] == ledger_append_2["chain_tip_sha256"]
    )
    assert append_entry_3["entry_sha256"] == _entry_hash(append_entry_3)
    assert append_entry_3["scientific_attempt"] is False
    assert append_entry_3["candidate_or_comparator_value_read"] is False
    assert append_entry_3["return_reading_development_trial"] is False
    assert ledger_append_3["effective_entry_count"] == 12
    assert ledger_append_3["effective_infrastructure_failure_attempt_count"] == 5
    assert ledger_append_3["cumulative_historical_research_attempt_count"] == 2863
    assert ledger_append_3["chain_tip_sha256"] == append_entry_3["entry_sha256"]


def test_state_keeps_goal_candidate49_and_credential_boundary() -> None:
    assert _sha256(STATE) == (
        "df7e404aba8cbd825756fd76a2a0546642be5f9b0191d9cfaf14b40a41e16a5c"
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
    assert state["goal"]["current_campaign"] == 280
    assert "Campaign281" in state["goal"]["next_safe_work"]
    assert state["credential_presence_only"] == {
        "env_is_regular_file": True,
        "env_mode_octal": "0600",
        "git_ignored": True,
        "nonempty_tushare_token_assignment_count": 1,
        "credential_value_or_digest_read": False,
    }
    candidate49 = state["candidate49"]
    assert candidate49["same_session_retry_allowed"] is False
    assert candidate49["campaign280_plan_or_run_executed"] is False
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
    assert "社区/原住民协商、同意与利益分享虽经济独立" in handoff
    assert "持续目标保持 `active`" in handoff
    assert "不构成投资建议" in report
    title = "## Campaign280：既有机制重叠与社区同意来源缺口值前终止（2026-08-24）"
    for path in UNIFIED_REPORTS:
        text = path.read_text(encoding="utf-8")
        assert text.count(title) == 1
        section = text.split(title, maxsplit=1)[1]
        assert "累计历史尝试 2,863" in section
        assert "Candidate49 同日来源失败继续封口且账本 0/0" in section
        assert "Campaign281" in section


def test_library_and_historical_boundaries_remain_frozen() -> None:
    state = _load(STATE)
    library = state["library_state"]
    assert library["changed_by_campaign280"] is False
    assert library["complete_factor_definition_count"] == 162
    assert library["eligible_numeric_comparator_count"] == 143
    assert state["scientific_state"]["development_trial_count"] == 0
    assert state["scientific_state"]["stress_trial_count_2024_2025"] == 0
    assert state["scientific_state"]["predictive_claim_created"] is False
    assert state["candidate49"]["sole_active_prospective_candidate"] is True
