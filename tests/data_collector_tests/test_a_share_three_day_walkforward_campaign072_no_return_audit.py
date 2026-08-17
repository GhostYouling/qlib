from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign072_no_return_audit as audit


def test_campaign072_audit_order_is_complete() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(comparisons) == 102
    assert comparisons[-1] == {
        "name": "quarterly_net_profit_scale_rank",
        "score_direction": "higher",
    }
    assert (
        audit.candidate._runtime["_comparison_order_digest"](comparisons)
        == audit.EXPECTED_COMPARISON_ORDER_SHA256
    )


def test_campaign072_snapshot_is_frozen_before_audit_activation() -> None:
    assert audit.SNAPSHOT_MANIFEST_PATH.is_file()
    assert audit._sha256(audit.SNAPSHOT_MANIFEST_PATH) == audit.SNAPSHOT_MANIFEST_SHA256
    assert audit._sha256(audit.SNAPSHOT_BINDING) == audit.SNAPSHOT_BINDING_SHA256
    assert audit.EXPECTED_ELIGIBLE_ROWS == 7_231_483


def test_campaign072_status_preserves_prior_comparison_reads_but_no_returns() -> None:
    payload = audit.status()
    assert payload["audit_count"] == 0
    assert payload["coverage_or_capacity_metrics_previously_computed"] is True
    assert payload["comparison_values_read_by_status"] is True
    assert payload["historical_daily_price_fields_read"] == []
    assert payload["historical_forward_return_fields_read"] is False
    assert payload["provider_request_issued"] is False


def test_campaign072_static_hash_constants_match_candidate() -> None:
    assert (
        audit.EXPECTED_COMPARISON_ORDER_SHA256
        == audit.candidate.COMPARISON_ORDER_SHA256
    )
    assert (
        audit.EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256
        == audit.candidate.FULL_DEFINITION_ORDER_SHA256
    )
    assert audit.C71_SNAPSHOT_MANIFEST_PATH.is_file()
    assert (
        audit._sha256(audit.C71_SNAPSHOT_MANIFEST_PATH)
        == audit.candidate.C71_SNAPSHOT_MANIFEST_SHA256
    )
    assert (
        audit._sha256(audit.C71_SNAPSHOT_BINDING)
        == audit.candidate.C71_SNAPSHOT_BINDING_SHA256
    )


def test_campaign072_overrides_reach_the_executing_inner_runtime() -> None:
    inner = audit._runtime["_runtime"]
    assert inner["load_protocol"] is audit.load_protocol
    assert inner["_load_implementation_freeze"] is audit._load_implementation_freeze
    assert inner["_load_activation_binding"] is audit._load_activation_binding
    assert inner["verify_static_bindings"] is audit.verify_static_bindings
    assert inner["_load_comparisons_after_coverage"] is audit._load_comparisons_after_coverage
    assert inner["EXPECTED_COMPARISON_COUNT"] == 102
    assert inner["EXPECTED_COMPLETE_DEFINITION_COUNT"] == 103


def test_campaign072_exports_inherited_campaign070_compatibility_bindings() -> None:
    assert (
        audit.candidate.C70_SNAPSHOT_DATASET_SHA256
        == "35ea87d9e183b77a382a88789cedf96d79f6a102c5006e156bbde2ff87fd6efe"
    )
    assert (
        audit.candidate.C70_SNAPSHOT_BINDING_SHA256
        == "4c573c47ce247cac96c492ae37f93c39356303db18f05c093f1446a765e8aa34"
    )


def test_campaign072_layered_comparator_counts_are_101_then_102(monkeypatch) -> None:
    observed = []

    def fake_base_loader(**kwargs):
        del kwargs
        observed.append(audit._runtime["EXPECTED_COMPARISON_COUNT"])
        return ([{"comparison_factor": str(index)} for index in range(101)], {})

    def fake_append(**kwargs):
        del kwargs
        return ({"comparison_factor": audit.candidate.C71_FACTOR}, {"status": "synthetic"})

    monkeypatch.setattr(audit, "_base_load_comparisons", fake_base_loader)
    monkeypatch.setitem(audit._runtime["_runtime"], "_append_snapshot_comparison", fake_append)
    comparisons, receipts = audit._load_comparisons_after_coverage(
        candidate_keys=None,
        candidate_values=None,
        gate=None,
        engine=None,
        comparison_engine=None,
        workers=1,
    )
    assert observed == [101]
    assert len(comparisons) == 102
    assert comparisons[-1]["comparison_factor"] == audit.candidate.C71_FACTOR
    assert receipts["all_102_sources_loaded_in_frozen_order"] is True
    assert audit._runtime["EXPECTED_COMPARISON_COUNT"] == 102


def test_campaign072_append_helper_lives_in_executing_inner_runtime() -> None:
    assert "_append_snapshot_comparison" not in audit._runtime
    assert callable(audit._runtime["_runtime"]["_append_snapshot_comparison"])
