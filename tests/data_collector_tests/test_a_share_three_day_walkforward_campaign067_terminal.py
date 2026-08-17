from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
CAMPAIGN_ROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_067"
AUDIT = CAMPAIGN_ROOT / "no_return/20260805T115907Z_campaign067_no_return_audit.json"
TRIAL_LEDGER = CAMPAIGN_ROOT / "walkforward/trial_ledger.json"
SURVIVORS = CAMPAIGN_ROOT / "walkforward/development_survivors.json"
STRESS = CAMPAIGN_ROOT / "walkforward/exposed_stress_consumption_record.json"
ATTEMPTS = CAMPAIGN_ROOT / "research_attempt_ledger_v2.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_067_research_record.json"
FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_067_terminal_completion_freeze_20260805.json"
C49_FAILURE = ROOT / "docs/a_share_candidate49_20260805_daily_source_failure_record.json"
UNIFIED_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
SIGNAL_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
FACTOR = "quarterly_roe_profit_scale_efficiency_gap_2r"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign067_terminal_artifact_bindings_are_current() -> None:
    assert _sha256(RECORD) == "42f01ecde7725f79f848c6ec6e26f67585b643557b10a28b0ee6e2eabca88e68"
    assert _sha256(FREEZE) == "618e389ebab51e7b9882232cd5575930a8b9231bf29ac3a1ea3c2721f8eca954"
    for path, expected in ((RECORD, 22), (FREEZE, 8)):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["binding_count"] == expected


def test_campaign067_no_return_admission_is_complete() -> None:
    assert _sha256(AUDIT) == "daeac2c2364d00c09247d0e721435b81f587c0f215a5a93cba30b7661f205d54"
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    unique = audit["uniqueness"][FACTOR]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert unique["comparison_factor_count"] == 97
    assert unique["comparison_order_matches_preregistration"] is True
    assert unique["all_required_numeric_comparisons_passed"] is True
    assert unique["maximum_observed_absolute_median_daily_rank_correlation"] == 0.5941400969963562
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False


def test_campaign067_development_is_zero_survivors_and_stress_closed() -> None:
    assert _sha256(TRIAL_LEDGER) == "0a78a6a1ed9c9aa55a6cc00e2275e1d96b95cfe86b7f050c16e5809bc2bf1c8b"
    survivor = _load(SURVIVORS)
    decision = survivor["trial_decisions"][0]
    assert survivor["selected_survivor_count"] == 0
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 1
    assert decision["positive_normalized_return_fold_count"] == 2
    assert decision["positive_pilot_return_fold_count"] == 2
    assert decision["development_aggregate_20bp_return"] == -0.10663133148199833
    assert decision["operational_rejection_reasons"] == ["fold_1_amount_participation"]
    assert decision["validation_quality_rejection_reasons"] == [
        "insufficient_positive_ic_folds",
        "median_validation_mean_rank_ic",
        "worst_validation_normalized_drawdown",
        "nonpositive_development_aggregate_20bp_return",
    ]
    stress = _load(STRESS)
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_campaign067_attempt_accounting_keeps_the_development_continuation() -> None:
    assert _sha256(ATTEMPTS) == "c3abed753c57731b070b76c09090034f3bea8cba6f9926ba340d883367323a1e"
    ledger = _load(ATTEMPTS)
    assert ledger["campaign067_attempt_count"] == 1
    assert ledger["campaign067_ledger_entry_count"] == 2
    assert ledger["campaign067_infrastructure_or_synthetic_failure_count"] == 0
    assert ledger["campaign067_successful_preparatory_attempt_count"] == 0
    assert ledger["campaign067_complete_factor_attempt_count"] == 1
    assert ledger["campaign067_historical_return_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 402
    assert ledger["cumulative_return_reading_development_trial_count"] == 274


def test_campaign067_candidate49_failure_is_isolated_and_ledgers_remain_empty() -> None:
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


def test_unified_report_has_one_campaign067_and_one_candidate49_daily_section() -> None:
    report = UNIFIED_REPORT.read_text(encoding="utf-8")
    assert _sha256(UNIFIED_REPORT) == "46f34d458d964d9ac9a05a4a9359c32610e5fad1507526c9dd682a051cc13d64"
    assert report.count("## 历史滚动 Campaign067 权威追加") == 1
    assert report.count("## Candidate49 2026-08-05 前瞻数据源状态") == 1
    assert "`+10.639565%/+5.037207%/-1.072609%/-10.663133%`" in report
    assert "非法 `ts_code` 门禁以退出码 1 失败关闭" in report
