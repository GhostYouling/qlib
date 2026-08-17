from __future__ import annotations

from pathlib import Path

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign097_no_return_audit_v3 as audit,
)


def test_v2_and_failure_record_are_immutable() -> None:
    assert audit._sha256(Path(audit.v2.__file__).resolve()) == audit.V2_RUNNER_SHA256
    assert (
        audit._sha256(audit.v2.AUDIT_IMPLEMENTATION_FREEZE)
        == audit.V2_IMPLEMENTATION_FREEZE_SHA256
    )
    assert (
        audit._sha256(audit.v2.AUDIT_ACTIVATION_BINDING) == audit.V2_ACTIVATION_SHA256
    )
    assert audit._sha256(audit.FAILURE_RECORD) == audit.FAILURE_RECORD_SHA256


def test_verifier_accepts_exact_five_field_contract(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_verify(path: Path, *, workers: int) -> dict[str, int]:
        observed.update({"path": path, "workers": workers})
        return dict(audit.EXPECTED_VERIFICATION)

    monkeypatch.setattr(audit.v2.v1, "_require", lambda *_args: None)
    monkeypatch.setattr(audit.v2.v1.definitions, "verify_snapshot_files", fake_verify)
    result = audit.verify_candidate_snapshot(workers=2)
    assert result == audit.EXPECTED_VERIFICATION
    assert observed == {
        "path": audit.v2.v1.SNAPSHOT_MANIFEST_PATH,
        "workers": 2,
    }


def test_verifier_rejects_changed_aggregate(monkeypatch) -> None:
    changed = dict(audit.EXPECTED_VERIFICATION)
    changed["rows_verified"] -= 1
    monkeypatch.setattr(audit.v2.v1, "_require", lambda *_args: None)
    monkeypatch.setattr(
        audit.v2.v1.definitions,
        "verify_snapshot_files",
        lambda _path, *, workers: changed,
    )
    with pytest.raises(audit.Campaign097NoReturnAuditV3Error, match="aggregate"):
        audit.verify_candidate_snapshot(workers=1)


def test_status_does_not_read_values() -> None:
    result = audit.status()
    assert result["coverage_or_capacity_metrics_computed_by_status"] is False
    assert result["comparison_values_read_by_status"] is False
    assert (
        result["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert result["repair_scope"] == "exact_full_snapshot_verification_contract_only"
