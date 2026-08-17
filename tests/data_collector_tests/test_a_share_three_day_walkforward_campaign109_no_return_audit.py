from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign109_no_return_audit as audit


def test_campaign109_audit_protocol_is_coverage_first_all_132() -> None:
    spec = audit.load_protocol()
    gates = spec["ordered_no_return_gates"]
    assert gates["coverage_and_capacity_before_comparison_values"][
        "minimum_median_coverage"
    ] == 0.95
    assert gates["uniqueness_after_coverage_only"][
        "maximum_allowed_absolute_median_daily_rank_correlation"
    ] == 0.8
    assert len(gates["uniqueness_after_coverage_only"]["comparison_factors"]) == 132
    assert audit.EXPECTED_COMPARISON_COUNT == 132


def test_campaign109_audit_candidate_range_and_boundary() -> None:
    spec = audit.candidate.load_protocol()
    assert spec["candidate"]["valid_range"] == [-1.0, 1.0]
    assert spec["research_boundary"]["campaign109_comparison_values_read_before_freeze"] is False
    assert spec["research_boundary"]["historical_forward_returns_read_before_freeze"] is False
    assert spec["research_boundary"]["provider_request_issued"] is False

