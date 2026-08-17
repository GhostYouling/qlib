#!/usr/bin/env python3
"""Source-bound two-pass feature builder for Campaign151.

The first pass accumulates raw minute amount by date and clock across complete
stock-day profiles. The second pass subtracts the current stock, forms the
exact leave-one-out peer mean, and calls the separately frozen pure formula.
No command-line build entry is exposed here; a separately frozen zero-value
plan runner must authorize the confirmed build.
"""

from __future__ import annotations

import concurrent.futures
import datetime as dt
import gc
import hashlib
import json
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign151_formula as formula
from scripts import a_share_tushare_intraday_market_idiosyncratic_share as engine


foundation = engine.foundation
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_BUILDER_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_source_bound_builder_preregistration_20260815.json"
)
BUILDER_PROTOCOL_SHA256 = (
    "a7cd811fda8d925621a4d9e713f32723d01a1023d407943a309a78d8fb3530d7"
)
FORMULA_MODULE_SHA256 = (
    "e739c773543bf245ad02b73bdb552a41d294777f79cba5a7f2cb84af52f574fe"
)
FORMULA_PROTOCOL_SHA256 = (
    "99c2f95cad4058d004cc26aeecb5e710199ee930320beab97826a674cd6dff8c"
)
RAW_MANIFEST_SHA256 = "9b3d959563c9d182f38981c6a36bdb3bc9b415de08487a9e1f9e850825c0839f"
JOINT_MANIFEST_SHA256 = (
    "453c6719cb3c7da42fed8807b28a2bfe988700283e9625a6db97912534f368de"
)
JOINT_DATASET_SHA256 = (
    "0e4fe7c05536cdfcecc2936bc880726902f5560061188ffff82ef7ee6f346983"
)
CALENDAR_SHA256 = "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
RAW_MANIFEST_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/raw/a_share/rich/tushare/minutes/1m/"
    "snapshots/tushare_stk_mins_1m_2019_2025_ea0cbb8f/snapshot_manifest.json"
)
JOINT_MANIFEST_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_sentiment_clean/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_sentiment_clean_v1/"
    "snapshot_manifest.json"
)
CALENDAR_PATH = REPO_ROOT / "data/qlib/cn_a_share/calendars/day.txt"
FACTOR_NAME = formula.FACTOR_NAME
FACTOR_DIRECTION = formula.FACTOR_DIRECTION
PROFILE_POSITIONS = formula.PROFILE_POSITIONS
MINIMUM_LEAVE_ONE_OUT_PEERS = formula.MINIMUM_LEAVE_ONE_OUT_PEERS
RAW_COLUMNS = ("datetime", "symbol", "provider", "amount")
JOINT_COLUMNS = ("trade_date", "symbol")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
BENCHMARK_COLUMNS = (
    "trade_date",
    "profile_position",
    "raw_amount_sum",
    "complete_profile_count",
)
BENCHMARK_FILENAME = "raw_amount_peer_benchmark_240m.parquet"
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign151_feature_library_v1"
)
FULL_SOURCE_MINUTE_CODES = frozenset(
    [9 * 60 + 30]
    + list(range(9 * 60 + 31, 11 * 60 + 31))
    + list(range(13 * 60 + 1, 15 * 60 + 1))
)
CONTINUOUS_MINUTE_CODES = tuple(
    list(range(9 * 60 + 31, 11 * 60 + 31)) + list(range(13 * 60 + 1, 15 * 60 + 1))
)
EXPECTED_PARTITIONS = 33_015
EXPECTED_ROWS = 7_724_498
EXPECTED_SYMBOLS = 5_396
MINIMUM_FREE_BYTES = 10 * 1024**3


class Campaign151FeatureError(RuntimeError):
    """Raised when a frozen source, profile, peer, or output invariant changes."""


@dataclass(frozen=True)
class PeerBenchmark:
    """Dense exact-date raw amount sums and complete-profile counts."""

    dates: pd.DatetimeIndex
    amount_sums: np.ndarray
    valid_counts: np.ndarray
    date_to_index: dict[pd.Timestamp, int]
    frame_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign151FeatureError(f"{label} fingerprint changed: {path}")


def _resolve_repository_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def load_builder_protocol(
    path: Path = DEFAULT_BUILDER_PROTOCOL,
) -> dict[str, Any]:
    """Load the exact value-free source-bound builder preregistration."""

    target = path.expanduser().resolve()
    if target != DEFAULT_BUILDER_PROTOCOL.resolve():
        raise Campaign151FeatureError("Campaign151 builder protocol path changed")
    _require_file(target, BUILDER_PROTOCOL_SHA256, "Campaign151 builder protocol")
    spec = json.loads(target.read_text(encoding="utf-8"))
    for binding in (spec.get("authoritative_inputs") or {}).values():
        bound = _resolve_repository_path(str(binding.get("path", "")))
        _require_file(bound, str(binding.get("sha256", "")), "authoritative input")
    source = spec.get("source_contract") or {}
    extraction = spec.get("exact_profile_extraction") or {}
    first = spec.get("first_pass_peer_accumulator") or {}
    second = spec.get("second_pass_leave_one_out_snapshot") or {}
    output = spec.get("output_contract") or {}
    authorization = spec.get("build_authorization") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign151_source_bound_builder_preregistration"
        and spec.get("status")
        == "frozen_before_campaign151_historical_minute_or_peer_benchmark_values"
        and source.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and source.get("joint_clean_manifest_sha256") == JOINT_MANIFEST_SHA256
        and source.get("joint_clean_dataset_sha256") == JOINT_DATASET_SHA256
        and source.get("calendar_sha256") == CALENDAR_SHA256
        and source.get("expected_raw_partition_count") == EXPECTED_PARTITIONS
        and source.get("expected_joint_partition_count") == EXPECTED_PARTITIONS
        and source.get("expected_joint_rows") == EXPECTED_ROWS
        and source.get("expected_symbol_count") == EXPECTED_SYMBOLS
        and tuple(source.get("raw_projection") or ()) == RAW_COLUMNS
        and tuple(source.get("joint_projection") or ()) == JOINT_COLUMNS
        and source.get("provider_request_allowed") is False
        and source.get("credential_allowed") is False
        and extraction.get("raw_stock_day_identity_rows") == 241
        and extraction.get("selected_amount_positions") == PROFILE_POSITIONS
        and extraction.get("standalone_09_30_excluded") is True
        and extraction.get("positive_own_total_required_for_peer_membership") is False
        and extraction.get(
            "all_zero_complete_profile_is_a_valid_zero_peer_contribution"
        )
        is True
        and first.get("no_candidate_comparator_price_or_return_value") is True
        and second.get("peer_count")
        == "The same scalar leave-one-out complete-profile count applies to all 240 positions and must be at least 50."
        and second.get("factor_callable")
        == "scripts.a_share_three_day_walkforward_campaign151_formula::compute_relative_amount_share_clock_center"
        and tuple(second.get("output_columns") or ()) == OUTPUT_COLUMNS
        and output.get("output_run_id") == OUTPUT_RUN_ID
        and output.get("published_root_never_overwritten") is True
        and output.get("minimum_free_bytes_before_build") == MINIMUM_FREE_BYTES
        and authorization.get(
            "implementation_and_tests_must_be_fingerprint_frozen_first"
        )
        is True
        and authorization.get(
            "separate_zero_value_plan_runner_must_bind_this_record_code_tests_and_freeze"
        )
        is True
        and boundary.get("historical_minute_source_rows_or_values_read") is False
        and boundary.get("peer_benchmark_values_read") is False
        and boundary.get("candidate_or_comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign151FeatureError("Campaign151 builder protocol semantics changed")
    _require_file(
        Path(source["raw_manifest_path"]), RAW_MANIFEST_SHA256, "raw manifest"
    )
    _require_file(
        Path(source["joint_clean_manifest_path"]),
        JOINT_MANIFEST_SHA256,
        "joint-clean manifest",
    )
    _require_file(
        _resolve_repository_path(source["calendar_path"]), CALENDAR_SHA256, "calendar"
    )
    _require_file(
        formula.__file__ and Path(formula.__file__),
        FORMULA_MODULE_SHA256,
        "formula module",
    )
    if formula.PROTOCOL_SHA256 != FORMULA_PROTOCOL_SHA256:
        raise Campaign151FeatureError("Campaign151 formula protocol binding changed")
    formula.load_protocol()
    return spec


def _normalized_base(base: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if tuple(base.columns) != JOINT_COLUMNS:
        raise Campaign151FeatureError(
            f"unexpected joint-clean columns for {symbol}: {tuple(base.columns)}"
        )
    work = base.copy()
    work["trade_date"] = pd.to_datetime(
        work["trade_date"], errors="coerce"
    ).dt.normalize()
    work["symbol"] = work["symbol"].astype(str).str.upper()
    if work.empty:
        return work.reset_index(drop=True)
    normalized_symbol = symbol.upper()
    if (
        work["trade_date"].isna().any()
        or set(work["symbol"].unique()) != {normalized_symbol}
        or work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise Campaign151FeatureError(
            f"joint-clean key identity changed for {normalized_symbol}"
        )
    return work.sort_values("trade_date", kind="stable").reset_index(drop=True)


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


def extract_partition_amount_profiles(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, dict[str, int]]:
    """Extract exact raw 240-position amount profiles for one symbol/year."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign151FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work = _normalized_base(base, symbol)
    if base_work.empty:
        return (
            base_work,
            np.empty((0, PROFILE_POSITIONS), dtype=np.float64),
            np.empty(0, dtype=bool),
            {
                "base_rows": 0,
                "invalid_required_amount_rows": 0,
                "complete_profile_rows": 0,
            },
        )
    normalized_symbol = symbol.upper()
    if raw.empty:
        raise Campaign151FeatureError(
            f"raw source is empty for nonempty base partition {normalized_symbol}"
        )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {normalized_symbol}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign151FeatureError(
            f"raw identity or timestamp violation for {normalized_symbol}"
        )
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not counts.eq(241).all():
        raise Campaign151FeatureError(
            f"every source stock-day must retain 241 rows for {normalized_symbol}"
        )
    code_sets = work.groupby("trade_date", sort=True, observed=True)["minute_code"].agg(
        lambda values: frozenset(int(value) for value in values)
    )
    if not code_sets.eq(FULL_SOURCE_MINUTE_CODES).all():
        raise Campaign151FeatureError(
            f"source minute grid changed for {normalized_symbol}"
        )
    observed_dates = pd.Series(pd.Index(counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(observed_dates):
        raise Campaign151FeatureError(
            f"joint-clean dates do not match raw dates for {normalized_symbol}"
        )
    selected = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "amount"],
    ].copy()
    selected["minute_code"] = pd.Categorical(
        selected["minute_code"],
        categories=CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    selected = selected.sort_values(["trade_date", "minute_code"], kind="stable")
    amounts = (
        selected["amount"].to_numpy(dtype=np.float64).reshape(-1, PROFILE_POSITIONS)
    )
    complete = np.isfinite(amounts).all(axis=1) & (amounts >= 0.0).all(axis=1)
    amounts[~complete] = np.nan
    return (
        base_work,
        amounts,
        complete,
        {
            "base_rows": int(len(base_work)),
            "invalid_required_amount_rows": int((~complete).sum()),
            "complete_profile_rows": int(complete.sum()),
        },
    )


def accumulate_complete_profiles(
    amount_sums: np.ndarray,
    valid_counts: np.ndarray,
    date_indices: np.ndarray,
    amounts: np.ndarray,
    complete: np.ndarray,
) -> None:
    """Add a verified profile batch to an in-memory calendar accumulator."""

    if (
        amount_sums.ndim != 2
        or amount_sums.shape[1] != PROFILE_POSITIONS
        or valid_counts.shape != (amount_sums.shape[0],)
        or amounts.ndim != 2
        or amounts.shape[1] != PROFILE_POSITIONS
        or len(date_indices) != len(amounts)
        or complete.shape != (len(amounts),)
    ):
        raise Campaign151FeatureError("peer accumulator shapes changed")
    if complete.any():
        indices = date_indices[complete]
        if len(np.unique(indices)) != len(indices):
            raise Campaign151FeatureError("duplicate date in one symbol contribution")
        amount_sums[indices] += amounts[complete]
        valid_counts[indices] += 1


def _benchmark_arrays_for_dates(
    benchmark: PeerBenchmark,
    dates: Sequence[pd.Timestamp],
) -> tuple[np.ndarray, np.ndarray]:
    try:
        indices = np.fromiter(
            (
                benchmark.date_to_index[pd.Timestamp(value).normalize()]
                for value in dates
            ),
            dtype=np.int64,
            count=len(dates),
        )
    except KeyError as exc:
        raise Campaign151FeatureError(
            f"candidate date is absent from the peer benchmark: {exc}"
        ) from exc
    return benchmark.amount_sums[indices], benchmark.valid_counts[indices]


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    benchmark: PeerBenchmark,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Compute exact leave-one-out peer means and the frozen factor."""

    base_work, amounts, complete, source_quality = extract_partition_amount_profiles(
        raw, base, symbol=symbol
    )
    if base_work.empty:
        return empty_output_frame(), {
            **source_quality,
            "insufficient_leave_one_out_peer_rows": 0,
            "nonpositive_peer_clock_rows": 0,
            "nonpositive_relative_total_rows": 0,
            "invalid_score_rows": 0,
            "eligible_rows": 0,
        }
    sums, counts = _benchmark_arrays_for_dates(benchmark, base_work["trade_date"])
    own = np.where(complete[:, None], amounts, 0.0)
    peer_counts = counts.astype(np.int64) - complete.astype(np.int64)
    peer_sums = sums - own
    sufficient = peer_counts >= MINIMUM_LEAVE_ONE_OUT_PEERS
    peer_means = np.full_like(peer_sums, np.nan, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        np.divide(
            peer_sums,
            peer_counts[:, None],
            out=peer_means,
            where=peer_counts[:, None] > 0,
        )
    peer_positive = np.isfinite(peer_means).all(axis=1) & (peer_means > 0.0).all(axis=1)
    formula_own = np.where(complete[:, None], amounts, np.nan)
    values, formula_eligible, formula_quality = (
        formula.compute_relative_amount_share_clock_center(formula_own, peer_means)
    )
    eligible = complete & sufficient & peer_positive & formula_eligible
    values = np.where(eligible, values, np.nan)
    output = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol.upper(),
            "provider": "tushare",
            FACTOR_NAME: values,
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    return output, {
        **source_quality,
        "insufficient_leave_one_out_peer_rows": int((complete & ~sufficient).sum()),
        "nonpositive_peer_clock_rows": int(
            (complete & sufficient & ~peer_positive).sum()
        ),
        "nonpositive_relative_total_rows": int(
            formula_quality["nonpositive_relative_total_rows"]
        ),
        "invalid_score_rows": int(formula_quality["invalid_score_rows"]),
        "eligible_rows": int(eligible.sum()),
    }


def _calendar_dates() -> pd.DatetimeIndex:
    _require_file(CALENDAR_PATH, CALENDAR_SHA256, "frozen calendar")
    values = pd.to_datetime(
        pd.read_csv(CALENDAR_PATH, header=None, names=["trade_date"])["trade_date"],
        errors="coerce",
    )
    dates = pd.DatetimeIndex(
        values.loc[
            values.between(pd.Timestamp("2019-01-01"), pd.Timestamp("2025-12-31"))
        ]
    ).normalize()
    if dates.hasnans or dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise Campaign151FeatureError("frozen local calendar is invalid")
    return dates


def _validate_external_manifests(
    data_root: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, list[tuple[dict[str, Any], dict[str, Any]]]],
]:
    if data_root.expanduser().resolve() != DEFAULT_DATA_ROOT.resolve():
        raise Campaign151FeatureError("Campaign151 data root changed")
    _require_file(RAW_MANIFEST_PATH, RAW_MANIFEST_SHA256, "raw manifest")
    _require_file(JOINT_MANIFEST_PATH, JOINT_MANIFEST_SHA256, "joint manifest")
    raw = json.loads(RAW_MANIFEST_PATH.read_text(encoding="utf-8"))
    joint = json.loads(JOINT_MANIFEST_PATH.read_text(encoding="utf-8"))
    if not (
        raw.get("kind") == "a_share_rich_data_snapshot"
        and raw.get("run_id") == "tushare_stk_mins_1m_2019_2025_ea0cbb8f"
        and len(raw.get("files") or []) == EXPECTED_PARTITIONS
        and joint.get("kind") == "a_share_tushare_one_minute_sentiment_clean_snapshot"
        and joint.get("partitions") == EXPECTED_PARTITIONS
        and joint.get("rows") == EXPECTED_ROWS
        and joint.get("dataset_sha256") == JOINT_DATASET_SHA256
        and joint.get("source_manifest_sha256") == RAW_MANIFEST_SHA256
        and joint.get("forward_return_fields_read") is False
    ):
        raise Campaign151FeatureError("external source manifest semantics changed")
    raw_by_key = {
        (str(item["symbol"]), int(item["year"])): item
        for item in raw.get("files") or []
    }
    joint_by_key = {
        (str(item["symbol"]), int(item["year"])): item
        for item in joint.get("files") or []
    }
    if (
        len(raw_by_key) != EXPECTED_PARTITIONS
        or len(joint_by_key) != EXPECTED_PARTITIONS
        or set(raw_by_key) != set(joint_by_key)
    ):
        raise Campaign151FeatureError("raw and joint partition identities changed")
    by_symbol: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for key in sorted(joint_by_key):
        raw_record = raw_by_key[key]
        joint_record = joint_by_key[key]
        if (
            joint_record.get("source_byte_sha256") != raw_record.get("byte_sha256")
            or Path(str(joint_record.get("source_path"))).resolve()
            != Path(str(raw_record.get("path"))).resolve()
        ):
            raise Campaign151FeatureError(
                f"joint-clean raw binding changed for {key[0]}/{key[1]}"
            )
        by_symbol.setdefault(key[0], []).append((raw_record, joint_record))
    if len(by_symbol) != EXPECTED_SYMBOLS:
        raise Campaign151FeatureError("source symbol count changed")
    return raw, joint, by_symbol


def _read_verified_profiles(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, dict[str, int]]:
    raw_path = Path(str(raw_record["path"]))
    joint_path = Path(str(joint_record["path"]))
    if foundation.file_digest(raw_path) != raw_record.get("byte_sha256"):
        raise Campaign151FeatureError(f"raw partition changed: {raw_path}")
    if foundation.file_digest(joint_path) != joint_record.get("output_byte_sha256"):
        raise Campaign151FeatureError(f"joint partition changed: {joint_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    base = pd.read_parquet(joint_path, columns=list(JOINT_COLUMNS))
    return extract_partition_amount_profiles(
        raw, base, symbol=str(joint_record["symbol"])
    )


def _symbol_contribution(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> tuple[str, np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    symbol = str(pairs[0][1]["symbol"])
    date_parts: list[np.ndarray] = []
    amount_parts: list[np.ndarray] = []
    complete_parts: list[np.ndarray] = []
    quality: Counter[str] = Counter()
    for raw_record, joint_record in sorted(
        pairs, key=lambda pair: int(pair[1]["year"])
    ):
        base, amounts, complete, observed = _read_verified_profiles(
            raw_record, joint_record
        )
        date_parts.append(
            pd.to_datetime(base["trade_date"]).to_numpy(dtype="datetime64[ns]")
        )
        amount_parts.append(amounts)
        complete_parts.append(complete)
        quality.update(observed)
    dates = (
        np.concatenate(date_parts)
        if date_parts
        else np.empty(0, dtype="datetime64[ns]")
    )
    amounts = (
        np.concatenate(amount_parts, axis=0)
        if amount_parts
        else np.empty((0, PROFILE_POSITIONS), dtype=np.float64)
    )
    complete = (
        np.concatenate(complete_parts) if complete_parts else np.empty(0, dtype=bool)
    )
    if pd.Index(dates).duplicated().any():
        raise Campaign151FeatureError(f"duplicate contribution date for {symbol}")
    return symbol, dates, amounts, complete, dict(quality)


def _atomic_write_accumulator(
    path: Path,
    *,
    dates: pd.DatetimeIndex,
    amount_sums: np.ndarray,
    valid_counts: np.ndarray,
    processed_symbols: set[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.npz")
    np.savez_compressed(
        temporary,
        schema_version=np.array([1], dtype=np.int16),
        builder_protocol_sha256=np.array([BUILDER_PROTOCOL_SHA256]),
        raw_manifest_sha256=np.array([RAW_MANIFEST_SHA256]),
        joint_manifest_sha256=np.array([JOINT_MANIFEST_SHA256]),
        calendar_sha256=np.array([CALENDAR_SHA256]),
        dates=dates.to_numpy(dtype="datetime64[ns]"),
        amount_sums=amount_sums,
        valid_counts=valid_counts,
        processed_symbols=np.array(sorted(processed_symbols), dtype="U16"),
    )
    temporary.replace(path)


def _load_or_create_accumulator(
    path: Path,
    dates: pd.DatetimeIndex,
) -> tuple[np.ndarray, np.ndarray, set[str]]:
    expected_shape = (len(dates), PROFILE_POSITIONS)
    if not path.is_file():
        return (
            np.zeros(expected_shape, dtype=np.float64),
            np.zeros(len(dates), dtype=np.int32),
            set(),
        )
    try:
        with np.load(path, allow_pickle=False) as state:
            observed_dates = state["dates"].astype("datetime64[ns]")
            amount_sums = state["amount_sums"].astype(np.float64, copy=True)
            valid_counts = state["valid_counts"].astype(np.int32, copy=True)
            processed = {str(value) for value in state["processed_symbols"].tolist()}
            valid = (
                state["schema_version"].tolist() == [1]
                and state["builder_protocol_sha256"].tolist()
                == [BUILDER_PROTOCOL_SHA256]
                and state["raw_manifest_sha256"].tolist() == [RAW_MANIFEST_SHA256]
                and state["joint_manifest_sha256"].tolist() == [JOINT_MANIFEST_SHA256]
                and state["calendar_sha256"].tolist() == [CALENDAR_SHA256]
                and np.array_equal(
                    observed_dates, dates.to_numpy(dtype="datetime64[ns]")
                )
                and amount_sums.shape == expected_shape
                and valid_counts.shape == (len(dates),)
                and np.isfinite(amount_sums).all()
                and (amount_sums >= 0.0).all()
                and (valid_counts >= 0).all()
            )
    except (OSError, ValueError, KeyError) as exc:
        raise Campaign151FeatureError(
            f"peer accumulator is unreadable: {path}"
        ) from exc
    if not valid:
        raise Campaign151FeatureError(f"peer accumulator changed: {path}")
    return amount_sums, valid_counts, processed


def _build_peer_benchmark(
    *,
    by_symbol: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]],
    dates: pd.DatetimeIndex,
    partial_root: Path,
    final_root: Path,
    workers: int,
) -> tuple[PeerBenchmark, dict[str, Any]]:
    accumulator_path = partial_root / ".metadata/raw_amount_accumulator.npz"
    amount_sums, valid_counts, processed = _load_or_create_accumulator(
        accumulator_path, dates
    )
    if unexpected := processed - set(by_symbol):
        raise Campaign151FeatureError(
            f"peer accumulator contains unknown symbols: {sorted(unexpected)}"
        )
    date_to_index = {pd.Timestamp(value): index for index, value in enumerate(dates)}
    pending = [symbol for symbol in sorted(by_symbol) if symbol not in processed]
    quality: Counter[str] = Counter()
    batch_size = max(8, workers * 8)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for offset in range(0, len(pending), batch_size):
            batch = pending[offset : offset + batch_size]
            results = list(
                pool.map(_symbol_contribution, [by_symbol[symbol] for symbol in batch])
            )
            for symbol, observed_dates, amounts, complete, observed in results:
                try:
                    indices = np.fromiter(
                        (
                            date_to_index[pd.Timestamp(value).normalize()]
                            for value in observed_dates
                        ),
                        dtype=np.int64,
                        count=len(observed_dates),
                    )
                except KeyError as exc:
                    raise Campaign151FeatureError(
                        f"contribution date is outside frozen calendar: {exc}"
                    ) from exc
                accumulate_complete_profiles(
                    amount_sums, valid_counts, indices, amounts, complete
                )
                processed.add(symbol)
                quality.update(observed)
            del results
            gc.collect()
            _atomic_write_accumulator(
                accumulator_path,
                dates=dates,
                amount_sums=amount_sums,
                valid_counts=valid_counts,
                processed_symbols=processed,
            )
            print(
                f"Campaign151 peer progress symbols={len(processed):,}/{len(by_symbol):,}",
                flush=True,
            )
    if processed != set(by_symbol):
        raise Campaign151FeatureError("peer accumulator did not consume every symbol")
    active = valid_counts > 0
    if not active.any():
        raise Campaign151FeatureError("peer accumulator contains no active date")
    active_dates = dates[active]
    active_sums = amount_sums[active]
    active_counts = valid_counts[active]
    frame = pd.DataFrame(
        {
            "trade_date": np.repeat(active_dates.to_numpy(), PROFILE_POSITIONS),
            "profile_position": np.tile(
                np.arange(PROFILE_POSITIONS, dtype=np.int16), len(active_dates)
            ),
            "raw_amount_sum": active_sums.reshape(-1),
            "complete_profile_count": np.repeat(active_counts, PROFILE_POSITIONS),
        }
    ).loc[:, BENCHMARK_COLUMNS]
    benchmark_path = partial_root / BENCHMARK_FILENAME
    foundation.atomic_write_frame(frame, benchmark_path)
    frame_sha256 = foundation.frame_digest(frame)
    benchmark = PeerBenchmark(
        dates=active_dates,
        amount_sums=active_sums,
        valid_counts=active_counts,
        date_to_index={
            pd.Timestamp(value).normalize(): index
            for index, value in enumerate(active_dates)
        },
        frame_sha256=frame_sha256,
    )
    evidence = {
        "path": str(final_root / BENCHMARK_FILENAME),
        "rows": int(len(frame)),
        "trade_dates": int(len(active_dates)),
        "profile_positions_per_date": PROFILE_POSITIONS,
        "output_byte_sha256": foundation.file_digest(benchmark_path),
        "output_frame_sha256": frame_sha256,
        "complete_profile_count_minimum": int(active_counts.min()),
        "complete_profile_count_p05": float(np.quantile(active_counts, 0.05)),
        "complete_profile_count_median": float(np.median(active_counts)),
        "complete_profile_count_maximum": int(active_counts.max()),
        "processed_symbol_count": int(len(processed)),
        "fresh_pass_invalid_required_amount_rows": int(
            quality["invalid_required_amount_rows"]
        ),
        "source_fields_read": list(RAW_COLUMNS),
        "daily_price_fields_read": [],
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
    }
    return benchmark, evidence


def output_root(data_root: Path = DEFAULT_DATA_ROOT) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign151_feature_library"
        / OUTPUT_RUN_ID
    )


def partial_root(data_root: Path = DEFAULT_DATA_ROOT) -> Path:
    final = output_root(data_root)
    return final.parent / f".{OUTPUT_RUN_ID}.partial"


def _load_partition_checkpoint(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
    paths: Any,
    benchmark: PeerBenchmark,
) -> tuple[dict[str, Any], Counter[str]] | None:
    if not paths.partial_sidecar.exists():
        paths.partial_data.unlink(missing_ok=True)
        return None
    record = json.loads(paths.partial_sidecar.read_text(encoding="utf-8"))
    valid = (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign151_feature_partition"
        and record.get("builder_protocol_sha256") == BUILDER_PROTOCOL_SHA256
        and record.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and record.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
        and record.get("peer_benchmark_frame_sha256") == benchmark.frame_sha256
        and record.get("raw_source_byte_sha256") == raw_record.get("byte_sha256")
        and record.get("joint_base_byte_sha256")
        == joint_record.get("output_byte_sha256")
        and paths.partial_data.is_file()
        and foundation.file_digest(Path(raw_record["path"]))
        == raw_record.get("byte_sha256")
        and foundation.file_digest(Path(joint_record["path"]))
        == joint_record.get("output_byte_sha256")
        and foundation.file_digest(paths.partial_data)
        == record.get("output_byte_sha256")
    )
    if not valid:
        raise Campaign151FeatureError(
            f"completed Campaign151 checkpoint changed: {paths.partial_sidecar}"
        )
    output = pd.read_parquet(paths.partial_data)
    if len(output) != int(record.get("rows", -1)) or foundation.frame_digest(
        output
    ) != record.get("output_frame_sha256"):
        raise Campaign151FeatureError(
            f"completed Campaign151 frame changed: {paths.partial_data}"
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
    benchmark: PeerBenchmark,
    partial: Path,
    final: Path,
) -> tuple[dict[str, Any], Counter[str], bool]:
    paths = foundation.partition_paths(partial, final, joint_record)
    completed = _load_partition_checkpoint(raw_record, joint_record, paths, benchmark)
    if completed is not None:
        record, dates = completed
        return record, dates, True
    raw_path = Path(str(raw_record["path"]))
    joint_path = Path(str(joint_record["path"]))
    if foundation.file_digest(raw_path) != raw_record.get("byte_sha256"):
        raise Campaign151FeatureError(f"raw partition changed: {raw_path}")
    if foundation.file_digest(joint_path) != joint_record.get("output_byte_sha256"):
        raise Campaign151FeatureError(f"joint partition changed: {joint_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    base = pd.read_parquet(joint_path, columns=list(JOINT_COLUMNS))
    output, quality = compute_partition_frame(
        raw, base, benchmark, symbol=str(joint_record["symbol"])
    )
    foundation.atomic_write_frame(output, paths.partial_data)
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign151_feature_partition",
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "builder_protocol_sha256": BUILDER_PROTOCOL_SHA256,
        "formula_module_sha256": FORMULA_MODULE_SHA256,
        "raw_manifest_sha256": RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
        "peer_benchmark_frame_sha256": benchmark.frame_sha256,
        "output_run_id": OUTPUT_RUN_ID,
        "symbol": str(joint_record["symbol"]),
        "code": str(joint_record["code"]),
        "year": int(joint_record["year"]),
        "raw_source_path": str(raw_path),
        "raw_source_rows": int(raw_record["rows"]),
        "raw_source_byte_sha256": str(raw_record["byte_sha256"]),
        "joint_base_path": str(joint_path),
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
        "minute_amount_fields_read": ["amount"],
        "minute_price_or_volume_fields_read": [],
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
    benchmark: PeerBenchmark,
    partial: Path,
    final: Path,
) -> tuple[list[dict[str, Any]], Counter[str], int]:
    records: list[dict[str, Any]] = []
    dates: Counter[str] = Counter()
    resumed = 0
    for raw_record, joint_record in sorted(
        pairs, key=lambda pair: int(pair[1]["year"])
    ):
        record, observed, was_resumed = _process_partition(
            raw_record,
            joint_record,
            benchmark=benchmark,
            partial=partial,
            final=final,
        )
        records.append(record)
        dates.update(observed)
        resumed += int(was_resumed)
    return records, dates, resumed


def _aggregate_quality(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    total: Counter[str] = Counter()
    for record in records:
        total.update({key: int(value) for key, value in record["quality"].items()})
    return dict(total)


def build_snapshot(
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    workers: int,
    confirm_build: bool = False,
) -> Path:
    """Build once after a separate frozen plan has authorized the exact code."""

    if confirm_build is not True:
        raise Campaign151FeatureError("confirmed Campaign151 build flag is required")
    if workers < 1 or workers > 8:
        raise Campaign151FeatureError("workers must be between 1 and 8")
    load_builder_protocol()
    data_root = data_root.expanduser().resolve()
    final = output_root(data_root)
    partial = partial_root(data_root)
    if final.exists():
        raise Campaign151FeatureError(
            f"Campaign151 final root already exists and is never overwritten: {final}"
        )
    if shutil.disk_usage(data_root).free < MINIMUM_FREE_BYTES:
        raise Campaign151FeatureError("Campaign151 data root has less than 10 GiB free")
    _raw, _joint, by_symbol = _validate_external_manifests(data_root)
    lock_path = data_root / ".a_share_three_day_walkforward_campaign151.lock"
    with foundation.ProcessLock(lock_path):
        if final.exists():
            raise Campaign151FeatureError("Campaign151 final root appeared under lock")
        partial.mkdir(parents=True, exist_ok=True)
        benchmark, benchmark_evidence = _build_peer_benchmark(
            by_symbol=by_symbol,
            dates=_calendar_dates(),
            partial_root=partial,
            final_root=final,
            workers=workers,
        )
        all_records: list[dict[str, Any]] = []
        eligible_dates: Counter[str] = Counter()
        resumed = 0
        completed_symbols = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _process_symbol,
                    pairs,
                    benchmark=benchmark,
                    partial=partial,
                    final=final,
                ): symbol
                for symbol, pairs in sorted(by_symbol.items())
            }
            try:
                for future in concurrent.futures.as_completed(futures):
                    futures.pop(future)
                    records, observed, resumed_count = future.result()
                    all_records.extend(records)
                    eligible_dates.update(observed)
                    resumed += resumed_count
                    completed_symbols += 1
                    if completed_symbols % 25 == 0 or completed_symbols == len(
                        by_symbol
                    ):
                        print(
                            f"Campaign151 snapshot progress symbols={completed_symbols:,}/"
                            f"{len(by_symbol):,} partitions={len(all_records):,}/"
                            f"{EXPECTED_PARTITIONS:,}",
                            flush=True,
                        )
            except BaseException:
                for future in futures:
                    future.cancel()
                raise
        if len(all_records) != EXPECTED_PARTITIONS:
            raise Campaign151FeatureError("not every source partition produced output")
        _require_file(RAW_MANIFEST_PATH, RAW_MANIFEST_SHA256, "raw manifest")
        _require_file(JOINT_MANIFEST_PATH, JOINT_MANIFEST_SHA256, "joint manifest")
        all_records.sort(key=lambda item: (str(item["symbol"]), int(item["year"])))
        quality = _aggregate_quality(all_records)
        if int(quality.get("base_rows", -1)) != EXPECTED_ROWS:
            raise Campaign151FeatureError("Campaign151 output row count changed")
        dataset_payload = "\n".join(
            [
                f"benchmark|{benchmark_evidence['output_byte_sha256']}",
                *[
                    f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
                    for item in all_records
                ],
            ]
        ).encode("utf-8")
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign151_feature_snapshot",
            "status": "candidate_feature_complete_pending_coverage_and_ordered_uniqueness",
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "output_run_id": OUTPUT_RUN_ID,
            "builder_protocol_path": str(DEFAULT_BUILDER_PROTOCOL),
            "builder_protocol_sha256": BUILDER_PROTOCOL_SHA256,
            "formula_module_sha256": FORMULA_MODULE_SHA256,
            "raw_manifest_path": str(RAW_MANIFEST_PATH),
            "raw_manifest_sha256": RAW_MANIFEST_SHA256,
            "joint_manifest_path": str(JOINT_MANIFEST_PATH),
            "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
            "joint_dataset_sha256": JOINT_DATASET_SHA256,
            "calendar_path": str(CALENDAR_PATH),
            "calendar_sha256": CALENDAR_SHA256,
            "dataset_sha256": hashlib.sha256(dataset_payload).hexdigest(),
            "factor_name": FACTOR_NAME,
            "factor_direction": FACTOR_DIRECTION,
            "factor_formula": "sum_i((a_i/b_i)/sum_j(a_j/b_j))*(i/239)",
            "peer_benchmark": benchmark_evidence,
            "files": all_records,
            "partitions": len(all_records),
            "rows": int(quality["base_rows"]),
            "eligible_rows": int(quality.get("eligible_rows", 0)),
            "quality": quality,
            "eligible_names_by_date": dict(sorted(eligible_dates.items())),
            "source_fields_read": list(RAW_COLUMNS),
            "standalone_09_30_excluded": True,
            "complete_profile_all_zero_peer_contribution_allowed": True,
            "leave_one_out_raw_amount_peer_mean": True,
            "minimum_leave_one_out_peers": MINIMUM_LEAVE_ONE_OUT_PEERS,
            "daily_price_fields_read": [],
            "comparison_factor_values_read": False,
            "forward_return_fields_read": False,
            "training_or_model_fitting_performed": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
            "current_scoring_selection_sizing_positions_or_orders_performed": False,
            "promotion_allowed": False,
            "resumed_partitions": resumed,
        }
        foundation.atomic_write_json(manifest, partial / "snapshot_manifest.json")
        (partial / ".metadata/raw_amount_accumulator.npz").unlink(missing_ok=True)
        final.parent.mkdir(parents=True, exist_ok=True)
        partial.replace(final)
        return final / "snapshot_manifest.json"


__all__ = [
    "BENCHMARK_COLUMNS",
    "BENCHMARK_FILENAME",
    "BUILDER_PROTOCOL_SHA256",
    "CONTINUOUS_MINUTE_CODES",
    "DEFAULT_BUILDER_PROTOCOL",
    "DEFAULT_DATA_ROOT",
    "EXPECTED_PARTITIONS",
    "EXPECTED_ROWS",
    "EXPECTED_SYMBOLS",
    "FACTOR_NAME",
    "FULL_SOURCE_MINUTE_CODES",
    "JOINT_COLUMNS",
    "MINIMUM_LEAVE_ONE_OUT_PEERS",
    "OUTPUT_COLUMNS",
    "OUTPUT_RUN_ID",
    "PROFILE_POSITIONS",
    "RAW_COLUMNS",
    "Campaign151FeatureError",
    "PeerBenchmark",
    "accumulate_complete_profiles",
    "build_snapshot",
    "compute_partition_frame",
    "empty_output_frame",
    "extract_partition_amount_profiles",
    "load_builder_protocol",
    "output_root",
    "partial_root",
]
