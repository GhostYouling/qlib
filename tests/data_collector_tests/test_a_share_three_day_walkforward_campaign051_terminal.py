"""Post-result immutable evidence tests for terminal Campaign051."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.a_share_three_day_preregistration_binding_validator as bindings
import scripts.a_share_three_day_walkforward_campaign051 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_051"
WALKFORWARD = CAMPAIGN_ROOT / "walkforward"
RESEARCH_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_051_research_record_v3.json"
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"


def load(name: str) -> dict:
    return json.loads((WALKFORWARD / name).read_text())


def test_campaign051_exactly_one_frozen_trial_reached_development() -> None:
    ledger = load("trial_ledger.json")
    assert len(ledger["entries"]) == 1
    entry = ledger["entries"][0]
    assert entry["trial_id"] == "wf051_intraday_close_range_occupancy_entropy_10b_single_higher"
    assert [fold["validation_metrics"]["start"][:4] for fold in entry["training_and_validation_folds"]] == ["2021", "2022", "2023"]


def test_campaign051_terminal_rejection_metrics_are_preserved() -> None:
    survivors = load("development_survivors.json")
    decision = survivors["trial_decisions"][0]
    assert survivors["selected_survivor_count"] == 0
    assert decision["complexity"] == 1
    assert decision["operationally_admissible"] is False
    assert decision["operational_rejection_reasons"] == ["fold_1_board_lot_affordability"]
    assert decision["positive_mean_rank_ic_fold_count"] == 2
    assert decision["positive_normalized_return_fold_count"] == 0
    assert decision["positive_pilot_return_fold_count"] == 1
    assert decision["median_validation_mean_rank_ic"] == pytest.approx(0.003607376715204383)
    assert decision["median_validation_normalized_return"] == pytest.approx(-0.08586244150600875)
    assert decision["median_validation_pilot_return"] == pytest.approx(-0.0309623094165401)
    assert decision["worst_validation_normalized_drawdown"] == pytest.approx(-0.3062616645776082)
    assert decision["development_aggregate_20bp_return"] == pytest.approx(-0.14030842434245971)


def test_campaign051_did_not_open_2024_2025() -> None:
    stress = load("exposed_stress_consumption_record.json")
    report = load("campaign_report.json")
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert stress["selected_survivor_count"] == 0
    assert report["selected_exposed_stress_survivor_count"] == 0
    assert report["exposed_stress"] == stress


def test_campaign051_keeps_candidate49_ledgers_immutable() -> None:
    assert campaign._sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert campaign._sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"


def test_campaign051_terminal_research_bindings_and_attempts_are_current() -> None:
    result = bindings.validate_record(RESEARCH_RECORD, data_root=Path("/Volumes/DIsk/qlib-a-share-tushare-1m"))
    assert result["all_bindings_passed"] is True
    ledger = json.loads((CAMPAIGN_ROOT / "research_attempt_ledger_v3.json").read_text())
    assert ledger["append_only"] is True
    assert ledger["campaign051_attempt_count"] == 10
    assert ledger["campaign051_ledger_entry_count"] == 11
    assert ledger["campaign051_infrastructure_only_failure_count"] == 9
    assert ledger["cumulative_historical_research_attempt_count"] == 296
    assert ledger["campaign051_historical_return_trial_count"] == 1
    assert ledger["cumulative_return_reading_development_trial_count"] == 266
    assert [entry["sequence"] for entry in ledger["entries"]] == list(range(1, 12))
    assert ledger["entries"][8]["parent_sequence"] == 8
    assert ledger["entries"][8]["research_attempt_count_increment"] == 0


def test_unified_report_contains_campaign051_terminal_result() -> None:
    report = (REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md").read_text()
    assert "## 历史滚动 Campaign051 权威追加" in report
    assert "最大绝对中位日秩相关为 `0.282850`" in report
    assert "累计历史研究尝试由 286 推进到 296" in report
    assert "累计读取开发收益的试验由 265 推进到 266" in report
