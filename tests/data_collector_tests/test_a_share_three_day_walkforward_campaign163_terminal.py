from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
FAILURE_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_163_prevalue_infrastructure_failure_20260815.json"
)
FAILURE_V2 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_163_prevalue_infrastructure_failure_v2_20260815.json"
)
FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_163_prevalue_infrastructure_failure_v3_20260815.json"
)
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_163_supply_chain_disclosure_source_frontier_20260815.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_163/research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_163/research_attempt_ledger_v2.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_163/research_attempt_ledger_v3.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_163_terminal_result_v3_20260815.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_163_terminal_report_v3.md"
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v232_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign163_prevalue_terminal_v3.json"
)
SIGNAL_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bound_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def test_campaign163_all_authoritative_bindings_resolve() -> None:
    for record_path in (FAILURE_V1, FRONTIER, TERMINAL, POLICY, STATE):
        record = _load(record_path)
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            bound = _bound_path(binding["path"])
            assert bound.is_file()
            assert _sha(bound) == binding["sha256"]

    state = _load(STATE)
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign163"]["terminal_result"]["sha256"] == _sha(TERMINAL)
    assert state["campaign163"]["attempt_ledger"]["sha256"] == _sha(LEDGER)
    assert state["reports"]["campaign163_final_terminal_report"]["sha256"] == _sha(
        REPORT
    )


def test_campaign163_frontier_is_finite_and_distinguishes_deferral() -> None:
    frontier = _load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert len(routes) == 6
    assert [item["catalog_id"] for item in routes] == [
        "c163_01",
        "c163_02",
        "c163_03",
        "c163_04",
        "c163_05",
        "c163_06",
    ]
    assert all(item["formula"] is None for item in routes)
    assert all(item["direction"] is None for item in routes)
    assert all(
        not item["parameters_filters_subsets_combinations_models"] for item in routes
    )
    assert sum(item["new_issuer_state"] for item in routes) == 3
    assert sum(item["complete_local_source_contract"] for item in routes) == 0
    summary = frontier["gate_summary"]
    assert summary["source_admission_deferrals_not_factor_failures"] == 3
    assert summary["related_operator_window_or_subset_rejections"] == 3
    assert summary["selected_candidate_count"] == 0
    assert (
        frontier["scientific_interpretation"][
            "supply_chain_disclosure_factor_predictive_value_tested"
        ]
        is False
    )
    assert (
        frontier["scientific_interpretation"]["deferred_routes_declared_ineffective"]
        is False
    )


def test_campaign163_source_gate_and_research_boundary_are_closed() -> None:
    frontier = _load(FRONTIER)
    gate = frontier["mandatory_source_admission_gate"]
    assert len([key for key in gate if key.startswith("gate_")]) == 5
    boundary = frontier["research_boundary"]
    assert boundary["annual_report_pdf_table_or_response_value_read"] is False
    assert boundary["source_row_or_column_value_read"] is False
    assert boundary["candidate_or_comparator_value_read"] is False
    assert boundary["historical_daily_price_or_forward_return_value_read"] is False
    assert boundary["provider_or_web_request_issued"] is False
    assert boundary["stress_2024_2025_opened"] is False


def test_campaign163_infrastructure_failure_is_preserved() -> None:
    v1 = _load(FAILURE_V1)
    first = v1["failure"]
    assert first["attempt_id"] == "campaign163_infrastructure_001"
    assert first["exit_code"] == 1
    assert first["failed_exit_code_bypassed_or_masked"] is False
    assert first["target_file_written"] is False
    v2 = _load(FAILURE_V2)
    assert v2["authoritative_predecessor"]["sha256"] == _sha(FAILURE_V1)
    second = v2["delta_failure"]
    assert second["attempt_id"] == "campaign163_infrastructure_002"
    assert second["exit_code"] == 1
    assert second["failed_exit_code_bypassed_or_masked"] is False
    assert second["correct_ledger_v1_sha256"] == _sha(LEDGER_V1)
    assert v2["effective_failure_count"] == 2
    v3 = _load(FAILURE)
    assert v3["authoritative_predecessor"]["sha256"] == _sha(FAILURE_V2)
    third = v3["delta_failure"]
    assert third["attempt_id"] == "campaign163_infrastructure_003"
    assert third["partial_target_write"] is False
    assert third["focused_recovery_tests_passed"] == 9
    assert v3["effective_failure_count"] == 3


def test_campaign163_attempt_chain_and_accounting_are_exact() -> None:
    ledger_v1 = _load(LEDGER_V1)
    predecessor = ledger_v1["authoritative_predecessor"]
    assert _sha(ROOT / predecessor["path"]) == predecessor["sha256"]
    assert predecessor["cumulative_historical_research_attempt_count"] == 1421
    previous = predecessor["chain_tip_sha256"]
    for entry in ledger_v1["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign163",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == previous
        assert entry["candidate_comparator_price_or_return_value_read"] is False
    assert previous == ledger_v1["chain_tip_sha256"]

    ledger_v2 = _load(LEDGER_V2)
    assert ledger_v2["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V1)
    for entry in ledger_v2["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign163",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == previous
        assert entry["candidate_comparator_price_or_return_value_read"] is False
    assert previous == ledger_v2["chain_tip_sha256"]

    ledger = _load(LEDGER)
    assert ledger["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V2)
    for entry in ledger["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign163",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == previous
        assert entry["candidate_comparator_price_or_return_value_read"] is False
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 9
    assert ledger["effective_prevalue_scientific_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 3
    assert ledger["cumulative_historical_research_attempt_count"] == 1430
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign163_preserves_library_orders_and_future_boundaries() -> None:
    definitions = features.reconstruct_complete_definitions()
    definitions.append(
        {
            "name": "eastmoney_debt_maturity_resilience",
            "score_direction": "higher",
        }
    )
    comparisons = features.reconstruct_comparisons()
    policy = _load(POLICY)

    assert len(definitions) == 158
    assert features._order_digest(definitions) == (
        "4819c7fd7c0795d7598a52f3c615e3f117d5f4ecd9332974bc8e3dfa57c96667"
    )
    assert len(comparisons) == 142
    assert features._order_digest(comparisons) == (
        "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )
    assert policy["complete_historical_feature_library"]["unchanged_from_v231"]
    assert policy["numerical_comparator_eligibility"]["unchanged_from_v231"]
    boundary = policy["future_campaign_boundary"]
    assert boundary["next_campaign"] == 164
    assert boundary["historical_offline_prevalue_work_may_continue_at_any_local_time"]
    assert boundary["2024_2025_source_or_returns_remain_closed"] is True


def test_campaign163_candidate49_weekend_and_goal_boundaries_hold() -> None:
    state = _load(STATE)
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert state["candidate49"]["signal_ledger"]["entries"] == 0
    assert state["candidate49"]["execution_ledger"]["entries"] == 0
    assert state["candidate49_daily_20260815"]["accepted_local_trading_day"] is False
    assert state["candidate49_daily_20260815"]["credential_presence_checked"] is False
    assert state["candidate49_daily_20260815"]["plan_run"] is False
    assert state["candidate49_daily_20260815"]["run_run"] is False
    assert state["goal"]["status"] == "active"
    assert state["goal"]["campaign164_offline_scouting_authorized"] is True
    assert state["goal"]["campaign164_started"] is False


def test_campaign163_reports_are_appended_exactly_once() -> None:
    heading = "## Campaign163 供应链披露来源前沿值前终止"
    assert "9 次尝试（6 科学、3 基础设施）" in REPORT.read_text(encoding="utf-8")
    state = _load(STATE)
    for report_key in ("current_research_report", "three_day_research_report"):
        binding = state["reports"][report_key]
        assert binding["mutable_append_only_report_not_an_immutable_binding"]
        text = (ROOT / binding["path"]).read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "Campaign163 共 7 次尝试（6 科学、1 基础设施）" in text
        assert text.count("### Campaign163 发布绑定校验会计追加") == 1
        assert "Campaign163 有效会计为 8 次尝试（6 科学、2 基础设施）" in text
        assert text.count("### Campaign163 最终发布会计追加") == 1
        assert "Campaign163 最终 9 次尝试（6 科学、3 基础设施）" in text
        assert len(binding["sha256_at_publication"]) == 64


def test_campaign163_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (
        FAILURE_V1,
        FAILURE_V2,
        FAILURE,
        FRONTIER,
        LEDGER_V1,
        LEDGER_V2,
        LEDGER,
        TERMINAL,
        POLICY,
        STATE,
    ):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at
