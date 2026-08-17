from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign094_no_return_audit as audit


def test_campaign094_no_return_static_contract() -> None:
    spec = audit.load_protocol()
    comparisons = audit.definitions.reconstruct_comparisons()
    complete = audit.definitions.reconstruct_complete_definitions()
    assert audit.definitions.bindings is not None
    assert spec["candidate"]["name"] == audit.FACTOR_NAME
    assert len(comparisons) == audit.EXPECTED_COMPARISON_COUNT == 123
    assert len(complete) == audit.EXPECTED_COMPLETE_DEFINITION_COUNT == 125
    assert comparisons[-1] == {
        "name": "intraday_close_transition_range_quadratic_efficiency_238p",
        "score_direction": "higher",
    }
    assert complete[-1] == comparisons[-1]


def test_campaign094_candidate_snapshot_binding_verifies() -> None:
    result = audit.verify_candidate_snapshot()
    assert result["status"] == "verified"
    assert result["rows"] == audit.EXPECTED_ROWS
    assert result["eligible_rows"] == audit.EXPECTED_ELIGIBLE_ROWS
    assert result["dataset_sha256"] == audit.SNAPSHOT_DATASET_SHA256
    assert result["comparison_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False
    assert result["provider_request_issued"] is False


def test_campaign094_range_registration_is_exact() -> None:
    class Engine:
        def __init__(self) -> None:
            self.FACTOR_RANGES: dict[str, tuple[float, float]] = {}

    engine = Engine()
    audit._install_frozen_ranges(engine)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (0.0, 0.25)


def test_campaign094_no_return_status_is_read_only() -> None:
    result = audit.status()
    expected = (
        "ready_for_single_audit"
        if audit.AUDIT_ACTIVATION_BINDING.is_file()
        else "activation_binding_absent"
    )
    assert result["status"] == expected
    assert result["candidate_snapshot_exists"] is True
    assert result["coverage_or_capacity_metrics_computed"] is False
    assert result["comparison_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False
    assert result["provider_request_issued"] is False
