from __future__ import annotations

import numpy as np

from scripts import a_share_three_day_walkforward_campaign096_features as c96


def _hlc_from_states(states: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    low = np.ones_like(states, dtype=np.float64)
    high = np.full_like(states, np.e, dtype=np.float64)
    close = np.exp(states)
    return high, low, close


def test_constant_and_alternating_states_anchor_zero_and_one() -> None:
    constant = np.full((1, 240), 0.25, dtype=np.float64)
    high, low, close = _hlc_from_states(constant)
    values, eligible, _states, pairs, transitions = (
        c96.compute_intrabar_close_location_total_variation(high, low, close)
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]
    assert pairs.sum() == 238
    assert np.nanmax(transitions) == 0.0

    alternating = np.tile([0.0, 1.0], 120)[None, :]
    high, low, close = _hlc_from_states(alternating)
    values, eligible, *_ = c96.compute_intrabar_close_location_total_variation(
        high, low, close
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [1.0]


def test_linear_half_paths_have_exact_mean_edge_length_and_reverse_invariance() -> None:
    half = np.linspace(0.0, 1.0, 120, dtype=np.float64)
    states = np.concatenate((half, half))[None, :]
    high, low, close = _hlc_from_states(states)
    base, base_eligible, *_ = c96.compute_intrabar_close_location_total_variation(
        high, low, close
    )
    reversed_states = np.concatenate((half[::-1], half[::-1]))[None, :]
    rh, rl, rc = _hlc_from_states(reversed_states)
    reversed_value, reversed_eligible, *_ = (
        c96.compute_intrabar_close_location_total_variation(rh, rl, rc)
    )
    assert base_eligible.tolist() == reversed_eligible.tolist() == [True]
    assert np.allclose(base, [1.0 / 119.0], atol=1e-15, rtol=0.0)
    assert np.allclose(base, reversed_value, atol=1e-15, rtol=0.0)


def test_reflection_and_positive_price_scaling_are_invariant() -> None:
    rng = np.random.default_rng(9601)
    states = rng.uniform(0.01, 0.99, size=(1, 240))
    high, low, close = _hlc_from_states(states)
    base, base_eligible, *_ = c96.compute_intrabar_close_location_total_variation(
        high, low, close
    )
    rh, rl, rc = _hlc_from_states(1.0 - states)
    reflected, reflected_eligible, *_ = (
        c96.compute_intrabar_close_location_total_variation(rh, rl, rc)
    )
    scaled, scaled_eligible, *_ = (
        c96.compute_intrabar_close_location_total_variation(
            high * 37.0, low * 37.0, close * 37.0
        )
    )
    assert base_eligible.tolist() == reflected_eligible.tolist() == [True]
    assert scaled_eligible.tolist() == [True]
    assert np.allclose(base, reflected, atol=2e-15, rtol=0.0)
    assert np.allclose(base, scaled, atol=2e-15, rtol=0.0)


def test_lunch_transition_is_excluded() -> None:
    states = np.concatenate((np.zeros(120), np.ones(120)))[None, :]
    high, low, close = _hlc_from_states(states)
    values, eligible, _states, pairs, transitions = (
        c96.compute_intrabar_close_location_total_variation(high, low, close)
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]
    assert pairs.sum() == 238
    assert np.nanmax(transitions) == 0.0


def test_zero_range_bars_remove_only_incident_pairs_and_support_is_frozen() -> None:
    states = np.full((1, 240), 0.5, dtype=np.float64)
    high, low, close = _hlc_from_states(states)
    high[0, :119] = 1.0
    close[0, :119] = 1.0
    values, eligible, _states, pairs, *_ = (
        c96.compute_intrabar_close_location_total_variation(high, low, close)
    )
    assert pairs.sum() == 119
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])

    high[0, 118] = np.e
    close[0, 118] = np.exp(0.5)
    values, eligible, _states, pairs, *_ = (
        c96.compute_intrabar_close_location_total_variation(high, low, close)
    )
    assert pairs.sum() == 120
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]


def test_invalid_hlc_fails_closed() -> None:
    states = np.full((1, 240), 0.5, dtype=np.float64)
    high, low, close = _hlc_from_states(states)
    close[0, 4] = high[0, 4] * 1.01
    values, eligible, *_ = c96.compute_intrabar_close_location_total_variation(
        high, low, close
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])


def test_frozen_protocol_and_orders_validate() -> None:
    spec = c96.load_protocol()
    assert spec["candidate"]["name"] == c96.FACTOR_NAME
    assert len(c96.reconstruct_complete_definitions()) == 127
    assert len(c96.reconstruct_comparisons()) == 124
    assert c96.reconstruct_complete_definitions()[-2:] == [
        {
            "name": "intraday_range_local_peak_clock_dispersion_236p",
            "score_direction": "higher",
        },
        c96.C95_SEMANTIC_DEFINITION,
    ]
    assert c96.reconstruct_comparisons()[-1] == {
        "name": "intraday_range_local_peak_clock_dispersion_236p",
        "score_direction": "higher",
    }
    assert (
        c96._comparison_order_digest(c96.reconstruct_complete_definitions())
        == c96.FULL_DEFINITION_ORDER_SHA256
    )
    assert (
        c96._comparison_order_digest(c96.reconstruct_comparisons())
        == c96.COMPARISON_ORDER_SHA256
    )
