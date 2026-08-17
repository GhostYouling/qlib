"""Terminal evidence tests for historical Campaign053."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import scripts.a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
CROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_053"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_053_research_record.json"
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign053_verified.json"
AUDIT = CROOT / "no_return/20260803T125238Z_campaign053_no_return_audit.json"
FACTOR = "intraday_amount_price_discovery_alignment_js_238p"
DUPLICATE = "intraday_price_update_share_238m"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign053_terminal_bindings_are_current() -> None:
    result = bindings.validate_record(RECORD, data_root=DATA_ROOT)
    assert result["all_bindings_passed"] is True


def test_campaign053_attempt_ledger_is_complete_and_append_only() -> None:
    ledger = load(CROOT / "research_attempt_ledger.json")
    assert ledger["append_only"] is True
    assert ledger["campaign053_attempt_count"] == 2
    assert ledger["campaign053_infrastructure_only_failure_count"] == 1
    assert ledger["campaign053_complete_factor_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 302
    assert ledger["campaign053_historical_return_trial_count"] == 0
    assert ledger["cumulative_return_reading_development_trial_count"] == 266
    assert [entry["sequence"] for entry in ledger["entries"]] == [1, 2]


def test_campaign053_coverage_passed_but_uniqueness_failed_before_returns() -> None:
    record = load(RECORD)
    result = record["no_return_result"]
    assert result["median_coverage"] > result["minimum_median_coverage"]
    assert result["p05_coverage"] > result["minimum_p05_coverage"]
    assert result["p05_eligible_names"] >= result["minimum_p05_eligible_names"]
    assert result["potential_three_session_cohorts"] == 540
    assert result["comparison_factor_count"] == 76
    assert result["comparison_order_matches_preregistration"] is True
    assert result["failed_comparison_count"] == 1
    assert result["failed_comparison_factor"] == DUPLICATE
    assert result["maximum_absolute_median_daily_rank_correlation"] == 0.8528583420588608
    assert result["historical_daily_price_fields_read"] == []
    assert result["historical_forward_return_fields_read"] is False


def test_campaign053_audit_verified_every_frozen_snapshot_and_boundary() -> None:
    audit = load(AUDIT)
    uniqueness = audit["uniqueness"][FACTOR]
    assert sha256(AUDIT) == "8228e32422686d020bdf7c6b00e54469d025884c23c234b48088428280bfd3ba"
    assert uniqueness["comparison_factor_count"] == 76
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["campaign051_snapshot_file_verification"]["isolated_exact_campaign051_output_columns"][-2:] == [
        "intraday_close_range_occupancy_entropy_10b",
        "intraday_close_range_occupancy_entropy_10b_eligible",
    ]
    assert audit["source_fields_read"] == ["datetime", "symbol", "provider", "close", "amount"]
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["training_or_model_fitting_performed"] is False


def test_campaign053_development_and_stress_stayed_closed() -> None:
    state = load(STATE)
    campaign = state["campaign053"]
    assert campaign["development"]["folds_opened"] is False
    assert campaign["development"]["trial_count"] == 0
    assert campaign["stress_2024_2025"]["opened"] is False
    assert campaign["stress_2024_2025"]["return_fields_read"] is False
    assert state["cumulative_state"]["current_historical_aggregation_candidate_count"] == 0


def test_campaign053_candidate49_ledgers_are_unchanged() -> None:
    signal = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    execution = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    assert sha256(signal) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert sha256(execution) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"


def test_campaign053_formula_is_terminal_without_rescue() -> None:
    record = load(RECORD)
    assert record["factor_definition"]["name"] == FACTOR
    assert record["factor_definition"]["direction"] == "higher"
    assert record["decision"]["factor_terminal"] is True
    assert record["decision"]["inversion_rewindow_rescale_threshold_filter_subset_model_combination_rerun_or_rescue_allowed"] is False


def test_unified_report_contains_campaign053_terminal_result() -> None:
    report = (ROOT / "data/experiments/short_horizon/three_day_research_report.md").read_text()
    assert "## 历史滚动 Campaign053 权威追加" in report
    assert "`0.852858`" in report
    assert "累计历史研究尝试由 300 推进到 302" in report
