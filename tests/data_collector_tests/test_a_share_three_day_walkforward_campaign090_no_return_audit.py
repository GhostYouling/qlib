from __future__ import annotations

import numpy as np

from scripts import a_share_three_day_walkforward_campaign090_no_return_audit as audit


def test_campaign090_no_return_protocol_uses_complete_frozen_orders() -> None:
    protocol = audit.load_protocol()
    gate = protocol["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert gate["numeric_comparator_count"] == 119
    assert gate["complete_definition_count"] == 121
    assert len(gate["comparison_factors"]) == 119
    assert gate["comparison_factors"][-1] == {
        "name": "intraday_directional_amount_timing_spread_238m",
        "score_direction": "higher",
    }


def test_campaign090_candidate_snapshot_verifies_without_comparators_or_returns() -> None:
    result = audit.verify_candidate_snapshot()
    assert result == {
        "status": "verified",
        "dataset_sha256": audit.SNAPSHOT_DATASET_SHA256,
        "partitions": 7,
        "rows": 1_331_759,
        "eligible_rows": 1_328_449,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def test_campaign090_candidate_arrays_bind_exact_finite_count() -> None:
    keys, values, years = audit.load_candidate_arrays()
    assert len(keys) == 1_331_759
    assert np.all(keys[1:] > keys[:-1])
    assert int(np.isfinite(values).sum()) == 1_328_449
    assert np.array_equal(np.unique(years), np.arange(2019, 2026))


def test_campaign090_installs_frozen_zero_one_range() -> None:
    class Engine:
        FACTOR_RANGES: dict[str, tuple[float, float]] = {}

    engine = Engine()
    audit._install_frozen_ranges(engine)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (0.0, 1.0)


def test_campaign090_audit_status_is_value_free() -> None:
    payload = audit.status(audit.DEFAULT_EXPERIMENT_ROOT)
    assert payload["audit_count"] == 0
    assert payload["coverage_or_capacity_metrics_computed"] is True
    assert payload["comparison_values_read"] is True
    assert payload["historical_daily_price_or_forward_return_values_read"] is False
    assert payload["provider_request_issued"] is False
