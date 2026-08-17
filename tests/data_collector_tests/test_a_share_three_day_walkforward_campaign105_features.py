from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign105_features as campaign105


def _raw(
    volume: np.ndarray,
    amount: np.ndarray,
    *,
    opening_volume: float = 0.0,
    opening_amount: float = 0.0,
) -> pd.DataFrame:
    rows = []
    values = {
        code: (float(v), float(a))
        for code, v, a in zip(
            campaign105.CONTINUOUS_MINUTE_CODES, volume, amount, strict=True
        )
    }
    values[9 * 60 + 30] = (opening_volume, opening_amount)
    for code in sorted(campaign105.SOURCE_MINUTE_CODE_SET):
        v, a = values[code]
        rows.append(
            {
                "datetime": pd.Timestamp(2024, 1, 2, code // 60, code % 60),
                "symbol": "000001.SZ",
                "provider": "tushare",
                "volume": v,
                "amount": a,
            }
        )
    return pd.DataFrame(rows).loc[:, campaign105.RAW_COLUMNS]


def _score(volume: np.ndarray, amount: np.ndarray, **kwargs: float) -> float:
    frame, quality = campaign105.extract_active_trading_bar_share(
        _raw(volume, amount, **kwargs), symbol="000001.SZ"
    )
    assert quality["valid_activity_sessions"] == 1
    return float(frame.loc[0, "active_trading_bar_share"])


def test_protocol_and_exact_v62_order_are_prevalue_safe() -> None:
    spec = campaign105.load_protocol()
    comparisons = campaign105.reconstruct_comparisons()
    assert spec["candidate"]["name"] == campaign105.FACTOR_NAME
    assert len(comparisons) == 131
    assert (
        campaign105._order_digest(comparisons)
        == campaign105.NUMERIC_COMPARATOR_ORDER_SHA256
    )
    assert comparisons[-1] == {
        "name": "full_numeric_library_directional_rank_improvement_breadth_130f",
        "score_direction": "higher",
    }
    status = campaign105.status()
    assert status["source_fields_read_by_status"] == []
    assert status["candidate_or_comparison_values_read_by_status"] is False
    assert (
        status["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )


def test_all_joint_zero_and_all_joint_positive_are_valid_endpoints() -> None:
    zeros = np.zeros(240, dtype=np.float64)
    ones = np.ones(240, dtype=np.float64)
    assert _score(zeros, zeros) == 0.0
    assert _score(ones, ones * 100.0) == 1.0


def test_active_count_is_exact_and_activity_magnitude_or_order_is_unused() -> None:
    volume = np.zeros(240, dtype=np.float64)
    amount = np.zeros(240, dtype=np.float64)
    volume[:37] = np.arange(1.0, 38.0)
    amount[:37] = np.arange(1.0, 38.0) * 1_000_000.0
    assert _score(volume, amount) == pytest.approx(37.0 / 240.0, abs=1e-15)
    permutation = np.arange(240)[::-1]
    assert _score(volume[permutation], amount[permutation]) == pytest.approx(
        37.0 / 240.0, abs=1e-15
    )
    assert _score(volume * 7.0, amount * 0.25) == pytest.approx(37.0 / 240.0, abs=1e-15)


def test_invalid_cases_are_distinct_and_opening_row_is_not_in_formula() -> None:
    volume = np.ones(240, dtype=np.float64)
    amount = np.ones(240, dtype=np.float64)

    one_sided_volume = volume.copy()
    one_sided_volume[4] = 0.0
    frame, quality = campaign105.extract_active_trading_bar_share(
        _raw(one_sided_volume, amount), symbol="000001.SZ"
    )
    assert frame["active_trading_bar_share"].isna().all()
    assert quality["one_sided_zero_sessions"] == 1

    one_sided_amount = amount.copy()
    one_sided_amount[4] = 0.0
    frame, quality = campaign105.extract_active_trading_bar_share(
        _raw(volume, one_sided_amount), symbol="000001.SZ"
    )
    assert frame["active_trading_bar_share"].isna().all()
    assert quality["one_sided_zero_sessions"] == 1

    negative = volume.copy()
    negative[4] = -1.0
    frame, quality = campaign105.extract_active_trading_bar_share(
        _raw(negative, amount), symbol="000001.SZ"
    )
    assert frame["active_trading_bar_share"].isna().all()
    assert quality["invalid_numeric_sessions"] == 1

    nonfinite = amount.copy()
    nonfinite[4] = np.nan
    frame, quality = campaign105.extract_active_trading_bar_share(
        _raw(volume, nonfinite), symbol="000001.SZ"
    )
    assert frame["active_trading_bar_share"].isna().all()
    assert quality["invalid_numeric_sessions"] == 1

    assert (
        _score(
            volume,
            amount,
            opening_volume=0.0,
            opening_amount=999.0,
        )
        == 1.0
    )


def test_grid_and_discrete_output_semantics_fail_closed() -> None:
    raw = _raw(np.ones(240), np.ones(240)).iloc[:-1]
    with pytest.raises(campaign105.Campaign105FeatureError):
        campaign105.extract_active_trading_bar_share(raw, symbol="000001.SZ")

    assert campaign105.validate_value_semantics(campaign105.empty_output_frame()) == (
        0,
        0,
    )
    bad = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["000001.SZ"],
            "provider": ["tushare"],
            campaign105.FACTOR_NAME: [0.101],
            f"{campaign105.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, campaign105.OUTPUT_COLUMNS]
    with pytest.raises(campaign105.Campaign105FeatureError):
        campaign105.validate_value_semantics(bad)


def test_build_requires_explicit_confirmation_before_source_access() -> None:
    with pytest.raises(campaign105.Campaign105FeatureError, match="confirm-build"):
        campaign105.build_snapshot(
            data_root=campaign105.DEFAULT_DATA_ROOT,
            workers=1,
            confirm_build=False,
        )


def test_feature_code_does_not_name_price_or_return_columns_in_extractor() -> None:
    source = inspect.getsource(campaign105.extract_active_trading_bar_share)
    for forbidden in ("open", "high", "low", "close", "forward_return"):
        assert f'["{forbidden}"]' not in source


def test_implementation_freeze_is_live() -> None:
    freeze = campaign105._validate_implementation_freeze()
    assert (
        freeze["research_boundary"]["candidate_source_rows_read_before_freeze"] is False
    )
