from __future__ import annotations

from pathlib import Path

import pytest

from scripts import a_share_three_day_walkforward_completion_audit as audit


def test_completion_audit_proves_every_declared_requirement() -> None:
    result = audit.audit()

    assert result["status"] == "passed"
    assert result["requirement_check_count"] == 15
    assert result["failed_requirement_checks"] == []
    assert all(item["passed"] for item in result["checks"])


def test_completion_audit_binding_check_rejects_wrong_digest(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}\n", encoding="utf-8")

    assert (
        audit.binding_matches(
            {"path": str(artifact), "sha256": "0" * 64}
        )
        is False
    )


def test_completion_audit_rejects_timezone_naive_chronology() -> None:
    with pytest.raises(audit.CompletionAuditError, match="timezone-aware"):
        audit.parse_timestamp("2026-07-27T12:00:00")
