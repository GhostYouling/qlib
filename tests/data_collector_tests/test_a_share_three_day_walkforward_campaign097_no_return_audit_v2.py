from __future__ import annotations

from pathlib import Path

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign097_no_return_audit_v2 as audit,
)


def test_v1_and_failure_record_are_immutable() -> None:
    assert audit._sha256(Path(audit.v1.__file__).resolve()) == audit.V1_RUNNER_SHA256
    assert (
        audit._sha256(audit.v1.AUDIT_IMPLEMENTATION_FREEZE)
        == audit.V1_IMPLEMENTATION_FREEZE_SHA256
    )
    assert (
        audit._sha256(audit.v1.AUDIT_ACTIVATION_BINDING) == audit.V1_ACTIVATION_SHA256
    )
    assert audit._sha256(audit.FAILURE_RECORD) == audit.FAILURE_RECORD_SHA256


def test_verifier_binds_workers_without_changing_semantics(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_verify(path: Path, *, workers: int) -> dict[str, object]:
        observed.update({"path": path, "workers": workers})
        return {
            "status": "verified",
            "dataset_sha256": audit.v1.SNAPSHOT_DATASET_SHA256,
            "partitions": audit.v1.EXPECTED_RAW_PARTITIONS,
            "rows": audit.v1.EXPECTED_RAW_ROWS,
            "eligible_rows": audit.v1.EXPECTED_RAW_ELIGIBLE_ROWS,
            "comparison_values_read": False,
        }

    monkeypatch.setattr(audit.v1, "_require", lambda *_args: None)
    monkeypatch.setattr(audit.v1.definitions, "verify_snapshot_files", fake_verify)
    result = audit.verify_candidate_snapshot(workers=3)
    assert result["status"] == "verified"
    assert observed == {"path": audit.v1.SNAPSHOT_MANIFEST_PATH, "workers": 3}


def test_verifier_rejects_nonpositive_workers() -> None:
    with pytest.raises(audit.Campaign097NoReturnAuditV2Error, match="positive"):
        audit.verify_candidate_snapshot(workers=0)


def test_status_does_not_read_values() -> None:
    result = audit.status()
    assert result["coverage_or_capacity_metrics_computed_by_status"] is False
    assert result["comparison_values_read_by_status"] is False
    assert (
        result["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert result["repair_scope"] == "snapshot_verifier_workers_keyword_only"
