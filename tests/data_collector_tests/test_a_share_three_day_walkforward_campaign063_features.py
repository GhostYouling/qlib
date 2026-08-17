from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign063_features as campaign063


def _matrix(value: float, rows: int = 1) -> np.ndarray:
    return np.full((rows, campaign063.RETURN_POSITION_COUNT), value, dtype=float)


def test_protocol_reconstructs_exact_frozen_94_comparison_order() -> None:
    spec = campaign063.load_protocol()
    comparisons = campaign063.reconstruct_comparisons(spec)
    assert len(comparisons) == 94
    assert campaign063._comparison_order_digest(comparisons) == campaign063.COMPARISON_ORDER_SHA256
    assert comparisons[-1] == {
        "name": "quarterly_announcement_peer_crowding_sparsity",
        "score_direction": "higher",
    }


def test_constant_state_is_exactly_one_and_lunch_jump_is_excluded() -> None:
    stock = _matrix(0.0, rows=2)
    stock[1, 119:] = 9.0
    means = _matrix(0.0, rows=2)
    variances = _matrix(1.0, rows=2)
    peers = np.ones_like(stock, dtype=bool)
    values, eligible, quality = campaign063.compute_state_stability_values(
        stock, means, variances, peers
    )
    assert eligible.tolist() == [True, True]
    assert values.tolist() == [1.0, 1.0]
    assert quality["exact_zero_displacement_pairs"] == 2 * campaign063.ADJACENT_STATE_PAIR_COUNT


def test_exact_236_pair_absolute_displacement_formula() -> None:
    states = np.concatenate(
        [np.arange(119, dtype=float), np.arange(119, dtype=float)]
    )[None, :]
    values, eligible, _ = campaign063.compute_state_stability_values(
        states, _matrix(0.0), _matrix(1.0), np.ones_like(states, dtype=bool)
    )
    assert eligible.tolist() == [True]
    assert values[0] == pytest.approx(0.5)


def test_leave_one_out_moments_remove_stock_exactly() -> None:
    stock = _matrix(2.0)
    peer_count = 50
    peer_mean = 1.5
    peer_variance = 4.0
    sums = stock + peer_count * peer_mean
    sum_squares = stock * stock + peer_count * (peer_variance + peer_mean**2)
    counts = np.full_like(stock, peer_count + 1, dtype=np.int64)
    means, variances, sufficient, quality = campaign063.reconstruct_leave_one_out_moments(
        stock, sums, sum_squares, counts
    )
    assert np.allclose(means, peer_mean)
    assert np.allclose(variances, peer_variance)
    assert sufficient.all()
    assert quality["minimum_leave_one_out_peer_count"] == peer_count


def test_incomplete_stock_is_not_subtracted_from_benchmark_population() -> None:
    stock = _matrix(2.0)
    stock[0, 3] = np.nan
    sums = _matrix(75.0)
    sum_squares = _matrix(312.5)
    counts = np.full_like(stock, 50, dtype=np.int64)
    means, variances, sufficient, quality = campaign063.reconstruct_leave_one_out_moments(
        stock, sums, sum_squares, counts
    )
    assert np.allclose(means, 1.5)
    assert np.allclose(variances, 4.0)
    assert sufficient.all()
    assert quality["incomplete_stock_return_rows"] == 1


def test_any_nonpositive_variance_or_insufficient_position_fails_closed() -> None:
    stock = _matrix(0.0, rows=3)
    means = _matrix(0.0, rows=3)
    variances = _matrix(1.0, rows=3)
    variances[0, 4] = 0.0
    variances[1, 5] = -5e-19
    peers = np.ones_like(stock, dtype=bool)
    peers[2, 6] = False
    values, eligible, quality = campaign063.compute_state_stability_values(
        stock, means, variances, peers
    )
    assert eligible.tolist() == [False, False, False]
    assert np.isnan(values).all()
    assert quality["tiny_negative_variance_positions_canonicalized"] == 1
    assert quality["nonpositive_variance_rows"] == 2
    assert quality["insufficient_peer_rows"] == 1


def test_material_negative_or_nonfinite_input_fails_closed() -> None:
    stock = _matrix(0.0, rows=2)
    means = _matrix(0.0, rows=2)
    variances = _matrix(1.0, rows=2)
    variances[0, 0] = -2e-18
    stock[1, 0] = np.inf
    values, eligible, quality = campaign063.compute_state_stability_values(
        stock, means, variances, np.ones_like(stock, dtype=bool)
    )
    assert eligible.tolist() == [False, False]
    assert np.isnan(values).all()
    assert quality["material_negative_variance_rows"] == 1
    assert quality["nonfinite_input_rows"] == 2


def test_wrong_shapes_raise() -> None:
    with pytest.raises(campaign063.Campaign063FeatureError):
        campaign063.compute_state_stability_values(
            np.zeros((1, 237)),
            np.zeros((1, 237)),
            np.ones((1, 237)),
            np.ones((1, 237), dtype=bool),
        )
