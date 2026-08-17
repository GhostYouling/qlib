"""Terminal semantics for the coverage-rejected Campaign060 research path."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_research_record.json"
AUDIT = REPO_ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_060/"
    "20260804T160410Z_campaign060_no_return_audit.json"
)
LEDGER = REPO_ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_060/"
    "research_attempt_ledger_v6.json"
)
STRESS = REPO_ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_060/"
    "unopened_stress_record.json"
)
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
SIGNAL_LEDGER = REPO_ROOT / (
    "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = REPO_ROOT / (
    "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign060_immutable_chain_has_live_bindings() -> None:
    paths = (
        RECORD,
        REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_concept_scouting.json",
        REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_mechanism_overlap_audit.json",
        REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_no_return_preregistration.json",
        REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_feature_implementation_freeze_20260804.json",
        REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_empty_partition_repair_freeze_20260804.json",
        REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_feature_snapshot_binding_20260804.json",
        REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_no_return_audit_implementation_freeze_20260805.json",
        REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_no_return_audit_range_repair_freeze_20260805.json",
        REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_no_return_audit_freeze_20260805.json",
        LEDGER,
    )
    for path in paths:
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign060_coverage_failure_stops_before_comparisons_and_returns() -> None:
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][
        "intraday_day_over_day_directional_return_agreement_238b"
    ]
    uniqueness = audit["uniqueness"][
        "intraday_day_over_day_directional_return_agreement_238b"
    ]
    assert coverage["median_coverage"] == 0.9033241252302026
    assert coverage["p05_coverage"] == 0.7990173123486684
    assert coverage["gate"]["minimum_median_coverage"] == 0.95
    assert coverage["gate"]["minimum_p05_coverage"] == 0.9
    assert coverage["gate_passed_before_comparison_values"] is False
    assert uniqueness["comparison_values_loaded_after_coverage_pass"] is False
    assert uniqueness["comparisons"] == []
    assert audit["admissible_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["training_or_model_fitting_performed"] is False
    assert audit["provider_request_issued"] is False


def test_campaign060_append_only_attempt_accounting_and_unopened_folds() -> None:
    ledger = _load(LEDGER)
    stress = _load(STRESS)
    assert ledger["campaign060_attempt_count"] == 10
    assert ledger["campaign060_ledger_entry_count"] == 10
    assert ledger["campaign060_infrastructure_only_failure_count"] == 9
    assert ledger["campaign060_complete_factor_attempt_count"] == 1
    assert ledger["campaign060_historical_return_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 351
    assert ledger["cumulative_return_reading_development_trial_count"] == 269
    assert stress["development_interval"]["opened"] is False
    assert stress["development_interval"]["forward_returns_read"] is False
    assert stress["stress_interval"]["opened"] is False
    assert stress["stress_interval"]["forward_returns_read"] is False


def test_campaign060_reports_are_current_and_generator_is_idempotent(
    tmp_path: Path,
) -> None:
    assert _sha256(RECORD) == (
        "889ab11013ba8cead84b0377cea15fdce0a405ce98d6a0d96eac08eb17bfbadd"
    )
    assert _sha256(REPORT) == (
        "da0974bca9fee1a9f835ed19e2cc8e92f93260bea82b40c0673c08ab04619bcc"
    )
    assert _sha256(PIPELINE_DOC) == (
        "2c0fcf30eee2f03a0d15f22bfa19a66da3819b06c85cd050aaea4275c024f57f"
    )
    assert _sha256(SKILL) == (
        "fadd108b37bc94d4b74c41499b168434e1b5c800e519a9ab410c654366a1464b"
    )
    for path in (REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "Campaign060" in text
        assert "0.903324" in text or "90.332413" in text
        assert "351" in text
        assert "269" in text
    generated = tmp_path / "three_day_research_report.md"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPO_ROOT)
    subprocess.run(
        [
            sys.executable,
            "scripts/a_share_short_horizon_factor_research.py",
            "report",
            "--output",
            str(generated),
        ],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert generated.read_bytes() == REPORT.read_bytes()
    assert generated.read_text(encoding="utf-8").count(
        "## 历史滚动 Campaign060 权威追加"
    ) == 1


def test_campaign060_preserves_candidate49_isolation() -> None:
    assert _sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL_LEDGER).get("entries", []) == []
    assert _load(EXECUTION_LEDGER).get("entries", []) == []
    boundary = _load(RECORD)["candidate49_boundary"]
    assert boundary["historical_backfill_performed"] is False
    assert boundary["provider_request_issued_by_campaign060"] is False
    assert _load(RECORD)["terminal_decision"][
        "current_scoring_selection_sizing_or_orders_performed"
    ] is False
