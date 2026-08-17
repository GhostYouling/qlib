#!/usr/bin/env python3
"""Pure Campaign263 amount-profile spectral-entropy formula."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_no_return_preregistration_20260816.json"
)
PROTOCOL_SHA256 = "07c5875034f3e26e6a98f01e3329b3cf1d3d287d119c9358e32e5a2e76b5b924"
FACTOR_NAME = "intraday_amount_profile_spectral_entropy_60f"
FACTOR_DIRECTION = "higher"
PROFILE_POSITIONS = 240
HALF_POSITIONS = 120
FREQUENCY_BINS = 60
BOUND_TOLERANCE = 1e-12


class Campaign263FormulaError(RuntimeError):
    """Raised when the frozen protocol or supplied array is invalid."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Load and semantically validate the value-free Campaign263 protocol."""

    target = path.expanduser().resolve()
    if target != DEFAULT_PROTOCOL.resolve():
        raise Campaign263FormulaError("Campaign263 protocol path changed")
    if not target.is_file() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign263FormulaError("Campaign263 protocol fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    exact = candidate.get("exact_formula") or {}
    comparison = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign263_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign263_minute_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == FACTOR_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "amount"]
        and grid.get("accepted_rows_required") == 241
        and grid.get("selected_rows") == PROFILE_POSITIONS
        and grid.get("standalone_09_30_preserved_but_not_loaded_for_formula") is True
        and grid.get("lunch_transition_included") is False
        and exact.get("transform")
        == "Compute the unnormalized length-120 real DFT X_hk of x_h for every k=1..60 inclusive; k=60 is the Nyquist bin."
        and exact.get("score")
        == "-sum_{k:q_k>0} q_k*ln(q_k)/ln(60)."
        and exact.get("valid_range_inclusive") == [0.0, 1.0]
        and exact.get("direction") == FACTOR_DIRECTION
        and comparison.get("candidate_appended_complete_definition_count") == 162
        and comparison.get("candidate_appended_complete_definition_order_sha256")
        == "974f2c1f16a85eb43a0bd1e8db768dbe120cd8826c1754d5f220bf9f1d4a3ea0"
        and comparison.get("numeric_comparator_count") == 142
        and comparison.get("numeric_comparator_order_sha256")
        == "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
        and boundary.get("campaign263_source_rows_read_before_freeze") is False
        and boundary.get("campaign263_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("historical_daily_price_or_forward_return_values_read_before_freeze")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign263FormulaError("Campaign263 protocol semantics changed")
    return spec


def compute_amount_profile_spectral_entropy(
    amounts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Return all-frequency entropy of two normalized 120-bar amount profiles."""

    values = np.asarray(amounts, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != PROFILE_POSITIONS:
        raise Campaign263FormulaError(
            "Campaign263 requires a two-dimensional 240-position array"
        )
    finite = np.isfinite(values).all(axis=1)
    nonnegative = (values >= 0.0).all(axis=1)
    structurally_valid = finite & nonnegative
    half_totals = np.full((values.shape[0], 2), np.nan, dtype=np.float64)
    if structurally_valid.any():
        shaped = values[structurally_valid].reshape(-1, 2, HALF_POSITIONS)
        half_totals[structurally_valid] = shaped.sum(axis=2)
    positive_halves = structurally_valid & np.isfinite(half_totals).all(axis=1)
    positive_halves &= (half_totals > 0.0).all(axis=1)
    scores = np.full(values.shape[0], np.nan, dtype=np.float64)
    zero_power = np.zeros(values.shape[0], dtype=bool)
    bound_violations = np.zeros(values.shape[0], dtype=bool)
    if positive_halves.any():
        selected = values[positive_halves].reshape(-1, 2, HALF_POSITIONS)
        totals = selected.sum(axis=2)
        normalized = HALF_POSITIONS * selected / totals[:, :, None] - 1.0
        spectrum = np.fft.rfft(normalized, axis=2)[:, :, 1:]
        if spectrum.shape[2] != FREQUENCY_BINS:
            raise Campaign263FormulaError("Campaign263 rFFT frequency support changed")
        powers = np.square(np.abs(spectrum)).sum(axis=1)
        power_totals = powers.sum(axis=1)
        local_positive = np.isfinite(power_totals) & (power_totals > 0.0)
        positive_indices = np.flatnonzero(positive_halves)
        zero_power[positive_indices[~local_positive]] = True
        if local_positive.any():
            probabilities = powers[local_positive] / power_totals[local_positive, None]
            terms = np.zeros_like(probabilities)
            nonzero = probabilities > 0.0
            terms[nonzero] = probabilities[nonzero] * np.log(probabilities[nonzero])
            raw_scores = -terms.sum(axis=1) / np.log(float(FREQUENCY_BINS))
            canonical = raw_scores.copy()
            canonical[(canonical < 0.0) & (canonical >= -BOUND_TOLERANCE)] = 0.0
            canonical[(canonical > 1.0) & (canonical <= 1.0 + BOUND_TOLERANCE)] = 1.0
            local_bad = (
                ~np.isfinite(canonical)
                | (canonical < 0.0)
                | (canonical > 1.0)
            )
            eligible_indices = positive_indices[local_positive]
            bound_violations[eligible_indices[local_bad]] = True
            scores[eligible_indices[~local_bad]] = canonical[~local_bad]
    eligible = positive_halves & ~zero_power & ~bound_violations & np.isfinite(scores)
    scores[~eligible] = np.nan
    quality = {
        "rows": int(values.shape[0]),
        "nonfinite_amount_rows": int((~finite).sum()),
        "negative_amount_rows": int((finite & ~nonnegative).sum()),
        "nonpositive_half_total_rows": int((structurally_valid & ~positive_halves).sum()),
        "zero_non_dc_power_rows": int(zero_power.sum()),
        "bound_violation_rows": int(bound_violations.sum()),
        "eligible_rows": int(eligible.sum()),
    }
    return scores, eligible, quality


__all__ = [
    "BOUND_TOLERANCE",
    "DEFAULT_PROTOCOL",
    "FACTOR_DIRECTION",
    "FACTOR_NAME",
    "FREQUENCY_BINS",
    "HALF_POSITIONS",
    "PROFILE_POSITIONS",
    "PROTOCOL_SHA256",
    "Campaign263FormulaError",
    "compute_amount_profile_spectral_entropy",
    "load_protocol",
]
