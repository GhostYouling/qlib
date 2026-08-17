from __future__ import annotations

import hashlib

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign136_formula as formula


def test_protocol_binding_and_single_frozen_choice() -> None:
    spec = formula.load_protocol()
    assert hashlib.sha256(formula.PROTOCOL_PATH.read_bytes()).hexdigest() == (
        formula.PROTOCOL_SHA256
    )
    candidate = spec["candidate"]
    assert candidate["name"] == formula.FACTOR_NAME
    assert candidate["direction"] == "higher"
    assert candidate["search_space"]["candidate_count"] == 1
    assert spec["comparison_contract"]["numeric_comparator_count"] == 140


def test_absolute_log_ratio_is_symmetric_and_nonnegative() -> None:
    current = np.array([2.0, 0.5, 1.0])
    previous = np.ones(3)
    mask = np.ones(3, dtype=bool)
    scores, eligible, quality = formula.compute_price_basis_adjustment_magnitude(
        current, previous, mask, mask
    )
    assert eligible.tolist() == [True, True, True]
    assert scores.tolist() == pytest.approx([np.log(2.0), np.log(2.0), 0.0])
    assert quality["exact_zero_score_pairs"] == 1
    assert quality["positive_score_pairs"] == 2


def test_common_positive_chain_level_cancels() -> None:
    current = np.array([1.01, 0.97, 4.0])
    previous = np.array([1.0, 1.0, 2.0])
    mask = np.ones(3, dtype=bool)
    first, first_eligible, _ = formula.compute_price_basis_adjustment_magnitude(
        current, previous, mask, mask
    )
    second, second_eligible, _ = formula.compute_price_basis_adjustment_magnitude(
        current * 123.0, previous * 123.0, mask, mask
    )
    assert first_eligible.tolist() == second_eligible.tolist()
    assert second.tolist() == pytest.approx(first.tolist(), abs=1e-14)


def test_nonadjacent_predecessor_and_invalid_identity_fail_closed() -> None:
    current = np.array([1.1, 1.2, 1.3])
    previous = np.ones(3)
    adjacent = np.array([True, False, True])
    identity = np.array([True, True, False])
    scores, eligible, quality = formula.compute_price_basis_adjustment_magnitude(
        current, previous, adjacent, identity
    )
    assert eligible.tolist() == [True, False, False]
    assert np.isfinite(scores[0])
    assert np.isnan(scores[1:]).all()
    assert quality["nonadjacent_or_missing_predecessor_pairs"] == 1
    assert quality["invalid_source_identity_pairs"] == 1


def test_invalid_factor_values_are_missing_without_fill_or_threshold() -> None:
    current = np.array([np.nan, 0.0, -1.0, np.inf, 1.0 + 1e-14])
    previous = np.ones(5)
    mask = np.ones(5, dtype=bool)
    scores, eligible, quality = formula.compute_price_basis_adjustment_magnitude(
        current, previous, mask, mask
    )
    assert eligible.tolist() == [False, False, False, False, True]
    assert np.isnan(scores[:4]).all()
    assert scores[4] > 0.0
    assert quality["invalid_factor_pairs"] == 4


def test_invalid_shapes_and_nonboolean_masks_raise() -> None:
    with pytest.raises(formula.Campaign136FormulaError, match="one-dimensional"):
        formula.compute_price_basis_adjustment_magnitude(
            np.ones((1, 2)),
            np.ones((1, 2)),
            np.ones(2, dtype=bool),
            np.ones(2, dtype=bool),
        )
    with pytest.raises(formula.Campaign136FormulaError, match="shapes"):
        formula.compute_price_basis_adjustment_magnitude(
            np.ones(2),
            np.ones(3),
            np.ones(2, dtype=bool),
            np.ones(2, dtype=bool),
        )
    with pytest.raises(formula.Campaign136FormulaError, match="boolean vector"):
        formula.compute_price_basis_adjustment_magnitude(
            np.ones(2), np.ones(2), np.ones(2), np.ones(2, dtype=bool)
        )
