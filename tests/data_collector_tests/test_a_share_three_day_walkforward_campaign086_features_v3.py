from __future__ import annotations

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign086_features as v1
from scripts import a_share_three_day_walkforward_campaign086_features_v3 as v3


def _identity(rows: int) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2019-01-02")] * rows,
            "symbol": ["SH600145"] * rows,
            "provider": ["tushare"] * rows,
        }
    )
    return frame.loc[:, v1.IDENTITY_COLUMNS]


def _values() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2019-01-02")],
            v1.FACTOR_NAME: [0.5],
        }
    )


def test_empty_identity_uses_exact_v2_empty_schema() -> None:
    result = v3.attach_values(_identity(0), _values(), symbol="SH600145")
    assert result.empty
    assert tuple(result.columns) == (*v1.IDENTITY_COLUMNS, v1.FACTOR_NAME)


def test_nonempty_dispatch_uses_captured_v1_during_runtime_replacement() -> None:
    original = v1.attach_values
    v1.attach_values = v3.attach_values
    try:
        result = v3.attach_values(_identity(1), _values(), symbol="SH600145")
    finally:
        v1.attach_values = original
    assert result.loc[0, v1.FACTOR_NAME] == 0.5


def test_v3_status_is_no_return_and_absent_before_retry() -> None:
    result = v3.status()
    assert result["comparison_values_read_by_status"] is False
    assert result["historical_daily_price_or_forward_return_values_read_by_status"] is False
    assert result["provider_request_issued_by_status"] is False
