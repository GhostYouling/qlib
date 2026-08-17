from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign050_features as campaign


def _half(shock: float, retracement: float, shock_end_index: int = 30) -> np.ndarray:
    log_closes = np.zeros(120, dtype=float)
    log_closes[shock_end_index:] = shock
    remaining = 119 - shock_end_index
    if remaining:
        log_closes[shock_end_index:] += np.linspace(0.0, retracement, remaining + 1)
    return np.exp(log_closes)


def _day(morning: np.ndarray, afternoon: np.ndarray | None = None) -> np.ndarray:
    return np.concatenate([morning, morning if afternoon is None else afternoon])[None, :]


def test_campaign050_protocol_is_finite_and_binding_valid() -> None:
    spec = campaign.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert spec["kind"] == "a_share_three_day_walkforward_campaign050_no_return_preregistration"
    assert gate["comparison_factors"][-1] == {
        "name": campaign.C49_FACTOR_NAME,
        "score_direction": "higher",
    }
    assert len(gate["comparison_factors"]) == 73
    assert campaign._comparison_order_digest(gate["comparison_factors"]) == campaign.COMPARISON_ORDER_SHA256
    assert spec["finite_post_admissibility_search"]["development_trial_count"] == 1


def test_campaign050_perfect_same_half_reversal_scores_one() -> None:
    values, eligible, _ = campaign.compute_factor_values(
        closes=_day(_half(0.20, -0.20))
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(1.0)


def test_campaign050_equal_continuation_scores_minus_one() -> None:
    values, eligible, _ = campaign.compute_factor_values(
        closes=_day(_half(0.20, 0.20))
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(-1.0)


def test_campaign050_zero_terminal_retracement_is_valid_zero() -> None:
    values, eligible, _ = campaign.compute_factor_values(
        closes=_day(_half(0.20, 0.0))
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(0.0)


def test_campaign050_two_half_scores_are_equal_weighted() -> None:
    values, eligible, _ = campaign.compute_factor_values(
        closes=_day(_half(0.20, -0.20), _half(0.20, 0.20))
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [True]
    assert values[campaign.FACTOR_NAME][0] == pytest.approx(0.0)


def test_campaign050_earliest_absolute_shock_tie_wins() -> None:
    returns = np.zeros(119)
    returns[10] = 0.20
    returns[20] = -0.20
    logs = np.concatenate([[0.0], np.cumsum(returns)])
    scores, eligible, diagnostics = campaign._half_scores(np.exp(logs)[None, :])
    assert eligible.tolist() == [True]
    assert diagnostics["selected_index"].tolist() == [10]
    expected_retracement = logs[-1] - logs[11]
    expected = -2.0 * 0.20 * expected_retracement / (
        0.20**2 + expected_retracement**2
    )
    assert scores[0] == pytest.approx(expected)


def test_campaign050_all_zero_return_half_is_missing() -> None:
    values, eligible, quality = campaign.compute_factor_values(
        closes=_day(np.ones(120), _half(0.20, -0.20))
    )
    assert eligible[campaign.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[campaign.FACTOR_NAME][0])
    assert quality[f"{campaign.FACTOR_NAME}__all_zero_morning_return_rows"] == 1


def test_campaign050_rejects_nonpositive_and_nonfinite_closes() -> None:
    closes = np.vstack([
        _day(_half(0.20, -0.20))[0],
        _day(_half(0.20, -0.20))[0],
    ])
    closes[0, 7] = 0.0
    closes[1, 8] = np.nan
    values, eligible, quality = campaign.compute_factor_values(closes=closes)
    assert eligible[campaign.FACTOR_NAME].tolist() == [False, False]
    assert np.isnan(values[campaign.FACTOR_NAME]).all()
    assert quality[f"{campaign.FACTOR_NAME}__nonpositive_close_rows"] == 1
    assert quality[f"{campaign.FACTOR_NAME}__nonfinite_close_rows"] == 1


def test_campaign050_partition_uses_exact_241_row_source_grid() -> None:
    date = pd.Timestamp("2021-01-04")
    codes = [570] + list(campaign.market.CONTINUOUS_MINUTE_CODES)
    datetimes = [
        date + pd.Timedelta(minutes=int(code // 60 * 60 + code % 60))
        for code in codes
    ]
    close = np.concatenate([[1.0], _day(_half(0.20, -0.20))[0]])
    raw = pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "SZ000001",
            "provider": "tushare",
            "close": close,
        }
    ).loc[:, campaign.RAW_COLUMNS]
    base = pd.DataFrame({"trade_date": [date], "symbol": ["SZ000001"]})
    frame, quality = campaign.compute_partition_frame(
        raw, base, None, symbol="SZ000001"
    )
    assert list(frame.columns) == list(campaign.OUTPUT_COLUMNS)
    assert frame[campaign.FACTOR_NAME].iloc[0] == pytest.approx(1.0)
    assert bool(frame[f"{campaign.FACTOR_NAME}_eligible"].iloc[0]) is True
    assert quality["base_rows"] == 1


def test_campaign050_v1_cannot_build_before_additive_freeze_binding() -> None:
    assert campaign.IMPLEMENTATION_FREEZE_SHA256 == ""
    with pytest.raises(campaign.Campaign050FeatureError, match="implementation freeze"):
        campaign._load_implementation_freeze()


def test_campaign050_prevalue_records_disclose_no_value_or_return_read() -> None:
    for path in (
        Path("docs/a_share_three_day_walkforward_campaign_050_concept_scouting.json"),
        Path("docs/a_share_three_day_walkforward_campaign_050_mechanism_overlap_audit.json"),
        Path("docs/a_share_three_day_walkforward_campaign_050_no_return_preregistration.json"),
    ):
        record = json.loads(path.read_text(encoding="utf-8"))
        boundary = record["research_boundary"]
        assert boundary.get("provider_request_issued") is False
        assert boundary.get("candidate49_ledgers_changed") is False
        assert boundary.get("candidate50_prospective_activation_created") is False
        assert not any(
            value is True
            for key, value in boundary.items()
            if "value" in key or "price" in key or "return" in key
        )
