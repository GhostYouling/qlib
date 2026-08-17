#!/usr/bin/env python3
"""Fail-closed reporting helpers for three-session walk-forward campaigns."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class WalkForwardReportingError(RuntimeError):
    """Raised when a trial cannot be represented without semantic ambiguity."""


def canonical_feature_complexity(entry: Mapping[str, Any]) -> int:
    """Return the number of distinct preregistered features in one trial."""

    feature_set = entry.get("feature_set")
    if not isinstance(feature_set, (list, tuple)) or not feature_set:
        raise WalkForwardReportingError(
            "trial feature_set must be a nonempty list or tuple"
        )
    normalized: list[str] = []
    for value in feature_set:
        if not isinstance(value, str) or not value.strip():
            raise WalkForwardReportingError(
                "trial feature_set must contain only nonempty strings"
            )
        normalized.append(value.strip())
    if len(set(normalized)) != len(normalized):
        raise WalkForwardReportingError(
            "trial feature_set must not contain duplicate factors"
        )
    configuration = (
        entry.get("window_transform_threshold_filter_and_weight_configuration")
        or {}
    )
    kind = configuration.get("kind")
    if kind == "single_factor" and len(normalized) != 1:
        raise WalkForwardReportingError(
            "single_factor trial must contain exactly one feature"
        )
    return len(normalized)


def with_canonical_complexity(
    inherited_decision: Mapping[str, Any],
    entry: Mapping[str, Any],
) -> dict[str, Any]:
    """Copy a survivor decision and replace display complexity from its trial."""

    repaired = dict(inherited_decision)
    repaired["complexity"] = canonical_feature_complexity(entry)
    return repaired
