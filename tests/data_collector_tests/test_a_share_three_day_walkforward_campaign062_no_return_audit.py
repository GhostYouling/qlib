from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign062_no_return_audit as audit


def test_static_snapshot_bindings_are_frozen() -> None:
    result = audit.verify_static_bindings()
    assert result["candidate_manifest_sha256"] == audit.SNAPSHOT_MANIFEST_SHA256
    assert result["candidate_dataset_sha256"] == audit.SNAPSHOT_DATASET_SHA256
    assert result["campaign061_manifest_sha256"] == audit.C61_SNAPSHOT_SHA256
    assert result["comparison_count"] == 93


def test_protocol_reconstructs_exact_93_factor_order() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(comparisons) == 93
    assert comparisons[-1] == {
        "name": audit.C61_FACTOR,
        "score_direction": "higher",
    }


def test_status_is_return_closed_before_audit() -> None:
    payload = audit.status(audit.DEFAULT_EXPERIMENT_ROOT)
    assert payload["audit_count"] == 0
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read"] == []
    assert payload["historical_forward_return_fields_read"] is False
    assert payload["candidate49_historical_return_read"] is False
    assert payload["provider_request_issued"] is False
