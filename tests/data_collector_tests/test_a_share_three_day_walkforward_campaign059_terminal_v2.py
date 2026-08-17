"""Versioned current terminal and reporting tests for Campaign059."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_059_research_record_v3.json"
LEDGER = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_059/research_attempt_ledger_v4.json"
FAILURE_1 = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_059_terminal_deselect_prefix_failure_20260804.json"
FAILURE_2 = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_059_terminal_binding_mutation_failure_20260804.json"
FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_059_terminal_completion_freeze_v3_20260804.json"
SUPERSESSION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_059_unified_report_supersession_v3_20260804.json"
SURVIVORS = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_059/walkforward/development_survivors.json"
STRESS = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_059/walkforward/exposed_stress_consumption_record.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign059_v2_current_records_have_live_bindings() -> None:
    paths = (
        REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_059_preregistration.json",
        REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_059_development_implementation_freeze_20260804.json",
        RECORD,
        LEDGER,
        FAILURE_1,
        FAILURE_2,
        FREEZE,
        SUPERSESSION,
    )
    for path in paths:
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign059_v2_result_and_append_only_accounting_are_exact() -> None:
    record = _load(RECORD)
    canonical = record["canonical_factor_result_unchanged"]
    accounting = record["append_only_attempt_accounting"]
    ledger = _load(LEDGER)
    assert canonical["comparison_factor_count"] == 90
    assert canonical["all_comparisons_passed"] is True
    assert canonical["maximum_absolute_median_daily_rank_correlation"] == (
        0.7148903759224717
    )
    assert canonical["validation_rank_ic"] == [
        -0.010330795383273883,
        0.013325929435016594,
        0.01056626775172599,
    ]
    assert canonical["validation_normalized_return"] == [
        0.2197368198808547,
        -0.37502953669720074,
        0.012631469535495654,
    ]
    assert canonical["validation_pilot_10bp_return"] == [
        0.020980317053472586,
        -0.07662733787933296,
        -0.011706923718404427,
    ]
    assert canonical["development_aggregate_pilot_20bp_return"] == (
        -0.13017742332606042
    )
    assert canonical["development_survivor_count"] == 0
    assert canonical["stress_2024_2025_opened"] is False
    assert canonical["stress_2024_2025_returns_read"] is False
    assert ledger["campaign059_ledger_entry_count"] == 7
    assert ledger["campaign059_attempt_count"] == 6
    assert ledger["campaign059_infrastructure_only_failure_count"] == 5
    assert ledger["campaign059_complete_factor_attempt_count"] == 1
    assert accounting["cumulative_historical_research_attempt_count"] == 339
    assert accounting["cumulative_return_reading_development_trial_count"] == 269


def test_campaign059_v2_current_status_is_post_audit_and_stress_closed() -> None:
    audit_status = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_walkforward_campaign059_no_return_audit_range_repair.py",
            "status",
            "--data-root",
            str(DATA_ROOT),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    audit_payload = json.loads(audit_status.stdout)
    assert audit_payload["audit_count"] == 1
    assert audit_payload["comparison_count"] == 90
    walkforward_status = subprocess.run(
        [sys.executable, "scripts/a_share_three_day_walkforward_campaign059.py", "status"],
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


def test_campaign059_v2_reports_and_generator_are_current(tmp_path: Path) -> None:
    assert _sha256(REPORT) == (
        "dce3893c5fe3a1b032ff69390288bf37caf68a5d9156b9f14c8d6d3ae3fb0923"
    )
    assert _sha256(PIPELINE_DOC) == (
        "37c923e6b46c1c040ecd0262e4a75e3565dae0a05de2d82d22696223bb4e0b69"
    )
    assert _sha256(SKILL) == (
        "5d22485b41869bac01e2a6a5d9ea01c4db8d8da2e5542031a62b6c7de48255bf"
    )
    for path in (REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "Campaign059" in text
        assert "0.714890" in text
        assert "339" in text
        assert "269" in text
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
        "## 历史滚动 Campaign059 权威追加"
    ) == 1


def test_campaign059_v2_preserves_candidate49_isolation() -> None:
    assert _sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL_LEDGER).get("entries", []) == []
    assert _load(EXECUTION_LEDGER).get("entries", []) == []
    boundary = _load(RECORD)["prospective_boundary"]
    assert boundary["candidate49_historical_backfill_performed"] is False
    assert boundary["second_prospective_candidate_created"] is False
    assert boundary["provider_request_issued_by_campaign059"] is False
    assert boundary["current_scoring_selection_sizing_or_orders_performed"] is False
