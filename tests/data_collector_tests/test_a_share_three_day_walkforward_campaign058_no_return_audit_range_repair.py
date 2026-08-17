from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign058_no_return_audit_range_repair as repair


def _frame(values: list[float], eligible: list[bool]) -> pd.DataFrame:
    factor = repair.audit.FACTOR_NAME
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-05-06", "2024-05-06"]),
            "symbol": ["sh600000", "sz000001"],
            factor: values,
            f"{factor}_eligible": eligible,
        }
    )


def test_repair_bindings_are_frozen_without_value_load() -> None:
    result = repair.verify_repair_bindings()
    assert result["failure_record_sha256"] == repair.FAILURE_RECORD_SHA256


def test_finite_float_values_pass_without_clipping_or_transform() -> None:
    frame = _frame([np.finfo(np.float64).max, np.nan], [True, False])
    result = repair.validate_candidate_frame(
        frame, expected_rows=2, expected_eligible_rows=1
    )
    assert result.loc[0, repair.audit.FACTOR_NAME] == np.finfo(np.float64).max
    assert str(result["symbol"].dtype) == "category"


def test_nonfinite_eligible_value_fails_closed() -> None:
    frame = _frame([np.inf, np.nan], [True, False])
    with pytest.raises(
        repair.Campaign058NoReturnAuditRangeRepairError,
        match="values or keys",
    ):
        repair.validate_candidate_frame(
            frame, expected_rows=2, expected_eligible_rows=1
        )


def test_ineligible_nonmissing_value_fails_closed() -> None:
    frame = _frame([1.0, 2.0], [True, False])
    with pytest.raises(
        repair.Campaign058NoReturnAuditRangeRepairError,
        match="values or keys",
    ):
        repair.validate_candidate_frame(
            frame, expected_rows=2, expected_eligible_rows=1
        )


def test_install_changes_only_actual_candidate_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_append = repair.audit._audit_engine["_append_all_prior_comparisons"]
    original_verify = repair.audit._audit_engine["verify_static_bindings"]
    original_run = repair.audit._audit_engine["run_no_return_audit"]
    monkeypatch.setitem(
        repair.audit._audit_engine,
        "load_candidate_frame",
        repair.audit.load_candidate_frame,
    )
    repair.install_repair()
    assert (
        repair.audit._audit_engine["load_candidate_frame"]
        is repair.load_candidate_frame_compat
    )
    assert repair.audit._audit_engine["_append_all_prior_comparisons"] is original_append
    assert repair.audit._audit_engine["verify_static_bindings"] is original_verify
    assert repair.audit._audit_engine["run_no_return_audit"] is original_run
