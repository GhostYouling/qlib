from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign118_formula as c118


def test_campaign118_protocol_and_finite_formula_are_frozen() -> None:
    spec = c118.load_protocol()
    assert spec["candidate"]["name"] == c118.FACTOR_NAME
    assert spec["candidate"]["direction"] == "higher"
    assert c118.SELECTED_BAR_COUNT == 240
    assert c118.EVENT_COUNT == 24
    assert c118.GAP_COUNT == 25
    assert c118.NON_EVENT_COUNT == 216


def test_campaign118_clustered_events_have_zero_entropy() -> None:
    amounts = np.ones((1, 240), dtype=np.float64)
    amounts[:, :24] = 2.0
    values, eligible, events, gaps, quality = (
        c118.compute_top_decile_amount_event_spacing_entropy(amounts)
    )
    assert eligible.tolist() == [True]
    assert values[0] == pytest.approx(0.0, abs=1e-15)
    assert events.tolist() == [list(range(24))]
    assert gaps[0, :-1].tolist() == [0] * 24
    assert gaps[0, -1] == 216
    assert quality["exact_top24_boundary_tie_rows"] == 0


def test_campaign118_even_gap_construction_matches_frozen_entropy() -> None:
    desired_gaps = np.asarray([9] * 16 + [8] * 9, dtype=np.int16)
    events = np.empty(24, dtype=np.int16)
    events[0] = desired_gaps[0]
    for index in range(1, 24):
        events[index] = events[index - 1] + desired_gaps[index] + 1
    amounts = np.ones((1, 240), dtype=np.float64)
    amounts[0, events] = 2.0
    values, eligible, observed_events, gaps, _quality = (
        c118.compute_top_decile_amount_event_spacing_entropy(amounts)
    )
    probabilities = desired_gaps.astype(np.float64) / 216.0
    expected = -(probabilities * np.log(probabilities)).sum() / np.log(25.0)
    assert eligible.tolist() == [True]
    assert np.array_equal(observed_events[0], events)
    assert np.array_equal(gaps[0], desired_gaps)
    assert gaps.sum() == 216
    assert values[0] == pytest.approx(expected, abs=1e-15)


def test_campaign118_exact_boundary_ties_choose_earlier_clock_indices() -> None:
    amounts = np.ones((1, 240), dtype=np.float64)
    values, eligible, events, gaps, quality = (
        c118.compute_top_decile_amount_event_spacing_entropy(amounts)
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]
    assert events.tolist() == [list(range(24))]
    assert gaps.sum() == 216
    assert quality["exact_top24_boundary_tie_rows"] == 1
    assert quality["zero_amount_selected_observations"] == 0


def test_campaign118_is_invariant_to_strictly_increasing_transform() -> None:
    rng = np.random.default_rng(118)
    amounts = rng.lognormal(mean=4.0, sigma=1.0, size=(3, 240))
    base = c118.compute_top_decile_amount_event_spacing_entropy(amounts)
    transformed = c118.compute_top_decile_amount_event_spacing_entropy(
        np.log1p(amounts)
    )
    assert base[1].tolist() == transformed[1].tolist() == [True, True, True]
    assert np.allclose(base[0], transformed[0], rtol=0.0, atol=0.0)
    assert np.array_equal(base[2], transformed[2])
    assert np.array_equal(base[3], transformed[3])


def test_campaign118_non_event_reordering_does_not_change_score() -> None:
    amounts = np.arange(1.0, 241.0)[None, :]
    base = c118.compute_top_decile_amount_event_spacing_entropy(amounts)
    changed = amounts.copy()
    changed[0, :216] = changed[0, :216][::-1]
    observed = c118.compute_top_decile_amount_event_spacing_entropy(changed)
    assert base[1].tolist() == observed[1].tolist() == [True]
    assert base[0].tolist() == observed[0].tolist()
    assert np.array_equal(base[2], observed[2])
    assert np.array_equal(base[3], observed[3])


def test_campaign118_invalid_source_and_shape_fail_closed() -> None:
    amounts = np.ones((3, 240), dtype=np.float64)
    amounts[0, 10] = np.nan
    amounts[1, 10] = -1.0
    amounts[2] = 0.0
    values, eligible, _events, _gaps, quality = (
        c118.compute_top_decile_amount_event_spacing_entropy(amounts)
    )
    assert eligible.tolist() == [False, False, False]
    assert np.isnan(values).all()
    assert quality["nonfinite_amount_rows"] == 1
    assert quality["negative_amount_rows"] == 1
    assert quality["nonpositive_total_amount_rows"] == 1

    with pytest.raises(c118.Campaign118FormulaError):
        c118.compute_top_decile_amount_event_spacing_entropy(np.ones((1, 239)))
