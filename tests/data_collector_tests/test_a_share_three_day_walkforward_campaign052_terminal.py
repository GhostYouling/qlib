"""Terminal evidence tests for historical Campaign052."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import scripts.a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
CROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_052"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_052_research_record.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign052_verified.json"
FACTOR = "quarterly_announcement_delay_consistency_4q"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign052_terminal_bindings_are_current() -> None:
    result = bindings.validate_record(RECORD, data_root=DATA_ROOT)
    assert result["all_bindings_passed"] is True


def test_campaign052_attempt_ledger_is_complete_and_append_only() -> None:
    ledger = load(CROOT / "research_attempt_ledger.json")
    assert ledger["append_only"] is True
    assert ledger["campaign052_attempt_count"] == 4
    assert ledger["campaign052_infrastructure_only_failure_count"] == 3
    assert ledger["campaign052_complete_factor_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 300
    assert ledger["campaign052_historical_return_trial_count"] == 0
    assert ledger["cumulative_return_reading_development_trial_count"] == 266
    assert [entry["sequence"] for entry in ledger["entries"]] == [1, 2, 3, 4]


def test_campaign052_stopped_before_comparisons_prices_and_returns() -> None:
    record = load(RECORD)
    result = record["no_return_result"]
    assert result["median_coverage"] > result["minimum_median_coverage"]
    assert result["p05_coverage"] == 0.0
    assert result["p05_coverage"] < result["minimum_p05_coverage"]
    assert result["comparison_factor_count_frozen"] == 75
    assert result["comparison_values_loaded"] is False
    assert result["comparison_correlations_computed"] == 0
    assert result["historical_daily_price_fields_read"] == []
    assert result["historical_forward_return_fields_read"] is False


def test_campaign052_development_and_stress_stayed_closed() -> None:
    state = load(STATE)
    campaign = state["campaign052"]
    assert campaign["development"]["folds_opened"] is False
    assert campaign["development"]["trial_count"] == 0
    assert campaign["stress_2024_2025"]["opened"] is False
    assert campaign["stress_2024_2025"]["return_fields_read"] is False
    assert state["cumulative_state"]["current_historical_aggregation_candidate_count"] == 0


def test_campaign052_candidate49_ledgers_are_unchanged() -> None:
    signal = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    execution = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    assert sha256(signal) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert sha256(execution) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"


def test_campaign052_formula_is_terminal_without_rescue() -> None:
    record = load(RECORD)
    assert record["factor_definition"]["name"] == FACTOR
    assert record["factor_definition"]["lookback_reports"] == 4
    assert record["decision"]["factor_terminal"] is True
    assert record["decision"]["shorter_window_later_start_threshold_relaxation_imputation_filter_subset_model_combination_rerun_or_rescue_allowed"] is False


def test_unified_report_contains_campaign052_terminal_result() -> None:
    report = (ROOT / "data/experiments/short_horizon/three_day_research_report.md").read_text()
    assert "## 历史滚动 Campaign052 权威追加" in report
    assert "P05 覆盖为 `0.000000%`" in report
    assert "累计历史研究尝试由 296 推进到 300" in report
