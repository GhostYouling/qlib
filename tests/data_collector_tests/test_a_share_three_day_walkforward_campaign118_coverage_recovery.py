from __future__ import annotations

from scripts import (
    a_share_three_day_walkforward_campaign118_coverage_recovery as recovery,
)


def test_coverage_recovery_binds_exact_existing_components() -> None:
    assert recovery._sha256(recovery.ORIGINAL_AUDIT_RUNNER) == (
        recovery.ORIGINAL_AUDIT_RUNNER_SHA256
    )
    assert recovery._sha256(recovery.audit.ACTIVATION_BINDING_PATH) == (
        recovery.ACTIVATION_BINDING_SHA256
    )
    assert recovery._sha256(recovery.Path(recovery.recovery.__file__).resolve()) == (
        recovery.RECOVERY_VERIFIER_SHA256
    )


def test_coverage_recovery_preserves_exact_gate_and_no_return_output() -> None:
    gate = recovery.audit.expected_gate()
    assert gate["minimum_median_daily_coverage"] == 0.95
    assert gate["minimum_p05_daily_coverage"] == 0.90
    assert gate["minimum_nonconstant_cross_sectional_sessions"] == 200
    assert recovery.audit.candidate.NUMERIC_COMPARATOR_COUNT == 135
    assert recovery.audit.OUTPUT_PATH.name == "campaign118_coverage_audit.json"
