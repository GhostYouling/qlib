#!/usr/bin/env python3
"""Build and verify the additive v2 compact-comparator cache repair."""

from __future__ import annotations

import argparse
import errno
import gc
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset

from scripts import a_share_three_day_compact_comparator_cache as v1


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_protocol_v2_20260805.json"
)
PROTOCOL_SHA256 = "98fa0318754c145ce645d647e591d32b89bc1b432db36028899c48220029dec9"
V1_PROTOCOL_SHA256 = v1.PROTOCOL_SHA256
V1_BUILDER_SHA256 = "9d78ac449c74cf0709bcd5a479eabc39eed487dc6c09fed1dd71c8127911f6a5"
V1_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_v1_build_failure_20260805.json"
)
V1_FAILURE_SHA256 = "9221d3b0c98b0ce9efb094a9e2e301d26e1fadd354f333e3ee2467227bdbd177"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_implementation_freeze_v2_20260805.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_compact_comparator_cache_v2.py"
)
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
DEFAULT_OUTPUT_ROOT = (
    DEFAULT_DATA_ROOT
    / "derived/a_share/rich/tushare/compact_comparator_cache/"
    "campaign067_terminal_numeric98_v2"
)
FAILED_V1_OUTPUT_ROOT = v1.DEFAULT_OUTPUT_ROOT


class CompactComparatorCacheV2Error(RuntimeError):
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
        raise CompactComparatorCacheV2Error(f"{label} changed")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_protocol() -> dict[str, Any]:
    _require(PROTOCOL_PATH, PROTOCOL_SHA256, "compact-cache v2 protocol")
    _require(V1_FAILURE_PATH, V1_FAILURE_SHA256, "compact-cache v1 failure")
    if _sha256(Path(v1.__file__).resolve()) != V1_BUILDER_SHA256:
        raise CompactComparatorCacheV2Error("frozen compact-cache v1 builder changed")
    base = v1.load_protocol()
    spec = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    base_binding = spec.get("authoritative_base_protocol") or {}
    failure = spec.get("recorded_v1_failure") or {}
    output = spec.get("frozen_output") or {}
    keys = spec.get("eligibility_key_contract") or {}
    library = spec.get("numeric_library_contract") or {}
    loader = spec.get("repair_loader_contract") or {}
    equivalence = spec.get("semantic_equivalence_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_candidate_independent_compact_comparator_cache_protocol"
        and spec.get("status")
        == "frozen_repair_before_v2_comparator_values_or_cache_files_are_materialized"
        and base_binding.get("sha256") == V1_PROTOCOL_SHA256
        and failure.get("sha256") == V1_FAILURE_SHA256
        and failure.get("v1_formal_output_published") is False
        and failure.get("v1_temporary_values_reusable") is False
        and output.get("output_root") == str(DEFAULT_OUTPUT_ROOT)
        and output.get("v1_output_root_may_be_published_or_reused") is False
        and keys.get("row_count") == v1.EXPECTED_ROWS
        and keys.get("calendar_session_count") == v1.EXPECTED_SESSIONS
        and keys.get("sorted_little_endian_int64_sha256")
        == v1.EXPECTED_KEYS_SHA256
        and library.get("numeric_comparator_count") == v1.EXPECTED_NUMERIC_COUNT
        and library.get("numeric_comparator_order_sha256")
        == v1.EXPECTED_NUMERIC_ORDER_SHA256
        and library.get(
            "complete_definition_count_including_structural_nonnumeric_factor"
        )
        == v1.EXPECTED_COMPLETE_COUNT
        and library.get("complete_definition_order_sha256")
        == v1.EXPECTED_COMPLETE_ORDER_SHA256
        and library.get("cross_sectional_rank_materialization_allowed") is False
        and loader.get("source_key_absent")
        == "Store a nonfinite float64 NaN at that global key."
        and loader.get("source_key_duplicate")
        == "Fail closed before publication."
        and equivalence.get("campaign067_required_comparison_count") == 97
        and equivalence.get(
            "campaign067_result_objects_must_be_exactly_equal_to_completed_audit"
        )
        is True
        and boundary.get("v2_comparison_values_read_before_protocol_freeze") is False
        and boundary.get("historical_daily_price_fields_read") == []
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("provider_request_issued") is False
        and isinstance(base, dict)
    ):
        raise CompactComparatorCacheV2Error("compact-cache v2 protocol changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise CompactComparatorCacheV2Error(
            "compact-cache v2 implementation freeze is absent"
        )
    record = json.loads(IMPLEMENTATION_FREEZE_PATH.read_text(encoding="utf-8"))
    protocol = record.get("protocol") or {}
    builder = record.get("builder") or {}
    tests = record.get("tests") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_compact_comparator_cache_implementation_freeze"
        and record.get("version") == 2
        and record.get("status")
        == "frozen_before_v2_comparator_values_or_cache_files_materialized"
        and protocol.get("sha256") == PROTOCOL_SHA256
        and builder.get("sha256") == _sha256(Path(__file__).resolve())
        and tests.get("sha256") == _sha256(TEST_PATH)
        and record.get("v2_cache_output_existed_before_freeze") is False
        and record.get("v2_comparison_factor_values_read_before_freeze") is False
        and record.get("historical_daily_price_or_forward_return_values_read_before_freeze")
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise CompactComparatorCacheV2Error(
            "compact-cache v2 implementation freeze changed"
        )
    return record


def _scan_explicit_values(
    *,
    paths: list[str],
    factors: Iterable[str],
    target_keys: np.ndarray,
    expected_rows: int,
) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    """Align explicit snapshot rows to sorted keys; absent keys remain NaN."""

    factor_tuple = tuple(str(value) for value in factors)
    keys = np.asarray(target_keys, dtype=np.int64)
    if (
        not factor_tuple
        or len(paths) != len(set(paths))
        or len(np.unique(keys)) != len(keys)
        or (len(keys) > 1 and not np.all(keys[1:] > keys[:-1]))
    ):
        raise CompactComparatorCacheV2Error("v2 explicit alignment inputs changed")
    aligned = {
        factor: np.full(len(keys), np.nan, dtype=np.float64)
        for factor in factor_tuple
    }
    seen = np.zeros(len(keys), dtype=bool)
    _, _, _, _, _, comparison_engine = (
        v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    dataset = pa_dataset.dataset(paths, format="parquet")
    scanner = dataset.scanner(
        columns=["trade_date", "symbol", *factor_tuple],
        batch_size=262_144,
        use_threads=True,
    )
    total_rows = 0
    for batch in scanner.to_batches():
        frame = batch.to_pandas(split_blocks=True, self_destruct=True)
        total_rows += len(frame)
        source_keys = comparison_engine._compact_stock_day_keys(
            frame["trade_date"], frame["symbol"]
        )
        positions = np.searchsorted(keys, source_keys, side="left")
        bounded = positions < len(keys)
        matched = np.zeros(len(source_keys), dtype=bool)
        matched[bounded] = keys[positions[bounded]] == source_keys[bounded]
        selected_positions = positions[matched]
        if (
            len(np.unique(selected_positions)) != len(selected_positions)
            or seen[selected_positions].any()
        ):
            raise CompactComparatorCacheV2Error(
                "explicit snapshot contains duplicate requested source keys"
            )
        seen[selected_positions] = True
        for factor in factor_tuple:
            aligned[factor][selected_positions] = pd.to_numeric(
                frame.loc[matched, factor], errors="coerce"
            ).to_numpy(dtype=np.float64)
        del (
            frame,
            source_keys,
            positions,
            bounded,
            matched,
            selected_positions,
            batch,
        )
    del scanner, dataset
    gc.collect()
    if total_rows != expected_rows:
        raise CompactComparatorCacheV2Error(
            f"explicit snapshot row count changed: {total_rows} != {expected_rows}"
        )
    matched_rows = int(seen.sum())
    return aligned, {
        "source_rows": total_rows,
        "requested_global_keys": len(keys),
        "matched_global_keys": matched_rows,
        "absent_global_keys": len(keys) - matched_rows,
    }


def _install_global_alignment_loader(
    *,
    keys: np.ndarray,
    alignment_receipts: list[dict[str, Any]],
) -> tuple[Any, Any]:
    _, _, engine, _, candidate49, _ = (
        v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    previous = engine._load_filtered_comparison_values_explicit
    expected_keys = np.asarray(keys, dtype=np.int64)

    def load_explicit_with_absent_keys_as_nan(
        manifest: dict[str, Any],
        factors: Iterable[str],
        candidate_keys: np.ndarray,
    ) -> dict[str, np.ndarray]:
        factor_tuple = tuple(str(value) for value in factors)
        observed_keys = np.asarray(candidate_keys, dtype=np.int64)
        if not np.array_equal(observed_keys, expected_keys):
            raise CompactComparatorCacheV2Error(
                "v2 loader was used outside the frozen global eligibility keys"
            )
        records = list(manifest.get("files") or [])
        partitions = manifest.get("partitions")
        rows = manifest.get("rows")
        if (
            not isinstance(partitions, int)
            or not isinstance(rows, int)
            or len(records) != partitions
            or partitions <= 0
            or rows <= 0
        ):
            raise CompactComparatorCacheV2Error(
                "explicit snapshot manifest row or partition count changed"
            )
        paths = [str(Path(str(record["path"])).expanduser().resolve()) for record in records]

        def scan() -> tuple[dict[str, np.ndarray], dict[str, int]]:
            return _scan_explicit_values(
                paths=paths,
                factors=factor_tuple,
                target_keys=expected_keys,
                expected_rows=rows,
            )

        try:
            aligned, counts = scan()
        except InterruptedError as exc:
            is_candidate49 = bool(
                exc.errno == errno.EINTR
                and factor_tuple == (candidate49.FACTOR_NAME,)
                and manifest.get("dataset_sha256")
                == candidate49.CANDIDATE_DATASET_SHA256
            )
            if not is_candidate49:
                raise
            aligned, counts = scan()
        alignment_receipts.append(
            {
                "source_kind": str(manifest.get("kind")),
                "dataset_sha256": str(manifest.get("dataset_sha256")),
                "output_run_id": str(manifest.get("output_run_id", "")),
                "factors": list(factor_tuple),
                **counts,
            }
        )
        return aligned

    engine._load_filtered_comparison_values_explicit = (
        load_explicit_with_absent_keys_as_nan
    )
    return engine, previous


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_sha256": PROTOCOL_SHA256,
        "base_protocol_sha256": V1_PROTOCOL_SHA256,
        "implementation_freeze_sha256": manifest["implementation_freeze"]["sha256"],
        "builder_sha256": manifest["builder"]["sha256"],
        "eligibility_keys_sha256": v1.EXPECTED_KEYS_SHA256,
        "numeric_order_sha256": v1.EXPECTED_NUMERIC_ORDER_SHA256,
        "columns": manifest["columns"],
        "files": manifest["files"],
        "source_verification_receipts_sha256": manifest[
            "source_snapshot_verifications_sha256"
        ],
        "candidate_snapshot_verification_receipt_sha256": manifest[
            "campaign067_snapshot_file_verification_sha256"
        ],
        "source_key_alignment_receipts_sha256": manifest[
            "source_key_alignment_receipts_sha256"
        ],
        "semantic_equivalence_sha256": _json_sha256(
            manifest["semantic_equivalence"]
        ),
    }


def _v2_manifest(
    *,
    names: list[str],
    definitions: list[dict[str, str]],
    keys: np.ndarray,
    matrix: np.ndarray,
    files: list[dict[str, Any]],
    receipts: dict[str, Any],
    candidate_receipt: dict[str, Any],
    equivalence: dict[str, Any],
    alignment_receipts: list[dict[str, Any]],
    freeze_sha256: str,
) -> dict[str, Any]:
    manifest = v1._manifest_core(
        names=names,
        definitions=definitions,
        keys=keys,
        matrix=matrix,
        files=files,
        receipts=receipts,
        candidate_receipt=candidate_receipt,
        equivalence=equivalence,
        freeze_sha256=freeze_sha256,
    )
    manifest.update(
        {
            "schema_version": 2,
            "kind": "a_share_three_day_candidate_independent_compact_comparator_cache_v2",
            "status": "complete_verified_semantically_equivalent_no_return_cache",
            "created_at": _utc_now(),
            "protocol": {
                "path": str(PROTOCOL_PATH.resolve()),
                "sha256": PROTOCOL_SHA256,
            },
            "authoritative_base_protocol": {
                "path": str(v1.PROTOCOL_PATH.resolve()),
                "sha256": V1_PROTOCOL_SHA256,
            },
            "recorded_v1_failure": {
                "path": str(V1_FAILURE_PATH.resolve()),
                "sha256": V1_FAILURE_SHA256,
            },
            "implementation_freeze": {
                "path": str(IMPLEMENTATION_FREEZE_PATH.resolve()),
                "sha256": freeze_sha256,
            },
            "builder": {
                "path": str(Path(__file__).resolve()),
                "sha256": _sha256(Path(__file__).resolve()),
            },
            "source_key_alignment_receipts": alignment_receipts,
            "source_key_alignment_receipts_sha256": _json_sha256(
                alignment_receipts
            ),
            "absent_source_keys_materialized_as_nan": True,
            "imputation_ranking_or_scaling_performed": False,
            "failed_v1_temporary_values_reused": False,
        }
    )
    manifest["dataset_sha256"] = _json_sha256(_dataset_material(manifest))
    return manifest


def build_cache(
    *, data_root: Path, output_root: Path, workers: int, confirm_build: bool
) -> Path:
    if not confirm_build:
        raise CompactComparatorCacheV2Error("v2 build requires --confirm-build")
    load_protocol()
    _load_implementation_freeze()
    data_root = data_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise CompactComparatorCacheV2Error("compact-cache v2 data root changed")
    if output_root != DEFAULT_OUTPUT_ROOT.resolve():
        raise CompactComparatorCacheV2Error("compact-cache v2 output root changed")
    if output_root.exists():
        raise CompactComparatorCacheV2Error("compact-cache v2 output already exists")
    if FAILED_V1_OUTPUT_ROOT.exists():
        raise CompactComparatorCacheV2Error("failed compact-cache v1 root was published")
    definitions, _ = v1.numeric_definitions()
    names = [item["name"] for item in definitions]
    keys = v1.eligible_keys()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.", dir=output_root.parent)
    )
    working_path = temporary_root / "working_matrix.npy"
    matrix = np.lib.format.open_memmap(
        working_path,
        mode="w+",
        dtype=np.float64,
        shape=(len(keys), len(names)),
    )
    alignment_receipts: list[dict[str, Any]] = []
    engine, previous_loader = _install_global_alignment_loader(
        keys=keys,
        alignment_receipts=alignment_receipts,
    )
    try:
        receipts, candidate_receipt, completed = v1._capture_matrix(
            data_root=data_root,
            workers=workers,
            keys=keys,
            matrix=matrix,
            definitions=definitions,
        )
    finally:
        engine._load_filtered_comparison_values_explicit = previous_loader
    files = v1._write_partitions(
        root=temporary_root,
        keys=keys,
        matrix=matrix,
        names=names,
    )
    loaded_keys, loaded_matrix = v1._load_cache_matrix(
        root=temporary_root,
        records=files,
        names=names,
    )
    if not np.array_equal(loaded_keys, keys):
        raise CompactComparatorCacheV2Error("v2 Parquet key round trip changed")
    for index, name in enumerate(names):
        if v1.canonical_column_sha256(
            loaded_matrix[:, index]
        ) != v1.canonical_column_sha256(matrix[:, index]):
            raise CompactComparatorCacheV2Error(
                f"v2 Parquet value round trip changed for {name}"
            )
    equivalence = v1._actual_equivalence(
        keys=loaded_keys,
        matrix=loaded_matrix,
        definitions=definitions,
        completed=completed,
    )
    freeze_sha256 = _sha256(IMPLEMENTATION_FREEZE_PATH)
    manifest = _v2_manifest(
        names=names,
        definitions=definitions,
        keys=loaded_keys,
        matrix=loaded_matrix,
        files=files,
        receipts=receipts,
        candidate_receipt=candidate_receipt,
        equivalence=equivalence,
        alignment_receipts=alignment_receipts,
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
        raise CompactComparatorCacheV2Error("compact-cache v2 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    definitions, _ = v1.numeric_definitions()
    names = [item["name"] for item in definitions]
    alignments = manifest.get("source_key_alignment_receipts") or []
    if not (
        manifest.get("schema_version") == 2
        and manifest.get("kind")
        == "a_share_three_day_candidate_independent_compact_comparator_cache_v2"
        and manifest.get("status")
        == "complete_verified_semantically_equivalent_no_return_cache"
        and (manifest.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (manifest.get("authoritative_base_protocol") or {}).get("sha256")
        == V1_PROTOCOL_SHA256
        and (manifest.get("recorded_v1_failure") or {}).get("sha256")
        == V1_FAILURE_SHA256
        and (manifest.get("builder") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and manifest.get("numeric_comparator_count") == v1.EXPECTED_NUMERIC_COUNT
        and manifest.get("numeric_comparator_order_sha256")
        == v1.EXPECTED_NUMERIC_ORDER_SHA256
        and manifest.get("absent_source_keys_materialized_as_nan") is True
        and manifest.get("imputation_ranking_or_scaling_performed") is False
        and manifest.get("failed_v1_temporary_values_reused") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("provider_request_issued") is False
        and alignments
        and manifest.get("source_key_alignment_receipts_sha256")
        == _json_sha256(alignments)
        and all(
            item.get("requested_global_keys") == v1.EXPECTED_ROWS
            and item.get("matched_global_keys", -1) >= 0
            and item.get("absent_global_keys", -1) >= 0
            and item.get("matched_global_keys") + item.get("absent_global_keys")
            == v1.EXPECTED_ROWS
            for item in alignments
        )
        and manifest.get("dataset_sha256")
        == _json_sha256(_dataset_material(manifest))
    ):
        raise CompactComparatorCacheV2Error("compact-cache v2 manifest changed")
    completed = v1._completed_audit()
    expected_receipts = completed["uniqueness"][v1.FACTOR_NAME][
        "source_snapshot_verifications"
    ]
    if not (
        manifest.get("source_snapshot_verifications") == expected_receipts
        and manifest.get("source_snapshot_verifications_sha256")
        == _json_sha256(expected_receipts)
        and manifest.get("campaign067_snapshot_file_verification")
        == completed["snapshot_file_verification"]
    ):
        raise CompactComparatorCacheV2Error("compact-cache v2 source receipts changed")
    keys, matrix = v1._load_cache_matrix(
        root=manifest_path.parent,
        records=list(manifest["files"]),
        names=names,
    )
    if hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest() != (
        v1.EXPECTED_KEYS_SHA256
    ):
        raise CompactComparatorCacheV2Error("compact-cache v2 keys changed")
    for index, record in enumerate(manifest["columns"]):
        values = matrix[:, index]
        if not (
            record.get("name") == names[index]
            and record.get("score_direction")
            == definitions[index]["score_direction"]
            and record.get("finite_rows") == int(np.isfinite(values).sum())
            and record.get("nonfinite_rows") == int((~np.isfinite(values)).sum())
            and record.get("canonical_value_sha256")
            == v1.canonical_column_sha256(values)
        ):
            raise CompactComparatorCacheV2Error(
                f"compact-cache v2 column changed at {names[index]}"
            )
    if full_equivalence:
        recomputed = v1._actual_equivalence(
            keys=keys,
            matrix=matrix,
            definitions=definitions,
            completed=completed,
        )
        if recomputed != manifest["semantic_equivalence"]:
            raise CompactComparatorCacheV2Error(
                "compact-cache v2 full semantic equivalence changed"
            )
    result = {
        "status": "verified",
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "dataset_sha256": manifest["dataset_sha256"],
        "rows": len(keys),
        "numeric_comparator_count": len(names),
        "alignment_receipt_count": len(alignments),
        "alignment_receipts_with_absent_keys": sum(
            int(item["absent_global_keys"] > 0) for item in alignments
        ),
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
        "v1_output_exists": FAILED_V1_OUTPUT_ROOT.exists(),
        "v2_output_exists": DEFAULT_OUTPUT_ROOT.exists(),
        "v2_manifest_exists": manifest.is_file(),
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
