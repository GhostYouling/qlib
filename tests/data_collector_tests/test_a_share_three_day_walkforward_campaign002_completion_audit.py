from __future__ import annotations

from scripts import (
    a_share_three_day_walkforward_campaign002_completion_audit as AUDIT,
)


def test_completed_campaign002_passes_all_read_only_requirements() -> None:
    result = AUDIT.audit()
    assert result["status"] == "passed"
    assert result["requirement_check_count"] == 12
    assert result["failed_requirement_checks"] == []
    assert all(item["passed"] for item in result["checks"])


def test_completed_campaign002_never_opened_exposed_stress_interval() -> None:
    result = AUDIT.audit()
    check = next(
        item
        for item in result["checks"]
        if item["name"]
        == "historically_exposed_2024_2025_interval_was_not_opened"
    )
    assert check["passed"] is True
    assert check["evidence"]["stress_interval_opened"] is False
    assert check["evidence"]["stress_ledger_entry_count"] == 0
