from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign260_formula as formula


def test_protocol_is_frozen_and_value_free() -> None:
    spec = formula.load_protocol()
    assert spec["candidate"]["name"] == formula.FACTOR_NAME
    assert spec["comparison_contract"]["numeric_comparator_count"] == 142
    assert spec["research_boundary"]["campaign260_source_rows_read_before_freeze"] is False


def test_uniform_and_single_point_mass_are_neutral() -> None:
    amounts = np.ones((2, formula.PROFILE_POSITIONS), dtype=np.float64)
    amounts[1] = 0.0
    amounts[1, 37] = 1.0
    scores, eligible, quality = formula.compute_amount_clock_third_central_moment(
        amounts
    )
    assert eligible.tolist() == [True, True]
    assert scores == pytest.approx([0.5, 0.5], abs=1e-14)
    assert quality["eligible_rows"] == 2


def test_time_reversal_complements_score() -> None:
    amounts = np.zeros((1, formula.PROFILE_POSITIONS), dtype=np.float64)
    amounts[0, 15] = 8.0
    amounts[0, 120] = 2.0
    amounts[0, 230] = 1.0
    forward, _, _ = formula.compute_amount_clock_third_central_moment(amounts)
    reverse, _, _ = formula.compute_amount_clock_third_central_moment(
        amounts[:, ::-1]
    )
    assert forward[0] + reverse[0] == pytest.approx(1.0, abs=1e-14)


def test_common_positive_scale_is_invariant() -> None:
    amounts = np.arange(1.0, formula.PROFILE_POSITIONS + 1.0)[None, :]
    first, _, _ = formula.compute_amount_clock_third_central_moment(amounts)
    second, _, _ = formula.compute_amount_clock_third_central_moment(amounts * 1e6)
    assert first[0] == pytest.approx(second[0], abs=1e-14)


def test_sharp_two_endpoint_extrema_map_to_unit_interval_endpoints() -> None:
    q_low = (3.0 - np.sqrt(3.0)) / 6.0
    positive = np.zeros((1, formula.PROFILE_POSITIONS), dtype=np.float64)
    positive[0, 0] = 1.0 - q_low
    positive[0, -1] = q_low
    negative = positive[:, ::-1]
    high, high_ok, _ = formula.compute_amount_clock_third_central_moment(positive)
    low, low_ok, _ = formula.compute_amount_clock_third_central_moment(negative)
    assert high_ok.tolist() == [True]
    assert low_ok.tolist() == [True]
    assert high[0] == pytest.approx(1.0, abs=1e-14)
    assert low[0] == pytest.approx(0.0, abs=1e-14)


def test_invalid_amount_rows_fail_closed() -> None:
    amounts = np.ones((4, formula.PROFILE_POSITIONS), dtype=np.float64)
    amounts[0] = 0.0
    amounts[1, 2] = -1.0
    amounts[2, 3] = np.nan
    amounts[3, 4] = np.inf
    scores, eligible, quality = formula.compute_amount_clock_third_central_moment(
        amounts
    )
    assert eligible.tolist() == [False, False, False, False]
    assert np.isnan(scores).all()
    assert quality["nonpositive_total_amount_rows"] == 1
    assert quality["negative_amount_rows"] == 1
    assert quality["nonfinite_amount_rows"] == 2


def test_shape_is_exactly_240_positions() -> None:
    with pytest.raises(formula.Campaign260FormulaError):
        formula.compute_amount_clock_third_central_moment(np.ones((2, 239)))
