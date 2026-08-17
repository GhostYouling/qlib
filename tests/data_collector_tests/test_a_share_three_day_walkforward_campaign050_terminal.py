"""Post-result immutable evidence tests for terminal Campaign050."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.a_share_three_day_preregistration_binding_validator as bindings
import scripts.a_share_three_day_walkforward_campaign050_v3 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_050"
)
WALKFORWARD = CAMPAIGN_ROOT / "walkforward"
RESEARCH_RECORD = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_050_research_record_v2.json"
)
SIGNAL_LEDGER = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def load(name: str) -> dict:
    return json.loads((WALKFORWARD / name).read_text())


def test_campaign050_exactly_one_frozen_trial_reached_development() -> None:
    ledger = load("trial_ledger.json")
    assert len(ledger["entries"]) == 1
    entry = ledger["entries"][0]
    assert entry["trial_id"] == (
        "wf050_intraday_half_session_extreme_shock_reversal_completion_2h_"
        "single_higher"
    )
    assert len(entry["training_and_validation_folds"]) == 3
    assert [
        fold["validation_metrics"]["start"][:4]
        for fold in entry["training_and_validation_folds"]
    ] == ["2021", "2022", "2023"]


def test_campaign050_terminal_decision_preserves_rejection_metrics() -> None:
    survivors = load("development_survivors.json")
    decision = survivors["trial_decisions"][0]
    assert survivors["selected_survivor_count"] == 0
    assert decision["complexity"] == 1
    assert decision["operationally_admissible"] is True
    assert decision["operational_rejection_reasons"] == []
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 2
    assert decision["positive_normalized_return_fold_count"] == 1
    assert decision["positive_pilot_return_fold_count"] == 1
    assert decision["median_validation_mean_rank_ic"] == pytest.approx(
        0.0005635670666854743
    )
    assert decision["median_validation_normalized_return"] == pytest.approx(
        -0.16237229490099314
    )
    assert decision["median_validation_pilot_return"] == pytest.approx(
        -0.046999906704844885
    )
    assert decision["worst_validation_normalized_drawdown"] == pytest.approx(
        -0.26793059522643603
    )
    assert decision["development_aggregate_20bp_return"] == pytest.approx(
        -0.1840317181252532
    )
    assert decision["validation_quality_rejection_reasons"] == [
        "median_validation_spread",
        "insufficient_positive_normalized_return_folds",
        "insufficient_positive_pilot_return_folds",
        "median_validation_pilot_return",
        "worst_validation_normalized_drawdown",
        "nonpositive_development_aggregate_20bp_return",
    ]


def test_campaign050_did_not_open_2024_2025() -> None:
    stress = load("exposed_stress_consumption_record.json")
    report = load("campaign_report.json")
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert stress["selected_survivor_count"] == 0
    assert report["selected_exposed_stress_survivor_count"] == 0
    assert report["exposed_stress"] == stress


def test_campaign050_survivor_value_hash_is_not_file_byte_hash() -> None:
    survivors = load("development_survivors.json")
    stress = load("exposed_stress_consumption_record.json")
    assert stress["survivor_record_sha256"] == campaign.base.value_sha256(
        survivors
    )
    assert stress["survivor_record_sha256"] != campaign._sha256(
        WALKFORWARD / "development_survivors.json"
    )


def test_campaign050_keeps_candidate49_ledgers_immutable() -> None:
    assert campaign._sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert campaign._sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_campaign050_terminal_research_bindings_and_attempts_are_current() -> None:
    result = bindings.validate_record(RESEARCH_RECORD)
    assert result["all_bindings_passed"] is True
    ledger = json.loads((CAMPAIGN_ROOT / "research_attempt_ledger_v2.json").read_text())
    assert ledger["append_only"] is True
    assert ledger["campaign050_attempt_count"] == 6
    assert ledger["campaign050_ledger_entry_count"] == 7
    assert ledger["cumulative_historical_research_attempt_count"] == 286
    assert ledger["campaign050_historical_return_trial_count"] == 1
    assert ledger["cumulative_return_reading_development_trial_count"] == 265
    assert [entry["sequence"] for entry in ledger["entries"]] == [1, 2, 3, 4, 5, 6, 7]
    assert ledger["entries"][5]["parent_sequence"] == 3
    assert ledger["entries"][5]["research_attempt_count_increment"] == 0


def test_unified_report_contains_campaign050_terminal_result() -> None:
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign050 权威追加" in report
    assert "最大绝对中位日秩相关为 `0.149511`" in report
    assert "累计历史研究尝试由 280 推进到 286" in report
    assert "累计读取开发收益的试验由 264 推进到 265" in report
