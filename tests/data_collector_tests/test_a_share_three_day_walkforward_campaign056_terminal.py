"""Current terminal-state tests for Campaign056."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_056_research_record.json"
ATTEMPT_LEDGER = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_056/research_attempt_ledger_v4.json"
TRIAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_056/walkforward/trial_ledger.json"
SURVIVORS = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_056/walkforward/development_survivors.json"
STRESS = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_056/walkforward/exposed_stress_consumption_record.json"
COMPLETION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_056_terminal_completion_freeze_20260804.json"
SUPERSESSION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_056_unified_report_supersession_20260804.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign056_terminal_records_have_live_bindings() -> None:
    for path in (RECORD, ATTEMPT_LEDGER, COMPLETION_FREEZE, SUPERSESSION):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign056_single_trial_metrics_and_accounting_are_exact() -> None:
    record = _load(RECORD)
    attempt_ledger = _load(ATTEMPT_LEDGER)
    trial_ledger = _load(TRIAL_LEDGER)
    assert _sha256(TRIAL_LEDGER) == "823967446ff945a04b03ff6b5819fc748328c894d0c07a1c77ea8eff9ba426dd"
    assert len(trial_ledger["entries"]) == 1
    assert trial_ledger["chain_tip_sha256"] == "133404ac09197ef1752c1b3820f29cd4e0d87038466255081a8c2f2a7b62181d"
    assert [item["validation_year"] for item in record["validation_fold_results"]] == [2021, 2022, 2023]
    assert [item["mean_rank_ic"] for item in record["validation_fold_results"]] == [
        -0.04687948439933215,
        -0.02835483788017809,
        -0.05066834243052904,
    ]
    assert [item["normalized_return"] for item in record["validation_fold_results"]] == [
        -0.25281000802743314,
        -0.41429928016820505,
        -0.6028591763390986,
    ]
    assert [item["pilot_10bp_return"] for item in record["validation_fold_results"]] == [
        -0.03054931947348838,
        -0.06020876908966888,
        -0.09581920134468469,
    ]
    assert record["development_aggregate_result"]["pilot_20bp_return"] == -0.19371124612024093
    assert attempt_ledger["campaign056_ledger_entry_count"] == 4
    assert attempt_ledger["campaign056_attempt_count"] == 3
    assert attempt_ledger["campaign056_infrastructure_only_failure_count"] == 2
    assert attempt_ledger["campaign056_complete_factor_attempt_count"] == 1
    assert attempt_ledger["cumulative_historical_research_attempt_count"] == 324
    assert attempt_ledger["cumulative_return_reading_development_trial_count"] == 268


def test_campaign056_zero_survivor_and_unopened_stress_semantics() -> None:
    survivors = _load(SURVIVORS)
    stress = _load(STRESS)
    assert survivors["selected_survivor_count"] == 0
    assert survivors["stress_return_fields_read"] is False
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    result = subprocess.run(
        [sys.executable, "scripts/a_share_three_day_walkforward_campaign056.py", "status"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    status = json.loads(result.stdout)
    assert status["ledger_entry_count"] == 1
    assert status["selected_survivor_count"] == 0
    assert status["stress_intent_exists"] is False
    assert status["stress_record_exists"] is True
    assert status["stress_status"] == "not_opened_zero_development_survivors"
    assert status["candidate49_historical_return_read"] is False
    assert status["current_scoring_selection_sizing_or_orders_allowed"] is False


def test_campaign056_reports_and_generator_are_current(tmp_path: Path) -> None:
    assert _sha256(REPORT) == "70b7b64ff78e7c2bd9c1ee2cd39af5f6ccf82ec553f7efc675e8e744c1495df8"
    assert _sha256(PIPELINE_DOC) == "e39f084afaa621f4c15a9d6d1a258d0e351cecf42e7067fc3b0cdc01f5883cf7"
    assert _sha256(SKILL) == "0e85c969d7455937b6d5b2a77bb690b49efdd09f84d06048a715a0aa1a515ae3"
    for path in (REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "Campaign056" in text
        assert "0.747165" in text
        assert "324" in text
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


def test_campaign056_preserves_candidate49_isolation() -> None:
    assert _sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert _load(SIGNAL_LEDGER).get("entries", []) == []
    assert _load(EXECUTION_LEDGER).get("entries", []) == []
    decision = _load(RECORD)["decision"]
    assert decision["candidate49_historical_return_signal_execution_or_milestone_backfill_performed"] is False
    assert decision["current_score_selection_size_order_or_investment_advice_allowed"] is False
