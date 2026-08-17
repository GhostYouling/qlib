from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign087 as campaign

ROOT = Path(__file__).resolve().parents[2]
WALKFORWARD = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_087/walkforward"
)
RESEARCH_RECORD = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_087_research_record_v3.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v26_20260807.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_terminal_status_has_one_trial_zero_survivors_and_closed_stress() -> None:
    result = campaign.status(
        argparse.Namespace(
            campaign=str(campaign.DEFAULT_PREREGISTRATION),
            output_root=str(WALKFORWARD),
        )
    )
    assert result["ledger_entry_count"] == 1
    assert result["selected_survivor_count"] == 0
    assert result["stress_status"] == "not_opened_zero_development_survivors"
    assert result["stress_record_exists"] is True
    assert result["candidate49_historical_return_read"] is False
    assert result["current_scoring_selection_sizing_or_orders_allowed"] is False


def test_frozen_trial_metrics_and_rejection_reasons_are_preserved() -> None:
    ledger = _load(WALKFORWARD / "trial_ledger.json")
    assert len(ledger["entries"]) == 1
    trial = ledger["entries"][0]
    assert trial["trial_id"] == campaign.FROZEN_TRIAL_ID
    assert trial["phase"] == "development_walkforward_2019_2023"
    validations = [
        fold["validation_metrics"] for fold in trial["training_and_validation_folds"]
    ]
    assert [item["association"]["mean_rank_ic"] for item in validations] == [
        -0.03573984752323499,
        -0.025507650649194955,
        -0.052188374064640386,
    ]
    survivor = _load(WALKFORWARD / "development_survivors.json")
    decision = survivor["trial_decisions"][0]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["development_aggregate_20bp_return"] == 0.025282371211220678
    assert decision["validation_quality_rejection_reasons"] == [
        "insufficient_positive_ic_folds",
        "median_validation_mean_rank_ic",
        "median_validation_spread",
        "worst_validation_normalized_drawdown",
    ]


def test_2024_2025_stress_was_not_opened_or_read() -> None:
    record = _load(WALKFORWARD / "exposed_stress_consumption_record.json")
    assert record["status"] == "not_opened_zero_development_survivors"
    assert record["stress_interval_opened"] is False
    assert record["stress_return_fields_read"] is False
    assert record["selected_survivor_count"] == 0


def test_terminal_record_and_next_comparator_policy_bindings_pass() -> None:
    for path in (RESEARCH_RECORD, POLICY):
        report = bindings.validate_record(path)
        assert report["all_bindings_passed"] is True
    policy = _load(POLICY)
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 119
    )
    numeric = policy["numerical_comparator_eligibility"]
    assert numeric["eligible_numeric_comparator_count"] == 117
    assert numeric["last_comparator"]["development_survivor_count"] == 0
    assert (
        policy["research_boundary"][
            "current_scoring_selection_sizing_or_orders_performed"
        ]
        is False
    )
