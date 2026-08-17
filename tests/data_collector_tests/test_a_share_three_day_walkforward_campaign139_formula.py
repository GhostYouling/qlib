from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign139_formula as formula


def test_protocol_binding_and_frozen_identity() -> None:
    spec = formula.load_protocol()

    assert formula.FACTOR_NAME == (
        "quarterly_realized_profit_growth_forecast_surprise_rank"
    )
    assert formula.SCORE_DIRECTION == "higher"
    assert spec["candidate"]["raw_formula"] == "profit_yoy - forecast_profit_yoy"
    assert spec["candidate"]["event_age_calendar_days"] == 3


def test_raw_surprise_and_average_tie_percentile() -> None:
    scores, eligible, quality = formula.compute_ranked_surprise(
        np.array([20.0, 10.0, 10.0, np.nan, 30.0]),
        np.array([10.0, 10.0, 0.0, 5.0, 20.0]),
        np.array([True, True, True, True, True]),
        np.array([True, True, True, True, True]),
        np.array([True, True, True, True, True]),
    )

    np.testing.assert_array_equal(eligible, np.array([True, True, True, False, True]))
    np.testing.assert_allclose(scores[eligible], np.array([0.75, 0.25, 0.75, 0.75]))
    assert np.isnan(scores[3])
    assert quality == {
        "source_pairs": 5,
        "eligible_pairs": 4,
        "nonfinite_pairs": 1,
        "mismatched_key_pairs": 0,
        "nonprior_forecast_pairs": 0,
        "conflicting_duplicate_pairs": 0,
        "positive_surprises": 3,
        "exact_zero_surprises": 1,
        "negative_surprises": 0,
    }


def test_invalid_join_semantics_fail_rows_closed() -> None:
    raw, eligible, quality = formula.compute_raw_surprise(
        np.array([5.0, 5.0, 5.0, 5.0]),
        np.array([1.0, 1.0, 1.0, 1.0]),
        np.array([False, True, True, True]),
        np.array([True, False, True, True]),
        np.array([True, True, False, True]),
    )

    np.testing.assert_array_equal(eligible, np.array([False, False, False, True]))
    assert np.isnan(raw[:3]).all()
    assert raw[3] == 4.0
    assert quality["mismatched_key_pairs"] == 1
    assert quality["nonprior_forecast_pairs"] == 1
    assert quality["conflicting_duplicate_pairs"] == 1


def test_common_shift_invariance_and_direction() -> None:
    realized = np.array([2.0, 5.0, 9.0])
    forecast = np.array([4.0, 4.0, 4.0])
    valid = np.ones(3, dtype=bool)

    base, eligible, _ = formula.compute_ranked_surprise(
        realized, forecast, valid, valid, valid
    )
    shifted, shifted_eligible, _ = formula.compute_ranked_surprise(
        realized + 100.0,
        forecast + 100.0,
        valid,
        valid,
        valid,
    )

    np.testing.assert_array_equal(eligible, shifted_eligible)
    np.testing.assert_allclose(base, shifted)
    np.testing.assert_allclose(base, np.array([1.0 / 3.0, 2.0 / 3.0, 1.0]))


def test_exact_ties_have_no_tolerance() -> None:
    raw = np.array([0.0, 0.0, np.nextafter(0.0, 1.0)])
    scores = formula.average_tie_percentile(raw, np.ones(3, dtype=bool))

    np.testing.assert_allclose(scores[:2], np.array([0.5, 0.5]))
    assert scores[2] == 1.0


def test_shape_and_mask_errors_fail_closed() -> None:
    with pytest.raises(formula.Campaign139FormulaError):
        formula.compute_raw_surprise(
            np.array([[1.0]]),
            np.array([1.0]),
            np.array([True]),
            np.array([True]),
            np.array([True]),
        )
    with pytest.raises(formula.Campaign139FormulaError):
        formula.average_tie_percentile(np.array([1.0]), np.array([1], dtype=np.int64))
