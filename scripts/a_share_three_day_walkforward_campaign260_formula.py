#!/usr/bin/env python3
"""Pure Campaign260 amount-clock third-central-moment formula."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_260_no_return_preregistration_20260816.json"
)
PROTOCOL_SHA256 = "93e3ff36fd657d167e458d33471f0bbcd5dfd471f7d6b77a24822f670923e181"
FACTOR_NAME = "intraday_amount_clock_third_central_moment_240m"
FACTOR_DIRECTION = "higher"
PROFILE_POSITIONS = 240
BOUND_TOLERANCE = 1e-12


class Campaign260FormulaError(RuntimeError):
    """Raised when the frozen protocol or supplied array is invalid."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Load and semantically validate the value-free Campaign260 protocol."""

    target = path.expanduser().resolve()
    if target != DEFAULT_PROTOCOL.resolve():
        raise Campaign260FormulaError("Campaign260 protocol path changed")
    if not target.is_file() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign260FormulaError("Campaign260 protocol fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    exact = candidate.get("exact_formula") or {}
    comparison = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign260_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign260_minute_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == FACTOR_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "amount"]
        and grid.get("accepted_rows_required") == 241
        and grid.get("selected_rows") == PROFILE_POSITIONS
        and grid.get("standalone_09_30_preserved_but_not_loaded_for_formula") is True
        and exact.get("score") == "0.5+3*sqrt(3)*m3."
        and exact.get("valid_range_inclusive") == [0.0, 1.0]
        and exact.get("direction") == FACTOR_DIRECTION
        and comparison.get("candidate_appended_complete_definition_count") == 159
        and comparison.get("candidate_appended_complete_definition_order_sha256")
        == "0a83a9c82f8ee0ebb9f57da3214e058e6772c8b7648da181b24a93d10e3de3f8"
        and comparison.get("numeric_comparator_count") == 142
        and comparison.get("numeric_comparator_order_sha256")
        == "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
        and boundary.get("campaign260_source_rows_read_before_freeze") is False
        and boundary.get(
            "campaign260_candidate_values_computed_or_read_before_freeze"
        )
        is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign260FormulaError("Campaign260 protocol semantics changed")
    return spec


def compute_amount_clock_third_central_moment(
    amounts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Return the bounded signed third central moment for each 240-bar row."""

    values = np.asarray(amounts, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != PROFILE_POSITIONS:
        raise Campaign260FormulaError(
            "Campaign260 requires a two-dimensional 240-position array"
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
        selected = values[positive]
        weights = selected / totals[positive, None]
        clock = np.arange(PROFILE_POSITIONS, dtype=np.float64) / (
            PROFILE_POSITIONS - 1
        )
        centers = weights @ clock
        third = np.sum(weights * (clock[None, :] - centers[:, None]) ** 3, axis=1)
        raw_scores = 0.5 + 3.0 * np.sqrt(3.0) * third
        canonical = raw_scores.copy()
        canonical[(canonical < 0.0) & (canonical >= -BOUND_TOLERANCE)] = 0.0
        canonical[(canonical > 1.0) & (canonical <= 1.0 + BOUND_TOLERANCE)] = 1.0
        local_bad = (
            ~np.isfinite(canonical) | (canonical < 0.0) | (canonical > 1.0)
        )
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
    "Campaign260FormulaError",
    "compute_amount_clock_third_central_moment",
    "load_protocol",
]
