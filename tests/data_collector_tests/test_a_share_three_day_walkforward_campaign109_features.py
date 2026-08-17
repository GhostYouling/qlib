from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign109_features as c109


def test_campaign109_prevalue_orders_and_protocol_are_frozen() -> None:
    spec = c109.load_protocol()
    assert spec["candidate"]["name"] == c109.FACTOR_NAME
    assert spec["candidate"]["valid_range"] == [-1.0, 1.0]
    assert len(c109.reconstruct_complete_definitions()) == 138
    assert len(c109.reconstruct_comparisons()) == 132
    assert c109.RAW_COLUMNS == ("datetime", "symbol", "provider", "open", "close")


def test_campaign109_body_persistence_retains_zero_bodies() -> None:
    body = np.concatenate(
        [np.linspace(0.0, 0.02, 120), np.linspace(0.0, 0.03, 120)]
    )[None, :]
    open_ = np.full((1, 240), 100.0)
    close = open_ * np.exp(body)
    values, eligible, bodies, lag_var, lead_var = (
        c109.compute_body_magnitude_serial_persistence(open_, close)
    )
    assert eligible.tolist() == [True]
    assert values[0] > 0.999
    assert (bodies == 0.0).sum() == 2
    assert lag_var[0] > 0.0
    assert lead_var[0] > 0.0


def test_campaign109_degenerate_body_vector_is_missing() -> None:
    open_ = np.full((1, 240), 100.0)
    close = open_.copy()
    values, eligible, _bodies, lag_var, lead_var = (
        c109.compute_body_magnitude_serial_persistence(open_, close)
    )
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])
    assert lag_var[0] == 0.0
    assert lead_var[0] == 0.0


def test_campaign109_extract_validates_241_grid_and_excludes_lunch_pair() -> None:
    date = pd.Timestamp("2025-01-02")
    codes = [9 * 60 + 30, *c109.CONTINUOUS_MINUTE_CODES]
    body = np.concatenate(
        [np.linspace(0.0, 0.02, 120), np.linspace(0.0, 0.03, 120)]
    )
    opens = np.full(241, 100.0)
    closes = opens.copy()
    closes[1:] = opens[1:] * np.exp(body)
    raw = pd.DataFrame(
        {
            "datetime": [
                date + pd.Timedelta(minutes=int(code)) for code in codes
            ],
            "symbol": "SH600000",
            "provider": "tushare",
            "open": opens,
            "close": closes,
        }
    ).loc[:, c109.RAW_COLUMNS]
    frame, quality = c109.extract_body_magnitude_serial_persistence(
        raw, symbol="SH600000"
    )
    assert len(frame) == 1
    assert frame.iloc[0, 1] > 0.999
    assert quality["valid_body_persistence_sessions"] == 1
    assert quality["source_rows"] == 241
    assert quality["zero_body_bars"] == 2
