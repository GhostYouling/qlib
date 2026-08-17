from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign263_features as features


def _raw_frame(*, symbol: str = "SZ000001", uniform: bool = False) -> pd.DataFrame:
    date = pd.Timestamp("2020-01-02")
    codes = sorted(features.SOURCE_MINUTE_CODE_SET)
    datetimes = [
        date + pd.Timedelta(hours=code // 60, minutes=code % 60) for code in codes
    ]
    amounts = []
    for code in codes:
        if code not in features.CONTINUOUS_MINUTE_CODE_SET:
            amounts.append(1.0)
            continue
        ordinal = features.CONTINUOUS_MINUTE_CODES.index(code)
        half_ordinal = ordinal % 120
        if uniform:
            amounts.append(1.0)
        else:
            amounts.append(
                1.0
                + 0.4
                * np.cos(2.0 * np.pi * 7.0 * float(half_ordinal) / 120.0)
            )
    return pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": symbol,
            "provider": "tushare",
            "amount": amounts,
        }
    )[list(features.RAW_COLUMNS)]


def test_reconstructed_orders_are_frozen() -> None:
    assert len(features.reconstruct_complete_definitions()) == 162
    assert features.reconstruct_complete_definitions()[-1] == {
        "name": features.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert len(features.reconstruct_comparisons()) == 142


def test_protocol_bindings_pass() -> None:
    spec = features.load_protocol()
    assert spec["source_snapshot_contract"]["expected_partitions"] == 33015


def test_extract_valid_spectral_session() -> None:
    result, quality = features.extract_amount_profile_spectral_entropy(
        _raw_frame(), symbol="SZ000001"
    )
    assert len(result) == 1
    assert np.isfinite(result[features.FACTOR_SHORT_NAME].iloc[0])
    assert quality["valid_spectral_sessions"] == 1
    assert quality["zero_non_dc_power_sessions"] == 0


def test_uniform_session_is_missing() -> None:
    result, quality = features.extract_amount_profile_spectral_entropy(
        _raw_frame(uniform=True), symbol="SZ000001"
    )
    assert np.isnan(result[features.FACTOR_SHORT_NAME].iloc[0])
    assert quality["zero_non_dc_power_sessions"] == 1


def test_wrong_identity_fails_closed() -> None:
    raw = _raw_frame()
    raw.loc[0, "provider"] = "other"
    with pytest.raises(features.Campaign263FeatureError):
        features.extract_amount_profile_spectral_entropy(raw, symbol="SZ000001")


def test_wrong_grid_fails_closed() -> None:
    with pytest.raises(features.Campaign263FeatureError):
        features.extract_amount_profile_spectral_entropy(
            _raw_frame().iloc[:-1].copy(), symbol="SZ000001"
        )


def test_finalize_and_validate_semantics() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-03")],
            "symbol": ["SZ000001", "SZ000001"],
            "provider": ["tushare", "tushare"],
            features.FACTOR_SHORT_NAME: [0.25, np.nan],
        }
    )
    final = features.finalize_feature_frame(frame)
    assert features.FACTOR_NAME in final.columns
    partition_output = final.loc[:, list(features.OUTPUT_COLUMNS)].copy()
    assert features.validate_value_semantics(partition_output) == (2, 1)


def test_finalize_preserves_internal_partition_index() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2020-01-02")],
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
            features.FACTOR_SHORT_NAME: [0.25],
            "_partition_index": [7],
        }
    )
    final = features.finalize_feature_frame(frame)
    assert final["_partition_index"].tolist() == [7]


def test_output_root_is_campaign_specific() -> None:
    root = features.output_root(Path("/tmp/campaign263-root"))
    assert "campaign263" in str(root)
    assert features.OUTPUT_RUN_ID in str(root)
