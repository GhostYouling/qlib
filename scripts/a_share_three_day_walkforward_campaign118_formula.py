#!/usr/bin/env python3
"""Pure, prevalue implementation of Campaign118's frozen event-spacing entropy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_118_no_return_preregistration_20260813.json"
)
PROTOCOL_SHA256 = "f17d9feff0a812d7b7dad06cd24b2891e0d76d0a67e2b7e98dba4f74ae1d31ec"
FACTOR_NAME = "intraday_top_decile_amount_event_spacing_entropy_25g"
SCORE_DIRECTION = "higher"
SELECTED_BAR_COUNT = 240
EVENT_COUNT = 24
GAP_COUNT = 25
NON_EVENT_COUNT = 216


class Campaign118FormulaError(ValueError):
    """Raised when frozen Campaign118 formula inputs or bindings change."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Load the exact preregistration without opening a historical value file."""

    target = path.expanduser().resolve()
    if target != PROTOCOL_PATH.resolve() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign118FormulaError("Campaign118 preregistration fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    formula = candidate.get("exact_formula") or {}
    search = candidate.get("search_space") or {}
    comparisons = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign118_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign118_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == SCORE_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "amount"]
        and grid.get("selected_rows") == SELECTED_BAR_COUNT
        and grid.get("event_count") == EVENT_COUNT
        and grid.get("gap_count") == GAP_COUNT
        and grid.get("non_event_count") == NON_EVENT_COUNT
        and grid.get("lunch_is_one_adjacent_selected_clock_step") is True
        and formula.get("valid_range_inclusive") == [0.0, 1.0]
        and search.get("candidate_count") == 1
        and search.get("direction_count") == 1
        and search.get("event_counts") == [EVENT_COUNT]
        and search.get("event_fractions") == [0.1]
        and search.get("tie_rules") == ["descending_amount_then_ascending_clock_index"]
        and search.get("gap_definitions")
        == ["25_edge_and_inter_event_non_event_counts"]
        and search.get("operators") == ["normalized_Shannon_entropy"]
        and search.get(
            "alternate_field_direction_event_count_fraction_tie_rule_gap_definition_operator_window_threshold_filter_subset_fit_model_or_combination_search"
        )
        is False
        and comparisons.get("numeric_comparator_count") == 135
        and comparisons.get("numeric_comparator_order_sha256")
        == "50323aed7e13a7f0241677beefda6c847482844eea68cf51cb92c833cd316322"
        and boundary.get("campaign118_source_rows_read_before_freeze") is False
        and boundary.get("campaign118_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign118_comparator_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign118FormulaError("Campaign118 preregistration semantics changed")
    return spec


def compute_top_decile_amount_event_spacing_entropy(
    amounts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Compute frozen scores for an n-by-240 amount array.

    Returns ``(values, eligible, event_indices, gap_counts, quality)``. Stable
    descending sorting makes the earlier clock index win every exact amount tie.
    """

    values = np.asarray(amounts, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign118FormulaError("Campaign118 requires an n-by-240 amount array")

    finite = np.isfinite(values).all(axis=1)
    nonnegative = (values >= 0.0).all(axis=1)
    safe = np.where(np.isfinite(values) & (values >= 0.0), values, 0.0)
    positive_total = safe.sum(axis=1) > 0.0
    source_valid = finite & nonnegative & positive_total

    descending_order = np.argsort(-safe, axis=1, kind="stable")
    selected_by_rank = descending_order[:, :EVENT_COUNT]
    event_indices = np.sort(selected_by_rank, axis=1).astype(np.int16, copy=False)

    gaps = np.empty((len(values), GAP_COUNT), dtype=np.int16)
    gaps[:, 0] = event_indices[:, 0]
    gaps[:, 1:EVENT_COUNT] = np.diff(event_indices, axis=1) - 1
    gaps[:, EVENT_COUNT] = SELECTED_BAR_COUNT - 1 - event_indices[:, -1]

    distinct_events = (np.diff(event_indices, axis=1) > 0).all(axis=1)
    nonnegative_gaps = (gaps >= 0).all(axis=1)
    exact_gap_total = gaps.sum(axis=1) == NON_EVENT_COUNT
    support_valid = distinct_events & nonnegative_gaps & exact_gap_total

    probabilities = gaps.astype(np.float64) / float(NON_EVENT_COUNT)
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(
            probabilities > 0.0,
            probabilities * np.log(probabilities),
            0.0,
        )
    scores = -terms.sum(axis=1) / np.log(float(GAP_COUNT))
    finite_score = np.isfinite(scores)
    in_range = (scores >= 0.0) & (scores <= 1.0)
    eligible = source_valid & support_valid & finite_score & in_range
    output = np.full(values.shape[0], np.nan, dtype=np.float64)
    output[eligible] = scores[eligible]

    ranked_amounts = np.take_along_axis(safe, descending_order, axis=1)
    boundary_ties = ranked_amounts[:, EVENT_COUNT - 1] == ranked_amounts[:, EVENT_COUNT]
    selected_amounts = np.take_along_axis(safe, selected_by_rank, axis=1)
    quality = {
        "rows": int(len(values)),
        "eligible_rows": int(eligible.sum()),
        "nonfinite_amount_rows": int((~finite).sum()),
        "negative_amount_rows": int((finite & ~nonnegative).sum()),
        "nonpositive_total_amount_rows": int(
            (finite & nonnegative & ~positive_total).sum()
        ),
        "event_or_gap_support_mismatch_rows": int(
            (source_valid & ~support_valid).sum()
        ),
        "exact_top24_boundary_tie_rows": int((source_valid & boundary_ties).sum()),
        "zero_amount_selected_observations": int(
            ((selected_amounts == 0.0) & source_valid[:, None]).sum()
        ),
        "zero_gap_observations": int(((gaps == 0) & source_valid[:, None]).sum()),
        "nonfinite_or_out_of_range_score_rows": int(
            (source_valid & support_valid & (~finite_score | ~in_range)).sum()
        ),
    }
    return output, eligible, event_indices, gaps, quality


__all__ = [
    "Campaign118FormulaError",
    "EVENT_COUNT",
    "FACTOR_NAME",
    "GAP_COUNT",
    "NON_EVENT_COUNT",
    "PROTOCOL_PATH",
    "PROTOCOL_SHA256",
    "SCORE_DIRECTION",
    "SELECTED_BAR_COUNT",
    "compute_top_decile_amount_event_spacing_entropy",
    "load_protocol",
]
