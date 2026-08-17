from __future__ import annotations

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign151_formula as c151


def test_campaign151_protocol_and_formula_boundary_are_frozen() -> None:
    spec = c151.load_protocol()
    assert spec["candidate"]["name"] == c151.FACTOR_NAME
    assert spec["candidate"]["direction"] == "higher"
    assert c151.PROFILE_POSITIONS == 240
    assert c151.MINIMUM_LEAVE_ONE_OUT_PEERS == 50
    assert c151.VALID_RANGE == (0.0, 1.0)


def test_campaign151_exact_peer_shape_match_has_midpoint_score() -> None:
    peer = np.linspace(10.0, 1000.0, 240, dtype=np.float64)[None, :]
    own = 7.0 * peer
    values, eligible, quality = c151.compute_relative_amount_share_clock_center(
        own, peer
    )
    assert eligible.tolist() == [True]
    assert values.tolist() == pytest.approx([0.5], abs=1e-15)
    assert quality["eligible_rows"] == 1


def test_campaign151_late_relative_activity_scores_higher() -> None:
    peer = np.ones((2, 240), dtype=np.float64)
    own = np.zeros((2, 240), dtype=np.float64)
    own[0, 0] = 1.0
    own[1, -1] = 1.0
    values, eligible, _quality = c151.compute_relative_amount_share_clock_center(
        own, peer
    )
    assert eligible.tolist() == [True, True]
    assert values.tolist() == pytest.approx([0.0, 1.0], abs=0.0)


def test_campaign151_is_invariant_to_own_and_peer_common_scales() -> None:
    own = np.linspace(1.0, 240.0, 240, dtype=np.float64)[None, :]
    peer = np.linspace(300.0, 10.0, 240, dtype=np.float64)[None, :]
    base = c151.compute_relative_amount_share_clock_center(own, peer)
    scaled = c151.compute_relative_amount_share_clock_center(
        own * 1_000_000.0, peer * 37.0
    )
    assert base[1].tolist() == scaled[1].tolist() == [True]
    assert scaled[0].tolist() == pytest.approx(base[0].tolist(), abs=1e-15)


def test_campaign151_is_invariant_to_same_per_clock_market_scale() -> None:
    own = np.linspace(1.0, 240.0, 240, dtype=np.float64)[None, :]
    peer = np.linspace(240.0, 1.0, 240, dtype=np.float64)[None, :]
    clock_scale = np.exp(np.linspace(-4.0, 4.0, 240))[None, :]
    base = c151.compute_relative_amount_share_clock_center(own, peer)
    changed = c151.compute_relative_amount_share_clock_center(
        own * clock_scale, peer * clock_scale
    )
    assert base[1].tolist() == changed[1].tolist() == [True]
    assert changed[0].tolist() == pytest.approx(base[0].tolist(), abs=1e-15)


def test_campaign151_zero_total_and_invalid_inputs_fail_closed() -> None:
    own = np.ones((5, 240), dtype=np.float64)
    peer = np.ones((5, 240), dtype=np.float64)
    own[0] = 0.0
    own[1, 5] = np.nan
    own[2, 5] = -1.0
    peer[3, 5] = np.nan
    peer[4, 5] = 0.0
    values, eligible, quality = c151.compute_relative_amount_share_clock_center(
        own, peer
    )
    assert eligible.tolist() == [False, False, False, False, False]
    assert np.isnan(values).all()
    assert quality["nonpositive_relative_total_rows"] == 1
    assert quality["nonfinite_own_amount_rows"] == 1
    assert quality["negative_own_amount_rows"] == 1
    assert quality["nonfinite_peer_mean_rows"] == 1
    assert quality["nonpositive_peer_mean_rows"] == 1


def test_campaign151_wrong_shape_fails_closed() -> None:
    with pytest.raises(c151.Campaign151FormulaError):
        c151.compute_relative_amount_share_clock_center(
            np.ones((1, 239)), np.ones((1, 239))
        )
    with pytest.raises(c151.Campaign151FormulaError):
        c151.compute_relative_amount_share_clock_center(
            np.ones((1, 240)), np.ones((2, 240))
        )
