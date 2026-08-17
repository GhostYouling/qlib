from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign136_coverage_audit as audit
from scripts import a_share_three_day_walkforward_campaign136_formula as formula


def _keys() -> pd.DataFrame:
    dates = pd.DatetimeIndex(
        np.concatenate(
            [
                pd.date_range(f"{year}-01-02", periods=123, freq="B").to_numpy()
                for year in range(2019, 2024)
            ]
        )
    )
    symbols = [f"SH60{index:04d}" for index in range(60)]
    return pd.MultiIndex.from_product(
        [dates, symbols], names=["trade_date", "symbol"]
    ).to_frame(index=False)


def _candidate(keys: pd.DataFrame) -> pd.DataFrame:
    frame = keys.copy()
    symbol_number = frame["symbol"].str[-4:].astype(int).to_numpy()
    date_number = frame.groupby("trade_date", sort=True).ngroup().to_numpy()
    frame[formula.FACTOR_NAME] = (symbol_number + date_number % 7) / 100.0
    frame[f"{formula.FACTOR_NAME}_eligible"] = True
    return frame


def test_expected_gate_matches_frozen_protocol() -> None:
    gate = audit.expected_gate()
    assert gate["minimum_median_daily_coverage"] == 0.95
    assert gate["minimum_p05_daily_coverage"] == 0.90
    assert gate["minimum_non_overlapping_three_signal_session_cohorts"] == 200
    assert gate["candidate_value_range"] == "finite [0,+infinity)"
    spec = audit.load_protocol()
    assert spec["comparison_contract"]["numeric_comparator_count"] == 140


def test_complete_five_year_panel_passes_coverage_variation_and_capacity() -> None:
    keys = _keys()
    result = audit.coverage_and_variation(_candidate(keys), keys)
    assert result["median_daily_coverage"] == 1.0
    assert result["p05_daily_coverage"] == 1.0
    assert result["eligible_names_p05"] == 60.0
    assert result["potential_non_overlapping_three_signal_session_cohorts"] >= 200
    assert result["observed_cohort_years"] == [2019, 2020, 2021, 2022, 2023]
    assert result["nonconstant_cross_sectional_sessions"] == 615
    assert result["gate_passed_before_comparator_values"] is True


def test_sparse_candidate_is_not_rescued_by_missing_rows() -> None:
    keys = _keys()
    candidate = _candidate(keys)
    declared = np.arange(len(candidate)) % 20 == 0
    candidate[f"{formula.FACTOR_NAME}_eligible"] = declared
    candidate.loc[~declared, formula.FACTOR_NAME] = np.nan
    result = audit.coverage_and_variation(candidate, keys)
    assert result["p05_daily_coverage"] < 0.90
    assert result["eligible_names_p05"] < 50
    assert result["gate_passed_before_comparator_values"] is False


def test_nonnegative_unbounded_value_is_allowed_but_negative_is_rejected() -> None:
    keys = pd.DataFrame(
        {"trade_date": pd.to_datetime(["2019-01-02"]), "symbol": ["SH600000"]}
    )
    candidate = keys.copy()
    candidate[formula.FACTOR_NAME] = [2.0]
    candidate[f"{formula.FACTOR_NAME}_eligible"] = [True]
    result = audit.coverage_and_variation(candidate, keys)
    assert result["candidate_eligible_rows"] == 1
    candidate[formula.FACTOR_NAME] = [-0.01]
    with pytest.raises(audit.Campaign136CoverageAuditError, match="values"):
        audit.coverage_and_variation(candidate, keys)


def test_ineligible_nonmissing_and_declared_missing_values_fail_closed() -> None:
    keys = pd.DataFrame(
        {"trade_date": pd.to_datetime(["2019-01-02"]), "symbol": ["SH600000"]}
    )
    candidate = keys.copy()
    candidate[formula.FACTOR_NAME] = [0.0]
    candidate[f"{formula.FACTOR_NAME}_eligible"] = [False]
    with pytest.raises(audit.Campaign136CoverageAuditError, match="values"):
        audit.coverage_and_variation(candidate, keys)
    candidate[formula.FACTOR_NAME] = [np.nan]
    candidate[f"{formula.FACTOR_NAME}_eligible"] = [True]
    with pytest.raises(audit.Campaign136CoverageAuditError, match="values"):
        audit.coverage_and_variation(candidate, keys)


def test_source_publication_and_coverage_freeze_are_live() -> None:
    publication = audit.validate_source_publication()
    freeze = audit.validate_coverage_freeze()
    assert publication["confirmed_run"]["dataset_sha256"] == (
        audit.SNAPSHOT_DATASET_SHA256
    )
    assert freeze["frozen_implementation"]["runner_sha256"] == (
        audit.file_sha256(Path(audit.__file__).resolve())
    )
