#!/usr/bin/env python3
"""Recover the Campaign107 adapter contract from append-only skill drift only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import (
    a_share_three_day_walkforward_campaign107_comparator_adapter as adapter,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = adapter.CONTRACT.resolve()
CONTRACT_SHA256 = "6b8ac9484b3e46ebd7bd0857eb99e24bba4ede3c8781891d0b150de0cae19962"
SKILL_PATH = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
HISTORICAL_SKILL_SHA256 = (
    "8e541bf7c5d77f27a0b0562bd1235878b46c1074c53d79f64a21c417a68ad470"
)
CURRENT_SKILL_SHA256 = (
    "5f05f0986c78355b75fa397545aed7fc7d474892849c475e3869dbddf09fdcad"
)
FAILED_POINTER = "/authoritative_inputs/manage_qlib_a_share_data_skill"


class Campaign117AdapterBindingRecoveryError(RuntimeError):
    """Fail closed unless skill drift is the sole historical binding mismatch."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    target = path.expanduser().resolve()
    if (
        target != CONTRACT_PATH
        or not target.is_file()
        or _sha256(target) != CONTRACT_SHA256
        or _sha256(SKILL_PATH) != CURRENT_SKILL_SHA256
    ):
        raise Campaign117AdapterBindingRecoveryError(
            "Campaign107 recovery authority changed"
        )
    report = bindings.validate_record(target, data_root=adapter.DEFAULT_DATA_ROOT)
    failed = list(report.get("failed_bindings") or [])
    results = list(report.get("results") or [])
    if not (
        report.get("binding_count") == len(results) == 6
        and report.get("passed_binding_count") == 5
        and report.get("failed_binding_count") == len(failed) == 1
        and all(
            item.get("passed") is True or item.get("json_pointer") == FAILED_POINTER
            for item in results
        )
        and failed[0].get("json_pointer") == FAILED_POINTER
        and failed[0].get("expected_sha256") == HISTORICAL_SKILL_SHA256
        and failed[0].get("observed_sha256") == CURRENT_SKILL_SHA256
        and failed[0].get("exists") is True
        and failed[0].get("passed") is False
    ):
        raise Campaign117AdapterBindingRecoveryError(
            "skill drift is not the sole adapter binding mismatch"
        )
    record = json.loads(target.read_text(encoding="utf-8"))
    semantics = record.get("frozen_adapter_semantics") or {}
    registration = semantics.get("range_registration") or {}
    source = semantics.get("source_frame") or {}
    alignment = semantics.get("alignment") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign107_raw_comparator_adapter_contract"
        and record.get("status")
        == "frozen_before_campaign107_candidate_comparator_daily_price_or_return_values"
        and registration.get(
            "every_raw_numeric_comparator_requires_an_explicit_finite_lower_upper_pair"
        )
        is True
        and registration.get("lower_may_equal_upper") is False
        and registration.get("existing_identical_registration_is_idempotent") is True
        and registration.get("existing_conflicting_registration_fails_closed") is True
        and source.get("nan_is_a_valid_missing_comparator_value") is True
        and source.get("positive_or_negative_infinity_is_invalid") is True
        and source.get("nan_may_not_be_filled_ranked_or_dropped_before_alignment")
        is True
        and alignment.get("aligned_nan_must_remain_nan") is True
        and alignment.get(
            "pairwise_overlap_is_handled_only_by_the_frozen_correlation_gate"
        )
        is True
        and boundary.get("campaign107_source_rows_read") is False
        and boundary.get("campaign107_candidate_values_read") is False
        and boundary.get("campaign107_comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign117AdapterBindingRecoveryError(
            "Campaign107 adapter semantics changed"
        )
    return record


__all__ = [
    "CURRENT_SKILL_SHA256",
    "Campaign117AdapterBindingRecoveryError",
    "validate_contract",
]
