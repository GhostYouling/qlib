"""Current Campaign055 terminal tests after append-only test-selection accounting."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_055_research_record_v3.json"
LEDGER = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_055/research_attempt_ledger_v3.json"
SUPERSESSION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_055_unified_report_supersession_v3_20260804.json"
SELECTION_FAILURE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_055_terminal_v2_historical_assertion_selection_failure_20260804.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign055_v3_current_records_have_live_bindings() -> None:
    for path in (RECORD, LEDGER, SUPERSESSION, SELECTION_FAILURE):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign055_v3_result_and_attempt_accounting_are_exact() -> None:
    record = _load(RECORD)
    result = record["canonical_factor_result_unchanged"]
    accounting = record["append_only_attempt_accounting"]
    ledger = _load(LEDGER)
    assert result["factor"] == "intraday_price_update_clock_entropy_10b_238m"
    assert result["coverage_gate_passed"] is True
    assert result["failed_comparison_factor"] == "intraday_price_update_share_238m"
    assert result["failed_comparison_median_daily_rank_correlation"] == 0.8780592267975353
    assert result["uniqueness_gate_passed"] is False
    assert result["admissible_factor_count"] == 0
    assert result["historical_daily_price_fields_read"] == []
    assert result["historical_forward_return_fields_read"] is False
    assert result["development_folds_opened"] is False
    assert result["stress_2024_2025_opened"] is False
    assert ledger["campaign055_ledger_entry_count"] == 8
    assert ledger["campaign055_infrastructure_only_failure_count"] == 7
    assert ledger["campaign055_complete_factor_attempt_count"] == 1
    assert accounting["campaign055_total_attempt_count"] == 8
    assert accounting["cumulative_historical_research_attempt_count"] == 320
    assert accounting["cumulative_return_reading_development_trial_count"] == 267


def test_campaign055_v3_reports_and_generator_are_current(tmp_path: Path) -> None:
    assert _sha256(REPORT) == "45d0c23289ea9111f2b24b696b13413140e873ed98d3a8e674f5d68be85f2c7a"
    assert _sha256(PIPELINE_DOC) == "ac9175743b652c2fd366566dd9ff981ac5c4f7c28e13b7653e0759122fb3a251"
    assert _sha256(SKILL) == "3f5553fa112dede4395cc882fb0cb6a4202b432397ed48bcd46e149ff21c2df6"
    for path in (REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "Campaign055" in text
        assert "0.878059" in text
        assert "320" in text
        assert "267" in text
    generated = tmp_path / "three_day_research_report.md"
    subprocess.run(
        [sys.executable, "scripts/a_share_short_horizon_factor_research.py", "report", "--output", str(generated)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert generated.read_bytes() == REPORT.read_bytes()
    assert generated.read_text(encoding="utf-8").count("## 历史滚动 Campaign055 权威追加") == 1


def test_campaign055_v3_preserves_candidate49_isolation() -> None:
    boundary = _load(RECORD)["prospective_boundary"]
    assert _sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert boundary["candidate49_signal_entry_count"] == 0
    assert boundary["candidate49_execution_entry_count"] == 0
    assert boundary["candidate49_historical_backfill_performed"] is False
    assert boundary["second_prospective_candidate_created"] is False
    assert boundary["provider_request_issued_by_post_terminal_attempt"] is False
    assert boundary["current_scoring_selection_sizing_or_orders_performed"] is False
