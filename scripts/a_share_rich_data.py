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

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data"
RAW_ROOT = DATA_ROOT / "raw" / "a_share" / "rich"
METADATA_ROOT = DATA_ROOT / "metadata" / "rich_data"
RUNS_ROOT = METADATA_ROOT / "runs"

DEFAULT_ACCEPTANCE_SYMBOLS = ("600519", "000001", "300750", "688981")
PROVIDER_REQUIREMENTS = {
    "tushare": {"package": "tushare", "environment": ("TUSHARE_TOKEN",)},
    "jqdata": {"package": "jqdatasdk", "environment": ("JQDATA_USERNAME", "JQDATA_PASSWORD")},
    "rqdata": {"package": "rqdatac", "environment": ("RQDATA_USERNAME", "RQDATA_PASSWORD")},
}
EVENT_DATASETS = ("moneyflow", "limit-list", "top-list")


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
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
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
        "acceptance_status": "pending_daily_reconciliation",
    }
    run_manifest_path = RUNS_ROOT / f"{run_id}.json"
    atomic_write_json(manifest, run_manifest_path)
    return run_manifest_path


def sync_minutes(
    provider: str,
    codes: list[str],
    start: dt.date,
    end: dt.date,
    frequency: str,
    allow_large: bool,
) -> Path:
    """Download and validate explicit-symbol minute bars into one snapshot."""

    if frequency not in {"1m", "5m", "15m", "30m", "60m"}:
        raise RichDataError("frequency must be one of 1m, 5m, 15m, 30m, 60m")
    require_provider(provider)
    validate_range(start, end, allow_large=allow_large, unit_count=len(codes))
    fetcher = MINUTE_FETCHERS[provider]
    rows_by_code: dict[str, pd.DataFrame] = {}
    for code in codes:
        raw = fetcher(code, start, end, frequency)
        rows_by_code[code] = canonicalize_minute_bars(raw, provider, code, start, end)
    return write_minute_snapshot(provider, frequency, start, end, rows_by_code)


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
    return {
        "repository": str(REPO_ROOT),
        "data_root": str(DATA_ROOT),
        "providers": [asdict(provider_availability(provider)) | {"ready": provider_availability(provider).ready} for provider in PROVIDER_REQUIREMENTS],
        "snapshot_manifest_count": len(manifests),
        "latest_snapshot_manifest": str(manifests[-1]) if manifests else None,
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
            manifest = sync_minutes(args.provider, args.symbols, args.date, args.date, args.frequency, False)
        elif args.command == "sync-tushare-events":
            datasets = [item.strip() for item in args.datasets.split(",") if item.strip()]
            manifest = sync_tushare_events(datasets, args.start, args.end, args.allow_large)
        else:  # pragma: no cover - argparse enforces the known subcommands.
            raise RichDataError(f"unknown command: {args.command}")
    except RichDataError as exc:
        print(f"error: {exc}")
        return 2
    print(json.dumps({"manifest": str(manifest), "status": "stored_pending_acceptance"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
