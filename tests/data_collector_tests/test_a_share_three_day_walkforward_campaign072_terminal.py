from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator
from scripts import a_share_tushare_candidate49_future_execution as execution


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
CAMPAIGN_ROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_072"
AUDIT = CAMPAIGN_ROOT / "no_return/20260805T221540Z_campaign072_no_return_audit.json"
ATTEMPTS = CAMPAIGN_ROOT / "research_attempt_ledger.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_072_research_record.json"
CAMPAIGN_REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_072_report.md"
UNIFIED_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
SIGNAL_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
FACTOR = "quarterly_joint_profit_revenue_growth_floor_rank"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign072_research_record_bindings_are_current() -> None:
    assert _sha256(RECORD) == "ca554c1db619c640821037a1ee47401b205644b284cff15390f605e94c202209"
    receipt = validator.validate_record(RECORD, data_root=DATA_ROOT)
    assert receipt["all_bindings_passed"] is True
    assert receipt["binding_count"] == 12


def test_campaign072_snapshot_identity_is_current_without_rebuilding() -> None:
    manifest = _load(
        DATA_ROOT
        / "derived/a_share/rich/tushare/minute_walkforward_campaign072_feature_library"
        / "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign072_feature_library_v1"
        / "snapshot_manifest.json"
    )
    assert manifest["dataset_sha256"] == "7baf6939336261bb307fd3dc13ccb8e9676eacbcc7e7d1139e019fb3b96f90b3"
    assert len(manifest["files"]) == 33015
    assert sum(int(item["rows"]) for item in manifest["files"]) == 7724498
    assert manifest["factor_eligible_rows"][FACTOR] == 7231483


def test_campaign072_no_return_rejection_is_exact() -> None:
    assert _sha256(AUDIT) == "d574fa66c316fe27f00698179b64a90fa86dae7adde5d25d0caca33967063054"
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    failed = {
        item["comparison_factor"]: item
        for item in uniqueness["comparisons"]
        if not item["gate_passed"]
    }
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["quality_listing_eligible_rows"] == 1331759
    assert coverage["candidate_eligible_rows"] == 1330171
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert coverage["eligible_names_p05"] == 138.0
    assert coverage["potential_non_overlapping_three_session_cohorts"] == 540
    assert uniqueness["comparison_factor_count"] == 102
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert set(failed) == {"quality_revenue", "quality_growth", "quality_score"}
    assert failed["quality_revenue"]["median_daily_rank_correlation"] == 0.8984481039202764
    assert failed["quality_growth"]["median_daily_rank_correlation"] == 0.9132455824123146
    assert failed["quality_score"]["median_daily_rank_correlation"] == 0.8279200836772669
    assert {item["pairwise_sessions"] for item in failed.values()} == {1623}
    assert audit["admissible_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["training_or_model_fitting_performed"] is False
    assert audit["provider_request_issued"] is False
    assert audit["current_scoring_selection_sizing_or_orders_performed"] is False


def test_campaign072_attempt_accounting_and_reports_are_current() -> None:
    assert _sha256(ATTEMPTS) == "e87982267f69c1e056b20c522eba308523dc845b7c81d6ac021c840b66c87278"
    ledger = _load(ATTEMPTS)
    assert ledger["campaign072_ledger_entry_count"] == 11
    assert ledger["campaign072_infrastructure_failure_count"] == 10
    assert ledger["campaign072_complete_factor_attempt_count"] == 1
    assert ledger["campaign072_attempt_count"] == 11
    assert ledger["campaign072_return_reading_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 437
    assert ledger["cumulative_return_reading_development_trial_count"] == 275
    assert _sha256(CAMPAIGN_REPORT) == "5a09848a0c7d851b22dfbe73b4006cf481049f81aea407102e85a6685c3b109a"
    assert _sha256(UNIFIED_REPORT) == "ea18532f5087446c4bcbdf3c4d51ef1ecd770b506b8aabe9ab9a514431287eed"
    report = UNIFIED_REPORT.read_text(encoding="utf-8")
    assert report.count("## 历史滚动 Campaign072 权威追加") == 1
    assert "`+0.913246`、`+0.898448` 和 `+0.827920`" in report
    assert "Campaign072 在日线价格和 forward return 之前终止" in report
    assert "累计历史研究尝试由 426 推进到 437" in report


def test_campaign072_preserves_candidate49_semantics_and_empty_ledgers() -> None:
    assert _sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert _load(SIGNAL_LEDGER)["entries"] == []
    assert _load(EXECUTION_LEDGER)["entries"] == []
    payload = execution.validate_reporting_state(
        signal_path=SIGNAL_LEDGER,
        execution_path=EXECUTION_LEDGER,
        evaluation_root=SIGNAL_LEDGER.parent / "candidate49_future_evaluations",
    )
    assert payload["signal_entries"] == []
    assert payload["execution_entries"] == []
    assert payload["status"] == "candidate49_reporting_state_semantically_validated_read_only"
    assert payload["filesystem_write_performed"] is False
    assert payload["provider_request_issued"] is False
    assert payload["live_order_performed"] is False
