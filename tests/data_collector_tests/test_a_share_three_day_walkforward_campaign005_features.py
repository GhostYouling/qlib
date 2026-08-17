from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "a_share_three_day_walkforward_campaign005_features.py"
SPEC = importlib.util.spec_from_file_location("campaign005_features_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
campaign = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(campaign)


def _path_from_returns(
    morning_returns: np.ndarray,
    lunch_return: float,
    afternoon_returns: np.ndarray,
) -> np.ndarray:
    assert morning_returns.shape == (119,)
    assert afternoon_returns.shape == (119,)
    logs = np.empty(240, dtype=float)
    logs[0] = np.log(100.0)
    logs[1:120] = logs[0] + np.cumsum(morning_returns)
    logs[120] = logs[119] + lunch_return
    logs[121:240] = logs[120] + np.cumsum(afternoon_returns)
    return np.exp(logs)


def test_formula_catalog_matches_frozen_mechanism_audit() -> None:
    assert campaign.FACTOR_NAMES == (
        "intraday_zero_return_amount_intensity_238m",
        "intraday_lunch_repricing_persistence_119m",
        "intraday_directional_price_impact_asymmetry_238m",
    )
    assert campaign.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "close",
        "amount",
    )
    assert campaign.TRANSITION_COUNT == 238
    assert campaign.ZERO_RETURN_UPPER == pytest.approx(np.log(238.0))
    assert campaign.FACTOR_RANGES[campaign.ZERO_RETURN_FACTOR] == (
        -np.inf,
        campaign.ZERO_RETURN_UPPER,
    )
    assert campaign.FACTOR_RANGES[campaign.LUNCH_FACTOR] == (-1.0, 1.0)
    assert campaign.FACTOR_RANGES[campaign.IMPACT_FACTOR] == (-1.0, 1.0)


def test_compute_factor_values_rejects_wrong_shapes() -> None:
    with pytest.raises(campaign.Campaign005FeatureError):
        campaign.compute_factor_values(
            closes=np.ones((1, 239), dtype=float),
            amounts=np.ones((1, 239), dtype=float),
        )


def test_zero_return_amount_intensity_controls_for_unchanged_count() -> None:
    morning = np.tile(np.array([0.001, -0.001, 0.0, 0.0]), 30)[:119]
    afternoon = np.tile(np.array([-0.001, 0.001, 0.0, 0.0]), 30)[:119]
    closes = _path_from_returns(morning, 0.002, afternoon)
    amounts = np.ones(240, dtype=float)
    zero_destinations = np.concatenate(
        [
            closes[1:120] == closes[:119],
            closes[121:240] == closes[120:239],
        ]
    )
    destination_indices = np.concatenate(
        [np.arange(1, 120), np.arange(121, 240)]
    )
    amounts[destination_indices[zero_destinations]] = 4.0
    values, eligible, _ = campaign.compute_factor_values(
        closes=closes[None, :],
        amounts=amounts[None, :],
    )
    zero_count = int(zero_destinations.sum())
    zero_amount = float(amounts[destination_indices[zero_destinations]].sum())
    total_amount = float(amounts[destination_indices].sum())
    expected = np.log(
        (zero_amount / zero_count) / (total_amount / campaign.TRANSITION_COUNT)
    )
    assert eligible[campaign.ZERO_RETURN_FACTOR].tolist() == [True]
    assert values[campaign.ZERO_RETURN_FACTOR][0] == pytest.approx(expected)
    assert values[campaign.ZERO_RETURN_FACTOR][0] > 0.0


def test_lunch_persistence_is_one_for_monotone_same_direction_afternoon() -> None:
    morning = np.tile(np.array([0.001, -0.001]), 60)[:119]
    afternoon = np.full(119, 0.001, dtype=float)
    closes = _path_from_returns(morning, 0.01, afternoon)
    amounts = np.ones(240, dtype=float)
    values, eligible, _ = campaign.compute_factor_values(
        closes=closes[None, :],
        amounts=amounts[None, :],
    )
    assert eligible[campaign.LUNCH_FACTOR].tolist() == [True]
    assert values[campaign.LUNCH_FACTOR][0] == pytest.approx(1.0)


def test_lunch_persistence_changes_sign_when_afternoon_rejects_jump() -> None:
    morning = np.tile(np.array([0.001, -0.001]), 60)[:119]
    afternoon = np.full(119, -0.001, dtype=float)
    closes = _path_from_returns(morning, 0.01, afternoon)
    amounts = np.ones(240, dtype=float)
    values, eligible, _ = campaign.compute_factor_values(
        closes=closes[None, :],
        amounts=amounts[None, :],
    )
    assert eligible[campaign.LUNCH_FACTOR].tolist() == [True]
    assert values[campaign.LUNCH_FACTOR][0] == pytest.approx(-1.0)


def test_directional_impact_asymmetry_matches_bounded_formula() -> None:
    morning = np.tile(np.array([0.002, -0.001]), 60)[:119]
    afternoon = np.tile(np.array([0.002, -0.001]), 60)[:119]
    closes = _path_from_returns(morning, 0.003, afternoon)
    amounts = np.ones(240, dtype=float)
    destination_indices = np.concatenate(
        [np.arange(1, 120), np.arange(121, 240)]
    )
    returns = np.concatenate([morning, afternoon])
    amounts[destination_indices[returns < 0.0]] = 2.0
    values, eligible, _ = campaign.compute_factor_values(
        closes=closes[None, :],
        amounts=amounts[None, :],
    )
    up_impact = returns[returns > 0.0].sum() / amounts[
        destination_indices[returns > 0.0]
    ].sum()
    down_impact = (-returns[returns < 0.0]).sum() / amounts[
        destination_indices[returns < 0.0]
    ].sum()
    expected = (up_impact - down_impact) / (up_impact + down_impact)
    assert eligible[campaign.IMPACT_FACTOR].tolist() == [True]
    assert values[campaign.IMPACT_FACTOR][0] == pytest.approx(expected)
    assert values[campaign.IMPACT_FACTOR][0] > 0.0


def test_missing_denominators_remain_ineligible() -> None:
    closes = np.full((1, 240), 100.0, dtype=float)
    amounts = np.ones((1, 240), dtype=float)
    values, eligible, quality = campaign.compute_factor_values(
        closes=closes,
        amounts=amounts,
    )
    assert eligible[campaign.ZERO_RETURN_FACTOR].tolist() == [True]
    assert values[campaign.ZERO_RETURN_FACTOR][0] == pytest.approx(0.0)
    assert eligible[campaign.LUNCH_FACTOR].tolist() == [False]
    assert eligible[campaign.IMPACT_FACTOR].tolist() == [False]
    assert quality[f"{campaign.LUNCH_FACTOR}__zero_lunch_repricing_rows"] == 1
    assert quality[f"{campaign.IMPACT_FACTOR}__missing_positive_side_rows"] == 1
    assert quality[f"{campaign.IMPACT_FACTOR}__missing_negative_side_rows"] == 1
