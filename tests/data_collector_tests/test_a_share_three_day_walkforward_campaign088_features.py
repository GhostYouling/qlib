from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign087_features as c87
from scripts import a_share_three_day_walkforward_campaign088_features as c88


def _closes_from_returns(returns: np.ndarray, *, start: float = 10.0) -> np.ndarray:
    if returns.shape != (119,):
        raise ValueError("one half requires 119 returns")
    return start * np.exp(np.concatenate(([0.0], np.cumsum(returns))))


def _grid_frame(closes: np.ndarray, *, symbol: str = "SH600000") -> pd.DataFrame:
    if closes.shape != (240,):
        raise ValueError("selected close grid must have 240 values")
    minutes = [pd.Timestamp("2020-01-02 09:30")]
    minutes.extend(pd.date_range("2020-01-02 09:31", periods=120, freq="min"))
    minutes.extend(pd.date_range("2020-01-02 13:01", periods=120, freq="min"))
    return pd.DataFrame(
        {
            "datetime": minutes,
            "symbol": symbol,
            "provider": "tushare",
            "close": np.concatenate(([closes[0]], closes)),
        }
    ).loc[:, c88.RAW_COLUMNS]


def test_protocol_and_v26_orders_are_bound() -> None:
    spec = c88.load_protocol()
    comparisons = c88.reconstruct_comparisons()
    definitions = c88.reconstruct_complete_definitions()
    assert spec["candidate"]["name"] == c88.FACTOR_NAME
    assert len(comparisons) == 117
    assert len(definitions) == 119
    assert comparisons[-1] == {
        "name": c87.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert definitions[-1] == comparisons[-1]


def test_v26_orders_remain_bound_inside_builder_adapter() -> None:
    expected_comparisons = c88.reconstruct_comparisons()
    expected_definitions = c88.reconstruct_complete_definitions()
    with c88._patched_campaign086_builder():
        c88.load_protocol()
        assert c88.reconstruct_comparisons() == expected_comparisons
        assert c88.reconstruct_complete_definitions() == expected_definitions


def test_isolated_jump_is_one_and_diffusive_path_is_zero() -> None:
    isolated = np.zeros(119)
    isolated[59] = 0.03
    smooth = np.full(119, 0.001)
    closes = np.vstack(
        (
            np.concatenate(
                (_closes_from_returns(isolated), _closes_from_returns(np.zeros(119)))
            ),
            np.concatenate(
                (_closes_from_returns(smooth), _closes_from_returns(smooth))
            ),
        )
    )
    score, eligible, rv, bv = c88.compute_bipower_jump_share(closes)
    assert eligible.tolist() == [True, True]
    assert score[0] == pytest.approx(1.0)
    assert bv[0] == pytest.approx(0.0)
    assert rv[0] > 0.0
    assert score[1] == pytest.approx(0.0)
    assert bv[1] > rv[1]


def test_sign_scale_price_level_and_lunch_gap_invariances() -> None:
    base = np.linspace(-0.003, 0.004, 119)
    mirror = -base
    morning = _closes_from_returns(base)
    afternoon = _closes_from_returns(base, start=40.0)
    transformed = np.concatenate(
        (
            _closes_from_returns(2.0 * mirror, start=50.0),
            _closes_from_returns(2.0 * mirror, start=3.0),
        )
    )
    original = np.concatenate((morning, afternoon))
    price_scaled = original * 17.0
    score, eligible, _rv, _bv = c88.compute_bipower_jump_share(
        np.vstack((original, price_scaled, transformed))
    )
    assert eligible.all()
    assert score[0] == pytest.approx(score[1], abs=1e-12)
    assert score[0] == pytest.approx(score[2], abs=1e-12)


def test_constant_or_invalid_close_is_missing() -> None:
    constant = np.full(240, 10.0)
    zero = constant.copy()
    zero[5] = 0.0
    missing = constant.copy()
    missing[10] = np.nan
    score, eligible, rv, _bv = c88.compute_bipower_jump_share(
        np.vstack((constant, zero, missing))
    )
    assert not eligible.any()
    assert np.isnan(score).all()
    assert rv[0] == 0.0
    with pytest.raises(c88.Campaign088FeatureError):
        c88.compute_bipower_jump_share(np.ones((2, 239)))


def test_exact_grid_extraction_excludes_0930_and_lunch_pair() -> None:
    returns = np.zeros(119)
    returns[25] = 0.02
    closes = np.concatenate(
        (_closes_from_returns(returns), _closes_from_returns(np.zeros(119), start=99.0))
    )
    values, quality = c88.extract_bipower_jump_share(
        _grid_frame(closes), symbol="SH600000"
    )
    assert len(values) == 1
    assert values[c88.FACTOR_NAME].iloc[0] == pytest.approx(1.0)
    assert quality["source_rows"] == 241
    assert quality["valid_serial_persistence_sessions"] == 1
    assert quality["retained_informative_pairs"] == 236


def test_grid_or_identity_change_fails_closed() -> None:
    returns = np.zeros(119)
    returns[3] = 0.01
    closes = np.concatenate(
        (_closes_from_returns(returns), _closes_from_returns(np.zeros(119)))
    )
    raw = _grid_frame(closes)
    with pytest.raises(c88.Campaign088FeatureError):
        c88.extract_bipower_jump_share(raw.iloc[:-1].copy(), symbol="SH600000")
    duplicate = pd.concat((raw, raw.iloc[[1]]), ignore_index=True)
    with pytest.raises(c88.Campaign088FeatureError):
        c88.extract_bipower_jump_share(duplicate, symbol="SH600000")


def test_build_is_confirmation_gated_and_output_is_absent() -> None:
    assert not c88.output_root(c88.DEFAULT_DATA_ROOT).exists()
    with pytest.raises(c88.Campaign088FeatureError):
        c88.build_snapshot(data_root=c88.DEFAULT_DATA_ROOT)
