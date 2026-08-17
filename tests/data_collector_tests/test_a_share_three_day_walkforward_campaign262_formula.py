from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign262_formula as formula


def test_protocol_is_frozen_and_value_free() -> None:
    spec = formula.load_protocol()
    assert spec["candidate"]["name"] == formula.FACTOR_NAME
    assert spec["comparison_contract"]["numeric_comparator_count"] == 142
    assert (
        spec["research_boundary"]["campaign262_source_rows_read_before_freeze"] is False
    )


def test_uniform_is_one_and_endpoint_concentration_is_zero() -> None:
    amounts = np.ones((3, formula.PROFILE_POSITIONS), dtype=np.float64)
    amounts[1:] = 0.0
    amounts[1, 0] = 1.0
    amounts[2, -1] = 1.0
    scores, eligible, quality = formula.compute_amount_schedule_uniformity(amounts)
    assert eligible.tolist() == [True, True, True]
    assert scores == pytest.approx([1.0, 0.0, 0.0], abs=1e-14)
    assert quality["eligible_rows"] == 3


def test_clock_reversal_is_symmetric() -> None:
    amounts = np.arange(1.0, formula.PROFILE_POSITIONS + 1.0)[None, :]
    first, _, _ = formula.compute_amount_schedule_uniformity(amounts)
    second, _, _ = formula.compute_amount_schedule_uniformity(amounts[:, ::-1])
    assert first[0] == pytest.approx(second[0], abs=1e-14)


def test_clock_permutation_can_change_score_while_amount_multiset_is_fixed() -> None:
    amounts = np.ones((1, formula.PROFILE_POSITIONS), dtype=np.float64)
    amounts[0, :24] = 100.0
    spread = np.ones((1, formula.PROFILE_POSITIONS), dtype=np.float64)
    spread[0, np.arange(0, formula.PROFILE_POSITIONS, 10)] = 100.0
    clustered_score, _, _ = formula.compute_amount_schedule_uniformity(amounts)
    spread_score, _, _ = formula.compute_amount_schedule_uniformity(spread)
    assert spread_score[0] > clustered_score[0]


def test_same_maximal_gini_has_different_schedule_score() -> None:
    endpoint = np.zeros((1, formula.PROFILE_POSITIONS), dtype=np.float64)
    midpoint = endpoint.copy()
    endpoint[0, 0] = 1.0
    midpoint[0, formula.PROFILE_POSITIONS // 2] = 1.0
    endpoint_score, _, _ = formula.compute_amount_schedule_uniformity(endpoint)
    midpoint_score, _, _ = formula.compute_amount_schedule_uniformity(midpoint)
    assert endpoint_score[0] == pytest.approx(0.0, abs=1e-14)
    assert midpoint_score[0] > endpoint_score[0]


def test_common_positive_scale_is_invariant() -> None:
    amounts = np.arange(1.0, formula.PROFILE_POSITIONS + 1.0)[None, :]
    first, _, _ = formula.compute_amount_schedule_uniformity(amounts)
    second, _, _ = formula.compute_amount_schedule_uniformity(amounts * 1e6)
    assert first[0] == pytest.approx(second[0], abs=1e-14)


def test_invalid_amount_rows_fail_closed() -> None:
    amounts = np.ones((4, formula.PROFILE_POSITIONS), dtype=np.float64)
    amounts[0] = 0.0
    amounts[1, 2] = -1.0
    amounts[2, 3] = np.nan
    amounts[3, 4] = np.inf
    scores, eligible, quality = formula.compute_amount_schedule_uniformity(amounts)
    assert eligible.tolist() == [False, False, False, False]
    assert np.isnan(scores).all()
    assert quality["nonpositive_total_amount_rows"] == 1
    assert quality["negative_amount_rows"] == 1
    assert quality["nonfinite_amount_rows"] == 2


def test_shape_is_exactly_240_positions() -> None:
    with pytest.raises(formula.Campaign262FormulaError):
        formula.compute_amount_schedule_uniformity(np.ones((2, 239)))
