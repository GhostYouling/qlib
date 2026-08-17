#!/usr/bin/env python3
"""Retry Campaign077 with the frozen runtime-compatibility-only repair."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from scripts import a_share_three_day_walkforward_campaign077_no_return_audit as v1


REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_077_no_return_runtime_compatibility_repair_protocol_v2_20260806.json"
REPAIR_PROTOCOL_SHA256 = "e1a0567bd83f4ae75288fa2c7c50de504ff613a873bd967802ef546cca788841"
FAILURE_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_077_no_return_v1_runtime_compatibility_failure_20260806.json"
FAILURE_RECORD_SHA256 = "369b196d2e9f1f823693ef830dd4b21ff475d14e4b200c53d447df9a652ff469"
BASE_V1_SHA256 = "2247df82f8282919707d36597ea0d97959caa21ef4831d1bd5b92d65a9a8e9dc"
IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_077_no_return_audit_implementation_freeze_v2_20260806.json"
TEST_PATH = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign077_no_return_audit_v2.py"
LEGACY_PANDAS_VERSION = "2.2.3"
LEGACY_PYARROW_VERSION = "25.0.0"
CURRENT_PANDAS_VERSION = "2.2.2"
CURRENT_PYARROW_VERSION = "16.1.0"


class Campaign077NoReturnAuditV2Error(RuntimeError):
    """Fail-closed Campaign077 v2 audit error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign077NoReturnAuditV2Error(f"{label} changed: {path}")


def _legacy_verifier_module() -> Any:
    return v1.c76_audit.c75_v5.v4.v3


def load_repair_protocol() -> dict[str, Any]:
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "v2 repair protocol")
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "v1 failure record")
    _require(Path(v1.__file__).resolve(), BASE_V1_SHA256, "v1 audit runner")
    spec = json.loads(REPAIR_PROTOCOL.read_text(encoding="utf-8"))
    sole = spec.get("sole_repair") or {}
    retry = spec.get("retry") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign077_no_return_runtime_compatibility_repair_protocol"
        and spec.get("status")
        == "frozen_after_v1_runtime_failure_before_full_retry"
        and all(
            sole.get(key) is True
            for key in (
                "legacy_snapshot_manifest_hashes_still_required",
                "legacy_partition_byte_hashes_still_required",
                "legacy_partition_row_counts_still_required",
                "legacy_partition_schemas_still_required",
                "legacy_factor_value_semantics_still_required",
                "legacy_dataset_digest_still_required",
                "runtime_sensitive_output_frame_hash_recomputation_remains_skipped",
            )
        )
        and all(
            sole.get(key) is False
            for key in (
                "candidate_formula_changed",
                "candidate_snapshot_or_manifest_changed",
                "coverage_gate_changed",
                "comparison_library_or_order_changed",
                "uniqueness_threshold_changed",
                "historical_daily_price_or_return_field_changed",
                "development_or_stress_rule_changed",
                "provider_or_candidate49_workflow_changed",
            )
        )
        and retry.get("partial_statistics_reused") is False
        and retry.get("restart_from_candidate_snapshot_verification_and_coverage") is True
        and retry.get("expected_audit_count_before_retry") == 0
        and retry.get("maximum_authorized_v2_retries") == 1
    ):
        raise Campaign077NoReturnAuditV2Error("v2 repair protocol semantics changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign077NoReturnAuditV2Error("v2 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign077_no_return_audit_implementation_freeze"
        and record.get("version") == 2
        and record.get("status")
        == "frozen_before_full_retry_with_runtime_version_gate_only_repair"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v2_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("partial_statistics_reused") is False
        and record.get("candidate_snapshot_or_manifest_rewritten") is False
        and record.get("historical_daily_price_fields_read_before_retry") == []
        and record.get("historical_forward_returns_read_before_retry") is False
    ):
        raise Campaign077NoReturnAuditV2Error("v2 implementation freeze changed")
    return record


@contextmanager
def _temporary_runtime_version_binding() -> Iterator[None]:
    module = _legacy_verifier_module()
    if (
        module.PANDAS_VERSION != LEGACY_PANDAS_VERSION
        or module.PYARROW_VERSION != LEGACY_PYARROW_VERSION
    ):
        raise Campaign077NoReturnAuditV2Error("legacy verifier constants changed")
    if (
        module.pd.__version__ != CURRENT_PANDAS_VERSION
        or module.pyarrow.__version__ != CURRENT_PYARROW_VERSION
    ):
        raise Campaign077NoReturnAuditV2Error("current runtime changed")
    original_pandas = module.PANDAS_VERSION
    original_pyarrow = module.PYARROW_VERSION
    module.PANDAS_VERSION = CURRENT_PANDAS_VERSION
    module.PYARROW_VERSION = CURRENT_PYARROW_VERSION
    try:
        yield
    finally:
        module.PANDAS_VERSION = original_pandas
        module.PYARROW_VERSION = original_pyarrow


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    load_repair_protocol()
    _load_implementation_freeze()
    if v1.status(experiment_root).get("audit_count") != 0:
        raise Campaign077NoReturnAuditV2Error("v2 retry requires zero published audits")
    with _temporary_runtime_version_binding():
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
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
