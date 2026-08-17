from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign083_features as campaign083


def _raw(closes: np.ndarray | None = None) -> pd.DataFrame:
    values = (
        np.full(240, 100.0, dtype=np.float64)
        if closes is None
        else np.asarray(closes, dtype=np.float64)
    )
    assert values.shape == (240,)
    by_code = {
        code: float(value)
        for code, value in zip(campaign083.CONTINUOUS_MINUTE_CODES, values)
    }
    by_code[9 * 60 + 30] = 100.0
    rows = []
    for code in sorted(campaign083.SOURCE_MINUTE_CODE_SET):
        rows.append(
            {
                "datetime": pd.Timestamp(2024, 1, 2, code // 60, code % 60),
                "symbol": "000001.SZ",
                "provider": "tushare",
                "close": by_code[code],
            }
        )
    return pd.DataFrame(rows).loc[:, campaign083.RAW_COLUMNS]


def _score(raw: pd.DataFrame) -> float:
    frame, quality = campaign083.extract_close_frontier_innovation_share(
        raw, symbol="000001.SZ"
    )
    assert quality["valid_close_frontier_innovation_sessions"] == 1
    return float(frame.loc[0, "close_frontier_innovation_share"])


def test_frozen_orders_protocol_and_status_are_prevalue_safe() -> None:
    spec = campaign083.load_protocol()
    assert spec["candidate"]["name"] == campaign083.FACTOR_NAME
    comparisons = campaign083.reconstruct_comparisons()
    complete = campaign083.reconstruct_complete_definitions()
    assert len(comparisons) == 112
    assert len(complete) == 114
    assert comparisons[-1] == {
        "name": "intraday_range_amount_peak_timing_alignment_240m",
        "score_direction": "higher",
    }
    assert complete[-1] == comparisons[-1]
    status = campaign083.status(campaign083.DEFAULT_DATA_ROOT)
    assert status["source_fields_read_by_status"] == []
    assert status["candidate_or_comparison_values_read_by_status"] is False
    assert (
        status["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )


def test_constant_and_monotone_half_session_endpoints() -> None:
    assert _score(_raw()) == 0.0
    monotone = np.concatenate([np.arange(100.0, 220.0), np.arange(300.0, 420.0)])
    assert _score(_raw(monotone)) == 1.0


def test_strict_frontier_count_and_exact_ties() -> None:
    closes = np.full(240, 100.0, dtype=np.float64)
    closes[1] = 101.0
    closes[2] = 101.0
    closes[3] = 99.0
    closes[4] = 100.5
    closes[120:] = 200.0
    closes[121] = 199.0
    closes[122] = 201.0
    closes[123] = 200.0
    assert _score(_raw(closes)) == pytest.approx(4.0 / 238.0, abs=1e-15)


def test_lunch_reset_prevents_cross_lunch_innovation() -> None:
    closes = np.concatenate([np.full(120, 100.0), np.full(120, 1000.0)])
    assert _score(_raw(closes)) == 0.0


def test_positive_scale_and_vertical_order_reflection_invariance() -> None:
    closes = np.concatenate(
        [
            np.array([100.0, 101.0, 100.5, 99.0, 102.0]),
            np.full(115, 100.0),
            np.array([200.0, 199.0, 201.0, 198.0, 200.0]),
            np.full(115, 200.0),
        ]
    )
    base = _score(_raw(closes))
    assert _score(_raw(closes * 7.0)) == pytest.approx(base, abs=1e-15)
    reflected = 1000.0 - closes
    assert _score(_raw(reflected)) == pytest.approx(base, abs=1e-15)


@pytest.mark.parametrize("bad", [0.0, -1.0, np.nan, np.inf])
def test_invalid_close_is_missing_without_rescue(bad: float) -> None:
    raw = _raw()
    raw.loc[1, "close"] = bad
    frame, quality = campaign083.extract_close_frontier_innovation_share(
        raw, symbol="000001.SZ"
    )
    assert frame["close_frontier_innovation_share"].isna().all()
    assert quality["invalid_close_grid_sessions"] == 1


def test_grid_identity_and_output_semantics_fail_closed() -> None:
    with pytest.raises(campaign083.Campaign083FeatureError):
        campaign083.extract_close_frontier_innovation_share(
            _raw().iloc[:-1], symbol="000001.SZ"
        )
    output = campaign083.empty_output_frame()
    assert campaign083.validate_value_semantics(output) == (0, 0)
    bad = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["000001.SZ"],
            "provider": ["tushare"],
            campaign083.FACTOR_NAME: [1.001],
            f"{campaign083.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, campaign083.OUTPUT_COLUMNS]
    with pytest.raises(campaign083.Campaign083FeatureError):
        campaign083.validate_value_semantics(bad)


def test_feature_implementation_freeze_is_live_when_published() -> None:
    if campaign083.DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        freeze = campaign083._validate_implementation_freeze()
        assert (
            freeze["research_boundary"]["candidate_source_rows_read_before_freeze"]
            is False
        )
        assert (
            Path(freeze["feature_runner"]["path"]).name
            == Path(campaign083.__file__).name
        )
