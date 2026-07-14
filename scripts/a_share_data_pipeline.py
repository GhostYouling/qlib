#!/usr/bin/env python3
"""Download China A-share daily data and materialize it as a Qlib data set.

The pipeline deliberately keeps two universes:

* ``buyable_main_chinext``: Shanghai/Shenzhen main-board and ChiNext stocks.
* ``factor_main_chinext_star``: the buyable universe plus STAR Market stocks.

The latter is useful when STAR Market prices are used as explanatory variables,
while the former remains the universe that a stock-selection strategy may hold.

All generated data lives under ``<repository>/data``.  The script uses public
Eastmoney endpoints directly, so no username, password, or API token is
required.  It is intentionally a data-ingestion tool, not investment advice.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import fcntl
import json
import logging
import os
import random
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data"
RAW_DIR = DATA_ROOT / "raw" / "a_share" / "daily"
METADATA_DIR = DATA_ROOT / "metadata"
RUNS_DIR = METADATA_DIR / "runs"
LOG_DIR = DATA_ROOT / "logs"
QLIB_DIR = DATA_ROOT / "qlib" / "cn_a_share"
LOCK_PATH = DATA_ROOT / ".a_share_pipeline.lock"
PRICE_BASIS_MANIFEST = QLIB_DIR / "price_basis.json"

# Eleven years of daily cross-sectional history is enough for the initial
# stock-selection baseline while fitting the combined raw + Qlib data set on a
# typical laptop.  Users with more disk can request earlier dates explicitly.
DEFAULT_START_DATE = "2015-01-01"
DEFAULT_REFRESH_DAYS = 45
DEFAULT_WORKERS = 3

POINT_IN_TIME_PRICE_BASIS = "close_known_raw_pct_chg_chain_v1"
POINT_IN_TIME_RAW_COLUMNS = (
    "raw_open",
    "raw_high",
    "raw_low",
    "raw_close",
    "raw_volume",
    "raw_vwap",
)
POINT_IN_TIME_EXCLUDED_FIELDS = (
    "date",
    "symbol",
    "price_basis",
    "daily_source",
    *POINT_IN_TIME_RAW_COLUMNS,
)
NON_FAILURE_PRICE_BASIS_COUNTS = {"source_vwap_quarantined_rows"}

UNIVERSE_URL = "https://82.push2.eastmoney.com/api/qt/clist/get"
KLINE_URLS = (
    "https://63.push2his.eastmoney.com/api/qt/stock/kline/get",
    "http://push2his.eastmoney.com/api/qt/stock/kline/get",
)
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://quote.eastmoney.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
}

# Board prefixes are documented here rather than inferred from a mutable name
# field returned by the data provider.  This intentionally excludes B shares,
# Beijing Stock Exchange, ETFs, funds, and indices.
MAIN_BOARD_PREFIXES = ("600", "601", "603", "605", "000", "001", "002", "003")
CHINEXT_PREFIXES = ("300", "301")
STAR_PREFIXES = ("688", "689")


class PipelineError(RuntimeError):
    """A recoverable data-source or materialization failure."""


@dataclass(frozen=True)
class Instrument:
    """A listed A-share instrument returned by the universe endpoint."""

    symbol: str
    code: str
    name: str
    board: str
    listing_date: str | None
    market_cap: float | None
    float_market_cap: float | None
    is_st: bool


@dataclass
class DownloadResult:
    """A single symbol's download outcome, persisted in the run manifest."""

    symbol: str
    status: str
    rows: int = 0
    first_date: str | None = None
    last_date: str | None = None
    error: str | None = None


class PipelineLock:
    """An advisory process lock so scheduled runs cannot corrupt data output."""

    def __init__(self, path: Path):
        self.path = path
        self._file: Any | None = None

    def __enter__(self) -> "PipelineLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a+")
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PipelineError(
                f"another A-share pipeline run holds {self.path}; refusing to overlap"
            ) from exc
        self._file.write(f"pid={os.getpid()} started_at={dt.datetime.now(dt.timezone.utc).isoformat()}\n")
        self._file.flush()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._file is not None:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            self._file.close()


def parse_date(value: str) -> dt.date:
    """Parse a CLI ISO date into a date, with a useful argparse error upstream."""

    return dt.date.fromisoformat(value)


def latest_completed_session_date(now: dt.datetime | None = None) -> dt.date:
    """Return a conservative daily-data cutoff in the local China/Singapore time zone.

    A-share daily bars are provisional before the close. The workspace time
    zone matches China Standard Time, so before 15:30 on a weekday the most
    recent safe date is the preceding weekday. Exchange holidays simply leave
    the existing calendar unchanged, which is safer than ingesting a live bar.
    """

    local_now = now or dt.datetime.now()
    cutoff = local_now.date()
    if local_now.weekday() < 5 and local_now.time() < dt.time(15, 30):
        cutoff -= dt.timedelta(days=1)
    while cutoff.weekday() >= 5:
        cutoff -= dt.timedelta(days=1)
    return cutoff


def qlib_symbol(code: str) -> str:
    """Convert a six-digit A-share code into Qlib's ``SH/SZ`` notation."""

    if code.startswith(("6", "9")):
        return f"SH{code}"
    return f"SZ{code}"


def classify_board(code: str) -> str | None:
    """Classify the requested boards and reject all non-target instruments."""

    if code.startswith(MAIN_BOARD_PREFIXES):
        return "main"
    if code.startswith(CHINEXT_PREFIXES):
        return "chinext"
    if code.startswith(STAR_PREFIXES):
        return "star"
    return None


def is_st_name(name: str) -> bool:
    """Return whether an exchange-provided name carries an ST risk marker."""

    normalized = name.upper().replace(" ", "")
    return normalized.startswith("ST") or normalized.startswith("*ST")


def valid_listing_date(value: Any) -> str | None:
    """Normalize the provider's optional YYYYMMDD listing date."""

    if value in (None, "", 0, "0"):
        return None
    raw = str(value).strip()
    if len(raw) == 8 and raw.isdigit():
        try:
            return dt.datetime.strptime(raw, "%Y%m%d").date().isoformat()
        except ValueError:
            return None
    return None


class EastmoneyClient:
    """Small, retrying adapter around the public Eastmoney JSON endpoints."""

    def __init__(self, timeout: float = 30.0, retries: int = 4, delay: float = 0.35):
        self.timeout = timeout
        self.retries = retries
        self.delay = delay

    def _get_json(self, urls: Iterable[str], params: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        for attempt in range(self.retries):
            for url in urls:
                try:
                    response = requests.get(url, params=params, headers=HEADERS, timeout=self.timeout)
                    response.raise_for_status()
                    payload = response.json()
                    if payload.get("rc") not in (0, None):
                        raise PipelineError(f"provider returned rc={payload.get('rc')}")
                    time.sleep(self.delay + random.uniform(0, self.delay / 3))
                    return payload
                except (requests.RequestException, ValueError, PipelineError) as exc:
                    errors.append(f"{url}: {type(exc).__name__}: {exc}")
            time.sleep(min(16.0, (2**attempt) + random.uniform(0, 0.5)))
        raise PipelineError("; ".join(errors[-len(tuple(urls)) :]))

    def list_instruments(self) -> list[Instrument]:
        """Fetch the current A-share list and retain only the requested boards."""

        params = {
            "pn": 1,
            # This endpoint silently caps page size at 100 even if a larger
            # value is supplied, so explicitly page through the whole list.
            "pz": 100,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            # SH/SZ/BJ A-share groups.  Prefix filtering below is the authoritative
            # scope control and excludes BJ and any accidental non-equity results.
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
            "fields": "f12,f14,f20,f21,f26",
        }
        rows: list[dict[str, Any]] = []
        expected_total: int | None = None
        page = 1
        while True:
            params["pn"] = page
            payload = self._get_json((UNIVERSE_URL,), params)
            data = payload.get("data") or {}
            page_rows = data.get("diff") or []
            if expected_total is None:
                expected_total = int(data.get("total") or 0)
            if not page_rows:
                break
            rows.extend(page_rows)
            if expected_total and len(rows) >= expected_total:
                break
            page += 1
        instruments: list[Instrument] = []
        for row in rows:
            code = str(row.get("f12") or "").zfill(6)
            board = classify_board(code)
            if board is None:
                continue
            name = str(row.get("f14") or "")
            instruments.append(
                Instrument(
                    symbol=qlib_symbol(code),
                    code=code,
                    name=name,
                    board=board,
                    listing_date=valid_listing_date(row.get("f26")),
                    market_cap=_float_or_none(row.get("f20")),
                    float_market_cap=_float_or_none(row.get("f21")),
                    is_st=is_st_name(name),
                )
            )
        if not instruments:
            raise PipelineError("the universe endpoint returned no requested A-share instruments")
        return sorted(instruments, key=lambda item: item.symbol)

    def daily_bars(self, instrument: Instrument, start: dt.date, end: dt.date, adjust: str) -> pd.DataFrame:
        """Return adjusted daily OHLCV data in a Qlib-ready column layout."""

        adjust_code = {"point_in_time": "0", "raw": "0", "qfq": "1", "hfq": "2"}[adjust]
        params = {
            "secid": _eastmoney_secid(instrument),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101",
            "fqt": adjust_code,
            "beg": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
        }
        payload = self._get_json(KLINE_URLS, params)
        data = payload.get("data") or {}
        rows = data.get("klines") or []
        if not rows:
            return pd.DataFrame(columns=_BAR_COLUMNS)

        parsed: list[list[Any]] = []
        for raw in rows:
            values = str(raw).split(",")
            if len(values) < 11:
                continue
            try:
                volume = float(values[5])
                amount = float(values[6])
                # Eastmoney reports A-share volume in lots (100 shares).  Convert
                # amount / volume into an actual price-level VWAP for Alpha158.
                vwap = amount / (volume * 100.0) if volume > 0 else float("nan")
                parsed.append(
                    [
                        values[0],
                        float(values[1]),
                        float(values[3]),
                        float(values[4]),
                        float(values[2]),
                        volume,
                        amount,
                        vwap,
                        float(values[9]),
                        float(values[8]),
                        float(values[10]),
                    ]
                )
            except (TypeError, ValueError):
                continue
        bars = pd.DataFrame(parsed, columns=_BAR_COLUMNS)
        if bars.empty:
            return bars
        bars["date"] = pd.to_datetime(bars["date"], errors="coerce")
        bars = bars.dropna(subset=["date", "open", "high", "low", "close"])
        bars = bars.loc[~invalid_price_mask(bars)]
        bars.insert(1, "symbol", instrument.symbol)
        bars = bars.sort_values("date").drop_duplicates("date", keep="last")
        if adjust == "point_in_time":
            for raw_column, source_column in zip(
                POINT_IN_TIME_RAW_COLUMNS,
                ("open", "high", "low", "close", "volume", "vwap"),
            ):
                bars[raw_column] = bars[source_column]
            bars["price_basis"] = POINT_IN_TIME_PRICE_BASIS
            bars["daily_source"] = "eastmoney"
            bars = rebuild_point_in_time_prices(bars)
        return bars


class BaoStockClient:
    """Sequential BaoStock daily adapter used for independent recovery."""

    def __init__(self) -> None:
        try:
            import baostock as bs  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise PipelineError(
                "BaoStock source requires `python -m pip install baostock==0.9.3`"
            ) from exc
        self._bs = bs
        self._login()

    def _login(self) -> None:
        """Open or refresh the process-local BaoStock session."""

        login = self._bs.login()
        if login.error_code != "0":
            raise PipelineError(f"BaoStock login failed: {login.error_code} {login.error_msg}")

    def close(self) -> None:
        """Close the process-global BaoStock session."""

        self._bs.logout()

    @staticmethod
    def _symbol(instrument: Instrument) -> str:
        market = "sh" if instrument.symbol.startswith("SH") else "sz"
        return f"{market}.{instrument.code}"

    def list_instruments(self, as_of: dt.date) -> list[Instrument]:
        """Return the current requested A-share boards from BaoStock."""

        response = self._bs.query_all_stock(day=as_of.isoformat())
        if response.error_code != "0":
            raise PipelineError(
                f"BaoStock universe query failed: {response.error_code} {response.error_msg}"
            )
        rows: list[list[str]] = []
        while response.next():
            rows.append(response.get_row_data())
        prior_path = METADATA_DIR / "universe_latest.json"
        prior = {}
        if prior_path.exists():
            prior = {
                str(item.get("symbol", "")).upper(): item
                for item in json.loads(prior_path.read_text(encoding="utf-8"))
            }
        instruments: list[Instrument] = []
        for code_with_market, _trade_status, name in rows:
            market, separator, code = str(code_with_market).lower().partition(".")
            if separator != "." or len(code) != 6 or not code.isdigit():
                continue
            if market == "sh" and not code.startswith((*MAIN_BOARD_PREFIXES[:4], *STAR_PREFIXES)):
                continue
            if market == "sz" and not code.startswith((*MAIN_BOARD_PREFIXES[4:], *CHINEXT_PREFIXES)):
                continue
            board = classify_board(code)
            if board is None:
                continue
            symbol = f"{market.upper()}{code}"
            previous = prior.get(symbol) or {}
            instruments.append(
                Instrument(
                    symbol=symbol,
                    code=code,
                    name=str(name),
                    board=board,
                    listing_date=previous.get("listing_date"),
                    market_cap=_float_or_none(previous.get("market_cap")),
                    float_market_cap=_float_or_none(previous.get("float_market_cap")),
                    is_st=is_st_name(str(name)),
                )
            )
        current_symbols = {item.symbol for item in instruments}
        for symbol, previous in prior.items():
            if symbol in current_symbols:
                continue
            try:
                historical = Instrument(**previous)
            except TypeError:
                continue
            if historical.board in {"main", "chinext", "star"}:
                instruments.append(historical)
        if not instruments:
            raise PipelineError("BaoStock returned no requested A-share instruments")
        return sorted(instruments, key=lambda item: item.symbol)

    def daily_bars(self, instrument: Instrument, start: dt.date, end: dt.date, adjust: str) -> pd.DataFrame:
        """Return BaoStock daily data in the same canonical source schema."""

        adjust_flag = {"point_in_time": "3", "raw": "3", "qfq": "2", "hfq": "1"}[adjust]
        fields = "date,code,open,high,low,close,preclose,volume,amount,turn,pctChg,isST"
        response = self._bs.query_history_k_data_plus(
            self._symbol(instrument),
            fields,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            frequency="d",
            adjustflag=adjust_flag,
        )
        if response.error_code == "10001001":
            # Long full-market recoveries can outlive a server-side session.
            # Refresh only this worker's connection and retry the same query.
            self._login()
            response = self._bs.query_history_k_data_plus(
                self._symbol(instrument),
                fields,
                start_date=start.isoformat(),
                end_date=end.isoformat(),
                frequency="d",
                adjustflag=adjust_flag,
            )
        if response.error_code != "0":
            raise PipelineError(
                f"BaoStock query failed for {instrument.symbol}: "
                f"{response.error_code} {response.error_msg}"
            )
        rows: list[list[str]] = []
        while response.next():
            rows.append(response.get_row_data())
        if not rows:
            return pd.DataFrame(columns=_BAR_COLUMNS)
        source = pd.DataFrame(rows, columns=response.fields)
        numeric_columns = [
            "open", "high", "low", "close", "preclose", "volume", "amount", "turn", "pctChg"
        ]
        source[numeric_columns] = source[numeric_columns].apply(pd.to_numeric, errors="coerce")
        source["date"] = pd.to_datetime(source["date"], errors="coerce")
        source["pctChg"] = fill_baostock_pct_chg(source)
        volume_lots = source["volume"] / 100.0
        bars = pd.DataFrame(
            {
                "date": source["date"],
                "symbol": instrument.symbol,
                "open": source["open"],
                "high": source["high"],
                "low": source["low"],
                "close": source["close"],
                "volume": volume_lots,
                "amount": source["amount"],
                "vwap": source["amount"].div(source["volume"].where(source["volume"].gt(0.0))),
                "change": source["close"] - source["preclose"],
                "pct_chg": source["pctChg"],
                "turnover": source["turn"],
            }
        ).dropna(subset=["date", "open", "high", "low", "close"])
        bars = bars.loc[~invalid_price_mask(bars)].sort_values("date").drop_duplicates("date", keep="last")
        if adjust == "point_in_time":
            for raw_column, source_column in zip(
                POINT_IN_TIME_RAW_COLUMNS,
                ("open", "high", "low", "close", "volume", "vwap"),
            ):
                bars[raw_column] = bars[source_column]
            bars["price_basis"] = POINT_IN_TIME_PRICE_BASIS
            bars["daily_source"] = "baostock"
            bars = rebuild_point_in_time_prices(bars)
        return bars


_BAR_COLUMNS = [
    "date",
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
]


def fill_baostock_pct_chg(source: pd.DataFrame) -> pd.Series:
    """Fill BaoStock's blank no-trade returns from its adjusted pre-close.

    BaoStock leaves ``pctChg`` blank on some zero-volume suspension rows even
    though ``preclose`` and ``close`` are present.  Its pre-close is the
    provider's same-session comparison basis, so the derived return remains
    close-known and preserves ex-date continuity.  Only the first usable row
    may fall back to zero because it is the chain's local anchor; an
    unresolvable gap later in the series remains invalid.
    """

    close = pd.to_numeric(source["close"], errors="coerce")
    preclose = pd.to_numeric(source["preclose"], errors="coerce")
    pct_chg = pd.to_numeric(source["pctChg"], errors="coerce").copy()
    derived = close.div(preclose.where(preclose.gt(0.0))).sub(1.0).mul(100.0)
    pct_chg = pct_chg.fillna(derived)
    usable = close.gt(0.0)
    if usable.any():
        first_index = usable[usable].index[0]
        if pd.isna(pct_chg.loc[first_index]):
            pct_chg.loc[first_index] = 0.0
    return pct_chg


def rebuild_point_in_time_prices(bars: pd.DataFrame) -> pd.DataFrame:
    """Build a close-known adjusted price index from raw bars and provider returns.

    A vendor's qfq history can subtract later cash distributions from earlier
    prices.  For high-dividend stocks this can push old prices close to zero
    and create impossible percentage returns.  The raw ``pct_chg``
    is instead chained in date order.  It is known at each close, remains
    independent of later corporate actions, and supplies an adjusted/raw
    restoration factor for Qlib execution.
    """

    required = {"date", "pct_chg", "amount", "turnover", "daily_source", *POINT_IN_TIME_RAW_COLUMNS}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise PipelineError("point-in-time price construction is missing columns: " + ", ".join(missing))
    result = bars.sort_values("date").drop_duplicates("date", keep="last").copy()
    numeric_columns = ["pct_chg", "amount", "turnover", *POINT_IN_TIME_RAW_COLUMNS]
    result[numeric_columns] = result[numeric_columns].apply(pd.to_numeric, errors="coerce")
    raw_prices = result[["raw_open", "raw_high", "raw_low", "raw_close"]]
    if raw_prices.isna().any(axis=None) or (raw_prices <= 0.0).any(axis=None):
        raise PipelineError("point-in-time price construction requires positive finite raw OHLC")
    gross_multiplier = 1.0 + result["pct_chg"] / 100.0
    if gross_multiplier.isna().any() or (gross_multiplier <= 0.0).any():
        raise PipelineError("point-in-time price construction requires finite pct_chg above -100%")
    adjusted_close = result["raw_close"].iloc[0] * gross_multiplier.iloc[1:].cumprod()
    result["close"] = pd.concat(
        [pd.Series([result["raw_close"].iloc[0]], index=result.index[:1]), adjusted_close]
    ).sort_index()
    result["factor"] = result["close"] / result["raw_close"]
    for adjusted_column, raw_column in (
        ("open", "raw_open"),
        ("high", "raw_high"),
        ("low", "raw_low"),
    ):
        result[adjusted_column] = result[raw_column] * result["factor"]
    source_vwap_invalid = raw_vwap_outside_ohlc_mask(result)
    result["vwap"] = result["raw_vwap"].where(~source_vwap_invalid) * result["factor"]
    result["volume"] = result["raw_volume"] / result["factor"]
    prior_adjusted_close = result["close"] / gross_multiplier
    result["change"] = result["close"] - prior_adjusted_close
    result["price_basis"] = POINT_IN_TIME_PRICE_BASIS
    if invalid_price_mask(result).any():
        raise PipelineError("point-in-time adjustment produced invalid OHLC relationships")
    return result


def raw_vwap_outside_ohlc_mask(bars: pd.DataFrame) -> pd.Series:
    """Identify source amount/volume pairs that cannot describe the source OHLC."""

    required = {"raw_low", "raw_high", "raw_volume", "raw_vwap"}
    if not required.issubset(bars.columns):
        return pd.Series(False, index=bars.index)
    numeric = bars[list(required)].apply(pd.to_numeric, errors="coerce")
    tolerance = 0.011 + numeric["raw_high"].abs() * 1e-6
    present = numeric["raw_volume"].gt(0.0) & numeric["raw_vwap"].notna()
    return present & (
        numeric["raw_vwap"].lt(numeric["raw_low"] - tolerance)
        | numeric["raw_vwap"].gt(numeric["raw_high"] + tolerance)
    )


def invalid_price_mask(bars: pd.DataFrame) -> pd.Series:
    """Identify unusable OHLC rows, including negative qfq artifacts.

    Eastmoney's qfq history can become negative for a small number of stocks
    after large cumulative cash distributions. Negative prices make price
    ratios and Qlib labels invalid, so represent those dates as unavailable
    rather than passing a fabricated tradable price into research.
    """

    required = ["open", "high", "low", "close"]
    if not set(required).issubset(bars.columns):
        return pd.Series(True, index=bars.index)
    prices = bars[required].apply(pd.to_numeric, errors="coerce")
    tolerance = 1e-8 + prices.abs().max(axis=1) * 1e-8
    return (
        prices.isna().any(axis=1)
        | (prices <= 0).any(axis=1)
        | (prices["high"] + tolerance < prices["low"])
        | (prices["high"] + tolerance < prices[["open", "close"]].max(axis=1))
        | (prices["low"] - tolerance > prices[["open", "close"]].min(axis=1))
    )


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _eastmoney_secid(instrument: Instrument) -> str:
    """Map Qlib's instrument notation to Eastmoney's market.code notation."""

    return f"1.{instrument.code}" if instrument.symbol.startswith("SH") else f"0.{instrument.code}"


def _latest_parquet_date(path: Path) -> dt.date | None:
    """Read the latest source date from compressed Parquet data."""

    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        dates = pd.read_parquet(path, columns=["date"])["date"]
        latest = pd.to_datetime(dates, errors="coerce").max()
        return latest.date() if not pd.isna(latest) else None
    except (OSError, ValueError, KeyError):
        return None


def _atomic_write_parquet(data: pd.DataFrame, destination: Path) -> None:
    """Atomically write compressed source data without filling the local disk."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".parquet", dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
    data.to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(destination)


def merge_and_save_bars(
    path: Path,
    new_bars: pd.DataFrame,
    end: dt.date | None = None,
    *,
    replace_existing: bool = False,
) -> pd.DataFrame:
    """Merge refreshed rows into a per-symbol source file, preserving latest data."""

    expected_symbol = path.stem.upper()
    new_bars = normalize_bar_symbols(new_bars, expected_symbol, source=f"new rows for {path.name}")
    if path.exists() and not replace_existing:
        old_bars = normalize_bar_symbols(
            pd.read_parquet(path), expected_symbol, source=f"existing rows in {path.name}"
        )
        combined = pd.concat([old_bars, new_bars], ignore_index=True)
    else:
        combined = new_bars.copy()
    combined["date"] = pd.to_datetime(combined["date"])
    combined = combined.sort_values("date").drop_duplicates("date", keep="last")
    if end is not None:
        combined = combined.loc[combined["date"] <= pd.Timestamp(end)].copy()
    if "price_basis" in combined:
        basis = combined["price_basis"].astype("string")
        source = combined.get("daily_source", pd.Series(pd.NA, index=combined.index)).astype("string")
        if (
            basis.isna().any()
            or not basis.eq(POINT_IN_TIME_PRICE_BASIS).all()
            or source.isna().any()
            or source.nunique() != 1
        ):
            raise PipelineError(
                f"{path.name} mixes legacy price bases or daily sources; "
                "rerun with --force-full --adjust point_in_time"
            )
        combined = rebuild_point_in_time_prices(combined)
    _atomic_write_parquet(combined, path)
    return combined


def normalize_bar_symbols(bars: pd.DataFrame, expected_symbol: str, *, source: str) -> pd.DataFrame:
    """Return bars with a canonical symbol column, rejecting conflicting identities.

    Source files are one symbol per filename. A recovery source may omit the
    redundant ``symbol`` field, but it must never relabel another instrument.
    """

    normalized = bars.copy()
    expected = expected_symbol.upper()
    if "symbol" not in normalized:
        normalized.insert(1, "symbol", expected)
        return normalized
    supplied = normalized["symbol"].astype("string").str.strip().str.upper()
    conflicting = supplied.notna() & supplied.ne("") & supplied.ne(expected)
    if conflicting.any():
        examples = sorted(supplied.loc[conflicting].dropna().unique())[:3]
        raise PipelineError(f"{source} has symbol values inconsistent with {expected}: {examples}")
    normalized["symbol"] = expected
    return normalized


def normalize_source_symbols(max_examples: int = 20) -> dict[str, Any]:
    """Restore missing redundant symbol fields without changing market values.

    Non-empty mismatched codes are treated as a hard error instead of being
    overwritten, so this repair cannot silently alter a stock's identity.
    """

    normalized_rows = 0
    affected: list[dict[str, Any]] = []
    files = sorted(RAW_DIR.glob("*.parquet"))
    for path in files:
        bars = pd.read_parquet(path)
        expected = path.stem.upper()
        if "symbol" not in bars:
            missing = pd.Series(True, index=bars.index)
        else:
            supplied = bars["symbol"].astype("string").str.strip().str.upper()
            conflicting = supplied.notna() & supplied.ne("") & supplied.ne(expected)
            if conflicting.any():
                examples = sorted(supplied.loc[conflicting].dropna().unique())[:3]
                raise PipelineError(f"{path.name} has symbol values inconsistent with {expected}: {examples}")
            missing = supplied.isna() | supplied.eq("")
        if not missing.any():
            continue
        repaired = normalize_bar_symbols(bars, expected, source=f"existing rows in {path.name}")
        _atomic_write_parquet(repaired, path)
        count = int(missing.sum())
        normalized_rows += count
        affected.append({"symbol": expected, "rows_normalized": count})
    return {
        "raw_files_checked": len(files),
        "symbols_affected": len(affected),
        "rows_normalized": normalized_rows,
        "affected_symbols": affected[:max_examples],
        "affected_symbol_count_not_shown": max(0, len(affected) - max_examples),
    }


def migrate_csv_source_files() -> int:
    """Migrate early CSV source files to compressed Parquet once."""

    migrated = 0
    for legacy_path in RAW_DIR.glob("*.csv"):
        destination = legacy_path.with_suffix(".parquet")
        if not destination.exists():
            legacy = pd.read_csv(legacy_path, parse_dates=["date"])
            _atomic_write_parquet(legacy, destination)
        legacy_path.unlink()
        migrated += 1
    return migrated


def sanitize_source_data(max_examples: int = 20) -> dict[str, Any]:
    """Remove legacy non-positive OHLC rows from local source Parquet files.

    The dropped dates are retained as NaN spans after Qlib materialization,
    matching Qlib's convention for unavailable trading data. A repair manifest
    records every affected symbol so the operation remains auditable.
    """

    removed_rows = 0
    affected: list[dict[str, Any]] = []
    files = sorted(RAW_DIR.glob("*.parquet"))
    for path in files:
        bars = pd.read_parquet(path)
        bad = invalid_price_mask(bars)
        if not bad.any():
            continue
        bad_dates = pd.to_datetime(bars.loc[bad, "date"]).dt.date.astype(str).tolist()
        cleaned = bars.loc[~bad].copy()
        if cleaned.empty:
            raise PipelineError(f"sanitizing {path.name} would remove every source row")
        _atomic_write_parquet(cleaned, path)
        removed_rows += int(bad.sum())
        affected.append({"symbol": path.stem.upper(), "rows_removed": int(bad.sum()), "dates": bad_dates})
    return {
        "raw_files_checked": len(files),
        "symbols_affected": len(affected),
        "rows_removed": removed_rows,
        "affected_symbols": affected[:max_examples],
        "affected_symbol_count_not_shown": max(0, len(affected) - max_examples),
    }


def prune_source_after(end: dt.date, max_examples: int = 20) -> dict[str, Any]:
    """Remove provisional source rows later than a completed-session cutoff."""

    removed_rows = 0
    affected: list[dict[str, Any]] = []
    files = sorted(RAW_DIR.glob("*.parquet"))
    cutoff = pd.Timestamp(end)
    for path in files:
        bars = pd.read_parquet(path)
        dates = pd.to_datetime(bars["date"])
        future = dates > cutoff
        if not future.any():
            continue
        cleaned = bars.loc[~future].copy()
        if cleaned.empty:
            raise PipelineError(f"pruning {path.name} would remove every source row")
        _atomic_write_parquet(cleaned, path)
        removed_rows += int(future.sum())
        affected.append(
            {
                "symbol": path.stem.upper(),
                "rows_removed": int(future.sum()),
                "first_removed_date": dates.loc[future].min().date().isoformat(),
                "last_removed_date": dates.loc[future].max().date().isoformat(),
            }
        )
    return {
        "cutoff": end.isoformat(),
        "raw_files_checked": len(files),
        "symbols_affected": len(affected),
        "rows_removed": removed_rows,
        "affected_symbols": affected[:max_examples],
        "affected_symbol_count_not_shown": max(0, len(affected) - max_examples),
    }


def price_basis_quality_counts(bars: pd.DataFrame) -> dict[str, int]:
    """Count violations of the point-in-time adjusted/raw data contract."""

    required = {
        "open",
        "high",
        "low",
        "close",
        "volume",
        "vwap",
        "pct_chg",
        "factor",
        "price_basis",
        "daily_source",
        *POINT_IN_TIME_RAW_COLUMNS,
    }
    if not required.issubset(bars.columns):
        return {"missing_contract_columns": len(required - set(bars.columns))}
    numeric = bars[[
        "open",
        "high",
        "low",
        "close",
        "volume",
        "vwap",
        "pct_chg",
        "factor",
        *POINT_IN_TIME_RAW_COLUMNS,
    ]].apply(pd.to_numeric, errors="coerce")
    tolerance = 0.011 + numeric["high"].abs() * 1e-6
    vwap_present = numeric["volume"].gt(0.0) & numeric["vwap"].notna()
    vwap_outside = vwap_present & (
        numeric["vwap"].lt(numeric["low"] - tolerance)
        | numeric["vwap"].gt(numeric["high"] + tolerance)
    )
    reconstructed_close = numeric["close"] / numeric["factor"]
    reconstruction_error = (
        reconstructed_close - numeric["raw_close"]
    ).abs() > (1e-6 + numeric["raw_close"].abs() * 1e-6)
    observed_return = numeric["close"].pct_change(fill_method=None) * 100.0
    return_error = observed_return.iloc[1:].sub(numeric["pct_chg"].iloc[1:]).abs().gt(1e-6)
    source_vwap_invalid = raw_vwap_outside_ohlc_mask(bars)
    source_vwap_unquarantined = source_vwap_invalid & numeric["vwap"].notna()
    return {
        "unsupported_price_basis_rows": int(
            (~bars["price_basis"].astype("string").eq(POINT_IN_TIME_PRICE_BASIS)).sum()
        ),
        "unsupported_daily_source_rows": int(
            (~bars["daily_source"].astype("string").isin({"eastmoney", "baostock"})).sum()
        ),
        "mixed_daily_source_rows": int(
            len(bars) if bars["daily_source"].astype("string").dropna().nunique() != 1 else 0
        ),
        "non_positive_or_missing_factor_rows": int(
            (numeric["factor"].isna() | numeric["factor"].le(0.0)).sum()
        ),
        "invalid_adjusted_ohlc_rows": int(invalid_price_mask(numeric).sum()),
        "adjusted_vwap_outside_ohlc_rows": int(vwap_outside.sum()),
        "source_vwap_unquarantined_rows": int(source_vwap_unquarantined.sum()),
        "source_vwap_quarantined_rows": int(
            (source_vwap_invalid & numeric["vwap"].isna()).sum()
        ),
        "raw_close_reconstruction_error_rows": int(reconstruction_error.sum()),
        "pct_chg_chain_error_rows": int(return_error.sum()),
    }


def audit_point_in_time_source(raw_dir: Path = RAW_DIR, max_examples: int = 20) -> dict[str, Any]:
    """Validate every source file before it can become a research provider."""

    files = sorted(raw_dir.glob("*.parquet"))
    totals: dict[str, int] = {}
    affected: list[dict[str, Any]] = []
    row_count = 0
    daily_sources: set[str] = set()
    for path in files:
        bars = pd.read_parquet(path)
        row_count += len(bars)
        if "daily_source" in bars:
            daily_sources.update(bars["daily_source"].astype("string").dropna().astype(str).unique())
        counts = price_basis_quality_counts(bars)
        for name, count in counts.items():
            totals[name] = totals.get(name, 0) + int(count)
        if any(counts.values()) and len(affected) < max_examples:
            affected.append({"symbol": path.stem.upper(), "violations": counts})
    if len(daily_sources) != 1:
        totals["mixed_daily_sources"] = max(1, len(daily_sources))
    failures = {
        name: count
        for name, count in totals.items()
        if count and name not in NON_FAILURE_PRICE_BASIS_COUNTS
    }
    return {
        "status": "passed" if files and not failures else "failed",
        "price_basis": POINT_IN_TIME_PRICE_BASIS,
        "daily_sources": sorted(daily_sources),
        "raw_files": len(files),
        "rows": row_count,
        "violations": totals,
        "affected_examples": affected,
        "failures": failures,
    }


def write_json(path: Path, value: Any) -> None:
    """Atomically save machine-readable metadata."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def write_universe_snapshot(instruments: list[Instrument], as_of: dt.date) -> None:
    """Persist the current universe snapshot and a stable latest copy."""

    records = [asdict(item) for item in instruments]
    write_json(METADATA_DIR / f"universe_{as_of.isoformat()}.json", records)
    write_json(METADATA_DIR / "universe_latest.json", records)


def _requested_symbols(value: str | None) -> set[str] | None:
    if not value:
        return None
    result: set[str] = set()
    for item in value.split(","):
        code = item.strip().upper()
        if not code:
            continue
        if len(code) == 6 and code.isdigit():
            result.add(qlib_symbol(code))
        elif len(code) == 8 and code[:2] in {"SH", "SZ"} and code[2:].isdigit():
            result.add(code)
        else:
            raise PipelineError(f"invalid --symbols value: {item!r}; use 600519 or SH600519")
    return result


def select_instruments(
    instruments: list[Instrument], scope: str, requested: set[str] | None
) -> list[Instrument]:
    """Apply the requested collection scope after the canonical board classification."""

    allowed = {"main", "chinext"} if scope == "buyable" else {"main", "chinext", "star"}
    selected = [item for item in instruments if item.board in allowed]
    if requested is not None:
        known = {item.symbol for item in selected}
        unknown = requested - known
        if unknown:
            raise PipelineError(f"requested symbols are outside this scope or not currently listed: {sorted(unknown)}")
        selected = [item for item in selected if item.symbol in requested]
    return selected


def download_instrument(
    client: EastmoneyClient,
    instrument: Instrument,
    start: dt.date,
    end: dt.date,
    refresh_days: int,
    force_full: bool,
    only_missing: bool,
    adjust: str,
) -> DownloadResult:
    """Download one symbol, refreshing a tail window to catch late corrections."""

    destination = RAW_DIR / f"{instrument.symbol.lower()}.parquet"
    latest = _latest_parquet_date(destination)
    if latest is not None and only_missing:
        if adjust != "point_in_time":
            return DownloadResult(instrument.symbol, "up_to_date", last_date=latest.isoformat())
        expected_source = "baostock" if isinstance(client, BaoStockClient) else "eastmoney"
        contract_matches = False
        try:
            contract = pd.read_parquet(destination, columns=["price_basis", "daily_source"])
            contract_matches = (
                contract["price_basis"].astype("string").eq(POINT_IN_TIME_PRICE_BASIS).all()
                and contract["daily_source"].astype("string").eq(expected_source).all()
            )
        except (OSError, ValueError, KeyError):
            contract_matches = False
        if contract_matches and latest >= end:
            return DownloadResult(instrument.symbol, "up_to_date", last_date=latest.isoformat())
        if not contract_matches:
            # ``only_missing`` doubles as safe interrupted-recovery: a legacy
            # file is missing the new contract even though its path exists.
            force_full = True
    fetch_start = start
    if latest is not None and not force_full:
        fetch_start = max(start, latest - dt.timedelta(days=refresh_days))
    if instrument.listing_date:
        fetch_start = max(fetch_start, parse_date(instrument.listing_date))
    if fetch_start > end:
        return DownloadResult(instrument.symbol, "up_to_date", last_date=latest.isoformat() if latest else None)
    try:
        bars = client.daily_bars(instrument, fetch_start, end, adjust)
        if bars.empty:
            return DownloadResult(instrument.symbol, "empty", error=f"no bars returned for {fetch_start}..{end}")
        merged = merge_and_save_bars(destination, bars, end=end, replace_existing=force_full)
        return DownloadResult(
            instrument.symbol,
            "ok",
            rows=len(bars),
            first_date=merged["date"].iloc[0].date().isoformat(),
            last_date=merged["date"].iloc[-1].date().isoformat(),
        )
    except Exception as exc:  # collect per-symbol failures; do not lose a whole run
        return DownloadResult(instrument.symbol, "failed", error=f"{type(exc).__name__}: {exc}")


_BAOSTOCK_WORKER_CLIENT: BaoStockClient | None = None


def initialize_baostock_worker() -> None:
    """Create one independent BaoStock socket per process-pool worker."""

    global _BAOSTOCK_WORKER_CLIENT
    _BAOSTOCK_WORKER_CLIENT = BaoStockClient()


def download_instrument_baostock_worker(
    instrument: Instrument,
    start: dt.date,
    end: dt.date,
    refresh_days: int,
    force_full: bool,
    only_missing: bool,
    adjust: str,
) -> DownloadResult:
    """Process-pool entry point for a thread-unsafe BaoStock session."""

    if _BAOSTOCK_WORKER_CLIENT is None:
        raise PipelineError("BaoStock worker was not initialized")
    return download_instrument(
        _BAOSTOCK_WORKER_CLIENT,
        instrument,
        start,
        end,
        refresh_days,
        force_full,
        only_missing,
        adjust,
    )


def _read_qlib_instruments(path: Path) -> dict[str, tuple[str, str]]:
    if not path.exists():
        return {}
    result: dict[str, tuple[str, str]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            pieces = line.rstrip("\n").split("\t")
            if len(pieces) == 3:
                result[pieces[0].upper()] = (pieces[1], pieces[2])
    return result


def _write_qlib_universe(path: Path, symbols: set[str], all_ranges: dict[str, tuple[str, str]]) -> int:
    rows = [
        "\t".join([symbol, *all_ranges[symbol]])
        for symbol in sorted(symbols)
        if symbol in all_ranges
    ]
    path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return len(rows)


def materialize_qlib(instruments: list[Instrument], workers: int) -> dict[str, int]:
    """Rebuild Qlib binary data from compressed source files and write scopes.

    A complete rebuild is intentional: qfq prices may be restated by later
    corporate actions.  Appending only fresh bars would silently leave an
    inconsistent adjusted-price history.
    """

    parquet_count = len(list(RAW_DIR.glob("*.parquet")))
    if not parquet_count:
        raise PipelineError(f"no source Parquet files exist under {RAW_DIR}")
    write_json(
        PRICE_BASIS_MANIFEST,
        {
            "status": "validating",
            "price_basis": POINT_IN_TIME_PRICE_BASIS,
            "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
    )
    price_basis_audit = audit_point_in_time_source()
    if price_basis_audit["status"] != "passed":
        write_json(
            PRICE_BASIS_MANIFEST,
            {
                **price_basis_audit,
                "status": "failed",
                "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            },
        )
        raise PipelineError(
            "source price-basis acceptance failed; run a full point-in-time refresh: "
            f"{price_basis_audit['failures']}"
        )
    # ``dump_bin.py`` is part of this repository.  We reuse its binary writer
    # but orchestrate it here with threads rather than its ProcessPoolExecutor:
    # macOS uses ``spawn`` for child processes, which can recursively re-enter a
    # CLI main module when this pipeline is invoked by launchd.
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.dump_bin import DumpDataAll  # pylint: disable=import-outside-toplevel

    dumper = DumpDataAll(
        data_path=str(RAW_DIR),
        qlib_dir=str(QLIB_DIR),
        freq="day",
        max_workers=1,
        date_field_name="date",
        file_suffix=".parquet",
        symbol_field_name="symbol",
        exclude_fields=",".join(POINT_IN_TIME_EXCLUDED_FIELDS),
    )
    all_datetimes: set[pd.Timestamp] = set()
    date_ranges: list[str] = []
    for source_path in dumper.df_files:
        (begin, end), dates = dumper._get_date(source_path, is_begin_end=True, as_set=True)
        all_datetimes.update(dates)
        if isinstance(begin, pd.Timestamp) and isinstance(end, pd.Timestamp):
            date_ranges.append(
                "\t".join(
                    [
                        dumper.get_symbol_from_file(source_path).upper(),
                        dumper._format_datetime(begin),
                        dumper._format_datetime(end),
                    ]
                )
            )
    dumper._calendars_list = sorted(map(pd.Timestamp, all_datetimes))
    if not dumper._calendars_list:
        raise PipelineError("source Parquet files contain no usable trading dates")
    dumper.save_calendars(dumper._calendars_list)
    dumper.save_instruments(date_ranges)

    def dump_one(source_path: Path) -> None:
        dumper._dump_bin(source_path, dumper._calendars_list)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        for _ in executor.map(dump_one, dumper.df_files):
            pass

    ranges = _read_qlib_instruments(QLIB_DIR / "instruments" / "all.txt")
    buyable = {item.symbol for item in instruments if item.board in {"main", "chinext"}}
    factor = {item.symbol for item in instruments if item.board in {"main", "chinext", "star"}}
    instruments_dir = QLIB_DIR / "instruments"
    buyable_count = _write_qlib_universe(instruments_dir / "buyable_main_chinext.txt", buyable, ranges)
    factor_count = _write_qlib_universe(instruments_dir / "factor_main_chinext_star.txt", factor, ranges)
    summary = {
        "raw_parquet_files": parquet_count,
        "qlib_all": len(ranges),
        "qlib_buyable_main_chinext": buyable_count,
        "qlib_factor_main_chinext_star": factor_count,
    }
    write_json(
        PRICE_BASIS_MANIFEST,
        {
            **price_basis_audit,
            "status": "passed",
            "price_basis": POINT_IN_TIME_PRICE_BASIS,
            "construction": "raw OHLCV adjusted by the cumulative same-close provider pct_chg chain",
            "restoration_factor": "factor = adjusted_price / raw_price",
            "vwap": "raw amount/volume VWAP multiplied by the same daily restoration factor",
            "volume": "raw lot volume divided by the same daily restoration factor",
            "future_corporate_actions_used": False,
            "materialized_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "qlib": summary,
        },
    )
    return summary


def run_sync(args: argparse.Namespace) -> int:
    """Execute one idempotent collection/materialization run."""

    start = parse_date(args.start)
    end = (
        parse_date(args.end)
        if args.end
        else dt.date.today()
        if args.include_current_session
        else latest_completed_session_date()
    )
    if start > end:
        raise PipelineError("--start must not be later than --end")
    for directory in (RAW_DIR, METADATA_DIR, RUNS_DIR, LOG_DIR, QLIB_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    run_started = dt.datetime.now(dt.timezone.utc)
    universe_client: Any = (
        EastmoneyClient(timeout=args.timeout, retries=args.retries, delay=args.delay)
        if args.source == "eastmoney"
        else BaoStockClient()
    )
    with PipelineLock(LOCK_PATH):
        migrated_csv_files = migrate_csv_source_files()
        try:
            universe = (
                universe_client.list_instruments()
                if args.source == "eastmoney"
                else universe_client.list_instruments(end)
            )
        finally:
            if args.source == "baostock":
                universe_client.close()
        write_universe_snapshot(universe, end)
        selected = select_instruments(universe, args.scope, _requested_symbols(args.symbols))
        write_json(
            PRICE_BASIS_MANIFEST,
            {
                "status": "source_update_in_progress",
                "price_basis": POINT_IN_TIME_PRICE_BASIS,
                "daily_source": args.source,
                "requested_adjustment": args.adjust,
                "started_at": run_started.isoformat(),
                "research_allowed": False,
            },
        )
        logging.info(
            "collecting %d symbols (%s scope; %d main, %d ChiNext, %d STAR in current snapshot)",
            len(selected),
            args.scope,
            sum(item.board == "main" for item in universe),
            sum(item.board == "chinext" for item in universe),
            sum(item.board == "star" for item in universe),
        )

        results: list[DownloadResult] = []
        executor_context: Any = (
            concurrent.futures.ThreadPoolExecutor(max_workers=args.workers)
            if args.source == "eastmoney"
            else concurrent.futures.ProcessPoolExecutor(
                max_workers=args.workers,
                initializer=initialize_baostock_worker,
            )
        )
        with executor_context as executor:
            if args.source == "eastmoney":
                futures = [
                    executor.submit(
                        download_instrument,
                        universe_client,
                        item,
                        start,
                        end,
                        args.refresh_days,
                        args.force_full,
                        args.only_missing,
                        args.adjust,
                    )
                    for item in selected
                ]
            else:
                futures = [
                    executor.submit(
                        download_instrument_baostock_worker,
                        item,
                        start,
                        end,
                        args.refresh_days,
                        args.force_full,
                        args.only_missing,
                        args.adjust,
                    )
                    for item in selected
                ]
            for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                result = future.result()
                results.append(result)
                if result.status == "failed":
                    logging.warning("%s failed: %s", result.symbol, result.error)
                elif index % 100 == 0 or index == len(futures):
                    logging.info("download progress: %d/%d", index, len(futures))

        ok_count = sum(item.status == "ok" for item in results)
        failed = [item for item in results if item.status == "failed"]
        empty = [item for item in results if item.status == "empty"]
        qlib_summary: dict[str, int] = {}
        if not args.skip_dump and (ok_count > 0 or any(RAW_DIR.glob("*.parquet"))):
            qlib_summary = materialize_qlib(universe, args.dump_workers)

        completed = dt.datetime.now(dt.timezone.utc)
        manifest = {
            "started_at": run_started.isoformat(),
            "completed_at": completed.isoformat(),
            "scope": args.scope,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "adjust": args.adjust,
            "source": args.source,
            "force_full": args.force_full,
            "only_missing": args.only_missing,
            "requested_symbols": args.symbols,
            "universe_counts": {
                "main": sum(item.board == "main" for item in universe),
                "chinext": sum(item.board == "chinext" for item in universe),
                "star": sum(item.board == "star" for item in universe),
                "selected": len(selected),
            },
            "download_counts": {
                "ok": ok_count,
                "empty": len(empty),
                "failed": len(failed),
                "up_to_date": sum(item.status == "up_to_date" for item in results),
            },
            "migrated_legacy_csv_files": migrated_csv_files,
            "failed": [asdict(item) for item in failed],
            "empty": [asdict(item) for item in empty],
            "qlib": qlib_summary,
        }
        run_id = run_started.strftime("%Y%m%dT%H%M%SZ")
        write_json(RUNS_DIR / f"{run_id}.json", manifest)
        write_json(METADATA_DIR / "latest_run.json", manifest)
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
        # A failed subset should be visible to a scheduler without losing the
        # successfully acquired data.  Exit 2 makes launchd retain the log.
        return 2 if failed else 0


def run_status(_: argparse.Namespace) -> int:
    """Print the latest local pipeline state without accessing the network."""

    latest_run = METADATA_DIR / "latest_run.json"
    latest_summary: dict[str, Any] | None = None
    if latest_run.exists():
        run = json.loads(latest_run.read_text(encoding="utf-8"))
        latest_summary = {
            key: run.get(key)
            for key in (
                "started_at",
                "completed_at",
                "scope",
                "start",
                "end",
                "adjust",
                "source",
                "force_full",
                "only_missing",
                "universe_counts",
                "download_counts",
                "qlib",
            )
        }
        latest_summary["empty_symbols_path"] = str(latest_run)
        latest_summary["failed_symbols_path"] = str(latest_run)
    calendar_path = QLIB_DIR / "calendars" / "day.txt"
    calendar_end = None
    if calendar_path.exists():
        with calendar_path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    calendar_end = line.strip()
    maintenance: dict[str, Any] | None = None
    maintenance_candidates = [
        METADATA_DIR / "latest_sanitization.json",
        METADATA_DIR / "latest_session_prune.json",
        METADATA_DIR / "latest_symbol_normalization.json",
    ]
    existing_maintenance = [path for path in maintenance_candidates if path.exists()]
    if existing_maintenance:
        path = max(existing_maintenance, key=lambda item: item.stat().st_mtime)
        record = json.loads(path.read_text(encoding="utf-8"))
        repair = record.get("repair") or record.get("prune")
        if isinstance(repair, dict):
            repair = {key: value for key, value in repair.items() if key != "affected_symbols"}
        maintenance = {
            "path": str(path),
            "completed_at": record.get("completed_at"),
            "repair": repair,
            "qlib": record.get("qlib"),
        }
    summary: dict[str, Any] = {
        "repository": str(REPO_ROOT),
        "data_root": str(DATA_ROOT),
        "raw_parquet_files": len(list(RAW_DIR.glob("*.parquet"))),
        "qlib_features": len(list((QLIB_DIR / "features").glob("*"))) if (QLIB_DIR / "features").exists() else 0,
        "qlib_calendar_end": calendar_end,
        "latest_run": latest_summary,
        "latest_local_maintenance": maintenance,
        "price_basis": (
            json.loads(PRICE_BASIS_MANIFEST.read_text(encoding="utf-8"))
            if PRICE_BASIS_MANIFEST.exists()
            else {"status": "missing", "research_allowed": False}
        ),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def run_materialize(_: argparse.Namespace) -> int:
    """Rebuild Qlib files from local source data without any network requests."""

    universe_path = METADATA_DIR / "universe_latest.json"
    if not universe_path.exists():
        raise PipelineError("no universe snapshot exists; run `sync` before `materialize`")
    instruments = [Instrument(**item) for item in json.loads(universe_path.read_text(encoding="utf-8"))]
    started = dt.datetime.now(dt.timezone.utc)
    with PipelineLock(LOCK_PATH):
        summary = materialize_qlib(instruments, workers=DEFAULT_WORKERS)
    manifest = {
        "started_at": started.isoformat(),
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "qlib": summary,
    }
    write_json(METADATA_DIR / "latest_materialization.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def run_price_basis_audit(args: argparse.Namespace) -> int:
    """Audit every source file without downloading or materializing data."""

    started = dt.datetime.now(dt.timezone.utc)
    with PipelineLock(LOCK_PATH):
        audit = audit_point_in_time_source(max_examples=args.max_examples)
    report = {
        **audit,
        "started_at": started.isoformat(),
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "forward_return_fields_read": False,
    }
    destination = METADATA_DIR / f"price_basis_audit_{started.strftime('%Y%m%dT%H%M%SZ')}.json"
    write_json(destination, report)
    print(json.dumps({**report, "report_path": str(destination.resolve())}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if audit["status"] == "passed" else 1


def run_quarantine_source_vwap(_: argparse.Namespace) -> int:
    """Null research VWAP where source amount/volume contradict source OHLC."""

    started = dt.datetime.now(dt.timezone.utc)
    affected: list[dict[str, Any]] = []
    quarantined_rows = 0
    with PipelineLock(LOCK_PATH):
        for path in sorted(RAW_DIR.glob("*.parquet")):
            bars = pd.read_parquet(path)
            mask = raw_vwap_outside_ohlc_mask(bars)
            if not mask.any():
                continue
            bars.loc[mask, "vwap"] = float("nan")
            _atomic_write_parquet(bars, path)
            count = int(mask.sum())
            quarantined_rows += count
            affected.append({"symbol": path.stem.upper(), "rows": count})
    report = {
        "status": "completed",
        "operation": "quarantine_source_vwap_outside_raw_ohlc",
        "started_at": started.isoformat(),
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "affected_files": len(affected),
        "quarantined_rows": quarantined_rows,
        "affected": affected,
        "raw_vwap_preserved": True,
        "research_vwap_set_to_missing": True,
        "price_fields_changed": False,
        "forward_return_fields_read": False,
    }
    destination = METADATA_DIR / "repairs" / f"{started.strftime('%Y%m%dT%H%M%SZ')}_vwap_quarantine.json"
    write_json(destination, report)
    print(json.dumps({**report, "report_path": str(destination.resolve())}, ensure_ascii=False, indent=2))
    return 0


def run_sanitize(args: argparse.Namespace) -> int:
    """Repair legacy invalid price rows, then rebuild Qlib data from local files."""

    universe_path = METADATA_DIR / "universe_latest.json"
    if not universe_path.exists():
        raise PipelineError("no universe snapshot exists; run `sync` before `sanitize`")
    instruments = [Instrument(**item) for item in json.loads(universe_path.read_text(encoding="utf-8"))]
    started = dt.datetime.now(dt.timezone.utc)
    with PipelineLock(LOCK_PATH):
        repair = sanitize_source_data(max_examples=args.max_examples)
        qlib_summary = (
            materialize_qlib(instruments, workers=args.dump_workers)
            if repair["rows_removed"] and not args.skip_dump
            else {}
        )
    manifest = {
        "started_at": started.isoformat(),
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repair": repair,
        "qlib": qlib_summary,
    }
    write_json(METADATA_DIR / "latest_sanitization.json", manifest)
    write_json(METADATA_DIR / "repairs" / f"sanitize_{started.strftime('%Y%m%dT%H%M%SZ')}.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def run_normalize_symbols(args: argparse.Namespace) -> int:
    """Repair missing source symbol fields and rebuild Qlib only when needed."""

    universe_path = METADATA_DIR / "universe_latest.json"
    if not universe_path.exists():
        raise PipelineError("no universe snapshot exists; run `sync` before `normalize-symbols`")
    instruments = [Instrument(**item) for item in json.loads(universe_path.read_text(encoding="utf-8"))]
    started = dt.datetime.now(dt.timezone.utc)
    with PipelineLock(LOCK_PATH):
        repair = normalize_source_symbols(max_examples=args.max_examples)
        qlib_summary = (
            materialize_qlib(instruments, workers=args.dump_workers)
            if repair["rows_normalized"] and not args.skip_dump
            else {}
        )
    manifest = {
        "started_at": started.isoformat(),
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repair": repair,
        "qlib": qlib_summary,
        "limitations": ["Only missing or blank symbol fields are restored; price and date fields are unchanged."],
    }
    write_json(METADATA_DIR / "latest_symbol_normalization.json", manifest)
    write_json(METADATA_DIR / "repairs" / f"normalize_symbols_{started.strftime('%Y%m%dT%H%M%SZ')}.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def run_prune_session(args: argparse.Namespace) -> int:
    """Drop provisional daily bars and rebuild Qlib output without a network call."""

    universe_path = METADATA_DIR / "universe_latest.json"
    if not universe_path.exists():
        raise PipelineError("no universe snapshot exists; run `sync` before `prune-session`")
    end = parse_date(args.end) if args.end else latest_completed_session_date()
    instruments = [Instrument(**item) for item in json.loads(universe_path.read_text(encoding="utf-8"))]
    started = dt.datetime.now(dt.timezone.utc)
    with PipelineLock(LOCK_PATH):
        prune = prune_source_after(end, max_examples=args.max_examples)
        qlib_summary = (
            materialize_qlib(instruments, workers=args.dump_workers)
            if prune["rows_removed"] and not args.skip_dump
            else {}
        )
    manifest = {
        "started_at": started.isoformat(),
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "prune": prune,
        "qlib": qlib_summary,
    }
    write_json(METADATA_DIR / "latest_session_prune.json", manifest)
    write_json(METADATA_DIR / "repairs" / f"prune_{started.strftime('%Y%m%dT%H%M%SZ')}.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    sync = subparsers.add_parser("sync", help="download data and rebuild the Qlib daily data set")
    sync.add_argument("--start", default=DEFAULT_START_DATE, help=f"first history date (default: {DEFAULT_START_DATE})")
    sync.add_argument("--end", help="last history date; defaults to the latest completed local session")
    sync.add_argument(
        "--include-current-session",
        action="store_true",
        help="allow an unfinished current-day bar when --end is omitted",
    )
    sync.add_argument("--scope", choices=("buyable", "factor"), default="factor", help="factor includes STAR data")
    sync.add_argument("--symbols", help="comma-separated test/repair subset, e.g. 600519,300750,688981")
    sync.add_argument(
        "--source",
        choices=("eastmoney", "baostock"),
        default="eastmoney",
        help="daily-bar provider; BaoStock is sequential and can recover an unavailable Eastmoney history endpoint",
    )
    sync.add_argument(
        "--adjust",
        choices=("point_in_time", "qfq", "hfq", "raw"),
        default="point_in_time",
        help="price basis requested from source; point_in_time is required for research materialization",
    )
    sync.add_argument("--refresh-days", type=int, default=DEFAULT_REFRESH_DAYS, help="tail window refreshed each run")
    sync.add_argument("--force-full", action="store_true", help="redownload each selected symbol from --start")
    sync.add_argument(
        "--only-missing",
        action="store_true",
        help="bootstrap/recovery mode: skip every symbol that already has a local source file",
    )
    sync.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="parallel source requests (keep low to respect source)")
    sync.add_argument("--dump-workers", type=int, default=DEFAULT_WORKERS, help="Qlib binary materialization workers")
    sync.add_argument("--timeout", type=float, default=30.0, help="per-request timeout in seconds")
    sync.add_argument("--retries", type=int, default=4, help="per-symbol source retry count")
    sync.add_argument("--delay", type=float, default=0.35, help="minimum delay after a source request")
    sync.add_argument("--skip-dump", action="store_true", help="download source Parquet only; skip Qlib binary rebuild")
    sync.set_defaults(func=run_sync)
    materialize = subparsers.add_parser("materialize", help="rebuild Qlib binary data from local source Parquet files")
    materialize.set_defaults(func=run_materialize)
    price_basis_audit = subparsers.add_parser(
        "price-basis-audit",
        help="verify point-in-time prices, VWAP, returns, and restoration factors without reading future returns",
    )
    price_basis_audit.add_argument("--max-examples", type=int, default=20)
    price_basis_audit.set_defaults(func=run_price_basis_audit)
    quarantine_vwap = subparsers.add_parser(
        "quarantine-vwap",
        help="preserve raw source VWAP but null the research VWAP when amount/volume contradict raw OHLC",
    )
    quarantine_vwap.set_defaults(func=run_quarantine_source_vwap)
    sanitize = subparsers.add_parser("sanitize", help="remove invalid local OHLC rows and rebuild Qlib binaries")
    sanitize.add_argument("--dump-workers", type=int, default=DEFAULT_WORKERS, help="Qlib binary materialization workers")
    sanitize.add_argument("--skip-dump", action="store_true", help="repair Parquet only; do not rebuild Qlib binaries")
    sanitize.add_argument("--max-examples", type=int, default=20, help="maximum affected-symbol details printed")
    sanitize.set_defaults(func=run_sanitize)
    normalize_symbols = subparsers.add_parser(
        "normalize-symbols", help="restore missing source symbol fields and rebuild Qlib binaries"
    )
    normalize_symbols.add_argument(
        "--dump-workers", type=int, default=DEFAULT_WORKERS, help="Qlib binary materialization workers"
    )
    normalize_symbols.add_argument("--skip-dump", action="store_true", help="repair Parquet only; do not rebuild Qlib binaries")
    normalize_symbols.add_argument("--max-examples", type=int, default=20, help="maximum affected-symbol details printed")
    normalize_symbols.set_defaults(func=run_normalize_symbols)
    prune = subparsers.add_parser("prune-session", help="remove provisional daily bars after a safe cutoff")
    prune.add_argument("--end", help="completed-session cutoff; defaults to the latest safe local date")
    prune.add_argument("--dump-workers", type=int, default=DEFAULT_WORKERS, help="Qlib binary materialization workers")
    prune.add_argument("--skip-dump", action="store_true", help="prune Parquet only; do not rebuild Qlib binaries")
    prune.add_argument("--max-examples", type=int, default=20, help="maximum affected-symbol details printed")
    prune.set_defaults(func=run_prune_session)
    status = subparsers.add_parser("status", help="show local data and last run information")
    status.set_defaults(func=run_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    if getattr(args, "workers", 1) < 1 or getattr(args, "dump_workers", 1) < 1:
        raise PipelineError("worker counts must be positive")
    if getattr(args, "refresh_days", 0) < 0:
        raise PipelineError("--refresh-days must be non-negative")
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PipelineError as exc:
        logging.error("pipeline failed: %s", exc)
        raise SystemExit(1) from exc
