from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign081_features as campaign081


def _raw_from_continuous_amounts(amounts: np.ndarray) -> pd.DataFrame:
    values = {
        code: float(value)
        for code, value in zip(campaign081.CONTINUOUS_MINUTE_CODES, amounts)
    }
    values[9 * 60 + 30] = 0.0
    rows = []
    for code in sorted(campaign081.SOURCE_MINUTE_CODE_SET):
        rows.append(
            {
                "datetime": pd.Timestamp(2024, 1, 2, code // 60, code % 60),
                "symbol": "000001.SZ",
                "provider": "tushare",
                "amount": values[code],
            }
        )
    return pd.DataFrame(rows).loc[:, campaign081.RAW_COLUMNS]


def _score(amounts: np.ndarray) -> float:
    frame, quality = campaign081.extract_amount_path_efficiency(
        _raw_from_continuous_amounts(amounts), symbol="000001.SZ"
    )
    assert quality["valid_amount_path_efficiency_sessions"] == 1
    return float(frame.loc[0, "amount_path_efficiency"])


def test_frozen_orders_protocol_and_status_are_prevalue_safe() -> None:
    spec = campaign081.load_protocol()
    assert spec["candidate"]["name"] == campaign081.FACTOR_NAME
    comparisons = campaign081.reconstruct_comparisons()
    complete = campaign081.reconstruct_complete_definitions()
    assert len(comparisons) == 110
    assert len(complete) == 112
    assert comparisons[-1] == {
        "name": "intraday_above_median_amount_longest_run_240m",
        "score_direction": "higher",
    }
    assert complete[-1] == {
        "name": "intraday_above_median_amount_longest_run_240m",
        "score_direction": "higher",
    }
    status = campaign081.status(campaign081.DEFAULT_DATA_ROOT)
    assert status["source_fields_read_by_status"] == []
    assert status["candidate_or_comparison_values_read_by_status"] is False
    assert status["historical_daily_price_or_forward_return_values_read_by_status"] is False


def test_monotone_zigzag_and_half_reversal_semantics() -> None:
    monotone_x = np.concatenate(
        [np.linspace(0.0, 3.0, 120), np.linspace(5.0, 1.0, 120)]
    )
    monotone = np.expm1(monotone_x)
    assert _score(monotone) == pytest.approx(1.0, abs=1e-15)

    zigzag_x = np.concatenate(
        [np.tile(np.array([0.0, 1.0]), 60), np.zeros(120)]
    )
    zigzag = np.expm1(zigzag_x)
    assert _score(zigzag) == pytest.approx(1.0 / 119.0, abs=1e-15)

    profile_x = np.concatenate(
        [np.array([float((index * 37) % 121) / 20.0 for index in range(120)]),
         np.array([float((index * 53) % 127) / 20.0 for index in range(120)])]
    )
    profile = np.expm1(profile_x)
    reversed_halves = np.expm1(
        np.concatenate([profile_x[:120][::-1], profile_x[120:][::-1]])
    )
    assert _score(profile) == pytest.approx(_score(reversed_halves), abs=1e-15)


def test_lunch_is_a_hard_path_boundary() -> None:
    base_x = np.concatenate(
        [np.linspace(0.0, 1.0, 120), np.linspace(20.0, 19.0, 120)]
    )
    translated_afternoon_x = base_x.copy()
    translated_afternoon_x[120:] += 50.0
    assert _score(np.expm1(base_x)) == pytest.approx(1.0, abs=1e-15)
    assert _score(np.expm1(translated_afternoon_x)) == pytest.approx(
        1.0, abs=1e-15
    )


def test_invalid_amounts_are_missing_without_imputation() -> None:
    negative = np.ones(240, dtype=np.float64)
    negative[8] = -1.0
    frame, quality = campaign081.extract_amount_path_efficiency(
        _raw_from_continuous_amounts(negative), symbol="000001.SZ"
    )
    assert frame["amount_path_efficiency"].isna().all()
    assert quality["invalid_amount_grid_sessions"] == 1

    zero = np.zeros(240, dtype=np.float64)
    frame, quality = campaign081.extract_amount_path_efficiency(
        _raw_from_continuous_amounts(zero), symbol="000001.SZ"
    )
    assert frame["amount_path_efficiency"].isna().all()
    assert quality["zero_total_variation_sessions"] == 1


def test_grid_identity_and_output_semantics_fail_closed() -> None:
    raw = _raw_from_continuous_amounts(np.ones(240, dtype=np.float64)).iloc[:-1]
    with pytest.raises(campaign081.Campaign081FeatureError):
        campaign081.extract_amount_path_efficiency(raw, symbol="000001.SZ")

    output = campaign081.empty_output_frame()
    assert campaign081.validate_value_semantics(output) == (0, 0)
    bad = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["000001.SZ"],
            "provider": ["tushare"],
            campaign081.FACTOR_NAME: [1.001],
            f"{campaign081.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, campaign081.OUTPUT_COLUMNS]
    with pytest.raises(campaign081.Campaign081FeatureError):
        campaign081.validate_value_semantics(bad)


def test_feature_implementation_freeze_is_live() -> None:
    freeze = campaign081._validate_implementation_freeze()
    assert freeze["research_boundary"]["candidate_source_rows_read_before_freeze"] is False
    assert Path(freeze["feature_runner"]["path"]).name == Path(campaign081.__file__).name
