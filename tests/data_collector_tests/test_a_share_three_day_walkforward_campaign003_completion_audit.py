from __future__ import annotations

from argparse import Namespace

from scripts import (
    a_share_three_day_walkforward_campaign003_completion_audit as AUDIT,
)


def test_real_campaign003_completion_audit_passes_all_checks() -> None:
    result = AUDIT.run_audit(
        Namespace(
            campaign=str(AUDIT.DEFAULT_CAMPAIGN),
            output_root=str(AUDIT.DEFAULT_OUTPUT_ROOT),
            research_record=str(AUDIT.DEFAULT_RESEARCH_RECORD),
            compact=True,
        )
    )
    assert result["status"] == "passed"
    assert result["requirement_check_count"] == 12
    assert result["failed_requirement_checks"] == []
    assert all(item["passed"] for item in result["checks"])
