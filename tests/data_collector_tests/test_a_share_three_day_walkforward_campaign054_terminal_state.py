"""Current-record and advancing-state tests for terminal Campaign054."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_054_research_record.json"
SUPERSESSION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_054_unified_report_supersession_20260803.json"
VERIFICATION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_054_verification_20260803.json"
STATE = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260803_campaign054_verified.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign054_current_records_have_live_bindings() -> None:
    for path in (RECORD, SUPERSESSION, VERIFICATION, STATE):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign054_advancing_state_is_terminal_without_stress() -> None:
    state = _load(STATE)
    campaign = state["campaign054"]
    cumulative = state["cumulative_state"]
    assert state["status"] == (
        "campaign054_terminal_verified_zero_survivors_ready_for_independent_campaign055"
    )
    assert campaign["terminal"] is True
    assert campaign["development_trial_count"] == 1
    assert campaign["development_survivor_count"] == 0
    assert campaign["stress_2024_2025_opened"] is False
    assert campaign["stress_2024_2025_returns_read"] is False
    assert cumulative["cumulative_historical_research_attempt_count_after_campaign054"] == 312
    assert cumulative["cumulative_return_reading_development_trial_count_after_campaign054"] == 267
    assert cumulative["current_historical_aggregation_candidate_count"] == 0


def test_campaign054_reports_and_skill_publish_the_terminal_result() -> None:
    assert _sha256(REPORT) == "22208a6309ec4f6299225b64e97f0ed2e48ae3a5817c9a48dd2a115de529a4ab"
    assert _sha256(PIPELINE_DOC) == "11794b1edc3157eb462087992e5780825714470a66d23d717efac3d284001141"
    assert _sha256(SKILL) == "a9ccfca2aed550998fe53bad7c6bc28e794b902093a126cdfef6c08ffca9ca21"
    for path in (REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "intraday_volume_weighted_transaction_price_bowley_skew_240m" in text
        assert "312" in text
        assert "267" in text


def test_campaign054_preserves_candidate49_isolation_and_same_day_failure_closure() -> None:
    state = _load(STATE)
    prospective = state["prospective_boundary"]
    assert _sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert prospective["active_candidate_count"] == 1
    assert prospective["candidate49_20260803_same_day_retry_allowed"] is False
    assert prospective[
        "candidate49_historical_return_signal_execution_or_milestone_backfill_performed"
    ] is False
    assert prospective["second_prospective_candidate_activation_allowed"] is False
