from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign096_features as v1
from scripts import a_share_three_day_walkforward_campaign096_features_v2 as v2


def _raw_one_session() -> pd.DataFrame:
    morning = pd.date_range("2023-06-01 09:30", "2023-06-01 11:30", freq="min")
    afternoon = pd.date_range("2023-06-01 13:01", "2023-06-01 15:00", freq="min")
    times = morning.append(afternoon)
    return pd.DataFrame(
        {
            "datetime": times,
            "symbol": "SH600000",
            "provider": "tushare",
            "high": np.e,
            "low": 1.0,
            "close": np.exp(0.5),
        }
    ).loc[:, v2.RAW_COLUMNS]


def test_v2_adds_only_the_frozen_quality_alias() -> None:
    raw = _raw_one_session()
    frame_v1, quality_v1 = v1.extract_intrabar_close_location_total_variation(
        raw, symbol="SH600000"
    )
    frame_v2, quality_v2 = v2.extract_intrabar_close_location_total_variation(
        raw, symbol="SH600000"
    )
    pd.testing.assert_frame_equal(frame_v1, frame_v2)
    assert "zero_destination_range_pairs" not in quality_v1
    assert quality_v2.pop("zero_destination_range_pairs") == quality_v1["zero_range_bars"]
    assert quality_v2 == quality_v1


def test_v2_preserves_formula_protocol_and_orders() -> None:
    spec = v2.load_protocol()
    assert spec["candidate"]["name"] == v2.FACTOR_NAME
    assert v2.FACTOR_FORMULA == v1.FACTOR_FORMULA
    assert len(v2.reconstruct_complete_definitions()) == 127
    assert len(v2.reconstruct_comparisons()) == 124
    assert (
        v2._comparison_order_digest(v2.reconstruct_complete_definitions())
        == v2.FULL_DEFINITION_ORDER_SHA256
    )
    assert (
        v2._comparison_order_digest(v2.reconstruct_comparisons())
        == v2.COMPARISON_ORDER_SHA256
    )


def test_v2_compute_is_byte_for_byte_v1_logic() -> None:
    rng = np.random.default_rng(962)
    states = rng.uniform(0.0, 1.0, size=(3, 240))
    low = np.ones_like(states)
    high = np.full_like(states, np.e)
    close = np.exp(states)
    observed_v1 = v1.compute_intrabar_close_location_total_variation(
        high, low, close
    )
    observed_v2 = v2.compute_intrabar_close_location_total_variation(
        high, low, close
    )
    for left, right in zip(observed_v1, observed_v2, strict=True):
        assert np.array_equal(left, right, equal_nan=True)


def test_v2_redirects_only_freeze_test_and_runner_identity() -> None:
    assert v2.DEFAULT_IMPLEMENTATION_FREEZE.name.endswith(
        "campaign_096_feature_implementation_freeze_v2_20260807.json"
    )
    assert v2.TEST_PATH.name.endswith("campaign096_features_v2.py")
    assert v2._generated["__file__"] == str(v2.Path(v2.__file__).resolve())
