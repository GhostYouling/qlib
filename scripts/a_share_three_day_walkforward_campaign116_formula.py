#!/usr/bin/env python3
"""Pure, prevalue implementation of Campaign116's frozen factor formula."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_116_no_return_preregistration_20260812.json"
)
PROTOCOL_SHA256 = "d47d4f1b8d6d7742c17eb82712a85a1dbe8dbb6e8f44e0ff9190e36ef7115c2c"
FACTOR_NAME = "intraday_amount_conditioned_directional_persistence_spread_236p"
SCORE_DIRECTION = "higher"
SELECTED_BAR_COUNT = 240
HALF_BAR_COUNT = 120
PAIR_COUNT_PER_HALF = 118
TOTAL_PAIR_COUNT = 236
MINIMUM_GROUP_SUPPORT = 30


class Campaign116FormulaError(ValueError):
    """Raised when frozen Campaign116 formula inputs or bindings change."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Load the exact preregistration without opening any historical value file."""

    target = path.expanduser().resolve()
    if target != PROTOCOL_PATH.resolve() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign116FormulaError("Campaign116 preregistration fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    formula = candidate.get("exact_formula") or {}
    search = candidate.get("search_space") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign116_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign116_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == SCORE_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "close", "amount"]
        and grid.get("selected_rows") == SELECTED_BAR_COUNT
        and grid.get("returns_per_half") == 119
        and grid.get("adjacent_return_pairs_per_half") == PAIR_COUNT_PER_HALF
        and grid.get("total_return_pairs") == TOTAL_PAIR_COUNT
        and grid.get("lunch_transition_excluded") is True
        and formula.get("valid_range_inclusive") == [-1.0, 1.0]
        and search.get("candidate_count") == 1
        and search.get("direction_count") == 1
        and search.get("minimum_group_support_values")
        == [MINIMUM_GROUP_SUPPORT]
        and search.get(
            "alternate_direction_threshold_support_lag_window_formula_filter_subset_fit_model_or_combination_search"
        )
        is False
        and boundary.get("campaign116_source_rows_read_before_freeze") is False
        and boundary.get("campaign116_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign116_comparator_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read_before_freeze")
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign116FormulaError("Campaign116 preregistration semantics changed")
    return spec


def compute_amount_conditioned_directional_persistence_spread(
    closes: np.ndarray, amounts: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute the exact preregistered score for one or more stock-days.

    Inputs are n-by-240 arrays ordered as the two separate 120-bar continuous
    sessions. The return across the lunch break is deliberately never formed.
    The returned tuple is ``(values, eligible, high_support,
    ordinary_support, pair_states, high_pair_mask)``.
    """

    close = np.asarray(closes, dtype=np.float64)
    amount = np.asarray(amounts, dtype=np.float64)
    if close.ndim != 2 or close.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign116FormulaError("Campaign116 requires an n-by-240 close array")
    if amount.shape != close.shape:
        raise Campaign116FormulaError("Campaign116 close/amount shapes changed")

    source_valid = (
        np.isfinite(close).all(axis=1)
        & (close > 0.0).all(axis=1)
        & np.isfinite(amount).all(axis=1)
        & (amount >= 0.0).all(axis=1)
        & (amount.sum(axis=1) > 0.0)
    )
    medians = np.median(amount, axis=1)

    return_blocks: list[np.ndarray] = []
    endpoint_amount_blocks: list[np.ndarray] = []
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        for start in (0, HALF_BAR_COUNT):
            half_close = close[:, start : start + HALF_BAR_COUNT]
            returns = np.diff(np.log(half_close), axis=1)
            return_blocks.append(returns)
            endpoint_amount_blocks.append(
                amount[:, start + 2 : start + HALF_BAR_COUNT]
            )

    first_returns = np.concatenate(
        [block[:, :-1] for block in return_blocks], axis=1
    )
    second_returns = np.concatenate(
        [block[:, 1:] for block in return_blocks], axis=1
    )
    endpoint_amounts = np.concatenate(endpoint_amount_blocks, axis=1)
    if first_returns.shape[1] != TOTAL_PAIR_COUNT:
        raise Campaign116FormulaError("Campaign116 fixed pair count changed")

    informative = (
        np.isfinite(first_returns)
        & np.isfinite(second_returns)
        & (first_returns != 0.0)
        & (second_returns != 0.0)
    )
    pair_states = np.zeros(first_returns.shape, dtype=np.float64)
    pair_states[(first_returns > 0.0) & (second_returns > 0.0)] = 1.0
    pair_states[(first_returns < 0.0) & (second_returns < 0.0)] = -1.0
    pair_states[~informative] = np.nan

    high_pair_mask = informative & (endpoint_amounts > medians[:, None])
    ordinary_pair_mask = informative & ~high_pair_mask
    high_support = high_pair_mask.sum(axis=1, dtype=np.int64)
    ordinary_support = ordinary_pair_mask.sum(axis=1, dtype=np.int64)

    high_sum = np.where(high_pair_mask, pair_states, 0.0).sum(axis=1)
    ordinary_sum = np.where(ordinary_pair_mask, pair_states, 0.0).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw_score = 0.5 * (
            high_sum / high_support - ordinary_sum / ordinary_support
        )
    eligible = (
        source_valid
        & (high_support >= MINIMUM_GROUP_SUPPORT)
        & (ordinary_support >= MINIMUM_GROUP_SUPPORT)
        & np.isfinite(raw_score)
        & (raw_score >= -1.0)
        & (raw_score <= 1.0)
    )
    values = np.full(close.shape[0], np.nan, dtype=np.float64)
    values[eligible] = raw_score[eligible]
    return (
        values,
        eligible,
        high_support,
        ordinary_support,
        pair_states,
        high_pair_mask,
    )


__all__ = [
    "Campaign116FormulaError",
    "FACTOR_NAME",
    "HALF_BAR_COUNT",
    "MINIMUM_GROUP_SUPPORT",
    "PAIR_COUNT_PER_HALF",
    "PROTOCOL_PATH",
    "PROTOCOL_SHA256",
    "SCORE_DIRECTION",
    "SELECTED_BAR_COUNT",
    "TOTAL_PAIR_COUNT",
    "compute_amount_conditioned_directional_persistence_spread",
    "load_protocol",
]

