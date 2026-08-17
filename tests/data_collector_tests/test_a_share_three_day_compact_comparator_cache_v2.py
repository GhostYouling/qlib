from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts import a_share_three_day_compact_comparator_cache_v2 as cache


def _keys(dates: list[str], symbols: list[str]) -> np.ndarray:
    _, _, _, _, _, engine = (
        cache.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    return engine._compact_stock_day_keys(
        pd.Series(dates, dtype="datetime64[ns]"),
        pd.Series(symbols, dtype="object"),
    ).astype(np.int64, copy=False)


def test_v2_protocol_binds_v1_failure_and_preserves_library() -> None:
    spec = cache.load_protocol()
    numeric, complete = cache.v1.numeric_definitions()
    assert spec["recorded_v1_failure"]["v1_formal_output_published"] is False
    assert spec["recorded_v1_failure"]["v1_temporary_values_reusable"] is False
    assert spec["frozen_output"]["output_root"] == str(cache.DEFAULT_OUTPUT_ROOT)
    assert len(numeric) == 98
    assert len(complete) == 99
    assert numeric[-1]["name"] == "quarterly_roe_profit_scale_efficiency_gap_2r"


def test_explicit_alignment_preserves_values_and_marks_absent_keys_nan(
    tmp_path: Path,
) -> None:
    source_dates = ["2020-01-02", "2020-01-02", "2020-01-02"]
    source_symbols = ["SZ000001", "SZ000003", "SZ000004"]
    target_dates = ["2020-01-02", "2020-01-02", "2020-01-02"]
    target_symbols = ["SZ000001", "SZ000002", "SZ000003"]
    target_keys = np.sort(_keys(target_dates, target_symbols), kind="stable")
    path = tmp_path / "source.parquet"
    pq.write_table(
        pa.table(
            {
                "trade_date": pa.array(source_dates),
                "symbol": pa.array(source_symbols),
                "factor_a": pa.array([1.25, -0.0, 99.0], type=pa.float64()),
            }
        ),
        path,
    )
    values, receipt = cache._scan_explicit_values(
        paths=[str(path)],
        factors=["factor_a"],
        target_keys=target_keys,
        expected_rows=3,
    )
    observed = values["factor_a"]
    assert observed[0] == 1.25
    assert np.isnan(observed[1])
    assert observed[2] == 0.0 and np.signbit(observed[2])
    assert receipt == {
        "source_rows": 3,
        "requested_global_keys": 3,
        "matched_global_keys": 2,
        "absent_global_keys": 1,
    }


def test_explicit_alignment_fails_closed_on_duplicate_requested_key(
    tmp_path: Path,
) -> None:
    dates = ["2020-01-02", "2020-01-02"]
    symbols = ["SZ000001", "SZ000001"]
    path = tmp_path / "duplicate.parquet"
    pq.write_table(
        pa.table(
            {
                "trade_date": pa.array(dates),
                "symbol": pa.array(symbols),
                "factor_a": pa.array([1.0, 2.0], type=pa.float64()),
            }
        ),
        path,
    )
    with pytest.raises(
        cache.CompactComparatorCacheV2Error,
        match="duplicate requested source keys",
    ):
        cache._scan_explicit_values(
            paths=[str(path)],
            factors=["factor_a"],
            target_keys=_keys(["2020-01-02"], ["SZ000001"]),
            expected_rows=2,
        )


def test_status_and_unconfirmed_v2_build_read_no_comparator_values() -> None:
    payload = cache.status()
    assert payload["v1_output_exists"] is False
    assert payload["v2_output_exists"] is False
    assert payload["v2_manifest_exists"] is False
    assert payload["comparison_factor_values_read_by_status"] is False
    assert payload["historical_daily_price_or_forward_return_values_read"] is False
    assert payload["provider_request_issued"] is False
    with pytest.raises(cache.CompactComparatorCacheV2Error, match="--confirm-build"):
        cache.build_cache(
            data_root=cache.DEFAULT_DATA_ROOT,
            output_root=cache.DEFAULT_OUTPUT_ROOT,
            workers=1,
            confirm_build=False,
        )


def test_v2_protocol_forbids_imputation_rank_cache_and_v1_temp_reuse() -> None:
    spec = json.loads(cache.PROTOCOL_PATH.read_text(encoding="utf-8"))
    loader = spec["repair_loader_contract"]
    library = spec["numeric_library_contract"]
    failure = spec["failure_policy"]
    assert "NaN" in loader["source_key_absent"]
    assert "imputation" in loader["source_key_present"]
    assert library["cross_sectional_rank_materialization_allowed"] is False
    assert failure["reuse_v1_failed_temporary_root"] is False


def test_frozen_v1_builder_and_failure_record_are_unchanged() -> None:
    assert cache._sha256(Path(cache.v1.__file__).resolve()) == cache.V1_BUILDER_SHA256
    assert cache._sha256(cache.V1_FAILURE_PATH) == cache.V1_FAILURE_SHA256
