from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign146 as campaign
from scripts import a_share_three_day_walkforward_campaign146_features as features


ROOT = Path(__file__).resolve().parents[2]
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_terminal_result_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v197_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign146_terminal_v3.json"
)
WALKFORWARD = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_146/walkforward"
)
ATTEMPT_LEDGERS = tuple(
    ROOT / f"data/experiments/short_horizon/historical_walkforward/campaign_146/{name}"
    for name in (
        "research_attempt_ledger.json",
        "research_attempt_ledger_v2.json",
        "research_attempt_ledger_v3.json",
        "research_attempt_ledger_v4.json",
        "research_attempt_ledger_v5.json",
        "research_attempt_ledger_v6.json",
    )
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _attempt_hash(attempt_id: str, previous: str, phase: str, status: str) -> str:
    payload = f"campaign146|{attempt_id}|{previous}|{phase}|{status}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_terminal_bindings_and_zero_survivor_semantics() -> None:
    assert bindings.validate_record(TERMINAL)["all_bindings_passed"] is True
    terminal = _load(TERMINAL)
    survivors = _load(WALKFORWARD / "development_survivors.json")
    stress = _load(WALKFORWARD / "exposed_stress_consumption_record.json")
    assert terminal["terminal_decision"]["development_survivor_count"] == 0
    assert survivors["selected_survivor_count"] == 0
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert stress["survivor_record_sha256"] == campaign.base.value_sha256(survivors)


def test_exact_one_frozen_trial_and_rejection_metrics_are_preserved() -> None:
    ledger = _load(WALKFORWARD / "trial_ledger.json")
    terminal = _load(TERMINAL)["trial"]
    assert len(ledger["entries"]) == 1
    assert ledger["chain_tip_sha256"] == ledger["entries"][0]["entry_sha256"]
    assert terminal["positive_mean_rank_ic_fold_count"] == 3
    assert terminal["positive_normalized_return_fold_count"] == 2
    assert terminal["positive_pilot_10bp_return_fold_count"] == 2
    assert terminal["median_validation_mean_rank_ic"] == 0.01695367196711484
    assert terminal["median_validation_spread"] == -0.00026719538775617127
    assert terminal["worst_validation_normalized_drawdown"] == -0.37616136808041245
    assert terminal["development_aggregate_20bp_return"] == -0.09481533266368902
    assert terminal["rejection_reasons"] == [
        "fold_1_board_lot_affordability",
        "fold_3_board_lot_affordability",
        "median_validation_spread",
        "worst_validation_normalized_drawdown",
        "nonpositive_development_aggregate_20bp_return",
    ]


def test_append_only_attempt_ledgers_chain_without_rewriting_predecessors() -> None:
    records = [_load(path) for path in ATTEMPT_LEDGERS]
    for predecessor, record in zip(ATTEMPT_LEDGERS, records[1:]):
        assert _sha(predecessor) == record["authoritative_predecessor"]["sha256"]
    previous = records[0]["chain_tip_sha256"]
    for record in records[1:]:
        assert record["authoritative_predecessor"]["chain_tip_sha256"] == previous
        for entry in record["entries"]:
            assert entry["previous_entry_sha256"] == previous
            assert entry["entry_sha256"] == _attempt_hash(
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            )
            previous = entry["entry_sha256"]
        assert record["chain_tip_sha256"] == previous
    final = records[-1]
    assert final["effective_entry_count"] == 22
    assert final["effective_infrastructure_failure_attempt_count"] == 15
    assert final["effective_return_reading_development_trial_count"] == 1
    assert final["cumulative_historical_research_attempt_count"] == 1273
    assert final["cumulative_return_reading_development_trial_count"] == 314


def test_v197_preserves_campaign146_definition_and_numeric_series_once() -> None:
    policy = _load(POLICY)
    assert bindings.validate_record(POLICY)["all_bindings_passed"] is True
    complete = features.reconstruct_complete_definitions()
    numeric = features.reconstruct_comparisons() + [
        {
            "name": "intraday_return_amount_cross_spectral_phase_lead_59f",
            "score_direction": "higher",
        }
    ]
    library = policy["complete_historical_feature_library"]
    eligibility = policy["numerical_comparator_eligibility"]
    assert len(complete) == library["factor_definition_count"] == 155
    assert features._order_digest(complete) == library["order_sha256"]
    assert len(numeric) == eligibility["eligible_numeric_comparator_count"] == 142
    assert (
        features._order_digest(numeric)
        == eligibility["eligible_numeric_comparator_order_sha256"]
    )
    assert eligibility[
        "campaign146_numeric_series_appended_once_after_terminal_classification"
    ]


def test_candidate49_and_current_action_boundaries_remain_closed() -> None:
    terminal = _load(TERMINAL)
    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha(signal) == terminal["candidate49"]["signal_ledger_sha256"]
    assert _sha(execution) == terminal["candidate49"]["execution_ledger_sha256"]
    assert terminal["candidate49"]["signal_entry_count"] == 0
    assert terminal["candidate49"]["execution_entry_count"] == 0
    boundary = terminal["research_boundary"]
    assert boundary["stress_2024_2025_opened"] is False
    assert boundary["candidate49_historical_backfill_performed"] is False
    assert boundary["second_prospective_candidate_created"] is False
    assert (
        boundary["current_scoring_selection_sizing_positions_or_orders_performed"]
        is False
    )


def test_status_and_reports_record_terminal_result_and_active_goal() -> None:
    binding_report = bindings.validate_record(STATUS)
    assert binding_report["all_bindings_passed"] is False
    assert {item["json_pointer"] for item in binding_report["failed_bindings"]} == {
        "/reports/current_research_report",
        "/reports/three_day_research_report",
    }
    status = _load(STATUS)
    assert status["goal"]["status"] == "active"
    assert status["campaign146"]["terminal"] is True
    assert status["campaign146"]["stress_2024_2025_returns_opened"] is False
    assert status["candidate49_daily_20260814"]["same_day_retry_performed"] is False
    for relative in (
        "docs/a_share_three_day_walkforward_campaign_146_terminal_report_v3.md",
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "Campaign146" in text
        assert "2024–2025" in text
        assert "155/142" in text
