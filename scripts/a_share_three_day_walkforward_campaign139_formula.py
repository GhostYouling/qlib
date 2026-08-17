#!/usr/bin/env python3
"""Pure frozen formula for Campaign139 forecast-realization surprise."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


FACTOR_NAME = "quarterly_realized_profit_growth_forecast_surprise_rank"
SCORE_DIRECTION = "higher"
REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_139_no_return_preregistration_20260814.json"
)
PROTOCOL_SHA256 = "def4153f0fdc112ddb5b6349b83449874be040546ef4a9e2a6527dc07e713a1c"


class Campaign139FormulaError(ValueError):
    """Raised when an input violates the frozen Campaign139 formula."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Validate the preregistration without reading a historical source value."""

    target = path.expanduser().resolve()
    if target != PROTOCOL_PATH.resolve() or file_sha256(target) != PROTOCOL_SHA256:
        raise Campaign139FormulaError("Campaign139 preregistration fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    search = candidate.get("search_space") or {}
    comparisons = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    source = spec.get("source_contract") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign139_no_return_preregistration"
        and spec.get("status")
        == "frozen_one_candidate_before_campaign139_source_rows_candidate_comparator_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == SCORE_DIRECTION
        and candidate.get("raw_formula") == "profit_yoy - forecast_profit_yoy"
        and candidate.get("score_formula")
        == "On each signal session, compute pandas-compatible average-tie percentile ranks over finite live raw surprises after every quality/listing gate."
        and candidate.get("event_age_calendar_days") == 3
        and candidate.get("valid_raw_range") == "finite real number"
        and candidate.get("valid_score_range") == "finite (0,1]"
        and search.get("candidate_count") == 1
        and search.get("direction_count") == 1
        and search.get("formula_count") == 1
        and search.get("forecast_selection_rule_count") == 1
        and search.get("event_age_choice_count") == 1
        and search.get("thresholds") == []
        and search.get("filters") == []
        and search.get("subsets") == []
        and search.get("models") == []
        and search.get("fitted_weights") == []
        and search.get("alternate_transforms_or_rescues_allowed") is False
        and comparisons.get("complete_semantic_definition_count_reviewed_before_values")
        == 152
        and comparisons.get("numeric_comparator_count") == 141
        and comparisons.get("numeric_comparator_order_sha256")
        == "ec1aebcb939ad516c58037a36a4aaadd4ad8b2abbd3c884705895c58da85a2ee"
        and source.get("provider_request_allowed") is False
        and source.get("credential_required") is False
        and boundary.get("campaign139_source_rows_read_before_preregistration") is False
        and boundary.get(
            "campaign139_candidate_values_computed_or_read_before_preregistration"
        )
        is False
        and boundary.get("campaign139_comparator_values_read_before_preregistration")
        is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("stress_2024_2025_opened") is False
    ):
        raise Campaign139FormulaError("Campaign139 preregistration semantics changed")
    return spec


def _boolean_mask(values: np.ndarray[Any, Any], *, label: str, size: int) -> np.ndarray:
    mask = np.asarray(values)
    if mask.ndim != 1 or len(mask) != size or mask.dtype.kind != "b":
        raise Campaign139FormulaError(f"{label} must be a boolean vector of length n")
    return mask.astype(bool, copy=False)


def compute_raw_surprise(
    realized_profit_yoy: np.ndarray[Any, Any],
    forecast_profit_yoy: np.ndarray[Any, Any],
    same_instrument_report_period: np.ndarray[Any, Any],
    forecast_strictly_precedes_realized_announcement: np.ndarray[Any, Any],
    duplicate_semantics_valid: np.ndarray[Any, Any],
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any], dict[str, int]]:
    """Compute the frozen raw same-period expectation error."""

    realized = np.asarray(realized_profit_yoy, dtype=np.float64)
    forecast = np.asarray(forecast_profit_yoy, dtype=np.float64)
    if realized.ndim != 1:
        raise Campaign139FormulaError("realized_profit_yoy must be one-dimensional")
    if forecast.shape != realized.shape:
        raise Campaign139FormulaError("realized and forecast shapes must match")
    same_key = _boolean_mask(
        same_instrument_report_period,
        label="same_instrument_report_period",
        size=len(realized),
    )
    prior = _boolean_mask(
        forecast_strictly_precedes_realized_announcement,
        label="forecast_strictly_precedes_realized_announcement",
        size=len(realized),
    )
    duplicates = _boolean_mask(
        duplicate_semantics_valid,
        label="duplicate_semantics_valid",
        size=len(realized),
    )
    finite = np.isfinite(realized) & np.isfinite(forecast)
    eligible = finite & same_key & prior & duplicates
    raw = np.full(len(realized), np.nan, dtype=np.float64)
    raw[eligible] = realized[eligible] - forecast[eligible]
    if not np.isfinite(raw[eligible]).all():
        raise Campaign139FormulaError("eligible raw surprise must be finite")
    quality = {
        "source_pairs": int(len(realized)),
        "eligible_pairs": int(eligible.sum()),
        "nonfinite_pairs": int((~finite).sum()),
        "mismatched_key_pairs": int((finite & ~same_key).sum()),
        "nonprior_forecast_pairs": int((finite & same_key & ~prior).sum()),
        "conflicting_duplicate_pairs": int(
            (finite & same_key & prior & ~duplicates).sum()
        ),
        "positive_surprises": int((eligible & (raw > 0.0)).sum()),
        "exact_zero_surprises": int((eligible & (raw == 0.0)).sum()),
        "negative_surprises": int((eligible & (raw < 0.0)).sum()),
    }
    return raw, eligible, quality


def average_tie_percentile(
    raw_surprise: np.ndarray[Any, Any], eligible: np.ndarray[Any, Any]
) -> np.ndarray[Any, Any]:
    """Rank one signal-session cross-section with exact average ties."""

    raw = np.asarray(raw_surprise, dtype=np.float64)
    if raw.ndim != 1:
        raise Campaign139FormulaError("raw_surprise must be one-dimensional")
    mask = _boolean_mask(eligible, label="eligible", size=len(raw))
    if not np.isfinite(raw[mask]).all():
        raise Campaign139FormulaError("eligible raw_surprise values must be finite")
    scores = np.full(len(raw), np.nan, dtype=np.float64)
    indexes = np.flatnonzero(mask)
    if not len(indexes):
        return scores
    values = raw[indexes]
    order = np.argsort(values, kind="mergesort")
    ordered_values = values[order]
    ordered_scores = np.empty(len(order), dtype=np.float64)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and ordered_values[stop] == ordered_values[start]:
            stop += 1
        average_one_based_rank = ((start + 1) + stop) / 2.0
        ordered_scores[start:stop] = average_one_based_rank / len(order)
        start = stop
    inverse = np.empty(len(order), dtype=np.int64)
    inverse[order] = np.arange(len(order), dtype=np.int64)
    scores[indexes] = ordered_scores[inverse]
    if not (
        np.isfinite(scores[mask]).all()
        and (scores[mask] > 0.0).all()
        and (scores[mask] <= 1.0).all()
    ):
        raise Campaign139FormulaError("ranked surprise outside frozen (0,1] range")
    return scores


def compute_ranked_surprise(
    realized_profit_yoy: np.ndarray[Any, Any],
    forecast_profit_yoy: np.ndarray[Any, Any],
    same_instrument_report_period: np.ndarray[Any, Any],
    forecast_strictly_precedes_realized_announcement: np.ndarray[Any, Any],
    duplicate_semantics_valid: np.ndarray[Any, Any],
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any], dict[str, int]]:
    """Compute raw surprises and their one-session frozen direction ranks."""

    raw, eligible, quality = compute_raw_surprise(
        realized_profit_yoy,
        forecast_profit_yoy,
        same_instrument_report_period,
        forecast_strictly_precedes_realized_announcement,
        duplicate_semantics_valid,
    )
    return average_tie_percentile(raw, eligible), eligible, quality
