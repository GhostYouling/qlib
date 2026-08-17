from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
FAILURES_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_prevalue_infrastructure_failures_20260815.json"
)
FAILURES_V2 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_prevalue_infrastructure_failures_v2_20260815.json"
)
FAILURES_V3 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_prevalue_infrastructure_failures_v3_20260815.json"
)
FAILURES_V4 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_prevalue_infrastructure_failures_v4_20260815.json"
)
FAILURES_V5 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_prevalue_infrastructure_failures_v5_20260815.json"
)
FAILURES_V6 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_prevalue_infrastructure_failures_v6_20260815.json"
)
FAILURES_V7 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_prevalue_infrastructure_failures_v7_20260815.json"
)
FAILURES = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_prevalue_infrastructure_failures_v8_20260815.json"
)
TIMESTAMP_CORRECTION_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_recorded_at_correction_20260815.json"
)
TIMESTAMP_CORRECTION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_recorded_at_correction_v2_20260815.json"
)
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_operating_scale_adoption_kpi_source_frontier_20260815.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_168/research_attempt_ledger.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_168/research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_168/research_attempt_ledger_v3.json"
)
LEDGER_V4 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_168/research_attempt_ledger_v4.json"
)
LEDGER_V5 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_168/research_attempt_ledger_v5.json"
)
LEDGER_V6 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_168/research_attempt_ledger_v6.json"
)
LEDGER_V7 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_168/research_attempt_ledger_v7.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_168/research_attempt_ledger_v8.json"
)
TERMINAL_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_terminal_result_20260815.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_terminal_result_v8_20260815.json"
)
REPORT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_168_terminal_report_v8_20260815.md"
)
POLICY_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v240_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v246_20260815.json"
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


def test_campaign168_bindings_and_finite_frontier() -> None:
    for record_path in (FAILURES, FRONTIER, TERMINAL, POLICY):
        record = _load(record_path)
        superseded = record.get("supersedes_without_rewriting")
        if isinstance(superseded, dict) and "path" in superseded:
            bound = _bound_path(superseded["path"])
            assert bound.is_file()
            assert _sha(bound) == superseded["sha256"]
        for binding in record.get("authoritative_inputs", {}).values():
            if isinstance(binding, dict) and "path" in binding:
                bound = _bound_path(binding["path"])
                assert bound.is_file()
                assert _sha(bound) == binding["sha256"]

    frontier = _load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert [item["catalog_id"] for item in routes] == [
        f"c168_0{i}" for i in range(1, 8)
    ]
    assert all(item["formula"] is None and item["direction"] is None for item in routes)
    assert all(
        not item["parameters_filters_subsets_combinations_models"] for item in routes
    )
    assert sum(item["new_issuer_state"] for item in routes) == 4
    assert sum(item["complete_local_source_contract"] for item in routes) == 0
    assert (
        frontier["gate_summary"]["source_admission_deferrals_not_factor_failures"] == 4
    )
    assert frontier["gate_summary"]["leakage_or_operator_route_rejections"] == 3
    assert frontier["gate_summary"]["selected_candidate_count"] == 0


def test_campaign168_failures_source_gate_and_attempt_chain() -> None:
    failures_v1 = _load(FAILURES_V1)
    assert [item["attempt_id"] for item in failures_v1["failures"]] == [
        "campaign168_infrastructure_001",
        "campaign168_infrastructure_002",
    ]
    assert all(item["exit_code"] == 2 for item in failures_v1["failures"])
    assert all(item["write_occurred"] is False for item in failures_v1["failures"])
    assert all(
        item["failed_exit_code_bypassed_or_masked"] is False
        for item in failures_v1["failures"]
    )
    failures_v2 = _load(FAILURES_V2)
    assert failures_v2["supersedes_without_rewriting"]["sha256"] == _sha(FAILURES_V1)
    assert [item["attempt_id"] for item in failures_v2["delta_failures"]] == [
        "campaign168_infrastructure_003",
        "campaign168_infrastructure_004",
    ]
    assert failures_v2["delta_failures"][1]["failed_exit_code_bypassed_or_masked"]
    assert failures_v2["delta_failures"][1][
        "masked_exit_is_now_recorded_and_not_used_as_gate_success"
    ]
    failures_v3 = _load(FAILURES_V3)
    assert failures_v3["authoritative_predecessor"]["sha256"] == _sha(FAILURES_V2)
    assert failures_v3["delta_failures"][0]["attempt_id"] == (
        "campaign168_infrastructure_005"
    )
    failures_v4 = _load(FAILURES_V4)
    assert failures_v4["authoritative_predecessor"]["sha256"] == _sha(FAILURES_V3)
    assert failures_v4["delta_failures"][0]["attempt_id"] == (
        "campaign168_infrastructure_006"
    )
    failures_v5 = _load(FAILURES_V5)
    assert failures_v5["authoritative_predecessor"]["sha256"] == _sha(FAILURES_V4)
    assert failures_v5["delta_failures"][0]["attempt_id"] == (
        "campaign168_infrastructure_007"
    )
    failures_v6 = _load(FAILURES_V6)
    assert failures_v6["authoritative_predecessor"]["sha256"] == _sha(FAILURES_V5)
    assert failures_v6["delta_failures"][0]["attempt_id"] == (
        "campaign168_infrastructure_008"
    )
    failures_v7 = _load(FAILURES_V7)
    assert failures_v7["authoritative_predecessor"]["sha256"] == _sha(FAILURES_V6)
    assert failures_v7["delta_failures"][0]["attempt_id"] == (
        "campaign168_infrastructure_009"
    )
    failures = _load(FAILURES)
    assert failures["authoritative_predecessor"]["sha256"] == _sha(FAILURES_V7)
    assert failures["delta_failures"][0]["attempt_id"] == (
        "campaign168_infrastructure_010"
    )
    assert failures["effective_failure_count"] == 10
    assert (
        failures["unrecovered_or_unrecorded_failed_exit_codes_bypassed_or_masked"]
        is False
    )

    frontier = _load(FRONTIER)
    assert (
        len(
            frontier["mandatory_source_admission_gate"][
                "must_freeze_before_any_formula_or_direction"
            ]
        )
        == 12
    )
    assert (
        frontier["mandatory_source_admission_gate"][
            "formula_direction_parameter_filter_subset_combination_or_model_choice_allowed_before_gate"
        ]
        is False
    )
    assert (
        frontier["research_boundary"][
            "source_row_document_title_body_kpi_candidate_comparator_price_or_return_value_read"
        ]
        is False
    )

    ledger_v1 = _load(LEDGER_V1)
    predecessor = ledger_v1["authoritative_predecessor"]
    assert _sha(ROOT / predecessor["path"]) == predecessor["sha256"]
    previous = predecessor["chain_tip_sha256"]
    for entry in ledger_v1["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign168",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode()).hexdigest()
        assert entry["entry_sha256"] == previous
        assert entry["candidate_comparator_price_or_return_value_read"] is False
    assert previous == ledger_v1["chain_tip_sha256"]
    assert ledger_v1["effective_entry_count"] == 9

    for ledger_path in (
        LEDGER_V2,
        LEDGER_V3,
        LEDGER_V4,
        LEDGER_V5,
        LEDGER_V6,
        LEDGER_V7,
        LEDGER,
    ):
        ledger = _load(ledger_path)
        predecessor = ledger["authoritative_predecessor"]
        assert _sha(ROOT / predecessor["path"]) == predecessor["sha256"]
        assert predecessor["chain_tip_sha256"] == previous
        for entry in ledger["delta_entries"]:
            assert entry["previous_entry_sha256"] == previous
            payload = "|".join(
                [
                    "campaign168",
                    entry["attempt_id"],
                    previous,
                    entry["phase"],
                    entry["status"],
                ]
            )
            previous = hashlib.sha256(payload.encode()).hexdigest()
            assert entry["entry_sha256"] == previous
            assert entry["candidate_comparator_price_or_return_value_read"] is False
        assert previous == ledger["chain_tip_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 17
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 10
    assert ledger["cumulative_historical_research_attempt_count"] == 1480
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign168_library_policy_and_candidate49_boundaries() -> None:
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
    assert policy["complete_historical_feature_library"]["unchanged_from_v245"]
    assert policy["numerical_comparator_eligibility"]["unchanged_from_v245"]
    assert policy["future_campaign_boundary"]["next_campaign"] == 169
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert policy["candidate49"]["signal_entry_count"] == 0
    assert policy["candidate49"]["execution_entry_count"] == 0


def test_campaign168_reports_are_appended_exactly_once() -> None:
    heading = "## Campaign168 经营规模、采用与利用率 KPI 来源前沿值前终止"
    report_text = REPORT.read_text(encoding="utf-8")
    assert "17 次尝试（7 科学、10 基础设施）" in report_text
    for report_path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = report_path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "Campaign168 共 9 次尝试（7 科学、2 基础设施）" in text
        assert text.count("### Campaign168 有效验证基础设施会计追加") == 1
        assert "Campaign168 有效会计为 11 次尝试（7 科学、4 基础设施）" in text
        assert text.count("### Campaign168 时间与绑定恢复最终会计") == 1
        assert "Campaign168 最终有效会计为 13 次尝试（7 科学、6 基础设施）" in text
        assert text.count("### Campaign168 第二项时间校正最终会计") == 1
        assert "Campaign168 最终有效会计为 14 次尝试（7 科学、7 基础设施）" in text
        assert text.count("### Campaign168 测试补丁恢复最终会计") == 1
        assert "Campaign168 最终有效会计为 15 次尝试（7 科学、8 基础设施）" in text
        assert text.count("### Campaign168 累计回归节点恢复会计") == 1
        assert "Campaign168 最终有效会计为 16 次尝试（7 科学、9 基础设施）" in text
        assert text.count("### Campaign168 累计回归启动器恢复会计") == 1
        assert "Campaign168 最终有效会计为 17 次尝试（7 科学、10 基础设施）" in text


def test_campaign168_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (
        FAILURES_V1,
        FAILURES_V2,
        FAILURES_V3,
        FAILURES_V4,
        FAILURES_V5,
        FAILURES_V6,
        FAILURES_V7,
        FAILURES,
        TIMESTAMP_CORRECTION_V1,
        TIMESTAMP_CORRECTION,
        FRONTIER,
        LEDGER_V1,
        LEDGER_V2,
        LEDGER_V4,
        LEDGER_V5,
        LEDGER_V6,
        LEDGER_V7,
        LEDGER,
        TERMINAL_V1,
        TERMINAL,
        POLICY,
    ):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at

    correction_v1 = _load(TIMESTAMP_CORRECTION_V1)["corrected_record"]
    assert correction_v1["path"] == POLICY_V1.relative_to(ROOT).as_posix()
    assert correction_v1["sha256"] == _sha(POLICY_V1)
    assert (
        correction_v1["invalid_declared_recorded_at"]
        > correction_v1["original_file_mtime"]
    )
    correction = _load(TIMESTAMP_CORRECTION)
    assert correction["authoritative_predecessor"]["sha256"] == _sha(
        TIMESTAMP_CORRECTION_V1
    )
    delta = correction["delta_correction"]
    assert delta["path"] == LEDGER_V3.relative_to(ROOT).as_posix()
    assert delta["sha256"] == _sha(LEDGER_V3)
    assert delta["invalid_declared_recorded_at"] > delta["original_file_mtime"]
