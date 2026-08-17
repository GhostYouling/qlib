"""Synthetic and pre-value tests for Campaign044 terminal-library consensus."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign044_features as features


def _panel(
    first: list[float],
    second: list[float],
    *,
    date: str = "2025-01-02",
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.Timestamp(date),
            "symbol": [f"SZ00000{index}" for index in range(1, len(first) + 1)],
            "higher_factor": first,
            "lower_factor": second,
        }
    )


SPECS = [
    {"name": "higher_factor", "score_direction": "higher"},
    {"name": "lower_factor", "score_direction": "lower"},
]


def test_directional_percentile_consensus_uses_frozen_directions() -> None:
    result = features.compute_consensus_frame(
        _panel([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]),
        factors=SPECS,
        minimum_common_support_names=3,
    )

    assert result[f"{features.FACTOR_NAME}_eligible"].tolist() == [True] * 3
    assert result[features.FACTOR_NAME].tolist() == pytest.approx(
        [1.0 / 3.0, 2.0 / 3.0, 1.0]
    )


def test_average_ties_are_retained_without_jitter() -> None:
    result = features.compute_consensus_frame(
        _panel([1.0, 1.0, 3.0], [3.0, 3.0, 1.0]),
        factors=SPECS,
        minimum_common_support_names=3,
    )

    assert result[features.FACTOR_NAME].tolist() == pytest.approx(
        [0.5, 0.5, 1.0]
    )


def test_missing_component_removes_name_and_reranks_common_support() -> None:
    result = features.compute_consensus_frame(
        _panel([np.nan, 2.0, 3.0], [3.0, 2.0, 1.0]),
        factors=SPECS,
        minimum_common_support_names=2,
    )

    assert result[f"{features.FACTOR_NAME}_eligible"].tolist() == [False, True, True]
    assert np.isnan(result[features.FACTOR_NAME].iloc[0])
    assert result[features.FACTOR_NAME].iloc[1:].tolist() == pytest.approx(
        [0.5, 1.0]
    )


def test_session_below_minimum_common_support_is_wholly_missing() -> None:
    result = features.compute_consensus_frame(
        _panel([1.0, 2.0, 3.0], [3.0, 2.0, np.nan]),
        factors=SPECS,
        minimum_common_support_names=3,
    )

    assert not result[f"{features.FACTOR_NAME}_eligible"].any()
    assert result[features.FACTOR_NAME].isna().all()


def test_duplicate_keys_and_missing_columns_fail_closed() -> None:
    duplicated = _panel([1.0, 2.0], [2.0, 1.0])
    duplicated.loc[1, "symbol"] = duplicated.loc[0, "symbol"]
    with pytest.raises(features.Campaign044FeatureError):
        features.compute_consensus_frame(
            duplicated,
            factors=SPECS,
            minimum_common_support_names=2,
        )

    with pytest.raises(features.Campaign044FeatureError):
        features.compute_consensus_frame(
            duplicated.drop(columns="lower_factor"),
            factors=SPECS,
            minimum_common_support_names=2,
        )


def test_quality_listing_keys_are_strictly_intersected_with_minute_identity() -> None:
    keys, dates = features._intersect_sorted_master_keys(
        np.array([1, 2, 3, 4], dtype=np.int64),
        np.array(
            ["2025-01-02", "2025-01-02", "2025-01-03", "2025-01-03"],
            dtype="datetime64[ns]",
        ),
        np.array([2, 4, 9], dtype=np.int64),
    )

    assert keys.tolist() == [2, 4]
    np.testing.assert_array_equal(
        dates,
        np.array(["2025-01-02", "2025-01-03"], dtype="datetime64[ns]"),
    )
    with pytest.raises(features.Campaign044FeatureError):
        features._intersect_sorted_master_keys(
            np.array([1, 2], dtype=np.int64),
            np.array(["2025-01-02", "2025-01-03"], dtype="datetime64[ns]"),
            np.array([9], dtype=np.int64),
        )


def test_protocol_freezes_all_terminal_factors_and_excludes_candidate49() -> None:
    spec = features.load_protocol()
    factors = features.source_factor_specs(spec)

    assert len(factors) == features.SOURCE_FACTOR_COUNT == 66
    assert len({item["name"] for item in factors}) == 66
    assert features.ACTIVE_CANDIDATE49_FACTOR not in {
        item["name"] for item in factors
    }
    assert features._comparison_order_digest(factors) == (
        features.SOURCE_FACTOR_ORDER_SHA256
    )
    assert factors[3] == {
        "name": "intraday_realized_volatility",
        "score_direction": "lower",
    }
    assert factors[28:30] == [
        {
            "name": "intraday_lunch_repricing_persistence_119m",
            "score_direction": "higher",
        },
        {
            "name": "intraday_directional_price_impact_asymmetry_238m",
            "score_direction": "higher",
        },
    ]
    assert factors[-1] == {
        "name": "intraday_transaction_vwap_consensus_240m",
        "score_direction": "higher",
    }
    assert spec["candidate"]["all_components_required"] is True
    assert len(spec["append_only_attempt_catalog"]) == 3
    assert spec["append_only_attempt_catalog"][0]["kind"] == (
        "pre_value_design_rejection"
    )
    assert spec["append_only_attempt_catalog"][1]["kind"] == (
        "pre_value_design_rejection"
    )


def test_source_catalog_order_uses_no_candidate49_snapshot() -> None:
    catalog, verifications = features._build_source_catalog(
        data_root=features.DEFAULT_DATA_ROOT,
        workers=1,
        verify_files=False,
    )
    observed = [factor for item in catalog for factor in item["factors"]]

    assert observed == [
        item["name"] for item in features.source_factor_specs()
    ]
    assert features.ACTIVE_CANDIDATE49_FACTOR not in observed
    assert sum(len(item["factors"]) for item in catalog) == 66
    assert len(verifications) == len(catalog)
    assert all(
        item["file_verification_deferred"] is True
        for item in verifications.values()
    )


def test_status_reads_no_factor_value_price_or_return() -> None:
    result = features.status(
        features.DEFAULT_DATA_ROOT,
        features.DEFAULT_EXPERIMENT_ROOT,
    )

    assert result["protocol_sha256_bound"] is True
    assert result["source_factor_count"] == 66
    assert result["active_candidate49_factor_excluded"] == (
        features.ACTIVE_CANDIDATE49_FACTOR
    )
    assert result["source_factor_values_read_by_status"] is False
    assert result["daily_price_fields_read_by_status"] is False
    assert result["forward_return_fields_read_by_status"] is False
    assert result["candidate49_factor_values_read_by_status"] is False
    assert result["candidate49_historical_return_read"] is False
