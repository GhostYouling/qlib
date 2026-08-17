from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign128_features as c128


def _raw_session(*, date: str = "2025-01-02", symbol: str = "SH600000") -> pd.DataFrame:
    session = pd.Timestamp(date)
    codes = [9 * 60 + 30, *c128.CONTINUOUS_MINUTE_CODES]
    volume = np.ones(241, dtype=np.float64)
    log_prices = np.concatenate(
        (
            np.repeat([0.0, 1.0, 2.0, 3.0], 30),
            np.repeat([0.0, 0.25, 0.5, 0.75], 30),
        )
    )
    amount = np.ones(241, dtype=np.float64)
    amount[1:] = np.exp(log_prices)
    volume[0] = 9999.0
    amount[0] = 9999.0 * np.exp(99.0)
    return pd.DataFrame(
        {
            "datetime": [session + pd.Timedelta(minutes=int(code)) for code in codes],
            "symbol": symbol,
            "provider": "tushare",
            "volume": volume,
            "amount": amount,
        }
    ).loc[:, c128.RAW_COLUMNS]


def test_campaign128_protocol_projection_and_orders_are_frozen() -> None:
    spec = c128.load_protocol()
    assert spec["candidate"]["name"] == c128.FACTOR_NAME
    assert tuple(spec["candidate"]["source_projection"]) == c128.RAW_COLUMNS
    assert len(c128.reconstruct_complete_definitions()) == 151
    assert len(c128.reconstruct_comparisons()) == 139
    assert c128.reconstruct_complete_definitions()[-1] == {
        "name": c128.FACTOR_NAME,
        "score_direction": "higher",
    }


def test_campaign128_extract_enforces_grid_and_excludes_0930() -> None:
    raw = _raw_session()
    values, quality = c128.extract_transaction_price_dispersion_resolution(
        raw, symbol="SH600000"
    )
    selected_volume = raw["volume"].to_numpy()[1:].reshape(1, 240)
    selected_amount = raw["amount"].to_numpy()[1:].reshape(1, 240)
    expected, eligible, *_ = c128.compute_transaction_price_dispersion_resolution(
        selected_volume, selected_amount
    )
    assert eligible.tolist() == [True]
    assert values[c128.FACTOR_SHORT_NAME].tolist() == expected.tolist()
    assert values.iloc[0, 1] > 0.0
    assert quality["raw_source_rows"] == 241
    assert quality["valid_dispersion_resolution_sessions"] == 1


def test_campaign128_extract_rejects_changed_grid_and_projection() -> None:
    raw = _raw_session()
    with pytest.raises(c128.Campaign128FeatureError):
        c128.extract_transaction_price_dispersion_resolution(
            raw.iloc[:-1].copy(), symbol="SH600000"
        )
    with pytest.raises(c128.Campaign128FeatureError):
        c128.extract_transaction_price_dispersion_resolution(
            raw.drop(columns="amount"), symbol="SH600000"
        )


def test_campaign128_extract_preserves_missing_support_without_rescue() -> None:
    raw = _raw_session()
    raw.loc[1:61, ["volume", "amount"]] = 0.0
    values, quality = c128.extract_transaction_price_dispersion_resolution(
        raw, symbol="SH600000"
    )
    assert np.isnan(values.iloc[0, 1])
    assert quality["insufficient_morning_active_sessions"] == 1
    raw = _raw_session()
    raw.loc[10, "volume"] = 0.0
    _, quality = c128.extract_transaction_price_dispersion_resolution(
        raw, symbol="SH600000"
    )
    assert quality["one_sided_zero_sessions"] == 1


def test_campaign128_attach_finalize_and_value_semantics() -> None:
    raw = _raw_session()
    values, _ = c128.extract_transaction_price_dispersion_resolution(
        raw, symbol="SH600000"
    )
    identity = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2025-01-02")],
            "symbol": ["SH600000"],
            "provider": ["tushare"],
        }
    ).loc[:, c128.IDENTITY_COLUMNS]
    attached = c128.attach_dispersion_resolution_values(
        identity, values, symbol="SH600000"
    )
    output = c128.finalize_feature_frame(attached).loc[:, c128.OUTPUT_COLUMNS]
    assert c128.validate_value_semantics(output) == (1, 1)
    assert output[f"{c128.FACTOR_NAME}_eligible"].tolist() == [True]


def test_campaign128_value_semantics_fail_closed() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2025-01-02")],
            "symbol": ["SH600000"],
            "provider": ["tushare"],
            c128.FACTOR_NAME: [1.01],
            f"{c128.FACTOR_NAME}_eligible": [True],
        }
    ).loc[:, c128.OUTPUT_COLUMNS]
    with pytest.raises(c128.Campaign128FeatureError):
        c128.validate_value_semantics(frame)


def test_campaign128_status_does_not_read_values() -> None:
    payload = c128.status()
    assert payload["status"] == "snapshot_absent_prebuild"
    assert payload["source_fields_read_by_status"] == []
    assert payload["candidate_or_comparison_values_read_by_status"] is False
