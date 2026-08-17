from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign092_no_return_audit as audit


def test_campaign092_no_return_static_contract() -> None:
    spec = audit.load_protocol()
    comparisons = audit.definitions.reconstruct_comparisons()
    complete = audit.definitions.reconstruct_complete_definitions()
    assert spec["candidate"]["name"] == audit.FACTOR_NAME
    assert len(comparisons) == audit.EXPECTED_COMPARISON_COUNT == 121
    assert len(complete) == audit.EXPECTED_COMPLETE_DEFINITION_COUNT == 123
    assert comparisons[-1] == {
        "name": "intraday_directional_range_mass_imbalance_240m",
        "score_direction": "higher",
    }
    assert complete[-1] == comparisons[-1]


def test_campaign092_candidate_snapshot_binding_verifies() -> None:
    result = audit.verify_candidate_snapshot()
    assert result["status"] == "verified"
    assert result["rows"] == audit.EXPECTED_ROWS
    assert result["eligible_rows"] == audit.EXPECTED_ELIGIBLE_ROWS
    assert result["dataset_sha256"] == audit.SNAPSHOT_DATASET_SHA256
    assert result["comparison_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False
    assert result["provider_request_issued"] is False


def test_campaign092_no_return_status_is_read_only_before_activation() -> None:
    result = audit.status()
    assert result["status"] == "activation_binding_absent"
    assert result["candidate_snapshot_exists"] is True
    assert result["audit_count"] == 0
    assert result["coverage_or_capacity_metrics_computed"] is False
    assert result["comparison_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False
    assert result["provider_request_issued"] is False
