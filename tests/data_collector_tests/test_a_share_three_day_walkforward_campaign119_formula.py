from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign119_formula as c119


def _boundaries_from_midpoints(midpoints: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    midpoint = np.asarray(midpoints, dtype=np.float64).reshape(1, 240)
    return midpoint + 1.0, midpoint - 1.0


def test_campaign119_protocol_and_finite_formula_are_frozen() -> None:
    spec = c119.load_protocol()
    assert spec["candidate"]["name"] == c119.FACTOR_NAME
    assert spec["candidate"]["direction"] == "higher"
    assert c119.SELECTED_BAR_COUNT == 240
    assert c119.HALF_BAR_COUNT == 120
    assert c119.PAIR_COUNT_PER_HALF == 119
    assert c119.TOTAL_PAIR_COUNT == 238
    assert c119.STATE_COUNT == 9


def test_campaign119_constant_boundaries_have_zero_entropy() -> None:
    high = np.full((1, 240), 12.0)
    low = np.full((1, 240), 10.0)
    values, eligible, counts, codes, quality = (
        c119.compute_range_boundary_direction_state_entropy(high, low)
    )
    assert eligible.tolist() == [True]
    assert values[0] == pytest.approx(0.0, abs=1e-15)
    assert counts.tolist() == [[0, 0, 0, 0, 238, 0, 0, 0, 0]]
    assert np.all(codes == 4)
    assert quality["recognized_state_observations"] == 238
    assert quality["exact_joint_tie_pair_observations"] == 238


def test_campaign119_two_translation_states_match_binary_entropy() -> None:
    one_half = np.asarray([100.0 + (index % 2) for index in range(120)])
    midpoints = np.concatenate((one_half, one_half))
    high, low = _boundaries_from_midpoints(midpoints)
    values, eligible, counts, _codes, _quality = (
        c119.compute_range_boundary_direction_state_entropy(high, low)
    )
    probabilities = counts[0, counts[0] > 0].astype(np.float64) / 238.0
    expected = -(probabilities * np.log(probabilities)).sum() / np.log(9.0)
    assert eligible.tolist() == [True]
    assert counts[0, 0] == 118
    assert counts[0, 8] == 120
    assert counts.sum() == 238
    assert values[0] == pytest.approx(expected, abs=1e-15)


def test_campaign119_excludes_lunch_transition() -> None:
    high = np.concatenate((np.full(120, 12.0), np.full(120, 102.0)))[None, :]
    low = np.concatenate((np.full(120, 10.0), np.full(120, 100.0)))[None, :]
    values, eligible, counts, codes, _quality = (
        c119.compute_range_boundary_direction_state_entropy(high, low)
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]
    assert counts.tolist() == [[0, 0, 0, 0, 238, 0, 0, 0, 0]]
    assert codes.shape == (1, 238)


def test_campaign119_positive_affine_boundary_transform_is_invariant() -> None:
    rng = np.random.default_rng(119)
    midpoint = 100.0 + np.cumsum(rng.normal(size=(3, 240)), axis=1)
    width = rng.uniform(0.0, 4.0, size=(3, 240))
    high = midpoint + width / 2.0
    low = midpoint - width / 2.0
    base = c119.compute_range_boundary_direction_state_entropy(high, low)
    transformed = c119.compute_range_boundary_direction_state_entropy(
        3.0 * high + 7.0,
        3.0 * low + 7.0,
    )
    assert base[1].tolist() == transformed[1].tolist() == [True, True, True]
    assert np.allclose(base[0], transformed[0], rtol=0.0, atol=0.0)
    assert np.array_equal(base[2], transformed[2])
    assert np.array_equal(base[3], transformed[3])


def test_campaign119_zero_width_bars_and_exact_ties_are_valid() -> None:
    price = np.full((1, 240), 10.0)
    values, eligible, _counts, _codes, quality = (
        c119.compute_range_boundary_direction_state_entropy(price, price)
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]
    assert quality["zero_width_bar_observations"] == 240
    assert quality["exact_low_tie_pair_observations"] == 238
    assert quality["exact_high_tie_pair_observations"] == 238


def test_campaign119_invalid_source_and_shape_fail_closed() -> None:
    high = np.full((3, 240), 12.0)
    low = np.full((3, 240), 10.0)
    high[0, 10] = np.nan
    low[1, 10] = 0.0
    high[2, 10] = 9.0
    values, eligible, _counts, _codes, quality = (
        c119.compute_range_boundary_direction_state_entropy(high, low)
    )
    assert eligible.tolist() == [False, False, False]
    assert np.isnan(values).all()
    assert quality["nonfinite_high_low_rows"] == 1
    assert quality["nonpositive_high_low_rows"] == 1
    assert quality["high_below_low_rows"] == 1

    with pytest.raises(c119.Campaign119FormulaError):
        c119.compute_range_boundary_direction_state_entropy(
            np.ones((1, 239)), np.ones((1, 239))
        )
    with pytest.raises(c119.Campaign119FormulaError):
        c119.compute_range_boundary_direction_state_entropy(
            np.ones((1, 240)), np.ones((2, 240))
        )
