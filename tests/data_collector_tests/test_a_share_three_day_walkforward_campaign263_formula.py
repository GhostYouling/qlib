from __future__ import annotations

import math

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign263_formula as formula


def _two_half_profile(*components: tuple[int, float]) -> np.ndarray:
    position = np.arange(formula.HALF_POSITIONS, dtype=np.float64)
    half = np.ones(formula.HALF_POSITIONS, dtype=np.float64)
    for frequency, amplitude in components:
        half += amplitude * np.cos(
            2.0 * np.pi * float(frequency) * position / formula.HALF_POSITIONS
        )
    assert (half >= 0.0).all()
    return np.concatenate([half, half])[None, :]


def test_protocol_is_fingerprint_bound() -> None:
    spec = formula.load_protocol()
    assert spec["candidate"]["name"] == formula.FACTOR_NAME


def test_one_frequency_has_zero_entropy_and_is_eligible() -> None:
    scores, eligible, quality = formula.compute_amount_profile_spectral_entropy(
        _two_half_profile((7, 0.5))
    )
    assert eligible.tolist() == [True]
    assert scores[0] == pytest.approx(0.0, abs=1e-12)
    assert quality["eligible_rows"] == 1


def test_two_equal_frequency_powers_have_exact_normalized_entropy() -> None:
    scores, eligible, _ = formula.compute_amount_profile_spectral_entropy(
        _two_half_profile((7, 0.25), (19, 0.25))
    )
    assert eligible.tolist() == [True]
    assert scores[0] == pytest.approx(math.log(2.0) / math.log(60.0), abs=1e-12)


def test_uniform_profile_is_missing_for_zero_non_dc_power() -> None:
    values = np.ones((1, formula.PROFILE_POSITIONS), dtype=np.float64)
    scores, eligible, quality = formula.compute_amount_profile_spectral_entropy(values)
    assert eligible.tolist() == [False]
    assert np.isnan(scores[0])
    assert quality["zero_non_dc_power_rows"] == 1


def test_exact_zero_bars_are_retained() -> None:
    values = _two_half_profile((1, 1.0))
    assert (values == 0.0).any()
    scores, eligible, quality = formula.compute_amount_profile_spectral_entropy(values)
    assert eligible.tolist() == [True]
    assert np.isfinite(scores[0])
    assert quality["negative_amount_rows"] == 0


def test_nonpositive_half_total_is_missing() -> None:
    values = np.ones((1, formula.PROFILE_POSITIONS), dtype=np.float64)
    values[0, : formula.HALF_POSITIONS] = 0.0
    scores, eligible, quality = formula.compute_amount_profile_spectral_entropy(values)
    assert eligible.tolist() == [False]
    assert np.isnan(scores[0])
    assert quality["nonpositive_half_total_rows"] == 1


@pytest.mark.parametrize("bad", [np.nan, np.inf, -1.0])
def test_invalid_amount_is_missing(bad: float) -> None:
    values = _two_half_profile((3, 0.5))
    values[0, 10] = bad
    scores, eligible, _ = formula.compute_amount_profile_spectral_entropy(values)
    assert eligible.tolist() == [False]
    assert np.isnan(scores[0])


def test_batch_shape_and_bounds() -> None:
    values = np.concatenate(
        [
            _two_half_profile((2, 0.3)),
            _two_half_profile((2, 0.2), (11, 0.1), (37, 0.1)),
        ],
        axis=0,
    )
    scores, eligible, quality = formula.compute_amount_profile_spectral_entropy(values)
    assert eligible.tolist() == [True, True]
    assert ((scores >= 0.0) & (scores <= 1.0)).all()
    assert quality["rows"] == 2


def test_wrong_shape_fails_closed() -> None:
    with pytest.raises(formula.Campaign263FormulaError):
        formula.compute_amount_profile_spectral_entropy(np.ones((2, 239)))
