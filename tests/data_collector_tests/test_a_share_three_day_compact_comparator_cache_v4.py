from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache


def test_v4_protocol_binds_v3_diagnosis_and_dynamic_recipe() -> None:
    spec = cache.load_protocol()
    assert spec["recorded_v3_failure"]["v3_formal_output_published"] is False
    assert (
        spec["recorded_v3_failure"][
            "v3_temporary_values_reusable_for_v4_publication"
        ]
        is False
    )
    assert spec["bound_v3_diagnosis"]["mismatch_names"] == [
        "quality_growth",
        "quality_score",
    ]
    recipe = spec["dynamic_quality_recipe_contract"]
    assert recipe["candidate_intersection_precedes_ranking"] is True
    assert recipe["global_materialized_quality_growth_or_quality_score_may_be_stored"] is False
    assert recipe["raw_auxiliary_columns"] == list(cache.AUXILIARY_COLUMNS)


def test_v4_library_layout_preserves_98_logical_and_stores_99_physical() -> None:
    layout = cache._library_layout()
    assert len(layout["logical_names"]) == 98
    assert len(layout["fixed_names"]) == 96
    assert len(layout["physical_names"]) == 99
    assert all(name not in layout["physical_names"] for name in cache.DYNAMIC_COMPARATORS)
    assert layout["physical_names"][-3:] == list(cache.AUXILIARY_COLUMNS)
    assert layout["logical_names"][84:86] == list(cache.DYNAMIC_COMPARATORS)


def test_dynamic_recipe_matches_campaign058_direct_materialization() -> None:
    day0 = int(np.datetime64("2021-01-04", "D").astype(np.int64))
    day1 = int(np.datetime64("2021-01-05", "D").astype(np.int64))
    keys = np.array(
        [
            day0 * 4_000_000 + 1,
            day0 * 4_000_000 + 2,
            day0 * 4_000_000 + 3,
            day1 * 4_000_000 + 1,
            day1 * 4_000_000 + 2,
            day1 * 4_000_000 + 3,
        ],
        dtype=np.int64,
    )
    raw = {
        "quality_raw_roe": np.array([3.0, 1.0, 2.0, 4.0, 4.0, 1.0]),
        "quality_raw_profit_yoy": np.array([1.0, 3.0, 2.0, 2.0, 1.0, 3.0]),
        "quality_raw_revenue_yoy": np.array([2.0, 1.0, 3.0, 3.0, 2.0, 1.0]),
    }
    observed = cache.reconstruct_dynamic_quality_values(
        candidate_keys=keys,
        raw_auxiliary_values=raw,
    )
    direct = pd.DataFrame(
        {
            "datetime": pd.to_datetime((keys // 4_000_000).astype("datetime64[D]")),
            "roe": raw["quality_raw_roe"],
            "profit_yoy": raw["quality_raw_profit_yoy"],
            "revenue_yoy": raw["quality_raw_revenue_yoy"],
            "roe_change": np.zeros(len(keys)),
            "revenue_yoy_acceleration": np.zeros(len(keys)),
            "profit_yoy_acceleration": np.zeros(len(keys)),
            "quality_eligible": np.ones(len(keys), dtype=bool),
        }
    )
    expected = cache.quality_audit.materialize_quality_comparison_frame(direct)
    assert np.array_equal(
        observed["quality_growth"], expected["quality_growth"].to_numpy()
    )
    assert np.array_equal(
        observed["quality_score"], expected["quality_score"].to_numpy()
    )


def test_dynamic_composite_must_be_ranked_after_candidate_intersection() -> None:
    day = int(np.datetime64("2021-01-04", "D").astype(np.int64))
    keys = day * 4_000_000 + np.arange(1, 6, dtype=np.int64)
    raw = {
        "quality_raw_roe": np.array([9.0, 2.0, 6.0, 4.0, 1.0]),
        "quality_raw_profit_yoy": np.array([1.0, 8.0, 3.0, 5.0, 7.0]),
        "quality_raw_revenue_yoy": np.array([8.0, 1.0, 7.0, 2.0, 4.0]),
    }
    global_values = cache.reconstruct_dynamic_quality_values(
        candidate_keys=keys,
        raw_auxiliary_values=raw,
    )
    selected = np.array([0, 2, 4])
    subset_values = cache.reconstruct_dynamic_quality_values(
        candidate_keys=keys[selected],
        raw_auxiliary_values={name: values[selected] for name, values in raw.items()},
    )
    assert not np.array_equal(
        global_values["quality_growth"][selected],
        subset_values["quality_growth"],
    )
    assert not np.array_equal(
        global_values["quality_score"][selected],
        subset_values["quality_score"],
    )


def test_logical_reconstruction_uses_fixed_columns_and_dynamic_auxiliaries() -> None:
    layout = cache._library_layout()
    day = int(np.datetime64("2021-01-04", "D").astype(np.int64))
    keys = day * 4_000_000 + np.arange(1, 4, dtype=np.int64)
    physical = np.zeros((3, len(layout["physical_names"])), dtype=np.float64)
    physical_index = {
        name: index for index, name in enumerate(layout["physical_names"])
    }
    physical[:, physical_index[layout["fixed_names"][0]]] = [4.0, 5.0, 6.0]
    physical[:, physical_index["quality_raw_roe"]] = [3.0, 1.0, 2.0]
    physical[:, physical_index["quality_raw_profit_yoy"]] = [1.0, 3.0, 2.0]
    physical[:, physical_index["quality_raw_revenue_yoy"]] = [2.0, 1.0, 3.0]
    logical = cache._logical_values_from_physical(
        candidate_keys=keys,
        candidate_positions=np.arange(3),
        physical_matrix=physical,
        layout=layout,
    )
    assert set(logical) == set(layout["logical_names"])
    assert np.array_equal(logical[layout["fixed_names"][0]], [4.0, 5.0, 6.0])
    assert np.all(np.isfinite(logical["quality_growth"]))
    assert np.all(np.isfinite(logical["quality_score"]))


def test_dynamic_recipe_fails_closed_on_unsorted_or_missing_inputs() -> None:
    raw = {name: np.array([1.0, 2.0]) for name in cache.AUXILIARY_COLUMNS}
    with pytest.raises(cache.CompactComparatorCacheV4Error):
        cache.reconstruct_dynamic_quality_values(
            candidate_keys=np.array([2, 1], dtype=np.int64),
            raw_auxiliary_values=raw,
        )
    with pytest.raises(cache.CompactComparatorCacheV4Error):
        cache.reconstruct_dynamic_quality_values(
            candidate_keys=np.array([1, 2], dtype=np.int64),
            raw_auxiliary_values={"quality_raw_roe": np.array([1.0, 2.0])},
        )


def test_status_and_unconfirmed_v4_build_read_no_values() -> None:
    payload = cache.status()
    assert payload["failed_formal_outputs_exist"] is False
    assert payload["v4_output_exists"] is False
    assert payload["v4_manifest_exists"] is False
    assert payload["comparison_or_raw_auxiliary_values_read_by_status"] is False
    assert payload["historical_daily_price_or_forward_return_values_read"] is False
    assert payload["provider_request_issued"] is False
    with pytest.raises(cache.CompactComparatorCacheV4Error, match="--confirm-build"):
        cache.build_cache(
            data_root=cache.DEFAULT_DATA_ROOT,
            output_root=cache.DEFAULT_OUTPUT_ROOT,
            workers=1,
            confirm_build=False,
        )


def test_v3_builder_failure_and_diagnosis_remain_frozen() -> None:
    assert cache._sha256(Path(cache.v3.__file__).resolve()) == cache.V3_BUILDER_SHA256
    assert cache._sha256(cache.V3_FAILURE_PATH) == cache.V3_FAILURE_SHA256
    assert cache._sha256(cache.V3_DIAGNOSIS_PATH) == cache.V3_DIAGNOSIS_SHA256
