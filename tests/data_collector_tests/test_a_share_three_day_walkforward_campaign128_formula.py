from __future__ import annotations

import hashlib

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign128_formula as formula


def _four_blocks(values: tuple[float, float, float, float]) -> np.ndarray:
    return np.repeat(np.asarray(values, dtype=float), 30)


def _base_log_prices() -> np.ndarray:
    morning = _four_blocks((0.0, 1.0, 3.0, 4.0))
    afternoon = _four_blocks((0.0, 1.0, 2.0, 3.0))
    return np.r_[morning, afternoon]


def test_protocol_binding_and_single_frozen_choice() -> None:
    spec = formula.load_protocol()
    assert hashlib.sha256(formula.PROTOCOL_PATH.read_bytes()).hexdigest() == (
        formula.PROTOCOL_SHA256
    )
    candidate = spec["candidate"]
    assert candidate["name"] == formula.FACTOR_NAME
    assert candidate["direction"] == "higher"
    assert candidate["search_space"]["candidate_count"] == 1
    assert spec["comparison_contract"]["numeric_comparator_count"] == 139


def test_morning_to_afternoon_dispersion_contraction_has_positive_direction() -> None:
    log_prices = _base_log_prices()
    volumes = np.ones((1, 240))
    amounts = np.exp(log_prices)[None, :]
    scores, eligible, morning, afternoon, quality = (
        formula.compute_transaction_price_dispersion_resolution(volumes, amounts)
    )
    assert eligible.tolist() == [True]
    assert morning.tolist() == pytest.approx([3.0])
    assert afternoon.tolist() == pytest.approx([2.0])
    assert scores.tolist() == pytest.approx([0.2])
    assert quality["eligible_rows"] == 1


def test_half_swap_reverses_score_without_changing_absolute_magnitude() -> None:
    first = _base_log_prices()
    second = np.r_[first[120:], first[:120]]
    volumes = np.ones((2, 240))
    amounts = np.exp(np.vstack([first, second]))
    scores, eligible, _, _, _ = formula.compute_transaction_price_dispersion_resolution(
        volumes, amounts
    )
    assert eligible.all()
    assert scores.tolist() == pytest.approx([0.2, -0.2])


def test_common_transaction_price_unit_shift_cancels() -> None:
    log_prices = _base_log_prices()
    volumes = np.linspace(1.0, 3.0, 240)[None, :]
    amounts = volumes * np.exp(log_prices)[None, :]
    shifted = amounts * 1000.0
    first, first_eligible, _, _, _ = (
        formula.compute_transaction_price_dispersion_resolution(volumes, amounts)
    )
    second, second_eligible, _, _, _ = (
        formula.compute_transaction_price_dispersion_resolution(volumes, shifted)
    )
    assert first_eligible.tolist() == second_eligible.tolist() == [True]
    assert second.tolist() == pytest.approx(first.tolist(), abs=1e-12)


def test_joint_zero_bars_are_inactive_at_exact_half_support() -> None:
    volumes = np.zeros((1, 240))
    amounts = np.zeros((1, 240))
    morning_indices = np.arange(60)
    afternoon_indices = np.arange(120, 180)
    volumes[0, morning_indices] = 1.0
    volumes[0, afternoon_indices] = 1.0
    amounts[0, morning_indices] = np.exp(np.linspace(0.0, 3.0, 60))
    amounts[0, afternoon_indices] = np.exp(np.linspace(0.0, 2.0, 60))
    scores, eligible, _, _, quality = (
        formula.compute_transaction_price_dispersion_resolution(volumes, amounts)
    )
    assert eligible.tolist() == [True]
    assert np.isfinite(scores[0])
    assert quality["insufficient_morning_active_rows"] == 0
    assert quality["insufficient_afternoon_active_rows"] == 0


def test_one_sided_zero_and_insufficient_half_support_fail_closed() -> None:
    volumes = np.ones((2, 240))
    amounts = np.exp(np.vstack([_base_log_prices(), _base_log_prices()]))
    amounts[0, 7] = 0.0
    volumes[1, :61] = 0.0
    amounts[1, :61] = 0.0
    scores, eligible, _, _, quality = (
        formula.compute_transaction_price_dispersion_resolution(volumes, amounts)
    )
    assert eligible.tolist() == [False, False]
    assert np.isnan(scores).all()
    assert quality["one_sided_zero_rows"] == 1
    assert quality["insufficient_morning_active_rows"] == 1


def test_flat_half_dispersion_is_missing_without_epsilon() -> None:
    log_prices = _base_log_prices()
    log_prices[120:] = 2.0
    volumes = np.ones((1, 240))
    amounts = np.exp(log_prices)[None, :]
    scores, eligible, morning, afternoon, quality = (
        formula.compute_transaction_price_dispersion_resolution(volumes, amounts)
    )
    assert eligible.tolist() == [False]
    assert np.isnan(scores[0])
    assert morning[0] > 0.0
    assert afternoon.tolist() == [0.0]
    assert quality["nonpositive_afternoon_dispersion_rows"] == 1


def test_invalid_shapes_and_raw_values_fail_closed() -> None:
    with pytest.raises(formula.Campaign128FormulaError, match="shape"):
        formula.compute_transaction_price_dispersion_resolution(
            np.ones((1, 239)), np.ones((1, 239))
        )
    with pytest.raises(formula.Campaign128FormulaError, match="match"):
        formula.compute_transaction_price_dispersion_resolution(
            np.ones((1, 240)), np.ones((2, 240))
        )
    volumes = np.ones((3, 240))
    amounts = np.exp(
        np.vstack([_base_log_prices(), _base_log_prices(), _base_log_prices()])
    )
    volumes[0, 3] = -1.0
    amounts[1, 4] = np.nan
    volumes[2, 5] = np.inf
    scores, eligible, _, _, quality = (
        formula.compute_transaction_price_dispersion_resolution(volumes, amounts)
    )
    assert eligible.tolist() == [False, False, False]
    assert np.isnan(scores).all()
    assert quality["invalid_raw_rows"] == 3
