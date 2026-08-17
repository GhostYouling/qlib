from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign085_features as feature


def test_protocol_and_complete_orders_are_frozen() -> None:
    spec = feature.load_protocol()
    comparisons = feature.reconstruct_comparisons()
    complete = feature.reconstruct_complete_definitions()
    assert spec["candidate"]["name"] == feature.FACTOR_NAME
    assert len(comparisons) == 114
    assert len(complete) == 116
    assert (
        feature._comparison_order_digest(comparisons) == feature.COMPARISON_ORDER_SHA256
    )
    assert (
        feature._comparison_order_digest(complete)
        == feature.FULL_DEFINITION_ORDER_SHA256
    )
    assert comparisons[-1] == {
        "name": feature.c84.FACTOR_NAME,
        "score_direction": "higher",
    }


def test_confirmation_product_and_missing_semantics() -> None:
    ranks = np.array(
        [
            [0.5, 0.8],
            [1.0, 1.0],
            [np.nan, 0.7],
            [0.0, 0.6],
            [0.4, 1.1],
        ],
        dtype=np.float64,
    )
    values, eligible = feature.compute_confirmation_product(ranks)
    assert eligible.tolist() == [True, True, False, False, False]
    assert values[:2].tolist() == pytest.approx([0.4, 1.0])
    assert np.isnan(values[2:]).all()


def test_confirmation_product_requires_exactly_two_rank_columns() -> None:
    with pytest.raises(feature.Campaign085FeatureError, match="n-by-2"):
        feature.compute_confirmation_product(np.ones((3, 3), dtype=np.float64))


def test_rank_and_product_uses_exact_common_finite_session_universe() -> None:
    frame = pd.DataFrame(
        {
            "stock_day_key": [4_000_001, 4_000_002, 4_000_003, 8_000_001],
            "quarterly_announcement_freshness_60s": [1.0, 3.0, 2.0, 4.0],
            "intraday_market_neutral_late_residual_drift_238m": [
                30.0,
                10.0,
                np.nan,
                5.0,
            ],
        }
    )
    out = feature.rank_and_product_cache_frame(frame)
    factor = out[feature.FACTOR_NAME].to_numpy(dtype=np.float64)
    eligible = out[f"{feature.FACTOR_NAME}_eligible"].tolist()
    assert eligible == [True, True, False, True]
    assert factor[[0, 1, 3]].tolist() == pytest.approx([0.5, 0.5, 1.0])
    assert np.isnan(factor[2])


def test_rank_and_product_rejects_duplicate_or_unsorted_keys() -> None:
    duplicate = pd.DataFrame(
        {
            "stock_day_key": [4_000_001, 4_000_001],
            feature.INPUT_FACTORS[0]: [1.0, 2.0],
            feature.INPUT_FACTORS[1]: [3.0, 4.0],
        }
    )
    with pytest.raises(feature.Campaign085FeatureError, match="identities"):
        feature.rank_and_product_cache_frame(duplicate)
    unsorted = duplicate.copy()
    unsorted["stock_day_key"] = [4_000_002, 4_000_001]
    with pytest.raises(feature.Campaign085FeatureError, match="identities"):
        feature.rank_and_product_cache_frame(unsorted)


def test_temporary_root_helper_creates_exact_missing_parent(tmp_path) -> None:
    root = tmp_path / "nested" / "campaign085_v1"
    assert root.parent.exists() is False
    temporary = feature._prepare_temporary_root(root)
    try:
        assert root.parent.is_dir()
        assert temporary.parent == root.parent
        assert temporary.name.startswith(f".{root.name}.")
    finally:
        temporary.rmdir()


def test_status_is_read_only_before_build() -> None:
    payload = feature.status()
    assert payload["status"] == "snapshot_absent_pre_build"
    assert payload["compact_cache_rows_read"] is False
    assert payload["candidate_values_computed"] is False
    assert payload["comparison_values_read"] is False
    assert payload["historical_daily_price_or_forward_return_values_read"] is False
    assert payload["provider_request_issued"] is False
