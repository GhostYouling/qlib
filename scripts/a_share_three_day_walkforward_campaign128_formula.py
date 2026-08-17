#!/usr/bin/env python3
"""Pure frozen formula for Campaign128 transaction-price dispersion resolution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


SELECTED_BAR_COUNT = 240
HALF_BAR_COUNT = 120
MINIMUM_ACTIVE_BARS_PER_HALF = 60
MIN_SCORE = -1.0
MAX_SCORE = 1.0
FACTOR_NAME = "intraday_transaction_price_dispersion_resolution_2h"
SCORE_DIRECTION = "higher"
REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_128_no_return_preregistration_20260814.json"
)
PROTOCOL_SHA256 = "c3529b84f2785bb3cd0d9afe1594be8de6b784fae0850c461bd7300f56eeb8a1"


class Campaign128FormulaError(ValueError):
    """Raised when inputs violate the frozen Campaign128 formula contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Validate the preregistration without reading a historical value file."""

    target = path.expanduser().resolve()
    if target != PROTOCOL_PATH.resolve() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign128FormulaError("Campaign128 preregistration fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    active = candidate.get("active_bar_contract") or {}
    exact = candidate.get("exact_formula") or {}
    search = candidate.get("search_space") or {}
    comparisons = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign128_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign128_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == SCORE_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "volume", "amount"]
        and grid.get("selected_rows") == SELECTED_BAR_COUNT
        and grid.get("morning_rows") == HALF_BAR_COUNT
        and grid.get("afternoon_rows") == HALF_BAR_COUNT
        and grid.get("standalone_09_30_excluded") is True
        and grid.get("lunch_or_cross_day_state_included") is False
        and active.get("joint_zero_volume_and_amount") == "inactive"
        and active.get("one_sided_zero") == "fatal_for_stock_day"
        and active.get("minimum_active_bars_per_half") == MINIMUM_ACTIVE_BARS_PER_HALF
        and active.get("active_transaction_log_price") == "x_i=ln(amount_i/volume_i)"
        and active.get("active_distribution_weight") == "w_i=volume_i"
        and exact.get("morning_dispersion") == "D_m=Q_m,0.75-Q_m,0.25"
        and exact.get("afternoon_dispersion") == "D_a=Q_a,0.75-Q_a,0.25"
        and exact.get("score") == "(D_m-D_a)/(D_m+D_a)"
        and exact.get("valid_range_inclusive") == [MIN_SCORE, MAX_SCORE]
        and search.get("candidate_count") == 1
        and search.get("direction_count") == 1
        and search.get("half_session_split_count") == 1
        and search.get("quantile_pair_count") == 1
        and search.get("quantile_estimator_count") == 1
        and search.get("minimum_active_support_count") == 1
        and search.get("score_operator_count") == 1
        and search.get(
            "alternate_quantiles_estimator_window_direction_weight_threshold_filter_subset_fit_model_residualization_or_combination_search"
        )
        is False
        and comparisons.get("numeric_comparator_count") == 139
        and comparisons.get("numeric_comparator_order_sha256")
        == "9c4de054ca1b83eced67eece256b024ebec3a6e1925de17a4cedfa7d36265161"
        and comparisons.get("candidate_appended_complete_definition_count") == 151
        and comparisons.get("candidate_appended_complete_definition_order_sha256")
        == "91c2da3018330edbaddbb60b86370dcd9732425590f0565c70790b990002e0b5"
        and boundary.get("campaign128_minute_source_rows_read") is False
        and boundary.get("campaign128_candidate_values_computed_or_read") is False
        and boundary.get("campaign128_comparator_values_read") is False
        and boundary.get("historical_daily_price_fields_read") == []
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign128FormulaError("Campaign128 preregistration semantics changed")
    return spec


def _weighted_interquartile_dispersion(
    log_prices: np.ndarray, weights: np.ndarray
) -> float:
    order = np.argsort(log_prices, kind="stable")
    ordered_prices = log_prices[order]
    ordered_weights = weights[order]
    cumulative = np.cumsum(ordered_weights, dtype=np.float64)
    total = float(cumulative[-1])
    if not np.isfinite(total) or total <= 0.0:
        raise Campaign128FormulaError("active weight must be finite and positive")
    positions = []
    for probability in (0.25, 0.75):
        index = int(np.searchsorted(cumulative, probability * total, side="left"))
        if index >= len(ordered_prices):
            index = len(ordered_prices) - 1
        positions.append(float(ordered_prices[index]))
    return positions[1] - positions[0]


def compute_transaction_price_dispersion_resolution(
    volumes: np.ndarray[Any, Any], amounts: np.ndarray[Any, Any]
) -> tuple[
    np.ndarray[Any, Any],
    np.ndarray[Any, Any],
    np.ndarray[Any, Any],
    np.ndarray[Any, Any],
    dict[str, int],
]:
    """Compute the frozen score for ``n x 240`` volume/amount matrices."""

    volume_values = np.asarray(volumes, dtype=np.float64)
    amount_values = np.asarray(amounts, dtype=np.float64)
    if volume_values.ndim != 2 or volume_values.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign128FormulaError("volumes must have shape (n,240)")
    if amount_values.shape != volume_values.shape:
        raise Campaign128FormulaError("volume and amount shapes must match")

    raw_valid = (
        np.isfinite(volume_values).all(axis=1)
        & np.isfinite(amount_values).all(axis=1)
        & (volume_values >= 0.0).all(axis=1)
        & (amount_values >= 0.0).all(axis=1)
    )
    volume_positive = volume_values > 0.0
    amount_positive = amount_values > 0.0
    one_sided_zero = np.logical_xor(volume_positive, amount_positive).any(axis=1)
    active = volume_positive & amount_positive
    morning_count = active[:, :HALF_BAR_COUNT].sum(axis=1)
    afternoon_count = active[:, HALF_BAR_COUNT:].sum(axis=1)
    supported = (
        raw_valid
        & ~one_sided_zero
        & (morning_count >= MINIMUM_ACTIVE_BARS_PER_HALF)
        & (afternoon_count >= MINIMUM_ACTIVE_BARS_PER_HALF)
    )

    scores = np.full(len(volume_values), np.nan, dtype=np.float64)
    eligible = np.zeros(len(volume_values), dtype=bool)
    morning_dispersion = np.full(len(volume_values), np.nan, dtype=np.float64)
    afternoon_dispersion = np.full(len(volume_values), np.nan, dtype=np.float64)
    nonpositive_morning = 0
    nonpositive_afternoon = 0
    for row_number in np.flatnonzero(supported):
        row_active = active[row_number]
        row_log_prices = np.full(SELECTED_BAR_COUNT, np.nan, dtype=np.float64)
        row_log_prices[row_active] = np.log(
            amount_values[row_number, row_active]
            / volume_values[row_number, row_active]
        )
        morning_mask = row_active[:HALF_BAR_COUNT]
        afternoon_mask = row_active[HALF_BAR_COUNT:]
        morning = _weighted_interquartile_dispersion(
            row_log_prices[:HALF_BAR_COUNT][morning_mask],
            volume_values[row_number, :HALF_BAR_COUNT][morning_mask],
        )
        afternoon = _weighted_interquartile_dispersion(
            row_log_prices[HALF_BAR_COUNT:][afternoon_mask],
            volume_values[row_number, HALF_BAR_COUNT:][afternoon_mask],
        )
        morning_dispersion[row_number] = morning
        afternoon_dispersion[row_number] = afternoon
        if not np.isfinite(morning) or morning <= 0.0:
            nonpositive_morning += 1
            continue
        if not np.isfinite(afternoon) or afternoon <= 0.0:
            nonpositive_afternoon += 1
            continue
        score = (morning - afternoon) / (morning + afternoon)
        if not np.isfinite(score) or not MIN_SCORE <= score <= MAX_SCORE:
            raise Campaign128FormulaError("score outside frozen range")
        scores[row_number] = score
        eligible[row_number] = True

    quality = {
        "source_rows": int(len(volume_values)),
        "eligible_rows": int(eligible.sum()),
        "invalid_raw_rows": int((~raw_valid).sum()),
        "one_sided_zero_rows": int(one_sided_zero.sum()),
        "insufficient_morning_active_rows": int(
            (raw_valid & ~one_sided_zero & (morning_count < 60)).sum()
        ),
        "insufficient_afternoon_active_rows": int(
            (raw_valid & ~one_sided_zero & (afternoon_count < 60)).sum()
        ),
        "nonpositive_morning_dispersion_rows": nonpositive_morning,
        "nonpositive_afternoon_dispersion_rows": nonpositive_afternoon,
    }
    return scores, eligible, morning_dispersion, afternoon_dispersion, quality
