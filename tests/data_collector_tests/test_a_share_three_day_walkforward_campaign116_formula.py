from __future__ import annotations

import numpy as np

from scripts import a_share_three_day_walkforward_campaign116_formula as c116


def _two_half_close_grid() -> np.ndarray:
    one_half_returns = np.concatenate(
        [np.full(60, 0.01), np.full(59, -0.01)]
    )
    one_half = 100.0 * np.exp(
        np.concatenate([[0.0], np.cumsum(one_half_returns)])
    )
    return np.concatenate([one_half, one_half])[None, :]


def _positive_pair_high_amount_grid() -> np.ndarray:
    amounts = np.ones((1, 240), dtype=np.float64)
    for start in (0, 120):
        amounts[0, start + 2 : start + 61] = 3.0
    amounts[0, [0, 120]] = 3.0
    assert np.median(amounts) == 2.0
    return amounts


def test_campaign116_protocol_and_finite_formula_are_frozen() -> None:
    spec = c116.load_protocol()
    assert spec["candidate"]["name"] == c116.FACTOR_NAME
    assert spec["candidate"]["direction"] == "higher"
    assert c116.TOTAL_PAIR_COUNT == 236
    assert c116.MINIMUM_GROUP_SUPPORT == 30


def test_campaign116_exact_activity_conditioned_score() -> None:
    values, eligible, high_support, ordinary_support, states, high_mask = (
        c116.compute_amount_conditioned_directional_persistence_spread(
            _two_half_close_grid(), _positive_pair_high_amount_grid()
        )
    )
    assert eligible.tolist() == [True]
    assert high_support.tolist() == [118]
    assert ordinary_support.tolist() == [118]
    assert high_mask.sum() == 118
    assert np.count_nonzero(states == 1.0) == 118
    assert np.count_nonzero(states == -1.0) == 116
    assert np.count_nonzero(states == 0.0) == 2
    assert np.isclose(values[0], 117.0 / 118.0, rtol=0.0, atol=1e-12)


def test_campaign116_excludes_lunch_transition() -> None:
    closes = _two_half_close_grid()
    amounts = _positive_pair_high_amount_grid()
    base = c116.compute_amount_conditioned_directional_persistence_spread(
        closes, amounts
    )[0]
    rescaled_afternoon = closes.copy()
    rescaled_afternoon[:, 120:] *= 1000.0
    changed = c116.compute_amount_conditioned_directional_persistence_spread(
        rescaled_afternoon, amounts
    )[0]
    assert changed.tolist() == base.tolist()


def test_campaign116_median_equal_amount_is_ordinary() -> None:
    closes = _two_half_close_grid()
    amounts = _positive_pair_high_amount_grid()
    amounts[0, 2] = 2.0
    amounts[0, 1] = 2.0
    assert np.median(amounts) == 2.0
    result = c116.compute_amount_conditioned_directional_persistence_spread(
        closes, amounts
    )
    assert result[1].tolist() == [True]
    assert not result[5][0, 0]


def test_campaign116_zero_returns_are_noninformative_and_fail_support() -> None:
    closes = np.full((1, 240), 100.0)
    amounts = np.tile(np.arange(240, dtype=np.float64), (1, 1))
    values, eligible, high_support, ordinary_support, states, _high_mask = (
        c116.compute_amount_conditioned_directional_persistence_spread(
            closes, amounts
        )
    )
    assert eligible.tolist() == [False]
    assert high_support.tolist() == [0]
    assert ordinary_support.tolist() == [0]
    assert np.isnan(states).all()
    assert np.isnan(values).all()


def test_campaign116_invalid_source_and_shapes_fail_closed() -> None:
    closes = np.tile(_two_half_close_grid(), (3, 1))
    amounts = np.tile(_positive_pair_high_amount_grid(), (3, 1))
    closes[0, 10] = np.nan
    amounts[1, 10] = -1.0
    amounts[2] = 0.0
    values, eligible, *_rest = (
        c116.compute_amount_conditioned_directional_persistence_spread(
            closes, amounts
        )
    )
    assert eligible.tolist() == [False, False, False]
    assert np.isnan(values).all()

    try:
        c116.compute_amount_conditioned_directional_persistence_spread(
            np.ones((1, 239)), np.ones((1, 239))
        )
    except c116.Campaign116FormulaError:
        pass
    else:
        raise AssertionError("Campaign116 accepted a non-240 close grid")
