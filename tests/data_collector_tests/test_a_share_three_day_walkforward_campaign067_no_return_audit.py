from __future__ import annotations

import json

from scripts import a_share_three_day_walkforward_campaign067_no_return_audit as audit


def test_campaign067_complete_definition_and_numeric_orders_are_bound() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factors"]
    complete = audit.reconstruct_complete_definitions(comparisons)

    assert len(comparisons) == 97
    assert len(complete) == 98
    assert comparisons[-1] == {
        "name": "quarterly_quality_rank_balance_3f",
        "score_direction": "higher",
    }
    assert audit.STRUCTURALLY_NONNUMERIC_FACTOR in [item["name"] for item in complete]
    assert audit.STRUCTURALLY_NONNUMERIC_FACTOR not in [item["name"] for item in comparisons]


def test_campaign067_static_snapshot_bindings_are_exact() -> None:
    payload = audit.verify_static_bindings()
    assert payload["candidate_manifest_sha256"] == audit.SNAPSHOT_MANIFEST_SHA256
    assert payload["candidate_dataset_sha256"] == audit.SNAPSHOT_DATASET_SHA256
    assert payload["campaign066_manifest_sha256"] == audit.C66_SNAPSHOT_SHA256
    assert payload["campaign066_dataset_sha256"] == audit.C66_DATASET_SHA256
    assert payload["comparison_count"] == 97


def test_campaign067_audit_freeze_is_pre_metric_and_pre_return() -> None:
    freeze = json.loads(audit.AUDIT_IMPLEMENTATION_FREEZE.read_text())
    assert freeze["audit_runner"]["sha256"] == audit._sha256(audit.Path(audit.__file__))
    assert freeze["coverage_or_capacity_metrics_computed_before_freeze"] is False
    assert freeze["comparison_values_read_before_freeze"] is False
    assert freeze["historical_daily_price_fields_read_before_freeze"] == []
    assert freeze["historical_forward_returns_read_before_freeze"] is False
    assert freeze["io_semantics"]["unsafe_completed_audit_receipt_shortcut_used"] is False


def test_campaign067_status_does_not_load_comparison_values() -> None:
    payload = audit.status()
    assert payload["audit_count"] == 0
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read"] == []
    assert payload["historical_forward_return_fields_read"] is False
    assert payload["provider_request_issued"] is False
