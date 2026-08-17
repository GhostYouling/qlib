from __future__ import annotations

import pytest

from scripts import a_share_three_day_walkforward_campaign108_features_v2 as candidate
from scripts import (
    a_share_three_day_walkforward_campaign108_no_return_audit_v2 as audit,
)


def test_audit_is_bound_to_recovered_candidate_and_same_protocol() -> None:
    assert audit.candidate is candidate
    spec = audit.load_protocol()
    assert spec["candidate"]["formula"] == ("-tanh(log(close_15_00 / close_09_31))")
    assert (
        len(
            spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
                "comparison_factors"
            ]
        )
        == 132
    )


def test_recovered_audit_still_requires_coverage_and_confirmation(tmp_path) -> None:
    with pytest.raises(audit.Campaign108NoReturnAuditError, match="before"):
        audit._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": False}
        )
    with pytest.raises(audit.Campaign108NoReturnAuditError, match="confirm-run"):
        audit.run_no_return_audit(
            data_root=audit.DEFAULT_DATA_ROOT,
            experiment_root=tmp_path,
            workers=1,
            confirm_run=False,
        )


def test_recovered_status_is_value_blind() -> None:
    status = audit.status()
    assert status["comparison_values_read_by_status"] is False
    assert (
        status["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert status["provider_request_issued_by_status"] is False
