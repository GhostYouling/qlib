from __future__ import annotations

import numpy as np

from scripts import (
    a_share_three_day_walkforward_campaign097_compact_features as compact,
)


def test_authoritative_admission_and_source_are_frozen() -> None:
    assert compact._sha256(compact.AUTHORITATIVE_NO_RETURN_AUDIT) == (
        compact.AUTHORITATIVE_NO_RETURN_AUDIT_SHA256
    )
    assert compact._sha256(compact.SOURCE_MANIFEST) == compact.SOURCE_MANIFEST_SHA256
    assert compact.EXPECTED_ROWS == 1_331_759
    assert compact.EXPECTED_ELIGIBLE_ROWS == 1_328_449


def test_frame_digest_is_deterministic_and_missing_sensitive() -> None:
    keys = np.array([1, 2, 3], dtype=np.int64)
    values = np.array([0.1, np.nan, -0.2], dtype=np.float64)
    first = compact._frame_sha256(keys, values)
    assert first == compact._frame_sha256(keys.copy(), values.copy())
    changed = values.copy()
    changed[1] = 0.0
    assert first != compact._frame_sha256(keys, changed)


def test_output_root_is_new_compact_namespace() -> None:
    root = compact.output_root(compact.DEFAULT_DATA_ROOT)
    assert "campaign097_compact_feature_library" in str(root)
    assert root.name == compact.OUTPUT_RUN_ID


def test_status_is_value_free() -> None:
    result = compact.status(data_root=compact.DEFAULT_DATA_ROOT)
    assert (
        result["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert result["provider_request_issued_by_status"] is False
