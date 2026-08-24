from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_267_issuer_bond_credit_spread_source_frontier_20260824.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_267/research_attempt_ledger_v1.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_267_terminal_result_20260824.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260824_campaign267_credit_spread_source_terminal.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_267_terminal_report.md"
HANDOFF = ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign267_final.md"
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
            "campaign267",
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
        "371ae8f8b512e0d9e97cfd7bbe962b69a831ae49c1a6351d37f4c39793cfe93f"
    )
    assert _sha256(LEDGER) == (
        "3982c1e26415c8805dcbf71afd007f02b7a4aa8763bdef29b5d05b2a1ab042a7"
    )
    assert _sha256(RESULT) == (
        "a8d0602d869b560f8a9e26babd37b64fb5dd1a53e2f3969f1989c525559f318d"
    )
    assert _sha256(REPORT) == (
        "d0c0feb4e3697ad6220d803377680b4c378d22dbeccaf8a658b17e93f5dd17c9"
    )
    assert _sha256(STATE) == (
        "8af1b81a4433fd71d17900ea4623772e3c948ffce3c389d92fcc0d129b86d9bd"
    )
    assert _sha256(HANDOFF) == (
        "5c501a611af493028a5a2eb90f0fb6d3fdf6d62a90c3f4c6edd5e22f1f9df3cf"
    )
    _assert_bindings(frontier["authoritative_inputs"])
    _assert_bindings(result["authoritative_inputs"])
    _assert_bindings(state["authoritative_inputs"])


def test_finite_credit_spread_frontier_is_terminal_before_formula_or_values() -> None:
    frontier = _load(FRONTIER)
    catalog = frontier["finite_prevalue_catalog"]
    assert [item["route_id"] for item in catalog] == [
        "c267_01",
        "c267_02",
        "c267_03",
        "c267_04",
        "c267_05",
        "c267_06",
        "c267_07",
    ]
    assert all(item["decision"].startswith("reject_") for item in catalog)
    assert all(item["formula"] is None for item in catalog)
    assert all(item["direction"] is None for item in catalog)
    gate = frontier["gate_summary"]
    assert gate["finite_route_count"] == 7
    assert gate["selected_factor_count"] == 0
    assert gate["numeric_formula_or_direction_frozen"] is False
    assert gate["candidate_snapshot_adapter_or_source_request_created"] is False
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
    assert boundary["credential_value_or_digest_inspected"] is False
    assert boundary["provider_client_created"] is False
    assert boundary["provider_request_issued"] is False
    assert evidence["tushare_cb_daily"]["minimum_points"] == 2000
    assert evidence["tushare_cb_basic"]["minimum_points"] == 2000
    assert evidence["tushare_cb_rating"]["minimum_points"] == 2000
    assert evidence["tushare_bc_otcqt_and_bc_bestotcqt"]["minimum_points"] == 2000
    assert evidence["tushare_bond_blk"]["minimum_points"] == 5000
    assert evidence["tushare_repo_daily"]["minimum_points"] == 2000
    assert evidence["tushare_yc_cb"]["minimum_points"] is None
    assert "convertible-bond-only" in evidence["tushare_cb_daily"]["admission_effect"]
    assert (
        "shared by groups"
        in evidence["chinamoney_closing_yield_curves"]["admission_effect"]
    )


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    ledger = _load(LEDGER)
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    entries = ledger["entries"]
    assert len(entries) == ledger["effective_entry_count"] == 16
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
        == ("fe246bd88e2bde789be0238af195a78a04edb4a495b282582dfe7b7f71b2d1b4")
    )
    assert sum(not item["scientific_attempt"] for item in entries) == 9
    assert sum(item["scientific_attempt"] for item in entries) == 7
    assert sum(item["result_consumed"] for item in entries) == 7
    assert ledger["effective_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2681
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_state_keeps_campaign265_candidate49_and_goal_boundaries() -> None:
    state = _load(STATE)
    assert state["scientific_state"]["complete_factor_definition_count"] == 162
    assert state["scientific_state"]["eligible_numeric_comparator_count"] == 143
    assert (
        state["campaign265"]["scientific_or_execution_state_changed_by_campaign267"]
        is False
    )
    assert state["campaign265"]["v420_policy_present"] is False
    assert state["campaign265"]["accepted_source_manifest_present"] is False
    assert state["campaign265"]["provider_request_authorized"] is False
    assert state["goal"]["status"] == "active"
    assert state["goal"]["continuous_iteration_confirmed"] is True
    assert "c157_04" in state["goal"]["next_safe_work"]
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
    for artifact in (_load(FRONTIER), _load(RESULT), _load(STATE)):
        boundary = artifact["research_boundary"]
        assert boundary["official_public_documentation_web_read"] is True
        for key, value in boundary.items():
            if key in {
                "official_public_documentation_web_read",
                "repository_metadata_and_prior_terminal_history_read",
            }:
                continue
            assert value is False, key
    boundary = _load(LEDGER)["research_boundary"]
    assert boundary["official_public_documentation_web_read"] is True
    for key, value in boundary.items():
        if key == "official_public_documentation_web_read":
            continue
        assert value is False, key


def test_unified_reports_have_one_exact_campaign267_section() -> None:
    state = _load(STATE)
    heading = "## Campaign267：发行人债券信用利差—股票背离来源值前终止（2026-08-24）"
    expected = (
        state["mutable_unified_reports"]["current"]["sha256_at_publication"],
        state["mutable_unified_reports"]["three_day"]["sha256_at_publication"],
    )
    for path, expected_sha256 in zip(UNIFIED_REPORTS, expected, strict=True):
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "2,681" in text
        assert "c157_04" in text
        assert _sha256(path) == expected_sha256
