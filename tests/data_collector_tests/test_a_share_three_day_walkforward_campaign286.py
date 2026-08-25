from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign286 as campaign
from scripts import a_share_three_day_walkforward_campaign286_design as design


def test_compact_key_decode_round_trip() -> None:
    dates = pd.Series(["2020-01-02", "2021-06-30", "2023-12-29"])
    instruments = pd.Series(["SH600000", "SZ000001", "BJ430001"])
    keys = design.compact_stock_day_keys(dates, instruments)

    decoded_dates, decoded_instruments = campaign.decode_keys(keys)

    assert decoded_dates.strftime("%Y-%m-%d").tolist() == dates.tolist()
    assert decoded_instruments.tolist() == instruments.tolist()


def test_target_percentiles_requires_fifty_names_and_uses_average_ties() -> None:
    dates = pd.Series(
        [pd.Timestamp("2020-01-02")] * 50 + [pd.Timestamp("2020-01-03")] * 49
    )
    values = pd.Series([0.0] * 2 + list(range(2, 50)) + list(range(49)))

    target = campaign.target_percentiles(dates, values)

    assert target[0] == pytest.approx(1.5 / 50.0)
    assert target[1] == pytest.approx(1.5 / 50.0)
    assert target[49] == pytest.approx(1.0)
    assert np.isnan(target[50:]).all()


def test_training_weights_give_each_session_equal_mass() -> None:
    dates = pd.Series(
        [pd.Timestamp("2020-01-02")] * 50 + [pd.Timestamp("2020-01-03")] * 100
    )
    target = np.linspace(0.01, 1.0, 150)
    eligible = np.ones(150, dtype=bool)

    valid, weights, statistics = campaign.training_weights(dates, target, eligible)

    assert valid.all()
    assert weights[:50].sum() == pytest.approx(0.5)
    assert weights[50:].sum() == pytest.approx(0.5)
    assert statistics["training_sessions"] == 2


def test_model_parameters_keep_complete_library_and_native_missing_values() -> None:
    trial = {
        "trial_id": "wf286_lgb_deep_158f",
        "learning_rate": 0.02,
        "num_boost_round": 400,
        "max_depth": 8,
        "num_leaves": 63,
        "min_data_in_leaf": 100,
        "lambda_l1": 1.0,
        "lambda_l2": 10.0,
    }

    parameters, rounds = campaign.model_parameters(trial)

    assert rounds == 400
    assert parameters["feature_pre_filter"] is False
    assert parameters["deterministic"] is True
    assert parameters["seed"] == 286
    assert "use_missing" not in parameters


def _validation(
    *, affordability: float = 1.0, rank_ic: float = 0.02
) -> dict[str, object]:
    return {
        "association": {
            "cohorts": 80,
            "mean_rank_ic": rank_ic,
            "mean_top3_minus_bottom3_gross_return": 0.01,
        },
        "normalized_execution": {
            "net_cumulative_return": 0.05,
            "maximum_drawdown": -0.1,
            "terminal_unresolved_position_count": 0,
        },
        "pilot_execution_primary_10bp": {
            "net_cumulative_return": 0.02,
            "board_lot_affordability_rate": affordability,
            "maximum_filled_trade_daily_amount_participation": 0.001,
            "terminal_unresolved_position_count": 0,
        },
        "pilot_slippage_sensitivity": {"0.0020": {"net_cumulative_return": 0.01}},
    }


def test_survivor_decision_requires_all_frozen_quality_and_execution_gates() -> None:
    passing = {"validation_metrics": [_validation(), _validation(), _validation()]}
    failing = {
        "validation_metrics": [
            _validation(),
            _validation(affordability=0.89),
            _validation(),
        ]
    }

    assert campaign.survivor_decision(passing)["passed"]
    rejected = campaign.survivor_decision(failing)
    assert not rejected["passed"]
    assert "fold_2_board_lot_affordability" in rejected["rejection_reasons"]


def test_append_only_ledger_keeps_all_prevalue_and_model_attempts() -> None:
    trials = [{"attempt_id": f"trial_{index}"} for index in range(3)]

    ledger = campaign.build_ledger(trials)

    assert ledger["entry_count"] == 15
    assert ledger["prevalue_concept_attempt_count"] == 6
    assert ledger["infrastructure_failure_attempt_count"] == 6
    assert ledger["model_trial_attempt_count"] == 3
    assert ledger["entries"][0]["previous_entry_sha256"] == campaign.CHAIN_GENESIS
    for previous, current in zip(ledger["entries"], ledger["entries"][1:]):
        assert current["previous_entry_sha256"] == previous["entry_sha256"]
