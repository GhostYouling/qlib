from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign106_no_return_audit as audit


def test_runtime_protocol_preserves_coverage_first_exact_132_order() -> None:
    spec = audit.load_protocol()
    coverage = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    uniqueness = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert coverage == {
        "holding_period_sessions": 3,
        "minimum_median_coverage": 0.95,
        "minimum_p05_coverage": 0.9,
        "minimum_p05_eligible_names": 50,
        "minimum_non_overlapping_three_session_cohorts": 200,
        "minimum_observed_calendar_years": 5,
    }
    assert len(uniqueness["comparison_factors"]) == 132
    assert uniqueness["comparison_factors"][-1]["name"] == audit.c105.FACTOR_NAME
    assert uniqueness["maximum_allowed_absolute_median_daily_rank_correlation"] == 0.8


def test_comparator_loader_cannot_run_before_coverage_pass() -> None:
    with pytest.raises(audit.Campaign106NoReturnAuditError, match="before"):
        audit._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": False},
            candidate_keys=np.array([1], dtype=np.int64),
            candidate_values=np.array([0.5]),
            gate={},
            comparison_engine=SimpleNamespace(),
        )


def test_directional_matrix_is_not_inverted_twice() -> None:
    observed: dict[str, object] = {}

    class Engine:
        @staticmethod
        def _aligned_comparison_result(**kwargs: object) -> dict[str, object]:
            observed.update(kwargs)
            return {
                "comparison_factor": kwargs["comparison"],
                "score_direction": kwargs["direction"],
                "gate_passed": True,
            }

    result = audit._directionally_normalized_result(
        comparison_engine=Engine(),
        candidate_keys=np.array([1, 2], dtype=np.int64),
        candidate_values=np.array([0.0, 1.0]),
        values=np.array([0.25, 0.75]),
        definition={"name": "lower_raw_factor", "score_direction": "lower"},
        gate={},
    )
    assert observed["direction"] == "higher"
    assert result["source_score_direction"] == "lower"
    assert result["score_direction"] == "higher_after_frozen_direction_normalization"


def test_campaign105_value_alignment_is_exact_and_missing_safe() -> None:
    aligned = audit._align_factor_values(
        source_keys=np.array([10, 11, 12, 13], dtype=np.int64),
        source_values=np.array([0.1, np.nan, 0.3, 0.4]),
        target_keys=np.array([10, 12], dtype=np.int64),
    )
    np.testing.assert_allclose(aligned, [0.1, 0.3])
    with pytest.raises(audit.Campaign106NoReturnAuditError, match="cover"):
        audit._align_factor_values(
            source_keys=np.array([10, 12], dtype=np.int64),
            source_values=np.array([0.1, 0.3]),
            target_keys=np.array([10, 11], dtype=np.int64),
        )


def test_status_is_value_blind_and_audit_requires_confirmation(tmp_path) -> None:
    status = audit.status(tmp_path)
    assert status["audit_count"] == 0
    assert status["coverage_or_capacity_metrics_computed_by_status"] is False
    assert status["comparison_values_read_by_status"] is False
    assert status["historical_daily_price_or_forward_return_values_read_by_status"] is False
    assert status["provider_request_issued_by_status"] is False
    with pytest.raises(audit.Campaign106NoReturnAuditError, match="confirm-run"):
        audit.run_no_return_audit(
            data_root=audit.DEFAULT_DATA_ROOT,
            experiment_root=tmp_path,
            workers=1,
            confirm_run=False,
        )


def test_shared_implementation_freeze_is_live() -> None:
    freeze = audit.candidate._validate_implementation_freeze()
    assert freeze["numeric_comparator_count"] == 132

