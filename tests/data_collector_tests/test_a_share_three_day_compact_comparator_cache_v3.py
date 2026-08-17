from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pytest

from scripts import a_share_three_day_compact_comparator_cache_v3 as cache


class _KeyDelegate:
    def __init__(self) -> None:
        self.calls: list[tuple[object, object]] = []

    def _compact_stock_day_keys(self, trade_dates: object, symbols: object) -> np.ndarray:
        self.calls.append((trade_dates, symbols))
        return np.array([11, 12], dtype=np.int64)


def test_v3_protocol_binds_v2_failure_and_exact_member_audit() -> None:
    spec = cache.load_protocol()
    audit = spec["post_campaign057_engine_member_audit"]
    assert spec["recorded_v2_failure"]["v2_formal_output_published"] is False
    assert spec["recorded_v2_failure"]["v2_temporary_values_reusable"] is False
    assert spec["frozen_output"]["output_root"] == str(cache.DEFAULT_OUTPUT_ROOT)
    assert audit["members_observed"] == [
        "_aligned_comparison_result",
        "_compact_stock_day_keys",
    ]
    assert audit["other_members_allowed"] is False


def test_post_campaign057_source_member_audit_is_complete() -> None:
    observed: set[str] = set()
    for campaign in range(58, 68):
        for path in cache.REPO_ROOT.joinpath("scripts").glob(
            f"a_share_three_day_walkforward_campaign{campaign:03d}*.py"
        ):
            observed.update(
                re.findall(
                    r"comparison_engine\.([A-Za-z_][A-Za-z0-9_]*)",
                    path.read_text(encoding="utf-8"),
                )
            )
    assert observed == {"_aligned_comparison_result", "_compact_stock_day_keys"}


def test_capture_proxy_preserves_sink_and_delegates_only_key_helper(
    tmp_path: Path,
) -> None:
    keys = np.array([1, 2], dtype=np.int64)
    matrix = np.lib.format.open_memmap(
        tmp_path / "matrix.npy",
        mode="w+",
        dtype=np.float64,
        shape=(2, 1),
    )
    delegate = _KeyDelegate()
    proxy = cache._DelegatingCaptureComparisonEngine(
        delegate=delegate,
        keys=keys,
        matrix=matrix,
        definitions=[{"name": "factor_a", "score_direction": "higher"}],
    )
    dates = object()
    symbols = object()
    assert np.array_equal(
        proxy._compact_stock_day_keys(dates, symbols),
        np.array([11, 12], dtype=np.int64),
    )
    assert delegate.calls == [(dates, symbols)]
    result = proxy._aligned_comparison_result(
        candidate_keys=keys,
        candidate_values=np.zeros(2),
        comparison_values=np.array([1.25, np.nan]),
        comparison="factor_a",
        direction="higher",
        gate={},
    )
    assert result["comparison_factor"] == "factor_a"
    assert proxy.seen == ["factor_a"]
    assert matrix[0, 0] == 1.25
    assert np.isnan(matrix[1, 0])
    with pytest.raises(AttributeError):
        getattr(proxy, "unfrozen_helper")


def test_status_and_unconfirmed_v3_build_read_no_values() -> None:
    payload = cache.status()
    assert payload["failed_formal_outputs_exist"] is False
    assert payload["v3_output_exists"] is False
    assert payload["v3_manifest_exists"] is False
    assert payload["comparison_factor_values_read_by_status"] is False
    assert payload["historical_daily_price_or_forward_return_values_read"] is False
    assert payload["provider_request_issued"] is False
    with pytest.raises(cache.CompactComparatorCacheV3Error, match="--confirm-build"):
        cache.build_cache(
            data_root=cache.DEFAULT_DATA_ROOT,
            output_root=cache.DEFAULT_OUTPUT_ROOT,
            workers=1,
            confirm_build=False,
        )


def test_v2_builder_and_failure_record_remain_frozen() -> None:
    assert cache._sha256(Path(cache.v2.__file__).resolve()) == cache.V2_BUILDER_SHA256
    assert cache._sha256(cache.V2_FAILURE_PATH) == cache.V2_FAILURE_SHA256


def test_v3_inherits_v2_absent_key_alignment_tests() -> None:
    spec = cache.load_protocol()
    inherited = spec["inherited_v2_absent_key_contract"]
    assert inherited["source_key_absent_stored_as_nan"] is True
    assert inherited["duplicate_requested_source_key_fails_closed"] is True
    assert inherited["imputation_ranking_scaling_forward_or_backward_fill"] is False
