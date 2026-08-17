#!/usr/bin/env python3
"""Run Campaign117 coverage with the frozen recovered snapshot verifier."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign117_no_return_audit as audit
from scripts import (
    a_share_three_day_walkforward_campaign117_snapshot_verify_recovery as recovery,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_AUDIT_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign117_no_return_audit.py"
)
ORIGINAL_AUDIT_RUNNER_SHA256 = (
    "8ea3a1b2e0cc369ea6a1192304af101b54fecdfebc5334fa199dbe53807331a5"
)
RECOVERY_VERIFIER_SHA256 = (
    "0dafa52aa8e39f6b42f93c4142198bfde16ffe2f94ff69ee2a18140be3a21ef4"
)
ACTIVATION_BINDING_SHA256 = (
    "84c992169fa5cfbbc9babd305a19452a695609df36cd4beab72956d35c414b9c"
)
RECOVERY_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_117_coverage_recovery_freeze_20260813.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign117_coverage_recovery.py"
)


class Campaign117CoverageRecoveryError(RuntimeError):
    """Fail closed when the coverage recovery boundary changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def _validate_recovery_freeze() -> dict[str, Any]:
    if not RECOVERY_FREEZE_PATH.is_file():
        raise Campaign117CoverageRecoveryError("coverage recovery freeze is absent")
    record = json.loads(RECOVERY_FREEZE_PATH.read_text(encoding="utf-8"))
    frozen = record.get("frozen_recovery") or {}
    test = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign117_coverage_recovery_freeze"
        and record.get("status")
        == "recovered_verifier_call_frozen_before_candidate_coverage_values"
        and frozen.get("runner_path") == _relative(Path(__file__))
        and frozen.get("runner_sha256") == _sha256(Path(__file__))
        and frozen.get("test_path") == _relative(TEST_PATH)
        and frozen.get("test_sha256") == _sha256(TEST_PATH)
        and frozen.get("original_audit_runner_sha256") == ORIGINAL_AUDIT_RUNNER_SHA256
        and frozen.get("recovery_verifier_sha256") == RECOVERY_VERIFIER_SHA256
        and frozen.get("activation_binding_sha256") == ACTIVATION_BINDING_SHA256
        and test.get("passed") == 2
        and test.get("exit_code") == 0
        and boundary.get("candidate_coverage_values_read_before_freeze") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign117CoverageRecoveryError("coverage recovery freeze changed")
    return record


def validate_static_bindings() -> dict[str, Any]:
    for path, expected, label in (
        (
            ORIGINAL_AUDIT_RUNNER,
            ORIGINAL_AUDIT_RUNNER_SHA256,
            "original coverage runner",
        ),
        (
            Path(recovery.__file__).resolve(),
            RECOVERY_VERIFIER_SHA256,
            "recovery verifier",
        ),
        (
            audit.ACTIVATION_BINDING_PATH,
            ACTIVATION_BINDING_SHA256,
            "coverage activation binding",
        ),
    ):
        if not path.is_file() or _sha256(path) != expected:
            raise Campaign117CoverageRecoveryError(f"{label} changed: {path}")
    freeze = _validate_recovery_freeze()
    original_plan = audit.build_plan()
    if original_plan.get("ready") is not True:
        raise Campaign117CoverageRecoveryError(
            "original frozen coverage plan is not ready"
        )
    return {
        "original_plan": original_plan,
        "coverage_recovery_freeze_sha256": _sha256(RECOVERY_FREEZE_PATH),
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "recovery_status": freeze["status"],
    }


def run_coverage_audit(*, workers: int, confirm: bool) -> Path:
    if not confirm:
        raise Campaign117CoverageRecoveryError(
            "coverage recovery requires --confirm-coverage-audit"
        )
    static = validate_static_bindings()
    activation = audit._load_activation()
    snapshot_verification = recovery.verify_snapshot(workers=workers)
    expected_eligible = int(activation["candidate_snapshot"]["eligible_rows"])
    candidate_frame = audit._load_candidate_frame(expected_eligible)
    eligible_keys = audit._quality_listing_eligible_keys()
    coverage = audit.coverage_and_variation(candidate_frame, eligible_keys)
    del candidate_frame, eligible_keys
    gc.collect()
    passed = coverage["gate_passed_before_comparator_values"] is True
    result = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign117_coverage_audit",
        "status": (
            "coverage_passed_ready_to_freeze_all_134_ordered_comparator_audit"
            if passed
            else "coverage_failed_terminal_before_all_comparator_values"
        ),
        "recorded_at": datetime.now(UTC).isoformat(),
        "factor": audit.FACTOR_NAME,
        "direction": "higher",
        "static_bindings": static,
        "snapshot_verification": snapshot_verification,
        "coverage_and_variation": coverage,
        "comparator_values_read": False,
        "numeric_comparator_count_read": 0,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "stress_2024_2025_opened": False,
        "training_or_model_fitting_performed": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "current_scoring_selection_sizing_positions_or_orders_performed": False,
        "investment_advice": False,
        "next_action": (
            "freeze an exact all-134 ordered no-return comparator audit before reading any comparator value"
            if passed
            else "terminalize Campaign117 without reading comparator values, daily prices, or returns"
        ),
    }
    audit._atomic_exclusive_json(audit.OUTPUT_PATH, result)
    return audit.OUTPUT_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--confirm-coverage-audit", action="store_true")
    args = parser.parse_args()
    path = run_coverage_audit(
        workers=args.workers,
        confirm=args.confirm_coverage_audit,
    )
    print(json.dumps({"coverage_audit_path": str(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
