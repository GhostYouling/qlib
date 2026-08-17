"""Post-result immutable evidence tests for terminal Campaign045."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

import scripts.a_share_three_day_preregistration_binding_validator as bindings
import scripts.a_share_three_day_walkforward_campaign045 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_SHA256 = (
    "cae090291152fd58d218346af759cfa2db840be93c58550639a617d1bfe6efe0"
)
CAMPAIGN_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_045"
)
RESEARCH_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_045_research_record.json"
)
SIGNAL_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def test_campaign045_status_is_terminal_with_closed_stress() -> None:
    result = campaign.status(
        argparse.Namespace(
            campaign=str(campaign.engine_namespace["DEFAULT_CAMPAIGN"]),
            output_root=str(campaign.engine_namespace["DEFAULT_OUTPUT_ROOT"]),
        )
    )
    assert result["campaign_sha256"] == CAMPAIGN_SHA256
    assert result["expected_trial_count"] == 1
    assert result["ledger_entry_count"] == 1
    assert result["selected_survivor_count"] == 0
    assert result["stress_intent_exists"] is False
    assert result["stress_record_exists"] is True
    assert result["stress_status"] == "not_opened_zero_development_survivors"
    assert result["candidate49_historical_return_read"] is False
    assert result["current_scoring_selection_sizing_or_orders_allowed"] is False


def test_campaign045_research_record_bindings_are_current() -> None:
    result = bindings.validate_record(RESEARCH_RECORD)
    assert result["all_bindings_passed"] is True
    assert result["binding_count"] == 26
    assert result["passed_binding_count"] == 26


def test_campaign045_attempt_ledger_counts_failure_and_exact_trial() -> None:
    ledger = json.loads(
        (CAMPAIGN_ROOT / "research_attempt_ledger.json").read_text()
    )
    assert ledger["append_only"] is True
    assert ledger["prior_historical_research_attempt_count"] == 265
    assert ledger["campaign045_attempt_count"] == 2
    assert ledger["cumulative_historical_research_attempt_count"] == 267
    assert ledger["campaign045_historical_return_trial_count"] == 1
    assert ledger["cumulative_historical_return_trial_count"] == 262
    assert [entry["sequence"] for entry in ledger["entries"]] == [1, 2]
    assert [entry["kind"] for entry in ledger["entries"]] == [
        "infrastructure_only_failure",
        "single_factor_no_return_then_2019_2023_expanding_walkforward",
    ]
    failure, trial = ledger["entries"]
    assert failure["candidate_source_values_returned"] is False
    assert failure["comparison_factor_values_read"] is False
    assert failure["historical_forward_return_fields_read"] is False
    assert trial["historical_forward_return_fields_read"] is True
    assert trial["2024_2025_stress_return_fields_read"] is False
    assert trial["candidate49_historical_return_fields_read"] is False


def test_campaign045_terminal_decision_preserves_all_rejections() -> None:
    root = CAMPAIGN_ROOT / "walkforward"
    ledger = json.loads((root / "trial_ledger.json").read_text())
    survivors = json.loads((root / "development_survivors.json").read_text())
    stress = json.loads(
        (root / "exposed_stress_consumption_record.json").read_text()
    )
    record = json.loads(RESEARCH_RECORD.read_text())

    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["complexity"] == 1
    assert decision["operationally_admissible"] is False
    assert decision["operational_rejection_reasons"] == [
        "fold_1_board_lot_affordability",
        "fold_2_board_lot_affordability",
        "fold_3_board_lot_affordability",
    ]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 0
    assert decision["positive_normalized_return_fold_count"] == 1
    assert decision["positive_pilot_return_fold_count"] == 1
    assert decision["median_validation_mean_rank_ic"] == pytest.approx(
        -0.006394714560189761
    )
    assert decision["development_aggregate_20bp_return"] == pytest.approx(
        -0.11557079653603797
    )
    assert decision["validation_quality_rejection_reasons"] == [
        "insufficient_positive_ic_folds",
        "median_validation_mean_rank_ic",
        "insufficient_positive_normalized_return_folds",
        "insufficient_positive_pilot_return_folds",
        "median_validation_pilot_return",
        "worst_validation_normalized_drawdown",
        "nonpositive_development_aggregate_20bp_return",
    ]
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert record["decision"]["factor_terminal"] is True
    assert record["decision"]["2024_2025_returns_read"] is False


def test_campaign045_keeps_candidate49_ledgers_immutable() -> None:
    assert campaign._sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert campaign._sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_unified_report_contains_campaign045_terminal_result() -> None:
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign045 权威追加" in report
    assert "最大绝对中位日秩相关为 `0.111220`" in report
    assert "开发期 20bp 累计收益为 -11.56%" in report
    assert "累计历史研究尝试为 267" in report
    assert "累计读取开发收益的试验为 262" in report
