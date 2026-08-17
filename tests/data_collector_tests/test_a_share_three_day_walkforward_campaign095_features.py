from __future__ import annotations

import numpy as np

from scripts import a_share_three_day_walkforward_campaign095_features as c95


def _hlc_from_states(states: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    low = np.ones_like(states, dtype=np.float64)
    high = np.full_like(states, np.e, dtype=np.float64)
    close = np.exp(states)
    return high, low, close


def test_equal_fixed_bin_counts_have_unit_entropy() -> None:
    states = np.tile((np.arange(10, dtype=np.float64) + 0.5) / 10.0, 24)[None, :]
    high, low, close = _hlc_from_states(states)
    values, eligible, observed, informative, bins, counts = (
        c95.compute_own_bar_close_location_entropy(high, low, close)
    )
    assert eligible.tolist() == [True]
    assert np.allclose(values, [1.0], atol=1e-15, rtol=0.0)
    assert np.allclose(observed, states, atol=1e-15, rtol=0.0)
    assert informative.all()
    assert counts.tolist() == [[24] * 10]
    assert sorted(np.unique(bins).tolist()) == list(range(10))


def test_concentrated_state_has_zero_entropy_and_endpoints_use_edge_bins() -> None:
    states = np.full((1, 240), 0.25, dtype=np.float64)
    states[0, 0] = 0.0
    states[0, 1] = 1.0
    high, low, close = _hlc_from_states(states)
    values, eligible, _observed, _informative, bins, counts = (
        c95.compute_own_bar_close_location_entropy(high, low, close)
    )
    expected_counts = [1, 0, 238, 0, 0, 0, 0, 0, 0, 1]
    probabilities = np.array([1.0, 238.0, 1.0]) / 240.0
    expected = -np.sum(probabilities * np.log(probabilities)) / np.log(10.0)
    assert eligible.tolist() == [True]
    assert np.allclose(values, [expected], atol=1e-15, rtol=0.0)
    assert bins[0, 0] == 0
    assert bins[0, 1] == 9
    assert counts.tolist() == [expected_counts]


def test_reflection_and_permutation_are_invariant() -> None:
    states = np.tile((np.arange(240, dtype=np.float64) % 37) / 36.0, 1)[None, :]
    high, low, close = _hlc_from_states(states)
    base, base_eligible, *_ = c95.compute_own_bar_close_location_entropy(
        high, low, close
    )
    reflected_h, reflected_l, reflected_c = _hlc_from_states(1.0 - states)
    reflected, reflected_eligible, *_ = c95.compute_own_bar_close_location_entropy(
        reflected_h, reflected_l, reflected_c
    )
    permutation = np.arange(239, -1, -1)
    permuted, permuted_eligible, *_ = c95.compute_own_bar_close_location_entropy(
        high[:, permutation], low[:, permutation], close[:, permutation]
    )
    assert base_eligible.tolist() == reflected_eligible.tolist() == [True]
    assert permuted_eligible.tolist() == [True]
    assert np.allclose(base, reflected, atol=1e-15, rtol=0.0)
    assert np.allclose(base, permuted, atol=1e-15, rtol=0.0)


def test_zero_range_bars_are_noninformative_and_support_is_frozen() -> None:
    states = np.full((1, 240), 0.5, dtype=np.float64)
    high, low, close = _hlc_from_states(states)
    high[0, :121] = 1.0
    close[0, :121] = 1.0
    values, eligible, _states, informative, *_ = (
        c95.compute_own_bar_close_location_entropy(high, low, close)
    )
    assert informative.sum() == 119
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])

    high[0, 120] = np.e
    close[0, 120] = np.exp(0.5)
    values, eligible, _states, informative, *_ = (
        c95.compute_own_bar_close_location_entropy(high, low, close)
    )
    assert informative.sum() == 120
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]


def test_invalid_hlc_fails_closed() -> None:
    states = np.full((1, 240), 0.5, dtype=np.float64)
    high, low, close = _hlc_from_states(states)
    close[0, 4] = high[0, 4] * 1.01
    values, eligible, *_ = c95.compute_own_bar_close_location_entropy(
        high, low, close
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])


def test_frozen_protocol_and_orders_validate() -> None:
    spec = c95.load_protocol()
    assert spec["candidate"]["name"] == c95.FACTOR_NAME
    assert len(c95.reconstruct_complete_definitions()) == 126
    assert len(c95.reconstruct_comparisons()) == 124
    expected_tail = {
        "name": "intraday_range_local_peak_clock_dispersion_236p",
        "score_direction": "higher",
    }
    assert c95.reconstruct_complete_definitions()[-1] == expected_tail
    assert c95.reconstruct_comparisons()[-1] == expected_tail
    assert (
        c95._comparison_order_digest(c95.reconstruct_complete_definitions())
        == c95.FULL_DEFINITION_ORDER_SHA256
    )
    assert (
        c95._comparison_order_digest(c95.reconstruct_comparisons())
        == c95.COMPARISON_ORDER_SHA256
    )
