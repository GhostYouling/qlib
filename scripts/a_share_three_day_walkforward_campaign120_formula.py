#!/usr/bin/env python3
"""Pure frozen formula for Campaign120 direction-dictionary novelty."""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


SELECTED_BAR_COUNT = 240
HALF_BAR_COUNT = 120
SYMBOL_COUNT_PER_HALF = 119
TOTAL_SYMBOL_COUNT = 238
ALPHABET = (-1, 0, 1)
MIN_SCORE = 2
MAX_SCORE = 238
REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_120_no_return_preregistration_20260814.json"
)
PROTOCOL_SHA256 = "eb23880c27d2e0a575d0f28218794872cb66bf681940bdb790f1bee865020a6e"
FACTOR_NAME = "intraday_return_direction_dictionary_phrase_count_238s"
SCORE_DIRECTION = "higher"


class Campaign120FormulaError(ValueError):
    """Raised when inputs violate the frozen formula contract."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    """Validate the frozen protocol without opening a historical value file."""

    target = path.expanduser().resolve()
    if target != PROTOCOL_PATH.resolve() or _sha256(target) != PROTOCOL_SHA256:
        raise Campaign120FormulaError("Campaign120 preregistration fingerprint changed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    exact = candidate.get("exact_formula") or {}
    search = candidate.get("search_space") or {}
    comparisons = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign120_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign120_source_candidate_comparator_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == SCORE_DIRECTION
        and candidate.get("source_projection")
        == ["datetime", "symbol", "provider", "close"]
        and grid.get("selected_rows") == SELECTED_BAR_COUNT
        and grid.get("direction_symbols_per_half") == SYMBOL_COUNT_PER_HALF
        and grid.get("total_direction_symbols") == TOTAL_SYMBOL_COUNT
        and grid.get("lunch_return_or_phrase_included") is False
        and exact.get("alphabet_order") == list(ALPHABET)
        and exact.get("normalization") == "none"
        and exact.get("valid_range_inclusive") == [MIN_SCORE, MAX_SCORE]
        and search.get("candidate_count") == 1
        and search.get("direction_count") == 1
        and search.get("parser_count") == 1
        and search.get(
            "alternate_parser_normalization_alphabet_window_direction_threshold_filter_subset_fit_model_or_combination_search"
        )
        is False
        and comparisons.get("numeric_comparator_count") == 137
        and comparisons.get("numeric_comparator_order_sha256")
        == "aaac5973c5f93e4cb6275f0b5ae92bc04ce1f7968b100785d8763565fa095621"
        and boundary.get("campaign120_source_rows_read_before_freeze") is False
        and boundary.get("campaign120_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign120_comparator_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign120FormulaError("Campaign120 preregistration semantics changed")
    return spec


def dictionary_phrase_count(symbols: Sequence[int] | np.ndarray[Any, Any]) -> int:
    """Parse one fixed 119-symbol half with the frozen incremental dictionary."""

    sequence = tuple(int(item) for item in symbols)
    if len(sequence) != SYMBOL_COUNT_PER_HALF:
        raise Campaign120FormulaError("each half must contain exactly 119 symbols")
    if any(item not in ALPHABET for item in sequence):
        raise Campaign120FormulaError("symbols must use the exact ternary alphabet")

    dictionary: set[tuple[int, ...]] = set()
    cursor = 0
    phrase_count = 0
    while cursor < len(sequence):
        longest = 0
        remaining = len(sequence) - cursor
        for length in range(1, remaining + 1):
            if sequence[cursor : cursor + length] in dictionary:
                longest = length
            else:
                break
        if cursor + longest < len(sequence):
            phrase = sequence[cursor : cursor + longest + 1]
            if phrase in dictionary:
                raise Campaign120FormulaError("parser failed shortest-unseen invariant")
            dictionary.add(phrase)
            cursor += longest + 1
        else:
            cursor = len(sequence)
        phrase_count += 1

    if not MIN_SCORE // 2 <= phrase_count <= MAX_SCORE // 2:
        raise Campaign120FormulaError("half phrase count outside conservative range")
    return phrase_count


def compute_direction_dictionary_phrase_count(
    closes: np.ndarray[Any, Any],
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any], dict[str, int]]:
    """Compute Campaign120 scores for an ``n x 240`` close matrix."""

    values = np.asarray(closes, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign120FormulaError("closes must have shape (n,240)")
    eligible = np.isfinite(values).all(axis=1) & (values > 0.0).all(axis=1)
    scores = np.full(values.shape[0], np.nan, dtype=np.float64)
    symbol_observations = 0
    zero_symbol_observations = 0
    for row_number in np.flatnonzero(eligible):
        row = values[row_number]
        morning = np.sign(np.diff(row[:HALF_BAR_COUNT])).astype(np.int8)
        afternoon = np.sign(np.diff(row[HALF_BAR_COUNT:])).astype(np.int8)
        symbols = np.concatenate((morning, afternoon))
        if symbols.size != TOTAL_SYMBOL_COUNT or not np.isin(symbols, ALPHABET).all():
            raise Campaign120FormulaError("direction-symbol support changed")
        score = dictionary_phrase_count(morning) + dictionary_phrase_count(afternoon)
        if not MIN_SCORE <= score <= MAX_SCORE:
            raise Campaign120FormulaError("score outside conservative range")
        scores[row_number] = float(score)
        symbol_observations += int(symbols.size)
        zero_symbol_observations += int(np.count_nonzero(symbols == 0))
    quality = {
        "source_rows": int(values.shape[0]),
        "eligible_rows": int(eligible.sum()),
        "invalid_close_rows": int((~eligible).sum()),
        "recognized_direction_symbol_observations": symbol_observations,
        "exact_zero_direction_symbol_observations": zero_symbol_observations,
    }
    return scores, eligible, quality
