#!/usr/bin/env python3
"""Pure prevalue formula for Campaign146's return-amount phase lead."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_no_return_preregistration_20260814.json"
)
PROTOCOL_SHA256 = "7ad8c1bd0ab56521609bf02fcd2f4effa9fb49753ee5703fb3bf3d55c1527e47"
FACTOR_NAME = "intraday_return_amount_cross_spectral_phase_lead_59f"
SCORE_DIRECTION = "higher"
SOURCE_BAR_COUNT = 241
SELECTED_BAR_COUNT = 240
HALF_BAR_COUNT = 120
OBSERVATIONS_PER_HALF = 119
POSITIVE_FREQUENCY_COUNT = 59
VALID_RANGE = (-1.0, 1.0)


class Campaign146FormulaError(ValueError):
    """Raised when a frozen Campaign146 formula invariant changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Load the exact preregistration without reading historical values."""

    target = path.expanduser().resolve()
    if target != PROTOCOL_PATH.resolve() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign146FormulaError("Campaign146 preregistration fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    formula = candidate.get("exact_formula") or {}
    search = candidate.get("search_space") or {}
    comparisons = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign146_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign146_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == SCORE_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "close", "amount"]
        and candidate.get("source_fields_forbidden")
        == ["open", "high", "low", "volume", "daily_price", "forward_return"]
        and grid.get("accepted_rows_required") == SOURCE_BAR_COUNT
        and grid.get("selected_rows") == SELECTED_BAR_COUNT
        and grid.get("rows_per_half") == HALF_BAR_COUNT
        and grid.get("adjacent_returns_per_half") == OBSERVATIONS_PER_HALF
        and grid.get("destination_amount_observations_per_half")
        == OBSERVATIONS_PER_HALF
        and grid.get("positive_frequency_count_per_half") == POSITIVE_FREQUENCY_COUNT
        and grid.get("positive_frequency_indices_inclusive") == [1, 59]
        and grid.get("standalone_09_30_preserved_but_not_loaded_for_formula") is True
        and grid.get("lunch_transition_excluded") is True
        and formula.get("valid_range_inclusive") == list(VALID_RANGE)
        and search.get("candidate_count") == 1
        and search.get("direction_count") == 1
        and search.get("half_weights") == [0.5, 0.5]
        and search.get("dft_length") == OBSERVATIONS_PER_HALF
        and search.get("positive_frequency_indices_inclusive") == [1, 59]
        and search.get("time_lags_selected") == []
        and search.get("operators")
        == ["power_weighted_signed_cross_spectral_phase_lead"]
        and search.get(
            "alternate_direction_field_demeaning_dft_normalization_phase_orientation_frequency_band_half_weight_lag_window_threshold_filter_subset_fit_model_or_combination_search"
        )
        is False
        and comparisons.get("candidate_appended_complete_definition_count") == 155
        and comparisons.get("candidate_appended_complete_definition_order_sha256")
        == "2e4114edb26fa3aaebd145ef07fe4e2ac9c5d9dc4586cf70ff61c20e39b954ba"
        and comparisons.get("numeric_comparator_count") == 141
        and comparisons.get("numeric_comparator_order_sha256")
        == "ec1aebcb939ad516c58037a36a4aaadd4ad8b2abbd3c884705895c58da85a2ee"
        and boundary.get("campaign146_source_rows_read_before_freeze") is False
        and boundary.get("campaign146_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign146_comparator_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign146FormulaError("Campaign146 preregistration semantics changed")
    return spec


def _half_phase(
    closes: np.ndarray, amounts: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    returns = np.log(closes[:, 1:] / closes[:, :-1])
    activity = np.log1p(amounts[:, 1:])
    demeaned_returns = returns - returns.mean(axis=1, keepdims=True)
    demeaned_activity = activity - activity.mean(axis=1, keepdims=True)
    return_spectrum = np.fft.rfft(demeaned_returns, axis=1)[:, 1:]
    activity_spectrum = np.fft.rfft(demeaned_activity, axis=1)[:, 1:]
    if (
        return_spectrum.shape[1] != POSITIVE_FREQUENCY_COUNT
        or activity_spectrum.shape[1] != POSITIVE_FREQUENCY_COUNT
    ):
        raise Campaign146FormulaError(
            "unexpected Campaign146 positive-frequency support"
        )
    cross_spectrum = np.conjugate(activity_spectrum) * return_spectrum
    numerator = -np.imag(cross_spectrum).sum(axis=1)
    denominator = (np.abs(activity_spectrum) * np.abs(return_spectrum)).sum(axis=1)
    positive_denominator = np.isfinite(denominator) & (denominator > 0.0)
    phase = np.divide(
        numerator,
        denominator,
        out=np.full(len(closes), np.nan, dtype=np.float64),
        where=positive_denominator,
    )
    finite_in_range = (
        np.isfinite(phase) & (phase >= VALID_RANGE[0]) & (phase <= VALID_RANGE[1])
    )
    eligible = positive_denominator & finite_in_range
    return (
        phase,
        eligible,
        {
            "nonpositive_spectral_denominator_rows": int((~positive_denominator).sum()),
            "nonfinite_or_out_of_range_phase_rows": int(
                (positive_denominator & ~finite_in_range).sum()
            ),
        },
    )


def compute_return_amount_cross_spectral_phase_lead(
    closes: np.ndarray,
    amounts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Return values, eligibility, two half phases and quality counts."""

    close_values = np.asarray(closes, dtype=np.float64)
    amount_values = np.asarray(amounts, dtype=np.float64)
    if (
        close_values.ndim != 2
        or amount_values.ndim != 2
        or close_values.shape != amount_values.shape
        or close_values.shape[1] != SELECTED_BAR_COUNT
    ):
        raise Campaign146FormulaError(
            "Campaign146 requires equal n-by-240 close and amount arrays"
        )

    finite_close = np.isfinite(close_values).all(axis=1)
    positive_close = (close_values > 0.0).all(axis=1)
    finite_amount = np.isfinite(amount_values).all(axis=1)
    nonnegative_amount = (amount_values >= 0.0).all(axis=1)
    source_valid = finite_close & positive_close & finite_amount & nonnegative_amount

    safe_close = np.where(
        np.isfinite(close_values) & (close_values > 0.0), close_values, 1.0
    )
    safe_amount = np.where(
        np.isfinite(amount_values) & (amount_values >= 0.0), amount_values, 0.0
    )
    morning_phase, morning_eligible, morning_quality = _half_phase(
        safe_close[:, :HALF_BAR_COUNT], safe_amount[:, :HALF_BAR_COUNT]
    )
    afternoon_phase, afternoon_eligible, afternoon_quality = _half_phase(
        safe_close[:, HALF_BAR_COUNT:], safe_amount[:, HALF_BAR_COUNT:]
    )
    half_phases = np.column_stack((morning_phase, afternoon_phase))
    scores = half_phases.mean(axis=1)
    finite_in_range = (
        np.isfinite(scores) & (scores >= VALID_RANGE[0]) & (scores <= VALID_RANGE[1])
    )
    eligible = source_valid & morning_eligible & afternoon_eligible & finite_in_range
    output = np.full(len(close_values), np.nan, dtype=np.float64)
    output[eligible] = scores[eligible]
    quality = {
        "rows": int(len(close_values)),
        "eligible_rows": int(eligible.sum()),
        "nonfinite_close_rows": int((~finite_close).sum()),
        "nonpositive_close_rows": int((finite_close & ~positive_close).sum()),
        "nonfinite_amount_rows": int((~finite_amount).sum()),
        "negative_amount_rows": int((finite_amount & ~nonnegative_amount).sum()),
        "morning_nonpositive_spectral_denominator_rows": morning_quality[
            "nonpositive_spectral_denominator_rows"
        ],
        "afternoon_nonpositive_spectral_denominator_rows": afternoon_quality[
            "nonpositive_spectral_denominator_rows"
        ],
        "half_nonfinite_or_out_of_range_phase_rows": morning_quality[
            "nonfinite_or_out_of_range_phase_rows"
        ]
        + afternoon_quality["nonfinite_or_out_of_range_phase_rows"],
        "score_nonfinite_or_out_of_range_rows": int(
            (
                source_valid & morning_eligible & afternoon_eligible & ~finite_in_range
            ).sum()
        ),
    }
    return output, eligible, half_phases, quality


__all__ = [
    "Campaign146FormulaError",
    "FACTOR_NAME",
    "HALF_BAR_COUNT",
    "OBSERVATIONS_PER_HALF",
    "POSITIVE_FREQUENCY_COUNT",
    "PROTOCOL_PATH",
    "PROTOCOL_SHA256",
    "SCORE_DIRECTION",
    "SELECTED_BAR_COUNT",
    "SOURCE_BAR_COUNT",
    "VALID_RANGE",
    "compute_return_amount_cross_spectral_phase_lead",
    "load_protocol",
]
