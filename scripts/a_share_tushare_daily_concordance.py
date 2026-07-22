#!/usr/bin/env python3
"""Download Tushare raw daily bars and compare them with the BaoStock basis.

This is an independent provider-concordance snapshot.  It never overwrites the
repository's accepted BaoStock daily files or materializes a new Qlib basis.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = REPO_ROOT / "docs" / "a_share_tushare_daily_concordance_protocol.json"
PROTOCOL_SHA256 = "acf72e28283405aee93e64f68d63470380d65fa8ccc64c588bfdf203f3914297"
REPAIR_PATH = (
    REPO_ROOT / "docs" / "a_share_tushare_daily_concordance_implementation_repair.json"
)
REPAIR_SHA256 = "c673c0b4405a7cf53535e0d8915b3c2c9bf6711d40fcf9ac8e5d1689190efe80"
CALENDAR_PATH = REPO_ROOT / "data" / "qlib" / "cn_a_share" / "calendars" / "day.txt"
REFERENCE_DAILY_ROOT = REPO_ROOT / "data" / "raw" / "a_share" / "daily"
REFERENCE_PRICE_BASIS = "close_known_raw_pct_chg_chain_v1"
START_DATE = dt.date(2019, 1, 1)
END_DATE = dt.date(2025, 12, 31)
ACCEPTANCE_DATE = dt.date(2025, 12, 31)
FIELDS = (
    "ts_code",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "change",
    "pct_chg",
    "vol",
    "amount",
)
NUMERIC_FIELDS = FIELDS[2:]
COMPARISON_SOURCE_FIELDS = ("open", "high", "low", "close", "vol", "amount")
AUXILIARY_SOURCE_FIELDS = ("pre_close", "change", "pct_chg")
REPRESENTATIVE_CODES = frozenset(
    {"600519.SH", "000001.SZ", "300750.SZ", "688981.SH"}
)
ERROR_FIELDS = ("open", "high", "low", "close", "volume", "amount")
ERROR_BANDS = (0.0, 0.0005, 0.002, 0.005, 0.01)
CODE_PATTERN = re.compile(r"^\d{6}\.(?:SH|SZ|BJ)$")


class DailyConcordanceError(RuntimeError):
    """Raised when a frozen source, storage, or comparison contract fails."""


def file_digest(path: Path) -> str:
    path = Path(path)
    digest = hashlib.sha256()
    if path.suffix.lower() in {
        ".csv",
        ".json",
        ".md",
        ".rst",
        ".tsv",
        ".txt",
        ".yaml",
        ".yml",
    }:
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        return digest.hexdigest()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
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


def validate_protocol() -> dict[str, Any]:
    if file_digest(PROTOCOL_PATH) != PROTOCOL_SHA256:
        raise DailyConcordanceError(f"daily concordance protocol changed: {PROTOCOL_PATH}")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if (
        protocol.get("kind") != "a_share_tushare_daily_concordance_protocol"
        or (protocol.get("source") or {}).get("interface") != "daily"
        or (protocol.get("research_boundary") or {}).get("forward_return_fields_read")
        is not False
    ):
        raise DailyConcordanceError("daily concordance protocol identity is rejected")
    if not REPAIR_PATH.is_file() or file_digest(REPAIR_PATH) != REPAIR_SHA256:
        raise DailyConcordanceError(
            f"daily concordance implementation repair changed: {REPAIR_PATH}"
        )
    return protocol


def load_calendar() -> pd.DatetimeIndex:
    values = pd.to_datetime(
        CALENDAR_PATH.read_text(encoding="utf-8").splitlines(), errors="coerce"
    )
    if pd.isna(values).any():
        raise DailyConcordanceError("local calendar contains an invalid date")
    calendar = pd.DatetimeIndex(values).normalize().unique().sort_values()
    selected = calendar[
        (calendar >= pd.Timestamp(START_DATE)) & (calendar <= pd.Timestamp(END_DATE))
    ]
    if (
        len(selected) != 1699
        or selected[0] != pd.Timestamp("2019-01-02")
        or selected[-1] != pd.Timestamp("2025-12-31")
    ):
        raise DailyConcordanceError("local 2019-2025 calendar fingerprint changed")
    return selected


def symbol_from_ts_code(values: pd.Series) -> pd.Series:
    codes = values.astype(str).str.upper()
    suffix = codes.str[-2:]
    prefix = suffix.map({"SH": "SH", "SZ": "SZ", "BJ": "BJ"})
    return prefix + codes.str[:6]


def canonicalize_tushare_daily(
    raw: pd.DataFrame,
    trade_date: dt.date,
    *,
    require_representatives: bool = False,
) -> pd.DataFrame:
    """Validate one exact-date provider response without changing its units."""

    if raw.empty:
        raise DailyConcordanceError(f"Tushare daily returned no rows for {trade_date}")
    if len(raw) >= 6000:
        raise DailyConcordanceError(
            f"Tushare daily reached the possible truncation ceiling for {trade_date}"
        )
    if set(raw.columns) != set(FIELDS):
        missing = sorted(set(FIELDS) - set(raw.columns))
        extra = sorted(set(raw.columns) - set(FIELDS))
        raise DailyConcordanceError(
            f"Tushare daily schema mismatch; missing={missing}; extra={extra}"
        )
    frame = raw.loc[:, FIELDS].copy()
    frame["ts_code"] = frame["ts_code"].astype(str).str.upper().str.strip()
    if not frame["ts_code"].map(lambda value: bool(CODE_PATTERN.fullmatch(value))).all():
        raise DailyConcordanceError("Tushare daily contains an invalid stock code")
    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"].astype(str), format="%Y%m%d", errors="coerce"
    )
    if frame["trade_date"].isna().any() or set(frame["trade_date"].dt.date) != {
        trade_date
    }:
        raise DailyConcordanceError(
            f"Tushare daily response contains an outside date for {trade_date}"
        )
    for column in NUMERIC_FIELDS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    comparison_numeric = frame[list(COMPARISON_SOURCE_FIELDS)].to_numpy(dtype=float)
    if not np.isfinite(comparison_numeric).all():
        raise DailyConcordanceError(
            "Tushare daily contains a non-finite OHLC, volume, or amount value"
        )
    if not (frame[["open", "high", "low", "close"]] > 0.0).all(axis=None):
        raise DailyConcordanceError("Tushare daily contains a non-positive price")
    if not (frame[["vol", "amount"]] >= 0.0).all(axis=None):
        raise DailyConcordanceError("Tushare daily contains negative activity")
    envelope = (
        (frame["high"] >= frame[["open", "close"]].max(axis=1))
        & (frame["low"] <= frame[["open", "close"]].min(axis=1))
        & (frame["high"] >= frame["low"])
    )
    if not envelope.all():
        raise DailyConcordanceError("Tushare daily contains an invalid OHLC envelope")
    if frame.duplicated(["ts_code", "trade_date"]).any():
        raise DailyConcordanceError("Tushare daily contains a duplicate stock-date key")
    if require_representatives:
        observed = set(frame["ts_code"])
        if missing := sorted(REPRESENTATIVE_CODES - observed):
            raise DailyConcordanceError(
                "Tushare daily acceptance is missing representative codes: "
                + ", ".join(missing)
            )
    return frame.sort_values(["trade_date", "ts_code"], kind="stable").reset_index(
        drop=True
    )


class RateLimiter:
    def __init__(self, minimum_interval: float = 0.18) -> None:
        self.minimum_interval = minimum_interval
        self.last_call_started = 0.0

    def wait(self) -> None:
        delay = self.minimum_interval - (time.monotonic() - self.last_call_started)
        if delay > 0.0:
            time.sleep(delay)
        self.last_call_started = time.monotonic()


def _non_retryable_provider_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in ("权限", "积分", "permission", "token", "参数", "接口")
    )


def fetch_tushare_daily(
    pro: Any, trade_date: dt.date, limiter: RateLimiter
) -> pd.DataFrame:
    last_error: BaseException | None = None
    for attempt in range(1, 4):
        limiter.wait()
        try:
            raw = pro.daily(
                trade_date=trade_date.strftime("%Y%m%d"), fields=",".join(FIELDS)
            )
            return canonicalize_tushare_daily(raw, trade_date)
        except DailyConcordanceError:
            raise
        except BaseException as exc:
            last_error = exc
            if _non_retryable_provider_error(exc) or attempt == 3:
                break
            time.sleep(float(attempt))
    name = type(last_error).__name__ if last_error is not None else "UnknownError"
    raise DailyConcordanceError(
        f"Tushare daily request failed for {trade_date} after frozen attempts ({name})"
    )


def tushare_client() -> Any:
    token = os.environ.get("TUSHARE_TOKEN", "")
    if not token:
        raise DailyConcordanceError("TUSHARE_TOKEN is not configured in this process")
    try:
        import tushare as ts
    except ImportError as exc:
        raise DailyConcordanceError("the tushare package is not installed") from exc
    return ts.pro_api(token)


class ProcessLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle: Any = None

    def __enter__(self) -> "ProcessLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.handle.close()
            raise DailyConcordanceError(
                f"another Tushare daily process holds {self.path}"
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


def storage_paths(data_root: Path) -> dict[str, Path]:
    base = (
        data_root.expanduser().resolve()
        / "raw"
        / "a_share"
        / "rich"
        / "tushare"
        / "daily"
    )
    acceptance_name = f"tushare_daily_20251231_{PROTOCOL_SHA256[:8]}"
    snapshot_name = f"tushare_daily_2019_2025_{PROTOCOL_SHA256[:8]}"
    return {
        "base": base,
        "acceptance": base / "acceptance" / acceptance_name,
        "acceptance_partial": base / "acceptance" / f".{acceptance_name}.partial",
        "snapshot": base / "snapshots" / snapshot_name,
        "snapshot_partial": base / "snapshots" / f".{snapshot_name}.partial",
        "lock": data_root.expanduser().resolve() / ".a_share_tushare_daily.lock",
    }


def load_and_verify_frame_record(record: dict[str, Any]) -> pd.DataFrame:
    path = Path(str(record["path"]))
    if not path.is_file() or file_digest(path) != record.get("byte_sha256"):
        raise DailyConcordanceError(f"stored Tushare daily partition changed: {path}")
    frame = pd.read_parquet(path)
    if len(frame) != int(record.get("rows", -1)) or frame_digest(frame) != record.get(
        "frame_sha256"
    ):
        raise DailyConcordanceError(f"stored Tushare daily frame changed: {path}")
    return frame


def acceptance(*, data_root: Path) -> Path:
    validate_protocol()
    paths = storage_paths(data_root)
    final_root = paths["acceptance"]
    final_manifest = final_root / "snapshot_manifest.json"
    if final_manifest.is_file():
        manifest = json.loads(final_manifest.read_text(encoding="utf-8"))
        if (
            manifest.get("protocol_sha256") != PROTOCOL_SHA256
            or manifest.get("trade_date") != ACCEPTANCE_DATE.isoformat()
        ):
            raise DailyConcordanceError("existing Tushare daily acceptance is rejected")
        frame = load_and_verify_frame_record(manifest["file"])
        canonicalize_tushare_daily(
            frame.assign(trade_date=frame["trade_date"].dt.strftime("%Y%m%d")),
            ACCEPTANCE_DATE,
            require_representatives=True,
        )
        return final_manifest

    with ProcessLock(paths["lock"]):
        if final_manifest.is_file():
            return final_manifest
        partial_root = paths["acceptance_partial"]
        if partial_root.exists():
            raise DailyConcordanceError(
                f"unexpected incomplete acceptance directory exists: {partial_root}"
            )
        partial_root.mkdir(parents=True, exist_ok=False)
        try:
            raw = fetch_tushare_daily(tushare_client(), ACCEPTANCE_DATE, RateLimiter())
            frame = canonicalize_tushare_daily(
                raw.assign(trade_date=raw["trade_date"].dt.strftime("%Y%m%d")),
                ACCEPTANCE_DATE,
                require_representatives=True,
            )
            partial_data = partial_root / "daily.parquet"
            final_data = final_root / "daily.parquet"
            atomic_write_frame(frame, partial_data)
            record = {
                "path": str(final_data),
                "rows": int(len(frame)),
                "byte_sha256": file_digest(partial_data),
                "frame_sha256": frame_digest(frame),
            }
            manifest = {
                "schema_version": 1,
                "kind": "a_share_tushare_daily_acceptance",
                "status": "accepted_entitlement_schema_units_pending_full_history",
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "protocol_path": str(PROTOCOL_PATH),
                "protocol_sha256": PROTOCOL_SHA256,
                "provider": "tushare",
                "interface": "daily",
                "trade_date": ACCEPTANCE_DATE.isoformat(),
                "fields": list(FIELDS),
                "representative_codes": sorted(REPRESENTATIVE_CODES),
                "file": record,
                "volume_unit": "lots_of_100_shares",
                "amount_unit": "thousand_CNY",
                "credential_value_persisted": False,
                "forward_return_fields_read": False,
                "existing_baostock_daily_files_mutated": False,
            }
            atomic_write_json(manifest, partial_root / "snapshot_manifest.json")
            final_root.parent.mkdir(parents=True, exist_ok=True)
            partial_root.replace(final_root)
            return final_manifest
        except BaseException:
            shutil.rmtree(partial_root, ignore_errors=True)
            raise


def load_acceptance_manifest(path: Path) -> tuple[dict[str, Any], pd.DataFrame, str]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise DailyConcordanceError(f"acceptance manifest is missing: {path}")
    digest = file_digest(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (
        manifest.get("kind") != "a_share_tushare_daily_acceptance"
        or manifest.get("status")
        != "accepted_entitlement_schema_units_pending_full_history"
        or manifest.get("protocol_sha256") != PROTOCOL_SHA256
        or manifest.get("trade_date") != ACCEPTANCE_DATE.isoformat()
        or manifest.get("forward_return_fields_read") is not False
    ):
        raise DailyConcordanceError("Tushare daily acceptance manifest is rejected")
    frame = load_and_verify_frame_record(manifest["file"])
    canonicalize_tushare_daily(
        frame.assign(trade_date=frame["trade_date"].dt.strftime("%Y%m%d")),
        ACCEPTANCE_DATE,
        require_representatives=True,
    )
    return manifest, frame, digest


def _year_paths(partial_root: Path, final_root: Path, year: int) -> tuple[Path, Path, Path]:
    return (
        partial_root / f"{year}.parquet",
        partial_root / ".metadata" / f"{year}.json",
        final_root / f"{year}.parquet",
    )


def load_completed_year(
    partial_root: Path, final_root: Path, year: int, acceptance_sha256: str
) -> dict[str, Any] | None:
    partial_data, sidecar, _ = _year_paths(partial_root, final_root, year)
    if not sidecar.exists():
        partial_data.unlink(missing_ok=True)
        return None
    record = json.loads(sidecar.read_text(encoding="utf-8"))
    if (
        record.get("kind") != "a_share_tushare_daily_year_checkpoint"
        or record.get("protocol_sha256") != PROTOCOL_SHA256
        or record.get("acceptance_manifest_sha256") != acceptance_sha256
        or record.get("year") != year
        or not partial_data.is_file()
        or file_digest(partial_data) != record.get("byte_sha256")
    ):
        raise DailyConcordanceError(f"Tushare daily year checkpoint changed: {sidecar}")
    frame = pd.read_parquet(partial_data)
    if len(frame) != int(record.get("rows", -1)) or frame_digest(frame) != record.get(
        "frame_sha256"
    ):
        raise DailyConcordanceError(f"Tushare daily year frame changed: {partial_data}")
    return record


def sync(*, data_root: Path, acceptance_manifest: Path) -> Path:
    validate_protocol()
    calendar = load_calendar()
    _, accepted_frame, acceptance_sha256 = load_acceptance_manifest(acceptance_manifest)
    paths = storage_paths(data_root)
    final_root = paths["snapshot"]
    final_manifest = final_root / "snapshot_manifest.json"
    if final_manifest.is_file():
        manifest = json.loads(final_manifest.read_text(encoding="utf-8"))
        if (
            manifest.get("protocol_sha256") != PROTOCOL_SHA256
            or manifest.get("acceptance_manifest_sha256") != acceptance_sha256
        ):
            raise DailyConcordanceError("existing Tushare daily snapshot is rejected")
        return final_manifest
    if shutil.disk_usage(data_root).free < 5 * 1024**3:
        raise DailyConcordanceError("external data root has less than 5 GiB free")

    with ProcessLock(paths["lock"]):
        partial_root = paths["snapshot_partial"]
        partial_root.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, Any]] = []
        resumed_years = 0
        provider_calls_this_invocation = 0
        completed_sessions = 0
        client: Any | None = None
        limiter = RateLimiter()
        for year in range(START_DATE.year, END_DATE.year + 1):
            year_dates = calendar[calendar.year == year]
            completed = load_completed_year(
                partial_root, final_root, year, acceptance_sha256
            )
            if completed is not None:
                records.append(completed)
                resumed_years += 1
                completed_sessions += int(completed["sessions"])
                print(
                    f"resumed year={year} sessions={completed_sessions:,}/1,699",
                    flush=True,
                )
                continue
            frames: list[pd.DataFrame] = []
            for value in year_dates:
                trade_date = value.date()
                if trade_date == ACCEPTANCE_DATE:
                    frame = accepted_frame.copy()
                else:
                    if client is None:
                        client = tushare_client()
                    frame = fetch_tushare_daily(client, trade_date, limiter)
                    provider_calls_this_invocation += 1
                frames.append(frame)
                completed_sessions += 1
                if completed_sessions % 25 == 0 or completed_sessions == len(calendar):
                    print(
                        f"progress sessions={completed_sessions:,}/{len(calendar):,} "
                        f"provider_calls={provider_calls_this_invocation:,}",
                        flush=True,
                    )
            annual = pd.concat(frames, ignore_index=True)
            annual = annual.sort_values(
                ["trade_date", "ts_code"], kind="stable"
            ).reset_index(drop=True)
            if annual.duplicated(["ts_code", "trade_date"]).any():
                raise DailyConcordanceError(f"annual Tushare daily keys duplicate in {year}")
            if set(annual["trade_date"].dt.normalize()) != set(year_dates):
                raise DailyConcordanceError(f"annual Tushare daily dates are incomplete in {year}")
            partial_data, sidecar, final_data = _year_paths(
                partial_root, final_root, year
            )
            atomic_write_frame(annual, partial_data)
            date_counts = annual.groupby("trade_date", observed=True).size()
            auxiliary_null_counts = {
                column: int(annual[column].isna().sum())
                for column in AUXILIARY_SOURCE_FIELDS
            }
            record = {
                "schema_version": 1,
                "kind": "a_share_tushare_daily_year_checkpoint",
                "protocol_sha256": PROTOCOL_SHA256,
                "acceptance_manifest_sha256": acceptance_sha256,
                "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "year": year,
                "path": str(final_data),
                "rows": int(len(annual)),
                "sessions": int(len(year_dates)),
                "minimum_names_per_session": int(date_counts.min()),
                "maximum_names_per_session": int(date_counts.max()),
                "auxiliary_null_counts": auxiliary_null_counts,
                "byte_sha256": file_digest(partial_data),
                "frame_sha256": frame_digest(annual),
                "forward_return_fields_read": False,
            }
            atomic_write_json(record, sidecar)
            records.append(record)
            print(
                f"completed year={year} rows={len(annual):,} "
                f"sessions={len(year_dates):,}",
                flush=True,
            )

        if len(records) != 7 or sum(int(item["sessions"]) for item in records) != 1699:
            raise DailyConcordanceError("Tushare daily snapshot did not complete all years")
        records.sort(key=lambda item: int(item["year"]))
        manifest = {
            "schema_version": 1,
            "kind": "a_share_tushare_daily_snapshot",
            "status": "complete_pending_independent_baostock_concordance",
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "protocol_path": str(PROTOCOL_PATH),
            "protocol_sha256": PROTOCOL_SHA256,
            "implementation_repair_path": str(REPAIR_PATH),
            "implementation_repair_sha256": REPAIR_SHA256,
            "acceptance_manifest_path": str(acceptance_manifest.expanduser().resolve()),
            "acceptance_manifest_sha256": acceptance_sha256,
            "provider": "tushare",
            "interface": "daily",
            "prices": "raw_unadjusted",
            "requested_start": START_DATE.isoformat(),
            "requested_end": END_DATE.isoformat(),
            "calendar_path": str(CALENDAR_PATH),
            "calendar_sha256": file_digest(CALENDAR_PATH),
            "calendar_sessions": 1699,
            "files": records,
            "rows": int(sum(int(item["rows"]) for item in records)),
            "volume_unit": "lots_of_100_shares",
            "amount_unit": "thousand_CNY",
            "auxiliary_null_counts": {
                column: int(
                    sum(
                        int((item.get("auxiliary_null_counts") or {}).get(column, 0))
                        for item in records
                    )
                )
                for column in AUXILIARY_SOURCE_FIELDS
            },
            "provider_calls_in_full_snapshot": 1698,
            "provider_calls_this_invocation": provider_calls_this_invocation,
            "resumed_years": resumed_years,
            "credential_value_persisted": False,
            "forward_return_fields_read": False,
            "factor_values_read": False,
            "existing_baostock_daily_files_mutated": False,
        }
        atomic_write_json(manifest, partial_root / "snapshot_manifest.json")
        final_root.parent.mkdir(parents=True, exist_ok=True)
        partial_root.replace(final_root)
        return final_manifest


def relative_error(candidate: np.ndarray, reference: np.ndarray) -> np.ndarray:
    candidate = np.asarray(candidate, dtype=float)
    reference = np.asarray(reference, dtype=float)
    result = np.full(candidate.shape, np.inf, dtype=float)
    nonzero = np.abs(reference) > 0.0
    result[nonzero] = np.abs(candidate[nonzero] - reference[nonzero]) / np.abs(
        reference[nonzero]
    )
    both_zero = (~nonzero) & (candidate == 0.0)
    result[both_zero] = 0.0
    return result


def summarize_errors(errors: np.ndarray) -> dict[str, Any]:
    errors = np.asarray(errors, dtype=float)
    finite = errors[np.isfinite(errors)]
    if not len(errors) or not len(finite):
        raise DailyConcordanceError("provider comparison has no finite common errors")
    quantiles = np.quantile(finite, [0.5, 0.9, 0.95, 0.99, 0.999])
    return {
        "rows": int(len(errors)),
        "finite_rows": int(len(finite)),
        "exact_rows": int((errors == 0.0).sum()),
        "exact_share": float((errors == 0.0).mean()),
        "p50_relative_error": float(quantiles[0]),
        "p90_relative_error": float(quantiles[1]),
        "p95_relative_error": float(quantiles[2]),
        "p99_relative_error": float(quantiles[3]),
        "p999_relative_error": float(quantiles[4]),
        "maximum_finite_relative_error": float(finite.max()),
        "infinite_relative_error_rows": int((~np.isfinite(errors)).sum()),
        "cumulative_error_bands": {
            str(band): int((errors <= band).sum()) for band in ERROR_BANDS
        },
    }


def normalize_tushare_for_comparison(frame: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame(
        {
            "symbol": symbol_from_ts_code(frame["ts_code"]),
            "trade_date": pd.to_datetime(frame["trade_date"]).dt.normalize(),
            "open": pd.to_numeric(frame["open"]),
            "high": pd.to_numeric(frame["high"]),
            "low": pd.to_numeric(frame["low"]),
            "close": pd.to_numeric(frame["close"]),
            "volume": pd.to_numeric(frame["vol"]),
            "amount": pd.to_numeric(frame["amount"]) * 1000.0,
        }
    )
    if result.duplicated(["symbol", "trade_date"]).any():
        raise DailyConcordanceError("normalized Tushare daily keys duplicate")
    return result


def load_baostock_reference() -> tuple[pd.DataFrame, str, int]:
    paths = sorted(REFERENCE_DAILY_ROOT.glob("*.parquet"))
    if len(paths) != 5451:
        raise DailyConcordanceError(
            f"expected 5,451 BaoStock daily files, observed {len(paths):,}"
        )
    digest = hashlib.sha256()
    frames: list[pd.DataFrame] = []
    required = {
        "date",
        "symbol",
        "raw_open",
        "raw_high",
        "raw_low",
        "raw_close",
        "raw_volume",
        "amount",
        "daily_source",
        "price_basis",
    }
    for index, path in enumerate(paths, start=1):
        byte_sha256 = file_digest(path)
        digest.update(f"{path.name}|{byte_sha256}\n".encode("utf-8"))
        frame = pd.read_parquet(path, columns=sorted(required))
        if set(frame["daily_source"].dropna().astype(str)) != {"baostock"}:
            raise DailyConcordanceError(f"daily reference source changed: {path}")
        if set(frame["price_basis"].dropna().astype(str)) != {
            REFERENCE_PRICE_BASIS
        }:
            raise DailyConcordanceError(f"daily reference price basis changed: {path}")
        work = pd.DataFrame(
            {
                "symbol": frame["symbol"].astype(str).str.upper(),
                "trade_date": pd.to_datetime(frame["date"]).dt.normalize(),
                "open": pd.to_numeric(frame["raw_open"]),
                "high": pd.to_numeric(frame["raw_high"]),
                "low": pd.to_numeric(frame["raw_low"]),
                "close": pd.to_numeric(frame["raw_close"]),
                "volume": pd.to_numeric(frame["raw_volume"]),
                "amount": pd.to_numeric(frame["amount"]),
            }
        )
        work = work[
            (work["trade_date"] >= pd.Timestamp(START_DATE))
            & (work["trade_date"] <= pd.Timestamp(END_DATE))
        ]
        frames.append(work)
        if index % 500 == 0:
            print(f"reference files={index:,}/{len(paths):,}", flush=True)
    reference = pd.concat(frames, ignore_index=True)
    if reference.duplicated(["symbol", "trade_date"]).any():
        raise DailyConcordanceError("BaoStock reference keys duplicate")
    return reference, digest.hexdigest(), len(paths)


def compare(*, snapshot_manifest: Path) -> Path:
    protocol = validate_protocol()
    snapshot_manifest = snapshot_manifest.expanduser().resolve()
    if not snapshot_manifest.is_file():
        raise DailyConcordanceError(f"Tushare daily snapshot is missing: {snapshot_manifest}")
    snapshot_sha256 = file_digest(snapshot_manifest)
    snapshot = json.loads(snapshot_manifest.read_text(encoding="utf-8"))
    if (
        snapshot.get("kind") != "a_share_tushare_daily_snapshot"
        or snapshot.get("status") != "complete_pending_independent_baostock_concordance"
        or snapshot.get("protocol_sha256") != PROTOCOL_SHA256
        or snapshot.get("forward_return_fields_read") is not False
        or len(snapshot.get("files") or []) != 7
    ):
        raise DailyConcordanceError("Tushare daily snapshot manifest is rejected")
    audit_path = snapshot_manifest.parent / "provider_concordance_audit.json"
    if audit_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if (
            audit.get("protocol_sha256") != PROTOCOL_SHA256
            or audit.get("tushare_snapshot_manifest_sha256") != snapshot_sha256
        ):
            raise DailyConcordanceError("existing provider concordance audit is rejected")
        return audit_path

    reference, reference_sha256, reference_file_count = load_baostock_reference()
    error_parts: dict[str, list[np.ndarray]] = {field: [] for field in ERROR_FIELDS}
    examples: dict[str, list[dict[str, Any]]] = {field: [] for field in ERROR_FIELDS}
    yearly: list[dict[str, Any]] = []
    total_common = 0
    total_tushare_only = 0
    total_baostock_only = 0
    total_tushare = 0
    total_reference = 0
    total_material = 0

    for record in sorted(snapshot["files"], key=lambda item: int(item["year"])):
        year = int(record["year"])
        source = normalize_tushare_for_comparison(load_and_verify_frame_record(record))
        base = reference[reference["trade_date"].dt.year == year]
        merged = source.merge(
            base,
            on=["symbol", "trade_date"],
            how="outer",
            suffixes=("_tushare", "_baostock"),
            indicator=True,
            validate="one_to_one",
        )
        common = merged[merged["_merge"] == "both"].copy()
        tushare_only = int((merged["_merge"] == "left_only").sum())
        baostock_only = int((merged["_merge"] == "right_only").sum())
        material = np.zeros(len(common), dtype=bool)
        year_field_p99: dict[str, float] = {}
        for field in ERROR_FIELDS:
            errors = relative_error(
                common[f"{field}_tushare"].to_numpy(dtype=float),
                common[f"{field}_baostock"].to_numpy(dtype=float),
            )
            error_parts[field].append(errors)
            finite = errors[np.isfinite(errors)]
            year_field_p99[field] = (
                float(np.quantile(finite, 0.99)) if len(finite) else math.inf
            )
            threshold = 0.002 if field in {"open", "high", "low", "close"} else 0.005
            material |= errors > threshold
            if len(errors):
                positions = np.argsort(errors)[-5:]
                for position in positions:
                    row = common.iloc[int(position)]
                    examples[field].append(
                        {
                            "symbol": str(row["symbol"]),
                            "trade_date": pd.Timestamp(row["trade_date"])
                            .date()
                            .isoformat(),
                            "relative_error": (
                                float(errors[position])
                                if np.isfinite(errors[position])
                                else None
                            ),
                        }
                    )
        year_common = int(len(common))
        year_reference = int(len(base))
        yearly.append(
            {
                "year": year,
                "tushare_rows": int(len(source)),
                "baostock_rows": year_reference,
                "common_rows": year_common,
                "common_share_of_baostock": year_common / year_reference,
                "tushare_only_rows": tushare_only,
                "baostock_only_rows": baostock_only,
                "material_difference_rows": int(material.sum()),
                "material_difference_share_of_common": float(material.mean()),
                "field_p99_relative_error": year_field_p99,
            }
        )
        total_common += year_common
        total_tushare_only += tushare_only
        total_baostock_only += baostock_only
        total_tushare += int(len(source))
        total_reference += year_reference
        total_material += int(material.sum())
        print(
            f"compared year={year} common={year_common:,} "
            f"tushare_only={tushare_only:,} baostock_only={baostock_only:,}",
            flush=True,
        )

    field_summaries: dict[str, Any] = {}
    for field in ERROR_FIELDS:
        values = np.concatenate(error_parts[field])
        field_summaries[field] = summarize_errors(values)
        candidates = sorted(
            examples[field],
            key=lambda item: (
                math.inf
                if item["relative_error"] is None
                else float(item["relative_error"])
            ),
            reverse=True,
        )
        examples[field] = candidates[:10]
    common_coverage = total_common / total_reference
    small = (
        common_coverage >= 0.99
        and all(
            field_summaries[field]["p99_relative_error"] <= 0.002
            for field in ("open", "high", "low", "close")
        )
        and all(
            field_summaries[field]["p99_relative_error"] <= 0.005
            for field in ("volume", "amount")
        )
    )
    audit = {
        "schema_version": 1,
        "kind": "a_share_tushare_baostock_daily_concordance_audit",
        "status": "completed_no_provider_switch",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol_path": str(PROTOCOL_PATH),
        "protocol_sha256": PROTOCOL_SHA256,
        "tushare_snapshot_manifest_path": str(snapshot_manifest),
        "tushare_snapshot_manifest_sha256": snapshot_sha256,
        "baostock_reference_root": str(REFERENCE_DAILY_ROOT),
        "baostock_reference_dataset_sha256": reference_sha256,
        "baostock_reference_file_count": reference_file_count,
        "requested_start": START_DATE.isoformat(),
        "requested_end": END_DATE.isoformat(),
        "key_coverage": {
            "tushare_rows": total_tushare,
            "baostock_rows": total_reference,
            "common_rows": total_common,
            "common_share_of_baostock": common_coverage,
            "tushare_only_rows": total_tushare_only,
            "baostock_only_rows": total_baostock_only,
        },
        "field_relative_error": field_summaries,
        "material_difference": {
            "definition": (protocol["comparison"])["material_difference_definition"],
            "rows": total_material,
            "share_of_common": total_material / total_common,
        },
        "yearly": yearly,
        "largest_relative_error_examples_without_raw_values": examples,
        "summary_classification": "small" if small else "material",
        "classification_contract": (protocol["comparison"])[
            "summary_classification"
        ],
        "tushare_amount_multiplied_by_1000_before_comparison": True,
        "tushare_and_baostock_volume_compared_in_lots": True,
        "existing_baostock_daily_files_mutated": False,
        "active_daily_provider_switched": False,
        "forward_return_fields_read": False,
        "factor_values_read": False,
        "aggregation_scoring_selection_sizing_or_orders_performed": False,
    }
    atomic_write_json(audit, audit_path)
    return audit_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    acceptance_parser = subparsers.add_parser("acceptance")
    acceptance_parser.add_argument("--data-root", type=Path, required=True)
    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("--data-root", type=Path, required=True)
    sync_parser.add_argument("--acceptance-manifest", type=Path, required=True)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--snapshot-manifest", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "acceptance":
        result = acceptance(data_root=args.data_root)
    elif args.command == "sync":
        result = sync(
            data_root=args.data_root, acceptance_manifest=args.acceptance_manifest
        )
    elif args.command == "compare":
        result = compare(snapshot_manifest=args.snapshot_manifest)
    else:
        raise DailyConcordanceError(f"unsupported command: {args.command}")
    print(result, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
