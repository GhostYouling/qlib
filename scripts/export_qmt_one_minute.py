#!/usr/bin/env python3
"""Export the frozen QMT/XtQuant one-minute acceptance bundle on Windows.

This script is intentionally export-only. It never accesses accounts, orders,
positions, Level-2 data, or repository prices and returns. Run it only inside
an already-lawful MiniQMT/XtQuant environment, then move the immutable output
directory to the research machine for offline acceptance.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import importlib.metadata
import json
import math
import platform
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    REPO_ROOT / "docs" / "a_share_qmt_xtquant_one_minute_export_data_contract.json"
)
CONTRACT_SHA256 = (
    "a5ccb8bb4a7356a2c655d3cfd3ffc72365cc93c19198476110fb793c2fa71399"
)


class QmtExportError(RuntimeError):
    """A frozen export-contract violation."""


def file_sha256(path: Path) -> str:
    """Return a file's SHA-256 digest."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    """Load and structurally validate the immutable pre-row contract."""

    path = path.expanduser().resolve()
    if file_sha256(path) != CONTRACT_SHA256:
        raise QmtExportError("QMT one-minute export contract fingerprint mismatch")
    payload = json.loads(path.read_text(encoding="utf-8"))
    exporter = payload.get("exporter_protocol") or {}
    acceptance = payload.get("formal_acceptance") or {}
    bundle = payload.get("bundle_manifest_contract") or {}
    if (
        payload.get("version") != 1
        or payload.get("kind")
        != "a_share_qmt_xtquant_one_minute_export_data_contract"
        or payload.get("status")
        != "frozen_before_qmt_runtime_export_rows_minute_factor_values_prices_or_forward_returns"
        or exporter.get("allowed_operation") != "export-acceptance"
        or exporter.get("api_module") != "xtquant.xtdata"
        or exporter.get("history_download_function") != "download_history_data2"
        or exporter.get("history_read_function") != "get_market_data_ex"
        or exporter.get("period") != "1m"
        or exporter.get("field_list_in_order")
        != [
            "time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "suspendFlag",
        ]
        or exporter.get("dividend_type") != "none"
        or exporter.get("fill_data") is not False
        or exporter.get("count") != -1
        or exporter.get("export_manifest_filename")
        != "qmt_1m_acceptance_export.json"
        or exporter.get("gzip_mtime") != 0
        or acceptance.get("trade_date") != "2026-07-13"
        or acceptance.get("symbols") != ["600519", "000001", "300750", "688981"]
        or acceptance.get("source_symbols")
        != ["600519.SH", "000001.SZ", "300750.SZ", "688981.SH"]
        or bundle.get("kind") != "a_share_qmt_xtquant_one_minute_export_bundle"
        or bundle.get("version") != 1
        or bundle.get("provider") != "qmt_xtquant"
        or bundle.get("export_kind") != "acceptance"
        or bundle.get("required_top_level_fields")
        != [
            "version",
            "kind",
            "provider",
            "export_kind",
            "generated_at_utc",
            "trade_date",
            "symbols",
            "source_symbols",
            "api_request",
            "runtime",
            "data_contract",
            "files",
            "privacy",
        ]
        or bundle.get("file_columns_required")
        != [
            "timetag_ms",
            "source_symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "suspend_flag",
        ]
        or payload.get("qmt_runtime_or_export_rows_observed_before_freeze") is not False
        or payload.get("minute_factor_values_observed_before_freeze") is not False
        or payload.get("forward_return_fields_read") is not False
        or payload.get("selection_or_promotion_allowed") is not False
    ):
        raise QmtExportError("QMT one-minute export contract changed after freeze")
    return payload


def _strict_number_series(
    series: pd.Series, *, field: str, integer: bool = False
) -> pd.Series:
    """Normalize one exported numeric field without dropping a source row."""

    if series.map(lambda value: isinstance(value, (bool,))).any():
        raise QmtExportError(f"QMT export field {field} contains a boolean")
    numeric = pd.to_numeric(series, errors="coerce")
    finite = numeric.map(lambda value: pd.notna(value) and math.isfinite(float(value)))
    if not finite.all():
        raise QmtExportError(f"QMT export field {field} is missing or non-finite")
    if integer:
        integral = numeric.map(lambda value: float(value).is_integer())
        if not integral.all():
            raise QmtExportError(f"QMT export field {field} is not an integer")
        return numeric.astype("int64")
    return numeric.astype("float64")


def canonical_export_frame(
    frame: pd.DataFrame, source_symbol: str, fields: list[str]
) -> pd.DataFrame:
    """Convert one XtData DataFrame to the frozen privacy-minimized CSV schema."""

    if not isinstance(frame, pd.DataFrame):
        raise QmtExportError(f"QMT export for {source_symbol} is not a DataFrame")
    if list(frame.columns) != fields:
        raise QmtExportError(
            f"QMT export for {source_symbol} changed field order or schema"
        )
    output = pd.DataFrame()
    output["timetag_ms"] = _strict_number_series(
        frame["time"], field="time", integer=True
    )
    output["source_symbol"] = source_symbol
    for field in ("open", "high", "low", "close", "volume", "amount"):
        output[field] = _strict_number_series(frame[field], field=field)
    output["suspend_flag"] = _strict_number_series(
        frame["suspendFlag"], field="suspendFlag", integer=True
    )
    return output.sort_values("timetag_ms", kind="stable").reset_index(drop=True)


def write_deterministic_gzip_csv(frame: pd.DataFrame, destination: Path) -> None:
    """Write deterministic UTF-8 CSV gzip bytes for cross-machine hashing."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, suffix=".csv.gz", delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                csv_bytes = frame.to_csv(
                    index=False,
                    lineterminator="\n",
                    float_format="%.17g",
                ).encode("utf-8")
                zipped.write(csv_bytes)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _xtquant_version(module: Any) -> str:
    """Return a non-sensitive runtime version string when one is available."""

    try:
        value = importlib.metadata.version("xtquant")
    except importlib.metadata.PackageNotFoundError:
        value = getattr(module, "__version__", "unavailable")
    text = str(value).strip()
    return text or "unavailable"


def export_qmt_acceptance_bundle(
    output_root: Path,
    *,
    xtdata_module: Any | None = None,
    generated_at: dt.datetime | None = None,
) -> Path:
    """Download and export the single frozen four-symbol acceptance bundle."""

    contract = load_contract()
    exporter = contract["exporter_protocol"]
    acceptance = contract["formal_acceptance"]
    destination = output_root.expanduser().resolve()
    if destination.exists():
        raise QmtExportError(f"QMT export destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / f".{destination.name}.partial"
    if temporary.exists():
        raise QmtExportError(f"QMT export temporary destination exists: {temporary}")
    temporary.mkdir()
    try:
        if xtdata_module is None:
            try:
                from xtquant import xtdata as xtdata_module
            except ImportError as exc:
                raise QmtExportError(
                    "xtquant is unavailable; run this exporter inside the user's "
                    "lawful Windows MiniQMT/XtQuant environment"
                ) from exc
        source_symbols = list(acceptance["source_symbols"])
        trade_date = str(acceptance["trade_date"]).replace("-", "")
        fields = list(exporter["field_list_in_order"])
        xtdata_module.download_history_data2(
            source_symbols,
            period="1m",
            start_time=trade_date,
            end_time=trade_date,
        )
        response = xtdata_module.get_market_data_ex(
            fields,
            source_symbols,
            period="1m",
            start_time=trade_date,
            end_time=trade_date,
            count=-1,
            dividend_type="none",
            fill_data=False,
        )
        if not isinstance(response, dict) or set(response) != set(source_symbols):
            raise QmtExportError(
                "QMT acceptance response does not contain exactly the frozen symbols"
            )
        files: list[dict[str, Any]] = []
        for source_symbol in source_symbols:
            frame = canonical_export_frame(response[source_symbol], source_symbol, fields)
            filename = (
                f"qmt_1m_{source_symbol.replace('.', '_')}_{trade_date}.csv.gz"
            )
            path = temporary / filename
            write_deterministic_gzip_csv(frame, path)
            files.append(
                {
                    "source_symbol": source_symbol,
                    "path": filename,
                    "rows": int(len(frame)),
                    "sha256": file_sha256(path),
                    "columns": list(frame.columns),
                }
            )
        observed_time = generated_at or dt.datetime.now(dt.timezone.utc)
        if observed_time.tzinfo is None:
            observed_time = observed_time.replace(tzinfo=dt.timezone.utc)
        manifest = {
            "version": 1,
            "kind": "a_share_qmt_xtquant_one_minute_export_bundle",
            "provider": "qmt_xtquant",
            "export_kind": "acceptance",
            "generated_at_utc": observed_time.astimezone(dt.timezone.utc).isoformat(),
            "trade_date": acceptance["trade_date"],
            "symbols": acceptance["symbols"],
            "source_symbols": source_symbols,
            "api_request": {
                "history_download_function": "download_history_data2",
                "history_read_function": "get_market_data_ex",
                "period": "1m",
                "fields": fields,
                "start_time": trade_date,
                "end_time": trade_date,
                "count": -1,
                "dividend_type": "none",
                "fill_data": False,
            },
            "runtime": {
                "python_version": platform.python_version(),
                "xtquant_version": _xtquant_version(xtdata_module),
            },
            "data_contract": {
                "path": "docs/a_share_qmt_xtquant_one_minute_export_data_contract.json",
                "sha256": CONTRACT_SHA256,
            },
            "files": files,
            "privacy": {
                "credential_account_cookie_token_client_path_machine_name_or_username_persisted": False,
                "trading_or_level2_api_used": False,
                "raw_qmt_cache_or_client_database_copied": False,
            },
        }
        manifest_path = temporary / str(exporter["export_manifest_filename"])
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(destination)
        return destination / manifest_path.name
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    """Build the fixed export-only CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    acceptance = subparsers.add_parser(
        "export-acceptance",
        help="export the frozen 2026-07-13 four-symbol Level-1 sample",
    )
    acceptance.add_argument(
        "--output",
        type=Path,
        required=True,
        help="new output directory; existing directories are never overwritten",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the exporter without printing any bar or sensitive runtime value."""

    args = build_parser().parse_args(argv)
    try:
        manifest = export_qmt_acceptance_bundle(args.output)
    except QmtExportError as exc:
        print(f"error: {exc}")
        return 2
    print(json.dumps({"manifest": str(manifest), "status": "exported_acceptance"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
