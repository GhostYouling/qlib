from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign056_empty_partition_repair as repair
from scripts import a_share_three_day_walkforward_campaign056_features as core


def _raw_session(date: str, *, symbol: str = "SH600000") -> pd.DataFrame:
    timestamps = pd.date_range(f"{date} 09:30", periods=121, freq="1min").append(
        pd.date_range(f"{date} 13:01", periods=120, freq="1min")
    )
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": symbol,
            "provider": "tushare",
            "amount": np.arange(1.0, len(timestamps) + 1.0),
        }
    ).loc[:, core.RAW_COLUMNS]


def test_repair_bindings_freeze_exact_manifest_empty_partition_set() -> None:
    payload = repair.verify_repair_bindings()
    assert payload["manifest_declared_empty_partitions"] == [
        "SH600485/2021",
        "SH600677/2021",
        "SH600680/2019",
        "SZ000670/2021",
        "SZ002260/2020",
        "SZ002260/2021",
    ]


def test_repair_accepts_only_exact_column_empty_frame() -> None:
    empty = pd.DataFrame(columns=core.RAW_COLUMNS)
    profiles, quality = repair.extract_amount_profiles_compat(
        empty,
        symbol="SH600485",
    )
    assert profiles == {}
    assert quality == {"source_sessions": 0}

    with pytest.raises(core.Campaign056FeatureError, match="unexpected raw columns"):
        repair.extract_amount_profiles_compat(
            empty.drop(columns=["amount"]),
            symbol="SH600485",
        )


def test_repair_delegates_nonempty_frame_without_changing_values() -> None:
    raw = _raw_session("2020-01-02")
    expected_profiles, expected_quality = repair._ORIGINAL_EXTRACT_AMOUNT_PROFILES(
        raw,
        symbol="SH600000",
    )
    actual_profiles, actual_quality = repair.extract_amount_profiles_compat(
        raw,
        symbol="SH600000",
    )
    assert actual_quality == expected_quality
    assert actual_quality["source_sessions"] == 1
    assert list(actual_profiles) == list(expected_profiles)
    assert np.array_equal(
        actual_profiles[pd.Timestamp("2020-01-02")],
        expected_profiles[pd.Timestamp("2020-01-02")],
    )
