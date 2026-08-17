from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign062_features as c62


def _raw_session(date: str, symbol: str = "SZ000001") -> pd.DataFrame:
    day = pd.Timestamp(date)
    codes = sorted(c62.base.market.SOURCE_MINUTE_CODE_SET)
    return pd.DataFrame(
        {
            "datetime": [
                day + pd.Timedelta(hours=code // 60, minutes=code % 60)
                for code in codes
            ],
            "symbol": symbol,
            "provider": "tushare",
        }
    )


def test_protocol_and_comparison_order_are_frozen() -> None:
    spec = c62.load_protocol()
    comparisons = c62.reconstruct_comparisons(spec)
    assert len(comparisons) == 93
    assert comparisons[-1] == {
        "name": "intraday_day_over_day_realized_variance_stability_238b",
        "score_direction": "higher",
    }
    assert c62._comparison_order_digest(comparisons) == c62.COMPARISON_ORDER_SHA256


def test_reciprocal_peer_count_formula_and_range() -> None:
    values, eligible, quality = c62.compute_factor_values(
        np.array([1.0, 2.0, 5.0], dtype=float)
    )
    assert eligible[c62.FACTOR_NAME].tolist() == [True, True, True]
    assert values[c62.FACTOR_NAME].tolist() == pytest.approx([1.0, 0.5, 0.2])
    assert quality[f"{c62.FACTOR_NAME}__singleton_peer_group_rows"] == 1


def test_missing_noninteger_and_nonpositive_peer_counts_are_ineligible() -> None:
    values, eligible, quality = c62.compute_factor_values(
        np.array([np.nan, 0.0, -1.0, 1.5], dtype=float)
    )
    assert eligible[c62.FACTOR_NAME].tolist() == [False, False, False, False]
    assert np.isnan(values[c62.FACTOR_NAME]).all()
    assert quality[f"{c62.FACTOR_NAME}__no_prior_effective_disclosure_rows"] == 1
    assert quality[f"{c62.FACTOR_NAME}__nonpositive_peer_count_rows"] == 2
    assert quality[f"{c62.FACTOR_NAME}__noninteger_peer_count_rows"] == 1


def test_partition_uses_latest_effective_event_without_price_fields(monkeypatch) -> None:
    dates = [pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-03")]
    calendar = np.array(dates, dtype="datetime64[ns]")
    monkeypatch.setattr(
        c62,
        "_load_disclosure_events",
        lambda: (
            calendar,
            {
                "SZ000001": {
                    "effective_position": np.array([0, 1], dtype=np.int64),
                    "peer_count": np.array([4.0, 2.0], dtype=float),
                }
            },
        ),
    )
    raw = pd.concat([_raw_session(str(date.date())) for date in dates], ignore_index=True)
    base = pd.DataFrame(
        {
            "trade_date": dates,
            "symbol": ["SZ000001", "SZ000001"],
        }
    )
    frame, quality = c62.compute_partition_frame(
        raw, base, None, symbol="SZ000001"
    )
    assert tuple(raw.columns) == c62.RAW_COLUMNS
    assert frame[c62.FACTOR_NAME].tolist() == pytest.approx([0.25, 0.5])
    assert frame[f"{c62.FACTOR_NAME}_eligible"].tolist() == [True, True]
    assert quality[f"{c62.FACTOR_NAME}__eligible_rows"] == 2


def test_partition_before_first_effective_event_is_missing(monkeypatch) -> None:
    date = pd.Timestamp("2020-01-02")
    calendar = np.array([date], dtype="datetime64[ns]")
    monkeypatch.setattr(
        c62,
        "_load_disclosure_events",
        lambda: (calendar, {}),
    )
    base = pd.DataFrame(
        {
            "trade_date": [date],
            "symbol": ["SZ000001"],
        }
    )
    frame, quality = c62.compute_partition_frame(
        _raw_session("2020-01-02"), base, None, symbol="SZ000001"
    )
    assert np.isnan(frame[c62.FACTOR_NAME].iloc[0])
    assert not bool(frame[f"{c62.FACTOR_NAME}_eligible"].iloc[0])
    assert quality[f"{c62.FACTOR_NAME}__no_prior_effective_disclosure_rows"] == 1


def test_partition_rejects_extra_source_column(monkeypatch) -> None:
    raw = _raw_session("2020-01-02")
    raw["close"] = 1.0
    base = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2020-01-02")],
            "symbol": ["SZ000001"],
        }
    )
    monkeypatch.setattr(
        c62,
        "_load_disclosure_events",
        lambda: (np.array([pd.Timestamp("2020-01-02")], dtype="datetime64[ns]"), {}),
    )
    with pytest.raises(c62.Campaign062FeatureError, match="unexpected raw columns"):
        c62.compute_partition_frame(raw, base, None, symbol="SZ000001")
