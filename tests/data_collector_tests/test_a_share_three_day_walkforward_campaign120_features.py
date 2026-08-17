from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign120_features as c120


def _raw_session(closes: np.ndarray) -> pd.DataFrame:
    trade_date = pd.Timestamp("2025-01-02")
    source_codes = sorted(c120.SOURCE_MINUTE_CODE_SET)
    continuous = list(c120.CONTINUOUS_MINUTE_CODES)
    close_by_code = {code: float(value) for code, value in zip(continuous, closes)}
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
            "close": [close_by_code.get(code, 10.0) for code in source_codes],
        },
        columns=c120.RAW_COLUMNS,
    )


def test_campaign120_protocol_and_orders_are_bound() -> None:
    spec = c120.load_protocol()
    assert spec["candidate"]["name"] == c120.FACTOR_NAME
    assert len(c120.reconstruct_comparisons()) == 137
    assert len(c120.reconstruct_complete_definitions()) == 146
    assert c120.reconstruct_complete_definitions()[-1] == {
        "name": c120.FACTOR_NAME,
        "score_direction": "higher",
    }


def test_campaign120_partition_projection_and_exact_grid() -> None:
    closes = np.full(240, 10.0)
    values, quality = c120.extract_direction_dictionary_phrase_count(
        _raw_session(closes), symbol="SZ000001"
    )
    expected, eligible, formula_quality = (
        c120.formula.compute_direction_dictionary_phrase_count(closes.reshape(1, 240))
    )
    assert tuple(values.columns) == (
        "trade_date",
        c120.FACTOR_SHORT_NAME,
    )
    assert values[c120.FACTOR_SHORT_NAME].tolist() == expected.tolist()
    assert eligible.tolist() == [True]
    assert quality["source_rows"] == 241
    assert quality["valid_dictionary_sessions"] == 1
    assert quality["recognized_direction_symbol_observations"] == 238
    assert quality["exact_zero_direction_symbol_observations"] == 238
    assert (
        quality["exact_zero_direction_symbol_observations"]
        == formula_quality["exact_zero_direction_symbol_observations"]
    )


def test_campaign120_attach_finalize_and_semantics() -> None:
    trade_date = pd.Timestamp("2025-01-02")
    identity = pd.DataFrame(
        {
            "trade_date": [trade_date],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
        },
        columns=c120.IDENTITY_COLUMNS,
    )
    values = pd.DataFrame({"trade_date": [trade_date], c120.FACTOR_SHORT_NAME: [20.0]})
    attached = c120.attach_dictionary_values(identity, values, symbol="SZ000001")
    frame = c120.finalize_feature_frame(attached).loc[:, c120.OUTPUT_COLUMNS]
    assert frame[c120.FACTOR_NAME].tolist() == [20.0]
    assert frame[f"{c120.FACTOR_NAME}_eligible"].tolist() == [True]
    assert c120.validate_value_semantics(frame) == (1, 1)


def test_campaign120_invalid_close_and_wrong_projection_fail_closed() -> None:
    raw = _raw_session(np.full(240, 10.0))
    raw.loc[10, "close"] = 0.0
    values, quality = c120.extract_direction_dictionary_phrase_count(
        raw, symbol="SZ000001"
    )
    assert np.isnan(values[c120.FACTOR_SHORT_NAME]).all()
    assert quality["invalid_close_sessions"] == 1

    with pytest.raises(c120.Campaign120FeatureError):
        c120.extract_direction_dictionary_phrase_count(
            raw.drop(columns="close"), symbol="SZ000001"
        )


def test_campaign120_generated_builder_is_close_only_and_no_return() -> None:
    assert c120.RAW_COLUMNS == ("datetime", "symbol", "provider", "close")
    assert c120._generated["RAW_COLUMNS"] == c120.RAW_COLUMNS
    assert "open" not in c120._generated["RAW_COLUMNS"]
    assert "high" not in c120._generated["RAW_COLUMNS"]
    assert "low" not in c120._generated["RAW_COLUMNS"]
    assert "amount" not in c120._generated["RAW_COLUMNS"]
    assert c120._generated["FACTOR_FORMULA"] == c120.FACTOR_FORMULA
    status = c120.status()
    assert status["source_fields_read_by_status"] == []
    assert (
        status["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )


def test_campaign120_output_semantics_reject_invalid_rows() -> None:
    for invalid in (1.0, 2.5, 239.0):
        frame = pd.DataFrame(
            {
                "trade_date": [pd.Timestamp("2025-01-02")],
                "symbol": ["SZ000001"],
                "provider": ["tushare"],
                c120.FACTOR_NAME: [invalid],
                f"{c120.FACTOR_NAME}_eligible": [True],
            },
            columns=c120.OUTPUT_COLUMNS,
        )
        with pytest.raises(c120.Campaign120FeatureError):
            c120.validate_value_semantics(frame)
