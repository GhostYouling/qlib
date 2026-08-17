from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign145_features as c145


def _half(*, return_index: int, amount_index: int) -> tuple[np.ndarray, np.ndarray]:
    returns = np.zeros(119, dtype=np.float64)
    returns[return_index] = 1.0
    closes = np.exp(np.r_[0.0, np.cumsum(returns)])
    amounts = np.zeros(120, dtype=np.float64)
    amounts[amount_index + 1] = 10.0
    return closes, amounts


def _raw_session() -> pd.DataFrame:
    trade_date = pd.Timestamp("2025-01-02")
    source_codes = sorted(c145.SOURCE_MINUTE_CODE_SET)
    continuous = list(c145.CONTINUOUS_MINUTE_CODES)
    close_half, amount_half = _half(return_index=100, amount_index=0)
    closes = np.r_[close_half, close_half]
    amounts = np.r_[amount_half, amount_half]
    close_by_code = {code: float(value) for code, value in zip(continuous, closes)}
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
            "close": [close_by_code.get(code, 1.0) for code in source_codes],
            "amount": [amount_by_code.get(code, 1.0) for code in source_codes],
        },
        columns=c145.RAW_COLUMNS,
    )


def test_campaign145_protocol_and_orders_are_bound() -> None:
    spec = c145.load_protocol()
    assert spec["candidate"]["name"] == c145.FACTOR_NAME
    assert len(c145.reconstruct_comparisons()) == 141
    assert len(c145.reconstruct_complete_definitions()) == 154
    assert c145.reconstruct_complete_definitions()[-1] == {
        "name": c145.FACTOR_NAME,
        "score_direction": "higher",
    }


def test_campaign145_partition_projection_and_exact_grid() -> None:
    values, quality = c145.extract_return_amount_cumulative_path_signed_area(
        _raw_session(), symbol="SZ000001"
    )
    assert tuple(values.columns) == ("trade_date", c145.FACTOR_SHORT_NAME)
    assert values[c145.FACTOR_SHORT_NAME].tolist() == pytest.approx([0.5])
    assert quality["source_rows"] == 241
    assert quality["valid_path_area_sessions"] == 1
    assert quality["return_amount_pair_observations"] == 238


def test_campaign145_attach_finalize_and_semantics() -> None:
    trade_date = pd.Timestamp("2025-01-02")
    identity = pd.DataFrame(
        {
            "trade_date": [trade_date],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
        },
        columns=c145.IDENTITY_COLUMNS,
    )
    values = pd.DataFrame({"trade_date": [trade_date], c145.FACTOR_SHORT_NAME: [0.25]})
    attached = c145.attach_path_area_values(identity, values, symbol="SZ000001")
    frame = c145.finalize_feature_frame(attached).loc[:, c145.OUTPUT_COLUMNS]
    assert frame[c145.FACTOR_NAME].tolist() == [0.25]
    assert frame[f"{c145.FACTOR_NAME}_eligible"].tolist() == [True]
    assert c145.validate_value_semantics(frame) == (1, 1)


def test_campaign145_invalid_close_amount_and_projection_fail_closed() -> None:
    raw = _raw_session()
    raw.loc[10, "amount"] = -1.0
    values, quality = c145.extract_return_amount_cumulative_path_signed_area(
        raw, symbol="SZ000001"
    )
    assert np.isnan(values[c145.FACTOR_SHORT_NAME]).all()
    assert quality["invalid_close_or_amount_sessions"] == 1

    with pytest.raises(c145.Campaign145FeatureError):
        c145.extract_return_amount_cumulative_path_signed_area(
            raw.drop(columns="close"), symbol="SZ000001"
        )


def test_campaign145_output_semantics_reject_invalid_rows() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2025-01-02")],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
            c145.FACTOR_NAME: [2.0],
            f"{c145.FACTOR_NAME}_eligible": [True],
        },
        columns=c145.OUTPUT_COLUMNS,
    )
    with pytest.raises(c145.Campaign145FeatureError):
        c145.validate_value_semantics(frame)


def test_campaign145_generated_builder_reads_only_frozen_projection() -> None:
    assert c145.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "close",
        "amount",
    )
    assert c145._generated["RAW_COLUMNS"] == c145.RAW_COLUMNS
    assert "open" not in c145._generated["RAW_COLUMNS"]
    assert "high" not in c145._generated["RAW_COLUMNS"]
    assert "low" not in c145._generated["RAW_COLUMNS"]
    assert "volume" not in c145._generated["RAW_COLUMNS"]
    assert c145._generated["FACTOR_FORMULA"] == c145.FACTOR_FORMULA
