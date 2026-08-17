"""Terminal no-return uniqueness and reporting tests for Campaign057."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
FACTOR = "intraday_day_over_day_absolute_return_profile_similarity_238b"
AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_057/"
    "20260804T073457Z_campaign057_no_return_audit.json"
)
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_057_research_record.json"
LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_057/"
    "research_attempt_ledger_v3.json"
)
FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_057_terminal_completion_freeze_20260804.json"
)
SUPERSESSION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_057_unified_report_supersession_20260804.json"
)
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign057_terminal_records_have_live_bindings() -> None:
    for path in (RECORD, FREEZE, SUPERSESSION):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign057_coverage_passed_but_uniqueness_failed_before_returns() -> None:
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]]
    assert _sha256(AUDIT) == (
        "1a0452a5ca821589d10131ec095f36a08046289f796770070bf750bfc1aa5a8b"
    )
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9972875203865161
    assert coverage["p05_coverage"] == 0.9905660377358491
    assert coverage["eligible_names_p05"] == 138.0
    assert coverage["potential_non_overlapping_three_session_cohorts"] == 540
    assert uniqueness["comparison_factor_count"] == 80
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_comparisons_passed"] is False
    assert [(item["comparison_factor"], item["median_daily_rank_correlation"]) for item in failed] == [
        ("intraday_price_update_share_238m", 0.872246911088057),
        ("intraday_amount_price_discovery_alignment_js_238p", 0.8320562564839863),
    ]
    assert audit["admissible_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["training_or_model_fitting_performed"] is False


def test_campaign057_development_stress_and_prospective_boundaries() -> None:
    record = _load(RECORD)
    decision = record["decision"]
    accounting = record["append_only_attempt_accounting"]
    ledger = _load(LEDGER)
    assert decision["development_folds_opened"] is False
    assert decision["development_return_fields_read"] is False
    assert decision["2024_2025_stress_opened"] is False
    assert decision["2024_2025_returns_read"] is False
    assert decision["factor_terminal"] is True
    assert ledger["campaign057_infrastructure_only_failure_count"] == 2
    assert ledger["campaign057_complete_factor_attempt_count"] == 1
    assert ledger["campaign057_attempt_count"] == 3
    assert accounting["cumulative_historical_research_attempt_count"] == 328
    assert accounting["cumulative_return_reading_development_trial_count"] == 268
    assert not (REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign057.py").exists()


def test_campaign057_reports_are_current_and_generator_is_idempotent(tmp_path: Path) -> None:
    assert _sha256(REPORT) == "936aadd0fa5fdf433bd26fd2cff5afa2e6fd2acff14f0e3e25f1e98f245528b1"
    assert _sha256(PIPELINE_DOC) == "8c6740ab979623e3dd90ff613d5e1b3f7be2b742f1b5e4c928307d8fbd2d2507"
    assert _sha256(SKILL) == "b47d6e353ca786e45c60f098021649ac8eaf702578870d1565b672c1d52a6462"
    for path in (REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "Campaign057" in text
        assert "0.872247" in text
        assert "328" in text
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
        "## 历史滚动 Campaign057 权威追加"
    ) == 1


def test_campaign057_preserves_candidate49_isolation() -> None:
    boundary = _load(RECORD)["prospective_boundary"]
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
    assert boundary["provider_request_issued_by_campaign057"] is False
    assert boundary["current_scoring_selection_sizing_or_orders_performed"] is False
