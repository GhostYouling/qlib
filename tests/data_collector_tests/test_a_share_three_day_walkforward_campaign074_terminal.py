from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator
from scripts import a_share_tushare_candidate49_future_execution as execution


ROOT = Path(__file__).resolve().parents[2]
MINUTE_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
CAMPAIGN_ROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_074"
AUDIT = CAMPAIGN_ROOT / "no_return/20260806T001358Z_campaign074_no_return_audit.json"
ATTEMPTS = CAMPAIGN_ROOT / "research_attempt_ledger_v6.json"
TRIAL_LEDGER = CAMPAIGN_ROOT / "walkforward/trial_ledger.json"
SURVIVORS = CAMPAIGN_ROOT / "walkforward/development_survivors.json"
STRESS = CAMPAIGN_ROOT / "walkforward/exposed_stress_consumption_record.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_074_research_record_v5.json"
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_074_report.md"
UNIFIED_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
SIGNAL_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
FACTOR = "intraday_terminal_bar_amount_share_240m"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign074_current_research_record_bindings_are_valid() -> None:
    assert _sha256(RECORD) == "fb5ea4bd55ac0a0577288e1a80d810941b88e7083f92f21dab0052ba3f9952f3"
    receipt = validator.validate_record(RECORD, data_root=MINUTE_ROOT)
    assert receipt["all_bindings_passed"] is True
    record = _load(RECORD)
    assert record["unchanged_factor_and_result"]["factor"] == FACTOR
    assert record["unchanged_factor_and_result"]["development_survivor_count"] == 0
    assert record["current_attempt_accounting"]["campaign074_attempts"] == 10
    assert record["current_attempt_accounting"]["cumulative_historical_attempts"] == 452
    assert record["current_attempt_accounting"]["cumulative_return_reading_development_trials"] == 276


def test_campaign074_no_return_gate_admits_one_unique_factor() -> None:
    assert _sha256(AUDIT) == "6256ca2db8ff21dcfb3e101e019957c2d1241fd893f290bd449ed462ace17009"
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["candidate_eligible_rows"] == 1330171
    assert coverage["quality_listing_eligible_rows"] == 1331759
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert uniqueness["comparison_factor_count"] == 104
    assert len(uniqueness["comparisons"]) == 104
    assert all(item["gate_passed"] for item in uniqueness["comparisons"])
    nearest = max(uniqueness["comparisons"], key=lambda item: item["absolute_median_daily_rank_correlation"])
    assert nearest["comparison_factor"] == "late_amount_share_30m"
    assert nearest["absolute_median_daily_rank_correlation"] == 0.42555644028639117
    assert audit["admissible_factor_count"] == 1
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False


def test_campaign074_development_result_has_zero_survivors_and_closed_stress() -> None:
    assert _sha256(TRIAL_LEDGER) == "5e1e28b5b86b6bf44c54a93ed0983dc2586e106a1bf8f1740d328201f0a47d07"
    assert _sha256(SURVIVORS) == "034cf1e72804cf3027606b6b6d96c38893a0356ef2a9c990bdd237cbab0f4481"
    assert _sha256(STRESS) == "24c73ab5a15963ca03b9daead7cc31bdc03aa1ad96a00e5935b563cc91b1f310"
    trial = _load(TRIAL_LEDGER)["entries"][0]
    folds = trial["training_and_validation_folds"]
    assert len(folds) == 3
    assert [fold["validation_metrics"]["association"]["mean_rank_ic"] for fold in folds] == [
        -0.015199722591048851,
        -0.011329858878378488,
        -0.010665389101273421,
    ]
    assert all(fold["validation_metrics"]["normalized_execution"]["net_cumulative_return"] < 0 for fold in folds)
    assert all(fold["validation_metrics"]["pilot_execution_primary_10bp"]["net_cumulative_return"] < 0 for fold in folds)
    survivor = _load(SURVIVORS)
    assert survivor["selected_survivor_count"] == 0
    assert survivor["trial_decisions"][0]["validation_quality_gate_passed"] is False
    assert survivor["trial_decisions"][0]["operationally_admissible"] is True
    stress = _load(STRESS)
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_campaign074_append_only_accounting_and_reports_are_current() -> None:
    assert _sha256(ATTEMPTS) == "ff62c7d62fff13f025466ffa6fe81c3f868165902b2c8f6cd712df50679ebf67"
    ledger = _load(ATTEMPTS)
    assert ledger["campaign074_ledger_entry_count"] == 11
    assert ledger["campaign074_infrastructure_failure_count"] == 9
    assert ledger["campaign074_complete_factor_attempt_count"] == 1
    assert ledger["campaign074_return_reading_development_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 452
    assert ledger["cumulative_return_reading_development_trial_count"] == 276
    assert _sha256(REPORT) == "d86c3a1e1f14d2ac4bd51303a98fea40086a539cc52c28d490ed8055e7e145c1"
    assert _sha256(UNIFIED_REPORT) == "343bcee351b11c1f278eb7e18d374b2ac1845dea396cc117cef76c20f460ebef"
    unified = UNIFIED_REPORT.read_text(encoding="utf-8")
    assert unified.count("## 历史滚动 Campaign074 权威追加") == 1
    assert "累计历史研究尝试由 442 推进到 452" in unified
    assert "累计开发收益试验由 275 推进到 276" in unified


def test_campaign074_preserves_candidate49_empty_ledger_semantics() -> None:
    assert _sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert _load(SIGNAL_LEDGER)["entries"] == []
    assert _load(EXECUTION_LEDGER)["entries"] == []
    payload = execution.validate_reporting_state(
        signal_path=SIGNAL_LEDGER,
        execution_path=EXECUTION_LEDGER,
        evaluation_root=SIGNAL_LEDGER.parent / "candidate49_future_evaluations",
    )
    assert payload["status"] == "candidate49_reporting_state_semantically_validated_read_only"
    assert payload["filesystem_write_performed"] is False
    assert payload["provider_request_issued"] is False
    assert payload["live_order_performed"] is False
