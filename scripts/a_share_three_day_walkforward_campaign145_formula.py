#!/usr/bin/env python3
"""Pure prevalue formula for Campaign145's return-amount path area."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_145_no_return_preregistration_20260814.json"
)
PROTOCOL_SHA256 = "0c422531fc1d5ceffb4193d4bcd6b42227555d3cff0ec58f04c81a3aab19edd2"
FACTOR_NAME = "intraday_return_amount_cumulative_path_signed_area_238p"
SCORE_DIRECTION = "higher"
SOURCE_BAR_COUNT = 241
SELECTED_BAR_COUNT = 240
HALF_BAR_COUNT = 120
PAIRS_PER_HALF = 119
TOTAL_PAIR_COUNT = 238
VALID_RANGE = (-1.0, 1.0)


class Campaign145FormulaError(ValueError):
    """Raised when a frozen Campaign145 formula invariant changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Load the exact preregistration without reading a historical value file."""

    target = path.expanduser().resolve()
    if target != PROTOCOL_PATH.resolve() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign145FormulaError("Campaign145 preregistration fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    formula = candidate.get("exact_formula") or {}
    search = candidate.get("search_space") or {}
    comparisons = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign145_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign145_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == SCORE_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "close", "amount"]
        and grid.get("accepted_rows_required") == SOURCE_BAR_COUNT
        and grid.get("selected_rows") == SELECTED_BAR_COUNT
        and grid.get("rows_per_half") == HALF_BAR_COUNT
        and grid.get("adjacent_returns_per_half") == PAIRS_PER_HALF
        and grid.get("total_return_amount_pairs") == TOTAL_PAIR_COUNT
        and grid.get("standalone_09_30_preserved_but_not_loaded_for_formula") is True
        and grid.get("lunch_transition_excluded") is True
        and formula.get("valid_range_inclusive") == list(VALID_RANGE)
        and search.get("candidate_count") == 1
        and search.get("direction_count") == 1
        and search.get("lags") == [1]
        and search.get("operators") == ["half_session_open_path_oriented_area"]
        and search.get(
            "alternate_direction_field_normalization_orientation_closure_half_weight_lag_window_threshold_filter_subset_fit_model_or_combination_search"
        )
        is False
        and comparisons.get("numeric_comparator_count") == 141
        and comparisons.get("numeric_comparator_order_sha256")
        == "ec1aebcb939ad516c58037a36a4aaadd4ad8b2abbd3c884705895c58da85a2ee"
        and boundary.get("campaign145_source_rows_read_before_freeze") is False
        and boundary.get("campaign145_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign145_comparator_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign145FormulaError("Campaign145 preregistration semantics changed")
    return spec


def _half_area(
    closes: np.ndarray, amounts: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    returns = np.log(closes[:, 1:] / closes[:, :-1])
    endpoint_amounts = amounts[:, 1:]
    absolute_return_total = np.abs(returns).sum(axis=1)
    amount_total = endpoint_amounts.sum(axis=1)
    valid = (absolute_return_total > 0.0) & (amount_total > 0.0)

    dx = np.divide(
        returns,
        absolute_return_total[:, None],
        out=np.zeros_like(returns),
        where=absolute_return_total[:, None] > 0.0,
    )
    dy = np.divide(
        endpoint_amounts,
        amount_total[:, None],
        out=np.zeros_like(endpoint_amounts),
        where=amount_total[:, None] > 0.0,
    )
    x_previous = np.cumsum(dx, axis=1) - dx
    y_previous = np.cumsum(dy, axis=1) - dy
    area = 0.5 * np.sum(y_previous * dx - x_previous * dy, axis=1)
    finite_in_range = (
        np.isfinite(area) & (area >= VALID_RANGE[0]) & (area <= VALID_RANGE[1])
    )
    eligible = valid & finite_in_range
    return (
        area,
        eligible,
        {
            "zero_absolute_return_total_rows": int(
                (absolute_return_total <= 0.0).sum()
            ),
            "nonpositive_endpoint_amount_total_rows": int((amount_total <= 0.0).sum()),
            "nonfinite_or_out_of_range_area_rows": int(
                (valid & ~finite_in_range).sum()
            ),
        },
    )


def compute_return_amount_path_signed_area(
    closes: np.ndarray,
    amounts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Return values, eligibility, two half areas and aggregate quality counts."""

    close_values = np.asarray(closes, dtype=np.float64)
    amount_values = np.asarray(amounts, dtype=np.float64)
    if (
        close_values.ndim != 2
        or amount_values.ndim != 2
        or close_values.shape != amount_values.shape
        or close_values.shape[1] != SELECTED_BAR_COUNT
    ):
        raise Campaign145FormulaError(
            "Campaign145 requires equal n-by-240 close and amount arrays"
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
    morning_area, morning_eligible, morning_quality = _half_area(
        safe_close[:, :HALF_BAR_COUNT], safe_amount[:, :HALF_BAR_COUNT]
    )
    afternoon_area, afternoon_eligible, afternoon_quality = _half_area(
        safe_close[:, HALF_BAR_COUNT:], safe_amount[:, HALF_BAR_COUNT:]
    )
    half_areas = np.column_stack((morning_area, afternoon_area))
    scores = half_areas.mean(axis=1)
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
        "morning_zero_absolute_return_total_rows": morning_quality[
            "zero_absolute_return_total_rows"
        ],
        "afternoon_zero_absolute_return_total_rows": afternoon_quality[
            "zero_absolute_return_total_rows"
        ],
        "morning_nonpositive_endpoint_amount_total_rows": morning_quality[
            "nonpositive_endpoint_amount_total_rows"
        ],
        "afternoon_nonpositive_endpoint_amount_total_rows": afternoon_quality[
            "nonpositive_endpoint_amount_total_rows"
        ],
        "half_nonfinite_or_out_of_range_area_rows": morning_quality[
            "nonfinite_or_out_of_range_area_rows"
        ]
        + afternoon_quality["nonfinite_or_out_of_range_area_rows"],
        "score_nonfinite_or_out_of_range_rows": int(
            (
                source_valid & morning_eligible & afternoon_eligible & ~finite_in_range
            ).sum()
        ),
    }
    return output, eligible, half_areas, quality


__all__ = [
    "Campaign145FormulaError",
    "FACTOR_NAME",
    "HALF_BAR_COUNT",
    "PAIRS_PER_HALF",
    "PROTOCOL_PATH",
    "PROTOCOL_SHA256",
    "SCORE_DIRECTION",
    "SELECTED_BAR_COUNT",
    "SOURCE_BAR_COUNT",
    "TOTAL_PAIR_COUNT",
    "VALID_RANGE",
    "compute_return_amount_path_signed_area",
    "load_protocol",
]
