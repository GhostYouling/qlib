from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign146_features as c146


def _half(*, return_index: int, amount_index: int) -> tuple[np.ndarray, np.ndarray]:
    returns = np.zeros(119, dtype=np.float64)
    activity = np.zeros(119, dtype=np.float64)
    returns[return_index] = 0.01
    activity[amount_index] = 1.0
    closes = np.concatenate(([1.0], np.exp(np.cumsum(returns))))
    amounts = np.concatenate(([0.0], np.expm1(activity)))
    return closes, amounts


def _raw_session() -> pd.DataFrame:
    trade_date = pd.Timestamp("2025-01-02")
    source_codes = sorted(c146.SOURCE_MINUTE_CODE_SET)
    continuous = list(c146.CONTINUOUS_MINUTE_CODES)
    close_half, amount_half = _half(return_index=21, amount_index=20)
    closes = np.concatenate((close_half, close_half))
    amounts = np.concatenate((amount_half, amount_half))
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
            "amount": [amount_by_code.get(code, 0.0) for code in source_codes],
        },
        columns=c146.RAW_COLUMNS,
    )


def test_campaign146_protocol_and_orders_are_bound() -> None:
    spec = c146.load_protocol()
    assert spec["candidate"]["name"] == c146.FACTOR_NAME
    assert len(c146.reconstruct_comparisons()) == 141
    assert len(c146.reconstruct_complete_definitions()) == 155
    assert c146.reconstruct_complete_definitions()[-1] == {
        "name": c146.FACTOR_NAME,
        "score_direction": "higher",
    }


def test_campaign146_partition_projection_grid_and_orientation() -> None:
    values, quality = c146.extract_return_amount_cross_spectral_phase_lead(
        _raw_session(), symbol="SZ000001"
    )
    assert tuple(values.columns) == ("trade_date", c146.FACTOR_SHORT_NAME)
    assert values[c146.FACTOR_SHORT_NAME].iloc[0] > 0.0
    assert quality["source_rows"] == 241
    assert quality["valid_phase_sessions"] == 1
    assert quality["positive_frequency_observations"] == 118


def test_campaign146_attach_finalize_preserves_negative_values() -> None:
    trade_date = pd.Timestamp("2025-01-02")
    identity = pd.DataFrame(
        {
            "trade_date": [trade_date],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
        },
        columns=c146.IDENTITY_COLUMNS,
    )
    values = pd.DataFrame({"trade_date": [trade_date], c146.FACTOR_SHORT_NAME: [-0.25]})
    attached = c146.attach_phase_values(identity, values, symbol="SZ000001")
    frame = c146.finalize_feature_frame(attached).loc[:, c146.OUTPUT_COLUMNS]
    assert frame[c146.FACTOR_NAME].tolist() == [-0.25]
    assert frame[f"{c146.FACTOR_NAME}_eligible"].tolist() == [True]
    assert c146.validate_value_semantics(frame) == (1, 1)


def test_campaign146_invalid_close_amount_and_projection_fail_closed() -> None:
    raw = _raw_session()
    raw.loc[10, "amount"] = -1.0
    values, quality = c146.extract_return_amount_cross_spectral_phase_lead(
        raw, symbol="SZ000001"
    )
    assert np.isnan(values[c146.FACTOR_SHORT_NAME]).all()
    assert quality["invalid_close_or_amount_sessions"] == 1

    with pytest.raises(c146.Campaign146FeatureError):
        c146.extract_return_amount_cross_spectral_phase_lead(
            raw.drop(columns="close"), symbol="SZ000001"
        )


def test_campaign146_output_semantics_reject_invalid_rows() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2025-01-02")],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
            c146.FACTOR_NAME: [2.0],
            f"{c146.FACTOR_NAME}_eligible": [True],
        },
        columns=c146.OUTPUT_COLUMNS,
    )
    with pytest.raises(c146.Campaign146FeatureError):
        c146.validate_value_semantics(frame)


def test_campaign146_generated_builder_reads_only_frozen_projection() -> None:
    assert c146.RAW_COLUMNS == (
        "datetime",
        "symbol",
        "provider",
        "close",
        "amount",
    )
    assert c146._generated["RAW_COLUMNS"] == c146.RAW_COLUMNS
    assert set(("open", "high", "low", "volume")).isdisjoint(c146.RAW_COLUMNS)
    assert c146._generated["FACTOR_FORMULA"] == c146.FACTOR_FORMULA
    assert c146._generated["finalize_feature_frame"] is c146.finalize_feature_frame
