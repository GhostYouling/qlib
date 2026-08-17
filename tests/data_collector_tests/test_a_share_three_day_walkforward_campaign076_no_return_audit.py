from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign076_no_return_audit as audit


def test_protocol_binds_exact_107_and_106_orders_without_values() -> None:
    spec = audit.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert len(gate["comparison_factors"]) == 106
    assert gate["comparison_factors"][-1] == {
        "name": "accepted_instrument_session_youth_20s",
        "score_direction": "higher",
    }
    assert gate["all_106_numeric_comparators_must_pass"] is True


def test_structurally_nonnumeric_definition_is_not_numeric_comparator() -> None:
    complete = audit.candidate.reconstruct_complete_definitions()
    numeric = audit.candidate.reconstruct_comparisons()
    assert audit.STRUCTURALLY_NONNUMERIC_FACTOR in [x["name"] for x in complete]
    assert audit.STRUCTURALLY_NONNUMERIC_FACTOR not in [x["name"] for x in numeric]


def test_frozen_range_install_adds_campaign076_without_changing_prior() -> None:
    class Engine:
        FACTOR_RANGES = {}

    engine = Engine()
    audit._install_frozen_ranges(engine)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (0.0, 1.0)
    assert engine.FACTOR_RANGES[audit.candidate.C75_FACTOR][1] == -20.0


def test_status_does_not_compute_gates_or_read_values() -> None:
    result = audit.status()
    assert result["audit_count"] == 0
    assert result["coverage_or_capacity_metrics_computed_by_status"] is False
    assert result["comparison_values_read_by_status"] is False
    assert result["historical_forward_return_fields_read"] is False
    assert result["provider_request_issued"] is False


def test_candidate_and_previous_snapshot_bindings_are_exact() -> None:
    assert audit.SNAPSHOT_MANIFEST_SHA256 == "dc23177c4125142fb2287fb3e19a4be8a3cd53b70abd3be91718979aaf200f32"
    assert audit.SNAPSHOT_DATASET_SHA256 == "aef7cfb7cbc3ccaabe5552a4ed4f81ea8582d5f739153dd405b70e2a73b3a952"
    assert audit.candidate.C75_MANIFEST_SHA256 == "d621c73d8f32fa0187c0b8f834a170548eeb8deb04e1fade7a12da08f160aef4"
    assert audit.EXPECTED_ELIGIBLE_ROWS == audit.EXPECTED_ROWS
