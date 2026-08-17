from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
FAILURE_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_164_prevalue_infrastructure_failure_20260815.json"
)
FAILURE_V2 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_164_prevalue_infrastructure_failure_v2_20260815.json"
)
FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_164_prevalue_infrastructure_failure_v3_20260815.json"
)
TIMESTAMP_CORRECTION_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_164_recorded_at_correction_20260815.json"
)
TIMESTAMP_CORRECTION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_164_recorded_at_correction_v2_20260815.json"
)
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_164_human_capital_source_frontier_20260815.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_164/research_attempt_ledger.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_164/research_attempt_ledger_v2.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_164_terminal_result_v2_20260815.json"
)
REPORT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_164_terminal_report_v2_20260815.md"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v235_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign164_prevalue_terminal_v3.json"
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


def test_campaign164_all_authoritative_bindings_resolve() -> None:
    for record_path in (
        FRONTIER,
        FAILURE,
        TIMESTAMP_CORRECTION,
        TERMINAL,
        POLICY,
        STATE,
    ):
        record = _load(record_path)
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            bound = _bound_path(binding["path"])
            assert bound.is_file()
            assert _sha(bound) == binding["sha256"]

    state = _load(STATE)
    assert state["authoritative_policy"]["sha256"] == _sha(POLICY)
    assert state["campaign164"]["terminal_result"]["sha256"] == _sha(TERMINAL)
    assert state["campaign164"]["attempt_ledger"]["sha256"] == _sha(LEDGER)
    assert state["reports"]["campaign164_effective_terminal_report"]["sha256"] == _sha(
        REPORT
    )


def test_campaign164_frontier_is_finite_and_distinguishes_deferral() -> None:
    frontier = _load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert len(routes) == 6
    assert [item["catalog_id"] for item in routes] == [
        "c164_01",
        "c164_02",
        "c164_03",
        "c164_04",
        "c164_05",
        "c164_06",
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
    assert summary["prior_leakage_or_related_route_rejections"] == 3
    assert summary["selected_candidate_count"] == 0
    assert (
        frontier["scientific_interpretation"][
            "human_capital_or_employee_productivity_declared_ineffective"
        ]
        is False
    )


def test_campaign164_source_gate_and_research_boundary_are_closed() -> None:
    frontier = _load(FRONTIER)
    gate = frontier["mandatory_source_admission_gate"]
    assert len(gate["must_freeze_before_any_formula_or_direction"]) == 9
    assert (
        gate[
            "formula_direction_parameter_filter_subset_combination_or_model_choice_allowed_before_gate"
        ]
        is False
    )
    boundary = frontier["research_boundary"]
    assert (
        boundary[
            "annual_report_document_pdf_table_source_row_candidate_comparator_price_or_return_value_read"
        ]
        is False
    )
    assert boundary["provider_or_web_request_issued"] is False
    assert boundary["stress_2024_2025_opened"] is False


def test_campaign164_infrastructure_failures_are_preserved() -> None:
    v1 = _load(FAILURE_V1)
    assert len(v1["failures"]) == 1
    assert v1["failures"][0]["exit_code"] == 1
    assert v1["failures"][0]["write_occurred"] is False

    v2 = _load(FAILURE_V2)
    assert v2["supersedes_without_rewriting"]["sha256"] == _sha(FAILURE_V1)
    assert len(v2["failures"]) == 2
    assert [item["attempt_id"] for item in v2["failures"]] == [
        "campaign164_infrastructure_001",
        "campaign164_infrastructure_002",
    ]
    assert all(item["exit_code"] == 1 for item in v2["failures"])
    assert all(item["write_occurred"] is False for item in v2["failures"])
    assert all(
        item["failed_exit_code_bypassed_or_masked"] is False for item in v2["failures"]
    )

    failure = _load(FAILURE)
    assert failure["authoritative_predecessor"]["sha256"] == _sha(FAILURE_V2)
    assert failure["effective_failure_count"] == 5
    assert [item["attempt_id"] for item in failure["delta_failures"]] == [
        "campaign164_infrastructure_003",
        "campaign164_infrastructure_004",
        "campaign164_infrastructure_005",
    ]
    assert all(
        item["failed_exit_code_bypassed_or_masked"] is False
        for item in failure["delta_failures"]
    )


def test_campaign164_attempt_chain_and_accounting_are_exact() -> None:
    ledger_v1 = _load(LEDGER_V1)
    predecessor = ledger_v1["authoritative_predecessor"]
    assert _sha(ROOT / predecessor["path"]) == predecessor["sha256"]
    assert predecessor["cumulative_historical_research_attempt_count"] == 1432
    previous = predecessor["chain_tip_sha256"]
    for entry in ledger_v1["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign164",
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
    assert ledger_v1["effective_entry_count"] == 8

    ledger = _load(LEDGER)
    assert ledger["authoritative_predecessor"]["sha256"] == _sha(LEDGER_V1)
    for entry in ledger["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign164",
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
    assert ledger["effective_entry_count"] == 11
    assert ledger["effective_prevalue_scientific_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 5
    assert ledger["cumulative_historical_research_attempt_count"] == 1443
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign164_preserves_library_orders_and_future_boundaries() -> None:
    definitions = features.reconstruct_complete_definitions()
    definitions.append(
        {"name": "eastmoney_debt_maturity_resilience", "score_direction": "higher"}
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
    assert policy["complete_historical_feature_library"]["unchanged_from_v234"]
    assert policy["numerical_comparator_eligibility"]["unchanged_from_v234"]
    boundary = policy["future_campaign_boundary"]
    assert boundary["next_campaign"] == 165
    assert boundary["historical_offline_prevalue_work_may_continue_at_any_local_time"]
    assert boundary["2024_2025_source_or_returns_remain_closed"] is True


def test_campaign164_candidate49_weekend_and_goal_boundaries_hold() -> None:
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
    assert state["goal"]["campaign165_offline_scouting_authorized"] is True
    assert state["goal"]["campaign165_started"] is False


def test_campaign164_reports_are_appended_exactly_once() -> None:
    heading = "## Campaign164 人力资本来源前沿值前终止"
    assert "最终有效会计为 11 次尝试（6 科学、5 基础设施）" in REPORT.read_text(
        encoding="utf-8"
    )
    state = _load(STATE)
    for report_key in ("current_research_report", "three_day_research_report"):
        binding = state["reports"][report_key]
        assert binding["mutable_append_only_report_not_an_immutable_binding"]
        text = (ROOT / binding["path"]).read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "Campaign164 共 8 次尝试（6 科学、2 基础设施）" in text
        assert text.count("### Campaign164 有效发布与时间校正会计追加") == 1
        assert "Campaign164 最终有效会计为 11 次尝试（6 科学、5 基础设施）" in text
        assert _sha(ROOT / binding["path"]) == binding["sha256_at_publication"]


def test_campaign164_timestamp_mistakes_are_additively_corrected() -> None:
    v1 = _load(TIMESTAMP_CORRECTION_V1)
    assert len(v1["corrections"]) == 7
    for correction in v1["corrections"][:6]:
        bound = ROOT / correction["path"]
        assert _sha(bound) == correction["sha256"]
        assert datetime.fromisoformat(
            correction["effective_recorded_at_from_original_file_mtime"]
        ) < datetime.fromisoformat(correction["invalid_declared_recorded_at"])

    correction = _load(TIMESTAMP_CORRECTION)
    assert correction["authoritative_predecessor"]["sha256"] == _sha(
        TIMESTAMP_CORRECTION_V1
    )
    delta = correction["delta_correction"]
    assert _sha(ROOT / delta["path"]) == delta["correct_sha256"]
    assert delta["correct_sha256"] != delta["invalid_sha256_in_v1"]
    assert correction["correction_rules"]["old_files_rewritten"] is False
