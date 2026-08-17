from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _json(relative: str) -> dict:
    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


def _sha(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def test_campaign152_terminal_authority_bindings() -> None:
    status = _json(
        "docs/a_share_three_day_iteration_status_20260815_campaign152_terminal.json"
    )
    for binding in status["authoritative_inputs"].values():
        assert _sha(binding["path"]) == binding["sha256"]
    assert (
        status["status"]
        == "campaign152_terminal_goal_active_campaign153_historical_prevalue_authorized"
    )
    assert status["goal"]["status"] == "active"


def test_complete_library_appends_definition_but_numeric_library_does_not() -> None:
    policy = _json(
        "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v209_20260815.json"
    )
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 157
    )
    assert (
        policy["complete_historical_feature_library"]["order_sha256"]
        == "c39bb6ca969b5f469a9377a5b5ca743405cec9d8511297ed6a1c44188ef40b82"
    )
    numeric = policy["numerical_comparator_eligibility"]
    assert numeric["eligible_numeric_comparator_count"] == 142
    assert numeric["campaign152_numeric_series_appended"] is False


def test_terminal_result_is_uniqueness_failure_before_returns() -> None:
    result = _json(
        "docs/a_share_three_day_walkforward_campaign_152_terminal_result_20260815.json"
    )
    uniqueness = result["uniqueness_result"]
    assert uniqueness["comparison_count"] == 142
    assert uniqueness["passed_comparison_count"] == 141
    assert uniqueness["failed_comparison_count"] == 1
    assert (
        uniqueness["failed_comparator"] == "intraday_interbar_gap_discovery_share_238p"
    )
    assert uniqueness["absolute_median_daily_rank_correlation"] >= 0.8
    assert result["terminal_decision"]["return_reading_development_trial_count"] == 0
    assert (
        result["research_boundary"][
            "historical_daily_price_or_forward_return_values_read"
        ]
        is False
    )


def test_effective_ledger_chain_and_counts() -> None:
    predecessor = _json(
        "data/experiments/short_horizon/historical_walkforward/campaign_152/research_attempt_ledger_v1.json"
    )
    ledger = _json(
        "data/experiments/short_horizon/historical_walkforward/campaign_152/research_attempt_ledger_v2.json"
    )
    assert ledger["authoritative_predecessor"]["sha256"] == _sha(
        "data/experiments/short_horizon/historical_walkforward/campaign_152/research_attempt_ledger_v1.json"
    )
    previous = predecessor["chain_tip_sha256"]
    for entry in ledger["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign152",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        assert hashlib.sha256(payload.encode()).hexdigest() == entry["entry_sha256"]
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_attempt_count"] == 14
    assert ledger["effective_infrastructure_failure_attempt_count"] == 8
    assert ledger["cumulative_historical_research_attempt_count"] == 1332
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_snapshot_coverage_and_all_comparison_receipts() -> None:
    verification = _json(
        "docs/a_share_three_day_walkforward_campaign_152_feature_snapshot_verification_result_20260815.json"
    )
    coverage = _json(
        "data/experiments/short_horizon/historical_walkforward/campaign_152/coverage/campaign152_coverage_audit.json"
    )
    uniqueness = _json(
        "data/experiments/short_horizon/historical_walkforward/campaign_152/uniqueness/campaign152_ordered_uniqueness_audit.json"
    )
    assert verification["snapshot_manifest"]["eligible_rows"] == 7_724_498
    assert (
        coverage["coverage_and_variation"]["gate_passed_before_comparator_values"]
        is True
    )
    assert len(uniqueness["comparisons"]) == 142
    assert uniqueness["all_142_results_recorded_without_early_stop"] is True
    assert uniqueness["historical_daily_price_or_forward_return_values_read"] is False


def test_candidate49_ledgers_remain_empty_and_exact() -> None:
    signal = "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    execution = (
        "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert (
        _sha(signal)
        == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert (
        _sha(execution)
        == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _json(signal)["entries"] == []
    assert _json(execution)["entries"] == []
