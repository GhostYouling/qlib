from __future__ import annotations

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign086_features as v1
from scripts import a_share_three_day_walkforward_campaign086_features_v2 as v2


def test_empty_identity_returns_exact_empty_attached_schema() -> None:
    identity = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="object"),
            "provider": pd.Series(dtype="object"),
        }
    ).loc[:, v1.IDENTITY_COLUMNS]
    values = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2019-01-02")],
            v1.FACTOR_NAME: [0.5],
        }
    )
    result = v2.attach_values(identity, values, symbol="SH600145")
    assert result.empty
    assert tuple(result.columns) == (*v1.IDENTITY_COLUMNS, v1.FACTOR_NAME)


def test_nonempty_identity_delegates_to_frozen_v1() -> None:
    identity = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2019-01-02")],
            "symbol": ["SH600145"],
            "provider": ["tushare"],
        }
    ).loc[:, v1.IDENTITY_COLUMNS]
    values = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2019-01-02")],
            v1.FACTOR_NAME: [0.5],
        }
    )
    result = v2.attach_values(identity, values, symbol="SH600145")
    assert result.loc[0, v1.FACTOR_NAME] == 0.5


def test_v2_status_is_no_return_and_output_absent_before_retry() -> None:
    result = v2.status()
    assert result["comparison_values_read_by_status"] is False
    assert result["historical_daily_price_or_forward_return_values_read_by_status"] is False
    assert result["provider_request_issued_by_status"] is False
