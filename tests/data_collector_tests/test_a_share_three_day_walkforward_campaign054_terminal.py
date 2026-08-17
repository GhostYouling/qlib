"""Terminal development and stress-closure tests for Campaign054."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_054/walkforward"
)
LEDGER = ROOT / "trial_ledger.json"
SURVIVORS = ROOT / "development_survivors.json"
STRESS = ROOT / "exposed_stress_consumption_record.json"
REPORT = ROOT / "campaign_report.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign054_terminal_ledger_contains_exactly_one_trial() -> None:
    ledger = _load(LEDGER)
    assert _sha256(LEDGER) == (
        "5ff51038c372cae378e390b886749db68917ec096443e91c27c01e98eb644530"
    )
    assert ledger["append_only"] is True
    assert ledger["chain_tip_sha256"] == (
        "4258747db711b28d63341cd5640914e0807f108760170f712b4e84aa104196d9"
    )
    assert len(ledger["entries"]) == 1
    entry = ledger["entries"][0]
    assert entry["trial_id"] == (
        "wf054_intraday_volume_weighted_transaction_price_bowley_skew_240m_single_higher"
    )
    assert entry["feature_set"] == [
        "intraday_volume_weighted_transaction_price_bowley_skew_240m"
    ]
    assert entry["candidate49_historical_return_read"] is False
    assert entry["current_scoring_selection_sizing_or_orders_performed"] is False
    assert entry["locked_backtest_metrics_when_opened"] is None


def test_campaign054_terminal_trial_fails_frozen_development_gates() -> None:
    survivors = _load(SURVIVORS)
    assert _sha256(SURVIVORS) == (
        "57f3dea0e32b83edddd10c4da03274793fb1d427f5a4f1c94a430bd527fd3038"
    )
    assert survivors["selected_survivor_count"] == 0
    decision = survivors["trial_decisions"][0]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["operationally_admissible"] is True
    assert decision["positive_mean_rank_ic_fold_count"] == 1
    assert decision["positive_normalized_return_fold_count"] == 1
    assert decision["positive_pilot_return_fold_count"] == 0
    assert decision["median_validation_mean_rank_ic"] == -0.0009506467167493653
    assert decision["median_validation_spread"] == -0.0009030427742824966
    assert decision["median_validation_pilot_return"] == -0.008040341510729188
    assert decision["worst_validation_normalized_drawdown"] == -0.3840158512518532
    assert decision["development_aggregate_20bp_return"] == -0.22940811579095166
    assert decision["validation_quality_rejection_reasons"] == [
        "insufficient_positive_ic_folds",
        "median_validation_mean_rank_ic",
        "median_validation_spread",
        "insufficient_positive_normalized_return_folds",
        "insufficient_positive_pilot_return_folds",
        "median_validation_pilot_return",
        "worst_validation_normalized_drawdown",
        "nonpositive_development_aggregate_20bp_return",
    ]


def test_campaign054_stress_interval_remains_closed() -> None:
    stress = _load(STRESS)
    report = _load(REPORT)
    assert _sha256(STRESS) == (
        "7258aac70583498d047a6773533b149673b699a2b4d0be93a2891e410c18054e"
    )
    assert _sha256(REPORT) == (
        "f6afe04827948f6867d276c4c13352b2ef0f0f79b7e52dc55f946cd5f1932791"
    )
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert stress["selected_survivor_count"] == 0
    assert stress["candidate49_historical_return_read"] is False
    assert report["development_trial_count"] == 1
    assert report["development_gate_passer_count"] == 0
    assert report["exposed_stress"]["stress_interval_opened"] is False
    assert report["candidate49"]["historical_return_read"] is False
    assert report["current_scoring_selection_sizing_or_orders_allowed"] is False
