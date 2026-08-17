from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign078_no_return_audit_v2 as audit


def test_v2_repair_protocol_allows_only_the_helper_attribute_path() -> None:
    spec = audit.load_repair_protocol()
    sole = spec["sole_repair"]
    assert sole["old_attribute_path"] == (
        "c77_audit.c75_v5.v4.v3.v1.base.base._append_snapshot_comparison"
    )
    assert sole["new_attribute_path"] == (
        "c77_audit.c76_audit.c75_v5.v4.v3.v1.base.base._append_snapshot_comparison"
    )
    assert spec["retry"]["partial_statistics_reused"] is False


def test_corrected_helper_path_is_live_and_comparison_order_is_unchanged() -> None:
    helper = (
        audit.v1.c77_audit.c76_audit.c75_v5.v4.v3.v1.base.base._append_snapshot_comparison
    )
    assert callable(helper)
    assert audit.v1.EXPECTED_COMPARISON_COUNT == 108
    assert len(audit.v1.candidate.reconstruct_comparisons()) == 108


def test_v2_pre_retry_status_is_zero_audits_and_no_returns() -> None:
    status = audit.v1.status()
    assert status["audit_count"] == 0
    assert status["comparison_values_read_by_status"] is False
    assert status["historical_daily_price_fields_read"] == []
    assert status["historical_forward_return_fields_read"] is False
    assert status["provider_request_issued"] is False


def test_v2_implementation_freeze_is_live() -> None:
    freeze = audit._load_implementation_freeze()
    assert freeze["partial_statistics_reused"] is False
    assert freeze["candidate_snapshot_or_manifest_rewritten"] is False
    assert freeze["historical_forward_returns_read_before_retry"] is False
