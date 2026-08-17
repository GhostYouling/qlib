from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign074_features as feature


def _raw(amounts: np.ndarray | None = None) -> pd.DataFrame:
    codes = feature.SOURCE_MINUTE_CODES
    if amounts is None:
        amounts = np.arange(1.0, len(codes) + 1.0, dtype=float)
    datetimes = [
        pd.Timestamp("2021-01-04")
        + pd.Timedelta(hours=int(code) // 60, minutes=int(code) % 60)
        for code in codes
    ]
    return pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "000001.SZ",
            "provider": "tushare",
            "amount": amounts,
        }
    ).loc[:, feature.RAW_COLUMNS]


def _identity() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2021-01-04")],
            "symbol": ["000001.SZ"],
            "provider": ["tushare"],
        }
    ).loc[:, feature.IDENTITY_COLUMNS]


def test_protocol_and_frozen_orders_are_valid_without_candidate_values() -> None:
    spec = feature.load_protocol()
    assert spec["candidate"]["name"] == feature.FACTOR_NAME
    comparisons = feature.reconstruct_comparisons()
    complete = feature.reconstruct_complete_definitions()
    assert len(comparisons) == 104
    assert len(complete) == 105
    assert comparisons[-1] == {
        "name": feature.C73_FACTOR,
        "score_direction": "higher",
    }
    assert feature._comparison_order_digest(comparisons) == (
        feature.COMPARISON_ORDER_SHA256
    )
    assert feature._comparison_order_digest(complete) == (
        feature.FULL_DEFINITION_ORDER_SHA256
    )


def test_exact_terminal_amount_share_excludes_standalone_0930() -> None:
    amounts = np.ones(len(feature.SOURCE_MINUTE_CODES), dtype=float)
    amounts[0] = 10_000.0
    shares, quality = feature.extract_terminal_amount_shares(
        _raw(amounts), symbol="000001.SZ"
    )
    assert shares.loc[0, "terminal_amount_share"] == pytest.approx(1.0 / 240.0)
    assert quality["valid_terminal_share_sessions"] == 1
    assert quality["invalid_amount_grid_sessions"] == 0
    assert quality["nonpositive_total_amount_sessions"] == 0


def test_zero_terminal_amount_is_valid_closed_interval_zero() -> None:
    amounts = np.ones(len(feature.SOURCE_MINUTE_CODES), dtype=float)
    amounts[-1] = 0.0
    shares, quality = feature.extract_terminal_amount_shares(
        _raw(amounts), symbol="000001.SZ"
    )
    assert shares.loc[0, "terminal_amount_share"] == 0.0
    assert quality["valid_terminal_share_sessions"] == 1


def test_terminal_only_positive_amount_can_reach_valid_one() -> None:
    amounts = np.zeros(len(feature.SOURCE_MINUTE_CODES), dtype=float)
    amounts[-1] = 7.0
    shares, quality = feature.extract_terminal_amount_shares(
        _raw(amounts), symbol="000001.SZ"
    )
    assert shares.loc[0, "terminal_amount_share"] == 1.0
    assert quality["valid_terminal_share_sessions"] == 1


def test_negative_selected_amount_makes_session_missing() -> None:
    amounts = np.ones(len(feature.SOURCE_MINUTE_CODES), dtype=float)
    amounts[10] = -1.0
    shares, quality = feature.extract_terminal_amount_shares(
        _raw(amounts), symbol="000001.SZ"
    )
    assert pd.isna(shares.loc[0, "terminal_amount_share"])
    assert quality["invalid_amount_grid_sessions"] == 1


def test_zero_selected_total_makes_session_missing() -> None:
    amounts = np.zeros(len(feature.SOURCE_MINUTE_CODES), dtype=float)
    amounts[0] = 9.0
    shares, quality = feature.extract_terminal_amount_shares(
        _raw(amounts), symbol="000001.SZ"
    )
    assert pd.isna(shares.loc[0, "terminal_amount_share"])
    assert quality["nonpositive_total_amount_sessions"] == 1


def test_missing_minute_fails_closed() -> None:
    raw = _raw().iloc[:-1].reset_index(drop=True)
    with pytest.raises(feature.Campaign074FeatureError, match="minute grid"):
        feature.extract_terminal_amount_shares(raw, symbol="000001.SZ")


def test_attach_finalize_and_value_semantics_preserve_identity() -> None:
    shares, _ = feature.extract_terminal_amount_shares(
        _raw(), symbol="000001.SZ"
    )
    attached = feature.attach_terminal_amount_shares(
        _identity(), shares, symbol="000001.SZ"
    )
    output = feature.finalize_feature_frame(attached).loc[:, feature.OUTPUT_COLUMNS]
    rows, eligible = feature.validate_value_semantics(output)
    assert (rows, eligible) == (1, 1)
    assert output.loc[0, "symbol"] == "000001.SZ"
    assert output.loc[0, "provider"] == "tushare"
