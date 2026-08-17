#!/usr/bin/env python3
"""Pure, prevalue implementation of Campaign119's boundary-state entropy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_119_no_return_preregistration_20260813.json"
)
PROTOCOL_SHA256 = "41d10d618c59e1c7f61b075ff1d14d4d6045d763cbdb15f487dcb4a801094f19"
FACTOR_NAME = "intraday_range_boundary_direction_state_entropy_238p"
SCORE_DIRECTION = "higher"
SELECTED_BAR_COUNT = 240
HALF_BAR_COUNT = 120
PAIR_COUNT_PER_HALF = 119
TOTAL_PAIR_COUNT = 238
STATE_COUNT = 9
STATE_LABELS = (
    "(-1,-1)",
    "(-1,0)",
    "(-1,+1)",
    "(0,-1)",
    "(0,0)",
    "(0,+1)",
    "(+1,-1)",
    "(+1,0)",
    "(+1,+1)",
)


class Campaign119FormulaError(ValueError):
    """Raised when frozen Campaign119 formula inputs or bindings change."""


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
        raise Campaign119FormulaError("Campaign119 preregistration fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    formula = candidate.get("exact_formula") or {}
    search = candidate.get("search_space") or {}
    comparisons = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign119_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign119_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == SCORE_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "high", "low"]
        and grid.get("selected_rows") == SELECTED_BAR_COUNT
        and grid.get("morning_rows") == HALF_BAR_COUNT
        and grid.get("afternoon_rows") == HALF_BAR_COUNT
        and grid.get("morning_adjacent_pairs") == PAIR_COUNT_PER_HALF
        and grid.get("afternoon_adjacent_pairs") == PAIR_COUNT_PER_HALF
        and grid.get("total_adjacent_pairs") == TOTAL_PAIR_COUNT
        and grid.get("state_count") == STATE_COUNT
        and grid.get("lunch_transition_pair_included") is False
        and formula.get("ordered_state_alphabet") == list(STATE_LABELS)
        and formula.get("valid_range_inclusive") == [0.0, 1.0]
        and search.get("candidate_count") == 1
        and search.get("direction_count") == 1
        and search.get("state_alphabets")
        == ["nine_exact_joint_low_high_direction_states"]
        and search.get("pair_supports")
        == ["119_morning_plus_119_afternoon_adjacent_pairs"]
        and search.get("comparison_tolerances") == [0.0]
        and search.get("operators") == ["normalized_Shannon_entropy"]
        and search.get(
            "alternate_field_direction_alphabet_pair_support_tolerance_operator_window_threshold_filter_subset_fit_model_transition_or_combination_search"
        )
        is False
        and comparisons.get("numeric_comparator_count") == 136
        and comparisons.get("numeric_comparator_order_sha256")
        == "bb1b850f4277919eb1866e9bfb014577efca6d0f81b184a31b3c202f50eb0282"
        and boundary.get("campaign119_source_rows_read_before_freeze") is False
        and boundary.get("campaign119_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign119_comparator_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign119FormulaError("Campaign119 preregistration semantics changed")
    return spec


def _within_half_differences(values: np.ndarray) -> np.ndarray:
    return np.concatenate(
        (
            np.diff(values[:, :HALF_BAR_COUNT], axis=1),
            np.diff(values[:, HALF_BAR_COUNT:], axis=1),
        ),
        axis=1,
    )


def compute_range_boundary_direction_state_entropy(
    highs: np.ndarray,
    lows: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Compute frozen scores for two matching n-by-240 raw boundary arrays.

    Returns ``(values, eligible, state_counts, state_codes, quality)``. State
    code ``3 * (sign(delta_low) + 1) + sign(delta_high) + 1`` follows the
    preregistered nine-state order. The lunch transition is never constructed.
    """

    high = np.asarray(highs, dtype=np.float64)
    low = np.asarray(lows, dtype=np.float64)
    if (
        high.ndim != 2
        or low.ndim != 2
        or high.shape != low.shape
        or high.shape[1] != SELECTED_BAR_COUNT
    ):
        raise Campaign119FormulaError(
            "Campaign119 requires matching n-by-240 high and low arrays"
        )

    finite = np.isfinite(high).all(axis=1) & np.isfinite(low).all(axis=1)
    positive = (high > 0.0).all(axis=1) & (low > 0.0).all(axis=1)
    ordered = (high >= low).all(axis=1)
    source_valid = finite & positive & ordered

    safe_high = np.where(np.isfinite(high) & (high > 0.0), high, 1.0)
    safe_low = np.where(np.isfinite(low) & (low > 0.0), low, 1.0)
    low_delta = _within_half_differences(safe_low)
    high_delta = _within_half_differences(safe_high)
    low_sign = np.sign(low_delta).astype(np.int8, copy=False)
    high_sign = np.sign(high_delta).astype(np.int8, copy=False)
    state_codes = (
        3 * (low_sign.astype(np.int16) + 1) + high_sign.astype(np.int16) + 1
    ).astype(np.int8, copy=False)

    state_counts = np.stack(
        [(state_codes == code).sum(axis=1) for code in range(STATE_COUNT)],
        axis=1,
    ).astype(np.int16, copy=False)
    recognized = ((state_codes >= 0) & (state_codes < STATE_COUNT)).all(axis=1)
    exact_pair_total = state_counts.sum(axis=1) == TOTAL_PAIR_COUNT
    support_valid = recognized & exact_pair_total

    probabilities = state_counts.astype(np.float64) / float(TOTAL_PAIR_COUNT)
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(
            probabilities > 0.0,
            probabilities * np.log(probabilities),
            0.0,
        )
    scores = -terms.sum(axis=1) / np.log(float(STATE_COUNT))
    finite_score = np.isfinite(scores)
    in_range = (scores >= 0.0) & (scores <= 1.0)
    eligible = source_valid & support_valid & finite_score & in_range
    output = np.full(high.shape[0], np.nan, dtype=np.float64)
    output[eligible] = scores[eligible]

    quality = {
        "rows": int(len(high)),
        "eligible_rows": int(eligible.sum()),
        "nonfinite_high_low_rows": int((~finite).sum()),
        "nonpositive_high_low_rows": int((finite & ~positive).sum()),
        "high_below_low_rows": int((finite & positive & ~ordered).sum()),
        "state_support_mismatch_rows": int((source_valid & ~support_valid).sum()),
        "recognized_state_observations": int(
            ((state_codes >= 0) & (state_codes < STATE_COUNT))[source_valid].sum()
        ),
        "exact_low_tie_pair_observations": int((low_delta == 0.0)[source_valid].sum()),
        "exact_high_tie_pair_observations": int(
            (high_delta == 0.0)[source_valid].sum()
        ),
        "exact_joint_tie_pair_observations": int(
            ((low_delta == 0.0) & (high_delta == 0.0))[source_valid].sum()
        ),
        "zero_width_bar_observations": int((high == low)[source_valid].sum()),
        "nonfinite_or_out_of_range_score_rows": int(
            (source_valid & support_valid & (~finite_score | ~in_range)).sum()
        ),
    }
    return output, eligible, state_counts, state_codes, quality


__all__ = [
    "Campaign119FormulaError",
    "FACTOR_NAME",
    "HALF_BAR_COUNT",
    "PAIR_COUNT_PER_HALF",
    "PROTOCOL_PATH",
    "PROTOCOL_SHA256",
    "SCORE_DIRECTION",
    "SELECTED_BAR_COUNT",
    "STATE_COUNT",
    "STATE_LABELS",
    "TOTAL_PAIR_COUNT",
    "compute_range_boundary_direction_state_entropy",
    "load_protocol",
]
