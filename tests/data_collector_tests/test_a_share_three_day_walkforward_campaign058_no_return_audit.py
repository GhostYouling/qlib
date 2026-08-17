from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign058_no_return_audit as audit


def test_static_bindings_reconstruct_exact_89_factor_order() -> None:
    result = audit.verify_static_bindings()
    assert result["comparison_count"] == 89
    assert result["comparison_order_sha256"] == audit.EXPECTED_COMPARISON_ORDER_SHA256
    assert result["quality_comparison_factors"] == list(audit.QUALITY_COMPARISON_FACTORS)


def test_quality_semantics_use_average_tie_daily_ranks_and_frozen_composites() -> None:
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-05-06"] * 3 + ["2024-05-07"] * 2),
            "roe": [10.0, 20.0, 20.0, 5.0, 15.0],
            "revenue_yoy": [5.0, 15.0, 25.0, 30.0, 10.0],
            "profit_yoy": [30.0, 20.0, 10.0, 12.0, 24.0],
            "roe_change": [1.0, np.nan, 3.0, 2.0, 4.0],
            "revenue_yoy_acceleration": [2.0, 4.0, 6.0, 1.0, 3.0],
            "profit_yoy_acceleration": [9.0, 7.0, 5.0, np.nan, 8.0],
            "quality_eligible": True,
        }
    )
    result = audit.materialize_quality_comparison_frame(frame)
    assert result.loc[:2, "quality_roe"].tolist() == pytest.approx(
        [1 / 3, 5 / 6, 5 / 6]
    )
    assert result.loc[0, "quality_profit"] == pytest.approx(1.0)
    assert result.loc[0, "quality_revenue"] == pytest.approx(1 / 3)
    assert result.loc[0, "quality_growth"] == pytest.approx(2 / 3)
    assert result.loc[0, "quality_score"] == pytest.approx(5 / 9)
    assert pd.isna(result.loc[1, "roe_change"])
    assert result.loc[4, "quality_roe"] == pytest.approx(1.0)


def test_quality_semantics_reject_mask_drift() -> None:
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2024-05-06"]),
            "roe": [10.0],
            "revenue_yoy": [5.0],
            "profit_yoy": [7.0],
            "roe_change": [1.0],
            "revenue_yoy_acceleration": [2.0],
            "profit_yoy_acceleration": [3.0],
            "quality_eligible": [False],
        }
    )
    with pytest.raises(audit.Campaign058NoReturnAuditError, match="mask diverged"):
        audit.materialize_quality_comparison_frame(frame)


def test_generated_runner_is_bound_to_campaign058_overrides() -> None:
    globals_ = audit._base_run_no_return_audit.__globals__
    assert globals_["candidate"].FACTOR_NAME == audit.FACTOR_NAME
    assert globals_["EXPECTED_COMPARISON_COUNT"] == 89
    assert globals_["_load_bound_prior_snapshots"] is audit._load_bound_prior_snapshots
    assert globals_["_append_all_prior_comparisons"] is audit._append_all_prior_comparisons
    assert globals_["verify_static_bindings"] is audit.verify_static_bindings


def test_status_reads_no_candidate_comparison_daily_or_return_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        pd,
        "read_parquet",
        lambda *args, **kwargs: pytest.fail("status must not read parquet values"),
    )
    result = audit.status()
    assert result["comparison_count"] == 89
    assert result["daily_price_fields_read_by_status"] is False
    assert result["forward_return_fields_read_by_status"] is False
    assert result["provider_request_issued_by_status"] is False
