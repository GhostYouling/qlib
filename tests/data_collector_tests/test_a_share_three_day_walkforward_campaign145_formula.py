from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign145_formula as c145


def _half(*, return_index: int, amount_index: int) -> tuple[np.ndarray, np.ndarray]:
    returns = np.zeros(119, dtype=np.float64)
    returns[return_index] = 1.0
    closes = np.exp(np.r_[0.0, np.cumsum(returns)])
    amounts = np.zeros(120, dtype=np.float64)
    amounts[amount_index + 1] = 10.0
    return closes, amounts


def _day(*, return_index: int, amount_index: int) -> tuple[np.ndarray, np.ndarray]:
    close_half, amount_half = _half(
        return_index=return_index, amount_index=amount_index
    )
    return (
        np.r_[close_half, close_half][None, :],
        np.r_[amount_half, amount_half][None, :],
    )


def test_campaign145_protocol_and_formula_boundary_are_frozen() -> None:
    spec = c145.load_protocol()
    assert spec["candidate"]["name"] == c145.FACTOR_NAME
    assert spec["candidate"]["direction"] == "higher"
    assert c145.TOTAL_PAIR_COUNT == 238
    assert c145.VALID_RANGE == (-1.0, 1.0)


def test_campaign145_amount_before_positive_return_is_positive() -> None:
    closes, amounts = _day(return_index=100, amount_index=0)
    values, eligible, halves, quality = c145.compute_return_amount_path_signed_area(
        closes, amounts
    )
    assert eligible.tolist() == [True]
    assert np.allclose(halves, [[0.5, 0.5]], rtol=0.0, atol=1e-15)
    assert values.tolist() == pytest.approx([0.5])
    assert quality["eligible_rows"] == 1


def test_campaign145_positive_return_before_amount_is_negative() -> None:
    closes, amounts = _day(return_index=0, amount_index=118)
    values, eligible, halves, _quality = c145.compute_return_amount_path_signed_area(
        closes, amounts
    )
    assert eligible.tolist() == [True]
    assert np.allclose(halves, [[-0.5, -0.5]], rtol=0.0, atol=1e-15)
    assert values.tolist() == pytest.approx([-0.5])


def test_campaign145_is_price_and_amount_scale_invariant() -> None:
    closes, amounts = _day(return_index=80, amount_index=20)
    base = c145.compute_return_amount_path_signed_area(closes, amounts)
    scaled = c145.compute_return_amount_path_signed_area(
        closes * 100.0, amounts * 1_000_000.0
    )
    assert base[1].tolist() == scaled[1].tolist() == [True]
    assert np.allclose(base[0], scaled[0], rtol=0.0, atol=1e-15)
    assert np.allclose(base[2], scaled[2], rtol=0.0, atol=1e-15)


def test_campaign145_does_not_form_a_lunch_return() -> None:
    closes, amounts = _day(return_index=80, amount_index=20)
    shifted = closes.copy()
    shifted[:, 120:] *= 37.0
    base = c145.compute_return_amount_path_signed_area(closes, amounts)
    changed = c145.compute_return_amount_path_signed_area(shifted, amounts)
    assert base[1].tolist() == changed[1].tolist() == [True]
    assert np.allclose(base[0], changed[0], rtol=0.0, atol=1e-15)
    assert np.allclose(base[2], changed[2], rtol=0.0, atol=1e-15)


def test_campaign145_zero_increments_are_retained_but_denominators_are_required() -> (
    None
):
    closes, amounts = _day(return_index=50, amount_index=50)
    values, eligible, _halves, _quality = c145.compute_return_amount_path_signed_area(
        closes, amounts
    )
    assert eligible.tolist() == [True]
    assert np.isfinite(values).all()

    flat = np.ones((1, 240), dtype=np.float64)
    positive_amount = np.ones((1, 240), dtype=np.float64)
    values, eligible, _halves, quality = c145.compute_return_amount_path_signed_area(
        flat, positive_amount
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values).all()
    assert quality["morning_zero_absolute_return_total_rows"] == 1
    assert quality["afternoon_zero_absolute_return_total_rows"] == 1


def test_campaign145_invalid_source_and_shape_fail_closed() -> None:
    closes = np.ones((4, 240), dtype=np.float64)
    amounts = np.ones((4, 240), dtype=np.float64)
    closes[0, 10] = np.nan
    closes[1, 10] = 0.0
    amounts[2, 10] = np.nan
    amounts[3, 10] = -1.0
    values, eligible, _halves, quality = c145.compute_return_amount_path_signed_area(
        closes, amounts
    )
    assert eligible.tolist() == [False, False, False, False]
    assert np.isnan(values).all()
    assert quality["nonfinite_close_rows"] == 1
    assert quality["nonpositive_close_rows"] == 1
    assert quality["nonfinite_amount_rows"] == 1
    assert quality["negative_amount_rows"] == 1

    with pytest.raises(c145.Campaign145FormulaError):
        c145.compute_return_amount_path_signed_area(
            np.ones((1, 239)), np.ones((1, 239))
        )
