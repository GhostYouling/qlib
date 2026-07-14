#!/usr/bin/env python3
"""Ingest auditable A-share intraday and event data from licensed providers.

This tool deliberately does not replace ``a_share_data_pipeline.py``.  The
existing pipeline remains the daily OHLCV source used by the production-like
selection workflow.  This script stores paid/credentialed data separately,
with a manifest for each immutable download snapshot, so that a research run
can always identify its provider, retrieval time, and raw input files.

Supported providers
-------------------
* ``tushare``: minute OHLCV plus end-of-day moneyflow/limit-list/top-list.
* ``jqdata``: minute OHLCV.
* ``rqdata``: minute OHLCV.

Credentials are read only from environment variables.  Never place a token or
password in a command line, a config file committed to git, or a run manifest.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data"
RAW_ROOT = DATA_ROOT / "raw" / "a_share" / "rich"
METADATA_ROOT = DATA_ROOT / "metadata" / "rich_data"
RUNS_ROOT = METADATA_ROOT / "runs"
ALIGNMENTS_ROOT = METADATA_ROOT / "alignments"
FEATURE_RUNS_ROOT = METADATA_ROOT / "feature_runs"
DERIVED_ROOT = DATA_ROOT / "derived" / "a_share" / "rich"
DAILY_RAW_DIR = DATA_ROOT / "raw" / "a_share" / "daily"
DEFAULT_MINUTE_FACTOR_SPEC = REPO_ROOT / "docs" / "a_share_minute_factor_preregistration.json"

DEFAULT_ACCEPTANCE_SYMBOLS = ("600519", "000001", "300750", "688981")
PROVIDER_REQUIREMENTS = {
    "tushare": {"package": "tushare", "environment": ("TUSHARE_TOKEN",)},
    "jqdata": {"package": "jqdatasdk", "environment": ("JQDATA_USERNAME", "JQDATA_PASSWORD")},
    "rqdata": {"package": "rqdatac", "environment": ("RQDATA_USERNAME", "RQDATA_PASSWORD")},
}
EVENT_DATASETS = ("moneyflow", "limit-list", "top-list")
MINUTE_FEATURE_EXPECTED_BARS = 240
MINUTE_FEATURE_NAMES = (
    "late_return_30m",
    "late_amount_share_30m",
    "late_vwap_to_day_vwap_30m",
    "opening_gap_digestion",
    "intraday_realized_volatility",
)
MINUTE_FEATURE_DIRECTIONS = ("higher", "higher", "higher", "higher", "lower")
REQUIRED_DAILY_PRICE_BASIS = "close_known_raw_pct_chg_chain_v1"


class RichDataError(RuntimeError):
    """A recoverable provider, credential, or data-contract error."""


@dataclass(frozen=True)
class ProviderAvailability:
    """Safe provider readiness status; secrets are never represented here."""

    provider: str
    package: str
    package_installed: bool
    required_environment: tuple[str, ...]
    missing_environment: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return self.package_installed and not self.missing_environment


def parse_date(value: str) -> dt.date:
    """Parse a CLI ISO date."""

    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc


def latest_completed_session_date(now: dt.datetime | None = None) -> dt.date:
    """Conservatively avoid requesting a still-forming A-share session.

    The workspace time zone is China/Singapore.  The function intentionally
    only knows weekends; an exchange holiday will naturally return no rows and
    be recorded as such in the manifest rather than treated as a data error.
    """

    local_now = now or dt.datetime.now()
    cutoff = local_now.date()
    if local_now.weekday() < 5 and local_now.time() < dt.time(15, 30):
        cutoff -= dt.timedelta(days=1)
    while cutoff.weekday() >= 5:
        cutoff -= dt.timedelta(days=1)
    return cutoff


def qlib_symbol(code: str) -> str:
    """Convert a six-digit A-share code to the repository's symbol form."""

    code = str(code).strip().zfill(6)
    if code.startswith(("6", "9")):
        return f"SH{code}"
    if code.startswith(("0", "1", "2", "3")):
        return f"SZ{code}"
    raise RichDataError(f"unsupported A-share code: {code}")


def vendor_symbol(code: str, provider: str) -> str:
    """Return the selected provider's stock-code convention."""

    code = str(code).strip().zfill(6)
    symbol = qlib_symbol(code)
    if provider == "tushare":
        return f"{code}.{'SH' if symbol.startswith('SH') else 'SZ'}"
    if provider in {"jqdata", "rqdata"}:
        return f"{code}.{'XSHG' if symbol.startswith('SH') else 'XSHE'}"
    raise RichDataError(f"unknown provider: {provider}")


def parse_symbols(value: str) -> list[str]:
    """Parse and de-duplicate a comma-separated A-share code list."""

    symbols = [item.strip() for item in value.split(",") if item.strip()]
    if not symbols:
        raise argparse.ArgumentTypeError("at least one symbol is required")
    normalized: list[str] = []
    for code in symbols:
        if not code.isdigit() or len(code) > 6:
            raise argparse.ArgumentTypeError(f"invalid A-share code: {code}")
        code = code.zfill(6)
        qlib_symbol(code)
        if code not in normalized:
            normalized.append(code)
    return normalized


def provider_availability(provider: str) -> ProviderAvailability:
    """Report credential/SDK readiness without disclosing a secret's value."""

    try:
        details = PROVIDER_REQUIREMENTS[provider]
    except KeyError as exc:
        raise RichDataError(f"unknown provider: {provider}") from exc
    required = tuple(details["environment"])
    return ProviderAvailability(
        provider=provider,
        package=str(details["package"]),
        package_installed=importlib.util.find_spec(str(details["package"])) is not None,
        required_environment=required,
        missing_environment=tuple(key for key in required if not os.environ.get(key)),
    )


def require_provider(provider: str) -> None:
    """Fail before a network call when the selected provider is not usable."""

    availability = provider_availability(provider)
    if not availability.package_installed:
        raise RichDataError(
            f"{provider} SDK is not installed; run "
            "python -m pip install -r scripts/data_collector/a_share_rich/requirements.txt"
        )
    if availability.missing_environment:
        keys = ", ".join(availability.missing_environment)
        raise RichDataError(f"{provider} credentials are missing from the environment: {keys}")


def _column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    lookup = {str(column).casefold(): str(column) for column in frame.columns}
    for candidate in candidates:
        found = lookup.get(candidate.casefold())
        if found is not None:
            return found
    return None


def canonicalize_minute_bars(
    frame: pd.DataFrame,
    provider: str,
    code: str,
    start: dt.date,
    end: dt.date,
) -> pd.DataFrame:
    """Normalize provider bars to a strict, unadjusted minute-bar contract.

    We retain raw, unadjusted prices.  Adjustment is deliberately deferred to
    downstream factor construction and must use a documented as-of adjustment
    series; a vendor's mutable present-day qfq series is not point-in-time.
    """

    if frame is None or frame.empty:
        return pd.DataFrame(
            columns=[
                "datetime", "symbol", "source_symbol", "open", "high", "low", "close", "volume", "amount", "provider"
            ]
        )
    normalized = frame.copy()
    # JQData commonly returns a DatetimeIndex without a name, while RQData can
    # return a named MultiIndex.  Both carry the provider timestamp in the
    # index and therefore must be made explicit before column resolution.
    if not isinstance(normalized.index, pd.RangeIndex):
        normalized = normalized.reset_index()
    datetime_column = _column(normalized, ("datetime", "trade_time", "time", "date"))
    if datetime_column is None:
        raise RichDataError(f"{provider} minute response has no datetime column")
    field_map = {
        "open": ("open",),
        "high": ("high",),
        "low": ("low",),
        "close": ("close",),
        "volume": ("volume", "vol"),
        "amount": ("amount", "money", "total_turnover", "turnover"),
    }
    resolved = {field: _column(normalized, candidates) for field, candidates in field_map.items()}
    missing = [field for field, column in resolved.items() if column is None]
    if missing:
        raise RichDataError(f"{provider} minute response is missing required columns: {', '.join(missing)}")
    result = pd.DataFrame(
        {
            "datetime": pd.to_datetime(normalized[datetime_column], errors="coerce"),
            "symbol": qlib_symbol(code),
            "source_symbol": vendor_symbol(code, provider),
            "provider": provider,
        }
    )
    for field, column in resolved.items():
        assert column is not None
        result[field] = pd.to_numeric(normalized[column], errors="coerce")
    start_timestamp = pd.Timestamp(start)
    end_timestamp = pd.Timestamp(end) + pd.Timedelta(days=1)
    result = result.loc[(result["datetime"] >= start_timestamp) & (result["datetime"] < end_timestamp)].copy()
    result = result.dropna(subset=["datetime", "open", "high", "low", "close", "volume", "amount"])
    if result.empty:
        return result.sort_values("datetime").reset_index(drop=True)
    invalid_price = (
        (result[["open", "high", "low", "close"]] <= 0).any(axis=1)
        | (result["high"] < result[["open", "low", "close"]].max(axis=1))
        | (result["low"] > result[["open", "high", "close"]].min(axis=1))
        | (result["volume"] < 0)
        | (result["amount"] < 0)
    )
    if invalid_price.any():
        raise RichDataError(f"{provider} returned {int(invalid_price.sum())} invalid minute bars for {code}")
    result = result.drop_duplicates(subset=["datetime"], keep="last").sort_values("datetime")
    return result.reset_index(drop=True)


def minute_daily_summary(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Return small reconciliation summaries without duplicating the raw data."""

    if frame.empty:
        return []
    work = frame.assign(trade_date=frame["datetime"].dt.date.astype(str))
    summaries: list[dict[str, Any]] = []
    for trade_date, group in work.groupby("trade_date", sort=True):
        summaries.append(
            {
                "trade_date": trade_date,
                "bars": int(len(group)),
                "first_bar": group["datetime"].iloc[0].isoformat(),
                "last_bar": group["datetime"].iloc[-1].isoformat(),
                "last_close": float(group["close"].iloc[-1]),
                "volume": float(group["volume"].sum()),
                "amount": float(group["amount"].sum()),
            }
        )
    return summaries


def _in_regular_session(timestamp: pd.Timestamp) -> bool:
    """Accept either provider's start- or end-labelled A-share minute bar."""

    time_of_day = timestamp.time()
    return dt.time(9, 30) <= time_of_day <= dt.time(11, 30) or dt.time(13, 0) <= time_of_day <= dt.time(15, 0)


def minute_session_check(frame: pd.DataFrame) -> dict[str, Any]:
    """Check that minute bars are timestamped inside regular A-share sessions.

    A provider may label a bar by its start (09:30) or end (09:31) minute, so
    this deliberately accepts both conventions.  Trading halts can reduce the
    count, therefore row count is diagnostic information rather than a reason
    to silently fill or reject valid source data.
    """

    if frame.empty:
        return {"status": "failed", "reason": "no_bars", "days": []}
    work = frame.assign(trade_date=frame["datetime"].dt.date.astype(str))
    days: list[dict[str, Any]] = []
    for trade_date, group in work.groupby("trade_date", sort=True):
        in_session = group["datetime"].map(_in_regular_session)
        days.append(
            {
                "trade_date": trade_date,
                "bars": int(len(group)),
                "in_regular_session_bars": int(in_session.sum()),
                "out_of_session_bars": int((~in_session).sum()),
                "first_bar": group["datetime"].iloc[0].isoformat(),
                "last_bar": group["datetime"].iloc[-1].isoformat(),
            }
        )
    return {
        "status": "passed" if all(day["out_of_session_bars"] == 0 for day in days) else "failed",
        "days": days,
    }


def _relative_error(actual: float, expected: float) -> float | None:
    if not pd.notna(actual) or not pd.notna(expected) or expected == 0:
        return None
    return abs(actual / expected - 1.0)


def minute_daily_reconciliation(frame: pd.DataFrame) -> dict[str, Any]:
    """Compare minute aggregates with local daily data without mixing prices.

    Local daily prices are qfq while incoming minute prices are explicitly raw.
    Absolute prices and close-to-close returns therefore are not comparable at
    an ex-right/ex-dividend boundary.  Same-day OHLC/close ratios are invariant
    to one day's price scale and can be reconciled safely.  Volume and amount
    ratios are retained to discover provider unit conventions before factors
    use the data.
    """

    if frame.empty:
        return {"status": "failed", "reason": "no_bars", "days": []}
    symbol = str(frame["symbol"].iloc[0]).lower()
    path = DAILY_RAW_DIR / f"{symbol}.parquet"
    if not path.exists():
        return {"status": "unavailable", "reason": f"missing_local_daily:{path}", "days": []}
    daily = pd.read_parquet(path)
    daily["date"] = pd.to_datetime(daily["date"]).dt.normalize()
    daily = daily.set_index("date")
    work = frame.assign(trade_date=frame["datetime"].dt.normalize())
    days: list[dict[str, Any]] = []
    for trade_date, group in work.groupby("trade_date", sort=True):
        daily_row = daily.loc[daily.index == trade_date]
        if daily_row.empty:
            days.append({"trade_date": trade_date.date().isoformat(), "status": "missing_local_daily"})
            continue
        reference = daily_row.iloc[-1]
        minute_close = float(group["close"].iloc[-1])
        minute_ohlc = {
            "open": float(group["open"].iloc[0]),
            "high": float(group["high"].max()),
            "low": float(group["low"].min()),
            "close": minute_close,
        }
        price_relative_errors = {
            field: _relative_error(minute_ohlc[field] / minute_close, float(reference[field]) / float(reference["close"]))
            for field in ("open", "high", "low")
        }
        volume_ratio = float(group["volume"].sum() / float(reference["volume"])) if float(reference["volume"]) else None
        amount_ratio = float(group["amount"].sum() / float(reference["amount"])) if float(reference["amount"]) else None
        price_ok = all(error is not None and error <= 0.002 for error in price_relative_errors.values())
        amount_ok = amount_ratio is not None and abs(amount_ratio - 1.0) <= 0.005
        # The public daily pipe reports volume in lots.  Sources can report
        # shares or lots, so accept either 1x or 100x here but record the
        # inferred ratio; never rescale a provider silently.
        volume_ok = volume_ratio is not None and min(abs(volume_ratio - 1.0), abs(volume_ratio - 100.0)) <= 0.005
        days.append(
            {
                "trade_date": trade_date.date().isoformat(),
                "status": "passed" if price_ok and amount_ok and volume_ok else "failed",
                "price_relative_errors": price_relative_errors,
                "amount_ratio_to_local_daily": amount_ratio,
                "volume_ratio_to_local_daily": volume_ratio,
                "inferred_volume_unit": "shares" if volume_ratio is not None and abs(volume_ratio - 100.0) <= 0.005 else "lots",
            }
        )
    statuses = [day["status"] for day in days]
    if statuses and all(status == "passed" for status in statuses):
        status = "passed"
    elif "missing_local_daily" in statuses:
        status = "unavailable"
    else:
        status = "failed"
    return {"status": status, "daily_price_basis": "qfq_ratio_only", "days": days}


def minute_acceptance_report(frame: pd.DataFrame) -> dict[str, Any]:
    """Run the automatic checks required before minute data may become features."""

    session = minute_session_check(frame)
    reconciliation = minute_daily_reconciliation(frame)
    passed = session["status"] == "passed" and reconciliation["status"] == "passed"
    return {
        "status": "automatic_checks_passed_pending_time_alignment" if passed else "automatic_checks_failed",
        "session": session,
        "daily_reconciliation": reconciliation,
    }


def _import_tushare() -> Any:
    import tushare as ts

    ts.set_token(os.environ["TUSHARE_TOKEN"])
    return ts


def fetch_tushare_minutes(code: str, start: dt.date, end: dt.date, frequency: str) -> pd.DataFrame:
    """Fetch raw minute bars through Tushare's documented ``pro_bar`` wrapper."""

    ts = _import_tushare()
    return ts.pro_bar(
        ts_code=vendor_symbol(code, "tushare"),
        asset="E",
        adj=None,
        freq=frequency,
        # Tushare minute requests require time-of-day parameters and omit an
        # end date supplied without a time component.
        start_date=f"{start.isoformat()} 09:00:00",
        end_date=f"{end.isoformat()} 17:00:00",
    )


def fetch_jqdata_minutes(code: str, start: dt.date, end: dt.date, frequency: str) -> pd.DataFrame:
    """Fetch raw minute bars with JQData, authenticating only in process memory."""

    from jqdatasdk import auth, get_price

    authenticated = auth(os.environ["JQDATA_USERNAME"], os.environ["JQDATA_PASSWORD"])
    if authenticated is False:
        raise RichDataError("JQData rejected the configured credentials")
    return get_price(
        vendor_symbol(code, "jqdata"),
        start_date=f"{start.isoformat()} 09:30:00",
        end_date=f"{end.isoformat()} 15:00:00",
        frequency=frequency,
        fields=["open", "high", "low", "close", "volume", "money"],
        skip_paused=False,
        fq=None,
        panel=False,
    )


def fetch_rqdata_minutes(code: str, start: dt.date, end: dt.date, frequency: str) -> pd.DataFrame:
    """Fetch raw minute bars from RQData's licensed API."""

    import rqdatac

    rqdatac.init(os.environ["RQDATA_USERNAME"], os.environ["RQDATA_PASSWORD"])
    return rqdatac.get_price(
        vendor_symbol(code, "rqdata"),
        start_date=start,
        end_date=end,
        frequency=frequency,
        fields=["open", "high", "low", "close", "volume", "total_turnover"],
        adjust_type="none",
        skip_suspended=False,
        expect_df=True,
    )


MINUTE_FETCHERS: dict[str, Callable[[str, dt.date, dt.date, str], pd.DataFrame]] = {
    "tushare": fetch_tushare_minutes,
    "jqdata": fetch_jqdata_minutes,
    "rqdata": fetch_rqdata_minutes,
}


def fetch_tushare_event(dataset: str, trade_date: dt.date) -> pd.DataFrame:
    """Fetch a single complete-session Tushare event table."""

    if dataset not in EVENT_DATASETS:
        raise RichDataError(f"unsupported Tushare event dataset: {dataset}")
    ts = _import_tushare()
    pro = ts.pro_api()
    method = {
        "moneyflow": pro.moneyflow,
        "limit-list": pro.limit_list_d,
        "top-list": pro.top_list,
    }[dataset]
    result = method(trade_date=trade_date.strftime("%Y%m%d"))
    if result is None:
        return pd.DataFrame()
    return result.copy()


def validate_range(start: dt.date, end: dt.date, allow_large: bool, unit_count: int = 1) -> None:
    """Guard against an accidental multi-year paid-data request."""

    if end < start:
        raise RichDataError("end date precedes start date")
    completed = latest_completed_session_date()
    if end > completed:
        raise RichDataError(
            f"end date {end.isoformat()} is not a completed A-share session; use {completed.isoformat()} or earlier"
        )
    work_units = len(pd.bdate_range(start, end)) * unit_count
    if work_units > 100 and not allow_large:
        raise RichDataError(
            f"request covers {work_units} symbol-sessions; pass --allow-large only after a small acceptance run succeeds"
        )


def frame_digest(frame: pd.DataFrame) -> str:
    """Return a stable digest for a stored data frame."""

    content = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def file_digest(path: Path) -> str:
    """Return a SHA-256 digest for an immutable manifest or specification."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_record_path(value: str | Path) -> Path:
    """Resolve a manifest-stored repository-relative path safely."""

    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def load_json_record(path: Path, *, kind: str | None = None) -> dict[str, Any]:
    """Load one JSON record and optionally enforce its immutable kind."""

    path = path.expanduser().resolve()
    if not path.exists():
        raise RichDataError(f"JSON record does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RichDataError(f"JSON record is invalid: {path}") from exc
    if not isinstance(payload, dict):
        raise RichDataError(f"JSON record must contain an object: {path}")
    if kind is not None and payload.get("kind") != kind:
        raise RichDataError(f"expected {kind!r}, got {payload.get('kind')!r}: {path}")
    return payload


def atomic_write_frame(frame: pd.DataFrame, destination: Path) -> None:
    """Write one Parquet snapshot atomically."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".parquet", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        frame.to_parquet(temporary, index=False)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(payload: dict[str, Any], destination: Path) -> None:
    """Write a manifest atomically."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".json", mode="w", encoding="utf-8", delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def new_run_id(prefix: str) -> str:
    """Create a chronological, collision-resistant snapshot identifier."""

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{now}_{prefix}_{uuid.uuid4().hex[:8]}"


def manifest_path(path: Path) -> str:
    """Use repository-relative paths in production and absolute paths in tests."""

    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def write_minute_snapshot(
    provider: str,
    frequency: str,
    start: dt.date,
    end: dt.date,
    rows_by_code: dict[str, pd.DataFrame],
    acceptance_by_code: dict[str, dict[str, Any]] | None = None,
) -> Path:
    """Persist one immutable minute-data snapshot and its complete manifest."""

    run_id = new_run_id(f"{provider}_{frequency}")
    run_root = RAW_ROOT / provider / "minutes" / frequency / "snapshots" / run_id
    files: list[dict[str, Any]] = []
    for code, frame in rows_by_code.items():
        destination = run_root / f"{qlib_symbol(code).lower()}.parquet"
        atomic_write_frame(frame, destination)
        files.append(
            {
                "code": code,
                "symbol": qlib_symbol(code),
                "path": manifest_path(destination),
                "rows": int(len(frame)),
                "sha256": frame_digest(frame),
                "daily_summary": minute_daily_summary(frame),
                "acceptance": (acceptance_by_code or {}).get(code),
            }
        )
    manifest = {
        "kind": "a_share_rich_data_snapshot",
        "dataset": "minutes",
        "provider": provider,
        "frequency": frequency,
        "prices": "raw_unadjusted",
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_id": run_id,
        "files": files,
        "acceptance_status": (
            "automatic_checks_passed_pending_time_alignment"
            if acceptance_by_code and all(report["status"].startswith("automatic_checks_passed") for report in acceptance_by_code.values())
            else "not_run" if acceptance_by_code is None else "automatic_checks_failed"
        ),
    }
    run_manifest_path = RUNS_ROOT / f"{run_id}.json"
    atomic_write_json(manifest, run_manifest_path)
    return run_manifest_path


def expected_minute_times(bar_label: str) -> tuple[dt.time, ...]:
    """Return the exact 240 regular-session timestamps for one label convention."""

    if bar_label not in {"start", "end"}:
        raise RichDataError("bar label must be 'start' or 'end'")
    anchor = pd.Timestamp("2000-01-03")
    bar_ends = pd.DatetimeIndex(
        [
            *pd.date_range(anchor + pd.Timedelta(hours=9, minutes=31), periods=120, freq="1min"),
            *pd.date_range(anchor + pd.Timedelta(hours=13, minutes=1), periods=120, freq="1min"),
        ]
    )
    timestamps = bar_ends - (pd.Timedelta(minutes=1) if bar_label == "start" else pd.Timedelta(0))
    return tuple(value.time() for value in timestamps)


def load_snapshot_frame(file_record: dict[str, Any]) -> pd.DataFrame:
    """Read and fingerprint one immutable snapshot file."""

    path_value = file_record.get("path")
    if not path_value:
        raise RichDataError("snapshot file record has no path")
    path = resolve_record_path(str(path_value))
    if not path.exists():
        raise RichDataError(f"snapshot data file does not exist: {path}")
    frame = pd.read_parquet(path)
    expected = str(file_record.get("sha256") or "")
    observed = frame_digest(frame)
    if not expected or observed != expected:
        raise RichDataError(f"snapshot data fingerprint mismatch: {path}")
    return frame


def confirmation_volume_units(snapshot: dict[str, Any]) -> set[str]:
    """Collect only volume units inferred by passed daily reconciliation rows."""

    units: set[str] = set()
    for file_record in snapshot.get("files") or []:
        acceptance = file_record.get("acceptance") or {}
        reconciliation = acceptance.get("daily_reconciliation") or {}
        for day in reconciliation.get("days") or []:
            if day.get("status") == "passed" and day.get("inferred_volume_unit") in {"shares", "lots"}:
                units.add(str(day["inferred_volume_unit"]))
    return units


def confirm_minute_alignment(
    snapshot_path: Path,
    *,
    bar_label: str,
    volume_unit: str,
    reviewed_boundaries: bool,
    output: Path | None = None,
) -> Path:
    """Write an append-only provider alignment confirmation.

    The source snapshot remains immutable.  This record binds the explicit
    operator review to its manifest fingerprint and can later authorize bulk
    snapshots from only the same provider/frequency contract.
    """

    if not reviewed_boundaries:
        raise RichDataError("pass --reviewed-boundaries only after checking the first and last minute labels")
    if bar_label not in {"start", "end"}:
        raise RichDataError("bar label must be 'start' or 'end'")
    if volume_unit not in {"shares", "lots"}:
        raise RichDataError("volume unit must be 'shares' or 'lots'")
    snapshot_path = snapshot_path.expanduser().resolve()
    snapshot = load_json_record(snapshot_path, kind="a_share_rich_data_snapshot")
    if snapshot.get("dataset") != "minutes" or snapshot.get("frequency") != "1m":
        raise RichDataError("minute alignment confirmation requires a 1m minute snapshot")
    if snapshot.get("acceptance_status") != "automatic_checks_passed_pending_time_alignment":
        raise RichDataError("minute snapshot has not passed automatic acceptance checks")
    files = list(snapshot.get("files") or [])
    if not files:
        raise RichDataError("minute snapshot contains no files")

    expected_times = expected_minute_times(bar_label)
    complete_session_evidence: list[dict[str, Any]] = []
    for file_record in files:
        frame = load_snapshot_frame(file_record)
        if frame.empty:
            continue
        required = {"datetime", "symbol", "open", "high", "low", "close", "volume", "amount", "provider"}
        if missing := sorted(required - set(frame.columns)):
            raise RichDataError("minute snapshot file is missing canonical columns: " + ", ".join(missing))
        timestamps = pd.to_datetime(frame["datetime"], errors="coerce")
        if timestamps.isna().any():
            raise RichDataError("minute snapshot contains an invalid timestamp")
        providers = set(frame["provider"].dropna().astype(str))
        if providers != {str(snapshot["provider"])}:
            raise RichDataError(
                f"minute snapshot contains an unexpected provider: {sorted(providers)}"
            )
        work = frame.assign(_datetime=timestamps, _trade_date=timestamps.dt.normalize())
        for trade_date, group in work.groupby("_trade_date", sort=True):
            observed_times = tuple(group.sort_values("_datetime")["_datetime"].dt.time)
            if len(observed_times) == MINUTE_FEATURE_EXPECTED_BARS:
                if observed_times != expected_times:
                    raise RichDataError(
                        f"declared {bar_label}-label convention conflicts with a 240-bar session on "
                        f"{pd.Timestamp(trade_date).date().isoformat()}"
                    )
                complete_session_evidence.append(
                    {
                        "symbol": str(group["symbol"].iloc[0]),
                        "trade_date": pd.Timestamp(trade_date).date().isoformat(),
                        "first_bar": group.sort_values("_datetime")["_datetime"].iloc[0].isoformat(),
                        "last_bar": group.sort_values("_datetime")["_datetime"].iloc[-1].isoformat(),
                    }
                )
    if not complete_session_evidence:
        raise RichDataError("alignment confirmation needs at least one exact 240-bar session as boundary evidence")
    inferred_units = confirmation_volume_units(snapshot)
    if inferred_units != {volume_unit}:
        raise RichDataError(
            "declared volume unit conflicts with automatic reconciliation: "
            f"declared={volume_unit}, inferred={sorted(inferred_units)}"
        )

    run_id = new_run_id(f"{snapshot['provider']}_1m_alignment")
    record = {
        "schema_version": 1,
        "kind": "a_share_minute_alignment_confirmation",
        "status": "passed_for_feature_research",
        "run_id": run_id,
        "confirmed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": snapshot["provider"],
        "frequency": "1m",
        "bar_timestamp_label": bar_label,
        "normalization_to_bar_end": "add_one_minute" if bar_label == "start" else "identity",
        "volume_unit": volume_unit,
        "reviewed_boundaries": True,
        "complete_session_evidence": complete_session_evidence,
        "source_acceptance_snapshot": {
            "path": manifest_path(snapshot_path),
            "sha256": file_digest(snapshot_path),
            "run_id": snapshot.get("run_id"),
        },
        "forward_return_fields_read": False,
        "limitations": [
            "This confirms timestamp and volume-unit semantics only; it does not validate a factor or strategy.",
            "Missing or halted minute bars remain missing and must never be zero-filled.",
        ],
    }
    destination = output.expanduser().resolve() if output is not None else ALIGNMENTS_ROOT / f"{run_id}.json"
    if destination.exists():
        raise RichDataError(f"alignment confirmation already exists: {destination}")
    atomic_write_json(record, destination)
    return destination


def load_minute_factor_spec(path: Path = DEFAULT_MINUTE_FACTOR_SPEC) -> dict[str, Any]:
    """Load the frozen minute-factor preregistration and enforce its catalog."""

    path = path.expanduser().resolve()
    spec = load_json_record(path, kind="a_share_minute_factor_preregistration")
    features = list(spec.get("features") or [])
    names = tuple(str(item.get("name")) for item in features if isinstance(item, dict))
    directions = tuple(
        str(item.get("diagnostic_direction")) for item in features if isinstance(item, dict)
    )
    minute_contract = spec.get("minute_contract") or {}
    holding_protocol = spec.get("holding_protocol") or {}
    contract_ok = (
        spec.get("version") == 1
        and spec.get("status") == "frozen_before_minute_data_observed"
        and names == MINUTE_FEATURE_NAMES
        and directions == MINUTE_FEATURE_DIRECTIONS
        and minute_contract.get("frequency") == "1m"
        and minute_contract.get("prices") == "raw_unadjusted"
        and minute_contract.get("timestamp_normalized_to") == "bar_end"
        and minute_contract.get("complete_regular_session_required") is True
        and minute_contract.get("expected_regular_session_bars") == MINUTE_FEATURE_EXPECTED_BARS
        and holding_protocol.get("holding_period_trading_days") == 3
        and holding_protocol.get("non_overlapping_cohorts") is True
        and holding_protocol.get("topk") == 3
        and holding_protocol.get("open_cost") == 0.00012
        and holding_protocol.get("close_cost") == 0.00062
    )
    if not contract_ok:
        raise RichDataError("minute factor preregistration does not match the frozen v1 feature catalog")
    if (
        spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "minute factor preregistration must exclude forward returns and promotion"
        )
    return spec


def previous_comparable_close_map(symbol: str) -> dict[pd.Timestamp, float]:
    """Express the prior close on each current session's raw-price scale.

    ``raw_close[t-1]`` alone creates a false gap on an ex-rights date.  The
    accepted daily factor lets us carry yesterday's adjusted close onto
    today's raw scale as ``raw_close[t-1] * factor[t-1] / factor[t]``.
    """

    path = DAILY_RAW_DIR / f"{str(symbol).lower()}.parquet"
    if not path.exists():
        raise RichDataError(f"local daily raw history is missing for minute feature construction: {path}")
    daily = pd.read_parquet(path)
    required = {"date", "raw_close", "factor", "price_basis"}
    if missing := sorted(required - set(daily.columns)):
        raise RichDataError("local daily history is missing raw-price columns: " + ", ".join(missing))
    bases = set(daily["price_basis"].dropna().astype(str))
    if bases != {REQUIRED_DAILY_PRICE_BASIS}:
        raise RichDataError(f"local daily history has an unaccepted price basis for {symbol}: {sorted(bases)}")
    work = daily[["date", "raw_close", "factor"]].copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce").dt.normalize()
    work["raw_close"] = pd.to_numeric(work["raw_close"], errors="coerce")
    work["factor"] = pd.to_numeric(work["factor"], errors="coerce")
    work = work.dropna().sort_values("date", kind="stable").drop_duplicates("date", keep="last")
    work["previous_comparable_close"] = (
        work["raw_close"].shift(1) * work["factor"].shift(1) / work["factor"]
    )
    return {
        pd.Timestamp(row.date): float(row.previous_comparable_close)
        for row in work.itertuples(index=False)
        if pd.notna(row.previous_comparable_close)
        and float(row.previous_comparable_close) > 0.0
    }


def minute_feature_frame(
    frame: pd.DataFrame,
    *,
    bar_label: str,
    previous_closes: dict[str, dict[pd.Timestamp, float]],
) -> pd.DataFrame:
    """Construct the five frozen close-known minute features without returns."""

    required = {"datetime", "symbol", "open", "high", "low", "close", "volume", "amount", "provider"}
    if missing := sorted(required - set(frame.columns)):
        raise RichDataError("minute feature input is missing columns: " + ", ".join(missing))
    if bar_label not in {"start", "end"}:
        raise RichDataError("bar label must be 'start' or 'end'")
    work = frame.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    if work["datetime"].isna().any():
        raise RichDataError("minute feature input contains invalid timestamps")
    work["bar_end"] = work["datetime"] + (
        pd.Timedelta(minutes=1) if bar_label == "start" else pd.Timedelta(0)
    )
    numeric_columns = ["open", "high", "low", "close", "volume", "amount"]
    for column in numeric_columns:
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if not np.isfinite(work[numeric_columns].to_numpy(dtype=float)).all():
        raise RichDataError("minute feature input contains non-finite OHLCV/amount values")
    if (work[["open", "high", "low", "close"]] <= 0.0).any().any():
        raise RichDataError("minute feature input contains non-positive prices")
    if (work[["volume", "amount"]] < 0.0).any().any():
        raise RichDataError("minute feature input contains negative volume or amount")
    work["trade_date"] = work["bar_end"].dt.normalize()
    expected_bar_ends = expected_minute_times("end")
    rows: list[dict[str, Any]] = []
    for (symbol, trade_date), group in work.groupby(["symbol", "trade_date"], sort=True):
        group = group.sort_values("bar_end", kind="stable")
        observed_bar_ends = tuple(group["bar_end"].dt.time)
        complete = (
            len(group) == MINUTE_FEATURE_EXPECTED_BARS
            and observed_bar_ends == expected_bar_ends
        )
        values = {name: float("nan") for name in MINUTE_FEATURE_NAMES}
        opening_gap_return = float("nan")
        if complete:
            day_open = float(group["open"].iloc[0])
            day_close = float(group["close"].iloc[-1])
            anchor = group.loc[group["bar_end"].dt.time == dt.time(14, 30)]
            late = group.loc[group["bar_end"].dt.time > dt.time(14, 30)]
            total_amount = float(group["amount"].sum())
            total_volume = float(group["volume"].sum())
            late_amount = float(late["amount"].sum())
            late_volume = float(late["volume"].sum())
            if len(anchor) == 1 and len(late) == 30 and float(anchor["close"].iloc[0]) > 0.0:
                values["late_return_30m"] = day_close / float(anchor["close"].iloc[0]) - 1.0
            if total_amount > 0.0:
                values["late_amount_share_30m"] = late_amount / total_amount
            if total_amount > 0.0 and total_volume > 0.0 and late_amount > 0.0 and late_volume > 0.0:
                values["late_vwap_to_day_vwap_30m"] = (late_amount / late_volume) / (
                    total_amount / total_volume
                ) - 1.0
            previous_close = previous_closes.get(str(symbol), {}).get(pd.Timestamp(trade_date))
            if previous_close is not None and previous_close > 0.0 and day_open > 0.0:
                opening_gap_return = day_open / previous_close - 1.0
                values["opening_gap_digestion"] = -float(np.sign(opening_gap_return)) * (
                    day_close / day_open - 1.0
                )
            log_returns = np.log(pd.to_numeric(group["close"], errors="coerce")).diff().dropna()
            if len(log_returns) == MINUTE_FEATURE_EXPECTED_BARS - 1 and np.isfinite(log_returns).all():
                values["intraday_realized_volatility"] = float(np.sqrt(np.square(log_returns).sum()))
        eligible = complete and all(np.isfinite(values[name]) for name in MINUTE_FEATURE_NAMES)
        rows.append(
            {
                "symbol": str(symbol),
                "trade_date": pd.Timestamp(trade_date),
                "provider": str(group["provider"].iloc[0]),
                "bar_timestamp_label": bar_label,
                "minute_bars": int(len(group)),
                "complete_regular_session": bool(complete),
                "minute_feature_eligible": bool(eligible),
                "opening_gap_return": opening_gap_return,
                **values,
            }
        )
    return pd.DataFrame(rows).sort_values(["trade_date", "symbol"], kind="stable").reset_index(drop=True)


def build_minute_features(
    snapshot_path: Path,
    alignment_path: Path,
    *,
    factor_spec_path: Path = DEFAULT_MINUTE_FACTOR_SPEC,
    output: Path | None = None,
) -> Path:
    """Build frozen minute features only after provider semantics are confirmed."""

    snapshot_path = snapshot_path.expanduser().resolve()
    alignment_path = alignment_path.expanduser().resolve()
    factor_spec_path = factor_spec_path.expanduser().resolve()
    snapshot = load_json_record(snapshot_path, kind="a_share_rich_data_snapshot")
    alignment = load_json_record(alignment_path, kind="a_share_minute_alignment_confirmation")
    spec = load_minute_factor_spec(factor_spec_path)
    if snapshot.get("dataset") != "minutes" or snapshot.get("frequency") != "1m":
        raise RichDataError("minute feature construction requires a 1m minute snapshot")
    if snapshot.get("prices") != "raw_unadjusted":
        raise RichDataError("minute feature construction requires raw unadjusted prices")
    if alignment.get("status") != "passed_for_feature_research":
        raise RichDataError("minute alignment has not passed for feature research")
    if snapshot.get("provider") != alignment.get("provider") or snapshot.get("frequency") != alignment.get("frequency"):
        raise RichDataError("minute snapshot provider/frequency does not match the alignment confirmation")
    source_acceptance = alignment.get("source_acceptance_snapshot") or {}
    source_acceptance_path = resolve_record_path(str(source_acceptance.get("path") or ""))
    if not source_acceptance.get("path") or not source_acceptance_path.exists():
        raise RichDataError("alignment confirmation has no readable source acceptance snapshot")
    if file_digest(source_acceptance_path) != source_acceptance.get("sha256"):
        raise RichDataError("alignment confirmation source acceptance fingerprint mismatch")
    acceptance_snapshot = load_json_record(
        source_acceptance_path, kind="a_share_rich_data_snapshot"
    )
    if (
        acceptance_snapshot.get("acceptance_status")
        != "automatic_checks_passed_pending_time_alignment"
        or acceptance_snapshot.get("provider") != alignment.get("provider")
        or acceptance_snapshot.get("frequency") != alignment.get("frequency")
    ):
        raise RichDataError("alignment confirmation is not bound to a compatible accepted snapshot")
    files = list(snapshot.get("files") or [])
    if not files:
        raise RichDataError("minute snapshot contains no files")

    previous_closes: dict[str, dict[pd.Timestamp, float]] = {}
    feature_frames: list[pd.DataFrame] = []
    for file_record in files:
        frame = load_snapshot_frame(file_record)
        if frame.empty:
            continue
        providers = frame["provider"].dropna().astype(str).unique().tolist()
        if providers != [str(snapshot["provider"])]:
            raise RichDataError("minute snapshot file contains a mixed or unexpected provider")
        symbols = frame["symbol"].dropna().astype(str).unique().tolist()
        if len(symbols) != 1:
            raise RichDataError("each minute snapshot file must contain exactly one canonical symbol")
        symbol = symbols[0]
        previous_closes.setdefault(symbol, previous_comparable_close_map(symbol))
        feature_frames.append(
            minute_feature_frame(
                frame,
                bar_label=str(alignment["bar_timestamp_label"]),
                previous_closes=previous_closes,
            )
        )
    if not feature_frames:
        raise RichDataError("minute snapshot contains no bars for feature construction")
    features = pd.concat(feature_frames, ignore_index=True).sort_values(
        ["trade_date", "symbol"], kind="stable"
    )
    eligible_rows = int(features["minute_feature_eligible"].sum())
    if eligible_rows == 0:
        raise RichDataError("minute snapshot has no complete feature-eligible sessions; missing bars are not filled")

    run_id = new_run_id(f"{snapshot['provider']}_minute_features_v1")
    feature_path = (
        output.expanduser().resolve()
        if output is not None
        else DERIVED_ROOT / "minute_features" / "v1" / run_id / "features.parquet"
    )
    if feature_path.exists():
        raise RichDataError(f"minute feature output already exists: {feature_path}")
    atomic_write_frame(features, feature_path)
    manifest = {
        "schema_version": 1,
        "kind": "a_share_minute_feature_run",
        "status": "features_built_research_only",
        "run_id": run_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": snapshot["provider"],
        "frequency": "1m",
        "feature_spec": {
            "path": manifest_path(factor_spec_path),
            "sha256": file_digest(factor_spec_path),
            "version": spec.get("version"),
            "features": spec["features"],
        },
        "source_snapshot": {
            "path": manifest_path(snapshot_path),
            "sha256": file_digest(snapshot_path),
            "run_id": snapshot.get("run_id"),
            "prices": snapshot.get("prices"),
        },
        "alignment_confirmation": {
            "path": manifest_path(alignment_path),
            "sha256": file_digest(alignment_path),
            "run_id": alignment.get("run_id"),
            "bar_timestamp_label": alignment.get("bar_timestamp_label"),
            "volume_unit": alignment.get("volume_unit"),
        },
        "output": {
            "path": manifest_path(feature_path),
            "sha256": frame_digest(features),
            "rows": int(len(features)),
            "eligible_rows": eligible_rows,
            "incomplete_session_rows": int((~features["complete_regular_session"]).sum()),
            "calendar_start": pd.Timestamp(features["trade_date"].min()).date().isoformat(),
            "calendar_end": pd.Timestamp(features["trade_date"].max()).date().isoformat(),
        },
        "forward_return_fields_read": False,
        "future_price_fields_read": False,
        "selection_or_promotion_allowed": False,
    }
    destination = FEATURE_RUNS_ROOT / f"{run_id}.json"
    atomic_write_json(manifest, destination)
    return destination


def sync_minutes(
    provider: str,
    codes: list[str],
    start: dt.date,
    end: dt.date,
    frequency: str,
    allow_large: bool,
    acceptance: bool = False,
) -> Path:
    """Download and validate explicit-symbol minute bars into one snapshot."""

    if frequency not in {"1m", "5m", "15m", "30m", "60m"}:
        raise RichDataError("frequency must be one of 1m, 5m, 15m, 30m, 60m")
    require_provider(provider)
    validate_range(start, end, allow_large=allow_large, unit_count=len(codes))
    fetcher = MINUTE_FETCHERS[provider]
    rows_by_code: dict[str, pd.DataFrame] = {}
    acceptance_by_code: dict[str, dict[str, Any]] = {}
    for code in codes:
        raw = fetcher(code, start, end, frequency)
        rows_by_code[code] = canonicalize_minute_bars(raw, provider, code, start, end)
        if acceptance:
            acceptance_by_code[code] = minute_acceptance_report(rows_by_code[code])
    return write_minute_snapshot(
        provider,
        frequency,
        start,
        end,
        rows_by_code,
        acceptance_by_code if acceptance else None,
    )


def sync_tushare_events(
    datasets: list[str], start: dt.date, end: dt.date, allow_large: bool
) -> Path:
    """Download one or more Tushare end-of-day event tables into a snapshot."""

    require_provider("tushare")
    unknown = sorted(set(datasets) - set(EVENT_DATASETS))
    if unknown:
        raise RichDataError(f"unsupported event dataset(s): {', '.join(unknown)}")
    validate_range(start, end, allow_large=allow_large, unit_count=len(datasets))
    run_id = new_run_id("tushare_events")
    run_root = RAW_ROOT / "tushare" / "events" / "snapshots" / run_id
    files: list[dict[str, Any]] = []
    for trade_date in pd.bdate_range(start, end):
        date = trade_date.date()
        for dataset in datasets:
            frame = fetch_tushare_event(dataset, date)
            frame = frame.copy()
            frame["provider"] = "tushare"
            frame["dataset"] = dataset
            frame["retrieved_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            destination = run_root / dataset / f"{date.isoformat()}.parquet"
            atomic_write_frame(frame, destination)
            files.append(
                {
                    "dataset": dataset,
                    "trade_date": date.isoformat(),
                    "path": manifest_path(destination),
                    "rows": int(len(frame)),
                    "sha256": frame_digest(frame),
                }
            )
    manifest = {
        "kind": "a_share_rich_data_snapshot",
        "dataset": "tushare_events",
        "provider": "tushare",
        "requested_start": start.isoformat(),
        "requested_end": end.isoformat(),
        "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_id": run_id,
        "files": files,
        "acceptance_status": "pending_factor_time_alignment",
    }
    run_manifest_path = RUNS_ROOT / f"{run_id}.json"
    atomic_write_json(manifest, run_manifest_path)
    return run_manifest_path


def status_payload() -> dict[str, Any]:
    """Return safe machine-readable readiness information."""

    manifests = sorted(RUNS_ROOT.glob("*.json")) if RUNS_ROOT.exists() else []
    alignments = sorted(ALIGNMENTS_ROOT.glob("*.json")) if ALIGNMENTS_ROOT.exists() else []
    feature_runs = sorted(FEATURE_RUNS_ROOT.glob("*.json")) if FEATURE_RUNS_ROOT.exists() else []
    return {
        "repository": str(REPO_ROOT),
        "data_root": str(DATA_ROOT),
        "providers": [asdict(provider_availability(provider)) | {"ready": provider_availability(provider).ready} for provider in PROVIDER_REQUIREMENTS],
        "snapshot_manifest_count": len(manifests),
        "latest_snapshot_manifest": str(manifests[-1]) if manifests else None,
        "alignment_confirmation_count": len(alignments),
        "latest_alignment_confirmation": str(alignments[-1]) if alignments else None,
        "minute_feature_run_count": len(feature_runs),
        "latest_minute_feature_run": str(feature_runs[-1]) if feature_runs else None,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="show safe provider readiness and stored snapshots")

    minute = subparsers.add_parser("sync-minutes", help="download explicit-symbol minute bars")
    minute.add_argument("--provider", choices=sorted(MINUTE_FETCHERS), required=True)
    minute.add_argument("--symbols", type=parse_symbols, required=True, help="comma-separated six-digit A-share codes")
    minute.add_argument("--start", type=parse_date, required=True)
    minute.add_argument("--end", type=parse_date, required=True)
    minute.add_argument("--frequency", default="1m")
    minute.add_argument("--allow-large", action="store_true", help="confirm a request above 100 symbol-sessions")

    acceptance = subparsers.add_parser("acceptance", help="run a small minute-data acceptance download")
    acceptance.add_argument("--provider", choices=sorted(MINUTE_FETCHERS), required=True)
    acceptance.add_argument("--date", type=parse_date, default=latest_completed_session_date())
    acceptance.add_argument("--symbols", type=parse_symbols, default=list(DEFAULT_ACCEPTANCE_SYMBOLS))
    acceptance.add_argument("--frequency", default="1m")

    events = subparsers.add_parser("sync-tushare-events", help="download Tushare event tables after the close")
    events.add_argument("--datasets", default="moneyflow,limit-list,top-list")
    events.add_argument("--start", type=parse_date, required=True)
    events.add_argument("--end", type=parse_date, required=True)
    events.add_argument("--allow-large", action="store_true", help="confirm a request above 100 table-sessions")

    alignment = subparsers.add_parser(
        "confirm-minute-alignment",
        help="write a separate timestamp/volume confirmation for an accepted 1m snapshot",
    )
    alignment.add_argument("--manifest", type=Path, required=True)
    alignment.add_argument("--bar-label", choices=("start", "end"), required=True)
    alignment.add_argument("--volume-unit", choices=("shares", "lots"), required=True)
    alignment.add_argument(
        "--reviewed-boundaries",
        action="store_true",
        help="confirm the acceptance snapshot's first/last bars were reviewed",
    )
    alignment.add_argument("--output", type=Path)

    features = subparsers.add_parser(
        "build-minute-features",
        help="build the frozen close-known v1 minute features from a confirmed 1m snapshot",
    )
    features.add_argument("--manifest", type=Path, required=True)
    features.add_argument("--alignment", type=Path, required=True)
    features.add_argument("--factor-spec", type=Path, default=DEFAULT_MINUTE_FACTOR_SPEC)
    features.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the rich-data CLI."""

    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            print(json.dumps(status_payload(), ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        if args.command == "sync-minutes":
            manifest = sync_minutes(
                args.provider, args.symbols, args.start, args.end, args.frequency, args.allow_large
            )
        elif args.command == "acceptance":
            manifest = sync_minutes(args.provider, args.symbols, args.date, args.date, args.frequency, False, acceptance=True)
        elif args.command == "sync-tushare-events":
            datasets = [item.strip() for item in args.datasets.split(",") if item.strip()]
            manifest = sync_tushare_events(datasets, args.start, args.end, args.allow_large)
        elif args.command == "confirm-minute-alignment":
            manifest = confirm_minute_alignment(
                args.manifest,
                bar_label=args.bar_label,
                volume_unit=args.volume_unit,
                reviewed_boundaries=args.reviewed_boundaries,
                output=args.output,
            )
        elif args.command == "build-minute-features":
            manifest = build_minute_features(
                args.manifest,
                args.alignment,
                factor_spec_path=args.factor_spec,
                output=args.output,
            )
        else:  # pragma: no cover - argparse enforces the known subcommands.
            raise RichDataError(f"unknown command: {args.command}")
    except RichDataError as exc:
        print(f"error: {exc}")
        return 2
    command_status = {
        "confirm-minute-alignment": "stored_alignment_confirmation",
        "build-minute-features": "stored_research_features",
    }.get(args.command, "stored_pending_acceptance")
    print(json.dumps({"manifest": str(manifest), "status": command_status}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
