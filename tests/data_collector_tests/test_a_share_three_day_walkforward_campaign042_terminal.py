"""Post-result immutable evidence tests for terminal Campaign042."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

import scripts.a_share_three_day_walkforward_campaign042 as campaign
import scripts.a_share_three_day_preregistration_binding_validator as bindings


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_SHA256 = (
    "a3d97e31d956e30325e1d771e8b9452e4e61fbffaa2d9ad6d6159c9f63b48d41"
)
RESEARCH_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_042_research_record.json"
)


def test_campaign042_status_is_terminal_with_closed_stress() -> None:
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


def test_campaign042_terminal_record_preserves_all_rejections() -> None:
    root = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_042"
        / "walkforward"
    )
    ledger = json.loads((root / "trial_ledger.json").read_text())
    survivors = json.loads((root / "development_survivors.json").read_text())
    stress = json.loads(
        (root / "exposed_stress_consumption_record.json").read_text()
    )
    record = json.loads(RESEARCH_RECORD.read_text())

    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["complexity"] == 1
    assert decision["operationally_admissible"] is True
    assert decision["operational_rejection_reasons"] == []
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 0
    assert decision["positive_normalized_return_fold_count"] == 0
    assert decision["positive_pilot_return_fold_count"] == 0
    assert decision["median_validation_mean_rank_ic"] == pytest.approx(
        -0.002932028642535807
    )
    assert decision["development_aggregate_20bp_return"] == pytest.approx(
        -0.18965983120625274
    )
    assert decision["validation_quality_rejection_reasons"] == [
        "insufficient_positive_ic_folds",
        "median_validation_mean_rank_ic",
        "median_validation_spread",
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


def test_campaign042_research_record_preserves_historical_report_binding() -> None:
    result = bindings.validate_record(RESEARCH_RECORD)
    assert result["binding_count"] == 23
    assert result["passed_binding_count"] == 22
    assert result["failed_binding_count"] == 1
    failure = result["failed_bindings"][0]
    assert failure["json_pointer"] == (
        "/development_artifacts/unified_research_report"
    )
    assert failure["expected_sha256"] == (
        "ab08fecf964efbb664daa18361fb7c3e8ba12b992aef469446c2c72738e2b3ff"
    )
    assert failure["exists"] is True
    assert failure["observed_sha256"] != failure["expected_sha256"]


def test_unified_report_contains_campaign042_terminal_result() -> None:
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign042 权威追加" in report
    assert "最大绝对中位日秩相关为 `0.041753`" in report
    assert (
        "0/5/10/20bp 整手收益为 "
        "`-2.146893%/-7.421575%/-11.867364%/-18.965983%`"
    ) in report
    assert "累计历史开发试验推进到 260" in report
