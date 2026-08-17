from __future__ import annotations

import json

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign069_no_return_audit_v3 as repair


def test_campaign069_v3_protocol_freezes_only_comparator_alignment_repair() -> None:
    spec = repair.load_repair_protocol()
    semantics = spec["sole_repair"]
    assert "all finite values" in semantics["candidate_sorter_semantics_unchanged"]
    assert "retain finite and NaN comparator values unchanged" in semantics[
        "campaign068_comparator_sorter_semantics"
    ]
    assert semantics["delegate_all_other_behavior_to_immutable_v1_and_v2_runners"] is True
    assert spec["unchanged_semantics"]["coverage_gates_changed"] is False
    assert spec["unchanged_semantics"]["uniqueness_gates_changed"] is False


def test_campaign069_v3_sorter_retains_campaign068_nan_values_only() -> None:
    class ComparisonEngine:
        @staticmethod
        def _compact_stock_day_keys(dates: pd.Series, symbols: pd.Series) -> np.ndarray:
            del dates
            return symbols.map({"SH600001": 2, "SH600000": 1}).to_numpy(dtype=np.int64)

    def original(frame: pd.DataFrame, factor: str) -> tuple[np.ndarray, np.ndarray]:
        del frame, factor
        raise AssertionError("original sorter should not handle Campaign068")

    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04", "2021-01-04"]),
            "symbol": ["SH600001", "SH600000"],
            repair.v1.candidate.C68_FACTOR: [np.nan, -0.25],
        }
    )
    sorter = repair.build_comparator_sorter(
        original=original, comparison_engine=ComparisonEngine()
    )
    keys, values = sorter(frame, repair.v1.candidate.C68_FACTOR)
    assert keys.tolist() == [1, 2]
    assert values[0] == -0.25
    assert np.isnan(values[1])


def test_campaign069_v3_sorter_delegates_candidate_finiteness_unchanged() -> None:
    called: list[str] = []

    def original(frame: pd.DataFrame, factor: str) -> tuple[np.ndarray, np.ndarray]:
        del frame
        called.append(factor)
        return np.array([1]), np.array([0.0])

    sorter = repair.build_comparator_sorter(
        original=original, comparison_engine=object()
    )
    keys, values = sorter(pd.DataFrame(), repair.v1.FACTOR_NAME)
    assert called == [repair.v1.FACTOR_NAME]
    assert keys.tolist() == [1]
    assert values.tolist() == [0.0]


def test_campaign069_v3_status_is_read_only() -> None:
    payload = repair.status()
    assert payload["first_two_failures_preserved"] is True
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read_by_status"] == []
    assert payload["historical_forward_return_fields_read_by_status"] is False
    assert payload["provider_request_issued_by_status"] is False


def test_campaign069_v3_implementation_freeze_binds_runner_and_tests() -> None:
    record = json.loads(repair.IMPLEMENTATION_FREEZE.read_text())
    assert record["v3_runner"]["sha256"] == repair._sha256(
        repair.Path(repair.__file__)
    )
    assert record["tests"]["sha256"] == repair._sha256(repair.TEST_PATH)
    assert record["historical_daily_price_fields_read_before_freeze"] == []
    assert record["historical_forward_returns_read_before_freeze"] is False
