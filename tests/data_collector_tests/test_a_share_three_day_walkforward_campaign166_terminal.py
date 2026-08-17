from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_166_operational_incident_disclosure_source_frontier_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_166/research_attempt_ledger.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_166_terminal_result_20260815.json"
)
REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_166_terminal_report_20260815.md"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v238_20260815.json"
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


def test_campaign166_all_authoritative_bindings_resolve() -> None:
    for record_path in (FRONTIER, TERMINAL, POLICY):
        record = _load(record_path)
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            bound = _bound_path(binding["path"])
            assert bound.is_file()
            assert _sha(bound) == binding["sha256"]


def test_campaign166_frontier_is_finite_and_distinguishes_deferral() -> None:
    frontier = _load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert len(routes) == 6
    assert [item["catalog_id"] for item in routes] == [
        "c166_01",
        "c166_02",
        "c166_03",
        "c166_04",
        "c166_05",
        "c166_06",
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
    assert summary["terminal_or_related_route_rejections"] == 3
    assert summary["selected_candidate_count"] == 0
    assert (
        frontier["scientific_interpretation"][
            "operational_incident_disclosure_declared_ineffective"
        ]
        is False
    )


def test_campaign166_source_gate_and_research_boundary_are_closed() -> None:
    frontier = _load(FRONTIER)
    gate = frontier["mandatory_source_admission_gate"]
    assert len(gate["must_freeze_before_any_formula_or_direction"]) == 10
    assert (
        gate[
            "formula_direction_parameter_filter_subset_combination_or_model_choice_allowed_before_gate"
        ]
        is False
    )
    boundary = frontier["research_boundary"]
    assert (
        boundary[
            "announcement_row_title_body_source_candidate_comparator_price_or_return_value_read"
        ]
        is False
    )
    assert boundary["provider_or_web_request_issued"] is False
    assert boundary["stress_2024_2025_opened"] is False


def test_campaign166_attempt_chain_and_accounting_are_exact() -> None:
    ledger = _load(LEDGER)
    predecessor = ledger["authoritative_predecessor"]
    assert _sha(ROOT / predecessor["path"]) == predecessor["sha256"]
    assert predecessor["cumulative_historical_research_attempt_count"] == 1451
    previous = predecessor["chain_tip_sha256"]
    for entry in ledger["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign166",
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
    assert ledger["effective_entry_count"] == 6
    assert ledger["effective_prevalue_scientific_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 1457
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign166_preserves_library_orders_and_future_boundaries() -> None:
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
    assert policy["complete_historical_feature_library"]["unchanged_from_v237"]
    assert policy["numerical_comparator_eligibility"]["unchanged_from_v237"]
    boundary = policy["future_campaign_boundary"]
    assert boundary["next_campaign"] == 167
    assert boundary["historical_offline_prevalue_work_may_continue_at_any_local_time"]
    assert boundary["2024_2025_source_or_returns_remain_closed"] is True
    assert boundary[
        "future_cumulative_regression_must_deselect_three_exact_historical_lifecycle_nodes"
    ]


def test_campaign166_candidate49_and_prospective_boundaries_hold() -> None:
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    policy = _load(POLICY)
    assert policy["candidate49"]["signal_entry_count"] == 0
    assert policy["candidate49"]["execution_entry_count"] == 0
    assert policy["candidate49"]["ledgers_changed"] is False
    assert policy["research_boundary"]["second_prospective_candidate_created"] is False


def test_campaign166_reports_are_appended_exactly_once() -> None:
    heading = "## Campaign166 运营中断与产品事故来源前沿值前终止"
    assert "本轮共 6 次科学尝试、0 次基础设施失败" in REPORT.read_text(encoding="utf-8")
    for report_path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = report_path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "Campaign166 共 6 次科学尝试、0 次基础设施失败" in text


def test_campaign166_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (FRONTIER, LEDGER, TERMINAL, POLICY):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at
