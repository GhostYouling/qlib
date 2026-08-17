#!/usr/bin/env python3
"""Run Campaign110 no-return gates with the frozen verify-only snapshot adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign110_snapshot_verifier as verifier
from scripts import a_share_three_day_walkforward_campaign110_no_return_audit as base


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_ADAPTER_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_no_return_audit_adapter_freeze_20260808.json"
)
AUDIT_ADAPTER_TEST = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign110_no_return_audit_v2.py"
)
SNAPSHOT_BINDING_SHA256 = (
    "35315e56abe2f48abd51177d6ff29b3f5dd6854202675af95fb26d71f493aefe"
)
VERIFIER_FREEZE_SHA256 = (
    "b9337ed49073e6af228790a0e2700218eef193673af15212c0796fd33ad11a3c"
)


if base.candidate._base_generated["_validate_manifest"] is not verifier.validate_manifest:
    raise RuntimeError("Campaign110 verify-only manifest adapter is not active")


def validate_audit_adapter_freeze() -> dict[str, Any]:
    if not AUDIT_ADAPTER_FREEZE.is_file():
        raise base.Campaign110NoReturnAuditError(
            "Campaign110 no-return audit adapter freeze is absent"
        )
    record = json.loads(AUDIT_ADAPTER_FREEZE.read_text(encoding="utf-8"))
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign110_no_return_audit_adapter_freeze"
        and record.get("status")
        == "frozen_after_verified_snapshot_before_coverage_or_comparator_values"
        and (record.get("audit_entry_point") or {}).get("sha256")
        == base.candidate._sha256(Path(__file__).resolve())
        and (record.get("synthetic_test") or {}).get("sha256")
        == base.candidate._sha256(AUDIT_ADAPTER_TEST)
        and (record.get("snapshot_binding") or {}).get("sha256")
        == SNAPSHOT_BINDING_SHA256
        and (record.get("snapshot_verifier_implementation_freeze") or {}).get(
            "sha256"
        )
        == VERIFIER_FREEZE_SHA256
        and boundary.get("coverage_or_capacity_metrics_computed_before_freeze")
        is False
        and boundary.get("comparator_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued_before_freeze") is False
        and boundary.get("snapshot_modified_after_verification") is False
    ):
        raise base.Campaign110NoReturnAuditError(
            "Campaign110 no-return audit adapter freeze changed"
        )
    return record


Campaign110NoReturnAuditError = base.Campaign110NoReturnAuditError
candidate = base.candidate
c109 = base.c109
FACTOR_NAME = base.FACTOR_NAME
DEFAULT_DATA_ROOT = base.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = base.DEFAULT_EXPERIMENT_ROOT
SNAPSHOT_MANIFEST_PATH = base.SNAPSHOT_MANIFEST_PATH
SNAPSHOT_BINDING = base.SNAPSHOT_BINDING
AUDIT_ACTIVATION_BINDING = base.AUDIT_ACTIVATION_BINDING
EXPECTED_ROWS = base.EXPECTED_ROWS
EXPECTED_PARTITIONS = base.EXPECTED_PARTITIONS
EXPECTED_COMPARISON_COUNT = base.EXPECTED_COMPARISON_COUNT
load_protocol = base.load_protocol
verify_static_bindings = base.verify_static_bindings
verify_candidate_snapshot = base.verify_candidate_snapshot
run_no_return_audit = base.run_no_return_audit
status = base.status


def main() -> int:
    validate_audit_adapter_freeze()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
