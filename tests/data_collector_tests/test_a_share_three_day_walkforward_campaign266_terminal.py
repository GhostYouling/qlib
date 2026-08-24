from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_266_etf_primary_market_source_frontier_20260824.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_266/research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_266/research_attempt_ledger_v2.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_266/research_attempt_ledger_v3.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_266_terminal_result_20260824.json"
)
INITIAL_STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260824_campaign266_etf_source_terminal.json"
)
ACCOUNTING_STATE_V1 = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260824_campaign266_validation_accounting_corrected.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260824_campaign266_final_accounting_corrected.json"
)
CORRECTION_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_266_validation_accounting_correction_20260824.json"
)
CORRECTION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_266_validation_accounting_correction_v2_20260824.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_266_terminal_report.md"
INITIAL_HANDOFF = (
    ROOT
    / "docs/a_share_three_day_strategy_handoff_20260824_campaign266_etf_source_terminal.md"
)
INTERIM_HANDOFF = (
    ROOT
    / "docs/a_share_three_day_strategy_handoff_20260824_campaign266_validation_accounting_corrected.md"
)
HANDOFF = ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign266_final.md"
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
            "campaign266",
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
        "c3bd3e8e91627c78b3a4cafe470ef25f50a0fa55a897381894b68279734d731e"
    )
    assert _sha256(LEDGER_V1) == (
        "5efdb899bb7efd66ff18c6bf0abcfaa05fdda64b35ae0708d8dc0c9e87829011"
    )
    assert _sha256(LEDGER_V2) == (
        "ed624fa75dbe0ef51b8161b19bd3e048cb1bf5ad470751c98e6c4d3333f1686d"
    )
    assert _sha256(LEDGER) == (
        "bd81edad46e2a3076cd7cae5b0d6e89270d1381e1077d3967c97e6989adea764"
    )
    assert _sha256(RESULT) == (
        "664d415e5902b12af24c9fb0623216c3aee8d0490761881beebd76e1debe7c5f"
    )
    assert _sha256(REPORT) == (
        "b8583827fdb7175e0028cbc896dc9741788648c60fa6fef506c725e8f815dfba"
    )
    assert _sha256(INITIAL_STATE) == (
        "c93ab756724ab4964c9eb4b6db14e2d6e41b14b1e84d0a2b6adf4db35f029a68"
    )
    assert _sha256(CORRECTION_V1) == (
        "32b54f629db3cc6135c7aa8e453c436a9b3221b6c82257f9ba5b6b21d55dcab0"
    )
    assert _sha256(ACCOUNTING_STATE_V1) == (
        "7d2fc481597b1d500172062dc4650b489fc24129f7fe556b6fc1cec9149278ac"
    )
    assert _sha256(CORRECTION) == (
        "7a93111571ecefb3d76521c043ca6945f13ca65f2bfed3771a88134e389974b4"
    )
    assert _sha256(STATE) == (
        "381ef07ca82464f1d63812c7b215782757027c2bc654f0db174c639888e6022f"
    )
    assert _sha256(INITIAL_HANDOFF) == (
        "224d2c7b0090bee0ac0e082c65e712ab0eb937ec1c2aec10ddd28ae0df4e02ad"
    )
    assert INTERIM_HANDOFF.is_file()
    assert _sha256(HANDOFF) == (
        "25b2cc310edbd1e51ed7d6d8e86249c61a66f47991430c93ca781df5dc41c734"
    )
    _assert_bindings(frontier["authoritative_inputs"])
    _assert_bindings(result["authoritative_inputs"])
    _assert_bindings(state["authoritative_inputs"])


def test_finite_etf_frontier_is_terminal_before_formula_or_values() -> None:
    frontier = _load(FRONTIER)
    catalog = frontier["finite_prevalue_catalog"]
    assert [item["route_id"] for item in catalog] == [
        "c266_01",
        "c266_02",
        "c266_03",
        "c266_04",
        "c266_05",
        "c266_06",
    ]
    assert all(item["decision"].startswith("reject_") for item in catalog)
    assert all(item["formula"] is None for item in catalog)
    assert all(item["direction"] is None for item in catalog)
    gate = frontier["gate_summary"]
    assert gate["finite_route_count"] == 6
    assert gate["selected_factor_count"] == 0
    assert gate["numeric_formula_or_direction_frozen"] is False
    assert gate["candidate_snapshot_adapter_or_source_request_created"] is False
    assert gate["candidate_or_comparator_value_read"] is False
    assert gate["historical_daily_price_or_forward_return_read"] is False
    assert gate["development_trial_count"] == 0
    assert gate["stress_trial_count_2024_2025"] == 0
    assert gate["complete_definition_or_numeric_comparator_append_allowed"] is False


def test_official_metadata_evidence_respects_3000_point_boundary() -> None:
    frontier = _load(FRONTIER)
    evidence = {
        item["interface"]: item
        for item in frontier["official_public_documentation_evidence"]
    }
    assert (
        frontier["authorized_provider_boundary"][
            "user_authorized_tushare_point_ceiling"
        ]
        == 3000
    )
    assert evidence["fund_share"]["minimum_points"] == 2000
    assert evidence["index_weight"]["minimum_points"] == 2000
    assert evidence["fund_basic"]["minimum_points"] == 2000
    assert evidence["etf_basic"]["minimum_points"] == 8000
    assert evidence["etf_share_size"]["minimum_points"] == 8000
    assert evidence["etf_sh_cons_and_etf_sz_cons"]["minimum_points_each"] == 8000
    assert evidence["fund_portfolio"]["minimum_points"] == 5000
    assert "monthly" in evidence["index_weight"]["documented_frequency_or_semantics"]
    assert (
        "quarterly" in evidence["fund_portfolio"]["documented_frequency_or_semantics"]
    )
    boundary = frontier["authorized_provider_boundary"]
    assert boundary["credential_value_or_digest_inspected"] is False
    assert boundary["provider_client_created"] is False
    assert boundary["provider_request_issued"] is False


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    ledger_v1 = _load(LEDGER_V1)
    ledger_v2 = _load(LEDGER_V2)
    ledger = _load(LEDGER)
    previous = ledger_v1["authoritative_predecessor"]["chain_tip_sha256"]
    entries = (
        ledger_v1["entries"]
        + ledger_v2["appended_entries"]
        + ledger["appended_entries"]
    )
    assert len(ledger_v1["entries"]) == ledger_v1["effective_entry_count"] == 15
    assert len(entries) == ledger["effective_entry_count"] == 17
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
        == ("85638655a44010d11e319e344a84ad27ab7802020e0b43f021e55496b2847d48")
    )
    assert sum(not item["scientific_attempt"] for item in entries) == 11
    assert sum(item["scientific_attempt"] for item in entries) == 6
    assert sum(item["result_consumed"] for item in entries) == 6
    assert ledger["effective_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2665
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_state_keeps_campaign265_candidate49_and_goal_boundaries() -> None:
    state = _load(STATE)
    assert state["scientific_state"]["complete_factor_definition_count"] == 162
    assert state["scientific_state"]["eligible_numeric_comparator_count"] == 143
    assert (
        state["campaign265"]["scientific_or_execution_state_changed_by_campaign266"]
        is False
    )
    assert state["campaign265"]["v420_policy_present"] is False
    assert state["campaign265"]["accepted_source_manifest_present"] is False
    assert state["campaign265"]["provider_request_authorized"] is False
    assert state["goal"]["status"] == "active"
    assert state["goal"]["continuous_iteration_confirmed"] is True
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
    for path in (LEDGER_V1, LEDGER_V2, LEDGER, CORRECTION_V1, CORRECTION):
        boundary = _load(path)["research_boundary"]
        assert boundary
        for key, value in boundary.items():
            if key == "official_public_documentation_web_read":
                continue
            assert value is False, key


def test_unified_reports_have_one_exact_campaign266_section() -> None:
    state = _load(STATE)
    heading = "## Campaign266：ETF 一级市场压力来源值前终止（2026-08-24）"
    black_correction = "### Campaign266 首轮格式验证会计更正"
    boundary_correction = "### Campaign266 跨阶段边界断言会计更正"
    expected = (
        state["mutable_unified_reports"]["current"]["sha256_at_publication"],
        state["mutable_unified_reports"]["three_day"]["sha256_at_publication"],
    )
    for path, expected_sha256 in zip(UNIFIED_REPORTS, expected, strict=True):
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert text.count(black_correction) == 1
        assert text.count(boundary_correction) == 1
        assert "2,665" in text
        assert "c157_02" in text
        assert _sha256(path) == expected_sha256
