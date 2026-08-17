from __future__ import annotations

import json

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign068_no_return_audit as audit


def test_campaign068_complete_definition_and_numeric_orders_are_bound() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(comparisons) == 98
    assert comparisons[-1] == {
        "name": "quarterly_roe_profit_scale_efficiency_gap_2r",
        "score_direction": "higher",
    }
    assert audit.candidate._comparison_order_digest(comparisons) == (
        audit.EXPECTED_COMPARISON_ORDER_SHA256
    )


def test_campaign068_static_candidate_and_cache_bindings_are_exact() -> None:
    payload = audit.verify_static_bindings()
    assert payload["candidate_manifest_sha256"] == audit.SNAPSHOT_MANIFEST_SHA256
    assert payload["candidate_dataset_sha256"] == audit.SNAPSHOT_DATASET_SHA256
    assert payload["compact_cache_manifest_sha256"] == audit.CACHE_MANIFEST_SHA256
    assert payload["compact_cache_dataset_sha256"] == audit.CACHE_DATASET_SHA256
    assert payload["comparison_count"] == 98
    assert payload["comparator_values_read"] is False


def test_campaign068_cache_loader_refuses_failed_coverage_gate() -> None:
    with pytest.raises(
        audit.Campaign068NoReturnAuditError,
        match="forbidden before all coverage gates pass",
    ):
        audit._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": False},
            candidate_keys=np.array([], dtype=np.int64),
            candidate_values=np.array([], dtype=np.float64),
            gate={},
            comparison_engine=object(),
        )


def test_campaign068_audit_freeze_is_pre_metric_and_pre_return() -> None:
    freeze = json.loads(audit.AUDIT_IMPLEMENTATION_FREEZE.read_text())
    assert freeze["audit_runner"]["sha256"] == audit._sha256(
        audit.Path(audit.__file__)
    )
    assert freeze["coverage_or_capacity_metrics_computed_before_freeze"] is False
    assert freeze["comparison_values_read_before_freeze"] is False
    assert freeze["historical_daily_price_fields_read_before_freeze"] == []
    assert freeze["historical_forward_returns_read_before_freeze"] is False
    assert freeze["io_semantics"]["compact_cache_loader_is_coverage_guarded"] is True


def test_campaign068_status_does_not_load_comparison_values() -> None:
    payload = audit.status()
    assert payload["audit_count"] == 0
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read"] == []
    assert payload["historical_forward_return_fields_read"] is False
    assert payload["provider_request_issued"] is False
