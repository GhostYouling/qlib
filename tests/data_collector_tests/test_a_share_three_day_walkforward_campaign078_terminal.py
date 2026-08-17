from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign078_features as features


ROOT = Path(__file__).resolve().parents[2]
FACTOR = "intraday_amount_local_peak_density_238p"


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_terminal_research_result_and_additive_accounting_are_consistent() -> None:
    record = _load("docs/a_share_three_day_walkforward_campaign_078_research_record_v4.json")
    ledger = _load(
        "data/experiments/short_horizon/historical_walkforward/campaign_078/"
        "research_attempt_ledger_v5.json"
    )
    assert record["status"] == "terminal_zero_development_survivors_stress_closed"
    assert record["development_trial"]["survivor_decision"]["development_survivor_count"] == 0
    assert len(record["postcompletion_infrastructure_failures"]) == 3
    assert all(
        item["research_values_or_returns_recomputed"] is False
        for item in record["postcompletion_infrastructure_failures"]
    )
    assert record["attempt_accounting"] == {
        "campaign078_infrastructure_failures": 4,
        "campaign078_complete_factor_attempts": 1,
        "campaign078_attempts": 5,
        "campaign078_ledger_entries": 6,
        "campaign078_return_reading_development_trials": 1,
        "cumulative_historical_attempts": 483,
        "cumulative_return_reading_development_trials": 280,
    }
    assert ledger["campaign078_infrastructure_failure_count"] == 4
    assert ledger["campaign078_ledger_entry_count"] == 6
    assert ledger["cumulative_historical_research_attempt_count"] == 483
    assert ledger["cumulative_return_reading_development_trial_count"] == 280


def test_no_return_audit_passed_coverage_and_all_108_comparisons() -> None:
    audit = _load(
        "data/experiments/short_horizon/historical_walkforward/campaign_078/no_return/"
        "20260806T063847Z_campaign078_no_return_audit.json"
    )
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["candidate_eligible_rows"] == 1_330_171
    assert uniqueness["comparison_factor_count"] == 108
    assert uniqueness["all_required_numeric_comparisons_passed"] is True
    assert uniqueness["maximum_observed_absolute_median_daily_rank_correlation"] == 0.1895045287399153
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False


def test_single_development_trial_has_zero_survivors_and_closed_stress() -> None:
    trial = _load(
        "data/experiments/short_horizon/historical_walkforward/campaign_078/walkforward/"
        "trial_ledger.json"
    )
    survivors = _load(
        "data/experiments/short_horizon/historical_walkforward/campaign_078/walkforward/"
        "development_survivors.json"
    )
    stress = _load(
        "data/experiments/short_horizon/historical_walkforward/campaign_078/walkforward/"
        "exposed_stress_consumption_record.json"
    )
    assert len(trial["entries"]) == 1
    assert survivors["selected_survivor_count"] == 0
    decision = survivors["trial_decisions"][0]
    assert decision["positive_mean_rank_ic_fold_count"] == 3
    assert decision["positive_pilot_return_fold_count"] == 0
    assert decision["development_aggregate_20bp_return"] == -0.11446777783710638
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_v14_appends_campaign078_to_both_frozen_orders() -> None:
    policy = _load(
        "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v14_timestamp_corrected_20260806.json"
    )
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    new = {"name": FACTOR, "score_direction": "higher"}
    assert complete["factor_definition_count"] == 110
    assert complete["order_sha256"] == features._comparison_order_digest(
        features.reconstruct_complete_definitions() + [new]
    )
    assert complete["order_sha256"] == "4d3003f8580945a66dac7426f535a58f8725d1d880bb4cb552d87b477e826463"
    assert numeric["eligible_numeric_comparator_count"] == 109
    assert numeric["eligible_numeric_comparator_order_sha256"] == features._comparison_order_digest(
        features.reconstruct_comparisons() + [new]
    )
    assert (
        numeric["eligible_numeric_comparator_order_sha256"]
        == "0893e0ff54c0094e48e67def84f0038a453fd11230629631e3e54120480a3529"
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


def test_reports_include_campaign078_and_terminal_loss_without_trading_claims() -> None:
    for path, frozen_loss_text in (
        ("docs/a_share_three_day_walkforward_campaign_078_report.md", "0.114468"),
        ("data/experiments/short_horizon/three_day_research_report.md", "11.446778"),
        ("docs/a_share_data_pipeline.md", "0.114468"),
    ):
        report = (ROOT / path).read_text(encoding="utf-8")
        assert "Campaign078" in report
        assert frozen_loss_text in report
        assert "Candidate49" in report


def test_current_terminal_artifact_hashes() -> None:
    assert (
        _sha("docs/a_share_three_day_walkforward_campaign_078_research_record_v4.json")
        == "44f9402d485c84725378141ec73a96e76121754834752c027b22e730d4e3bfd1"
    )
    assert (
        _sha(
            "data/experiments/short_horizon/historical_walkforward/campaign_078/"
            "research_attempt_ledger_v5.json"
        )
        == "dab1c811a04c4e4d4a9fce11932c137b074eb1e99c57247b53d5aa5c15b68a4c"
    )
    assert (
        _sha(
            "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v14_timestamp_corrected_20260806.json"
        )
        == "8f518f6db27a7026f59c0332e38972a3752022ee9b11134d4257ca08f238407b"
    )
