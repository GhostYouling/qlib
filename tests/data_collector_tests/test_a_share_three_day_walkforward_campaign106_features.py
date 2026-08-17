from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign106_features as campaign106


def _raw(
    highs: np.ndarray,
    lows: np.ndarray,
    *,
    opening_high: float = 1.0,
    opening_low: float = 1.0,
) -> pd.DataFrame:
    values = {
        code: (float(high), float(low))
        for code, high, low in zip(
            campaign106.CONTINUOUS_MINUTE_CODES, highs, lows, strict=True
        )
    }
    values[9 * 60 + 30] = (opening_high, opening_low)
    rows = []
    for code in sorted(campaign106.SOURCE_MINUTE_CODE_SET):
        high, low = values[code]
        rows.append(
            {
                "datetime": pd.Timestamp(2024, 1, 2, code // 60, code % 60),
                "symbol": "000001.SZ",
                "provider": "tushare",
                "high": high,
                "low": low,
            }
        )
    return pd.DataFrame(rows).loc[:, campaign106.RAW_COLUMNS]


def _score(highs: np.ndarray, lows: np.ndarray, **kwargs: float) -> float:
    frame, quality = campaign106.extract_nonzero_range_bar_share(
        _raw(highs, lows, **kwargs), symbol="000001.SZ"
    )
    assert quality["valid_range_occupancy_sessions"] == 1
    return float(frame.loc[0, "nonzero_range_bar_share"])


def test_protocol_and_exact_v63_orders_are_prevalue_safe() -> None:
    spec = campaign106.load_protocol()
    comparisons = campaign106.reconstruct_comparisons()
    definitions = campaign106.reconstruct_complete_definitions()
    assert spec["candidate"]["name"] == campaign106.FACTOR_NAME
    assert len(comparisons) == 132
    assert campaign106._order_digest(comparisons) == campaign106.NUMERIC_COMPARATOR_ORDER_SHA256
    assert len(definitions) == 135
    assert campaign106._order_digest(definitions) == campaign106.COMPLETE_DEFINITION_ORDER_SHA256
    assert comparisons[-1] == {
        "name": "intraday_active_trading_bar_share_240m",
        "score_direction": "higher",
    }
    status = campaign106.status()
    assert status["source_fields_read_by_status"] == []
    assert status["candidate_or_comparison_values_read_by_status"] is False
    assert status["historical_daily_price_or_forward_return_values_read_by_status"] is False


def test_all_zero_range_and_all_positive_range_are_valid_endpoints() -> None:
    lows = np.full(240, 10.0, dtype=np.float64)
    assert _score(lows.copy(), lows) == 0.0
    assert _score(lows + 0.01, lows) == 1.0


def test_count_is_exact_and_range_magnitude_or_clock_order_is_unused() -> None:
    lows = np.full(240, 10.0, dtype=np.float64)
    highs = lows.copy()
    highs[:37] += np.arange(1.0, 38.0) / 100.0
    assert _score(highs, lows) == pytest.approx(37.0 / 240.0, abs=1e-15)
    permutation = np.arange(240)[::-1]
    assert _score(highs[permutation], lows[permutation]) == pytest.approx(
        37.0 / 240.0, abs=1e-15
    )
    scaled = lows.copy()
    scaled[:37] += 100.0
    assert _score(scaled, lows) == pytest.approx(37.0 / 240.0, abs=1e-15)


def test_invalid_selected_values_fail_closed_but_opening_row_is_unused() -> None:
    lows = np.full(240, 10.0, dtype=np.float64)
    highs = lows + 0.1

    reversed_bar = lows.copy()
    reversed_bar[4] = 10.2
    frame, quality = campaign106.extract_nonzero_range_bar_share(
        _raw(highs, reversed_bar), symbol="000001.SZ"
    )
    assert frame["nonzero_range_bar_share"].isna().all()
    assert quality["invalid_ordered_range_sessions"] == 1

    nonpositive = lows.copy()
    nonpositive[4] = 0.0
    frame, quality = campaign106.extract_nonzero_range_bar_share(
        _raw(highs, nonpositive), symbol="000001.SZ"
    )
    assert frame["nonzero_range_bar_share"].isna().all()
    assert quality["invalid_numeric_sessions"] == 1

    nonfinite = highs.copy()
    nonfinite[4] = np.nan
    frame, quality = campaign106.extract_nonzero_range_bar_share(
        _raw(nonfinite, lows), symbol="000001.SZ"
    )
    assert frame["nonzero_range_bar_share"].isna().all()
    assert quality["invalid_numeric_sessions"] == 1

    assert _score(highs, lows, opening_high=0.0, opening_low=999.0) == 1.0


def test_grid_and_discrete_output_semantics_fail_closed() -> None:
    raw = _raw(np.full(240, 10.1), np.full(240, 10.0)).iloc[:-1]
    with pytest.raises(campaign106.Campaign106FeatureError):
        campaign106.extract_nonzero_range_bar_share(raw, symbol="000001.SZ")

    assert campaign106.validate_value_semantics(campaign106.empty_output_frame()) == (0, 0)
    bad = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["000001.SZ"],
            "provider": ["tushare"],
            campaign106.FACTOR_NAME: [0.101],
            f"{campaign106.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, campaign106.OUTPUT_COLUMNS]
    with pytest.raises(campaign106.Campaign106FeatureError):
        campaign106.validate_value_semantics(bad)


def test_build_requires_explicit_confirmation_before_source_access() -> None:
    with pytest.raises(campaign106.Campaign106FeatureError, match="confirm-build"):
        campaign106.build_snapshot(
            data_root=campaign106.DEFAULT_DATA_ROOT,
            workers=1,
            confirm_build=False,
        )


def test_extractor_uses_only_frozen_high_low_projection() -> None:
    source = inspect.getsource(campaign106.extract_nonzero_range_bar_share)
    for forbidden in ("open", "close", "volume", "amount", "forward_return"):
        assert f'["{forbidden}"]' not in source


def test_implementation_freeze_is_live() -> None:
    freeze = campaign106._validate_implementation_freeze()
    assert freeze["numeric_comparator_count"] == 132
    assert freeze["research_boundary"]["candidate_source_rows_read_before_freeze"] is False

