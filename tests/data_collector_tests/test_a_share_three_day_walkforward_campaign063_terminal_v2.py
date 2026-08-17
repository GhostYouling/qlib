"""Current Campaign063 terminal semantics after additive validation evidence."""

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
CAMPAIGN_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_063"
AUDIT = CAMPAIGN_ROOT / "no_return/20260804T224823Z_campaign063_no_return_audit.json"
LEDGER = CAMPAIGN_ROOT / "research_attempt_ledger_v7.json"
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_063_research_record_v3.json"
FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_063_terminal_completion_freeze_v3_20260805.json"
DIAGNOSIS = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_063_structural_peer_variance_diagnosis_20260805.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
CAMPAIGN_REPORT = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_063_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
GENERATOR = REPO_ROOT / "scripts/a_share_short_horizon_factor_research.py"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign063_v2_current_immutable_chain_has_live_bindings() -> None:
    for path in (RECORD, FREEZE, LEDGER):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign063_v2_structural_zero_variance_is_exact_and_terminal() -> None:
    diagnosis = _load(DIAGNOSIS)
    replay = diagnosis["frozen_variance_replay"]
    consequence = diagnosis["candidate_manifest_consequence"]
    assert replay["trade_dates"] == 1699
    assert replay["position236"]["zero_variance_rows"] == 1699
    assert replay["position236"]["minimum"] == 0.0
    assert replay["position236"]["median"] == 0.0
    assert replay["position29"]["zero_variance_rows"] == 1
    assert replay["position30"]["zero_variance_rows"] == 1
    assert consequence["complete_stock_return_rows"] == 7724498
    assert consequence["insufficient_peer_rows"] == 0
    assert consequence["nonpositive_variance_rows"] == 7724498
    assert consequence["eligible_rows"] == 0
    assert diagnosis["decision"]["same_campaign_repair_or_rescue_allowed"] is False


def test_campaign063_v2_sole_audit_stopped_before_comparisons_and_returns() -> None:
    assert sorted((CAMPAIGN_ROOT / "no_return").glob("*.json")) == [AUDIT]
    audit = _load(AUDIT)
    factor = "intraday_cross_sectional_standardized_return_state_stability_236p"
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    assert audit["admissible_factor_count"] == 0
    assert coverage["quality_listing_eligible_rows"] == 1331759
    assert coverage["candidate_eligible_rows"] == 0
    assert coverage["median_coverage"] == 0.0
    assert coverage["p05_coverage"] == 0.0
    assert coverage["gate_passed_before_comparison_values"] is False
    assert audit["comparison_factor_values_read"] is False
    assert uniqueness["comparison_factor_count"] == 0
    assert uniqueness["comparisons"] == []
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["training_or_model_fitting_performed"] is False
    assert audit["provider_request_issued"] is False


def test_campaign063_v2_append_only_attempt_accounting() -> None:
    ledger = _load(LEDGER)
    assert ledger["campaign063_attempt_count"] == 7
    assert ledger["campaign063_ledger_entry_count"] == 7
    assert ledger["campaign063_infrastructure_only_failure_count"] == 6
    assert ledger["campaign063_complete_factor_attempt_count"] == 1
    assert ledger["campaign063_historical_return_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 368
    assert ledger["cumulative_return_reading_development_trial_count"] == 271


def test_campaign063_v2_reports_are_current_and_generator_is_idempotent(tmp_path: Path) -> None:
    expected_hashes = {
        REPORT: "dcdfd6b5346adfac6ff4959853d72b2d67e1c7a874a0d9d1a26f699846bd7ab0",
        CAMPAIGN_REPORT: "27ccd9332c9d541698a1e821a5d3499c6f7fa8ce9f78d213415c50d76e47027f",
        PIPELINE_DOC: "dde1449cb37bb6d784c58fab1dfcaf1ae9c831b09bdc0ecc8fe65f59f7b3cef3",
        GENERATOR: "03f10f3992053780e162c661f802faf2564500a7ea1c9afce2582961caa9f996",
        SKILL: "fdb878e542841a50b8a01482c9d5752a5be6103031775c4881006610632352ab",
    }
    for path, expected in expected_hashes.items():
        assert _sha256(path) == expected
    for path in (REPORT, CAMPAIGN_REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "Campaign063" in text
        assert "368" in text
        assert "271" in text
    generator_text = GENERATOR.read_text(encoding="utf-8")
    assert "intraday_cross_sectional_standardized_return_state_stability_236p" in generator_text
    assert '63: "_v3"' in generator_text
    assert "368" in generator_text
    assert "271" in generator_text
    generated = tmp_path / "three_day_research_report.md"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(REPO_ROOT)
    subprocess.run(
        [sys.executable, "scripts/a_share_short_horizon_factor_research.py", "report", "--output", str(generated)],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert generated.read_bytes() == REPORT.read_bytes()
    assert generated.read_text(encoding="utf-8").count("## 历史滚动 Campaign063 权威追加") == 1


def test_campaign063_v2_preserves_candidate49_isolation() -> None:
    assert _sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert _load(SIGNAL_LEDGER).get("entries", []) == []
    assert _load(EXECUTION_LEDGER).get("entries", []) == []
    semantics = _load(RECORD)["inherited_research_semantics"]
    assert semantics["candidate49_historical_backfill_or_ledger_change"] is False
    assert semantics["provider_request_issued"] is False
    assert semantics["current_scoring_selection_sizing_or_orders_performed"] is False
