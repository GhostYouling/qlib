from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_268_option_implied_skew_term_structure_source_frontier_20260824.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_268/research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_268/research_attempt_ledger_v2.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_268/research_attempt_ledger_v3.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_268_terminal_result_20260824.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260824_campaign268_final_validated.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_268_terminal_report.md"
HANDOFF = (
    ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign268_final_v4.md"
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
            "campaign268",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_reference_graph_and_publication_hashes_are_exact() -> None:
    frontier = _load(FRONTIER)
    result = _load(RESULT)
    state = _load(STATE)
    assert _sha256(FRONTIER) == (
        "b3552cad165ffec002c0796cd6e6842506e4a554669d73d67949b41678b83dbb"
    )
    assert _sha256(LEDGER) == (
        "1863995fee16d64e28c3e74074395e649a660e24d9a2cdc653ac45e3fda8a1b7"
    )
    assert _sha256(RESULT) == (
        "e436a863bcddfa8d4a242e482f1e8e52760bed2171de057b3b01f462404b59fc"
    )
    assert _sha256(REPORT) == (
        "ccf558fd1e6d674552ebeae48f4c8533c4f9dd2acaefc3473aa6542db0725003"
    )
    assert _sha256(STATE) == (
        "6bdca2e27e9d947078f8e6154434358eefc1134b52e688c18d4fb70ace5229b7"
    )
    assert _sha256(HANDOFF) == (
        "e3abce4ffffc8e08b12baadba287a0ee1f96a6cb6d64499ccc47d24ba7082c4d"
    )
    _assert_bindings(frontier["authoritative_inputs"])
    _assert_bindings(result["authoritative_inputs"])
    _assert_bindings(state["authoritative_inputs"])


def test_finite_option_surface_frontier_is_terminal_before_formula_or_values() -> None:
    frontier = _load(FRONTIER)
    catalog = frontier["finite_prevalue_catalog"]
    assert [item["route_id"] for item in catalog] == [
        "c268_01",
        "c268_02",
        "c268_03",
        "c268_04",
        "c268_05",
        "c268_06",
        "c268_07",
    ]
    assert all(item["decision"].startswith("reject_") for item in catalog)
    assert all(item["formula"] is None for item in catalog)
    assert all(item["direction"] is None for item in catalog)
    gate = frontier["gate_summary"]
    assert gate["finite_route_count"] == 7
    assert gate["selected_factor_count"] == 0
    assert gate["numeric_formula_or_direction_frozen"] is False
    assert gate["candidate_snapshot_adapter_or_source_request_created"] is False
    assert gate["option_price_or_surface_value_read"] is False
    assert gate["candidate_or_comparator_value_read"] is False
    assert gate["historical_daily_price_or_forward_return_read"] is False
    assert gate["development_trial_count"] == 0
    assert gate["stress_trial_count_2024_2025"] == 0
    assert gate["complete_definition_or_numeric_comparator_append_allowed"] is False


def test_official_metadata_does_not_substitute_or_exceed_authorization() -> None:
    frontier = _load(FRONTIER)
    evidence = {
        item["interface"]: item
        for item in frontier["official_public_documentation_evidence"]
    }
    boundary = frontier["authorized_provider_boundary"]
    assert boundary["user_authorized_tushare_point_ceiling"] == 3000
    assert boundary["credential_presence_verified_without_value_or_digest"] is True
    assert boundary["credential_value_or_digest_inspected"] is False
    assert boundary["provider_client_created"] is False
    assert boundary["provider_request_issued"] is False
    assert evidence["tushare_opt_basic"]["minimum_points"] == 5000
    assert evidence["tushare_opt_daily"]["minimum_points"] == 2000
    assert (
        "bid and ask quotes" in evidence["tushare_opt_daily"]["missing_surface_fields"]
    )
    assert (
        "ETF basket underlyings"
        in evidence["sse_current_etf_option_underlyings"]["admission_effect"]
    )
    assert (
        "shared basket state"
        in evidence["szse_etf_option_products"]["admission_effect"]
    )


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    base = _load(LEDGER_V1)
    first_correction = _load(LEDGER_V2)
    ledger = _load(LEDGER)
    assert _sha256(LEDGER_V1) == first_correction["authoritative_predecessor"]["sha256"]
    assert _sha256(LEDGER_V2) == ledger["authoritative_predecessor"]["sha256"]
    previous = base["authoritative_predecessor"]["chain_tip_sha256"]
    entries = (
        base["entries"]
        + first_correction["appended_entries"]
        + ledger["appended_entries"]
    )
    assert len(entries) == ledger["effective_entry_count"] == 22
    for ordinal, entry in enumerate(entries, 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_comparator_value_read"] is False
        assert entry["return_reading_development_trial"] is False
        previous = entry["entry_sha256"]
    assert (
        previous
        == ledger["chain_tip_sha256"]
        == ("d25e5d155a3e6a8cbb01af1d8492e1ea5b4831409242816502085c6d04581a8e")
    )
    assert sum(not item["scientific_attempt"] for item in entries) == 15
    assert sum(item["scientific_attempt"] for item in entries) == 7
    assert sum(item["result_consumed"] for item in entries) == 7
    assert ledger["effective_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2703
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_state_keeps_campaign265_candidate49_and_goal_boundaries() -> None:
    state = _load(STATE)
    assert state["scientific_state"]["complete_factor_definition_count"] == 162
    assert state["scientific_state"]["eligible_numeric_comparator_count"] == 143
    assert state["scientific_state"]["option_price_or_surface_value_read"] is False
    assert (
        state["campaign265"]["scientific_or_execution_state_changed_by_campaign268"]
        is False
    )
    assert state["campaign265"]["v420_policy_present"] is False
    assert state["campaign265"]["accepted_source_manifest_present"] is False
    assert state["campaign265"]["provider_request_authorized"] is False
    assert state["goal"]["status"] == "active"
    assert state["goal"]["continuous_iteration_confirmed"] is True
    assert "Campaign269" in state["goal"]["next_safe_work"]
    workflow = state["candidate49_same_session_workflow"]
    assert workflow["plan_ready"] is True
    assert workflow["plan_after_1630_exit_code"] == 0
    assert workflow["confirmed_run_exit_code"] == 1
    assert workflow["provider_continuation_allowed"] is False
    assert workflow["same_session_retry_allowed"] is False
    assert _sha256(SIGNAL) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []
    assert not list(
        (ROOT / "docs").glob(
            "a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v420*.json"
        )
    )


def test_research_boundary_records_public_docs_but_no_provider_or_values() -> None:
    for artifact in (_load(FRONTIER), _load(RESULT)):
        boundary = artifact["research_boundary"]
        assert boundary["official_public_documentation_web_read"] is True
        for key, value in boundary.items():
            if key in {
                "official_public_documentation_web_read",
                "repository_metadata_and_prior_terminal_history_read",
            }:
                continue
            assert value is False, key
    state_boundary = _load(STATE)["research_boundary"]
    assert state_boundary["official_public_documentation_web_read"] is True
    assert (
        state_boundary[
            "provider_api_request_issued_by_candidate49_same_session_workflow"
        ]
        is True
    )
    assert state_boundary["candidate49_plan_executed"] is True
    assert state_boundary["candidate49_confirmed_run_executed"] is True
    for key, value in state_boundary.items():
        if key in {
            "official_public_documentation_web_read",
            "repository_metadata_and_prior_terminal_history_read",
            "provider_api_request_issued_by_candidate49_same_session_workflow",
            "candidate49_plan_executed",
            "candidate49_confirmed_run_executed",
        }:
            continue
        assert value is False, key
    boundary = _load(LEDGER)["research_boundary"]
    assert boundary["scientific_result_changed"] is False
    assert all(value is False for value in boundary.values())


def test_unified_reports_have_one_exact_campaign268_section() -> None:
    state = _load(STATE)
    heading = "## Campaign268：期权隐含偏度/期限结构来源值前终止（2026-08-24）"
    expected = (
        state["mutable_unified_reports"]["current"]["sha256_at_publication"],
        state["mutable_unified_reports"]["three_day"]["sha256_at_publication"],
    )
    for path, expected_sha256 in zip(UNIFIED_REPORTS, expected, strict=True):
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "2,703" in text
        assert "Campaign269" in text
        assert _sha256(path) == expected_sha256
