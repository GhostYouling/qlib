#!/usr/bin/env python3
"""Run Campaign097's additive snapshot-verification contract repair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import (
    a_share_three_day_walkforward_campaign097_no_return_audit_v2 as v2,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = v2.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = v2.DEFAULT_EXPERIMENT_ROOT
V2_RUNNER_SHA256 = "4e89b3e002f6a42b84fe41f0e4c09cb411e19307c4224867782ed1df141e20d2"
V2_IMPLEMENTATION_FREEZE_SHA256 = (
    "3773142cca7e86f135caadfcb448588eb613031eaa56a1b9ccc39b2e94e6faf4"
)
V2_ACTIVATION_SHA256 = (
    "31237866d1e200390567e6b99fc146dfc1f0444803f642fbd2efab198e11da2d"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_no_return_audit_verification_contract_failure_20260807.json"
)
FAILURE_RECORD_SHA256 = (
    "5211b89c8bc0a7334cab5b33adfcfce4417043140c7b265a276a8d8985b26f0c"
)
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_no_return_audit_implementation_freeze_v3_20260807.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_no_return_audit_activation_binding_v3_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign097_no_return_audit_v3.py"
)
EXPECTED_VERIFICATION = {
    "partitions_verified": 33_015,
    "rows_verified": 7_724_498,
    "eligible_rows_verified": 7_699_914,
    "partition_bytes_verified": 290_653_280,
    "market_benchmark_bytes_verified": 3_607_113,
}


class Campaign097NoReturnAuditV3Error(RuntimeError):
    """Fail-closed Campaign097 v3 no-return audit error."""


def _sha256(path: Path) -> str:
    return v2._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign097NoReturnAuditV3Error(f"Campaign097 v3 {label} changed: {path}")


def _load_implementation_freeze() -> dict[str, Any]:
    _require(Path(v2.__file__).resolve(), V2_RUNNER_SHA256, "v2 runner")
    _require(
        v2.AUDIT_IMPLEMENTATION_FREEZE,
        V2_IMPLEMENTATION_FREEZE_SHA256,
        "v2 implementation freeze",
    )
    _require(v2.AUDIT_ACTIVATION_BINDING, V2_ACTIVATION_SHA256, "v2 activation")
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "v2 failure record")
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign097NoReturnAuditV3Error("v3 implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_no_return_audit_implementation_freeze_v3"
        and record.get("status")
        == "verification_contract_repair_frozen_before_campaign097_candidate_column_alignment_coverage_comparison_or_return_values"
        and (record.get("v3_audit_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v3_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("v2_failure_record") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and record.get("repair_scope")
        == "assert the exact five-field Campaign097 full snapshot verification result only"
        and record.get("candidate_parquet_columns_decoded_before_v3_freeze") is False
        and record.get("eligibility_stock_day_keys_read_before_v3_freeze") is False
        and record.get("coverage_or_capacity_metrics_computed_before_v3_freeze")
        is False
        and record.get("comparison_values_read_before_v3_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_v3_freeze"
        )
        is False
        and record.get("provider_request_issued_before_v3_freeze") is False
    ):
        raise Campaign097NoReturnAuditV3Error("v3 implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign097NoReturnAuditV3Error("v3 activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_no_return_audit_activation_binding_v3"
        and record.get("status")
        == "verification_contract_repair_frozen_before_campaign097_candidate_column_alignment_coverage_comparison_or_return_values"
        and (record.get("implementation_freeze_v3") or {}).get("sha256")
        == _sha256(AUDIT_IMPLEMENTATION_FREEZE)
        and (record.get("v2_failure_record") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and record.get("eligibility_stock_day_keys_read_before_activation") is False
        and record.get("coverage_or_capacity_metrics_computed_before_activation")
        is False
        and record.get("comparison_values_read_before_activation") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_activation"
        )
        is False
        and record.get("provider_request_issued_before_activation") is False
    ):
        raise Campaign097NoReturnAuditV3Error("v3 activation binding changed")
    return record


def verify_candidate_snapshot(*, workers: int) -> dict[str, int]:
    if workers < 1:
        raise Campaign097NoReturnAuditV3Error("workers must be positive")
    v2.v1._require(
        v2.v1.SNAPSHOT_MANIFEST_PATH,
        v2.v1.SNAPSHOT_MANIFEST_SHA256,
        "candidate snapshot",
    )
    result = v2.v1.definitions.verify_snapshot_files(
        v2.v1.SNAPSHOT_MANIFEST_PATH, workers=workers
    )
    if result != EXPECTED_VERIFICATION:
        raise Campaign097NoReturnAuditV3Error(
            "candidate snapshot verification aggregate changed"
        )
    return result


def _run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int, confirm_run: bool
) -> Path:
    if not confirm_run:
        raise Campaign097NoReturnAuditV3Error(
            "Campaign097 v3 audit requires --confirm-run"
        )
    _load_activation_binding()
    original_verifier = v2.verify_candidate_snapshot
    v2.verify_candidate_snapshot = lambda *, workers: verify_candidate_snapshot(
        workers=workers
    )
    try:
        path = v2._run_no_return_audit(
            data_root=data_root,
            experiment_root=experiment_root,
            workers=workers,
            confirm_run=True,
        )
    finally:
        v2.verify_candidate_snapshot = original_verifier
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["audit_verification_contract_repair"] = {
        "scope": "exact five-field full snapshot verification result only",
        "expected_verification": EXPECTED_VERIFICATION,
        "v2_runner_sha256": V2_RUNNER_SHA256,
        "v2_implementation_freeze_sha256": V2_IMPLEMENTATION_FREEZE_SHA256,
        "v2_activation_binding_sha256": V2_ACTIVATION_SHA256,
        "v2_failure_record_sha256": FAILURE_RECORD_SHA256,
        "v3_implementation_freeze_sha256": _sha256(AUDIT_IMPLEMENTATION_FREEZE),
        "v3_activation_binding_sha256": _sha256(AUDIT_ACTIVATION_BINDING),
        "factor_alignment_coverage_gate_comparator_order_or_threshold_changed": False,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    base = v2.status(experiment_root)
    return {
        **base,
        "status": (
            "ready_for_single_v3_audit"
            if AUDIT_ACTIVATION_BINDING.is_file()
            else "v3_activation_binding_absent"
        ),
        "repair_scope": "exact_full_snapshot_verification_contract_only",
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
