#!/usr/bin/env python3
"""Pure Campaign151 relative-amount-share clock-center formula.

This module performs no source discovery, provider access, benchmark build,
comparison, price, or return read. The source-bound benchmark and snapshot
builder must be frozen separately before historical minute values are opened.
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
    / "docs/a_share_three_day_walkforward_campaign_151_no_return_preregistration_20260815.json"
)
PROTOCOL_SHA256 = "99c2f95cad4058d004cc26aeecb5e710199ee930320beab97826a674cd6dff8c"
FACTOR_NAME = "intraday_relative_amount_share_clock_center_240m"
FACTOR_DIRECTION = "higher"
PROFILE_POSITIONS = 240
MINIMUM_LEAVE_ONE_OUT_PEERS = 50
ENDPOINT_TOLERANCE = 1e-12
VALID_RANGE = (0.0, 1.0)
CLOCK = np.arange(PROFILE_POSITIONS, dtype=np.float64) / (PROFILE_POSITIONS - 1)


class Campaign151FormulaError(RuntimeError):
    """Raised when the frozen protocol or pure formula input is invalid."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Load and validate the value-free Campaign151 protocol."""

    target = path.expanduser().resolve()
    if target != DEFAULT_PROTOCOL.resolve():
        raise Campaign151FormulaError("Campaign151 protocol path changed")
    if not target.is_file() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign151FormulaError("Campaign151 protocol fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    source = candidate.get("source_grid") or {}
    peer = candidate.get("peer_benchmark_contract") or {}
    exact = candidate.get("exact_formula") or {}
    comparison = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign151_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign151_source_peer_benchmark_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == FACTOR_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "amount"]
        and source.get("selected_rows") == PROFILE_POSITIONS
        and peer.get("leave_one_out") is True
        and peer.get("minimum_other_peers_at_every_clock")
        == MINIMUM_LEAVE_ONE_OUT_PEERS
        and peer.get("peer_aggregator")
        == "arithmetic mean amount at each exact clock over the complete other-peer set"
        and peer.get("every_peer_mean_finite_and_strictly_positive") is True
        and peer.get("own_stock_excluded_from_every_denominator") is True
        and exact.get("clock") == "x_i=i/239 for zero-based i=0,...,239."
        and exact.get("score") == "sum_i(q_i*x_i)."
        and exact.get("endpoint_rule")
        == "Canonicalize only values within 1e-12 of 0 or 1 to the exact endpoint; otherwise require the inclusive [0,1] range."
        and exact.get("valid_range_inclusive") == [0.0, 1.0]
        and comparison.get("candidate_appended_complete_definition_count") == 156
        and comparison.get("candidate_appended_complete_definition_order_sha256")
        == "928e7eff198f44fa3112d7e8ff94571c1ad18b85a1ee50a38f3896baf555847c"
        and comparison.get("numeric_comparator_count") == 142
        and comparison.get("numeric_comparator_order_sha256")
        == "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
        and boundary.get("campaign151_source_rows_read_before_freeze") is False
        and boundary.get("campaign151_peer_benchmark_values_read_before_freeze")
        is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("candidate49_ledgers_changed") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign151FormulaError("Campaign151 protocol semantics changed")
    return spec


def compute_relative_amount_share_clock_center(
    own_amounts: np.ndarray,
    peer_mean_amounts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Compute the frozen score for aligned stock-day amount profiles.

    Parameters are two float-like arrays with shape ``(rows, 240)``. The peer
    array must already exclude the corresponding stock; enforcing peer identity
    and count belongs to the separately frozen source-bound builder.
    """

    own = np.asarray(own_amounts, dtype=np.float64)
    peer = np.asarray(peer_mean_amounts, dtype=np.float64)
    if own.ndim != 2 or peer.ndim != 2 or own.shape != peer.shape:
        raise Campaign151FormulaError(
            "own and peer arrays must have the same two-dimensional shape"
        )
    if own.shape[1] != PROFILE_POSITIONS:
        raise Campaign151FormulaError("Campaign151 requires exactly 240 positions")

    row_count = own.shape[0]
    finite_own = np.isfinite(own).all(axis=1)
    nonnegative_own = (own >= 0.0).all(axis=1)
    finite_peer = np.isfinite(peer).all(axis=1)
    positive_peer = (peer > 0.0).all(axis=1)
    structural = finite_own & nonnegative_own & finite_peer & positive_peer

    relative = np.full_like(own, np.nan)
    if structural.any():
        relative[structural] = own[structural] / peer[structural]
    relative_total = np.full(row_count, np.nan, dtype=np.float64)
    if structural.any():
        relative_total[structural] = relative[structural].sum(axis=1)
    positive_total = structural & np.isfinite(relative_total) & (relative_total > 0.0)

    scores = np.full(row_count, np.nan, dtype=np.float64)
    if positive_total.any():
        weights = relative[positive_total] / relative_total[positive_total, None]
        scores[positive_total] = weights @ CLOCK

    near_zero = positive_total & (np.abs(scores) <= ENDPOINT_TOLERANCE)
    near_one = positive_total & (np.abs(scores - 1.0) <= ENDPOINT_TOLERANCE)
    scores[near_zero] = 0.0
    scores[near_one] = 1.0
    eligible = (
        positive_total
        & np.isfinite(scores)
        & (scores >= VALID_RANGE[0])
        & (scores <= VALID_RANGE[1])
    )
    scores[~eligible] = np.nan

    quality = {
        "rows": int(row_count),
        "nonfinite_own_amount_rows": int((~finite_own).sum()),
        "negative_own_amount_rows": int((finite_own & ~nonnegative_own).sum()),
        "nonfinite_peer_mean_rows": int((~finite_peer).sum()),
        "nonpositive_peer_mean_rows": int((finite_peer & ~positive_peer).sum()),
        "nonpositive_relative_total_rows": int(
            (structural & ~(np.isfinite(relative_total) & (relative_total > 0.0))).sum()
        ),
        "invalid_score_rows": int((positive_total & ~eligible).sum()),
        "eligible_rows": int(eligible.sum()),
    }
    return scores, eligible, quality


__all__ = [
    "CLOCK",
    "DEFAULT_PROTOCOL",
    "ENDPOINT_TOLERANCE",
    "FACTOR_DIRECTION",
    "FACTOR_NAME",
    "MINIMUM_LEAVE_ONE_OUT_PEERS",
    "PROFILE_POSITIONS",
    "PROTOCOL_SHA256",
    "VALID_RANGE",
    "Campaign151FormulaError",
    "compute_relative_amount_share_clock_center",
    "load_protocol",
]
