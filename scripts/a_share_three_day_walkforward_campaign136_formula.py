#!/usr/bin/env python3
"""Pure frozen formula for Campaign136 price-basis adjustment magnitude."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


FACTOR_NAME = "daily_realized_price_basis_adjustment_magnitude_1d"
SCORE_DIRECTION = "higher"
PRICE_BASIS = "close_known_raw_pct_chg_chain_v1"
DAILY_SOURCE = "baostock"
REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_136_no_return_preregistration_v2_20260814.json"
)
PROTOCOL_SHA256 = "f23cc1df5d4ed640c82b75ae1b9575718e75977d51b3ce1c33a846534c71e4f0"


class Campaign136FormulaError(ValueError):
    """Raised when inputs violate the frozen Campaign136 formula contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Validate the preregistration without decoding a historical source value."""

    target = path.expanduser().resolve()
    if target != PROTOCOL_PATH.resolve() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign136FormulaError("Campaign136 preregistration fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    source = spec.get("source_snapshot_contract") or {}
    candidate = spec.get("candidate") or {}
    predecessor = candidate.get("predecessor_contract") or {}
    identity = candidate.get("source_identity_contract") or {}
    exact = candidate.get("exact_formula") or {}
    search = candidate.get("search_space") or {}
    comparisons = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign136_no_return_preregistration"
        and spec.get("status")
        == "frozen_v2_before_campaign136_daily_factor_source_candidate_comparator_ohlcv_or_return_values"
        and source.get("source_file_count") == 5451
        and source.get("source_total_bytes") == 1502484498
        and source.get("source_file_identity_order_sha256")
        == "d7dca618dbef6620e1c4782cb970178afa5777e3f1101a916df5eb6b8bf37cab"
        and source.get("output_signal_start") == "2019-01-01"
        and source.get("output_signal_end") == "2025-12-31"
        and source.get("source_predecessor_calendar_sessions_before_start") == 1
        and source.get("source_rows_after_output_signal_end_allowed") is False
        and source.get("output_rows_outside_frozen_signal_range_allowed") is False
        and source.get("provider_request_allowed") is False
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == SCORE_DIRECTION
        and candidate.get("source_projection")
        == ["date", "symbol", "factor", "price_basis", "daily_source"]
        and predecessor.get("lag_count") == 1
        and predecessor.get("same_symbol_row_required_on_both_dates") is True
        and predecessor.get("suspension_listing_or_missing_gap_bridge_allowed") is False
        and predecessor.get("previous_source_row_substitution_allowed") is False
        and identity.get("price_basis_on_both_rows") == PRICE_BASIS
        and identity.get("daily_source_on_both_rows") == DAILY_SOURCE
        and identity.get("finite_strictly_positive_factor_on_both_rows") is True
        and exact.get("score") == "abs(log(factor_t/factor_p))"
        and exact.get("valid_range") == "finite [0,+infinity)"
        and exact.get("exact_factor_equality") == "valid zero"
        and exact.get("threshold_tolerance_rounding_clip_fill_or_event_classification")
        is False
        and search.get("candidate_count") == 1
        and search.get("direction_count") == 1
        and search.get("lag_count") == 1
        and search.get("formula_operator_count") == 1
        and search.get(
            "alternate_sign_lag_window_threshold_tolerance_filter_subset_fit_model_residualization_or_combination_search"
        )
        is False
        and comparisons.get("numeric_comparator_count") == 140
        and comparisons.get("numeric_comparator_order_sha256")
        == "c71bfe27486c9567afd3aca21e4b04053658c23ac651e7f4df7fd014b0c31efd"
        and comparisons.get("candidate_appended_complete_definition_count") == 152
        and comparisons.get("candidate_appended_complete_definition_order_sha256")
        == "60c465a3e2043efae6b92b8c5f3e007cd397a1cd0ec3094b4fa005665bbe5736"
        and boundary.get("campaign136_daily_source_values_decoded_or_read") is False
        and boundary.get("campaign136_candidate_values_computed_or_read") is False
        and boundary.get("campaign136_comparator_values_read") is False
        and boundary.get("historical_daily_ohlcv_fields_read") == []
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign136FormulaError("Campaign136 preregistration semantics changed")
    return spec


def _boolean_mask(values: np.ndarray[Any, Any], *, label: str, size: int) -> np.ndarray:
    mask = np.asarray(values)
    if mask.ndim != 1 or len(mask) != size or mask.dtype.kind != "b":
        raise Campaign136FormulaError(f"{label} must be a boolean vector of length n")
    return mask.astype(bool, copy=False)


def compute_price_basis_adjustment_magnitude(
    current_factors: np.ndarray[Any, Any],
    previous_factors: np.ndarray[Any, Any],
    calendar_adjacent: np.ndarray[Any, Any],
    source_identity_valid: np.ndarray[Any, Any],
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any], dict[str, int]]:
    """Compute the frozen score for paired same-symbol adjacent-session factors."""

    current = np.asarray(current_factors, dtype=np.float64)
    previous = np.asarray(previous_factors, dtype=np.float64)
    if current.ndim != 1:
        raise Campaign136FormulaError(
            "current_factors must be a one-dimensional vector"
        )
    if previous.shape != current.shape:
        raise Campaign136FormulaError("current and previous factor shapes must match")
    adjacent = _boolean_mask(
        calendar_adjacent, label="calendar_adjacent", size=len(current)
    )
    identity = _boolean_mask(
        source_identity_valid,
        label="source_identity_valid",
        size=len(current),
    )

    valid_factors = (
        np.isfinite(current)
        & np.isfinite(previous)
        & (current > 0.0)
        & (previous > 0.0)
    )
    eligible = valid_factors & adjacent & identity
    scores = np.full(len(current), np.nan, dtype=np.float64)
    scores[eligible] = np.abs(np.log(current[eligible]) - np.log(previous[eligible]))
    if (
        np.isfinite(scores[eligible]).sum() != int(eligible.sum())
        or (scores[eligible] < 0.0).any()
    ):
        raise Campaign136FormulaError("score outside frozen finite nonnegative range")

    exact_zero = eligible & (current == previous)
    quality = {
        "source_pairs": int(len(current)),
        "eligible_pairs": int(eligible.sum()),
        "invalid_factor_pairs": int((~valid_factors).sum()),
        "nonadjacent_or_missing_predecessor_pairs": int(
            (valid_factors & ~adjacent).sum()
        ),
        "invalid_source_identity_pairs": int(
            (valid_factors & adjacent & ~identity).sum()
        ),
        "exact_zero_score_pairs": int(exact_zero.sum()),
        "positive_score_pairs": int((eligible & ~exact_zero).sum()),
    }
    return scores, eligible, quality
