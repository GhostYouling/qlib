from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign107_comparator_adapter as adapter


FACTOR = "raw_factor"


def _frame(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-01-02"] * len(values)),
            "symbol": [f"{index:06d}.SZ" for index in range(len(values))],
            FACTOR: values,
        }
    )


def _keys(values: list[int]):
    return lambda _dates, _symbols: np.asarray(values, dtype=np.int64)


def test_contract_and_status_are_value_blind() -> None:
    contract = adapter.validate_contract()
    assert contract["research_boundary"]["campaign107_comparator_values_read"] is False
    status = adapter.status()
    assert status["candidate_values_read"] is False
    assert status["comparator_values_read"] is False
    assert status["historical_daily_price_or_forward_return_values_read"] is False


def test_range_registration_is_idempotent_and_conflicts_fail() -> None:
    result = adapter.register_raw_factor_range(
        {"old": (-1.0, 1.0), FACTOR: (0.0, 1.0)},
        factor=FACTOR,
        value_range=(0.0, 1.0),
    )
    assert result == {"old": (-1.0, 1.0), FACTOR: (0.0, 1.0)}
    with pytest.raises(adapter.Campaign107ComparatorAdapterError, match="conflicting"):
        adapter.register_raw_factor_range(
            {FACTOR: (-1.0, 1.0)}, factor=FACTOR, value_range=(0.0, 1.0)
        )


def test_finite_endpoints_and_legal_nan_survive_sort_and_alignment() -> None:
    frame = _frame([1.0, np.nan, 0.0, 0.5])
    source_keys, source_values = adapter.sorted_raw_comparator_arrays(
        frame,
        factor=FACTOR,
        value_range=(0.0, 1.0),
        compact_key_fn=_keys([40, 20, 10, 30]),
    )
    np.testing.assert_array_equal(source_keys, [10, 20, 30, 40])
    assert source_values[0] == 0.0
    assert np.isnan(source_values[1])
    assert source_values[2] == 0.5
    assert source_values[3] == 1.0
    aligned = adapter.align_raw_comparator_values(
        source_keys=source_keys,
        source_values=source_values,
        target_keys=np.array([20, 40], dtype=np.int64),
    )
    assert np.isnan(aligned[0])
    assert aligned[1] == 1.0


@pytest.mark.parametrize("bad", [np.inf, -np.inf])
def test_both_infinities_are_rejected(bad: float) -> None:
    with pytest.raises(adapter.Campaign107ComparatorAdapterError, match="infinite"):
        adapter.sorted_raw_comparator_arrays(
            _frame([0.0, bad]),
            factor=FACTOR,
            value_range=(0.0, 1.0),
            compact_key_fn=_keys([1, 2]),
        )


@pytest.mark.parametrize("bad", [-0.01, 1.01])
def test_finite_out_of_range_values_are_rejected(bad: float) -> None:
    with pytest.raises(adapter.Campaign107ComparatorAdapterError, match="outside"):
        adapter.sorted_raw_comparator_arrays(
            _frame([0.5, bad]),
            factor=FACTOR,
            value_range=(0.0, 1.0),
            compact_key_fn=_keys([1, 2]),
        )


def test_duplicate_source_key_is_rejected() -> None:
    with pytest.raises(adapter.Campaign107ComparatorAdapterError, match="unique"):
        adapter.sorted_raw_comparator_arrays(
            _frame([0.25, 0.75]),
            factor=FACTOR,
            value_range=(0.0, 1.0),
            compact_key_fn=_keys([7, 7]),
        )


def test_missing_target_identity_is_rejected() -> None:
    with pytest.raises(adapter.Campaign107ComparatorAdapterError, match="cover"):
        adapter.align_raw_comparator_values(
            source_keys=np.array([1, 3], dtype=np.int64),
            source_values=np.array([0.25, np.nan]),
            target_keys=np.array([1, 2], dtype=np.int64),
        )


def test_non_numeric_payload_is_not_silently_converted_to_missing() -> None:
    frame = _frame([0.25, 0.75])
    frame[FACTOR] = frame[FACTOR].astype(object)
    frame.loc[1, FACTOR] = SimpleNamespace()
    with pytest.raises(adapter.Campaign107ComparatorAdapterError, match="numeric"):
        adapter.sorted_raw_comparator_arrays(
            frame,
            factor=FACTOR,
            value_range=(0.0, 1.0),
            compact_key_fn=_keys([1, 2]),
        )
