"""Post-result immutable evidence tests for terminal historical Campaign049."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.a_share_three_day_preregistration_binding_validator as bindings
import scripts.a_share_three_day_walkforward_campaign049_features as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_049"
RESEARCH_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_research_record.json"
AUDIT_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_no_return_audit_freeze_20260801.json"
AUDIT = CAMPAIGN_ROOT / "no_return/20260801T072440Z_campaign049_no_return_audit.json"
ATTEMPT_LEDGER = CAMPAIGN_ROOT / "research_attempt_ledger.json"
REPORT_SUPERSESSION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_unified_report_supersession_20260801.json"
CURRENT_REPORT_SUPERSESSION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_050_unified_report_supersession_v3_20260801.json"
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"


def test_campaign049_terminal_records_and_supersession_bindings_are_current() -> None:
    for path in (RESEARCH_RECORD, AUDIT_FREEZE):
        result = bindings.validate_record(path)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0
    historical = bindings.validate_record(REPORT_SUPERSESSION)
    assert historical["failed_binding_count"] == 1
    assert historical["failed_bindings"][0]["json_pointer"] == (
        "/bindings/current_unified_research_report"
    )
    current = json.loads(CURRENT_REPORT_SUPERSESSION.read_text())
    assert historical["failed_bindings"][0]["observed_sha256"] == current[
        "historical_binding"
    ]["current_sha256"]
    assert current["historical_binding"]["historical_record_rewritten"] is False
    assert bindings.validate_record(CURRENT_REPORT_SUPERSESSION)[
        "all_bindings_passed"
    ] is True


def test_campaign049_uniqueness_failure_stopped_before_returns() -> None:
    audit = json.loads(AUDIT.read_text())
    factor = campaign.FACTOR_NAME
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]]

    assert audit["status"] == "completed_zero_admissible_factors_stop_before_historical_returns"
    assert audit["admissible_factor_count"] == 0
    assert coverage["median_coverage"] == 0.9981114258734656
    assert coverage["p05_coverage"] == 0.9906542056074766
    assert coverage["gate_passed_before_comparison_values"] is True
    assert uniqueness["comparison_factor_count"] == 72
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_comparisons_passed"] is False
    assert len(failed) == 1
    assert failed[0]["comparison_factor"] == "intraday_amount_participation_entropy_240m"
    assert failed[0]["median_daily_rank_correlation"] == 0.8715970553916501
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["training_or_model_fitting_performed"] is False
    assert audit["candidate49_historical_return_read"] is False


def test_campaign049_attempt_ledger_counts_one_no_return_attempt() -> None:
    ledger = json.loads(ATTEMPT_LEDGER.read_text())
    assert ledger["append_only"] is True
    assert ledger["campaign049_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 280
    assert ledger["campaign049_historical_return_trial_count"] == 0
    assert ledger["cumulative_return_reading_development_trial_count"] == 264
    assert [entry["sequence"] for entry in ledger["entries"]] == [1]
    assert ledger["entries"][0]["historical_forward_return_fields_read"] is False


def test_campaign049_keeps_candidate49_ledgers_immutable() -> None:
    assert campaign._sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert campaign._sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"


def test_unified_report_contains_campaign049_terminal_result() -> None:
    report = (REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md").read_text()
    assert "## 历史滚动 Campaign049 权威追加" in report
    assert "中位日秩相关为 `+0.871597`" in report
    assert "累计历史研究尝试由 279 推进到 280" in report
    assert "累计读取开发收益的试验仍为 264" in report
    assert "前瞻 Candidate49 无关" in report
