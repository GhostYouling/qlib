from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator
from scripts import a_share_tushare_candidate49_future_execution as execution


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
CAMPAIGN_ROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_073"
AUDIT = CAMPAIGN_ROOT / "no_return/20260805T231452Z_campaign073_no_return_audit.json"
ATTEMPTS = CAMPAIGN_ROOT / "research_attempt_ledger_v2.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_073_research_record_v2.json"
POLICY = ROOT / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v8_20260806.json"
PREREG = ROOT / "docs/a_share_three_day_walkforward_campaign_073_no_return_preregistration.json"
SNAPSHOT_BINDING = ROOT / "docs/a_share_three_day_walkforward_campaign_073_feature_snapshot_binding_20260806.json"
CAMPAIGN_REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_073_report.md"
UNIFIED_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
SIGNAL_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
FACTOR = "intraday_terminal_nominal_share_price_affordability_rank_240m"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign073_protocol_policy_and_research_record_bindings_are_current() -> None:
    assert _sha256(POLICY) == "c936e9df4bd8ac8cdb23ee27d16796a612341c84577ee60f727e8a3cf72cb1db"
    assert _sha256(PREREG) == "473373e71a97b9daf25f97062682ec4ad1f8b05a778efad161c887aa586d5280"
    assert _sha256(SNAPSHOT_BINDING) == "0bf34d781cff79f9f8e8262173a78699232cfa5271bd12b2fb897a9173698ae7"
    assert _sha256(RECORD) == "dc97df498f35cecbd8b5bb276e949849def5047dff12043f6e2ea6b76770b490"

    policy = _load(POLICY)
    prereg = _load(PREREG)
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 104
    assert policy["complete_historical_feature_library"]["order_sha256"] == (
        "45686a0e92d16896d3c1702938f73aa173cb44252d9b76b482623c617d2bda5d"
    )
    assert policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"] == 103
    assert policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_order_sha256"] == (
        "28dd90482da7c263873f829e0268fbf4d4fffa53561a9e628797ced4c54991cc"
    )
    uniqueness = prereg["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert prereg["candidate"]["name"] == FACTOR
    assert prereg["candidate"]["direction"] == "higher"
    assert uniqueness["numeric_comparator_count"] == 103
    assert uniqueness["numeric_comparator_order_sha256"] == (
        "28dd90482da7c263873f829e0268fbf4d4fffa53561a9e628797ced4c54991cc"
    )

    receipt = validator.validate_record(RECORD, data_root=DATA_ROOT)
    assert receipt["all_bindings_passed"] is True
    assert receipt["binding_count"] == 14


def test_campaign073_snapshot_identity_is_current_without_rebuilding() -> None:
    manifest = _load(
        DATA_ROOT
        / "derived/a_share/rich/tushare/minute_walkforward_campaign073_feature_library"
        / "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign073_feature_library_v1"
        / "snapshot_manifest.json"
    )
    assert _sha256(
        DATA_ROOT
        / "derived/a_share/rich/tushare/minute_walkforward_campaign073_feature_library"
        / "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign073_feature_library_v1"
        / "snapshot_manifest.json"
    ) == "6b281be298be7df908300db6735e3ed3efc7d7c13b44c2ae679bf5a2073940e4"
    assert manifest["dataset_sha256"] == "2cea2e0502be1c5cc70f93260a96175abac5f36af50482847c35746a80252a5f"
    assert len(manifest["files"]) == 33015
    assert sum(int(item["rows"]) for item in manifest["files"]) == 7724498
    assert manifest["factor_eligible_rows"][FACTOR] == 7724498


def test_campaign073_coverage_passes_then_exact_uniqueness_rejection_stops_returns() -> None:
    assert _sha256(AUDIT) == "82fd04603093b80048e0e874b01ca961a4bb10ab0991052b66e7f42e26cac557"
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]]

    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["quality_listing_eligible_rows"] == 1331759
    assert coverage["candidate_eligible_rows"] == 1330171
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert coverage["eligible_names_p05"] == 138.0
    assert coverage["potential_non_overlapping_three_session_cohorts"] == 540
    assert uniqueness["comparison_factor_count"] == 103
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert len(uniqueness["comparisons"]) == 103
    assert len(failed) == 1
    assert failed[0]["comparison_factor"] == "intraday_price_update_share_238m"
    assert failed[0]["median_daily_rank_correlation"] == -0.8607906131941189
    assert failed[0]["absolute_median_daily_rank_correlation"] == 0.8607906131941189
    assert failed[0]["daily_rank_correlation_p05"] == -0.9095197560503101
    assert failed[0]["daily_rank_correlation_p95"] == -0.7877230226632117
    assert failed[0]["minimum_pairwise_names_observed"] == 52
    assert failed[0]["pairwise_sessions"] == 1623
    assert audit["admissible_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["training_or_model_fitting_performed"] is False
    assert audit["provider_request_issued"] is False
    assert audit["current_scoring_selection_sizing_or_orders_performed"] is False


def test_campaign073_corrected_append_only_accounting_is_current() -> None:
    assert _sha256(ATTEMPTS) == "e0b4d38fb14775e124d3ba9381c79af8614955c6904dca5f3725bc153f66965b"
    ledger = _load(ATTEMPTS)
    assert ledger["supersedes_without_rewriting"]["sha256"] == (
        "143a4086c86fcba088c4d79eb45c159f44825fab6d09e7a9e62cb006f250364d"
    )
    assert ledger["campaign073_ledger_entry_count"] == 5
    assert ledger["campaign073_infrastructure_failure_count"] == 4
    assert ledger["campaign073_complete_factor_attempt_count"] == 1
    assert ledger["campaign073_attempt_count"] == 5
    assert ledger["campaign073_return_reading_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 442
    assert ledger["cumulative_return_reading_development_trial_count"] == 275
    assert [item["ordinal"] for item in ledger["entries"]] == [1, 2, 3, 4, 5]
    assert sum(item["attempt_type"] == "infrastructure_failure" for item in ledger["entries"]) == 4

    record = _load(RECORD)
    assert record["attempt_accounting"]["campaign073_attempts"] == 5
    assert record["attempt_accounting"]["cumulative_historical_attempts"] == 442
    assert record["historical_return_boundary"]["forward_returns_read"] is False
    assert record["historical_return_boundary"]["stress_2024_2025_opened"] is False


def test_campaign073_reports_are_current() -> None:
    assert _sha256(CAMPAIGN_REPORT) == "8872b38cddabb657c74edcb0c78d07e5a45b57714b5cabe2b92f94ee2e98017b"
    assert _sha256(UNIFIED_REPORT) == "15707d2b8f2d3ae12303b01b5feb2592255ece90ebcc27efd1ce57a80f129258"
    report = UNIFIED_REPORT.read_text(encoding="utf-8")
    assert report.count("## 历史滚动 Campaign073 权威追加") == 1
    assert "`-0.860791`" in report
    assert "累计历史研究尝试由 437 推进到 442" in report
    assert "2019–2023 开发折与 2024–2025 压力区间均未打开" in report


def test_campaign073_preserves_candidate49_semantics_and_empty_ledgers() -> None:
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
