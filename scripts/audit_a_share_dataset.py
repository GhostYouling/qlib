"""Run a full integrity audit of the repository-local A-share Qlib data set.

The audit reads every source Parquet file and compares every dumped Qlib binary
feature with it.  It also checks calendar/instrument/universe consistency and
performs deterministic Qlib-reader and source-tail probes.  The audit reports
the distinct limitation of an absent Qlib restoration factor separately from
signal-data integrity.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data"
RAW_DIR = DATA_ROOT / "raw" / "a_share" / "daily"
QLIB_DIR = DATA_ROOT / "qlib" / "cn_a_share"
METADATA_DIR = DATA_ROOT / "metadata"
DEFAULT_OUTPUT = DATA_ROOT / "metadata" / "dataset_audit.json"
DEFAULT_UNIVERSE_SNAPSHOT = METADATA_DIR / "universe_latest.json"
RAW_COLUMNS = (
    "date",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "vwap",
    "change",
    "pct_chg",
    "turnover",
)
FEATURE_FIELDS = RAW_COLUMNS[2:]
PRICE_FIELDS = ("open", "high", "low", "close")


def evenly_spaced(items: Iterable[str], count: int) -> list[str]:
    """Select a deterministic spread from a sorted sequence."""

    values = list(items)
    if count <= 0 or not values:
        return []
    if len(values) <= count:
        return values
    if count == 1:
        return [values[len(values) // 2]]
    positions = [round(index * (len(values) - 1) / (count - 1)) for index in range(count)]
    return [values[position] for position in positions]


def read_calendar(path: Path) -> pd.DatetimeIndex:
    """Load and validate a Qlib day calendar."""

    dates = pd.to_datetime(pd.read_csv(path, header=None).iloc[:, 0], errors="coerce")
    if dates.isna().any():
        raise ValueError(f"calendar has {int(dates.isna().sum())} invalid dates: {path}")
    calendar = pd.DatetimeIndex(dates).normalize()
    if not calendar.is_monotonic_increasing or calendar.has_duplicates:
        raise ValueError(f"calendar is not strictly increasing and unique: {path}")
    return calendar


def read_instrument_ranges(path: Path) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    """Read Qlib's three-column instrument ranges."""

    ranges: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            raise ValueError(f"invalid instrument row in {path}: {line!r}")
        symbol, begin, end = parts
        if symbol in ranges:
            raise ValueError(f"duplicate instrument in {path}: {symbol}")
        start, finish = pd.Timestamp(begin), pd.Timestamp(end)
        if start > finish:
            raise ValueError(f"inverted range for {symbol} in {path}")
        ranges[symbol] = (start, finish)
    return ranges


def audit_temporal_universe_coverage(
    snapshot_path: Path,
    calendar: pd.DatetimeIndex,
    instrument_ranges: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
    buyable_ranges: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
    factor_ranges: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Check point-in-time *ranges* for every locally retained instrument.

    A current provider snapshot is not proof that no historical delisted stock
    was ever omitted.  It can, however, prove the narrower and crucial
    invariant that every retained stock is absent before its known listing date
    and after the final locally available trading date, and that both custom
    Qlib universes preserve those same date ranges.
    """

    errors: list[str] = []
    limitations: list[str] = [
        "The current universe snapshot can validate trading ranges for locally retained symbols, but it cannot prove complete historical listing/delisting coverage."
    ]
    if not snapshot_path.exists():
        return (
            {
                "status": "unavailable",
                "snapshot_path": str(snapshot_path),
                "retained_instrument_count": len(instrument_ranges),
            },
            [f"universe snapshot does not exist: {snapshot_path}"],
            limitations,
        )
    try:
        records = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (
            {
                "status": "unavailable",
                "snapshot_path": str(snapshot_path),
                "retained_instrument_count": len(instrument_ranges),
            },
            [f"cannot read universe snapshot: {type(exc).__name__}"],
            limitations,
        )
    if not isinstance(records, list):
        return (
            {
                "status": "unavailable",
                "snapshot_path": str(snapshot_path),
                "retained_instrument_count": len(instrument_ranges),
            },
            ["universe snapshot must be a list of records"],
            limitations,
        )

    by_symbol: dict[str, dict[str, Any]] = {}
    malformed = 0
    duplicate_symbols: list[str] = []
    for record in records:
        if not isinstance(record, dict) or not record.get("symbol"):
            malformed += 1
            continue
        symbol = str(record["symbol"]).upper()
        if symbol in by_symbol:
            duplicate_symbols.append(symbol)
        by_symbol[symbol] = record
    if malformed:
        errors.append(f"universe snapshot has {malformed} malformed records")
    if duplicate_symbols:
        errors.append(f"universe snapshot has duplicate symbols: {len(set(duplicate_symbols))}")

    snapshot_symbols = set(by_symbol)
    retained_symbols = set(instrument_ranges)
    missing_snapshot = retained_symbols - snapshot_symbols
    extra_snapshot = snapshot_symbols - retained_symbols
    if missing_snapshot:
        errors.append(f"universe snapshot is missing {len(missing_snapshot)} retained instruments")
    if extra_snapshot:
        limitations.append(
            f"The current snapshot has {len(extra_snapshot)} symbols without retained daily bars; they are excluded from the local Qlib universes and are not tradable research candidates."
        )

    listing_date_missing = 0
    listing_date_invalid = 0
    pre_listing_ranges: list[str] = []
    for symbol, (start, _) in instrument_ranges.items():
        record = by_symbol.get(symbol)
        if record is None:
            continue
        raw_listing_date = record.get("listing_date")
        if not raw_listing_date:
            listing_date_missing += 1
            continue
        listing_date = pd.to_datetime(raw_listing_date, errors="coerce")
        if pd.isna(listing_date):
            listing_date_invalid += 1
            continue
        if start < pd.Timestamp(listing_date).normalize():
            pre_listing_ranges.append(symbol)
    if listing_date_invalid:
        errors.append(f"universe snapshot has {listing_date_invalid} invalid listing dates")
    if pre_listing_ranges:
        errors.append(f"{len(pre_listing_ranges)} retained instruments start before their listed date")

    buyable_range_mismatches = [
        symbol for symbol, date_range in buyable_ranges.items() if instrument_ranges.get(symbol) != date_range
    ]
    factor_range_mismatches = [
        symbol for symbol, date_range in factor_ranges.items() if instrument_ranges.get(symbol) != date_range
    ]
    if buyable_range_mismatches:
        errors.append(f"{len(buyable_range_mismatches)} buyable ranges differ from instruments/all.txt")
    if factor_range_mismatches:
        errors.append(f"{len(factor_range_mismatches)} factor ranges differ from instruments/all.txt")

    calendar_end = calendar[-1]
    terminal_symbols = sorted(symbol for symbol, (_, finish) in instrument_ranges.items() if finish < calendar_end)
    terminal_buyable = sorted(symbol for symbol in terminal_symbols if symbol in buyable_ranges)
    return (
        {
            "status": "passed" if not errors else "failed",
            "snapshot_path": str(snapshot_path.resolve()),
            "snapshot_symbol_count": len(snapshot_symbols),
            "retained_instrument_count": len(retained_symbols),
            "snapshot_without_daily_bar_count": len(extra_snapshot),
            "snapshot_without_daily_bar_examples": sorted(extra_snapshot)[:20],
            "retained_without_snapshot_count": len(missing_snapshot),
            "listing_date_coverage": float(
                (len(retained_symbols) - listing_date_missing - listing_date_invalid) / len(retained_symbols)
            )
            if retained_symbols
            else 0.0,
            "listing_date_missing": listing_date_missing,
            "listing_date_invalid": listing_date_invalid,
            "pre_listing_range_count": len(pre_listing_ranges),
            "terminal_range_count": len(terminal_symbols),
            "terminal_buyable_range_count": len(terminal_buyable),
            "buyable_range_mismatch_count": len(buyable_range_mismatches),
            "factor_range_mismatch_count": len(factor_range_mismatches),
            "terminal_range_examples": terminal_symbols[:20],
        },
        errors,
        limitations,
    )


def _float_array(frame: pd.DataFrame, field: str) -> np.ndarray:
    return pd.to_numeric(frame[field], errors="coerce").to_numpy(dtype=np.float64, copy=False)


def audit_symbol(
    source_path: Path,
    calendar_positions: dict[pd.Timestamp, int],
    instrument_ranges: dict[str, tuple[pd.Timestamp, pd.Timestamp]],
    qlib_dir: Path,
) -> dict[str, Any]:
    """Audit one Parquet file and every matching Qlib binary feature."""

    symbol = source_path.stem.upper()
    result: dict[str, Any] = {"symbol": symbol, "rows": 0, "errors": [], "mismatches": {}}
    try:
        frame = pd.read_parquet(source_path)
    except Exception as exc:  # pragma: no cover - depends on damaged local files
        result["errors"].append(f"cannot read Parquet: {type(exc).__name__}: {exc}")
        return result

    result["rows"] = len(frame)
    if tuple(frame.columns) != RAW_COLUMNS:
        result["errors"].append(f"schema mismatch: {list(frame.columns)}")
        return result
    if frame.empty:
        result["errors"].append("source file is empty")
        return result
    if set(frame["symbol"].astype(str).str.upper()) != {symbol}:
        result["errors"].append("symbol column does not match filename")

    dates = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    if dates.isna().any():
        result["errors"].append(f"invalid dates: {int(dates.isna().sum())}")
        return result
    if dates.duplicated().any():
        result["errors"].append(f"duplicate dates: {int(dates.duplicated().sum())}")
    if not dates.is_monotonic_increasing:
        result["errors"].append("dates are not increasing")
    positions = np.array([calendar_positions.get(date, -1) for date in dates], dtype=np.int64)
    if (positions < 0).any():
        result["errors"].append(f"dates absent from Qlib calendar: {int((positions < 0).sum())}")
        return result

    source_range = (dates.iloc[0], dates.iloc[-1])
    if symbol not in instrument_ranges:
        result["errors"].append("missing from instruments/all.txt")
    elif instrument_ranges[symbol] != source_range:
        result["errors"].append(
            f"instrument range {instrument_ranges[symbol]} differs from Parquet range {source_range}"
        )

    numeric = {field: _float_array(frame, field) for field in FEATURE_FIELDS}
    for field, values in numeric.items():
        if field == "vwap":
            invalid = ~np.isfinite(values) & (numeric["volume"] > 0)
        else:
            invalid = ~np.isfinite(values)
        if invalid.any():
            result["errors"].append(f"{field} has {int(invalid.sum())} unexpected non-finite values")
    if (np.column_stack([numeric[field] for field in PRICE_FIELDS]) <= 0).any(axis=1).any():
        result["errors"].append("non-positive OHLC value")
    if (numeric["high"] < numeric["low"]).any():
        result["errors"].append("high below low")
    if (numeric["high"] < np.maximum(numeric["open"], numeric["close"])).any():
        result["errors"].append("high below open or close")
    if (numeric["low"] > np.minimum(numeric["open"], numeric["close"])).any():
        result["errors"].append("low above open or close")
    if (numeric["volume"] < 0).any() or (numeric["amount"] < 0).any():
        result["errors"].append("negative volume or amount")
    nonzero_volume = numeric["volume"] > 0
    expected_vwap = numeric["amount"][nonzero_volume] / (numeric["volume"][nonzero_volume] * 100.0)
    if not np.isclose(numeric["vwap"][nonzero_volume], expected_vwap, rtol=1e-7, atol=1e-7).all():
        result["errors"].append("vwap differs from amount / (volume * 100)")

    feature_dir = qlib_dir / "features" / symbol.lower()
    if not feature_dir.is_dir():
        result["errors"].append("missing Qlib feature directory")
        return result
    qlib_fields = {path.name.removesuffix(".day.bin") for path in feature_dir.glob("*.day.bin")}
    if qlib_fields != set(FEATURE_FIELDS):
        result["errors"].append(
            f"Qlib feature field mismatch: missing={sorted(set(FEATURE_FIELDS) - qlib_fields)}, "
            f"extra={sorted(qlib_fields - set(FEATURE_FIELDS))}"
        )

    first_position, final_position = int(positions[0]), int(positions[-1])
    expected_length = final_position - first_position + 1
    if expected_length <= 0:
        result["errors"].append("invalid calendar span")
        return result
    relative_positions = positions - first_position
    for field, raw_values in numeric.items():
        bin_path = feature_dir / f"{field}.day.bin"
        if not bin_path.exists():
            continue
        dumped = np.fromfile(bin_path, dtype="<f4")
        if dumped.size != expected_length + 1:
            result["mismatches"][field] = f"binary length {dumped.size}, expected {expected_length + 1}"
            continue
        if int(dumped[0]) != first_position:
            result["mismatches"][field] = f"binary start index {dumped[0]}, expected {first_position}"
            continue
        expected = np.full(expected_length, np.nan, dtype=np.float32)
        expected[relative_positions] = raw_values.astype(np.float32)
        matches = np.isclose(dumped[1:], expected, rtol=1e-6, atol=1e-7, equal_nan=True)
        if not matches.all():
            result["mismatches"][field] = f"{int((~matches).sum())} binary values differ from source"
    if result["mismatches"]:
        result["errors"].append("Qlib binary values differ from Parquet")
    return result


def audit_qllib_reader(
    provider_uri: Path, raw_dir: Path, calendar: pd.DatetimeIndex, symbols: list[str]
) -> list[str]:
    """Exercise Qlib's reader on deterministic tails, not just binary bytes."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import qlib
    from qlib.data import D

    qlib.init(provider_uri=str(provider_uri), region="cn", kernels=1)
    start, end = calendar[-5], calendar[-1]
    qlib_frame = D.features(symbols, [f"${field}" for field in FEATURE_FIELDS], start_time=start, end_time=end, freq="day")
    errors: list[str] = []
    for symbol in symbols:
        if symbol not in qlib_frame.index.get_level_values("instrument"):
            errors.append(f"Qlib reader returned no latest-tail rows for {symbol}")
            continue
        source = pd.read_parquet(raw_dir / f"{symbol.lower()}.parquet")
        source["date"] = pd.to_datetime(source["date"])
        expected = source[source["date"].between(start, end)].set_index("date")[list(FEATURE_FIELDS)]
        actual = qlib_frame.xs(symbol, level="instrument")
        expected = expected.reindex(actual.index)
        if not np.isclose(
            actual.to_numpy(dtype=float), expected.to_numpy(dtype=float), rtol=1e-6, atol=1e-7, equal_nan=True
        ).all():
            errors.append(f"Qlib reader mismatch for {symbol}")
    return errors


def audit_source_tail(raw_dir: Path, symbols: list[str], end: pd.Timestamp) -> list[str]:
    """Compare deterministic latest tails with the public source used by the pipeline."""

    pipeline_path = REPO_ROOT / "scripts" / "a_share_data_pipeline.py"
    spec = importlib.util.spec_from_file_location("a_share_pipeline_audit", pipeline_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot import pipeline module: {pipeline_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    client = module.EastmoneyClient(timeout=20, retries=3, delay=0.08)
    start = (end - pd.Timedelta(days=14)).date()
    errors: list[str] = []
    for symbol in symbols:
        instrument = module.Instrument(symbol, symbol[-6:], "audit", "main", None, None, None, False)
        try:
            fetched = client.daily_bars(instrument, start, end.date(), "qfq")
        except Exception as exc:  # pragma: no cover - depends on remote source
            errors.append(f"source query failed for {symbol}: {type(exc).__name__}: {exc}")
            continue
        stored = pd.read_parquet(raw_dir / f"{symbol.lower()}.parquet")
        stored["date"] = pd.to_datetime(stored["date"])
        compared = fetched.merge(stored, on=["date", "symbol"], suffixes=("_source", "_stored"))
        if fetched.empty or compared.empty:
            errors.append(f"source tail has no overlap for {symbol}")
            continue
        for field in FEATURE_FIELDS:
            left, right = f"{field}_source", f"{field}_stored"
            if not np.isclose(compared[left], compared[right], rtol=1e-7, atol=1e-7, equal_nan=True).all():
                errors.append(f"source tail mismatch for {symbol} field {field}")
                break
    return errors


def run_audit(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Audit every local data file and return a JSON-safe report plus exit status."""

    raw_dir = Path(args.raw_dir).expanduser().resolve()
    qlib_dir = Path(args.qlib_dir).expanduser().resolve()
    calendar = read_calendar(qlib_dir / "calendars" / "day.txt")
    calendar_positions = {date: index for index, date in enumerate(calendar)}
    instrument_ranges = read_instrument_ranges(qlib_dir / "instruments" / "all.txt")
    raw_files = sorted(raw_dir.glob("*.parquet"))
    failures: list[str] = []
    if not raw_files:
        raise ValueError(f"no Parquet files found under {raw_dir}")

    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = [
            executor.submit(audit_symbol, path, calendar_positions, instrument_ranges, qlib_dir) for path in raw_files
        ]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: item["symbol"])

    failed_symbols = [item for item in results if item["errors"]]
    row_count = sum(item["rows"] for item in results)
    raw_symbols = {item["symbol"] for item in results}
    if raw_symbols != set(instrument_ranges):
        failures.append(
            f"raw/instruments mismatch: raw_only={len(raw_symbols - set(instrument_ranges))}, "
            f"instrument_only={len(set(instrument_ranges) - raw_symbols)}"
        )
    if failed_symbols:
        failures.append(f"{len(failed_symbols)} symbols failed source or binary audit")

    buyable = read_instrument_ranges(qlib_dir / "instruments" / "buyable_main_chinext.txt")
    factor = read_instrument_ranges(qlib_dir / "instruments" / "factor_main_chinext_star.txt")
    buyable_star = [symbol for symbol in buyable if symbol[-6:].startswith(("688", "689"))]
    factor_star = [symbol for symbol in factor if symbol[-6:].startswith(("688", "689"))]
    if not set(buyable).issubset(raw_symbols) or not set(factor).issubset(raw_symbols):
        failures.append("custom universe contains a symbol absent from raw data")
    if buyable_star:
        failures.append(f"buyable universe contains {len(buyable_star)} STAR instruments")
    if not factor_star:
        failures.append("factor universe contains no STAR instruments")

    temporal_universe, temporal_errors, temporal_limitations = audit_temporal_universe_coverage(
        Path(args.universe_snapshot).expanduser().resolve(), calendar, instrument_ranges, buyable, factor
    )
    if temporal_errors:
        failures.extend(temporal_errors)

    active_symbols = sorted(
        symbol for symbol, (_, finish) in instrument_ranges.items() if finish >= calendar[-1]
    )
    sample_symbols = evenly_spaced(active_symbols, args.qlib_samples)
    reader_errors = audit_qllib_reader(qlib_dir, raw_dir, calendar, sample_symbols)
    if reader_errors:
        failures.extend(reader_errors)
    source_symbols = evenly_spaced(active_symbols, args.source_samples)
    source_errors = audit_source_tail(raw_dir, source_symbols, calendar[-1]) if source_symbols else []
    if source_errors:
        failures.extend(source_errors)

    restoration_factor_files = list((qlib_dir / "features").glob("*/factor.day.bin"))
    limitations: list[str] = list(temporal_limitations)
    if len(restoration_factor_files) != len(raw_files):
        limitations.append(
            "Qlib restoration factors are absent; Alpha features are usable, but exact A-share lot-size backtests are not."
        )
        if args.require_restoration_factor:
            failures.append("restoration factor is required but not present for every instrument")

    mismatch_counts = Counter()
    for item in failed_symbols:
        mismatch_counts.update(item["mismatches"].keys())
    report: dict[str, Any] = {
        "status": "failed" if failures else "passed_with_limitations" if limitations else "passed",
        "raw_dir": str(raw_dir),
        "qlib_dir": str(qlib_dir),
        "calendar": {"days": len(calendar), "start": calendar[0].date().isoformat(), "end": calendar[-1].date().isoformat()},
        "coverage": {"raw_files": len(raw_files), "instruments_all": len(instrument_ranges), "rows": row_count},
        "universes": {
            "buyable_main_chinext": len(buyable),
            "buyable_star_count": len(buyable_star),
            "factor_main_chinext_star": len(factor),
            "factor_star_count": len(factor_star),
        },
        "temporal_universe": temporal_universe,
        "qlib_binary": {"fields": list(FEATURE_FIELDS), "mismatch_fields": dict(mismatch_counts)},
        "runtime_reader": {"samples": sample_symbols, "errors": reader_errors},
        "source_tail": {"samples": source_symbols, "errors": source_errors},
        "restoration_factor_files": len(restoration_factor_files),
        "limitations": limitations,
        "failures": failures,
        "failed_symbols": failed_symbols[: args.max_error_examples],
    }
    return report, 0 if not failures else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", default=str(RAW_DIR), help="source Parquet directory")
    parser.add_argument("--qlib-dir", default=str(QLIB_DIR), help="Qlib binary provider directory")
    parser.add_argument("--workers", type=int, default=3, help="parallel file-audit workers")
    parser.add_argument("--qlib-samples", type=int, default=32, help="Qlib runtime reader samples")
    parser.add_argument("--source-samples", type=int, default=24, help="public-source tail comparison samples; set 0 to skip")
    parser.add_argument(
        "--universe-snapshot",
        default=str(DEFAULT_UNIVERSE_SNAPSHOT),
        help="current provider universe snapshot used to validate locally retained trading ranges",
    )
    parser.add_argument("--require-restoration-factor", action="store_true", help="fail if factor.day.bin is absent")
    parser.add_argument("--max-error-examples", type=int, default=20, help="maximum failed-symbol details in JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="JSON report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report, status = run_audit(args)
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return status


if __name__ == "__main__":
    sys.exit(main())
