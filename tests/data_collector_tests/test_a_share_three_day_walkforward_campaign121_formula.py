from __future__ import annotations

import hashlib

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign121_formula as formula


def _base() -> tuple[np.ndarray, np.ndarray]:
    opens = np.full((1, 240), 100.0)
    closes = np.full((1, 240), 100.0)
    return opens, closes


def test_frozen_protocol_binding_and_single_choice() -> None:
    spec = formula.load_protocol()
    assert hashlib.sha256(formula.PROTOCOL_PATH.read_bytes()).hexdigest() == (
        formula.PROTOCOL_SHA256
    )
    assert spec["candidate"]["name"] == formula.FACTOR_NAME
    assert spec["candidate"]["search_space"]["candidate_count"] == 1
    assert spec["comparison_contract"]["numeric_comparator_count"] == 138


def test_upward_and_downward_first_attainment_are_symmetric() -> None:
    opens = np.full((2, 240), 100.0)
    closes = np.full((2, 240), 100.0)
    closes[0, 39:] = 110.0
    closes[1, 39:] = 90.0
    scores, eligible, tau, quality = (
        formula.compute_terminal_close_direction_first_attainment(opens, closes)
    )
    assert eligible.tolist() == [True, True]
    assert tau.tolist() == [40, 40]
    assert scores.tolist() == [200.0 / 239.0, 200.0 / 239.0]
    assert quality["upward_terminal_rows"] == 1
    assert quality["downward_terminal_rows"] == 1


def test_terminal_only_attainment_is_zero_and_early_attainment_is_one() -> None:
    opens = np.full((2, 240), 100.0)
    closes = np.full((2, 240), 100.0)
    closes[0, -1] = 101.0
    closes[1, :] = 101.0
    scores, eligible, tau, _ = (
        formula.compute_terminal_close_direction_first_attainment(opens, closes)
    )
    assert eligible.tolist() == [True, True]
    assert tau.tolist() == [240, 1]
    assert scores.tolist() == [0.0, 1.0]


def test_exact_neutral_direction_is_valid_zero_without_synthetic_tau() -> None:
    opens, closes = _base()
    closes[0, 10:20] = 110.0
    closes[0, 20:30] = 90.0
    scores, eligible, tau, quality = (
        formula.compute_terminal_close_direction_first_attainment(opens, closes)
    )
    assert eligible.tolist() == [True]
    assert scores.tolist() == [0.0]
    assert tau.tolist() == [0]
    assert quality["neutral_terminal_rows"] == 1


def test_preterminal_reordering_changes_score_with_fixed_endpoints() -> None:
    opens = np.full((2, 240), 100.0)
    closes = np.linspace(100.0, 110.0, 240)[None, :].repeat(2, axis=0)
    closes[0, 20] = 110.0
    closes[1, 200] = 110.0
    closes[:, -1] = 110.0
    scores, eligible, tau, _ = (
        formula.compute_terminal_close_direction_first_attainment(opens, closes)
    )
    assert eligible.all()
    assert tau.tolist() == [21, 201]
    assert scores[0] > scores[1]


def test_invalid_shapes_and_values_fail_closed() -> None:
    with pytest.raises(formula.Campaign121FormulaError, match="shape"):
        formula.compute_terminal_close_direction_first_attainment(
            np.ones((1, 239)), np.ones((1, 239))
        )
    with pytest.raises(formula.Campaign121FormulaError, match="match"):
        formula.compute_terminal_close_direction_first_attainment(
            np.ones((1, 240)), np.ones((2, 240))
        )
    opens = np.ones((3, 240))
    closes = np.ones((3, 240))
    opens[0, 0] = np.nan
    closes[1, 30] = 0.0
    closes[2, 30] = -1.0
    scores, eligible, tau, quality = (
        formula.compute_terminal_close_direction_first_attainment(opens, closes)
    )
    assert eligible.tolist() == [False, False, False]
    assert np.isnan(scores).all()
    assert tau.tolist() == [0, 0, 0]
    assert quality["invalid_anchor_or_close_rows"] == 3
