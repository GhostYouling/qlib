from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign080_features as campaign080


def _raw_from_continuous_amounts(amounts: np.ndarray) -> pd.DataFrame:
    values = {
        code: float(value)
        for code, value in zip(campaign080.CONTINUOUS_MINUTE_CODES, amounts)
    }
    values[9 * 60 + 30] = 0.0
    rows = []
    for code in sorted(campaign080.SOURCE_MINUTE_CODE_SET):
        rows.append(
            {
                "datetime": pd.Timestamp(2024, 1, 2, code // 60, code % 60),
                "symbol": "000001.SZ",
                "provider": "tushare",
                "amount": values[code],
            }
        )
    return pd.DataFrame(rows).loc[:, campaign080.RAW_COLUMNS]


def _score(amounts: np.ndarray) -> float:
    frame, quality = campaign080.extract_above_median_amount_longest_run(
        _raw_from_continuous_amounts(amounts), symbol="000001.SZ"
    )
    assert quality["valid_above_median_amount_longest_run_sessions"] == 1
    return float(frame.loc[0, "above_median_amount_longest_run"])


def test_frozen_orders_protocol_and_status_are_prevalue_safe() -> None:
    spec = campaign080.load_protocol()
    assert spec["candidate"]["name"] == campaign080.FACTOR_NAME
    comparisons = campaign080.reconstruct_comparisons()
    complete = campaign080.reconstruct_complete_definitions()
    assert len(comparisons) == 109
    assert len(complete) == 111
    assert comparisons[-1] == {
        "name": "intraday_amount_local_peak_density_238p",
        "score_direction": "higher",
    }
    assert complete[-1] == {
        "name": "signal_day_turnover_rate_pct",
        "score_direction": "higher",
    }
    status = campaign080.status(campaign080.DEFAULT_DATA_ROOT)
    assert status["source_fields_read_by_status"] == []
    assert status["candidate_or_comparison_values_read_by_status"] is False
    assert status["historical_daily_price_or_forward_return_values_read_by_status"] is False


def test_longest_run_endpoints_fragmentation_scale_transform_and_ties() -> None:
    one_half_high = np.concatenate([np.ones(120), np.zeros(120)])
    assert _score(one_half_high) == pytest.approx(1.0, abs=1e-15)

    fragmented = np.tile(np.array([0.0, 1.0]), 120)
    assert _score(fragmented) == pytest.approx(1.0 / 120.0, abs=1e-15)

    profile = np.array([float((index * 37) % 241 + 1) for index in range(240)])
    reversed_halves = np.concatenate([profile[:120][::-1], profile[120:][::-1]])
    assert _score(profile) == pytest.approx(_score(profile * 123.0), abs=1e-15)
    assert _score(profile) == pytest.approx(_score(np.square(profile)), abs=1e-15)
    assert _score(profile) == pytest.approx(_score(reversed_halves), abs=1e-15)

    ties = np.ones(240, dtype=np.float64)
    assert _score(ties) == pytest.approx(0.0, abs=1e-15)


def test_lunch_is_a_hard_run_boundary() -> None:
    amounts = np.zeros(240, dtype=np.float64)
    amounts[110:130] = 1.0
    assert _score(amounts) == pytest.approx(10.0 / 120.0, abs=1e-15)


def test_invalid_amounts_are_missing_without_imputation() -> None:
    negative = np.ones(240, dtype=np.float64)
    negative[8] = -1.0
    frame, quality = campaign080.extract_above_median_amount_longest_run(
        _raw_from_continuous_amounts(negative), symbol="000001.SZ"
    )
    assert frame["above_median_amount_longest_run"].isna().all()
    assert quality["invalid_amount_grid_sessions"] == 1

    zero = np.zeros(240, dtype=np.float64)
    frame, quality = campaign080.extract_above_median_amount_longest_run(
        _raw_from_continuous_amounts(zero), symbol="000001.SZ"
    )
    assert frame["above_median_amount_longest_run"].isna().all()
    assert quality["nonpositive_total_amount_sessions"] == 1


def test_grid_identity_and_output_semantics_fail_closed() -> None:
    raw = _raw_from_continuous_amounts(np.ones(240, dtype=np.float64)).iloc[:-1]
    with pytest.raises(campaign080.Campaign080FeatureError):
        campaign080.extract_above_median_amount_longest_run(
            raw, symbol="000001.SZ"
        )

    output = campaign080.empty_output_frame()
    assert campaign080.validate_value_semantics(output) == (0, 0)
    bad = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["000001.SZ"],
            "provider": ["tushare"],
            campaign080.FACTOR_NAME: [0.101],
            f"{campaign080.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, campaign080.OUTPUT_COLUMNS]
    with pytest.raises(campaign080.Campaign080FeatureError):
        campaign080.validate_value_semantics(bad)


def test_feature_implementation_freeze_is_live() -> None:
    freeze = campaign080._validate_implementation_freeze()
    assert freeze["research_boundary"]["candidate_source_rows_read_before_freeze"] is False
    assert Path(freeze["feature_runner"]["path"]).name == Path(campaign080.__file__).name
