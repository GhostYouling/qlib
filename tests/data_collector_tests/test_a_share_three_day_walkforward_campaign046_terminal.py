"""Post-result immutable evidence tests for terminal Campaign046."""

from __future__ import annotations

import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign046_features as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_RECORD = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_046_research_record.json"
)
AUDIT_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_046_no_return_audit_freeze_20260801.json"
)
AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_046"
    / "no_return/20260801T003958Z_campaign046_no_return_audit.json"
)
ATTEMPT_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_046"
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


def test_campaign046_research_record_bindings_are_current() -> None:
    result = bindings.validate_record(RESEARCH_RECORD)
    assert result["all_bindings_passed"] is True
    assert result["passed_binding_count"] == 21


def test_campaign046_no_return_freeze_bindings_are_current() -> None:
    result = bindings.validate_record(AUDIT_FREEZE)
    assert result["all_bindings_passed"] is True
    assert result["passed_binding_count"] == 9


def test_campaign046_uniqueness_failure_stopped_before_returns() -> None:
    audit = json.loads(AUDIT.read_text())
    factor = campaign.FACTOR_NAME
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]]

    assert audit["status"] == (
        "completed_zero_admissible_factors_stop_before_historical_returns"
    )
    assert audit["admissible_factor_count"] == 0
    assert coverage["median_coverage"] == 0.9981884043107445
    assert coverage["p05_coverage"] == 0.9928739107791087
    assert coverage["potential_non_overlapping_three_session_cohorts"] == 540
    assert coverage["gate_passed_before_comparison_values"] is True
    assert uniqueness["comparison_factor_count"] == 69
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_comparisons_passed"] is False
    assert len(failed) == 1
    assert failed[0]["comparison_factor"] == (
        "intraday_five_minute_variance_ratio_230w"
    )
    assert failed[0]["median_daily_rank_correlation"] == -0.8177575304876467
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["candidate49_historical_return_read"] is False
    assert audit["candidate49_prospective_ledgers_changed"] is False


def test_campaign046_attempt_ledger_counts_every_failure_and_candidate() -> None:
    ledger = json.loads(ATTEMPT_LEDGER.read_text())
    entries = ledger["entries"]

    assert ledger["append_only"] is True
    assert ledger["campaign046_attempt_count"] == 3
    assert ledger["cumulative_historical_research_attempt_count"] == 270
    assert ledger["campaign046_historical_return_trial_count"] == 0
    assert ledger["cumulative_return_reading_development_trial_count"] == 262
    assert [entry["sequence"] for entry in entries] == [1, 2, 3]
    assert [entry["kind"] for entry in entries] == [
        "infrastructure_only_failure",
        "infrastructure_only_failure",
        "single_factor_ordered_no_return_gate",
    ]
    assert all(entry["historical_forward_return_fields_read"] is False for entry in entries)


def test_campaign046_keeps_candidate49_ledgers_immutable() -> None:
    assert campaign._sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert campaign._sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_unified_report_contains_campaign046_terminal_result() -> None:
    report = (
        REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign046 权威追加" in report
    assert "中位/P05 覆盖为 `99.818840%/99.287391%`" in report
    assert "累计历史研究尝试由 267 推进到 270" in report
    assert "累计读取开发收益的试验仍为 262" in report
