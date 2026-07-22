#!/usr/bin/env python3
"""Build and audit the preregistered intraday terminal close location.

The candidate reads only minute identity, timestamp, and close from the
immutable Tushare source.  It measures where the 15:00 close lies within the
full-session range of continuous minute closes.  Build and no-return audit
never read a daily price or forward return, and terminal comparison values
load only after coverage passes.
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

import a_share_tushare_intraday_upside_semivariance_share as previous


foundation = previous.foundation
profile = previous.previous
entropy = previous.entropy
recovery = previous.recovery
research = previous.research
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_intraday_terminal_close_location_no_return_preregistration.json"
)
PREREGISTRATION_SHA256 = (
    "f15e3743458cdc7d52b68be50210fb35a76d8c3f5a62ed6415785a16ed4f1ef4"
)
DEFAULT_TERMINAL_RECORD = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_intraday_terminal_close_location_research_record.json"
)
TERMINAL_RECORD_SHA256 = (
    "b5c0f740353e35df27d7f0390dbee7e500990fb4d7986550faadd632ab0ef0c9"
)
NO_RETURN_AUDIT_SHA256 = (
    "1ff6a7b0b73192664145f97e2e9d66351b80fad20d4b8add19478d484ab559af"
)
CANDIDATE_MANIFEST_SHA256 = (
    "69a66d063cb470702db5e8b256f0b4be0f54c847c3188578fe85fba6ba63441c"
)
RAW_MANIFEST_SHA256 = foundation.RAW_MANIFEST_SHA256
JOINT_MANIFEST_SHA256 = foundation.JOINT_MANIFEST_SHA256
AFTERNOON_EFFICIENCY_MANIFEST_SHA256 = previous.AFTERNOON_EFFICIENCY_MANIFEST_SHA256
AFTERNOON_EFFICIENCY_DATASET_SHA256 = previous.AFTERNOON_EFFICIENCY_DATASET_SHA256
AFTERNOON_RECOVERY_MANIFEST_SHA256 = previous.AFTERNOON_RECOVERY_MANIFEST_SHA256
AFTERNOON_RECOVERY_DATASET_SHA256 = previous.AFTERNOON_RECOVERY_DATASET_SHA256
AMOUNT_ENTROPY_MANIFEST_SHA256 = previous.AMOUNT_ENTROPY_MANIFEST_SHA256
AMOUNT_ENTROPY_DATASET_SHA256 = previous.AMOUNT_ENTROPY_DATASET_SHA256
AMOUNT_PROFILE_PERSISTENCE_MANIFEST_SHA256 = (
    previous.AMOUNT_PROFILE_PERSISTENCE_MANIFEST_SHA256
)
AMOUNT_PROFILE_PERSISTENCE_DATASET_SHA256 = (
    previous.AMOUNT_PROFILE_PERSISTENCE_DATASET_SHA256
)
UPSIDE_SEMIVARIANCE_MANIFEST_SHA256 = previous.CANDIDATE_MANIFEST_SHA256
UPSIDE_SEMIVARIANCE_DATASET_SHA256 = (
    "4745113ff183f44f9dfab2114a5ff161471d2a8fba9f3aa529a45e25e4638c0b"
)
CURRENT_STATUS_SHA256 = (
    "c3d59982bc509d3648b80862dc1dd4e1df61f6cbb171af84226d46c7e0400661"
)
SOURCE_RUN_ID = foundation.SOURCE_RUN_ID
OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_intraday_terminal_close_location_v1"
FACTOR_NAME = "intraday_terminal_close_location_240m"
FACTOR_FORMULA = (
    "(c_240 - min(c_1..c_240)) / (max(c_1..c_240) - min(c_1..c_240)), "
    "using the 240 continuous-session closes at 09:31-11:30 and 13:01-15:00"
)
COMPARISON_FACTORS = (*previous.COMPARISON_FACTORS, previous.FACTOR_NAME)
COMPARISON_DIRECTIONS = (*previous.COMPARISON_DIRECTIONS, "higher")
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
SOURCE_MINUTE_CODES = previous.SOURCE_MINUTE_CODES
SOURCE_MINUTE_CODE_SET = previous.SOURCE_MINUTE_CODE_SET
CONTINUOUS_MINUTE_CODES = previous.CONTINUOUS_MINUTE_CODES
BOUNDARY_TOLERANCE = 1e-12


class TerminalCloseLocationError(RuntimeError):
    """Raised when a frozen source, factor, or no-return gate is violated."""


def _repository_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    observed = foundation.file_digest(path)
    if observed != expected_sha256:
        raise TerminalCloseLocationError(
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


def load_preregistration(path: Path = DEFAULT_PREREGISTRATION) -> dict[str, Any]:
    """Load and enforce the exact protocol frozen before candidate values."""

    path = path.expanduser().resolve()
    _require_file(path, PREREGISTRATION_SHA256, "terminal-close-location protocol")
    spec = research.load_json_record(
        path,
        kind="a_share_tushare_intraday_terminal_close_location_no_return_preregistration",
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
        == "aggregation_blocked_after_intraday_upside_semivariance_share_terminal_rejection_zero_dual_gate_factors"
        and current.get("terminal_mechanism_count_before_this_candidate") == 33
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
        and grid.get("excluded_source_bar_end") == "09:30"
        and grid.get("continuous_bar_ends_start") == "09:31"
        and grid.get("morning_bar_ends_end") == "11:30"
        and grid.get("afternoon_bar_ends_start") == "13:01"
        and grid.get("continuous_bar_ends_end") == "15:00"
        and grid.get("continuous_bars") == 240
        and grid.get("terminal_bar_end") == "15:00"
        and candidate.get("formula") == FACTOR_FORMULA
        and validity.get("all_240_required_close_values_finite_and_strictly_positive")
        is True
        and validity.get("continuous_close_range_strictly_positive") is True
        and validity.get("allowed_closed_interval") == [0.0, 1.0]
        and validity.get("zero_close_range_policy") == "missing"
        and validity.get("ieee_boundary_canonicalization_tolerance")
        == BOUNDARY_TOLERANCE
        and validity.get(
            "statistical_clipping_imputation_winsorization_or_daily_substitution_allowed"
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
        and uniqueness.get("all_nine_comparisons_must_pass") is True
        and boundary.get("candidate_factor_values_observed_before_registration")
        is False
        and boundary.get(
            "terminal_factor_comparison_values_observed_for_this_candidate_before_registration"
        )
        is False
        and boundary.get("forward_return_fields_read_before_registration") is False
    ):
        raise TerminalCloseLocationError(
            "terminal-close-location protocol no longer matches its frozen definition"
        )
    return spec


def validate_repository_chain(spec: dict[str, Any]) -> dict[str, Any]:
    return foundation.validate_repository_chain(spec)


def load_terminal_record_if_present() -> dict[str, Any] | None:
    """Validate and return the immutable terminal record when this branch is closed."""

    if not DEFAULT_TERMINAL_RECORD.is_file():
        return None
    _require_file(
        DEFAULT_TERMINAL_RECORD,
        TERMINAL_RECORD_SHA256,
        "terminal-close-location research record",
    )
    record = research.load_json_record(
        DEFAULT_TERMINAL_RECORD,
        kind="a_share_tushare_intraday_terminal_close_location_research_record",
    )
    protocol = (record.get("ordered_protocol") or {}).get(
        "no_return_preregistration"
    ) or {}
    audit = (record.get("ordered_protocol") or {}).get("no_return_audit") or {}
    candidate = (record.get("source_chain") or {}).get("candidate_manifest") or {}
    decision = record.get("decision") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("status") == "terminal_rejected_at_no_return_uniqueness_gate"
        and protocol.get("sha256") == PREREGISTRATION_SHA256
        and candidate.get("sha256") == CANDIDATE_MANIFEST_SHA256
        and audit.get("sha256") == NO_RETURN_AUDIT_SHA256
        and audit.get("status") == "terminal_rejected_at_no_return_uniqueness_gate"
        and audit.get("forward_return_fields_read") is False
        and decision.get("return_diagnostic_allowed") is False
        and decision.get("aggregation_candidate_added") is False
        and boundary.get("forward_return_fields_read") is False
    ):
        raise TerminalCloseLocationError(
            "terminal-close-location research record is inconsistent"
        )
    return record


def _validate_upside_semivariance_manifest(
    spec: dict[str, Any], data_root: Path
) -> tuple[dict[str, Any], Path]:
    link = (spec.get("source_chain") or {}).get(
        "upside_semivariance_share_comparison_manifest"
    ) or {}
    path = (data_root / str(link.get("path_below_data_root"))).resolve()
    _require_file(
        path,
        UPSIDE_SEMIVARIANCE_MANIFEST_SHA256,
        "upside-semivariance-share manifest",
    )
    manifest = research.load_json_record(
        path,
        kind="a_share_tushare_intraday_upside_semivariance_share_snapshot",
    )
    if not (
        manifest.get("status")
        == "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        and manifest.get("factor_name") == previous.FACTOR_NAME
        and manifest.get("factor_direction") == "higher"
        and manifest.get("dataset_sha256")
        == UPSIDE_SEMIVARIANCE_DATASET_SHA256
        and manifest.get("partitions") == 33_015
        and manifest.get("rows") == 7_724_498
        and manifest.get("eligible_rows") == 7_695_092
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
    ):
        raise TerminalCloseLocationError(
            "upside-semivariance-share manifest identity is rejected"
        )
    return manifest, path


def validate_external_chain(
    spec: dict[str, Any], data_root: Path
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    Path,
    Path,
    dict[str, Any],
    Path,
    dict[str, Any],
    Path,
    dict[str, Any],
    Path,
    dict[str, Any],
    Path,
    dict[str, Any],
    Path,
]:
    (
        raw,
        joint,
        raw_path,
        joint_path,
        efficiency,
        efficiency_path,
        recovery_manifest,
        recovery_path,
        entropy,
        entropy_path,
        profile_manifest,
        profile_path,
    ) = previous.validate_external_chain(spec, data_root)
    upside, upside_path = _validate_upside_semivariance_manifest(spec, data_root)
    return (
        raw,
        joint,
        raw_path,
        joint_path,
        efficiency,
        efficiency_path,
        recovery_manifest,
        recovery_path,
        entropy,
        entropy_path,
        profile_manifest,
        profile_path,
        upside,
        upside_path,
    )


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Compute the terminal close's location in the continuous close range."""

    if missing := sorted(set(RAW_COLUMNS) - set(raw.columns)):
        raise TerminalCloseLocationError(
            "raw minute partition is missing columns: " + ", ".join(missing)
        )
    if missing := sorted({"trade_date", "symbol"} - set(base.columns)):
        raise TerminalCloseLocationError(
            "joint base partition is missing columns: " + ", ".join(missing)
        )
    empty_quality = {
        "base_rows": 0,
        "eligible_rows": 0,
        "zero_close_range_rows": 0,
        "invalid_required_value_rows": 0,
        "ieee_boundary_canonicalization_rows": 0,
        "location_range_violation_rows": 0,
    }
    if base.empty:
        return empty_output_frame(), empty_quality

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
        raise TerminalCloseLocationError(f"joint base identity is invalid for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(drop=True)

    raw_work = raw[list(RAW_COLUMNS)].copy()
    raw_work["datetime"] = pd.to_datetime(raw_work["datetime"], errors="coerce")
    if raw_work["datetime"].isna().any():
        raise TerminalCloseLocationError(f"raw timestamps are invalid for {symbol}")
    raw_work["symbol"] = raw_work["symbol"].astype(str).str.upper()
    raw_work["provider"] = raw_work["provider"].astype(str).str.lower()
    if set(raw_work["symbol"]) != {symbol} or set(raw_work["provider"]) != {"tushare"}:
        raise TerminalCloseLocationError(f"raw identity is invalid for {symbol}")
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
        on_grid=("minute_code", lambda values: values.isin(SOURCE_MINUTE_CODE_SET).sum()),
    )
    if (
        len(stats) != len(base_work)
        or not stats.index.equals(pd.DatetimeIndex(base_work["trade_date"]))
        or not stats["rows"].eq(241).all()
        or not stats["unique_times"].eq(241).all()
        or not stats["on_grid"].eq(241).all()
    ):
        raise TerminalCloseLocationError(
            f"raw source does not reproduce every joint-base 241-row grid for {symbol}"
        )
    codes = raw_work["minute_code"].to_numpy().reshape(-1, 241)
    if not np.array_equal(codes, np.broadcast_to(SOURCE_MINUTE_CODES, codes.shape)):
        raise TerminalCloseLocationError(f"raw source grid order changed for {symbol}")
    if len(CONTINUOUS_MINUTE_CODES) != 240:
        raise TerminalCloseLocationError("continuous close support changed")

    closes = raw_work["close"].to_numpy(dtype=float).reshape(-1, 241)[:, 1:]
    required_valid = np.isfinite(closes).all(axis=1) & (closes > 0.0).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        low_close = np.min(closes, axis=1)
        high_close = np.max(closes, axis=1)
        terminal_close = closes[:, -1]
        close_range = high_close - low_close
        values = (terminal_close - low_close) / close_range
    positive_range = (
        np.isfinite(low_close)
        & np.isfinite(high_close)
        & np.isfinite(terminal_close)
        & np.isfinite(close_range)
        & (close_range > 0.0)
    )
    canonicalizable = (
        required_valid
        & positive_range
        & np.isfinite(values)
        & (
            ((values > 1.0) & (values <= 1.0 + BOUNDARY_TOLERANCE))
            | ((values < 0.0) & (values >= -BOUNDARY_TOLERANCE))
        )
    )
    values = np.where(canonicalizable & (values > 1.0), 1.0, values)
    values = np.where(canonicalizable & (values < 0.0), 0.0, values)
    range_violation = (
        required_valid
        & positive_range
        & np.isfinite(values)
        & ((values < 0.0) | (values > 1.0))
    )
    if range_violation.any():
        raise TerminalCloseLocationError(
            f"terminal close location escaped [0, 1] beyond tolerance for {symbol}"
        )
    eligible = (
        required_valid
        & positive_range
        & np.isfinite(values)
        & (values >= 0.0)
        & (values <= 1.0)
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
        "zero_close_range_rows": int((required_valid & ~positive_range).sum()),
        "invalid_required_value_rows": int((~required_valid).sum()),
        "ieee_boundary_canonicalization_rows": int(canonicalizable.sum()),
        "location_range_violation_rows": int(range_violation.sum()),
    }


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_intraday_terminal_close_location"
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
        == "a_share_tushare_intraday_terminal_close_location_partition"
        and record.get("protocol_sha256") == PREREGISTRATION_SHA256
        and record.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and record.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
        and record.get("raw_source_byte_sha256") == raw_record.get("byte_sha256")
        and record.get("joint_base_byte_sha256") == joint_record.get("output_byte_sha256")
        and paths.partial_data.is_file()
        and foundation.file_digest(raw_path) == raw_record.get("byte_sha256")
        and foundation.file_digest(base_path) == joint_record.get("output_byte_sha256")
        and foundation.file_digest(paths.partial_data) == record.get("output_byte_sha256")
    )
    if not valid:
        raise TerminalCloseLocationError(
            f"completed terminal-close-location checkpoint changed: {paths.partial_sidecar}"
        )
    output = pd.read_parquet(paths.partial_data)
    if len(output) != int(record.get("rows", -1)) or foundation.frame_digest(output) != record.get(
        "output_frame_sha256"
    ):
        raise TerminalCloseLocationError(
            f"completed terminal-close-location frame changed: {paths.partial_data}"
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
        raise TerminalCloseLocationError(f"raw partition changed: {raw_path}")
    if foundation.file_digest(base_path) != joint_record.get("output_byte_sha256"):
        raise TerminalCloseLocationError(f"joint-base partition changed: {base_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    base = pd.read_parquet(base_path, columns=["trade_date", "symbol"])
    if len(raw) != int(raw_record.get("rows", -1)):
        raise TerminalCloseLocationError(f"raw row count changed: {raw_path}")
    if len(base) != int(joint_record.get("rows", -1)):
        raise TerminalCloseLocationError(f"joint-base row count changed: {base_path}")
    output, quality = compute_partition_frame(raw, base, symbol=str(joint_record["symbol"]))
    foundation.atomic_write_frame(output, paths.partial_data)
    record = {
        "schema_version": 1,
        "kind": "a_share_tushare_intraday_terminal_close_location_partition",
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
        "minute_price_fields_read": ["close"],
        "minute_open_high_low_volume_or_amount_fields_read": [],
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
    for raw_record, joint_record in sorted(pairs, key=lambda pair: int(pair[1]["year"])):
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
    final_root = output_root(data_root)
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    final_manifest = final_root / "snapshot_manifest.json"
    if final_root.exists():
        if not final_manifest.is_file():
            raise TerminalCloseLocationError(
                f"published terminal-close-location root has no manifest: {final_root}"
            )
        _require_file(
            final_manifest,
            CANDIDATE_MANIFEST_SHA256,
            "published terminal-close-location manifest",
        )
        load_terminal_record_if_present()
        manifest = research.load_json_record(
            final_manifest,
            kind="a_share_tushare_intraday_terminal_close_location_snapshot",
        )
        if not (
            manifest.get("protocol_sha256") == PREREGISTRATION_SHA256
            and manifest.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
            and manifest.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
            and manifest.get("output_run_id") == OUTPUT_RUN_ID
            and manifest.get("dataset_sha256")
            == "da90792615fa120d07417c8d9d5a2d8660a16f7c5ea5cd2bb09b5cb724eeba00"
            and manifest.get("partitions") == 33_015
            and manifest.get("rows") == 7_724_498
            and manifest.get("eligible_rows") == 7_695_092
            and (manifest.get("quality") or {}).get("zero_close_range_rows")
            == 29_406
            and manifest.get("forward_return_fields_read") is False
        ):
            raise TerminalCloseLocationError(
                f"published terminal-close-location snapshot changed: {final_root}"
            )
        return final_manifest
    repository_evidence = validate_repository_chain(spec)
    chain = validate_external_chain(spec, data_root)
    raw, joint, raw_manifest_path, joint_manifest_path = chain[:4]
    if shutil.disk_usage(data_root).free < 5 * 1024**3:
        raise TerminalCloseLocationError("external data root has less than 5 GiB free")

    raw_records = list(raw.get("files") or [])
    joint_records = list(joint.get("files") or [])
    raw_by_key = {(str(item["symbol"]), int(item["year"])): item for item in raw_records}
    joint_by_key = {
        (str(item["symbol"]), int(item["year"])): item for item in joint_records
    }
    if (
        len(raw_by_key) != 33_015
        or len(joint_by_key) != 33_015
        or set(raw_by_key) != set(joint_by_key)
    ):
        raise TerminalCloseLocationError(
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
            raise TerminalCloseLocationError(
                f"joint-clean raw source binding changed for {key[0]}/{key[1]}"
            )
        by_symbol.setdefault(key[0], []).append((raw_record, joint_record))

    lock_path = data_root / ".a_share_tushare_intraday_terminal_close_location.lock"
    with foundation.ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        all_records: list[dict[str, Any]] = []
        eligible_dates: Counter[str] = Counter()
        resumed = 0
        completed_symbols = 0
        print(
            f"building {len(joint_records):,} terminal-close-location partitions "
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
                    if completed_symbols % 25 == 0 or completed_symbols == len(by_symbol):
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
            raise TerminalCloseLocationError(
                "not every source partition produced an terminal-close-location checkpoint"
            )
        _require_file(raw_manifest_path, RAW_MANIFEST_SHA256, "raw minute manifest")
        _require_file(joint_manifest_path, JOINT_MANIFEST_SHA256, "joint-clean manifest")
        all_records.sort(key=lambda item: (str(item["symbol"]), int(item["year"])))
        quality = foundation._aggregate_quality(all_records)
        dataset_payload = "\n".join(
            f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
            for item in all_records
        ).encode("utf-8")
        manifest = {
            "schema_version": 1,
            "kind": "a_share_tushare_intraday_terminal_close_location_snapshot",
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
            "source_close_read": True,
            "source_open_high_low_volume_or_amount_read": False,
            "standalone_09_30_row_excluded_from_formula": True,
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
        raise TerminalCloseLocationError("candidate snapshot partition count changed")
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(record: dict[str, Any]) -> tuple[int, int, int]:
        path = Path(str(record["path"])).resolve()
        try:
            path.relative_to(partition_root)
        except ValueError as exc:
            raise TerminalCloseLocationError(
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
                print(f"verified candidate partitions {index}/{len(records)}", flush=True)
    if rows != manifest.get("rows") or eligible != manifest.get("eligible_rows"):
        raise TerminalCloseLocationError("candidate snapshot aggregate counts changed")
    return {
        "partitions_verified": len(records),
        "rows_verified": rows,
        "eligible_rows_verified": eligible,
        "partition_bytes_verified": byte_count,
    }


def load_candidate_frame(manifest_path: Path, manifest: dict[str, Any]) -> pd.DataFrame:
    dataset = pa_dataset.dataset(str(manifest_path.parent / "partitions"), format="parquet")
    table = dataset.to_table(columns=list(OUTPUT_COLUMNS), use_threads=True)
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    if len(frame) != int(manifest.get("rows", -1)):
        raise TerminalCloseLocationError("candidate frame row count changed")
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce").dt.normalize()
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
        or not frame.loc[eligible, FACTOR_NAME].between(0.0, 1.0).all()
        or frame.loc[~eligible, FACTOR_NAME].notna().any()
    ):
        raise TerminalCloseLocationError("candidate frame values or keys are invalid")
    frame["symbol"] = frame["symbol"].astype("category")
    return frame


def coverage_and_capacity(
    candidate: pd.DataFrame,
    eligible_keys: pd.DataFrame,
    spec: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    previous_name = previous.FACTOR_NAME
    previous.FACTOR_NAME = FACTOR_NAME
    try:
        return previous.coverage_and_capacity(candidate, eligible_keys, spec)
    finally:
        previous.FACTOR_NAME = previous_name


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
    efficiency_manifest: dict[str, Any],
    efficiency_manifest_path: Path,
    recovery_manifest: dict[str, Any],
    recovery_manifest_path: Path,
    entropy_manifest: dict[str, Any],
    entropy_manifest_path: Path,
    profile_manifest: dict[str, Any],
    profile_manifest_path: Path,
    upside_manifest: dict[str, Any],
    upside_manifest_path: Path,
    spec: dict[str, Any],
    workers: int,
) -> dict[str, Any]:
    print("coverage passed; loading nine terminal comparison factors", flush=True)
    efficiency_verification = foundation.verify_snapshot_files(
        efficiency_manifest, efficiency_manifest_path, workers
    )
    recovery_verification = recovery.verify_snapshot_files(
        recovery_manifest, recovery_manifest_path, workers
    )
    entropy_verification = entropy.verify_snapshot_files(
        entropy_manifest, entropy_manifest_path, workers
    )
    profile_verification = profile.verify_snapshot_files(
        profile_manifest, profile_manifest_path, workers
    )
    upside_verification = previous.verify_snapshot_files(
        upside_manifest, upside_manifest_path, workers
    )
    dataset = pa_dataset.dataset(str(joint_manifest_path.parent / "partitions"), format="parquet")
    table = dataset.to_table(
        columns=["trade_date", "symbol", *recovery.BASE_COMPARISON_FACTORS],
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
        raise TerminalCloseLocationError("base comparison frame identity changed")
    efficiency = foundation.load_candidate_frame(
        efficiency_manifest_path, efficiency_manifest
    )[["trade_date", "symbol", foundation.FACTOR_NAME]]
    recovery_frame = recovery.load_candidate_frame(
        recovery_manifest_path, recovery_manifest
    )[["trade_date", "symbol", recovery.FACTOR_NAME]]
    entropy_frame = entropy.load_candidate_frame(
        entropy_manifest_path, entropy_manifest
    )[["trade_date", "symbol", entropy.FACTOR_NAME]]
    profile_frame = profile.load_candidate_frame(
        profile_manifest_path, profile_manifest
    )[
        ["trade_date", "symbol", profile.FACTOR_NAME]
    ]
    upside_frame = previous.load_candidate_frame(
        upside_manifest_path, upside_manifest
    )[
        ["trade_date", "symbol", previous.FACTOR_NAME]
    ]
    for frame in (
        efficiency,
        recovery_frame,
        entropy_frame,
        profile_frame,
        upside_frame,
    ):
        frame["symbol"] = frame["symbol"].astype(str)
    comparisons = (
        comparisons.merge(
            efficiency, on=["trade_date", "symbol"], how="left", validate="one_to_one"
        )
        .merge(
            recovery_frame,
            on=["trade_date", "symbol"],
            how="left",
            validate="one_to_one",
        )
        .merge(
            entropy_frame,
            on=["trade_date", "symbol"],
            how="left",
            validate="one_to_one",
        )
        .merge(
            profile_frame,
            on=["trade_date", "symbol"],
            how="left",
            validate="one_to_one",
        )
        .merge(
            upside_frame,
            on=["trade_date", "symbol"],
            how="left",
            validate="one_to_one",
        )
    )
    del efficiency, recovery_frame, entropy_frame, profile_frame, upside_frame
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
            sessions >= minimum_sessions and math.isfinite(median) and abs(median) < threshold
        )
        results.append(
            {
                "comparison_factor": comparison,
                "score_direction": direction,
                "pairwise_sessions": sessions,
                "minimum_pairwise_names_observed": (
                    int(daily["pairwise_names"].min()) if sessions else 0
                ),
                "median_daily_rank_correlation": median if math.isfinite(median) else None,
                "absolute_median_daily_rank_correlation": (
                    abs(median) if math.isfinite(median) else None
                ),
                "daily_rank_correlation_p05": (
                    float(daily["rank_correlation"].quantile(0.05)) if sessions else None
                ),
                "daily_rank_correlation_p95": (
                    float(daily["rank_correlation"].quantile(0.95)) if sessions else None
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
    all_passed = len(results) == 9 and all(item["gate_passed"] for item in results)
    return {
        "comparison_values_loaded_after_coverage_pass": True,
        "comparison_field_count": len(results),
        "prior_candidate_snapshot_file_verification": {
            "afternoon_efficiency": efficiency_verification,
            "afternoon_recovery": recovery_verification,
            "amount_entropy": entropy_verification,
            "amount_profile_serial_persistence": profile_verification,
            "upside_semivariance_share": upside_verification,
        },
        "minimum_pairwise_names_per_session": minimum_names,
        "minimum_pairwise_sessions_per_comparison": minimum_sessions,
        "maximum_allowed_absolute_median_daily_rank_correlation": threshold,
        "comparisons": results,
        "maximum_observed_absolute_median_daily_rank_correlation": (
            max(observed) if observed else None
        ),
        "all_nine_comparisons_passed": all_passed,
    }


def _find_existing_audit(experiment_root: Path, manifest_sha256: str) -> Path | None:
    for path in sorted(
        experiment_root.glob(
            "*_intraday_terminal_close_location_no_return_audit.json"
        )
    ):
        record = research.load_json_record(path)
        if (
            record.get("kind")
            == "a_share_tushare_intraday_terminal_close_location_no_return_audit"
            and (record.get("candidate_snapshot") or {}).get("sha256") == manifest_sha256
        ):
            return path
    return None


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_preregistration()
    terminal_record = load_terminal_record_if_present()
    if terminal_record is not None:
        manifest_path = output_root(data_root) / "snapshot_manifest.json"
        _require_file(
            manifest_path,
            CANDIDATE_MANIFEST_SHA256,
            "terminal candidate snapshot manifest",
        )
        audit_link = (terminal_record.get("ordered_protocol") or {}).get(
            "no_return_audit"
        ) or {}
        audit_path = _repository_path(str(audit_link.get("path", "")))
        _require_file(audit_path, NO_RETURN_AUDIT_SHA256, "terminal no-return audit")
        audit = research.load_json_record(
            audit_path,
            kind="a_share_tushare_intraday_terminal_close_location_no_return_audit",
        )
        if not (
            audit.get("status") == "terminal_rejected_at_no_return_uniqueness_gate"
            and (audit.get("candidate_snapshot") or {}).get("sha256")
            == CANDIDATE_MANIFEST_SHA256
            and (audit.get("coverage_and_capacity") or {}).get(
                "gate_passed_before_comparison_values"
            )
            is True
            and (audit.get("uniqueness") or {}).get(
                "all_nine_comparisons_passed"
            )
            is False
            and (audit.get("decision") or {}).get(
                "separate_return_diagnostic_preregistration_allowed"
            )
            is False
            and audit.get("forward_return_fields_read") is False
        ):
            raise TerminalCloseLocationError(
                "terminal no-return audit is inconsistent"
            )
        return audit_path
    repository_evidence = validate_repository_chain(spec)
    chain = validate_external_chain(spec, data_root)
    (
        _,
        joint,
        _,
        joint_manifest_path,
        efficiency_manifest,
        efficiency_manifest_path,
        recovery_manifest,
        recovery_manifest_path,
        entropy_manifest,
        entropy_manifest_path,
        profile_manifest,
        profile_manifest_path,
        upside_manifest,
        upside_manifest_path,
    ) = chain
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"candidate snapshot must be built before its no-return audit: {manifest_path}"
        )
    manifest = research.load_json_record(
        manifest_path,
        kind="a_share_tushare_intraday_terminal_close_location_snapshot",
    )
    if not (
        manifest.get("status")
        == "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        and manifest.get("protocol_sha256") == PREREGISTRATION_SHA256
        and manifest.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and manifest.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
        and manifest.get("rows") == 7_724_498
        and manifest.get("source_close_read") is True
        and manifest.get("source_open_high_low_volume_or_amount_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
    ):
        raise TerminalCloseLocationError("candidate snapshot identity is rejected")
    manifest_sha256 = foundation.file_digest(manifest_path)
    if manifest_sha256 != CANDIDATE_MANIFEST_SHA256:
        raise TerminalCloseLocationError(
            "candidate snapshot fingerprint changed: expected "
            f"{CANDIDATE_MANIFEST_SHA256}, got {manifest_sha256}"
        )
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
        "all_nine_comparisons_passed": False,
        "comparisons": [],
    }
    if coverage["gate_passed_before_comparison_values"]:
        uniqueness = uniqueness_audit(
            candidate_quality,
            joint_manifest_path,
            efficiency_manifest,
            efficiency_manifest_path,
            recovery_manifest,
            recovery_manifest_path,
            entropy_manifest,
            entropy_manifest_path,
            profile_manifest,
            profile_manifest_path,
            upside_manifest,
            upside_manifest_path,
            spec,
            workers,
        )
    del candidate_quality
    gc.collect()
    passed = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_nine_comparisons_passed"]
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
        "kind": "a_share_tushare_intraday_terminal_close_location_no_return_audit",
        "status": status,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": "ordered_candidate_coverage_capacity_then_nine_terminal_factor_uniqueness_without_daily_prices_or_forward_returns",
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
            "afternoon_recovery_manifest_sha256": AFTERNOON_RECOVERY_MANIFEST_SHA256,
            "amount_entropy_manifest_sha256": AMOUNT_ENTROPY_MANIFEST_SHA256,
            "amount_profile_serial_persistence_manifest_sha256": AMOUNT_PROFILE_PERSISTENCE_MANIFEST_SHA256,
            "upside_semivariance_share_manifest_sha256": UPSIDE_SEMIVARIANCE_MANIFEST_SHA256,
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
        "minute_price_fields_loaded": ["close"],
        "minute_open_high_low_volume_or_amount_fields_loaded": [],
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
        / f"{run_id}_intraday_terminal_close_location_no_return_audit.json"
    )
    foundation.atomic_write_json(audit, path)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build", help="Build the external candidate snapshot")
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
        raise TerminalCloseLocationError(f"unsupported command: {args.command}")
    print(json.dumps({"status": "ok", "path": str(path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
