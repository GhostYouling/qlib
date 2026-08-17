from __future__ import annotations

import copy

import numpy as np

from scripts import a_share_three_day_walkforward_campaign085_no_return_audit as audit


def _key(session: int, symbol_id: int) -> int:
    return session * 4_000_000 + symbol_id


def test_protocol_and_orders_are_frozen_before_coverage() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(comparisons) == 114
    assert comparisons[-1] == {
        "name": audit.candidate.c84.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert (
        audit.candidate._comparison_order_digest(comparisons)
        == audit.candidate.COMPARISON_ORDER_SHA256
    )


def test_coverage_uses_all_frozen_keys_and_common_finite_values() -> None:
    spec = copy.deepcopy(audit.load_protocol())
    gate = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    gate["minimum_non_overlapping_three_session_cohorts"] = 5
    gate["minimum_p05_eligible_names"] = 2
    sessions = list(range(18_001, 18_016))
    years = np.repeat(np.arange(2019, 2024), 3)
    keys = np.array(
        [_key(session, symbol) for session in sessions for symbol in (1, 2)],
        dtype=np.int64,
    )
    values = np.linspace(0.1, 1.0, len(keys), dtype=np.float64)
    row_years = np.repeat(years, 2)
    result, finite_keys, finite_values = audit.coverage_and_capacity(
        keys, values, row_years, spec
    )
    assert result["calendar_sessions"] == 15
    assert result["quality_listing_eligible_rows"] == 30
    assert result["candidate_eligible_rows"] == 30
    assert result["median_coverage"] == 1.0
    assert result["p05_coverage"] == 1.0
    assert result["eligible_names_p05"] == 2.0
    assert result["potential_non_overlapping_three_session_cohorts"] == 5
    assert result["observed_cohort_years"] == [2019, 2020, 2021, 2022, 2023]
    assert result["gate_passed_before_comparison_values"] is True
    assert np.array_equal(finite_keys, keys)
    assert np.array_equal(finite_values, values)


def test_coverage_fails_closed_when_one_session_is_nonfinite() -> None:
    spec = copy.deepcopy(audit.load_protocol())
    gate = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    gate["minimum_non_overlapping_three_session_cohorts"] = 0
    gate["minimum_observed_calendar_years"] = 1
    gate["minimum_p05_eligible_names"] = 1
    keys = np.array([_key(19_360, 1), _key(19_360, 2)], dtype=np.int64)
    years = np.array([2023, 2023], dtype=np.int64)
    values = np.array([np.nan, np.nan], dtype=np.float64)
    result, finite_keys, finite_values = audit.coverage_and_capacity(
        keys, values, years, spec
    )
    assert result["median_coverage"] == 0.0
    assert result["p05_coverage"] == 0.0
    assert result["gate_passed_before_comparison_values"] is False
    assert len(finite_keys) == 0
    assert len(finite_values) == 0


def test_status_is_truthful_before_the_single_audit() -> None:
    result = audit.status()
    assert result["candidate_snapshot_exists"] is True
    assert result["audit_count"] == 0
    assert result["coverage_or_capacity_metrics_computed"] is False
    assert result["comparison_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False
    assert result["provider_request_issued"] is False


def test_v3_uses_the_frozen_current_runtime_adapter_and_restores_constants() -> None:
    audit.c77_v2.load_repair_protocol()
    audit.c77_v2._load_implementation_freeze()
    module = audit.c77_v2._legacy_verifier_module()
    assert module.PANDAS_VERSION == audit.c77_v2.LEGACY_PANDAS_VERSION
    assert module.PYARROW_VERSION == audit.c77_v2.LEGACY_PYARROW_VERSION
    with audit.c77_v2._temporary_runtime_version_binding():
        assert module.PANDAS_VERSION == audit.c77_v2.CURRENT_PANDAS_VERSION
        assert module.PYARROW_VERSION == audit.c77_v2.CURRENT_PYARROW_VERSION
    assert module.PANDAS_VERSION == audit.c77_v2.LEGACY_PANDAS_VERSION
    assert module.PYARROW_VERSION == audit.c77_v2.LEGACY_PYARROW_VERSION


def test_v4_uses_the_frozen_campaign083_verifier_adapter_and_restores_it() -> None:
    audit.c83_v3.load_repair_protocol()
    audit.c83_v3._load_implementation_freeze()
    original = audit.c83_v3.v1.candidate.verify_snapshot_files
    with audit.c83_v3._temporary_candidate_verifier_binding():
        assert (
            audit.c83_v3.v1.candidate.verify_snapshot_files
            is audit.c83_v3.verify_candidate_snapshot_compatible
        )
    assert audit.c83_v3.v1.candidate.verify_snapshot_files is original
