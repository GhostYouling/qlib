#!/usr/bin/env python3
"""Pure frozen formula for Campaign121 terminal-level first attainment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


SELECTED_BAR_COUNT = 240
POSITION_SPAN = 239
MIN_SCORE = 0.0
MAX_SCORE = 1.0
REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_121_no_return_preregistration_20260814.json"
)
PROTOCOL_SHA256 = "9ca39c1b9daac5f8cec11523ee1992b71c105a6c71547e4805d7301be93f0399"
FACTOR_NAME = "intraday_terminal_close_direction_first_attainment_240m"
SCORE_DIRECTION = "higher"


class Campaign121FormulaError(ValueError):
    """Raised when inputs violate the frozen Campaign121 contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Validate the protocol without opening a historical value file."""

    target = path.expanduser().resolve()
    if target != PROTOCOL_PATH.resolve() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign121FormulaError("Campaign121 preregistration fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    exact = candidate.get("exact_formula") or {}
    search = candidate.get("search_space") or {}
    comparisons = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign121_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign121_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == SCORE_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "open", "close"]
        and grid.get("raw_rows_required") == 241
        and grid.get("selected_rows") == SELECTED_BAR_COUNT
        and grid.get("open_reference") == "raw open of the 09:31 selected bar"
        and grid.get("terminal_reference") == "raw close of the 15:00 selected bar"
        and grid.get("standalone_09_30_loaded_only_for_exact_grid_validation") is True
        and grid.get("lunch_return_or_cross_day_state_included") is False
        and exact.get("normalization") == "fixed 239-position span"
        and exact.get("valid_range_inclusive") == [MIN_SCORE, MAX_SCORE]
        and search.get("candidate_count") == 1
        and search.get("direction_count") == 1
        and search.get("reference_count") == 1
        and search.get("attainment_operator_count") == 1
        and search.get(
            "alternate_reference_arrival_operator_normalization_window_direction_threshold_filter_subset_fit_model_or_combination_search"
        )
        is False
        and comparisons.get("numeric_comparator_count") == 138
        and comparisons.get("numeric_comparator_order_sha256")
        == "e917d9f832bda02f87c0a7e02a26127629146318de826684e8dfd6432fc20a3b"
        and comparisons.get("candidate_appended_complete_definition_count") == 147
        and comparisons.get("candidate_appended_complete_definition_order_sha256")
        == "3f3756a4128011d9cd718e97d23ee3b1c78022433b269c75bd715f304a055bf0"
        and boundary.get("campaign121_source_rows_read") is False
        and boundary.get("campaign121_candidate_values_computed_or_read") is False
        and boundary.get("campaign121_comparator_values_read") is False
        and boundary.get("historical_daily_price_fields_read") == []
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign121FormulaError("Campaign121 preregistration semantics changed")
    return spec


def compute_terminal_close_direction_first_attainment(
    opens: np.ndarray[Any, Any], closes: np.ndarray[Any, Any]
) -> tuple[
    np.ndarray[Any, Any],
    np.ndarray[Any, Any],
    np.ndarray[Any, Any],
    dict[str, int],
]:
    """Compute the frozen score for ``n x 240`` open/close matrices."""

    open_values = np.asarray(opens, dtype=np.float64)
    close_values = np.asarray(closes, dtype=np.float64)
    if open_values.ndim != 2 or open_values.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign121FormulaError("opens must have shape (n,240)")
    if close_values.shape != open_values.shape:
        raise Campaign121FormulaError("open and close shapes must match")

    reference = open_values[:, 0]
    terminal = close_values[:, -1]
    eligible = (
        np.isfinite(reference)
        & (reference > 0.0)
        & np.isfinite(close_values).all(axis=1)
        & (close_values > 0.0).all(axis=1)
    )
    scores = np.full(len(reference), np.nan, dtype=np.float64)
    tau = np.zeros(len(reference), dtype=np.int16)
    neutral = 0
    upward = 0
    downward = 0
    for row_number in np.flatnonzero(eligible):
        anchor = reference[row_number]
        target = terminal[row_number]
        row = close_values[row_number]
        if target == anchor:
            scores[row_number] = 0.0
            neutral += 1
            continue
        if target > anchor:
            matches = np.flatnonzero(row >= target)
            upward += 1
        else:
            matches = np.flatnonzero(row <= target)
            downward += 1
        if matches.size == 0:
            raise Campaign121FormulaError("terminal close failed its own attainment")
        first = int(matches[0]) + 1
        if not 1 <= first <= SELECTED_BAR_COUNT:
            raise Campaign121FormulaError("attainment index outside frozen support")
        tau[row_number] = first
        scores[row_number] = (SELECTED_BAR_COUNT - first) / POSITION_SPAN

    if (
        np.isfinite(scores[eligible]).sum() != int(eligible.sum())
        or (scores[eligible] < MIN_SCORE).any()
        or (scores[eligible] > MAX_SCORE).any()
    ):
        raise Campaign121FormulaError("score outside frozen range")
    quality = {
        "source_rows": int(len(reference)),
        "eligible_rows": int(eligible.sum()),
        "invalid_anchor_or_close_rows": int((~eligible).sum()),
        "upward_terminal_rows": upward,
        "downward_terminal_rows": downward,
        "neutral_terminal_rows": neutral,
        "directional_first_attainment_rows": upward + downward,
    }
    return scores, eligible, tau, quality
