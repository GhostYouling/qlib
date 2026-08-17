#!/usr/bin/env python3
"""Build and verify Campaign136's frozen daily price-basis feature snapshot."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import a_share_three_day_walkforward_campaign136_formula as formula


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DAILY_ROOT = REPO_ROOT / "data/raw/a_share/daily"
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_136/source_snapshot_v1"
)
PRICE_BASIS_MANIFEST = REPO_ROOT / "data/qlib/cn_a_share/price_basis.json"
CALENDAR_PATH = REPO_ROOT / "data/qlib/cn_a_share/calendars/day.txt"
UNIVERSE_PATH = (
    REPO_ROOT / "data/qlib/cn_a_share/instruments/factor_main_chinext_star.txt"
)
FORMULA_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_136_formula_implementation_freeze_v2_20260814.json"
)
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_136_source_bound_implementation_freeze_v3_20260814.json"
)
FEATURE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign136_features.py"
)
FORMULA_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign136_formula.py"
)

PROTOCOL_SHA256 = formula.PROTOCOL_SHA256
FORMULA_SHA256 = "4a57b79716269cf3acd21bb7b6909ce80ab5378f89d25fb27d97a02f815e7b66"
FORMULA_FREEZE_SHA256 = (
    "207cb1771f99f42738cce2c3bbfbf88a454a92daa77a7e099f126ac1e8815ec6"
)
PRICE_BASIS_MANIFEST_SHA256 = (
    "68e9dbb83749779b34d5cf3b116195074c154ff74cb6de95ba67695bedc1f14f"
)
CALENDAR_SHA256 = "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
UNIVERSE_SHA256 = "cdded13c831b78045f4cfe80ba5d9a49f82152c615fef4267d00f992e7f53762"
SOURCE_FILE_COUNT = 5451
SOURCE_TOTAL_BYTES = 1502484498
SOURCE_IDENTITY_SHA256 = (
    "d7dca618dbef6620e1c4782cb970178afa5777e3f1101a916df5eb6b8bf37cab"
)
OUTPUT_START = pd.Timestamp("2019-01-01")
OUTPUT_END = pd.Timestamp("2025-12-31")
SOURCE_COLUMNS = ("date", "symbol", "factor", "price_basis", "daily_source")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    formula.FACTOR_NAME,
    f"{formula.FACTOR_NAME}_eligible",
)
MANIFEST_NAME = "snapshot_manifest.json"


class Campaign136FeatureError(RuntimeError):
    """Fail closed when a frozen Campaign136 source or output invariant changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign136FeatureError(f"Campaign136 {label} binding changed")


def load_calendar(path: Path = CALENDAR_PATH) -> pd.DatetimeIndex:
    require_file(path, CALENDAR_SHA256, "calendar")
    values = pd.to_datetime(
        [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ],
        errors="raise",
    ).normalize()
    calendar = pd.DatetimeIndex(values).sort_values().unique()
    if len(calendar) < 2 or calendar.has_duplicates:
        raise Campaign136FeatureError("Campaign136 calendar is invalid")
    return calendar


def source_identity(root: Path) -> dict[str, Any]:
    files = sorted(root.glob("*.parquet"))
    items: list[list[Any]] = []
    total_bytes = 0
    for path in files:
        size = path.stat().st_size
        total_bytes += size
        items.append([path.name, size, file_sha256(path)])
    return {
        "file_count": len(files),
        "total_bytes": total_bytes,
        "file_identity_order_sha256": canonical_sha256(items),
        "files": files,
    }


def _validate_source_schemas(files: Iterable[Path]) -> None:
    required = set(SOURCE_COLUMNS)
    for path in files:
        names = set(pq.ParquetFile(path).schema_arrow.names)
        if not required.issubset(names):
            raise Campaign136FeatureError(
                f"Campaign136 required source schema missing for {path.name}"
            )


def validate_protocol() -> dict[str, Any]:
    try:
        spec = formula.load_protocol()
    except formula.Campaign136FormulaError as exc:
        raise Campaign136FeatureError(str(exc)) from exc
    require_file(Path(formula.__file__).resolve(), FORMULA_SHA256, "formula")
    require_file(FORMULA_FREEZE, FORMULA_FREEZE_SHA256, "formula freeze")
    require_file(
        PRICE_BASIS_MANIFEST,
        PRICE_BASIS_MANIFEST_SHA256,
        "price-basis manifest",
    )
    require_file(UNIVERSE_PATH, UNIVERSE_SHA256, "factor universe")
    snapshot = spec.get("source_snapshot_contract") or {}
    if not (
        snapshot.get("daily_root") == str(DEFAULT_DAILY_ROOT.resolve())
        and snapshot.get("source_file_count") == SOURCE_FILE_COUNT
        and snapshot.get("source_total_bytes") == SOURCE_TOTAL_BYTES
        and snapshot.get("source_file_identity_order_sha256") == SOURCE_IDENTITY_SHA256
        and snapshot.get("output_signal_start") == OUTPUT_START.date().isoformat()
        and snapshot.get("output_signal_end") == OUTPUT_END.date().isoformat()
        and snapshot.get("source_predecessor_calendar_sessions_before_start") == 1
        and snapshot.get("source_rows_after_output_signal_end_allowed") is False
        and snapshot.get("output_rows_outside_frozen_signal_range_allowed") is False
        and snapshot.get("output_root")
        == str(DEFAULT_OUTPUT_ROOT.relative_to(REPO_ROOT))
        and snapshot.get("provider_request_allowed") is False
        and snapshot.get("credential_required") is False
    ):
        raise Campaign136FeatureError("Campaign136 source snapshot contract changed")
    return spec


def validate_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign136FeatureError("Campaign136 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    frozen = record.get("frozen_implementation") or {}
    observed_tests = {
        str(item.get("path")): str(item.get("sha256"))
        for item in record.get("synthetic_tests") or []
    }
    expected_tests = {
        str(FEATURE_TEST_PATH.relative_to(REPO_ROOT)): file_sha256(FEATURE_TEST_PATH),
        str(FORMULA_TEST_PATH.relative_to(REPO_ROOT)): file_sha256(FORMULA_TEST_PATH),
    }
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign136_source_bound_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign136_daily_source_candidate_comparator_ohlcv_or_return_values"
        and frozen.get("protocol_sha256") == PROTOCOL_SHA256
        and frozen.get("formula_sha256") == FORMULA_SHA256
        and frozen.get("formula_freeze_sha256") == FORMULA_FREEZE_SHA256
        and frozen.get("feature_builder_sha256")
        == file_sha256(Path(__file__).resolve())
        and observed_tests == expected_tests
        and frozen.get("source_file_count") == SOURCE_FILE_COUNT
        and frozen.get("source_total_bytes") == SOURCE_TOTAL_BYTES
        and frozen.get("source_file_identity_order_sha256") == SOURCE_IDENTITY_SHA256
        and frozen.get("source_projection") == list(SOURCE_COLUMNS)
        and frozen.get("output_columns") == list(OUTPUT_COLUMNS)
        and frozen.get("output_signal_start") == OUTPUT_START.date().isoformat()
        and frozen.get("output_signal_end") == OUTPUT_END.date().isoformat()
        and boundary.get(
            "campaign136_daily_source_values_were_decoded_in_failed_v1_run"
        )
        is True
        and boundary.get("campaign136_candidate_computation_started_in_failed_v1_run")
        is True
        and boundary.get("campaign136_candidate_snapshot_published") is False
        and boundary.get("campaign136_comparator_values_read") is False
        and boundary.get("historical_daily_ohlcv_fields_read") == []
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign136FeatureError("Campaign136 implementation freeze changed")
    return record


def plan_source_snapshot(root: Path = DEFAULT_DAILY_ROOT) -> dict[str, Any]:
    validate_protocol()
    freeze = validate_implementation_freeze()
    calendar = load_calendar()
    identity = source_identity(root.resolve())
    if not (
        identity["file_count"] == SOURCE_FILE_COUNT
        and identity["total_bytes"] == SOURCE_TOTAL_BYTES
        and identity["file_identity_order_sha256"] == SOURCE_IDENTITY_SHA256
    ):
        raise Campaign136FeatureError("Campaign136 daily source identity changed")
    _validate_source_schemas(identity["files"])
    first_output_position = int(calendar.searchsorted(OUTPUT_START, side="left"))
    if first_output_position < 1:
        raise Campaign136FeatureError("Campaign136 predecessor calendar unavailable")
    source_start = calendar[first_output_position - 1]
    return {
        "ready": True,
        "source_value_rows_decoded": False,
        "source_file_count": identity["file_count"],
        "source_total_bytes": identity["total_bytes"],
        "source_file_identity_order_sha256": identity["file_identity_order_sha256"],
        "source_schema_metadata_verified": True,
        "source_projection": list(SOURCE_COLUMNS),
        "source_read_start": source_start.date().isoformat(),
        "output_signal_start": OUTPUT_START.date().isoformat(),
        "output_signal_end": OUTPUT_END.date().isoformat(),
        "provider_request_issued": False,
        "credential_loaded": False,
        "implementation_freeze_status": freeze["status"],
    }


def symbol_from_source_path(path: Path) -> str:
    name = path.stem.lower()
    if len(name) != 8 or name[:2] not in {"sh", "sz"} or not name[2:].isdigit():
        raise Campaign136FeatureError(
            f"Campaign136 invalid source filename {path.name}"
        )
    return name.upper()


def build_symbol_frame(
    raw: pd.DataFrame,
    *,
    symbol: str,
    calendar: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != SOURCE_COLUMNS:
        raise Campaign136FeatureError("Campaign136 source projection changed")
    work = raw.copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce").dt.normalize()
    work["symbol"] = work["symbol"].astype("string").str.upper()
    work["factor"] = pd.to_numeric(work["factor"], errors="coerce")
    work["price_basis"] = work["price_basis"].astype("string")
    work["daily_source"] = work["daily_source"].astype("string").str.lower()
    if work["date"].isna().any() or work.duplicated(["date"]).any():
        raise Campaign136FeatureError(f"Campaign136 invalid dates for {symbol}")
    if not work.empty and set(work["symbol"].dropna().unique()) != {symbol.upper()}:
        raise Campaign136FeatureError(
            f"Campaign136 symbol identity changed for {symbol}"
        )
    work = work.sort_values("date", kind="stable").reset_index(drop=True)
    output_mask = work["date"].between(OUTPUT_START, OUTPUT_END, inclusive="both")
    current = work.loc[output_mask].copy()
    if current.empty:
        empty = pd.DataFrame(
            {
                "trade_date": pd.Series(dtype="datetime64[ns]"),
                "symbol": pd.Series(dtype="string"),
                "provider": pd.Series(dtype="string"),
                formula.FACTOR_NAME: pd.Series(dtype="float64"),
                f"{formula.FACTOR_NAME}_eligible": pd.Series(dtype="bool"),
            }
        )
        return empty, {
            "source_rows": len(work),
            "output_rows": 0,
            "eligible_rows": 0,
            "invalid_factor_pairs": 0,
            "nonadjacent_or_missing_predecessor_pairs": 0,
            "invalid_source_identity_pairs": 0,
            "exact_zero_score_pairs": 0,
            "positive_score_pairs": 0,
        }

    positions = pd.Series(
        np.arange(len(calendar), dtype=np.int64),
        index=calendar,
    )
    calendar_position = work["date"].map(positions)
    previous_position = calendar_position.shift(1)
    adjacent_all = (
        calendar_position.notna()
        & previous_position.notna()
        & previous_position.eq(calendar_position - 1)
    )
    identity_all = (
        work["price_basis"].eq(formula.PRICE_BASIS)
        & work["daily_source"].eq(formula.DAILY_SOURCE)
        & work["price_basis"].shift(1).eq(formula.PRICE_BASIS)
        & work["daily_source"].shift(1).eq(formula.DAILY_SOURCE)
    ).fillna(False)
    indices = np.flatnonzero(output_mask.to_numpy(dtype=bool))
    previous_factors = work["factor"].shift(1).iloc[indices].to_numpy(dtype=np.float64)
    scores, eligible, formula_quality = (
        formula.compute_price_basis_adjustment_magnitude(
            current["factor"].to_numpy(dtype=np.float64),
            previous_factors,
            adjacent_all.iloc[indices].to_numpy(dtype=bool),
            identity_all.iloc[indices].to_numpy(dtype=bool),
        )
    )
    output = pd.DataFrame(
        {
            "trade_date": current["date"].to_numpy(),
            "symbol": current["symbol"].astype("string").to_numpy(),
            "provider": current["daily_source"].astype("string").to_numpy(),
            formula.FACTOR_NAME: scores,
            f"{formula.FACTOR_NAME}_eligible": eligible,
        },
        columns=OUTPUT_COLUMNS,
    )
    if (
        output["trade_date"].lt(OUTPUT_START).any()
        or output["trade_date"].gt(OUTPUT_END).any()
        or output.duplicated(["trade_date", "symbol"]).any()
        or output.loc[eligible, formula.FACTOR_NAME].isna().any()
        or (output.loc[eligible, formula.FACTOR_NAME] < 0.0).any()
    ):
        raise Campaign136FeatureError(
            f"Campaign136 output invariant failed for {symbol}"
        )
    quality = {
        "source_rows": int(len(work)),
        "output_rows": int(len(output)),
        "eligible_rows": int(eligible.sum()),
        **{
            key: int(value)
            for key, value in formula_quality.items()
            if key not in {"source_pairs", "eligible_pairs"}
        },
    }
    return output, quality


def _source_bounds(calendar: pd.DatetimeIndex) -> tuple[datetime, datetime]:
    first_output_position = int(calendar.searchsorted(OUTPUT_START, side="left"))
    source_start = calendar[first_output_position - 1]
    return source_start.to_pydatetime(), OUTPUT_END.to_pydatetime()


def read_source_projection(path: Path, *, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    source_start, source_end = _source_bounds(calendar)
    table = pq.read_table(
        path,
        columns=list(SOURCE_COLUMNS),
        filters=[("date", ">=", source_start), ("date", "<=", source_end)],
    )
    return table.to_pandas(split_blocks=True, self_destruct=True)


def _write_partition(path: Path, frame: pd.DataFrame) -> dict[str, Any]:
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path, compression="zstd", use_dictionary=True)
    return {
        "path": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": file_sha256(path),
        "rows": int(len(frame)),
        "eligible_rows": int(frame[f"{formula.FACTOR_NAME}_eligible"].sum()),
    }


def _process_source_file(
    source_path: Path,
    *,
    temporary_output: Path,
    calendar: pd.DatetimeIndex,
) -> tuple[dict[str, Any] | None, dict[str, int]]:
    symbol = symbol_from_source_path(source_path)
    raw = read_source_projection(source_path, calendar=calendar)
    frame, quality = build_symbol_frame(raw, symbol=symbol, calendar=calendar)
    if frame.empty:
        return None, quality
    entry = _write_partition(temporary_output / source_path.name, frame)
    entry["symbol"] = symbol
    entry["source_path"] = source_path.name
    return entry, quality


def _dataset_digest(entries: list[dict[str, Any]]) -> str:
    identity = [
        [
            item["path"],
            item["size_bytes"],
            item["sha256"],
            item["rows"],
            item["eligible_rows"],
        ]
        for item in entries
    ]
    return canonical_sha256(identity)


def verify_snapshot(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    verify_source: bool = True,
) -> dict[str, Any]:
    freeze = validate_implementation_freeze()
    manifest_path = output_root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise Campaign136FeatureError("Campaign136 snapshot manifest missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not (
        manifest.get("kind") == "a_share_three_day_walkforward_campaign136_snapshot"
        and manifest.get("status") == "published_and_verified"
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("formula_sha256") == FORMULA_SHA256
        and manifest.get("implementation_freeze_sha256")
        == file_sha256(IMPLEMENTATION_FREEZE)
        and manifest.get("source_projection") == list(SOURCE_COLUMNS)
        and manifest.get("output_columns") == list(OUTPUT_COLUMNS)
        and manifest.get("output_signal_start") == OUTPUT_START.date().isoformat()
        and manifest.get("output_signal_end") == OUTPUT_END.date().isoformat()
    ):
        raise Campaign136FeatureError("Campaign136 snapshot manifest semantics changed")
    if verify_source:
        identity = source_identity(DEFAULT_DAILY_ROOT)
        if identity["file_identity_order_sha256"] != SOURCE_IDENTITY_SHA256:
            raise Campaign136FeatureError(
                "Campaign136 source changed after publication"
            )
    entries = list(manifest.get("partitions") or [])
    total_rows = 0
    eligible_rows = 0
    for item in entries:
        path = output_root / str(item["path"])
        if (
            not path.is_file()
            or path.stat().st_size != item["size_bytes"]
            or file_sha256(path) != item["sha256"]
        ):
            raise Campaign136FeatureError("Campaign136 output partition changed")
        parquet = pq.ParquetFile(path)
        if parquet.schema_arrow.names != list(OUTPUT_COLUMNS):
            raise Campaign136FeatureError("Campaign136 output schema changed")
        total_rows += int(item["rows"])
        eligible_rows += int(item["eligible_rows"])
    if not (
        _dataset_digest(entries) == manifest.get("dataset_sha256")
        and total_rows == manifest.get("rows")
        and eligible_rows == manifest.get("eligible_rows")
        and len(entries) == manifest.get("partition_count")
    ):
        raise Campaign136FeatureError("Campaign136 output aggregate changed")
    return {
        "verified": True,
        "manifest_sha256": file_sha256(manifest_path),
        "dataset_sha256": manifest["dataset_sha256"],
        "partition_count": len(entries),
        "rows": total_rows,
        "eligible_rows": eligible_rows,
        "source_verified": verify_source,
        "implementation_freeze_status": freeze["status"],
    }


def build_snapshot(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    workers: int = 8,
) -> dict[str, Any]:
    plan = plan_source_snapshot()
    if output_root.exists():
        verification = verify_snapshot(output_root)
        return {"reused": True, **verification}
    calendar = load_calendar()
    source_files = sorted(DEFAULT_DAILY_ROOT.glob("*.parquet"))
    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.", dir=output_root.parent)
    )
    try:
        results: list[tuple[dict[str, Any] | None, dict[str, int]]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = [
                pool.submit(
                    _process_source_file,
                    path,
                    temporary_output=temporary,
                    calendar=calendar,
                )
                for path in source_files
            ]
            for future in futures:
                results.append(future.result())
        entries = sorted(
            [entry for entry, _ in results if entry is not None],
            key=lambda item: str(item["path"]),
        )
        quality_totals: dict[str, int] = {}
        for _, quality in results:
            for key, value in quality.items():
                quality_totals[key] = quality_totals.get(key, 0) + int(value)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign136_snapshot",
            "status": "published_and_verified",
            "created_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "protocol_path": str(formula.PROTOCOL_PATH.relative_to(REPO_ROOT)),
            "protocol_sha256": PROTOCOL_SHA256,
            "formula_path": str(
                Path(formula.__file__).resolve().relative_to(REPO_ROOT)
            ),
            "formula_sha256": FORMULA_SHA256,
            "formula_freeze_sha256": FORMULA_FREEZE_SHA256,
            "implementation_freeze_sha256": file_sha256(IMPLEMENTATION_FREEZE),
            "source_root": str(DEFAULT_DAILY_ROOT.resolve()),
            "source_file_count": plan["source_file_count"],
            "source_total_bytes": plan["source_total_bytes"],
            "source_file_identity_order_sha256": plan[
                "source_file_identity_order_sha256"
            ],
            "source_projection": list(SOURCE_COLUMNS),
            "historical_daily_ohlcv_fields_read": [],
            "source_read_start": plan["source_read_start"],
            "output_signal_start": plan["output_signal_start"],
            "output_signal_end": plan["output_signal_end"],
            "output_columns": list(OUTPUT_COLUMNS),
            "partition_count": len(entries),
            "rows": sum(int(item["rows"]) for item in entries),
            "eligible_rows": sum(int(item["eligible_rows"]) for item in entries),
            "dataset_sha256": _dataset_digest(entries),
            "quality_totals": quality_totals,
            "partitions": entries,
            "provider_request_issued": False,
            "credential_loaded": False,
            "historical_forward_returns_read": False,
            "candidate49_ledgers_changed": False,
        }
        atomic_json(temporary / MANIFEST_NAME, manifest)
        os.replace(temporary, output_root)
        return {"reused": False, **verify_snapshot(output_root)}
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    run = subparsers.add_parser("run")
    run.add_argument("--confirm-run", action="store_true")
    run.add_argument("--workers", type=int, default=8)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--skip-source-byte-verification", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "plan":
            payload = plan_source_snapshot()
        elif args.command == "run":
            if not args.confirm_run:
                raise Campaign136FeatureError("Campaign136 run requires --confirm-run")
            payload = build_snapshot(workers=args.workers)
        else:
            payload = verify_snapshot(
                verify_source=not args.skip_source_byte_verification
            )
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    except Campaign136FeatureError as exc:
        print(
            json.dumps(
                {
                    "ready": False,
                    "error_code": "campaign136_source_or_snapshot_contract_failure",
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
