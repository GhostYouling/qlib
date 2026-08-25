from __future__ import annotations

import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign286_design_recovery_v3 as v3


def test_defined_domain_excludes_and_records_zero_denominators() -> None:
    sessions = pd.bdate_range("2019-01-01", "2023-12-31")
    quality = pd.Series(100, index=sessions)
    quality.iloc[:67] = 0
    eligible = quality.copy()
    daily = pd.DataFrame(
        {
            "session": sessions,
            "quality_listing_names": quality.to_numpy(),
            "eligible_names": eligible.to_numpy(),
        }
    )

    result = v3.coverage_summary_defined_domain(daily)

    assert result["zero_denominator_sessions_excluded_from_defined_domain"] == 67
    assert result["defined_denominator_sessions"] == len(sessions) - 67
    assert result["median_daily_feature_row_coverage"] == pytest.approx(1.0)
    assert result["p05_daily_feature_row_coverage"] == pytest.approx(1.0)
    assert result["gate_passed_before_historical_label_or_forward_return_read"]
    assert not result["threshold_change"]


def test_defined_domain_keeps_frozen_capacity_gate() -> None:
    sessions = pd.bdate_range("2019-01-01", "2023-12-31")
    daily = pd.DataFrame(
        {
            "session": sessions,
            "quality_listing_names": 100,
            "eligible_names": 49,
        }
    )

    result = v3.coverage_summary_defined_domain(daily)

    assert result["eligible_names_p05"] == pytest.approx(49.0)
    assert not result["gate_passed_before_historical_label_or_forward_return_read"]


def test_defined_domain_fails_closed_when_all_denominators_are_zero() -> None:
    daily = pd.DataFrame(
        {
            "session": [pd.Timestamp("2019-01-02")],
            "quality_listing_names": [0],
            "eligible_names": [0],
        }
    )

    with pytest.raises(v3.Campaign286RecoveryV3Error):
        v3.coverage_summary_defined_domain(daily)


def test_frozen_partition_receipts_cover_all_development_years() -> None:
    assert list(v3.PARTITIONS) == [2019, 2020, 2021, 2022, 2023]
    assert sum(item["rows"] for item in v3.PARTITIONS.values()) == 4_918_999
