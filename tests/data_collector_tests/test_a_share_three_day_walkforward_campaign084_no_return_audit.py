from __future__ import annotations

import json

from scripts import a_share_three_day_walkforward_campaign084_no_return_audit as audit


def test_protocol_and_orders_are_frozen_before_coverage() -> None:
    spec = audit.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert gate["numeric_comparator_count"] == 113
    assert gate["complete_definition_count"] == 115
    assert len(gate["comparison_factors"]) == 113
    assert gate["comparison_factors"][-1] == {
        "name": "intraday_close_frontier_innovation_share_238p",
        "score_direction": "higher",
    }
    assert gate["all_113_numeric_comparators_must_pass"] is True


def test_snapshot_identity_is_frozen_without_loading_values() -> None:
    manifest = json.loads(audit.SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert audit._sha256(audit.SNAPSHOT_MANIFEST_PATH) == audit.SNAPSHOT_MANIFEST_SHA256
    assert manifest["dataset_sha256"] == audit.SNAPSHOT_DATASET_SHA256
    assert manifest["partitions"] == 33015
    assert manifest["rows"] == 7724498
    assert manifest["factor_eligible_rows"][audit.FACTOR_NAME] == 6321289
    assert manifest["comparison_factor_values_read"] is False
    assert manifest["daily_price_fields_read"] == []
    assert manifest["forward_return_fields_read"] is False


def test_status_is_truthful_before_the_sole_audit() -> None:
    status = audit.status()
    assert status["candidate_snapshot_exists"] is True
    assert status["audit_count"] == 0
    assert status["coverage_or_capacity_metrics_computed_by_status"] is False
    assert status["comparison_values_read_by_status"] is False
    assert status["historical_daily_price_fields_read"] == []
    assert status["historical_forward_return_fields_read"] is False
    assert status["provider_request_issued"] is False


def test_audit_implementation_and_activation_bindings_are_live_when_published() -> None:
    if audit.AUDIT_IMPLEMENTATION_FREEZE.is_file():
        implementation = audit._load_implementation_freeze()
        assert implementation["comparison_values_read_before_freeze"] is False
    if audit.AUDIT_ACTIVATION_BINDING.is_file():
        activation = audit._load_activation_binding()
        assert activation["comparison_values_read_before_activation"] is False
        assert (
            activation["candidate_snapshot"]["dataset_sha256"]
            == audit.SNAPSHOT_DATASET_SHA256
        )
