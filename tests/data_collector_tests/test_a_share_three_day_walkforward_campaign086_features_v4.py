from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign086_features_v4 as v4


@pytest.mark.parametrize(
    ("symbol", "security_number"),
    [("SH600145", 1_600_145), ("SZ000001", 2_000_001), ("BJ430001", 3_430_001)],
)
def test_prefix_symbol_compacts_with_frozen_arithmetic(
    symbol: str, security_number: int
) -> None:
    keys = v4.compact_stock_day_keys(
        pd.Series([pd.Timestamp("2024-01-02")]), pd.Series([symbol])
    )
    day = np.datetime64("2024-01-02", "D").astype(np.int64)
    assert keys.tolist() == [int(day * 4_000_000 + security_number)]


@pytest.mark.parametrize("symbol", ["600145.SH", "sh600145", "SH60014", "XX600145"])
def test_nonaccepted_symbol_formats_fail_closed(symbol: str) -> None:
    with pytest.raises(v4.Campaign086FeatureV4Error):
        v4.compact_stock_day_keys(
            pd.Series([pd.Timestamp("2024-01-02")]), pd.Series([symbol])
        )


def test_v4_status_is_no_return_and_absent_before_retry() -> None:
    result = v4.status()
    assert result["comparison_values_read_by_status"] is False
    assert result["historical_daily_price_or_forward_return_values_read_by_status"] is False
    assert result["provider_request_issued_by_status"] is False
