import json

import numpy as np

from scripts import a_share_three_day_walkforward_campaign132_design as design


def test_campaign132_protocol_and_complete_order_are_frozen() -> None:
    protocol = design.load_protocol()
    features = design.current_feature_order()
    assert len(features) == 140
    assert features[-1] == {
        "name": "intraday_transaction_price_dispersion_resolution_2h",
        "score_direction": "higher",
    }
    assert protocol["complete_feature_library"]["numeric_feature_order_sha256"] == (
        design.FEATURE_ORDER_SHA256
    )
    assert len(protocol["trial_catalog"]) == 3


def test_align_values_preserves_missing_and_rejects_no_target() -> None:
    source_keys = np.array([30, 10, 40], dtype=np.int64)
    source_values = np.array([3.0, 1.0, np.nan], dtype=np.float64)
    target_keys = np.array([10, 20, 30, 40], dtype=np.int64)
    aligned = design.align_values(
        source_keys=source_keys,
        source_values=source_values,
        target_keys=target_keys,
    )
    np.testing.assert_allclose(aligned[[0, 2]], np.array([1.0, 3.0]))
    assert np.isnan(aligned[[1, 3]]).all()


def test_favorable_percentile_ranks_use_daily_average_ties() -> None:
    day_a = 20_000 * 4_000_000
    day_b = 20_001 * 4_000_000
    keys = np.array(
        [day_a + 1_000_001, day_a + 1_000_002, day_a + 2_000_001, day_b + 1_000_001],
        dtype=np.int64,
    )
    values = np.array([2.0, 2.0, 5.0, np.nan])
    ranked = design.favorable_percentile_ranks(keys, values)
    np.testing.assert_allclose(ranked[:3], np.array([0.5, 0.5, 1.0]))
    assert np.isnan(ranked[3])


def test_extend_matrix_uses_exact_105_of_140_support() -> None:
    base = np.full((2, 130), np.nan, dtype=np.float32)
    base[0, :95] = 0.25
    base[1, :94] = 0.75
    appended = [np.ones(2, dtype=np.float32) for _ in range(10)]
    matrix, counts, eligible = design.extend_matrix(base, appended)
    assert matrix.shape == (2, 140)
    np.testing.assert_array_equal(counts, np.array([105, 104], dtype=np.uint8))
    np.testing.assert_array_equal(eligible, np.array([True, False]))


def test_plan_is_price_and_return_blind() -> None:
    plan = design.build_plan()
    assert plan["feature_count"] == 140
    assert plan["source_manifest_count"] == 11
    assert plan["component_factor_values_read_by_plan"] is False
    assert plan["historical_daily_price_or_forward_return_values_read_by_plan"] is False
    json.dumps(plan, allow_nan=False)
