"""Post-result immutable evidence tests for terminal Campaign035."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FACTOR = "intraday_return_weak_order_entropy_234t"
AUDIT_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_035"
    / "no_return/20260730T205353Z_campaign035_no_return_audit.json"
)
RECORD_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_035_research_record.json"
)


def test_campaign035_terminal_audit_preserves_complete_rejection() -> None:
    audit = json.loads(AUDIT_PATH.read_text())
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]

    assert audit["status"] == (
        "completed_zero_admissible_factors_stop_before_historical_returns"
    )
    assert audit["admissible_factor_count"] == 0
    assert coverage["gate_passed_before_comparison_values"] is True
    assert uniqueness["comparison_factor_count"] == 56
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_comparisons_passed"] is False
    assert len(uniqueness["comparisons"]) == 56
    failed = [
        item for item in uniqueness["comparisons"] if not item["gate_passed"]
    ]
    assert len(failed) == 1
    assert failed[0]["comparison_factor"] == "intraday_price_update_share_238m"
    assert failed[0]["median_daily_rank_correlation"] == -0.8831373194357716
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False


def test_campaign035_research_record_closes_returns_and_stress() -> None:
    record = json.loads(RECORD_PATH.read_text())

    assert record["status"] == (
        "completed_zero_no_return_admissible_factors_stop_before_historical_returns"
    )
    assert record["trial_accounting"]["development_preregistration_created"] is False
    assert record["trial_accounting"]["development_trial_count"] == 0
    assert record["trial_accounting"]["development_return_fields_read"] is False
    assert record["trial_accounting"]["stress_2024_2025_opened"] is False
    assert record["trial_accounting"]["stress_return_fields_read"] is False
    assert (
        record["trial_accounting"][
            "cumulative_historical_development_trial_count_after_campaign"
        ]
        == 255
    )
    assert record["interpretation"]["uniqueness_supported"] is False


def test_unified_report_contains_campaign035_terminal_result() -> None:
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()

    assert "## 历史滚动 Campaign035 权威追加" in report
    assert "中位日秩相关为 -0.883137" in report
    assert "没有读取 2019–2023 日线或 forward return" in report
    assert "累计历史开发试验仍为 255" in report
