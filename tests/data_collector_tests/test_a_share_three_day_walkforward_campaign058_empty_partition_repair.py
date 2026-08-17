from __future__ import annotations

import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign058_empty_partition_repair as repair


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
    states, quality = repair.extract_states_compat(empty, symbol="SH600485")
    assert states == {}
    assert quality == {
        "source_sessions": 0,
        "source_identity_rows": 0,
        "sessions_without_prior_effective_quarterly_event": 0,
        "sessions_with_nonfinite_growth_spread_state": 0,
        "sessions_with_finite_growth_spread_state": 0,
    }


def test_wrong_empty_schema_still_delegates_and_fails_closed() -> None:
    empty = pd.DataFrame(columns=["datetime", "symbol", "provider", "amount"])
    with pytest.raises(repair.core.Campaign058FeatureError, match="unexpected raw identity columns"):
        repair.extract_states_compat(empty, symbol="SH600485")


def test_nonempty_frame_delegates_to_the_frozen_extractor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: dict[str, object] = {}

    def fake(raw: pd.DataFrame, *, symbol: str):
        called["columns"] = tuple(raw.columns)
        called["symbol"] = symbol
        return {pd.Timestamp("2020-01-02"): 7.0}, {"source_sessions": 1}

    monkeypatch.setattr(repair, "_ORIGINAL_EXTRACT_STATES", fake)
    raw = pd.DataFrame(
        [[pd.Timestamp("2020-01-02 09:31"), "SH600000", "tushare"]],
        columns=repair.core.RAW_COLUMNS,
    )
    states, quality = repair.extract_states_compat(raw, symbol="SH600000")
    assert called == {
        "columns": repair.core.RAW_COLUMNS,
        "symbol": "SH600000",
    }
    assert states == {pd.Timestamp("2020-01-02"): 7.0}
    assert quality == {"source_sessions": 1}


def test_install_changes_only_generated_extractor_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_compute = repair.core._engine["compute_output_frame"]
    original_validate = repair.core._engine["_validate_manifest"]
    monkeypatch.setitem(
        repair.core._engine,
        "extract_amount_profiles",
        repair._ORIGINAL_EXTRACT_STATES,
    )
    repair.install_repair()
    assert repair.core._engine["extract_amount_profiles"] is repair.extract_states_compat
    assert repair.core._engine["compute_output_frame"] is original_compute
    assert repair.core._engine["_validate_manifest"] is original_validate
