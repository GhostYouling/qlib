from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign061_no_return_audit as audit
from scripts import a_share_three_day_walkforward_campaign061_no_return_audit_range_repair as repair


def test_range_repair_bindings() -> None:
    result = repair.verify_repair_bindings()
    assert result["audit_runner_sha256"] == repair.AUDIT_RUNNER_SHA256


def test_range_repair_exports_only_frozen_bounds() -> None:
    repair.install_repair()
    assert audit.candidate.LOWER_BOUND == 0.0
    assert audit.candidate.UPPER_BOUND == 1.0
    assert audit.candidate.FACTOR_RANGES[audit.FACTOR_NAME] == (0.0, 1.0)


def test_repaired_status_remains_pre_audit() -> None:
    repair.install_repair()
    result = audit.status(audit.DEFAULT_DATA_ROOT, audit.DEFAULT_EXPERIMENT_ROOT)
    assert result["audit_count"] == 0
    assert result["comparison_count"] == 92


def test_repair_does_not_replace_audit_functions() -> None:
    original_run = audit.run_no_return_audit
    original_loader = audit.load_candidate_frame
    repair.install_repair()
    assert audit.run_no_return_audit is original_run
    assert audit.load_candidate_frame is original_loader
