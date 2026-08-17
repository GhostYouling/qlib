from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from scripts import (
    a_share_three_day_walkforward_campaign097_no_return_audit_v4 as audit,
)


def test_v3_and_failure_record_are_immutable() -> None:
    assert audit._sha256(Path(audit.v3.__file__).resolve()) == audit.V3_RUNNER_SHA256
    assert (
        audit._sha256(audit.v3.AUDIT_IMPLEMENTATION_FREEZE)
        == audit.V3_IMPLEMENTATION_FREEZE_SHA256
    )
    assert (
        audit._sha256(audit.v3.AUDIT_ACTIVATION_BINDING) == audit.V3_ACTIVATION_SHA256
    )
    assert audit._sha256(audit.FAILURE_RECORD) == audit.FAILURE_RECORD_SHA256


def test_alignment_retains_complete_denominator_and_unmatched_nan() -> None:
    keys, values, years = audit.align_candidate_year(
        eligible_keys=np.array([10, 20, 40], dtype=np.int64),
        candidate_keys=np.array([40, 30, 10], dtype=np.int64),
        candidate_values=np.array([0.4, 0.3, 0.1]),
        year=2019,
    )
    assert np.array_equal(keys, np.array([10, 20, 40], dtype=np.int64))
    assert np.allclose(values[[0, 2]], [0.1, 0.4])
    assert np.isnan(values[1])
    assert np.array_equal(years, np.full(3, 2019, dtype=np.int64))


def test_alignment_fails_closed_on_duplicate_candidate_key() -> None:
    with pytest.raises(audit.Campaign097NoReturnAuditV4Error, match="inputs"):
        audit.align_candidate_year(
            eligible_keys=np.array([10, 20], dtype=np.int64),
            candidate_keys=np.array([10, 10], dtype=np.int64),
            candidate_values=np.array([0.1, 0.2]),
            year=2019,
        )


def test_alignment_fails_closed_on_range_violation() -> None:
    with pytest.raises(audit.Campaign097NoReturnAuditV4Error, match="range"):
        audit.align_candidate_year(
            eligible_keys=np.array([10], dtype=np.int64),
            candidate_keys=np.array([10], dtype=np.int64),
            candidate_values=np.array([1.01]),
            year=2019,
        )


def test_status_does_not_read_values() -> None:
    result = audit.status()
    assert result["coverage_or_capacity_metrics_computed_by_status"] is False
    assert result["comparison_values_read_by_status"] is False
    assert (
        result["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert result["repair_scope"] == "total_denominator_left_alignment_only"
