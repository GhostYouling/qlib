from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign117_formula as c117


def test_campaign117_protocol_and_finite_formula_are_frozen() -> None:
    spec = c117.load_protocol()
    assert spec["candidate"]["name"] == c117.FACTOR_NAME
    assert spec["candidate"]["direction"] == "higher"
    assert c117.TOTAL_TRIPLE_COUNT == 236
    assert c117.WEAK_ORDER_CODES.tolist() == [
        0,
        1,
        2,
        5,
        8,
        9,
        13,
        17,
        18,
        21,
        24,
        25,
        26,
    ]


def test_campaign117_strictly_increasing_halves_have_zero_entropy() -> None:
    half = np.arange(1.0, 121.0)
    amounts = np.r_[half, half][None, :]
    values, eligible, counts, _codes, quality = c117.compute_amount_weak_order_entropy(
        amounts
    )
    assert eligible.tolist() == [True]
    assert values[0] == pytest.approx(0.0, abs=1e-15)
    assert counts.sum() == 236
    assert counts.max() == 236
    assert quality["exact_tie_triple_observations"] == 0


def test_campaign117_exact_ties_are_retained() -> None:
    amounts = np.ones((1, 240), dtype=np.float64)
    values, eligible, counts, _codes, quality = c117.compute_amount_weak_order_entropy(
        amounts
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]
    assert counts.sum() == 236
    assert counts.max() == 236
    assert quality["exact_tie_triple_observations"] == 236


def test_campaign117_is_invariant_to_strictly_increasing_transform() -> None:
    rng = np.random.default_rng(117)
    amounts = rng.lognormal(mean=4.0, sigma=1.0, size=(3, 240))
    base = c117.compute_amount_weak_order_entropy(amounts)
    transformed = c117.compute_amount_weak_order_entropy(np.log1p(amounts))
    assert base[1].tolist() == transformed[1].tolist() == [True, True, True]
    assert np.allclose(base[0], transformed[0], rtol=0.0, atol=0.0)
    assert np.array_equal(base[2], transformed[2])


def test_campaign117_excludes_lunch_transition() -> None:
    morning = np.arange(1.0, 121.0)
    afternoon = np.arange(120.0, 0.0, -1.0)
    amounts = np.r_[morning, afternoon][None, :]
    base = c117.compute_amount_weak_order_entropy(amounts)
    shifted = amounts.copy()
    shifted[:, 120:] += 10000.0
    changed = c117.compute_amount_weak_order_entropy(shifted)
    assert base[1].tolist() == changed[1].tolist() == [True]
    assert base[0].tolist() == changed[0].tolist()
    assert np.array_equal(base[2], changed[2])


def test_campaign117_invalid_source_and_shape_fail_closed() -> None:
    amounts = np.ones((3, 240), dtype=np.float64)
    amounts[0, 10] = np.nan
    amounts[1, 10] = -1.0
    amounts[2] = 0.0
    values, eligible, _counts, _codes, quality = c117.compute_amount_weak_order_entropy(
        amounts
    )
    assert eligible.tolist() == [False, False, False]
    assert np.isnan(values).all()
    assert quality["nonfinite_amount_rows"] == 1
    assert quality["negative_amount_rows"] == 1
    assert quality["nonpositive_total_amount_rows"] == 1

    with pytest.raises(c117.Campaign117FormulaError):
        c117.compute_amount_weak_order_entropy(np.ones((1, 239)))
