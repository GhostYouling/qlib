from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign152_formula as formula


def test_protocol_is_frozen_before_values() -> None:
    spec = formula.load_protocol()
    assert spec["candidate"]["name"] == formula.FACTOR_NAME
    assert (
        spec["research_boundary"]["campaign152_source_rows_read_before_freeze"] is False
    )


def test_formula_is_exact_log1p_total_and_monotone() -> None:
    amount = np.vstack([np.ones(240), np.full(240, 2.0)])
    scores, eligible, quality = formula.compute_session_total_amount_magnitude(amount)
    np.testing.assert_allclose(scores, np.log1p([240.0, 480.0]))
    assert eligible.tolist() == [True, True]
    assert quality["eligible_rows"] == 2
    assert scores[1] > scores[0]


def test_formula_is_clock_permutation_invariant() -> None:
    amount = np.arange(240, dtype=np.float64)[None, :]
    reverse = amount[:, ::-1]
    first, first_ok, _ = formula.compute_session_total_amount_magnitude(amount)
    second, second_ok, _ = formula.compute_session_total_amount_magnitude(reverse)
    np.testing.assert_array_equal(first_ok, second_ok)
    np.testing.assert_allclose(first, second)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -1.0])
def test_formula_rejects_invalid_amount_rows(bad: float) -> None:
    amount = np.ones((1, 240), dtype=np.float64)
    amount[0, 17] = bad
    scores, eligible, _ = formula.compute_session_total_amount_magnitude(amount)
    assert not eligible[0]
    assert np.isnan(scores[0])


def test_formula_rejects_zero_total() -> None:
    scores, eligible, quality = formula.compute_session_total_amount_magnitude(
        np.zeros((1, 240), dtype=np.float64)
    )
    assert not eligible[0]
    assert np.isnan(scores[0])
    assert quality["nonpositive_total_amount_rows"] == 1


def test_formula_requires_exact_240_positions() -> None:
    with pytest.raises(formula.Campaign152FormulaError):
        formula.compute_session_total_amount_magnitude(np.ones((1, 239)))
