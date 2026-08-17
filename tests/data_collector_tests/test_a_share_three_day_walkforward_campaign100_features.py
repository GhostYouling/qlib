from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign100_features as c100


def _broad_hlc(closes: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    close = np.asarray(closes, dtype=np.float64).reshape(1, 240)
    high = np.full_like(close, 10.0)
    low = np.full_like(close, 1.0)
    return high, low, close


def test_protocol_and_v52_orders_are_bound_without_candidate_values() -> None:
    spec = c100.load_protocol()
    assert spec["candidate"]["name"] == c100.FACTOR_NAME
    definitions = c100.reconstruct_complete_definitions()
    comparisons = c100.reconstruct_comparisons()
    assert len(definitions) == 131
    assert len(comparisons) == 128
    assert definitions[-1] == {
        "name": "intraday_market_close_location_profile_synchronization_240m",
        "score_direction": "higher",
    }
    assert comparisons[-1] == definitions[-1]


def test_all_unchanged_and_all_changed_paths_hit_exact_endpoints() -> None:
    unchanged = np.full(240, 2.0)
    high, low, close = _broad_hlc(unchanged)
    values, eligible, *_ = c100.compute_unchanged_close_range_absorption_share(
        high, low, close
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [1.0]

    changed = np.resize(np.array([2.0, 3.0]), 240)
    high, low, close = _broad_hlc(changed)
    values, eligible, *_ = c100.compute_unchanged_close_range_absorption_share(
        high, low, close
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]


def test_range_mass_not_event_count_determines_score() -> None:
    closes = np.resize(np.array([2.0, 3.0]), 240)
    closes[1] = closes[0]
    high, low, close = _broad_hlc(closes)
    values, eligible, absorbed, total, unchanged, ranges = (
        c100.compute_unchanged_close_range_absorption_share(high, low, close)
    )
    expected = float(ranges[0, unchanged[0]].sum() / ranges[0].sum())
    assert eligible.tolist() == [True]
    assert absorbed[0] > 0.0
    assert total[0] > absorbed[0]
    assert values[0] == pytest.approx(expected)


def test_lunch_equality_is_not_a_transition() -> None:
    closes = np.empty(240, dtype=np.float64)
    closes[:120] = np.resize(np.array([2.0, 3.0]), 120)
    closes[120:] = np.resize(np.array([3.0, 2.0]), 120)
    assert closes[119] == closes[120]
    high, low, close = _broad_hlc(closes)
    values, eligible, *_ = c100.compute_unchanged_close_range_absorption_share(
        high, low, close
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]


def test_equality_is_exact_and_has_no_tick_or_epsilon_tolerance() -> None:
    closes = np.resize(np.array([2.0, 3.0]), 240)
    closes[1] = np.nextafter(closes[0], np.inf)
    high, low, close = _broad_hlc(closes)
    values, eligible, *_ = c100.compute_unchanged_close_range_absorption_share(
        high, low, close
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == [0.0]


def test_zero_total_range_and_invalid_hlc_fail_closed() -> None:
    close = np.full((2, 240), 2.0)
    high = close.copy()
    low = close.copy()
    high[1, 7] = 1.5
    values, eligible, *_ = c100.compute_unchanged_close_range_absorption_share(
        high, low, close
    )
    assert eligible.tolist() == [False, False]
    assert np.isnan(values).all()


def test_shape_and_confirmation_guards_fail_closed() -> None:
    with pytest.raises(c100.Campaign100FeatureError, match="n-by-240"):
        c100.compute_unchanged_close_range_absorption_share(
            np.ones((1, 239)), np.ones((1, 239)), np.ones((1, 239))
        )
    with pytest.raises(c100.Campaign100FeatureError, match="confirm-build"):
        c100.build_snapshot(data_root=c100.DEFAULT_DATA_ROOT, confirm_build=False)
