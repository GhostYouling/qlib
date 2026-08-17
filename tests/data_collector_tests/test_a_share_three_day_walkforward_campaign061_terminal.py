"""Terminal semantics for the zero-survivor Campaign061 research path."""

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
CAMPAIGN_ROOT = REPO_ROOT / (
    "data/experiments/short_horizon/historical_walkforward/campaign_061"
)
WALKFORWARD_ROOT = CAMPAIGN_ROOT / "walkforward"
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_061_research_record.json"
FREEZE = REPO_ROOT / (
    "docs/a_share_three_day_walkforward_campaign_061_terminal_completion_freeze_20260805.json"
)
AUDIT = CAMPAIGN_ROOT / "20260804T183906Z_campaign061_no_return_audit.json"
LEDGER = CAMPAIGN_ROOT / "research_attempt_ledger_v4.json"
TRIAL_LEDGER = WALKFORWARD_ROOT / "trial_ledger.json"
SURVIVORS = WALKFORWARD_ROOT / "development_survivors.json"
STRESS = WALKFORWARD_ROOT / "exposed_stress_consumption_record.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
CAMPAIGN_REPORT = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_061_report.md"
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


def test_campaign061_immutable_chain_has_live_bindings() -> None:
    for path in (RECORD, FREEZE, LEDGER):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign061_no_return_admission_was_ordered_and_return_closed() -> None:
    audit = _load(AUDIT)
    factor = "intraday_day_over_day_realized_variance_stability_238b"
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    assert coverage["median_coverage"] == 0.9972875203865161
    assert coverage["p05_coverage"] == 0.9905660377358491
    assert coverage["gate_passed_before_comparison_values"] is True
    assert uniqueness["comparison_values_loaded_after_coverage_pass"] is True
    assert uniqueness["comparison_factor_count"] == 92
    assert len(uniqueness["comparisons"]) == 92
    assert uniqueness["all_required_comparisons_passed"] is True
    assert audit["admissible_factor_names"] == [factor]
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["provider_request_issued"] is False


def test_campaign061_exact_development_result_and_closed_stress() -> None:
    trial = _load(TRIAL_LEDGER)["entries"][0]
    decisions = _load(SURVIVORS)
    stress = _load(STRESS)
    validation = [
        fold["validation_metrics"] for fold in trial["training_and_validation_folds"]
    ]
    assert [item["association"]["mean_rank_ic"] for item in validation] == [
        0.009062751775781086,
        0.009686169693856897,
        0.023550617175191343,
    ]
    assert [
        item["normalized_execution"]["net_cumulative_return"] for item in validation
    ] == [
        -0.17240066941502474,
        -0.022935304017539293,
        -0.24769727537251462,
    ]
    assert [
        item["pilot_execution_primary_10bp"]["net_cumulative_return"]
        for item in validation
    ] == [
        -0.027808604914117296,
        -0.021204236251575304,
        -0.047987314190158226,
    ]
    assert decisions["selected_survivor_count"] == 0
    assert decisions["trial_decisions"][0]["development_survivor_gate_passed"] is False
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_campaign061_append_only_attempt_accounting() -> None:
    ledger = _load(LEDGER)
    assert ledger["campaign061_attempt_count"] == 4
    assert ledger["campaign061_ledger_entry_count"] == 5
    assert ledger["campaign061_infrastructure_only_failure_count"] == 3
    assert ledger["campaign061_complete_factor_attempt_count"] == 1
    assert ledger["campaign061_historical_return_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 355
    assert ledger["cumulative_return_reading_development_trial_count"] == 270


def test_campaign061_reports_are_current_and_generator_is_idempotent(
    tmp_path: Path,
) -> None:
    assert _sha256(RECORD) == (
        "e644f6612f65dbde37ce1174c9e6e9c6ff30ea9f43f79b40ac003723374748d3"
    )
    assert _sha256(REPORT) == (
        "17d99dab3df0911d9888a3ce62cffe27180a9363a3e323f279449f441bd43f14"
    )
    assert _sha256(CAMPAIGN_REPORT) == (
        "b821c5920f6b0f61fc1e52d6a7e04bfc721d4db7fac8dd062fea3d6cd8a5668c"
    )
    assert _sha256(PIPELINE_DOC) == (
        "76bb7d4339b6ac231cdc6cafc66263b5b24239f2deacdc6ed4c78e8c88ab0e86"
    )
    assert _sha256(SKILL) == (
        "ce9bccabafc0163217fca4e0349d0f7f8d560940909d6d2a2b2953c152c72bf4"
    )
    for path in (REPORT, CAMPAIGN_REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "Campaign061" in text
        assert "0.212609" in text
        assert "355" in text
        assert "270" in text
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
        "## 历史滚动 Campaign061 权威追加"
    ) == 1


def test_campaign061_preserves_candidate49_isolation() -> None:
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
    assert boundary["provider_request_issued_by_campaign061"] is False
    assert _load(RECORD)["terminal_decision"][
        "current_scoring_selection_sizing_or_orders_performed"
    ] is False
