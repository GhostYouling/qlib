from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign097_features as definitions


ROOT = Path(__file__).resolve().parents[2]
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_099_terminal_verification_20260807.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v48_20260807.json"
)
ATTEMPTS = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_099/research_attempt_ledger_v18.json"
)
WALKFORWARD = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_099/walkforward"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_terminal_result_and_stress_boundary_are_exact() -> None:
    terminal = _load(TERMINAL)
    assert terminal["status"] == (
        "verified_terminal_zero_development_survivors_stress_not_opened"
    )
    assert terminal["factor"] == (
        "intraday_market_close_location_profile_synchronization_240m"
    )
    assert terminal["no_return_admission"]["numeric_comparison_count"] == 127
    assert terminal["no_return_admission"]["all_numeric_comparisons_passed"]
    assert terminal["development"]["survivor_decision"]["selected_survivor_count"] == 0
    assert not terminal["development"]["survivor_decision"][
        "development_survivor_gate_passed"
    ]
    assert terminal["exposed_stress"]["stress_interval_opened"] is False
    assert terminal["exposed_stress"]["stress_return_fields_read"] is False


def test_engine_outputs_preserve_failure_then_one_complete_trial() -> None:
    ledger_path = WALKFORWARD / "trial_ledger.json"
    survivor_path = WALKFORWARD / "development_survivors.json"
    stress_path = WALKFORWARD / "exposed_stress_consumption_record.json"
    assert _sha256(ledger_path) == (
        "3732090e257465078516a9cfa86d432273cef24e6dd8cff820af6288c2e60a76"
    )
    assert _sha256(survivor_path) == (
        "fe3203f26337fd04bc9e22bddfdb3a72a021513514b89a56ee5b2ebcf26ddf08"
    )
    assert _sha256(stress_path) == (
        "b3726634c30ba5c6892212db1a4170bd36f0fd6f0dfae5c6114f2f0931c1e81a"
    )
    ledger = _load(ledger_path)
    assert [entry["phase"] for entry in ledger["entries"]] == [
        "infrastructure_failure",
        "development_walkforward_2019_2023",
    ]
    assert (
        ledger["entries"][1]["previous_entry_sha256"]
        == ledger["entries"][0]["entry_sha256"]
    )
    assert ledger["chain_tip_sha256"] == ledger["entries"][1]["entry_sha256"]
    assert _load(survivor_path)["selected_survivor_count"] == 0
    assert _load(stress_path)["status"] == "not_opened_zero_development_survivors"


def test_development_metrics_and_rejection_reasons_are_preserved() -> None:
    terminal = _load(TERMINAL)
    decision = terminal["development"]["survivor_decision"]
    assert decision["positive_mean_rank_ic_fold_count"] == 0
    assert decision["positive_normalized_return_fold_count"] == 0
    assert decision["positive_pilot_return_fold_count"] == 0
    assert set(decision["operational_rejection_reasons"]) == {
        "fold_1_board_lot_affordability",
        "fold_3_board_lot_affordability",
    }
    assert (
        "nonpositive_development_aggregate_20bp_return"
        in decision["validation_quality_rejection_reasons"]
    )
    aggregate = terminal["development"]["aggregate"]
    assert aggregate["mean_rank_ic"] == -0.006820610251179351
    assert aggregate["pilot_10bp_net_return"] == -0.058529119945582186
    assert aggregate["pilot_20bp_net_return"] == -0.11034078460848806


def test_attempt_accounting_and_report_semantics_are_explicit() -> None:
    assert _sha256(ATTEMPTS) == (
        "41e2b1ee2abe24047f56807fff1458e4b9b634ce9e2a4a3295bf8fd479321a59"
    )
    attempts = _load(ATTEMPTS)
    assert attempts["campaign099_attempt_count"] == 14
    assert attempts["campaign099_ledger_entry_count"] == 19
    assert (
        attempts["campaign099_infrastructure_implementation_or_recording_failure_count"]
        == 11
    )
    assert attempts["campaign099_return_reading_development_trial_count"] == 1
    assert attempts["cumulative_historical_research_attempt_count"] == 706
    assert attempts["cumulative_return_reading_development_trial_count"] == 294
    report = _load(WALKFORWARD / "campaign_report.json")
    assert report["infrastructure_failure_count"] == 0
    discrepancy = _load(
        ROOT
        / "docs/a_share_three_day_walkforward_campaign_099_generated_report_failure_count_semantics_20260807.json"
    )
    assert (
        discrepancy["authoritative_trial_ledger"]["infrastructure_failure_entry_count"]
        == 1
    )


def test_v48_orders_append_campaign099_once() -> None:
    policy = _load(POLICY)
    extra = [
        {
            "name": "intraday_market_range_profile_synchronization_240m",
            "score_direction": "higher",
        },
        {
            "name": "intraday_range_clock_variance_240m",
            "score_direction": "higher",
        },
        {
            "name": "intraday_market_close_location_profile_synchronization_240m",
            "score_direction": "higher",
        },
    ]
    complete = definitions.reconstruct_complete_definitions() + extra
    numeric = definitions.reconstruct_comparisons() + extra
    complete_policy = policy["complete_historical_feature_library"]
    numeric_policy = policy["numerical_comparator_eligibility"]
    assert len(complete) == complete_policy["factor_definition_count"] == 131
    assert definitions._order_digest(complete) == complete_policy["order_sha256"]
    assert len(numeric) == numeric_policy["eligible_numeric_comparator_count"] == 128
    assert (
        definitions._order_digest(numeric)
        == numeric_policy["eligible_numeric_comparator_order_sha256"]
    )
    assert numeric_policy["last_comparator"][
        "numeric_comparator_eligible_for_campaign100"
    ]


def test_candidate49_ledgers_remain_empty_and_unchanged() -> None:
    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha256(signal) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(execution) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(signal)["entries"] == []
    assert _load(execution)["entries"] == []
