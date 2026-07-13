#!/usr/bin/env python3
"""Recover a completed A-share daily close when the primary source is unavailable.

This is a narrow, auditable fallback for the repository's daily data pipeline:
it reads the existing local universe snapshot, fetches only one completed
session from Tencent's public quote endpoint, and records a recovery manifest.
The normal Eastmoney ``sync`` remains authoritative and will refresh this tail
again when it is available.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from a_share_data_pipeline import (  # noqa: E402
    DATA_ROOT,
    METADATA_DIR,
    PipelineError,
    PipelineLock,
    Instrument,
    materialize_qlib,
    merge_and_save_bars,
)


UNIVERSE_PATH = METADATA_DIR / "universe_latest.json"
RECOVERY_DIR = METADATA_DIR / "recoveries"
QUOTE_URL = "https://qt.gtimg.cn/q="
QUOTE_PATTERN = re.compile(r"v_(?P<symbol>[a-z]{2}\d{6})=\"(?P<values>[^\"]*)\";")
HEADERS = {
    "Accept": "*/*",
    "Referer": "https://gu.qq.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
}


def tencent_symbol(instrument: Instrument) -> str:
    """Return Tencent's lower-case exchange/code identifier."""

    return ("sh" if instrument.symbol.startswith("SH") else "sz") + instrument.code


def _finite_number(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"non-finite numeric value {value!r}")
    return number


def parse_quote_line(symbol: str, raw: str, expected_date: dt.date) -> dict[str, Any] | None:
    """Parse one Tencent close quote, returning None when it is not the target day."""

    values = raw.split("~")
    # Indexes are the documented/observed quote positions used here: latest,
    # previous close, open, volume, quote timestamp, daily change/percent,
    # high/low, ``price/volume/amount`` and turnover rate.
    if len(values) <= 38:
        raise ValueError(f"incomplete Tencent quote for {symbol}: {len(values)} fields")
    timestamp = values[30]
    if len(timestamp) < 8 or not timestamp[:8].isdigit():
        return None
    quote_date = dt.datetime.strptime(timestamp[:8], "%Y%m%d").date()
    if quote_date != expected_date:
        return None
    close = _finite_number(values[3])
    previous_close = _finite_number(values[4])
    open_price = _finite_number(values[5])
    volume = _finite_number(values[6])
    high = _finite_number(values[33])
    low = _finite_number(values[34])
    amount_parts = values[35].split("/")
    if len(amount_parts) != 3:
        raise ValueError(f"missing amount tuple for {symbol}")
    amount = _finite_number(amount_parts[2])
    turnover = _finite_number(values[38])
    if min(open_price, high, low, close, volume, amount) <= 0:
        raise ValueError(f"invalid non-positive close quote for {symbol}")
    return {
        "date": pd.Timestamp(expected_date),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "amount": amount,
        "vwap": amount / (volume * 100.0),
        "change": close - previous_close,
        "pct_chg": _finite_number(values[32]),
        "turnover": turnover,
    }


def fetch_quotes(symbols: Iterable[str], expected_date: dt.date, batch_size: int) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Fetch complete-session quotes in batches and retain parse failures for audit."""

    ordered = list(symbols)
    quotes: dict[str, dict[str, Any]] = {}
    failures: dict[str, str] = {}
    session = requests.Session()
    session.headers.update(HEADERS)
    for offset in range(0, len(ordered), batch_size):
        batch = ordered[offset : offset + batch_size]
        try:
            response = session.get(QUOTE_URL + ",".join(batch), timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            for symbol in batch:
                failures[symbol] = f"request failed: {type(exc).__name__}: {exc}"
            continue
        received: set[str] = set()
        for match in QUOTE_PATTERN.finditer(response.text):
            symbol = match.group("symbol")
            if symbol not in batch:
                continue
            received.add(symbol)
            try:
                parsed = parse_quote_line(symbol, match.group("values"), expected_date)
                if parsed is None:
                    failures[symbol] = "no completed quote for requested date"
                else:
                    quotes[symbol] = parsed
            except (TypeError, ValueError) as exc:
                failures[symbol] = f"parse failed: {exc}"
        for symbol in set(batch) - received:
            failures.setdefault(symbol, "symbol absent from quote response")
        print(f"fetched {min(offset + len(batch), len(ordered))}/{len(ordered)} cached-universe quotes")
    return quotes, failures


def _atomic_write_json(destination: Path, payload: dict[str, Any]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(destination)


def run_recovery(target: dt.date, batch_size: int, dump_workers: int) -> dict[str, Any]:
    """Merge one Tencent close into local sources and rematerialize Qlib safely."""

    if not UNIVERSE_PATH.exists():
        raise PipelineError(f"cached universe snapshot is missing: {UNIVERSE_PATH}")
    universe = [Instrument(**item) for item in json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))]
    selected = [item for item in universe if item.board in {"main", "chinext"}]
    if not selected:
        raise PipelineError("cached universe contains no main-board or ChiNext instruments")
    symbol_to_instrument = {tencent_symbol(item): item for item in selected}
    started = dt.datetime.now(dt.timezone.utc)
    with PipelineLock(DATA_ROOT / ".a_share_pipeline.lock"):
        quotes, failures = fetch_quotes(symbol_to_instrument, target, batch_size)
        updated = 0
        for source_symbol, quote in quotes.items():
            instrument = symbol_to_instrument[source_symbol]
            destination = DATA_ROOT / "raw" / "a_share" / "daily" / f"{instrument.symbol.lower()}.parquet"
            bar = pd.DataFrame([quote])
            merge_and_save_bars(destination, bar, end=target)
            updated += 1
        if updated == 0:
            raise PipelineError(f"Tencent recovery found no usable completed quotes for {target}")
        qlib = materialize_qlib(universe, dump_workers)
    completed = dt.datetime.now(dt.timezone.utc)
    manifest = {
        "status": "completed",
        "source": "Tencent public close quote fallback",
        "source_url": QUOTE_URL,
        "target_date": target.isoformat(),
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "cached_universe_path": str(UNIVERSE_PATH.resolve()),
        "cached_universe_selected": len(selected),
        "updated_symbols": updated,
        "failed_or_stale_symbols": len(failures),
        "failures": failures,
        "qlib": qlib,
        "limitations": [
            "This is a one-session source fallback after the primary Eastmoney endpoints were unavailable.",
            "The normal Eastmoney tail refresh remains authoritative and should overwrite/verify this date once the primary source recovers.",
            "The cached universe is not a new point-in-time listing snapshot.",
        ],
    }
    stamp = completed.strftime("%Y%m%dT%H%M%SZ")
    destination = RECOVERY_DIR / f"tencent_close_{target.isoformat()}_{stamp}.json"
    _atomic_write_json(destination, manifest)
    _atomic_write_json(METADATA_DIR / "latest_tencent_close_recovery.json", manifest)
    manifest["path"] = str(destination.resolve())
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="completed A-share session in YYYY-MM-DD form")
    parser.add_argument("--batch-size", type=int, default=80)
    parser.add_argument("--dump-workers", type=int, default=1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.batch_size < 1 or args.dump_workers < 1:
        raise ValueError("--batch-size and --dump-workers must be positive")
    report = run_recovery(dt.date.fromisoformat(args.date), args.batch_size, args.dump_workers)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
