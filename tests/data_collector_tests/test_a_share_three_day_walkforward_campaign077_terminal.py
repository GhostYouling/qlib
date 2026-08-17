from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FACTOR = "intraday_amount_clock_dispersion_240m"


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_terminal_research_result_and_additive_accounting_are_consistent() -> None:
    record = _load("docs/a_share_three_day_walkforward_campaign_077_research_record.json")
    correction = _load(
        "docs/a_share_three_day_walkforward_campaign_077_postcompletion_accounting_correction_v2_20260806.json"
    )
    ledger = _load(
        "data/experiments/short_horizon/historical_walkforward/campaign_077/research_attempt_ledger_v8.json"
    )
    assert record["status"] == "terminal_zero_development_survivors_stress_closed"
    assert record["development_trial"]["survivor_decision"]["development_survivor_count"] == 0
    assert correction["research_values_changed"] is False
    assert correction["corrected_attempt_accounting"] == {
        "campaign077_infrastructure_failures": 9,
        "campaign077_complete_factor_attempts": 1,
        "campaign077_attempts": 10,
        "campaign077_ledger_entries": 11,
        "campaign077_return_reading_development_trials": 1,
        "cumulative_historical_attempts": 478,
        "cumulative_return_reading_development_trials": 279,
    }
    assert ledger["campaign077_infrastructure_failure_count"] == 9
    assert ledger["campaign077_ledger_entry_count"] == 11
    assert ledger["cumulative_historical_research_attempt_count"] == 478


def test_no_return_audit_passed_coverage_and_all_107_comparisons() -> None:
    audit = _load(
        "data/experiments/short_horizon/historical_walkforward/campaign_077/no_return/"
        "20260806T051558Z_campaign077_no_return_audit.json"
    )
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["candidate_eligible_rows"] == 1_330_171
    assert uniqueness["comparison_factor_count"] == 107
    assert uniqueness["all_required_numeric_comparisons_passed"] is True
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False


def test_single_development_trial_has_zero_survivors_and_closed_stress() -> None:
    ledger = _load(
        "data/experiments/short_horizon/historical_walkforward/campaign_077/walkforward/trial_ledger.json"
    )
    survivors = _load(
        "data/experiments/short_horizon/historical_walkforward/campaign_077/walkforward/development_survivors.json"
    )
    stress = _load(
        "data/experiments/short_horizon/historical_walkforward/campaign_077/walkforward/"
        "exposed_stress_consumption_record.json"
    )
    assert len(ledger["entries"]) == 1
    assert survivors["selected_survivor_count"] == 0
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_v13_appends_campaign077_to_both_frozen_orders() -> None:
    policy = _load(
        "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v13_20260806.json"
    )
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert complete["factor_definition_count"] == 109
    assert complete["order_sha256"] == "69bd56c8489064aa68e9cff7a6479f85e11ce23f855d79ba6a66bef9e72b08bc"
    assert numeric["eligible_numeric_comparator_count"] == 108
    assert (
        numeric["eligible_numeric_comparator_order_sha256"]
        == "7bdadc28e8d79b87cc16dcdbbd5e50964fa6ea8de9a5fb32023ddb05422fd1bc"
    )
    assert numeric["newly_appended_comparator"]["name"] == FACTOR


def test_candidate49_ledgers_remain_empty_and_immutable() -> None:
    for path, expected in (
        (
            "data/experiments/short_horizon/candidate49_future_signal_ledger.json",
            "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79",
        ),
        (
            "data/experiments/short_horizon/candidate49_future_execution_ledger.json",
            "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f",
        ),
    ):
        artifact = _load(path)
        assert _sha(path) == expected
        assert artifact["entries"] == []


def test_reports_include_campaign077_and_terminal_loss_without_trading_claims() -> None:
    for path, frozen_loss_text in (
        ("docs/a_share_three_day_walkforward_campaign_077_report.md", "0.364508"),
        ("data/experiments/short_horizon/three_day_research_report.md", "36.450754"),
        ("docs/a_share_data_pipeline.md", "0.364508"),
    ):
        report = (ROOT / path).read_text(encoding="utf-8")
        assert "Campaign077" in report
        assert frozen_loss_text in report
        assert "Candidate49" in report


def test_current_terminal_artifact_hashes() -> None:
    assert (
        _sha("docs/a_share_three_day_walkforward_campaign_077_research_record.json")
        == "befe34e7ed424f709628e934b734c76e0c67c2b132e534480a06b926c2f66ca5"
    )
    assert (
        _sha("docs/a_share_three_day_walkforward_campaign_077_postcompletion_accounting_correction_v2_20260806.json")
        == "bfbee70dfab48551a7f46f85e599f016b5a08d9bcbf595b5270d09b469c3143b"
    )
    assert (
        _sha("data/experiments/short_horizon/historical_walkforward/campaign_077/research_attempt_ledger_v8.json")
        == "d2e61cf91f5e3ec45ed45ce880492ed93d143efb78cfe1fa0234d5073efb8ad7"
    )
    assert (
        _sha("docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v13_20260806.json")
        == "fa8c48949ba1d57a10003c04003018d72bb9a54030111bc2ce3fbf9e1c042643"
    )
