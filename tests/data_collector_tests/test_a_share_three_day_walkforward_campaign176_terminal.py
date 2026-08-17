from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_176_post_employment_benefit_source_frontier_20260815.json"
)
FAILURE_LEDGER_PATH = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_176_candidate49_signal_ledger_path_probe_failure_20260815.json"
)
FAILURE_SEARCH = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_176_overlap_search_command_rejection_20260815.json"
)
FAILURE_INSURANCE_PATH = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_176_insurance_frontier_filename_probe_failure_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_176/research_attempt_ledger_v1.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_176_terminal_result_20260815.json"
)
REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_176_terminal_report_20260815.md"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v264_20260815.json"
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


def test_campaign176_bindings_and_finite_frontier() -> None:
    for record_path in (
        FRONTIER,
        FAILURE_LEDGER_PATH,
        FAILURE_SEARCH,
        FAILURE_INSURANCE_PATH,
        TERMINAL,
        POLICY,
    ):
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

    routes = _load(FRONTIER)["finite_prevalue_catalog"]
    assert [item["catalog_id"] for item in routes] == [
        f"c176_0{i}" for i in range(1, 8)
    ]
    assert all(item["formula"] is None and item["direction"] is None for item in routes)
    assert all(
        not item["parameters_filters_subsets_combinations_models"] for item in routes
    )
    assert sum(item["new_issuer_state"] for item in routes) == 4
    assert sum(item["complete_local_source_contract"] for item in routes) == 0
    summary = _load(FRONTIER)["gate_summary"]
    assert summary["source_admission_deferrals_not_factor_failures"] == 4
    assert summary["relabeling_or_operator_route_rejections"] == 3
    assert summary["selected_candidate_count"] == 0


def test_campaign176_source_gate_and_attempt_chain() -> None:
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
            "source_row_filing_document_pension_obligation_plan_asset_contribution_candidate_comparator_security_price_or_return_value_read"
        ]
        is False
    )

    ledger = _load(LEDGER)
    predecessor = ledger["authoritative_predecessor"]
    assert _sha(ROOT / predecessor["path"]) == predecessor["sha256"]
    previous = predecessor["chain_tip_sha256"]
    for entry in ledger["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign176",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode()).hexdigest()
        assert entry["entry_sha256"] == previous
        assert (
            entry["candidate_comparator_security_price_or_return_value_read"] is False
        )
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 10
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 3
    assert ledger["cumulative_historical_research_attempt_count"] == 1560
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign176_library_policy_and_candidate49_boundaries() -> None:
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
    assert policy["complete_historical_feature_library"]["unchanged_from_v263"]
    assert policy["numerical_comparator_eligibility"]["unchanged_from_v263"]
    assert policy["future_campaign_boundary"]["next_campaign"] == 177
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


def test_campaign176_reports_are_appended_exactly_once() -> None:
    heading = "## Campaign176 养老金与离职后福利来源前沿值前终止"
    assert "10 次尝试（7 次科学、3 次基础设施）" in REPORT.read_text(encoding="utf-8")
    for report_path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = report_path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "Campaign176 共 10 次尝试（7 科学、3 基础设施）" in text


def test_campaign176_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (
        FRONTIER,
        FAILURE_LEDGER_PATH,
        FAILURE_SEARCH,
        FAILURE_INSURANCE_PATH,
        LEDGER,
        TERMINAL,
        POLICY,
    ):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at
