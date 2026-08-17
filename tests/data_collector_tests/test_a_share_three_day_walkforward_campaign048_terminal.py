"""Post-result immutable evidence tests for terminal Campaign048."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.a_share_three_day_preregistration_binding_validator as bindings
import scripts.a_share_three_day_walkforward_campaign048_v2 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_048"
)
RESEARCH_RECORD = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_research_record.json"
)
SIGNAL_LEDGER = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def test_campaign048_research_record_bindings_are_current() -> None:
    result = bindings.validate_record(RESEARCH_RECORD)
    assert result["all_bindings_passed"] is True
    assert result["failed_binding_count"] == 0


def test_campaign048_attempt_ledger_counts_every_distinct_attempt() -> None:
    ledger = json.loads(
        (CAMPAIGN_ROOT / "research_attempt_ledger_v2.json").read_text()
    )
    assert ledger["append_only"] is True
    assert ledger["campaign048_attempt_count"] == 5
    assert ledger["campaign048_ledger_entry_count"] == 6
    assert ledger["cumulative_historical_research_attempt_count"] == 279
    assert ledger["campaign048_historical_return_trial_count"] == 1
    assert ledger["cumulative_return_reading_development_trial_count"] == 264
    assert [entry["sequence"] for entry in ledger["entries"]] == [1, 2, 3, 4, 5, 6]
    assert ledger["entries"][4]["parent_sequence"] == 3
    assert ledger["entries"][4]["research_attempt_count_increment"] == 0
    assert ledger["entries"][4]["historical_forward_return_fields_read"] is True
    assert ledger["entries"][4]["2024_2025_stress_return_fields_read"] is False


def test_campaign048_terminal_decision_preserves_all_rejections() -> None:
    root = CAMPAIGN_ROOT / "walkforward"
    trial = json.loads((root / "trial_ledger.json").read_text())
    survivors = json.loads((root / "development_survivors.json").read_text())
    stress = json.loads(
        (root / "exposed_stress_consumption_record.json").read_text()
    )
    record = json.loads(RESEARCH_RECORD.read_text())

    assert len(trial["entries"]) == 1
    assert trial["entries"][0]["trial_id"] == campaign.FROZEN_TRIAL_ID
    decision = survivors["trial_decisions"][0]
    assert decision["complexity"] == 1
    assert decision["operationally_admissible"] is True
    assert decision["operational_rejection_reasons"] == []
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 0
    assert decision["positive_normalized_return_fold_count"] == 0
    assert decision["positive_pilot_return_fold_count"] == 0
    assert decision["median_validation_mean_rank_ic"] == pytest.approx(
        -0.008993671581631607
    )
    assert decision["development_aggregate_20bp_return"] == pytest.approx(
        -0.16744958272895138
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


def test_campaign048_keeps_candidate49_ledgers_immutable() -> None:
    assert campaign._sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert campaign._sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_unified_report_contains_campaign048_terminal_result() -> None:
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign048 权威追加" in report
    assert "最大绝对中位日秩相关为 `0.173857`" in report
    assert "10bp/20bp 整手收益为 `-8.699285%/-16.744958%`" in report
    assert "累计历史研究尝试由 274 推进到 279" in report
    assert "累计读取开发收益的试验由 263 推进到 264" in report
