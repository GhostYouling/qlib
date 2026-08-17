#!/usr/bin/env python3
"""Run Campaign117 uniqueness with the frozen skill-drift adapter recovery."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import (
    a_share_three_day_walkforward_campaign117_adapter_binding_recovery as adapter_recovery,
)
from scripts import a_share_three_day_walkforward_campaign117_ordered_uniqueness as base


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER_SHA256 = "d1ac2e3359ccbd6a7b6ea223b62774dfd1b79611cb1ff9bc1cfab74e6e9406be"
FAILURE_RECORD_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_117_ordered_uniqueness_infrastructure_failure_20260813.json"
)
RECOVERY_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_117_ordered_uniqueness_recovery_freeze_20260813.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign117_ordered_uniqueness_recovery.py"
)
ADAPTER_RECOVERY_PATH = Path(adapter_recovery.__file__).resolve()


class Campaign117OrderedUniquenessRecoveryError(RuntimeError):
    """Fail closed when the skill-drift recovery boundary changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


# Patch only the historical metadata validator. Range, NaN, sort and alignment
# functions remain the exact Campaign107 implementations.
base.c110_v1.adapter.validate_contract = adapter_recovery.validate_contract


def _validate_recovery_freeze() -> dict[str, Any]:
    if not RECOVERY_FREEZE_PATH.is_file():
        raise Campaign117OrderedUniquenessRecoveryError(
            "ordered uniqueness recovery freeze is absent"
        )
    record = json.loads(RECOVERY_FREEZE_PATH.read_text(encoding="utf-8"))
    frozen = record.get("frozen_recovery") or {}
    test = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign117_ordered_uniqueness_recovery_freeze"
        and record.get("status")
        == "sole_skill_binding_drift_recovery_frozen_before_any_comparator_value"
        and frozen.get("runner_path") == _relative(Path(__file__))
        and frozen.get("runner_sha256") == _sha256(Path(__file__))
        and frozen.get("test_path") == _relative(TEST_PATH)
        and frozen.get("test_sha256") == _sha256(TEST_PATH)
        and frozen.get("base_runner_sha256") == BASE_RUNNER_SHA256
        and frozen.get("adapter_recovery_path") == _relative(ADAPTER_RECOVERY_PATH)
        and frozen.get("adapter_recovery_sha256") == _sha256(ADAPTER_RECOVERY_PATH)
        and frozen.get("current_skill_sha256") == adapter_recovery.CURRENT_SKILL_SHA256
        and test.get("passed") == 2
        and test.get("exit_code") == 0
        and boundary.get("comparator_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign117OrderedUniquenessRecoveryError(
            "ordered uniqueness recovery freeze changed"
        )
    return record


def validate_static_bindings() -> dict[str, Any]:
    if _sha256(Path(base.__file__).resolve()) != BASE_RUNNER_SHA256:
        raise Campaign117OrderedUniquenessRecoveryError("base runner changed")
    adapter_recovery.validate_contract()
    if not FAILURE_RECORD_PATH.is_file():
        raise Campaign117OrderedUniquenessRecoveryError("failure record is absent")
    freeze = _validate_recovery_freeze()
    plan = base.build_plan()
    if plan.get("ready") is not True:
        raise Campaign117OrderedUniquenessRecoveryError("base plan is not ready")
    return {
        "recovery_freeze_sha256": _sha256(RECOVERY_FREEZE_PATH),
        "failure_record_sha256": _sha256(FAILURE_RECORD_PATH),
        "base_plan": plan,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "recovery_status": freeze["status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--confirm-run", action="store_true")
    args = parser.parse_args()
    static = validate_static_bindings()
    if args.command == "plan":
        print(
            json.dumps(
                {
                    "kind": "a_share_three_day_walkforward_campaign117_ordered_uniqueness_recovery_plan",
                    "ready": True,
                    "static_bindings": static,
                    "comparator_values_read": False,
                    "historical_daily_price_or_forward_return_values_read": False,
                },
                sort_keys=True,
            )
        )
        return 0
    if not args.confirm_run:
        raise Campaign117OrderedUniquenessRecoveryError("run requires --confirm-run")
    path = base.run_ordered_uniqueness(confirm=True)
    print(json.dumps({"uniqueness_audit_path": str(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
