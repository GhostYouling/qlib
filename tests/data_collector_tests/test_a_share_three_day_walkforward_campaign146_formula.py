from __future__ import annotations

import json

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign146_formula as formula


def _paths_from_vectors(
    returns: np.ndarray, activity: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    closes = np.concatenate(([1.0], np.exp(np.cumsum(returns))))
    amounts = np.concatenate(([0.0], np.expm1(activity)))
    return closes, amounts


def _two_half_paths(
    return_index: int, amount_index: int
) -> tuple[np.ndarray, np.ndarray]:
    returns = np.zeros(formula.OBSERVATIONS_PER_HALF, dtype=np.float64)
    activity = np.zeros(formula.OBSERVATIONS_PER_HALF, dtype=np.float64)
    returns[return_index] = 0.01
    activity[amount_index] = 1.0
    half_close, half_amount = _paths_from_vectors(returns, activity)
    return (
        np.concatenate((half_close, half_close))[None, :],
        np.concatenate((half_amount, half_amount))[None, :],
    )


def test_protocol_is_exact_and_prevalue() -> None:
    spec = formula.load_protocol()
    assert spec["candidate"]["name"] == formula.FACTOR_NAME
    assert spec["candidate"]["direction"] == "higher"
    assert (
        spec["research_boundary"]["campaign146_source_rows_read_before_freeze"] is False
    )
    assert (
        spec["research_boundary"]["campaign146_comparator_values_read_before_freeze"]
        is False
    )
    assert (
        spec["research_boundary"][
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        ]
        is False
    )


def test_amount_leading_return_has_positive_orientation() -> None:
    closes, amounts = _two_half_paths(return_index=21, amount_index=20)
    values, eligible, halves, quality = (
        formula.compute_return_amount_cross_spectral_phase_lead(closes, amounts)
    )
    assert eligible.tolist() == [True]
    assert values[0] > 0.0
    assert halves[0, 0] == pytest.approx(halves[0, 1])
    assert quality["eligible_rows"] == 1


def test_return_leading_amount_has_negative_orientation() -> None:
    closes, amounts = _two_half_paths(return_index=20, amount_index=21)
    values, eligible, halves, _ = (
        formula.compute_return_amount_cross_spectral_phase_lead(closes, amounts)
    )
    assert eligible.tolist() == [True]
    assert values[0] < 0.0
    assert halves[0, 0] == pytest.approx(halves[0, 1])


def test_contemporaneous_impulses_have_zero_phase() -> None:
    closes, amounts = _two_half_paths(return_index=20, amount_index=20)
    values, eligible, halves, _ = (
        formula.compute_return_amount_cross_spectral_phase_lead(closes, amounts)
    )
    assert eligible.tolist() == [True]
    assert values[0] == pytest.approx(0.0, abs=1e-15)
    assert halves[0].tolist() == pytest.approx([0.0, 0.0], abs=1e-15)


def test_constant_half_or_invalid_source_is_missing() -> None:
    closes, amounts = _two_half_paths(return_index=21, amount_index=20)
    constant_close = closes.copy()
    constant_close[:, : formula.HALF_BAR_COUNT] = 1.0
    negative_amount = amounts.copy()
    negative_amount[0, 10] = -1.0
    stacked_close = np.concatenate((constant_close, closes), axis=0)
    stacked_amount = np.concatenate((amounts, negative_amount), axis=0)
    values, eligible, _, quality = (
        formula.compute_return_amount_cross_spectral_phase_lead(
            stacked_close, stacked_amount
        )
    )
    assert eligible.tolist() == [False, False]
    assert np.isnan(values).all()
    assert quality["morning_nonpositive_spectral_denominator_rows"] == 1
    assert quality["negative_amount_rows"] == 1


def test_shape_and_protocol_tampering_fail(tmp_path) -> None:
    with pytest.raises(formula.Campaign146FormulaError):
        formula.compute_return_amount_cross_spectral_phase_lead(
            np.ones((1, 239)), np.ones((1, 239))
        )

    changed = json.loads(formula.PROTOCOL_PATH.read_text(encoding="utf-8"))
    changed["candidate"]["direction"] = "lower"
    changed_path = tmp_path / "changed.json"
    changed_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(formula.Campaign146FormulaError):
        formula.load_protocol(changed_path)
