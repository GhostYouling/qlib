from __future__ import annotations

import pytest

from scripts import a_share_three_day_walkforward_campaign059_no_return_audit_range_repair as repair


def test_repair_bindings_match_exact_frozen_factor_range() -> None:
    result = repair.verify_repair_bindings()
    assert result["range_aliases"] == {"LOWER_BOUND": 0.0, "UPPER_BOUND": 1.0}
    assert repair.audit.candidate.FACTOR_RANGES[repair.audit.FACTOR_NAME] == (0.0, 1.0)


def test_install_only_adds_two_candidate_module_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(repair.audit.candidate, "LOWER_BOUND", raising=False)
    monkeypatch.delattr(repair.audit.candidate, "UPPER_BOUND", raising=False)
    original_load = repair.audit._audit_engine["load_candidate_frame"]
    original_append = repair.audit._audit_engine["_append_all_prior_comparisons"]
    original_run = repair.audit._audit_engine["run_no_return_audit"]
    repair.install_repair()
    assert repair.audit.candidate.LOWER_BOUND == 0.0
    assert repair.audit.candidate.UPPER_BOUND == 1.0
    assert repair.audit._audit_engine["load_candidate_frame"] is original_load
    assert repair.audit._audit_engine["_append_all_prior_comparisons"] is original_append
    assert repair.audit._audit_engine["run_no_return_audit"] is original_run


def test_conflicting_existing_alias_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repair.audit.candidate, "LOWER_BOUND", -1.0, raising=False)
    monkeypatch.delattr(repair.audit.candidate, "UPPER_BOUND", raising=False)
    with pytest.raises(
        repair.Campaign059NoReturnAuditRangeRepairError,
        match="conflicting LOWER_BOUND",
    ):
        repair.install_repair()
