from __future__ import annotations

from scripts import (
    a_share_three_day_walkforward_campaign099_compact_features as compact,
)


def test_campaign099_compact_transformation_is_exact() -> None:
    assert compact.FACTOR_NAME == (
        "intraday_market_close_location_profile_synchronization_240m"
    )
    assert compact.EXPECTED_ROWS == 1_331_759
    assert compact.EXPECTED_ELIGIBLE_ROWS == 1_328_449
    assert compact.SOURCE_MANIFEST_SHA256 == (
        "90c495594de88e183ec920a09be7a1ef66c89d9967f59d2aa27fdd49650b4651"
    )
    assert compact.SOURCE_DATASET_SHA256 == (
        "52f904b975a7b79f383d39ef94ce04c724a234a9a53a2e924402d17a3f7c4972"
    )
    assert compact.AUTHORITATIVE_NO_RETURN_AUDIT_SHA256 == (
        "6df7bfca75a59d00b34a431e2fe5c57d9872587a43b270fa23c5f17ba6411f72"
    )
    assert "audit_v1.c97_audit.compact_stock_day_keys" in compact.GENERATED_SOURCE
    assert "audit_v1.compact_stock_day_keys" not in compact.GENERATED_SOURCE


def test_campaign099_compact_status_is_no_return_read_only() -> None:
    payload = compact.status(data_root=compact.DEFAULT_DATA_ROOT)
    assert (
        payload["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert payload["provider_request_issued_by_status"] is False
