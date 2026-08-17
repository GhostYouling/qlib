from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from scripts import (
    a_share_three_day_walkforward_campaign145_no_return_audit_recovery as audit,
)


def test_campaign145_coverage_recovery_receipt_is_bound() -> None:
    receipt = audit.validate_recovery_receipt()
    assert receipt["snapshot_manifest"]["eligible_rows"] == 3_954_911
    assert receipt["known_header_correction"]["effective_verified_range"] == {
        audit.recovery.c145.FACTOR_NAME: [-1.0, 1.0]
    }


def test_campaign145_coverage_gate_is_unchanged() -> None:
    gate = audit.frozen_audit.expected_gate()
    assert gate["minimum_median_daily_coverage"] == 0.95
    assert gate["minimum_p05_daily_coverage"] == 0.90
    assert gate["minimum_p05_eligible_names"] == 50
    assert gate["minimum_non_overlapping_three_signal_session_cohorts"] == 200


def test_campaign145_coverage_semantics_accept_negative_candidate() -> None:
    factor = audit.recovery.c145.FACTOR_NAME
    candidate = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2023-01-03", "2023-01-03"]),
            "symbol": ["SZ000001", "SH600000"],
            factor: [-0.1, 0.2],
            f"{factor}_eligible": [True, True],
        }
    )
    eligible = candidate[["trade_date", "symbol"]].copy()
    result = audit.frozen_audit.coverage_and_variation(candidate, eligible)
    assert result["candidate_eligible_rows"] == 2
    assert result["median_daily_coverage"] == 1.0


def test_campaign145_coverage_activation_rejects_incomplete_record() -> None:
    with pytest.raises(audit.Campaign145CoverageRecoveryError):
        audit.validate_activation_record({})


def test_campaign145_coverage_runner_does_not_call_defective_verifier() -> None:
    source = Path(audit.__file__).read_text(encoding="utf-8")
    run_body = source.split("def run_coverage_audit", maxsplit=1)[1]
    assert "verify_snapshot_files" not in run_body
    assert "verify_current_partition_bytes" in run_body
