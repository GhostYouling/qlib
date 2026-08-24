from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_269_exogenous_facility_hazard_concept_scouting_20260824.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_269/research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_269/research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_269/research_attempt_ledger_v3.json"
)
LEDGER_V4 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_269/research_attempt_ledger_v4.json"
)
LEDGER_V5 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_269/research_attempt_ledger_v5.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_269/research_attempt_ledger_v6.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_269_terminal_result_20260824.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_269_terminal_report.md"
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260824_campaign269_terminal.json"
)
FINAL_STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260824_campaign269_final_validated.json"
)
HANDOFF = ROOT / "docs/a_share_three_day_strategy_handoff_20260824_campaign269_final.md"
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
            "campaign269",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_reference_graph_and_publication_hashes_are_exact() -> None:
    assert _sha256(FRONTIER) == (
        "82fa865c99d79e784ba86718f55e3ef18e4dcf2c50737eab0c857c8bba3bac1b"
    )
    assert _sha256(LEDGER_V1) == (
        "94380f2edfb51ed913bb516d6e07c3e2b618cd08437537a35a3cea0bfcdeaeea"
    )
    assert _sha256(LEDGER_V2) == (
        "425784415beb3cc7c8846f17afed9972854ac4c4d6ad3db7f2da3e0c084e24fd"
    )
    assert _sha256(LEDGER_V3) == (
        "9c9f3691ad6a399f2904e74a1f5368807b9100edb77c3c8ccb5643d04280067b"
    )
    assert _sha256(LEDGER_V4) == (
        "39fc548cdcb84987588d3d38bd2f9d748340be6f422a225c023969ce9691490d"
    )
    assert _sha256(LEDGER_V5) == (
        "5e2a76c1ee74df6c813f9df331b5c8cdddd896040d4eafa9ffb276f0cf075a1f"
    )
    assert _sha256(LEDGER) == (
        "8dad1656cfdd22a1e8af34112fea1118ae8092790cb1623bd9b042c1177fc41c"
    )
    assert _sha256(RESULT) == (
        "0cc4ede06987d24fdd850f4b238799ae13bac121766a5cb01827d9778ba2a2e7"
    )
    assert _sha256(REPORT) == (
        "149b3a88a9370e215a2515a0f3b79dab36de23bcf564a4166fda2124409f29dc"
    )
    assert _sha256(STATE) == (
        "7d33eb7c1f18d82e60733f3b162b4abd37604d73e43c312d473e10807206376b"
    )
    _assert_bindings(_load(FRONTIER)["authoritative_inputs"])
    _assert_bindings(_load(RESULT)["authoritative_inputs"])
    _assert_bindings(_load(STATE)["authoritative_inputs"])


def test_finite_concept_catalog_preserves_exactly_one_non_factor_route() -> None:
    frontier = _load(FRONTIER)
    catalog = frontier["finite_concept_catalog"]
    assert [item["route_id"] for item in catalog] == [
        "c269_01",
        "c269_02",
        "c269_03",
        "c269_04",
        "c269_05",
        "c269_06",
    ]
    assert all(item["formula"] is None for item in catalog)
    assert all(item["direction"] is None for item in catalog)
    assert all(item["source_fields"] is None for item in catalog)
    selected = [
        item
        for item in catalog
        if item["decision"] == "preserve_for_separate_future_source_contract"
    ]
    assert len(selected) == 1
    assert selected[0]["route_id"] == "c269_01"
    assert frontier["selection"]["selected_concept_is_not_a_factor"] is True
    gate = frontier["gate_summary"]
    assert gate["finite_route_count"] == 6
    assert gate["selected_factor_count"] == 0
    assert gate["numeric_formula_or_direction_frozen"] is False
    assert gate["source_contract_or_adapter_created"] is False


def test_metadata_evidence_distinguishes_external_state_from_terminal_families() -> (
    None
):
    frontier = _load(FRONTIER)
    evidence = frontier["bounded_repository_metadata_evidence"]
    assert evidence["accepted_local_unconsumed_raw_channel_present"] is False
    assert evidence["complete_factor_definition_count"] == 162
    assert evidence["eligible_numeric_comparator_count"] == 143
    for term in (
        "meteorological",
        "heatwave",
        "flood",
        "typhoon",
        "earthquake",
        "geospatial",
    ):
        assert evidence["literal_match_file_counts"][term] == 0
    assert evidence["literal_match_file_counts"]["facility location"] == 1
    assert "Campaign206" in evidence["facility_location_match_interpretation"]


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    ledgers = [
        _load(LEDGER_V1),
        _load(LEDGER_V2),
        _load(LEDGER_V3),
        _load(LEDGER_V4),
        _load(LEDGER_V5),
        _load(LEDGER),
    ]
    previous = ledgers[0]["authoritative_predecessor"]["chain_tip_sha256"]
    entries = [entry for ledger in ledgers for entry in ledger["entries"]]
    assert len(entries) == ledgers[-1]["effective_entry_count"] == 17
    for ordinal, entry in enumerate(entries, 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_comparator_value_read"] is False
        assert entry["return_reading_development_trial"] is False
        previous = entry["entry_sha256"]
    ledger = ledgers[-1]
    assert previous == ledger["chain_tip_sha256"]
    assert sum(not item["scientific_attempt"] for item in entries) == 11
    assert sum(item["scientific_attempt"] for item in entries) == 6
    assert sum(item["result_consumed"] for item in entries) == 6
    assert ledger["effective_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2720
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_no_value_provider_or_current_use_boundary_is_closed() -> None:
    for artifact in (
        _load(FRONTIER),
        _load(LEDGER_V1),
        _load(LEDGER_V2),
        _load(LEDGER_V3),
        _load(LEDGER_V4),
        _load(LEDGER_V5),
        _load(LEDGER),
        _load(RESULT),
        _load(STATE),
    ):
        boundary = artifact["research_boundary"]
        for key, value in boundary.items():
            if key == "repository_metadata_and_prior_terminal_history_read":
                assert value is True
            else:
                assert value is False
    result = _load(RESULT)
    assert result["scientific_result"]["development_trial_count"] == 0
    assert result["scientific_result"]["stress_trial_count_2024_2025"] == 0
    assert result["library_state"]["changed_by_campaign269"] is False
    assert result["library_state"]["complete_factor_definition_count"] == 162
    assert result["library_state"]["eligible_numeric_comparator_count"] == 143


def test_campaign265_candidate49_and_goal_remain_unchanged() -> None:
    state = _load(STATE)
    assert (
        state["campaign265"]["scientific_or_execution_state_changed_by_campaign269"]
        is False
    )
    assert state["campaign265"]["v420_policy_present"] is False
    assert state["campaign265"]["accepted_source_manifest_present"] is False
    assert (
        state["candidate49_same_session_boundary"]["same_session_retry_allowed"]
        is False
    )
    assert (
        state["candidate49_same_session_boundary"]["campaign269_plan_or_run_executed"]
        is False
    )
    assert _sha256(SIGNAL) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []
    assert state["goal"]["status"] == "active"
    assert "Campaign270" in state["goal"]["next_safe_work"]


def test_reports_have_one_campaign269_section_and_no_trading_claim() -> None:
    for path in UNIFIED_REPORTS:
        text = path.read_text(encoding="utf-8")
        assert text.count("## Campaign269：发行人设施外生灾害概念前沿") == 1
        section = text.split("## Campaign269：发行人设施外生灾害概念前沿", maxsplit=1)[
            1
        ]
        assert "它不是因子" in section
        assert "不构成投资建议" in section
        assert "Campaign270" in section
    report = REPORT.read_text(encoding="utf-8")
    assert "零网络、概念级" in report
    assert "没有方向、公式、字段、阈值或窗口" in report
    assert "不授权当前评分、选股、仓位或订单" in report
    final_state = _load(FINAL_STATE)
    assert final_state["status"] == (
        "campaign269_concept_frontier_terminal_validated_goal_active"
    )
    assert final_state["validation"]["focused_campaign269_tests_passed"] == 7
    assert (
        final_state["validation"][
            "cross_stage_campaign265_266_267_268_269_and_candidate49_tests_passed"
        ]
        == 200
    )
    handoff = HANDOFF.read_text(encoding="utf-8")
    assert _sha256(FINAL_STATE) in handoff
    assert "Campaign270" in handoff
    assert "持续目标保持 `active`" in handoff
