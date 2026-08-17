from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign116_features as c116


def _synthetic_selected() -> tuple[np.ndarray, np.ndarray]:
    returns = np.concatenate([np.full(60, 0.01), np.full(59, -0.01)])
    half = 100.0 * np.exp(np.concatenate([[0.0], np.cumsum(returns)]))
    closes = np.concatenate([half, half])
    amounts = np.ones(240, dtype=np.float64)
    for start in (0, 120):
        amounts[start + 2 : start + 61] = 3.0
    amounts[[0, 120]] = 3.0
    return closes, amounts


def test_campaign116_orders_protocol_and_implementation_are_bound() -> None:
    spec = c116.load_protocol()
    assert spec["candidate"]["name"] == c116.FACTOR_NAME
    assert len(c116.reconstruct_comparisons()) == 134
    assert len(c116.reconstruct_complete_definitions()) == 142
    assert c116.reconstruct_complete_definitions()[-1] == {
        "name": c116.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert c116._validate_implementation_freeze()["synthetic_verification"][
        "passed"
    ] == 10


def test_campaign116_extracts_only_the_fixed_240_continuous_bars() -> None:
    date = pd.Timestamp("2025-01-02")
    codes = [9 * 60 + 30, *c116.CONTINUOUS_MINUTE_CODES]
    closes, amounts = _synthetic_selected()
    raw = pd.DataFrame(
        {
            "datetime": [date + pd.Timedelta(minutes=int(code)) for code in codes],
            "symbol": "SH600000",
            "provider": "tushare",
            "close": np.concatenate([[np.nan], closes]),
            "amount": np.concatenate([[-1.0], amounts]),
        }
    ).loc[:, c116.RAW_COLUMNS]
    frame, quality = c116.extract_amount_conditioned_directional_persistence_spread(
        raw, symbol="SH600000"
    )
    assert len(frame) == 1
    assert np.isclose(frame.iloc[0, 1], 117.0 / 118.0)
    assert quality["source_rows"] == 241
    assert quality["valid_persistence_sessions"] == 1
    assert quality["informative_high_pairs"] == 118
    assert quality["informative_ordinary_pairs"] == 118


def test_campaign116_attach_finalize_and_value_semantics() -> None:
    date = pd.Timestamp("2025-01-02")
    identity = pd.DataFrame(
        {"trade_date": [date], "symbol": ["SH600000"], "provider": ["tushare"]}
    ).loc[:, c116.IDENTITY_COLUMNS]
    values = pd.DataFrame(
        {"trade_date": [date], c116.FACTOR_SHORT_NAME: [0.25]}
    )
    attached = c116.attach_persistence_values(
        identity, values, symbol="SH600000"
    )
    out = c116.finalize_feature_frame(attached).loc[:, c116.OUTPUT_COLUMNS]
    assert out[c116.FACTOR_NAME].tolist() == [0.25]
    assert out[f"{c116.FACTOR_NAME}_eligible"].tolist() == [True]
    assert c116.validate_value_semantics(out) == (1, 1)


def test_campaign116_out_of_range_value_fails_closed() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2025-01-02")],
            "symbol": ["SH600000"],
            "provider": ["tushare"],
            c116.FACTOR_NAME: [1.01],
            f"{c116.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, c116.OUTPUT_COLUMNS]
    try:
        c116.validate_value_semantics(frame)
    except c116.Campaign116FeatureError:
        pass
    else:
        raise AssertionError("Campaign116 accepted an out-of-range score")
