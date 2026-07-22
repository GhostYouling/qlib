#!/usr/bin/env python3
"""Build and audit the preregistered afternoon drawdown-recovery factor.

The build reads only minute identity, timestamp, and close from the immutable
Tushare source and restricts output to the immutable joint-clean stock-days.
The audit applies coverage and capacity before loading any terminal comparison
factor.  Neither command reads daily prices or forward returns.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gc
import hashlib
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_tushare_afternoon_signed_amount_efficiency as foundation


research = foundation.research
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_afternoon_drawdown_recovery_resilience_no_return_preregistration.json"
)
PREREGISTRATION_SHA256 = (
    "b4b1a15e5f8dc6073093bcd5ed52825c545e8f8cf228bee9ea9aa28e83eda6b8"
)
DEFAULT_DIAGNOSTIC_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_afternoon_drawdown_recovery_resilience_diagnostic_preregistration.json"
)
DIAGNOSTIC_PREREGISTRATION_SHA256 = (
    "9a4eb0da319e8acddd9cf8c22716d5bc408b46f4acb9408901651ea71b632515"
)
NO_RETURN_AUDIT_SHA256 = (
    "57227ee97c70155a69db5275514ad418c6a72ed467f1920a79eb2b578e4d8a36"
)
CANDIDATE_MANIFEST_SHA256 = (
    "a94413ba437dce44ef17215cce42c2d62e5aefab376f345df525dec3fd7a9c45"
)
DIAGNOSTIC_PURPOSE = (
    "development_only_preregistered_tushare_afternoon_drawdown_recovery_"
    "resilience_three_session_diagnostic_research_not_investment_advice"
)
CONSUMPTION_FILENAME = (
    "tushare_afternoon_drawdown_recovery_resilience_v1_consumption.json"
)
RAW_MANIFEST_SHA256 = foundation.RAW_MANIFEST_SHA256
JOINT_MANIFEST_SHA256 = foundation.JOINT_MANIFEST_SHA256
AFTERNOON_EFFICIENCY_MANIFEST_SHA256 = (
    "e1184b04385d1b0d1eb1eb4a56ad6c21609c4387cf53324cbbb41c420cdb8ed5"
)
AFTERNOON_EFFICIENCY_DATASET_SHA256 = (
    "e580ce8bbcd7779256d344153def5d0587e1fd1ee8d59af63ef9e3d6a9254dd2"
)
CURRENT_STATUS_SHA256 = (
    "c03b6eb2957885aa735f0e4a3ff82512654a5aabb5ccee935d71b618f734690b"
)
SOURCE_RUN_ID = foundation.SOURCE_RUN_ID
OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_afternoon_drawdown_recovery_resilience_v1"
FACTOR_NAME = "afternoon_drawdown_recovery_resilience_120m"
FACTOR_FORMULA = (
    "R / (D + R), where D is the maximum running-peak log drawdown on the "
    "11:30 plus 13:01-15:00 close path, t_star is its earliest occurrence, "
    "and R is the terminal log-price recovery from x_t_star"
)
BASE_COMPARISON_FACTORS = foundation.COMPARISON_FACTORS
COMPARISON_FACTORS = (*BASE_COMPARISON_FACTORS, foundation.FACTOR_NAME)
COMPARISON_DIRECTIONS = (*foundation.COMPARISON_DIRECTIONS, "higher")
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
SOURCE_MINUTE_CODES = foundation.SOURCE_MINUTE_CODES
SOURCE_MINUTE_CODE_SET = foundation.SOURCE_MINUTE_CODE_SET
BASELINE_INDEX = foundation.BASELINE_INDEX
AFTERNOON_START_INDEX = foundation.AFTERNOON_START_INDEX
DEVELOPMENT_START = foundation.DEVELOPMENT_START
DEVELOPMENT_END = foundation.DEVELOPMENT_END


class RecoveryResilienceError(RuntimeError):
    """Raised when a frozen source, factor, or no-return gate is violated."""


def _repository_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    observed = foundation.file_digest(path)
    if observed != expected_sha256:
        raise RecoveryResilienceError(
            f"{label} fingerprint mismatch: expected {expected_sha256}, got {observed}"
        )


def empty_output_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
            "provider": pd.Series(dtype="string"),
            FACTOR_NAME: pd.Series(dtype="float64"),
            f"{FACTOR_NAME}_eligible": pd.Series(dtype="bool"),
        }
    ).loc[:, OUTPUT_COLUMNS]


def load_preregistration(
    path: Path = DEFAULT_PREREGISTRATION,
) -> dict[str, Any]:
    """Load and enforce the exact protocol frozen before candidate values."""

    path = path.expanduser().resolve()
    _require_file(path, PREREGISTRATION_SHA256, "drawdown-recovery protocol")
    spec = research.load_json_record(
        path,
        kind="a_share_tushare_afternoon_drawdown_recovery_resilience_no_return_preregistration",
    )
    current = spec.get("current_research_state") or {}
    candidate = spec.get("candidate") or {}
    grid = candidate.get("bar_grid") or {}
    validity = candidate.get("validity") or {}
    output = spec.get("derived_snapshot") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_candidate_factor_values_comparison_values_or_forward_returns"
        and current.get("sha256") == CURRENT_STATUS_SHA256
        and current.get("status")
        == "aggregation_blocked_after_afternoon_efficiency_terminal_rejection_zero_dual_gate_factors"
        and current.get("terminal_mechanism_count_before_this_candidate") == 29
        and current.get("aggregation_allowed") is False
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("diagnostic_direction") == "higher"
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and set(candidate.get("source_fields_forbidden") or ())
        == {
            "open",
            "high",
            "low",
            "volume",
            "amount",
            "any_daily_price",
            "any_forward_return",
        }
        and grid.get("required_full_source_rows") == 241
        and grid.get("baseline_bar_end") == "11:30"
        and grid.get("path_bar_ends_start") == "13:01"
        and grid.get("path_bar_ends_end") == "15:00"
        and grid.get("afternoon_bars") == 120
        and grid.get("path_points_including_baseline") == 121
        and candidate.get("formula") == FACTOR_FORMULA
        and validity.get("all_121_required_close_values_finite_and_positive") is True
        and validity.get("maximum_log_drawdown_strictly_positive") is True
        and validity.get("terminal_recovery_nonnegative_by_construction") is True
        and validity.get("allowed_half_open_interval") == [0.0, 1.0]
        and validity.get(
            "imputation_clipping_winsorization_or_daily_substitution_allowed"
        )
        is False
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
        and uniqueness.get("all_five_comparisons_must_pass") is True
        and boundary.get("candidate_factor_values_observed_before_registration")
        is False
        and boundary.get(
            "terminal_factor_comparison_values_observed_for_this_candidate_before_registration"
        )
        is False
        and boundary.get("forward_return_fields_read_before_registration") is False
    ):
        raise RecoveryResilienceError(
            "drawdown-recovery protocol no longer matches its frozen definition"
        )
    return spec


def validate_repository_chain(spec: dict[str, Any]) -> dict[str, Any]:
    """Fingerprint-bind repository state without reading a price or return."""

    return foundation.validate_repository_chain(spec)


def validate_external_chain(
    spec: dict[str, Any], data_root: Path
) -> tuple[dict[str, Any], dict[str, Any], Path, Path, dict[str, Any], Path]:
    """Validate raw, joint-clean, and prior-factor immutable manifests."""

    raw, joint, raw_path, joint_path = foundation.validate_external_chain(
        spec, data_root
    )
    link = (spec.get("source_chain") or {}).get(
        "afternoon_efficiency_comparison_manifest"
    ) or {}
    comparison_path = (data_root / str(link.get("path_below_data_root"))).resolve()
    _require_file(
        comparison_path,
        AFTERNOON_EFFICIENCY_MANIFEST_SHA256,
        "afternoon-efficiency comparison manifest",
    )
    comparison = research.load_json_record(
        comparison_path,
        kind="a_share_tushare_afternoon_signed_amount_efficiency_snapshot",
    )
    if not (
        comparison.get("status")
        == "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        and comparison.get("factor_name") == foundation.FACTOR_NAME
        and comparison.get("factor_direction") == "higher"
        and comparison.get("dataset_sha256") == AFTERNOON_EFFICIENCY_DATASET_SHA256
        and comparison.get("rows") == 7_724_498
        and comparison.get("partitions") == 33_015
        and len(comparison.get("files") or []) == 33_015
        and comparison.get("forward_return_fields_read") is False
        and comparison.get("comparison_factor_values_read") is False
    ):
        raise RecoveryResilienceError(
            "afternoon-efficiency comparison snapshot identity is rejected"
        )
    return raw, joint, raw_path, joint_path, comparison, comparison_path


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Compute the frozen factor for one symbol-year using close only."""

    if missing := sorted(set(RAW_COLUMNS) - set(raw.columns)):
        raise RecoveryResilienceError(
            "raw minute partition is missing columns: " + ", ".join(missing)
        )
    if missing := sorted({"trade_date", "symbol"} - set(base.columns)):
        raise RecoveryResilienceError(
            "joint base partition is missing columns: " + ", ".join(missing)
        )
    if base.empty:
        return empty_output_frame(), {
            "base_rows": 0,
            "eligible_rows": 0,
            "zero_drawdown_rows": 0,
            "invalid_required_value_rows": 0,
            "recovery_identity_violation_rows": 0,
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
        raise RecoveryResilienceError(f"joint base identity is invalid for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )

    raw_work = raw[list(RAW_COLUMNS)].copy()
    raw_work["datetime"] = pd.to_datetime(raw_work["datetime"], errors="coerce")
    if raw_work["datetime"].isna().any():
        raise RecoveryResilienceError(f"raw timestamps are invalid for {symbol}")
    raw_work["symbol"] = raw_work["symbol"].astype(str).str.upper()
    raw_work["provider"] = raw_work["provider"].astype(str).str.lower()
    if set(raw_work["symbol"]) != {symbol} or set(raw_work["provider"]) != {"tushare"}:
        raise RecoveryResilienceError(f"raw identity is invalid for {symbol}")
    raw_work["trade_date"] = raw_work["datetime"].dt.normalize()
    raw_work = raw_work[raw_work["trade_date"].isin(base_work["trade_date"])].copy()
    raw_work["minute_code"] = (
        raw_work["datetime"].dt.hour * 60 + raw_work["datetime"].dt.minute
    ).astype(np.int16)
    raw_work["close"] = pd.to_numeric(raw_work["close"], errors="coerce")
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
        raise RecoveryResilienceError(
            f"raw source does not reproduce every joint-base 241-row grid for {symbol}"
        )
    codes = raw_work["minute_code"].to_numpy().reshape(-1, 241)
    if not np.array_equal(codes, np.broadcast_to(SOURCE_MINUTE_CODES, codes.shape)):
        raise RecoveryResilienceError(f"raw source grid order changed for {symbol}")

    closes = raw_work["close"].to_numpy(dtype=float).reshape(-1, 241)
    path = np.concatenate(
        [
            closes[:, BASELINE_INDEX : BASELINE_INDEX + 1],
            closes[:, AFTERNOON_START_INDEX:],
        ],
        axis=1,
    )
    if path.shape[1] != 121:
        raise RecoveryResilienceError("drawdown-recovery path length changed")
    required_valid = np.isfinite(path).all(axis=1) & (path > 0.0).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_path = np.log(path / path[:, :1])
    running_peak = np.maximum.accumulate(log_path, axis=1)
    drawdown = running_peak - log_path
    maximum_drawdown = np.max(drawdown, axis=1)
    trough_index = np.argmax(drawdown, axis=1)
    row_index = np.arange(len(path))
    trough_log_price = log_path[row_index, trough_index]
    direct_recovery = log_path[:, -1] - trough_log_price
    recovery = (running_peak[:, -1] - running_peak[row_index, trough_index]) + (
        maximum_drawdown - drawdown[:, -1]
    )
    identity_violation = (
        required_valid
        & np.isfinite(direct_recovery)
        & np.isfinite(recovery)
        & (np.abs(direct_recovery - recovery) > 1e-12)
    )
    if identity_violation.any():
        raise RecoveryResilienceError(f"drawdown-recovery algebra changed for {symbol}")
    negative_recovery = required_valid & np.isfinite(recovery) & (recovery < 0.0)
    if negative_recovery.any():
        raise RecoveryResilienceError(f"terminal recovery became negative for {symbol}")
    denominator = maximum_drawdown + recovery
    with np.errstate(divide="ignore", invalid="ignore"):
        values = recovery / denominator
    eligible = (
        required_valid
        & np.isfinite(maximum_drawdown)
        & (maximum_drawdown > 0.0)
        & np.isfinite(recovery)
        & (recovery >= 0.0)
        & np.isfinite(values)
        & (values >= 0.0)
        & (values < 1.0)
    )
    output = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol,
            "provider": "tushare",
            FACTOR_NAME: np.where(eligible, values, np.nan),
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    return output, {
        "base_rows": int(len(output)),
        "eligible_rows": int(eligible.sum()),
        "zero_drawdown_rows": int((required_valid & ~(maximum_drawdown > 0.0)).sum()),
        "invalid_required_value_rows": int((~required_valid).sum()),
        "recovery_identity_violation_rows": int(identity_violation.sum()),
    }


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_afternoon_drawdown_recovery_resilience"
        / OUTPUT_RUN_ID
    )


def _load_checkpoint(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
    paths: foundation.PartitionPaths,
) -> tuple[dict[str, Any], Counter[str]] | None:
    if not paths.partial_sidecar.exists():
        paths.partial_data.unlink(missing_ok=True)
        return None
    record = json.loads(paths.partial_sidecar.read_text(encoding="utf-8"))
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    valid = (
        record.get("kind")
        == "a_share_tushare_afternoon_drawdown_recovery_resilience_partition"
        and record.get("protocol_sha256") == PREREGISTRATION_SHA256
        and record.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and record.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
        and record.get("raw_source_byte_sha256") == raw_record.get("byte_sha256")
        and record.get("joint_base_byte_sha256")
        == joint_record.get("output_byte_sha256")
        and paths.partial_data.is_file()
        and foundation.file_digest(raw_path) == raw_record.get("byte_sha256")
        and foundation.file_digest(base_path) == joint_record.get("output_byte_sha256")
        and foundation.file_digest(paths.partial_data)
        == record.get("output_byte_sha256")
    )
    if not valid:
        raise RecoveryResilienceError(
            f"completed drawdown-recovery checkpoint changed: {paths.partial_sidecar}"
        )
    output = pd.read_parquet(paths.partial_data)
    if len(output) != int(record.get("rows", -1)) or foundation.frame_digest(
        output
    ) != record.get("output_frame_sha256"):
        raise RecoveryResilienceError(
            f"completed drawdown-recovery frame changed: {paths.partial_data}"
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
    paths = foundation.partition_paths(partial_root, final_root, joint_record)
    completed = _load_checkpoint(raw_record, joint_record, paths)
    if completed is not None:
        record, dates = completed
        return record, dates, True
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    if foundation.file_digest(raw_path) != raw_record.get("byte_sha256"):
        raise RecoveryResilienceError(f"raw partition changed: {raw_path}")
    if foundation.file_digest(base_path) != joint_record.get("output_byte_sha256"):
        raise RecoveryResilienceError(f"joint-base partition changed: {base_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    base = pd.read_parquet(base_path, columns=["trade_date", "symbol"])
    if len(raw) != int(raw_record.get("rows", -1)):
        raise RecoveryResilienceError(f"raw row count changed: {raw_path}")
    if len(base) != int(joint_record.get("rows", -1)):
        raise RecoveryResilienceError(f"joint-base row count changed: {base_path}")
    output, quality = compute_partition_frame(
        raw, base, symbol=str(joint_record["symbol"])
    )
    foundation.atomic_write_frame(output, paths.partial_data)
    record = {
        "schema_version": 1,
        "kind": "a_share_tushare_afternoon_drawdown_recovery_resilience_partition",
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
        "output_byte_sha256": foundation.file_digest(paths.partial_data),
        "output_frame_sha256": foundation.frame_digest(output),
        "quality": quality,
        "source_fields_read": list(RAW_COLUMNS),
        "daily_price_fields_read": [],
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
    }
    foundation.atomic_write_json(record, paths.partial_sidecar)
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


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Build all 33,015 symbol-year partitions with resumable checkpoints."""

    if workers < 1 or workers > 8:
        raise ValueError("--workers must be between 1 and 8")
    data_root = data_root.expanduser().resolve()
    spec = load_preregistration()
    repository_evidence = validate_repository_chain(spec)
    raw, joint, raw_manifest_path, joint_manifest_path, _, _ = validate_external_chain(
        spec, data_root
    )
    final_root = output_root(data_root)
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    final_manifest = final_root / "snapshot_manifest.json"
    if final_root.exists():
        if not final_manifest.is_file():
            raise RecoveryResilienceError(
                f"published drawdown-recovery root has no manifest: {final_root}"
            )
        manifest = research.load_json_record(
            final_manifest,
            kind="a_share_tushare_afternoon_drawdown_recovery_resilience_snapshot",
        )
        if not (
            manifest.get("protocol_sha256") == PREREGISTRATION_SHA256
            and manifest.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
            and manifest.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
            and manifest.get("output_run_id") == OUTPUT_RUN_ID
        ):
            raise RecoveryResilienceError(
                f"published drawdown-recovery snapshot changed: {final_root}"
            )
        return final_manifest
    if shutil.disk_usage(data_root).free < 5 * 1024**3:
        raise RecoveryResilienceError("external data root has less than 5 GiB free")

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
        raise RecoveryResilienceError(
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
            raise RecoveryResilienceError(
                f"joint-clean raw source binding changed for {key[0]}/{key[1]}"
            )
        by_symbol.setdefault(key[0], []).append((raw_record, joint_record))

    lock_path = data_root / ".a_share_tushare_afternoon_drawdown_recovery.lock"
    with foundation.ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        all_records: list[dict[str, Any]] = []
        eligible_dates: Counter[str] = Counter()
        resumed = 0
        completed_symbols = 0
        print(
            f"building {len(joint_records):,} drawdown-recovery partitions "
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
            raise RecoveryResilienceError(
                "not every source partition produced a drawdown-recovery checkpoint"
            )
        _require_file(raw_manifest_path, RAW_MANIFEST_SHA256, "raw minute manifest")
        _require_file(
            joint_manifest_path, JOINT_MANIFEST_SHA256, "joint-clean manifest"
        )
        all_records.sort(key=lambda item: (str(item["symbol"]), int(item["year"])))
        quality = foundation._aggregate_quality(all_records)
        dataset_payload = "\n".join(
            f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
            for item in all_records
        ).encode("utf-8")
        manifest = {
            "schema_version": 1,
            "kind": "a_share_tushare_afternoon_drawdown_recovery_resilience_snapshot",
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
            "source_fields_read": list(RAW_COLUMNS),
            "source_open_high_low_volume_or_amount_read": False,
            "daily_price_fields_read": [],
            "comparison_factor_values_read": False,
            "forward_return_fields_read": False,
            "training_or_model_fitting_performed": False,
            "aggregation_scoring_selection_sizing_or_orders_performed": False,
            "promotion_allowed": False,
            "resumed_partitions": resumed,
            "repository_evidence": repository_evidence,
        }
        foundation.atomic_write_json(manifest, partial_root / "snapshot_manifest.json")
        final_root.parent.mkdir(parents=True, exist_ok=True)
        partial_root.replace(final_root)
        return final_manifest


def verify_snapshot_files(
    manifest: dict[str, Any], manifest_path: Path, workers: int
) -> dict[str, int]:
    records = list(manifest.get("files") or [])
    if len(records) != 33_015:
        raise RecoveryResilienceError("candidate snapshot partition count changed")
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(record: dict[str, Any]) -> tuple[int, int, int]:
        path = Path(str(record["path"])).resolve()
        try:
            path.relative_to(partition_root)
        except ValueError as exc:
            raise RecoveryResilienceError(
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
        raise RecoveryResilienceError("candidate snapshot aggregate counts changed")
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
        raise RecoveryResilienceError("candidate frame row count changed")
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
        or not frame.loc[eligible, FACTOR_NAME].ge(0.0).all()
        or not frame.loc[eligible, FACTOR_NAME].lt(1.0).all()
        or frame.loc[~eligible, FACTOR_NAME].notna().any()
    ):
        raise RecoveryResilienceError("candidate frame values or keys are invalid")
    frame["symbol"] = frame["symbol"].astype("category")
    return frame


def coverage_and_capacity(
    candidate: pd.DataFrame,
    eligible_keys: pd.DataFrame,
    spec: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run the first no-return gate and retain eligible candidate rows."""

    merged = eligible_keys.merge(
        candidate, on=["trade_date", "symbol"], how="left", validate="one_to_one"
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
        "daily_coverage_frame_sha256": research.dataframe_content_sha256(daily),
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
    for trade_date, group in frame[["trade_date", FACTOR_NAME, comparison]].groupby(
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
    comparison_manifest: dict[str, Any],
    comparison_manifest_path: Path,
    spec: dict[str, Any],
    workers: int,
) -> dict[str, Any]:
    """Load five terminal values only after coverage passes and gate synonyms."""

    print("coverage passed; loading five terminal comparison factors", flush=True)
    comparison_verification = foundation.verify_snapshot_files(
        comparison_manifest, comparison_manifest_path, workers
    )
    dataset = pa_dataset.dataset(
        str(joint_manifest_path.parent / "partitions"), format="parquet"
    )
    table = dataset.to_table(
        columns=["trade_date", "symbol", *BASE_COMPARISON_FACTORS],
        use_threads=True,
    )
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
        raise RecoveryResilienceError("base comparison frame identity changed")
    prior = foundation.load_candidate_frame(
        comparison_manifest_path, comparison_manifest
    )[["trade_date", "symbol", foundation.FACTOR_NAME]]
    prior["symbol"] = prior["symbol"].astype(str)
    comparisons = comparisons.merge(
        prior, on=["trade_date", "symbol"], how="left", validate="one_to_one"
    )
    del prior
    candidate_quality = candidate_quality.copy()
    candidate_quality["symbol"] = candidate_quality["symbol"].astype(str)
    merged = candidate_quality.merge(
        comparisons, on=["trade_date", "symbol"], how="left", validate="one_to_one"
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
    all_passed = len(results) == 5 and all(item["gate_passed"] for item in results)
    return {
        "comparison_values_loaded_after_coverage_pass": True,
        "comparison_field_count": len(results),
        "prior_candidate_snapshot_file_verification": comparison_verification,
        "minimum_pairwise_names_per_session": minimum_names,
        "minimum_pairwise_sessions_per_comparison": minimum_sessions,
        "maximum_allowed_absolute_median_daily_rank_correlation": threshold,
        "comparisons": results,
        "maximum_observed_absolute_median_daily_rank_correlation": (
            max(observed) if observed else None
        ),
        "all_five_comparisons_passed": all_passed,
    }


def _find_existing_audit(experiment_root: Path, manifest_sha256: str) -> Path | None:
    for path in sorted(
        experiment_root.glob(
            "*_afternoon_drawdown_recovery_resilience_no_return_audit.json"
        )
    ):
        record = research.load_json_record(path)
        if (
            record.get("kind")
            == "a_share_tushare_afternoon_drawdown_recovery_resilience_no_return_audit"
            and (record.get("candidate_snapshot") or {}).get("sha256")
            == manifest_sha256
        ):
            return path
    return None


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    """Run coverage/capacity and then conditional five-factor uniqueness."""

    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_preregistration()
    repository_evidence = validate_repository_chain(spec)
    (
        _,
        joint,
        _,
        joint_manifest_path,
        comparison_manifest,
        comparison_manifest_path,
    ) = validate_external_chain(spec, data_root)
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"candidate snapshot must be built before its no-return audit: {manifest_path}"
        )
    manifest = research.load_json_record(
        manifest_path,
        kind="a_share_tushare_afternoon_drawdown_recovery_resilience_snapshot",
    )
    if not (
        manifest.get("status")
        == "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        and manifest.get("protocol_sha256") == PREREGISTRATION_SHA256
        and manifest.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and manifest.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
        and manifest.get("rows") == 7_724_498
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
    ):
        raise RecoveryResilienceError("candidate snapshot identity is rejected")
    manifest_sha256 = foundation.file_digest(manifest_path)
    existing = _find_existing_audit(experiment_root, manifest_sha256)
    if existing is not None:
        return existing
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    candidate = load_candidate_frame(manifest_path, manifest)
    print("building no-price quality/listing eligibility", flush=True)
    eligible_keys = foundation.quality_listing_eligible_keys(spec)
    candidate_quality, coverage = coverage_and_capacity(candidate, eligible_keys, spec)
    del candidate, eligible_keys
    gc.collect()
    uniqueness: dict[str, Any] = {
        "comparison_values_loaded_after_coverage_pass": False,
        "all_five_comparisons_passed": False,
        "comparisons": [],
    }
    if coverage["gate_passed_before_comparison_values"]:
        uniqueness = uniqueness_audit(
            candidate_quality,
            joint_manifest_path,
            comparison_manifest,
            comparison_manifest_path,
            spec,
            workers,
        )
    del candidate_quality
    gc.collect()
    passed = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_five_comparisons_passed"]
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
        "kind": "a_share_tushare_afternoon_drawdown_recovery_resilience_no_return_audit",
        "status": status,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": "ordered_candidate_coverage_capacity_then_five_terminal_factor_uniqueness_without_prices_or_forward_returns",
        "preregistration": {
            "path": str(DEFAULT_PREREGISTRATION.resolve()),
            "sha256": PREREGISTRATION_SHA256,
            "preregistered_at": spec["preregistered_at"],
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
            "afternoon_efficiency_manifest_sha256": AFTERNOON_EFFICIENCY_MANIFEST_SHA256,
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
        "source_fields_loaded": list(RAW_COLUMNS),
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
        / f"{run_id}_afternoon_drawdown_recovery_resilience_no_return_audit.json"
    )
    foundation.atomic_write_json(audit, path)
    return path


def load_diagnostic_preregistration(
    path: Path = DEFAULT_DIAGNOSTIC_PREREGISTRATION,
) -> dict[str, Any]:
    """Load the exact one-time return protocol frozen after no-return gates."""

    path = path.expanduser().resolve()
    _require_file(
        path,
        DIAGNOSTIC_PREREGISTRATION_SHA256,
        "drawdown-recovery diagnostic protocol",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_tushare_afternoon_drawdown_recovery_resilience_diagnostic_preregistration",
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
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_after_no_return_coverage_capacity_and_uniqueness_pass_before_first_forward_return_read"
        and factor.get("name") == FACTOR_NAME
        and factor.get("direction") == "higher"
        and factor.get("formula") == FACTOR_FORMULA
        and factor.get(
            "forward_returns_observed_before_this_diagnostic_preregistration"
        )
        is False
        and (evidence.get("protocol") or {}).get("sha256") == PREREGISTRATION_SHA256
        and snapshot.get("sha256") == CANDIDATE_MANIFEST_SHA256
        and snapshot.get("dataset_sha256")
        == "07f1d0e83de44a1d533acf6e269bf34fc02d0c6ef582affdd96eac5c7af769c8"
        and snapshot.get("partitions") == 33_015
        and snapshot.get("rows") == 7_724_498
        and snapshot.get("eligible_rows") == 7_631_291
        and snapshot.get("zero_drawdown_rows") == 93_207
        and snapshot.get("invalid_required_value_rows") == 0
        and snapshot.get("recovery_identity_violation_rows") == 0
        and audit.get("sha256") == NO_RETURN_AUDIT_SHA256
        and audit.get("forward_return_fields_read") is False
        and coverage.get("quality_listing_eligible_rows") == 1_331_759
        and coverage.get("candidate_eligible_rows_after_quality_and_listing")
        == 1_320_685
        and coverage.get("potential_non_overlapping_three_session_cohorts") == 540
        and coverage.get("gate_passed") is True
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("maximum_observed_absolute_median_daily_rank_correlation")
        == 0.6074802302511947
        and uniqueness.get("all_five_comparisons_passed") is True
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
        raise RecoveryResilienceError(
            "drawdown-recovery diagnostic protocol no longer matches its frozen definition"
        )
    return spec


def validate_diagnostic_source_chain(
    spec: dict[str, Any], data_root: Path
) -> tuple[dict[str, Any], dict[str, Any], Path, Path, dict[str, Any]]:
    """Validate the passed no-return chain before daily execution prices."""

    no_return = spec["no_return_evidence"]
    protocol_link = no_return["protocol"]
    protocol_path = _repository_path(str(protocol_link["path"]))
    _require_file(protocol_path, PREREGISTRATION_SHA256, "no-return protocol")
    snapshot_link = no_return["candidate_snapshot"]
    manifest_path = (data_root / str(snapshot_link["path_below_data_root"])).resolve()
    _require_file(
        manifest_path, CANDIDATE_MANIFEST_SHA256, "candidate snapshot manifest"
    )
    manifest = research.load_json_record(
        manifest_path,
        kind="a_share_tushare_afternoon_drawdown_recovery_resilience_snapshot",
    )
    if not (
        manifest.get("status")
        == "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        and manifest.get("protocol_sha256") == PREREGISTRATION_SHA256
        and manifest.get("dataset_sha256") == snapshot_link.get("dataset_sha256")
        and manifest.get("partitions") == 33_015
        and manifest.get("rows") == 7_724_498
        and manifest.get("eligible_rows") == 7_631_291
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("source_open_high_low_volume_or_amount_read") is False
    ):
        raise RecoveryResilienceError(
            "candidate snapshot conflicts with the diagnostic preregistration"
        )
    audit_link = no_return["ordered_audit"]
    audit_path = _repository_path(str(audit_link["path"]))
    _require_file(audit_path, NO_RETURN_AUDIT_SHA256, "ordered no-return audit")
    audit = research.load_json_record(
        audit_path,
        kind="a_share_tushare_afternoon_drawdown_recovery_resilience_no_return_audit",
    )
    if not (
        audit.get("status") == audit_link.get("status")
        and (audit.get("candidate_snapshot") or {}).get("sha256")
        == CANDIDATE_MANIFEST_SHA256
        and (audit.get("coverage_and_capacity") or {}).get(
            "gate_passed_before_comparison_values"
        )
        is True
        and (audit.get("uniqueness") or {}).get("all_five_comparisons_passed") is True
        and (audit.get("decision") or {}).get(
            "separate_return_diagnostic_preregistration_allowed"
        )
        is True
        and audit.get("daily_price_fields_loaded") == []
        and audit.get("forward_return_fields_read") is False
    ):
        raise RecoveryResilienceError(
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
        raise RecoveryResilienceError(
            f"drawdown-recovery historical diagnostic is already consumed: {marker}"
        )
    for path in sorted(experiment_root.glob("*_factor_diagnostic.json")):
        record = research.load_json_record(path)
        if record.get("purpose") == DIAGNOSTIC_PURPOSE:
            raise RecoveryResilienceError(
                f"drawdown-recovery historical diagnostic already exists: {path}"
            )


def attach_ranked_candidate(
    market: pd.DataFrame,
    candidate: pd.DataFrame,
    diagnostic_spec: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reuse the tested ranking gate with this module's frozen factor name."""

    prior_factor_name = foundation.FACTOR_NAME
    foundation.FACTOR_NAME = FACTOR_NAME
    try:
        return foundation.attach_ranked_candidate(market, candidate, diagnostic_spec)
    finally:
        foundation.FACTOR_NAME = prior_factor_name


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
        raise RecoveryResilienceError(
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
        "kind": "a_share_tushare_afternoon_drawdown_recovery_resilience_historical_consumption",
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
            "quality_state_semantics": spec["quarterly_quality"][
                "quality_state_semantics"
            ],
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
            "source_open_high_low_volume_or_amount_read_for_factor": False,
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
