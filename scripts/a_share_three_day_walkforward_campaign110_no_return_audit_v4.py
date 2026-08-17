#!/usr/bin/env python3
"""Run Campaign110's frozen coverage-first all-133 no-return audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign110_no_return_audit_v3 as base


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_ADAPTER_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_no_return_audit_adapter_freeze_v3_20260808.json"
)
AUDIT_ADAPTER_TEST = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign110_no_return_audit_v4.py"
)
PRIOR_ADAPTER_FREEZE_SHA256 = (
    "480746156fa6262abe60f347f497cf1a01d514706385cb49c7cc6c41e7509555"
)
RUNTIME_DOCSTRING = (
    "Run Campaign110's frozen coverage-first all-133 no-return audit."
)


original = base.base.base
original.main.__globals__["__doc__"] = RUNTIME_DOCSTRING


def validate_audit_adapter_freeze() -> dict[str, Any]:
    if not AUDIT_ADAPTER_FREEZE.is_file():
        raise base.Campaign110NoReturnAuditError(
            "Campaign110 v3 no-return audit adapter freeze is absent"
        )
    record = json.loads(AUDIT_ADAPTER_FREEZE.read_text(encoding="utf-8"))
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign110_no_return_audit_adapter_freeze"
        and record.get("status")
        == "cli_comparator_count_recovery_frozen_before_coverage_or_comparator_values"
        and (record.get("audit_entry_point") or {}).get("sha256")
        == original.candidate._sha256(Path(__file__).resolve())
        and (record.get("synthetic_test") or {}).get("sha256")
        == original.candidate._sha256(AUDIT_ADAPTER_TEST)
        and (record.get("prior_adapter_freeze") or {}).get("sha256")
        == PRIOR_ADAPTER_FREEZE_SHA256
        and boundary.get("coverage_or_capacity_metrics_computed_before_freeze")
        is False
        and boundary.get("comparator_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued_before_freeze") is False
    ):
        raise base.Campaign110NoReturnAuditError(
            "Campaign110 v3 no-return audit adapter freeze changed"
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
