"""Current Campaign056 terminal tests after historical-assertion selection accounting."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_056_research_record_v2.json"
LEDGER = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_056/research_attempt_ledger_v5.json"
FAILURE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_056_terminal_historical_assertion_selection_failure_20260804.json"
FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_056_terminal_completion_freeze_v2_20260804.json"
SUPERSESSION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_056_unified_report_supersession_v2_20260804.json"
SURVIVORS = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_056/walkforward/development_survivors.json"
STRESS = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_056/walkforward/exposed_stress_consumption_record.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign056_v2_current_records_have_live_bindings() -> None:
    for path in (RECORD, LEDGER, FAILURE, FREEZE, SUPERSESSION):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign056_v2_result_and_append_only_accounting_are_exact() -> None:
    record = _load(RECORD)
    result = record["canonical_factor_result_unchanged"]
    accounting = record["append_only_attempt_accounting"]
    ledger = _load(LEDGER)
    assert result["factor"] == "intraday_day_over_day_amount_profile_similarity_240b"
    assert result["all_comparisons_passed"] is True
    assert result["maximum_absolute_median_daily_rank_correlation"] == 0.7471649347166686
    assert result["validation_rank_ic"] == [-0.04687948439933215, -0.02835483788017809, -0.05066834243052904]
    assert result["validation_normalized_return"] == [-0.25281000802743314, -0.41429928016820505, -0.6028591763390986]
    assert result["validation_pilot_10bp_return"] == [-0.03054931947348838, -0.06020876908966888, -0.09581920134468469]
    assert result["development_aggregate_pilot_20bp_return"] == -0.19371124612024093
    assert result["development_survivor_count"] == 0
    assert result["stress_2024_2025_opened"] is False
    assert result["stress_2024_2025_returns_read"] is False
    assert ledger["campaign056_ledger_entry_count"] == 5
    assert ledger["campaign056_attempt_count"] == 4
    assert ledger["campaign056_infrastructure_only_failure_count"] == 3
    assert ledger["campaign056_complete_factor_attempt_count"] == 1
    assert accounting["cumulative_historical_research_attempt_count"] == 325
    assert accounting["cumulative_return_reading_development_trial_count"] == 268


def test_campaign056_v2_current_status_is_post_audit_and_stress_closed() -> None:
    audit_status = subprocess.run(
        [sys.executable, "scripts/a_share_three_day_walkforward_campaign056_no_return_audit.py", "status", "--data-root", str(DATA_ROOT)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    audit_payload = json.loads(audit_status.stdout)
    assert audit_payload["audit_count"] == 1
    walkforward_status = subprocess.run(
        [sys.executable, "scripts/a_share_three_day_walkforward_campaign056.py", "status"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(walkforward_status.stdout)
    assert payload["ledger_entry_count"] == 1
    assert payload["selected_survivor_count"] == 0
    assert payload["stress_intent_exists"] is False
    assert payload["stress_record_exists"] is True
    assert payload["stress_status"] == "not_opened_zero_development_survivors"
    assert _load(SURVIVORS)["selected_survivor_count"] == 0
    assert _load(STRESS)["stress_return_fields_read"] is False


def test_campaign056_v2_reports_and_generator_are_current(tmp_path: Path) -> None:
    assert _sha256(REPORT) == "2994d997098babf6d351db66c1f7e487d3ebffcd3e721cc487627c03ffb13db0"
    assert _sha256(PIPELINE_DOC) == "a614a3513e5bfc106b8559451fa518ddedbcfd66e0991cea3f0613049c7e5bf2"
    assert _sha256(SKILL) == "047a6eb857e9261efc40c5b87f5afff6c3a06d68bad709e78726219d51ef7358"
    for path in (REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "Campaign056" in text
        assert "0.747165" in text
        assert "325" in text
        assert "268" in text
    generated = tmp_path / "three_day_research_report.md"
    subprocess.run(
        [sys.executable, "scripts/a_share_short_horizon_factor_research.py", "report", "--output", str(generated)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert generated.read_bytes() == REPORT.read_bytes()
    assert generated.read_text(encoding="utf-8").count("## 历史滚动 Campaign056 权威追加") == 1


def test_campaign056_v2_preserves_candidate49_isolation() -> None:
    assert _sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert _load(SIGNAL_LEDGER).get("entries", []) == []
    assert _load(EXECUTION_LEDGER).get("entries", []) == []
    boundary = _load(RECORD)["prospective_boundary"]
    assert boundary["candidate49_historical_backfill_performed"] is False
    assert boundary["second_prospective_candidate_created"] is False
    assert boundary["provider_request_issued_by_post_terminal_attempt"] is False
    assert boundary["current_scoring_selection_sizing_or_orders_performed"] is False
