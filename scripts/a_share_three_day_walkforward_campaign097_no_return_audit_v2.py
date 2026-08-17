#!/usr/bin/env python3
"""Run Campaign097's additive snapshot-verifier worker-binding repair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import (
    a_share_three_day_walkforward_campaign097_no_return_audit as v1,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = v1.DEFAULT_EXPERIMENT_ROOT
V1_RUNNER_SHA256 = "c0d79005996420f2b6c84b645f75c427771549def134b01bca5adc710df786f2"
V1_IMPLEMENTATION_FREEZE_SHA256 = (
    "589ab6f801f47e04ec0910a3a79ad8349f994c972808955e963fc8ca22f77912"
)
V1_ACTIVATION_SHA256 = (
    "21fa50bae72afbd822ec95a3a61c35b0e4ce7cca9ae0b209fab1c1940980060a"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_no_return_audit_worker_binding_failure_20260807.json"
)
FAILURE_RECORD_SHA256 = (
    "631ea106365dca67c42ae2828ce02edf6536e46ad4c5074e8cc3cd2860d96b60"
)
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_no_return_audit_implementation_freeze_v2_20260807.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_no_return_audit_activation_binding_v2_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign097_no_return_audit_v2.py"
)


class Campaign097NoReturnAuditV2Error(RuntimeError):
    """Fail-closed Campaign097 v2 no-return audit error."""


def _sha256(path: Path) -> str:
    return v1._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign097NoReturnAuditV2Error(f"Campaign097 v2 {label} changed: {path}")


def _load_implementation_freeze() -> dict[str, Any]:
    _require(Path(v1.__file__).resolve(), V1_RUNNER_SHA256, "v1 runner")
    _require(
        v1.AUDIT_IMPLEMENTATION_FREEZE,
        V1_IMPLEMENTATION_FREEZE_SHA256,
        "v1 implementation freeze",
    )
    _require(v1.AUDIT_ACTIVATION_BINDING, V1_ACTIVATION_SHA256, "v1 activation")
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "v1 failure record")
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign097NoReturnAuditV2Error("v2 implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_no_return_audit_implementation_freeze_v2"
        and record.get("status")
        == "worker_binding_repair_frozen_before_campaign097_coverage_or_comparison_values"
        and (record.get("v2_audit_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v2_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("v1_failure_record") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and record.get("repair_scope")
        == "pass the frozen run workers value to Campaign097 candidate snapshot verification only"
        and record.get("candidate_partition_values_read_before_v2_freeze") is False
        and record.get("coverage_or_capacity_metrics_computed_before_v2_freeze")
        is False
        and record.get("comparison_values_read_before_v2_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_v2_freeze"
        )
        is False
        and record.get("provider_request_issued_before_v2_freeze") is False
    ):
        raise Campaign097NoReturnAuditV2Error("v2 implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign097NoReturnAuditV2Error("v2 activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_no_return_audit_activation_binding_v2"
        and record.get("status")
        == "worker_binding_repair_frozen_before_campaign097_coverage_or_comparison_values"
        and (record.get("implementation_freeze_v2") or {}).get("sha256")
        == _sha256(AUDIT_IMPLEMENTATION_FREEZE)
        and (record.get("v1_failure_record") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and record.get("coverage_or_capacity_metrics_computed_before_activation")
        is False
        and record.get("comparison_values_read_before_activation") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_activation"
        )
        is False
        and record.get("provider_request_issued_before_activation") is False
    ):
        raise Campaign097NoReturnAuditV2Error("v2 activation binding changed")
    return record


def verify_candidate_snapshot(*, workers: int) -> dict[str, Any]:
    if workers < 1:
        raise Campaign097NoReturnAuditV2Error("workers must be positive")
    v1._require(
        v1.SNAPSHOT_MANIFEST_PATH,
        v1.SNAPSHOT_MANIFEST_SHA256,
        "candidate snapshot",
    )
    result = v1.definitions.verify_snapshot_files(
        v1.SNAPSHOT_MANIFEST_PATH, workers=workers
    )
    if not (
        result.get("status") == "verified"
        and result.get("dataset_sha256") == v1.SNAPSHOT_DATASET_SHA256
        and result.get("partitions") == v1.EXPECTED_RAW_PARTITIONS
        and result.get("rows") == v1.EXPECTED_RAW_ROWS
        and result.get("eligible_rows") == v1.EXPECTED_RAW_ELIGIBLE_ROWS
        and result.get("comparison_values_read") is False
    ):
        raise Campaign097NoReturnAuditV2Error("candidate snapshot verification changed")
    return result


def _run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int, confirm_run: bool
) -> Path:
    if not confirm_run:
        raise Campaign097NoReturnAuditV2Error(
            "Campaign097 v2 audit requires --confirm-run"
        )
    _load_activation_binding()
    original_verifier = v1.verify_candidate_snapshot
    v1.verify_candidate_snapshot = lambda: verify_candidate_snapshot(workers=workers)
    try:
        path = v1._run_no_return_audit(
            data_root=data_root,
            experiment_root=experiment_root,
            workers=workers,
            confirm_run=True,
        )
    finally:
        v1.verify_candidate_snapshot = original_verifier
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["audit_runtime_repair"] = {
        "scope": "candidate snapshot verifier mandatory workers keyword only",
        "workers": workers,
        "v1_runner_sha256": V1_RUNNER_SHA256,
        "v1_implementation_freeze_sha256": V1_IMPLEMENTATION_FREEZE_SHA256,
        "v1_activation_binding_sha256": V1_ACTIVATION_SHA256,
        "v1_failure_record_sha256": FAILURE_RECORD_SHA256,
        "v2_implementation_freeze_sha256": _sha256(AUDIT_IMPLEMENTATION_FREEZE),
        "v2_activation_binding_sha256": _sha256(AUDIT_ACTIVATION_BINDING),
        "factor_alignment_coverage_gate_comparator_order_or_threshold_changed": False,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    base = v1.status(experiment_root)
    return {
        **base,
        "status": (
            "ready_for_single_v2_audit"
            if AUDIT_ACTIVATION_BINDING.is_file()
            else "v2_activation_binding_absent"
        ),
        "repair_scope": "snapshot_verifier_workers_keyword_only",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "run"))
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--confirm-run", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        print(json.dumps(status(args.experiment_root), sort_keys=True))
        return 0
    print(
        _run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
            confirm_run=args.confirm_run,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
