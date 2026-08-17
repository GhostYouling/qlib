#!/usr/bin/env python3
"""Build and verify the frozen candidate-independent comparator cache."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign067_features as candidate
from scripts import a_share_three_day_walkforward_campaign067_no_return_audit as audit


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_protocol_v1_20260805.json"
)
PROTOCOL_SHA256 = "bf5247378056851ea004c08aad071c7a1ccf552cb1feaf6937251a26234c3273"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_implementation_freeze_v1_20260805.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_compact_comparator_cache.py"
)
COMPLETED_AUDIT_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_067/no_return/"
    "20260805T115907Z_campaign067_no_return_audit.json"
)
COMPLETED_AUDIT_SHA256 = "daeac2c2364d00c09247d0e721435b81f587c0f215a5a93cba30b7661f205d54"
DEFAULT_DATA_ROOT = audit.DEFAULT_DATA_ROOT
DEFAULT_OUTPUT_ROOT = (
    DEFAULT_DATA_ROOT
    / "derived/a_share/rich/tushare/compact_comparator_cache/"
    "campaign067_terminal_numeric98_v1"
)
FACTOR_NAME = candidate.FACTOR_NAME
STRUCTURAL_FACTOR = audit.STRUCTURALLY_NONNUMERIC_FACTOR
EXPECTED_ROWS = 1_331_759
EXPECTED_SESSIONS = 1_632
EXPECTED_KEYS_SHA256 = "afa157a76aec8ef9cc3bdc191c792189d2a512ecf7fd7ebb09d2fe8f2d75841f"
EXPECTED_NUMERIC_COUNT = 98
EXPECTED_NUMERIC_ORDER_SHA256 = "bca0ba26252fcb74afa3a31ee1baf63c9cedfe3db5fc86ef71b3d7d93bf88f81"
EXPECTED_COMPLETE_COUNT = 99
EXPECTED_COMPLETE_ORDER_SHA256 = "74564d4d2d01a52371ddd6906db38b5d913acb743656a04bbe5c4f229c84ad53"


class CompactComparatorCacheError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise CompactComparatorCacheError(f"{label} changed")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_protocol() -> dict[str, Any]:
    _require(PROTOCOL_PATH, PROTOCOL_SHA256, "compact-cache protocol")
    report = bindings.validate_record(PROTOCOL_PATH, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise CompactComparatorCacheError("compact-cache protocol bindings failed")
    spec = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    eligibility = spec.get("eligibility_key_contract") or {}
    library = spec.get("numeric_library_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_candidate_independent_compact_comparator_cache_protocol"
        and spec.get("status")
        == "frozen_before_compact_comparator_values_or_cache_files_are_materialized"
        and eligibility.get("row_count") == EXPECTED_ROWS
        and eligibility.get("calendar_session_count") == EXPECTED_SESSIONS
        and eligibility.get("sorted_little_endian_int64_sha256")
        == EXPECTED_KEYS_SHA256
        and library.get("resulting_numeric_comparator_count")
        == EXPECTED_NUMERIC_COUNT
        and library.get("resulting_numeric_comparator_order_sha256")
        == EXPECTED_NUMERIC_ORDER_SHA256
        and library.get("complete_definition_count_including_structural_nonnumeric_factor")
        == EXPECTED_COMPLETE_COUNT
        and library.get("complete_definition_order_sha256")
        == EXPECTED_COMPLETE_ORDER_SHA256
        and library.get("structurally_nonnumeric_factor_excluded_from_numeric_cache")
        == STRUCTURAL_FACTOR
        and boundary.get("new_candidate_definition_or_value_read_before_protocol_freeze")
        is False
        and boundary.get("historical_daily_price_fields_read") == []
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise CompactComparatorCacheError("compact-cache protocol semantics changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise CompactComparatorCacheError("compact-cache implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE_PATH.read_text(encoding="utf-8"))
    protocol = record.get("protocol") or {}
    builder = record.get("builder") or {}
    tests = record.get("tests") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_compact_comparator_cache_implementation_freeze"
        and record.get("status")
        == "frozen_before_compact_comparator_values_or_cache_files_materialized"
        and protocol.get("sha256") == PROTOCOL_SHA256
        and builder.get("sha256") == _sha256(Path(__file__).resolve())
        and tests.get("sha256") == _sha256(TEST_PATH)
        and record.get("cache_output_existed_before_freeze") is False
        and record.get("comparison_factor_values_read_before_freeze") is False
        and record.get("historical_daily_price_or_forward_return_values_read_before_freeze")
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise CompactComparatorCacheError("compact-cache implementation freeze changed")
    return record


def numeric_definitions() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    comparisons = candidate.reconstruct_comparisons(audit.load_protocol())
    complete = audit.reconstruct_complete_definitions(comparisons)
    numeric = [*comparisons, {"name": FACTOR_NAME, "score_direction": "higher"}]
    all_definitions = [
        *complete,
        {"name": FACTOR_NAME, "score_direction": "higher"},
    ]
    if not (
        len(numeric) == EXPECTED_NUMERIC_COUNT
        and candidate._comparison_order_digest(numeric)
        == EXPECTED_NUMERIC_ORDER_SHA256
        and len(all_definitions) == EXPECTED_COMPLETE_COUNT
        and candidate._comparison_order_digest(all_definitions)
        == EXPECTED_COMPLETE_ORDER_SHA256
        and STRUCTURAL_FACTOR not in [item["name"] for item in numeric]
        and STRUCTURAL_FACTOR in [item["name"] for item in all_definitions]
    ):
        raise CompactComparatorCacheError("compact-cache factor order changed")
    return numeric, all_definitions


def eligible_keys() -> np.ndarray:
    prior, foundation, _, _, _, comparison_engine = (
        audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    frame = foundation.quality_listing_eligible_keys(prior.load_protocol())
    keys = comparison_engine._compact_stock_day_keys(
        frame["trade_date"], frame["symbol"]
    ).astype(np.int64, copy=False)
    keys = np.sort(keys, kind="stable")
    digest = hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest()
    if not (
        len(keys) == EXPECTED_ROWS
        and len(np.unique(keys)) == EXPECTED_ROWS
        and len(np.unique(keys // 4_000_000)) == EXPECTED_SESSIONS
        and digest == EXPECTED_KEYS_SHA256
    ):
        raise CompactComparatorCacheError("compact-cache eligibility keys changed")
    return keys


def canonical_column_sha256(values: np.ndarray) -> str:
    array = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(array)
    canonical = np.where(finite, array, 0.0).astype("<f8", copy=False)
    digest = hashlib.sha256()
    digest.update(finite.astype(np.uint8, copy=False).tobytes())
    digest.update(canonical.tobytes())
    return digest.hexdigest()


def partition_frame_sha256(
    keys: np.ndarray, matrix: np.ndarray, names: list[str]
) -> str:
    digest = hashlib.sha256()
    digest.update(b"stock_day_key\0")
    digest.update(np.asarray(keys, dtype="<i8").tobytes())
    for index, name in enumerate(names):
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "little"))
        digest.update(encoded)
        digest.update(bytes.fromhex(canonical_column_sha256(matrix[:, index])))
    return digest.hexdigest()


class _CaptureComparisonEngine:
    def __init__(
        self,
        *,
        keys: np.ndarray,
        matrix: np.memmap,
        definitions: list[dict[str, str]],
    ) -> None:
        self.keys = keys
        self.matrix = matrix
        self.definitions = definitions
        self.seen: list[str] = []

    def _aligned_comparison_result(
        self,
        *,
        candidate_keys: np.ndarray,
        candidate_values: np.ndarray,
        comparison_values: np.ndarray,
        comparison: str,
        direction: str,
        gate: dict[str, Any],
    ) -> dict[str, Any]:
        del gate
        index = len(self.seen)
        if index >= len(self.definitions):
            raise CompactComparatorCacheError("too many comparator values captured")
        expected = self.definitions[index]
        values = np.asarray(comparison_values, dtype=np.float64)
        if not (
            np.array_equal(np.asarray(candidate_keys, dtype=np.int64), self.keys)
            and len(candidate_values) == len(self.keys)
            and comparison == expected["name"]
            and direction == expected["score_direction"]
            and values.shape == (len(self.keys),)
        ):
            raise CompactComparatorCacheError(
                f"captured comparator semantics changed at {comparison}"
            )
        self.matrix[:, index] = values
        self.seen.append(comparison)
        return {
            "comparison_factor": comparison,
            "score_direction": direction,
            "gate_passed": True,
        }


def _completed_audit() -> dict[str, Any]:
    _require(COMPLETED_AUDIT_PATH, COMPLETED_AUDIT_SHA256, "Campaign067 audit")
    return json.loads(COMPLETED_AUDIT_PATH.read_text(encoding="utf-8"))


def _capture_matrix(
    *,
    data_root: Path,
    workers: int,
    keys: np.ndarray,
    matrix: np.memmap,
    definitions: list[dict[str, str]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    completed = _completed_audit()
    factor_result = completed["uniqueness"][FACTOR_NAME]
    expected_receipts = factor_result["source_snapshot_verifications"]
    prior, foundation, engine, _, candidate49, comparison_engine = (
        audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    del prior, foundation, comparison_engine
    spec = audit.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    directions = {
        str(item["name"]): str(item["score_direction"])
        for item in gate["comparison_factors"]
    }
    capture = _CaptureComparisonEngine(
        keys=keys,
        matrix=matrix,
        definitions=definitions[:-1],
    )
    dummy_values = np.zeros(len(keys), dtype=np.float64)
    captured, receipts = audit._append_prior_numeric_comparisons(
        data_root=data_root,
        workers=workers,
        keys=keys,
        values=dummy_values,
        gate=gate,
        directions=directions,
        engine=engine,
        candidate49=candidate49,
        comparison_engine=capture,
    )
    observed_order = [str(item["comparison_factor"]) for item in captured]
    expected_order = [item["name"] for item in definitions[:-1]]
    if not (
        observed_order == expected_order
        and capture.seen == expected_order
        and receipts == expected_receipts
    ):
        raise CompactComparatorCacheError(
            "inherited comparator capture or source verification receipt changed"
        )
    candidate_receipt = candidate.verify_snapshot_files(
        audit.SNAPSHOT_MANIFEST_PATH,
        workers=workers,
    )
    if candidate_receipt != completed["snapshot_file_verification"]:
        raise CompactComparatorCacheError(
            "Campaign067 candidate source verification receipt changed"
        )
    manifest = json.loads(
        audit.SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    values = engine._load_filtered_comparison_values_explicit(
        manifest,
        [FACTOR_NAME],
        keys,
    )[FACTOR_NAME]
    if np.asarray(values).shape != (len(keys),):
        raise CompactComparatorCacheError("Campaign067 aligned values changed")
    matrix[:, -1] = np.asarray(values, dtype=np.float64)
    matrix.flush()
    del values, dummy_values
    gc.collect()
    return receipts, candidate_receipt, completed


def _write_partitions(
    *,
    root: Path,
    keys: np.ndarray,
    matrix: np.ndarray,
    names: list[str],
) -> list[dict[str, Any]]:
    partition_root = root / "partitions"
    partition_root.mkdir(parents=True, exist_ok=False)
    days = keys // 4_000_000
    records: list[dict[str, Any]] = []
    for year in range(2019, 2026):
        start_day = np.datetime64(f"{year}-01-01", "D").astype(np.int64)
        stop_day = np.datetime64(f"{year + 1}-01-01", "D").astype(np.int64)
        start = int(np.searchsorted(days, start_day, side="left"))
        stop = int(np.searchsorted(days, stop_day, side="left"))
        year_keys = np.asarray(keys[start:stop], dtype=np.int64)
        year_matrix = np.asarray(matrix[start:stop, :], dtype=np.float64)
        arrays: list[pa.Array] = [pa.array(year_keys, type=pa.int64())]
        arrays.extend(
            pa.array(year_matrix[:, index], type=pa.float64(), from_pandas=False)
            for index in range(len(names))
        )
        table = pa.Table.from_arrays(arrays, names=["stock_day_key", *names])
        path = partition_root / f"{year}.parquet"
        pq.write_table(
            table,
            path,
            compression="zstd",
            use_dictionary=False,
            write_statistics=True,
            row_group_size=65_536,
            data_page_version="2.0",
        )
        records.append(
            {
                "year": year,
                "path": f"partitions/{year}.parquet",
                "rows": len(year_keys),
                "sha256": _sha256(path),
                "frame_sha256": partition_frame_sha256(
                    year_keys,
                    year_matrix,
                    names,
                ),
            }
        )
        del table, arrays, year_keys, year_matrix
        gc.collect()
    if sum(int(item["rows"]) for item in records) != EXPECTED_ROWS:
        raise CompactComparatorCacheError("compact-cache partition rows changed")
    return records


def _load_cache_matrix(
    *,
    root: Path,
    records: list[dict[str, Any]],
    names: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    keys = np.empty(EXPECTED_ROWS, dtype=np.int64)
    matrix = np.empty((EXPECTED_ROWS, len(names)), dtype=np.float64)
    offset = 0
    expected_schema = ["stock_day_key", *names]
    for record in records:
        path = (root / str(record["path"])).resolve()
        try:
            path.relative_to((root / "partitions").resolve())
        except ValueError as exc:
            raise CompactComparatorCacheError(
                "compact-cache partition escaped its root"
            ) from exc
        if _sha256(path) != record["sha256"]:
            raise CompactComparatorCacheError("compact-cache partition bytes changed")
        table = pq.read_table(path, columns=expected_schema)
        if table.column_names != expected_schema or table.num_rows != record["rows"]:
            raise CompactComparatorCacheError("compact-cache partition schema changed")
        count = int(table.num_rows)
        part_keys = table["stock_day_key"].combine_chunks().to_numpy(
            zero_copy_only=False
        ).astype(np.int64, copy=False)
        part_matrix = np.column_stack(
            [
                table[name].combine_chunks().to_numpy(zero_copy_only=False)
                for name in names
            ]
        ).astype(np.float64, copy=False)
        if partition_frame_sha256(part_keys, part_matrix, names) != record[
            "frame_sha256"
        ]:
            raise CompactComparatorCacheError("compact-cache frame digest changed")
        keys[offset : offset + count] = part_keys
        matrix[offset : offset + count, :] = part_matrix
        offset += count
        del table, part_keys, part_matrix
        gc.collect()
    if offset != EXPECTED_ROWS:
        raise CompactComparatorCacheError("compact-cache loaded row count changed")
    return keys, matrix


def _actual_equivalence(
    *,
    keys: np.ndarray,
    matrix: np.ndarray,
    definitions: list[dict[str, str]],
    completed: dict[str, Any],
) -> dict[str, Any]:
    prior, foundation, engine, _, _, comparison_engine = (
        audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    audit._install_frozen_candidate_range(engine)
    eligible = foundation.quality_listing_eligible_keys(prior.load_protocol())
    manifest = json.loads(
        audit.SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    candidate_frame = engine.load_factor_frame(
        audit.SNAPSHOT_MANIFEST_PATH,
        manifest,
        FACTOR_NAME,
    )
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate_frame,
        eligible,
        audit.load_protocol(),
        FACTOR_NAME,
    )
    del candidate_frame, eligible
    expected_coverage = completed["coverage_and_capacity"][FACTOR_NAME]
    if coverage != expected_coverage:
        raise CompactComparatorCacheError(
            "Campaign067 candidate coverage changed during cache equivalence"
        )
    candidate_keys, candidate_values = engine._sorted_candidate_arrays(
        quality_frame,
        FACTOR_NAME,
    )
    del quality_frame
    positions = np.searchsorted(keys, candidate_keys, side="left")
    if not (
        np.all(positions < len(keys))
        and np.array_equal(keys[positions], candidate_keys)
    ):
        raise CompactComparatorCacheError(
            "cache does not cover Campaign067 candidate keys"
        )
    gate = audit.load_protocol()["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]
    observed: list[dict[str, Any]] = []
    for index, definition in enumerate(definitions[:-1]):
        observed.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=candidate_keys,
                candidate_values=candidate_values,
                comparison_values=matrix[positions, index],
                comparison=definition["name"],
                direction=definition["score_direction"],
                gate=gate,
            )
        )
    expected = completed["uniqueness"][FACTOR_NAME]["comparisons"]
    if observed != expected:
        mismatches = [
            index
            for index, (left, right) in enumerate(zip(observed, expected, strict=True))
            if left != right
        ]
        raise CompactComparatorCacheError(
            f"cache semantic equivalence failed at comparisons {mismatches[:5]}"
        )
    receipt = {
        "candidate_factor": FACTOR_NAME,
        "candidate_coverage_exactly_equal_to_completed_audit": True,
        "comparison_count": len(observed),
        "all_comparison_result_objects_exactly_equal": True,
        "comparison_results_sha256": _json_sha256(observed),
        "bound_completed_audit_sha256": COMPLETED_AUDIT_SHA256,
        "campaign067_cache_column_sha256": canonical_column_sha256(
            matrix[:, -1]
        ),
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }
    return receipt


def _manifest_core(
    *,
    names: list[str],
    definitions: list[dict[str, str]],
    keys: np.ndarray,
    matrix: np.ndarray,
    files: list[dict[str, Any]],
    receipts: dict[str, Any],
    candidate_receipt: dict[str, Any],
    equivalence: dict[str, Any],
    freeze_sha256: str,
) -> dict[str, Any]:
    columns = []
    for index, definition in enumerate(definitions):
        values = np.asarray(matrix[:, index], dtype=np.float64)
        columns.append(
            {
                "name": definition["name"],
                "score_direction": definition["score_direction"],
                "finite_rows": int(np.isfinite(values).sum()),
                "nonfinite_rows": int((~np.isfinite(values)).sum()),
                "canonical_value_sha256": canonical_column_sha256(values),
            }
        )
    dataset_material = {
        "protocol_sha256": PROTOCOL_SHA256,
        "implementation_freeze_sha256": freeze_sha256,
        "eligibility_keys_sha256": EXPECTED_KEYS_SHA256,
        "numeric_order_sha256": EXPECTED_NUMERIC_ORDER_SHA256,
        "columns": columns,
        "files": files,
        "source_verification_receipts_sha256": _json_sha256(receipts),
        "candidate_snapshot_verification_receipt_sha256": _json_sha256(
            candidate_receipt
        ),
        "semantic_equivalence_sha256": _json_sha256(equivalence),
    }
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_candidate_independent_compact_comparator_cache",
        "status": "complete_verified_semantically_equivalent_no_return_cache",
        "created_at": _utc_now(),
        "protocol": {
            "path": str(PROTOCOL_PATH.resolve()),
            "sha256": PROTOCOL_SHA256,
        },
        "implementation_freeze": {
            "path": str(IMPLEMENTATION_FREEZE_PATH.resolve()),
            "sha256": freeze_sha256,
        },
        "builder": {
            "path": str(Path(__file__).resolve()),
            "sha256": _sha256(Path(__file__).resolve()),
        },
        "eligibility": {
            "rows": len(keys),
            "calendar_sessions": int(len(np.unique(keys // 4_000_000))),
            "sorted_little_endian_int64_sha256": hashlib.sha256(
                keys.astype("<i8", copy=False).tobytes()
            ).hexdigest(),
        },
        "numeric_comparator_count": len(names),
        "numeric_comparator_order_sha256": EXPECTED_NUMERIC_ORDER_SHA256,
        "complete_definition_count": EXPECTED_COMPLETE_COUNT,
        "complete_definition_order_sha256": EXPECTED_COMPLETE_ORDER_SHA256,
        "columns": columns,
        "files": files,
        "source_snapshot_verifications": receipts,
        "source_snapshot_verifications_sha256": _json_sha256(receipts),
        "campaign067_snapshot_file_verification": candidate_receipt,
        "campaign067_snapshot_file_verification_sha256": _json_sha256(
            candidate_receipt
        ),
        "semantic_equivalence": equivalence,
        "dataset_sha256": _json_sha256(dataset_material),
        "historical_daily_price_fields_read": [],
        "historical_forward_returns_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
        "provider_request_issued": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }


def build_cache(
    *, data_root: Path, output_root: Path, workers: int, confirm_build: bool
) -> Path:
    if not confirm_build:
        raise CompactComparatorCacheError("build requires --confirm-build")
    load_protocol()
    freeze = _load_implementation_freeze()
    data_root = data_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise CompactComparatorCacheError("compact-cache data root changed")
    if output_root != DEFAULT_OUTPUT_ROOT.resolve():
        raise CompactComparatorCacheError("compact-cache output root changed")
    if output_root.exists():
        raise CompactComparatorCacheError("compact-cache output already exists")
    definitions, _ = numeric_definitions()
    names = [item["name"] for item in definitions]
    keys = eligible_keys()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(
        tempfile.mkdtemp(
            prefix=f".{output_root.name}.",
            dir=output_root.parent,
        )
    )
    working_path = temporary_root / "working_matrix.npy"
    matrix = np.lib.format.open_memmap(
        working_path,
        mode="w+",
        dtype=np.float64,
        shape=(len(keys), len(names)),
    )
    receipts, candidate_receipt, completed = _capture_matrix(
        data_root=data_root,
        workers=workers,
        keys=keys,
        matrix=matrix,
        definitions=definitions,
    )
    files = _write_partitions(
        root=temporary_root,
        keys=keys,
        matrix=matrix,
        names=names,
    )
    loaded_keys, loaded_matrix = _load_cache_matrix(
        root=temporary_root,
        records=files,
        names=names,
    )
    if not np.array_equal(loaded_keys, keys):
        raise CompactComparatorCacheError("cache Parquet key round trip changed")
    for index, name in enumerate(names):
        if canonical_column_sha256(loaded_matrix[:, index]) != canonical_column_sha256(
            matrix[:, index]
        ):
            raise CompactComparatorCacheError(
                f"cache Parquet value round trip changed for {name}"
            )
    equivalence = _actual_equivalence(
        keys=loaded_keys,
        matrix=loaded_matrix,
        definitions=definitions,
        completed=completed,
    )
    freeze_sha256 = _sha256(IMPLEMENTATION_FREEZE_PATH)
    manifest = _manifest_core(
        names=names,
        definitions=definitions,
        keys=loaded_keys,
        matrix=loaded_matrix,
        files=files,
        receipts=receipts,
        candidate_receipt=candidate_receipt,
        equivalence=equivalence,
        freeze_sha256=freeze_sha256,
    )
    manifest_path = temporary_root / "snapshot_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    del loaded_matrix, loaded_keys, matrix
    gc.collect()
    working_path.unlink()
    os.replace(temporary_root, output_root)
    return output_root / "snapshot_manifest.json"


def verify_cache(
    manifest_path: Path = DEFAULT_OUTPUT_ROOT / "snapshot_manifest.json",
    *,
    full_equivalence: bool = False,
) -> dict[str, Any]:
    load_protocol()
    _load_implementation_freeze()
    manifest_path = manifest_path.expanduser().resolve()
    if manifest_path != (DEFAULT_OUTPUT_ROOT / "snapshot_manifest.json").resolve():
        raise CompactComparatorCacheError("compact-cache manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    definitions, _ = numeric_definitions()
    names = [item["name"] for item in definitions]
    if not (
        manifest.get("kind")
        == "a_share_three_day_candidate_independent_compact_comparator_cache"
        and manifest.get("status")
        == "complete_verified_semantically_equivalent_no_return_cache"
        and (manifest.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (manifest.get("builder") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and manifest.get("numeric_comparator_count") == EXPECTED_NUMERIC_COUNT
        and manifest.get("numeric_comparator_order_sha256")
        == EXPECTED_NUMERIC_ORDER_SHA256
        and manifest.get("complete_definition_count") == EXPECTED_COMPLETE_COUNT
        and manifest.get("complete_definition_order_sha256")
        == EXPECTED_COMPLETE_ORDER_SHA256
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise CompactComparatorCacheError("compact-cache manifest semantics changed")
    completed = _completed_audit()
    expected_receipts = completed["uniqueness"][FACTOR_NAME][
        "source_snapshot_verifications"
    ]
    if not (
        manifest.get("source_snapshot_verifications") == expected_receipts
        and manifest.get("source_snapshot_verifications_sha256")
        == _json_sha256(expected_receipts)
        and manifest.get("campaign067_snapshot_file_verification")
        == completed["snapshot_file_verification"]
    ):
        raise CompactComparatorCacheError("compact-cache source receipts changed")
    keys, matrix = _load_cache_matrix(
        root=manifest_path.parent,
        records=list(manifest["files"]),
        names=names,
    )
    if hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest() != (
        EXPECTED_KEYS_SHA256
    ):
        raise CompactComparatorCacheError("compact-cache eligibility digest changed")
    for index, record in enumerate(manifest["columns"]):
        values = matrix[:, index]
        if not (
            record.get("name") == names[index]
            and record.get("score_direction")
            == definitions[index]["score_direction"]
            and record.get("finite_rows") == int(np.isfinite(values).sum())
            and record.get("nonfinite_rows") == int((~np.isfinite(values)).sum())
            and record.get("canonical_value_sha256")
            == canonical_column_sha256(values)
        ):
            raise CompactComparatorCacheError(
                f"compact-cache column changed at {names[index]}"
            )
    observed_equivalence = manifest["semantic_equivalence"]
    if full_equivalence:
        recomputed = _actual_equivalence(
            keys=keys,
            matrix=matrix,
            definitions=definitions,
            completed=completed,
        )
        if recomputed != observed_equivalence:
            raise CompactComparatorCacheError(
                "compact-cache full semantic equivalence receipt changed"
            )
    result = {
        "status": "verified",
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "dataset_sha256": manifest["dataset_sha256"],
        "rows": len(keys),
        "numeric_comparator_count": len(names),
        "full_equivalence_recomputed": bool(full_equivalence),
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }
    del matrix, keys
    gc.collect()
    return result


def status() -> dict[str, Any]:
    load_protocol()
    manifest = DEFAULT_OUTPUT_ROOT / "snapshot_manifest.json"
    return {
        "protocol_sha256": PROTOCOL_SHA256,
        "implementation_freeze_exists": IMPLEMENTATION_FREEZE_PATH.is_file(),
        "output_exists": DEFAULT_OUTPUT_ROOT.exists(),
        "manifest_exists": manifest.is_file(),
        "comparison_factor_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    build = sub.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    build.add_argument("--workers", type=int, default=4)
    build.add_argument("--confirm-build", action="store_true")
    verify = sub.add_parser("verify")
    verify.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT / "snapshot_manifest.json",
    )
    verify.add_argument("--full-equivalence", action="store_true")
    args = parser.parse_args()
    if args.command == "status":
        payload = status()
    elif args.command == "build":
        payload = {
            "manifest": str(
                build_cache(
                    data_root=args.data_root,
                    output_root=args.output_root,
                    workers=args.workers,
                    confirm_build=args.confirm_build,
                )
            )
        }
    else:
        payload = verify_cache(
            args.manifest,
            full_equivalence=args.full_equivalence,
        )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
