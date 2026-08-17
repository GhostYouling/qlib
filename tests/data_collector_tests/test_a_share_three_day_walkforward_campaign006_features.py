from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    ROOT / "scripts" / "a_share_three_day_walkforward_campaign006_features.py"
)
SPEC = importlib.util.spec_from_file_location(
    "campaign006_features_under_test",
    MODULE_PATH,
)
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


def _paths() -> tuple[np.ndarray, np.ndarray]:
    morning = np.tile(np.array([0.002, -0.001, 0.0005]), 40)[:119]
    afternoon = np.tile(np.array([-0.0015, 0.0007, 0.0012]), 40)[:119]
    closes = _path_from_returns(morning, 0.004, afternoon)
    transaction_prices = _path_from_returns(morning, -0.003, afternoon)
    return closes, transaction_prices


def test_formula_catalog_matches_frozen_mechanism_audit() -> None:
    assert campaign.FACTOR_NAMES == (
        "intraday_transaction_price_path_confirmation_238p",
    )
    assert campaign.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "close",
        "volume",
        "amount",
    )
    assert campaign.MAXIMUM_PAIRS == 238
    assert campaign.MINIMUM_RETAINED_PAIRS == 120
    assert campaign.FACTOR_RANGES[campaign.FACTOR_NAME] == (-1.0, 1.0)


def test_compute_factor_values_rejects_wrong_shapes() -> None:
    with pytest.raises(campaign.Campaign006FeatureError):
        campaign.compute_factor_values(
            closes=np.ones((1, 239), dtype=float),
            volumes=np.ones((1, 239), dtype=float),
            amounts=np.ones((1, 239), dtype=float),
        )


def test_identical_return_paths_have_perfect_confirmation() -> None:
    closes, transaction_prices = _paths()
    volumes = np.full(240, 1000.0)
    amounts = volumes * transaction_prices
    values, eligible, _ = campaign.compute_factor_values(
        closes=closes[None, :],
        volumes=volumes[None, :],
        amounts=amounts[None, :],
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(1.0)


def test_constant_provider_unit_scaling_cancels() -> None:
    closes, transaction_prices = _paths()
    volumes = np.full(240, 1000.0)
    amounts = volumes * transaction_prices
    original = campaign.compute_factor_values(
        closes=closes[None, :],
        volumes=volumes[None, :],
        amounts=amounts[None, :],
    )[0][campaign.FACTOR_NAME][0]
    scaled = campaign.compute_factor_values(
        closes=closes[None, :],
        volumes=(volumes * 100.0)[None, :],
        amounts=amounts[None, :],
    )[0][campaign.FACTOR_NAME][0]
    assert scaled == pytest.approx(original)


def test_opposite_return_paths_have_negative_confirmation() -> None:
    morning = np.tile(np.array([0.002, -0.001, 0.0005]), 40)[:119]
    afternoon = np.tile(np.array([-0.0015, 0.0007, 0.0012]), 40)[:119]
    closes = _path_from_returns(morning, 0.004, afternoon)
    transaction_prices = _path_from_returns(-morning, -0.003, -afternoon)
    volumes = np.full(240, 1000.0)
    amounts = volumes * transaction_prices
    values, eligible, _ = campaign.compute_factor_values(
        closes=closes[None, :],
        volumes=volumes[None, :],
        amounts=amounts[None, :],
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(-1.0)


def test_both_zero_inactive_bars_remove_only_adjacent_pairs() -> None:
    closes, transaction_prices = _paths()
    volumes = np.full(240, 1000.0)
    amounts = volumes * transaction_prices
    inactive = np.array([20, 40, 60, 80, 100, 140, 160, 180, 200, 220])
    volumes[inactive] = 0.0
    amounts[inactive] = 0.0
    values, eligible, quality = campaign.compute_factor_values(
        closes=closes[None, :],
        volumes=volumes[None, :],
        amounts=amounts[None, :],
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(1.0)
    assert quality[
        f"{campaign.FACTOR_NAME}__fewer_than_120_pairs_rows"
    ] == 0


def test_one_sided_zero_activity_invalidates_stock_day() -> None:
    closes, transaction_prices = _paths()
    volumes = np.full(240, 1000.0)
    amounts = volumes * transaction_prices
    volumes[50] = 0.0
    values, eligible, quality = campaign.compute_factor_values(
        closes=closes[None, :],
        volumes=volumes[None, :],
        amounts=amounts[None, :],
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[campaign.FACTOR_NAME][0])
    assert quality[
        f"{campaign.FACTOR_NAME}__one_sided_zero_activity_rows"
    ] == 1


def test_fewer_than_120_retained_pairs_is_missing() -> None:
    closes, transaction_prices = _paths()
    volumes = np.zeros(240)
    amounts = np.zeros(240)
    active = np.concatenate([np.arange(60), np.arange(120, 180)])
    volumes[active] = 1000.0
    amounts[active] = volumes[active] * transaction_prices[active]
    values, eligible, quality = campaign.compute_factor_values(
        closes=closes[None, :],
        volumes=volumes[None, :],
        amounts=amounts[None, :],
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[campaign.FACTOR_NAME][0])
    assert quality[
        f"{campaign.FACTOR_NAME}__fewer_than_120_pairs_rows"
    ] == 1


def test_constant_transaction_price_return_path_is_missing() -> None:
    closes, _ = _paths()
    volumes = np.full(240, 1000.0)
    amounts = volumes * 100.0
    values, eligible, quality = campaign.compute_factor_values(
        closes=closes[None, :],
        volumes=volumes[None, :],
        amounts=amounts[None, :],
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[campaign.FACTOR_NAME][0])
    assert quality[
        f"{campaign.FACTOR_NAME}__constant_transaction_return_rows"
    ] == 1
