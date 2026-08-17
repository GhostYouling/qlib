#!/usr/bin/env python3
"""Independent whole-snapshot verifier for Campaign151's zero coverage.

The metadata-only ``plan`` opens no candidate partition or benchmark payload.
The confirmed ``verify`` checks every immutable partition byte/frame, key and
value semantic, recomputes the dataset digest, and verifies the peer benchmark
grid responsible for the preregistered all-row rejection.  It never reads a
comparison factor, daily price, forward return, credential, or provider.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign151_features as features,
)


PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_snapshot_full_verification_protocol_20260815.json"
)
PROTOCOL_SHA256 = "1d6658362584642416f46b2b2eea64d869813d2768db699d011d55c18a0f7836"
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_snapshot_verifier_implementation_freeze_v2_20260815.json"
)
VERIFIER_TEST = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign151_snapshot_verify.py"
)
RECEIPT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_snapshot_full_verification_20260815.json"
)
SNAPSHOT_ROOT = features.output_root()
SNAPSHOT_MANIFEST = SNAPSHOT_ROOT / "snapshot_manifest.json"
SNAPSHOT_MANIFEST_SHA256 = (
    "fdc23323e2ddc9e070f3c2a48fb5d05ebf9673b8c0c613ac88ecd0ea15054f83"
)
SNAPSHOT_DATASET_SHA256 = (
    "ef60fd141ab02a6b1add10de6193d47d8baad83a407a2a11488a50ce5e5f9029"
)
BENCHMARK_BYTE_SHA256 = (
    "2f8c309f9a02715b749fb961f40218650967674435e8bae1ef09024877293903"
)
BENCHMARK_FRAME_SHA256 = (
    "f9b7d4c35de39fec7ed7ba6ebb1501ee39b489651e71e41fa5739605082e95ee"
)
EXPECTED_PARTITIONS = 33_015
EXPECTED_ROWS = 7_724_498
EXPECTED_ELIGIBLE_ROWS = 0
EXPECTED_TRADE_DATES = 1_699
EXPECTED_BENCHMARK_ROWS = EXPECTED_TRADE_DATES * features.PROFILE_POSITIONS
SIGNAL_LEDGER = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
SIGNAL_LEDGER_SHA256 = (
    "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
)
EXECUTION_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
EXECUTION_LEDGER_SHA256 = (
    "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
)


class Campaign151SnapshotVerificationError(RuntimeError):
    """Raised when an immutable Campaign151 verification invariant changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path, expected_sha256: str, label: str) -> None:
    if path.is_symlink() or not path.is_file() or file_sha256(path) != expected_sha256:
        raise Campaign151SnapshotVerificationError(f"{label} changed: {path}")


def load_protocol() -> dict[str, Any]:
    require_file(PROTOCOL, PROTOCOL_SHA256, "full-verification protocol")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    snapshot = (protocol.get("authoritative_inputs") or {}).get(
        "snapshot_manifest"
    ) or {}
    verification = protocol.get("full_verification") or {}
    decision = protocol.get("terminal_decision") or {}
    boundary = protocol.get("research_boundary") or {}
    if not (
        protocol.get("kind")
        == "a_share_three_day_walkforward_campaign151_snapshot_full_verification_protocol"
        and protocol.get("status")
        == "frozen_after_peer_benchmark_diagnosis_before_candidate_partition_payload_reads"
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST)
        and snapshot.get("sha256") == SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and snapshot.get("partitions") == EXPECTED_PARTITIONS
        and snapshot.get("rows") == EXPECTED_ROWS
        and snapshot.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and verification.get("every_partition_byte_sha256_must_match") is True
        and verification.get("every_partition_frame_sha256_must_match") is True
        and verification.get("every_partition_sidecar_must_equal_manifest_record")
        is True
        and verification.get(
            "benchmark_position_238_sum_must_be_zero_on_all_1699_dates"
        )
        is True
        and decision.get("formula_or_gate_rescue_allowed") is False
        and decision.get("append_to_numeric_comparator_library_allowed") is False
        and boundary.get(
            "candidate_partition_values_read_after_publication_before_protocol"
        )
        is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign151SnapshotVerificationError(
            "full-verification protocol semantics changed"
        )
    return protocol


def load_manifest_metadata() -> dict[str, Any]:
    load_protocol()
    require_file(SNAPSHOT_MANIFEST, SNAPSHOT_MANIFEST_SHA256, "snapshot manifest")
    manifest = json.loads(SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))
    files = list(manifest.get("files") or [])
    quality = manifest.get("quality") or {}
    benchmark = manifest.get("peer_benchmark") or {}
    keys = [(str(item.get("symbol")), int(item.get("year", -1))) for item in files]
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign151_feature_snapshot"
        and manifest.get("status")
        == "candidate_feature_complete_pending_coverage_and_ordered_uniqueness"
        and manifest.get("output_run_id") == features.OUTPUT_RUN_ID
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and manifest.get("partitions") == len(files) == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and keys == sorted(keys)
        and len(set(keys)) == EXPECTED_PARTITIONS
        and manifest.get("factor_name") == features.FACTOR_NAME
        and manifest.get("factor_direction") == "higher"
        and manifest.get("source_fields_read") == list(features.RAW_COLUMNS)
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("promotion_allowed") is False
        and quality.get("base_rows") == EXPECTED_ROWS
        and quality.get("complete_profile_rows") == EXPECTED_ROWS
        and quality.get("eligible_rows") == 0
        and quality.get("nonpositive_peer_clock_rows") == EXPECTED_ROWS
        and quality.get("insufficient_leave_one_out_peer_rows") == 0
        and quality.get("invalid_required_amount_rows") == 0
        and quality.get("invalid_score_rows") == 0
        and benchmark.get("output_byte_sha256") == BENCHMARK_BYTE_SHA256
        and benchmark.get("output_frame_sha256") == BENCHMARK_FRAME_SHA256
        and benchmark.get("rows") == EXPECTED_BENCHMARK_ROWS
        and benchmark.get("trade_dates") == EXPECTED_TRADE_DATES
        and benchmark.get("profile_positions_per_date") == features.PROFILE_POSITIONS
        and all(int(item.get("eligible_rows", -1)) == 0 for item in files)
        and sum(int(item.get("rows", -1)) for item in files) == EXPECTED_ROWS
    ):
        raise Campaign151SnapshotVerificationError(
            "snapshot manifest semantics changed"
        )
    return manifest


def validate_implementation_freeze() -> dict[str, Any]:
    if IMPLEMENTATION_FREEZE.is_symlink() or not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign151SnapshotVerificationError(
            "snapshot verifier implementation freeze is absent"
        )
    freeze = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    implementation = freeze.get("frozen_implementation") or {}
    boundary = freeze.get("research_boundary") or {}
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign151_snapshot_verifier_implementation_freeze"
        and freeze.get("status")
        == "verifier_and_synthetic_tests_frozen_before_candidate_partition_payload_reads"
        and (freeze.get("authoritative_inputs") or {})
        .get("verification_protocol", {})
        .get("sha256")
        == PROTOCOL_SHA256
        and implementation.get("verifier_sha256")
        == file_sha256(Path(__file__).resolve())
        and implementation.get("verifier_test_sha256") == file_sha256(VERIFIER_TEST)
        and (freeze.get("verification") or {}).get("pytest_passed", 0) >= 6
        and boundary.get("candidate_partition_payloads_read_before_freeze") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign151SnapshotVerificationError(
            "snapshot verifier implementation freeze changed"
        )
    return freeze


def _validate_candidate49_ledgers() -> None:
    require_file(SIGNAL_LEDGER, SIGNAL_LEDGER_SHA256, "Candidate49 signal ledger")
    require_file(
        EXECUTION_LEDGER, EXECUTION_LEDGER_SHA256, "Candidate49 execution ledger"
    )
    for path in (SIGNAL_LEDGER, EXECUTION_LEDGER):
        if len(json.loads(path.read_text(encoding="utf-8")).get("entries") or []) != 0:
            raise Campaign151SnapshotVerificationError(
                "Candidate49 ledger entries changed"
            )


def plan() -> dict[str, Any]:
    manifest = load_manifest_metadata()
    validate_implementation_freeze()
    _validate_candidate49_ledgers()
    ready = not RECEIPT.exists()
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign151_snapshot_verification_plan",
        "status": "ready_for_confirmed_full_verification" if ready else "not_ready",
        "ready": ready,
        "reason": None if ready else "verification receipt already exists",
        "snapshot_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "dataset_sha256": manifest["dataset_sha256"],
        "partitions": len(manifest["files"]),
        "rows": manifest["rows"],
        "eligible_rows": manifest["eligible_rows"],
        "candidate_partition_or_benchmark_payload_opened_by_plan": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_ledgers_changed": False,
    }


def _contained_path(value: str, *, root: Path, label: str) -> Path:
    resolved_root = root.expanduser().resolve()
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(resolved_root)
    except ValueError as exc:
        raise Campaign151SnapshotVerificationError(
            f"{label} path escapes snapshot root: {path}"
        ) from exc
    if path.is_symlink():
        raise Campaign151SnapshotVerificationError(f"{label} path is a symlink: {path}")
    return path


def validate_partition_frame(
    frame: pd.DataFrame, item: dict[str, Any]
) -> tuple[int, int]:
    if tuple(frame.columns) != features.OUTPUT_COLUMNS:
        raise Campaign151SnapshotVerificationError("partition columns changed")
    expected_rows = int(item.get("rows", -1))
    if len(frame) != expected_rows:
        raise Campaign151SnapshotVerificationError("partition row count changed")
    dates = pd.to_datetime(frame["trade_date"], errors="coerce")
    symbol = str(item.get("symbol"))
    if (
        dates.isna().any()
        or not dates.equals(dates.dt.normalize())
        or not dates.is_monotonic_increasing
        or dates.duplicated().any()
        or (len(frame) and set(frame["symbol"].astype(str)) != {symbol})
        or (len(frame) and set(frame["provider"].astype(str)) != {"tushare"})
        or (len(frame) and set(dates.dt.year.astype(int)) != {int(item["year"])})
        or not pd.api.types.is_bool_dtype(
            frame[f"{features.FACTOR_NAME}_eligible"].dtype
        )
        or frame[f"{features.FACTOR_NAME}_eligible"].any()
        or frame[features.FACTOR_NAME].notna().any()
    ):
        raise Campaign151SnapshotVerificationError(
            f"partition key or zero-coverage semantics changed for {symbol}/{item.get('year')}"
        )
    return len(frame), 0


def verify_partition(item: dict[str, Any]) -> dict[str, Any]:
    data_root = SNAPSHOT_ROOT / "partitions"
    sidecar_root = SNAPSHOT_ROOT / ".metadata/partitions"
    path = _contained_path(str(item.get("path", "")), root=data_root, label="data")
    sidecar = _contained_path(
        str(item.get("sidecar_path", "")), root=sidecar_root, label="sidecar"
    )
    require_file(path, str(item.get("output_byte_sha256", "")), "partition")
    if not sidecar.is_file() or json.loads(sidecar.read_text(encoding="utf-8")) != item:
        raise Campaign151SnapshotVerificationError(
            f"partition sidecar changed: {sidecar}"
        )
    frame = pd.read_parquet(path)
    rows, eligible = validate_partition_frame(frame, item)
    if features.foundation.frame_digest(frame) != item.get("output_frame_sha256"):
        raise Campaign151SnapshotVerificationError(
            f"partition frame digest changed: {path}"
        )
    return {
        "symbol": str(item["symbol"]),
        "year": int(item["year"]),
        "rows": rows,
        "eligible_rows": eligible,
        "output_byte_sha256": str(item["output_byte_sha256"]),
        "output_frame_sha256": str(item["output_frame_sha256"]),
    }


def position_sets_are_exact(position_sets: pd.Series) -> bool:
    expected = tuple(range(features.PROFILE_POSITIONS))
    return bool(position_sets.map(lambda value: value == expected).all())


def verify_benchmark(manifest: dict[str, Any]) -> dict[str, Any]:
    item = manifest["peer_benchmark"]
    path = _contained_path(str(item["path"]), root=SNAPSHOT_ROOT, label="benchmark")
    require_file(path, BENCHMARK_BYTE_SHA256, "peer benchmark")
    frame = pd.read_parquet(path)
    if tuple(frame.columns) != features.BENCHMARK_COLUMNS:
        raise Campaign151SnapshotVerificationError("benchmark columns changed")
    dates = pd.to_datetime(frame["trade_date"], errors="coerce")
    positions = pd.to_numeric(frame["profile_position"], errors="coerce")
    sums = pd.to_numeric(frame["raw_amount_sum"], errors="coerce")
    counts = pd.to_numeric(frame["complete_profile_count"], errors="coerce")
    date_counts = frame.groupby(dates, sort=True).size()
    position_sets = frame.groupby(dates, sort=True)["profile_position"].agg(
        lambda values: tuple(int(value) for value in values)
    )
    count_ranges = frame.groupby(dates, sort=True)["complete_profile_count"].agg(
        ["min", "max"]
    )
    position_238 = frame.loc[positions == 238, "raw_amount_sum"]
    if not (
        len(frame) == EXPECTED_BENCHMARK_ROWS
        and dates.notna().all()
        and dates.nunique() == EXPECTED_TRADE_DATES
        and dates.is_monotonic_increasing
        and positions.notna().all()
        and np.isfinite(sums.to_numpy(dtype=np.float64)).all()
        and (sums >= 0.0).all()
        and np.isfinite(counts.to_numpy(dtype=np.float64)).all()
        and (counts >= features.MINIMUM_LEAVE_ONE_OUT_PEERS + 1).all()
        and date_counts.eq(features.PROFILE_POSITIONS).all()
        and position_sets_are_exact(position_sets)
        and count_ranges["min"].eq(count_ranges["max"]).all()
        and len(position_238) == EXPECTED_TRADE_DATES
        and position_238.eq(0.0).all()
        and features.foundation.frame_digest(frame) == BENCHMARK_FRAME_SHA256
    ):
        raise Campaign151SnapshotVerificationError("peer benchmark semantics changed")
    return {
        "rows": len(frame),
        "trade_dates": int(dates.nunique()),
        "positions_per_date": features.PROFILE_POSITIONS,
        "position_238_zero_dates": int(position_238.eq(0.0).sum()),
        "output_byte_sha256": BENCHMARK_BYTE_SHA256,
        "output_frame_sha256": BENCHMARK_FRAME_SHA256,
    }


def dataset_digest(records: list[dict[str, Any]]) -> str:
    payload = "\n".join(
        [
            f"benchmark|{BENCHMARK_BYTE_SHA256}",
            *[
                f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
                for item in records
            ],
        ]
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify(*, workers: int, confirm_snapshot_verification: bool) -> dict[str, Any]:
    if confirm_snapshot_verification is not True:
        raise Campaign151SnapshotVerificationError(
            "--confirm-snapshot-verification is required"
        )
    if workers < 1 or workers > 8:
        raise Campaign151SnapshotVerificationError("workers must be between 1 and 8")
    plan_record = plan()
    if not plan_record["ready"]:
        raise Campaign151SnapshotVerificationError("metadata-only plan is not ready")
    manifest = load_manifest_metadata()
    benchmark = verify_benchmark(manifest)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(verify_partition, manifest["files"]))
    records.sort(key=lambda item: (item["symbol"], item["year"]))
    observed_digest = dataset_digest(records)
    if not (
        len(records) == EXPECTED_PARTITIONS
        and sum(item["rows"] for item in records) == EXPECTED_ROWS
        and sum(item["eligible_rows"] for item in records) == EXPECTED_ELIGIBLE_ROWS
        and observed_digest == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign151SnapshotVerificationError(
            "aggregate partition or dataset digest changed"
        )
    _validate_candidate49_ledgers()
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign151_snapshot_full_verification",
        "status": "passed_zero_eligible_coverage_campaign151_must_terminate_before_returns",
        "snapshot_manifest_path": str(SNAPSHOT_MANIFEST),
        "snapshot_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "dataset_sha256": observed_digest,
        "partitions": len(records),
        "rows": sum(item["rows"] for item in records),
        "eligible_rows": sum(item["eligible_rows"] for item in records),
        "peer_benchmark": benchmark,
        "all_partition_byte_hashes_match": True,
        "all_partition_frame_hashes_match": True,
        "all_sidecars_match_manifest_records": True,
        "all_keys_ordered_and_unique": True,
        "all_eligible_flags_false": True,
        "all_factor_values_nan": True,
        "campaign151_return_read_allowed": False,
        "numeric_comparator_library_append_allowed": False,
        "formula_or_gate_rescue_allowed": False,
        "stress_2024_2025_opened": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_ledgers_changed": False,
        "current_scoring_selection_sizing_positions_or_orders_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan", help="run metadata-only verification gates")
    verification = subparsers.add_parser("verify", help="verify every snapshot file")
    verification.add_argument("--workers", type=int, default=4)
    verification.add_argument("--confirm-snapshot-verification", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "plan":
            result = plan()
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0 if result["ready"] else 2
        result = verify(
            workers=args.workers,
            confirm_snapshot_verification=args.confirm_snapshot_verification,
        )
    except Campaign151SnapshotVerificationError as exc:
        print(
            json.dumps(
                {
                    "kind": "a_share_three_day_walkforward_campaign151_snapshot_verification_failure",
                    "status": "failed",
                    "safe_error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "Campaign151SnapshotVerificationError",
    "dataset_digest",
    "load_manifest_metadata",
    "load_protocol",
    "main",
    "plan",
    "position_sets_are_exact",
    "validate_partition_frame",
    "verify",
    "verify_benchmark",
    "verify_partition",
]
