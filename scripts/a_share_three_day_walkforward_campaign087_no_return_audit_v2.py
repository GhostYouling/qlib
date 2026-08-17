#!/usr/bin/env python3
"""Run Campaign087's additive compact-comparator append repair."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign087_no_return_audit as v1

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = v1.DEFAULT_EXPERIMENT_ROOT
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_no_return_audit_v2_compact_append_repair_protocol_20260807.json"
)
REPAIR_PROTOCOL_SHA256 = (
    "8d6fe0a178264c62ef51878e993be8cc6bca3bb76846be3036838e1f680e6aa0"
)
V1_RUNNER_SHA256 = (
    "7512b21d30ad301faaa8f89d0d828e409a61ab357fee0400632ec5d55e210fef"
)
V1_FREEZE_SHA256 = (
    "f4d4b9cfb4835fdef2c67839f3cabb96a752d1c226210b181a731cea28d6276d"
)
V1_ACTIVATION_SHA256 = (
    "8b170f9e0b447a36c78ab1807b9b6fdecd7c34c0ff09588522f87264637cec11"
)
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_no_return_audit_implementation_freeze_v2_20260807.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_no_return_audit_activation_binding_v2_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign087_no_return_audit_v2.py"
)
C85_AUDIT = v1.c86_audit.c85_audit
C85_MANIFEST_PATH = v1.c86_audit.C85_SNAPSHOT_MANIFEST_PATH
C85_MANIFEST_SHA256 = (
    "fb8ea4bdb2b2f783a8c1d4e020f1dcdfca1697c779c732e50233fe7b040b4d28"
)
C85_FACTOR_NAME = C85_AUDIT.candidate.FACTOR_NAME
C86_MANIFEST_PATH = v1.C86_SNAPSHOT_MANIFEST_PATH
C86_MANIFEST_SHA256 = v1.c86_audit.SNAPSHOT_MANIFEST_SHA256
C86_FACTOR_NAME = v1.c86_audit.FACTOR_NAME


class Campaign087NoReturnAuditV2Error(RuntimeError):
    """Fail-closed Campaign087 no-return audit v2 error."""


def _sha256(path: Path) -> str:
    return v1._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign087NoReturnAuditV2Error(f"Campaign087 v2 {label} changed: {path}")


def _load_implementation_freeze() -> dict[str, Any]:
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "repair protocol")
    _require(Path(v1.__file__).resolve(), V1_RUNNER_SHA256, "v1 audit runner")
    _require(v1.AUDIT_IMPLEMENTATION_FREEZE, V1_FREEZE_SHA256, "v1 audit freeze")
    _require(v1.AUDIT_ACTIVATION_BINDING, V1_ACTIVATION_SHA256, "v1 activation")
    _require(C85_MANIFEST_PATH, C85_MANIFEST_SHA256, "C85 compact manifest")
    _require(C86_MANIFEST_PATH, C86_MANIFEST_SHA256, "C86 compact manifest")
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign087NoReturnAuditV2Error("Campaign087 audit v2 freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign087_no_return_audit_implementation_freeze_v2"
        and record.get("status")
        == "compact_append_repair_frozen_before_campaign087_v2_coverage_or_comparison_values"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v1_implementation_freeze") or {}).get("sha256")
        == V1_FREEZE_SHA256
        and (record.get("v2_audit_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v2_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("coverage_or_capacity_metrics_computed_before_v2_freeze")
        is False
        and record.get("comparison_values_read_before_v2_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_v2_freeze"
        )
        is False
        and record.get("provider_request_issued_before_v2_freeze") is False
    ):
        raise Campaign087NoReturnAuditV2Error("Campaign087 audit v2 freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign087NoReturnAuditV2Error("Campaign087 audit v2 activation absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign087_no_return_audit_activation_binding_v2"
        and record.get("status")
        == "compact_append_repair_frozen_before_campaign087_v2_coverage_or_comparison_values"
        and (record.get("implementation_freeze") or {}).get("sha256")
        == _sha256(AUDIT_IMPLEMENTATION_FREEZE)
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("candidate_snapshot") or {}).get("sha256")
        == v1.SNAPSHOT_MANIFEST_SHA256
        and record.get("coverage_or_capacity_metrics_computed_before_activation")
        is False
        and record.get("comparison_values_read_before_activation") is False
        and record.get("historical_daily_price_or_forward_return_values_read_before_activation")
        is False
        and record.get("provider_request_issued_before_activation") is False
    ):
        raise Campaign087NoReturnAuditV2Error("Campaign087 audit v2 activation changed")
    return record


def _compact_snapshot_comparison(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    factor: str,
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    gate: dict[str, Any],
    comparison_engine: Any,
    verifier: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require(manifest_path, expected_manifest_sha256, f"{factor} manifest")
    verification = verifier()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    keys: list[np.ndarray] = []
    values: list[np.ndarray] = []
    years: list[int] = []
    for record in manifest.get("files") or []:
        years.append(int(record["year"]))
        frame = pd.read_parquet(
            manifest_path.parent / str(record["path"]),
            columns=["stock_day_key", factor],
        )
        keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
        values.append(frame[factor].to_numpy(dtype=np.float64))
    all_keys = np.concatenate(keys)
    all_values = np.concatenate(values)
    if not (
        years == list(range(2019, 2026))
        and len(all_keys) == v1.EXPECTED_ROWS
        and all_values.shape == all_keys.shape
        and len(np.unique(all_keys)) == len(all_keys)
        and np.all(all_keys[1:] > all_keys[:-1])
    ):
        raise Campaign087NoReturnAuditV2Error(f"{factor} compact arrays changed")
    positions = np.searchsorted(all_keys, candidate_keys, side="left")
    if not (
        np.all(positions < len(all_keys))
        and np.array_equal(all_keys[positions], candidate_keys)
    ):
        raise Campaign087NoReturnAuditV2Error(f"{factor} misses candidate keys")
    result = comparison_engine._aligned_comparison_result(
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        comparison_values=all_values[positions],
        comparison=factor,
        direction="higher",
        gate=gate,
    )
    del all_keys, all_values, positions
    gc.collect()
    receipt = {
        **verification,
        "loader": "frozen_seven_partition_stock_day_key_direct_alignment",
        "manifest_sha256": expected_manifest_sha256,
        "factor": factor,
        "rows": v1.EXPECTED_ROWS,
        "partitions": 7,
    }
    return result, receipt


def _load_comparisons_after_coverage(
    *,
    coverage: dict[str, Any],
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    gate: dict[str, Any],
    engine: Any,
    comparison_engine: Any,
    workers: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    comparisons, receipts = C85_AUDIT._load_comparisons_after_coverage(
        coverage=coverage,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        engine=engine,
        comparison_engine=comparison_engine,
        workers=workers,
    )
    if len(comparisons) != 114:
        raise Campaign087NoReturnAuditV2Error("first 114 comparison order changed")
    c85_result, c85_receipt = _compact_snapshot_comparison(
        manifest_path=C85_MANIFEST_PATH,
        expected_manifest_sha256=C85_MANIFEST_SHA256,
        factor=C85_FACTOR_NAME,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        comparison_engine=comparison_engine,
        verifier=C85_AUDIT.verify_candidate_snapshot,
    )
    comparisons.append(c85_result)
    receipts["campaign085_compact_snapshot"] = c85_receipt
    c86_result, c86_receipt = _compact_snapshot_comparison(
        manifest_path=C86_MANIFEST_PATH,
        expected_manifest_sha256=C86_MANIFEST_SHA256,
        factor=C86_FACTOR_NAME,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        comparison_engine=comparison_engine,
        verifier=v1.c86_audit.verify_candidate_snapshot,
    )
    comparisons.append(c86_result)
    receipts["campaign086_compact_snapshot"] = c86_receipt
    receipts.pop("all_114_sources_loaded_in_frozen_order", None)
    receipts["all_116_sources_loaded_in_frozen_order"] = True
    if not (
        len(comparisons) == v1.EXPECTED_COMPARISON_COUNT
        and comparisons[-2]["comparison_factor"] == C85_FACTOR_NAME
        and comparisons[-1]["comparison_factor"] == C86_FACTOR_NAME
    ):
        raise Campaign087NoReturnAuditV2Error("Campaign087 v2 comparison order changed")
    return comparisons, receipts


def _run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int, confirm_run: bool
) -> Path:
    if not confirm_run:
        raise Campaign087NoReturnAuditV2Error("Campaign087 audit v2 requires --confirm-run")
    activation = _load_activation_binding()
    original_loader = v1._load_comparisons_after_coverage
    v1._load_comparisons_after_coverage = _load_comparisons_after_coverage
    try:
        path = v1._run_no_return_audit(
            data_root=data_root,
            experiment_root=experiment_root,
            workers=workers,
            confirm_run=True,
        )
    finally:
        v1._load_comparisons_after_coverage = original_loader
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["audit_runtime_repair"] = {
        "scope": "direct compact stock_day_key append for frozen comparisons 115 and 116",
        "repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "v2_implementation_freeze_sha256": _sha256(AUDIT_IMPLEMENTATION_FREEZE),
        "v2_activation_binding_sha256": _sha256(AUDIT_ACTIVATION_BINDING),
        "v1_failure_record_sha256": (
            activation.get("v1_failure_record") or {}
        ).get("sha256"),
        "first_114_loader_changed": False,
        "C85_compact_loader_used": True,
        "C86_compact_loader_used": True,
        "comparison_order_or_gate_changed": False,
    }
    v1.definitions.c85._atomic_json(payload, path)
    return path


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    return {
        "status": (
            "ready_for_single_v2_audit"
            if AUDIT_ACTIVATION_BINDING.is_file()
            else "v2_activation_binding_absent"
        ),
        "audit_count": len(
            list(
                experiment_root.expanduser()
                .resolve()
                .glob("*_campaign087_no_return_audit.json")
            )
        ),
        "coverage_or_capacity_metrics_computed_by_status": False,
        "comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
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
