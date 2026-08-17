from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator
from scripts import a_share_three_day_walkforward_campaign075_features as features
from scripts import a_share_tushare_candidate49_future_execution as execution


ROOT = Path(__file__).resolve().parents[2]
MINUTE_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
CAMPAIGN_ROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_075"
AUDIT = CAMPAIGN_ROOT / "no_return/20260806T015958Z_campaign075_no_return_audit.json"
ATTEMPTS = CAMPAIGN_ROOT / "research_attempt_ledger_v4.json"
TRIAL_LEDGER = CAMPAIGN_ROOT / "walkforward/trial_ledger.json"
SURVIVORS = CAMPAIGN_ROOT / "walkforward/development_survivors.json"
STRESS = CAMPAIGN_ROOT / "walkforward/exposed_stress_consumption_record.json"
ENGINE_REPORT = CAMPAIGN_ROOT / "walkforward/campaign_report.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_075_research_record_v3.json"
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_075_report.md"
POLICY = ROOT / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v11_20260806.json"
UNIFIED = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
PIPELINE = ROOT / "docs/a_share_data_pipeline.md"
SIGNAL_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
FACTOR = "accepted_instrument_session_youth_20s"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _value_sha256(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_campaign075_research_record_bindings_and_terminal_result() -> None:
    assert _sha256(RECORD) == "36709db098e6abb090c24bfd5aab969346f218657ea3e10638a05c5620fcf32d"
    receipt = validator.validate_record(RECORD, data_root=MINUTE_ROOT)
    assert receipt["all_bindings_passed"] is True
    assert receipt["binding_count"] == 3
    record = _load(RECORD)
    assert record["unchanged_factor_and_result"]["factor"] == FACTOR
    assert record["unchanged_factor_and_result"]["factor_terminal"] is True
    assert record["unchanged_factor_and_result"]["development_survivor_count"] == 0
    assert record["unchanged_factor_and_result"]["stress_2024_2025_opened"] is False
    assert record["current_attempt_accounting"]["campaign075_attempts"] == 9
    assert record["current_attempt_accounting"]["cumulative_historical_attempts"] == 456
    assert record["current_attempt_accounting"]["cumulative_return_reading_development_trials"] == 277


def test_campaign075_no_return_gate_admits_one_numeric_factor() -> None:
    assert _sha256(AUDIT) == "83fcd1907e1aaa56bae9bd03e4051025167402bc20bf46a4bfdad800cc57646b"
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["candidate_eligible_rows"] == 1330171
    assert coverage["quality_listing_eligible_rows"] == 1331759
    assert uniqueness["comparison_factor_count"] == 105
    assert len(uniqueness["comparisons"]) == 105
    assert all(item["gate_passed"] for item in uniqueness["comparisons"])
    nearest = max(
        uniqueness["comparisons"],
        key=lambda item: item["absolute_median_daily_rank_correlation"],
    )
    assert nearest["comparison_factor"] == "intraday_microgap_absorption_share_238p"
    assert nearest["median_daily_rank_correlation"] == -0.5439796276434999
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False


def test_campaign075_append_only_trial_chain_zero_survivors_and_closed_stress() -> None:
    assert _sha256(TRIAL_LEDGER) == "14079e97e5f2b421c525f6534026634cbc7abdc0eab3cc488b4e69c7ae76fe4f"
    ledger = _load(TRIAL_LEDGER)
    assert [item["phase"] for item in ledger["entries"]] == [
        "infrastructure_failure",
        "development_walkforward_2019_2023",
    ]
    previous = ledger["chain_genesis"]
    for ordinal, entry in enumerate(ledger["entries"], start=1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
        assert entry["entry_sha256"] == _value_sha256(payload)
        previous = entry["entry_sha256"]
    assert ledger["chain_tip_sha256"] == previous
    trial = ledger["entries"][1]
    assert [item["association"]["mean_rank_ic"] for item in trial["validation_metrics"]] == [
        -0.002682267538920306,
        -0.0239290875941235,
        -0.013780087584814799,
    ]
    assert _load(SURVIVORS)["selected_survivor_count"] == 0
    stress = _load(STRESS)
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert _load(ENGINE_REPORT)["infrastructure_failure_count"] == 0


def test_campaign075_current_attempt_accounting_includes_runtime_failure() -> None:
    assert _sha256(ATTEMPTS) == "ab8788d75885f2a1d9aa5d10f3ac4ce3ebad3a9659e5972e0cfb7e224ecf4e0f"
    ledger = _load(ATTEMPTS)
    assert ledger["campaign075_ledger_entry_count"] == 10
    assert ledger["campaign075_infrastructure_failure_count"] == 8
    assert ledger["campaign075_complete_factor_attempt_count"] == 1
    assert ledger["campaign075_return_reading_development_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 456
    assert ledger["cumulative_return_reading_development_trial_count"] == 277


def test_campaign075_v11_definition_and_numeric_orders_are_frozen() -> None:
    assert _sha256(POLICY) == "5ab04c661040e4f073a0081f421500c758966266a23b60b2ec09c8a501fd6a2d"
    receipt = validator.validate_record(POLICY, data_root=MINUTE_ROOT)
    assert receipt["all_bindings_passed"] is True
    appended = {"name": FACTOR, "score_direction": "higher"}
    full = features.reconstruct_complete_definitions() + [appended]
    numeric = features.reconstruct_comparisons() + [appended]
    policy = _load(POLICY)
    assert len(full) == 107
    assert features._comparison_order_digest(full) == policy[
        "complete_historical_feature_library"
    ]["order_sha256"]
    assert len(numeric) == 106
    assert features._comparison_order_digest(numeric) == policy[
        "numerical_comparator_eligibility"
    ]["eligible_numeric_comparator_order_sha256"]


def test_campaign075_reports_and_candidate49_boundaries_are_current() -> None:
    assert _sha256(REPORT) == "c7af20097efd8b493389bbeebe77312683f8a68486a14b90d67b6b8280a5ff49"
    assert _sha256(UNIFIED) == "7591d7bcb06c4176499c2ef42727ba50329adc5541a641ce207945a9843c6df9"
    assert _sha256(PIPELINE) == "834ac51a6adff8980b999ce8cbdd9cd9a64fb60721725fe6fa1da01e404d3397"
    assert UNIFIED.read_text(encoding="utf-8").count("## 历史滚动 Campaign075 权威追加") == 1
    assert PIPELINE.read_text(encoding="utf-8").count("## Campaign075：接受覆盖会话年轻度") == 1
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
    assert payload["provider_request_issued"] is False
    assert payload["live_order_performed"] is False
