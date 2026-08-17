import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign132_audit as audit


def _sessions(values: list[tuple[int, int]]) -> pd.DataFrame:
    days = pd.date_range("2019-01-02", periods=len(values), freq="365D")
    return pd.DataFrame(
        {
            "session": (days - pd.Timestamp("1970-01-01")).days,
            "quality_listing_names": [value[0] for value in values],
            "eligible_names": [value[1] for value in values],
        }
    )


def test_coverage_summary_passes_frozen_thresholds() -> None:
    frame = _sessions([(100, 100)] * 6)
    thresholds = {
        "minimum_median_coverage": 0.95,
        "minimum_p05_coverage": 0.90,
        "minimum_p05_eligible_names": 50.0,
        "minimum_potential_non_overlapping_three_session_cohorts": 1,
        "minimum_observed_cohort_years": 1,
    }
    result = audit.coverage_summary(
        frame,
        expected_rows=600,
        expected_sessions=6,
        thresholds=thresholds,
    )
    assert result["median_coverage"] == 1.0
    assert result["p05_coverage"] == 1.0
    assert result["gate_passed_before_model_fit_or_returns"] is True


def test_coverage_summary_fails_low_p05_coverage() -> None:
    frame = _sessions([(100, 100)] * 19 + [(100, 0)])
    thresholds = {
        "minimum_median_coverage": 0.95,
        "minimum_p05_coverage": 0.96,
        "minimum_p05_eligible_names": 0.0,
        "minimum_potential_non_overlapping_three_session_cohorts": 1,
        "minimum_observed_cohort_years": 1,
    }
    result = audit.coverage_summary(
        frame,
        expected_rows=2_000,
        expected_sessions=20,
        thresholds=thresholds,
    )
    assert result["median_coverage"] == 1.0
    assert result["p05_coverage"] < 0.96
    assert result["gate_passed_before_model_fit_or_returns"] is False


def test_coverage_summary_rejects_row_identity_change() -> None:
    frame = _sessions([(100, 100)] * 6)
    with pytest.raises(audit.Campaign132AuditError, match="identity changed"):
        audit.coverage_summary(
            frame,
            expected_rows=599,
            expected_sessions=6,
            thresholds=audit.THRESHOLDS,
        )
