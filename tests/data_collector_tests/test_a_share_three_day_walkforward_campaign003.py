from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign003 as CAMPAIGN


REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_CAMPAIGN_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_003_preregistration.json"
)


def catalog_campaign() -> dict:
    names = [
        "factor_a",
        "factor_b",
        "factor_c",
        "factor_d",
        "factor_e",
        "factor_f",
        "factor_g",
        CAMPAIGN.GATE_FACTOR,
    ]
    return {
        "factor_library": [
            {
                "name": name,
                "prior_terminal_conclusion_unchanged": True,
            }
            for name in names
        ],
        "search_space": {
            "risk_gate_factor": CAMPAIGN.GATE_FACTOR,
            "primary_signal_factor_names": sorted(names[:-1]),
            "low_vol_directional_rank_gate_thresholds": [
                {"id": "retain_75pct", "minimum_rank": 0.25},
                {"id": "retain_60pct", "minimum_rank": 0.40},
                {"id": "retain_45pct", "minimum_rank": 0.55},
            ],
            "within_gate_score_modes": [
                {
                    "id": "primary_within_gate_rank",
                    "weights": [1.0, 0.0],
                    "formula": "rank_gate(primary)",
                },
                {
                    "id": "primary_75_low_vol_25_within_gate_rank",
                    "weights": [0.75, 0.25],
                    "formula": "0.75*rank_gate(primary)+0.25*rank_gate(low_vol)",
                },
            ],
            "expected_trial_count": 42,
        },
    }


def test_catalog_is_complete_finite_primary_threshold_mode_product() -> None:
    trials = CAMPAIGN.build_trial_catalog(catalog_campaign())
    assert len(trials) == 42
    assert len({item["trial_id"] for item in trials}) == 42
    assert {item["gate_threshold"] for item in trials} == {0.25, 0.40, 0.55}
    assert {item["score_mode"] for item in trials} == set(CAMPAIGN.SCORE_MODES)
    assert all(item["gate_factor"] == CAMPAIGN.GATE_FACTOR for item in trials)
    assert all(item["primary_factor"] != CAMPAIGN.GATE_FACTOR for item in trials)


def test_catalog_rejects_incomplete_threshold_grid() -> None:
    campaign = catalog_campaign()
    campaign["search_space"]["low_vol_directional_rank_gate_thresholds"].pop()
    with pytest.raises(CAMPAIGN.Campaign003Error):
        CAMPAIGN.build_trial_catalog(campaign)


def test_real_preregistration_freezes_42_trials_and_excludes_candidate49() -> None:
    campaign, spec, _sha = CAMPAIGN.load_campaign(FROZEN_CAMPAIGN_PATH)
    trials = CAMPAIGN.build_trial_catalog(campaign)
    assert spec["status"].startswith("frozen_before_campaign003")
    assert len(trials) == 42
    assert all(
        "intraday_cumulative_vwap_crossing_rate_240m"
        not in item["feature_set"]
        for item in trials
    )


def _trial(mode: str, threshold: float = 0.40) -> dict:
    return {
        "primary_factor": "primary",
        "gate_factor": CAMPAIGN.GATE_FACTOR,
        "gate_threshold": threshold,
        "score_mode": mode,
    }


def test_trial_score_gates_then_reranks_both_components_within_date() -> None:
    panel = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(
                [
                    "2024-01-02",
                    "2024-01-02",
                    "2024-01-02",
                    "2024-01-02",
                    "2024-01-05",
                    "2024-01-05",
                ]
            ),
            CAMPAIGN.base.factor_score_column("primary"): [
                0.9,
                0.1,
                0.6,
                0.2,
                0.2,
                0.8,
            ],
            CAMPAIGN.base.factor_score_column(CAMPAIGN.GATE_FACTOR): [
                0.2,
                0.4,
                0.7,
                1.0,
                0.6,
                0.9,
            ],
        }
    )
    primary_only = CAMPAIGN.trial_score(
        panel, _trial("primary_within_gate_rank")
    )
    np.testing.assert_allclose(
        primary_only.to_numpy(),
        np.asarray([np.nan, 1 / 3, 1.0, 2 / 3, 0.5, 1.0]),
        equal_nan=True,
    )
    blended = CAMPAIGN.trial_score(
        panel, _trial("primary_75_low_vol_25_within_gate_rank")
    )
    expected = np.asarray(
        [
            np.nan,
            0.75 * (1 / 3) + 0.25 * (1 / 3),
            0.75 * 1.0 + 0.25 * (2 / 3),
            0.75 * (2 / 3) + 0.25 * 1.0,
            0.75 * 0.5 + 0.25 * 0.5,
            1.0,
        ]
    )
    np.testing.assert_allclose(blended.to_numpy(), expected, equal_nan=True)


def test_trial_score_requires_both_components_and_positive_ranks() -> None:
    panel = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2024-01-02"] * 4),
            CAMPAIGN.base.factor_score_column("primary"): [0.5, np.nan, 0.0, 0.8],
            CAMPAIGN.base.factor_score_column(CAMPAIGN.GATE_FACTOR): [
                0.5,
                0.8,
                0.9,
                np.nan,
            ],
        }
    )
    score = CAMPAIGN.trial_score(
        panel, _trial("primary_within_gate_rank", threshold=0.25)
    )
    np.testing.assert_allclose(
        score.to_numpy(), np.asarray([1.0, np.nan, np.nan, np.nan]), equal_nan=True
    )


def test_append_only_ledger_rejects_coherently_rehashed_edit(
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
    with pytest.raises(CAMPAIGN.Campaign003Error):
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


def test_survivor_quality_remains_a_hard_gate() -> None:
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
    assert (
        CAMPAIGN.survivor_decision(entry, survivor_campaign())[
            "development_survivor_gate_passed"
        ]
        is True
    )
    failed = deepcopy(entry)
    failed["validation_metrics"][0]["normalized_execution"][
        "maximum_drawdown"
    ] = -0.30
    decision = CAMPAIGN.survivor_decision(failed, survivor_campaign())
    assert decision["development_survivor_gate_passed"] is False
    assert "worst_validation_normalized_drawdown" in decision[
        "validation_quality_rejection_reasons"
    ]
