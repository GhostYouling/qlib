from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign152_features as features


def _raw(amount: np.ndarray | None = None) -> pd.DataFrame:
    minutes = [pd.Timestamp("2024-01-02 09:30")]
    minutes.extend(pd.date_range("2024-01-02 09:31", "2024-01-02 11:30", freq="min"))
    minutes.extend(pd.date_range("2024-01-02 13:01", "2024-01-02 15:00", freq="min"))
    values = np.arange(1.0, 242.0) if amount is None else amount
    return pd.DataFrame(
        {
            "datetime": minutes,
            "symbol": "SH600000",
            "provider": "tushare",
            "amount": values,
        }
    )


def _identity() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2024-01-02")],
            "symbol": ["SH600000"],
            "provider": ["tushare"],
        }
    )


def test_definition_and_comparator_orders_are_exact() -> None:
    assert len(features.reconstruct_prior_complete_definitions()) == 156
    assert len(features.reconstruct_complete_definitions()) == 157
    assert features.reconstruct_complete_definitions()[-1] == {
        "name": features.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert len(features.reconstruct_comparisons()) == 142


def test_protocol_binds_source_without_values() -> None:
    spec = features.load_protocol()
    assert spec["source_snapshot_contract"]["provider_request_allowed"] is False
    assert (
        spec["research_boundary"][
            "campaign152_candidate_values_computed_or_read_before_freeze"
        ]
        is False
    )


def test_extract_uses_exact_continuous_240_bar_sum() -> None:
    raw = _raw()
    values, quality = features.extract_session_total_amount_magnitude(
        raw, symbol="SH600000"
    )
    expected = np.log1p(np.arange(2.0, 242.0).sum())
    assert values.loc[0, features.FACTOR_SHORT_NAME] == pytest.approx(expected)
    assert quality["source_rows"] == 241
    assert quality["valid_amount_sessions"] == 1


def test_standalone_0930_amount_is_excluded() -> None:
    left = _raw()
    right = left.copy()
    right.loc[0, "amount"] = 1e15
    a, _ = features.extract_session_total_amount_magnitude(left, symbol="SH600000")
    b, _ = features.extract_session_total_amount_magnitude(right, symbol="SH600000")
    assert a.loc[0, features.FACTOR_SHORT_NAME] == b.loc[0, features.FACTOR_SHORT_NAME]


def test_invalid_or_nonpositive_amount_session_is_missing() -> None:
    for bad in (np.nan, -1.0):
        amount = np.arange(1.0, 242.0)
        amount[7] = bad
        values, quality = features.extract_session_total_amount_magnitude(
            _raw(amount), symbol="SH600000"
        )
        assert np.isnan(values.loc[0, features.FACTOR_SHORT_NAME])
        assert quality["valid_amount_sessions"] == 0
    zero = np.zeros(241)
    values, quality = features.extract_session_total_amount_magnitude(
        _raw(zero), symbol="SH600000"
    )
    assert np.isnan(values.loc[0, features.FACTOR_SHORT_NAME])
    assert quality["nonpositive_total_amount_sessions"] == 1


def test_attach_finalize_and_validate_semantics() -> None:
    values, _ = features.extract_session_total_amount_magnitude(
        _raw(), symbol="SH600000"
    )
    attached = features.attach_amount_values(_identity(), values, symbol="SH600000")
    finalized = features.finalize_feature_frame(attached)
    output = finalized.loc[:, features.OUTPUT_COLUMNS]
    assert features.validate_value_semantics(output) == (1, 1)


def test_wrong_projection_or_grid_fails_closed() -> None:
    with pytest.raises(features.Campaign152FeatureError):
        features.extract_session_total_amount_magnitude(
            _raw().drop(columns=["amount"]), symbol="SH600000"
        )
    with pytest.raises(features.Campaign152FeatureError):
        features.extract_session_total_amount_magnitude(
            _raw().iloc[:-1].copy(), symbol="SH600000"
        )
