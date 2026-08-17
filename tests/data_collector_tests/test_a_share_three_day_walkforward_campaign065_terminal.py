from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as validator


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
CAMPAIGN_ROOT = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_065"
AUDIT = CAMPAIGN_ROOT / "no_return/20260805T065707Z_campaign065_no_return_audit.json"
TRIAL_LEDGER = CAMPAIGN_ROOT / "walkforward/trial_ledger.json"
SURVIVORS = CAMPAIGN_ROOT / "walkforward/development_survivors.json"
STRESS = CAMPAIGN_ROOT / "walkforward/exposed_stress_consumption_record.json"
ATTEMPTS = CAMPAIGN_ROOT / "research_attempt_ledger_v7.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_065_research_record.json"
FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_065_terminal_completion_freeze_20260805.json"
POLICY = ROOT / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v2_20260805.json"
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_065_report.md"
UNIFIED_REPORT = ROOT / "data/experiments/short_horizon/three_day_research_report.md"
REPORT_GENERATOR = ROOT / "scripts/a_share_short_horizon_factor_research.py"
SIGNAL_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
FACTOR = "intraday_range_weak_order_time_reversal_divergence_236t"
C63_FACTOR = "intraday_cross_sectional_standardized_return_state_stability_236p"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _order_digest(items: list[dict]) -> str:
    payload = json.dumps(
        [[str(item["name"]), str(item["score_direction"])] for item in items],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_terminal_artifact_bindings_are_current() -> None:
    assert _sha256(RECORD) == "32d5dd18e5d14d30e327604ab02271c6ce74167ae96420d8aabca75f008590bc"
    assert _sha256(FREEZE) == "827c75b6c8fa97f88d823913278f926d63d94cba76efabbb52bd416d88dd3946"
    assert _sha256(POLICY) == "bad778474b4119f3a8f617283e2b4719f076fe060f11275aed7e7c469d6d4bf2"
    for path, expected in ((RECORD, 21), (FREEZE, 8), (POLICY, 7)):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0
        assert result["binding_count"] == expected


def test_no_return_admission_is_coverage_first_and_complete() -> None:
    assert _sha256(AUDIT) == "0e04aec29c4cd4b2bced6ba57d6556350a0fba4318de3e339d63ce8ef19401c0"
    audit = _load(AUDIT)
    coverage = audit["coverage_and_capacity"][FACTOR]
    unique = audit["uniqueness"][FACTOR]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert coverage["eligible_names_p05"] == 138.0
    assert coverage["potential_non_overlapping_three_session_cohorts"] == 540
    assert unique["comparison_factor_count"] == 95
    assert unique["comparison_order_matches_preregistration"] is True
    assert unique["all_required_numeric_comparisons_passed"] is True
    assert unique["maximum_observed_absolute_median_daily_rank_correlation"] == 0.17806408717814648
    assert audit["admissible_factor_count"] == 1
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["provider_request_issued"] is False


def test_development_result_is_zero_survivors_and_stress_closed() -> None:
    assert _sha256(TRIAL_LEDGER) == "d9ca8ad4656dde69e0bcbb0d184e77af86c4ab486425cbd644f61fb09b274b25"
    survivors = _load(SURVIVORS)
    decision = survivors["trial_decisions"][0]
    assert survivors["selected_survivor_count"] == 0
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 0
    assert decision["positive_normalized_return_fold_count"] == 1
    assert decision["positive_pilot_return_fold_count"] == 1
    assert decision["development_aggregate_20bp_return"] == -0.0921814012939457
    assert decision["operationally_admissible"] is False
    assert decision["operational_rejection_reasons"] == [
        "fold_1_board_lot_affordability",
        "fold_2_board_lot_affordability",
        "fold_3_board_lot_affordability",
    ]
    stress = _load(STRESS)
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_append_only_attempt_accounting_includes_status_failures() -> None:
    assert _sha256(ATTEMPTS) == "b916f0990306618609d79e7ccca7b32ab22027cea76733ec432159ed839800cf"
    ledger = _load(ATTEMPTS)
    assert ledger["campaign065_attempt_count"] == 11
    assert ledger["campaign065_ledger_entry_count"] == 12
    assert ledger["campaign065_infrastructure_or_synthetic_failure_count"] == 7
    assert ledger["campaign065_complete_factor_attempt_count"] == 1
    assert ledger["campaign065_historical_return_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 392
    assert ledger["cumulative_return_reading_development_trial_count"] == 272
    assert [item["exit_code"] for item in ledger["appended_entries"]] == [127, 1]


def test_campaign066_policy_appends_campaign065_before_new_values() -> None:
    audit = _load(AUDIT)
    numeric = [
        {"name": item["comparison_factor"], "score_direction": item["score_direction"]}
        for item in audit["uniqueness"][FACTOR]["comparisons"]
    ]
    full = numeric[:-1] + [{"name": C63_FACTOR, "score_direction": "higher"}] + numeric[-1:]
    appended = {"name": FACTOR, "score_direction": "higher"}
    policy = _load(POLICY)
    assert len(full) == 96
    assert _order_digest(full) == "974e3acd06536dcfbcc13524932f771f3636ac32023b2712f5d2d76f4d1f2d92"
    assert _order_digest(full + [appended]) == policy["complete_historical_feature_library"]["order_sha256"]
    assert _order_digest(numeric + [appended]) == policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_order_sha256"]
    assert policy["scope"]["effective_start_campaign"] == 66
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 97
    assert policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"] == 96


def test_report_and_candidate49_isolation_are_current() -> None:
    text = REPORT.read_text(encoding="utf-8")
    for expected in ("Campaign065", "0.178064", "-9.218140%", "392", "272"):
        assert expected in text
    assert _sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert _load(SIGNAL_LEDGER).get("entries", []) == []
    assert _load(EXECUTION_LEDGER).get("entries", []) == []


def test_unified_report_and_generator_contain_one_current_campaign065_section() -> None:
    report = UNIFIED_REPORT.read_text(encoding="utf-8")
    source = REPORT_GENERATOR.read_text(encoding="utf-8")
    assert report.count("## 历史滚动 Campaign065 权威追加") == 1
    assert "`-0.000294/-0.008297/-0.016556`" in report
    assert "聚合 20bp 收益为 `-9.218140%`" in report
    assert "累计历史研究尝试推进到 392" in report
    assert "65: (" in source
    assert "`+2.838227%/-4.741804%/-0.337072%`" in source
