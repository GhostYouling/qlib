from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign077_features as campaign077


def _raw_from_continuous_amounts(amounts: np.ndarray) -> pd.DataFrame:
    values = {code: float(value) for code, value in zip(campaign077.CONTINUOUS_MINUTE_CODES, amounts)}
    values[9 * 60 + 30] = 0.0
    rows = []
    for code in sorted(campaign077.SOURCE_MINUTE_CODE_SET):
        rows.append(
            {
                "datetime": pd.Timestamp(2024, 1, 2, code // 60, code % 60),
                "symbol": "000001.SZ",
                "provider": "tushare",
                "amount": values[code],
            }
        )
    return pd.DataFrame(rows).loc[:, campaign077.RAW_COLUMNS]


def _score(amounts: np.ndarray) -> float:
    frame, quality = campaign077.extract_amount_clock_dispersion(
        _raw_from_continuous_amounts(amounts), symbol="000001.SZ"
    )
    assert quality["valid_amount_clock_dispersion_sessions"] == 1
    return float(frame.loc[0, "amount_clock_dispersion"])


def test_frozen_orders_protocol_and_status_are_prevalue_safe() -> None:
    spec = campaign077.load_protocol()
    assert spec["candidate"]["name"] == campaign077.FACTOR_NAME
    comparisons = campaign077.reconstruct_comparisons()
    complete = campaign077.reconstruct_complete_definitions()
    assert len(comparisons) == 107
    assert len(complete) == 108
    assert comparisons[-1] == {
        "name": "intraday_peak_amount_bar_recency_240m",
        "score_direction": "higher",
    }
    status = campaign077.status(campaign077.DEFAULT_DATA_ROOT)
    assert status["source_fields_read_by_status"] == []
    assert status["candidate_or_comparison_values_read_by_status"] is False
    assert status["historical_daily_price_or_forward_return_values_read_by_status"] is False


def test_amount_clock_dispersion_endpoints_scale_reversal_and_uniform() -> None:
    endpoint = np.zeros(240, dtype=np.float64)
    endpoint[0] = 1.0
    endpoint[-1] = 1.0
    assert _score(endpoint) == pytest.approx(1.0, abs=1e-15)

    point = np.zeros(240, dtype=np.float64)
    point[73] = 7.0
    assert _score(point) == pytest.approx(0.0, abs=1e-15)

    profile = np.arange(1.0, 241.0)
    assert _score(profile) == pytest.approx(_score(profile * 123.0), abs=1e-15)
    assert _score(profile) == pytest.approx(_score(profile[::-1]), abs=1e-15)

    uniform = np.ones(240, dtype=np.float64)
    expected = (240.0 + 1.0) / (3.0 * (240.0 - 1.0))
    assert _score(uniform) == pytest.approx(expected, abs=1e-15)


def test_invalid_amounts_are_missing_without_imputation() -> None:
    negative = np.ones(240, dtype=np.float64)
    negative[8] = -1.0
    frame, quality = campaign077.extract_amount_clock_dispersion(
        _raw_from_continuous_amounts(negative), symbol="000001.SZ"
    )
    assert frame["amount_clock_dispersion"].isna().all()
    assert quality["invalid_amount_grid_sessions"] == 1

    zero = np.zeros(240, dtype=np.float64)
    frame, quality = campaign077.extract_amount_clock_dispersion(
        _raw_from_continuous_amounts(zero), symbol="000001.SZ"
    )
    assert frame["amount_clock_dispersion"].isna().all()
    assert quality["nonpositive_total_amount_sessions"] == 1


def test_grid_identity_and_output_semantics_fail_closed() -> None:
    raw = _raw_from_continuous_amounts(np.ones(240, dtype=np.float64)).iloc[:-1]
    with pytest.raises(campaign077.Campaign077FeatureError):
        campaign077.extract_amount_clock_dispersion(raw, symbol="000001.SZ")

    output = campaign077.empty_output_frame()
    assert campaign077.validate_value_semantics(output) == (0, 0)
    bad = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["000001.SZ"],
            "provider": ["tushare"],
            campaign077.FACTOR_NAME: [1.1],
            f"{campaign077.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, campaign077.OUTPUT_COLUMNS]
    with pytest.raises(campaign077.Campaign077FeatureError):
        campaign077.validate_value_semantics(bad)


def test_feature_implementation_freeze_is_live() -> None:
    freeze = campaign077._validate_implementation_freeze()
    assert freeze["research_boundary"]["candidate_source_rows_read_before_freeze"] is False
    assert Path(freeze["feature_runner"]["path"]).name == Path(campaign077.__file__).name
