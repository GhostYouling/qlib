"""Current terminal semantics for Campaign062 after additive infrastructure records."""

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
CAMPAIGN_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_062"
WALKFORWARD_ROOT = CAMPAIGN_ROOT / "walkforward"
RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_062_research_record_v3.json"
FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_062_terminal_completion_freeze_v3_20260805.json"
AUDIT = CAMPAIGN_ROOT / "no_return/20260804T210409Z_campaign062_no_return_audit.json"
LEDGER = CAMPAIGN_ROOT / "research_attempt_ledger_v4.json"
TRIAL_LEDGER = WALKFORWARD_ROOT / "trial_ledger.json"
SURVIVORS = WALKFORWARD_ROOT / "development_survivors.json"
STRESS = WALKFORWARD_ROOT / "exposed_stress_consumption_record.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
CAMPAIGN_REPORT = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_062_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign062_v2_immutable_chain_has_live_bindings() -> None:
    for path in (RECORD, FREEZE, LEDGER):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign062_v2_no_return_admission_remains_return_closed() -> None:
    audit = _load(AUDIT)
    factor = "quarterly_announcement_peer_crowding_sparsity"
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert coverage["gate_passed_before_comparison_values"] is True
    assert uniqueness["comparison_factor_count"] == 93
    assert len(uniqueness["comparisons"]) == 93
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_comparisons_passed"] is True
    assert uniqueness["maximum_observed_absolute_median_daily_rank_correlation"] == 0.7691435839145652
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["provider_request_issued"] is False


def test_campaign062_v2_exact_result_and_stress_remain_frozen() -> None:
    trial = _load(TRIAL_LEDGER)["entries"][0]
    validation = [fold["validation_metrics"] for fold in trial["training_and_validation_folds"]]
    assert [item["association"]["mean_rank_ic"] for item in validation] == [
        -0.004673771719555233,
        -0.015270283033833284,
        -0.006313994954814433,
    ]
    assert [item["normalized_execution"]["net_cumulative_return"] for item in validation] == [
        -0.18683720037448392,
        0.12604669185704842,
        -0.3042129367296751,
    ]
    assert [item["pilot_execution_primary_10bp"]["net_cumulative_return"] for item in validation] == [
        -0.050161567792464945,
        0.009857475765631785,
        -0.0636254600127385,
    ]
    decisions = _load(SURVIVORS)
    stress = _load(STRESS)
    assert decisions["selected_survivor_count"] == 0
    assert decisions["trial_decisions"][0]["development_survivor_gate_passed"] is False
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_campaign062_v2_append_only_attempt_accounting() -> None:
    ledger = _load(LEDGER)
    assert ledger["campaign062_attempt_count"] == 6
    assert ledger["campaign062_ledger_entry_count"] == 7
    assert ledger["campaign062_infrastructure_only_failure_count"] == 5
    assert ledger["campaign062_complete_factor_attempt_count"] == 1
    assert ledger["campaign062_historical_return_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 361
    assert ledger["cumulative_return_reading_development_trial_count"] == 271


def test_campaign062_v2_reports_are_current_and_idempotent(tmp_path: Path) -> None:
    assert _sha256(RECORD) == "0e7e828833ee5f37aa1daac67c2bb70383e2f2f29d4a131c34a469ef818a4b7d"
    assert _sha256(REPORT) == "33298a0ec4208b6fab4d3427848828e6ecec9e4927070ea99591154caad28f31"
    assert _sha256(CAMPAIGN_REPORT) == "292d046fb0949f754aaff3be6f1d23b42b6b7648edff1142108729c0b9aec267"
    assert _sha256(PIPELINE_DOC) == "8431e194a43dde66fbe91dfe305535150c7b1a72e85c6b6f4f31c372338e947a"
    assert _sha256(SKILL) == "526b148fefb14391e5c9e8d80e08adeef60c5960f887faf61be34e6b8024a5ec"
    for path in (REPORT, CAMPAIGN_REPORT, PIPELINE_DOC, SKILL):
        text = path.read_text(encoding="utf-8")
        assert "Campaign062" in text
        assert "0.769144" in text
        assert "361" in text
        assert "271" in text
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
    assert generated.read_text(encoding="utf-8").count("## 历史滚动 Campaign062 权威追加") == 1


def test_campaign062_v2_preserves_candidate49_isolation() -> None:
    assert _sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert _load(SIGNAL_LEDGER).get("entries", []) == []
    assert _load(EXECUTION_LEDGER).get("entries", []) == []
    current = _load(RECORD)
    assert current["inherited_research_semantics"]["candidate49_historical_backfill_or_ledger_change"] is False
    assert current["inherited_research_semantics"]["current_scoring_selection_sizing_or_orders_performed"] is False
