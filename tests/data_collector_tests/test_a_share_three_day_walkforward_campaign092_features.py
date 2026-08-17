from __future__ import annotations

import numpy as np

from scripts import a_share_three_day_walkforward_campaign092_features as c92


def _ranged_base() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    open_ = np.full((1, 240), 10.0)
    high = np.full((1, 240), 10.2)
    low = np.full((1, 240), 9.8)
    close = np.full((1, 240), 10.0)
    return open_, high, low, close


def test_gap_discovery_share_zero_and_one_endpoints() -> None:
    open_, high, low, close = _ranged_base()
    values, eligible, *_ = c92.compute_interbar_gap_discovery_share(
        open_, high, low, close
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]

    levels = np.tile(np.array([10.0, 11.0]), 120).reshape(1, 240)
    values, eligible, *_ = c92.compute_interbar_gap_discovery_share(
        levels, levels, levels, levels
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [1.0]


def test_lunch_boundary_is_excluded_and_flat_day_is_missing() -> None:
    open_ = np.full((1, 240), 10.0)
    open_[:, 120:] = 100.0
    close = open_.copy()
    high = open_ * 1.01
    low = open_ / 1.01
    values, eligible, gap_mass, *_ = c92.compute_interbar_gap_discovery_share(
        open_, high, low, close
    )
    assert eligible.tolist() == [True]
    assert gap_mass.tolist() == [0.0]
    assert values.tolist() == [0.0]

    flat = np.full((1, 240), 10.0)
    values, eligible, *_ = c92.compute_interbar_gap_discovery_share(
        flat, flat, flat, flat
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])


def test_invalid_ohlc_fails_closed_and_price_scale_is_invariant() -> None:
    open_, high, low, close = _ranged_base()
    open_[:, 1::2] = 10.1
    close[:, 1::2] = 10.1
    base, base_eligible, *_ = c92.compute_interbar_gap_discovery_share(
        open_, high, low, close
    )
    scaled, scaled_eligible, *_ = c92.compute_interbar_gap_discovery_share(
        open_ * 17.0, high * 17.0, low * 17.0, close * 17.0
    )
    assert base_eligible.tolist() == scaled_eligible.tolist() == [True]
    assert np.allclose(base, scaled, atol=1e-14, rtol=0.0)

    high[:, 0] = 9.0
    values, eligible, *_ = c92.compute_interbar_gap_discovery_share(
        open_, high, low, close
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])


def test_frozen_protocol_and_orders_validate() -> None:
    spec = c92.load_protocol()
    assert spec["candidate"]["name"] == c92.FACTOR_NAME
    assert len(c92.reconstruct_complete_definitions()) == 123
    assert len(c92.reconstruct_comparisons()) == 121
    assert c92.reconstruct_complete_definitions()[-1] == {
        "name": "intraday_directional_range_mass_imbalance_240m",
        "score_direction": "higher",
    }
    assert c92.reconstruct_comparisons()[-1] == {
        "name": "intraday_directional_range_mass_imbalance_240m",
        "score_direction": "higher",
    }
    assert (
        c92._comparison_order_digest(c92.reconstruct_complete_definitions())
        == c92.FULL_DEFINITION_ORDER_SHA256
    )
    assert (
        c92._comparison_order_digest(c92.reconstruct_comparisons())
        == c92.COMPARISON_ORDER_SHA256
    )
