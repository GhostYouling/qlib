from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign088_features as c88
from scripts import a_share_three_day_walkforward_campaign089_features as c89


def _closes_from_returns(returns: np.ndarray, *, start: float = 10.0) -> np.ndarray:
    if returns.shape != (119,):
        raise ValueError("one half requires 119 returns")
    return start * np.exp(np.concatenate(([0.0], np.cumsum(returns))))


def _closes_from_pooled_returns(
    returns: np.ndarray, *, morning_start: float = 10.0, afternoon_start: float = 20.0
) -> np.ndarray:
    if returns.shape != (238,):
        raise ValueError("pooled returns must contain 238 values")
    return np.concatenate(
        (
            _closes_from_returns(returns[:119], start=morning_start),
            _closes_from_returns(returns[119:], start=afternoon_start),
        )
    )


def _grid_frame(
    closes: np.ndarray, destination_amounts: np.ndarray, *, symbol: str = "SH600000"
) -> pd.DataFrame:
    if closes.shape != (240,) or destination_amounts.shape != (238,):
        raise ValueError("unexpected synthetic grid shape")
    minutes = [pd.Timestamp("2020-01-02 09:30")]
    minutes.extend(pd.date_range("2020-01-02 09:31", periods=120, freq="min"))
    minutes.extend(pd.date_range("2020-01-02 13:01", periods=120, freq="min"))
    selected_amounts = np.zeros(240, dtype=np.float64)
    selected_amounts[1:120] = destination_amounts[:119]
    selected_amounts[121:240] = destination_amounts[119:]
    return pd.DataFrame(
        {
            "datetime": minutes,
            "symbol": symbol,
            "provider": "tushare",
            "close": np.concatenate(([closes[0]], closes)),
            "amount": np.concatenate(([999.0], selected_amounts)),
        }
    ).loc[:, c89.RAW_COLUMNS]


def test_protocol_and_v28_orders_are_bound() -> None:
    spec = c89.load_protocol()
    comparisons = c89.reconstruct_comparisons()
    definitions = c89.reconstruct_complete_definitions()
    assert spec["candidate"]["name"] == c89.FACTOR_NAME
    assert len(comparisons) == 118
    assert len(definitions) == 120
    assert comparisons[-1] == {
        "name": c88.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert definitions[-1] == comparisons[-1]


def test_late_up_amount_and_early_down_amount_score_one() -> None:
    returns = np.zeros(238, dtype=np.float64)
    returns[0] = -0.01
    returns[-1] = 0.01
    amounts = np.zeros(238, dtype=np.float64)
    amounts[0] = 5.0
    amounts[-1] = 7.0
    score, eligible, up_mass, down_mass, up_center, down_center = (
        c89.compute_directional_amount_timing_spread(
            _closes_from_pooled_returns(returns)[None, :], amounts[None, :]
        )
    )
    assert eligible.tolist() == [True]
    assert score[0] == pytest.approx(1.0)
    assert up_mass[0] == pytest.approx(7.0)
    assert down_mass[0] == pytest.approx(5.0)
    assert up_center[0] == pytest.approx(1.0)
    assert down_center[0] == pytest.approx(0.0)


def test_sign_swap_negates_and_directional_amount_scaling_is_invariant() -> None:
    returns = np.resize(np.array([-0.004, 0.003, 0.0, 0.002]), 238)
    amounts = np.linspace(1.0, 4.0, 238)
    scaled_amounts = amounts.copy()
    scaled_amounts[returns > 0.0] *= 13.0
    scaled_amounts[returns < 0.0] *= 2.0
    closes = _closes_from_pooled_returns(returns)
    mirrored_closes = _closes_from_pooled_returns(-returns)
    score, eligible, *_ = c89.compute_directional_amount_timing_spread(
        np.vstack((closes, closes * 17.0, mirrored_closes)),
        np.vstack((amounts, scaled_amounts, amounts)),
    )
    assert eligible.all()
    assert score[0] == pytest.approx(score[1], abs=1e-12)
    assert score[2] == pytest.approx(-score[0], abs=1e-12)


def test_return_magnitude_is_irrelevant_when_signs_are_fixed() -> None:
    returns = np.resize(np.array([-0.001, 0.002, 0.0, 0.003]), 238)
    magnified = returns * np.linspace(0.5, 9.0, 238)
    amounts = np.linspace(1.0, 5.0, 238)
    score, eligible, *_ = c89.compute_directional_amount_timing_spread(
        np.vstack(
            (
                _closes_from_pooled_returns(returns),
                _closes_from_pooled_returns(magnified),
            )
        ),
        np.vstack((amounts, amounts)),
    )
    assert eligible.all()
    assert score[0] == pytest.approx(score[1], abs=1e-12)


def test_missing_directional_mass_or_invalid_inputs_are_missing() -> None:
    positive = np.full(238, 0.001)
    mixed = np.resize(np.array([-0.001, 0.001]), 238)
    amounts = np.ones(238)
    invalid_amounts = amounts.copy()
    invalid_amounts[3] = -1.0
    invalid_closes = _closes_from_pooled_returns(mixed)
    invalid_closes[10] = 0.0
    score, eligible, *_ = c89.compute_directional_amount_timing_spread(
        np.vstack(
            (
                _closes_from_pooled_returns(positive),
                _closes_from_pooled_returns(mixed),
                invalid_closes,
            )
        ),
        np.vstack((amounts, invalid_amounts, amounts)),
    )
    assert not eligible.any()
    assert np.isnan(score).all()
    with pytest.raises(c89.Campaign089FeatureError):
        c89.compute_directional_amount_timing_spread(
            np.ones((2, 239)), np.ones((2, 238))
        )
    with pytest.raises(c89.Campaign089FeatureError):
        c89.compute_directional_amount_timing_spread(
            np.ones((2, 240)), np.ones((2, 237))
        )


def test_exact_grid_extraction_excludes_0930_first_half_bars_and_lunch_pair() -> None:
    returns = np.zeros(238, dtype=np.float64)
    returns[0] = -0.01
    returns[-1] = 0.01
    amounts = np.zeros(238, dtype=np.float64)
    amounts[0] = 1.0
    amounts[-1] = 1.0
    raw = _grid_frame(_closes_from_pooled_returns(returns), amounts)
    raw.loc[raw["datetime"].dt.strftime("%H:%M") == "09:30", "amount"] = 1e15
    values, quality = c89.extract_directional_amount_timing_spread(
        raw, symbol="SH600000"
    )
    assert len(values) == 1
    assert values[c89.FACTOR_NAME].iloc[0] == pytest.approx(1.0)
    assert quality["source_rows"] == 241
    assert quality["valid_directional_timing_sessions"] == 1


def test_grid_or_identity_change_fails_closed() -> None:
    returns = np.resize(np.array([-0.001, 0.001]), 238)
    amounts = np.ones(238)
    raw = _grid_frame(_closes_from_pooled_returns(returns), amounts)
    with pytest.raises(c89.Campaign089FeatureError):
        c89.extract_directional_amount_timing_spread(
            raw.iloc[:-1].copy(), symbol="SH600000"
        )
    duplicate = pd.concat((raw, raw.iloc[[1]]), ignore_index=True)
    with pytest.raises(c89.Campaign089FeatureError):
        c89.extract_directional_amount_timing_spread(duplicate, symbol="SH600000")


def test_build_is_confirmation_gated_and_output_is_absent() -> None:
    assert not c89.output_root(c89.DEFAULT_DATA_ROOT).exists()
    with pytest.raises(c89.Campaign089FeatureError):
        c89.build_snapshot(data_root=c89.DEFAULT_DATA_ROOT)
