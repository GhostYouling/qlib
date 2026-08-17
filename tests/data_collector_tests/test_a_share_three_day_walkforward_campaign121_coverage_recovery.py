from __future__ import annotations

import copy

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign121_coverage_recovery as recovery,
)


def test_snapshot_verification_result_is_frozen_and_complete() -> None:
    record = recovery.load_snapshot_verification()
    assert record["snapshot"]["partitions"] == 33015
    assert record["snapshot"]["eligible_rows"] == 7724498
    assert record["factor"]["truthful_position_lattice_denominator"] == 239


def test_snapshot_verification_mutation_fails_closed() -> None:
    record = copy.deepcopy(recovery.load_snapshot_verification())
    record["snapshot"]["rows"] -= 1
    with pytest.raises(recovery.Campaign121CoverageRecoveryError):
        recovery.validate_snapshot_verification(record)


def test_base_plan_is_ready_without_reading_candidate_values() -> None:
    plan = recovery.audit.build_plan()
    assert plan["ready"] is True
    assert plan["candidate_values_read"] is False
    assert plan["comparator_values_read"] is False


def test_original_gate_and_output_are_unchanged() -> None:
    gate = recovery.audit.expected_gate()
    assert gate["minimum_median_daily_coverage"] == 0.95
    assert gate["minimum_nonconstant_cross_sectional_sessions"] == 200
    assert recovery.audit.OUTPUT_PATH.exists() is False
