from __future__ import annotations

import numpy as np

from scripts import a_share_three_day_walkforward_campaign094_features as c94


def _ranges_to_hl(ranges: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    low = np.ones_like(ranges, dtype=np.float64)
    high = np.exp(ranges)
    return high, low


def _two_peak_halves() -> np.ndarray:
    ranges = np.zeros((1, 240), dtype=np.float64)
    for offset in (0, 120):
        ranges[0, offset + 10] = 0.1
        ranges[0, offset + 110] = 0.2
    return ranges


def test_peak_clock_dispersion_matches_frozen_population_variance() -> None:
    high, low = _ranges_to_hl(_two_peak_halves())
    values, eligible, _, morning, afternoon, counts, variances = (
        c94.compute_range_local_peak_clock_dispersion(high, low)
    )
    expected = (50.0 / 119.0) ** 2
    assert eligible.tolist() == [True]
    assert np.allclose(values, [expected], atol=1e-15, rtol=0.0)
    assert counts.tolist() == [[2, 2]]
    assert morning.sum() == afternoon.sum() == 2
    assert np.allclose(variances, [[expected, expected]], atol=1e-15, rtol=0.0)


def test_ties_are_nonpeaks_and_two_peaks_are_required_in_each_half() -> None:
    ranges = _two_peak_halves()
    ranges[0, 10] = 0.0
    high, low = _ranges_to_hl(ranges)
    values, eligible, *_ = c94.compute_range_local_peak_clock_dispersion(high, low)
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])

    tied = np.full((1, 240), 0.1)
    high, low = _ranges_to_hl(tied)
    values, eligible, *_ = c94.compute_range_local_peak_clock_dispersion(high, low)
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])


def test_price_scale_and_positive_range_scale_are_invariant() -> None:
    ranges = _two_peak_halves()
    high, low = _ranges_to_hl(ranges)
    base, base_eligible, *_ = c94.compute_range_local_peak_clock_dispersion(high, low)
    price_scaled, price_scaled_eligible, *_ = (
        c94.compute_range_local_peak_clock_dispersion(high * 17.0, low * 17.0)
    )
    range_high, range_low = _ranges_to_hl(ranges * 3.0)
    range_scaled, range_scaled_eligible, *_ = (
        c94.compute_range_local_peak_clock_dispersion(range_high, range_low)
    )
    assert base_eligible.tolist() == [True]
    assert price_scaled_eligible.tolist() == [True]
    assert range_scaled_eligible.tolist() == [True]
    assert np.allclose(base, price_scaled, atol=1e-15, rtol=0.0)
    assert np.allclose(base, range_scaled, atol=1e-15, rtol=0.0)

    high[0, 0] = 0.0
    values, eligible, *_ = c94.compute_range_local_peak_clock_dispersion(high, low)
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])


def test_frozen_protocol_and_orders_validate() -> None:
    spec = c94.load_protocol()
    assert spec["candidate"]["name"] == c94.FACTOR_NAME
    assert len(c94.reconstruct_complete_definitions()) == 125
    assert len(c94.reconstruct_comparisons()) == 123
    assert c94.reconstruct_complete_definitions()[-1] == {
        "name": "intraday_close_transition_range_quadratic_efficiency_238p",
        "score_direction": "higher",
    }
    assert c94.reconstruct_comparisons()[-1] == {
        "name": "intraday_close_transition_range_quadratic_efficiency_238p",
        "score_direction": "higher",
    }
    assert (
        c94._comparison_order_digest(c94.reconstruct_complete_definitions())
        == c94.FULL_DEFINITION_ORDER_SHA256
    )
    assert (
        c94._comparison_order_digest(c94.reconstruct_comparisons())
        == c94.COMPARISON_ORDER_SHA256
    )
