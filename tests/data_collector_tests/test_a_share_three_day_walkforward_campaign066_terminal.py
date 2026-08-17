from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
CAMPAIGN_ROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_066"
AUDIT = CAMPAIGN_ROOT / "no_return/20260805T093555Z_campaign066_no_return_audit.json"
TRIAL_LEDGER = CAMPAIGN_ROOT / "walkforward/trial_ledger.json"
SURVIVORS = CAMPAIGN_ROOT / "walkforward/development_survivors.json"
STRESS = CAMPAIGN_ROOT / "walkforward/exposed_stress_consumption_record.json"
ATTEMPTS = CAMPAIGN_ROOT / "research_attempt_ledger_v10.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_066_research_record.json"
FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_066_terminal_completion_freeze_20260805.json"
C49_FAILURE = ROOT / "docs/a_share_candidate49_20260805_daily_source_failure_record.json"
UNIFIED_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
SIGNAL_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
FACTOR = "quarterly_quality_rank_balance_3f"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign066_terminal_artifact_bindings_are_current() -> None:
    assert _sha256(RECORD) == "ebcfb647ae9efa64fc5256ef77d681b57aa10a905c042a83f23c7ae8e3be5dde"
    assert _sha256(FREEZE) == "68532a334d38f3e738a8e4dabac91e4588c58b8f6fff637fed9e9ab9d5dcbafa"
    for path, expected in ((RECORD, 22), (FREEZE, 8)):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["binding_count"] == expected


def test_campaign066_no_return_admission_is_complete() -> None:
    assert _sha256(AUDIT) == "4d3b8436bc55eb0066458ccd73daf632daf0afae1a373822f20ddd5723b74bfa"
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    unique = audit["uniqueness"][FACTOR]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert unique["comparison_factor_count"] == 96
    assert unique["comparison_order_matches_preregistration"] is True
    assert unique["all_required_numeric_comparisons_passed"] is True
    assert unique["maximum_observed_absolute_median_daily_rank_correlation"] == 0.547510261420378
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False


def test_campaign066_development_is_zero_survivors_and_stress_closed() -> None:
    assert _sha256(TRIAL_LEDGER) == "f48b307ffa5899287752ea6e09f5e5fd6234a8eadb7bd90ebea106b405d164f1"
    survivor = _load(SURVIVORS)
    decision = survivor["trial_decisions"][0]
    assert survivor["selected_survivor_count"] == 0
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 1
    assert decision["positive_normalized_return_fold_count"] == 0
    assert decision["positive_pilot_return_fold_count"] == 0
    assert decision["development_aggregate_20bp_return"] == -0.14696600917741787
    assert decision["operational_rejection_reasons"] == [
        "fold_1_board_lot_affordability",
        "fold_2_board_lot_affordability",
    ]
    stress = _load(STRESS)
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_campaign066_attempt_accounting_keeps_all_failures_and_continuation() -> None:
    assert _sha256(ATTEMPTS) == "cae0c831e8ff360c7cea156c2e2503c7c6e81940ab52af7548f6817588187088"
    ledger = _load(ATTEMPTS)
    assert ledger["campaign066_attempt_count"] == 9
    assert ledger["campaign066_ledger_entry_count"] == 10
    assert ledger["campaign066_infrastructure_or_synthetic_failure_count"] == 2
    assert ledger["campaign066_successful_preparatory_attempt_count"] == 6
    assert ledger["campaign066_complete_factor_attempt_count"] == 1
    assert ledger["campaign066_historical_return_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 401
    assert ledger["cumulative_return_reading_development_trial_count"] == 273


def test_candidate49_failure_is_isolated_and_ledgers_remain_empty() -> None:
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


def test_unified_report_has_one_campaign066_and_one_candidate49_daily_section() -> None:
    report = UNIFIED_REPORT.read_text(encoding="utf-8")
    assert report.count("## 历史滚动 Campaign066 权威追加") == 1
    assert report.count("## Candidate49 2026-08-05 前瞻数据源状态") == 1
    assert "`+1.766587%/-3.557626%/-7.150711%/-14.696601%`" in report
    assert "非法 `ts_code` 门禁以退出码 1 失败关闭" in report
