#!/usr/bin/env python3
"""Retry Campaign075 with one frozen Campaign068 frame-hash compatibility repair."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from scripts import a_share_three_day_walkforward_campaign068_features_v2 as c68
from scripts import a_share_three_day_walkforward_campaign075_no_return_audit as v1


REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_no_return_runtime_compatibility_repair_protocol_v2_20260806.json"
)
REPAIR_PROTOCOL_SHA256 = "f23b997e6cccfc8a45b84afba82a9e5ce75c0242e34808c24206fd434ed50286"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_no_return_campaign068_frame_replay_failure_20260806.json"
)
FAILURE_RECORD_SHA256 = "8faab72c855df13c9472bf173936b6f03e910607335dc54b161ecde4f7ccec04"
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_no_return_audit_implementation_freeze_v2_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign075_no_return_audit_v2.py"
)
C68_MANIFEST_PATH = c68.output_root(c68.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C68_MANIFEST_SHA256 = "9878e6c0249cb9e965dbfade2ce2b3a355bed5e6a46bf68667c82fc568672004"
C68_DATASET_SHA256 = "bcd03a5e2122b64b072985b3a9a9ada880cad337dae4766a00cf52bf51f4f449"
C68_ELIGIBLE_ROWS = 6_317_276
PANDAS_VERSION = "2.2.3"
PYARROW_VERSION = "25.0.0"


class Campaign075NoReturnAuditV2Error(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign075NoReturnAuditV2Error(f"{label} changed: {path}")


def load_repair_protocol() -> dict[str, Any]:
    for path, expected, label in (
        (REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "repair protocol"),
        (FAILURE_RECORD, FAILURE_RECORD_SHA256, "failure record"),
        (Path(v1.__file__).resolve(), "477053429b81aaffb1d454984ad2163936c4546e9c5b5fc9b05f011b84ef5295", "v1 audit runner"),
        (v1.AUDIT_IMPLEMENTATION_FREEZE, "1e7b37cd42b7c2c80b1f11bec531cee402f62fcd7ca67026477519561e1bcd6b", "v1 audit freeze"),
        (v1.AUDIT_ACTIVATION_BINDING, "774c7706762aa2459e46d46987913e8446f40da3aa7771cc6359021ecdca2ad4", "v1 activation"),
        (Path(c68.__file__).resolve(), "c4facbb4c76f99de64f5322ed106736c10f95acd2177cbfc294b82c2710f477d", "Campaign068 verifier"),
        (C68_MANIFEST_PATH, C68_MANIFEST_SHA256, "Campaign068 manifest"),
    ):
        _require(path, expected, label)
    spec = json.loads(REPAIR_PROTOCOL.read_text(encoding="utf-8"))
    sole = spec.get("sole_repair") or {}
    unchanged = spec.get("unchanged_research_semantics") or {}
    if not (
        spec.get("version") == 2
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign075_no_return_runtime_compatibility_repair_protocol"
        and spec.get("status")
        == "frozen_after_infrastructure_failure_before_full_audit_retry"
        and sole.get("only_removed_check")
        == "recompute each stored output_frame_sha256 with the current pandas/pyarrow Arrow IPC serializer"
        and sole.get("campaign068_snapshot_files_may_be_rewritten") is False
        and sole.get("partial_statistics_may_be_reused") is False
        and sole.get("full_campaign075_audit_must_restart_from_coverage") is True
        and all(unchanged.values())
    ):
        raise Campaign075NoReturnAuditV2Error("repair protocol semantics changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign075NoReturnAuditV2Error("v2 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign075_no_return_audit_implementation_freeze"
        and record.get("version") == 2
        and record.get("status")
        == "frozen_before_full_retry_after_runtime_compatibility_failure"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v2_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("partial_coverage_or_comparison_statistics_reused") is False
        and record.get("historical_daily_price_fields_read_before_retry") == []
        and record.get("historical_forward_returns_read_before_retry") is False
    ):
        raise Campaign075NoReturnAuditV2Error("v2 implementation freeze changed")
    return record


def _verify_partition(
    item: dict[str, Any], *, partition_root: Path
) -> tuple[int, int]:
    path = Path(str(item["path"])).expanduser().resolve()
    try:
        path.relative_to(partition_root.resolve())
    except ValueError as exc:
        raise Campaign075NoReturnAuditV2Error(
            "Campaign068 partition escaped output root"
        ) from exc
    if _sha256(path) != item["output_byte_sha256"]:
        raise Campaign075NoReturnAuditV2Error(
            f"Campaign068 partition byte hash changed: {path}"
        )
    if pq.ParquetFile(path).metadata.num_rows != int(item["rows"]):
        raise Campaign075NoReturnAuditV2Error(
            f"Campaign068 partition row count changed: {path}"
        )
    frame = pd.read_parquet(path)
    if tuple(frame.columns) != c68.v1.OUTPUT_COLUMNS:
        raise Campaign075NoReturnAuditV2Error(
            f"Campaign068 partition schema changed: {path}"
        )
    return c68.validate_value_semantics(frame)


def verify_campaign068_snapshot_compatibly(
    manifest_path: Path, *, workers: int = 4
) -> dict[str, Any]:
    load_repair_protocol()
    _load_implementation_freeze()
    if pd.__version__ != PANDAS_VERSION:
        raise Campaign075NoReturnAuditV2Error("pandas runtime changed")
    import pyarrow

    if pyarrow.__version__ != PYARROW_VERSION:
        raise Campaign075NoReturnAuditV2Error("pyarrow runtime changed")
    manifest_path = manifest_path.expanduser().resolve()
    if manifest_path != C68_MANIFEST_PATH.resolve():
        raise Campaign075NoReturnAuditV2Error("Campaign068 manifest path changed")
    _require(manifest_path, C68_MANIFEST_SHA256, "Campaign068 manifest")
    c68.load_repair_protocol()
    c68._load_implementation_freeze()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    c68.v1._runtime["_validate_manifest"](manifest)
    files = list(manifest.get("files") or [])
    if not (
        manifest.get("dataset_sha256") == C68_DATASET_SHA256
        and manifest.get("partitions") == c68.v1.EXPECTED_PARTITIONS
        and manifest.get("rows") == c68.v1.EXPECTED_ROWS
        and len(files) == c68.v1.EXPECTED_PARTITIONS
        and (manifest.get("factor_eligible_rows") or {}).get(c68.v1.FACTOR_NAME)
        == C68_ELIGIBLE_ROWS
    ):
        raise Campaign075NoReturnAuditV2Error("Campaign068 aggregate semantics changed")
    partition_root = (manifest_path.parent / "partitions").resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        totals = list(
            pool.map(
                lambda item: _verify_partition(item, partition_root=partition_root),
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
    if not (
        c68.v1._runtime["_json_digest"](digest_rows) == C68_DATASET_SHA256
        and sum(value[0] for value in totals) == c68.v1.EXPECTED_ROWS
        and sum(value[1] for value in totals) == C68_ELIGIBLE_ROWS
    ):
        raise Campaign075NoReturnAuditV2Error("Campaign068 compatibility totals changed")
    return {
        "status": "verified_with_frozen_runtime_compatibility_repair",
        "repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "manifest_sha256": C68_MANIFEST_SHA256,
        "dataset_sha256": C68_DATASET_SHA256,
        "partitions": len(totals),
        "rows": sum(value[0] for value in totals),
        "eligible_rows": sum(value[1] for value in totals),
        "all_partition_byte_hashes_passed": True,
        "all_partition_row_schema_and_value_semantics_passed": True,
        "runtime_sensitive_frame_hash_recomputation_skipped": True,
        "stored_frame_hashes_and_manifest_dataset_digest_preserved": True,
        "comparison_values_read_only_after_campaign075_coverage_pass": True,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    load_repair_protocol()
    _load_implementation_freeze()
    target_module = v1.base.base.c68
    original = target_module.verify_snapshot_files
    try:
        target_module.verify_snapshot_files = verify_campaign068_snapshot_compatibly
        return v1.run_no_return_audit(
            data_root=data_root,
            experiment_root=experiment_root,
            workers=workers,
        )
    finally:
        target_module.verify_snapshot_files = original


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=v1.DEFAULT_DATA_ROOT)
    parser.add_argument("--experiment-root", type=Path, default=v1.DEFAULT_EXPERIMENT_ROOT)
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
