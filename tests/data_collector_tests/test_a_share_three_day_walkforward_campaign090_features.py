from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign090_features as features


def _raw_frame(*, uniform_range: bool = False, terminal_only: bool = False) -> pd.DataFrame:
    date = pd.Timestamp("2024-01-02")
    codes = tuple(sorted(features.c86.SOURCE_MINUTE_CODE_SET))
    datetimes = [date + pd.Timedelta(minutes=int(code)) for code in codes]
    high = np.ones(len(codes), dtype=np.float64)
    low = np.ones(len(codes), dtype=np.float64)
    selected = np.array(
        [code in features.c86.CONTINUOUS_MINUTE_CODE_SET for code in codes],
        dtype=bool,
    )
    if uniform_range:
        high[selected] = np.e
    if terminal_only:
        high[np.array(codes) == 15 * 60] = np.e
    return pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "SH600000",
            "provider": "tushare",
            "high": high,
            "low": low,
        }
    ).loc[:, features.RAW_COLUMNS]


def test_campaign090_formula_has_frozen_clock_endpoints() -> None:
    high = np.ones((4, 240), dtype=np.float64)
    low = np.ones((4, 240), dtype=np.float64)
    high[0, :] = np.e
    high[1, 0] = np.e
    high[2, -1] = np.e
    high[3, 20] = 0.5
    values, eligible, totals, ranges = features.compute_range_clock_center(high, low)
    assert values[0] == 0.5
    assert values[1] == 0.0
    assert values[2] == 1.0
    assert np.isnan(values[3])
    assert eligible.tolist() == [True, True, True, False]
    assert np.allclose(totals[:3], [240.0, 1.0, 1.0])
    assert ranges.shape == (4, 240)


def test_campaign090_zero_total_range_is_missing() -> None:
    high = np.ones((1, 240), dtype=np.float64)
    low = np.ones((1, 240), dtype=np.float64)
    values, eligible, totals, _ranges = features.compute_range_clock_center(high, low)
    assert np.isnan(values[0])
    assert eligible.tolist() == [False]
    assert totals.tolist() == [0.0]


def test_campaign090_extracts_exact_fixed_grid_without_0930() -> None:
    uniform, quality = features.extract_range_clock_center(
        _raw_frame(uniform_range=True), symbol="SH600000"
    )
    terminal, terminal_quality = features.extract_range_clock_center(
        _raw_frame(terminal_only=True), symbol="SH600000"
    )
    assert uniform[features.FACTOR_NAME].tolist() == [0.5]
    assert terminal[features.FACTOR_NAME].tolist() == [1.0]
    assert quality["source_rows"] == 241
    assert quality["source_sessions"] == 1
    assert quality["valid_range_clock_center_sessions"] == 1
    assert quality["zero_range_bars"] == 0
    assert terminal_quality["zero_range_bars"] == 239


def test_campaign090_protocol_and_frozen_orders_are_value_free() -> None:
    protocol = features.load_protocol()
    comparisons = features.reconstruct_comparisons()
    definitions = features.reconstruct_complete_definitions()
    assert protocol["candidate"]["name"] == features.FACTOR_NAME
    assert protocol["candidate"]["minute_source_projection"] == list(
        features.RAW_COLUMNS
    )
    assert len(comparisons) == 119
    assert len(definitions) == 121
    assert comparisons[-1] == {
        "name": "intraday_directional_amount_timing_spread_238m",
        "score_direction": "higher",
    }
    assert definitions[-1] == comparisons[-1]


def test_campaign090_status_is_read_only() -> None:
    payload = features.status(features.DEFAULT_DATA_ROOT)
    assert payload["source_rows_read_by_status"] is False
    assert payload["candidate_values_computed_by_status"] is False
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_or_forward_return_values_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False
