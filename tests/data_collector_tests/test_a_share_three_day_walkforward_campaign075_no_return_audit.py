import numpy as np

from scripts import a_share_three_day_walkforward_campaign075_no_return_audit as audit


class _Engine:
    FACTOR_RANGES = {}


def test_protocol_reconstructs_complete_frozen_orders() -> None:
    spec = audit.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert len(gate["comparison_factors"]) == 105
    assert gate["comparison_factors"][-1] == {
        "name": audit.candidate.C74_FACTOR,
        "score_direction": "higher",
    }
    complete = audit.candidate.reconstruct_complete_definitions()
    assert len(complete) == 106
    assert audit.STRUCTURALLY_NONNUMERIC_FACTOR in [item["name"] for item in complete]
    assert audit.STRUCTURALLY_NONNUMERIC_FACTOR not in [
        item["name"] for item in gate["comparison_factors"]
    ]


def test_frozen_candidate_range_is_negative_integer_domain() -> None:
    engine = _Engine()
    audit._install_frozen_ranges(engine)
    lower, upper = engine.FACTOR_RANGES[audit.FACTOR_NAME]
    assert np.isfinite(lower)
    assert upper == -20.0
    assert lower < upper
    assert engine.FACTOR_RANGES[audit.candidate.C74_FACTOR] == (0.0, 1.0)


def test_status_never_claims_coverage_or_comparison_reads() -> None:
    payload = audit.status()
    assert payload["candidate_snapshot_exists"] is True
    assert payload["audit_count"] == 0
    assert payload["coverage_or_capacity_metrics_computed_by_status"] is False
    assert payload["comparison_values_read_by_status"] is False
    assert payload["historical_daily_price_fields_read"] == []
    assert payload["historical_forward_return_fields_read"] is False
    assert payload["provider_request_issued"] is False


def test_snapshot_constants_match_verified_binding() -> None:
    assert audit.SNAPSHOT_MANIFEST_SHA256 == (
        "d621c73d8f32fa0187c0b8f834a170548eeb8deb04e1fade7a12da08f160aef4"
    )
    assert audit.SNAPSHOT_DATASET_SHA256 == (
        "63b3bd548fa3f2d7f88e19542eb6be5e4ee7cc6f9d83f5dc874868efade98936"
    )
    assert audit.EXPECTED_ELIGIBLE_ROWS == 7_689_881
    assert audit.EXPECTED_COMPARISON_COUNT == 105
