from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign063_no_return_audit as audit


def test_static_snapshot_bindings_and_zero_eligible_semantics_are_frozen() -> None:
    result = audit.verify_static_bindings()
    assert result["candidate_manifest_sha256"] == audit.SNAPSHOT_MANIFEST_SHA256
    assert result["candidate_dataset_sha256"] == audit.SNAPSHOT_DATASET_SHA256
    assert result["structural_diagnosis_sha256"] == audit.STRUCTURAL_DIAGNOSIS_SHA256
    assert result["comparison_count"] == 94
    assert result["eligible_rows"] == 0


def test_protocol_reconstructs_exact_94_factor_order_without_values() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(comparisons) == 94
    assert comparisons[-1] == {
        "name": "quarterly_announcement_peer_crowding_sparsity",
        "score_direction": "higher",
    }


def test_status_is_comparison_and_return_closed_before_audit() -> None:
    payload = audit.status(audit.DEFAULT_EXPERIMENT_ROOT)
    assert payload["audit_count"] == 0
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read"] == []
    assert payload["historical_forward_return_fields_read"] is False
    assert payload["candidate49_historical_return_read"] is False
    assert payload["provider_request_issued"] is False


def test_snapshot_quality_requires_terminal_coverage_failure() -> None:
    static = audit.verify_static_bindings()
    assert static["eligible_rows"] == 0
    diagnosis = audit.json.loads(audit.STRUCTURAL_DIAGNOSIS.read_text(encoding="utf-8"))
    assert diagnosis["frozen_variance_replay"]["position236"] == {
        "rows": 1699,
        "zero_variance_rows": 1699,
        "nonpositive_variance_rows": 1699,
        "minimum": 0.0,
        "median": 0.0,
    }
    assert diagnosis["decision"]["comparison_library_must_remain_unopened"] is True
