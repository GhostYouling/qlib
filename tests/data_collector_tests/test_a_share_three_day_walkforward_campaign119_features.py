from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign119_features as c119


def _raw_session(highs: np.ndarray, lows: np.ndarray) -> pd.DataFrame:
    trade_date = pd.Timestamp("2025-01-02")
    source_codes = sorted(c119.SOURCE_MINUTE_CODE_SET)
    continuous = list(c119.CONTINUOUS_MINUTE_CODES)
    high_by_code = {code: float(value) for code, value in zip(continuous, highs)}
    low_by_code = {code: float(value) for code, value in zip(continuous, lows)}
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
            "high": [high_by_code.get(code, 12.0) for code in source_codes],
            "low": [low_by_code.get(code, 10.0) for code in source_codes],
        },
        columns=c119.RAW_COLUMNS,
    )


def test_campaign119_protocol_and_orders_are_bound() -> None:
    spec = c119.load_protocol()
    assert spec["candidate"]["name"] == c119.FACTOR_NAME
    assert len(c119.reconstruct_comparisons()) == 136
    assert len(c119.reconstruct_complete_definitions()) == 145
    assert c119.reconstruct_complete_definitions()[-1] == {
        "name": c119.FACTOR_NAME,
        "score_direction": "higher",
    }


def test_campaign119_partition_projection_and_exact_grid() -> None:
    highs = np.full(240, 12.0)
    lows = np.full(240, 10.0)
    values, quality = c119.extract_range_boundary_direction_state_entropy(
        _raw_session(highs, lows), symbol="SZ000001"
    )
    assert tuple(values.columns) == ("trade_date", c119.FACTOR_SHORT_NAME)
    assert values[c119.FACTOR_SHORT_NAME].tolist() == [0.0]
    assert quality["source_rows"] == 241
    assert quality["valid_entropy_sessions"] == 1
    assert quality["recognized_state_observations"] == 238
    assert quality["exact_joint_tie_pair_observations"] == 238


def test_campaign119_attach_finalize_and_semantics() -> None:
    trade_date = pd.Timestamp("2025-01-02")
    identity = pd.DataFrame(
        {
            "trade_date": [trade_date],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
        },
        columns=c119.IDENTITY_COLUMNS,
    )
    values = pd.DataFrame({"trade_date": [trade_date], c119.FACTOR_SHORT_NAME: [0.25]})
    attached = c119.attach_state_entropy_values(identity, values, symbol="SZ000001")
    frame = c119.finalize_feature_frame(attached).loc[:, c119.OUTPUT_COLUMNS]
    assert frame[c119.FACTOR_NAME].tolist() == [0.25]
    assert frame[f"{c119.FACTOR_NAME}_eligible"].tolist() == [True]
    assert c119.validate_value_semantics(frame) == (1, 1)


def test_campaign119_invalid_range_and_wrong_projection_fail_closed() -> None:
    raw = _raw_session(np.full(240, 12.0), np.full(240, 10.0))
    raw.loc[10, "high"] = 9.0
    values, quality = c119.extract_range_boundary_direction_state_entropy(
        raw, symbol="SZ000001"
    )
    assert np.isnan(values[c119.FACTOR_SHORT_NAME]).all()
    assert quality["invalid_high_below_low_sessions"] == 1

    with pytest.raises(c119.Campaign119FeatureError):
        c119.extract_range_boundary_direction_state_entropy(
            raw.drop(columns="low"), symbol="SZ000001"
        )


def test_campaign119_generated_builder_is_high_low_only_and_no_return() -> None:
    assert c119.RAW_COLUMNS == ("datetime", "symbol", "provider", "high", "low")
    assert c119._generated["RAW_COLUMNS"] == c119.RAW_COLUMNS
    assert "open" not in c119._generated["RAW_COLUMNS"]
    assert "close" not in c119._generated["RAW_COLUMNS"]
    assert "amount" not in c119._generated["RAW_COLUMNS"]
    assert c119._generated["FACTOR_FORMULA"] == c119.FACTOR_FORMULA
    status = c119.status()
    assert status["source_fields_read_by_status"] == []
    assert (
        status["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )


def test_campaign119_output_semantics_reject_invalid_rows() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2025-01-02")],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
            c119.FACTOR_NAME: [2.0],
            f"{c119.FACTOR_NAME}_eligible": [True],
        },
        columns=c119.OUTPUT_COLUMNS,
    )
    with pytest.raises(c119.Campaign119FeatureError):
        c119.validate_value_semantics(frame)
