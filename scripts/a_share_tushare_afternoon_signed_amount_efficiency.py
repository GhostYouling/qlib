#!/usr/bin/env python3
"""Build and audit a preregistered Tushare afternoon path-efficiency factor.

The build reads only minute timestamp, identity, close, and amount from the
immutable raw source.  It restricts output to stock-days already admitted by
the immutable joint-clean base.  The no-return audit applies coverage and
capacity before it loads the four terminal comparison-factor values.  Neither
command reads a daily price or a forward return.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import fcntl
import gc
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_short_horizon_factor_research as research


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_afternoon_signed_amount_efficiency_no_return_preregistration.json"
)
PREREGISTRATION_SHA256 = (
    "072693166e96e228d734b3789db3613ea16d4fc87abfd35eb81edf1710f6d9b6"
)
DEFAULT_DIAGNOSTIC_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_afternoon_signed_amount_efficiency_diagnostic_preregistration_v2.json"
)
DIAGNOSTIC_PREREGISTRATION_SHA256 = (
    "3d050a7c303ffae8dd09e31a4010d9128611accc76aac7a6399a21192c7f9eda"
)
NO_RETURN_AUDIT_SHA256 = (
    "a0203b564ba093d09cebe17ebcb36595e63b97f972a8c04bd29098198325ed7d"
)
CANDIDATE_MANIFEST_SHA256 = (
    "e1184b04385d1b0d1eb1eb4a56ad6c21609c4387cf53324cbbb41c420cdb8ed5"
)
DIAGNOSTIC_PURPOSE = (
    "development_only_preregistered_tushare_afternoon_signed_amount_efficiency_"
    "three_session_diagnostic_research_not_investment_advice"
)
CONSUMPTION_FILENAME = "tushare_afternoon_signed_amount_efficiency_v1_consumption.json"
QUALITY_SEMANTICS_REPAIR_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_afternoon_signed_amount_efficiency_quality_semantics_repair.json"
)
QUALITY_SEMANTICS_REPAIR_SHA256 = (
    "2a22cd253249ec7e5574c77ae9e1ea9c9a0dadc717203d64c7198114fe5f87af"
)
SUPERSEDED_NO_RETURN_AUDIT_SHA256 = (
    "963c378d67dd5dc749cb43de1352ec79bab6ead4b8cfecf23c1d3a592790a8a1"
)
RAW_MANIFEST_SHA256 = "9b3d959563c9d182f38981c6a36bdb3bc9b415de08487a9e1f9e850825c0839f"
JOINT_MANIFEST_SHA256 = (
    "453c6719cb3c7da42fed8807b28a2bfe988700283e9625a6db97912534f368de"
)
SOURCE_RUN_ID = "tushare_stk_mins_1m_2019_2025_ea0cbb8f"
OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_afternoon_signed_amount_efficiency_v1"
FACTOR_NAME = "afternoon_signed_amount_efficiency_120m"
COMPARISON_FACTORS = (
    "late_return_30m",
    "late_amount_share_30m",
    "late_vwap_to_day_vwap_30m",
    "intraday_realized_volatility",
)
COMPARISON_DIRECTIONS = ("higher", "higher", "higher", "lower")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
DEVELOPMENT_START = pd.Timestamp("2019-01-01")
DEVELOPMENT_END = pd.Timestamp("2025-12-31")


class AfternoonEfficiencyError(RuntimeError):
    """Raised when a frozen source, factor, or no-return gate is violated."""


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def frame_digest(frame: pd.DataFrame) -> str:
    content = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def atomic_write_json(payload: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        suffix=".json",
        mode="w",
        encoding="utf-8",
        delete=False,
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_frame(frame: pd.DataFrame, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, suffix=".parquet", delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        frame.to_parquet(temporary, index=False)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


class ProcessLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle: Any | None = None

    def __enter__(self) -> "ProcessLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.handle.close()
            raise AfternoonEfficiencyError(
                f"another afternoon-efficiency process holds {self.path}"
            ) from exc
        self.handle.seek(0)
        self.handle.truncate()
        self.handle.write(f"pid={os.getpid()}\n")
        self.handle.flush()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.handle is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()


def expected_source_codes() -> np.ndarray:
    anchor = pd.Timestamp("2000-01-03")
    timestamps = [
        anchor + pd.Timedelta(hours=9, minutes=30),
        *pd.date_range(
            anchor + pd.Timedelta(hours=9, minutes=31), periods=120, freq="1min"
        ),
        *pd.date_range(
            anchor + pd.Timedelta(hours=13, minutes=1), periods=120, freq="1min"
        ),
    ]
    return np.asarray(
        [value.hour * 60 + value.minute for value in timestamps], dtype=np.int16
    )


SOURCE_MINUTE_CODES = expected_source_codes()
SOURCE_MINUTE_CODE_SET = frozenset(int(value) for value in SOURCE_MINUTE_CODES)
BASELINE_INDEX = int(np.flatnonzero(SOURCE_MINUTE_CODES == 11 * 60 + 30)[0])
AFTERNOON_START_INDEX = int(np.flatnonzero(SOURCE_MINUTE_CODES == 13 * 60 + 1)[0])


def empty_output_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="object"),
            "provider": pd.Series(dtype="object"),
            FACTOR_NAME: pd.Series(dtype="float64"),
            f"{FACTOR_NAME}_eligible": pd.Series(dtype="bool"),
        }
    ).loc[:, OUTPUT_COLUMNS]


def _repository_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    observed = file_digest(path)
    if observed != expected_sha256:
        raise AfternoonEfficiencyError(
            f"{label} fingerprint mismatch: expected {expected_sha256}, got {observed}"
        )


def load_preregistration(
    path: Path = DEFAULT_PREREGISTRATION,
) -> dict[str, Any]:
    """Load and enforce the exact pre-factor-value protocol."""

    path = path.expanduser().resolve()
    _require_file(path, PREREGISTRATION_SHA256, "afternoon-efficiency protocol")
    spec = research.load_json_record(
        path,
        kind="a_share_tushare_afternoon_signed_amount_efficiency_no_return_preregistration",
    )
    candidate = spec.get("candidate") or {}
    grid = candidate.get("bar_grid") or {}
    validity = candidate.get("validity") or {}
    output = spec.get("derived_snapshot") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    current = spec.get("current_research_state") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_candidate_factor_values_comparison_values_or_forward_returns"
        and current.get("sha256")
        == "616fc4ca19f9bfdc6b7eb4cd0e19740cbe4316766d33b81577f5a4baed924b2f"
        and current.get("terminal_mechanism_count_before_this_candidate") == 28
        and current.get("aggregation_allowed") is False
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("diagnostic_direction") == "higher"
        and tuple(candidate.get("source_fields_allowed") or ())
        == ("datetime", "symbol", "provider", "close", "amount")
        and set(candidate.get("source_fields_forbidden") or ())
        == {
            "open",
            "high",
            "low",
            "volume",
            "any_daily_price",
            "any_forward_return",
        }
        and grid.get("required_full_source_rows") == 241
        and grid.get("baseline_bar_end") == "11:30"
        and grid.get("weighted_bar_ends_start") == "13:01"
        and grid.get("weighted_bar_ends_end") == "15:00"
        and grid.get("weighted_bars") == 120
        and validity.get("weighted_absolute_return_denominator_strictly_positive")
        is True
        and validity.get("allowed_closed_interval") == [-1.0, 1.0]
        and validity.get("imputation_clipping_or_winsorization_allowed") is False
        and output.get("output_run_id") == OUTPUT_RUN_ID
        and output.get("provider_request_allowed") is False
        and output.get("forward_return_fields_read") is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("holding_period_sessions") == 3
        and tuple(item.get("name") for item in comparisons) == COMPARISON_FACTORS
        and tuple(item.get("score_direction") for item in comparisons)
        == COMPARISON_DIRECTIONS
        and uniqueness.get("screen_start") == "2019-01-01"
        and uniqueness.get("screen_end") == "2025-12-31"
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("all_four_comparisons_must_pass") is True
        and boundary.get("candidate_factor_values_observed_before_registration")
        is False
        and boundary.get(
            "terminal_factor_comparison_values_observed_for_this_candidate_before_registration"
        )
        is False
        and boundary.get("forward_return_fields_read_before_registration") is False
    ):
        raise AfternoonEfficiencyError(
            "afternoon-efficiency protocol no longer matches its frozen definition"
        )
    return spec


def validate_repository_chain(spec: dict[str, Any]) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    current = spec["current_research_state"]
    repository_links = (spec.get("source_chain") or {}).get("repository_records") or {}
    links = {"current_research_state": current, **repository_links}
    for name, link in links.items():
        path = _repository_path(str(link["path"]))
        expected = str(link["sha256"])
        _require_file(path, expected, name.replace("_", " "))
        evidence[name] = {"path": str(path), "sha256": expected}

    context = spec.get("point_in_time_context") or {}
    for name in ("source_universe", "holding_universe", "calendar"):
        link = context.get(name) or {}
        path = _repository_path(str(link["path"]))
        expected = str(link["sha256"])
        _require_file(path, expected, name.replace("_", " "))
        evidence[name] = {"path": str(path), "sha256": expected}
    quality = context.get("quarterly_quality") or {}
    for path_key, hash_key in (
        ("path", "sha256"),
        ("manifest_path", "manifest_sha256"),
    ):
        path = _repository_path(str(quality[path_key]))
        expected = str(quality[hash_key])
        _require_file(path, expected, path_key.replace("_", " "))
        evidence[path_key] = {"path": str(path), "sha256": expected}
    return evidence


def validate_external_chain(
    spec: dict[str, Any], data_root: Path
) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    source = spec.get("source_chain") or {}
    raw_link = source.get("raw_minute_manifest") or {}
    joint_link = source.get("joint_clean_manifest") or {}
    raw_path = (data_root / str(raw_link["path_below_data_root"])).resolve()
    joint_path = (data_root / str(joint_link["path_below_data_root"])).resolve()
    _require_file(raw_path, RAW_MANIFEST_SHA256, "raw minute manifest")
    _require_file(joint_path, JOINT_MANIFEST_SHA256, "joint-clean manifest")
    raw = research.load_json_record(raw_path, kind="a_share_rich_data_snapshot")
    joint = research.load_json_record(
        joint_path, kind="a_share_tushare_one_minute_sentiment_clean_snapshot"
    )
    if (
        raw.get("run_id") != SOURCE_RUN_ID
        or raw.get("provider") != "tushare"
        or raw.get("frequency") != "1m"
        or raw.get("rows") != 1_866_461_373
        or len(raw.get("files") or []) != 33_015
        or raw.get("forward_return_fields_read") is not False
    ):
        raise AfternoonEfficiencyError("raw minute source identity is rejected")
    if (
        joint.get("status")
        != "cleaned_sentiment_coverage_passed_pending_separate_no_return_research_protocol"
        or joint.get("output_run_id") != f"{SOURCE_RUN_ID}_sentiment_clean_v1"
        or joint.get("dataset_sha256") != joint_link.get("dataset_sha256")
        or joint.get("rows") != 7_724_498
        or joint.get("partitions") != 33_015
        or len(joint.get("files") or []) != 33_015
        or joint.get("forward_return_fields_read") is not False
    ):
        raise AfternoonEfficiencyError("joint-clean source identity is rejected")
    return raw, joint, raw_path, joint_path


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Compute the frozen factor for one symbol-year without other fields."""

    raw_required = {"datetime", "symbol", "provider", "close", "amount"}
    if missing := sorted(raw_required - set(raw.columns)):
        raise AfternoonEfficiencyError(
            "raw minute partition is missing columns: " + ", ".join(missing)
        )
    if missing := sorted({"trade_date", "symbol"} - set(base.columns)):
        raise AfternoonEfficiencyError(
            "joint base partition is missing columns: " + ", ".join(missing)
        )
    if base.empty:
        return empty_output_frame(), {
            "base_rows": 0,
            "eligible_rows": 0,
            "zero_denominator_rows": 0,
            "invalid_required_value_rows": 0,
        }

    symbol = symbol.upper()
    base_work = base[["trade_date", "symbol"]].copy()
    base_work["trade_date"] = pd.to_datetime(
        base_work["trade_date"], errors="coerce"
    ).dt.normalize()
    base_work["symbol"] = base_work["symbol"].astype(str).str.upper()
    if (
        base_work["trade_date"].isna().any()
        or set(base_work["symbol"]) != {symbol}
        or base_work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise AfternoonEfficiencyError(f"joint base identity is invalid for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )

    raw_work = raw[list(raw_required)].copy()
    raw_work["datetime"] = pd.to_datetime(raw_work["datetime"], errors="coerce")
    if raw_work["datetime"].isna().any():
        raise AfternoonEfficiencyError(f"raw timestamps are invalid for {symbol}")
    raw_work["symbol"] = raw_work["symbol"].astype(str).str.upper()
    raw_work["provider"] = raw_work["provider"].astype(str).str.lower()
    if set(raw_work["symbol"]) != {symbol} or set(raw_work["provider"]) != {"tushare"}:
        raise AfternoonEfficiencyError(f"raw identity is invalid for {symbol}")
    raw_work["trade_date"] = raw_work["datetime"].dt.normalize()
    raw_work = raw_work[raw_work["trade_date"].isin(base_work["trade_date"])].copy()
    raw_work["minute_code"] = (
        raw_work["datetime"].dt.hour * 60 + raw_work["datetime"].dt.minute
    ).astype(np.int16)
    raw_work["close"] = pd.to_numeric(raw_work["close"], errors="coerce")
    raw_work["amount"] = pd.to_numeric(raw_work["amount"], errors="coerce")
    raw_work = raw_work.sort_values(["trade_date", "datetime"], kind="stable")
    stats = raw_work.groupby("trade_date", observed=True, sort=True).agg(
        rows=("datetime", "size"),
        unique_times=("minute_code", "nunique"),
        on_grid=(
            "minute_code",
            lambda values: values.isin(SOURCE_MINUTE_CODE_SET).sum(),
        ),
    )
    if (
        len(stats) != len(base_work)
        or not stats.index.equals(pd.DatetimeIndex(base_work["trade_date"]))
        or not stats["rows"].eq(241).all()
        or not stats["unique_times"].eq(241).all()
        or not stats["on_grid"].eq(241).all()
    ):
        raise AfternoonEfficiencyError(
            f"raw source does not reproduce every joint-base 241-row grid for {symbol}"
        )
    codes = raw_work["minute_code"].to_numpy().reshape(-1, 241)
    if not np.array_equal(codes, np.broadcast_to(SOURCE_MINUTE_CODES, codes.shape)):
        raise AfternoonEfficiencyError(f"raw source grid order changed for {symbol}")
    closes = raw_work["close"].to_numpy(dtype=float).reshape(-1, 241)
    amounts = raw_work["amount"].to_numpy(dtype=float).reshape(-1, 241)
    previous = np.concatenate(
        [
            closes[:, BASELINE_INDEX : BASELINE_INDEX + 1],
            closes[:, AFTERNOON_START_INDEX:-1],
        ],
        axis=1,
    )
    current = closes[:, AFTERNOON_START_INDEX:]
    weights = amounts[:, AFTERNOON_START_INDEX:]
    if current.shape[1] != 120 or previous.shape != current.shape:
        raise AfternoonEfficiencyError("afternoon factor vectorization changed")
    required_values_valid = (
        np.isfinite(previous).all(axis=1)
        & np.isfinite(current).all(axis=1)
        & (previous > 0.0).all(axis=1)
        & (current > 0.0).all(axis=1)
        & np.isfinite(weights).all(axis=1)
        & (weights >= 0.0).all(axis=1)
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        returns = np.log(current / previous)
        numerator = np.sum(weights * returns, axis=1)
        denominator = np.sum(weights * np.abs(returns), axis=1)
        values = numerator / denominator
    eligible = (
        required_values_valid
        & np.isfinite(denominator)
        & (denominator > 0.0)
        & np.isfinite(values)
        & (values >= -1.0 - 1e-12)
        & (values <= 1.0 + 1e-12)
    )
    if (np.abs(values[eligible]) > 1.0 + 1e-12).any():
        raise AfternoonEfficiencyError("afternoon efficiency is outside [-1, 1]")
    output = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol,
            "provider": "tushare",
            FACTOR_NAME: np.where(eligible, values, np.nan),
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    quality = {
        "base_rows": int(len(output)),
        "eligible_rows": int(eligible.sum()),
        "zero_denominator_rows": int(
            (required_values_valid & ~(denominator > 0)).sum()
        ),
        "invalid_required_value_rows": int((~required_values_valid).sum()),
    }
    return output, quality


@dataclass(frozen=True)
class PartitionPaths:
    partial_data: Path
    partial_sidecar: Path
    final_data: Path
    final_sidecar: Path


def partition_paths(
    partial_root: Path, final_root: Path, joint_record: dict[str, Any]
) -> PartitionPaths:
    base_path = Path(str(joint_record["path"]))
    relative = Path(base_path.parent.name) / base_path.name
    metadata = Path(base_path.parent.name) / f"{base_path.stem}.json"
    return PartitionPaths(
        partial_data=partial_root / "partitions" / relative,
        partial_sidecar=partial_root / ".metadata" / "partitions" / metadata,
        final_data=final_root / "partitions" / relative,
        final_sidecar=final_root / ".metadata" / "partitions" / metadata,
    )


def _load_checkpoint(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
    paths: PartitionPaths,
) -> tuple[dict[str, Any], Counter[str]] | None:
    if not paths.partial_sidecar.exists():
        paths.partial_data.unlink(missing_ok=True)
        return None
    record = json.loads(paths.partial_sidecar.read_text(encoding="utf-8"))
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    valid = (
        record.get("kind")
        == "a_share_tushare_afternoon_signed_amount_efficiency_partition"
        and record.get("protocol_sha256") == PREREGISTRATION_SHA256
        and record.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and record.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
        and record.get("raw_source_byte_sha256") == raw_record.get("byte_sha256")
        and record.get("joint_base_byte_sha256")
        == joint_record.get("output_byte_sha256")
        and paths.partial_data.is_file()
        and file_digest(raw_path) == raw_record.get("byte_sha256")
        and file_digest(base_path) == joint_record.get("output_byte_sha256")
        and file_digest(paths.partial_data) == record.get("output_byte_sha256")
    )
    if not valid:
        raise AfternoonEfficiencyError(
            f"completed afternoon-efficiency checkpoint changed: {paths.partial_sidecar}"
        )
    output = pd.read_parquet(paths.partial_data)
    if len(output) != int(record.get("rows", -1)) or frame_digest(output) != record.get(
        "output_frame_sha256"
    ):
        raise AfternoonEfficiencyError(
            f"completed afternoon-efficiency frame changed: {paths.partial_data}"
        )
    dates = Counter(
        pd.to_datetime(output.loc[output[f"{FACTOR_NAME}_eligible"], "trade_date"])
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )
    return record, dates


def _process_partition(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
    *,
    partial_root: Path,
    final_root: Path,
) -> tuple[dict[str, Any], Counter[str], bool]:
    paths = partition_paths(partial_root, final_root, joint_record)
    completed = _load_checkpoint(raw_record, joint_record, paths)
    if completed is not None:
        record, dates = completed
        return record, dates, True

    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    if file_digest(raw_path) != raw_record.get("byte_sha256"):
        raise AfternoonEfficiencyError(f"raw partition changed: {raw_path}")
    if file_digest(base_path) != joint_record.get("output_byte_sha256"):
        raise AfternoonEfficiencyError(f"joint-base partition changed: {base_path}")
    raw = pd.read_parquet(
        raw_path, columns=["datetime", "symbol", "provider", "close", "amount"]
    )
    base = pd.read_parquet(base_path, columns=["trade_date", "symbol"])
    if len(raw) != int(raw_record.get("rows", -1)):
        raise AfternoonEfficiencyError(f"raw row count changed: {raw_path}")
    if len(base) != int(joint_record.get("rows", -1)):
        raise AfternoonEfficiencyError(f"joint-base row count changed: {base_path}")
    output, quality = compute_partition_frame(
        raw, base, symbol=str(joint_record["symbol"])
    )
    atomic_write_frame(output, paths.partial_data)
    record = {
        "schema_version": 1,
        "kind": "a_share_tushare_afternoon_signed_amount_efficiency_partition",
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol_sha256": PREREGISTRATION_SHA256,
        "raw_manifest_sha256": RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
        "output_run_id": OUTPUT_RUN_ID,
        "symbol": str(joint_record["symbol"]),
        "code": str(joint_record["code"]),
        "year": int(joint_record["year"]),
        "raw_source_path": str(raw_path),
        "raw_source_rows": int(raw_record["rows"]),
        "raw_source_byte_sha256": str(raw_record["byte_sha256"]),
        "joint_base_path": str(base_path),
        "joint_base_rows": int(joint_record["rows"]),
        "joint_base_byte_sha256": str(joint_record["output_byte_sha256"]),
        "path": str(paths.final_data),
        "sidecar_path": str(paths.final_sidecar),
        "rows": int(len(output)),
        "eligible_rows": int(output[f"{FACTOR_NAME}_eligible"].sum()),
        "output_byte_sha256": file_digest(paths.partial_data),
        "output_frame_sha256": frame_digest(output),
        "quality": quality,
        "source_fields_read": ["datetime", "symbol", "provider", "close", "amount"],
        "daily_price_fields_read": [],
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
    }
    atomic_write_json(record, paths.partial_sidecar)
    dates = Counter(
        pd.to_datetime(output.loc[output[f"{FACTOR_NAME}_eligible"], "trade_date"])
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )
    return record, dates, False


def _process_symbol(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    *,
    partial_root: Path,
    final_root: Path,
) -> tuple[list[dict[str, Any]], Counter[str], int]:
    records: list[dict[str, Any]] = []
    eligible_dates: Counter[str] = Counter()
    resumed = 0
    for raw_record, joint_record in sorted(
        pairs, key=lambda pair: int(pair[1]["year"])
    ):
        record, dates, was_resumed = _process_partition(
            raw_record,
            joint_record,
            partial_root=partial_root,
            final_root=final_root,
        )
        records.append(record)
        eligible_dates.update(dates)
        resumed += int(was_resumed)
    return records, eligible_dates, resumed


def _aggregate_quality(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    values: Counter[str] = Counter()
    for record in records:
        for key, value in (record.get("quality") or {}).items():
            values[str(key)] += int(value)
    return dict(sorted(values.items()))


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_afternoon_signed_amount_efficiency"
        / OUTPUT_RUN_ID
    )


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Build all 33,015 symbol-year partitions with resumable checkpoints."""

    if workers < 1 or workers > 8:
        raise ValueError("--workers must be between 1 and 8")
    data_root = data_root.expanduser().resolve()
    spec = load_preregistration()
    repository_evidence = validate_repository_chain(spec)
    raw, joint, raw_manifest_path, joint_manifest_path = validate_external_chain(
        spec, data_root
    )
    final_root = output_root(data_root)
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    final_manifest = final_root / "snapshot_manifest.json"
    if final_root.exists():
        if not final_manifest.is_file():
            raise AfternoonEfficiencyError(
                f"published afternoon-efficiency root has no manifest: {final_root}"
            )
        manifest = research.load_json_record(
            final_manifest,
            kind="a_share_tushare_afternoon_signed_amount_efficiency_snapshot",
        )
        if (
            manifest.get("protocol_sha256") != PREREGISTRATION_SHA256
            or manifest.get("raw_manifest_sha256") != RAW_MANIFEST_SHA256
            or manifest.get("joint_manifest_sha256") != JOINT_MANIFEST_SHA256
            or manifest.get("output_run_id") != OUTPUT_RUN_ID
        ):
            raise AfternoonEfficiencyError(
                f"published afternoon-efficiency snapshot changed: {final_root}"
            )
        return final_manifest

    if shutil.disk_usage(data_root).free < 5 * 1024**3:
        raise AfternoonEfficiencyError("external data root has less than 5 GiB free")
    raw_records = list(raw.get("files") or [])
    joint_records = list(joint.get("files") or [])
    raw_by_key = {
        (str(item["symbol"]), int(item["year"])): item for item in raw_records
    }
    joint_by_key = {
        (str(item["symbol"]), int(item["year"])): item for item in joint_records
    }
    if (
        len(raw_by_key) != 33_015
        or len(joint_by_key) != 33_015
        or set(raw_by_key) != set(joint_by_key)
    ):
        raise AfternoonEfficiencyError(
            "raw and joint-clean partition identities do not match exactly"
        )
    by_symbol: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for key in sorted(joint_by_key):
        raw_record = raw_by_key[key]
        joint_record = joint_by_key[key]
        if (
            joint_record.get("source_byte_sha256") != raw_record.get("byte_sha256")
            or Path(str(joint_record.get("source_path"))).resolve()
            != Path(str(raw_record.get("path"))).resolve()
        ):
            raise AfternoonEfficiencyError(
                f"joint-clean raw source binding changed for {key[0]}/{key[1]}"
            )
        by_symbol.setdefault(key[0], []).append((raw_record, joint_record))

    lock_path = data_root / ".a_share_tushare_afternoon_efficiency.lock"
    with ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        all_records: list[dict[str, Any]] = []
        eligible_dates: Counter[str] = Counter()
        resumed = 0
        completed_symbols = 0
        print(
            f"building {len(joint_records):,} afternoon-efficiency partitions "
            f"across {len(by_symbol):,} symbols with {workers} workers",
            flush=True,
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _process_symbol,
                    pairs,
                    partial_root=partial_root,
                    final_root=final_root,
                ): symbol
                for symbol, pairs in sorted(by_symbol.items())
            }
            try:
                for future in concurrent.futures.as_completed(futures):
                    futures.pop(future)
                    records, dates, resumed_count = future.result()
                    all_records.extend(records)
                    eligible_dates.update(dates)
                    resumed += resumed_count
                    completed_symbols += 1
                    if completed_symbols % 25 == 0 or completed_symbols == len(
                        by_symbol
                    ):
                        print(
                            f"progress symbols={completed_symbols:,}/{len(by_symbol):,} "
                            f"partitions={len(all_records):,}/{len(joint_records):,} "
                            f"eligible_rows={sum(eligible_dates.values()):,} "
                            f"resumed={resumed:,}",
                            flush=True,
                        )
            except BaseException:
                for future in futures:
                    future.cancel()
                raise
        if len(all_records) != 33_015:
            raise AfternoonEfficiencyError(
                "not every source partition produced an afternoon-efficiency checkpoint"
            )
        _require_file(raw_manifest_path, RAW_MANIFEST_SHA256, "raw minute manifest")
        _require_file(
            joint_manifest_path, JOINT_MANIFEST_SHA256, "joint-clean manifest"
        )
        all_records.sort(key=lambda item: (str(item["symbol"]), int(item["year"])))
        quality = _aggregate_quality(all_records)
        dataset_payload = "\n".join(
            f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
            for item in all_records
        ).encode("utf-8")
        manifest = {
            "schema_version": 1,
            "kind": "a_share_tushare_afternoon_signed_amount_efficiency_snapshot",
            "status": "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness",
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "output_run_id": OUTPUT_RUN_ID,
            "protocol_path": str(DEFAULT_PREREGISTRATION.resolve()),
            "protocol_sha256": PREREGISTRATION_SHA256,
            "raw_manifest_path": str(raw_manifest_path),
            "raw_manifest_sha256": RAW_MANIFEST_SHA256,
            "joint_manifest_path": str(joint_manifest_path),
            "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
            "dataset_sha256": hashlib.sha256(dataset_payload).hexdigest(),
            "factor_name": FACTOR_NAME,
            "factor_direction": "higher",
            "files": all_records,
            "partitions": len(all_records),
            "rows": int(quality.get("base_rows", -1)),
            "eligible_rows": int(quality.get("eligible_rows", -1)),
            "quality": quality,
            "eligible_names_by_date": dict(sorted(eligible_dates.items())),
            "source_fields_read": ["datetime", "symbol", "provider", "close", "amount"],
            "source_open_high_low_or_volume_read": False,
            "daily_price_fields_read": [],
            "comparison_factor_values_read": False,
            "forward_return_fields_read": False,
            "training_or_model_fitting_performed": False,
            "aggregation_scoring_selection_sizing_or_orders_performed": False,
            "promotion_allowed": False,
            "resumed_partitions": resumed,
            "repository_evidence": repository_evidence,
        }
        atomic_write_json(manifest, partial_root / "snapshot_manifest.json")
        final_root.parent.mkdir(parents=True, exist_ok=True)
        partial_root.replace(final_root)
        return final_manifest


def verify_snapshot_files(
    manifest: dict[str, Any], manifest_path: Path, workers: int
) -> dict[str, int]:
    records = list(manifest.get("files") or [])
    if len(records) != 33_015:
        raise AfternoonEfficiencyError("candidate snapshot partition count changed")
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(record: dict[str, Any]) -> tuple[int, int, int]:
        path = Path(str(record["path"])).resolve()
        try:
            path.relative_to(partition_root)
        except ValueError as exc:
            raise AfternoonEfficiencyError(
                f"candidate partition escapes its frozen root: {path}"
            ) from exc
        _require_file(path, str(record["output_byte_sha256"]), "candidate partition")
        _require_file(
            Path(str(record["raw_source_path"])),
            str(record["raw_source_byte_sha256"]),
            "raw source partition",
        )
        _require_file(
            Path(str(record["joint_base_path"])),
            str(record["joint_base_byte_sha256"]),
            "joint-base partition",
        )
        return int(record["rows"]), int(record["eligible_rows"]), path.stat().st_size

    rows = eligible = byte_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for index, result in enumerate(pool.map(verify, records), start=1):
            partition_rows, partition_eligible, partition_bytes = result
            rows += partition_rows
            eligible += partition_eligible
            byte_count += partition_bytes
            if index % 5000 == 0 or index == len(records):
                print(
                    f"verified candidate partitions {index}/{len(records)}", flush=True
                )
    if rows != manifest.get("rows") or eligible != manifest.get("eligible_rows"):
        raise AfternoonEfficiencyError("candidate snapshot aggregate counts changed")
    return {
        "partitions_verified": len(records),
        "rows_verified": rows,
        "eligible_rows_verified": eligible,
        "partition_bytes_verified": byte_count,
    }


def load_candidate_frame(manifest_path: Path, manifest: dict[str, Any]) -> pd.DataFrame:
    dataset = pa_dataset.dataset(
        str(manifest_path.parent / "partitions"), format="parquet"
    )
    table = dataset.to_table(columns=list(OUTPUT_COLUMNS), use_threads=True)
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    if len(frame) != int(manifest.get("rows", -1)):
        raise AfternoonEfficiencyError("candidate frame row count changed")
    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"], errors="coerce"
    ).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    frame[f"{FACTOR_NAME}_eligible"] = (
        frame[f"{FACTOR_NAME}_eligible"].astype("boolean").fillna(False).astype(bool)
    )
    frame[FACTOR_NAME] = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"]
    if (
        frame["trade_date"].isna().any()
        or frame.duplicated(["trade_date", "symbol"]).any()
        or not np.isfinite(frame.loc[eligible, FACTOR_NAME].to_numpy(dtype=float)).all()
        or not frame.loc[eligible, FACTOR_NAME].between(-1.0, 1.0).all()
        or frame.loc[~eligible, FACTOR_NAME].notna().any()
    ):
        raise AfternoonEfficiencyError("candidate frame values or keys are invalid")
    frame["symbol"] = frame["symbol"].astype("category")
    return frame


def _read_calendar(path: Path) -> pd.DatetimeIndex:
    values = pd.to_datetime(
        path.read_text(encoding="utf-8").splitlines(), errors="coerce"
    )
    if pd.isna(values).any():
        raise AfternoonEfficiencyError("local calendar contains invalid dates")
    calendar = pd.DatetimeIndex(values).normalize().unique().sort_values()
    if calendar.empty:
        raise AfternoonEfficiencyError("local calendar is empty")
    return calendar


def quality_listing_eligible_keys(spec: dict[str, Any]) -> pd.DataFrame:
    """Materialize no-price quality/listing-eligible holding-universe keys."""

    context = spec["point_in_time_context"]
    calendar = _read_calendar(_repository_path(context["calendar"]["path"]))
    development_calendar = calendar[
        (calendar >= DEVELOPMENT_START) & (calendar <= DEVELOPMENT_END)
    ]
    holding_path = _repository_path(context["holding_universe"]["path"])
    intervals = pd.read_csv(
        holding_path,
        sep="\t",
        header=None,
        names=["instrument", "active_start", "active_end"],
        dtype={"instrument": "string"},
    )
    intervals["instrument"] = intervals["instrument"].astype(str).str.upper()
    intervals["active_start"] = pd.to_datetime(
        intervals["active_start"], errors="coerce"
    ).dt.normalize()
    intervals["active_end"] = pd.to_datetime(
        intervals["active_end"], errors="coerce"
    ).dt.normalize()
    if (
        intervals.empty
        or intervals.isna().any().any()
        or intervals["instrument"].duplicated().any()
        or intervals["active_start"].gt(intervals["active_end"]).any()
    ):
        raise AfternoonEfficiencyError("holding-universe intervals are invalid")

    quality_path = _repository_path(context["quarterly_quality"]["path"])
    fundamentals = pd.read_parquet(quality_path)
    required = {
        "instrument",
        "report_date",
        "announcement_date",
        "roe",
        "net_profit",
        "revenue_yoy",
        "profit_yoy",
    }
    if missing := sorted(required - set(fundamentals.columns)):
        raise AfternoonEfficiencyError(
            "quarterly quality is missing columns: " + ", ".join(missing)
        )
    fundamentals = fundamentals[list(required)].copy()
    fundamentals["instrument"] = fundamentals["instrument"].astype(str).str.upper()
    fundamentals["report_date"] = pd.to_datetime(
        fundamentals["report_date"], errors="coerce"
    ).dt.normalize()
    fundamentals["announcement_date"] = pd.to_datetime(
        fundamentals["announcement_date"], errors="coerce"
    ).dt.normalize()
    for column in ("roe", "net_profit", "revenue_yoy", "profit_yoy"):
        fundamentals[column] = pd.to_numeric(fundamentals[column], errors="coerce")
    if (
        fundamentals[["instrument", "report_date", "announcement_date"]]
        .isna()
        .any()
        .any()
    ):
        raise AfternoonEfficiencyError("quarterly quality identities are invalid")
    announcement_values = fundamentals["announcement_date"].to_numpy(
        dtype="datetime64[ns]"
    )
    positions = np.searchsorted(
        calendar.to_numpy(dtype="datetime64[ns]"), announcement_values, side="right"
    )
    effective = np.full(len(fundamentals), np.datetime64("NaT"), dtype="datetime64[ns]")
    in_range = positions < len(calendar)
    effective[in_range] = calendar.to_numpy(dtype="datetime64[ns]")[positions[in_range]]
    fundamentals["effective_date"] = pd.to_datetime(effective)
    fundamentals = (
        fundamentals.dropna(subset=["effective_date"])
        .sort_values(
            ["instrument", "effective_date", "report_date", "announcement_date"],
            kind="stable",
        )
        .drop_duplicates(["instrument", "effective_date"], keep="last")
    )
    quality_state_columns = ["roe", "net_profit", "revenue_yoy", "profit_yoy"]
    fundamentals[quality_state_columns] = fundamentals.groupby(
        "instrument", sort=False
    )[quality_state_columns].ffill()
    events_by_instrument = {
        str(instrument): group.reset_index(drop=True)
        for instrument, group in fundamentals.groupby("instrument", sort=False)
    }
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    eligible_frames: list[pd.DataFrame] = []
    maximum_age = int(context["quarterly_quality"]["maximum_age_days"])
    minimum_listing = int(context["minimum_listing_sessions"])
    for row in intervals.itertuples(index=False):
        start = max(pd.Timestamp(row.active_start), DEVELOPMENT_START)
        end = min(pd.Timestamp(row.active_end), DEVELOPMENT_END)
        if start > end:
            continue
        dates = development_calendar[
            (development_calendar >= start) & (development_calendar <= end)
        ]
        if dates.empty:
            continue
        start_position = int(
            np.searchsorted(
                calendar_values, np.datetime64(row.active_start), side="left"
            )
        )
        date_positions = np.searchsorted(
            calendar_values, dates.to_numpy(dtype="datetime64[ns]"), side="left"
        )
        listing_eligible = date_positions - start_position + 1 >= minimum_listing
        events = events_by_instrument.get(str(row.instrument))
        if events is None or events.empty:
            continue
        event_dates = events["effective_date"].to_numpy(dtype="datetime64[ns]")
        event_positions = (
            np.searchsorted(
                event_dates, dates.to_numpy(dtype="datetime64[ns]"), side="right"
            )
            - 1
        )
        has_event = event_positions >= 0
        if not has_event.any():
            continue
        selected = np.clip(event_positions, 0, len(events) - 1)
        effective_dates = events["effective_date"].to_numpy(dtype="datetime64[ns]")[
            selected
        ]
        age_days = (
            dates.to_numpy(dtype="datetime64[D]")
            - effective_dates.astype("datetime64[D]")
        ).astype(int)
        quality_eligible = has_event & (age_days >= 0) & (age_days <= maximum_age)
        for column, comparator in (
            ("roe", lambda values: values >= 5.0),
            ("net_profit", lambda values: values > 0.0),
            ("revenue_yoy", lambda values: values > 0.0),
            ("profit_yoy", lambda values: values > 0.0),
        ):
            values = events[column].to_numpy(dtype=float)[selected]
            quality_eligible &= np.isfinite(values) & comparator(values)
        keep = listing_eligible & quality_eligible
        if keep.any():
            eligible_frames.append(
                pd.DataFrame(
                    {
                        "trade_date": dates[keep],
                        "symbol": str(row.instrument),
                    }
                )
            )
    if not eligible_frames:
        raise AfternoonEfficiencyError("no quality/listing-eligible holding rows exist")
    result = pd.concat(eligible_frames, ignore_index=True)
    result = result.sort_values(["trade_date", "symbol"], kind="stable").reset_index(
        drop=True
    )
    if result.duplicated(["trade_date", "symbol"]).any():
        raise AfternoonEfficiencyError("quality/listing eligibility has duplicate keys")
    result["symbol"] = result["symbol"].astype("category")
    return result


def coverage_and_capacity(
    candidate: pd.DataFrame,
    eligible_keys: pd.DataFrame,
    spec: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run the first no-return gate and return the eligible candidate rows."""

    merged = eligible_keys.merge(
        candidate,
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    candidate_eligible = (
        merged[f"{FACTOR_NAME}_eligible"].astype("boolean").fillna(False).astype(bool)
        & pd.to_numeric(merged[FACTOR_NAME], errors="coerce").notna()
    )
    merged[f"{FACTOR_NAME}_eligible"] = candidate_eligible
    denominators = merged.groupby("trade_date", observed=True, sort=True).size()
    numerators = (
        merged.loc[candidate_eligible]
        .groupby("trade_date", observed=True, sort=True)
        .size()
        .reindex(denominators.index, fill_value=0)
    )
    ratios = numerators / denominators
    gate = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    hold_days = int(gate["holding_period_sessions"])
    indices = np.arange(0, max(len(denominators) - hold_days, 0), hold_days)
    minimum_names = int(gate["minimum_p05_eligible_names"])
    potential = int(numerators.iloc[indices].ge(minimum_names).sum())
    cohort_years = sorted(
        int(year)
        for year in pd.DatetimeIndex(
            numerators.index[indices][numerators.iloc[indices].ge(minimum_names)]
        ).year.unique()
    )
    daily = pd.DataFrame(
        {
            "trade_date": denominators.index,
            "quality_listing_eligible_names": denominators.to_numpy(dtype=int),
            "candidate_eligible_names": numerators.to_numpy(dtype=int),
            "coverage": ratios.to_numpy(dtype=float),
        }
    )
    daily_hash = research.dataframe_content_sha256(daily)
    median = float(ratios.median())
    p05 = float(ratios.quantile(0.05))
    names_p05 = float(numerators.quantile(0.05))
    passed = bool(
        median >= float(gate["minimum_median_coverage"])
        and p05 >= float(gate["minimum_p05_coverage"])
        and names_p05 >= minimum_names
        and potential >= int(gate["minimum_non_overlapping_three_session_cohorts"])
        and len(cohort_years) >= int(gate["minimum_observed_calendar_years"])
    )
    result = {
        "quality_listing_eligible_rows": int(len(eligible_keys)),
        "candidate_eligible_rows": int(candidate_eligible.sum()),
        "calendar_sessions": int(len(denominators)),
        "median_coverage": median,
        "p05_coverage": p05,
        "eligible_names_min": int(numerators.min()),
        "eligible_names_p05": names_p05,
        "eligible_names_median": float(numerators.median()),
        "potential_non_overlapping_three_session_cohorts": potential,
        "observed_cohort_years": cohort_years,
        "daily_coverage_frame_sha256": daily_hash,
        "worst_ten_sessions": [
            {
                "trade_date": pd.Timestamp(row.trade_date).date().isoformat(),
                "quality_listing_eligible_names": int(
                    row.quality_listing_eligible_names
                ),
                "candidate_eligible_names": int(row.candidate_eligible_names),
                "coverage": float(row.coverage),
            }
            for row in daily.sort_values(["coverage", "trade_date"], kind="stable")
            .head(10)
            .itertuples(index=False)
        ],
        "gate": {
            "minimum_median_coverage": float(gate["minimum_median_coverage"]),
            "minimum_p05_coverage": float(gate["minimum_p05_coverage"]),
            "minimum_p05_eligible_names": minimum_names,
            "minimum_non_overlapping_three_session_cohorts": int(
                gate["minimum_non_overlapping_three_session_cohorts"]
            ),
            "minimum_observed_calendar_years": int(
                gate["minimum_observed_calendar_years"]
            ),
        },
        "gate_passed_before_comparison_values": passed,
    }
    return merged.loc[candidate_eligible, ["trade_date", "symbol", FACTOR_NAME]], result


def _daily_directional_rank_correlations(
    frame: pd.DataFrame,
    comparison: str,
    direction: str,
    minimum_names: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    columns = ["trade_date", FACTOR_NAME, comparison]
    for trade_date, group in frame[columns].groupby(
        "trade_date", observed=True, sort=True
    ):
        pair = group[[FACTOR_NAME, comparison]].apply(pd.to_numeric, errors="coerce")
        pair = pair.replace([np.inf, -np.inf], np.nan).dropna()
        if len(pair) < minimum_names or pair.nunique().min() < 2:
            continue
        candidate_score = pair[FACTOR_NAME].rank(method="average", pct=True)
        comparison_score = pair[comparison].rank(
            method="average", pct=True, ascending=(direction == "higher")
        )
        correlation = candidate_score.corr(comparison_score, method="pearson")
        if math.isfinite(float(correlation)):
            rows.append(
                {
                    "trade_date": pd.Timestamp(trade_date),
                    "pairwise_names": int(len(pair)),
                    "rank_correlation": float(correlation),
                }
            )
    return pd.DataFrame(rows)


def uniqueness_audit(
    candidate_quality: pd.DataFrame,
    joint_manifest_path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    """Load the four terminal values only after coverage passed and gate synonyms."""

    print("coverage passed; loading four terminal comparison factors", flush=True)
    dataset = pa_dataset.dataset(
        str(joint_manifest_path.parent / "partitions"), format="parquet"
    )
    columns = ["trade_date", "symbol", *COMPARISON_FACTORS]
    table = dataset.to_table(columns=columns, use_threads=True)
    comparisons = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    comparisons["trade_date"] = pd.to_datetime(
        comparisons["trade_date"], errors="coerce"
    ).dt.normalize()
    comparisons["symbol"] = comparisons["symbol"].astype(str).str.upper()
    if (
        len(comparisons) != 7_724_498
        or comparisons["trade_date"].isna().any()
        or comparisons.duplicated(["trade_date", "symbol"]).any()
    ):
        raise AfternoonEfficiencyError("terminal comparison frame identity changed")
    candidate_quality = candidate_quality.copy()
    candidate_quality["symbol"] = candidate_quality["symbol"].astype(str)
    merged = candidate_quality.merge(
        comparisons,
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    del comparisons, candidate_quality
    gc.collect()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    minimum_names = int(gate["minimum_pairwise_names_per_session"])
    minimum_sessions = int(gate["minimum_pairwise_sessions_per_comparison"])
    threshold = float(gate["maximum_allowed_absolute_median_daily_rank_correlation"])
    results: list[dict[str, Any]] = []
    for comparison, direction in zip(COMPARISON_FACTORS, COMPARISON_DIRECTIONS):
        daily = _daily_directional_rank_correlations(
            merged, comparison, direction, minimum_names
        )
        sessions = int(len(daily))
        median = float(daily["rank_correlation"].median()) if sessions else math.nan
        passed = bool(
            sessions >= minimum_sessions
            and math.isfinite(median)
            and abs(median) < threshold
        )
        results.append(
            {
                "comparison_factor": comparison,
                "score_direction": direction,
                "pairwise_sessions": sessions,
                "minimum_pairwise_names_observed": (
                    int(daily["pairwise_names"].min()) if sessions else 0
                ),
                "median_daily_rank_correlation": (
                    median if math.isfinite(median) else None
                ),
                "absolute_median_daily_rank_correlation": (
                    abs(median) if math.isfinite(median) else None
                ),
                "daily_rank_correlation_p05": (
                    float(daily["rank_correlation"].quantile(0.05))
                    if sessions
                    else None
                ),
                "daily_rank_correlation_p95": (
                    float(daily["rank_correlation"].quantile(0.95))
                    if sessions
                    else None
                ),
                "daily_correlation_frame_sha256": (
                    research.dataframe_content_sha256(daily) if sessions else None
                ),
                "gate_passed": passed,
            }
        )
    observed = [
        item["absolute_median_daily_rank_correlation"]
        for item in results
        if item["absolute_median_daily_rank_correlation"] is not None
    ]
    all_passed = len(results) == 4 and all(item["gate_passed"] for item in results)
    return {
        "comparison_values_loaded_after_coverage_pass": True,
        "comparison_field_count": len(results),
        "minimum_pairwise_names_per_session": minimum_names,
        "minimum_pairwise_sessions_per_comparison": minimum_sessions,
        "maximum_allowed_absolute_median_daily_rank_correlation": threshold,
        "comparisons": results,
        "maximum_observed_absolute_median_daily_rank_correlation": (
            max(observed) if observed else None
        ),
        "all_four_comparisons_passed": all_passed,
    }


def _find_existing_audit(experiment_root: Path, manifest_sha256: str) -> Path | None:
    for path in sorted(
        experiment_root.glob(
            "*_afternoon_signed_amount_efficiency_no_return_audit.json"
        )
    ):
        record = research.load_json_record(path)
        if file_digest(path) == SUPERSEDED_NO_RETURN_AUDIT_SHA256:
            continue
        if (
            record.get("kind")
            == "a_share_tushare_afternoon_signed_amount_efficiency_no_return_audit"
            and (record.get("candidate_snapshot") or {}).get("sha256")
            == manifest_sha256
        ):
            return path
    return None


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    """Run coverage/capacity, then conditionally uniqueness, with no returns."""

    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_preregistration()
    repository_evidence = validate_repository_chain(spec)
    _require_file(
        QUALITY_SEMANTICS_REPAIR_PATH,
        QUALITY_SEMANTICS_REPAIR_SHA256,
        "quality-semantics repair",
    )
    repair = research.load_json_record(
        QUALITY_SEMANTICS_REPAIR_PATH,
        kind="a_share_tushare_afternoon_signed_amount_efficiency_quality_semantics_repair",
    )
    if (
        repair.get("status")
        != "frozen_after_pre_return_infrastructure_mismatch_before_corrected_no_return_audit"
        or (repair.get("superseded_no_return_audit") or {}).get("sha256")
        != SUPERSEDED_NO_RETURN_AUDIT_SHA256
        or (repair.get("failed_diagnostic_attempts") or {}).get(
            "stopped_before_forward_return_construction"
        )
        is not True
        or (repair.get("only_authorized_repair") or {}).get("factor_formula_changed")
        is not False
    ):
        raise AfternoonEfficiencyError("quality-semantics repair record changed")
    repository_evidence["quality_semantics_repair"] = {
        "path": str(QUALITY_SEMANTICS_REPAIR_PATH.resolve()),
        "sha256": QUALITY_SEMANTICS_REPAIR_SHA256,
    }
    _, joint, _, joint_manifest_path = validate_external_chain(spec, data_root)
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"candidate snapshot must be built before its no-return audit: {manifest_path}"
        )
    manifest = research.load_json_record(
        manifest_path,
        kind="a_share_tushare_afternoon_signed_amount_efficiency_snapshot",
    )
    if (
        manifest.get("status")
        != "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        or manifest.get("protocol_sha256") != PREREGISTRATION_SHA256
        or manifest.get("raw_manifest_sha256") != RAW_MANIFEST_SHA256
        or manifest.get("joint_manifest_sha256") != JOINT_MANIFEST_SHA256
        or manifest.get("rows") != 7_724_498
        or manifest.get("comparison_factor_values_read") is not False
        or manifest.get("forward_return_fields_read") is not False
    ):
        raise AfternoonEfficiencyError("candidate snapshot identity is rejected")
    manifest_sha256 = file_digest(manifest_path)
    existing = _find_existing_audit(experiment_root, manifest_sha256)
    if existing is not None:
        return existing
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    candidate = load_candidate_frame(manifest_path, manifest)
    print("building no-price quality/listing eligibility", flush=True)
    eligible_keys = quality_listing_eligible_keys(spec)
    candidate_quality, coverage = coverage_and_capacity(candidate, eligible_keys, spec)
    del candidate, eligible_keys
    gc.collect()
    uniqueness: dict[str, Any] = {
        "comparison_values_loaded_after_coverage_pass": False,
        "all_four_comparisons_passed": False,
        "comparisons": [],
    }
    if coverage["gate_passed_before_comparison_values"]:
        uniqueness = uniqueness_audit(candidate_quality, joint_manifest_path, spec)
    del candidate_quality
    gc.collect()
    passed = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_four_comparisons_passed"]
    )
    status = (
        "passed_no_return_coverage_capacity_and_uniqueness_pending_separate_return_diagnostic_preregistration"
        if passed
        else (
            "terminal_rejected_at_no_return_uniqueness_gate"
            if coverage["gate_passed_before_comparison_values"]
            else "terminal_rejected_at_no_return_coverage_or_capacity_gate"
        )
    )
    audit = {
        "schema_version": 1,
        "kind": "a_share_tushare_afternoon_signed_amount_efficiency_no_return_audit",
        "status": status,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": "ordered_candidate_coverage_capacity_then_four_terminal_factor_uniqueness_without_prices_or_forward_returns",
        "preregistration": {
            "path": str(DEFAULT_PREREGISTRATION.resolve()),
            "sha256": PREREGISTRATION_SHA256,
            "preregistered_at": spec["preregistered_at"],
        },
        "quality_semantics_repair": {
            "path": str(QUALITY_SEMANTICS_REPAIR_PATH.resolve()),
            "sha256": QUALITY_SEMANTICS_REPAIR_SHA256,
            "superseded_no_return_audit_sha256": SUPERSEDED_NO_RETURN_AUDIT_SHA256,
            "forward_return_fields_read_before_repair": False,
        },
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": manifest_sha256,
            "dataset_sha256": str(manifest["dataset_sha256"]),
            "rows": int(manifest["rows"]),
            "eligible_rows": int(manifest["eligible_rows"]),
        },
        "source_chain": {
            "raw_manifest_sha256": RAW_MANIFEST_SHA256,
            "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
            "joint_dataset_sha256": str(joint["dataset_sha256"]),
            "repository_evidence": repository_evidence,
            "snapshot_file_verification": verification,
        },
        "candidate": {
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": spec["candidate"]["formula"],
        },
        "coverage_and_capacity": coverage,
        "uniqueness": uniqueness,
        "decision": {
            "all_no_return_gates_passed": passed,
            "separate_return_diagnostic_preregistration_allowed": passed,
            "return_diagnostic_authorized_without_separate_preregistration": False,
            "aggregation_allowed": False,
            "current_scoring_allowed": False,
            "selection_allowed": False,
            "sizing_or_orders_allowed": False,
            "level2_intake_justified": False,
        },
        "source_fields_loaded": ["datetime", "symbol", "provider", "close", "amount"],
        "comparison_fields_loaded": (
            list(COMPARISON_FACTORS)
            if uniqueness["comparison_values_loaded_after_coverage_pass"]
            else []
        ),
        "daily_price_fields_loaded": [],
        "forward_return_fields_read": False,
        "training_or_model_fitting_performed": False,
        "investment_advice": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = (
        experiment_root
        / f"{run_id}_afternoon_signed_amount_efficiency_no_return_audit.json"
    )
    atomic_write_json(audit, path)
    return path


def load_diagnostic_preregistration(
    path: Path = DEFAULT_DIAGNOSTIC_PREREGISTRATION,
) -> dict[str, Any]:
    """Load the exact one-time return protocol frozen after no-return gates."""

    path = path.expanduser().resolve()
    _require_file(
        path,
        DIAGNOSTIC_PREREGISTRATION_SHA256,
        "afternoon-efficiency diagnostic protocol",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_tushare_afternoon_signed_amount_efficiency_diagnostic_preregistration",
    )
    factor = spec.get("factor") or {}
    evidence = spec.get("no_return_evidence") or {}
    snapshot = evidence.get("candidate_snapshot") or {}
    audit = evidence.get("ordered_audit") or {}
    coverage = evidence.get("coverage_and_capacity") or {}
    uniqueness = evidence.get("uniqueness") or {}
    holding = spec.get("holding_protocol") or {}
    gates = spec.get("diagnostic_gates") or {}
    decision = spec.get("post_diagnostic_decision") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("version") == 2
        and spec.get("status")
        == "frozen_after_corrected_no_return_coverage_capacity_and_uniqueness_pass_before_first_forward_return_read"
        and factor.get("name") == FACTOR_NAME
        and factor.get("direction") == "higher"
        and factor.get(
            "forward_returns_observed_before_this_diagnostic_preregistration"
        )
        is False
        and (evidence.get("protocol") or {}).get("sha256") == PREREGISTRATION_SHA256
        and (evidence.get("quality_semantics_repair") or {}).get("sha256")
        == QUALITY_SEMANTICS_REPAIR_SHA256
        and (evidence.get("superseded_ordered_audit") or {}).get("sha256")
        == SUPERSEDED_NO_RETURN_AUDIT_SHA256
        and snapshot.get("sha256") == CANDIDATE_MANIFEST_SHA256
        and snapshot.get("dataset_sha256")
        == "e580ce8bbcd7779256d344153def5d0587e1fd1ee8d59af63ef9e3d6a9254dd2"
        and snapshot.get("partitions") == 33_015
        and snapshot.get("rows") == 7_724_498
        and snapshot.get("eligible_rows") == 7_633_609
        and snapshot.get("zero_denominator_rows") == 90_889
        and snapshot.get("invalid_required_value_rows") == 0
        and audit.get("sha256") == NO_RETURN_AUDIT_SHA256
        and audit.get("forward_return_fields_read") is False
        and coverage.get("quality_listing_eligible_rows") == 1_331_759
        and coverage.get("candidate_eligible_rows_after_quality_and_listing")
        == 1_321_007
        and coverage.get("potential_non_overlapping_three_session_cohorts") == 540
        and coverage.get("gate_passed") is True
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("maximum_observed_absolute_median_daily_rank_correlation")
        == 0.5817546144749696
        and uniqueness.get("all_four_comparisons_passed") is True
        and holding.get("universe") == "buyable_main_chinext"
        and holding.get("minimum_listing_sessions") == research.MIN_LISTING_SESSIONS
        and holding.get("development_start") == "2019-01-01"
        and holding.get("development_end") == "2025-12-31"
        and holding.get("holding_period_trading_days") == 3
        and holding.get("non_overlapping_cohorts") is True
        and holding.get("topk") == 3
        and holding.get("open_cost") == 0.00012
        and holding.get("close_cost") == 0.00062
        and gates.get("minimum_non_overlapping_cohorts") == 200
        and gates.get("minimum_observed_calendar_years") == 5
        and decision.get("same_history_combination_return_evaluation_allowed") is False
        and decision.get("current_scoring_selection_sizing_or_orders_allowed") is False
        and boundary.get("forward_return_fields_read_before_registration") is False
        and boundary.get("training_or_model_fitting_performed") is False
    ):
        raise AfternoonEfficiencyError(
            "afternoon-efficiency diagnostic protocol no longer matches its frozen definition"
        )
    return spec


def validate_diagnostic_source_chain(
    spec: dict[str, Any], data_root: Path
) -> tuple[dict[str, Any], dict[str, Any], Path, Path, dict[str, Any]]:
    """Validate the passed no-return chain before any daily execution price."""

    no_return = spec["no_return_evidence"]
    protocol_link = no_return["protocol"]
    protocol_path = _repository_path(str(protocol_link["path"]))
    _require_file(protocol_path, PREREGISTRATION_SHA256, "no-return protocol")
    repair_link = no_return["quality_semantics_repair"]
    repair_path = _repository_path(str(repair_link["path"]))
    _require_file(
        repair_path,
        QUALITY_SEMANTICS_REPAIR_SHA256,
        "quality-semantics repair",
    )
    snapshot_link = no_return["candidate_snapshot"]
    manifest_path = (data_root / str(snapshot_link["path_below_data_root"])).resolve()
    _require_file(
        manifest_path, CANDIDATE_MANIFEST_SHA256, "candidate snapshot manifest"
    )
    manifest = research.load_json_record(
        manifest_path,
        kind="a_share_tushare_afternoon_signed_amount_efficiency_snapshot",
    )
    if (
        manifest.get("status")
        != "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        or manifest.get("protocol_sha256") != PREREGISTRATION_SHA256
        or manifest.get("dataset_sha256") != snapshot_link.get("dataset_sha256")
        or manifest.get("partitions") != 33_015
        or manifest.get("rows") != 7_724_498
        or manifest.get("eligible_rows") != 7_633_609
        or manifest.get("comparison_factor_values_read") is not False
        or manifest.get("forward_return_fields_read") is not False
    ):
        raise AfternoonEfficiencyError(
            "candidate snapshot conflicts with the diagnostic preregistration"
        )
    audit_link = no_return["ordered_audit"]
    audit_path = _repository_path(str(audit_link["path"]))
    _require_file(audit_path, NO_RETURN_AUDIT_SHA256, "ordered no-return audit")
    audit = research.load_json_record(
        audit_path,
        kind="a_share_tushare_afternoon_signed_amount_efficiency_no_return_audit",
    )
    if (
        audit.get("status") != audit_link.get("status")
        or (audit.get("candidate_snapshot") or {}).get("sha256")
        != CANDIDATE_MANIFEST_SHA256
        or (audit.get("quality_semantics_repair") or {}).get("sha256")
        != QUALITY_SEMANTICS_REPAIR_SHA256
        or (audit.get("coverage_and_capacity") or {}).get(
            "gate_passed_before_comparison_values"
        )
        is not True
        or (audit.get("uniqueness") or {}).get("all_four_comparisons_passed")
        is not True
        or (audit.get("decision") or {}).get(
            "separate_return_diagnostic_preregistration_allowed"
        )
        is not True
        or audit.get("daily_price_fields_loaded") != []
        or audit.get("forward_return_fields_read") is not False
    ):
        raise AfternoonEfficiencyError(
            "ordered no-return audit does not authorize the frozen diagnostic"
        )

    repository_evidence: dict[str, Any] = {}
    for name, link in (
        ("accepted_daily_price_basis", spec["accepted_daily_price_basis"]),
        ("quarterly_quality", spec["quarterly_quality"]),
    ):
        path = _repository_path(str(link["path"]))
        expected = str(link["sha256"])
        _require_file(path, expected, name.replace("_", " "))
        repository_evidence[name] = {"path": str(path), "sha256": expected}
    quality = spec["quarterly_quality"]
    quality_manifest_path = _repository_path(str(quality["manifest_path"]))
    _require_file(
        quality_manifest_path,
        str(quality["manifest_sha256"]),
        "quarterly quality manifest",
    )
    repository_evidence["quarterly_quality_manifest"] = {
        "path": str(quality_manifest_path),
        "sha256": str(quality["manifest_sha256"]),
    }
    for name, link in spec["execution_policies"].items():
        path = _repository_path(str(link["path"]))
        expected = str(link["sha256"])
        _require_file(path, expected, name.replace("_", " "))
        repository_evidence[name] = {"path": str(path), "sha256": expected}
    return manifest, audit, manifest_path, audit_path, repository_evidence


def require_diagnostic_unconsumed(experiment_root: Path) -> None:
    marker = experiment_root / CONSUMPTION_FILENAME
    if marker.exists():
        raise AfternoonEfficiencyError(
            f"afternoon-efficiency historical diagnostic is already consumed: {marker}"
        )
    for path in sorted(experiment_root.glob("*_factor_diagnostic.json")):
        record = research.load_json_record(path)
        if record.get("purpose") == DIAGNOSTIC_PURPOSE:
            raise AfternoonEfficiencyError(
                f"afternoon-efficiency historical diagnostic already exists: {path}"
            )


def attach_ranked_candidate(
    market: pd.DataFrame,
    candidate: pd.DataFrame,
    diagnostic_spec: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Merge and rank the candidate under the exact quality/listing gate."""

    required_market = {
        "datetime",
        "instrument",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "price_factor",
        "quality_eligible",
        "fundamental_quality_eligible",
        "listing_seasoning_eligible",
        "listing_age_sessions",
    }
    if missing := sorted(required_market - set(market.columns)):
        raise AfternoonEfficiencyError(
            "daily execution frame is missing columns: " + ", ".join(missing)
        )
    minute = candidate.rename(
        columns={"trade_date": "datetime", "symbol": "instrument"}
    ).copy()
    minute["datetime"] = pd.to_datetime(minute["datetime"]).dt.normalize()
    categories = pd.Index(
        sorted(
            set(minute["instrument"].astype(str).unique())
            | set(market["instrument"].astype(str).unique())
        )
    )
    symbol_dtype = pd.CategoricalDtype(categories=categories)
    minute["instrument"] = minute["instrument"].astype(str).astype(symbol_dtype)
    result = market.copy()
    result["instrument"] = result["instrument"].astype(str).astype(symbol_dtype)
    result = result.merge(
        minute[
            [
                "datetime",
                "instrument",
                FACTOR_NAME,
                f"{FACTOR_NAME}_eligible",
            ]
        ],
        on=["datetime", "instrument"],
        how="left",
        validate="one_to_one",
    )
    del minute, market
    gc.collect()
    quality_eligible = result["quality_eligible"].fillna(False).astype(bool)
    feature_start = candidate["trade_date"].min()
    feature_end = candidate["trade_date"].max()
    in_span = result["datetime"].between(feature_start, feature_end)
    quality_counts = (
        result.loc[in_span & quality_eligible]
        .groupby("datetime", observed=True, sort=True)
        .size()
    )
    eligibility = (
        result[f"{FACTOR_NAME}_eligible"].astype("boolean").fillna(False).astype(bool)
    )
    raw_values = pd.to_numeric(result[FACTOR_NAME], errors="coerce")
    factor_eligible = in_span & quality_eligible & eligibility & raw_values.notna()
    eligible_counts = (
        result.loc[factor_eligible]
        .groupby("datetime", observed=True, sort=True)
        .size()
        .reindex(quality_counts.index, fill_value=0)
    )
    minimum_names = 50
    cross_section_dates = eligible_counts.index[eligible_counts.ge(minimum_names)]
    rank_eligible = factor_eligible & result["datetime"].isin(cross_section_dates)
    scores = (
        raw_values.loc[rank_eligible]
        .groupby(result.loc[rank_eligible, "datetime"], sort=False)
        .rank(method="average", pct=True, ascending=True)
    )
    result[FACTOR_NAME] = np.nan
    result.loc[scores.index, FACTOR_NAME] = scores.astype("float64")
    ratios = eligible_counts / quality_counts
    holding = diagnostic_spec["holding_protocol"]
    hold_days = int(holding["holding_period_trading_days"])
    indices = np.arange(0, max(len(eligible_counts) - hold_days, 0), hold_days)
    potential = int(eligible_counts.iloc[indices].ge(minimum_names).sum())
    years = sorted(
        int(year)
        for year in pd.DatetimeIndex(
            eligible_counts.index[indices][
                eligible_counts.iloc[indices].ge(minimum_names)
            ]
        ).year.unique()
    )
    coverage = {
        "quality_listing_eligible_rows": int(quality_counts.sum()),
        "candidate_eligible_rows": int(factor_eligible.sum()),
        "rank_eligible_rows": int(rank_eligible.sum()),
        "rank_eligible_dates": int(len(cross_section_dates)),
        "median_coverage": float(ratios.median()),
        "p05_coverage": float(ratios.quantile(0.05)),
        "eligible_names_p05": float(eligible_counts.quantile(0.05)),
        "potential_non_overlapping_three_session_cohorts": potential,
        "observed_calendar_years": years,
        "listing_gate_applied_before_cross_sectional_ranking": True,
    }
    expected = diagnostic_spec["no_return_evidence"]["coverage_and_capacity"]
    if not (
        coverage["candidate_eligible_rows"]
        == expected["candidate_eligible_rows_after_quality_and_listing"]
        and math.isclose(
            coverage["median_coverage"],
            float(expected["median_coverage"]),
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        and math.isclose(
            coverage["p05_coverage"],
            float(expected["p05_coverage"]),
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        and math.isclose(
            coverage["eligible_names_p05"],
            float(expected["p05_eligible_names"]),
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        and coverage["potential_non_overlapping_three_session_cohorts"]
        == expected["potential_non_overlapping_three_session_cohorts"]
        and coverage["observed_calendar_years"] == expected["observed_calendar_years"]
    ):
        raise AfternoonEfficiencyError(
            "diagnostic-time candidate coverage changed from the passed no-return audit: "
            + json.dumps(
                {"observed": coverage, "expected": expected},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    return result, coverage


def run_diagnostic(args: argparse.Namespace) -> Path:
    """Consume the one preregistered historical return diagnostic."""

    data_root = Path(args.data_root).expanduser().resolve()
    provider_uri = Path(args.provider_uri).expanduser().resolve()
    fundamentals_path = Path(args.fundamentals).expanduser().resolve()
    experiment_root = Path(args.experiment_root).expanduser().resolve()
    experiment_root.mkdir(parents=True, exist_ok=True)
    require_diagnostic_unconsumed(experiment_root)
    spec = load_diagnostic_preregistration()
    manifest, no_return_audit, manifest_path, audit_path, repository_evidence = (
        validate_diagnostic_source_chain(spec, data_root)
    )
    verification = verify_snapshot_files(
        manifest, manifest_path, int(args.verification_workers)
    )
    candidate = load_candidate_frame(manifest_path, manifest)
    holding = spec["holding_protocol"]
    start = str(holding["development_start"])
    end = str(holding["development_end"])
    if candidate["trade_date"].min() < pd.Timestamp(start) or candidate[
        "trade_date"
    ].max() > pd.Timestamp(end):
        raise AfternoonEfficiencyError(
            "candidate feature dates escape the frozen diagnostic window"
        )
    print("loading accepted daily execution and quality context", flush=True)
    price_basis = research.research_price_basis_metadata(provider_uri)
    fundamentals = research.load_fundamentals(fundamentals_path)
    market = research.load_market_execution_data(
        provider_uri, start, end, int(args.batch_size)
    )
    market = research.attach_quality_asof(
        market,
        fundamentals,
        max_age_days=int(spec["quarterly_quality"]["maximum_age_days"]),
    )
    del fundamentals
    gc.collect()
    quality_counts = {
        "fundamental_eligible_rows_before_listing_gate": int(
            market["fundamental_quality_eligible"].fillna(False).sum()
        ),
        "eligible_rows_after_listing_gate": int(
            market["quality_eligible"].fillna(False).sum()
        ),
        "fundamental_rows_excluded_by_listing_gate": int(
            (
                market["fundamental_quality_eligible"].fillna(False)
                & ~market["listing_seasoning_eligible"].fillna(False)
            ).sum()
        ),
    }
    market_rows = int(len(market))
    market_start = market["datetime"].min().date().isoformat()
    market_end = market["datetime"].max().date().isoformat()
    ranked, coverage = attach_ranked_candidate(market, candidate, spec)
    del market, candidate
    gc.collect()

    execution_policy = research.load_prospective_execution_policy()
    research.require_prospective_execution_policy_compatibility(
        execution_policy,
        hold_days=int(holding["holding_period_trading_days"]),
        topk=int(holding["topk"]),
        open_cost=float(holding["open_cost"]),
        close_cost=float(holding["close_cost"]),
    )
    pilot_policy = research.load_pilot_execution_policy()
    marker_path = experiment_root / CONSUMPTION_FILENAME
    marker = {
        "kind": "a_share_tushare_afternoon_signed_amount_efficiency_historical_consumption",
        "status": "historical_forward_return_read_started",
        "started_at": research._timestamp(),
        "diagnostic_preregistration_path": str(
            DEFAULT_DIAGNOSTIC_PREREGISTRATION.resolve()
        ),
        "diagnostic_preregistration_sha256": DIAGNOSTIC_PREREGISTRATION_SHA256,
        "candidate_manifest_sha256": CANDIDATE_MANIFEST_SHA256,
        "no_return_audit_sha256": NO_RETURN_AUDIT_SHA256,
        "forward_return_fields_read": True,
        "selection_or_promotion_allowed": False,
    }
    research._atomic_write_text(
        marker_path, json.dumps(marker, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        "no-return gates reproduced; beginning the single authorized forward-return read",
        flush=True,
    )
    forward_returns = research.forward_factor_return_frame(
        ranked, int(holding["holding_period_trading_days"])
    )
    summaries = research.summarize_factor_diagnostics(
        forward_returns,
        [FACTOR_NAME],
        hold_days=int(holding["holding_period_trading_days"]),
        topk=int(holding["topk"]),
        open_cost=float(holding["open_cost"]),
        close_cost=float(holding["close_cost"]),
    )
    del forward_returns
    gc.collect()
    summary = (
        summaries[0]
        if summaries
        else research.unavailable_factor_diagnostic_summary(
            FACTOR_NAME, int(holding["holding_period_trading_days"])
        )
    )
    print("simulating normalized and CNY 200,000 execution policies", flush=True)
    summary["execution_aware_topk"] = research.simulate_prospective_execution_topk(
        ranked, FACTOR_NAME, policy=execution_policy
    )
    summary["pilot_execution_topk"] = research.simulate_pilot_execution_topk(
        ranked,
        FACTOR_NAME,
        execution_policy=execution_policy,
        pilot_policy=pilot_policy,
    )
    del ranked
    gc.collect()
    run_id = research._timestamp()
    diagnostic = {
        "run_id": run_id,
        "status": "completed",
        "purpose": DIAGNOSTIC_PURPOSE,
        "factor_catalog": [FACTOR_NAME],
        "factor_directions": {FACTOR_NAME: "higher"},
        "strategy_timing": {
            "universe": holding["universe"],
            "minimum_listing_sessions": research.MIN_LISTING_SESSIONS,
            "listing_gate_applied_before_cross_sectional_ranking": True,
            "holding_period_trading_days": int(holding["holding_period_trading_days"]),
            "rebalancing": "non_overlapping_every_holding_period",
            "signal_time": "afternoon minute factor known after signal-session close",
            "same_session_trade_allowed": False,
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "diagnostic_topk": int(holding["topk"]),
            "open_cost": float(holding["open_cost"]),
            "close_cost": float(holding["close_cost"]),
            "parameters_read_from_preregistration": True,
        },
        "quality_gate": {
            "source": str(fundamentals_path),
            "sha256": research.file_sha256(fundamentals_path),
            "effective_date": "strictly next local trading session after announcement_date",
            "max_quality_age_days": int(spec["quarterly_quality"]["maximum_age_days"]),
            **quality_counts,
        },
        "minute_factor": {
            "provider": "tushare",
            "frequency": "1m",
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": spec["factor"]["formula"],
            "candidate_manifest": {
                "path": str(manifest_path),
                "sha256": CANDIDATE_MANIFEST_SHA256,
                "dataset_sha256": manifest["dataset_sha256"],
                "verification": verification,
            },
            "no_return_audit": {
                "path": str(audit_path),
                "sha256": NO_RETURN_AUDIT_SHA256,
                "status": no_return_audit["status"],
            },
            "coverage": coverage,
            "source_open_high_low_or_volume_read_for_factor": False,
            "daily_prices_substituted_into_minute_rows": False,
            "forward_return_fields_stored_in_feature_source": False,
            "selection_or_promotion_allowed": False,
        },
        "data": {
            "provider_uri": str(provider_uri),
            **price_basis,
            "calendar_start": market_start,
            "calendar_end": market_end,
            "development_start": start,
            "development_end": end,
            "market_rows": market_rows,
            "eligible_rows": quality_counts["eligible_rows_after_listing_gate"],
            "minimum_listing_sessions": research.MIN_LISTING_SESSIONS,
            "test_period_used_for_factor_design": False,
        },
        "prospective_execution_policy": {
            "path": str(research.DEFAULT_PROSPECTIVE_EXECUTION_POLICY),
            "sha256": research.PROSPECTIVE_EXECUTION_POLICY_SHA256,
            "frozen_at": execution_policy["frozen_at"],
            "applied_to_every_reported_factor": True,
        },
        "pilot_execution_policy": {
            "path": str(research.DEFAULT_PILOT_EXECUTION_POLICY),
            "sha256": research.PILOT_EXECUTION_POLICY_SHA256,
            "frozen_at": pilot_policy["frozen_at"],
            "applied_to_every_reported_factor": True,
            "initial_capital_cny": 200000.0,
            "buy_lot_size_shares": 100,
            "primary_slippage_rate_each_side": 0.001,
            "maximum_daily_amount_participation": 0.01,
        },
        "preregistration": {
            "path": str(DEFAULT_DIAGNOSTIC_PREREGISTRATION.resolve()),
            "sha256": DIAGNOSTIC_PREREGISTRATION_SHA256,
            "preregistered_at": spec["preregistered_at"],
            "factor_returns_observed_before_registration": False,
            "single_use_marker": str(marker_path),
        },
        "repository_evidence": repository_evidence,
        "ranking_by_development_rank_ic": [summary],
        "post_diagnostic_decision": spec["post_diagnostic_decision"],
        "forward_return_fields_read": True,
        "selection_or_promotion_allowed": False,
        "limitations": [
            "This is an exploratory 2019-2025 diagnostic, not a pristine holdout and not investment advice.",
            "Only the higher direction frozen before this return read was evaluated.",
            "A failure may not be inverted, re-windowed, thresholded, or retested on this history.",
            "A pass admits only one factor and cannot satisfy the two-factor aggregation minimum by itself.",
            "Daily execution bars cannot reconstruct exact queue priority, partial fills, or realized market impact.",
        ],
    }
    destination = experiment_root / f"{run_id}_factor_diagnostic.json"
    research._atomic_write_text(
        destination,
        json.dumps(
            diagnostic, ensure_ascii=False, indent=2, default=research._json_default
        )
        + "\n",
    )
    marker.update(
        {
            "status": "historical_diagnostic_completed",
            "completed_at": research._timestamp(),
            "diagnostic_path": str(destination),
            "diagnostic_sha256": research.file_sha256(destination),
        }
    )
    research._atomic_write_text(
        marker_path, json.dumps(marker, ensure_ascii=False, indent=2) + "\n"
    )
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser(
        "build", help="Build the external candidate snapshot"
    )
    build_parser.add_argument("--data-root", type=Path, required=True)
    build_parser.add_argument("--workers", type=int, default=4)
    audit_parser = subparsers.add_parser(
        "audit", help="Run ordered coverage/capacity and uniqueness without returns"
    )
    audit_parser.add_argument("--data-root", type=Path, required=True)
    audit_parser.add_argument(
        "--experiment-root",
        type=Path,
        default=REPO_ROOT / "data/experiments/short_horizon",
    )
    audit_parser.add_argument("--workers", type=int, default=8)
    diagnose_parser = subparsers.add_parser(
        "diagnose", help="Consume the single preregistered three-session diagnostic"
    )
    diagnose_parser.add_argument("--data-root", type=Path, required=True)
    diagnose_parser.add_argument(
        "--provider-uri", type=Path, default=REPO_ROOT / "data/qlib/cn_a_share"
    )
    diagnose_parser.add_argument(
        "--fundamentals",
        type=Path,
        default=REPO_ROOT / "data/raw/a_share/fundamentals/quarterly_quality.parquet",
    )
    diagnose_parser.add_argument(
        "--experiment-root",
        type=Path,
        default=REPO_ROOT / "data/experiments/short_horizon",
    )
    diagnose_parser.add_argument("--batch-size", type=int, default=250)
    diagnose_parser.add_argument("--verification-workers", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "build":
        path = build_snapshot(data_root=args.data_root, workers=args.workers)
    elif args.command == "audit":
        path = run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
        )
    else:
        path = run_diagnostic(args)
    print(json.dumps({"status": "ok", "path": str(path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
