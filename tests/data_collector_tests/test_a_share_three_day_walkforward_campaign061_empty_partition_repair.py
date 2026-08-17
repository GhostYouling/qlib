from __future__ import annotations

import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign061_empty_partition_repair as repair
from scripts import a_share_three_day_walkforward_campaign061_features as core


def test_repair_bindings_and_manifest_empty_set() -> None:
    result = repair.verify_repair_bindings()
    assert result["manifest_declared_empty_partitions"] == [
        "SH600485/2021",
        "SH600677/2021",
        "SH600680/2019",
        "SZ000670/2021",
        "SZ002260/2020",
        "SZ002260/2021",
    ]


def test_exact_column_empty_frame_is_accepted() -> None:
    raw = pd.DataFrame({name: pd.Series(dtype="object") for name in core.RAW_COLUMNS})
    profiles, quality = repair.extract_profiles_compat(raw, symbol="SH600485")
    assert profiles == {}
    assert quality == {"source_sessions": 0}


def test_wrong_column_empty_frame_delegates_and_fails() -> None:
    raw = pd.DataFrame(columns=["datetime", "symbol", "provider"])
    with pytest.raises(core.Campaign061FeatureError, match="unexpected raw columns"):
        repair.extract_profiles_compat(raw, symbol="SH600485")


def test_nonempty_frame_delegates_to_original() -> None:
    raw = pd.DataFrame(
        {
            "datetime": [pd.Timestamp("2020-01-02 09:30")],
            "symbol": ["SH600485"],
            "provider": ["tushare"],
            "close": [10.0],
        }
    )
    with pytest.raises(core.Campaign061FeatureError, match="241 rows"):
        repair.extract_profiles_compat(raw, symbol="SH600485")
