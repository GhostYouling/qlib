from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign086_features as campaign086


def _arrays(states: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.asarray(states, dtype=np.float64)
    assert x.shape == (240,)
    low = np.full((1, 240), 100.0, dtype=np.float64)
    high = np.full((1, 240), 110.0, dtype=np.float64)
    close = low * np.exp(x.reshape(1, 240) * np.log(high / low))
    return high, low, close


def _raw(states: np.ndarray) -> pd.DataFrame:
    high, low, close = _arrays(states)
    by_code = {
        code: (float(high[0, index]), float(low[0, index]), float(close[0, index]))
        for index, code in enumerate(campaign086.CONTINUOUS_MINUTE_CODES)
    }
    by_code[9 * 60 + 30] = (100.0, 100.0, 100.0)
    rows = []
    for code in sorted(campaign086.SOURCE_MINUTE_CODE_SET):
        h, low_value, c = by_code[code]
        rows.append(
            {
                "datetime": pd.Timestamp(2024, 1, 2, code // 60, code % 60),
                "symbol": "000001.SZ",
                "provider": "tushare",
                "high": h,
                "low": low_value,
                "close": c,
            }
        )
    return pd.DataFrame(rows).loc[:, campaign086.RAW_COLUMNS]


def test_protocol_orders_and_status_are_prevalue_safe() -> None:
    spec = campaign086.load_protocol()
    assert spec["candidate"]["name"] == campaign086.FACTOR_NAME
    comparisons = campaign086.reconstruct_comparisons()
    complete = campaign086.reconstruct_complete_definitions()
    assert len(comparisons) == 115
    assert len(complete) == 117
    assert comparisons[-1] == {
        "name": "quarterly_freshness_market_neutral_late_drift_confirmation_product_2r",
        "score_direction": "higher",
    }
    status = campaign086.status()
    assert status["source_rows_read_by_status"] is False
    assert status["candidate_values_computed_by_status"] is False
    assert status["comparison_values_read_by_status"] is False


def test_positive_and_negative_serial_endpoints() -> None:
    positive_half = np.linspace(0.05, 0.95, 120)
    positive = np.concatenate((positive_half, positive_half))
    high, low, close = _arrays(positive)
    values, eligible, pairs = campaign086.compute_serial_persistence(high, low, close)
    assert eligible.tolist() == [True]
    assert pairs.tolist() == [238]
    assert values[0] == pytest.approx(1.0, abs=1e-12)

    negative_half = np.tile(np.array([0.1, 0.9]), 60)
    negative = np.concatenate((negative_half, negative_half))
    high, low, close = _arrays(negative)
    values, eligible, pairs = campaign086.compute_serial_persistence(high, low, close)
    assert eligible.tolist() == [True]
    assert pairs.tolist() == [238]
    assert values[0] == pytest.approx(0.0, abs=1e-12)


def test_zero_range_removes_only_incident_pairs_without_bridging() -> None:
    states = np.concatenate(
        (np.linspace(0.05, 0.95, 120), np.linspace(0.1, 0.9, 120))
    )
    high, low, close = _arrays(states)
    high[0, 50] = low[0, 50]
    close[0, 50] = low[0, 50]
    values, eligible, pairs = campaign086.compute_serial_persistence(high, low, close)
    assert pairs.tolist() == [236]
    assert eligible.tolist() == [True]
    assert np.isfinite(values[0])


def test_lunch_pair_is_excluded() -> None:
    states = np.concatenate(
        (np.linspace(0.05, 0.95, 120), np.linspace(0.95, 0.05, 120))
    )
    high, low, close = _arrays(states)
    _values, _eligible, pairs = campaign086.compute_serial_persistence(
        high, low, close
    )
    assert pairs.tolist() == [238]


def test_constant_state_and_invalid_source_are_missing() -> None:
    high, low, close = _arrays(np.full(240, 0.5))
    values, eligible, pairs = campaign086.compute_serial_persistence(high, low, close)
    assert pairs.tolist() == [238]
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])

    close[0, 1] = high[0, 1] + 1.0
    values, eligible, _pairs = campaign086.compute_serial_persistence(high, low, close)
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])


def test_minimum_informative_pair_gate() -> None:
    states = np.concatenate(
        (np.linspace(0.05, 0.95, 120), np.linspace(0.1, 0.9, 120))
    )
    high, low, close = _arrays(states)
    high[0, ::2] = low[0, ::2]
    close[0, ::2] = low[0, ::2]
    values, eligible, pairs = campaign086.compute_serial_persistence(high, low, close)
    assert pairs[0] < 120
    assert eligible.tolist() == [False]
    assert np.isnan(values[0])


def test_positive_scale_invariance_and_raw_grid() -> None:
    states = np.concatenate(
        (np.linspace(0.05, 0.95, 120), np.linspace(0.1, 0.9, 120))
    )
    raw = _raw(states)
    base, quality = campaign086.extract_serial_persistence(raw, symbol="000001.SZ")
    assert quality["valid_serial_persistence_sessions"] == 1
    scaled = raw.copy()
    scaled[["high", "low", "close"]] *= 7.0
    other, _quality = campaign086.extract_serial_persistence(
        scaled, symbol="000001.SZ"
    )
    assert other.loc[0, campaign086.FACTOR_NAME] == pytest.approx(
        base.loc[0, campaign086.FACTOR_NAME], abs=1e-12
    )
    with pytest.raises(campaign086.Campaign086FeatureError):
        campaign086.extract_serial_persistence(raw.iloc[:-1], symbol="000001.SZ")


def test_compact_stock_day_key_matches_frozen_encoding() -> None:
    keys = campaign086.compact_stock_day_keys(
        pd.Series([pd.Timestamp("2024-01-02")]), pd.Series(["000001.SZ"])
    )
    day = np.datetime64("2024-01-02", "D").astype(np.int64)
    assert keys.tolist() == [int(day * 4_000_000 + 2_000_001)]


def test_serial_persistence_rejects_wrong_shape() -> None:
    bad = np.ones((1, 239), dtype=np.float64)
    with pytest.raises(campaign086.Campaign086FeatureError):
        campaign086.compute_serial_persistence(bad, bad, bad)
