from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign002 as CAMPAIGN


REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_CAMPAIGN_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_002_preregistration.json"
)


def catalog_campaign() -> dict:
    return {
        "factor_library": [
            {
                "name": f"factor_{index}",
                "prior_terminal_conclusion_unchanged": True,
            }
            for index in range(8)
        ],
        "search_space": {
            "nonlinear_consensus_operators": [
                {
                    "id": "geometric_mean",
                    "formula": "sqrt(rank_a * rank_b)",
                },
                {
                    "id": "harmonic_mean",
                    "formula": "2 / (1/rank_a + 1/rank_b)",
                },
                {"id": "minimum", "formula": "min(rank_a, rank_b)"},
            ],
            "expected_trial_count": 84,
        },
    }


def test_catalog_is_complete_finite_pair_operator_product() -> None:
    trials = CAMPAIGN.build_trial_catalog(catalog_campaign())
    assert len(trials) == 84
    assert len({item["trial_id"] for item in trials}) == 84
    assert {
        item["operator"] for item in trials
    } == {"geometric_mean", "harmonic_mean", "minimum"}
    assert all(len(item["feature_set"]) == 2 for item in trials)
    assert all(item["parent_trial_id"].endswith("__w50_50") for item in trials)


def test_catalog_rejects_candidate49() -> None:
    campaign = catalog_campaign()
    campaign["factor_library"][0]["name"] = (
        "intraday_cumulative_vwap_crossing_rate_240m"
    )
    with pytest.raises(CAMPAIGN.Campaign002Error):
        CAMPAIGN.build_trial_catalog(campaign)


@pytest.mark.parametrize(
    ("operator", "expected"),
    [
        ("geometric_mean", [np.sqrt(0.08), np.sqrt(0.24), np.nan]),
        ("harmonic_mean", [2.0 / 7.5, 0.48, np.nan]),
        ("minimum", [0.2, 0.4, np.nan]),
    ],
)
def test_nonlinear_consensus_scores_require_both_components(
    operator: str, expected: list[float]
) -> None:
    panel = pd.DataFrame(
        {
            CAMPAIGN.base.factor_score_column("left"): [0.2, 0.6, 0.9],
            CAMPAIGN.base.factor_score_column("right"): [0.4, 0.4, np.nan],
        }
    )
    score = CAMPAIGN.trial_score(
        panel,
        {
            "feature_set": ["left", "right"],
            "operator": operator,
        },
    )
    np.testing.assert_allclose(
        score.to_numpy(),
        np.asarray(expected),
        rtol=1e-12,
        atol=1e-12,
        equal_nan=True,
    )


def test_append_only_ledger_rejects_coherently_unlinked_edit(
    tmp_path: Path,
) -> None:
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text("{}\n", encoding="utf-8")
    campaign_sha = CAMPAIGN.base.file_sha256(campaign_path)
    ledger_path = tmp_path / "ledger.json"
    ledger = CAMPAIGN.load_or_initialize_ledger(
        ledger_path, campaign_path, campaign_sha
    )
    ledger = CAMPAIGN.append_ledger_entry(
        ledger_path,
        ledger,
        {
            "trial_id": "trial_1",
            "parent_trial_id": None,
            "phase": CAMPAIGN.DEVELOPMENT_PHASE,
        },
        campaign_path,
        campaign_sha,
    )
    edited = deepcopy(ledger)
    edited["entries"][0]["phase"] = "changed"
    edited["entries"][0]["entry_sha256"] = CAMPAIGN.base.value_sha256(
        CAMPAIGN.base.entry_payload_for_hash(edited["entries"][0])
    )
    with pytest.raises(CAMPAIGN.Campaign002Error):
        CAMPAIGN.validate_ledger(edited, campaign_path, campaign_sha)


def _validation_metrics(
    *,
    mean_ic: float = 0.02,
    spread: float = 0.01,
    normalized_return: float = 0.05,
    pilot_return: float = 0.04,
    drawdown: float = -0.10,
) -> dict:
    return {
        "association": {
            "cohorts": 70,
            "mean_rank_ic": mean_ic,
            "mean_top3_minus_bottom3_gross_return": spread,
        },
        "normalized_execution": {
            "net_cumulative_return": normalized_return,
            "maximum_drawdown": drawdown,
            "terminal_unresolved_position_count": 0,
        },
        "pilot_execution_primary_10bp": {
            "net_cumulative_return": pilot_return,
            "board_lot_affordability_rate": 0.95,
            "maximum_filled_trade_daily_amount_participation": 0.005,
            "filled_trade_amount_missing_count": 0,
            "terminal_unresolved_position_count": 0,
        },
    }


def survivor_campaign() -> dict:
    return {
        "walkforward_folds": [{}, {}, {}],
        "survivor_rule": {
            "minimum_validation_association_cohorts_per_fold": 60,
            "minimum_board_lot_affordability_rate_each_fold": 0.9,
            "maximum_daily_amount_participation_each_fold": 0.01,
            "positive_ic_fold_count_gte": 2,
            "median_validation_mean_rank_ic_gt": 0.0,
            "median_validation_spread_gt": 0.0,
            "positive_normalized_return_fold_count_gte": 2,
            "positive_pilot_return_fold_count_gte": 2,
            "median_validation_pilot_return_gt": 0.0,
            "worst_normalized_drawdown_gte": -0.25,
            "development_aggregate_20bp_return_gt": 0.0,
        },
    }


def test_survivor_quality_is_a_hard_gate() -> None:
    entry = {
        "validation_metrics": [
            _validation_metrics(),
            _validation_metrics(),
            _validation_metrics(mean_ic=-0.01),
        ],
        "development_aggregate_metrics": {
            "pilot_slippage_sensitivity": {
                "0.0020": {"net_cumulative_return": 0.03}
            }
        },
    }
    passed = CAMPAIGN.survivor_decision(entry, survivor_campaign())
    assert passed["development_survivor_gate_passed"] is True

    failed_entry = deepcopy(entry)
    for result in failed_entry["validation_metrics"]:
        result["pilot_execution_primary_10bp"]["net_cumulative_return"] = -0.01
    failed = CAMPAIGN.survivor_decision(failed_entry, survivor_campaign())
    assert failed["operationally_admissible"] is True
    assert failed["validation_quality_gate_passed"] is False
    assert failed["development_survivor_gate_passed"] is False
    assert "insufficient_positive_pilot_return_folds" in failed[
        "validation_quality_rejection_reasons"
    ]


def test_real_preregistration_freezes_84_trials_and_excludes_candidate49() -> None:
    campaign, spec, _sha = CAMPAIGN.load_campaign(FROZEN_CAMPAIGN_PATH)
    trials = CAMPAIGN.build_trial_catalog(campaign)
    assert spec["status"].startswith("frozen_before_campaign002")
    assert len(trials) == 84
    assert all(
        "intraday_cumulative_vwap_crossing_rate_240m"
        not in item["feature_set"]
        for item in trials
    )
