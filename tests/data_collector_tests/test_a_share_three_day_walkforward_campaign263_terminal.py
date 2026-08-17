from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_result_v6_20260816.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v414_20260816.json"
)
PRE_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v7.json"
)
DEV_LEDGER = PRE_LEDGER.with_name("research_attempt_ledger_v8.json")
FINAL_LEDGER = PRE_LEDGER.with_name("research_attempt_ledger_v9.json")
VALIDATION_LEDGER = PRE_LEDGER.with_name("research_attempt_ledger_v10.json")
STATIC_LEDGER = PRE_LEDGER.with_name("research_attempt_ledger_v11.json")
PATCH_LEDGER = PRE_LEDGER.with_name("research_attempt_ledger_v12.json")
EXEMPTION_LEDGER = PRE_LEDGER.with_name("research_attempt_ledger_v13.json")
TRIAL_LEDGER = PRE_LEDGER.parent / "walkforward/trial_ledger.json"
SURVIVORS = PRE_LEDGER.parent / "walkforward/development_survivors.json"
STRESS = PRE_LEDGER.parent / "walkforward/exposed_stress_consumption_record.json"
SIGNAL = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
REPORTS = (
    ROOT / "data/experiments/short_horizon/current_research_report.md",
    ROOT / "data/experiments/short_horizon/three_day_research_report.md",
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_sha256"}
    payload = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_terminal_result_and_policy_bind_current_artifacts() -> None:
    result = _load(RESULT)
    policy = _load(POLICY)
    assert (
        _sha256(RESULT)
        == "e4b11b5d857d2e1377d174d9b1c9c16c5910d5f6f72b446940a2119df49f2cff"
    )
    assert (
        _sha256(POLICY)
        == "a41c4a3849d5a14c448e76d9c7f6cc5bf0603da2b8db57cadc85d1534349dac0"
    )
    assert policy["version"] == 414
    assert policy["authoritative_campaign263_terminal_result"]["sha256"] == _sha256(
        RESULT
    )
    for item in result["authoritative_inputs"].values():
        assert _sha256(ROOT / item["path"]) == item["sha256"]


def test_uniqueness_passed_but_the_only_development_trial_failed() -> None:
    result = _load(RESULT)["scientific_result"]
    assert result["factor"] == "intraday_amount_profile_spectral_entropy_60f"
    assert result["coverage_gate_passed"] is True
    assert result["numeric_comparison_count"] == 142
    assert result["numeric_uniqueness_passed"] is True
    assert result["maximum_observed_absolute_median_daily_rank_correlation"] == (
        0.7210231781829792
    )
    assert result["development_trial_count"] == 1
    assert result["positive_mean_rank_ic_fold_count"] == 3
    assert result["positive_normalized_return_fold_count"] == 0
    assert result["positive_pilot_return_fold_count"] == 0
    assert result["development_aggregate_20bp_return"] == -0.3153288524795882
    assert result["development_survivor_count"] == 0
    assert result["stress_trial_count_2024_2025"] == 0
    assert result["stress_2024_2025_opened"] is False
    assert result["retry_or_rescue_allowed"] is False


def test_trial_ledger_and_survivor_decision_are_exact() -> None:
    trial = _load(TRIAL_LEDGER)
    survivor = _load(SURVIVORS)
    stress = _load(STRESS)
    assert len(trial["entries"]) == 1
    assert trial["entries"][0]["trial_id"] == (
        "wf263_intraday_amount_profile_spectral_entropy_60f_single_higher"
    )
    decision = survivor["trial_decisions"][0]
    assert survivor["selected_survivor_count"] == 0
    assert decision["operationally_admissible"] is True
    assert decision["development_survivor_gate_passed"] is False
    assert decision["validation_quality_rejection_reasons"] == [
        "insufficient_positive_normalized_return_folds",
        "insufficient_positive_pilot_return_folds",
        "median_validation_pilot_return",
        "worst_validation_normalized_drawdown",
        "nonpositive_development_aggregate_20bp_return",
    ]
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_append_only_recovery_chain_and_attempt_accounting() -> None:
    pre = _load(PRE_LEDGER)
    previous = pre["authoritative_predecessor"]["chain_tip_sha256"]
    for ordinal, entry in enumerate(pre["entries"], 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        previous = entry["entry_sha256"]
    assert previous == pre["chain_tip_sha256"]
    dev = _load(DEV_LEDGER)
    dev_entry = dev["delta_entries"][0]
    assert dev_entry["ordinal"] == 29
    assert dev_entry["previous_entry_sha256"] == pre["chain_tip_sha256"]
    assert dev_entry["entry_sha256"] == _entry_hash(dev_entry)
    final = _load(FINAL_LEDGER)
    final_entry = final["delta_entries"][0]
    assert final_entry["ordinal"] == 30
    assert final_entry["previous_entry_sha256"] == dev["chain_tip_sha256"]
    assert final_entry["entry_sha256"] == _entry_hash(final_entry)
    assert final["chain_tip_sha256"] == final_entry["entry_sha256"]
    validation = _load(VALIDATION_LEDGER)
    validation_entry = validation["delta_entries"][0]
    assert validation_entry["ordinal"] == 31
    assert validation_entry["previous_entry_sha256"] == final["chain_tip_sha256"]
    assert validation_entry["entry_sha256"] == _entry_hash(validation_entry)
    assert validation["chain_tip_sha256"] == validation_entry["entry_sha256"]
    static = _load(STATIC_LEDGER)
    static_entry = static["delta_entries"][0]
    assert static_entry["ordinal"] == 32
    assert static_entry["previous_entry_sha256"] == validation["chain_tip_sha256"]
    assert static_entry["entry_sha256"] == _entry_hash(static_entry)
    assert static["chain_tip_sha256"] == static_entry["entry_sha256"]
    patch = _load(PATCH_LEDGER)
    patch_entry = patch["delta_entries"][0]
    assert patch_entry["ordinal"] == 33
    assert patch_entry["previous_entry_sha256"] == static["chain_tip_sha256"]
    assert patch_entry["entry_sha256"] == _entry_hash(patch_entry)
    assert patch["chain_tip_sha256"] == patch_entry["entry_sha256"]
    exemption = _load(EXEMPTION_LEDGER)
    exemption_entry = exemption["delta_entries"][0]
    assert exemption_entry["ordinal"] == 34
    assert exemption_entry["previous_entry_sha256"] == patch["chain_tip_sha256"]
    assert exemption_entry["entry_sha256"] == _entry_hash(exemption_entry)
    assert exemption["chain_tip_sha256"] == exemption_entry["entry_sha256"]
    assert exemption["effective_entry_count"] == 34
    assert exemption["effective_infrastructure_failure_attempt_count"] == 25
    assert exemption["effective_return_reading_development_trial_count"] == 1
    assert exemption["cumulative_historical_research_attempt_count"] == 2597
    assert exemption["cumulative_return_reading_development_trial_count"] == 315


def test_library_and_candidate49_semantics_are_terminal() -> None:
    policy = _load(POLICY)
    library = policy["complete_historical_feature_library"]
    comparison = policy["numerical_comparator_eligibility"]
    assert library["factor_definition_count"] == 162
    assert library["order_sha256"] == (
        "974f2c1f16a85eb43a0bd1e8db768dbe120cd8826c1754d5f220bf9f1d4a3ea0"
    )
    assert comparison["eligible_numeric_comparator_count"] == 143
    assert comparison["order_sha256"] == (
        "f4fbf3d578e2c80c29425716a30d60a3df01d67d04e37f1651236c4dff899588"
    )
    assert comparison["campaign263_numeric_comparator_appended"] is True
    assert _sha256(SIGNAL) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []


def test_unified_reports_have_one_matching_campaign263_section() -> None:
    heading = "## Campaign263：成交额轮廓频谱熵开发终止（2026-08-16）"
    for path in REPORTS:
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "0.721023" in text
        assert "−31.53%" in text
        assert "Campaign264" in text


def test_campaign264_boundary_is_offline_only_and_current_use_is_forbidden() -> None:
    policy = _load(POLICY)
    assert policy["future_campaign_boundary"]["next_campaign"] == 264
    assert (
        policy["future_campaign_boundary"][
            "historical_offline_prevalue_work_may_continue_at_any_local_time"
        ]
        is True
    )
    boundary = policy["research_boundary"]
    assert boundary["stress_2024_2025_opened"] is False
    assert boundary["provider_or_web_request_issued"] is False
    assert boundary["candidate49_plan_or_run_executed"] is False
    assert boundary["candidate49_ledgers_changed"] is False
    assert (
        boundary["current_scoring_selection_sizing_positions_or_orders_performed"]
        is False
    )
    assert boundary["investment_advice"] is False
