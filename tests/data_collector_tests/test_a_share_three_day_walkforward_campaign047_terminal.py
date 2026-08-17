"""Post-result immutable evidence tests for terminal Campaign047."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.a_share_three_day_preregistration_binding_validator as bindings
import scripts.a_share_three_day_walkforward_campaign047 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_047"
)
RESEARCH_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_047_research_record.json"
)
REPORT_SUPERSESSION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_050_unified_report_supersession_v3_20260801.json"
)
SIGNAL_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def test_campaign047_research_record_bindings_are_current() -> None:
    result = bindings.validate_record(RESEARCH_RECORD)
    assert result["binding_count"] == 26
    assert result["passed_binding_count"] == 25
    assert result["failed_binding_count"] == 1
    failure = result["failed_bindings"][0]
    assert failure["json_pointer"] == (
        "/development_artifacts/unified_research_report"
    )
    supersession = json.loads(REPORT_SUPERSESSION.read_text())
    assert failure["observed_sha256"] == supersession["historical_binding"][
        "current_sha256"
    ]
    assert supersession["historical_binding"]["historical_record_rewritten"] is False
    assert bindings.validate_record(REPORT_SUPERSESSION)[
        "all_bindings_passed"
    ] is True


def test_campaign047_attempt_ledger_counts_every_distinct_attempt() -> None:
    ledger = json.loads(
        (CAMPAIGN_ROOT / "research_attempt_ledger.json").read_text()
    )
    assert ledger["append_only"] is True
    assert ledger["campaign047_attempt_count"] == 4
    assert ledger["campaign047_ledger_entry_count"] == 5
    assert ledger["cumulative_historical_research_attempt_count"] == 274
    assert ledger["campaign047_historical_return_trial_count"] == 1
    assert ledger["cumulative_return_reading_development_trial_count"] == 263
    assert [entry["sequence"] for entry in ledger["entries"]] == [1, 2, 3, 4, 5]
    assert ledger["entries"][4]["parent_sequence"] == 3
    assert ledger["entries"][4]["research_attempt_count_increment"] == 0
    assert ledger["entries"][4]["historical_forward_return_fields_read"] is True
    assert ledger["entries"][4]["2024_2025_stress_return_fields_read"] is False


def test_campaign047_terminal_decision_preserves_all_rejections() -> None:
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
    assert decision["operationally_admissible"] is True
    assert decision["operational_rejection_reasons"] == []
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 3
    assert decision["positive_normalized_return_fold_count"] == 1
    assert decision["positive_pilot_return_fold_count"] == 1
    assert decision["median_validation_mean_rank_ic"] == pytest.approx(
        0.04895330573103019
    )
    assert decision["development_aggregate_20bp_return"] == pytest.approx(
        -0.1927397534905354
    )
    assert decision["validation_quality_rejection_reasons"] == [
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


def test_campaign047_keeps_candidate49_ledgers_immutable() -> None:
    assert campaign._sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert campaign._sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_unified_report_contains_campaign047_terminal_result() -> None:
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign047 权威追加" in report
    assert "最大绝对中位日秩相关为 `0.590707`" in report
    assert "10bp/20bp 整手收益为 `-10.364923%/-19.273975%`" in report
    assert "累计历史研究尝试由 270 推进到 274" in report
    assert "累计读取开发收益的试验由 262 推进到 263" in report
