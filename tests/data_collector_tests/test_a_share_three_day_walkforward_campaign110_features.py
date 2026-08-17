from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign110_features as c110


def test_campaign110_prevalue_orders_and_protocol_are_frozen() -> None:
    spec = c110.load_protocol()
    assert spec["candidate"]["name"] == c110.FACTOR_NAME
    assert spec["candidate"]["valid_range"] == [-1.0, 1.0]
    assert len(c110.reconstruct_complete_definitions()) == 139
    assert len(c110.reconstruct_comparisons()) == 133
    assert c110.reconstruct_comparisons()[-1]["name"].endswith(
        "body_magnitude_serial_persistence_238p"
    )
    assert c110.RAW_COLUMNS == ("datetime", "symbol", "provider", "open", "close")


def test_campaign110_fixed_open_reference_retains_ties_in_denominator() -> None:
    opens = np.full((1, 240), 100.0)
    closes = np.concatenate(
        [np.full(120, 101.0), np.full(60, 100.0), np.full(60, 99.0)]
    )[None, :]
    values, eligible, states, reference = (
        c110.compute_open_reference_directional_occupancy(opens, closes)
    )
    assert eligible.tolist() == [True]
    assert reference.tolist() == [100.0]
    assert (states > 0.0).sum() == 120
    assert (states == 0.0).sum() == 60
    assert (states < 0.0).sum() == 60
    assert values[0] == 0.25


def test_campaign110_non_anchor_opens_do_not_change_value_or_support() -> None:
    opens = np.full((2, 240), 100.0)
    closes = np.tile(np.linspace(99.0, 101.0, 240), (2, 1))
    opens[1, 1:] = np.nan
    values, eligible, _states, _reference = (
        c110.compute_open_reference_directional_occupancy(opens, closes)
    )
    assert eligible.tolist() == [True, True]
    assert values[0] == values[1]


def test_campaign110_invalid_anchor_or_any_close_is_missing() -> None:
    opens = np.full((2, 240), 100.0)
    closes = np.full((2, 240), 101.0)
    opens[0, 0] = 0.0
    closes[1, 100] = np.nan
    values, eligible, _states, _reference = (
        c110.compute_open_reference_directional_occupancy(opens, closes)
    )
    assert eligible.tolist() == [False, False]
    assert np.isnan(values).all()


def test_campaign110_extract_validates_241_grid_and_excludes_0930() -> None:
    date = pd.Timestamp("2025-01-02")
    codes = [9 * 60 + 30, *c110.CONTINUOUS_MINUTE_CODES]
    opens = np.full(241, 100.0)
    opens[0] = 9999.0
    closes = np.full(241, 99.0)
    closes[1:121] = 101.0
    closes[121:181] = 100.0
    raw = pd.DataFrame(
        {
            "datetime": [date + pd.Timedelta(minutes=int(code)) for code in codes],
            "symbol": "SH600000",
            "provider": "tushare",
            "open": opens,
            "close": closes,
        }
    ).loc[:, c110.RAW_COLUMNS]
    frame, quality = c110.extract_open_reference_directional_occupancy(
        raw, symbol="SH600000"
    )
    assert len(frame) == 1
    assert frame.iloc[0, 1] == 0.25
    assert quality["valid_open_reference_occupancy_sessions"] == 1
    assert quality["source_rows"] == 241
    assert quality["equal_reference_bars"] == 60
    assert quality["nonzero_reference_state_bars"] == 180


def test_campaign110_value_semantics_require_240_state_lattice() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2025-01-02")],
            "symbol": ["SH600000"],
            "provider": ["tushare"],
            c110.FACTOR_NAME: [0.25],
            f"{c110.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, c110.OUTPUT_COLUMNS]
    assert c110.validate_value_semantics(frame) == (1, 1)
    frame.loc[0, c110.FACTOR_NAME] = 0.251
    try:
        c110.validate_value_semantics(frame)
    except c110.Campaign110FeatureError:
        pass
    else:
        raise AssertionError("non-lattice Campaign110 value was accepted")
