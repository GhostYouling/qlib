#!/usr/bin/env python3
"""Retry Campaign075 with the finite Campaign068-Campaign074 verifier repair."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import pyarrow
import pyarrow.parquet as pq

from scripts import a_share_three_day_walkforward_campaign068_features_v2 as c68
from scripts import a_share_three_day_walkforward_campaign069_features as c69
from scripts import a_share_three_day_walkforward_campaign070_features as c70
from scripts import a_share_three_day_walkforward_campaign071_features as c71
from scripts import a_share_three_day_walkforward_campaign072_features as c72
from scripts import a_share_three_day_walkforward_campaign073_features as c73
from scripts import a_share_three_day_walkforward_campaign074_features as c74
from scripts import a_share_three_day_walkforward_campaign075_no_return_audit as v1


REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_no_return_runtime_compatibility_repair_protocol_v3_20260806.json"
)
REPAIR_PROTOCOL_SHA256 = "927b86a173f2789a20261a101a1fff43605d05cab8d2755a20076e1e0b51bedd"
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_no_return_audit_implementation_freeze_v3_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign075_no_return_audit_v3.py"
)
PANDAS_VERSION = "2.2.3"
PYARROW_VERSION = "25.0.0"


class Campaign075NoReturnAuditV3Error(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign075NoReturnAuditV3Error(f"{label} changed: {path}")


def load_repair_protocol() -> dict[str, Any]:
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "v3 repair protocol")
    spec = json.loads(REPAIR_PROTOCOL.read_text(encoding="utf-8"))
    snapshots = list(spec.get("finite_compatibility_snapshot_list") or [])
    checks = spec.get("compatibility_verification_for_every_listed_snapshot") or {}
    retry = spec.get("retry_semantics") or {}
    if not (
        spec.get("version") == 3
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign075_no_return_runtime_compatibility_repair_protocol"
        and spec.get("status")
        == "frozen_after_bounded_campaign068_to_campaign074_compatibility_scout_before_full_retry"
        and [int(item["campaign"]) for item in snapshots]
        == [68, 69, 70, 71, 72, 73, 74]
        and checks.get("only_omitted_check")
        == "current-runtime recomputation of stored Arrow IPC output_frame_sha256"
        and checks.get("stored_output_frame_sha256_values_removed_or_rewritten")
        is False
        and checks.get("snapshot_or_manifest_files_may_be_rewritten") is False
        and retry.get("partial_statistics_reused") is False
        and retry.get("full_audit_restarts_from_candidate_snapshot_and_coverage")
        is True
    ):
        raise Campaign075NoReturnAuditV3Error("v3 repair protocol semantics changed")
    for item in snapshots:
        _require(
            REPO_ROOT / str(item["feature_runner_path"]),
            str(item["feature_runner_sha256"]),
            f"Campaign{int(item['campaign']):03d} feature runner",
        )
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign075NoReturnAuditV3Error("v3 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign075_no_return_audit_implementation_freeze"
        and record.get("version") == 3
        and record.get("status")
        == "frozen_before_full_retry_with_finite_campaign068_to_campaign074_adapter"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v3_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("partial_statistics_reused") is False
        and record.get("snapshot_files_rewritten") is False
        and record.get("historical_daily_price_fields_read_before_retry") == []
        and record.get("historical_forward_returns_read_before_retry") is False
    ):
        raise Campaign075NoReturnAuditV3Error("v3 implementation freeze changed")
    return record


def _source_validate(module: Any, campaign: int) -> None:
    if campaign == 68:
        module.load_repair_protocol()
        module._load_implementation_freeze()
    else:
        module.load_protocol()
        if hasattr(module, "_validate_implementation_freeze"):
            module._validate_implementation_freeze()


def _manifest_validate(module: Any, manifest: dict[str, Any], campaign: int) -> None:
    if campaign == 68:
        module.v1._runtime["_validate_manifest"](manifest)
    elif campaign in {69, 70, 71, 72}:
        module._runtime["_validate_manifest"](manifest)
    else:
        module._validate_manifest(manifest)


def _output_columns(module: Any, campaign: int) -> tuple[str, ...]:
    return tuple(module.v1.OUTPUT_COLUMNS if campaign == 68 else module.OUTPUT_COLUMNS)


def _expected_rows(module: Any, campaign: int) -> tuple[int, int]:
    source = module.v1 if campaign == 68 else module
    return int(source.EXPECTED_ROWS), int(source.EXPECTED_PARTITIONS)


def _factor_name(module: Any, campaign: int) -> str:
    return str(module.v1.FACTOR_NAME if campaign == 68 else module.FACTOR_NAME)


def _dataset_digest(module: Any, campaign: int, rows: list[list[Any]]) -> str:
    if campaign == 68:
        return str(module.v1._runtime["_json_digest"](rows))
    if campaign in {69, 70, 71, 72}:
        return str(module._runtime["_json_digest"](rows))
    return str(module._json_digest(rows))


def _verify_partition(
    item: dict[str, Any],
    *,
    partition_root: Path,
    output_columns: tuple[str, ...],
    validate_values: Callable[[pd.DataFrame], tuple[int, int]],
) -> tuple[int, int]:
    path = Path(str(item["path"])).expanduser().resolve()
    try:
        path.relative_to(partition_root.resolve())
    except ValueError as exc:
        raise Campaign075NoReturnAuditV3Error("partition escaped frozen root") from exc
    if _sha256(path) != item["output_byte_sha256"]:
        raise Campaign075NoReturnAuditV3Error(f"partition byte hash changed: {path}")
    if pq.ParquetFile(path).metadata.num_rows != int(item["rows"]):
        raise Campaign075NoReturnAuditV3Error(f"partition row count changed: {path}")
    frame = pd.read_parquet(path)
    if tuple(frame.columns) != output_columns:
        raise Campaign075NoReturnAuditV3Error(f"partition schema changed: {path}")
    return validate_values(frame)


def _snapshot_configs() -> dict[int, dict[str, Any]]:
    modules = {68: c68, 69: c69, 70: c70, 71: c71, 72: c72, 73: c73, 74: c74}
    spec = load_repair_protocol()
    result: dict[int, dict[str, Any]] = {}
    for item in spec["finite_compatibility_snapshot_list"]:
        campaign = int(item["campaign"])
        module = modules[campaign]
        manifest_path = module.output_root(module.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
        result[campaign] = {
            "module": module,
            "manifest_path": manifest_path.resolve(),
            "manifest_sha256": str(item["manifest_sha256"]),
            "dataset_sha256": str(item["dataset_sha256"]),
            "factor": str(item["factor"]),
            "eligible_rows": int(item["eligible_rows"]),
        }
    return result


def verify_snapshot_compatibly(
    campaign: int, manifest_path: Path, *, workers: int = 4
) -> dict[str, Any]:
    _load_implementation_freeze()
    if pd.__version__ != PANDAS_VERSION or pyarrow.__version__ != PYARROW_VERSION:
        raise Campaign075NoReturnAuditV3Error("frozen pandas/pyarrow runtime changed")
    config = _snapshot_configs()[int(campaign)]
    module = config["module"]
    manifest_path = manifest_path.expanduser().resolve()
    if manifest_path != config["manifest_path"]:
        raise Campaign075NoReturnAuditV3Error(f"Campaign{campaign:03d} manifest path changed")
    _require(manifest_path, config["manifest_sha256"], f"Campaign{campaign:03d} manifest")
    _source_validate(module, campaign)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _manifest_validate(module, manifest, campaign)
    expected_rows, expected_partitions = _expected_rows(module, campaign)
    factor = _factor_name(module, campaign)
    files = list(manifest.get("files") or [])
    if not (
        factor == config["factor"]
        and manifest.get("dataset_sha256") == config["dataset_sha256"]
        and manifest.get("factor_names") == [factor]
        and manifest.get("rows") == expected_rows
        and manifest.get("partitions") == expected_partitions
        and len(files) == expected_partitions
        and (manifest.get("factor_eligible_rows") or {}).get(factor)
        == config["eligible_rows"]
    ):
        raise Campaign075NoReturnAuditV3Error(
            f"Campaign{campaign:03d} aggregate semantics changed"
        )
    partition_root = (manifest_path.parent / "partitions").resolve()
    validate_values = module.validate_value_semantics
    output_columns = _output_columns(module, campaign)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        totals = list(
            pool.map(
                lambda item: _verify_partition(
                    item,
                    partition_root=partition_root,
                    output_columns=output_columns,
                    validate_values=validate_values,
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
    if not (
        _dataset_digest(module, campaign, digest_rows) == config["dataset_sha256"]
        and sum(value[0] for value in totals) == expected_rows
        and sum(value[1] for value in totals) == config["eligible_rows"]
    ):
        raise Campaign075NoReturnAuditV3Error(
            f"Campaign{campaign:03d} compatibility totals changed"
        )
    return {
        "status": "verified_with_frozen_runtime_compatibility_repair",
        "campaign": campaign,
        "repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "manifest_sha256": config["manifest_sha256"],
        "dataset_sha256": config["dataset_sha256"],
        "partitions": len(totals),
        "rows": sum(value[0] for value in totals),
        "eligible_rows": sum(value[1] for value in totals),
        "all_partition_byte_hashes_passed": True,
        "all_partition_row_schema_and_value_semantics_passed": True,
        "runtime_sensitive_frame_hash_recomputation_skipped": True,
        "stored_frame_hashes_and_manifest_dataset_digest_preserved": True,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def _verifier(campaign: int) -> Callable[..., dict[str, Any]]:
    def verify(manifest_path: Path, *, workers: int = 4) -> dict[str, Any]:
        return verify_snapshot_compatibly(campaign, manifest_path, workers=workers)

    return verify


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    load_repair_protocol()
    _load_implementation_freeze()
    targets = [
        (v1.base.base.c68, 68),
        (v1.base.base.c69, 69),
        (v1.base.base.c70, 70),
        (v1.base.base.c71, 71),
        (v1.base.base.c72, 72),
        (v1.base.c73, 73),
        (v1.c74_features, 74),
    ]
    originals = [(module, module.verify_snapshot_files) for module, _ in targets]
    try:
        for module, campaign in targets:
            module.verify_snapshot_files = _verifier(campaign)
        return v1.run_no_return_audit(
            data_root=data_root,
            experiment_root=experiment_root,
            workers=workers,
        )
    finally:
        for module, original in originals:
            module.verify_snapshot_files = original


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
