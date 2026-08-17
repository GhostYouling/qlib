from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign082_features as campaign082


def _raw(
    *,
    range_peak_indices: tuple[int, ...],
    amount_peak_indices: tuple[int, ...],
) -> pd.DataFrame:
    highs = np.full(240, 100.0, dtype=np.float64)
    lows = np.full(240, 100.0, dtype=np.float64)
    amounts = np.ones(240, dtype=np.float64)
    for index in range_peak_indices:
        highs[index] = 110.0
    for index in amount_peak_indices:
        amounts[index] = 10.0
    values = {
        code: (float(high), float(low), float(amount))
        for code, high, low, amount in zip(
            campaign082.CONTINUOUS_MINUTE_CODES, highs, lows, amounts
        )
    }
    values[9 * 60 + 30] = (100.0, 100.0, 0.0)
    rows = []
    for code in sorted(campaign082.SOURCE_MINUTE_CODE_SET):
        high, low, amount = values[code]
        rows.append(
            {
                "datetime": pd.Timestamp(2024, 1, 2, code // 60, code % 60),
                "symbol": "000001.SZ",
                "provider": "tushare",
                "high": high,
                "low": low,
                "amount": amount,
            }
        )
    return pd.DataFrame(rows).loc[:, campaign082.RAW_COLUMNS]


def _score(raw: pd.DataFrame) -> float:
    frame, quality = campaign082.extract_range_amount_peak_timing_alignment(
        raw, symbol="000001.SZ"
    )
    assert quality["valid_peak_timing_alignment_sessions"] == 1
    return float(frame.loc[0, "peak_timing_alignment"])


def test_frozen_orders_protocol_and_status_are_prevalue_safe() -> None:
    spec = campaign082.load_protocol()
    assert spec["candidate"]["name"] == campaign082.FACTOR_NAME
    comparisons = campaign082.reconstruct_comparisons()
    complete = campaign082.reconstruct_complete_definitions()
    assert len(comparisons) == 111
    assert len(complete) == 113
    assert comparisons[-1] == {
        "name": "intraday_amount_path_efficiency_238p",
        "score_direction": "higher",
    }
    assert complete[-1] == comparisons[-1]
    status = campaign082.status(campaign082.DEFAULT_DATA_ROOT)
    assert status["source_fields_read_by_status"] == []
    assert status["candidate_or_comparison_values_read_by_status"] is False
    assert (
        status["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )


def test_alignment_endpoints_and_interior_distance() -> None:
    assert _score(_raw(range_peak_indices=(0,), amount_peak_indices=(0,))) == 1.0
    assert _score(_raw(range_peak_indices=(0,), amount_peak_indices=(239,))) == 0.0
    assert _score(
        _raw(range_peak_indices=(10,), amount_peak_indices=(110,))
    ) == pytest.approx(1.0 - 100.0 / 239.0, abs=1e-15)


def test_last_exact_maximum_tie_rule_is_independent() -> None:
    tied = _raw(range_peak_indices=(4, 40), amount_peak_indices=(10, 50))
    assert _score(tied) == pytest.approx(1.0 - 10.0 / 239.0, abs=1e-15)


def test_joint_reversal_and_scale_invariance() -> None:
    base = _raw(range_peak_indices=(17,), amount_peak_indices=(101,))
    base_score = _score(base)
    continuous = base.loc[
        base["datetime"].dt.hour * 60 + base["datetime"].dt.minute != 9 * 60 + 30
    ].copy()
    continuous[["high", "low", "amount"]] = (
        continuous[["high", "low", "amount"]].iloc[::-1].to_numpy()
    )
    reversed_raw = pd.concat(
        [base.iloc[[0]], continuous], ignore_index=True
    ).sort_values("datetime", kind="stable")
    reversed_raw = reversed_raw.loc[:, campaign082.RAW_COLUMNS].reset_index(drop=True)
    assert _score(reversed_raw) == pytest.approx(base_score, abs=1e-15)
    scaled = base.copy()
    scaled[["high", "low"]] *= 7.0
    scaled["amount"] *= 13.0
    assert _score(scaled) == pytest.approx(base_score, abs=1e-15)


@pytest.mark.parametrize(
    "mutation,quality_key",
    [
        (
            lambda frame: frame.assign(high=100.0, low=100.0),
            "nonpositive_maximum_range_sessions",
        ),
        (lambda frame: frame.assign(amount=0.0), "nonpositive_maximum_amount_sessions"),
        (
            lambda frame: frame.assign(low=lambda x: x["high"] + 1.0),
            "invalid_high_low_grid_sessions",
        ),
        (lambda frame: frame.assign(amount=-1.0), "invalid_amount_grid_sessions"),
    ],
)
def test_invalid_inputs_are_missing_without_rescue(mutation, quality_key: str) -> None:
    frame, quality = campaign082.extract_range_amount_peak_timing_alignment(
        mutation(_raw(range_peak_indices=(3,), amount_peak_indices=(3,))),
        symbol="000001.SZ",
    )
    assert frame["peak_timing_alignment"].isna().all()
    assert quality[quality_key] == 1


def test_grid_identity_and_output_semantics_fail_closed() -> None:
    raw = _raw(range_peak_indices=(3,), amount_peak_indices=(3,)).iloc[:-1]
    with pytest.raises(campaign082.Campaign082FeatureError):
        campaign082.extract_range_amount_peak_timing_alignment(raw, symbol="000001.SZ")
    output = campaign082.empty_output_frame()
    assert campaign082.validate_value_semantics(output) == (0, 0)
    bad = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["000001.SZ"],
            "provider": ["tushare"],
            campaign082.FACTOR_NAME: [1.001],
            f"{campaign082.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, campaign082.OUTPUT_COLUMNS]
    with pytest.raises(campaign082.Campaign082FeatureError):
        campaign082.validate_value_semantics(bad)


def test_feature_implementation_freeze_is_live_when_published() -> None:
    if campaign082.DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        freeze = campaign082._validate_implementation_freeze()
        assert (
            freeze["research_boundary"]["candidate_source_rows_read_before_freeze"]
            is False
        )
        assert (
            Path(freeze["feature_runner"]["path"]).name
            == Path(campaign082.__file__).name
        )
