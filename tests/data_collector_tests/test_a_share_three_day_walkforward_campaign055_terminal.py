"""Terminal no-return uniqueness and report tests for Campaign055."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/20260803T181825Z_campaign055_no_return_audit.json"
)
AUDIT_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_055_no_return_audit_freeze_20260804.json"
)
RECORD = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_055_research_record.json"
)
SUPERSESSION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_055_unified_report_supersession_20260804.json"
)
LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_055/research_attempt_ledger.json"
)
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
SIGNAL_LEDGER = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
FACTOR = "intraday_price_update_clock_entropy_10b_238m"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign055_terminal_records_have_live_bindings() -> None:
    for path in (AUDIT_FREEZE, RECORD, SUPERSESSION, LEDGER):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign055_coverage_passed_but_uniqueness_failed_before_returns() -> None:
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]]
    assert _sha256(AUDIT) == (
        "c931097cb92f6138c34bef7ad45e204cb17a25ae384d9fc1ad1b2622c0d66f7e"
    )
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9963302258089495
    assert coverage["p05_coverage"] == 0.9885011697690977
    assert coverage["eligible_names_p05"] == 138.0
    assert coverage["potential_non_overlapping_three_session_cohorts"] == 540
    assert uniqueness["comparison_values_loaded_after_coverage_pass"] is True
    assert uniqueness["comparison_factor_count"] == 78
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert len(failed) == 1
    assert failed[0]["comparison_factor"] == "intraday_price_update_share_238m"
    assert failed[0]["median_daily_rank_correlation"] == 0.8780592267975353
    assert uniqueness["all_required_comparisons_passed"] is False
    assert audit["admissible_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["training_or_model_fitting_performed"] is False


def test_campaign055_development_and_stress_remain_closed() -> None:
    record = _load(RECORD)
    decision = record["decision"]
    accounting = record["append_only_attempt_accounting"]
    assert record["status"] == (
        "completed_zero_admissible_factors_stop_before_historical_returns"
    )
    assert decision["development_folds_opened"] is False
    assert decision["development_return_fields_read"] is False
    assert decision["2024_2025_stress_opened"] is False
    assert decision["2024_2025_returns_read"] is False
    assert accounting["campaign055_infrastructure_only_failure_count"] == 5
    assert accounting["campaign055_complete_factor_attempt_count"] == 1
    assert accounting["campaign055_total_attempt_count"] == 6
    assert accounting["cumulative_historical_research_attempt_count"] == 318
    assert accounting["campaign055_historical_return_trial_count"] == 0
    assert accounting["cumulative_return_reading_development_trial_count"] == 267


def test_campaign055_reports_and_skill_publish_terminal_result() -> None:
    assert _sha256(REPORT) == (
        "274b4e28cb24e766ecdf2899c442e24cefb669bf198bb186dcf9daf1ef07d201"
    )
    assert _sha256(PIPELINE_DOC) == (
        "53593b055857b9ca7ac44df26bbc3e1b2428f892ba21cb8d305dd9c7f27f86d3"
    )
    assert _sha256(SKILL) == (
        "a7eb92f935aeb96064fee1da28798a87689eaa7704414878965df79e7fa58fb4"
    )
    for path in (REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert FACTOR in text or "Campaign055" in text
        assert "0.878059" in text
        assert "318" in text
        assert "267" in text


def test_campaign055_report_generator_is_idempotent(tmp_path: Path) -> None:
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
    text = generated.read_text(encoding="utf-8")
    assert text.count("## 历史滚动 Campaign055 权威追加") == 1


def test_campaign055_preserves_candidate49_isolation() -> None:
    record = _load(RECORD)
    prospective = record["prospective_boundary"]
    assert _sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert prospective["candidate49_signal_ledger"]["entry_count"] == 0
    assert prospective["candidate49_execution_ledger"]["entry_count"] == 0
    assert prospective[
        "candidate49_historical_return_signal_execution_or_milestone_backfill_performed"
    ] is False
    assert prospective["second_prospective_candidate_created"] is False
    assert prospective["current_scoring_selection_sizing_or_orders_performed"] is False
