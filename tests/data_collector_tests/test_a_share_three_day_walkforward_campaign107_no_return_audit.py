from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from scripts import a_share_three_day_walkforward_campaign107_no_return_audit as audit


def test_runtime_protocol_has_exact_coverage_and_132_uniqueness_gates() -> None:
    spec = audit.load_protocol()
    coverage = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    uniqueness = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert coverage == {
        "holding_period_sessions": 3,
        "minimum_median_coverage": 0.95,
        "minimum_p05_coverage": 0.90,
        "minimum_p05_eligible_names": 50,
        "minimum_non_overlapping_three_session_cohorts": 200,
        "minimum_observed_calendar_years": 5,
    }
    assert len(uniqueness["comparison_factors"]) == 132
    assert uniqueness["minimum_pairwise_names_per_session"] == 50
    assert uniqueness["minimum_pairwise_sessions_per_comparison"] == 100
    assert uniqueness["maximum_allowed_absolute_median_daily_rank_correlation"] == 0.8
    assert uniqueness["raw_comparator_nan_preserved_until_pairwise_overlap"] is True


def test_adapter_freeze_and_exact_raw_ranges_are_live() -> None:
    freeze = audit._validate_adapter_freeze()
    assert freeze["synthetic_test"]["result"] == "10 passed"
    engine = SimpleNamespace(FACTOR_RANGES={})
    observed = audit._register_raw_ranges(engine)
    assert observed[audit.c103.FACTOR_NAME] == (0.0, 1.0)
    assert observed[audit.c105.FACTOR_NAME] == (0.0, 1.0)
    assert engine.FACTOR_RANGES == observed


def test_raw_comparator_loader_uses_nan_preserving_adapter() -> None:
    source = inspect.getsource(audit._load_comparisons_after_coverage)
    assert "sorted_raw_comparator_arrays" in source
    assert "align_raw_comparator_values" in source
    assert "_sorted_candidate_arrays(frame, c105.FACTOR_NAME)" not in source


def test_comparator_loader_rejects_precoverage_call() -> None:
    with pytest.raises(audit.Campaign107NoReturnAuditError, match="before"):
        audit._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": False},
            candidate_keys=None,
            candidate_values=None,
            gate={},
            comparison_engine=None,
        )


def test_run_requires_explicit_confirmation_before_any_values(tmp_path) -> None:
    with pytest.raises(audit.Campaign107NoReturnAuditError, match="confirm-run"):
        audit.run_no_return_audit(
            data_root=audit.DEFAULT_DATA_ROOT,
            experiment_root=tmp_path,
            workers=1,
            confirm_run=False,
        )


def test_status_is_value_blind() -> None:
    status = audit.status()
    assert status["coverage_or_capacity_metrics_computed_by_status"] is False
    assert status["comparison_values_read_by_status"] is False
    assert (
        status["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert status["provider_request_issued_by_status"] is False
