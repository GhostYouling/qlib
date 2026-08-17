"""Terminal no-return uniqueness, reporting, and isolation tests for Campaign058."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
FACTOR = "quarterly_profit_revenue_growth_spread_pp"
AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_058/"
    "20260804T105439Z_campaign058_no_return_audit.json"
)
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_058_research_record.json"
LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_058/"
    "research_attempt_ledger.json"
)
FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_058_terminal_completion_freeze_20260804.json"
)
SUPERSESSION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_058_unified_report_supersession_20260804.json"
)
CANDIDATE49_FAILURE = REPO_ROOT / "docs/a_share_candidate49_20260804_daily_source_failure_record.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign058_terminal_records_have_live_bindings() -> None:
    for path in (RECORD, FREEZE, SUPERSESSION):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign058_coverage_passed_but_only_quality_profit_failed_uniqueness() -> None:
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]]
    assert _sha256(AUDIT) == (
        "df9c2ec09d6162ffa2ba4190f5c1141258a9769203cd7b4e297f8977f779b5b8"
    )
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["candidate_eligible_rows"] == 1330171
    assert coverage["quality_listing_eligible_rows"] == 1331759
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert coverage["eligible_names_p05"] == 138.0
    assert coverage["potential_non_overlapping_three_session_cohorts"] == 540
    assert uniqueness["comparison_factor_count"] == 89
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_comparisons_passed"] is False
    assert [(item["comparison_factor"], item["median_daily_rank_correlation"]) for item in failed] == [
        ("quality_profit", 0.8170091742276029)
    ]
    assert audit["admissible_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["training_or_model_fitting_performed"] is False
    assert audit["provider_request_issued_by_campaign058_audit"] is False


def test_campaign058_terminal_accounting_and_return_boundaries() -> None:
    record = _load(RECORD)
    ledger = _load(LEDGER)
    decision = record["decision"]
    accounting = record["append_only_attempt_accounting"]
    assert decision["development_folds_opened"] is False
    assert decision["development_return_fields_read"] is False
    assert decision["2024_2025_stress_opened"] is False
    assert decision["2024_2025_returns_read"] is False
    assert decision["factor_terminal"] is True
    assert ledger["campaign058_infrastructure_only_failure_count"] == 4
    assert ledger["campaign058_complete_factor_attempt_count"] == 1
    assert ledger["campaign058_attempt_count"] == 5
    assert accounting["cumulative_historical_research_attempt_count"] == 333
    assert accounting["cumulative_return_reading_development_trial_count"] == 268
    assert not (REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign058.py").exists()


def test_campaign058_reports_are_current_and_generator_is_idempotent(tmp_path: Path) -> None:
    for path in (REPORT, PIPELINE_DOC):
        text = path.read_text(encoding="utf-8")
        assert "Campaign058" in text
        assert "quality_profit" in text
        assert "0.817009" in text
        assert "333" in text
        assert "268" in text
    generated = tmp_path / "three_day_research_report.md"
    subprocess.run(
        [
            sys.executable,
            "scripts/a_share_short_horizon_factor_research.py",
            "report",
            "--output",
            str(generated),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert generated.read_bytes() == REPORT.read_bytes()
    assert generated.read_text(encoding="utf-8").count(
        "## 历史滚动 Campaign058 权威追加"
    ) == 1


def test_campaign058_preserves_candidate49_and_records_independent_source_failure() -> None:
    boundary = _load(RECORD)["prospective_boundary"]
    failure = _load(CANDIDATE49_FAILURE)
    assert _sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert boundary["candidate49_signal_entry_count"] == 0
    assert boundary["candidate49_execution_entry_count"] == 0
    assert boundary["candidate49_historical_backfill_performed"] is False
    assert boundary["second_prospective_candidate_created"] is False
    assert boundary["provider_request_issued_by_campaign058"] is False
    assert boundary["current_scoring_selection_sizing_or_orders_performed"] is False
    assert failure["readonly_plan"]["ready"] is True
    assert failure["readonly_plan"]["actual_exit_code"] == 0
    assert failure["confirmed_run"]["actual_exit_code"] == 1
    assert failure["confirmed_run"]["failure_stage"] == "stock_basic"
    assert failure["confirmed_run"]["same_day_retry_allowed"] is False
    assert failure["credential_safety"]["credential_missing_is_not_the_failure"] is True
    assert failure["post_failure_state"]["source_snapshot_published"] is False
    assert failure["research_boundary"]["failure_exit_code_bypassed"] is False
