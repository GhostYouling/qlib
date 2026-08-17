#!/usr/bin/env python3
"""Pure, prevalue implementation of Campaign117's frozen amount-order entropy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_117_no_return_preregistration_20260813.json"
)
PROTOCOL_SHA256 = "01cda2c9ec8646ca3d8db86f20e2720514c26c0a6a6044faeac01e6420f9fcb7"
FACTOR_NAME = "intraday_amount_weak_order_entropy_236t"
SCORE_DIRECTION = "higher"
SELECTED_BAR_COUNT = 240
HALF_BAR_COUNT = 120
TRIPLES_PER_HALF = 118
TOTAL_TRIPLE_COUNT = 236
WEAK_ORDER_STATE_COUNT = 13

# Base-3 encodings of the 13 transitive comparison keys
# (cmp(a0,a1), cmp(a0,a2), cmp(a1,a2)), with cmp in {-1, 0, +1}.
WEAK_ORDER_CODES = np.asarray(
    [0, 1, 2, 5, 8, 9, 13, 17, 18, 21, 24, 25, 26],
    dtype=np.int8,
)


class Campaign117FormulaError(ValueError):
    """Raised when frozen Campaign117 formula inputs or bindings change."""


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
        raise Campaign117FormulaError("Campaign117 preregistration fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    formula = candidate.get("exact_formula") or {}
    search = candidate.get("search_space") or {}
    comparisons = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign117_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign117_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == SCORE_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "amount"]
        and grid.get("selected_rows") == SELECTED_BAR_COUNT
        and grid.get("rows_per_half") == HALF_BAR_COUNT
        and grid.get("overlapping_triples_per_half") == TRIPLES_PER_HALF
        and grid.get("total_triples") == TOTAL_TRIPLE_COUNT
        and grid.get("lunch_transition_excluded") is True
        and formula.get("valid_range_inclusive") == [0.0, 1.0]
        and search.get("candidate_count") == 1
        and search.get("direction_count") == 1
        and search.get("tuple_lengths") == [3]
        and search.get("lags") == [1]
        and search.get("operators") == ["normalized_Shannon_entropy"]
        and search.get(
            "alternate_field_direction_tuple_lag_alphabet_tie_rule_operator_window_threshold_filter_subset_fit_model_or_combination_search"
        )
        is False
        and comparisons.get("numeric_comparator_count") == 134
        and comparisons.get("numeric_comparator_order_sha256")
        == "31d788db467f558a0ac538315343090f1b3ad4cb27a26136a49ebaa88b2fdbf2"
        and boundary.get("campaign117_source_rows_read_before_freeze") is False
        and boundary.get("campaign117_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign117_comparator_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign117FormulaError("Campaign117 preregistration semantics changed")
    return spec


def compute_amount_weak_order_entropy(
    amounts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Compute the exact frozen score for one or more n-by-240 stock-days.

    Returns ``(values, eligible, state_counts, state_codes, quality)``. Morning
    and afternoon triples are constructed independently, so lunch is excluded.
    """

    values = np.asarray(amounts, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign117FormulaError("Campaign117 requires an n-by-240 amount array")

    finite = np.isfinite(values).all(axis=1)
    nonnegative = (values >= 0.0).all(axis=1)
    positive_total = np.where(np.isfinite(values), values, 0.0).sum(axis=1) > 0.0
    source_valid = finite & nonnegative & positive_total
    safe = np.where(np.isfinite(values) & (values >= 0.0), values, 0.0)

    triples = np.concatenate(
        (
            np.stack((safe[:, :118], safe[:, 1:119], safe[:, 2:120]), axis=2),
            np.stack(
                (safe[:, 120:238], safe[:, 121:239], safe[:, 122:240]),
                axis=2,
            ),
        ),
        axis=1,
    )
    if triples.shape[1:] != (TOTAL_TRIPLE_COUNT, 3):
        raise Campaign117FormulaError("Campaign117 fixed triple support changed")

    first, second, third = triples[:, :, 0], triples[:, :, 1], triples[:, :, 2]
    comparisons = np.stack(
        (
            np.sign(first - second),
            np.sign(first - third),
            np.sign(second - third),
        ),
        axis=2,
    ).astype(np.int8)
    codes = (
        (comparisons[:, :, 0] + 1) * 9
        + (comparisons[:, :, 1] + 1) * 3
        + comparisons[:, :, 2]
        + 1
    ).astype(np.int8)
    counts = np.stack(
        [(codes == code).sum(axis=1) for code in WEAK_ORDER_CODES], axis=1
    )
    recognized = counts.sum(axis=1)
    recognized_all = recognized == TOTAL_TRIPLE_COUNT
    probabilities = counts.astype(np.float64) / float(TOTAL_TRIPLE_COUNT)
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(
            probabilities > 0.0,
            probabilities * np.log(probabilities),
            0.0,
        )
    scores = -terms.sum(axis=1) / np.log(float(WEAK_ORDER_STATE_COUNT))
    finite_score = np.isfinite(scores)
    in_range = (scores >= 0.0) & (scores <= 1.0)
    eligible = source_valid & recognized_all & finite_score & in_range
    output = np.full(values.shape[0], np.nan, dtype=np.float64)
    output[eligible] = scores[eligible]
    quality = {
        "rows": int(len(values)),
        "eligible_rows": int(eligible.sum()),
        "nonfinite_amount_rows": int((~finite).sum()),
        "negative_amount_rows": int((finite & ~nonnegative).sum()),
        "nonpositive_total_amount_rows": int(
            (finite & nonnegative & ~positive_total).sum()
        ),
        "state_count_mismatch_rows": int((source_valid & ~recognized_all).sum()),
        "exact_tie_triple_observations": int(
            ((comparisons == 0).any(axis=2) & source_valid[:, None]).sum()
        ),
        "recognized_state_observations": int(recognized[source_valid].sum()),
        "nonfinite_or_out_of_range_score_rows": int(
            (source_valid & recognized_all & (~finite_score | ~in_range)).sum()
        ),
    }
    return output, eligible, counts, codes, quality


__all__ = [
    "Campaign117FormulaError",
    "FACTOR_NAME",
    "HALF_BAR_COUNT",
    "PROTOCOL_PATH",
    "PROTOCOL_SHA256",
    "SCORE_DIRECTION",
    "SELECTED_BAR_COUNT",
    "TOTAL_TRIPLE_COUNT",
    "TRIPLES_PER_HALF",
    "WEAK_ORDER_CODES",
    "WEAK_ORDER_STATE_COUNT",
    "compute_amount_weak_order_entropy",
    "load_protocol",
]
