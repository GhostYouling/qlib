#!/usr/bin/env python3
"""Retry Campaign083 with a frozen cross-runtime frame-hash verifier repair."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign083_no_return_audit as v1
from scripts import a_share_three_day_walkforward_campaign083_no_return_audit_v2 as v2

REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_083_no_return_snapshot_frame_compatibility_repair_protocol_v3_20260806.json"
)
REPAIR_PROTOCOL_SHA256 = (
    "3f20b8e7fb2625031868c5ddae93ede63fad6950100612b4063d495b11604aa2"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_083_v2_pre_retry_snapshot_frame_hash_failure_20260806.json"
)
FAILURE_RECORD_SHA256 = (
    "bcff3a9f3b4d7c6d1c77fd77e9c971ba46edb31ffa3c174b5b5cf105fdf825e5"
)
BASE_V1_SHA256 = v2.BASE_V1_SHA256
BASE_V2_SHA256 = "6cc05dd63a16d4f5449fcca31e2efbb3c6d60803e5cb21640fbef1faa90b43a7"
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_083_no_return_audit_implementation_freeze_v3_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign083_no_return_audit_v3.py"
)
candidate = v1.candidate


class Campaign083NoReturnAuditV3Error(RuntimeError):
    """Fail-closed Campaign083 v3 snapshot-compatibility error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign083NoReturnAuditV3Error(f"{label} changed: {path}")


def load_repair_protocol() -> dict[str, Any]:
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "v3 repair protocol")
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "v2 failure record")
    _require(Path(v1.__file__).resolve(), BASE_V1_SHA256, "v1 audit runner")
    _require(Path(v2.__file__).resolve(), BASE_V2_SHA256, "v2 audit runner")
    spec = json.loads(REPAIR_PROTOCOL.read_text(encoding="utf-8"))
    sole = spec.get("sole_compatibility_repair") or {}
    retry = spec.get("retry") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign083_no_return_snapshot_frame_compatibility_repair_protocol"
        and spec.get("status")
        == "frozen_after_v2_pre_retry_frame_hash_failure_before_full_v3_retry"
        and all(
            sole.get(key) is True
            for key in (
                "candidate_manifest_byte_hash_still_required",
                "candidate_manifest_dataset_digest_still_required",
                "every_partition_path_containment_still_required",
                "every_partition_byte_hash_still_required",
                "every_partition_row_count_still_required",
                "every_partition_exact_schema_still_required",
                "every_partition_frozen_factor_value_semantics_still_required",
                "aggregate_partition_row_and_eligible_counts_still_required",
                "stored_dataset_digest_recomputed_from_stored_partition_receipts_still_required",
                "runtime_sensitive_output_frame_hash_recomputation_skipped",
            )
        )
        and all(
            sole.get(key) is False
            for key in (
                "candidate_snapshot_or_manifest_rewrite_allowed",
                "original_legacy_runtime_gate_suppression_allowed",
                "prior_comparator_verifier_change_allowed",
                "candidate_formula_direction_coverage_gate_comparator_order_or_threshold_change_allowed",
                "historical_daily_price_return_development_stress_provider_or_candidate49_change_allowed",
            )
        )
        and retry.get("partial_statistics_reused") is False
        and retry.get("v2_full_retry_entered") is False
        and retry.get(
            "restart_from_static_bindings_candidate_snapshot_compatibility_verification_and_coverage"
        )
        is True
        and retry.get("expected_published_audit_count_before_retry") == 0
        and retry.get("maximum_authorized_v3_retries") == 1
    ):
        raise Campaign083NoReturnAuditV3Error("v3 repair protocol semantics changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign083NoReturnAuditV3Error("v3 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign083_no_return_audit_implementation_freeze"
        and record.get("version") == 3
        and record.get("status")
        == "frozen_before_full_retry_with_candidate_frame_hash_compatibility_only_repair"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v3_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("partial_statistics_reused") is False
        and record.get("candidate_snapshot_or_manifest_rewritten") is False
        and record.get("original_legacy_runtime_gate_suppressed") is False
        and record.get("prior_comparator_verifier_changed") is False
        and record.get("historical_daily_price_fields_read_before_retry") == []
        and record.get("historical_forward_returns_read_before_retry") is False
    ):
        raise Campaign083NoReturnAuditV3Error("v3 implementation freeze changed")
    return record


def _verify_partition_compatible(
    item: dict[str, Any], *, partition_root: Path
) -> tuple[int, int]:
    path = Path(str(item["path"])).expanduser().resolve()
    try:
        path.relative_to(partition_root)
    except ValueError as exc:
        raise Campaign083NoReturnAuditV3Error(
            f"partition escaped frozen root: {path}"
        ) from exc
    if _sha256(path) != item.get("output_byte_sha256"):
        raise Campaign083NoReturnAuditV3Error(f"partition byte hash changed: {path}")
    frame = pd.read_parquet(path)
    if len(frame) != item.get("rows"):
        raise Campaign083NoReturnAuditV3Error(f"partition rows changed: {path}")
    try:
        return candidate.validate_value_semantics(frame)
    except candidate.Campaign083FeatureError as exc:
        raise Campaign083NoReturnAuditV3Error(
            f"partition value semantics changed: {path}"
        ) from exc


def verify_candidate_snapshot_compatible(
    manifest_path: Path, *, workers: int = 4
) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = v1.SNAPSHOT_MANIFEST_PATH.resolve()
    if manifest_path != expected:
        raise Campaign083NoReturnAuditV3Error("candidate manifest path changed")
    _require(manifest_path, v1.SNAPSHOT_MANIFEST_SHA256, "candidate manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidate._validate_manifest(manifest)
    files = list(manifest.get("files") or [])
    partition_root = (manifest_path.parent / "partitions").resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        verified = list(
            pool.map(
                lambda item: _verify_partition_compatible(
                    item, partition_root=partition_root
                ),
                files,
            )
        )
    digest_rows = [
        [
            item["relative_path"],
            item["output_byte_sha256"],
            item["output_frame_sha256"],
            item["rows"],
        ]
        for item in files
    ]
    rows = sum(row_count for row_count, _eligible in verified)
    eligible = sum(count for _rows, count in verified)
    if not (
        len(files) == v1.EXPECTED_PARTITIONS
        and len(verified) == v1.EXPECTED_PARTITIONS
        and rows == v1.EXPECTED_ROWS
        and eligible == v1.EXPECTED_ELIGIBLE_ROWS
        and candidate._json_digest(digest_rows) == v1.SNAPSHOT_DATASET_SHA256
        and manifest.get("dataset_sha256") == v1.SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign083NoReturnAuditV3Error(
            "candidate aggregate compatibility identity changed"
        )
    return {
        "status": "verified",
        "partitions": len(verified),
        "rows": rows,
        "eligible_rows": eligible,
        "dataset_sha256": manifest["dataset_sha256"],
        "partition_byte_hash_row_schema_and_value_semantics_verified": True,
        "output_frame_hash_recomputation_skipped_runtime_compatibility_only": True,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


@contextmanager
def _temporary_candidate_verifier_binding() -> Iterator[None]:
    original = v1.candidate.verify_snapshot_files
    if original is not candidate.verify_snapshot_files:
        raise Campaign083NoReturnAuditV3Error("candidate verifier binding changed")
    v1.candidate.verify_snapshot_files = verify_candidate_snapshot_compatible
    try:
        yield
    finally:
        v1.candidate.verify_snapshot_files = original


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    load_repair_protocol()
    _load_implementation_freeze()
    v2.load_repair_protocol()
    v2._load_implementation_freeze()
    v2.require_exact_runtime()
    if v1.status(experiment_root).get("audit_count") != 0:
        raise Campaign083NoReturnAuditV3Error(
            "v3 retry requires zero published Campaign083 audits"
        )
    with _temporary_candidate_verifier_binding():
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
        "snapshot_frame_compatibility_repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "runtime_versions": v2.runtime_versions(),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
