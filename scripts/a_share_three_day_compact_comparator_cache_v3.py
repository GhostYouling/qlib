#!/usr/bin/env python3
"""Build and verify the additive v3 capture-proxy cache repair."""

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

from scripts import a_share_three_day_compact_comparator_cache as v1
from scripts import a_share_three_day_compact_comparator_cache_v2 as v2


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_protocol_v3_20260805.json"
)
PROTOCOL_SHA256 = "44b5274de5684ca29e7ee9b290072412b1d97428b70e64711b979cac154d0841"
V2_PROTOCOL_SHA256 = v2.PROTOCOL_SHA256
V2_BUILDER_SHA256 = "eb4a2873bc6120c33860b93288dc19185b2e7afe796a4389c94a5ec6f207ae20"
V2_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_v2_build_failure_20260805.json"
)
V2_FAILURE_SHA256 = "89810370270b9718d5e5161462f45483dde58e89f0670a5124ec6aa26560f24c"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_implementation_freeze_v3_20260805.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_compact_comparator_cache_v3.py"
)
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
DEFAULT_OUTPUT_ROOT = (
    DEFAULT_DATA_ROOT
    / "derived/a_share/rich/tushare/compact_comparator_cache/"
    "campaign067_terminal_numeric98_v3"
)
FAILED_OUTPUT_ROOTS = (v1.DEFAULT_OUTPUT_ROOT, v2.DEFAULT_OUTPUT_ROOT)


class CompactComparatorCacheV3Error(RuntimeError):
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
        raise CompactComparatorCacheV3Error(f"{label} changed")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_protocol() -> dict[str, Any]:
    _require(PROTOCOL_PATH, PROTOCOL_SHA256, "compact-cache v3 protocol")
    _require(V2_FAILURE_PATH, V2_FAILURE_SHA256, "compact-cache v2 failure")
    if _sha256(Path(v2.__file__).resolve()) != V2_BUILDER_SHA256:
        raise CompactComparatorCacheV3Error("frozen compact-cache v2 builder changed")
    inherited = v2.load_protocol()
    spec = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    chain = spec.get("authoritative_protocol_chain") or []
    failure = spec.get("recorded_v2_failure") or {}
    output = spec.get("frozen_output") or {}
    audit = spec.get("post_campaign057_engine_member_audit") or {}
    proxy = spec.get("capture_proxy_contract") or {}
    library = spec.get("frozen_library_and_keys") or {}
    equivalence = spec.get("semantic_equivalence_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_candidate_independent_compact_comparator_cache_protocol"
        and spec.get("status") == "frozen_capture_proxy_repair_before_v3_values"
        and [item.get("sha256") for item in chain]
        == [v1.PROTOCOL_SHA256, V2_PROTOCOL_SHA256]
        and failure.get("sha256") == V2_FAILURE_SHA256
        and failure.get("v2_formal_output_published") is False
        and failure.get("v2_temporary_values_reusable") is False
        and output.get("output_root") == str(DEFAULT_OUTPUT_ROOT)
        and audit.get("members_observed")
        == ["_aligned_comparison_result", "_compact_stock_day_keys"]
        and audit.get("delegated_read_only_helper_members")
        == ["_compact_stock_day_keys"]
        and audit.get("other_members_allowed") is False
        and proxy.get("attribute_fallback_allowed") is False
        and proxy.get("factor_values_may_be_transformed_by_proxy") is False
        and library.get("eligibility_rows") == v1.EXPECTED_ROWS
        and library.get("eligibility_keys_sha256") == v1.EXPECTED_KEYS_SHA256
        and library.get("numeric_comparator_count") == v1.EXPECTED_NUMERIC_COUNT
        and library.get("numeric_order_sha256") == v1.EXPECTED_NUMERIC_ORDER_SHA256
        and library.get("complete_definition_count") == v1.EXPECTED_COMPLETE_COUNT
        and library.get("complete_definition_order_sha256")
        == v1.EXPECTED_COMPLETE_ORDER_SHA256
        and equivalence.get("campaign067_comparison_count") == 97
        and equivalence.get("campaign067_comparison_result_objects_exact_equality_required")
        is True
        and boundary.get("v3_comparison_values_read_before_protocol_freeze") is False
        and boundary.get("historical_daily_price_fields_read") == []
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("provider_request_issued") is False
        and isinstance(inherited, dict)
    ):
        raise CompactComparatorCacheV3Error("compact-cache v3 protocol changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise CompactComparatorCacheV3Error(
            "compact-cache v3 implementation freeze is absent"
        )
    record = json.loads(IMPLEMENTATION_FREEZE_PATH.read_text(encoding="utf-8"))
    if not (
        record.get("version") == 3
        and record.get("kind")
        == "a_share_three_day_compact_comparator_cache_implementation_freeze"
        and record.get("status")
        == "frozen_before_v3_comparator_values_or_cache_files_materialized"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("builder") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("v3_cache_output_existed_before_freeze") is False
        and record.get("v3_comparison_factor_values_read_before_freeze") is False
        and record.get("historical_daily_price_or_forward_return_values_read_before_freeze")
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise CompactComparatorCacheV3Error(
            "compact-cache v3 implementation freeze changed"
        )
    return record


class _DelegatingCaptureComparisonEngine(v1._CaptureComparisonEngine):
    """The v1 sink plus the sole helper required by Campaign058."""

    def __init__(self, *, delegate: Any, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._delegate = delegate

    def _compact_stock_day_keys(self, trade_dates: Any, symbols: Any) -> np.ndarray:
        return self._delegate._compact_stock_day_keys(trade_dates, symbols)


def _capture_matrix(
    *,
    data_root: Path,
    workers: int,
    keys: np.ndarray,
    matrix: np.memmap,
    definitions: list[dict[str, str]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    completed = v1._completed_audit()
    factor_result = completed["uniqueness"][v1.FACTOR_NAME]
    expected_receipts = factor_result["source_snapshot_verifications"]
    _, _, engine, _, candidate49, comparison_engine = (
        v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    spec = v1.audit.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    directions = {
        str(item["name"]): str(item["score_direction"])
        for item in gate["comparison_factors"]
    }
    capture = _DelegatingCaptureComparisonEngine(
        delegate=comparison_engine,
        keys=keys,
        matrix=matrix,
        definitions=definitions[:-1],
    )
    dummy_values = np.zeros(len(keys), dtype=np.float64)
    captured, receipts = v1.audit._append_prior_numeric_comparisons(
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
    expected_order = [item["name"] for item in definitions[:-1]]
    observed_order = [str(item["comparison_factor"]) for item in captured]
    if not (
        observed_order == expected_order
        and capture.seen == expected_order
        and receipts == expected_receipts
    ):
        raise CompactComparatorCacheV3Error(
            "v3 inherited capture order or source receipt changed"
        )
    candidate_receipt = v1.candidate.verify_snapshot_files(
        v1.audit.SNAPSHOT_MANIFEST_PATH,
        workers=workers,
    )
    if candidate_receipt != completed["snapshot_file_verification"]:
        raise CompactComparatorCacheV3Error(
            "v3 Campaign067 candidate source receipt changed"
        )
    manifest = json.loads(
        v1.audit.SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    candidate_values = engine._load_filtered_comparison_values_explicit(
        manifest,
        [v1.FACTOR_NAME],
        keys,
    )[v1.FACTOR_NAME]
    if np.asarray(candidate_values).shape != (len(keys),):
        raise CompactComparatorCacheV3Error("v3 Campaign067 values changed")
    matrix[:, -1] = np.asarray(candidate_values, dtype=np.float64)
    matrix.flush()
    del candidate_values, dummy_values
    gc.collect()
    return receipts, candidate_receipt, completed


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_sha256": PROTOCOL_SHA256,
        "v1_protocol_sha256": v1.PROTOCOL_SHA256,
        "v2_protocol_sha256": V2_PROTOCOL_SHA256,
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


def _manifest(
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
    manifest = v2._v2_manifest(
        names=names,
        definitions=definitions,
        keys=keys,
        matrix=matrix,
        files=files,
        receipts=receipts,
        candidate_receipt=candidate_receipt,
        equivalence=equivalence,
        alignment_receipts=alignment_receipts,
        freeze_sha256=freeze_sha256,
    )
    manifest.update(
        {
            "schema_version": 3,
            "kind": "a_share_three_day_candidate_independent_compact_comparator_cache_v3",
            "created_at": _utc_now(),
            "protocol": {
                "path": str(PROTOCOL_PATH.resolve()),
                "sha256": PROTOCOL_SHA256,
            },
            "authoritative_protocol_chain": [
                {
                    "path": str(v1.PROTOCOL_PATH.resolve()),
                    "sha256": v1.PROTOCOL_SHA256,
                },
                {
                    "path": str(v2.PROTOCOL_PATH.resolve()),
                    "sha256": V2_PROTOCOL_SHA256,
                },
            ],
            "recorded_v2_failure": {
                "path": str(V2_FAILURE_PATH.resolve()),
                "sha256": V2_FAILURE_SHA256,
            },
            "implementation_freeze": {
                "path": str(IMPLEMENTATION_FREEZE_PATH.resolve()),
                "sha256": freeze_sha256,
            },
            "builder": {
                "path": str(Path(__file__).resolve()),
                "sha256": _sha256(Path(__file__).resolve()),
            },
            "capture_proxy": {
                "sink": "v1._CaptureComparisonEngine._aligned_comparison_result",
                "delegated_helpers": ["_compact_stock_day_keys"],
                "attribute_fallback_allowed": False,
            },
            "failed_v2_temporary_values_reused": False,
        }
    )
    manifest["dataset_sha256"] = _json_sha256(_dataset_material(manifest))
    return manifest


def build_cache(
    *, data_root: Path, output_root: Path, workers: int, confirm_build: bool
) -> Path:
    if not confirm_build:
        raise CompactComparatorCacheV3Error("v3 build requires --confirm-build")
    load_protocol()
    _load_implementation_freeze()
    data_root = data_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise CompactComparatorCacheV3Error("compact-cache v3 data root changed")
    if output_root != DEFAULT_OUTPUT_ROOT.resolve():
        raise CompactComparatorCacheV3Error("compact-cache v3 output root changed")
    if output_root.exists():
        raise CompactComparatorCacheV3Error("compact-cache v3 output already exists")
    if any(path.exists() for path in FAILED_OUTPUT_ROOTS):
        raise CompactComparatorCacheV3Error("a failed v1/v2 formal root was published")
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
    engine, previous_loader = v2._install_global_alignment_loader(
        keys=keys,
        alignment_receipts=alignment_receipts,
    )
    try:
        receipts, candidate_receipt, completed = _capture_matrix(
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
        raise CompactComparatorCacheV3Error("v3 Parquet key round trip changed")
    for index, name in enumerate(names):
        if v1.canonical_column_sha256(
            loaded_matrix[:, index]
        ) != v1.canonical_column_sha256(matrix[:, index]):
            raise CompactComparatorCacheV3Error(
                f"v3 Parquet value round trip changed for {name}"
            )
    equivalence = v1._actual_equivalence(
        keys=loaded_keys,
        matrix=loaded_matrix,
        definitions=definitions,
        completed=completed,
    )
    freeze_sha256 = _sha256(IMPLEMENTATION_FREEZE_PATH)
    manifest = _manifest(
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
        raise CompactComparatorCacheV3Error("compact-cache v3 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    definitions, _ = v1.numeric_definitions()
    names = [item["name"] for item in definitions]
    alignments = manifest.get("source_key_alignment_receipts") or []
    proxy = manifest.get("capture_proxy") or {}
    if not (
        manifest.get("schema_version") == 3
        and manifest.get("kind")
        == "a_share_three_day_candidate_independent_compact_comparator_cache_v3"
        and manifest.get("status")
        == "complete_verified_semantically_equivalent_no_return_cache"
        and (manifest.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (manifest.get("recorded_v2_failure") or {}).get("sha256")
        == V2_FAILURE_SHA256
        and (manifest.get("builder") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and manifest.get("numeric_comparator_count") == v1.EXPECTED_NUMERIC_COUNT
        and manifest.get("numeric_comparator_order_sha256")
        == v1.EXPECTED_NUMERIC_ORDER_SHA256
        and proxy.get("delegated_helpers") == ["_compact_stock_day_keys"]
        and proxy.get("attribute_fallback_allowed") is False
        and manifest.get("absent_source_keys_materialized_as_nan") is True
        and manifest.get("imputation_ranking_or_scaling_performed") is False
        and manifest.get("failed_v1_temporary_values_reused") is False
        and manifest.get("failed_v2_temporary_values_reused") is False
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
        raise CompactComparatorCacheV3Error("compact-cache v3 manifest changed")
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
        raise CompactComparatorCacheV3Error("compact-cache v3 source receipts changed")
    keys, matrix = v1._load_cache_matrix(
        root=manifest_path.parent,
        records=list(manifest["files"]),
        names=names,
    )
    if hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest() != (
        v1.EXPECTED_KEYS_SHA256
    ):
        raise CompactComparatorCacheV3Error("compact-cache v3 keys changed")
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
            raise CompactComparatorCacheV3Error(
                f"compact-cache v3 column changed at {names[index]}"
            )
    if full_equivalence:
        recomputed = v1._actual_equivalence(
            keys=keys,
            matrix=matrix,
            definitions=definitions,
            completed=completed,
        )
        if recomputed != manifest["semantic_equivalence"]:
            raise CompactComparatorCacheV3Error(
                "compact-cache v3 full semantic equivalence changed"
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
        "failed_formal_outputs_exist": any(path.exists() for path in FAILED_OUTPUT_ROOTS),
        "v3_output_exists": DEFAULT_OUTPUT_ROOT.exists(),
        "v3_manifest_exists": manifest.is_file(),
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
