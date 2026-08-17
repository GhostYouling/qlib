from __future__ import annotations

import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign057_empty_partition_repair as repair


def test_repair_bindings_accept_only_the_six_manifest_empty_partitions() -> None:
    result = repair.verify_repair_bindings()
    assert result["manifest_declared_empty_partitions"] == [
        "SH600485/2021",
        "SH600677/2021",
        "SH600680/2019",
        "SZ000670/2021",
        "SZ002260/2020",
        "SZ002260/2021",
    ]


def test_exact_column_empty_frame_is_accepted_without_values() -> None:
    empty = pd.DataFrame(columns=repair.core.RAW_COLUMNS)
    profiles, quality = repair.extract_profiles_compat(
        empty, symbol="SH600485"
    )
    assert profiles == {}
    assert quality == {"source_sessions": 0}


def test_wrong_empty_schema_still_delegates_and_fails_closed() -> None:
    empty = pd.DataFrame(columns=["datetime", "symbol", "provider", "amount"])
    with pytest.raises(repair.core.Campaign057FeatureError, match="unexpected raw columns"):
        repair.extract_profiles_compat(empty, symbol="SH600485")


def test_nonempty_frame_delegates_to_the_frozen_extractor(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake(raw: pd.DataFrame, *, symbol: str):
        called["columns"] = tuple(raw.columns)
        called["symbol"] = symbol
        return {pd.Timestamp("2020-01-02"): object()}, {"source_sessions": 1}

    monkeypatch.setattr(repair, "_ORIGINAL_EXTRACT_PROFILES", fake)
    raw = pd.DataFrame(
        [[pd.Timestamp("2020-01-02 09:31"), "SH600000", "tushare", 10.0]],
        columns=repair.core.RAW_COLUMNS,
    )
    profiles, quality = repair.extract_profiles_compat(raw, symbol="SH600000")
    assert called == {
        "columns": repair.core.RAW_COLUMNS,
        "symbol": "SH600000",
    }
    assert list(profiles) == [pd.Timestamp("2020-01-02")]
    assert quality == {"source_sessions": 1}
