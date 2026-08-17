#!/usr/bin/env python3
"""Collect and freeze one prospective candidate-49 signal session.

This module is deliberately separate from the historical candidate builder.
It cannot backfill a pre-registration session, does not read a forward return,
and does not settle an execution.  A successful run performs only this chain:

accepted local daily context -> immutable Tushare 1-minute source snapshot ->
immutable factor snapshot -> append-only close-known signal ledger entry.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import shutil
import stat
import sys
import threading
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_rich_data as rich  # noqa: E402
import a_share_tushare_intraday_cumulative_vwap_crossing_rate as candidate  # noqa: E402
from _a_share_runtime import resolve_data_root  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_DATA_ROOT = resolve_data_root(REPO_ROOT)
DEFAULT_FUNDAMENTALS = (
    ACTIVE_DATA_ROOT
    / "raw"
    / "a_share"
    / "fundamentals"
    / "quarterly_quality_future.parquet"
)
DEFAULT_FUNDAMENTALS_MANIFEST = (
    ACTIVE_DATA_ROOT / "metadata" / "quarterly_quality_future_manifest.json"
)
DEFAULT_DAILY_RAW_ROOT = ACTIVE_DATA_ROOT / "raw" / "a_share" / "daily"
HISTORICAL_FUNDAMENTALS = (
    REPO_ROOT / "data" / "raw" / "a_share" / "fundamentals" / "quarterly_quality.parquet"
)
HISTORICAL_FUNDAMENTALS_MANIFEST = (
    REPO_ROOT / "data" / "metadata" / "quarterly_quality_manifest.json"
)
MINIMUM_SIGNAL_NAMES = 50
MINIMUM_LISTING_SESSIONS = 20
MAXIMUM_QUALITY_AGE_DAYS = 550
RAW_SNAPSHOT_KIND = "a_share_candidate49_future_raw_minute_snapshot"
RAW_PARTITION_KIND = "a_share_candidate49_future_raw_minute_partition"
RAW_CHECKPOINT_KIND = "a_share_candidate49_future_raw_minute_checkpoint"
FACTOR_SNAPSHOT_KIND = "a_share_candidate49_future_factor_snapshot"
SOURCE_COLUMNS = (
    "datetime",
    "symbol",
    "source_symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "provider",
)
TUSHARE_SOURCE_FIELDS = (
    "ts_code",
    "trade_time",
    "open",
    "high",
    "low",
    "close",
    "vol",
    "amount",
)
FUTURE_DAILY_RECONCILIATION_FIELDS = (
    "raw_close",
    "raw_volume",
    "amount",
    "price_basis",
)
FUTURE_QUALITY_COLUMNS = (
    "instrument",
    "report_date",
    "announcement_date",
    "roe",
    "net_profit",
    "revenue_yoy",
    "profit_yoy",
)
FACTOR_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    candidate.FACTOR_NAME,
    f"{candidate.FACTOR_NAME}_formula_eligible",
    "source_exact_241_grid",
    "source_close_volume_amount_reconciled",
    "listing_age_sessions",
    "listing_seasoning_eligible",
    "quality_effective_date",
    "quality_age_days",
    "roe",
    "net_profit",
    "revenue_yoy",
    "profit_yoy",
    "fundamental_quality_eligible",
    "quality_listing_eligible",
    f"{candidate.FACTOR_NAME}_eligible",
    "ineligibility_reasons",
)
FetchFunction = Callable[[str, dt.date, dt.date, str], pd.DataFrame]
ProviderCheck = Callable[[], None]
ClockFunction = Callable[[], dt.datetime]
BoundaryCheck = Callable[[], None]


class Candidate49FutureObservationError(RuntimeError):
    """Raised when the frozen prospective observation contract is violated."""


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _active_root_binding(
    *,
    provider_uri: Path,
    daily_raw_root: Path,
) -> dict[str, str]:
    provider_uri = provider_uri.expanduser().resolve()
    daily_raw_root = daily_raw_root.expanduser().resolve()
    if (
        provider_uri.name != "cn_a_share"
        or provider_uri.parent.name != "qlib"
    ):
        raise Candidate49FutureObservationError(
            "provider_uri_not_under_active_root_qlib_cn_a_share"
        )
    active_root = provider_uri.parent.parent.resolve()
    expected_daily_raw_root_path = (
        active_root / "raw" / "a_share" / "daily"
    )
    if expected_daily_raw_root_path.is_symlink():
        raise Candidate49FutureObservationError(
            "candidate49_daily_raw_root_symlink_forbidden"
        )
    expected_daily_raw_root = expected_daily_raw_root_path.resolve()
    if daily_raw_root != expected_daily_raw_root:
        raise Candidate49FutureObservationError(
            "daily_raw_root_not_bound_to_accepted_provider_root"
        )
    return {
        "active_root": str(active_root),
        "provider_uri": str(provider_uri),
        "daily_raw_root": str(daily_raw_root),
        "daily_file_layout": "lowercase_symbol_parquet",
    }


def _canonical_digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dataset_digest(records: list[dict[str, Any]]) -> str:
    return _canonical_digest(
        [
            {
                "symbol": record["symbol"],
                "rows": record["rows"],
                "frame_sha256": record["frame_sha256"],
            }
            for record in sorted(records, key=lambda item: str(item["symbol"]))
        ]
    )


def _session_roots(
    data_root: Path,
    session_date: dt.date,
) -> tuple[Path, Path, Path, Path]:
    registration = candidate.load_future_registration()
    storage = registration["storage"]
    raw_final = (
        data_root
        / str(storage["future_raw_root_below_data_root"])
        / session_date.isoformat()
    ).resolve()
    factor_final = (
        data_root
        / str(storage["future_factor_root_below_data_root"])
        / session_date.isoformat()
    ).resolve()
    raw_partial = raw_final.parent / f".{raw_final.name}.partial"
    factor_partial = factor_final.parent / f".{factor_final.name}.partial"
    return raw_final, raw_partial, factor_final, factor_partial


def _raw_partition_paths(root: Path, symbol: str) -> tuple[Path, Path]:
    stem = symbol.lower()
    return (
        root / "partitions" / f"{stem}.parquet",
        root / ".metadata" / "partitions" / f"{stem}.json",
    )


def _relative_raw_partition_paths(symbol: str) -> tuple[str, str]:
    stem = symbol.lower()
    return (
        f"partitions/{stem}.parquet",
        f".metadata/partitions/{stem}.json",
    )


def _read_calendar(path: Path) -> pd.DatetimeIndex:
    if not path.is_file():
        raise Candidate49FutureObservationError(
            f"accepted local calendar does not exist: {path}"
        )
    values = pd.to_datetime(
        [value for value in path.read_text(encoding="utf-8").splitlines() if value],
        errors="coerce",
    )
    if pd.isna(values).any():
        raise Candidate49FutureObservationError("accepted local calendar is invalid")
    calendar = pd.DatetimeIndex(values).normalize().unique().sort_values()
    if calendar.empty:
        raise Candidate49FutureObservationError("accepted local calendar is empty")
    return calendar


def _active_interval_rows(
    instrument_path: Path,
    session_date: dt.date,
) -> pd.DataFrame:
    if not instrument_path.is_file():
        raise Candidate49FutureObservationError(
            f"accepted buyable universe does not exist: {instrument_path}"
        )
    rows = pd.read_csv(
        instrument_path,
        sep="\t",
        header=None,
        names=["symbol", "active_start", "active_end"],
        dtype={"symbol": "string"},
    )
    rows["symbol"] = rows["symbol"].astype(str).str.upper()
    rows["active_start"] = pd.to_datetime(
        rows["active_start"], errors="coerce"
    ).dt.normalize()
    rows["active_end"] = pd.to_datetime(
        rows["active_end"], errors="coerce"
    ).dt.normalize()
    if (
        rows.empty
        or rows.isna().any().any()
        or rows["active_start"].gt(rows["active_end"]).any()
    ):
        raise Candidate49FutureObservationError(
            "accepted buyable-universe intervals are invalid"
        )
    session = pd.Timestamp(session_date)
    active = rows.loc[
        rows["active_start"].le(session) & rows["active_end"].ge(session)
    ].copy()
    active = active.sort_values("symbol", kind="stable").reset_index(drop=True)
    if active["symbol"].duplicated().any():
        raise Candidate49FutureObservationError(
            "accepted buyable universe has duplicate active symbols"
        )
    return active


def _daily_source_file_identity(
    path: Path,
    *,
    daily_raw_root: Path,
) -> dict[str, Any] | None:
    daily_raw_root = daily_raw_root.expanduser().resolve()
    if path.is_symlink():
        raise Candidate49FutureObservationError(
            f"candidate49_daily_source_file_symlink_forbidden:{path}"
        )
    try:
        observed = os.lstat(path)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(observed.st_mode):
        raise Candidate49FutureObservationError(
            f"candidate49_daily_source_file_not_regular:{path}"
        )
    if observed.st_nlink != 1:
        raise Candidate49FutureObservationError(
            f"candidate49_daily_source_file_hardlink_forbidden:{path}"
        )
    resolved = path.resolve(strict=True)
    if resolved.parent != daily_raw_root:
        raise Candidate49FutureObservationError(
            f"candidate49_daily_source_file_outside_accepted_root:{path}"
        )
    return {
        "resolved_path": str(resolved),
        "device": int(observed.st_dev),
        "inode": int(observed.st_ino),
        "link_count": int(observed.st_nlink),
        "size_bytes": int(observed.st_size),
        "modified_time_ns": int(observed.st_mtime_ns),
    }


def _validate_active_daily_source_file_identities(
    *,
    provider_uri: Path,
    daily_raw_root: Path,
    session_date: dt.date,
) -> dict[str, Any]:
    active = _active_interval_rows(
        provider_uri / "instruments" / "buyable_main_chinext.txt",
        session_date,
    )
    existing = 0
    missing = 0
    for symbol in active["symbol"].astype(str):
        path = daily_raw_root / f"{symbol.lower()}.parquet"
        identity = _daily_source_file_identity(
            path,
            daily_raw_root=daily_raw_root,
        )
        if identity is None:
            missing += 1
        else:
            existing += 1
    return {
        "active_symbols_checked": int(len(active)),
        "regular_private_daily_files": existing,
        "missing_daily_files": missing,
        "symlinks_allowed": False,
        "hardlinks_allowed": False,
        "provider_request_issued": False,
    }


def _copy_context_file(
    source: Path,
    destination: Path,
    *,
    snapshot_root: Path,
) -> dict[str, Any]:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise Candidate49FutureObservationError(
            f"prospective context file does not exist: {source}"
        )
    before = rich.file_digest(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    after = rich.file_digest(source)
    copied = rich.file_digest(destination)
    if before != after or copied != before:
        destination.unlink(missing_ok=True)
        raise Candidate49FutureObservationError(
            f"prospective context changed while being frozen: {source}"
        )
    return {
        "source_path": str(source),
        "path_below_snapshot_root": str(destination.relative_to(snapshot_root)),
        "sha256": copied,
    }


def _validate_future_quality_source(
    *,
    fundamentals_path: Path,
    fundamentals_manifest_path: Path,
    session_date: dt.date,
) -> None:
    fundamentals_path = fundamentals_path.expanduser().resolve()
    fundamentals_manifest_path = fundamentals_manifest_path.expanduser().resolve()
    if fundamentals_path == HISTORICAL_FUNDAMENTALS.resolve():
        raise Candidate49FutureObservationError(
            "candidate49 future quality must not reuse or overwrite the "
            "historically fingerprint-bound quarterly_quality.parquet"
        )
    if fundamentals_manifest_path == HISTORICAL_FUNDAMENTALS_MANIFEST.resolve():
        raise Candidate49FutureObservationError(
            "candidate49 future quality must not reuse or overwrite the "
            "historically fingerprint-bound quarterly_quality_manifest.json"
        )
    if fundamentals_path == fundamentals_manifest_path:
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality data and manifest paths "
            "must be distinct"
        )
    if not fundamentals_path.is_file() or not fundamentals_manifest_path.is_file():
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality snapshot and manifest must "
            "exist before any provider request"
        )
    manifest = json.loads(
        fundamentals_manifest_path.read_text(encoding="utf-8")
    )
    if not (
        manifest.get("status") == "completed"
        and manifest.get("report_frequency") == "quarterly"
        and manifest.get("sha256") == rich.file_digest(fundamentals_path)
        and int(manifest.get("rows_written", 0)) >= MINIMUM_SIGNAL_NAMES
    ):
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality manifest is invalid or "
            "does not bind its data"
        )
    manifest_output = str(manifest.get("output") or "")
    if (
        not manifest_output
        or Path(manifest_output).expanduser().resolve() != fundamentals_path
    ):
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality manifest output path does "
            "not bind the supplied data path"
        )
    report_dates = manifest.get("report_dates")
    if (
        not isinstance(report_dates, list)
        or not report_dates
        or report_dates != sorted(set(str(value) for value in report_dates))
    ):
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality manifest report dates are invalid"
        )
    parsed_report_dates = pd.to_datetime(report_dates, errors="coerce")
    if pd.isna(parsed_report_dates).any():
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality manifest has an invalid report date"
        )
    allowed_quarter_ends = {
        pd.Timestamp(value)
        for year in sorted(set(parsed_report_dates.year))
        for value in candidate.research.quarterly_report_dates(year, year)
    }
    if any(pd.Timestamp(value) not in allowed_quarter_ends for value in parsed_report_dates):
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality report dates must be "
            "calendar-quarter ends"
        )
    latest_completed = candidate.research.latest_completed_quarter_end(session_date)
    expected_through = latest_completed.date().isoformat()
    if (
        str(manifest.get("through_report_date") or "") != expected_through
        or str(manifest.get("latest_completed_quarter_end_at_sync") or "")
        != expected_through
        or report_dates[-1] != expected_through
    ):
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly quality must cover exactly through "
            f"the latest completed quarter {expected_through}"
        )
    retrieved_value = str((manifest.get("source") or {}).get("retrieved_at") or "")
    try:
        retrieved_at = dt.datetime.fromisoformat(
            retrieved_value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality manifest has no valid retrieval time"
        ) from exc
    if retrieved_at.tzinfo is None:
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality retrieval time needs a timezone"
        )
    local_retrieval = retrieved_at.astimezone(candidate.CHINA_TZ)
    if (
        local_retrieval.date() != session_date
        or local_retrieval.time().replace(tzinfo=None) < dt.time(16, 0)
    ):
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly quality must be refreshed after "
            "16:00 local time on the signal session"
        )
    data_sha256 = rich.file_digest(fundamentals_path)
    try:
        frame = pd.read_parquet(
            fundamentals_path,
            columns=list(FUTURE_QUALITY_COLUMNS),
        )
    except Exception as exc:
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality required-column projection "
            f"failed: {type(exc).__name__}"
        ) from exc
    if rich.file_digest(fundamentals_path) != data_sha256:
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality data changed while being read"
        )
    if tuple(frame.columns) != FUTURE_QUALITY_COLUMNS:
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality projection changed"
        )
    if len(frame) != int(manifest["rows_written"]):
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality row count differs from manifest"
        )
    frame["report_date"] = pd.to_datetime(
        frame["report_date"], errors="coerce"
    ).dt.normalize()
    frame["announcement_date"] = pd.to_datetime(
        frame["announcement_date"], errors="coerce"
    ).dt.normalize()
    if (
        frame[["instrument", "report_date", "announcement_date"]]
        .isna()
        .any()
        .any()
    ):
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality identities are invalid"
        )
    rows_by_report_date = manifest.get("rows_by_report_date")
    observed_counts = {
        value: int(frame["report_date"].eq(pd.Timestamp(value)).sum())
        for value in report_dates
    }
    if (
        not isinstance(rows_by_report_date, dict)
        or {
            str(key): int(value) for key, value in rows_by_report_date.items()
        }
        != observed_counts
        or not frame["report_date"].isin(parsed_report_dates).all()
    ):
        raise Candidate49FutureObservationError(
            "candidate49 future quarterly-quality report-date counts differ "
            "from the manifest"
        )


def _freeze_raw_context(
    *,
    partial_root: Path,
    provider_uri: Path,
    daily_raw_root: Path,
    session_date: dt.date,
    fundamentals_path: Path,
    fundamentals_manifest_path: Path,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DatetimeIndex]:
    active_root_binding = _active_root_binding(
        provider_uri=provider_uri,
        daily_raw_root=daily_raw_root,
    )
    context_root = partial_root / ".metadata" / "context"
    context_manifest_path = context_root / "context.json"
    source_paths = {
        "calendar": provider_uri / "calendars" / "day.txt",
        "buyable_universe": (
            provider_uri / "instruments" / "buyable_main_chinext.txt"
        ),
        "price_basis": provider_uri / "price_basis.json",
        "quarterly_quality": fundamentals_path,
        "quarterly_quality_manifest": fundamentals_manifest_path,
    }
    if context_manifest_path.is_file():
        context = rich.load_json_record(
            context_manifest_path,
            kind="a_share_candidate49_future_raw_context",
        )
        if (
            context.get("session_date") != session_date.isoformat()
            or context.get("registration_id") != candidate.FUTURE_REGISTRATION_ID
            or context.get("registration_sha256")
            != candidate.FUTURE_REGISTRATION_SHA256
            or set((context.get("files") or {})) != set(source_paths)
            or context.get("active_root_binding") != active_root_binding
        ):
            raise Candidate49FutureObservationError(
                "resumable raw context header or required files changed"
            )
        for name, record in (context.get("files") or {}).items():
            source = source_paths.get(name)
            snapshot = partial_root / str(
                record.get("path_below_snapshot_root") or ""
            )
            if (
                source is None
                or not source.is_file()
                or not snapshot.is_file()
                or str(source.expanduser().resolve()) != record.get("source_path")
                or rich.file_digest(source) != record.get("sha256")
                or rich.file_digest(snapshot) != record.get("sha256")
            ):
                raise Candidate49FutureObservationError(
                    "accepted local context changed after candidate49 provider "
                    f"requests began: {name}"
                )
    else:
        _validate_future_quality_source(
            fundamentals_path=fundamentals_path,
            fundamentals_manifest_path=fundamentals_manifest_path,
            session_date=session_date,
        )
        files = {
            name: _copy_context_file(
                source,
                context_root / source.name,
                snapshot_root=partial_root,
            )
            for name, source in source_paths.items()
        }
        context = {
            "schema_version": 1,
            "kind": "a_share_candidate49_future_raw_context",
            "status": "frozen_before_first_provider_request",
            "created_at": _utc_now(),
            "registration_id": candidate.FUTURE_REGISTRATION_ID,
            "registration_sha256": candidate.FUTURE_REGISTRATION_SHA256,
            "session_date": session_date.isoformat(),
            "files": files,
            "active_root_binding": active_root_binding,
            "provider_request_issued_before_snapshot": False,
            "historical_backfill_allowed": False,
            "forward_return_fields_read": False,
        }
        rich.atomic_write_json(context, context_manifest_path)
    calendar_snapshot = partial_root / str(
        context["files"]["calendar"]["path_below_snapshot_root"]
    )
    universe_snapshot = partial_root / str(
        context["files"]["buyable_universe"]["path_below_snapshot_root"]
    )
    calendar = _read_calendar(calendar_snapshot)
    active = _active_interval_rows(universe_snapshot, session_date)
    expected_symbols = candidate._active_buyable_symbols(
        universe_snapshot,
        session_date,
    )
    if active["symbol"].tolist() != expected_symbols:
        raise Candidate49FutureObservationError(
            "frozen active universe changed between parsers"
        )
    return context, active, calendar


def _canonicalize_source_response(
    raw: pd.DataFrame,
    *,
    symbol: str,
    session_date: dt.date,
) -> pd.DataFrame:
    """Preserve every returned row without making OHLC an eligibility field."""

    if raw is None:
        raw = pd.DataFrame()
    if raw.empty:
        return pd.DataFrame(
            {
                "datetime": pd.Series(dtype="datetime64[ns]"),
                "symbol": pd.Series(dtype="object"),
                "source_symbol": pd.Series(dtype="object"),
                "open": pd.Series(dtype="float64"),
                "high": pd.Series(dtype="float64"),
                "low": pd.Series(dtype="float64"),
                "close": pd.Series(dtype="float64"),
                "volume": pd.Series(dtype="float64"),
                "amount": pd.Series(dtype="float64"),
                "provider": pd.Series(dtype="object"),
            }
        ).loc[:, SOURCE_COLUMNS]
    if missing := sorted(set(TUSHARE_SOURCE_FIELDS) - set(raw.columns)):
        raise Candidate49FutureObservationError(
            "Tushare stk_mins response changed its frozen schema: "
            + ", ".join(missing)
        )
    expected_source_symbol = rich.vendor_symbol(symbol[2:], "tushare")
    if set(raw["ts_code"].astype(str)) != {expected_source_symbol}:
        raise Candidate49FutureObservationError(
            f"Tushare stk_mins returned an unexpected symbol for {symbol}"
        )
    result = pd.DataFrame(
        {
            "datetime": pd.to_datetime(raw["trade_time"], errors="coerce"),
            "symbol": symbol,
            "source_symbol": expected_source_symbol,
            "provider": "tushare",
        }
    )
    for target, source in (
        ("open", "open"),
        ("high", "high"),
        ("low", "low"),
        ("close", "close"),
        ("volume", "vol"),
        ("amount", "amount"),
    ):
        result[target] = pd.to_numeric(raw[source], errors="coerce")
    result = result.loc[:, SOURCE_COLUMNS]
    if result["datetime"].isna().any():
        raise Candidate49FutureObservationError(
            f"Tushare returned an invalid timestamp for {symbol}"
        )
    dates = result["datetime"].dt.date
    if not dates.eq(session_date).all():
        raise Candidate49FutureObservationError(
            f"Tushare returned a row outside {session_date.isoformat()} for {symbol}"
        )
    return result.sort_values("datetime", kind="stable").reset_index(drop=True)


def _daily_close_volume_amount_reconciliation(
    frame: pd.DataFrame,
    *,
    symbol: str,
    session_date: dt.date,
    daily_raw_root: Path,
) -> dict[str, Any]:
    path = daily_raw_root / f"{symbol.lower()}.parquet"
    daily_file_identity = _daily_source_file_identity(
        path,
        daily_raw_root=daily_raw_root,
    )
    if daily_file_identity is None:
        return {
            "status": "unavailable",
            "reason": "missing_local_daily",
            "daily_path": str(path),
            "fields_compared": list(FUTURE_DAILY_RECONCILIATION_FIELDS),
            "open_high_low_compared": False,
        }
    daily_sha256 = rich.file_digest(path)
    required_columns = ("date", *FUTURE_DAILY_RECONCILIATION_FIELDS)
    try:
        daily = pd.read_parquet(
            path,
            columns=list(required_columns),
            filters=[("date", "==", pd.Timestamp(session_date))],
        )
    except Exception as exc:
        return {
            "status": "unavailable",
            "reason": (
                "local_daily_required_projection_failed:"
                f"{type(exc).__name__}"
            ),
            "daily_path": str(path),
            "daily_sha256": daily_sha256,
            "daily_file_identity": daily_file_identity,
            "fields_compared": list(FUTURE_DAILY_RECONCILIATION_FIELDS),
            "open_high_low_compared": False,
        }
    if (
        _daily_source_file_identity(
            path,
            daily_raw_root=daily_raw_root,
        )
        != daily_file_identity
        or rich.file_digest(path) != daily_sha256
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 raw daily file changed while being read: {path}"
        )
    if tuple(daily.columns) != required_columns:
        raise Candidate49FutureObservationError(
            f"candidate49 raw daily projection changed: {path}"
        )
    daily["date"] = pd.to_datetime(daily["date"], errors="coerce").dt.normalize()
    selected = daily.loc[daily["date"].eq(pd.Timestamp(session_date))]
    if selected.empty:
        return {
            "status": "unavailable",
            "reason": "missing_local_daily_session",
            "daily_path": str(path),
            "daily_sha256": daily_sha256,
            "daily_file_identity": daily_file_identity,
            "fields_compared": list(FUTURE_DAILY_RECONCILIATION_FIELDS),
            "open_high_low_compared": False,
        }
    reference = selected.iloc[-1]
    if str(reference["price_basis"]) != candidate.research.REQUIRED_PRICE_BASIS:
        return {
            "status": "failed",
            "reason": "unaccepted_local_daily_price_basis",
            "daily_path": str(path),
            "daily_sha256": daily_sha256,
            "daily_file_identity": daily_file_identity,
            "observed_price_basis": str(reference["price_basis"]),
            "fields_compared": list(FUTURE_DAILY_RECONCILIATION_FIELDS),
            "open_high_low_compared": False,
        }
    close = pd.to_numeric(frame["close"], errors="coerce")
    volume = pd.to_numeric(frame["volume"], errors="coerce")
    amount = pd.to_numeric(frame["amount"], errors="coerce")
    reference_close = float(reference["raw_close"])
    reference_volume = float(reference["raw_volume"])
    reference_amount = float(reference["amount"])
    minute_close = float(close.iloc[-1]) if len(close) and pd.notna(close.iloc[-1]) else np.nan
    minute_volume = float(volume.sum(min_count=1))
    minute_amount = float(amount.sum(min_count=1))
    close_error = (
        abs(minute_close / reference_close - 1.0)
        if np.isfinite(minute_close) and np.isfinite(reference_close) and reference_close
        else None
    )
    volume_ratio = (
        minute_volume / reference_volume
        if np.isfinite(minute_volume)
        and np.isfinite(reference_volume)
        and reference_volume
        else None
    )
    amount_ratio = (
        minute_amount / reference_amount
        if np.isfinite(minute_amount)
        and np.isfinite(reference_amount)
        and reference_amount
        else None
    )
    passed = bool(
        close_error is not None
        and close_error <= 0.002
        and volume_ratio is not None
        and abs(volume_ratio - 100.0) <= 0.005
        and amount_ratio is not None
        and abs(amount_ratio - 1.0) <= 0.005
    )
    return {
        "status": "passed" if passed else "failed",
        "daily_path": str(path),
        "daily_sha256": daily_sha256,
        "daily_file_identity": daily_file_identity,
        "trade_date": session_date.isoformat(),
        "fields_compared": list(FUTURE_DAILY_RECONCILIATION_FIELDS),
        "open_high_low_compared": False,
        "minute_close": minute_close if np.isfinite(minute_close) else None,
        "daily_raw_close": reference_close if np.isfinite(reference_close) else None,
        "close_relative_error": close_error,
        "minute_volume": minute_volume if np.isfinite(minute_volume) else None,
        "daily_raw_volume_lots": (
            reference_volume if np.isfinite(reference_volume) else None
        ),
        "volume_ratio_to_daily_lots": volume_ratio,
        "required_volume_unit": "shares",
        "minute_amount": minute_amount if np.isfinite(minute_amount) else None,
        "daily_amount": reference_amount if np.isfinite(reference_amount) else None,
        "amount_ratio_to_daily": amount_ratio,
    }


def _source_quality(
    frame: pd.DataFrame,
    *,
    symbol: str,
    session_date: dt.date,
    daily_raw_root: Path,
) -> dict[str, Any]:
    timestamps = pd.to_datetime(frame["datetime"], errors="coerce")
    expected = rich.expected_tushare_one_minute_source_times()
    observed = tuple(timestamps.dt.time) if not timestamps.isna().any() else ()
    duplicate_rows = int(timestamps.duplicated(keep=False).sum())
    expected_set = set(expected)
    off_grid_rows = int((~timestamps.dt.time.isin(expected_set)).sum())
    exact = bool(
        len(frame) == len(expected)
        and observed == expected
        and duplicate_rows == 0
        and off_grid_rows == 0
    )
    reconciliation = _daily_close_volume_amount_reconciliation(
        frame,
        symbol=symbol,
        session_date=session_date,
        daily_raw_root=daily_raw_root,
    )
    return {
        "source_rows": int(len(frame)),
        "source_rows_preserved": True,
        "expected_source_rows": len(expected),
        "first_timestamp": (
            timestamps.iloc[0].isoformat() if len(timestamps) else None
        ),
        "last_timestamp": (
            timestamps.iloc[-1].isoformat() if len(timestamps) else None
        ),
        "duplicate_timestamp_rows": duplicate_rows,
        "off_grid_rows": off_grid_rows,
        "exact_241_source_grid": exact,
        "close_volume_amount_reconciliation": reconciliation,
        "open_high_low_used_for_eligibility": False,
        "factor_source_eligible": bool(
            exact and reconciliation.get("status") == "passed"
        ),
    }

def _store_raw_partition(
    *,
    symbol: str,
    session_date: dt.date,
    partial_root: Path,
    fetcher: FetchFunction | None,
    limiter: rich.TushareOneMinuteRateLimiter,
    stop_event: threading.Event,
    daily_raw_root: Path,
    boundary_check: BoundaryCheck,
) -> dict[str, Any]:
    boundary_check()
    data_path, sidecar_path = _raw_partition_paths(partial_root, symbol)
    if sidecar_path.exists():
        raise Candidate49FutureObservationError(
            f"completed candidate49 partition was resubmitted: {sidecar_path}"
        )
    data_path.unlink(missing_ok=True)
    if fetcher is None:
        class BoundaryCheckedLimiter:
            def wait(self) -> None:
                limiter.wait()
                boundary_check()

        raw = rich.fetch_tushare_one_minute_leaf(
            symbol[2:],
            session_date,
            session_date,
            limiter=BoundaryCheckedLimiter(),  # type: ignore[arg-type]
            stop_event=stop_event,
        )
    else:
        limiter.wait()
        boundary_check()
        raw = fetcher(symbol[2:], session_date, session_date, "1m")
    boundary_check()
    frame = _canonicalize_source_response(
        raw,
        symbol=symbol,
        session_date=session_date,
    )
    quality = _source_quality(
        frame,
        symbol=symbol,
        session_date=session_date,
        daily_raw_root=daily_raw_root,
    )
    rich.atomic_write_frame(frame, data_path)
    relative_data, relative_sidecar = _relative_raw_partition_paths(symbol)
    record = {
        "schema_version": 1,
        "kind": RAW_PARTITION_KIND,
        "registration_id": candidate.FUTURE_REGISTRATION_ID,
        "registration_sha256": candidate.FUTURE_REGISTRATION_SHA256,
        "completed_at": _utc_now(),
        "session_date": session_date.isoformat(),
        "symbol": symbol,
        "source_symbol": rich.vendor_symbol(symbol[2:], "tushare"),
        "provider_calls": 1,
        "path_below_session_root": relative_data,
        "sidecar_below_session_root": relative_sidecar,
        "rows": int(len(frame)),
        "byte_sha256": rich.file_digest(data_path),
        "frame_sha256": rich.frame_digest(frame),
        "quality": quality,
        "source_fields_returned": list(TUSHARE_SOURCE_FIELDS),
        "source_rows_preserved": True,
        "minute_factor_values_read": False,
        "historical_daily_price_fields_read": [],
        "future_daily_fields_read_only_for_source_reconciliation": list(
            FUTURE_DAILY_RECONCILIATION_FIELDS
        ),
        "forward_return_fields_read": False,
    }
    rich.atomic_write_json(record, sidecar_path)
    return record


def _load_completed_raw_partition(
    *,
    symbol: str,
    session_date: dt.date,
    root: Path,
) -> dict[str, Any] | None:
    data_path, sidecar_path = _raw_partition_paths(root, symbol)
    if not sidecar_path.is_file():
        data_path.unlink(missing_ok=True)
        return None
    record = rich.load_json_record(sidecar_path, kind=RAW_PARTITION_KIND)
    if not (
        record.get("registration_id") == candidate.FUTURE_REGISTRATION_ID
        and record.get("registration_sha256") == candidate.FUTURE_REGISTRATION_SHA256
        and record.get("session_date") == session_date.isoformat()
        and record.get("symbol") == symbol
        and record.get("provider_calls") == 1
        and record.get("source_rows_preserved") is True
        and record.get("minute_factor_values_read") is False
        and record.get("historical_daily_price_fields_read") == []
        and record.get(
            "future_daily_fields_read_only_for_source_reconciliation"
        )
        == list(FUTURE_DAILY_RECONCILIATION_FIELDS)
        and record.get("forward_return_fields_read") is False
        and data_path.is_file()
        and rich.file_digest(data_path) == record.get("byte_sha256")
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 raw partition checkpoint changed: {sidecar_path}"
        )
    frame = pd.read_parquet(data_path)
    if (
        tuple(frame.columns) != SOURCE_COLUMNS
        or len(frame) != int(record.get("rows", -1))
        or rich.frame_digest(frame) != record.get("frame_sha256")
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 raw partition frame changed: {data_path}"
        )
    return record


def _validate_raw_manifest(
    manifest_path: Path,
    *,
    session_date: dt.date,
) -> dict[str, Any]:
    root = manifest_path.parent
    manifest = rich.load_json_record(manifest_path, kind=RAW_SNAPSHOT_KIND)
    files = manifest.get("files")
    if not (
        manifest.get("status") == "atomically_published_immutable_future_raw_session"
        and manifest.get("registration_id") == candidate.FUTURE_REGISTRATION_ID
        and manifest.get("registration_sha256")
        == candidate.FUTURE_REGISTRATION_SHA256
        and manifest.get("session_date") == session_date.isoformat()
        and manifest.get("source_rows_preserved") is True
        and manifest.get("historical_backfill_allowed") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get(
            "future_daily_fields_read_only_for_source_reconciliation"
        )
        == list(FUTURE_DAILY_RECONCILIATION_FIELDS)
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("accepted_daily_source")
        in {"eastmoney", "baostock", "tushare"}
        and isinstance(files, list)
        and len(files) == int(manifest.get("active_buyable_symbols", -1))
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 raw snapshot header changed: {manifest_path}"
        )
    records: list[dict[str, Any]] = []
    context_path = root / ".metadata" / "context" / "context.json"
    if (
        not context_path.is_file()
        or rich.file_digest(context_path)
        != manifest.get("frozen_context_manifest_sha256")
        or rich.load_json_record(
            context_path,
            kind="a_share_candidate49_future_raw_context",
        )
        != manifest.get("frozen_context")
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 frozen raw context changed: {context_path}"
        )
    for name, record in manifest["frozen_context"]["files"].items():
        context_file = root / str(record.get("path_below_snapshot_root") or "")
        if (
            not context_file.is_file()
            or rich.file_digest(context_file) != record.get("sha256")
        ):
            raise Candidate49FutureObservationError(
                f"candidate49 frozen raw context file changed: {name}"
            )
    binding = manifest["frozen_context"].get("active_root_binding")
    price_basis_source = Path(
        str(
            manifest["frozen_context"]["files"]["price_basis"].get(
                "source_path"
            )
            or ""
        )
    ).parent
    if (
        not isinstance(binding, dict)
        or set(binding)
        != {
            "active_root",
            "provider_uri",
            "daily_raw_root",
            "daily_file_layout",
        }
        or binding.get("daily_file_layout") != "lowercase_symbol_parquet"
        or _active_root_binding(
            provider_uri=price_basis_source,
            daily_raw_root=Path(str(binding.get("daily_raw_root") or "")),
        )
        != binding
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 frozen active-root binding changed: {context_path}"
        )
    frozen_price_basis_path = root / str(
        manifest["frozen_context"]["files"]["price_basis"][
            "path_below_snapshot_root"
        ]
    )
    frozen_price_basis = json.loads(
        frozen_price_basis_path.read_text(encoding="utf-8")
    )
    if frozen_price_basis.get("daily_sources") != [
        manifest["accepted_daily_source"]
    ]:
        raise Candidate49FutureObservationError(
            "candidate49 frozen raw daily source changed"
        )
    for expected in files:
        symbol = str(expected.get("symbol") or "")
        observed = _load_completed_raw_partition(
            symbol=symbol,
            session_date=session_date,
            root=root,
        )
        if observed is None or observed != expected:
            raise Candidate49FutureObservationError(
                f"candidate49 raw snapshot partition record changed: {symbol}"
            )
        records.append(observed)
    if _dataset_digest(records) != manifest.get("dataset_sha256"):
        raise Candidate49FutureObservationError(
            f"candidate49 raw dataset fingerprint changed: {manifest_path}"
        )
    provider_calls = sum(int(record["provider_calls"]) for record in records)
    rows = sum(int(record["rows"]) for record in records)
    exact_count = sum(
        bool((record.get("quality") or {}).get("exact_241_source_grid"))
        for record in records
    )
    reconciled_count = sum(
        (record.get("quality") or {})
        .get("close_volume_amount_reconciliation", {})
        .get("status")
        == "passed"
        for record in records
    )
    source_eligible_count = sum(
        bool((record.get("quality") or {}).get("factor_source_eligible"))
        for record in records
    )
    resumed_partitions = manifest.get("resumed_partitions")
    invocation_calls = manifest.get("provider_calls_this_invocation")
    if not (
        manifest.get("provider_calls") == provider_calls
        and manifest.get("rows") == rows
        and manifest.get("exact_241_source_grid_symbols") == exact_count
        and manifest.get("close_volume_amount_reconciled_symbols")
        == reconciled_count
        and manifest.get("factor_source_eligible_symbols")
        == source_eligible_count
        and isinstance(resumed_partitions, int)
        and not isinstance(resumed_partitions, bool)
        and 0 <= resumed_partitions <= len(records)
        and isinstance(invocation_calls, int)
        and not isinstance(invocation_calls, bool)
        and invocation_calls == provider_calls - resumed_partitions
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 raw snapshot aggregate counters changed: {manifest_path}"
        )
    return manifest


def _publish_raw_snapshot(
    *,
    data_root: Path,
    provider_uri: Path,
    daily_raw_root: Path,
    fundamentals_path: Path,
    fundamentals_manifest_path: Path,
    session_date: dt.date,
    allow_large: bool,
    now: dt.datetime | None,
    token_configured: bool | None,
    signal_path: Path,
    execution_path: Path,
    fetcher: FetchFunction | None,
    provider_check: ProviderCheck | None,
    workers: int,
    request_interval_seconds: float,
    clock: ClockFunction | None,
) -> tuple[Path, dict[str, Any], int]:
    raw_final, raw_partial, _, _ = _session_roots(data_root, session_date)
    final_manifest_path = raw_final / "snapshot_manifest.json"
    if raw_final.exists():
        if not final_manifest_path.is_file():
            raise Candidate49FutureObservationError(
                f"published raw root has no manifest: {raw_final}"
            )
        return final_manifest_path, _validate_raw_manifest(
            final_manifest_path,
            session_date=session_date,
        ), 0
    _active_root_binding(
        provider_uri=provider_uri,
        daily_raw_root=daily_raw_root,
    )

    def require_same_signal_date() -> None:
        check_now = clock() if clock is not None else now
        _, timing_failures = candidate.future_session_time_boundary_failures(
            session_date=session_date,
            now=check_now,
        )
        if timing_failures:
            raise Candidate49FutureObservationError(
                "candidate49 future session stopped before provider request: "
                + ",".join(timing_failures)
            )

    preflight = candidate.future_session_preflight(
        session_date=session_date,
        data_root=data_root,
        provider_uri=provider_uri,
        now=now,
        token_configured=token_configured,
        signal_path=signal_path,
        execution_path=execution_path,
    )
    if not preflight["ready"]:
        raise Candidate49FutureObservationError(
            "candidate49 future session stopped before provider request: "
            + ",".join(preflight["failures"])
        )
    if not allow_large:
        raise Candidate49FutureObservationError(
            "full-buyable-universe candidate49 collection requires --allow-large"
        )
    require_same_signal_date()
    expected_daily_source = str(preflight["accepted_daily_sources"][0])
    raw_partial.mkdir(parents=True, exist_ok=True)
    context, active, calendar = _freeze_raw_context(
        partial_root=raw_partial,
        provider_uri=provider_uri,
        daily_raw_root=daily_raw_root,
        session_date=session_date,
        fundamentals_path=fundamentals_path,
        fundamentals_manifest_path=fundamentals_manifest_path,
    )
    frozen_price_basis_path = raw_partial / str(
        context["files"]["price_basis"]["path_below_snapshot_root"]
    )
    frozen_price_basis = json.loads(
        frozen_price_basis_path.read_text(encoding="utf-8")
    )
    daily_sources = frozen_price_basis.get("daily_sources")
    if daily_sources != [expected_daily_source]:
        raise Candidate49FutureObservationError(
            "candidate49 frozen price-basis daily source differs from preflight"
        )
    if pd.Timestamp(session_date) not in calendar:
        raise Candidate49FutureObservationError(
            "candidate49 session is absent from the frozen accepted calendar"
        )
    symbols = active["symbol"].astype(str).tolist()
    if len(symbols) < MINIMUM_SIGNAL_NAMES:
        raise Candidate49FutureObservationError(
            "candidate49 frozen active universe has fewer than fifty names"
        )
    completed: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        record = _load_completed_raw_partition(
            symbol=symbol,
            session_date=session_date,
            root=raw_partial,
        )
        if record is not None:
            completed[symbol] = record
    initially_completed = len(completed)
    pending = [symbol for symbol in symbols if symbol not in completed]
    checkpoint_path = raw_partial / ".metadata" / "checkpoint.json"
    checkpoint = {
        "schema_version": 1,
        "kind": RAW_CHECKPOINT_KIND,
        "status": "running",
        "updated_at": _utc_now(),
        "registration_id": candidate.FUTURE_REGISTRATION_ID,
        "registration_sha256": candidate.FUTURE_REGISTRATION_SHA256,
        "session_date": session_date.isoformat(),
        "expected_partitions": len(symbols),
        "completed_partitions": len(completed),
        "resumed_partitions": initially_completed,
        "provider_calls_this_invocation": 0,
        "source_rows_stored": int(
            sum(int(record["rows"]) for record in completed.values())
        ),
        "historical_backfill_allowed": False,
        "forward_return_fields_read": False,
    }
    rich.atomic_write_json(checkpoint, checkpoint_path)
    provider_calls_this_invocation = 0
    if pending:
        check = provider_check or (lambda: rich.require_provider("tushare"))
        check()
        limiter = rich.TushareOneMinuteRateLimiter(request_interval_seconds)
        stop_event = threading.Event()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
        futures: dict[concurrent.futures.Future[dict[str, Any]], str] = {}
        iterator = iter(pending)

        def submit_next() -> bool:
            try:
                symbol = next(iterator)
            except StopIteration:
                return False
            future = executor.submit(
                _store_raw_partition,
                symbol=symbol,
                session_date=session_date,
                partial_root=raw_partial,
                fetcher=fetcher,
                limiter=limiter,
                stop_event=stop_event,
                daily_raw_root=daily_raw_root,
                boundary_check=require_same_signal_date,
            )
            futures[future] = symbol
            return True

        for _ in range(min(len(pending), workers * 2)):
            submit_next()
        try:
            while futures:
                done, _ = concurrent.futures.wait(
                    futures,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                for future in done:
                    symbol = futures.pop(future)
                    record = future.result()
                    completed[symbol] = record
                    provider_calls_this_invocation += int(record["provider_calls"])
                    checkpoint.update(
                        {
                            "updated_at": _utc_now(),
                            "completed_partitions": len(completed),
                            "provider_calls_this_invocation": (
                                provider_calls_this_invocation
                            ),
                            "source_rows_stored": int(
                                sum(
                                    int(item["rows"])
                                    for item in completed.values()
                                )
                            ),
                        }
                    )
                    rich.atomic_write_json(checkpoint, checkpoint_path)
                    if len(completed) == 1 or len(completed) % 500 == 0:
                        print(
                            json.dumps(
                                {
                                    "candidate49_future_progress": {
                                        "completed_partitions": len(completed),
                                        "expected_partitions": len(symbols),
                                        "provider_calls_this_invocation": (
                                            provider_calls_this_invocation
                                        ),
                                    }
                                },
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                    submit_next()
        except Exception as exc:
            stop_event.set()
            for future in futures:
                future.cancel()
            executor.shutdown(wait=True, cancel_futures=True)
            checkpoint.update(
                {
                    "status": (
                        "interrupted_after_signal_date_preserved_not_resumable"
                        if (
                            "past_session_delayed_source_to_signal_backfill_forbidden"
                            in str(exc)
                        )
                        else "interrupted_resumable"
                    ),
                    "updated_at": _utc_now(),
                    "error_type": type(exc).__name__,
                    "error": rich.safe_exception_text(exc),
                }
            )
            rich.atomic_write_json(checkpoint, checkpoint_path)
            raise
        else:
            executor.shutdown(wait=True)
    if set(completed) != set(symbols):
        raise Candidate49FutureObservationError(
            "candidate49 raw collection ended without every active partition"
        )
    require_same_signal_date()
    records = [completed[symbol] for symbol in symbols]
    exact_count = sum(
        bool((record.get("quality") or {}).get("exact_241_source_grid"))
        for record in records
    )
    reconciled_count = sum(
        (record.get("quality") or {})
        .get("close_volume_amount_reconciliation", {})
        .get("status")
        == "passed"
        for record in records
    )
    source_eligible_count = sum(
        bool((record.get("quality") or {}).get("factor_source_eligible"))
        for record in records
    )
    checkpoint.update(
        {
            "status": "complete_pending_atomic_publish",
            "updated_at": _utc_now(),
            "completed_partitions": len(records),
        }
    )
    rich.atomic_write_json(checkpoint, checkpoint_path)
    manifest = {
        "schema_version": 1,
        "kind": RAW_SNAPSHOT_KIND,
        "status": "atomically_published_immutable_future_raw_session",
        "created_at": _utc_now(),
        "registration_id": candidate.FUTURE_REGISTRATION_ID,
        "registration_sha256": candidate.FUTURE_REGISTRATION_SHA256,
        "future_only_policy_sha256": candidate.POLICY_SHA256,
        "session_date": session_date.isoformat(),
        "provider": "tushare",
        "interface": "pro.stk_mins",
        "frequency_argument": "1min",
        "accepted_daily_source": expected_daily_source,
        "source_request_fields": list(TUSHARE_SOURCE_FIELDS),
        "maximum_calls_per_minute": rich.TUSHARE_ONE_MINUTE_MAX_CALLS_PER_MINUTE,
        "workers": workers,
        "transient_retries": rich.TUSHARE_ONE_MINUTE_PARTITION_RETRIES,
        "active_buyable_symbols": len(symbols),
        "provider_calls": int(
            sum(int(record["provider_calls"]) for record in records)
        ),
        "provider_calls_this_invocation": provider_calls_this_invocation,
        "resumed_partitions": initially_completed,
        "rows": int(sum(int(record["rows"]) for record in records)),
        "exact_241_source_grid_symbols": int(exact_count),
        "close_volume_amount_reconciled_symbols": int(reconciled_count),
        "factor_source_eligible_symbols": int(source_eligible_count),
        "dataset_sha256": _dataset_digest(records),
        "files": records,
        "frozen_context": context,
        "frozen_context_manifest_sha256": rich.file_digest(
            raw_partial / ".metadata" / "context" / "context.json"
        ),
        "source_rows_preserved": True,
        "missing_incomplete_or_suspended_stock_days_imputed": False,
        "open_high_low_used_for_candidate49_eligibility": False,
        "historical_daily_price_fields_read": [],
        "future_daily_fields_read_only_for_source_reconciliation": list(
            FUTURE_DAILY_RECONCILIATION_FIELDS
        ),
        "forward_return_fields_read": False,
        "signal_selection_or_execution_performed": False,
        "historical_backfill_allowed": False,
        "credentials_logged_or_stored": False,
    }
    rich.atomic_write_json(manifest, raw_partial / "snapshot_manifest.json")
    raw_partial.replace(raw_final)
    return (
        final_manifest_path,
        _validate_raw_manifest(final_manifest_path, session_date=session_date),
        provider_calls_this_invocation,
    )


def _freeze_factor_context(
    *,
    partial_root: Path,
    raw_root: Path,
    raw_context: dict[str, Any],
) -> dict[str, Any]:
    context_root = partial_root / "context"
    raw_files = raw_context["files"]
    fundamentals_path = raw_root / str(
        raw_files["quarterly_quality"]["path_below_snapshot_root"]
    )
    fundamentals_manifest_path = raw_root / str(
        raw_files["quarterly_quality_manifest"]["path_below_snapshot_root"]
    )
    records = {
        "quarterly_quality": _copy_context_file(
            fundamentals_path,
            context_root / "quarterly_quality.parquet",
            snapshot_root=partial_root,
        ),
        "quarterly_quality_manifest": _copy_context_file(
            fundamentals_manifest_path,
            context_root / "quarterly_quality_manifest.json",
            snapshot_root=partial_root,
        ),
    }
    quality_manifest = json.loads(
        (
            partial_root
            / records["quarterly_quality_manifest"]["path_below_snapshot_root"]
        ).read_text(encoding="utf-8")
    )
    if (
        quality_manifest.get("sha256")
        != records["quarterly_quality"]["sha256"]
    ):
        raise Candidate49FutureObservationError(
            "quarterly-quality data and its manifest fingerprint differ"
        )
    return records


def _quality_rows_for_session(
    *,
    active: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    session_date: dt.date,
    fundamentals_path: Path,
) -> pd.DataFrame:
    fundamentals_sha256 = rich.file_digest(fundamentals_path)
    try:
        fundamentals = pd.read_parquet(
            fundamentals_path,
            columns=list(FUTURE_QUALITY_COLUMNS),
            filters=[
                (
                    "announcement_date",
                    "<",
                    pd.Timestamp(session_date),
                )
            ],
        )
    except Exception as exc:
        raise Candidate49FutureObservationError(
            "candidate49 frozen quarterly-quality required-column/date "
            f"projection failed: {type(exc).__name__}"
        ) from exc
    if rich.file_digest(fundamentals_path) != fundamentals_sha256:
        raise Candidate49FutureObservationError(
            "candidate49 frozen quarterly-quality data changed while being read"
        )
    if tuple(fundamentals.columns) != FUTURE_QUALITY_COLUMNS:
        raise Candidate49FutureObservationError(
            "candidate49 frozen quarterly-quality projection changed"
        )
    fundamentals = fundamentals.copy()
    fundamentals["instrument"] = (
        fundamentals["instrument"].astype(str).str.upper()
    )
    for column in ("report_date", "announcement_date"):
        fundamentals[column] = pd.to_datetime(
            fundamentals[column], errors="coerce"
        ).dt.normalize()
    for column in ("roe", "net_profit", "revenue_yoy", "profit_yoy"):
        fundamentals[column] = pd.to_numeric(
            fundamentals[column], errors="coerce"
        )
    if (
        fundamentals[["instrument", "report_date", "announcement_date"]]
        .isna()
        .any()
        .any()
    ):
        raise Candidate49FutureObservationError(
            "quarterly-quality identities are invalid"
        )
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    announcement_values = fundamentals["announcement_date"].to_numpy(
        dtype="datetime64[ns]"
    )
    effective_positions = np.searchsorted(
        calendar_values,
        announcement_values,
        side="right",
    )
    effective = np.full(
        len(fundamentals),
        np.datetime64("NaT"),
        dtype="datetime64[ns]",
    )
    in_range = effective_positions < len(calendar_values)
    effective[in_range] = calendar_values[effective_positions[in_range]]
    fundamentals["quality_effective_date"] = pd.to_datetime(effective)
    fundamentals = (
        fundamentals.dropna(subset=["quality_effective_date"])
        .sort_values(
            [
                "instrument",
                "quality_effective_date",
                "report_date",
                "announcement_date",
            ],
            kind="stable",
        )
        .drop_duplicates(["instrument", "quality_effective_date"], keep="last")
    )
    state_columns = ["roe", "net_profit", "revenue_yoy", "profit_yoy"]
    fundamentals[state_columns] = fundamentals.groupby(
        "instrument", sort=False
    )[state_columns].ffill()
    session = pd.Timestamp(session_date)
    available = fundamentals.loc[
        fundamentals["quality_effective_date"].le(session)
    ]
    latest = (
        available.sort_values(
            [
                "instrument",
                "quality_effective_date",
                "report_date",
                "announcement_date",
            ],
            kind="stable",
        )
        .groupby("instrument", sort=False)
        .tail(1)
        .set_index("instrument")
    )
    session_position = int(
        np.searchsorted(calendar_values, np.datetime64(session), side="left")
    )
    rows: list[dict[str, Any]] = []
    for item in active.itertuples(index=False):
        symbol = str(item.symbol)
        start_position = int(
            np.searchsorted(
                calendar_values,
                np.datetime64(pd.Timestamp(item.active_start)),
                side="left",
            )
        )
        listing_age = session_position - start_position + 1
        listing_eligible = listing_age >= MINIMUM_LISTING_SESSIONS
        state = latest.loc[symbol] if symbol in latest.index else None
        effective_date = (
            pd.Timestamp(state["quality_effective_date"])
            if state is not None
            else pd.NaT
        )
        quality_age = (
            int((session - effective_date).days)
            if pd.notna(effective_date)
            else None
        )
        values = {
            column: (
                float(state[column])
                if state is not None and pd.notna(state[column])
                else np.nan
            )
            for column in state_columns
        }
        fundamental_eligible = bool(
            quality_age is not None
            and 0 <= quality_age <= MAXIMUM_QUALITY_AGE_DAYS
            and np.isfinite(values["roe"])
            and values["roe"] >= 5.0
            and np.isfinite(values["net_profit"])
            and values["net_profit"] > 0.0
            and np.isfinite(values["revenue_yoy"])
            and values["revenue_yoy"] > 0.0
            and np.isfinite(values["profit_yoy"])
            and values["profit_yoy"] > 0.0
        )
        rows.append(
            {
                "symbol": symbol,
                "listing_age_sessions": listing_age,
                "listing_seasoning_eligible": listing_eligible,
                "quality_effective_date": effective_date,
                "quality_age_days": quality_age,
                **values,
                "fundamental_quality_eligible": fundamental_eligible,
                "quality_listing_eligible": bool(
                    listing_eligible and fundamental_eligible
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("symbol", kind="stable").reset_index(
        drop=True
    )


def _factor_row(
    *,
    raw_root: Path,
    raw_record: dict[str, Any],
    session_date: dt.date,
    quality: dict[str, Any],
) -> dict[str, Any]:
    symbol = str(raw_record["symbol"])
    source_quality = raw_record["quality"]
    exact = bool(source_quality["exact_241_source_grid"])
    reconciled = bool(
        source_quality["close_volume_amount_reconciliation"]["status"] == "passed"
    )
    formula_value = np.nan
    formula_eligible = False
    if exact and reconciled:
        data_path = raw_root / str(raw_record["path_below_session_root"])
        source_sha256 = rich.file_digest(data_path)
        morning_start = pd.Timestamp.combine(session_date, dt.time(9, 31))
        morning_end = pd.Timestamp.combine(session_date, dt.time(11, 30))
        afternoon_start = pd.Timestamp.combine(session_date, dt.time(13, 1))
        afternoon_end = pd.Timestamp.combine(session_date, dt.time(15, 0))
        source_filters = [
            [
                ("datetime", ">=", morning_start),
                ("datetime", "<=", morning_end),
            ],
            [
                ("datetime", ">=", afternoon_start),
                ("datetime", "<=", afternoon_end),
            ],
        ]
        try:
            raw = pd.read_parquet(
                data_path,
                columns=list(candidate.RAW_COLUMNS),
                filters=source_filters,
            )
        except Exception as exc:
            raise Candidate49FutureObservationError(
                "candidate49 frozen minute required-column/session-grid "
                f"projection failed for {symbol}: {type(exc).__name__}"
            ) from exc
        if rich.file_digest(data_path) != source_sha256:
            raise Candidate49FutureObservationError(
                f"candidate49 frozen minute partition changed while being read: {symbol}"
            )
        if tuple(raw.columns) != candidate.RAW_COLUMNS:
            raise Candidate49FutureObservationError(
                f"candidate49 frozen minute projection changed for {symbol}"
            )
        base = pd.DataFrame(
            {"trade_date": [pd.Timestamp(session_date)], "symbol": [symbol]}
        )
        computed, _ = candidate.compute_partition_frame(
            raw,
            base,
            symbol=symbol,
        )
        if len(computed) != 1:
            raise Candidate49FutureObservationError(
                f"candidate49 formula did not return one row for {symbol}"
            )
        formula_eligible = bool(
            computed[f"{candidate.FACTOR_NAME}_eligible"].iloc[0]
        )
        if formula_eligible:
            formula_value = float(computed[candidate.FACTOR_NAME].iloc[0])
    quality_listing = bool(quality["quality_listing_eligible"])
    eligible = bool(formula_eligible and quality_listing)
    reasons: list[str] = []
    if not exact:
        reasons.append("not_exact_241_source_grid")
    if not reconciled:
        reasons.append("close_volume_amount_reconciliation_failed")
    if exact and reconciled and not formula_eligible:
        reasons.append("factor_formula_invalid_or_insufficient_nonzero_signs")
    if not bool(quality["listing_seasoning_eligible"]):
        reasons.append("listing_age_below_20_sessions")
    if not bool(quality["fundamental_quality_eligible"]):
        reasons.append("quarterly_quality_gate_failed_or_stale")
    return {
        "trade_date": pd.Timestamp(session_date),
        "symbol": symbol,
        "provider": "tushare",
        candidate.FACTOR_NAME: formula_value,
        f"{candidate.FACTOR_NAME}_formula_eligible": formula_eligible,
        "source_exact_241_grid": exact,
        "source_close_volume_amount_reconciled": reconciled,
        "listing_age_sessions": int(quality["listing_age_sessions"]),
        "listing_seasoning_eligible": bool(
            quality["listing_seasoning_eligible"]
        ),
        "quality_effective_date": quality["quality_effective_date"],
        "quality_age_days": quality["quality_age_days"],
        "roe": quality["roe"],
        "net_profit": quality["net_profit"],
        "revenue_yoy": quality["revenue_yoy"],
        "profit_yoy": quality["profit_yoy"],
        "fundamental_quality_eligible": bool(
            quality["fundamental_quality_eligible"]
        ),
        "quality_listing_eligible": quality_listing,
        f"{candidate.FACTOR_NAME}_eligible": eligible,
        "ineligibility_reasons": "|".join(reasons),
    }


def _validate_factor_snapshot(
    manifest_path: Path,
    *,
    session_date: dt.date,
    raw_manifest_path: Path,
    raw_manifest: dict[str, Any],
) -> tuple[dict[str, Any], pd.DataFrame]:
    root = manifest_path.parent
    raw_manifest_path = raw_manifest_path.expanduser().resolve()
    raw_manifest_sha256 = rich.file_digest(raw_manifest_path)
    manifest = rich.load_json_record(manifest_path, kind=FACTOR_SNAPSHOT_KIND)
    factor_path = root / "factor.parquet"
    quality_context = manifest.get("quality_context")
    if not (
        manifest.get("registration_id") == candidate.FUTURE_REGISTRATION_ID
        and manifest.get("registration_sha256")
        == candidate.FUTURE_REGISTRATION_SHA256
        and manifest.get("future_only_policy_sha256") == candidate.POLICY_SHA256
        and manifest.get("session_date") == session_date.isoformat()
        and (manifest.get("raw_snapshot") or {}).get("path")
        == str(raw_manifest_path)
        and (manifest.get("raw_snapshot") or {}).get("sha256")
        == raw_manifest_sha256
        and (manifest.get("raw_snapshot") or {}).get("dataset_sha256")
        == raw_manifest.get("dataset_sha256")
        and manifest.get("factor_name") == candidate.FACTOR_NAME
        and manifest.get("factor_direction") == "higher"
        and manifest.get("formula") == candidate.FACTOR_FORMULA
        and manifest.get("formula_or_direction_changed") is False
        and manifest.get("source_fields") == list(candidate.RAW_COLUMNS)
        and manifest.get("source_open_high_low_loaded_for_factor") is False
        and manifest.get("source_09_30_row_loaded_for_factor") is False
        and manifest.get("quality_source_fields")
        == list(FUTURE_QUALITY_COLUMNS)
        and manifest.get("quality_rows_after_signal_date_loaded") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get(
            "future_daily_fields_read_only_for_source_reconciliation"
        )
        == list(FUTURE_DAILY_RECONCILIATION_FIELDS)
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("execution_fields_read") == []
        and manifest.get("selection_performed") is False
        and manifest.get("open_high_low_used_for_formula_or_eligibility")
        is False
        and manifest.get("missing_incomplete_or_suspended_stock_days_imputed")
        is False
        and manifest.get("minimum_signal_names") == MINIMUM_SIGNAL_NAMES
        and isinstance(quality_context, dict)
        and set(quality_context)
        == {"quarterly_quality", "quarterly_quality_manifest"}
        and factor_path.is_file()
        and rich.file_digest(factor_path) == manifest.get("factor_byte_sha256")
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 factor snapshot header changed: {manifest_path}"
        )
    frame = pd.read_parquet(factor_path)
    if (
        tuple(frame.columns) != FACTOR_COLUMNS
        or len(frame) != int(manifest.get("rows", -1))
        or rich.frame_digest(frame) != manifest.get("factor_frame_sha256")
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 factor snapshot frame changed: {factor_path}"
        )
    formula_eligible = (
        frame[f"{candidate.FACTOR_NAME}_formula_eligible"].astype(bool)
    )
    quality_listing_eligible = frame["quality_listing_eligible"].astype(bool)
    eligible = frame[f"{candidate.FACTOR_NAME}_eligible"].astype(bool)
    eligible_count = int(eligible.sum())
    expected_status = (
        "eligible_for_deterministic_future_signal"
        if eligible_count >= MINIMUM_SIGNAL_NAMES
        else "session_ineligible_fewer_than_50_quality_listing_finite_values"
    )
    if (
        manifest.get("formula_eligible_rows")
        != int(formula_eligible.sum())
        or manifest.get("quality_listing_eligible_rows")
        != int(quality_listing_eligible.sum())
        or manifest.get("eligible_rows") != eligible_count
        or manifest.get("status") != expected_status
        or frame["symbol"].astype(str).duplicated().any()
        or frame["symbol"].astype(str).tolist()
        != sorted(frame["symbol"].astype(str).tolist())
        or set(frame["provider"].astype(str)) != {"tushare"}
        or not pd.to_datetime(
            frame["trade_date"], errors="coerce"
        ).dt.normalize().eq(pd.Timestamp(session_date)).all()
        or (
            eligible
            & ~np.isfinite(
                pd.to_numeric(
                    frame[candidate.FACTOR_NAME], errors="coerce"
                ).to_numpy(dtype=float)
            )
        ).any()
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 factor snapshot frame or statistics changed: {factor_path}"
        )
    raw_quality_context = (raw_manifest.get("frozen_context") or {}).get(
        "files"
    ) or {}
    for name, record in quality_context.items():
        if not isinstance(record, dict):
            raise Candidate49FutureObservationError(
                f"candidate49 factor snapshot quality context changed: {name}"
            )
        context_file = root / str(record.get("path_below_snapshot_root") or "")
        raw_record = raw_quality_context.get(name) or {}
        if not isinstance(raw_record, dict):
            raise Candidate49FutureObservationError(
                f"candidate49 factor snapshot quality context changed: {name}"
            )
        raw_context_file = raw_manifest_path.parent / str(
            raw_record.get("path_below_snapshot_root") or ""
        )
        if (
            not context_file.is_file()
            or not raw_context_file.is_file()
            or record.get("source_path") != str(raw_context_file.resolve())
            or record.get("sha256") != raw_record.get("sha256")
            or rich.file_digest(raw_context_file) != raw_record.get("sha256")
            or rich.file_digest(context_file) != record.get("sha256")
        ):
            raise Candidate49FutureObservationError(
                f"candidate49 factor snapshot quality context changed: {name}"
            )
    frozen_quality_manifest = json.loads(
        (
            root
            / str(
                quality_context["quarterly_quality_manifest"].get(
                    "path_below_snapshot_root"
                )
                or ""
            )
        ).read_text(encoding="utf-8")
    )
    if frozen_quality_manifest.get("sha256") != quality_context[
        "quarterly_quality"
    ].get("sha256"):
        raise Candidate49FutureObservationError(
            "candidate49 factor snapshot quality data/manifest link changed"
        )
    return manifest, frame


def _publish_factor_snapshot(
    *,
    data_root: Path,
    session_date: dt.date,
    raw_manifest_path: Path,
    raw_manifest: dict[str, Any],
) -> tuple[Path, dict[str, Any], pd.DataFrame]:
    raw_final, _, factor_final, factor_partial = _session_roots(
        data_root, session_date
    )
    raw_manifest_sha256 = rich.file_digest(raw_manifest_path)
    final_manifest_path = factor_final / "factor_manifest.json"
    if factor_final.exists():
        if not final_manifest_path.is_file():
            raise Candidate49FutureObservationError(
                f"published factor root has no manifest: {factor_final}"
            )
        manifest, frame = _validate_factor_snapshot(
            final_manifest_path,
            session_date=session_date,
            raw_manifest_path=raw_manifest_path,
            raw_manifest=raw_manifest,
        )
        return final_manifest_path, manifest, frame
    if factor_partial.exists():
        raise Candidate49FutureObservationError(
            "candidate49 factor partial root exists; factor construction has no "
            "provider side effect, so inspect and remove only after confirming no "
            "published manifest exists"
        )
    factor_partial.mkdir(parents=True, exist_ok=False)
    try:
        frozen_quality = _freeze_factor_context(
            partial_root=factor_partial,
            raw_root=raw_final,
            raw_context=raw_manifest["frozen_context"],
        )
        raw_context = raw_manifest["frozen_context"]["files"]
        calendar_path = raw_final / str(
            raw_context["calendar"]["path_below_snapshot_root"]
        )
        universe_path = raw_final / str(
            raw_context["buyable_universe"]["path_below_snapshot_root"]
        )
        calendar = _read_calendar(calendar_path)
        active = _active_interval_rows(universe_path, session_date)
        frozen_fundamentals = factor_partial / str(
            frozen_quality["quarterly_quality"]["path_below_snapshot_root"]
        )
        quality_frame = _quality_rows_for_session(
            active=active,
            calendar=calendar,
            session_date=session_date,
            fundamentals_path=frozen_fundamentals,
        )
        quality_by_symbol = {
            str(row["symbol"]): row.to_dict()
            for _, row in quality_frame.iterrows()
        }
        records = {
            str(record["symbol"]): record for record in raw_manifest["files"]
        }
        symbols = active["symbol"].astype(str).tolist()
        if set(records) != set(symbols):
            raise Candidate49FutureObservationError(
                "candidate49 raw and frozen active universes differ"
            )
        rows = [
            _factor_row(
                raw_root=raw_final,
                raw_record=records[symbol],
                session_date=session_date,
                quality=quality_by_symbol[symbol],
            )
            for symbol in symbols
        ]
        frame = pd.DataFrame(rows).loc[:, FACTOR_COLUMNS]
        frame = frame.sort_values("symbol", kind="stable").reset_index(drop=True)
        eligible = frame[f"{candidate.FACTOR_NAME}_eligible"].astype(bool)
        eligible_count = int(eligible.sum())
        factor_path = factor_partial / "factor.parquet"
        rich.atomic_write_frame(frame, factor_path)
        manifest = {
            "schema_version": 1,
            "kind": FACTOR_SNAPSHOT_KIND,
            "status": (
                "eligible_for_deterministic_future_signal"
                if eligible_count >= MINIMUM_SIGNAL_NAMES
                else "session_ineligible_fewer_than_50_quality_listing_finite_values"
            ),
            "created_at": _utc_now(),
            "registration_id": candidate.FUTURE_REGISTRATION_ID,
            "registration_sha256": candidate.FUTURE_REGISTRATION_SHA256,
            "future_only_policy_sha256": candidate.POLICY_SHA256,
            "session_date": session_date.isoformat(),
            "raw_snapshot": {
                "path": str(raw_manifest_path),
                "sha256": raw_manifest_sha256,
                "dataset_sha256": raw_manifest["dataset_sha256"],
            },
            "factor_name": candidate.FACTOR_NAME,
            "factor_direction": "higher",
            "formula": candidate.FACTOR_FORMULA,
            "formula_or_direction_changed": False,
            "source_fields": list(candidate.RAW_COLUMNS),
            "source_open_high_low_loaded_for_factor": False,
            "source_09_30_row_loaded_for_factor": False,
            "source_grid": (
                "exact 241 source rows retained in raw; factor Parquet read "
                "pushes down only 09:31--11:30 and 13:01--15:00"
            ),
            "rows": int(len(frame)),
            "formula_eligible_rows": int(
                frame[
                    f"{candidate.FACTOR_NAME}_formula_eligible"
                ].astype(bool).sum()
            ),
            "quality_listing_eligible_rows": int(
                frame["quality_listing_eligible"].astype(bool).sum()
            ),
            "eligible_rows": eligible_count,
            "minimum_signal_names": MINIMUM_SIGNAL_NAMES,
            "factor_byte_sha256": rich.file_digest(factor_path),
            "factor_frame_sha256": rich.frame_digest(frame),
            "quality_context": frozen_quality,
            "quality_source_fields": list(FUTURE_QUALITY_COLUMNS),
            "quality_announcement_filter": "announcement_date < signal_session",
            "quality_rows_after_signal_date_loaded": False,
            "quality_semantics": {
                "strict_next_local_session_after_announcement": True,
                "per_field_forward_fill_after_effective_event_deduplication": True,
                "maximum_age_days": MAXIMUM_QUALITY_AGE_DAYS,
                "minimum_listing_sessions": MINIMUM_LISTING_SESSIONS,
                "roe_minimum_inclusive": 5.0,
                "net_profit_strictly_positive": True,
                "revenue_yoy_strictly_positive": True,
                "profit_yoy_strictly_positive": True,
            },
            "open_high_low_used_for_formula_or_eligibility": False,
            "missing_incomplete_or_suspended_stock_days_imputed": False,
            "historical_daily_price_fields_read": [],
            "future_daily_fields_read_only_for_source_reconciliation": list(
                FUTURE_DAILY_RECONCILIATION_FIELDS
            ),
            "forward_return_fields_read": False,
            "execution_fields_read": [],
            "selection_performed": False,
        }
        rich.atomic_write_json(
            manifest,
            factor_partial / "factor_manifest.json",
        )
        factor_partial.replace(factor_final)
    except BaseException:
        shutil.rmtree(factor_partial, ignore_errors=True)
        raise
    observed, observed_frame = _validate_factor_snapshot(
        final_manifest_path,
        session_date=session_date,
        raw_manifest_path=raw_manifest_path,
        raw_manifest=raw_manifest,
    )
    return final_manifest_path, observed, observed_frame


def _signal_payload(
    *,
    session_date: dt.date,
    raw_manifest_path: Path,
    raw_manifest: dict[str, Any],
    factor_manifest_path: Path,
    factor_manifest: dict[str, Any],
    factor_frame: pd.DataFrame,
) -> dict[str, Any] | None:
    eligible = factor_frame.loc[
        factor_frame[f"{candidate.FACTOR_NAME}_eligible"].astype(bool)
    ].copy()
    eligible[candidate.FACTOR_NAME] = pd.to_numeric(
        eligible[candidate.FACTOR_NAME], errors="coerce"
    )
    eligible = eligible.loc[
        np.isfinite(eligible[candidate.FACTOR_NAME].to_numpy(dtype=float))
    ]
    if len(eligible) < MINIMUM_SIGNAL_NAMES:
        return None
    ranked = eligible.sort_values(
        [candidate.FACTOR_NAME, "symbol"],
        ascending=[False, True],
        kind="stable",
    ).head(3)
    selections = [
        {
            "rank": rank,
            "symbol": str(row.symbol),
            "factor_value": float(getattr(row, candidate.FACTOR_NAME)),
        }
        for rank, row in enumerate(ranked.itertuples(index=False), start=1)
    ]
    return {
        "entry_id": (
            f"{candidate.FUTURE_REGISTRATION_ID}:signal:{session_date.isoformat()}"
        ),
        "session_date": session_date.isoformat(),
        "observed_at": factor_manifest["created_at"],
        "registration_sha256": candidate.FUTURE_REGISTRATION_SHA256,
        "raw_snapshot": {
            "path": str(raw_manifest_path),
            "sha256": rich.file_digest(raw_manifest_path),
            "dataset_sha256": raw_manifest["dataset_sha256"],
        },
        "factor_snapshot": {
            "path": str(factor_manifest_path),
            "sha256": rich.file_digest(factor_manifest_path),
            "frame_sha256": factor_manifest["factor_frame_sha256"],
        },
        "factor_name": candidate.FACTOR_NAME,
        "factor_direction": "higher",
        "eligible_names": int(len(eligible)),
        "ranking": "descending_factor_then_ascending_stock_code",
        "topk": 3,
        "selections": selections,
        "execution_rule": {
            "entry": "next accepted local session open",
            "exit": "third accepted local session close after entry",
            "initial_capital_cny": 200000,
            "target_entry_exposure_fraction_per_slot": 0.05,
            "maximum_entry_exposure_fraction_per_signal": 0.15,
            "buy_lot_size_shares": 100,
            "unfilled_entry_policy": "keep slot in cash without replacement",
            "paper_observation_only": True,
        },
        "provider_request_issued": bool(raw_manifest["provider_calls"]),
        "future_outcome_fields_read": [],
        "forward_return_fields_read": False,
        "execution_or_order_performed": False,
        "investment_advice": False,
    }


def _validate_signal_entry_semantics(
    entry: dict[str, Any],
) -> tuple[dict[str, Any], pd.DataFrame]:
    try:
        session_date = dt.date.fromisoformat(str(entry["session_date"]))
    except (KeyError, ValueError) as exc:
        raise Candidate49FutureObservationError(
            "candidate49 signal ledger semantic session changed"
        ) from exc
    raw_link = entry.get("raw_snapshot") or {}
    raw_manifest_path = Path(
        str(raw_link.get("path") or "")
    ).expanduser().resolve()
    if (
        not raw_manifest_path.is_file()
        or rich.file_digest(raw_manifest_path) != raw_link.get("sha256")
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 signal raw manifest changed: {raw_manifest_path}"
        )
    raw_manifest = rich.load_json_record(
        raw_manifest_path,
        kind=RAW_SNAPSHOT_KIND,
    )
    if not (
        raw_manifest.get("status")
        == "atomically_published_immutable_future_raw_session"
        and raw_manifest.get("registration_id")
        == candidate.FUTURE_REGISTRATION_ID
        and raw_manifest.get("registration_sha256")
        == candidate.FUTURE_REGISTRATION_SHA256
        and raw_manifest.get("future_only_policy_sha256")
        == candidate.POLICY_SHA256
        and raw_manifest.get("session_date") == session_date.isoformat()
        and raw_manifest.get("dataset_sha256")
        == raw_link.get("dataset_sha256")
        and isinstance(raw_manifest.get("frozen_context"), dict)
        and isinstance(raw_manifest.get("files"), list)
        and raw_manifest.get("forward_return_fields_read") is False
        and raw_manifest.get("historical_backfill_allowed") is False
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 signal raw snapshot semantics changed: {raw_manifest_path}"
        )
    factor_link = entry.get("factor_snapshot") or {}
    factor_manifest_path = Path(
        str(factor_link.get("path") or "")
    ).expanduser().resolve()
    if (
        not factor_manifest_path.is_file()
        or rich.file_digest(factor_manifest_path) != factor_link.get("sha256")
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 signal factor manifest changed: {factor_manifest_path}"
        )
    factor_manifest, factor_frame = _validate_factor_snapshot(
        factor_manifest_path,
        session_date=session_date,
        raw_manifest_path=raw_manifest_path,
        raw_manifest=raw_manifest,
    )
    if factor_manifest.get("factor_frame_sha256") != factor_link.get(
        "frame_sha256"
    ):
        raise Candidate49FutureObservationError(
            f"candidate49 signal factor frame link changed: {factor_manifest_path}"
        )
    expected = _signal_payload(
        session_date=session_date,
        raw_manifest_path=raw_manifest_path,
        raw_manifest=raw_manifest,
        factor_manifest_path=factor_manifest_path,
        factor_manifest=factor_manifest,
        factor_frame=factor_frame,
    )
    observed = {
        key: value
        for key, value in entry.items()
        if key not in {"ordinal", "previous_entry_sha256", "entry_sha256"}
    }
    if expected is None or observed != expected:
        raise Candidate49FutureObservationError(
            f"candidate49 signal ledger payload changed: {entry.get('entry_id')}"
        )
    return factor_manifest, factor_frame


def validate_signal_ledger_semantics(
    signal_path: Path,
) -> list[dict[str, Any]]:
    """Recompute every registered signal from its immutable factor evidence."""

    ledger = candidate.validate_future_ledger(
        signal_path,
        candidate.FUTURE_SIGNAL_LEDGER_KIND,
    )
    entries = list(ledger["entries"])
    dates = [
        dt.date.fromisoformat(str(entry["session_date"]))
        for entry in entries
    ]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise Candidate49FutureObservationError(
            "candidate49 signal ledger is not strictly chronological"
        )
    for entry in entries:
        _validate_signal_entry_semantics(entry)
    return entries


def _append_signal_idempotently(
    *,
    signal_path: Path,
    payload: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    entries = validate_signal_ledger_semantics(signal_path)
    entry_id = str(payload["entry_id"])
    session_date = str(payload["session_date"])
    for entry in entries:
        if str(entry.get("entry_id")) == entry_id:
            observed_payload = {
                key: value
                for key, value in entry.items()
                if key
                not in {"ordinal", "previous_entry_sha256", "entry_sha256"}
            }
            if observed_payload != payload:
                raise Candidate49FutureObservationError(
                    "candidate49 signal ledger contains a conflicting idempotent entry"
                )
            return entry, False
        if str(entry.get("session_date")) == session_date:
            raise Candidate49FutureObservationError(
                "candidate49 signal ledger already contains a conflicting session"
            )
    return (
        candidate.append_future_ledger_entry(
            path=signal_path,
            kind=candidate.FUTURE_SIGNAL_LEDGER_KIND,
            payload=payload,
        ),
        True,
    )


def collect_future_session(
    *,
    data_root: Path,
    session_date: dt.date,
    allow_large: bool,
    provider_uri: Path = candidate.DEFAULT_PROVIDER_URI,
    daily_raw_root: Path = DEFAULT_DAILY_RAW_ROOT,
    fundamentals_path: Path = DEFAULT_FUNDAMENTALS,
    fundamentals_manifest_path: Path = DEFAULT_FUNDAMENTALS_MANIFEST,
    signal_path: Path = candidate.FUTURE_SIGNAL_LEDGER,
    execution_path: Path = candidate.FUTURE_EXECUTION_LEDGER,
    now: dt.datetime | None = None,
    token_configured: bool | None = None,
    fetcher: FetchFunction | None = None,
    provider_check: ProviderCheck | None = None,
    workers: int = rich.TUSHARE_ONE_MINUTE_WORKERS,
    request_interval_seconds: float = (
        rich.TUSHARE_ONE_MINUTE_MINIMUM_REQUEST_INTERVAL_SECONDS
    ),
    clock: ClockFunction | None = None,
) -> dict[str, Any]:
    """Run the immutable source -> factor -> close-known signal pipeline."""

    if workers < 1 or workers > rich.TUSHARE_ONE_MINUTE_WORKERS:
        raise Candidate49FutureObservationError(
            f"candidate49 workers must be between 1 and {rich.TUSHARE_ONE_MINUTE_WORKERS}"
        )
    if request_interval_seconds < 0.0:
        raise Candidate49FutureObservationError(
            "candidate49 request interval cannot be negative"
        )
    data_root = data_root.expanduser().resolve()
    provider_uri = provider_uri.expanduser().resolve()
    daily_raw_root = daily_raw_root.expanduser().resolve()
    fundamentals_path = fundamentals_path.expanduser().resolve()
    fundamentals_manifest_path = fundamentals_manifest_path.expanduser().resolve()
    signal_path = signal_path.expanduser().resolve()
    execution_path = execution_path.expanduser().resolve()
    raw_final, _, factor_final, _ = _session_roots(data_root, session_date)
    complete_publication_exists = raw_final.exists() and factor_final.exists()
    if not complete_publication_exists:
        _active_root_binding(
            provider_uri=provider_uri,
            daily_raw_root=daily_raw_root,
        )
        _validate_active_daily_source_file_identities(
            provider_uri=provider_uri,
            daily_raw_root=daily_raw_root,
            session_date=session_date,
        )
        _, timing_failures = candidate.future_session_time_boundary_failures(
            session_date=session_date,
            now=now,
        )
        if timing_failures:
            raise Candidate49FutureObservationError(
                "candidate49 future session stopped before provider request: "
                + ",".join(timing_failures)
            )
    candidate.initialize_future_ledgers(
        signal_path=signal_path,
        execution_path=execution_path,
    )
    validate_signal_ledger_semantics(signal_path)
    if not complete_publication_exists:
        preflight = candidate.future_session_preflight(
            session_date=session_date,
            data_root=data_root,
            provider_uri=provider_uri,
            now=now,
            token_configured=token_configured,
            signal_path=signal_path,
            execution_path=execution_path,
        )
        if not preflight["ready"]:
            raise Candidate49FutureObservationError(
                "candidate49 future session stopped before provider request: "
                + ",".join(preflight["failures"])
            )
    data_root.mkdir(parents=True, exist_ok=True)
    lock_path = data_root / ".candidate49_future_observation.lock"
    with candidate.foundation.ProcessLock(lock_path):
        raw_manifest_path, raw_manifest, provider_calls = _publish_raw_snapshot(
            data_root=data_root,
            provider_uri=provider_uri,
            daily_raw_root=daily_raw_root,
            fundamentals_path=fundamentals_path,
            fundamentals_manifest_path=fundamentals_manifest_path,
            session_date=session_date,
            allow_large=allow_large,
            now=now,
            token_configured=token_configured,
            signal_path=signal_path,
            execution_path=execution_path,
            fetcher=fetcher,
            provider_check=provider_check,
            workers=workers,
            request_interval_seconds=request_interval_seconds,
            clock=clock,
        )
        if not factor_final.exists():
            factor_check_now = clock() if clock is not None else now
            _, timing_failures = candidate.future_session_time_boundary_failures(
                session_date=session_date,
                now=factor_check_now,
            )
            if timing_failures:
                raise Candidate49FutureObservationError(
                    "candidate49 factor publication stopped after the signal "
                    "date: "
                    + ",".join(timing_failures)
                )
        factor_manifest_path, factor_manifest, factor_frame = (
            _publish_factor_snapshot(
                data_root=data_root,
                session_date=session_date,
                raw_manifest_path=raw_manifest_path,
                raw_manifest=raw_manifest,
            )
        )
        payload = _signal_payload(
            session_date=session_date,
            raw_manifest_path=raw_manifest_path,
            raw_manifest=raw_manifest,
            factor_manifest_path=factor_manifest_path,
            factor_manifest=factor_manifest,
            factor_frame=factor_frame,
        )
        entry: dict[str, Any] | None = None
        appended = False
        if payload is not None:
            entry, appended = _append_signal_idempotently(
                signal_path=signal_path,
                payload=payload,
            )
        return {
            "status": (
                "future_signal_appended"
                if appended
                else (
                    "future_signal_already_present_idempotent"
                    if entry is not None
                    else "future_session_frozen_without_signal_fewer_than_50_names"
                )
            ),
            "session_date": session_date.isoformat(),
            "raw_manifest": str(raw_manifest_path),
            "raw_manifest_sha256": rich.file_digest(raw_manifest_path),
            "factor_manifest": str(factor_manifest_path),
            "factor_manifest_sha256": rich.file_digest(factor_manifest_path),
            "eligible_names": int(factor_manifest["eligible_rows"]),
            "selections": [] if entry is None else entry["selections"],
            "signal_entry_sha256": (
                None if entry is None else entry["entry_sha256"]
            ),
            "provider_calls_this_invocation": provider_calls,
            "raw_snapshot_reused": provider_calls == 0,
            "forward_return_fields_read": False,
            "execution_or_order_performed": False,
            "historical_backfill_allowed": False,
        }


def preflight_future_session(
    *,
    data_root: Path,
    session_date: dt.date,
    provider_uri: Path = candidate.DEFAULT_PROVIDER_URI,
    daily_raw_root: Path = DEFAULT_DAILY_RAW_ROOT,
    fundamentals_path: Path = DEFAULT_FUNDAMENTALS,
    fundamentals_manifest_path: Path = DEFAULT_FUNDAMENTALS_MANIFEST,
    signal_path: Path = candidate.FUTURE_SIGNAL_LEDGER,
    execution_path: Path = candidate.FUTURE_EXECUTION_LEDGER,
    now: dt.datetime | None = None,
    token_configured: bool | None = None,
) -> dict[str, Any]:
    """Combine every local source-to-signal gate without writing or requesting."""

    data_root = data_root.expanduser().resolve()
    provider_uri = provider_uri.expanduser().resolve()
    daily_raw_root = daily_raw_root.expanduser().resolve()
    fundamentals_path = fundamentals_path.expanduser().resolve()
    fundamentals_manifest_path = fundamentals_manifest_path.expanduser().resolve()
    signal_path = signal_path.expanduser().resolve()
    execution_path = execution_path.expanduser().resolve()
    base = candidate.future_session_preflight(
        session_date=session_date,
        data_root=data_root,
        provider_uri=provider_uri,
        now=now,
        token_configured=token_configured,
        signal_path=signal_path,
        execution_path=execution_path,
    )
    failures = list(base["failures"])
    signal_ledger_semantic_failure: str | None = None
    signal_ledger_semantics_ready = False
    if signal_path.is_file():
        try:
            validate_signal_ledger_semantics(signal_path)
        except (
            Candidate49FutureObservationError,
            candidate.IntradayCumulativeVwapCrossingRateError,
            OSError,
            ValueError,
        ) as exc:
            failures.append(
                "candidate49_signal_ledger_semantics_not_accepted"
            )
            signal_ledger_semantic_failure = rich.safe_exception_text(exc)
        else:
            signal_ledger_semantics_ready = True
    active_root_binding: dict[str, str] | None = None
    daily_file_identity: dict[str, Any] | None = None
    try:
        active_root_binding = _active_root_binding(
            provider_uri=provider_uri,
            daily_raw_root=daily_raw_root,
        )
        daily_file_identity = _validate_active_daily_source_file_identities(
            provider_uri=provider_uri,
            daily_raw_root=daily_raw_root,
            session_date=session_date,
        )
    except Candidate49FutureObservationError as exc:
        failures.append(str(exc))
    quality_failure: str | None = None
    quality_ready = False
    try:
        _validate_future_quality_source(
            fundamentals_path=fundamentals_path,
            fundamentals_manifest_path=fundamentals_manifest_path,
            session_date=session_date,
        )
    except (Candidate49FutureObservationError, OSError, ValueError) as exc:
        failures.append("future_quarterly_quality_not_accepted")
        quality_failure = rich.safe_exception_text(exc)
    else:
        quality_ready = True
    failures = list(dict.fromkeys(failures))
    ready = not failures
    return {
        **base,
        "status": (
            "ready_for_explicit_future_source_to_signal_collection"
            if ready
            else "not_ready_no_provider_request"
        ),
        "ready": ready,
        "recommended_cli_exit_code": 0 if ready else 2,
        "failures": failures,
        "future_quarterly_quality_ready": quality_ready,
        "future_quarterly_quality_failure": quality_failure,
        "future_quarterly_quality_path": str(fundamentals_path),
        "future_quarterly_quality_sha256": (
            rich.file_digest(fundamentals_path) if quality_ready else None
        ),
        "future_quarterly_quality_manifest_path": str(
            fundamentals_manifest_path
        ),
        "future_quarterly_quality_manifest_sha256": (
            rich.file_digest(fundamentals_manifest_path)
            if quality_ready
            else None
        ),
        "active_root_binding": active_root_binding,
        "daily_file_identity_preflight": daily_file_identity,
        "signal_ledger_semantics_ready": signal_ledger_semantics_ready,
        "signal_ledger_semantic_failure": signal_ledger_semantic_failure,
        "provider_request_issued": False,
        "minute_rows_read": False,
        "signal_or_execution_entry_written": False,
        "filesystem_write_performed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--session", type=dt.date.fromisoformat, required=True)
    parser.add_argument("--provider-uri", type=Path, default=candidate.DEFAULT_PROVIDER_URI)
    parser.add_argument("--daily-raw-root", type=Path, default=DEFAULT_DAILY_RAW_ROOT)
    parser.add_argument("--fundamentals", type=Path, default=DEFAULT_FUNDAMENTALS)
    parser.add_argument(
        "--fundamentals-manifest",
        type=Path,
        default=DEFAULT_FUNDAMENTALS_MANIFEST,
    )
    parser.add_argument("--allow-large", action="store_true")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help=(
            "validate every local prerequisite without any write or provider "
            "request; exit 2 while not ready"
        ),
    )
    parser.add_argument("--workers", type=int, default=rich.TUSHARE_ONE_MINUTE_WORKERS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.preflight_only:
        result = preflight_future_session(
            data_root=args.data_root,
            session_date=args.session,
            provider_uri=args.provider_uri,
            daily_raw_root=args.daily_raw_root,
            fundamentals_path=args.fundamentals,
            fundamentals_manifest_path=args.fundamentals_manifest,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(result["recommended_cli_exit_code"])
    result = collect_future_session(
        data_root=args.data_root,
        session_date=args.session,
        allow_large=args.allow_large,
        provider_uri=args.provider_uri,
        daily_raw_root=args.daily_raw_root,
        fundamentals_path=args.fundamentals,
        fundamentals_manifest_path=args.fundamentals_manifest,
        workers=args.workers,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
