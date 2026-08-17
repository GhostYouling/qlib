from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator
from scripts import a_share_three_day_walkforward_campaign069_features as features


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
CAMPAIGN_ROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_069"
AUDIT = CAMPAIGN_ROOT / "no_return/20260805T195018Z_campaign069_no_return_audit.json"
TRIAL_LEDGER = CAMPAIGN_ROOT / "walkforward/trial_ledger.json"
SURVIVORS = CAMPAIGN_ROOT / "walkforward/development_survivors.json"
STRESS = CAMPAIGN_ROOT / "walkforward/exposed_stress_consumption_record.json"
ATTEMPTS = CAMPAIGN_ROOT / "research_attempt_ledger_v2.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_069_research_record.json"
FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_069_terminal_completion_freeze_20260806.json"
C49_FAILURE = ROOT / "docs/a_share_candidate49_20260805_daily_source_failure_record.json"
UNIFIED_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
SIGNAL_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
FACTOR = "quarterly_profit_growth_roe_transition_gap_2r"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign069_terminal_artifact_bindings_are_current() -> None:
    assert _sha256(RECORD) == "85f1161e86beba49a1b5841dec335d627171702a633270a47b52899dc11f24bd"
    assert _sha256(FREEZE) == "66a58159041ee462c1e6f4df25e78afa3b57e9dcfc3525a766230e80d49f7989"
    for path, expected in ((RECORD, 22), (FREEZE, 9)):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["binding_count"] == expected


def test_campaign069_postbuild_feature_status_is_current_without_rewriting_prebuild_test() -> None:
    assert features.status()["status"] == "snapshot_present"
    failure = _load(ROOT / "docs/a_share_three_day_walkforward_campaign_069_postbuild_test_failure_20260806.json")
    assert failure["immutability"]["historical_test_edited"] is False
    assert failure["accounting"]["research_attempt_count_increment"] == 1


def test_campaign069_no_return_admission_is_complete() -> None:
    assert _sha256(AUDIT) == "1f05b0943a58e8414c898113d2e0db7b58f703d076d593f9f6c36fd6bc2df6d9"
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    unique = audit["uniqueness"][FACTOR]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert unique["comparison_factor_count"] == 99
    assert unique["comparison_order_matches_preregistration"] is True
    assert unique["all_required_numeric_comparisons_passed"] is True
    assert unique["maximum_observed_absolute_median_daily_rank_correlation"] == 0.786222265171396
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False


def test_campaign069_development_is_zero_survivors_and_stress_closed() -> None:
    assert _sha256(TRIAL_LEDGER) == "554ab4eceedb9fd5029e34c38a4bc962bf966603a7810a6f8d4ab8fc1ffb4e5f"
    survivor = _load(SURVIVORS)
    decision = survivor["trial_decisions"][0]
    assert survivor["selected_survivor_count"] == 0
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 2
    assert decision["positive_normalized_return_fold_count"] == 0
    assert decision["positive_pilot_return_fold_count"] == 0
    assert decision["development_aggregate_20bp_return"] == -0.2399648755584498
    assert decision["operational_rejection_reasons"] == []
    assert decision["validation_quality_rejection_reasons"] == [
        "median_validation_spread",
        "insufficient_positive_normalized_return_folds",
        "insufficient_positive_pilot_return_folds",
        "median_validation_pilot_return",
        "worst_validation_normalized_drawdown",
        "nonpositive_development_aggregate_20bp_return",
    ]
    stress = _load(STRESS)
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_campaign069_attempt_accounting_keeps_the_development_continuation() -> None:
    assert _sha256(ATTEMPTS) == "1a8d9bc9262c71c463e005d5da0dcf4742c422d1139fd33cf07f2fc10a01f5ee"
    ledger = _load(ATTEMPTS)
    assert ledger["campaign069_attempt_count"] == 4
    assert ledger["campaign069_ledger_entry_count"] == 5
    assert ledger["campaign069_infrastructure_or_synthetic_failure_count"] == 3
    assert ledger["campaign069_complete_factor_attempt_count"] == 1
    assert ledger["campaign069_historical_return_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 412
    assert ledger["cumulative_return_reading_development_trial_count"] == 275


def test_campaign069_candidate49_failure_is_isolated_and_ledgers_remain_empty() -> None:
    failure = _load(C49_FAILURE)
    assert failure["session_date"] == "2026-08-05"
    assert failure["real_workflow_attempt"]["cli_exit_code"] == 1
    assert failure["real_workflow_attempt"]["failure_stage"] == "stock_basic"
    assert failure["real_workflow_attempt"]["provider_continuation_allowed_for_same_session"] is False
    assert failure["verification"]["signal_execution_ledger_semantic_validation"]["semantics_valid"] is True
    assert _sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert _load(SIGNAL_LEDGER).get("entries", []) == []
    assert _load(EXECUTION_LEDGER).get("entries", []) == []


def test_unified_report_has_one_campaign069_terminal_section() -> None:
    report = UNIFIED_REPORT.read_text(encoding="utf-8")
    assert _sha256(UNIFIED_REPORT) == "a41d7701a83600702f6397527ab7b5ef028afc0e286b247606eb9a2ea3c0f00f"
    assert report.count("## 历史滚动 Campaign069 权威追加") == 1
    assert "`-7.772912%/-11.871798%/-16.583406%/-23.996488%`" in report
    assert "survivor 为 0，2024–2025 未打开" in report
