from __future__ import annotations

import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign059_no_return_audit as audit


def test_static_bindings_reconstruct_exact_90_factor_order() -> None:
    result = audit.verify_static_bindings()
    assert result["comparison_count"] == 90
    assert result["comparison_order_sha256"] == audit.EXPECTED_COMPARISON_ORDER_SHA256
    assert result["market_benchmark_manifest_sha256"] == audit.candidate.MARKET_BENCHMARK_MANIFEST_SHA256
    assert result["market_benchmark_frame_sha256"] == audit.candidate.MARKET_BENCHMARK_FRAME_SHA256


def test_protocol_appends_campaign058_once_after_89_prior_definitions() -> None:
    spec = audit._load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factors"]
    assert len(comparisons) == 90
    assert comparisons[-1] == {
        "name": "quarterly_profit_revenue_growth_spread_pp",
        "score_direction": "higher",
    }
    assert sum(item["name"] == "quarterly_profit_revenue_growth_spread_pp" for item in comparisons) == 1


def test_campaign058_snapshot_binding_is_exact() -> None:
    assert audit._local_sha256(audit.C58_SNAPSHOT_PATH) == audit.C58_SNAPSHOT_SHA256
    manifest = audit.json.loads(audit.C58_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert manifest["dataset_sha256"] == audit.C58_DATASET_SHA256
    assert manifest["factor_names"] == [audit.C58_FACTOR]


def test_generated_runner_is_bound_to_campaign059_overrides() -> None:
    globals_ = audit._base_run_no_return_audit.__globals__
    assert globals_["candidate"].FACTOR_NAME == audit.FACTOR_NAME
    assert globals_["EXPECTED_COMPARISON_COUNT"] == 90
    assert globals_["_load_bound_prior_snapshots"] is audit._load_bound_prior_snapshots
    assert globals_["_append_all_prior_comparisons"] is audit._append_all_prior_comparisons
    assert globals_["verify_static_bindings"] is audit.verify_static_bindings


def test_status_reads_no_partition_candidate_comparison_or_return_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pd,
        "read_parquet",
        lambda *args, **kwargs: pytest.fail("status must not read parquet values"),
    )
    result = audit.status()
    assert result["comparison_count"] == 90
    assert result["daily_price_fields_read_by_status"] is False
    assert result["forward_return_fields_read_by_status"] is False
    assert result["provider_request_issued_by_status"] is False
