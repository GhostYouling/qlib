from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from scripts import a_share_three_day_walkforward_campaign074_no_return_audit as audit


def test_protocol_injects_exact_104_comparators_after_prevalue_freeze() -> None:
    spec = audit.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    comparisons = gate["comparison_factors"]
    assert len(comparisons) == audit.EXPECTED_COMPARISON_COUNT
    assert comparisons[-1] == {
        "name": audit.candidate.C73_FACTOR,
        "score_direction": "higher",
    }
    assert audit.candidate._comparison_order_digest(comparisons) == (
        audit.EXPECTED_COMPARISON_ORDER_SHA256
    )


def test_complete_library_retains_structurally_nonnumeric_challenge() -> None:
    complete = audit.candidate.reconstruct_complete_definitions()
    numeric = audit.candidate.reconstruct_comparisons()
    assert len(complete) == audit.EXPECTED_COMPLETE_DEFINITION_COUNT
    assert audit.STRUCTURALLY_NONNUMERIC_FACTOR in [item["name"] for item in complete]
    assert audit.STRUCTURALLY_NONNUMERIC_FACTOR not in [item["name"] for item in numeric]


def test_snapshot_identity_is_bound_without_reading_factor_values() -> None:
    assert audit._sha256(audit.SNAPSHOT_MANIFEST_PATH) == (
        audit.SNAPSHOT_MANIFEST_SHA256
    )
    assert audit._sha256(audit.SNAPSHOT_BINDING) == audit.SNAPSHOT_BINDING_SHA256
    assert audit._sha256(audit.C73_SNAPSHOT_MANIFEST_PATH) == (
        audit.candidate.C73_MANIFEST_SHA256
    )


def test_frozen_ranges_include_candidate_and_campaign073() -> None:
    engine = SimpleNamespace(FACTOR_RANGES={})
    audit._install_frozen_ranges(engine)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (0.0, 1.0)
    assert engine.FACTOR_RANGES[audit.candidate.C73_FACTOR] == (0.0, 1.0)


def test_postcoverage_loader_appends_campaign073_exactly_once(monkeypatch) -> None:
    prior = [
        {"comparison_factor": item["name"], "gate_passed": True}
        for item in audit.candidate.reconstruct_comparisons()[:-1]
    ]
    monkeypatch.setattr(
        audit.base,
        "_load_comparisons_after_coverage",
        lambda **kwargs: (list(prior), {"all_103_sources_loaded_in_frozen_order": True}),
    )
    monkeypatch.setattr(
        audit.base,
        "_append_snapshot_comparison",
        lambda **kwargs: (
            {
                "comparison_factor": audit.candidate.C73_FACTOR,
                "gate_passed": True,
            },
            {"status": "verified"},
        ),
    )
    comparisons, receipts = audit._load_comparisons_after_coverage(
        coverage={"gate_passed_before_comparison_values": True},
        candidate_keys=np.array([1], dtype=np.uint64),
        candidate_values=np.array([0.5]),
        gate={},
        engine=object(),
        comparison_engine=object(),
        workers=1,
    )
    assert len(comparisons) == 104
    assert comparisons[-1]["comparison_factor"] == audit.candidate.C73_FACTOR
    assert "all_103_sources_loaded_in_frozen_order" not in receipts
    assert receipts["all_104_sources_loaded_in_frozen_order"] is True


def test_status_is_read_only_and_reports_no_metrics() -> None:
    result = audit.status()
    assert result["candidate_snapshot_exists"] is True
    assert result["audit_count"] == 0
    assert result["coverage_or_capacity_metrics_computed_by_status"] is False
    assert result["comparison_values_read_by_status"] is False
    assert result["historical_forward_return_fields_read"] is False
    assert result["provider_request_issued"] is False
