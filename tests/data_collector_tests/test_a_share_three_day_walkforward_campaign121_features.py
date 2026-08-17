from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign121_features as c121


def test_campaign121_prevalue_orders_and_protocol_are_frozen() -> None:
    spec = c121.load_protocol()
    assert spec["candidate"]["name"] == c121.FACTOR_NAME
    assert len(c121.reconstruct_complete_definitions()) == 147
    assert len(c121.reconstruct_comparisons()) == 138
    assert c121.reconstruct_comparisons()[-1]["name"].endswith(
        "direction_dictionary_phrase_count_238s"
    )
    assert c121.RAW_COLUMNS == ("datetime", "symbol", "provider", "open", "close")


def test_campaign121_compute_delegates_to_frozen_formula() -> None:
    opens = np.full((2, 240), 100.0)
    closes = np.full((2, 240), 100.0)
    closes[0, 39:] = 110.0
    closes[1, 199:] = 90.0
    values, eligible, tau, quality = (
        c121.compute_terminal_close_direction_first_attainment(opens, closes)
    )
    assert eligible.tolist() == [True, True]
    assert tau.tolist() == [40, 200]
    assert values.tolist() == [200.0 / 239.0, 40.0 / 239.0]
    assert quality["directional_first_attainment_rows"] == 2


def test_campaign121_extract_validates_241_grid_and_excludes_0930() -> None:
    date = pd.Timestamp("2025-01-02")
    codes = [9 * 60 + 30, *c121.CONTINUOUS_MINUTE_CODES]
    opens = np.full(241, 100.0)
    opens[0] = 9999.0
    closes = np.full(241, 100.0)
    closes[1 + 39 :] = 110.0
    raw = pd.DataFrame(
        {
            "datetime": [date + pd.Timedelta(minutes=int(code)) for code in codes],
            "symbol": "SH600000",
            "provider": "tushare",
            "open": opens,
            "close": closes,
        }
    ).loc[:, c121.RAW_COLUMNS]
    frame, quality = c121.extract_terminal_close_direction_first_attainment(
        raw, symbol="SH600000"
    )
    assert len(frame) == 1
    assert frame.iloc[0, 1] == 200.0 / 239.0
    assert quality["valid_terminal_first_attainment_sessions"] == 1
    assert quality["source_rows"] == 241


def test_campaign121_value_semantics_require_239_position_lattice() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2025-01-02")],
            "symbol": ["SH600000"],
            "provider": ["tushare"],
            c121.FACTOR_NAME: [200.0 / 239.0],
            f"{c121.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, c121.OUTPUT_COLUMNS]
    assert c121.validate_value_semantics(frame) == (1, 1)
    frame.loc[0, c121.FACTOR_NAME] = 0.251
    try:
        c121.validate_value_semantics(frame)
    except c121.Campaign121FeatureError:
        pass
    else:
        raise AssertionError("non-lattice Campaign121 value was accepted")
