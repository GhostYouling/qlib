from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign261_formula as formula


def test_protocol_is_frozen_and_value_free() -> None:
    spec = formula.load_protocol()
    assert spec["candidate"]["name"] == formula.FACTOR_NAME
    assert spec["comparison_contract"]["numeric_comparator_count"] == 142
    assert (
        spec["research_boundary"]["campaign261_source_rows_read_before_freeze"] is False
    )


def test_uniform_is_zero_and_single_positive_bar_is_one() -> None:
    amounts = np.ones((2, formula.PROFILE_POSITIONS), dtype=np.float64)
    amounts[1] = 0.0
    amounts[1, 37] = 1.0
    scores, eligible, quality = formula.compute_amount_lorenz_gini(amounts)
    assert eligible.tolist() == [True, True]
    assert scores == pytest.approx([0.0, 1.0], abs=1e-14)
    assert quality["eligible_rows"] == 2


def test_two_equal_positive_bars_have_closed_form_score() -> None:
    amounts = np.zeros((1, formula.PROFILE_POSITIONS), dtype=np.float64)
    amounts[0, [9, 201]] = 1.0
    scores, eligible, _ = formula.compute_amount_lorenz_gini(amounts)
    assert eligible.tolist() == [True]
    assert scores[0] == pytest.approx(238.0 / 239.0, abs=1e-14)


def test_arbitrary_permutation_is_invariant() -> None:
    amounts = np.arange(1.0, formula.PROFILE_POSITIONS + 1.0)[None, :]
    permutation = np.random.default_rng(261).permutation(formula.PROFILE_POSITIONS)
    first, _, _ = formula.compute_amount_lorenz_gini(amounts)
    second, _, _ = formula.compute_amount_lorenz_gini(amounts[:, permutation])
    assert first[0] == pytest.approx(second[0], abs=1e-14)


def test_common_positive_scale_is_invariant() -> None:
    amounts = np.arange(1.0, formula.PROFILE_POSITIONS + 1.0)[None, :]
    first, _, _ = formula.compute_amount_lorenz_gini(amounts)
    second, _, _ = formula.compute_amount_lorenz_gini(amounts * 1e6)
    assert first[0] == pytest.approx(second[0], abs=1e-14)


def test_more_concentrated_distribution_scores_higher() -> None:
    diffuse = np.ones((1, formula.PROFILE_POSITIONS), dtype=np.float64)
    concentrated = diffuse.copy()
    concentrated[0, 0] = 241.0
    diffuse_score, _, _ = formula.compute_amount_lorenz_gini(diffuse)
    concentrated_score, _, _ = formula.compute_amount_lorenz_gini(concentrated)
    assert concentrated_score[0] > diffuse_score[0]


def test_invalid_amount_rows_fail_closed() -> None:
    amounts = np.ones((4, formula.PROFILE_POSITIONS), dtype=np.float64)
    amounts[0] = 0.0
    amounts[1, 2] = -1.0
    amounts[2, 3] = np.nan
    amounts[3, 4] = np.inf
    scores, eligible, quality = formula.compute_amount_lorenz_gini(amounts)
    assert eligible.tolist() == [False, False, False, False]
    assert np.isnan(scores).all()
    assert quality["nonpositive_total_amount_rows"] == 1
    assert quality["negative_amount_rows"] == 1
    assert quality["nonfinite_amount_rows"] == 2


def test_shape_is_exactly_240_positions() -> None:
    with pytest.raises(formula.Campaign261FormulaError):
        formula.compute_amount_lorenz_gini(np.ones((2, 239)))
