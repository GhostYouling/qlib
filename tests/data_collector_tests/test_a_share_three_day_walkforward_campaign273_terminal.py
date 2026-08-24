from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_273_concept_scouting_20260824.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_273_prevalue_mechanism_frontier_result_20260824.json"
)
LEDGERS = tuple(
    ROOT
    / f"data/experiments/short_horizon/historical_walkforward/campaign_273/research_attempt_ledger_v{version}.json"
    for version in (1, 2, 3, 4)
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260824_campaign273_terminal.json"
)
FINAL_STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260824_campaign273_final_validated_v2.json"
)
VALIDATION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_273_terminal_validation_v2_20260824.json"
)
REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_273_terminal_prevalue_report.md"
)
HANDOFF = ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign273.md"
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
            "campaign273",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_catalog_freezes_seven_priority_routes_before_targeted_inventory() -> None:
    assert _sha256(CATALOG) == (
        "795096dadb60223a7891210be3eb0a50d3f5697d4355f8420964bb8300038877"
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
        "public_patent_citation_innovation_diffusion_state",
        "public_procurement_award_dependency_state",
        "public_court_enforcement_procedural_state",
        "satellite_nighttime_light_operating_footprint_state",
        "public_electricity_consumption_load_state",
        "public_customs_shipping_trade_flow_state",
        "public_product_recall_quality_event_state",
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
        "8ea413ec63956e7ca16207c5d3e8472dcde26e05c0a83784282d61fd391dbaa5"
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
    assert decision["economically_independent_route_count"] == 2
    assert decision["source_contract_ready_route_count"] == 0
    assert decision["selected_route_count"] == 0
    assert decision["complete_factor_definition_created"] is False
    assert decision["numeric_comparator_created"] is False
    assert decision["campaign273_terminalized"] is True
    library = result["library_state"]
    assert library["changed_by_campaign273"] is False
    assert library["complete_factor_definition_count"] == 162
    assert library["eligible_numeric_comparator_count"] == 143


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    assert tuple(_sha256(path) for path in LEDGERS) == (
        "28177c6e74963d80ce4046dee327cfe84fa4494764203541f28e46f4fd899c35",
        "37ae5d6c7c3440f0ae11b0d8d69969f35e5668f6e88f2d0d3fe43e432ce9b597",
        "4ab95fa158716f007e615a7de57e7ae853fd63d970f5c224731c49d63a82078c",
        "779dd2e5db290e3f687a35cc5d5e3f2da152c98842f9ae39510ded55038da31f",
    )
    ledgers = [_load(path) for path in LEDGERS]
    entries = [entry for ledger in ledgers for entry in ledger["entries"]]
    previous = ledgers[0]["authoritative_predecessor"]["chain_tip_sha256"]
    assert (
        previous == "4541baa46ad21e9d350fd49b46aa1574e805c2d35029511e964b7648d2ae82c2"
    )
    assert len(entries) == ledgers[-1]["effective_entry_count"] == 12
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
    assert sum(not entry["scientific_attempt"] for entry in entries) == 5
    assert sum(entry["result_consumed"] for entry in entries) == 7
    assert ledger["effective_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2779
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_state_keeps_goal_candidate49_and_credentials_boundary_unchanged() -> None:
    assert _sha256(STATE) == (
        "77d9719f37a8572e1dbab6975e9716d393428ee00072fff7681076b2448778be"
    )
    state = _load(STATE)
    _assert_bindings(state["authoritative_inputs"])
    assert state["goal"]["status"] == "active"
    assert state["goal"]["continuous_iteration_confirmed"] is True
    assert state["goal"]["current_campaign"] == 273
    assert "Campaign274" in state["goal"]["next_safe_work"]
    credentials = state["credential_presence_only"]
    assert credentials == {
        "env_is_regular_file": True,
        "env_mode_octal": "0600",
        "git_ignored": True,
        "nonempty_tushare_token_assignment_count": 1,
        "credential_value_or_digest_read": False,
    }
    candidate49 = state["candidate49"]
    assert candidate49["same_session_retry_allowed"] is False
    assert candidate49["campaign273_plan_or_run_executed"] is False
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


def test_reports_and_handoff_publish_one_nontrading_terminal_result() -> None:
    report = REPORT.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    assert "7 条路线全部终止" in handoff
    assert "持续目标保持 `active`" in handoff
    assert "不授权当前评分、选股、仓位、订单" in report
    title = "## Campaign273：七路线值前机制/来源前沿终止（2026-08-24）"
    for path in UNIFIED_REPORTS:
        text = path.read_text(encoding="utf-8")
        assert text.count(title) == 1
        section = text.split(title, maxsplit=1)[1]
        assert "累计历史尝试 2,777" in section
        assert "Candidate49 同日来源失败继续封口且账本 0/0" in section
        assert "本结果不构成投资建议" in section
        assert "Campaign274" in section


def test_optional_validation_and_final_state_bind_current_artifacts() -> None:
    if VALIDATION.exists():
        validation = _load(VALIDATION)
        _assert_bindings(validation["validated_artifacts"])
        assert validation["focused_test_result"]["passed"] == 7
        assert validation["json_validation"]["invalid_count"] == 0
    if FINAL_STATE.exists():
        final_state = _load(FINAL_STATE)
        _assert_bindings(final_state["authoritative_inputs"])
        assert final_state["goal"]["status"] == "active"
        assert final_state["goal"]["current_campaign"] == 273
        assert "Campaign274" in final_state["goal"]["next_safe_work"]
