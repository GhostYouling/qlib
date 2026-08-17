from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import a_share_three_day_walkforward_campaign066_no_return_audit as audit


def test_static_snapshot_bindings_are_frozen_without_partition_values():
    result = audit.verify_static_bindings()
    assert result["candidate_manifest_sha256"] == audit.SNAPSHOT_MANIFEST_SHA256
    assert result["candidate_dataset_sha256"] == audit.SNAPSHOT_DATASET_SHA256
    assert result["campaign065_manifest_sha256"] == audit.C65_SNAPSHOT_SHA256
    assert result["campaign065_dataset_sha256"] == audit.C65_DATASET_SHA256
    assert result["complete_definition_count"] == 97
    assert result["comparison_count"] == 96


def test_protocol_reconstructs_exact_full_and_numeric_orders():
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factors"]
    full = audit.reconstruct_complete_definitions(comparisons)
    assert len(full) == 97
    assert len(comparisons) == 96
    assert audit.STRUCTURALLY_NONNUMERIC_FACTOR in [item["name"] for item in full]
    assert audit.STRUCTURALLY_NONNUMERIC_FACTOR not in [item["name"] for item in comparisons]
    assert comparisons[-3:] == [
        {"name": audit.prior_audit.C62_FACTOR, "score_direction": "higher"},
        {"name": audit.prior_audit.C64_FACTOR, "score_direction": "higher"},
        {"name": audit.C65_FACTOR, "score_direction": "higher"},
    ]


def test_status_is_coverage_comparison_and_return_closed_before_audit():
    payload = audit.status(audit.DEFAULT_EXPERIMENT_ROOT)
    assert payload["audit_count"] == 0
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read"] == []
    assert payload["historical_forward_return_fields_read"] is False
    assert payload["candidate49_historical_return_read"] is False
    assert payload["provider_request_issued"] is False


def test_frozen_candidate_range_registration_is_exact_and_fails_closed():
    engine = SimpleNamespace(FACTOR_RANGES={"prior": (-1.0, 1.0)})
    audit._install_frozen_candidate_range(engine)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (0.0, 1.0)
    conflict = SimpleNamespace(FACTOR_RANGES={audit.FACTOR_NAME: (0.0, 2.0)})
    with pytest.raises(audit.Campaign066NoReturnAuditError):
        audit._install_frozen_candidate_range(conflict)


def test_campaign063_remains_explicit_nonnumeric_challenge():
    spec = audit.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert gate["structurally_nonnumeric_mechanism_challenges"] == [audit.STRUCTURALLY_NONNUMERIC_FACTOR]
    assert gate["numeric_comparator_classification_frozen_before_candidate_definition"] is True
    assert gate["candidate_specific_comparator_drop_allowed"] is False
    assert gate["all_96_numeric_comparators_must_pass"] is True


def test_campaign065_is_last_numeric_comparator_and_has_frozen_verifier():
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factors"]
    assert comparisons[-1] == {"name": audit.C65_FACTOR, "score_direction": "higher"}
    manifest = audit.json.loads(audit.C65_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert manifest["dataset_sha256"] == audit.C65_DATASET_SHA256
