from __future__ import annotations

import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign059_empty_partition_repair as repair


def test_repair_bindings_accept_only_six_manifest_empty_partitions() -> None:
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
    profiles, quality = repair.extract_profiles_compat(empty, symbol="SH600485")
    assert profiles == {}
    assert quality == {
        "source_sessions": 0,
        "source_rows": 0,
        "source_nonfinite_close_grid_rows": 0,
        "source_nonpositive_close_grid_rows": 0,
        "source_valid_close_grid_rows": 0,
        "source_exact_zero_return_positions": 0,
    }


def test_wrong_empty_schema_still_delegates_and_fails_closed() -> None:
    empty = pd.DataFrame(columns=["datetime", "symbol", "provider", "amount"])
    with pytest.raises(repair.core.Campaign059FeatureError, match="unexpected raw columns"):
        repair.extract_profiles_compat(empty, symbol="SH600485")


def test_nonempty_frame_delegates_to_frozen_extractor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    assert called == {"columns": repair.core.RAW_COLUMNS, "symbol": "SH600000"}
    assert list(profiles) == [pd.Timestamp("2020-01-02")]
    assert quality == {"source_sessions": 1}


def test_install_changes_only_extractor_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_compute = repair.core._engine["compute_output_frame"]
    original_validate = repair.core._engine["_validate_manifest"]
    monkeypatch.setitem(
        repair.core._engine,
        "extract_amount_profiles",
        repair._ORIGINAL_EXTRACT_PROFILES,
    )
    repair.install_repair()
    assert repair.core._engine["extract_amount_profiles"] is repair.extract_profiles_compat
    assert repair.core._engine["compute_output_frame"] is original_compute
    assert repair.core._engine["_validate_manifest"] is original_validate
