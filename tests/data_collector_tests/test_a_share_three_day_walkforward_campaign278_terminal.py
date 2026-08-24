from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_278_concept_scouting_20260824.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_278_prevalue_mechanism_frontier_result_20260824.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_278/research_attempt_ledger_v1.json"
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260824_campaign278_terminal.json"
)
REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_278_terminal_prevalue_report.md"
)
HANDOFF = ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign278.md"
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
            "campaign278",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_catalog_freezes_seven_routes_before_targeted_inventory() -> None:
    assert _sha256(CATALOG) == (
        "09548b8ea019c929ed33f71292c4475dfc177c52ab5c16882d55d13b98505753"
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
        "public_disaster_relief_business_interruption_recovery_state",
        "public_food_sanitation_grade_inspection_closure_state",
        "public_trade_quota_import_export_license_allocation_state",
        "public_carbon_allowance_credit_issuance_transfer_retirement_state",
        "public_academic_research_collaboration_publication_state",
        "public_spectrum_numbering_route_slot_capacity_allocation_state",
        "public_corporate_charitable_donation_social_relief_state",
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
        "7816ee4a3c26625995bc46a1dd3448e0de7ef5790395ec912bbace497fb0a738"
    )
    result = _load(RESULT)
    _assert_bindings(result["authoritative_inputs"])
    routes = result["route_results"]
    assert len(routes) == 7
    assert sum(route["economically_independent"] for route in routes) == 1
    assert all(route["source_contract_ready"] is False for route in routes)
    assert all(route["formula"] is None for route in routes)
    assert all(route["direction"] is None for route in routes)
    assert routes[-1]["decision"] == (
        "deferred_source_admission_no_complete_corporate_charity_relief_contract"
    )
    decision = result["decision"]
    assert decision["catalog_route_count"] == 7
    assert decision["economically_independent_route_count"] == 1
    assert decision["source_contract_ready_route_count"] == 0
    assert decision["selected_route_count"] == 0
    assert decision["complete_factor_definition_created"] is False
    assert decision["numeric_comparator_created"] is False
    assert decision["campaign278_terminalized"] is True


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    assert _sha256(LEDGER) == (
        "48619fd26b12a78df6d431655738b8b96412d05166790d5df587ff30d2b4364b"
    )
    ledger = _load(LEDGER)
    _assert_bindings({"predecessor": ledger["authoritative_predecessor"]})
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    entries = ledger["entries"]
    assert len(entries) == 16
    for ordinal, entry in enumerate(entries, start=1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_comparator_value_read"] is False
        assert entry["return_reading_development_trial"] is False
        assert entry["complete_factor_attempt"] is False
        if ordinal <= 9:
            assert entry["scientific_attempt"] is False
            assert entry["result_consumed"] is False
        else:
            assert entry["scientific_attempt"] is True
            assert entry["result_consumed"] is True
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 16
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 9
    assert ledger["cumulative_historical_research_attempt_count"] == 2843
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_state_keeps_goal_candidate49_and_credential_boundary() -> None:
    assert _sha256(STATE) == (
        "83f6f43f026e4bdd57c6651c0ec3e46bdd3aad94d9a670dbe029f275f2e23ef5"
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
    assert state["goal"]["current_campaign"] == 278
    assert "Campaign279" in state["goal"]["next_safe_work"]
    assert state["credential_presence_only"] == {
        "env_is_regular_file": True,
        "env_mode_octal": "0600",
        "git_ignored": True,
        "nonempty_tushare_token_assignment_count": 1,
        "credential_value_or_digest_read": False,
    }
    candidate49 = state["candidate49"]
    assert candidate49["same_session_retry_allowed"] is False
    assert candidate49["campaign278_plan_or_run_executed"] is False
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
    assert "企业慈善/社会救助虽经济独立" in handoff
    assert "持续目标保持 `active`" in handoff
    assert "不构成投资建议" in report
    title = "## Campaign278：既有机制重叠与慈善来源缺口值前终止（2026-08-24）"
    for path in UNIFIED_REPORTS:
        text = path.read_text(encoding="utf-8")
        assert text.count(title) == 1
        section = text.split(title, maxsplit=1)[1]
        assert "累计历史尝试 2,843" in section
        assert "Candidate49 同日来源失败继续封口且账本 0/0" in section
        assert "Campaign279" in section


def test_library_and_historical_boundaries_remain_frozen() -> None:
    state = _load(STATE)
    library = state["library_state"]
    assert library["changed_by_campaign278"] is False
    assert library["complete_factor_definition_count"] == 162
    assert library["eligible_numeric_comparator_count"] == 143
    assert state["scientific_state"]["development_trial_count"] == 0
    assert state["scientific_state"]["stress_trial_count_2024_2025"] == 0
    assert state["scientific_state"]["predictive_claim_created"] is False
    assert state["candidate49"]["sole_active_prospective_candidate"] is True
