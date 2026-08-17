from __future__ import annotations

import numpy as np

from scripts import a_share_three_day_walkforward_campaign093_features as c93


def _ranged_base() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    high = np.full((1, 240), 10.2)
    low = np.full((1, 240), 9.8)
    close = np.full((1, 240), 10.0)
    return high, low, close


def test_quadratic_efficiency_zero_and_one_endpoints() -> None:
    high, low, close = _ranged_base()
    values, eligible, *_ = c93.compute_close_transition_range_quadratic_efficiency(
        high, low, close
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]

    levels = np.tile(np.array([10.0, 11.0]), 120).reshape(1, 240)
    values, eligible, *_ = c93.compute_close_transition_range_quadratic_efficiency(
        levels, levels, levels
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [1.0]


def test_lunch_boundary_is_excluded_and_flat_day_is_missing() -> None:
    close = np.full((1, 240), 10.0)
    close[:, 120:] = 100.0
    high = close * 1.01
    low = close / 1.01
    values, eligible, q_mass, *_ = (
        c93.compute_close_transition_range_quadratic_efficiency(high, low, close)
    )
    assert eligible.tolist() == [True]
    assert q_mass.tolist() == [0.0]
    assert values.tolist() == [0.0]

    flat = np.full((1, 240), 10.0)
    values, eligible, *_ = c93.compute_close_transition_range_quadratic_efficiency(
        flat, flat, flat
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])


def test_invalid_hlc_fails_closed_and_price_scale_is_invariant() -> None:
    high, low, close = _ranged_base()
    close[:, 1::2] = 10.1
    base, base_eligible, *_ = c93.compute_close_transition_range_quadratic_efficiency(
        high, low, close
    )
    scaled, scaled_eligible, *_ = (
        c93.compute_close_transition_range_quadratic_efficiency(
            high * 17.0, low * 17.0, close * 17.0
        )
    )
    assert base_eligible.tolist() == scaled_eligible.tolist() == [True]
    assert np.allclose(base, scaled, atol=1e-14, rtol=0.0)

    high[:, 0] = 9.0
    values, eligible, *_ = c93.compute_close_transition_range_quadratic_efficiency(
        high, low, close
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])


def test_frozen_protocol_and_orders_validate() -> None:
    spec = c93.load_protocol()
    assert spec["candidate"]["name"] == c93.FACTOR_NAME
    assert len(c93.reconstruct_complete_definitions()) == 124
    assert len(c93.reconstruct_comparisons()) == 122
    assert c93.reconstruct_complete_definitions()[-1] == {
        "name": "intraday_interbar_gap_discovery_share_238p",
        "score_direction": "higher",
    }
    assert c93.reconstruct_comparisons()[-1] == {
        "name": "intraday_interbar_gap_discovery_share_238p",
        "score_direction": "higher",
    }
    assert (
        c93._comparison_order_digest(c93.reconstruct_complete_definitions())
        == c93.FULL_DEFINITION_ORDER_SHA256
    )
    assert (
        c93._comparison_order_digest(c93.reconstruct_comparisons())
        == c93.COMPARISON_ORDER_SHA256
    )
