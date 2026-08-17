from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign128_coverage_audit as audit


def test_campaign128_source_publication_is_exact_and_no_return() -> None:
    record = audit.load_source_publication()
    assert record["build"]["eligible_rows"] == audit.SNAPSHOT_ELIGIBLE_ROWS
    assert record["read_only_recovery_verification"]["status"] == "verified"
    assert record["research_boundary"]["comparison_values_read"] is False
    assert (
        record["research_boundary"][
            "historical_daily_price_or_forward_return_values_read"
        ]
        is False
    )


def test_campaign128_source_publication_mutation_fails_closed() -> None:
    record = copy.deepcopy(audit.load_source_publication())
    record["build"]["eligible_rows"] -= 1
    with pytest.raises(audit.Campaign128CoverageAuditError):
        audit.validate_source_publication(record)


def test_campaign128_coverage_accepts_negative_frozen_range() -> None:
    dates = pd.date_range("2019-01-02", periods=1500, freq="B")
    keys = pd.DataFrame(
        {
            "trade_date": np.repeat(dates, 60),
            "symbol": [f"SH{index:06d}" for _ in dates for index in range(60)],
        }
    )
    values = np.tile(np.linspace(-0.9, 0.9, 60), len(dates))
    frame = keys.copy()
    frame[audit.FACTOR_NAME] = values
    frame[f"{audit.FACTOR_NAME}_eligible"] = True
    result = audit.coverage_and_variation(frame, keys)
    assert result["gate_passed_before_comparator_values"] is True
    assert result["median_daily_coverage"] == 1.0
    assert result["nonconstant_cross_sectional_sessions"] == 1500


def test_campaign128_coverage_rejects_out_of_range_or_rescued_missing() -> None:
    keys = pd.DataFrame({"trade_date": ["2025-01-02"], "symbol": ["SH600000"]})
    frame = keys.copy()
    frame[audit.FACTOR_NAME] = [1.1]
    frame[f"{audit.FACTOR_NAME}_eligible"] = [True]
    with pytest.raises(audit.Campaign128CoverageAuditError):
        audit.coverage_and_variation(frame, keys)
    frame[audit.FACTOR_NAME] = [0.0]
    frame[f"{audit.FACTOR_NAME}_eligible"] = [False]
    with pytest.raises(audit.Campaign128CoverageAuditError):
        audit.coverage_and_variation(frame, keys)


def test_campaign128_coverage_gate_and_output_are_frozen() -> None:
    gate = audit.expected_gate()
    assert gate["minimum_median_daily_coverage"] == 0.95
    assert gate["minimum_p05_daily_coverage"] == 0.90
    assert gate["minimum_nonconstant_cross_sectional_sessions"] == 200
    assert audit.OUTPUT_PATH.exists() is False
