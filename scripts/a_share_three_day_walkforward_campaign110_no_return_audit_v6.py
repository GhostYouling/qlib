#!/usr/bin/env python3
"""Run the frozen Campaign110 comparator-133 recovery with exact verifier alias."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign110_no_return_audit_v5 as base


REPO_ROOT = Path(__file__).resolve().parents[1]
RECOVERY_ADAPTER_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_no_return_comparator_133_recovery_implementation_freeze_v2_20260808.json"
)
RECOVERY_ADAPTER_TEST = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign110_no_return_audit_v6.py"
)
PRIOR_RECOVERY_FREEZE_SHA256 = (
    "250200d189b27a0466a670c26ea60c5771a1bff88ae122d4138cb009e9222361"
)


expected_namespace = base.base.base.base
source_namespace = base.base.base
if hasattr(expected_namespace, "c109_verifier"):
    raise RuntimeError("Campaign110 verifier alias recovery is no longer necessary")
expected_namespace.c109_verifier = source_namespace.c109_verifier


def validate_recovery_adapter_freeze() -> dict[str, Any]:
    if not RECOVERY_ADAPTER_FREEZE.is_file():
        raise base.Campaign110NoReturnAuditError(
            "Campaign110 comparator133 v2 recovery freeze is absent"
        )
    record = json.loads(RECOVERY_ADAPTER_FREEZE.read_text(encoding="utf-8"))
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign110_no_return_comparator133_recovery_implementation_freeze"
        and record.get("status")
        == "verifier_module_alias_recovery_frozen_before_comparator133_or_recovery_values"
        and (record.get("entry_point") or {}).get("sha256")
        == base.candidate._sha256(Path(__file__).resolve())
        and (record.get("synthetic_test") or {}).get("sha256")
        == base.candidate._sha256(RECOVERY_ADAPTER_TEST)
        and (record.get("prior_recovery_freeze") or {}).get("sha256")
        == PRIOR_RECOVERY_FREEZE_SHA256
        and boundary.get("comparator_133_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued_before_freeze") is False
    ):
        raise base.Campaign110NoReturnAuditError(
            "Campaign110 comparator133 v2 recovery freeze changed"
        )
    return record


def main() -> int:
    validate_recovery_adapter_freeze()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
