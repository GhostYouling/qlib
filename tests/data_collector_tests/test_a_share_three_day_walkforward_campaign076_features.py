from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign076_features as c76


def _raw(amounts: np.ndarray, *, symbol: str = "000001.SZ") -> pd.DataFrame:
    continuous = list(c76.CONTINUOUS_MINUTE_CODES)
    codes = [570, *continuous]
    assert len(codes) == c76.SOURCE_BAR_COUNT
    times = [pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code)) for code in codes]
    return pd.DataFrame(
        {
            "datetime": times,
            "symbol": symbol,
            "provider": "tushare",
            "amount": np.concatenate([[1.0], amounts.astype(float)]),
        }
    ).loc[:, c76.RAW_COLUMNS]


def test_latest_exact_maximum_tie_is_frozen() -> None:
    amounts = np.ones(c76.SELECTED_BAR_COUNT)
    amounts[4] = 10.0
    amounts[200] = 10.0
    frame, quality = c76.extract_peak_amount_recency(_raw(amounts), symbol="000001.SZ")
    assert frame.loc[0, "peak_amount_bar_recency"] == pytest.approx(200.0 / 239.0)
    assert quality["valid_peak_recency_sessions"] == 1


def test_first_and_last_endpoints_are_inclusive() -> None:
    first = np.ones(c76.SELECTED_BAR_COUNT); first[0] = 2.0
    last = np.ones(c76.SELECTED_BAR_COUNT); last[-1] = 2.0
    out_first, _ = c76.extract_peak_amount_recency(_raw(first), symbol="000001.SZ")
    out_last, _ = c76.extract_peak_amount_recency(_raw(last), symbol="000001.SZ")
    assert out_first.loc[0, "peak_amount_bar_recency"] == 0.0
    assert out_last.loc[0, "peak_amount_bar_recency"] == 1.0


@pytest.mark.parametrize("bad", [np.nan, -1.0])
def test_nonfinite_or_negative_amount_makes_session_missing(bad: float) -> None:
    amounts = np.ones(c76.SELECTED_BAR_COUNT); amounts[20] = bad
    frame, quality = c76.extract_peak_amount_recency(_raw(amounts), symbol="000001.SZ")
    assert pd.isna(frame.loc[0, "peak_amount_bar_recency"])
    assert quality["invalid_amount_grid_sessions"] == 1


def test_zero_total_makes_session_missing() -> None:
    frame, quality = c76.extract_peak_amount_recency(_raw(np.zeros(c76.SELECTED_BAR_COUNT)), symbol="000001.SZ")
    assert pd.isna(frame.loc[0, "peak_amount_bar_recency"])
    assert quality["nonpositive_total_amount_sessions"] == 1


def test_grid_mismatch_fails_closed() -> None:
    raw = _raw(np.ones(c76.SELECTED_BAR_COUNT)).iloc[:-1].copy()
    with pytest.raises(c76.Campaign076FeatureError, match="grid changed"):
        c76.extract_peak_amount_recency(raw, symbol="000001.SZ")


def test_finalize_and_value_semantics_preserve_discrete_grid() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-02", "2020-01-03"]),
            "symbol": ["000001.SZ", "000001.SZ"],
            "provider": ["tushare", "tushare"],
            "peak_amount_bar_recency": [10.0 / 239.0, np.nan],
        }
    )
    out = c76.finalize_feature_frame(frame).loc[:, c76.OUTPUT_COLUMNS]
    assert c76.validate_value_semantics(out) == (2, 1)
    out.loc[0, c76.FACTOR_NAME] = 0.123
    with pytest.raises(c76.Campaign076FeatureError, match="value semantics"):
        c76.validate_value_semantics(out)


def test_protocol_and_definition_orders_are_bound_without_values() -> None:
    spec = c76.load_protocol()
    assert spec["candidate"]["name"] == c76.FACTOR_NAME
    assert len(c76.reconstruct_complete_definitions()) == 107
    assert len(c76.reconstruct_comparisons()) == 106


def test_status_is_read_only_before_build() -> None:
    result = c76.status(c76.DEFAULT_DATA_ROOT)
    assert result["candidate_or_comparison_values_read_by_status"] is False
    assert result["provider_request_issued_by_status"] is False
