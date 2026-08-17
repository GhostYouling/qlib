from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign110_no_return_audit as audit


def test_campaign110_audit_protocol_is_coverage_first_all_133() -> None:
    spec = audit.load_protocol()
    gates = spec["ordered_no_return_gates"]
    assert gates["coverage_and_capacity_before_comparison_values"][
        "minimum_median_coverage"
    ] == 0.95
    uniqueness = gates["uniqueness_after_coverage_only"]
    assert uniqueness[
        "maximum_allowed_absolute_median_daily_rank_correlation"
    ] == 0.8
    assert len(uniqueness["comparison_factors"]) == 133
    assert uniqueness["comparison_factors"][-1]["name"] == audit.c109.FACTOR_NAME
    assert audit.EXPECTED_COMPARISON_COUNT == 133


def test_campaign110_audit_candidate_range_and_boundary() -> None:
    spec = audit.candidate.load_protocol()
    assert spec["candidate"]["valid_range"] == [-1.0, 1.0]
    assert (
        spec["research_boundary"][
            "campaign110_comparison_values_read_before_freeze"
        ]
        is False
    )
    assert spec["research_boundary"]["historical_forward_returns_read_before_freeze"] is False
    assert spec["research_boundary"]["provider_request_issued"] is False


def test_campaign110_comparator_loader_fails_before_coverage() -> None:
    with pytest.raises(
        audit.Campaign110NoReturnAuditError,
        match="before Campaign110 coverage pass",
    ):
        audit._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": False},
            candidate_keys=np.array([], dtype=np.int64),
            candidate_values=np.array([], dtype=np.float64),
            gate={},
            comparison_engine=object(),
        )


def test_campaign110_comparator_133_is_bound_as_raw_minus_one_to_one() -> None:
    assert audit.C109_MANIFEST_SHA256 == (
        "b212eac0921bbca2c3a84c6eceb7f6741939c52ccb96a21e3897d1533c8b6aba"
    )
    assert audit.C109_DATASET_SHA256 == (
        "f222c80e80acb9872cc7e29a0fc89ab37e51bc1ee02f40f19f683c3757fcdb90"
    )
    registrations = audit.adapter.register_raw_factor_range(
        {}, factor=audit.c109.FACTOR_NAME, value_range=(-1.0, 1.0)
    )
    assert registrations[audit.c109.FACTOR_NAME] == (-1.0, 1.0)
