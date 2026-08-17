#!/usr/bin/env python3
"""Build Campaign085's frozen event-freshness/late-drift product snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts import a_share_three_day_compact_comparator_cache as cache_v1
from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign084_features as c84

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_085_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_085_feature_implementation_freeze_v3_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign085_features.py"
)
PROTOCOL_SHA256 = "c08bf9ec921e97ceafa44b143ef6da0bee8223b65841f09093a01358f61936e6"
MECHANISM_AUDIT_SHA256 = (
    "fea50eab003c24c6c893a7c169744988219f88b9ba866d16c8ed960349d7518f"
)
CURRENT_STATE_SHA256 = (
    "48b59866a0cf777ad05ee8a5f7b7652b460e30db097b1eb3525f2a55b8ac317e"
)
NUMERIC_POLICY_SHA256 = (
    "4dda0043a129dd6d986dfec75bb032b4df81c3648e01e7109c10cd97cf5d294d"
)
CACHE_PUBLICATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_v4_publication_binding_20260806.json"
)
CACHE_PUBLICATION_BINDING_SHA256 = (
    "244f70b88be0396f7473c6664835cbb3cdad9135b6692b77c74018b1d53c925b"
)
CACHE_MANIFEST_PATH = (
    DEFAULT_DATA_ROOT / "derived/a_share/rich/tushare/compact_comparator_cache/"
    "campaign067_terminal_numeric98_v4/snapshot_manifest.json"
)
CACHE_MANIFEST_SHA256 = (
    "3d81068f07ac61fe4cd04bd1a893e58759c06d88213263135fec5244e309b57b"
)
CACHE_DATASET_SHA256 = (
    "4a56dac48c14b667b6ee431519266f27bb8ff7cc25c51d8dce3bbc7aebe0376f"
)
EXPECTED_ROWS = 1_331_759
EXPECTED_PARTITIONS = 7
EXPECTED_SESSIONS = 1_632
FULL_DEFINITION_COUNT = 116
FULL_DEFINITION_ORDER_SHA256 = (
    "d30cad0f1e422e3e4ba80392f42316a968511f53593e1826c1c1bb7171d04253"
)
COMPARISON_COUNT = 114
COMPARISON_ORDER_SHA256 = (
    "03a0c534f3bc321d5bc452415e6207026030978c4ac5d433305b04a21db6cea9"
)
FACTOR_NAME = "quarterly_freshness_market_neutral_late_drift_confirmation_product_2r"
FACTOR_FORMULA = "r_freshness*r_late_residual"
INPUT_FACTORS = (
    "quarterly_announcement_freshness_60s",
    "intraday_market_neutral_late_residual_drift_238m",
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_"
    "campaign085_feature_library_v1"
)
OUTPUT_COLUMNS = ("stock_day_key", FACTOR_NAME, f"{FACTOR_NAME}_eligible")


class Campaign085FeatureError(RuntimeError):
    """Fail-closed Campaign085 feature error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    return _json_digest(
        [[str(item["name"]), str(item["score_direction"])] for item in items]
    )


def _frame_sha256(frame: pd.DataFrame) -> str:
    sink = pa.BufferOutputStream()
    table = pa.Table.from_pandas(frame, preserve_index=False)
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    return hashlib.sha256(sink.getvalue().to_pybytes()).hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign085FeatureError(f"Campaign085 {label} changed: {path}")


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = c84.reconstruct_comparisons()
    items.append({"name": c84.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _comparison_order_digest(items) != COMPARISON_ORDER_SHA256
        or items[-1] != {"name": c84.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign085FeatureError("Campaign085 comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = c84.reconstruct_complete_definitions()
    items.append({"name": c84.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _comparison_order_digest(items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign085FeatureError("Campaign085 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    _require(
        CACHE_PUBLICATION_BINDING,
        CACHE_PUBLICATION_BINDING_SHA256,
        "compact-cache publication binding",
    )
    _require(CACHE_MANIFEST_PATH, CACHE_MANIFEST_SHA256, "compact-cache manifest")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign085FeatureError("Campaign085 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    cache = json.loads(CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign085_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign085_compact_cache_candidate_comparison_daily_price_or_return_values"
        and (chain.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and (chain.get("numeric_comparator_policy_v20") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and (chain.get("compact_comparator_cache_v4_publication_binding") or {}).get(
            "sha256"
        )
        == CACHE_PUBLICATION_BINDING_SHA256
        and (chain.get("compact_comparator_cache_v4_manifest") or {}).get(
            "dataset_sha256"
        )
        == CACHE_DATASET_SHA256
        and cache.get("dataset_sha256") == CACHE_DATASET_SHA256
        and (cache.get("eligibility") or {}).get("rows") == EXPECTED_ROWS
        and len(cache.get("files") or []) == EXPECTED_PARTITIONS
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("source_value_projection") or ()) == INPUT_FACTORS
        and candidate.get("combination_rule", "").startswith(
            "Exactly r_freshness * r_late_residual"
        )
        and candidate.get("campaign084_factor_used_or_combined") is False
        and candidate.get("valid_range")
        == {
            "lower": 0.0,
            "lower_inclusive": False,
            "upper": 1.0,
            "upper_inclusive": True,
        }
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and unique.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and unique.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and unique.get("numeric_comparator_count") == COMPARISON_COUNT
        and unique.get("numeric_comparator_order_sha256") == COMPARISON_ORDER_SHA256
        and unique.get("all_114_numeric_comparators_must_pass") is True
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and finite.get("trial_id")
        == "wf085_quarterly_freshness_market_neutral_late_drift_confirmation_product_2r_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("expected_trial_count") == 1
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign085FeatureError("Campaign085 protocol semantics changed")
    return spec


def compute_confirmation_product(
    ranks: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(ranks, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 2:
        raise Campaign085FeatureError("confirmation product requires n-by-2 ranks")
    eligible = np.isfinite(values).all(axis=1) & (
        ((values > 0.0) & (values <= 1.0)).all(axis=1)
    )
    result = np.full(len(values), np.nan, dtype=np.float64)
    result[eligible] = values[eligible, 0] * values[eligible, 1]
    if ((result[eligible] <= 0.0) | (result[eligible] > 1.0)).any():
        raise Campaign085FeatureError("confirmation product escaped (0,1]")
    return result, eligible


def rank_and_product_cache_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = ("stock_day_key", *INPUT_FACTORS)
    if tuple(frame.columns) != required:
        raise Campaign085FeatureError("compact-cache source projection changed")
    work = frame.copy()
    keys = pd.to_numeric(work["stock_day_key"], errors="coerce")
    if (
        keys.isna().any()
        or work.empty
        or keys.duplicated().any()
        or not keys.is_monotonic_increasing
    ):
        raise Campaign085FeatureError("compact-cache stock-day identities changed")
    work["stock_day_key"] = keys.astype(np.int64)
    source = work.loc[:, INPUT_FACTORS].apply(pd.to_numeric, errors="coerce")
    common = np.isfinite(source.to_numpy(dtype=np.float64)).all(axis=1)
    selected = work.loc[common, ["stock_day_key"]].copy()
    selected["_session"] = selected["stock_day_key"] // 4_000_000
    ranks = [
        source.loc[common, name]
        .groupby(selected["_session"], sort=False)
        .rank(method="average", pct=True)
        for name in INPUT_FACTORS
    ]
    rank_matrix = np.column_stack([rank.to_numpy(dtype=np.float64) for rank in ranks])
    selected_values, selected_eligible = compute_confirmation_product(rank_matrix)
    values = np.full(len(work), np.nan, dtype=np.float64)
    eligible = np.zeros(len(work), dtype=bool)
    positions = np.flatnonzero(common)
    values[positions] = selected_values
    eligible[positions] = selected_eligible
    result = pd.DataFrame(
        {
            "stock_day_key": work["stock_day_key"].to_numpy(dtype=np.int64),
            FACTOR_NAME: values,
            f"{FACTOR_NAME}_eligible": eligible,
        }
    )
    return result.loc[:, OUTPUT_COLUMNS]


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_walkforward_campaign085_feature_library"
        / OUTPUT_RUN_ID
    )


def _prepare_temporary_root(root: Path) -> Path:
    root.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{root.name}.", dir=root.parent))


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    temporary_path = Path(temporary)
    try:
        pq.write_table(
            pa.Table.from_pandas(frame, preserve_index=False),
            temporary_path,
            compression="zstd",
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    temporary_path = Path(temporary)
    try:
        temporary_path.write_text(text, encoding="utf-8")
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _load_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign085FeatureError("Campaign085 implementation freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign085_feature_implementation_freeze"
        and record.get("status")
        == "frozen_v3_parent_and_handshake_repair_before_compact_cache_rows_candidate_or_comparison_values"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("compact_cache_rows_read_before_freeze") is False
        and record.get("candidate_values_computed_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign085FeatureError("Campaign085 implementation freeze changed")
    return record


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_sha256": manifest["protocol"]["sha256"],
        "implementation_freeze_sha256": manifest["implementation_freeze"]["sha256"],
        "source_manifest_sha256": manifest["source_cache"]["sha256"],
        "source_dataset_sha256": manifest["source_cache"]["dataset_sha256"],
        "factor_name": FACTOR_NAME,
        "factor_formula": FACTOR_FORMULA,
        "factor_eligible_rows": manifest["factor_eligible_rows"][FACTOR_NAME],
        "files": manifest["files"],
    }


def build_snapshot(*, data_root: Path, confirm_build: bool = False) -> Path:
    if not confirm_build:
        raise Campaign085FeatureError("Campaign085 build requires --confirm-build")
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign085FeatureError("Campaign085 data root changed")
    load_protocol()
    freeze = _load_implementation_freeze()
    root = output_root(data_root)
    if root.exists():
        raise Campaign085FeatureError("Campaign085 output already exists")
    cache = json.loads(CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    source_root = CACHE_MANIFEST_PATH.parent
    temporary_root = _prepare_temporary_root(root)
    records: list[dict[str, Any]] = []
    total_rows = 0
    total_eligible = 0
    all_keys: list[np.ndarray] = []
    try:
        for source in cache.get("files") or []:
            source_path = source_root / str(source["path"])
            if _sha256(source_path) != source.get("sha256"):
                raise Campaign085FeatureError("compact-cache partition bytes changed")
            projected = pd.read_parquet(
                source_path, columns=["stock_day_key", *INPUT_FACTORS]
            )
            out = rank_and_product_cache_frame(projected)
            year = int(source["year"])
            relative = Path("partitions") / f"{year}.parquet"
            destination = temporary_root / relative
            _atomic_parquet(out, destination)
            eligible = int(out[f"{FACTOR_NAME}_eligible"].sum())
            values = out[FACTOR_NAME].to_numpy(dtype=np.float64)
            keys = out["stock_day_key"].to_numpy(dtype=np.int64)
            records.append(
                {
                    "path": str(relative),
                    "year": year,
                    "rows": len(out),
                    "eligible_rows": eligible,
                    "sha256": _sha256(destination),
                    "frame_sha256": _frame_sha256(out),
                    "factor_canonical_value_sha256": cache_v1.canonical_column_sha256(
                        values
                    ),
                    "source_path": str(source["path"]),
                    "source_sha256": str(source["sha256"]),
                }
            )
            total_rows += len(out)
            total_eligible += eligible
            all_keys.append(keys)
        keys = np.concatenate(all_keys)
        if not (
            total_rows == EXPECTED_ROWS
            and len(records) == EXPECTED_PARTITIONS
            and len(np.unique(keys)) == EXPECTED_ROWS
            and np.all(keys[1:] > keys[:-1])
            and len(np.unique(keys // 4_000_000)) == EXPECTED_SESSIONS
        ):
            raise Campaign085FeatureError("Campaign085 aggregate keys changed")
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign085_feature_snapshot",
            "status": "complete_no_return_candidate_snapshot",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "protocol": {
                "path": str(DEFAULT_PROTOCOL.resolve()),
                "sha256": PROTOCOL_SHA256,
            },
            "implementation_freeze": {
                "path": str(DEFAULT_IMPLEMENTATION_FREEZE.resolve()),
                "sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
            },
            "feature_runner": {
                "path": str(Path(__file__).resolve()),
                "sha256": _sha256(Path(__file__).resolve()),
            },
            "source_cache": {
                "path": str(CACHE_MANIFEST_PATH.resolve()),
                "sha256": CACHE_MANIFEST_SHA256,
                "dataset_sha256": CACHE_DATASET_SHA256,
                "columns_read": ["stock_day_key", *INPUT_FACTORS],
                "all_other_comparator_columns_read": False,
            },
            "factor_names": [FACTOR_NAME],
            "factor_directions": {FACTOR_NAME: "higher"},
            "factor_formulas": {FACTOR_NAME: FACTOR_FORMULA},
            "rows": total_rows,
            "partitions": len(records),
            "calendar_sessions": len(np.unique(keys // 4_000_000)),
            "eligibility_keys_sha256": hashlib.sha256(
                keys.astype("<i8", copy=False).tobytes()
            ).hexdigest(),
            "factor_eligible_rows": {FACTOR_NAME: total_eligible},
            "factor_missing_rows": {FACTOR_NAME: total_rows - total_eligible},
            "files": records,
            "comparison_values_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_returns_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "implementation_freeze_status": freeze["status"],
        }
        manifest["dataset_sha256"] = _json_digest(_dataset_material(manifest))
        manifest_path = temporary_root / "snapshot_manifest.json"
        _atomic_json(manifest, manifest_path)
        root.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary_root, root)
        return root / "snapshot_manifest.json"
    except Exception:
        for path in sorted(temporary_root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        temporary_root.rmdir()
        raise


def verify_snapshot_files(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    if manifest_path != expected.resolve() or not manifest_path.is_file():
        raise Campaign085FeatureError("Campaign085 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign085_feature_snapshot"
        and manifest.get("status") == "complete_no_return_candidate_snapshot"
        and (manifest.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (manifest.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (manifest.get("source_cache") or {}).get("sha256") == CACHE_MANIFEST_SHA256
        and (manifest.get("source_cache") or {}).get("dataset_sha256")
        == CACHE_DATASET_SHA256
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("comparison_values_read") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("dataset_sha256") == _json_digest(_dataset_material(manifest))
    ):
        raise Campaign085FeatureError("Campaign085 manifest semantics changed")
    rows = 0
    eligible = 0
    all_keys: list[np.ndarray] = []
    for record in manifest.get("files") or []:
        path = manifest_path.parent / str(record["path"])
        if _sha256(path) != record.get("sha256"):
            raise Campaign085FeatureError("Campaign085 partition bytes changed")
        frame = pd.read_parquet(path, columns=list(OUTPUT_COLUMNS))
        if _frame_sha256(frame) != record.get("frame_sha256"):
            raise Campaign085FeatureError("Campaign085 partition frame changed")
        values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce").to_numpy(
            dtype=np.float64
        )
        flags = frame[f"{FACTOR_NAME}_eligible"].astype(bool).to_numpy()
        finite = np.isfinite(values)
        if not (
            np.array_equal(flags, finite)
            and ((values[finite] > 0.0) & (values[finite] <= 1.0)).all()
            and int(flags.sum()) == int(record["eligible_rows"])
            and cache_v1.canonical_column_sha256(values)
            == record.get("factor_canonical_value_sha256")
        ):
            raise Campaign085FeatureError("Campaign085 partition values changed")
        rows += len(frame)
        eligible += int(flags.sum())
        all_keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
    keys = np.concatenate(all_keys)
    if not (
        rows == EXPECTED_ROWS
        and eligible == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        and len(np.unique(keys)) == EXPECTED_ROWS
        and np.all(keys[1:] > keys[:-1])
        and hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest()
        == manifest.get("eligibility_keys_sha256")
    ):
        raise Campaign085FeatureError("Campaign085 aggregate verification changed")
    return {
        "status": "verified",
        "dataset_sha256": manifest["dataset_sha256"],
        "partitions": len(manifest["files"]),
        "rows": rows,
        "eligible_rows": eligible,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def status(data_root: Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    load_protocol()
    manifest_path = (
        output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    )
    return {
        "status": (
            "snapshot_present"
            if manifest_path.is_file()
            else "snapshot_absent_pre_build"
        ),
        "manifest_path": str(manifest_path),
        "compact_cache_rows_read": False,
        "candidate_values_computed": False,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "build", "verify"))
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--confirm-build", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        payload = status(args.data_root)
    elif args.command == "build":
        path = build_snapshot(
            data_root=args.data_root, confirm_build=args.confirm_build
        )
        payload = {"status": "built", "manifest_path": str(path)}
    else:
        manifest = args.manifest or (
            output_root(args.data_root) / "snapshot_manifest.json"
        )
        payload = verify_snapshot_files(manifest)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
