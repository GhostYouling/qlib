from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign068_features_v2 as features
from scripts import a_share_three_day_walkforward_campaign068_no_return_audit as audit


def test_campaign068_v2_snapshot_is_present_after_publication() -> None:
    payload = features.status()
    assert payload["status"] == "snapshot_present"
    assert payload["v1_failed_snapshot_accepted"] is False
    assert payload["candidate_or_comparison_values_read_by_status"] is False


def test_campaign068_terminal_audit_is_present_without_return_or_cache_status_reads() -> None:
    payload = audit.status()
    assert payload["audit_count"] == 1
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read"] == []
    assert payload["historical_forward_return_fields_read"] is False
    assert payload["provider_request_issued"] is False
