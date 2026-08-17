from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_172_enterprise_insurance_risk_transfer_source_frontier_20260815.json"
)
FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_172_report_append_failure_20260815.json"
)
CUMULATIVE_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_172_cumulative_regression_failure_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_172/research_attempt_ledger.json"
)
RECOVERY_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_172/research_attempt_ledger_v2.json"
)
EFFECTIVE_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_172/research_attempt_ledger_v3.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_172_terminal_result_v3_20260815.json"
)
REPORT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_172_terminal_report_v3_20260815.md"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v254_20260815.json"
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


def _verify_bindings(record: dict) -> None:
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


def test_campaign172_bindings_and_finite_frontier() -> None:
    for record_path in (FRONTIER, TERMINAL, POLICY):
        _verify_bindings(_load(record_path))

    routes = _load(FRONTIER)["finite_prevalue_catalog"]
    assert [item["catalog_id"] for item in routes] == [
        f"c172_0{i}" for i in range(1, 8)
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


def test_campaign172_source_gate_failure_and_attempt_chain() -> None:
    frontier = _load(FRONTIER)
    gate = frontier["mandatory_source_admission_gate"]
    assert len(gate["must_freeze_before_any_formula_or_direction"]) == 12
    assert (
        gate[
            "formula_direction_parameter_filter_subset_combination_or_model_choice_allowed_before_gate"
        ]
        is False
    )
    assert (
        frontier["research_boundary"][
            "source_row_policy_claim_filing_document_insurance_value_candidate_comparator_security_price_or_return_value_read"
        ]
        is False
    )

    previous = _load(LEDGER)["authoritative_predecessor"]["chain_tip_sha256"]
    for ledger_path in (LEDGER, RECOVERY_LEDGER, EFFECTIVE_LEDGER):
        ledger = _load(ledger_path)
        predecessor = ledger["authoritative_predecessor"]
        assert _sha(ROOT / predecessor["path"]) == predecessor["sha256"]
        assert predecessor["chain_tip_sha256"] == previous
        for entry in ledger["delta_entries"]:
            assert entry["previous_entry_sha256"] == previous
            payload = "|".join(
                [
                    "campaign172",
                    entry["attempt_id"],
                    previous,
                    entry["phase"],
                    entry["status"],
                ]
            )
            previous = hashlib.sha256(payload.encode()).hexdigest()
            assert entry["entry_sha256"] == previous
            assert (
                entry["candidate_comparator_security_price_or_return_value_read"]
                is False
            )
        assert previous == ledger["chain_tip_sha256"]

    effective = _load(EFFECTIVE_LEDGER)
    assert effective["campaign_effective_entry_count"] == 9
    assert effective["campaign_effective_prevalue_scientific_attempt_count"] == 7
    assert effective["campaign_effective_infrastructure_failure_attempt_count"] == 2
    assert effective["cumulative_historical_research_attempt_count"] == 1518
    assert effective["cumulative_return_reading_development_trial_count"] == 314
    failure = _load(FAILURE)
    assert failure["attempt"]["write_result"] == "zero_write"
    assert failure["attempt"]["campaign172_heading_count_after_failure"] == {
        "current_research_report": 0,
        "three_day_research_report": 0,
    }
    cumulative_failure = _load(CUMULATIVE_FAILURE)
    assert cumulative_failure["attempt"]["result"] == {
        "tests_passed": 374,
        "tests_skipped": 1,
        "tests_failed": 5,
        "tests_deselected": 0,
        "duration_seconds": 10.40,
    }


def test_campaign172_library_policy_and_candidate49_boundaries() -> None:
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
    assert policy["complete_historical_feature_library"]["unchanged_from_v253"]
    assert policy["numerical_comparator_eligibility"]["unchanged_from_v253"]
    assert policy["future_campaign_boundary"]["next_campaign"] == 173
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    lifecycle = policy["cumulative_regression_boundary"][
        "corrected_required_exact_historical_lifecycle_nodes"
    ]
    assert len(lifecycle) == 5
    assert len(set(lifecycle)) == 5
    assert (
        policy["cumulative_regression_boundary"][
            "campaign172_policy_binds_mutable_reports_as_current_hashes"
        ]
        is False
    )
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert policy["candidate49"]["signal_entry_count"] == 0
    assert policy["candidate49"]["execution_entry_count"] == 0


def test_campaign172_reports_are_appended_exactly_once() -> None:
    heading = "## Campaign172 企业保险与风险转移来源前沿值前终止"
    assert "9 次尝试（7 科学、2 基础设施）" in REPORT.read_text(encoding="utf-8")
    for report_path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = report_path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "Campaign172 最终有效会计为 8 次尝试（7 科学、1 基础设施）" in text
        assert text.count("### Campaign172 累计回归精确节点恢复会计") == 1
        assert "Campaign172 当前有效会计为 9 次尝试（7 科学、2 基础设施）" in text


def test_campaign172_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (
        FRONTIER,
        FAILURE,
        CUMULATIVE_FAILURE,
        LEDGER,
        RECOVERY_LEDGER,
        EFFECTIVE_LEDGER,
        TERMINAL,
        POLICY,
    ):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at
