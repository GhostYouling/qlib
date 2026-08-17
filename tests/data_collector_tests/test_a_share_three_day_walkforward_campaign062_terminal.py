"""Terminal semantics for the zero-survivor Campaign062 research path."""

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
    "data/experiments/short_horizon/historical_walkforward/campaign_062"
)
WALKFORWARD_ROOT = CAMPAIGN_ROOT / "walkforward"
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_062_research_record_v2.json"
FREEZE = REPO_ROOT / (
    "docs/a_share_three_day_walkforward_campaign_062_terminal_completion_freeze_v2_20260805.json"
)
AUDIT = (
    CAMPAIGN_ROOT / "no_return/20260804T210409Z_campaign062_no_return_audit.json"
)
LEDGER = CAMPAIGN_ROOT / "research_attempt_ledger_v3.json"
TRIAL_LEDGER = WALKFORWARD_ROOT / "trial_ledger.json"
SURVIVORS = WALKFORWARD_ROOT / "development_survivors.json"
STRESS = WALKFORWARD_ROOT / "exposed_stress_consumption_record.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
CAMPAIGN_REPORT = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_062_report.md"
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


def test_campaign062_immutable_chain_has_live_bindings() -> None:
    for path in (RECORD, FREEZE, LEDGER):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign062_no_return_admission_was_ordered_and_return_closed() -> None:
    audit = _load(AUDIT)
    factor = "quarterly_announcement_peer_crowding_sparsity"
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert coverage["gate_passed_before_comparison_values"] is True
    assert uniqueness["comparison_values_loaded_after_coverage_pass"] is True
    assert uniqueness["comparison_factor_count"] == 93
    assert len(uniqueness["comparisons"]) == 93
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_comparisons_passed"] is True
    assert uniqueness["maximum_observed_absolute_median_daily_rank_correlation"] == (
        0.7691435839145652
    )
    assert audit["admissible_factor_names"] == [factor]
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["provider_request_issued"] is False


def test_campaign062_exact_development_result_and_closed_stress() -> None:
    trial = _load(TRIAL_LEDGER)["entries"][0]
    decisions = _load(SURVIVORS)
    stress = _load(STRESS)
    validation = [
        fold["validation_metrics"] for fold in trial["training_and_validation_folds"]
    ]
    assert [item["association"]["mean_rank_ic"] for item in validation] == [
        -0.004673771719555233,
        -0.015270283033833284,
        -0.006313994954814433,
    ]
    assert [
        item["normalized_execution"]["net_cumulative_return"] for item in validation
    ] == [
        -0.18683720037448392,
        0.12604669185704842,
        -0.3042129367296751,
    ]
    assert [
        item["pilot_execution_primary_10bp"]["net_cumulative_return"]
        for item in validation
    ] == [
        -0.050161567792464945,
        0.009857475765631785,
        -0.0636254600127385,
    ]
    assert decisions["selected_survivor_count"] == 0
    assert decisions["trial_decisions"][0]["development_survivor_gate_passed"] is False
    assert decisions["trial_decisions"][0]["operationally_admissible"] is True
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_campaign062_append_only_attempt_accounting() -> None:
    ledger = _load(LEDGER)
    assert ledger["campaign062_attempt_count"] == 5
    assert ledger["campaign062_ledger_entry_count"] == 6
    assert ledger["campaign062_infrastructure_only_failure_count"] == 4
    assert ledger["campaign062_complete_factor_attempt_count"] == 1
    assert ledger["campaign062_historical_return_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 360
    assert ledger["cumulative_return_reading_development_trial_count"] == 271


def test_campaign062_reports_are_current_and_generator_is_idempotent(
    tmp_path: Path,
) -> None:
    assert _sha256(RECORD) == (
        "05530809c6d3db9a2322a13167518ccd7d80c76619f607ffe0f55693c318cbf3"
    )
    assert _sha256(REPORT) == (
        "0c63282c2994a849f12d6b5f50ba0be0ea147bdc716c2eb6b2f9d37196d5d366"
    )
    assert _sha256(CAMPAIGN_REPORT) == (
        "4edd170ec2bd1166aa1bd496fde7ca5c60816a124f89f3be2053f966aa0c76d9"
    )
    assert _sha256(PIPELINE_DOC) == (
        "8ba55d0f8816ea52267b8fad06fb0273aecff7e0df26bce9bf3e58da6f507e74"
    )
    assert _sha256(SKILL) == (
        "d52fb18688e63fdda354fdbc11742f2b1563a7ec866c8e491a95bb5b9fc8fca9"
    )
    for path in (REPORT, CAMPAIGN_REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "Campaign062" in text
        assert "0.769144" in text
        assert "360" in text
        assert "271" in text
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
        "## 历史滚动 Campaign062 权威追加"
    ) == 1


def test_campaign062_preserves_candidate49_isolation() -> None:
    assert _sha256(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL_LEDGER).get("entries", []) == []
    assert _load(EXECUTION_LEDGER).get("entries", []) == []
    base_record = _load(REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_062_research_record.json")
    boundary = base_record["candidate49_boundary"]
    assert boundary["historical_backfill_performed"] is False
    assert boundary["provider_request_issued_by_campaign062"] is False
    assert base_record["terminal_decision"][
        "current_scoring_selection_sizing_or_orders_performed"
    ] is False
