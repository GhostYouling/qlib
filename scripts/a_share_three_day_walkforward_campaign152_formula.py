#!/usr/bin/env python3
"""Pure Campaign152 session-total-amount magnitude formula.

This module performs no source discovery, provider access, comparison, price,
or return read.  It validates only the immutable pre-value protocol and arrays
explicitly supplied by the caller.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_152_no_return_preregistration_20260815.json"
)
PROTOCOL_SHA256 = "026344726b68729336ce68a4b039c91c5faeecec6586929a804f9fb3eb465250"
FACTOR_NAME = "intraday_session_total_amount_magnitude_240m"
FACTOR_DIRECTION = "higher"
PROFILE_POSITIONS = 240


class Campaign152FormulaError(RuntimeError):
    """Raised when the frozen protocol or pure formula input is invalid."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Load and semantically validate the value-free Campaign152 protocol."""

    target = path.expanduser().resolve()
    if target != DEFAULT_PROTOCOL.resolve():
        raise Campaign152FormulaError("Campaign152 protocol path changed")
    if not target.is_file() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign152FormulaError("Campaign152 protocol fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    exact = candidate.get("exact_formula") or {}
    comparison = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign152_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign152_minute_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == FACTOR_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "amount"]
        and grid.get("accepted_rows_required") == 241
        and grid.get("selected_rows") == PROFILE_POSITIONS
        and grid.get("standalone_09_30_preserved_but_not_loaded_for_formula") is True
        and exact.get("total")
        == "S=sum_i(a_i); require S finite and strictly positive."
        and exact.get("score") == "log1p(S) using the natural logarithm."
        and exact.get("direction") == FACTOR_DIRECTION
        and exact.get("valid_range") == "finite and strictly positive"
        and comparison.get("candidate_appended_complete_definition_count") == 157
        and comparison.get("candidate_appended_complete_definition_order_sha256")
        == "c39bb6ca969b5f469a9377a5b5ca743405cec9d8511297ed6a1c44188ef40b82"
        and comparison.get("numeric_comparator_count") == 142
        and comparison.get("numeric_comparator_order_sha256")
        == "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
        and boundary.get("campaign152_source_rows_read_before_freeze") is False
        and boundary.get("campaign152_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign152FormulaError("Campaign152 protocol semantics changed")
    return spec


def compute_session_total_amount_magnitude(
    amounts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Return ``log1p`` of each row's exact 240-bar raw CNY amount sum."""

    values = np.asarray(amounts, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != PROFILE_POSITIONS:
        raise Campaign152FormulaError(
            "Campaign152 requires a two-dimensional 240-position array"
        )
    finite = np.isfinite(values).all(axis=1)
    nonnegative = (values >= 0.0).all(axis=1)
    structurally_valid = finite & nonnegative
    totals = np.full(values.shape[0], np.nan, dtype=np.float64)
    if structurally_valid.any():
        totals[structurally_valid] = values[structurally_valid].sum(axis=1)
    eligible = structurally_valid & np.isfinite(totals) & (totals > 0.0)
    scores = np.full(values.shape[0], np.nan, dtype=np.float64)
    if eligible.any():
        scores[eligible] = np.log1p(totals[eligible])
    eligible &= np.isfinite(scores) & (scores > 0.0)
    scores[~eligible] = np.nan
    quality = {
        "rows": int(values.shape[0]),
        "nonfinite_amount_rows": int((~finite).sum()),
        "negative_amount_rows": int((finite & ~nonnegative).sum()),
        "nonpositive_total_amount_rows": int(
            (structurally_valid & ~(np.isfinite(totals) & (totals > 0.0))).sum()
        ),
        "eligible_rows": int(eligible.sum()),
    }
    return scores, eligible, quality


__all__ = [
    "DEFAULT_PROTOCOL",
    "FACTOR_DIRECTION",
    "FACTOR_NAME",
    "PROFILE_POSITIONS",
    "PROTOCOL_SHA256",
    "Campaign152FormulaError",
    "compute_session_total_amount_magnitude",
    "load_protocol",
]
