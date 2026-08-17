#!/usr/bin/env python3
"""Pure Campaign261 normalized Lorenz-Gini amount formula."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_261_no_return_preregistration_20260816.json"
)
PROTOCOL_SHA256 = "25d0304b770c3c11fd5697e49996c250c9d9316692a9b5aa498bb5591fe9ccc6"
FACTOR_NAME = "intraday_amount_lorenz_gini_240m"
FACTOR_DIRECTION = "higher"
PROFILE_POSITIONS = 240
BOUND_TOLERANCE = 1e-12


class Campaign261FormulaError(RuntimeError):
    """Raised when the frozen protocol or supplied array is invalid."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Load and semantically validate the value-free Campaign261 protocol."""

    target = path.expanduser().resolve()
    if target != DEFAULT_PROTOCOL.resolve():
        raise Campaign261FormulaError("Campaign261 protocol path changed")
    if not target.is_file() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign261FormulaError("Campaign261 protocol fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    exact = candidate.get("exact_formula") or {}
    comparison = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign261_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign261_minute_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == FACTOR_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "amount"]
        and grid.get("accepted_rows_required") == 241
        and grid.get("selected_rows") == PROFILE_POSITIONS
        and grid.get("standalone_09_30_preserved_but_not_loaded_for_formula") is True
        and exact.get("score")
        == "sum_i((2i-n-1)*b_(i))/((n-1)*S), with one-indexed i and n=240."
        and exact.get("valid_range_inclusive") == [0.0, 1.0]
        and exact.get("direction") == FACTOR_DIRECTION
        and comparison.get("candidate_appended_complete_definition_count") == 160
        and comparison.get("candidate_appended_complete_definition_order_sha256")
        == "2c431b3c9f9e772f7fdccab2625d671f8a836809710e78af8cb43d6d4e66cc0c"
        and comparison.get("numeric_comparator_count") == 142
        and comparison.get("numeric_comparator_order_sha256")
        == "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
        and boundary.get("campaign261_source_rows_read_before_freeze") is False
        and boundary.get("campaign261_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign261FormulaError("Campaign261 protocol semantics changed")
    return spec


def compute_amount_lorenz_gini(
    amounts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Return finite-sample-normalized Gini scores for 240 amount bars."""

    values = np.asarray(amounts, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != PROFILE_POSITIONS:
        raise Campaign261FormulaError(
            "Campaign261 requires a two-dimensional 240-position array"
        )
    finite = np.isfinite(values).all(axis=1)
    nonnegative = (values >= 0.0).all(axis=1)
    structurally_valid = finite & nonnegative
    totals = np.full(values.shape[0], np.nan, dtype=np.float64)
    if structurally_valid.any():
        totals[structurally_valid] = values[structurally_valid].sum(axis=1)
    positive = structurally_valid & np.isfinite(totals) & (totals > 0.0)
    scores = np.full(values.shape[0], np.nan, dtype=np.float64)
    bound_violations = np.zeros(values.shape[0], dtype=bool)
    if positive.any():
        ordered = np.sort(values[positive], axis=1)
        one_based = np.arange(1, PROFILE_POSITIONS + 1, dtype=np.float64)
        coefficients = 2.0 * one_based - PROFILE_POSITIONS - 1.0
        raw_scores = (ordered @ coefficients) / (
            (PROFILE_POSITIONS - 1.0) * totals[positive]
        )
        canonical = raw_scores.copy()
        canonical[(canonical < 0.0) & (canonical >= -BOUND_TOLERANCE)] = 0.0
        canonical[(canonical > 1.0) & (canonical <= 1.0 + BOUND_TOLERANCE)] = 1.0
        local_bad = ~np.isfinite(canonical) | (canonical < 0.0) | (canonical > 1.0)
        positive_indices = np.flatnonzero(positive)
        bound_violations[positive_indices[local_bad]] = True
        scores[positive_indices[~local_bad]] = canonical[~local_bad]
    eligible = positive & ~bound_violations & np.isfinite(scores)
    scores[~eligible] = np.nan
    quality = {
        "rows": int(values.shape[0]),
        "nonfinite_amount_rows": int((~finite).sum()),
        "negative_amount_rows": int((finite & ~nonnegative).sum()),
        "nonpositive_total_amount_rows": int((structurally_valid & ~positive).sum()),
        "bound_violation_rows": int(bound_violations.sum()),
        "eligible_rows": int(eligible.sum()),
    }
    return scores, eligible, quality


__all__ = [
    "BOUND_TOLERANCE",
    "DEFAULT_PROTOCOL",
    "FACTOR_DIRECTION",
    "FACTOR_NAME",
    "PROFILE_POSITIONS",
    "PROTOCOL_SHA256",
    "Campaign261FormulaError",
    "compute_amount_lorenz_gini",
    "load_protocol",
]
