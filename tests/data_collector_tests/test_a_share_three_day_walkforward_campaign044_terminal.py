"""Post-result immutable evidence tests for terminal Campaign044."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign044_features as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_044_research_record.json"
)
AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_044"
    / "no_return/20260731T191808Z_campaign044_no_return_audit.json"
)
ATTEMPT_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_044"
    / "research_attempt_ledger.json"
)
SIGNAL_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def test_campaign044_research_record_bindings_are_current() -> None:
    result = bindings.validate_record(RESEARCH_RECORD)
    assert result["all_bindings_passed"] is True
    assert result["passed_binding_count"] == 18


def test_campaign044_coverage_failure_stopped_before_correlations_and_returns() -> None:
    audit = json.loads(AUDIT.read_text())
    factor = campaign.FACTOR_NAME
    coverage = audit["coverage_and_capacity"][factor]
    dominance = audit["single_component_dominance"][factor]

    assert audit["status"] == (
        "completed_zero_admissible_factors_stop_before_historical_returns"
    )
    assert audit["admissible_factor_count"] == 0
    assert coverage["median_coverage"] == 0.5171763636653539
    assert coverage["p05_coverage"] == 0.3499289453372031
    assert coverage["potential_non_overlapping_three_session_cohorts"] == 539
    assert coverage["gate_passed_before_comparison_values"] is False
    assert dominance["source_component_values_reloaded_after_coverage_pass"] is False
    assert dominance["comparisons"] == []
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["candidate49_factor_values_read"] is False
    assert audit["candidate49_prospective_ledgers_changed"] is False


def test_campaign044_attempt_ledger_counts_every_design_and_failure() -> None:
    ledger = json.loads(ATTEMPT_LEDGER.read_text())
    entries = ledger["entries"]

    assert ledger["append_only"] is True
    assert ledger["campaign044_attempt_count"] == 4
    assert ledger["cumulative_historical_research_attempt_count"] == 265
    assert ledger["historical_return_trial_count"] == 0
    assert [entry["sequence"] for entry in entries] == [1, 2, 3, 4]
    assert [entry["kind"] for entry in entries] == [
        "pre_value_design_rejection",
        "pre_value_design_rejection",
        "infrastructure_only_failure",
        "fixed_equal_weight_complete_terminal_library_combination",
    ]
    assert all(entry["historical_forward_return_fields_read"] is False for entry in entries)
    assert all(entry["candidate49_factor_values_read"] is False for entry in entries)


def test_campaign044_keeps_candidate49_ledgers_immutable() -> None:
    assert campaign._sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert campaign._sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_unified_report_contains_campaign044_terminal_result() -> None:
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign044 权威追加" in report
    assert "中位/P05 覆盖为 `51.717636%/34.992895%`" in report
    assert "累计历史研究尝试由 261 推进到 265" in report
    assert "其中读取开发收益的试验累计仍为 261" in report
