from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts import a_share_three_day_walkforward_campaign064_no_return_audit as audit


def test_static_snapshot_bindings_are_frozen() -> None:
    result = audit.verify_static_bindings()
    assert result["candidate_manifest_sha256"] == audit.SNAPSHOT_MANIFEST_SHA256
    assert result["candidate_dataset_sha256"] == audit.SNAPSHOT_DATASET_SHA256
    assert result["campaign062_manifest_sha256"] == audit.C62_SNAPSHOT_SHA256
    assert result["campaign063_manifest_sha256"] == audit.C63_SNAPSHOT_SHA256
    assert result["comparison_count"] == 95


def test_protocol_reconstructs_exact_95_factor_order() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(comparisons) == 95
    assert comparisons[-2:] == [
        {"name": audit.C62_FACTOR, "score_direction": "higher"},
        {"name": audit.C63_FACTOR, "score_direction": "higher"},
    ]


def test_status_is_return_closed_before_audit() -> None:
    payload = audit.status(audit.DEFAULT_EXPERIMENT_ROOT)
    assert payload["audit_count"] == 0
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read"] == []
    assert payload["historical_forward_return_fields_read"] is False
    assert payload["candidate49_historical_return_read"] is False
    assert payload["provider_request_issued"] is False


def test_frozen_candidate_range_registration_preserves_and_fails_closed() -> None:
    engine = SimpleNamespace(FACTOR_RANGES={"prior_factor": (-1.0, 1.0)})
    audit._install_frozen_candidate_range(engine)
    assert engine.FACTOR_RANGES == {
        "prior_factor": (-1.0, 1.0),
        audit.FACTOR_NAME: (0.0, 1.0),
    }

    conflict = SimpleNamespace(FACTOR_RANGES={audit.FACTOR_NAME: (0.0, 2.0)})
    with pytest.raises(audit.Campaign064NoReturnAuditError):
        audit._install_frozen_candidate_range(conflict)


def test_c62_verifier_output_columns_are_restored_from_stale_state() -> None:
    audit.c62_features.base._engine_globals["OUTPUT_COLUMNS"] = ("stale",)
    audit._install_c62_verifier_globals()
    assert tuple(
        audit.c62_features.base._engine_globals["OUTPUT_COLUMNS"]
    ) == tuple(audit.c62_features.OUTPUT_COLUMNS)
