from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign118_features as c118


def _raw_session(amounts: np.ndarray) -> pd.DataFrame:
    trade_date = pd.Timestamp("2025-01-02")
    source_codes = sorted(c118.SOURCE_MINUTE_CODE_SET)
    continuous = list(c118.CONTINUOUS_MINUTE_CODES)
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
        columns=c118.RAW_COLUMNS,
    )


def test_campaign118_protocol_and_orders_are_bound() -> None:
    spec = c118.load_protocol()
    assert spec["candidate"]["name"] == c118.FACTOR_NAME
    assert len(c118.reconstruct_comparisons()) == 135
    assert len(c118.reconstruct_complete_definitions()) == 144
    assert c118.reconstruct_complete_definitions()[-1] == {
        "name": c118.FACTOR_NAME,
        "score_direction": "higher",
    }


def test_campaign118_partition_projection_and_exact_grid() -> None:
    amounts = np.ones(240, dtype=np.float64)
    amounts[:24] = 2.0
    values, quality = c118.extract_top_decile_amount_event_spacing_entropy(
        _raw_session(amounts), symbol="SZ000001"
    )
    assert tuple(values.columns) == ("trade_date", c118.FACTOR_SHORT_NAME)
    assert values[c118.FACTOR_SHORT_NAME].tolist() == [0.0]
    assert quality["source_rows"] == 241
    assert quality["valid_entropy_sessions"] == 1
    assert quality["zero_gap_observations"] == 24


def test_campaign118_attach_finalize_and_semantics() -> None:
    trade_date = pd.Timestamp("2025-01-02")
    identity = pd.DataFrame(
        {
            "trade_date": [trade_date],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
        },
        columns=c118.IDENTITY_COLUMNS,
    )
    values = pd.DataFrame({"trade_date": [trade_date], c118.FACTOR_SHORT_NAME: [0.25]})
    attached = c118.attach_event_spacing_values(identity, values, symbol="SZ000001")
    frame = c118.finalize_feature_frame(attached).loc[:, c118.OUTPUT_COLUMNS]
    assert frame[c118.FACTOR_NAME].tolist() == [0.25]
    assert frame[f"{c118.FACTOR_NAME}_eligible"].tolist() == [True]
    assert c118.validate_value_semantics(frame) == (1, 1)


def test_campaign118_invalid_amount_and_wrong_projection_fail_closed() -> None:
    raw = _raw_session(np.ones(240))
    raw.loc[10, "amount"] = -1.0
    values, quality = c118.extract_top_decile_amount_event_spacing_entropy(
        raw, symbol="SZ000001"
    )
    assert np.isnan(values[c118.FACTOR_SHORT_NAME]).all()
    assert quality["invalid_amount_sessions"] == 1

    with pytest.raises(c118.Campaign118FeatureError):
        c118.extract_top_decile_amount_event_spacing_entropy(
            raw.drop(columns="amount"), symbol="SZ000001"
        )


def test_campaign118_generated_builder_is_amount_only_and_no_return() -> None:
    assert c118.RAW_COLUMNS == ("datetime", "symbol", "provider", "amount")
    assert c118._generated["RAW_COLUMNS"] == c118.RAW_COLUMNS
    assert "volume" not in c118._generated["RAW_COLUMNS"]
    assert c118._generated["FACTOR_FORMULA"] == c118.FACTOR_FORMULA
    status = c118.status()
    assert status["source_fields_read_by_status"] == []
    assert (
        status["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )


def test_campaign118_output_semantics_reject_invalid_rows() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2025-01-02")],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
            c118.FACTOR_NAME: [2.0],
            f"{c118.FACTOR_NAME}_eligible": [True],
        },
        columns=c118.OUTPUT_COLUMNS,
    )
    with pytest.raises(c118.Campaign118FeatureError):
        c118.validate_value_semantics(frame)
