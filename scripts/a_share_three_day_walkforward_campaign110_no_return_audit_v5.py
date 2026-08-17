#!/usr/bin/env python3
"""Recover Campaign110 by binding the frozen 133-comparator loader exactly once."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign110_no_return_audit_v4 as base


REPO_ROOT = Path(__file__).resolve().parents[1]
RECOVERY_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_no_return_comparator_133_recovery_protocol_20260808.json"
)
RECOVERY_PROTOCOL_SHA256 = (
    "07ffa70076d41d921eba8cfde86155f97b2398aee521f2850b88ef58b4682e7d"
)
RECOVERY_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_no_return_comparator_133_recovery_implementation_freeze_20260808.json"
)
RECOVERY_TEST = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign110_no_return_audit_v5.py"
)
RECOVERY_OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_110/no_return_recovery_v1"
)


original = base.original
run_globals = original.run_no_return_audit.__globals__
run_globals["_load_comparisons_after_coverage"] = (
    original._load_comparisons_after_coverage
)


def load_recovery_protocol() -> dict[str, Any]:
    if original.candidate._sha256(RECOVERY_PROTOCOL) != RECOVERY_PROTOCOL_SHA256:
        raise original.Campaign110NoReturnAuditError(
            "Campaign110 comparator133 recovery protocol changed"
        )
    record = json.loads(RECOVERY_PROTOCOL.read_text(encoding="utf-8"))
    exact = record.get("exact_recovery") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign110_no_return_comparator133_recovery_protocol"
        and record.get("status")
        == "frozen_after_incomplete_132_comparator_audit_before_comparator133_or_any_return"
        and exact.get("required_comparator_count") == 133
        and exact.get("required_comparator_order_sha256")
        == original.candidate.NUMERIC_COMPARATOR_ORDER_SHA256
        and exact.get("last_comparator") == original.c109.FACTOR_NAME
        and exact.get("last_comparator_range") == [-1.0, 1.0]
        and Path(str(exact.get("new_output_root"))).resolve()
        == RECOVERY_OUTPUT_ROOT.resolve()
        and exact.get("single_recovery_run") is True
        and exact.get("all_133_results_and_source_receipts_must_be_present")
        is True
        and boundary.get("comparator_133_values_read_before_recovery_freeze")
        is False
        and boundary.get("historical_daily_price_fields_read") == []
        and boundary.get("historical_forward_return_fields_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise original.Campaign110NoReturnAuditError(
            "Campaign110 comparator133 recovery semantics changed"
        )
    return record


def validate_recovery_implementation_freeze() -> dict[str, Any]:
    if not RECOVERY_IMPLEMENTATION_FREEZE.is_file():
        raise original.Campaign110NoReturnAuditError(
            "Campaign110 comparator133 recovery implementation freeze is absent"
        )
    record = json.loads(RECOVERY_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign110_no_return_comparator133_recovery_implementation_freeze"
        and record.get("status")
        == "frozen_before_comparator133_or_recovery_audit_values"
        and (record.get("protocol") or {}).get("sha256")
        == RECOVERY_PROTOCOL_SHA256
        and (record.get("entry_point") or {}).get("sha256")
        == original.candidate._sha256(Path(__file__).resolve())
        and (record.get("synthetic_test") or {}).get("sha256")
        == original.candidate._sha256(RECOVERY_TEST)
        and boundary.get("comparator_133_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued_before_freeze") is False
    ):
        raise original.Campaign110NoReturnAuditError(
            "Campaign110 comparator133 recovery implementation freeze changed"
        )
    return record


Campaign110NoReturnAuditError = original.Campaign110NoReturnAuditError
candidate = original.candidate
c109 = original.c109
FACTOR_NAME = original.FACTOR_NAME
DEFAULT_DATA_ROOT = original.DEFAULT_DATA_ROOT
EXPECTED_ROWS = original.EXPECTED_ROWS
EXPECTED_PARTITIONS = original.EXPECTED_PARTITIONS
EXPECTED_COMPARISON_COUNT = original.EXPECTED_COMPARISON_COUNT
load_protocol = original.load_protocol
verify_static_bindings = original.verify_static_bindings
verify_candidate_snapshot = original.verify_candidate_snapshot


def status() -> dict[str, Any]:
    outputs = sorted(RECOVERY_OUTPUT_ROOT.glob("*_campaign110_no_return_audit.json"))
    return {
        "status": "recovery_output_present" if outputs else "recovery_ready",
        "recovery_output_root": str(RECOVERY_OUTPUT_ROOT),
        "recovery_output_count": len(outputs),
        "runtime_loader_is_frozen_133_loader": run_globals.get(
            "_load_comparisons_after_coverage"
        )
        is original._load_comparisons_after_coverage,
        "expected_comparison_count": EXPECTED_COMPARISON_COUNT,
        "coverage_or_comparator_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "run"))
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument(
        "--experiment-root", type=Path, default=RECOVERY_OUTPUT_ROOT
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--confirm-run", action="store_true")
    args = parser.parse_args()
    load_recovery_protocol()
    validate_recovery_implementation_freeze()
    base.validate_audit_adapter_freeze()
    base.base.validate_audit_adapter_freeze()
    base.base.base.validate_audit_adapter_freeze()
    base.base.base.c109_verifier.validate_implementation_freeze()
    base.base.base.base.verifier.validate_implementation_freeze()
    if args.experiment_root.expanduser().resolve() != RECOVERY_OUTPUT_ROOT.resolve():
        raise Campaign110NoReturnAuditError(
            "Campaign110 recovery output root changed"
        )
    if args.command == "status":
        print(json.dumps(status(), ensure_ascii=False, sort_keys=True))
        return 0
    path = original.run_no_return_audit(
        data_root=args.data_root,
        experiment_root=RECOVERY_OUTPUT_ROOT,
        workers=args.workers,
        confirm_run=args.confirm_run,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
