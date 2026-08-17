"""Current terminal accounting and boundary tests for Campaign055."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
AUDIT = REPO_ROOT / "data/experiments/short_horizon/20260803T181825Z_campaign055_no_return_audit.json"
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_055_research_record_v2.json"
LEDGER = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_055/research_attempt_ledger_v2.json"
FAILURE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_055_terminal_suite_root_volume_headroom_failure_20260804.json"
RETEST = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_055_terminal_suite_root_volume_headroom_retest_20260804.json"
SUPERSESSION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_055_unified_report_supersession_v2_20260804.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
FACTOR = "intraday_price_update_clock_entropy_10b_238m"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign055_v2_records_have_live_bindings() -> None:
    for path in (RECORD, LEDGER, RETEST, SUPERSESSION):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign055_factor_result_remains_terminal_before_returns() -> None:
    audit = _load(AUDIT)
    record = _load(RECORD)
    result = record["canonical_factor_result_unchanged"]
    assert _sha256(AUDIT) == "c931097cb92f6138c34bef7ad45e204cb17a25ae384d9fc1ad1b2622c0d66f7e"
    assert result["factor"] == FACTOR
    assert result["coverage_gate_passed"] is True
    assert result["comparison_factor_count"] == 78
    assert result["failed_comparison_factor"] == "intraday_price_update_share_238m"
    assert result["failed_comparison_median_daily_rank_correlation"] == 0.8780592267975353
    assert result["absolute_uniqueness_limit"] == 0.8
    assert result["uniqueness_gate_passed"] is False
    assert result["admissible_factor_count"] == 0
    assert result["historical_daily_price_fields_read"] == []
    assert result["historical_forward_return_fields_read"] is False
    assert result["development_folds_opened"] is False
    assert result["stress_2024_2025_opened"] is False
    assert audit["historical_forward_return_fields_read"] is False


def test_campaign055_v2_append_only_attempt_accounting() -> None:
    ledger = _load(LEDGER)
    accounting = _load(RECORD)["append_only_attempt_accounting"]
    assert ledger["prior_version"]["sha256"] == "8b71a8cd94d064ca9f3ef1b3bd8eea113097cec04da7f60331f17c754ea0b187"
    assert ledger["campaign055_ledger_entry_count"] == 7
    assert ledger["campaign055_attempt_count"] == 7
    assert ledger["campaign055_infrastructure_only_failure_count"] == 6
    assert ledger["campaign055_complete_factor_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 319
    assert ledger["cumulative_return_reading_development_trial_count"] == 267
    assert accounting["campaign055_total_attempt_count"] == 7
    assert accounting["cumulative_historical_research_attempt_count"] == 319
    assert accounting["cumulative_return_reading_development_trial_count"] == 267


def test_campaign055_headroom_failure_and_retest_are_infrastructure_only() -> None:
    failure = _load(FAILURE)
    retest = _load(RETEST)
    assert failure["attempt_class"] == "infrastructure_only"
    assert failure["provider_request_issued"] is False
    assert failure["historical_forward_return_fields_read"] is False
    assert retest["retest"]["exit_code"] == 0
    assert retest["retest"]["passed"] == 21
    assert retest["retest"]["failed"] == 0
    assert retest["retest"]["provider_requests_issued"] is False
    assert retest["campaign055_factor_formula_direction_snapshot_audit_comparisons_gates_or_terminal_decision_changed"] is False


def test_campaign055_v2_reports_are_current_and_report_is_idempotent(tmp_path: Path) -> None:
    assert _sha256(REPORT) == "5e0e9728fef678231cb5a4931f1e5ad4c18c57597f73b04ccedb87c55d3aa157"
    assert _sha256(PIPELINE_DOC) == "092df3e9b58d89dad8af24385301e9cb7e309ab446552451a2208f09bfb39168"
    assert _sha256(SKILL) == "30e2a246fe912c0fd8807439d692912364c1b31610420f691ccba12b1fcfb1ab"
    for path in (REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "Campaign055" in text
        assert "0.878059" in text
        assert "319" in text
        assert "267" in text
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
    assert generated.read_text(encoding="utf-8").count("## 历史滚动 Campaign055 权威追加") == 1


def test_campaign055_v2_preserves_candidate49_isolation() -> None:
    record = _load(RECORD)["prospective_boundary"]
    assert _sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert record["candidate49_signal_entry_count"] == 0
    assert record["candidate49_execution_entry_count"] == 0
    assert record["candidate49_historical_backfill_performed"] is False
    assert record["second_prospective_candidate_created"] is False
    assert record["provider_request_issued_by_post_terminal_attempt"] is False
    assert record["current_scoring_selection_sizing_or_orders_performed"] is False
