from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign078_features as campaign078


def _raw_from_continuous_amounts(amounts: np.ndarray) -> pd.DataFrame:
    values = {code: float(value) for code, value in zip(campaign078.CONTINUOUS_MINUTE_CODES, amounts)}
    values[9 * 60 + 30] = 0.0
    rows = []
    for code in sorted(campaign078.SOURCE_MINUTE_CODE_SET):
        rows.append(
            {
                "datetime": pd.Timestamp(2024, 1, 2, code // 60, code % 60),
                "symbol": "000001.SZ",
                "provider": "tushare",
                "amount": values[code],
            }
        )
    return pd.DataFrame(rows).loc[:, campaign078.RAW_COLUMNS]


def _score(amounts: np.ndarray) -> float:
    frame, quality = campaign078.extract_amount_local_peak_density(
        _raw_from_continuous_amounts(amounts), symbol="000001.SZ"
    )
    assert quality["valid_amount_local_peak_density_sessions"] == 1
    return float(frame.loc[0, "amount_local_peak_density"])


def test_frozen_orders_protocol_and_status_are_prevalue_safe() -> None:
    spec = campaign078.load_protocol()
    assert spec["candidate"]["name"] == campaign078.FACTOR_NAME
    comparisons = campaign078.reconstruct_comparisons()
    complete = campaign078.reconstruct_complete_definitions()
    assert len(comparisons) == 108
    assert len(complete) == 109
    assert comparisons[-1] == {
        "name": "intraday_amount_clock_dispersion_240m",
        "score_direction": "higher",
    }
    status = campaign078.status(campaign078.DEFAULT_DATA_ROOT)
    assert status["source_fields_read_by_status"] == []
    assert status["candidate_or_comparison_values_read_by_status"] is False
    assert status["historical_daily_price_or_forward_return_values_read_by_status"] is False


def test_amount_local_peak_density_endpoints_scale_reversal_and_ties() -> None:
    alternating = np.zeros(240, dtype=np.float64)
    alternating[1:239:2] = 1.0
    assert _score(alternating) == pytest.approx(1.0, abs=1e-15)

    monotone = np.arange(1.0, 241.0)
    assert _score(monotone) == pytest.approx(0.0, abs=1e-15)

    profile = np.array([float((index * 37) % 241 + 1) for index in range(240)])
    assert _score(profile) == pytest.approx(_score(profile * 123.0), abs=1e-15)
    assert _score(profile) == pytest.approx(_score(profile[::-1]), abs=1e-15)
    assert _score(profile) == pytest.approx(_score(np.square(profile)), abs=1e-15)

    ties = np.ones(240, dtype=np.float64)
    assert _score(ties) == pytest.approx(0.0, abs=1e-15)


def test_invalid_amounts_are_missing_without_imputation() -> None:
    negative = np.ones(240, dtype=np.float64)
    negative[8] = -1.0
    frame, quality = campaign078.extract_amount_local_peak_density(
        _raw_from_continuous_amounts(negative), symbol="000001.SZ"
    )
    assert frame["amount_local_peak_density"].isna().all()
    assert quality["invalid_amount_grid_sessions"] == 1

    zero = np.zeros(240, dtype=np.float64)
    frame, quality = campaign078.extract_amount_local_peak_density(
        _raw_from_continuous_amounts(zero), symbol="000001.SZ"
    )
    assert frame["amount_local_peak_density"].isna().all()
    assert quality["nonpositive_total_amount_sessions"] == 1


def test_grid_identity_and_output_semantics_fail_closed() -> None:
    raw = _raw_from_continuous_amounts(np.ones(240, dtype=np.float64)).iloc[:-1]
    with pytest.raises(campaign078.Campaign078FeatureError):
        campaign078.extract_amount_local_peak_density(raw, symbol="000001.SZ")

    output = campaign078.empty_output_frame()
    assert campaign078.validate_value_semantics(output) == (0, 0)
    bad = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["000001.SZ"],
            "provider": ["tushare"],
            campaign078.FACTOR_NAME: [1.1],
            f"{campaign078.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, campaign078.OUTPUT_COLUMNS]
    with pytest.raises(campaign078.Campaign078FeatureError):
        campaign078.validate_value_semantics(bad)


def test_feature_implementation_freeze_is_live() -> None:
    freeze = campaign078._validate_implementation_freeze()
    assert freeze["research_boundary"]["candidate_source_rows_read_before_freeze"] is False
    assert Path(freeze["feature_runner"]["path"]).name == Path(campaign078.__file__).name
