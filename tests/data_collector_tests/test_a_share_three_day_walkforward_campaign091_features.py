from __future__ import annotations

import numpy as np

from scripts import a_share_three_day_walkforward_campaign091_features as c91


def _base() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    open_ = np.full((1, 240), 10.0)
    high = np.full((1, 240), 10.2)
    low = np.full((1, 240), 9.8)
    close = np.full((1, 240), 10.1)
    return open_, high, low, close


def test_directional_range_mass_endpoints_and_zero() -> None:
    open_, high, low, close = _base()
    values, eligible, *_ = c91.compute_directional_range_mass_imbalance(
        open_, high, low, close
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [1.0]

    close[:] = 9.9
    values, eligible, *_ = c91.compute_directional_range_mass_imbalance(
        open_, high, low, close
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [-1.0]

    close[:, :120] = 10.1
    close[:, 120:] = 9.9
    values, eligible, *_ = c91.compute_directional_range_mass_imbalance(
        open_, high, low, close
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]


def test_zero_body_and_invalid_ohlc_fail_closed() -> None:
    open_, high, low, close = _base()
    close[:] = open_
    values, eligible, *_ = c91.compute_directional_range_mass_imbalance(
        open_, high, low, close
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])

    open_, high, low, close = _base()
    high[:, 0] = 9.0
    values, eligible, *_ = c91.compute_directional_range_mass_imbalance(
        open_, high, low, close
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])


def test_price_scale_and_body_magnitude_invariance() -> None:
    open_, high, low, close = _base()
    close[:, 120:] = 9.9
    base, *_ = c91.compute_directional_range_mass_imbalance(open_, high, low, close)
    scaled, *_ = c91.compute_directional_range_mass_imbalance(
        open_ * 17.0, high * 17.0, low * 17.0, close * 17.0
    )
    assert np.allclose(base, scaled, atol=1e-14, rtol=0.0)

    changed = close.copy()
    changed[:, :120] = 10.19
    changed[:, 120:] = 9.81
    body_changed, *_ = c91.compute_directional_range_mass_imbalance(
        open_, high, low, changed
    )
    assert np.allclose(base, body_changed, atol=1e-14, rtol=0.0)


def test_frozen_protocol_and_orders_validate() -> None:
    spec = c91.load_protocol()
    assert spec["candidate"]["name"] == c91.FACTOR_NAME
    assert len(c91.reconstruct_complete_definitions()) == 122
    assert len(c91.reconstruct_comparisons()) == 120
    assert (
        c91._comparison_order_digest(c91.reconstruct_complete_definitions())
        == c91.FULL_DEFINITION_ORDER_SHA256
    )
    assert (
        c91._comparison_order_digest(c91.reconstruct_comparisons())
        == c91.COMPARISON_ORDER_SHA256
    )
