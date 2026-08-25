from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign286_design as design


def test_complete_alpha158_library_is_frozen() -> None:
    expressions, names = design.feature_config()

    assert len(expressions) == len(names) == 158
    assert names[0] == "KMID"
    assert names[-1] == "VSUMD60"


def test_support_state_uses_frozen_119_of_158_threshold() -> None:
    matrix = np.full((3, design.FEATURE_COUNT), np.nan, dtype=np.float32)
    matrix[0, :118] = 1.0
    matrix[1, :119] = 1.0
    matrix[2, :] = 1.0
    matrix[2, 0] = np.inf

    counts, eligible = design.support_state(matrix)

    assert counts.tolist() == [118, 119, 157]
    assert eligible.tolist() == [False, True, True]


def test_compact_stock_day_keys_preserves_exchange_identity() -> None:
    keys = design.compact_stock_day_keys(
        pd.Series(["2020-01-02", "2020-01-02", "2020-01-02"]),
        pd.Series(["SH600000", "SZ000001", "BJ430001"]),
    )

    assert len(set(keys.tolist())) == 3
    assert (keys % 4_000_000).tolist() == [1_600_000, 2_000_001, 3_430_001]


def test_coverage_summary_passes_only_complete_five_year_capacity() -> None:
    sessions = pd.bdate_range("2019-01-01", "2023-12-31")
    daily = pd.DataFrame(
        {
            "session": sessions,
            "quality_listing_names": 100,
            "eligible_names": 98,
        }
    )

    result = design.coverage_summary(daily)

    assert result["gate_passed_before_historical_label_or_forward_return_read"]
    assert result["observed_cohort_years"] == [2019, 2020, 2021, 2022, 2023]
    assert result["median_daily_feature_row_coverage"] == pytest.approx(0.98)


def test_coverage_summary_rejects_low_feature_support() -> None:
    sessions = pd.bdate_range("2019-01-01", "2023-12-31")
    daily = pd.DataFrame(
        {
            "session": sessions,
            "quality_listing_names": 100,
            "eligible_names": 89,
        }
    )

    result = design.coverage_summary(daily)

    assert not result["gate_passed_before_historical_label_or_forward_return_read"]


def test_coverage_summary_fails_closed_on_zero_denominator() -> None:
    daily = pd.DataFrame(
        {
            "session": [pd.Timestamp("2019-01-02")],
            "quality_listing_names": [0],
            "eligible_names": [0],
        }
    )

    with pytest.raises(design.Campaign286DesignError):
        design.coverage_summary(daily)
