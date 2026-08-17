from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts import a_share_three_day_compact_comparator_cache as cache


def test_protocol_and_complete_numeric_orders_are_frozen() -> None:
    spec = cache.load_protocol()
    numeric, complete = cache.numeric_definitions()
    assert spec["status"] == (
        "frozen_before_compact_comparator_values_or_cache_files_are_materialized"
    )
    assert len(numeric) == 98
    assert numeric[-1] == {
        "name": "quarterly_roe_profit_scale_efficiency_gap_2r",
        "score_direction": "higher",
    }
    assert len(complete) == 99
    assert cache.STRUCTURAL_FACTOR not in [item["name"] for item in numeric]
    assert cache.STRUCTURAL_FACTOR in [item["name"] for item in complete]


def test_candidate_independent_eligibility_key_fingerprint_is_exact() -> None:
    keys = cache.eligible_keys()
    assert len(keys) == 1_331_759
    assert len(np.unique(keys // 4_000_000)) == 1_632
    assert np.all(keys[1:] > keys[:-1])


def test_canonical_column_digest_preserves_finite_bits_and_missingness() -> None:
    first = np.array([1.0, np.nan, -0.0, np.inf, -2.5], dtype=np.float64)
    second = first.copy()
    second[1] = np.float64("nan")
    assert cache.canonical_column_sha256(first) == cache.canonical_column_sha256(
        second
    )
    changed = first.copy()
    changed[-1] = -2.5000000000000004
    assert cache.canonical_column_sha256(first) != cache.canonical_column_sha256(
        changed
    )
    changed_missing = first.copy()
    changed_missing[0] = np.nan
    assert cache.canonical_column_sha256(first) != cache.canonical_column_sha256(
        changed_missing
    )


def test_synthetic_ties_pairwise_missingness_and_parquet_roundtrip_are_exact(
    tmp_path: Path,
) -> None:
    _, _, _, _, _, engine = (
        cache.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    days = np.repeat(np.array([18_000, 18_001, 18_002], dtype=np.int64), 6)
    securities = np.tile(np.arange(1_000_001, 1_000_007, dtype=np.int64), 3)
    keys = days * 4_000_000 + securities
    candidate = np.array(
        [
            1, 1, 2, 3, np.nan, 4,
            6, 5, 5, 4, 3, 2,
            1, np.nan, np.nan, np.nan, 2, 3,
        ],
        dtype=np.float64,
    )
    comparison = np.array(
        [
            9, 9, 7, 6, 5, 4,
            1, 2, np.nan, 4, 4, 6,
            3, 2, np.nan, np.nan, 1, np.nan,
        ],
        dtype=np.float64,
    )
    gate = {
        "minimum_pairwise_names_per_session": 3,
        "minimum_pairwise_sessions_per_comparison": 1,
        "maximum_allowed_absolute_median_daily_rank_correlation": 0.8,
    }
    direct_high = engine._aligned_comparison_result(
        candidate_keys=keys,
        candidate_values=candidate,
        comparison_values=comparison,
        comparison="synthetic",
        direction="higher",
        gate=gate,
    )
    direct_low = engine._aligned_comparison_result(
        candidate_keys=keys,
        candidate_values=candidate,
        comparison_values=comparison,
        comparison="synthetic",
        direction="lower",
        gate=gate,
    )
    path = tmp_path / "roundtrip.parquet"
    pq.write_table(
        pa.table(
            {
                "stock_day_key": pa.array(keys, type=pa.int64()),
                "synthetic": pa.array(
                    comparison,
                    type=pa.float64(),
                    from_pandas=False,
                ),
            }
        ),
        path,
        compression="zstd",
        use_dictionary=False,
    )
    restored = (
        pq.read_table(path)["synthetic"]
        .combine_chunks()
        .to_numpy(zero_copy_only=False)
    )
    roundtrip_high = engine._aligned_comparison_result(
        candidate_keys=keys,
        candidate_values=candidate,
        comparison_values=restored,
        comparison="synthetic",
        direction="higher",
        gate=gate,
    )
    roundtrip_low = engine._aligned_comparison_result(
        candidate_keys=keys,
        candidate_values=candidate,
        comparison_values=restored,
        comparison="synthetic",
        direction="lower",
        gate=gate,
    )
    assert roundtrip_high == direct_high
    assert roundtrip_low == direct_low
    assert direct_high["pairwise_sessions"] == 2
    assert direct_low["median_daily_rank_correlation"] == pytest.approx(
        -direct_high["median_daily_rank_correlation"], abs=1e-15
    )


def test_capture_sink_requires_exact_order_direction_and_keys(tmp_path: Path) -> None:
    keys = np.array([1, 2, 3], dtype=np.int64)
    matrix = np.lib.format.open_memmap(
        tmp_path / "matrix.npy",
        mode="w+",
        dtype=np.float64,
        shape=(3, 1),
    )
    sink = cache._CaptureComparisonEngine(
        keys=keys,
        matrix=matrix,
        definitions=[{"name": "factor_a", "score_direction": "higher"}],
    )
    result = sink._aligned_comparison_result(
        candidate_keys=keys,
        candidate_values=np.zeros(3),
        comparison_values=np.array([1.0, np.nan, 2.0]),
        comparison="factor_a",
        direction="higher",
        gate={},
    )
    assert result["comparison_factor"] == "factor_a"
    assert sink.seen == ["factor_a"]
    assert np.array_equal(np.isfinite(matrix[:, 0]), [True, False, True])


def test_status_and_unconfirmed_build_read_no_comparator_values() -> None:
    payload = cache.status()
    assert payload["output_exists"] is False
    assert payload["manifest_exists"] is False
    assert payload["comparison_factor_values_read_by_status"] is False
    assert payload["historical_daily_price_or_forward_return_values_read"] is False
    assert payload["provider_request_issued"] is False
    with pytest.raises(cache.CompactComparatorCacheError, match="--confirm-build"):
        cache.build_cache(
            data_root=cache.DEFAULT_DATA_ROOT,
            output_root=cache.DEFAULT_OUTPUT_ROOT,
            workers=1,
            confirm_build=False,
        )


def test_protocol_declares_no_rank_cache_and_future_only_use() -> None:
    spec = json.loads(cache.PROTOCOL_PATH.read_text(encoding="utf-8"))
    library = spec["numeric_library_contract"]
    equivalence = spec["semantic_equivalence_contract"]
    assert library["cross_sectional_rank_materialization_allowed"] is False
    assert equivalence["retroactive_campaign067_substitution_allowed"] is False
    assert "exact equality" in equivalence["actual_97_factor_gate"]
