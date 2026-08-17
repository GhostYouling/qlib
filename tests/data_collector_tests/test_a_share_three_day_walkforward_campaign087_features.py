from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign087_features as c87


def _arrays(rows: int = 1) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ranges = np.linspace(0.001, 0.240, c87.SELECTED_BAR_COUNT)
    lows = np.ones((rows, c87.SELECTED_BAR_COUNT), dtype=np.float64)
    highs = np.exp(np.tile(ranges, (rows, 1)))
    amounts = np.tile(ranges * 1_000_000.0, (rows, 1))
    return highs, lows, amounts


def test_identical_participation_profiles_score_one_and_scale_invariant() -> None:
    highs, lows, amounts = _arrays()
    score, eligible, total_range, total_amount = c87.compute_profile_alignment(
        highs, lows, amounts
    )
    scaled, scaled_eligible, _, _ = c87.compute_profile_alignment(
        highs * 17.0, lows * 17.0, amounts * 31.0
    )
    assert eligible.tolist() == [True]
    assert scaled_eligible.tolist() == [True]
    assert score[0] == pytest.approx(1.0, abs=1e-12)
    assert scaled[0] == pytest.approx(score[0], abs=1e-12)
    assert total_range[0] > 0.0
    assert total_amount[0] > 0.0


def test_disjoint_profiles_score_zero_and_zero_components_are_retained() -> None:
    lows = np.ones((1, c87.SELECTED_BAR_COUNT), dtype=np.float64)
    ranges = np.zeros((1, c87.SELECTED_BAR_COUNT), dtype=np.float64)
    ranges[:, :120] = 0.01
    highs = np.exp(ranges)
    amounts = np.zeros_like(ranges)
    amounts[:, 120:] = 10.0
    score, eligible, _, _ = c87.compute_profile_alignment(highs, lows, amounts)
    assert eligible.tolist() == [True]
    assert score[0] == pytest.approx(0.0, abs=1e-12)


def test_nonpositive_total_range_or_amount_fails_closed() -> None:
    highs = np.ones((2, c87.SELECTED_BAR_COUNT), dtype=np.float64)
    lows = np.ones_like(highs)
    amounts = np.ones_like(highs)
    amounts[1] = 0.0
    highs[1, 0] = np.exp(0.01)
    score, eligible, total_range, total_amount = c87.compute_profile_alignment(
        highs, lows, amounts
    )
    assert eligible.tolist() == [False, False]
    assert np.isnan(score).all()
    assert total_range[0] == pytest.approx(0.0)
    assert total_amount[1] == pytest.approx(0.0)


def test_invalid_input_and_wrong_shape_fail_closed() -> None:
    highs, lows, amounts = _arrays(rows=2)
    amounts[0, 5] = -1.0
    highs[1, 8] = np.nan
    score, eligible, _, _ = c87.compute_profile_alignment(highs, lows, amounts)
    assert eligible.tolist() == [False, False]
    assert np.isnan(score).all()
    with pytest.raises(c87.Campaign087FeatureError):
        c87.compute_profile_alignment(highs[:, :-1], lows[:, :-1], amounts[:, :-1])


def test_exact_source_grid_excludes_0930_and_preserves_identity() -> None:
    codes = sorted(c87.c86.SOURCE_MINUTE_CODE_SET)
    day = pd.Timestamp("2023-06-01")
    datetimes = [day + pd.Timedelta(hours=code // 60, minutes=code % 60) for code in codes]
    continuous = set(c87.c86.CONTINUOUS_MINUTE_CODE_SET)
    log_ranges = np.array(
        [0.005 + (index % 17) * 0.0001 if code in continuous else 0.9 for index, code in enumerate(codes)],
        dtype=np.float64,
    )
    amounts = np.array(
        [value * 1_000_000.0 if code in continuous else 1.0 for code, value in zip(codes, log_ranges)],
        dtype=np.float64,
    )
    raw = pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "000001.SZ",
            "provider": "tushare",
            "high": np.exp(log_ranges),
            "low": 1.0,
            "amount": amounts,
        }
    ).loc[:, c87.RAW_COLUMNS]
    values, quality = c87.extract_profile_alignment(raw, symbol="000001.SZ")
    assert len(values) == 1
    assert values[c87.FACTOR_NAME].iloc[0] == pytest.approx(1.0, abs=1e-12)
    assert quality["source_rows"] == c87.SOURCE_BAR_COUNT
    assert quality["valid_serial_persistence_sessions"] == 1


def test_frozen_definition_and_numeric_orders_include_campaign086_last() -> None:
    comparisons = c87.reconstruct_comparisons()
    complete = c87.reconstruct_complete_definitions()
    assert len(comparisons) == c87.COMPARISON_COUNT
    assert len(complete) == c87.FULL_DEFINITION_COUNT
    assert comparisons[-1] == {
        "name": c87.c86.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert complete[-1] == comparisons[-1]
    assert c87._comparison_order_digest(comparisons) == c87.COMPARISON_ORDER_SHA256
    assert (
        c87._comparison_order_digest(complete)
        == c87.FULL_DEFINITION_ORDER_SHA256
    )


def test_protocol_bindings_and_prevalue_boundaries() -> None:
    spec = c87.load_protocol()
    assert spec["candidate"]["name"] == c87.FACTOR_NAME
    assert (
        spec["research_boundary"]["candidate_source_rows_read_before_freeze"]
        is False
    )
    assert (
        spec["research_boundary"]["forward_return_fields_read_before_admissibility"]
        is False
    )
