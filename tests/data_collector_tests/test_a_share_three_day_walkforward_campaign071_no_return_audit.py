from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign071_no_return_audit as audit


def test_campaign071_audit_order_is_complete() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factors"]
    assert len(comparisons) == 101
    assert comparisons[-1] == {
        "name": "quarterly_announcement_delay_improvement_yoy_rank_1y",
        "score_direction": "higher",
    }


def test_campaign071_snapshot_is_frozen_before_audit_activation() -> None:
    assert audit.SNAPSHOT_MANIFEST_PATH.is_file()
    assert audit._sha256(audit.SNAPSHOT_MANIFEST_PATH) == audit.SNAPSHOT_MANIFEST_SHA256
    assert audit._sha256(audit.SNAPSHOT_BINDING) == audit.SNAPSHOT_BINDING_SHA256
    assert audit.EXPECTED_ELIGIBLE_ROWS == 7_081_458


def test_campaign071_status_is_no_return_and_pre_audit() -> None:
    payload = audit.status()
    assert payload["audit_count"] == 0
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read"] == []
    assert payload["historical_forward_return_fields_read"] is False
    assert payload["provider_request_issued"] is False


def test_campaign071_static_hash_constants_match_candidate() -> None:
    assert audit.EXPECTED_COMPARISON_ORDER_SHA256 == audit.candidate.COMPARISON_ORDER_SHA256
    assert audit.EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256 == audit.candidate.FULL_DEFINITION_ORDER_SHA256
    assert audit.C70_SNAPSHOT_MANIFEST_PATH.is_file()
