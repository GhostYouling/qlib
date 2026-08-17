#!/usr/bin/env python3
"""Run Campaign110 recovery with the exact Campaign109 loader export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign109_no_return_audit as c109_audit
from scripts import a_share_three_day_walkforward_campaign110_no_return_audit_v7 as base


REPO_ROOT = Path(__file__).resolve().parents[1]
RECOVERY_ADAPTER_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_no_return_comparator_133_recovery_implementation_freeze_v4_20260808.json"
)
RECOVERY_ADAPTER_TEST = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign110_no_return_audit_v8.py"
)
PRIOR_RECOVERY_FREEZE_SHA256 = (
    "dc1c9b9a47d8d050f1223cb1eb70e51ebe94b526f2ee8ab61d306418a5c487fc"
)


if hasattr(c109_audit, "_load_comparisons_after_coverage"):
    raise RuntimeError("Campaign109 loader export recovery is no longer necessary")
c109_audit._load_comparisons_after_coverage = c109_audit._generated[
    "_load_comparisons_after_coverage"
]


def validate_recovery_adapter_freeze() -> dict[str, Any]:
    if not RECOVERY_ADAPTER_FREEZE.is_file():
        raise base.base.base.Campaign110NoReturnAuditError(
            "Campaign110 comparator133 v4 recovery freeze is absent"
        )
    record = json.loads(RECOVERY_ADAPTER_FREEZE.read_text(encoding="utf-8"))
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign110_no_return_comparator133_recovery_implementation_freeze"
        and record.get("status")
        == "campaign109_loader_export_recovery_frozen_before_comparator_values"
        and (record.get("entry_point") or {}).get("sha256")
        == base.base.base.candidate._sha256(Path(__file__).resolve())
        and (record.get("synthetic_test") or {}).get("sha256")
        == base.base.base.candidate._sha256(RECOVERY_ADAPTER_TEST)
        and (record.get("prior_recovery_freeze") or {}).get("sha256")
        == PRIOR_RECOVERY_FREEZE_SHA256
        and boundary.get("comparator_values_read_by_failed_recovery") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued_before_freeze") is False
    ):
        raise base.base.base.Campaign110NoReturnAuditError(
            "Campaign110 comparator133 v4 recovery freeze changed"
        )
    return record


def main() -> int:
    validate_recovery_adapter_freeze()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
