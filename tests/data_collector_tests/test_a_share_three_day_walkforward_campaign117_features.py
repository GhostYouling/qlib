from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign117_features as c117


def _raw_session(amounts: np.ndarray) -> pd.DataFrame:
    trade_date = pd.Timestamp("2025-01-02")
    source_codes = sorted(c117.SOURCE_MINUTE_CODE_SET)
    continuous = list(c117.CONTINUOUS_MINUTE_CODES)
    amount_by_code = {code: float(value) for code, value in zip(continuous, amounts)}
    return pd.DataFrame(
        {
            "datetime": [
                trade_date
                + pd.Timedelta(hours=code // 60)
                + pd.Timedelta(minutes=code % 60)
                for code in source_codes
            ],
            "symbol": "SZ000001",
            "provider": "tushare",
            "amount": [amount_by_code.get(code, 1.0) for code in source_codes],
        },
        columns=c117.RAW_COLUMNS,
    )


def test_campaign117_protocol_and_orders_are_bound() -> None:
    spec = c117.load_protocol()
    assert spec["candidate"]["name"] == c117.FACTOR_NAME
    assert len(c117.reconstruct_comparisons()) == 134
    assert len(c117.reconstruct_complete_definitions()) == 143
    assert c117.reconstruct_complete_definitions()[-1] == {
        "name": c117.FACTOR_NAME,
        "score_direction": "higher",
    }


def test_campaign117_partition_projection_and_exact_grid() -> None:
    amounts = np.r_[np.arange(1.0, 121.0), np.arange(1.0, 121.0)]
    values, quality = c117.extract_amount_weak_order_entropy(
        _raw_session(amounts), symbol="SZ000001"
    )
    assert tuple(values.columns) == ("trade_date", c117.FACTOR_SHORT_NAME)
    assert values[c117.FACTOR_SHORT_NAME].tolist() == [0.0]
    assert quality["source_rows"] == 241
    assert quality["valid_entropy_sessions"] == 1
    assert quality["recognized_state_observations"] == 236


def test_campaign117_attach_finalize_and_semantics() -> None:
    trade_date = pd.Timestamp("2025-01-02")
    identity = pd.DataFrame(
        {
            "trade_date": [trade_date],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
        },
        columns=c117.IDENTITY_COLUMNS,
    )
    values = pd.DataFrame({"trade_date": [trade_date], c117.FACTOR_SHORT_NAME: [0.25]})
    attached = c117.attach_entropy_values(identity, values, symbol="SZ000001")
    frame = c117.finalize_feature_frame(attached).loc[:, c117.OUTPUT_COLUMNS]
    assert frame[c117.FACTOR_NAME].tolist() == [0.25]
    assert frame[f"{c117.FACTOR_NAME}_eligible"].tolist() == [True]
    assert c117.validate_value_semantics(frame) == (1, 1)


def test_campaign117_invalid_amount_and_wrong_projection_fail_closed() -> None:
    raw = _raw_session(np.ones(240))
    raw.loc[10, "amount"] = -1.0
    values, quality = c117.extract_amount_weak_order_entropy(raw, symbol="SZ000001")
    assert np.isnan(values[c117.FACTOR_SHORT_NAME]).all()
    assert quality["invalid_amount_sessions"] == 1

    with pytest.raises(c117.Campaign117FeatureError):
        c117.extract_amount_weak_order_entropy(
            raw.drop(columns="amount"), symbol="SZ000001"
        )


def test_campaign117_generated_builder_is_amount_only_and_no_return() -> None:
    assert c117.RAW_COLUMNS == ("datetime", "symbol", "provider", "amount")
    assert c117._generated["RAW_COLUMNS"] == c117.RAW_COLUMNS
    assert "volume" not in c117._generated["RAW_COLUMNS"]
    assert c117._generated["FACTOR_FORMULA"] == c117.FACTOR_FORMULA
    status = c117.status()
    assert status["source_fields_read_by_status"] == []
    assert (
        status["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )


def test_campaign117_output_semantics_reject_invalid_rows() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2025-01-02")],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
            c117.FACTOR_NAME: [2.0],
            f"{c117.FACTOR_NAME}_eligible": [True],
        },
        columns=c117.OUTPUT_COLUMNS,
    )
    with pytest.raises(c117.Campaign117FeatureError):
        c117.validate_value_semantics(frame)
