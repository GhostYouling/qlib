#!/usr/bin/env python3
"""Retry Campaign083 after an exact isolated-runtime compatibility repair."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow

from scripts import a_share_three_day_walkforward_campaign083_no_return_audit as v1

REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_083_no_return_runtime_compatibility_repair_protocol_v2_20260806.json"
)
REPAIR_PROTOCOL_SHA256 = (
    "730bcba595cced9640998e7e56453aaf0f828ce9dde39fafb2455054a426ae93"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_083_no_return_runtime_compatibility_failure_20260806.json"
)
FAILURE_RECORD_SHA256 = (
    "b5f021315a76bae6a606983d3b3c5c643b444bc8847a63807c4161ced4f39a0f"
)
BASE_V1_SHA256 = "ff9859120319a52c75aabcbd9d7f5b46c88166af0ca3fc460df981bf2fe71cf1"
ACTIVATION_BINDING_SHA256 = (
    "1bf6eba732c620e13f15ecf586b95b88239854703a901982c7df50010eed0e9d"
)
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_083_no_return_audit_implementation_freeze_v2_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign083_no_return_audit_v2.py"
)
REQUIRED_PANDAS_VERSION = "2.2.2"
REQUIRED_PYARROW_VERSION = "16.1.0"


class Campaign083NoReturnAuditV2Error(RuntimeError):
    """Fail-closed Campaign083 v2 runtime-repair error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign083NoReturnAuditV2Error(f"{label} changed: {path}")


def runtime_versions() -> dict[str, str]:
    return {"pandas": pd.__version__, "pyarrow": pyarrow.__version__}


def require_exact_runtime() -> dict[str, str]:
    observed = runtime_versions()
    if observed != {
        "pandas": REQUIRED_PANDAS_VERSION,
        "pyarrow": REQUIRED_PYARROW_VERSION,
    }:
        raise Campaign083NoReturnAuditV2Error(
            "isolated runtime does not match the frozen compatibility pair"
        )
    return observed


def load_repair_protocol() -> dict[str, Any]:
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "v2 repair protocol")
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "v1 failure record")
    _require(Path(v1.__file__).resolve(), BASE_V1_SHA256, "v1 audit runner")
    _require(
        v1.AUDIT_ACTIVATION_BINDING,
        ACTIVATION_BINDING_SHA256,
        "v1 activation binding",
    )
    spec = json.loads(REPAIR_PROTOCOL.read_text(encoding="utf-8"))
    runtime = spec.get("runtime_transition") or {}
    sole = spec.get("sole_repair") or {}
    retry = spec.get("retry") or {}
    required = runtime.get("required_runtime") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign083_no_return_runtime_compatibility_repair_protocol"
        and spec.get("status") == "frozen_after_v1_runtime_failure_before_full_retry"
        and required.get("pandas") == REQUIRED_PANDAS_VERSION
        and required.get("pyarrow") == REQUIRED_PYARROW_VERSION
        and runtime.get(
            "runtime_gate_suppression_monkey_patch_or_constant_rebinding_allowed"
        )
        is False
        and all(
            sole.get(key) is True
            for key in (
                "original_runner_hash_still_required",
                "original_activation_binding_hash_still_required",
                "candidate_snapshot_manifest_and_dataset_hashes_still_required",
                "candidate_partition_byte_and_frame_hashes_still_required",
                "coverage_gate_still_runs_from_scratch",
                "all_112_comparators_still_required_in_frozen_order_after_coverage_pass",
            )
        )
        and all(
            sole.get(key) is False
            for key in (
                "candidate_formula_or_direction_changed",
                "candidate_snapshot_or_manifest_changed",
                "coverage_or_capacity_gate_changed",
                "comparison_library_order_or_threshold_changed",
                "historical_daily_price_or_return_field_changed",
                "development_or_stress_rule_changed",
                "provider_or_candidate49_workflow_changed",
            )
        )
        and retry.get("partial_statistics_reused") is False
        and retry.get(
            "restart_from_static_binding_candidate_snapshot_verification_and_coverage"
        )
        is True
        and retry.get("expected_published_audit_count_before_retry") == 0
        and retry.get("maximum_authorized_v2_retries") == 1
    ):
        raise Campaign083NoReturnAuditV2Error("v2 repair protocol semantics changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign083NoReturnAuditV2Error("v2 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign083_no_return_audit_implementation_freeze"
        and record.get("version") == 2
        and record.get("status")
        == "frozen_before_full_retry_with_exact_runtime_install_only_repair"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v2_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("partial_statistics_reused") is False
        and record.get("candidate_snapshot_or_manifest_rewritten") is False
        and record.get("runtime_gate_suppressed_or_monkey_patched") is False
        and record.get("historical_daily_price_fields_read_before_retry") == []
        and record.get("historical_forward_returns_read_before_retry") is False
    ):
        raise Campaign083NoReturnAuditV2Error("v2 implementation freeze changed")
    return record


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    load_repair_protocol()
    _load_implementation_freeze()
    if v1.status(experiment_root).get("audit_count") != 0:
        raise Campaign083NoReturnAuditV2Error(
            "v2 retry requires zero published Campaign083 audits"
        )
    require_exact_runtime()
    return v1.run_no_return_audit(
        data_root=data_root,
        experiment_root=experiment_root,
        workers=workers,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=v1.DEFAULT_DATA_ROOT)
    parser.add_argument(
        "--experiment-root", type=Path, default=v1.DEFAULT_EXPERIMENT_ROOT
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    payload = {
        "audit": str(
            run_no_return_audit(
                data_root=args.data_root,
                experiment_root=args.experiment_root,
                workers=args.workers,
            )
        ),
        "runtime_compatibility_repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "runtime_versions": runtime_versions(),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
