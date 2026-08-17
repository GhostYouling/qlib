"""Post-result immutable evidence tests for terminal Campaign038."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

import scripts.a_share_three_day_walkforward_campaign038 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_SHA256 = (
    "09324d96780d48be9550a22aa13501fece00070571d0c5503e4c437525dfc312"
)


def test_campaign038_status_is_terminal_with_closed_stress() -> None:
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


def test_campaign038_terminal_record_preserves_all_rejections() -> None:
    root = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_038"
        / "walkforward"
    )
    record_path = (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_038_research_record.json"
    )
    ledger = json.loads((root / "trial_ledger.json").read_text())
    survivors = json.loads((root / "development_survivors.json").read_text())
    stress = json.loads(
        (root / "exposed_stress_consumption_record.json").read_text()
    )
    record = json.loads(record_path.read_text())
    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["complexity"] == 1
    assert decision["operationally_admissible"] is True
    assert decision["operational_rejection_reasons"] == []
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 3
    assert decision["positive_normalized_return_fold_count"] == 0
    assert decision["positive_pilot_return_fold_count"] == 0
    assert decision["median_validation_mean_rank_ic"] == pytest.approx(
        0.020183888633279735
    )
    assert decision["development_aggregate_20bp_return"] == pytest.approx(
        -0.2572644565140175
    )
    assert decision["validation_quality_rejection_reasons"] == [
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


def test_unified_report_contains_campaign038_terminal_result() -> None:
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign038 权威追加" in report
    assert "最大绝对中位日秩相关为 0.506321" in report
    assert (
        "零成本、5bp、10bp、20bp 整手收益为 "
        "-9.462748%/-13.966825%/-17.888889%/-25.726446%"
    ) in report
    assert "累计历史开发试验推进到 258" in report
