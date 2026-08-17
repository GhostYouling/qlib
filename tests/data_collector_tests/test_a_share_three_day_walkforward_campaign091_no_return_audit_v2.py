from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign091_no_return_audit_v2 as audit


def test_v2_exposes_binding_validator_without_changing_protocol() -> None:
    assert audit.definitions.bindings is not None
    assert audit.load_protocol()["candidate"]["name"] == audit.FACTOR_NAME
    assert len(audit.definitions.reconstruct_comparisons()) == 120


def test_v2_status_remains_precoverage_and_read_only() -> None:
    result = audit.status()
    assert result["status"] == "activation_binding_absent"
    assert result["audit_count"] == 0
    assert result["coverage_or_capacity_metrics_computed"] is False
    assert result["comparison_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False
    assert result["provider_request_issued"] is False
