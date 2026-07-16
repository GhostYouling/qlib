#!/usr/bin/env python3
"""Ingest auditable A-share intraday and event data from licensed providers.

This tool deliberately does not replace ``a_share_data_pipeline.py``.  The
existing pipeline remains the daily OHLCV source used by the production-like
selection workflow.  This script stores paid/credentialed data separately,
with a manifest for each immutable download snapshot, so that a research run
can always identify its provider, retrieval time, and raw input files.

Supported providers
-------------------
* ``baostock``: anonymous raw five-minute OHLCV/amount candidate history.
* ``tushare``: minute OHLCV plus end-of-day moneyflow, limit prices,
  historical ST status, and top-list events.  The richer limit-list table is
  optional because it requires a higher entitlement.
* ``jqdata``: minute OHLCV plus separately licensed professional daily moneyflow.
* ``rqdata``: minute OHLCV.

Credentials are read only from environment variables.  Never place a token or
password in a command line, a config file committed to git, or a run manifest.
"""

from __future__ import annotations

import argparse
import atexit
import concurrent.futures
import datetime as dt
import fcntl
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import shutil
import tempfile
import time
import unicodedata
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
DEFAULT_MINUTE_FACTOR_SPEC = (
    REPO_ROOT / "docs" / "a_share_minute_factor_preregistration.json"
)
DEFAULT_JQDATA_MONEYFLOW_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_jqdata_moneyflow_data_contract.json"
)
DEFAULT_TUSHARE_MONEYFLOW_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_moneyflow_data_contract.json"
)
DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_northbound_top10_data_contract.json"
)
DEFAULT_TUSHARE_TOP_INST_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_top_inst_data_contract.json"
)
DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_top10_float_concentration_data_contract.json"
)
DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_cash_conversion_data_contract.json"
)
DEFAULT_TUSHARE_CASH_CONVERSION_ACCEPTANCE_RECORD = (
    REPO_ROOT / "docs" / "a_share_tushare_cash_conversion_source_acceptance_record.json"
)
DEFAULT_TUSHARE_DAILY_PB_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_daily_pb_data_contract.json"
)
DEFAULT_TUSHARE_DAILY_PB_CAPACITY_SPEC = (
    REPO_ROOT / "docs" / "a_share_tushare_daily_pb_capacity_preregistration.json"
)
DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_tushare_sw_industry_breadth_data_contract.json"
)
DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_sw_industry_breadth_capacity_preregistration.json"
)
DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_SYMBOL_REPAIR = (
    REPO_ROOT / "docs" / "a_share_tushare_sw_industry_breadth_symbol_repair.json"
)
DEFAULT_BAOSTOCK_5M_CONTRACT = (
    REPO_ROOT / "docs" / "a_share_baostock_5m_data_contract.json"
)
DEFAULT_BAOSTOCK_5M_FACTOR_SPEC = (
    REPO_ROOT / "docs" / "a_share_baostock_5m_factor_preregistration.json"
)
DEFAULT_BAOSTOCK_5M_SUSPENSION_AUDIT = (
    REPO_ROOT / "docs" / "a_share_baostock_5m_suspension_placeholder_audit.json"
)
DEFAULT_BAOSTOCK_5M_THROTTLE_AUDIT = (
    REPO_ROOT / "docs" / "a_share_baostock_5m_request_throttle_audit.json"
)
DEFAULT_FACTOR_UNIVERSE = (
    DATA_ROOT / "qlib" / "cn_a_share" / "instruments" / "factor_main_chinext_star.txt"
)
DEFAULT_BUYABLE_UNIVERSE = (
    DATA_ROOT / "qlib" / "cn_a_share" / "instruments" / "buyable_main_chinext.txt"
)
DEFAULT_LOCAL_CALENDAR = DATA_ROOT / "qlib" / "cn_a_share" / "calendars" / "day.txt"

DEFAULT_ACCEPTANCE_SYMBOLS = ("600519", "000001", "300750", "688981")
PROVIDER_REQUIREMENTS = {
    "baostock": {"package": "baostock", "environment": ()},
    "tushare": {"package": "tushare", "environment": ("TUSHARE_TOKEN",)},
    "jqdata": {
        "package": "jqdatasdk",
        "environment": ("JQDATA_USERNAME", "JQDATA_PASSWORD"),
    },
    "rqdata": {
        "package": "rqdatac",
        "environment": ("RQDATA_USERNAME", "RQDATA_PASSWORD"),
    },
}
DEFAULT_EVENT_DATASETS = ("moneyflow", "limit-price", "stock-st", "top-list")
EVENT_DATASETS = DEFAULT_EVENT_DATASETS + ("limit-list",)
TUSHARE_EVENT_PERMISSION_POINTS = {
    "moneyflow": 2_000,
    "limit-price": 2_000,
    "stock-st": 3_000,
    "top-list": 2_000,
    "limit-list": 5_000,
}
TUSHARE_EVENT_KEY_FIELDS = {
    "moneyflow": ("trade_date", "ts_code"),
    "limit-price": ("trade_date", "ts_code"),
    "stock-st": ("trade_date", "ts_code"),
    "top-list": ("trade_date", "ts_code", "reason"),
    "limit-list": ("trade_date", "ts_code"),
}
MINUTE_FEATURE_EXPECTED_BARS = 240
MINUTE_EXPECTED_BARS_BY_FREQUENCY = {"1m": 240, "5m": 48}
MINUTE_FEATURE_NAMES = (
    "late_return_30m",
    "late_amount_share_30m",
    "late_vwap_to_day_vwap_30m",
    "opening_gap_digestion",
    "intraday_realized_volatility",
)
MINUTE_FEATURE_DIRECTIONS = ("higher", "higher", "higher", "higher", "lower")
BAOSTOCK_5M_FEATURE_NAMES = (
    "late_return_30m_5m",
    "late_amount_share_30m_5m",
    "late_vwap_to_day_vwap_30m_5m",
    "opening_gap_digestion_5m",
    "intraday_realized_volatility_5m",
)
BAOSTOCK_5M_FEATURE_DIRECTIONS = ("higher", "higher", "higher", "higher", "lower")
REQUIRED_DAILY_PRICE_BASIS = "close_known_raw_pct_chg_chain_v1"
JQDATA_MONEYFLOW_CONTRACT_SHA256 = (
    "1a3c451ecc2d1b4f8c2ef38a8de1acf4aa474bbce4f98b99dc0369bb8d9d6004"
)
TUSHARE_MONEYFLOW_CONTRACT_SHA256 = (
    "a38f8113d948a179e6cc38eb388f13fcd691fe793209703009762db6cfa81b12"
)
TUSHARE_NORTHBOUND_TOP10_CONTRACT_SHA256 = (
    "9362211f3e35cbb24c779d49d138fb757d61f7a092b61f0304d0e147a739f63e"
)
TUSHARE_TOP_INST_CONTRACT_SHA256 = (
    "0520cd8bac454f14c2434cf7b8092aaaf3ff94cdc09b5404a6b55323bf0e7461"
)
TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT_SHA256 = (
    "cec766613b49292e724cfd78090bdbec9d7c52ae8b337bceaf0ebe208c729897"
)
TUSHARE_CASH_CONVERSION_CONTRACT_SHA256 = (
    "54584d758fc0846d90281fecedc7b90113823bb56b55d4782e749a9a5212ee01"
)
TUSHARE_CASH_CONVERSION_ACCEPTANCE_RECORD_SHA256 = (
    "615f0b794c165569b3d89444c594ee16fc60c628b36f0f834c759e09167fe962"
)
TUSHARE_DAILY_PB_CONTRACT_SHA256 = (
    "cd5c95636d9efa8eb975190072dfe94c4ee6da954dd4d9d6826d2c0b391ebdd2"
)
TUSHARE_DAILY_PB_CAPACITY_SPEC_SHA256 = (
    "14668ad3f97cef68cd2fae882507280ef835c0f5e7b4ddecb763c1907590c0a0"
)
TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT_SHA256 = (
    "e8dc45f6302bb6a4f1173da3698064bf7133930616b2fcd3338061f2fc508e66"
)
TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC_SHA256 = (
    "dc5e0525df07e21d628ab09d46843511ddbeacb09ecbc3afb41d14b43bcfae59"
)
TUSHARE_SW_INDUSTRY_BREADTH_SYMBOL_REPAIR_SHA256 = (
    "5001ae0b278d086f26ca35bf8a1fc43c8009aa99c13b03258e7b2fb7bc99b18f"
)
BAOSTOCK_5M_CONTRACT_SHA256 = (
    "3352497aa911f69ced631fac57db1369eaa12acabad8ca7857f6254205354a8f"
)
BAOSTOCK_5M_FACTOR_SPEC_SHA256 = (
    "a6b679c1476cacfc193aba5bf93988c92691025872150d3eaab723576c7164b8"
)
BAOSTOCK_5M_SUSPENSION_AUDIT_SHA256 = (
    "5c29bd194ef70ed0d30a1e72aa3adc7e287ec1f513e0d3ee29d7551cf1dff47d"
)
BAOSTOCK_5M_THROTTLE_AUDIT_SHA256 = (
    "4a881c707f41dc1a1043015ca004b65ff4607bc96bce21cd65c832cb20dc18aa"
)
BAOSTOCK_5M_MINIMUM_FREE_BYTES = 10 * 1024**3
BAOSTOCK_5M_MAX_WORKERS = 4
BAOSTOCK_5M_PARTITION_RETRIES = 3
BAOSTOCK_5M_RESTORATION_PROBE_MAX_AGE_MINUTES = 30
JQDATA_MONEYFLOW_RAW_FIELDS = (
    "inflow_xl",
    "inflow_l",
    "inflow_m",
    "inflow_s",
    "outflow_xl",
    "outflow_l",
    "outflow_m",
    "outflow_s",
)
JQDATA_MONEYFLOW_COLUMNS = (
    "trade_date",
    "instrument",
    "inflow_xl_amount",
    "inflow_l_amount",
    "inflow_m_amount",
    "inflow_s_amount",
    "outflow_xl_amount",
    "outflow_l_amount",
    "outflow_m_amount",
    "outflow_s_amount",
    "jqdata_large_order_net_inflow_share",
    "provider",
)
TUSHARE_MONEYFLOW_AMOUNT_FIELDS = (
    "buy_sm_amount",
    "sell_sm_amount",
    "buy_md_amount",
    "sell_md_amount",
    "buy_lg_amount",
    "sell_lg_amount",
    "buy_elg_amount",
    "sell_elg_amount",
)
TUSHARE_MONEYFLOW_RAW_FIELDS = (
    "ts_code",
    "trade_date",
    *TUSHARE_MONEYFLOW_AMOUNT_FIELDS,
)
TUSHARE_MONEYFLOW_COLUMNS = (
    "trade_date",
    "instrument",
    *TUSHARE_MONEYFLOW_AMOUNT_FIELDS,
    "tushare_large_order_net_inflow_share",
    "provider",
)
TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS = (
    "trade_date",
    "ts_code",
    "rank",
    "market_type",
    "amount",
    "buy",
    "sell",
)
TUSHARE_NORTHBOUND_TOP10_COLUMNS = (
    "trade_date",
    "instrument",
    "rank",
    "market_type",
    "amount",
    "buy",
    "sell",
    "tushare_northbound_top10_net_buy_share",
    "provider",
)
TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES = ("1", "3")
TUSHARE_TOP_INST_RAW_FIELDS = (
    "trade_date",
    "ts_code",
    "exalter",
    "buy",
    "sell",
    "net_buy",
)
TUSHARE_TOP_INST_COLUMNS = (
    "trade_date",
    "instrument",
    "institution_seat_count",
    "buy",
    "sell",
    "tushare_top_inst_net_buy_share",
    "provider",
)
TUSHARE_TOP10_FLOAT_RAW_FIELDS = (
    "ts_code",
    "ann_date",
    "end_date",
    "holder_name",
    "hold_float_ratio",
)
TUSHARE_TOP10_FLOAT_SOURCE_COLUMNS = (
    "announcement_date",
    "report_period",
    "instrument",
    "holder_name_sha256",
    "hold_float_ratio",
    "provider",
)
TUSHARE_TOP10_FLOAT_FACTOR_COLUMNS = (
    "announcement_date",
    "report_period",
    "previous_report_period",
    "instrument",
    "top10_float_holder_count",
    "top10_float_concentration_pct",
    "top10_float_concentration_change_pp",
    "provider",
)
TUSHARE_TOP10_FLOAT_ACCEPTANCE_SYMBOLS = (
    "600519.SH",
    "000001.SZ",
    "300750.SZ",
)
TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS = (
    "ts_code",
    "ann_date",
    "f_ann_date",
    "end_date",
    "report_type",
    "comp_type",
    "n_income_attr_p",
    "update_flag",
)
TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS = (
    "ts_code",
    "ann_date",
    "f_ann_date",
    "end_date",
    "report_type",
    "comp_type",
    "n_cashflow_act",
    "update_flag",
)
TUSHARE_CASH_CONVERSION_COLUMNS = (
    "announcement_date",
    "income_actual_announcement_date",
    "cashflow_actual_announcement_date",
    "report_period",
    "instrument",
    "n_income_attr_p",
    "n_cashflow_act",
    "tushare_operating_cash_conversion",
    "provider",
)
TUSHARE_CASH_CONVERSION_INCOME_COLUMNS = (
    "income_announcement_date",
    "income_actual_announcement_date",
    "report_period",
    "instrument",
    "n_income_attr_p",
    "provider",
)
TUSHARE_CASH_CONVERSION_CASHFLOW_COLUMNS = (
    "cashflow_announcement_date",
    "cashflow_actual_announcement_date",
    "report_period",
    "instrument",
    "n_cashflow_act",
    "provider",
)
TUSHARE_CASH_CONVERSION_ACCEPTANCE_SYMBOLS = (
    "600519.SH",
    "000333.SZ",
    "300750.SZ",
)
TUSHARE_CASH_CONVERSION_ADJUSTMENT_REPORT_TYPES = frozenset({3, 4, 5, 8, 9, 10, 11, 12})
TUSHARE_CASH_CONVERSION_CONTEXT_REPORT_TYPES = frozenset({2, 6, 7})
TUSHARE_CASH_CONVERSION_KNOWN_REPORT_TYPES = frozenset(range(1, 13))
TUSHARE_CASH_CONVERSION_KNOWN_COMPANY_TYPES = frozenset({1, 2, 3, 4})
TUSHARE_DAILY_PB_RAW_FIELDS = ("ts_code", "trade_date", "pb")
TUSHARE_DAILY_PB_COLUMNS = (
    "trade_date",
    "instrument",
    "pb",
    "tushare_positive_book_to_market",
    "provider",
)
TUSHARE_SW_CLASSIFICATION_RAW_FIELDS = (
    "index_code",
    "industry_name",
    "level",
    "src",
)
TUSHARE_SW_MEMBERSHIP_RAW_FIELDS = (
    "l1_code",
    "l1_name",
    "l2_code",
    "l2_name",
    "l3_code",
    "l3_name",
    "ts_code",
    "in_date",
    "out_date",
    "is_new",
)
TUSHARE_SW_MEMBERSHIP_COLUMNS = (
    "l1_code",
    "l1_name",
    "l2_code",
    "l2_name",
    "l3_code",
    "l3_name",
    "instrument",
    "in_date",
    "out_date",
    "is_new",
    "provider",
)


class RichDataError(RuntimeError):
    """A recoverable provider, credential, or data-contract error."""


class RichDataProcessLock:
    """Hold one advisory lock for a long-running rich-data synchronization."""

    def __init__(self, path: Path):
        self.path = path
        self._handle: Any | None = None

    def __enter__(self) -> "RichDataProcessLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._handle.seek(0)
            owner = self._handle.read().strip() or "unknown"
            self._handle.close()
            self._handle = None
            raise RichDataError(
                f"another BaoStock five-minute synchronization holds {self.path}; owner={owner}"
            ) from exc
        self._handle.seek(0)
        self._handle.truncate()
        self._handle.write(str(os.getpid()))
        self._handle.flush()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._handle is not None:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
            self._handle.close()
            self._handle = None


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
    if provider == "baostock":
        return f"{'sh' if symbol.startswith('SH') else 'sz'}.{code}"
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
        raise RichDataError(
            f"{provider} credentials are missing from the environment: {keys}"
        )


def safe_exception_text(exc: BaseException) -> str:
    """Render an exception after removing any configured provider secret values."""

    message = str(exc)
    for details in PROVIDER_REQUIREMENTS.values():
        for key in details["environment"]:
            secret = os.environ.get(str(key))
            if secret:
                message = message.replace(secret, "<redacted>")
    return message


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
    resolved = {
        field: _column(normalized, candidates)
        for field, candidates in field_map.items()
    }
    missing = [field for field, column in resolved.items() if column is None]
    if missing:
        raise RichDataError(
            f"{provider} minute response is missing required columns: {', '.join(missing)}"
        )
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
    result = result.loc[
        (result["datetime"] >= start_timestamp) & (result["datetime"] < end_timestamp)
    ].copy()
    result = result.dropna(
        subset=["datetime", "open", "high", "low", "close", "volume", "amount"]
    )
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
        raise RichDataError(
            f"{provider} returned {int(invalid_price.sum())} invalid minute bars for {code}"
        )
    result = result.drop_duplicates(subset=["datetime"], keep="last").sort_values(
        "datetime"
    )
    return result.reset_index(drop=True)


def canonicalize_baostock_5m_bars(
    frame: pd.DataFrame,
    code: str,
    start: dt.date,
    end: dt.date,
) -> pd.DataFrame:
    """Normalize BaoStock bars without silently resolving duplicate timestamps."""

    source_rows = 0 if frame is None else int(len(frame))
    source_rows_by_year: dict[int, int] = {}
    placeholder_rows = 0
    placeholder_rows_by_year: dict[int, int] = {}
    placeholder_dates: list[str] = []
    normalized = frame
    if frame is not None and not frame.empty:
        normalized = frame.copy()
        if not isinstance(normalized.index, pd.RangeIndex):
            normalized = normalized.reset_index()
        datetime_column = _column(
            normalized, ("datetime", "trade_time", "time", "date")
        )
        if datetime_column is None:
            raise RichDataError("baostock minute response has no datetime column")
        timestamps = pd.to_datetime(normalized[datetime_column], errors="coerce")
        source_rows_by_year = {
            int(year): int(count)
            for year, count in timestamps.loc[timestamps.notna()]
            .dt.year.value_counts()
            .items()
        }
        if (
            timestamps.notna().any()
            and timestamps[timestamps.notna()].duplicated().any()
        ):
            raise RichDataError(
                f"BaoStock returned duplicate five-minute timestamps for {code}; "
                "the frozen contract forbids silent deduplication"
            )
        resolved = {
            field: _column(normalized, candidates)
            for field, candidates in {
                "open": ("open",),
                "high": ("high",),
                "low": ("low",),
                "close": ("close",),
                "volume": ("volume", "vol"),
                "amount": ("amount", "money", "total_turnover", "turnover"),
            }.items()
        }
        if missing := [field for field, column in resolved.items() if column is None]:
            raise RichDataError(
                "baostock minute response is missing required columns: "
                + ", ".join(missing)
            )
        numeric = pd.DataFrame(
            {
                field: pd.to_numeric(normalized[column], errors="coerce")
                for field, column in resolved.items()
                if column is not None
            }
        )
        zero_price_placeholder = (
            numeric[["open", "high", "low", "close"]].eq(0.0).all(axis=1)
            & numeric["volume"].eq(0.0)
            & numeric["amount"].eq(0.0)
        )
        placeholder_rows = int(zero_price_placeholder.sum())
        placeholder_rows_by_year = {
            int(year): int(count)
            for year, count in timestamps.loc[
                zero_price_placeholder & timestamps.notna()
            ]
            .dt.year.value_counts()
            .items()
        }
        placeholder_dates = sorted(
            timestamps.loc[zero_price_placeholder & timestamps.notna()]
            .dt.date.astype(str)
            .unique()
            .tolist()
        )
        normalized = normalized.loc[~zero_price_placeholder].copy()
    result = canonicalize_minute_bars(normalized, "baostock", code, start, end)
    result.attrs["source_rows"] = source_rows
    result.attrs["source_rows_by_year"] = source_rows_by_year
    result.attrs["zero_price_placeholder_rows_excluded"] = placeholder_rows
    result.attrs["zero_price_placeholder_rows_by_year"] = placeholder_rows_by_year
    result.attrs["zero_price_placeholder_session_dates"] = placeholder_dates
    return result


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
    return dt.time(9, 30) <= time_of_day <= dt.time(11, 30) or dt.time(
        13, 0
    ) <= time_of_day <= dt.time(15, 0)


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
        "status": (
            "passed"
            if all(day["out_of_session_bars"] == 0 for day in days)
            else "failed"
        ),
        "days": days,
    }


def _relative_error(actual: float, expected: float) -> float | None:
    if not pd.notna(actual) or not pd.notna(expected) or expected == 0:
        return None
    return abs(actual / expected - 1.0)


def minute_daily_reconciliation(frame: pd.DataFrame) -> dict[str, Any]:
    """Compare minute aggregates with local daily data without mixing prices.

    Incoming minute prices and volumes are explicitly raw.  The accepted daily
    pipeline preserves matching ``raw_*`` fields alongside factor-adjusted
    research columns, so reconciliation must use the raw fields directly.
    Comparing against adjusted ``volume`` would multiply the inferred source
    unit by the current adjustment factor and can reject otherwise exact data.
    """

    if frame.empty:
        return {"status": "failed", "reason": "no_bars", "days": []}
    symbol = str(frame["symbol"].iloc[0]).lower()
    path = DAILY_RAW_DIR / f"{symbol}.parquet"
    if not path.exists():
        return {
            "status": "unavailable",
            "reason": f"missing_local_daily:{path}",
            "days": [],
        }
    daily = pd.read_parquet(path)
    required_daily = {
        "date",
        "raw_open",
        "raw_high",
        "raw_low",
        "raw_close",
        "raw_volume",
        "amount",
        "price_basis",
    }
    if missing := sorted(required_daily - set(daily.columns)):
        return {
            "status": "unavailable",
            "reason": "local_daily_missing_raw_contract:" + ",".join(missing),
            "days": [],
        }
    bases = set(daily["price_basis"].dropna().astype(str))
    if bases != {REQUIRED_DAILY_PRICE_BASIS}:
        return {
            "status": "failed",
            "reason": f"unaccepted_local_daily_price_basis:{sorted(bases)}",
            "days": [],
        }
    daily["date"] = pd.to_datetime(daily["date"]).dt.normalize()
    daily = daily.set_index("date")
    work = frame.assign(trade_date=frame["datetime"].dt.normalize())
    days: list[dict[str, Any]] = []
    for trade_date, group in work.groupby("trade_date", sort=True):
        daily_row = daily.loc[daily.index == trade_date]
        if daily_row.empty:
            days.append(
                {
                    "trade_date": trade_date.date().isoformat(),
                    "status": "missing_local_daily",
                }
            )
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
            field: _relative_error(minute_ohlc[field], float(reference[f"raw_{field}"]))
            for field in ("open", "high", "low", "close")
        }
        volume_ratio = (
            float(group["volume"].sum() / float(reference["raw_volume"]))
            if float(reference["raw_volume"])
            else None
        )
        amount_ratio = (
            float(group["amount"].sum() / float(reference["amount"]))
            if float(reference["amount"])
            else None
        )
        price_ok = all(
            error is not None and error <= 0.002
            for error in price_relative_errors.values()
        )
        amount_ok = amount_ratio is not None and abs(amount_ratio - 1.0) <= 0.005
        # The public daily pipe reports volume in lots.  Sources can report
        # shares or lots, so accept either 1x or 100x here but record the
        # inferred ratio; never rescale a provider silently.
        volume_ok = (
            volume_ratio is not None
            and min(abs(volume_ratio - 1.0), abs(volume_ratio - 100.0)) <= 0.005
        )
        days.append(
            {
                "trade_date": trade_date.date().isoformat(),
                "status": (
                    "passed" if price_ok and amount_ok and volume_ok else "failed"
                ),
                "price_relative_errors": price_relative_errors,
                "amount_ratio_to_local_daily": amount_ratio,
                "volume_ratio_to_local_daily": volume_ratio,
                "inferred_volume_unit": (
                    "shares"
                    if volume_ratio is not None and abs(volume_ratio - 100.0) <= 0.005
                    else "lots"
                ),
            }
        )
    statuses = [day["status"] for day in days]
    if statuses and all(status == "passed" for status in statuses):
        status = "passed"
    elif "missing_local_daily" in statuses:
        status = "unavailable"
    else:
        status = "failed"
    return {
        "status": status,
        "daily_price_basis": "raw_unadjusted_to_raw_daily",
        "days": days,
    }


def minute_acceptance_report(frame: pd.DataFrame) -> dict[str, Any]:
    """Run the automatic checks required before minute data may become features."""

    session = minute_session_check(frame)
    reconciliation = minute_daily_reconciliation(frame)
    passed = session["status"] == "passed" and reconciliation["status"] == "passed"
    return {
        "status": (
            "automatic_checks_passed_pending_time_alignment"
            if passed
            else "automatic_checks_failed"
        ),
        "session": session,
        "daily_reconciliation": reconciliation,
    }


def _import_tushare() -> Any:
    import tushare as ts

    ts.set_token(os.environ["TUSHARE_TOKEN"])
    return ts


def _query_baostock_5m(
    client: Any, code: str, start: dt.date, end: dt.date
) -> pd.DataFrame:
    """Query one raw partition through an already authenticated BaoStock client."""

    fields = "date,time,code,open,high,low,close,volume,amount,adjustflag"
    response = client.query_history_k_data_plus(
        vendor_symbol(code, "baostock"),
        fields,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        frequency="5",
        adjustflag="3",
    )
    if str(response.error_code) != "0":
        raise RichDataError(
            f"BaoStock five-minute query failed for {code}: {response.error_msg}"
        )
    rows: list[list[str]] = []
    while response.next():
        rows.append(response.get_row_data())
    frame = pd.DataFrame(rows, columns=response.fields)
    if frame.empty:
        return frame
    expected_fields = fields.split(",")
    if list(frame.columns) != expected_fields:
        raise RichDataError(
            "BaoStock five-minute response changed its frozen field schema"
        )
    if set(frame["adjustflag"].astype(str)) != {"3"}:
        raise RichDataError(
            "BaoStock five-minute response is not entirely raw unadjusted data"
        )
    frame["datetime"] = pd.to_datetime(
        frame["time"], format="%Y%m%d%H%M%S%f", errors="coerce"
    )
    if frame["datetime"].isna().any():
        raise RichDataError(
            "BaoStock five-minute response contains an invalid timestamp"
        )
    return frame


def fetch_baostock_minutes(
    code: str, start: dt.date, end: dt.date, frequency: str
) -> pd.DataFrame:
    """Fetch only the frozen anonymous raw five-minute BaoStock fields."""

    if frequency != "5m":
        raise RichDataError(
            "the frozen BaoStock intraday contract supports only 5m bars"
        )
    import baostock as bs

    login = bs.login()
    if str(login.error_code) != "0":
        raise RichDataError(f"BaoStock anonymous login failed: {login.error_msg}")
    try:
        frame = _query_baostock_5m(bs, code, start, end)
    finally:
        bs.logout()
    return frame


_BAOSTOCK_WORKER_CLIENT: Any | None = None


def initialize_baostock_5m_worker() -> None:
    """Authenticate one anonymous BaoStock session per process."""

    import baostock as bs

    login = bs.login()
    if str(login.error_code) != "0":
        raise RichDataError(f"BaoStock worker login failed: {login.error_msg}")
    global _BAOSTOCK_WORKER_CLIENT
    _BAOSTOCK_WORKER_CLIENT = bs
    atexit.register(bs.logout)


def fetch_baostock_5m_request_worker(
    task: tuple[str, str, str],
) -> tuple[str, str, str, pd.DataFrame]:
    """Fetch one PIT instrument interval and canonicalize it with fixed retries."""

    code, start_value, end_value = task
    if _BAOSTOCK_WORKER_CLIENT is None:
        raise RichDataError("BaoStock five-minute worker is not initialized")
    start = dt.date.fromisoformat(start_value)
    end = dt.date.fromisoformat(end_value)
    error: Exception | None = None
    for attempt in range(1, BAOSTOCK_5M_PARTITION_RETRIES + 1):
        try:
            raw = _query_baostock_5m(_BAOSTOCK_WORKER_CLIENT, code, start, end)
            frame = canonicalize_baostock_5m_bars(raw, code, start, end)
            return code, start_value, end_value, frame
        except (
            Exception
        ) as exc:  # noqa: BLE001 - worker must preserve the final provider error.
            error = exc
            if "黑名单用户" in str(exc):
                break
            if attempt < BAOSTOCK_5M_PARTITION_RETRIES:
                time.sleep(float(attempt))
    attempts = (
        1
        if error is not None and "黑名单用户" in str(error)
        else BAOSTOCK_5M_PARTITION_RETRIES
    )
    raise RichDataError(
        f"BaoStock five-minute PIT request failed after {attempts} attempt(s): "
        f"{code} {start_value} {end_value}: {error}"
    )


def download_baostock_5m_requests(
    tasks: Iterable[tuple[str, str, str]],
    workers: int,
) -> Iterable[tuple[str, str, str, pd.DataFrame]]:
    """Yield PIT interval responses while bounding submitted work and process count."""

    if not 1 <= workers <= BAOSTOCK_5M_MAX_WORKERS:
        raise RichDataError(
            f"BaoStock five-minute workers must be between 1 and {BAOSTOCK_5M_MAX_WORKERS}"
        )
    task_iterator = iter(tasks)
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers,
        initializer=initialize_baostock_5m_worker,
    ) as executor:
        pending: dict[
            concurrent.futures.Future[tuple[str, str, str, pd.DataFrame]], None
        ] = {}
        for _ in range(workers * 2):
            try:
                pending[
                    executor.submit(
                        fetch_baostock_5m_request_worker, next(task_iterator)
                    )
                ] = None
            except StopIteration:
                break
        while pending:
            completed, _ = concurrent.futures.wait(
                pending, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for future in completed:
                del pending[future]
                yield future.result()
                try:
                    task = next(task_iterator)
                except StopIteration:
                    continue
                pending[executor.submit(fetch_baostock_5m_request_worker, task)] = None


def fetch_tushare_minutes(
    code: str, start: dt.date, end: dt.date, frequency: str
) -> pd.DataFrame:
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


def fetch_jqdata_minutes(
    code: str, start: dt.date, end: dt.date, frequency: str
) -> pd.DataFrame:
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


def fetch_jqdata_moneyflow_pro(
    codes: list[str], start: dt.date, end: dt.date
) -> pd.DataFrame:
    """Fetch only the eight frozen daily classified-flow amount fields."""

    from jqdatasdk import auth, get_money_flow_pro

    authenticated = auth(os.environ["JQDATA_USERNAME"], os.environ["JQDATA_PASSWORD"])
    if authenticated is False:
        raise RichDataError("JQData rejected the configured credentials")
    result = get_money_flow_pro(
        [vendor_symbol(code, "jqdata") for code in codes],
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        frequency="daily",
        fields=list(JQDATA_MONEYFLOW_RAW_FIELDS),
        data_type="money",
    )
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_moneyflow(trade_date: dt.date) -> pd.DataFrame:
    """Fetch one complete session using only the frozen Tushare field whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.moneyflow(
            trade_date=trade_date.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_MONEYFLOW_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            f"Tushare moneyflow request failed for {trade_date.isoformat()}: {exc}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_northbound_top10(
    trade_date: dt.date, market_type: str
) -> pd.DataFrame:
    """Fetch one market/session using only the frozen Northbound whitelist."""

    if str(market_type) not in TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES:
        raise RichDataError(f"unsupported Northbound market_type: {market_type}")
    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.hsgt_top10(
            trade_date=trade_date.strftime("%Y%m%d"),
            market_type=str(market_type),
            fields=",".join(TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare hsgt_top10 request failed for "
            f"{trade_date.isoformat()} market_type={market_type}: {exc}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_top_inst(trade_date: dt.date) -> pd.DataFrame:
    """Fetch one institution-seat session using only the frozen whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.top_inst(
            trade_date=trade_date.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_TOP_INST_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare top_inst request failed for "
            f"{trade_date.isoformat()}: {safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_top10_float_holders(
    ts_code: str,
    report_period_start: dt.date,
    report_period_end: dt.date,
) -> pd.DataFrame:
    """Fetch one stock's frozen report-period range with the exact whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.top10_floatholders(
            ts_code=ts_code,
            start_date=report_period_start.strftime("%Y%m%d"),
            end_date=report_period_end.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_TOP10_FLOAT_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare top10_floatholders request failed for "
            f"{ts_code}: {safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_cash_conversion_statement(
    endpoint: str,
    ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
) -> pd.DataFrame:
    """Fetch one frozen income or cashflow partition with its exact whitelist."""

    fields_by_endpoint = {
        "income": TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS,
        "cashflow": TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS,
    }
    if endpoint not in fields_by_endpoint:
        raise RichDataError(f"unsupported Tushare cash-conversion endpoint: {endpoint}")
    ts = _import_tushare()
    pro = ts.pro_api()
    request = getattr(pro, endpoint, None)
    if request is None or not callable(request):
        raise RichDataError(f"Tushare SDK lacks the required {endpoint} endpoint")
    try:
        result = request(
            ts_code=ts_code,
            start_date=announcement_start.strftime("%Y%m%d"),
            end_date=announcement_end.strftime("%Y%m%d"),
            fields=",".join(fields_by_endpoint[endpoint]),
        )
    except Exception as exc:
        raise RichDataError(
            f"Tushare {endpoint} request failed for {ts_code}: "
            f"{safe_exception_text(exc)}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_daily_pb(trade_date: dt.date) -> pd.DataFrame:
    """Fetch one daily_basic session using only the frozen PB whitelist."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.daily_basic(
            trade_date=trade_date.strftime("%Y%m%d"),
            fields=",".join(TUSHARE_DAILY_PB_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            f"Tushare daily_basic PB request failed for {trade_date.isoformat()}: {exc}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_sw_classification() -> pd.DataFrame:
    """Fetch only the frozen SW2021 level-one classification fields."""

    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.index_classify(
            level="L1",
            src="SW2021",
            fields=",".join(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(f"Tushare index_classify request failed: {exc}") from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_tushare_sw_members(l1_code: str, is_new: str) -> pd.DataFrame:
    """Fetch one frozen SW2021 L1/current-state membership partition."""

    if is_new not in {"Y", "N"}:
        raise RichDataError(f"unsupported Tushare SW membership is_new: {is_new}")
    ts = _import_tushare()
    pro = ts.pro_api()
    try:
        result = pro.index_member_all(
            l1_code=l1_code,
            is_new=is_new,
            fields=",".join(TUSHARE_SW_MEMBERSHIP_RAW_FIELDS),
        )
    except Exception as exc:
        raise RichDataError(
            "Tushare index_member_all request failed for "
            f"l1_code={l1_code} is_new={is_new}: {exc}"
        ) from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def fetch_rqdata_minutes(
    code: str, start: dt.date, end: dt.date, frequency: str
) -> pd.DataFrame:
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
    "baostock": fetch_baostock_minutes,
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
        "limit-price": pro.stk_limit,
        "stock-st": pro.stock_st,
        "limit-list": pro.limit_list_d,
        "top-list": pro.top_list,
    }[dataset]
    try:
        result = method(trade_date=trade_date.strftime("%Y%m%d"))
    except Exception as exc:
        raise RichDataError(f"Tushare {dataset} request failed: {exc}") from exc
    if result is None:
        return pd.DataFrame()
    return result.copy()


def tushare_event_quality(
    frame: pd.DataFrame,
    dataset: str,
    trade_date: dt.date,
) -> dict[str, Any]:
    """Audit one raw Tushare event response without changing source rows."""

    keys = TUSHARE_EVENT_KEY_FIELDS[dataset]
    if frame.empty:
        return {
            "status": "empty_source_response",
            "source_rows": 0,
            "missing_key_rows": 0,
            "outside_requested_date_rows": 0,
            "exact_duplicate_rows": 0,
            "duplicate_event_key_rows": 0,
            "raw_rows_preserved_without_deduplication": True,
        }
    missing_columns = [column for column in keys if column not in frame.columns]
    if missing_columns:
        raise RichDataError(
            f"Tushare {dataset} response lacks required columns: "
            + ", ".join(missing_columns)
        )
    missing_key_rows = int(frame[list(keys)].isna().any(axis=1).sum())
    if missing_key_rows:
        raise RichDataError(
            f"Tushare {dataset} response contains {missing_key_rows} rows with missing keys"
        )
    requested = trade_date.strftime("%Y%m%d")
    observed_dates = (
        frame["trade_date"].astype("string").str.replace("-", "", regex=False)
    )
    outside_requested_date_rows = int(observed_dates.ne(requested).sum())
    if outside_requested_date_rows:
        raise RichDataError(
            f"Tushare {dataset} response contains {outside_requested_date_rows} rows "
            "outside the requested date"
        )
    exact_duplicate_rows = int(frame.duplicated().sum())
    duplicate_event_key_rows = int(frame.duplicated(list(keys)).sum())
    return {
        "status": (
            "raw_duplicates_present_pending_canonicalization"
            if exact_duplicate_rows or duplicate_event_key_rows
            else "raw_keys_passed"
        ),
        "source_rows": int(len(frame)),
        "missing_key_rows": missing_key_rows,
        "outside_requested_date_rows": outside_requested_date_rows,
        "exact_duplicate_rows": exact_duplicate_rows,
        "duplicate_event_key_rows": duplicate_event_key_rows,
        "raw_rows_preserved_without_deduplication": True,
    }


def canonicalize_tushare_moneyflow(
    frame: pd.DataFrame,
    start: dt.date,
    end: dt.date,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Normalize Tushare classified amounts and derive the frozen local ratio."""

    empty_stats = {
        "input_rows": 0,
        "missing_rows_excluded": 0,
        "zero_denominator_rows_excluded": 0,
        "rows_written": 0,
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_MONEYFLOW_COLUMNS), empty_stats
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_MONEYFLOW_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare moneyflow response lacks requested fields: "
            + ", ".join(missing_columns)
        )

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        code = str(value).split(".", 1)[0].strip()
        if len(code) != 6 or not code.isdigit():
            return None
        try:
            return qlib_symbol(code)
        except RichDataError:
            return None

    normalized = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                raw["trade_date"].astype("string"), format="%Y%m%d", errors="coerce"
            ).dt.normalize(),
            "instrument": raw["ts_code"].map(instrument),
            **{
                field: pd.to_numeric(raw[field], errors="coerce")
                for field in TUSHARE_MONEYFLOW_AMOUNT_FIELDS
            },
        }
    )
    required = ["trade_date", "instrument", *TUSHARE_MONEYFLOW_AMOUNT_FIELDS]
    complete = normalized[required].notna().all(axis=1)
    missing_rows = int((~complete).sum())
    valid = normalized.loc[complete].copy()
    amount_columns = list(TUSHARE_MONEYFLOW_AMOUNT_FIELDS)
    if valid[amount_columns].lt(0.0).any().any():
        raise RichDataError(
            "Tushare moneyflow response contains a negative raw flow amount"
        )
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if not valid["trade_date"].between(start_ts, end_ts).all():
        raise RichDataError(
            "Tushare moneyflow response contains a date outside the request"
        )
    if valid.duplicated(["instrument", "trade_date"]).any():
        raise RichDataError(
            "Tushare moneyflow response contains duplicate instrument/date keys"
        )
    valid[amount_columns] = valid[amount_columns].astype("float64")
    denominator = valid[amount_columns].sum(axis=1)
    positive = denominator.gt(0.0)
    zero_denominator_rows = int((~positive).sum())
    valid = valid.loc[positive].copy()
    denominator = denominator.loc[positive]
    valid["tushare_large_order_net_inflow_share"] = (
        valid["buy_elg_amount"]
        + valid["buy_lg_amount"]
        - valid["sell_elg_amount"]
        - valid["sell_lg_amount"]
    ) / denominator
    valid["provider"] = "tushare"
    result = (
        valid.loc[:, list(TUSHARE_MONEYFLOW_COLUMNS)]
        .sort_values(["trade_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    if not result["tushare_large_order_net_inflow_share"].between(-1.0, 1.0).all():
        raise RichDataError("derived Tushare large-order ratio falls outside [-1, 1]")
    return result, {
        "input_rows": int(len(raw)),
        "missing_rows_excluded": missing_rows,
        "zero_denominator_rows_excluded": zero_denominator_rows,
        "rows_written": int(len(result)),
    }


def canonicalize_tushare_northbound_top10(
    frame: pd.DataFrame,
    start: dt.date,
    end: dt.date,
    expected_market_type: str | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Normalize one frozen Northbound top-ten response and derive its ratio."""

    empty_stats = {
        "input_rows": 0,
        "missing_rows_excluded": 0,
        "zero_denominator_rows_excluded": 0,
        "rows_written": 0,
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_NORTHBOUND_TOP10_COLUMNS), empty_stats
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare hsgt_top10 response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(
        set(raw.columns) - set(TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS)
    )
    if unexpected_columns:
        raise RichDataError(
            "Tushare hsgt_top10 response contains fields outside the frozen whitelist: "
            + ", ".join(unexpected_columns)
        )

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        code = str(value).split(".", 1)[0].strip()
        if len(code) != 6 or not code.isdigit():
            return None
        try:
            return qlib_symbol(code)
        except RichDataError:
            return None

    numeric_market = pd.to_numeric(raw["market_type"], errors="coerce")
    normalized = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                raw["trade_date"].astype("string"), format="%Y%m%d", errors="coerce"
            ).dt.normalize(),
            "instrument": raw["ts_code"].map(instrument),
            "rank": pd.to_numeric(raw["rank"], errors="coerce"),
            "market_type": numeric_market.map(
                lambda value: str(int(value)) if pd.notna(value) else pd.NA
            ).astype("string"),
            "amount": pd.to_numeric(raw["amount"], errors="coerce"),
            "buy": pd.to_numeric(raw["buy"], errors="coerce"),
            "sell": pd.to_numeric(raw["sell"], errors="coerce"),
        }
    )
    required = [
        "trade_date",
        "instrument",
        "rank",
        "market_type",
        "amount",
        "buy",
        "sell",
    ]
    complete = normalized[required].notna().all(axis=1)
    missing_rows = int((~complete).sum())
    valid = normalized.loc[complete].copy()
    if valid[["amount", "buy", "sell"]].lt(0.0).any().any():
        raise RichDataError(
            "Tushare hsgt_top10 response contains a negative raw amount"
        )
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if not valid["trade_date"].between(start_ts, end_ts).all():
        raise RichDataError(
            "Tushare hsgt_top10 response contains a date outside the request"
        )
    if not valid["market_type"].isin(TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES).all():
        raise RichDataError(
            "Tushare hsgt_top10 response contains an unsupported market_type"
        )
    if (
        expected_market_type is not None
        and not valid["market_type"].eq(str(expected_market_type)).all()
    ):
        raise RichDataError(
            "Tushare hsgt_top10 response market_type differs from the requested market"
        )
    integer_rank = valid["rank"].eq(np.floor(valid["rank"]))
    if not integer_rank.all() or not valid["rank"].between(1, 10).all():
        raise RichDataError(
            "Tushare hsgt_top10 ranks must be integers from 1 through 10"
        )
    valid["rank"] = valid["rank"].astype("int64")
    if valid.duplicated(["trade_date", "market_type", "rank"]).any():
        raise RichDataError(
            "Tushare hsgt_top10 response contains duplicate market ranks"
        )
    if valid.duplicated(["instrument", "trade_date"]).any():
        raise RichDataError(
            "Tushare hsgt_top10 response contains duplicate instrument/date keys"
        )
    market_counts = valid.groupby(["trade_date", "market_type"], observed=True).size()
    if market_counts.gt(10).any():
        raise RichDataError(
            "Tushare hsgt_top10 response contains more than ten rows per market"
        )
    valid[["amount", "buy", "sell"]] = valid[["amount", "buy", "sell"]].astype(
        "float64"
    )
    disclosed_total = valid["buy"] + valid["sell"]
    tolerance = np.maximum(1.0, np.maximum(valid["amount"], disclosed_total) * 0.000001)
    if (valid["amount"].sub(disclosed_total).abs() > tolerance).any():
        raise RichDataError(
            "Tushare hsgt_top10 amount does not reconcile to buy plus sell"
        )
    positive = disclosed_total.gt(0.0)
    zero_denominator_rows = int((~positive).sum())
    valid = valid.loc[positive].copy()
    disclosed_total = disclosed_total.loc[positive]
    valid["tushare_northbound_top10_net_buy_share"] = (
        valid["buy"] - valid["sell"]
    ) / disclosed_total
    valid["provider"] = "tushare"
    result = (
        valid.loc[:, list(TUSHARE_NORTHBOUND_TOP10_COLUMNS)]
        .sort_values(["trade_date", "market_type", "rank"], kind="stable")
        .reset_index(drop=True)
    )
    if not result["tushare_northbound_top10_net_buy_share"].between(-1.0, 1.0).all():
        raise RichDataError("derived Tushare Northbound ratio falls outside [-1, 1]")
    return result, {
        "input_rows": int(len(raw)),
        "missing_rows_excluded": missing_rows,
        "zero_denominator_rows_excluded": zero_denominator_rows,
        "rows_written": int(len(result)),
    }


def canonicalize_tushare_top_inst(
    frame: pd.DataFrame,
    start: dt.date,
    end: dt.date,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Reconcile unique institution-seat rows and derive the frozen ratio."""

    empty_stats = {
        "input_rows": 0,
        "institution_seat_rows_reconciled": 0,
        "zero_denominator_stock_days_excluded": 0,
        "rows_written": 0,
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_TOP_INST_COLUMNS), empty_stats
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_TOP_INST_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare top_inst response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(set(raw.columns) - set(TUSHARE_TOP_INST_RAW_FIELDS))
    if unexpected_columns:
        raise RichDataError(
            "Tushare top_inst response contains fields outside the frozen whitelist: "
            + ", ".join(unexpected_columns)
        )

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        source_code = str(value).strip()
        parts = source_code.split(".", 1)
        if len(parts) != 2:
            return None
        code, suffix = parts[0].strip(), parts[1].strip().upper()
        if len(code) != 6 or not code.isdigit() or suffix not in {"SH", "SZ"}:
            return None
        try:
            symbol = qlib_symbol(code)
        except RichDataError:
            return None
        return symbol if symbol.startswith(suffix) else None

    normalized = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                raw["trade_date"].astype("string"), format="%Y%m%d", errors="coerce"
            ).dt.normalize(),
            "instrument": raw["ts_code"].map(instrument),
            "exalter": raw["exalter"].astype("string").str.strip(),
            "buy": pd.to_numeric(raw["buy"], errors="coerce"),
            "sell": pd.to_numeric(raw["sell"], errors="coerce"),
            "net_buy": pd.to_numeric(raw["net_buy"], errors="coerce"),
        }
    )
    required = ["trade_date", "instrument", "exalter", "buy", "sell", "net_buy"]
    missing = normalized[required].isna().any(axis=1) | normalized["exalter"].eq("")
    finite_amounts = np.isfinite(normalized[["buy", "sell", "net_buy"]]).all(axis=1)
    if missing.any() or (~finite_amounts).any():
        invalid_rows = int((missing | ~finite_amounts).sum())
        raise RichDataError(
            f"Tushare top_inst response contains {invalid_rows} incomplete or non-finite rows"
        )
    if normalized[["buy", "sell"]].lt(0.0).any().any():
        raise RichDataError(
            "Tushare top_inst response contains a negative buy or sell amount"
        )
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if not normalized["trade_date"].between(start_ts, end_ts).all():
        raise RichDataError(
            "Tushare top_inst response contains a date outside the request"
        )
    seat_key = ["trade_date", "instrument", "exalter"]
    if normalized.duplicated(seat_key).any():
        raise RichDataError(
            "Tushare top_inst response contains duplicate institution-seat keys"
        )

    tolerance = np.maximum(
        0.01,
        0.000001
        * np.maximum(
            normalized["net_buy"].abs(),
            normalized["buy"] + normalized["sell"],
        ),
    )
    if (
        normalized["net_buy"].sub(normalized["buy"] - normalized["sell"]).abs()
        > tolerance
    ).any():
        raise RichDataError(
            "Tushare top_inst net_buy does not reconcile to buy minus sell"
        )

    aggregated = (
        normalized.groupby(["trade_date", "instrument"], as_index=False, observed=True)
        .agg(
            institution_seat_count=("exalter", "nunique"),
            buy=("buy", "sum"),
            sell=("sell", "sum"),
        )
        .sort_values(["trade_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    denominator = aggregated["buy"] + aggregated["sell"]
    positive = denominator.gt(0.0)
    zero_denominator_stock_days = int((~positive).sum())
    aggregated = aggregated.loc[positive].copy()
    denominator = denominator.loc[positive]
    aggregated["tushare_top_inst_net_buy_share"] = (
        aggregated["buy"] - aggregated["sell"]
    ) / denominator
    aggregated["provider"] = "tushare"
    result = aggregated.loc[:, list(TUSHARE_TOP_INST_COLUMNS)].reset_index(drop=True)
    factor = result["tushare_top_inst_net_buy_share"]
    if not np.isfinite(factor).all() or not factor.between(-1.0, 1.0).all():
        raise RichDataError(
            "derived Tushare institution-seat ratio falls outside [-1, 1]"
        )
    return result, {
        "input_rows": int(len(raw)),
        "institution_seat_rows_reconciled": int(len(normalized)),
        "zero_denominator_stock_days_excluded": zero_denominator_stock_days,
        "rows_written": int(len(result)),
    }


def canonicalize_tushare_top10_float_holders(
    frame: pd.DataFrame,
    expected_ts_code: str,
    report_period_start: dt.date,
    report_period_end: dt.date,
    latest_announcement_date: dt.date,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Hash identities, select first complete reports, and derive quarter changes."""

    empty_quality = {
        "input_rows": 0,
        "source_rows_written": 0,
        "report_groups_observed": 0,
        "complete_report_groups": 0,
        "incomplete_report_groups_excluded": 0,
        "first_complete_report_periods": 0,
        "later_complete_revision_groups_not_used": 0,
        "factor_ready_consecutive_pairs": 0,
    }
    if frame is None or frame.empty:
        return (
            pd.DataFrame(columns=TUSHARE_TOP10_FLOAT_SOURCE_COLUMNS),
            pd.DataFrame(columns=TUSHARE_TOP10_FLOAT_FACTOR_COLUMNS),
            empty_quality,
        )
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_TOP10_FLOAT_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare top10_floatholders response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(set(raw.columns) - set(TUSHARE_TOP10_FLOAT_RAW_FIELDS))
    if unexpected_columns:
        raise RichDataError(
            "Tushare top10_floatholders response contains fields outside the "
            "frozen whitelist: " + ", ".join(unexpected_columns)
        )

    expected_parts = expected_ts_code.strip().upper().split(".", 1)
    if (
        len(expected_parts) != 2
        or len(expected_parts[0]) != 6
        or not expected_parts[0].isdigit()
        or expected_parts[1] not in {"SH", "SZ"}
    ):
        raise RichDataError(
            f"invalid frozen top10_floatholders stock code: {expected_ts_code}"
        )
    expected_instrument = qlib_symbol(expected_parts[0])
    if not expected_instrument.startswith(expected_parts[1]):
        raise RichDataError(
            f"stock code and exchange suffix disagree: {expected_ts_code}"
        )

    def normalized_holder_name(value: Any) -> str | None:
        if pd.isna(value):
            return None
        normalized = unicodedata.normalize("NFKC", str(value))
        normalized = " ".join(normalized.strip().split())
        return normalized or None

    holder_names = raw["holder_name"].map(normalized_holder_name)
    normalized = pd.DataFrame(
        {
            "announcement_date": pd.to_datetime(
                raw["ann_date"].astype("string"),
                format="%Y%m%d",
                errors="coerce",
            ).dt.normalize(),
            "report_period": pd.to_datetime(
                raw["end_date"].astype("string"),
                format="%Y%m%d",
                errors="coerce",
            ).dt.normalize(),
            "instrument": expected_instrument,
            "holder_name": holder_names,
            "hold_float_ratio": pd.to_numeric(raw["hold_float_ratio"], errors="coerce"),
            "source_ts_code": raw["ts_code"].astype("string").str.strip().str.upper(),
        }
    )
    required = [
        "announcement_date",
        "report_period",
        "holder_name",
        "hold_float_ratio",
        "source_ts_code",
    ]
    missing = normalized[required].isna().any(axis=1)
    finite_ratio = np.isfinite(normalized["hold_float_ratio"])
    if missing.any() or (~finite_ratio).any():
        invalid_rows = int((missing | ~finite_ratio).sum())
        raise RichDataError(
            "Tushare top10_floatholders response contains "
            f"{invalid_rows} incomplete or non-finite rows"
        )
    if not normalized["source_ts_code"].eq(expected_ts_code.upper()).all():
        observed = sorted(set(normalized["source_ts_code"].astype(str)))
        raise RichDataError(
            "Tushare top10_floatholders response contains a stock outside its "
            f"request: expected {expected_ts_code.upper()}, observed {observed}"
        )
    ratio = normalized["hold_float_ratio"]
    if not ratio.between(0.0, 100.0).all():
        raise RichDataError(
            "Tushare top10_floatholders response contains a ratio outside [0, 100]"
        )
    report_start = pd.Timestamp(report_period_start)
    report_end = pd.Timestamp(report_period_end)
    if not normalized["report_period"].between(report_start, report_end).all():
        raise RichDataError(
            "Tushare top10_floatholders response contains a report period outside "
            "the request"
        )
    standard_quarter_end = (
        normalized["report_period"]
        .dt.strftime("%m%d")
        .isin({"0331", "0630", "0930", "1231"})
    )
    if not standard_quarter_end.all():
        raise RichDataError(
            "Tushare top10_floatholders response contains a non-quarter-end period"
        )
    if normalized["announcement_date"].gt(pd.Timestamp(latest_announcement_date)).any():
        raise RichDataError(
            "Tushare top10_floatholders response contains a future announcement"
        )
    if normalized["announcement_date"].lt(normalized["report_period"]).any():
        raise RichDataError(
            "Tushare top10_floatholders response contains an announcement before "
            "its report period"
        )

    normalized["holder_name_sha256"] = normalized["holder_name"].map(
        lambda value: hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    )
    raw_event_key = [
        "announcement_date",
        "report_period",
        "instrument",
        "holder_name_sha256",
    ]
    if normalized.duplicated(raw_event_key).any():
        raise RichDataError(
            "Tushare top10_floatholders response contains duplicate holder event keys"
        )

    persisted = normalized.assign(provider="tushare").loc[
        :, list(TUSHARE_TOP10_FLOAT_SOURCE_COLUMNS)
    ]
    persisted = persisted.sort_values(
        ["instrument", "report_period", "announcement_date", "holder_name_sha256"],
        kind="stable",
    ).reset_index(drop=True)

    group_key = ["instrument", "report_period", "announcement_date"]
    groups = (
        persisted.groupby(group_key, as_index=False, observed=True)
        .agg(
            top10_float_holder_count=("holder_name_sha256", "nunique"),
            top10_float_concentration_pct=("hold_float_ratio", "sum"),
        )
        .sort_values(group_key, kind="stable")
        .reset_index(drop=True)
    )
    if groups["top10_float_holder_count"].gt(10).any():
        raise RichDataError(
            "Tushare top10_floatholders response contains more than ten unique "
            "holders in one report group"
        )
    complete = groups["top10_float_holder_count"].eq(10)
    complete_groups = groups.loc[complete].copy()
    concentration = complete_groups["top10_float_concentration_pct"]
    if (
        not np.isfinite(concentration).all()
        or concentration.lt(0.0).any()
        or concentration.gt(100.000001).any()
    ):
        raise RichDataError(
            "Tushare top10_floatholders complete-group concentration falls "
            "outside [0, 100.000001]"
        )
    first_complete = (
        complete_groups.sort_values(
            ["instrument", "report_period", "announcement_date"], kind="stable"
        )
        .drop_duplicates(["instrument", "report_period"], keep="first")
        .reset_index(drop=True)
    )

    def previous_quarter(period: pd.Timestamp) -> pd.Timestamp:
        if period.month == 3:
            return pd.Timestamp(year=period.year - 1, month=12, day=31)
        if period.month == 6:
            return pd.Timestamp(year=period.year, month=3, day=31)
        if period.month == 9:
            return pd.Timestamp(year=period.year, month=6, day=30)
        return pd.Timestamp(year=period.year, month=9, day=30)

    lookup = {
        (str(row.instrument), pd.Timestamp(row.report_period)): row
        for row in first_complete.itertuples(index=False)
    }
    factor_rows: list[dict[str, Any]] = []
    for row in first_complete.itertuples(index=False):
        report_period = pd.Timestamp(row.report_period)
        prior_period = previous_quarter(report_period)
        prior = lookup.get((str(row.instrument), prior_period))
        if prior is None or pd.Timestamp(prior.announcement_date) > pd.Timestamp(
            row.announcement_date
        ):
            continue
        change = float(row.top10_float_concentration_pct) - float(
            prior.top10_float_concentration_pct
        )
        factor_rows.append(
            {
                "announcement_date": pd.Timestamp(row.announcement_date),
                "report_period": report_period,
                "previous_report_period": prior_period,
                "instrument": str(row.instrument),
                "top10_float_holder_count": int(row.top10_float_holder_count),
                "top10_float_concentration_pct": float(
                    row.top10_float_concentration_pct
                ),
                "top10_float_concentration_change_pp": change,
                "provider": "tushare",
            }
        )
    factors = (
        pd.DataFrame(factor_rows, columns=TUSHARE_TOP10_FLOAT_FACTOR_COLUMNS)
        .sort_values(
            ["instrument", "report_period", "announcement_date"], kind="stable"
        )
        .reset_index(drop=True)
    )
    if not factors.empty:
        changes = factors["top10_float_concentration_change_pp"]
        if (
            not np.isfinite(changes).all()
            or changes.lt(-100.000001).any()
            or changes.gt(100.000001).any()
        ):
            raise RichDataError(
                "derived top-ten float concentration change falls outside its "
                "frozen bounds"
            )
        if factors.duplicated(
            ["instrument", "announcement_date", "report_period"]
        ).any():
            raise RichDataError(
                "derived top-ten float concentration contains duplicate factor keys"
            )
    return (
        persisted,
        factors,
        {
            "input_rows": int(len(raw)),
            "source_rows_written": int(len(persisted)),
            "report_groups_observed": int(len(groups)),
            "complete_report_groups": int(complete.sum()),
            "incomplete_report_groups_excluded": int((~complete).sum()),
            "first_complete_report_periods": int(len(first_complete)),
            "later_complete_revision_groups_not_used": int(
                len(complete_groups) - len(first_complete)
            ),
            "factor_ready_consecutive_pairs": int(len(factors)),
        },
    )


def canonicalize_tushare_cash_conversion_endpoint(
    frame: pd.DataFrame,
    endpoint: str,
    expected_ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
    latest_actual_announcement_date: dt.date,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the frozen statement-version policy before cross-endpoint joining."""

    endpoint_specs = {
        "income": {
            "raw_fields": TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS,
            "metric": "n_income_attr_p",
            "columns": TUSHARE_CASH_CONVERSION_INCOME_COLUMNS,
            "announcement_column": "income_announcement_date",
            "actual_column": "income_actual_announcement_date",
        },
        "cashflow": {
            "raw_fields": TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS,
            "metric": "n_cashflow_act",
            "columns": TUSHARE_CASH_CONVERSION_CASHFLOW_COLUMNS,
            "announcement_column": "cashflow_announcement_date",
            "actual_column": "cashflow_actual_announcement_date",
        },
    }
    if endpoint not in endpoint_specs:
        raise RichDataError(f"unsupported cash-conversion endpoint: {endpoint}")
    spec = endpoint_specs[endpoint]
    empty_quality: dict[str, Any] = {
        "input_rows": 0,
        "non_target_company_rows_excluded": 0,
        "target_company_periods_observed": 0,
        "adjustment_periods_excluded": 0,
        "no_type_one_periods_excluded": 0,
        "missing_metric_periods_excluded": 0,
        "ambiguous_type_one_periods_excluded": 0,
        "semantic_duplicate_rows_collapsed": 0,
        "accepted_periods": 0,
        "update_flag_counts": {},
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=spec["columns"]), empty_quality

    raw = frame.copy()
    raw_fields = tuple(spec["raw_fields"])
    missing_columns = [field for field in raw_fields if field not in raw]
    if missing_columns:
        raise RichDataError(
            f"Tushare {endpoint} response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(set(raw.columns) - set(raw_fields))
    if unexpected_columns:
        raise RichDataError(
            f"Tushare {endpoint} response contains fields outside the frozen "
            "whitelist: " + ", ".join(unexpected_columns)
        )

    expected_code = expected_ts_code.strip().upper()
    expected_parts = expected_code.split(".", 1)
    if (
        len(expected_parts) != 2
        or len(expected_parts[0]) != 6
        or not expected_parts[0].isdigit()
        or expected_parts[1] not in {"SH", "SZ"}
    ):
        raise RichDataError(
            f"invalid frozen cash-conversion stock code: {expected_ts_code}"
        )
    expected_instrument = qlib_symbol(expected_parts[0])
    if not expected_instrument.startswith(expected_parts[1]):
        raise RichDataError(
            f"stock code and exchange suffix disagree: {expected_ts_code}"
        )

    source_code = (
        raw["ts_code"].astype("string").str.strip().str.upper().replace("", pd.NA)
    )
    announcement_date = pd.to_datetime(
        raw["ann_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    actual_announcement_date = pd.to_datetime(
        raw["f_ann_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    report_period = pd.to_datetime(
        raw["end_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.normalize()
    report_type_number = pd.to_numeric(raw["report_type"], errors="coerce")
    company_type_number = pd.to_numeric(raw["comp_type"], errors="coerce")
    update_flag = raw["update_flag"].astype("string").str.strip().replace("", pd.NA)
    report_type_integer = (
        report_type_number.notna()
        & pd.Series(np.isfinite(report_type_number), index=raw.index)
        & report_type_number.mod(1).eq(0)
    )
    company_type_integer = (
        company_type_number.notna()
        & pd.Series(np.isfinite(company_type_number), index=raw.index)
        & company_type_number.mod(1).eq(0)
    )
    invalid_key = (
        source_code.isna()
        | announcement_date.isna()
        | actual_announcement_date.isna()
        | report_period.isna()
        | ~report_type_integer
        | ~company_type_integer
        | update_flag.isna()
    )
    if invalid_key.any():
        raise RichDataError(
            f"Tushare {endpoint} response contains "
            f"{int(invalid_key.sum())} rows with incomplete or invalid statement keys"
        )

    report_type = report_type_number.astype(int)
    company_type = company_type_number.astype(int)
    unknown_report_types = sorted(
        set(report_type.astype(int)) - TUSHARE_CASH_CONVERSION_KNOWN_REPORT_TYPES
    )
    if unknown_report_types:
        raise RichDataError(
            f"Tushare {endpoint} response contains unknown report types: "
            f"{unknown_report_types}"
        )
    unknown_company_types = sorted(
        set(company_type.astype(int)) - TUSHARE_CASH_CONVERSION_KNOWN_COMPANY_TYPES
    )
    if unknown_company_types:
        raise RichDataError(
            f"Tushare {endpoint} response contains unknown company types: "
            f"{unknown_company_types}"
        )
    if not source_code.eq(expected_code).all():
        observed = sorted(set(source_code.astype(str)))
        raise RichDataError(
            f"Tushare {endpoint} response contains a stock outside its request: "
            f"expected {expected_code}, observed {observed}"
        )

    start_stamp = pd.Timestamp(announcement_start)
    end_stamp = pd.Timestamp(announcement_end)
    latest_stamp = pd.Timestamp(latest_actual_announcement_date)
    if announcement_date.lt(start_stamp).any() or announcement_date.gt(end_stamp).any():
        raise RichDataError(
            f"Tushare {endpoint} response contains an announcement outside the "
            "frozen request range"
        )
    if actual_announcement_date.lt(announcement_date).any():
        raise RichDataError(
            f"Tushare {endpoint} response contains an actual announcement before ann_date"
        )
    if actual_announcement_date.gt(latest_stamp).any():
        raise RichDataError(
            f"Tushare {endpoint} response contains an actual announcement after "
            "the frozen observation date"
        )
    if report_period.gt(announcement_date).any():
        raise RichDataError(
            f"Tushare {endpoint} response contains a report period after ann_date"
        )
    standard_quarter_ends = {"03-31", "06-30", "09-30", "12-31"}
    if not report_period.dt.strftime("%m-%d").isin(standard_quarter_ends).all():
        raise RichDataError(
            f"Tushare {endpoint} response contains a non-standard quarter end"
        )

    metric_name = str(spec["metric"])
    metric = pd.to_numeric(raw[metric_name], errors="coerce")
    normalized = pd.DataFrame(
        {
            "announcement_date": announcement_date,
            "actual_announcement_date": actual_announcement_date,
            "report_period": report_period,
            "instrument": expected_instrument,
            "report_type": report_type,
            "company_type": company_type,
            "metric": metric,
            "update_flag": update_flag,
        }
    )
    update_flag_counts = {
        str(key): int(value)
        for key, value in normalized["update_flag"]
        .value_counts(dropna=False)
        .sort_index()
        .items()
    }
    target = normalized.loc[normalized["company_type"].eq(1)].copy()
    quality: dict[str, Any] = {
        "input_rows": int(len(normalized)),
        "non_target_company_rows_excluded": int(normalized["company_type"].ne(1).sum()),
        "target_company_periods_observed": int(target["report_period"].nunique()),
        "adjustment_periods_excluded": 0,
        "no_type_one_periods_excluded": 0,
        "missing_metric_periods_excluded": 0,
        "ambiguous_type_one_periods_excluded": 0,
        "semantic_duplicate_rows_collapsed": 0,
        "accepted_periods": 0,
        "update_flag_counts": update_flag_counts,
    }
    accepted_rows: list[dict[str, Any]] = []
    for period, group in target.groupby("report_period", sort=True, observed=True):
        observed_types = set(group["report_type"].astype(int))
        if observed_types & TUSHARE_CASH_CONVERSION_ADJUSTMENT_REPORT_TYPES:
            quality["adjustment_periods_excluded"] += 1
            continue
        type_one = group.loc[group["report_type"].eq(1)].copy()
        if type_one.empty:
            quality["no_type_one_periods_excluded"] += 1
            continue
        finite_metric = pd.Series(np.isfinite(type_one["metric"]), index=type_one.index)
        if type_one["metric"].isna().any() or (~finite_metric).any():
            quality["missing_metric_periods_excluded"] += 1
            continue
        semantic = type_one.drop_duplicates(
            ["announcement_date", "actual_announcement_date", "metric"]
        )
        if len(semantic) != 1:
            quality["ambiguous_type_one_periods_excluded"] += 1
            continue
        quality["semantic_duplicate_rows_collapsed"] += int(len(type_one) - 1)
        row = semantic.iloc[0]
        accepted_rows.append(
            {
                str(spec["announcement_column"]): pd.Timestamp(
                    row["announcement_date"]
                ),
                str(spec["actual_column"]): pd.Timestamp(
                    row["actual_announcement_date"]
                ),
                "report_period": pd.Timestamp(period),
                "instrument": expected_instrument,
                metric_name: float(row["metric"]),
                "provider": "tushare",
            }
        )

    accepted = pd.DataFrame(accepted_rows, columns=spec["columns"])
    if not accepted.empty:
        accepted = accepted.sort_values(
            ["instrument", "report_period"], kind="stable"
        ).reset_index(drop=True)
        if accepted.duplicated(["instrument", "report_period"]).any():
            raise RichDataError(
                f"canonical Tushare {endpoint} rows contain a duplicate period key"
            )
    quality["accepted_periods"] = int(len(accepted))
    return accepted, quality


def derive_tushare_cash_conversion(
    income: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Join accepted statement periods and derive the sole frozen ratio."""

    if income.columns.tolist() != list(TUSHARE_CASH_CONVERSION_INCOME_COLUMNS):
        raise RichDataError(
            "cash-conversion income columns do not match the frozen schema"
        )
    if cashflow.columns.tolist() != list(TUSHARE_CASH_CONVERSION_CASHFLOW_COLUMNS):
        raise RichDataError(
            "cash-conversion cashflow columns do not match the frozen schema"
        )
    key = ["instrument", "report_period"]
    if income.duplicated(key).any() or cashflow.duplicated(key).any():
        raise RichDataError(
            "cash-conversion endpoint rows contain duplicate period keys"
        )
    income_keys = set(income.loc[:, key].itertuples(index=False, name=None))
    cashflow_keys = set(cashflow.loc[:, key].itertuples(index=False, name=None))
    joined = income.merge(
        cashflow,
        on=key,
        how="inner",
        suffixes=("_income", "_cashflow"),
        validate="one_to_one",
    )
    quality: dict[str, Any] = {
        "income_accepted_periods": int(len(income)),
        "cashflow_accepted_periods": int(len(cashflow)),
        "income_only_periods_excluded": int(len(income_keys - cashflow_keys)),
        "cashflow_only_periods_excluded": int(len(cashflow_keys - income_keys)),
        "joined_periods_before_metric_policy": int(len(joined)),
        "nonpositive_income_periods_excluded": 0,
        "nonfinite_cashflow_periods_excluded": 0,
        "nonfinite_derived_periods_excluded": 0,
        "usable_joined_periods": 0,
    }
    if joined.empty:
        return pd.DataFrame(columns=TUSHARE_CASH_CONVERSION_COLUMNS), quality
    if (
        not joined["provider_income"].eq("tushare").all()
        or not joined["provider_cashflow"].eq("tushare").all()
    ):
        raise RichDataError("cash-conversion endpoint provider identity mismatch")

    denominator = pd.to_numeric(joined["n_income_attr_p"], errors="coerce")
    numerator = pd.to_numeric(joined["n_cashflow_act"], errors="coerce")
    denominator_finite = pd.Series(np.isfinite(denominator), index=joined.index)
    numerator_finite = pd.Series(np.isfinite(numerator), index=joined.index)
    positive_denominator = denominator_finite & denominator.gt(0.0)
    quality["nonpositive_income_periods_excluded"] = int((~positive_denominator).sum())
    quality["nonfinite_cashflow_periods_excluded"] = int((~numerator_finite).sum())
    base_eligible = positive_denominator & numerator_finite
    derived = pd.Series(np.nan, index=joined.index, dtype="float64")
    derived.loc[base_eligible] = (
        numerator.loc[base_eligible] / denominator.loc[base_eligible]
    )
    derived_finite = pd.Series(np.isfinite(derived), index=joined.index)
    quality["nonfinite_derived_periods_excluded"] = int(
        (base_eligible & ~derived_finite).sum()
    )
    eligible = base_eligible & derived_finite
    accepted = joined.loc[eligible].copy()
    accepted["announcement_date"] = accepted[
        ["income_actual_announcement_date", "cashflow_actual_announcement_date"]
    ].max(axis=1)
    accepted["tushare_operating_cash_conversion"] = derived.loc[eligible]
    accepted["provider"] = "tushare"
    accepted = (
        accepted.loc[:, list(TUSHARE_CASH_CONVERSION_COLUMNS)]
        .sort_values(
            ["instrument", "report_period", "announcement_date"], kind="stable"
        )
        .reset_index(drop=True)
    )
    if accepted.duplicated(["instrument", "announcement_date", "report_period"]).any():
        raise RichDataError("cash-conversion factor rows contain duplicate event keys")
    quality["usable_joined_periods"] = int(len(accepted))
    return accepted, quality


def canonicalize_tushare_daily_pb(
    frame: pd.DataFrame,
    start: dt.date,
    end: dt.date,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Normalize a daily_basic PB response and derive positive book-to-market."""

    empty_stats = {
        "input_rows": 0,
        "missing_pb_rows_excluded": 0,
        "nonpositive_pb_rows_excluded": 0,
        "rows_written": 0,
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_DAILY_PB_COLUMNS), empty_stats
    raw = frame.copy()
    missing_columns = [
        field for field in TUSHARE_DAILY_PB_RAW_FIELDS if field not in raw
    ]
    if missing_columns:
        raise RichDataError(
            "Tushare daily_basic PB response lacks requested fields: "
            + ", ".join(missing_columns)
        )
    unexpected_columns = sorted(set(raw.columns) - set(TUSHARE_DAILY_PB_RAW_FIELDS))
    if unexpected_columns:
        raise RichDataError(
            "Tushare daily_basic PB response contains fields outside the frozen whitelist: "
            + ", ".join(unexpected_columns)
        )

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        source_code = str(value).strip()
        parts = source_code.split(".", 1)
        code = parts[0].strip()
        if len(code) != 6 or not code.isdigit():
            return None
        suffix = parts[1].upper() if len(parts) == 2 else ""
        # Tushare back-labels some historical NEEQ rows with a ``.BJ``
        # suffix.  The frozen PB contract explicitly excludes and counts BSE
        # names at the point-in-time holding-universe gate.  Preserve their
        # source identity long enough to reach that gate instead of
        # misclassifying a valid six-digit source key as missing.
        if suffix == "BJ" and code.startswith(("4", "8")):
            return f"BJ{code}"
        try:
            symbol = qlib_symbol(code)
        except RichDataError:
            return None
        if suffix in {"SH", "SZ"} and not symbol.startswith(suffix):
            return None
        return symbol

    normalized = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                raw["trade_date"].astype("string"), format="%Y%m%d", errors="coerce"
            ).dt.normalize(),
            "instrument": raw["ts_code"].map(instrument),
            "pb": pd.to_numeric(raw["pb"], errors="coerce"),
        }
    )
    missing_key = normalized[["trade_date", "instrument"]].isna().any(axis=1)
    if missing_key.any():
        raise RichDataError(
            f"Tushare daily_basic PB response contains {int(missing_key.sum())} missing keys"
        )
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if not normalized["trade_date"].between(start_ts, end_ts).all():
        raise RichDataError(
            "Tushare daily_basic PB response contains a date outside the request"
        )
    if normalized.duplicated(["instrument", "trade_date"]).any():
        raise RichDataError(
            "Tushare daily_basic PB response contains duplicate instrument/date keys"
        )
    finite_or_missing = normalized["pb"].isna() | np.isfinite(normalized["pb"])
    if not finite_or_missing.all():
        raise RichDataError(
            "Tushare daily_basic PB response contains an infinite PB value"
        )
    missing_pb = normalized["pb"].isna()
    nonpositive_pb = normalized["pb"].notna() & normalized["pb"].le(0.0)
    valid = normalized.loc[~missing_pb & ~nonpositive_pb].copy()
    valid["pb"] = valid["pb"].astype("float64")
    valid["tushare_positive_book_to_market"] = 1.0 / valid["pb"]
    if (
        not np.isfinite(valid["tushare_positive_book_to_market"]).all()
        or not valid["tushare_positive_book_to_market"].gt(0.0).all()
    ):
        raise RichDataError("derived Tushare book-to-market is not finite and positive")
    valid["provider"] = "tushare"
    result = (
        valid.loc[:, list(TUSHARE_DAILY_PB_COLUMNS)]
        .sort_values(["trade_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    return result, {
        "input_rows": int(len(raw)),
        "missing_pb_rows_excluded": int(missing_pb.sum()),
        "nonpositive_pb_rows_excluded": int(nonpositive_pb.sum()),
        "rows_written": int(len(result)),
    }


def canonicalize_tushare_sw_classification(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate the frozen SW2021 level-one classification response."""

    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_SW_CLASSIFICATION_RAW_FIELDS)
    raw = frame.copy()
    missing = [
        field for field in TUSHARE_SW_CLASSIFICATION_RAW_FIELDS if field not in raw
    ]
    if missing:
        raise RichDataError(
            "Tushare SW classification response lacks requested fields: "
            + ", ".join(missing)
        )
    unexpected = sorted(set(raw.columns) - set(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS))
    if unexpected:
        raise RichDataError(
            "Tushare SW classification response contains fields outside the frozen whitelist: "
            + ", ".join(unexpected)
        )
    result = raw.loc[:, list(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS)].copy()
    for column in TUSHARE_SW_CLASSIFICATION_RAW_FIELDS:
        result[column] = result[column].astype("string").str.strip()
    if result[list(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS)].isna().any(axis=None):
        raise RichDataError(
            "Tushare SW classification response contains a missing value"
        )
    if not result["level"].eq("L1").all() or not result["src"].eq("SW2021").all():
        raise RichDataError("Tushare SW classification response is not SW2021 L1")
    if not result["index_code"].str.fullmatch(r"\d{6}\.SI").all():
        raise RichDataError("Tushare SW classification contains an invalid index code")
    if result["index_code"].duplicated().any():
        raise RichDataError("Tushare SW classification contains duplicate L1 codes")
    return result.sort_values("index_code", kind="stable").reset_index(drop=True)


def canonicalize_tushare_sw_members(
    frame: pd.DataFrame,
    *,
    expected_l1_code: str,
    expected_is_new: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one frozen SW2021 membership partition without price data."""

    if expected_is_new not in {"Y", "N"}:
        raise RichDataError(
            f"unsupported expected SW membership is_new: {expected_is_new}"
        )
    if frame is None or frame.empty:
        return pd.DataFrame(columns=TUSHARE_SW_MEMBERSHIP_COLUMNS), {
            "input_rows": 0,
            "rows_written": 0,
            "missing_out_date_rows": 0,
            "unsupported_provider_symbol_rows_excluded": 0,
        }
    raw = frame.copy()
    missing = [field for field in TUSHARE_SW_MEMBERSHIP_RAW_FIELDS if field not in raw]
    if missing:
        raise RichDataError(
            "Tushare SW membership response lacks requested fields: "
            + ", ".join(missing)
        )
    unexpected = sorted(set(raw.columns) - set(TUSHARE_SW_MEMBERSHIP_RAW_FIELDS))
    if unexpected:
        raise RichDataError(
            "Tushare SW membership response contains fields outside the frozen whitelist: "
            + ", ".join(unexpected)
        )

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        source_code = str(value).strip()
        parts = source_code.split(".", 1)
        code = parts[0].strip()
        suffix = parts[1].upper() if len(parts) == 2 else ""
        if len(code) != 6 or not code.isdigit():
            return None
        if suffix not in {"SH", "SZ", "BJ"}:
            return None
        return f"{suffix}{code}"

    source_ts_code = raw["ts_code"].astype("string").str.strip()
    if source_ts_code.isna().any() or source_ts_code.eq("").any():
        raise RichDataError("Tushare SW membership response contains a missing ts_code")
    normalized = pd.DataFrame(
        {
            "l1_code": raw["l1_code"].astype("string").str.strip(),
            "l1_name": raw["l1_name"].astype("string").str.strip(),
            "l2_code": raw["l2_code"].astype("string").str.strip(),
            "l2_name": raw["l2_name"].astype("string").str.strip(),
            "l3_code": raw["l3_code"].astype("string").str.strip(),
            "l3_name": raw["l3_name"].astype("string").str.strip(),
            "instrument": source_ts_code.map(instrument),
            "in_date": pd.to_datetime(
                raw["in_date"].astype("string"), format="%Y%m%d", errors="coerce"
            ).dt.normalize(),
            "out_date": pd.to_datetime(
                raw["out_date"].astype("string"), format="%Y%m%d", errors="coerce"
            ).dt.normalize(),
            "is_new": raw["is_new"].astype("string").str.strip().str.upper(),
        }
    )
    required = [
        "l1_code",
        "l1_name",
        "l2_code",
        "l2_name",
        "l3_code",
        "l3_name",
        "in_date",
        "is_new",
    ]
    if normalized[required].isna().any(axis=None):
        raise RichDataError("Tushare SW membership response contains a missing key")
    if not normalized["l1_code"].eq(expected_l1_code).all():
        raise RichDataError("Tushare SW membership response contains another L1 code")
    if not normalized["is_new"].eq(expected_is_new).all():
        raise RichDataError(
            "Tushare SW membership response contains another is_new value"
        )
    if (
        not normalized["l2_code"].str.fullmatch(r"\d{6}\.SI").all()
        or not normalized["l3_code"].str.fullmatch(r"\d{6}\.SI").all()
    ):
        raise RichDataError(
            "Tushare SW membership response contains an invalid industry code"
        )
    missing_out = normalized["out_date"].isna()
    if expected_is_new == "Y" and not missing_out.all():
        raise RichDataError(
            "current Tushare SW membership row unexpectedly has out_date"
        )
    if expected_is_new == "N" and missing_out.any():
        raise RichDataError("historical Tushare SW membership row lacks out_date")
    dated = normalized["out_date"].notna()
    if (normalized.loc[dated, "in_date"] > normalized.loc[dated, "out_date"]).any():
        raise RichDataError("Tushare SW membership interval starts after it ends")
    unsupported_symbols = normalized["instrument"].isna()
    unsupported_symbol_rows = int(unsupported_symbols.sum())
    normalized = normalized.loc[~unsupported_symbols].copy()
    duplicate_key = [
        "l1_code",
        "l2_code",
        "l3_code",
        "instrument",
        "in_date",
        "out_date",
        "is_new",
    ]
    if normalized.duplicated(duplicate_key).any():
        raise RichDataError(
            "Tushare SW membership response contains duplicate intervals"
        )
    normalized["provider"] = "tushare"
    result = (
        normalized.loc[:, list(TUSHARE_SW_MEMBERSHIP_COLUMNS)]
        .sort_values(
            ["l1_code", "l2_code", "l3_code", "instrument", "in_date", "is_new"],
            kind="stable",
        )
        .reset_index(drop=True)
    )
    return result, {
        "input_rows": int(len(raw)),
        "rows_written": int(len(result)),
        "missing_out_date_rows": int(missing_out.sum()),
        "unsupported_provider_symbol_rows_excluded": unsupported_symbol_rows,
    }


def canonicalize_jqdata_moneyflow(
    frame: pd.DataFrame,
    codes: list[str],
    start: dt.date,
    end: dt.date,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Normalize licensed classified flows and derive the frozen ratio locally."""

    empty_stats = {
        "input_rows": 0,
        "missing_rows_excluded": 0,
        "zero_denominator_rows_excluded": 0,
        "rows_written": 0,
    }
    if frame is None or frame.empty:
        return pd.DataFrame(columns=JQDATA_MONEYFLOW_COLUMNS), empty_stats
    raw = frame.copy()
    if not isinstance(raw.index, pd.RangeIndex):
        raw = raw.reset_index()
    date_column = _column(raw, ("time", "date", "trade_date"))
    code_column = _column(raw, ("code", "sec_code", "security"))
    if date_column is None or code_column is None:
        raise RichDataError("JQData moneyflow response lacks a time or code key")
    raw_columns: dict[str, str] = {}
    for field in JQDATA_MONEYFLOW_RAW_FIELDS:
        column = _column(raw, (field,))
        if column is None:
            raise RichDataError(
                f"JQData moneyflow response lacks requested field: {field}"
            )
        raw_columns[field] = column

    def instrument(value: Any) -> str | None:
        code = str(value).split(".", 1)[0].strip()
        try:
            return qlib_symbol(code)
        except RichDataError:
            return None

    normalized = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(
                raw[date_column], errors="coerce"
            ).dt.normalize(),
            "instrument": raw[code_column].map(instrument),
            **{
                f"{field}_amount": pd.to_numeric(raw[column], errors="coerce")
                for field, column in raw_columns.items()
            },
        }
    )
    amount_columns = [f"{field}_amount" for field in JQDATA_MONEYFLOW_RAW_FIELDS]
    complete = (
        normalized[["trade_date", "instrument", *amount_columns]].notna().all(axis=1)
    )
    missing_rows = int((~complete).sum())
    valid = normalized.loc[complete].copy()
    if valid[amount_columns].lt(0.0).any().any():
        raise RichDataError(
            "JQData moneyflow response contains a negative raw flow amount"
        )
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if not valid["trade_date"].between(start_ts, end_ts).all():
        raise RichDataError(
            "JQData moneyflow response contains a date outside the request"
        )
    requested_instruments = {qlib_symbol(code) for code in codes}
    if not set(valid["instrument"]).issubset(requested_instruments):
        raise RichDataError(
            "JQData moneyflow response contains an unrequested instrument"
        )
    if valid.duplicated(["instrument", "trade_date"]).any():
        raise RichDataError(
            "JQData moneyflow response contains duplicate instrument/date keys"
        )
    valid[amount_columns] = valid[amount_columns].astype("float64")
    denominator = valid[amount_columns].sum(axis=1)
    positive = denominator.gt(0.0)
    zero_denominator_rows = int((~positive).sum())
    valid = valid.loc[positive].copy()
    denominator = denominator.loc[positive]
    valid["jqdata_large_order_net_inflow_share"] = (
        valid["inflow_xl_amount"]
        + valid["inflow_l_amount"]
        - valid["outflow_xl_amount"]
        - valid["outflow_l_amount"]
    ) / denominator
    valid["provider"] = "jqdata"
    result = (
        valid.loc[:, list(JQDATA_MONEYFLOW_COLUMNS)]
        .sort_values(["trade_date", "instrument"], kind="stable")
        .reset_index(drop=True)
    )
    if not result["jqdata_large_order_net_inflow_share"].between(-1.0, 1.0).all():
        raise RichDataError("derived JQData large-order ratio falls outside [-1, 1]")
    return result, {
        "input_rows": int(len(raw)),
        "missing_rows_excluded": missing_rows,
        "zero_denominator_rows_excluded": zero_denominator_rows,
        "rows_written": int(len(result)),
    }


def validate_range(
    start: dt.date, end: dt.date, allow_large: bool, unit_count: int = 1
) -> None:
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


def load_jqdata_moneyflow_contract(
    path: Path = DEFAULT_JQDATA_MONEYFLOW_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-entitlement daily moneyflow contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != JQDATA_MONEYFLOW_CONTRACT_SHA256:
        raise RichDataError("JQData moneyflow contract fingerprint mismatch")
    contract = load_json_record(path, kind="a_share_jqdata_moneyflow_data_contract")
    source = contract.get("source") or {}
    factor = contract.get("factor") or {}
    snapshot = contract.get("snapshot_contract") or {}
    partition = snapshot.get("partition_policy") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    coverage = contract.get("coverage_and_capacity_policy") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_jqdata_moneyflow_entitlement_or_rows_observed"
        or contract.get("preregistered_at") != "2026-07-14T20:20:32Z"
        or source.get("provider") != "jqdata"
        or source.get("api") != "get_money_flow_pro"
        or source.get("frequency") != "daily"
        or source.get("data_type") != "money"
        or tuple(source.get("requested_fields") or ()) != JQDATA_MONEYFLOW_RAW_FIELDS
        or tuple(snapshot.get("columns") or ()) != JQDATA_MONEYFLOW_COLUMNS
        or partition.get("partition") != "one calendar year"
        or partition.get("provider_documented_maximum_rows_per_call") != 2000000
        or factor.get("name") != "jqdata_large_order_net_inflow_share"
        or factor.get("direction") != "higher_is_better"
        or acceptance.get("symbols") != ["600519", "000001", "300750", "688981"]
        or coverage.get("minimum_required_cohorts") != 200
        or coverage.get("minimum_observed_years") != 5
        or coverage.get("holding_period_trading_days") != 3
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "JQData moneyflow contract does not match the frozen protocol"
        )
    return contract


def load_tushare_moneyflow_contract(
    path: Path = DEFAULT_TUSHARE_MONEYFLOW_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable post-acceptance, pre-history Tushare contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_MONEYFLOW_CONTRACT_SHA256:
        raise RichDataError("Tushare moneyflow contract fingerprint mismatch")
    contract = load_json_record(path, kind="a_share_tushare_moneyflow_data_contract")
    source = contract.get("source") or {}
    factor = contract.get("factor") or {}
    snapshot = contract.get("snapshot_contract") or {}
    partition = snapshot.get("partition_policy") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    coverage = contract.get("coverage_and_capacity_policy") or {}
    mechanism = contract.get("mechanism_identity") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_after_entitlement_acceptance_before_full_history_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T08:38:42Z"
        or source.get("provider") != "tushare"
        or source.get("api") != "moneyflow"
        or source.get("frequency") != "daily"
        or tuple(source.get("requested_fields") or ()) != TUSHARE_MONEYFLOW_RAW_FIELDS
        or tuple(snapshot.get("columns") or ()) != TUSHARE_MONEYFLOW_COLUMNS
        or partition.get("partition") != "one calendar year"
        or partition.get("provider_call_partition") != "one local trading session"
        or partition.get("provider_documented_maximum_rows_per_call") != 6000
        or partition.get("minimum_seconds_between_calls") != 0.32
        or partition.get("maximum_attempts_per_session") != 3
        or factor.get("name") != "tushare_large_order_net_inflow_share"
        or factor.get("direction") != "higher_is_better"
        or acceptance.get("status") != "completed_schema_and_entitlement_probe"
        or acceptance.get("bound_manifest_sha256")
        != "83c141749256a01852cf2cb0534da653e947e264a1b5ba3eb0efa2fd4b87a849"
        or mechanism.get("independent_factor_count") != 1
        or mechanism.get("jqdata_and_tushare_may_be_combined_as_independent_factors")
        is not False
        or coverage.get("minimum_required_cohorts") != 200
        or coverage.get("minimum_observed_years") != 5
        or coverage.get("holding_period_trading_days") != 3
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare moneyflow contract does not match the frozen protocol"
        )
    return contract


def load_tushare_northbound_top10_contract(
    path: Path = DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-entitlement Northbound top-ten contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_NORTHBOUND_TOP10_CONTRACT_SHA256:
        raise RichDataError("Tushare Northbound top-ten contract fingerprint mismatch")
    contract = load_json_record(
        path, kind="a_share_tushare_northbound_top10_data_contract"
    )
    source = contract.get("source") or {}
    factor = contract.get("factor") or {}
    snapshot = contract.get("snapshot_contract") or {}
    partition = snapshot.get("partition_policy") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    completeness = contract.get("source_completeness_policy") or {}
    capacity = contract.get("coverage_and_capacity_policy") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_entitlement_rows_full_history_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T09:37:55Z"
        or source.get("provider") != "tushare"
        or source.get("api") != "hsgt_top10"
        or tuple(source.get("market_types") or ())
        != TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES
        or tuple(source.get("requested_fields") or ())
        != TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS
        or tuple(snapshot.get("columns") or ()) != TUSHARE_NORTHBOUND_TOP10_COLUMNS
        or partition.get("partition") != "one calendar year"
        or partition.get("provider_call_partition")
        != "one local trading session and one market_type"
        or partition.get("minimum_seconds_between_calls") != 0.32
        or partition.get("maximum_attempts_per_market_session") != 3
        or factor.get("name") != "tushare_northbound_top10_net_buy_share"
        or factor.get("direction") != "higher_is_better"
        or factor.get("formula") != "(buy - sell) / (buy + sell)"
        or acceptance.get("fixed_completed_session") != "2026-07-13"
        or tuple(acceptance.get("markets_requested") or ())
        != TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES
        or completeness.get("minimum_nonempty_source_sessions") != 1000
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_trading_days") != 3
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare Northbound top-ten contract does not match the frozen protocol"
        )
    return contract


def load_tushare_top_inst_contract(
    path: Path = DEFAULT_TUSHARE_TOP_INST_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-entitlement institution-seat contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_TOP_INST_CONTRACT_SHA256:
        raise RichDataError("Tushare top_inst contract fingerprint mismatch")
    contract = load_json_record(path, kind="a_share_tushare_top_inst_data_contract")
    source_selection = contract.get("source_selection") or {}
    source = contract.get("source") or {}
    timing = contract.get("point_in_time_policy") or {}
    factor = contract.get("factor") or {}
    context = contract.get("local_context") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    gates = contract.get("no_return_gates") or {}
    completeness = gates.get("source_completeness") or {}
    capacity = gates.get("capacity") or {}
    uniqueness = gates.get("uniqueness") or {}
    diagnostic = contract.get("diagnostic_policy_if_all_no_return_gates_pass") or {}
    top_list_manifest = context.get("accepted_top_list_manifest") or {}
    top_list_frame = context.get("accepted_top_list_frame") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_top_inst_entitlement_rows_full_history_factor_values_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T12:50:27Z"
        or source_selection.get("minimum_permission_points") != 2000
        or source_selection.get("provider_documented_maximum_rows_per_call") != 10000
        or source.get("provider") != "tushare"
        or source.get("api") != "top_inst"
        or source.get("frequency") != "daily_after_close_event"
        or source.get("request_mode") != "one completed local trading session per call"
        or tuple(source.get("requested_fields") or ()) != TUSHARE_TOP_INST_RAW_FIELDS
        or timing.get("same_session_trade_allowed") is not False
        or timing.get("maximum_event_age_days") != 0
        or timing.get("forward_fill_allowed") is not False
        or factor.get("name") != "tushare_top_inst_net_buy_share"
        or factor.get("direction") != "higher_is_better"
        or factor.get("formula") != "(sum(buy) - sum(sell)) / (sum(buy) + sum(sell))"
        or factor.get("provider_net_buy_use")
        != "integrity reconciliation only; never use provider net_buy as the factor numerator"
        or top_list_manifest.get("sha256")
        != "83c141749256a01852cf2cb0534da653e947e264a1b5ba3eb0efa2fd4b87a849"
        or top_list_frame.get("sha256")
        != "658592ebdcc44685e15184a2f01bc77f3c9ebdac7f0147b537564b7290ae24e6"
        or top_list_frame.get("raw_rows") != 91
        or top_list_frame.get("exact_duplicate_rows_preserved") != 2
        or acceptance.get("fixed_completed_session") != "2026-07-13"
        or acceptance.get("provider_calls") != 1
        or acceptance.get("minimum_raw_institution_rows") != 1
        or acceptance.get("minimum_aggregated_stock_rows") != 1
        or snapshot.get("development_start") != "2019-01-01"
        or snapshot.get("development_end") != "2025-12-31"
        or snapshot.get("request_every_local_session") is not True
        or snapshot.get("provider_call_partition") != "one local trading session"
        or snapshot.get("minimum_seconds_between_calls") != 0.32
        or snapshot.get("maximum_attempts_per_session") != 3
        or tuple(snapshot.get("canonical_columns") or ()) != TUSHARE_TOP_INST_COLUMNS
        or completeness.get("minimum_nonempty_source_sessions") != 200
        or completeness.get("minimum_observed_source_years") != 5
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("topk") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("comparison_factor_count") != 51
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or diagnostic.get(
            "separate_immutable_preregistration_required_before_price_access"
        )
        is not True
        or diagnostic.get("holding_period_trading_days") != 3
        or diagnostic.get("topk") != 3
        or diagnostic.get("selection_or_promotion_allowed") is not False
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare top_inst contract does not match the frozen protocol"
        )
    return contract


def load_tushare_top_inst_top_list_context(
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Revalidate the accepted same-date raw top-list evidence without prices."""

    context = contract["local_context"]
    manifest_link = context["accepted_top_list_manifest"]
    frame_link = context["accepted_top_list_frame"]
    manifest_file = resolve_record_path(manifest_link["path"])
    frame_file = resolve_record_path(frame_link["path"])
    if (
        not manifest_file.exists()
        or file_digest(manifest_file) != manifest_link["sha256"]
    ):
        raise RichDataError("accepted Tushare top-list manifest fingerprint mismatch")
    manifest = load_json_record(manifest_file, kind="a_share_rich_data_snapshot")
    trade_date = contract["acceptance_protocol"]["fixed_completed_session"]
    if (
        manifest.get("dataset") != "tushare_events"
        or manifest.get("provider") != "tushare"
        or manifest.get("requested_start") != trade_date
        or manifest.get("requested_end") != trade_date
        or manifest.get("acceptance_status")
        != "pending_event_time_alignment_and_canonicalization"
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("accepted Tushare top-list manifest is incompatible")
    records = [
        item
        for item in manifest.get("files") or []
        if item.get("dataset") == "top-list"
    ]
    if len(records) != 1:
        raise RichDataError(
            "accepted Tushare event manifest must contain one top-list frame"
        )
    record = records[0]
    quality = record.get("quality") or {}
    if (
        resolve_record_path(record.get("path", "")) != frame_file
        or record.get("sha256") != frame_link["sha256"]
        or record.get("rows") != frame_link["raw_rows"]
        or quality.get("exact_duplicate_rows")
        != frame_link["exact_duplicate_rows_preserved"]
        or quality.get("missing_key_rows") != 0
        or quality.get("outside_requested_date_rows") != 0
        or quality.get("raw_rows_preserved_without_deduplication") is not True
    ):
        raise RichDataError("accepted Tushare top-list frame metadata mismatch")
    if not frame_file.exists():
        raise RichDataError("accepted Tushare top-list frame is missing")
    frame = pd.read_parquet(frame_file)
    if (
        frame_digest(frame) != frame_link["sha256"]
        or len(frame) != frame_link["raw_rows"]
    ):
        raise RichDataError(
            "accepted Tushare top-list frame content fingerprint mismatch"
        )
    required = {"trade_date", "ts_code"}
    if not required.issubset(frame.columns):
        raise RichDataError("accepted Tushare top-list frame lacks stock/date keys")
    dates = pd.to_datetime(
        frame["trade_date"].astype("string"), format="%Y%m%d", errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    if dates.isna().any() or not dates.eq(trade_date).all():
        raise RichDataError("accepted Tushare top-list frame has an incompatible date")

    def instrument(value: Any) -> str | None:
        if pd.isna(value):
            return None
        parts = str(value).strip().split(".", 1)
        if len(parts) != 2:
            return None
        code, suffix = parts[0].strip(), parts[1].strip().upper()
        if len(code) != 6 or not code.isdigit() or suffix not in {"SH", "SZ"}:
            return None
        try:
            symbol = qlib_symbol(code)
        except RichDataError:
            return None
        return symbol if symbol.startswith(suffix) else None

    instruments = frame["ts_code"].map(instrument)
    supported = instruments.dropna().astype(str)
    if supported.empty:
        raise RichDataError(
            "accepted Tushare top-list frame has no supported A-share stock keys"
        )
    return {
        "manifest_path": manifest_file,
        "manifest_sha256": manifest_link["sha256"],
        "frame_path": frame_file,
        "frame_sha256": frame_link["sha256"],
        "frame_rows": int(len(frame)),
        "exact_duplicate_rows_preserved": int(quality["exact_duplicate_rows"]),
        "unsupported_security_rows_excluded": int(instruments.isna().sum()),
        "instruments": frozenset(supported),
    }


def tushare_top_inst_acceptance_records() -> list[Path]:
    """Return prior success or rejection records that consumed the one-shot gate."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_top_inst_acceptance*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_top_inst_acceptance":
            records.append(path)
    return records


def load_tushare_top10_float_concentration_contract(
    path: Path = DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-row top-ten float concentration contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT_SHA256:
        raise RichDataError(
            "Tushare top-ten float concentration contract fingerprint mismatch"
        )
    contract = load_json_record(
        path, kind="a_share_tushare_top10_float_concentration_data_contract"
    )
    source_selection = contract.get("source_selection") or {}
    source = contract.get("source") or {}
    timing = contract.get("point_in_time_policy") or {}
    factor = contract.get("factor") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    gates = contract.get("no_return_gates") or {}
    completeness = gates.get("source_completeness") or {}
    capacity = gates.get("capacity") or {}
    uniqueness = gates.get("uniqueness") or {}
    diagnostic = contract.get("diagnostic_policy_if_all_no_return_gates_pass") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_top10_floatholders_entitlement_rows_full_history_factor_values_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T13:26:35Z"
        or source_selection.get("minimum_permission_points") != 2000
        or source_selection.get("current_account_points") != 3000
        or source.get("provider") != "tushare"
        or source.get("api") != "top10_floatholders"
        or source.get("request_mode")
        != "one stock and one frozen report-period range per call"
        or tuple(source.get("requested_fields") or ()) != TUSHARE_TOP10_FLOAT_RAW_FIELDS
        or source.get("plaintext_holder_name_may_be_logged_stored_or_committed")
        is not False
        or timing.get("conservative_availability")
        != "first local trading session strictly after ann_date"
        or timing.get("same_announcement_session_trade_allowed") is not False
        or timing.get("maximum_event_age_calendar_days") != 3
        or timing.get("forward_fill_beyond_event_age_allowed") is not False
        or factor.get("name") != "top10_float_concentration_change_pp"
        or factor.get("direction") != "higher_is_better"
        or factor.get("concentration_formula")
        != "sum(hold_float_ratio) across the exact ten-holder group"
        or factor.get("factor_formula")
        != "current first-complete top10_float_concentration_pct minus the immediately previous quarter's first-complete top10_float_concentration_pct"
        or tuple(acceptance.get("fixed_symbols") or ())
        != TUSHARE_TOP10_FLOAT_ACCEPTANCE_SYMBOLS
        or acceptance.get("fixed_report_period_start") != "20241231"
        or acceptance.get("fixed_report_period_end") != "20251231"
        or acceptance.get("latest_allowed_announcement_date") != "20260716"
        or acceptance.get("provider_calls") != 3
        or acceptance.get("minimum_complete_report_groups_per_symbol") != 2
        or acceptance.get("minimum_factor_ready_consecutive_pairs_per_symbol") != 1
        or acceptance.get("success_status")
        != "accepted_entitlement_schema_and_concentration_formula_pending_full_history"
        or snapshot.get("source_report_period_start") != "20181231"
        or snapshot.get("source_report_period_end") != "20251231"
        or snapshot.get("development_signal_start") != "2019-01-01"
        or snapshot.get("development_signal_end") != "2025-12-31"
        or snapshot.get("request_each_point_in_time_buyable_instrument_once")
        is not True
        or snapshot.get("provider_call_partition")
        != "one ts_code over the full frozen report-period range"
        or snapshot.get("minimum_seconds_between_calls") != 0.65
        or snapshot.get("maximum_attempts_per_symbol") != 3
        or tuple(snapshot.get("persisted_normalized_source_columns") or ())
        != TUSHARE_TOP10_FLOAT_SOURCE_COLUMNS
        or tuple(snapshot.get("canonical_factor_columns") or ())
        != TUSHARE_TOP10_FLOAT_FACTOR_COLUMNS
        or completeness.get("minimum_complete_factor_events") != 2000
        or completeness.get("minimum_observed_announcement_years") != 5
        or completeness.get("plaintext_holder_identity_persisted") is not False
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("topk") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("comparison_factor_count") != 54
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or diagnostic.get(
            "separate_immutable_preregistration_required_before_price_access"
        )
        is not True
        or diagnostic.get("holding_period_trading_days") != 3
        or diagnostic.get("topk") != 3
        or diagnostic.get("selection_or_promotion_allowed") is not False
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare top-ten float concentration contract does not match the "
            "frozen protocol"
        )
    return contract


def validate_tushare_top10_float_local_context(
    contract: dict[str, Any],
) -> dict[str, dict[str, str]]:
    """Fingerprint-bind every local no-return prerequisite before a provider call."""

    context = contract.get("local_context") or {}
    validated: dict[str, dict[str, str]] = {}
    for label, evidence in context.items():
        if (
            not isinstance(evidence, dict)
            or not evidence.get("path")
            or not evidence.get("sha256")
        ):
            raise RichDataError(
                f"top-ten float concentration context is incomplete: {label}"
            )
        path = resolve_record_path(str(evidence["path"]))
        expected = str(evidence["sha256"])
        if not path.exists() or file_digest(path) != expected:
            raise RichDataError(
                f"top-ten float concentration context fingerprint mismatch: {label}"
            )
        validated[label] = {
            "path": manifest_path(path),
            "sha256": expected,
        }
        manifest_value = evidence.get("manifest_path")
        manifest_sha = evidence.get("manifest_sha256")
        if manifest_value is not None or manifest_sha is not None:
            if not manifest_value or not manifest_sha:
                raise RichDataError(
                    f"top-ten float concentration manifest context is incomplete: {label}"
                )
            manifest_file = resolve_record_path(str(manifest_value))
            if not manifest_file.exists() or file_digest(manifest_file) != str(
                manifest_sha
            ):
                raise RichDataError(
                    "top-ten float concentration manifest fingerprint mismatch: "
                    f"{label}"
                )
            validated[f"{label}_manifest"] = {
                "path": manifest_path(manifest_file),
                "sha256": str(manifest_sha),
            }
    return validated


def tushare_top10_float_concentration_acceptance_records() -> list[Path]:
    """Return terminal records that have consumed this exact one-shot gate."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(
        RUNS_ROOT.glob("*tushare_top10_float_concentration_acceptance*.json")
    ):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_top10_float_concentration_acceptance":
            records.append(path)
    return records


def load_tushare_cash_conversion_contract(
    path: Path = DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT,
) -> dict[str, Any]:
    """Load and structurally revalidate the immutable pre-row accounting contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_CASH_CONVERSION_CONTRACT_SHA256:
        raise RichDataError("Tushare cash-conversion contract fingerprint mismatch")
    contract = load_json_record(
        path, kind="a_share_tushare_cash_conversion_data_contract"
    )
    selection = contract.get("source_selection") or {}
    source = contract.get("source") or {}
    version = contract.get("point_in_time_and_version_policy") or {}
    factor = contract.get("factor") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    gates = contract.get("no_return_gates") or {}
    completeness = gates.get("source_completeness") or {}
    capacity = gates.get("capacity") or {}
    uniqueness = gates.get("uniqueness") or {}
    diagnostic = contract.get("diagnostic_policy_if_all_no_return_gates_pass") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_income_or_cashflow_entitlement_rows_full_history_factor_values_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T13:43:50Z"
        or selection.get("minimum_permission_points_each") != 2000
        or selection.get("current_account_points") != 3000
        or selection.get("provider_documented_maximum_rows_per_call") != 100
        or source.get("provider") != "tushare"
        or tuple(source.get("apis") or ()) != ("income", "cashflow")
        or source.get("request_mode")
        != "one stock and one frozen announcement-date range per endpoint call"
        or tuple(source.get("income_requested_fields") or ())
        != TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS
        or tuple(source.get("cashflow_requested_fields") or ())
        != TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS
        or version.get("candidate_company_type") != "1"
        or version.get("candidate_report_type") != "1 consolidated cumulative report"
        or tuple(version.get("non_candidate_context_report_types") or ())
        != tuple(
            str(value) for value in sorted(TUSHARE_CASH_CONVERSION_CONTEXT_REPORT_TYPES)
        )
        or tuple(
            version.get(
                "adjustment_report_types_that_exclude_the_whole_endpoint_period"
            )
            or ()
        )
        != tuple(
            str(value)
            for value in sorted(TUSHARE_CASH_CONVERSION_ADJUSTMENT_REPORT_TYPES)
        )
        or version.get("conservative_availability")
        != "first local trading session strictly after the later actual announcement date"
        or version.get("same_announcement_session_trade_allowed") is not False
        or version.get("maximum_event_age_calendar_days") != 3
        or version.get("forward_fill_beyond_event_age_allowed") is not False
        or factor.get("name") != "tushare_operating_cash_conversion"
        or factor.get("direction") != "higher_is_better"
        or factor.get("formula") != "n_cashflow_act / n_income_attr_p"
        or factor.get("clipping_winsorization_log_absolute_value_or_imputation")
        is not None
        or tuple(acceptance.get("fixed_symbols") or ())
        != TUSHARE_CASH_CONVERSION_ACCEPTANCE_SYMBOLS
        or acceptance.get("fixed_announcement_start") != "20240101"
        or acceptance.get("fixed_announcement_end") != "20260630"
        or acceptance.get("latest_allowed_actual_announcement_date") != "20260716"
        or tuple(acceptance.get("endpoints_per_symbol") or ()) != ("income", "cashflow")
        or acceptance.get("provider_calls") != 6
        or acceptance.get("minimum_usable_joined_periods_per_symbol") != 4
        or acceptance.get("success_status")
        != "accepted_entitlement_schema_version_policy_and_formula_pending_full_history"
        or snapshot.get("announcement_start") != "20190101"
        or snapshot.get("announcement_end") != "20251231"
        or snapshot.get("development_signal_start") != "2019-01-01"
        or snapshot.get("development_signal_end") != "2025-12-31"
        or snapshot.get(
            "request_each_point_in_time_buyable_instrument_once_per_endpoint"
        )
        is not True
        or snapshot.get("provider_call_partition")
        != "one ts_code over the full frozen announcement-date range for each endpoint"
        or snapshot.get("provider_documented_maximum_rows_per_call") != 100
        or snapshot.get("minimum_seconds_between_calls") != 0.65
        or snapshot.get("maximum_attempts_per_symbol_endpoint") != 3
        or tuple(snapshot.get("canonical_columns") or ())
        != TUSHARE_CASH_CONVERSION_COLUMNS
        or completeness.get("minimum_complete_joined_factor_events") != 5000
        or completeness.get("minimum_observed_signal_years") != 5
        or capacity.get("minimum_eligible_names_per_cross_section") != 6
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("non_overlapping_cohorts") is not True
        or capacity.get("topk") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("maximum_quality_age_days") != 550
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("comparison_factor_count") != 54
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or diagnostic.get(
            "separate_immutable_preregistration_required_before_price_access"
        )
        is not True
        or diagnostic.get("holding_period_trading_days") != 3
        or diagnostic.get("topk") != 3
        or diagnostic.get("selection_or_promotion_allowed") is not False
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare cash-conversion contract does not match the frozen protocol"
        )
    return contract


def validate_tushare_cash_conversion_local_context(
    contract: dict[str, Any],
) -> dict[str, dict[str, str]]:
    """Fingerprint-bind every local no-return prerequisite before provider calls."""

    context = contract.get("local_context") or {}
    validated: dict[str, dict[str, str]] = {}
    for label, evidence in context.items():
        if (
            not isinstance(evidence, dict)
            or not evidence.get("path")
            or not evidence.get("sha256")
        ):
            raise RichDataError(f"cash-conversion context is incomplete: {label}")
        path = resolve_record_path(str(evidence["path"]))
        expected = str(evidence["sha256"])
        if not path.exists() or file_digest(path) != expected:
            raise RichDataError(
                f"cash-conversion context fingerprint mismatch: {label}"
            )
        validated[label] = {"path": manifest_path(path), "sha256": expected}
        manifest_value = evidence.get("manifest_path")
        manifest_sha = evidence.get("manifest_sha256")
        if manifest_value is not None or manifest_sha is not None:
            if not manifest_value or not manifest_sha:
                raise RichDataError(
                    f"cash-conversion manifest context is incomplete: {label}"
                )
            manifest_file = resolve_record_path(str(manifest_value))
            if not manifest_file.exists() or file_digest(manifest_file) != str(
                manifest_sha
            ):
                raise RichDataError(
                    f"cash-conversion manifest fingerprint mismatch: {label}"
                )
            validated[f"{label}_manifest"] = {
                "path": manifest_path(manifest_file),
                "sha256": str(manifest_sha),
            }
    return validated


def tushare_cash_conversion_acceptance_records() -> list[Path]:
    """Return terminal records that consumed the cash-conversion one-shot gate."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_cash_conversion_acceptance*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_cash_conversion_acceptance":
            records.append(path)
    return records


def load_tushare_cash_conversion_source_chain(
    record_path: Path = DEFAULT_TUSHARE_CASH_CONVERSION_ACCEPTANCE_RECORD,
) -> dict[str, Any]:
    """Revalidate the frozen contract and accepted no-return factor sample."""

    contract = load_tushare_cash_conversion_contract()
    record_path = record_path.expanduser().resolve()
    if (
        not record_path.exists()
        or file_digest(record_path) != TUSHARE_CASH_CONVERSION_ACCEPTANCE_RECORD_SHA256
    ):
        raise RichDataError(
            "Tushare cash-conversion acceptance record fingerprint mismatch"
        )
    record = load_json_record(
        record_path,
        kind="a_share_tushare_cash_conversion_source_acceptance_record",
    )
    contract_link = record.get("data_contract") or {}
    acceptance = record.get("acceptance") or {}
    next_action = record.get("one_shot_and_next_action") or {}
    manifest_file = resolve_record_path(str(acceptance.get("manifest_path") or ""))
    expected_manifest_sha = str(acceptance.get("manifest_sha256") or "")
    if (
        record.get("version") != 1
        or record.get("status")
        != "accepted_source_pending_frozen_full_history_and_no_return_gates"
        or contract_link.get("sha256") != TUSHARE_CASH_CONVERSION_CONTRACT_SHA256
        or contract_link.get("preregistered_at") != contract.get("preregistered_at")
        or acceptance.get("acceptance_status")
        != "accepted_entitlement_schema_version_policy_and_formula_pending_full_history"
        or tuple(acceptance.get("fixed_symbols") or ())
        != TUSHARE_CASH_CONVERSION_ACCEPTANCE_SYMBOLS
        or tuple(acceptance.get("endpoints_per_symbol") or ()) != ("income", "cashflow")
        or acceptance.get("provider_calls_issued") != 6
        or acceptance.get("provider_calls_expected") != 6
        or acceptance.get("total_source_rows") != 76
        or acceptance.get("formula") != "n_cashflow_act / n_income_attr_p"
        or acceptance.get("direction") != "higher_is_better"
        or acceptance.get("price_fields_loaded") != []
        or acceptance.get("forward_return_fields_read") is not False
        or acceptance.get("selection_or_promotion_performed") is not False
        or next_action.get("acceptance_consumed") is not True
        or next_action.get("price_access_authorized_now") is not False
        or next_action.get("aggregation_scoring_selection_or_trading_authorized_now")
        is not False
        or not manifest_file.exists()
        or file_digest(manifest_file) != expected_manifest_sha
    ):
        raise RichDataError("Tushare cash-conversion acceptance record is incompatible")
    manifest = load_json_record(manifest_file, kind="a_share_rich_data_snapshot")
    files = list(manifest.get("files") or [])
    published = acceptance.get("published_factor_frame") or {}
    if (
        manifest.get("dataset") != "tushare_cash_conversion_acceptance"
        or manifest.get("provider") != "tushare"
        or manifest.get("acceptance_status") != acceptance.get("acceptance_status")
        or manifest.get("price_fields_loaded") != []
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
        or len(files) != 1
        or files[0].get("path") != published.get("path")
        or files[0].get("sha256") != published.get("sha256")
        or files[0].get("rows") != published.get("rows")
    ):
        raise RichDataError(
            "Tushare cash-conversion acceptance manifest identity mismatch"
        )
    frame_path = resolve_record_path(str(published.get("path") or ""))
    if not frame_path.exists():
        raise RichDataError("Tushare cash-conversion accepted factor frame is missing")
    frame = pd.read_parquet(frame_path)
    denominator = pd.to_numeric(frame["n_income_attr_p"], errors="coerce")
    numerator = pd.to_numeric(frame["n_cashflow_act"], errors="coerce")
    factor = pd.to_numeric(frame["tushare_operating_cash_conversion"], errors="coerce")
    later_actual = frame[
        ["income_actual_announcement_date", "cashflow_actual_announcement_date"]
    ].max(axis=1)
    expected_instruments = {
        qlib_symbol(symbol.split(".", 1)[0])
        for symbol in TUSHARE_CASH_CONVERSION_ACCEPTANCE_SYMBOLS
    }
    if (
        tuple(frame.columns) != TUSHARE_CASH_CONVERSION_COLUMNS
        or len(frame) != int(published.get("rows") or -1)
        or frame_digest(frame) != published.get("sha256")
        or set(frame["instrument"].astype(str)) != expected_instruments
        or frame.duplicated(["instrument", "announcement_date", "report_period"]).any()
        or frame["announcement_date"].isna().any()
        or not pd.to_datetime(frame["announcement_date"]).eq(later_actual).all()
        or not np.isfinite(denominator).all()
        or not denominator.gt(0.0).all()
        or not np.isfinite(numerator).all()
        or not np.isfinite(factor).all()
        or not np.allclose(
            factor.to_numpy(dtype="float64"),
            numerator.to_numpy(dtype="float64") / denominator.to_numpy(dtype="float64"),
            rtol=0.0,
            atol=1e-12,
        )
        or not frame["provider"].eq("tushare").all()
    ):
        raise RichDataError(
            "Tushare cash-conversion accepted factor integrity audit failed"
        )
    return {
        "contract": contract,
        "record_path": record_path,
        "record": record,
        "manifest_path": manifest_file,
        "manifest": manifest,
        "frame_path": frame_path,
        "frame": frame,
    }


def tushare_cash_conversion_full_snapshot_records() -> list[Path]:
    """Return completed full-snapshot manifests for this exact mechanism."""

    if not RUNS_ROOT.exists():
        return []
    records: list[Path] = []
    for path in sorted(RUNS_ROOT.glob("*tushare_cash_conversion_full*.json")):
        payload = load_json_record(path)
        if payload.get("dataset") == "tushare_operating_cash_conversion":
            records.append(path)
    return records


def load_tushare_daily_pb_contract(
    path: Path = DEFAULT_TUSHARE_DAILY_PB_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-entitlement daily PB contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_DAILY_PB_CONTRACT_SHA256:
        raise RichDataError("Tushare daily PB contract fingerprint mismatch")
    contract = load_json_record(path, kind="a_share_tushare_daily_pb_data_contract")
    source = contract.get("source") or {}
    factor = contract.get("factor") or {}
    snapshot = contract.get("snapshot_contract") or {}
    partition = snapshot.get("partition_policy") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    completeness = contract.get("source_completeness_policy") or {}
    uniqueness = contract.get("no_return_uniqueness_policy") or {}
    capacity = contract.get("coverage_and_capacity_policy") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_entitlement_rows_full_history_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T09:48:42Z"
        or source.get("provider") != "tushare"
        or source.get("api") != "daily_basic"
        or tuple(source.get("requested_fields") or ()) != TUSHARE_DAILY_PB_RAW_FIELDS
        or tuple(snapshot.get("columns") or ()) != TUSHARE_DAILY_PB_COLUMNS
        or partition.get("partition") != "one calendar year"
        or partition.get("provider_call_partition") != "one local trading session"
        or partition.get("provider_documented_maximum_rows_per_call") != 6000
        or partition.get("minimum_seconds_between_calls") != 0.32
        or partition.get("maximum_attempts_per_session") != 3
        or factor.get("name") != "tushare_positive_book_to_market"
        or factor.get("direction") != "higher_is_better"
        or factor.get("formula") != "1 / pb"
        or acceptance.get("fixed_completed_session") != "2026-07-13"
        or acceptance.get("minimum_all_market_source_rows") != 4000
        or completeness.get("minimum_sessions_with_fifty_positive_pb_names") != 200
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_eligible_names_per_cross_section") != 50
        or capacity.get("minimum_observed_years") != 5
        or capacity.get("holding_period_trading_days") != 3
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare daily PB contract does not match the frozen protocol"
        )
    return contract


def load_tushare_sw_industry_breadth_contract(
    path: Path = DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT,
) -> dict[str, Any]:
    """Load the immutable pre-row SW2021 industry-breadth contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT_SHA256:
        raise RichDataError("Tushare SW industry-breadth contract fingerprint mismatch")
    contract = load_json_record(
        path, kind="a_share_tushare_sw_industry_breadth_data_contract"
    )
    source = contract.get("source") or {}
    membership = contract.get("point_in_time_membership_policy") or {}
    factor = contract.get("factor") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    snapshot = contract.get("full_snapshot_contract") or {}
    gates = contract.get("no_return_gates") or {}
    diagnostic = contract.get("diagnostic_policy_if_all_no_return_gates_pass") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_before_index_member_rows_factor_values_or_factor_returns_observed"
        or contract.get("preregistered_at") != "2026-07-16T11:22:05Z"
        or source.get("provider") != "tushare"
        or source.get("classification_api") != "index_classify"
        or source.get("classification_parameters") != {"level": "L1", "src": "SW2021"}
        or tuple(source.get("classification_requested_fields") or ())
        != TUSHARE_SW_CLASSIFICATION_RAW_FIELDS
        or source.get("membership_api") != "index_member_all"
        or tuple(source.get("membership_requested_fields") or ())
        != TUSHARE_SW_MEMBERSHIP_RAW_FIELDS
        or tuple(source.get("membership_is_new_values") or ()) != ("Y", "N")
        or membership.get("classification_version") != "SW2021"
        or membership.get("industry_level") != "L1 only"
        or membership.get("maximum_active_level_one_memberships_per_stock_session") != 1
        or factor.get("name") != "sw1_three_session_leave_one_out_breadth"
        or factor.get("direction") != "higher_is_better"
        or factor.get("minimum_other_valid_peers_each_session") != 10
        or factor.get("peer_minimum_listing_sessions") != 20
        or factor.get("stock_self_direction_included") is not False
        or acceptance.get("representative_l1_code") != "801010.SI"
        or acceptance.get("minimum_classification_rows") != 25
        or acceptance.get("maximum_classification_rows") != 40
        or acceptance.get("minimum_current_representative_members") != 20
        or acceptance.get("minimum_historical_representative_members") != 1
        or tuple(snapshot.get("canonical_columns") or ())
        != TUSHARE_SW_MEMBERSHIP_COLUMNS
        or ((gates.get("capacity") or {}).get("minimum_required_cohorts")) != 200
        or ((gates.get("capacity") or {}).get("holding_period_trading_days")) != 3
        or ((gates.get("uniqueness") or {}).get("comparison_factor_count")) != 45
        or (
            (gates.get("uniqueness") or {}).get(
                "maximum_allowed_absolute_median_daily_rank_correlation"
            )
        )
        != 0.8
        or diagnostic.get("holding_period_trading_days") != 3
        or diagnostic.get("topk") != 3
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare SW industry-breadth contract does not match the frozen protocol"
        )
    return contract


def load_tushare_sw_industry_breadth_symbol_repair(
    path: Path = DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_SYMBOL_REPAIR,
) -> dict[str, Any]:
    """Verify the no-price symbol-normalization repair for the exact retry."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_SW_INDUSTRY_BREADTH_SYMBOL_REPAIR_SHA256:
        raise RichDataError("Tushare SW symbol-repair fingerprint mismatch")
    repair = load_json_record(
        path,
        kind="a_share_tushare_sw_industry_breadth_symbol_normalization_repair",
    )
    contract = repair.get("bound_contract") or {}
    preregistration = repair.get("bound_preregistration") or {}
    failed = repair.get("failed_attempt") or {}
    diagnosis = repair.get("targeted_no_price_diagnosis") or {}
    rule = repair.get("repair") or {}
    retry = repair.get("retry_authorization") or {}
    failure_path = resolve_record_path(str(failed.get("record_path") or ""))
    if not failure_path.exists() or file_digest(failure_path) != failed.get(
        "record_sha256"
    ):
        raise RichDataError("Tushare SW symbol-repair failure evidence mismatch")
    failure = load_json_record(failure_path, kind="a_share_rich_data_source_failure")
    if (
        repair.get("version") != 1
        or repair.get("status")
        != "frozen_after_first_full_snapshot_infrastructure_failure_before_exact_retry_factor_values_or_factor_returns"
        or repair.get("recorded_at") != "2026-07-16T11:44:07Z"
        or contract.get("sha256") != TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT_SHA256
        or preregistration.get("sha256")
        != TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC_SHA256
        or failure.get("dataset") != "tushare_sw2021_l1_membership"
        or failure.get("failed_l1_code") != failed.get("failed_l1_code")
        or failure.get("failed_is_new") != failed.get("failed_is_new")
        or failure.get("completed_provider_calls_before_failure")
        != failed.get("completed_provider_calls_before_failure")
        or failure.get("partial_snapshot_deleted") is not True
        or failure.get("final_snapshot_published") is not False
        or failure.get("forward_return_fields_read") is not False
        or diagnosis.get("provider_calls_after_failure") != 2
        or diagnosis.get("request_identity_unchanged") is not True
        or diagnosis.get("l1_code") != "801170.SI"
        or diagnosis.get("is_new") != "Y"
        or diagnosis.get("rows_each_call") != 144
        or diagnosis.get("unsupported_provider_symbol_rows") != 1
        or diagnosis.get("unsupported_provider_symbol_examples") != ["T00018.SH"]
        or diagnosis.get("price_fields_loaded") != []
        or diagnosis.get("factor_values_constructed") is not False
        or diagnosis.get("forward_return_fields_read") is not False
        or rule.get("unsupported_non_six_digit_provider_symbol_policy")
        != "exclude the row from the canonical membership frame and count it explicitly"
        or rule.get("interval_dates_changed") is not False
        or rule.get("classification_codes_changed") is not False
        or rule.get("is_new_states_changed") is not False
        or rule.get("provider_fields_changed") is not False
        or rule.get("provider_call_count_changed") is not False
        or rule.get("factor_formula_direction_window_or_peer_threshold_changed")
        is not False
        or retry.get("exact_full_snapshot_retry_allowed") is not True
        or retry.get("retry_must_restart_all_62_calls") is not True
        or retry.get("partial_resume_allowed") is not False
        or retry.get("maximum_accepted_full_snapshot_retries_under_this_repair") != 1
        or retry.get("factor_or_return_access_allowed_by_this_record") is not False
        or repair.get("forward_return_fields_read") is not False
        or repair.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("Tushare SW symbol-repair record is inconsistent")
    return repair


def load_tushare_sw_industry_breadth_source_chain(
    path: Path = DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC,
) -> dict[str, Any]:
    """Verify the accepted SW2021 source before the 62-call full snapshot."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC_SHA256:
        raise RichDataError(
            "Tushare SW industry-breadth capacity preregistration fingerprint mismatch"
        )
    spec = load_json_record(
        path, kind="a_share_tushare_sw_industry_breadth_capacity_preregistration"
    )
    contract_link = spec.get("data_contract") or {}
    acceptance = spec.get("source_acceptance") or {}
    snapshot = spec.get("full_membership_snapshot") or {}
    context = spec.get("point_in_time_context") or {}
    factor = spec.get("factor_contract") or {}
    audit = spec.get("combined_no_return_audit") or {}
    capacity = audit.get("capacity") or {}
    uniqueness = audit.get("uniqueness") or {}
    evidence = spec.get("freeze_evidence") or {}
    contract = load_tushare_sw_industry_breadth_contract(
        resolve_record_path(str(contract_link.get("path") or ""))
    )
    classification_codes = tuple(snapshot.get("classification_codes") or ())
    if (
        spec.get("version") != 1
        or spec.get("status")
        != "frozen_after_source_acceptance_before_full_membership_factor_values_or_factor_returns_observed"
        or spec.get("preregistered_at") != "2026-07-16T11:29:22Z"
        or evidence
        != {
            "source_acceptance_observed": True,
            "full_membership_snapshot_observed": False,
            "factor_values_observed": False,
            "close_known_comparison_values_observed_for_this_factor": False,
            "factor_returns_observed": False,
            "selection_or_promotion_performed": False,
        }
        or contract_link.get("sha256") != TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT_SHA256
        or contract_link.get("preregistered_at") != contract.get("preregistered_at")
        or snapshot.get("dataset") != "tushare_sw2021_l1_membership"
        or snapshot.get("provider") != "tushare"
        or snapshot.get("membership_api") != "index_member_all"
        or tuple(snapshot.get("requested_fields") or ())
        != TUSHARE_SW_MEMBERSHIP_RAW_FIELDS
        or len(classification_codes) != 31
        or len(set(classification_codes)) != 31
        or tuple(sorted(classification_codes)) != classification_codes
        or tuple(snapshot.get("is_new_values") or ()) != ("Y", "N")
        or snapshot.get("expected_provider_calls") != 62
        or snapshot.get("provider_documented_maximum_rows_per_call") != 2000
        or snapshot.get("minimum_seconds_between_calls") != 0.32
        or snapshot.get("maximum_attempts_per_call") != 3
        or tuple(snapshot.get("retry_backoff_seconds") or ()) != (2, 5)
        or snapshot.get("requests_are_sequential") is not True
        or snapshot.get("partial_snapshot_accepted") is not False
        or snapshot.get("hidden_temporary_root_required") is not True
        or tuple(snapshot.get("canonical_columns") or ())
        != TUSHARE_SW_MEMBERSHIP_COLUMNS
        or snapshot.get("required_success_status")
        != "full_membership_snapshot_passed_pending_no_return_factor_capacity_and_uniqueness"
        or factor.get("factor_catalog") != ["sw1_three_session_leave_one_out_breadth"]
        or factor.get("direction") != "higher_is_better"
        or factor.get("minimum_other_valid_peers_each_session") != 10
        or factor.get("peer_minimum_listing_sessions") != 20
        or factor.get("stock_self_direction_included") is not False
        or factor.get("holding_universe") != "buyable_main_chinext"
        or factor.get("maximum_quality_age_days") != 550
        or factor.get("candidate_minimum_listing_sessions") != 20
        or capacity.get("development_start") != "2019-01-01"
        or capacity.get("development_end") != "2025-12-31"
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_eligible_names_per_cross_section") != 50
        or capacity.get("minimum_distinct_factor_values") != 2
        or capacity.get("minimum_observed_years") != 5
        or uniqueness.get("screen_start") != "2025-01-01"
        or uniqueness.get("screen_end") != "2025-12-31"
        or len(uniqueness.get("comparison_factors") or []) != 45
        or uniqueness.get("minimum_pairwise_sessions") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or audit.get("forward_return_fields_read") is not False
        or audit.get("selection_or_promotion_allowed") is not False
        or spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "Tushare SW industry-breadth capacity preregistration is inconsistent"
        )

    context_paths: dict[str, Path] = {}
    for key in ("source_universe", "holding_universe", "local_calendar"):
        link = context.get(key) or {}
        source_path = resolve_record_path(str(link.get("path") or ""))
        if (
            not source_path.exists()
            or not link.get("file_sha256")
            or file_digest(source_path) != link.get("file_sha256")
        ):
            raise RichDataError(f"Tushare SW point-in-time {key} fingerprint mismatch")
        context_paths[key] = source_path
    quality = context.get("quarterly_quality") or {}
    for key, path_key, sha_key in (
        ("quarterly_quality", "path", "sha256"),
        ("quarterly_quality_manifest", "manifest_path", "manifest_sha256"),
    ):
        source_path = resolve_record_path(str(quality.get(path_key) or ""))
        if (
            not source_path.exists()
            or not quality.get(sha_key)
            or file_digest(source_path) != quality.get(sha_key)
        ):
            raise RichDataError(f"Tushare SW {key} fingerprint mismatch")
        context_paths[key] = source_path
    price_link = context.get("accepted_price_basis") or {}
    price_path = resolve_record_path(str(price_link.get("path") or ""))
    if not price_path.exists() or file_digest(price_path) != price_link.get("sha256"):
        raise RichDataError("Tushare SW accepted price-basis fingerprint mismatch")
    price_basis = load_json_record(price_path)
    if (
        price_basis.get("status") != price_link.get("status")
        or price_basis.get("price_basis") != price_link.get("price_basis")
        or price_basis.get("daily_sources") != price_link.get("daily_sources")
        or price_basis.get("future_corporate_actions_used")
        is not price_link.get("future_corporate_actions_used")
    ):
        raise RichDataError("Tushare SW accepted price-basis identity mismatch")
    context_paths["accepted_price_basis"] = price_path

    record_path = resolve_record_path(str(acceptance.get("record_path") or ""))
    manifest_path_value = resolve_record_path(
        str(acceptance.get("manifest_path") or "")
    )
    if (
        not record_path.exists()
        or file_digest(record_path) != acceptance.get("record_sha256")
        or not manifest_path_value.exists()
        or file_digest(manifest_path_value) != acceptance.get("manifest_sha256")
    ):
        raise RichDataError("Tushare SW source-acceptance fingerprint mismatch")
    record = load_json_record(
        record_path,
        kind="a_share_tushare_sw_industry_breadth_source_acceptance_record",
    )
    manifest = load_json_record(manifest_path_value, kind="a_share_rich_data_snapshot")
    files = {str(item.get("dataset")): item for item in manifest.get("files") or []}
    stored_frames = record.get("stored_frames") or {}
    source_quality = manifest.get("source_quality") or {}
    if (
        record.get("status")
        != "accepted_entitlement_schema_and_point_in_time_intervals_pending_full_membership_snapshot"
        or (record.get("data_contract") or {}).get("sha256")
        != TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT_SHA256
        or (record.get("acceptance_manifest") or {}).get("sha256")
        != acceptance.get("manifest_sha256")
        or (
            (record.get("decision") or {}).get(
                "source_accepted_for_frozen_full_membership_snapshot"
            )
        )
        is not True
        or (
            (record.get("decision") or {}).get(
                "source_accepted_for_factor_construction_or_returns"
            )
        )
        is not False
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
        or manifest.get("dataset") != "tushare_sw2021_l1_acceptance"
        or manifest.get("provider") != "tushare"
        or manifest.get("run_id") != acceptance.get("run_id")
        or manifest.get("acceptance_status")
        != "accepted_entitlement_schema_and_point_in_time_intervals_pending_full_membership_snapshot"
        or (manifest.get("data_contract") or {}).get("sha256")
        != TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT_SHA256
        or (manifest.get("source_request") or {}).get("classification_fields")
        != list(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS)
        or (manifest.get("source_request") or {}).get("membership_fields")
        != list(TUSHARE_SW_MEMBERSHIP_RAW_FIELDS)
        or (manifest.get("source_request") or {}).get(
            "forbidden_fields_requested_or_stored"
        )
        != []
        or (manifest.get("source_request") or {}).get("credentials_logged_or_stored")
        is not False
        or manifest.get("price_fields_loaded") != []
        or manifest.get("factor_values_constructed") is not False
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
        or set(files) != {"classification", "membership"}
    ):
        raise RichDataError("Tushare SW source-acceptance identity mismatch")
    for key in ("classification", "membership"):
        record_frame = stored_frames.get(key) or {}
        manifest_frame = files[key]
        if (
            record_frame.get("path") != manifest_frame.get("path")
            or record_frame.get("sha256") != manifest_frame.get("sha256")
            or int(record_frame.get("rows") or -1)
            != int(manifest_frame.get("rows") or -2)
        ):
            raise RichDataError(f"Tushare SW accepted {key} frame identity mismatch")
    classification = load_snapshot_frame(files["classification"])
    membership = load_snapshot_frame(files["membership"])
    representative_l1 = str(contract["acceptance_protocol"]["representative_l1_code"])
    duplicate_key = list(contract["full_snapshot_contract"]["duplicate_event_key"])
    if (
        tuple(classification.columns) != TUSHARE_SW_CLASSIFICATION_RAW_FIELDS
        or len(classification) != int(acceptance.get("classification_rows") or -1)
        or tuple(classification["index_code"].astype(str)) != classification_codes
        or not classification["level"].eq("L1").all()
        or not classification["src"].eq("SW2021").all()
        or tuple(membership.columns) != TUSHARE_SW_MEMBERSHIP_COLUMNS
        or len(membership) != int(acceptance.get("membership_rows") or -1)
        or int(membership["is_new"].eq("Y").sum())
        != int(acceptance.get("current_membership_rows") or -1)
        or int(membership["is_new"].eq("N").sum())
        != int(acceptance.get("historical_membership_rows") or -1)
        or not membership["l1_code"].eq(representative_l1).all()
        or not membership["provider"].eq("tushare").all()
        or membership.duplicated(duplicate_key).any()
        or membership.loc[membership["is_new"].eq("Y"), "out_date"].notna().any()
        or membership.loc[membership["is_new"].eq("N"), "out_date"].isna().any()
        or source_quality.get("classification_codes") != list(classification_codes)
    ):
        raise RichDataError("Tushare SW accepted frame integrity audit failed")
    symbol_repair_path = DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_SYMBOL_REPAIR.resolve()
    symbol_repair = load_tushare_sw_industry_breadth_symbol_repair(symbol_repair_path)
    return {
        "spec_path": path,
        "spec": spec,
        "contract": contract,
        "record_path": record_path,
        "record": record,
        "manifest_path": manifest_path_value,
        "manifest": manifest,
        "classification": classification,
        "membership": membership,
        "context_paths": context_paths,
        "symbol_repair_path": symbol_repair_path,
        "symbol_repair": symbol_repair,
    }


def load_tushare_daily_pb_source_chain(
    path: Path = DEFAULT_TUSHARE_DAILY_PB_CAPACITY_SPEC,
) -> dict[str, Any]:
    """Verify the post-acceptance, pre-history PB evidence chain."""

    path = path.expanduser().resolve()
    if file_digest(path) != TUSHARE_DAILY_PB_CAPACITY_SPEC_SHA256:
        raise RichDataError(
            "Tushare daily PB capacity preregistration fingerprint mismatch"
        )
    spec = load_json_record(
        path, kind="a_share_tushare_daily_pb_capacity_preregistration"
    )
    contract_link = spec.get("data_contract") or {}
    acceptance = spec.get("source_acceptance") or {}
    required = spec.get("required_full_snapshot") or {}
    capacity = spec.get("capacity_contract") or {}
    uniqueness = spec.get("uniqueness_contract") or {}
    policy = spec.get("no_return_gate_policy") or {}
    contract = load_tushare_daily_pb_contract(
        resolve_record_path(str(contract_link.get("path") or ""))
    )
    if (
        spec.get("version") != 1
        or spec.get("status")
        != "frozen_after_single_session_acceptance_before_full_history_uniqueness_capacity_or_factor_returns_observed"
        or spec.get("preregistered_at") != "2026-07-16T10:05:41Z"
        or contract_link.get("sha256") != TUSHARE_DAILY_PB_CONTRACT_SHA256
        or contract_link.get("preregistered_at") != contract.get("preregistered_at")
        or tuple(spec.get("factor_catalog") or ())
        != ("tushare_positive_book_to_market",)
        or spec.get("factor_raw_columns")
        != {"tushare_positive_book_to_market": "tushare_positive_book_to_market"}
        or required.get("dataset") != "tushare_daily_pb"
        or required.get("provider") != "tushare"
        or required.get("acceptance_status")
        != "full_source_coverage_passed_pending_no_return_uniqueness_and_capacity"
        or tuple(required.get("required_partition_years") or ())
        != tuple(range(2019, 2026))
        or tuple(required.get("required_columns") or ()) != TUSHARE_DAILY_PB_COLUMNS
        or capacity.get("holding_period_trading_days") != 3
        or capacity.get("minimum_required_cohorts") != 200
        or capacity.get("minimum_valid_names_per_factor_cohort") != 50
        or capacity.get("minimum_listing_sessions") != 20
        or uniqueness.get("start") != "2025-01-01"
        or uniqueness.get("end") != "2025-12-31"
        or uniqueness.get("comparison_field_count") != 43
        or len(uniqueness.get("comparison_fields") or []) != 43
        or uniqueness.get("minimum_pairwise_names_per_session") != 50
        or uniqueness.get("minimum_pairwise_sessions_per_comparison") != 100
        or uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        != 0.8
        or policy.get("capacity_must_run_before_close_known_comparison_fields")
        is not True
        or policy.get("both_capacity_and_uniqueness_must_pass") is not True
        or policy.get("one_completed_combined_audit_per_full_snapshot") is not True
        or spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("Tushare daily PB capacity preregistration is inconsistent")

    record_path = resolve_record_path(str(acceptance.get("record_path") or ""))
    manifest_path = resolve_record_path(str(acceptance.get("manifest_path") or ""))
    frame_path = resolve_record_path(str(acceptance.get("frame_path") or ""))
    if (
        not record_path.exists()
        or file_digest(record_path) != acceptance.get("record_sha256")
        or not manifest_path.exists()
        or file_digest(manifest_path) != acceptance.get("manifest_sha256")
        or not frame_path.exists()
        or file_digest(frame_path) != acceptance.get("frame_file_sha256")
    ):
        raise RichDataError("Tushare daily PB acceptance evidence fingerprint mismatch")
    record = load_json_record(
        record_path, kind="a_share_tushare_daily_pb_source_acceptance_record"
    )
    manifest = load_json_record(manifest_path, kind="a_share_rich_data_snapshot")
    files = list(manifest.get("files") or [])
    if (
        record.get("status") != "accepted_pending_full_history_uniqueness_and_capacity"
        or (record.get("acceptance_manifest") or {}).get("sha256")
        != acceptance.get("manifest_sha256")
        or manifest.get("dataset") != "tushare_daily_pb_acceptance"
        or manifest.get("provider") != "tushare"
        or manifest.get("requested_start") != acceptance.get("trade_date")
        or manifest.get("requested_end") != acceptance.get("trade_date")
        or manifest.get("acceptance_status")
        != "accepted_entitlement_formula_and_current_coverage_pending_full_history"
        or manifest.get("price_fields_loaded") != []
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
        or len(files) != 1
        or files[0].get("path") != str(acceptance.get("frame_path"))
        or files[0].get("sha256") != acceptance.get("frame_content_sha256")
        or int(files[0].get("rows") or -1) != int(acceptance.get("rows") or -2)
    ):
        raise RichDataError("Tushare daily PB acceptance evidence identity mismatch")
    frame = load_snapshot_frame(files[0])
    trade_date = pd.Timestamp(str(acceptance["trade_date"]))
    stored_dates = pd.to_datetime(frame["trade_date"], errors="coerce").dt.normalize()
    stored_pb = pd.to_numeric(frame["pb"], errors="coerce")
    stored_factor = pd.to_numeric(
        frame["tushare_positive_book_to_market"], errors="coerce"
    )
    if (
        tuple(frame.columns) != TUSHARE_DAILY_PB_COLUMNS
        or len(frame) != int(acceptance["rows"])
        or stored_dates.isna().any()
        or not stored_dates.eq(trade_date).all()
        or frame["instrument"].astype("string").isna().any()
        or frame["instrument"].nunique() != len(frame)
        or not stored_pb.gt(0.0).all()
        or not np.isfinite(stored_factor).all()
        or not np.allclose(
            stored_factor.to_numpy(dtype="float64"),
            1.0 / stored_pb.to_numpy(dtype="float64"),
            rtol=0.0,
            atol=1e-12,
        )
        or not frame["provider"].eq("tushare").all()
    ):
        raise RichDataError("Tushare daily PB acceptance formula audit failed")
    return {
        "spec_path": path,
        "spec": spec,
        "record_path": record_path,
        "record": record,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "frame_path": frame_path,
    }


def load_baostock_5m_contract(
    path: Path = DEFAULT_BAOSTOCK_5M_CONTRACT,
) -> dict[str, Any]:
    """Load the frozen post-probe, pre-acceptance BaoStock contract."""

    path = path.expanduser().resolve()
    if file_digest(path) != BAOSTOCK_5M_CONTRACT_SHA256:
        raise RichDataError("BaoStock five-minute contract fingerprint mismatch")
    contract = load_json_record(path, kind="a_share_baostock_5m_data_contract")
    source = contract.get("source") or {}
    timestamp = contract.get("timestamp_contract") or {}
    acceptance = contract.get("formal_acceptance") or {}
    bulk = contract.get("bulk_snapshot_contract") or {}
    if (
        contract.get("version") != 1
        or contract.get("status")
        != "frozen_after_no_return_feasibility_probe_before_formal_acceptance_bulk_snapshot_or_factor_values"
        or contract.get("frozen_at") != "2026-07-14T20:57:08Z"
        or source.get("provider") != "baostock"
        or source.get("sdk_version") != "0.9.3"
        or source.get("source_frequency") != "5"
        or source.get("canonical_frequency") != "5m"
        or source.get("adjustflag") != "3"
        or source.get("requested_fields")
        != [
            "date",
            "time",
            "code",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "adjustflag",
        ]
        or timestamp.get("source_label") != "bar_end"
        or timestamp.get("expected_bars_per_complete_regular_session") != 48
        or acceptance.get("trade_date") != "2026-07-10"
        or acceptance.get("symbols") != ["600519", "000001", "300750", "688981"]
        or acceptance.get("required_rows_per_symbol") != 48
        or acceptance.get("raw_ohlc_max_relative_error_to_local_raw_daily") != 0.002
        or bulk.get("development_start") != "2020-01-01"
        or bulk.get("development_end") != "2025-12-31"
        or bulk.get("minimum_potential_non_overlapping_three_session_cohorts") != 200
        or contract.get("forward_return_fields_read") is not False
        or contract.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "BaoStock five-minute contract does not match the frozen protocol"
        )
    return contract


def load_factor_universe_intervals(
    path: Path = DEFAULT_FACTOR_UNIVERSE,
) -> pd.DataFrame:
    """Read point-in-time instrument intervals without loading any price field."""

    path = path.expanduser().resolve()
    if not path.exists():
        raise RichDataError(f"factor universe does not exist: {path}")
    frame = pd.read_csv(
        path,
        sep="\t",
        header=None,
        names=["instrument", "start_date", "end_date"],
        dtype={"instrument": "string"},
    )
    frame["start_date"] = pd.to_datetime(
        frame["start_date"], errors="coerce"
    ).dt.normalize()
    frame["end_date"] = pd.to_datetime(
        frame["end_date"], errors="coerce"
    ).dt.normalize()
    valid_symbols = frame["instrument"].str.fullmatch(r"(?:SH6|SZ[03])\d{5}", na=False)
    if (
        frame.empty
        or frame[["start_date", "end_date"]].isna().any().any()
        or (~valid_symbols).any()
        or frame["instrument"].duplicated().any()
        or frame["start_date"].gt(frame["end_date"]).any()
    ):
        raise RichDataError("factor universe contains invalid or duplicate intervals")
    return frame.sort_values("instrument", kind="stable").reset_index(drop=True)


def local_calendar_dates(
    start: dt.date,
    end: dt.date,
    path: Path = DEFAULT_LOCAL_CALENDAR,
) -> pd.DatetimeIndex:
    """Read the local calendar without touching daily prices."""

    path = path.expanduser().resolve()
    if not path.exists():
        raise RichDataError(f"local calendar does not exist: {path}")
    values = pd.to_datetime(
        path.read_text(encoding="utf-8").splitlines(), errors="coerce"
    )
    if pd.isna(values).any():
        raise RichDataError("local calendar contains an invalid date")
    calendar = pd.DatetimeIndex(values).normalize().unique().sort_values()
    return calendar[(calendar >= pd.Timestamp(start)) & (calendar <= pd.Timestamp(end))]


def atomic_write_frame(frame: pd.DataFrame, destination: Path) -> None:
    """Write one Parquet snapshot atomically."""

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


def atomic_write_json(payload: dict[str, Any], destination: Path) -> None:
    """Write a manifest atomically."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, suffix=".json", mode="w", encoding="utf-8", delete=False
    ) as handle:
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
    data_contract: dict[str, Any] | None = None,
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
            if acceptance_by_code
            and all(
                report["status"].startswith("automatic_checks_passed")
                for report in acceptance_by_code.values()
            )
            else "not_run" if acceptance_by_code is None else "automatic_checks_failed"
        ),
    }
    if data_contract is not None:
        manifest["data_contract"] = data_contract
    run_manifest_path = RUNS_ROOT / f"{run_id}.json"
    atomic_write_json(manifest, run_manifest_path)
    return run_manifest_path


def expected_minute_times(bar_label: str, frequency: str = "1m") -> tuple[dt.time, ...]:
    """Return exact regular-session timestamps for one supported bar contract."""

    if bar_label not in {"start", "end"}:
        raise RichDataError("bar label must be 'start' or 'end'")
    if frequency not in MINUTE_EXPECTED_BARS_BY_FREQUENCY:
        raise RichDataError(f"unsupported alignment frequency: {frequency}")
    minutes = int(frequency.removesuffix("m"))
    bars_per_half = 120 // minutes
    anchor = pd.Timestamp("2000-01-03")
    bar_ends = pd.DatetimeIndex(
        [
            *pd.date_range(
                anchor + pd.Timedelta(hours=9, minutes=30 + minutes),
                periods=bars_per_half,
                freq=f"{minutes}min",
            ),
            *pd.date_range(
                anchor + pd.Timedelta(hours=13, minutes=minutes),
                periods=bars_per_half,
                freq=f"{minutes}min",
            ),
        ]
    )
    timestamps = bar_ends - (
        pd.Timedelta(minutes=minutes) if bar_label == "start" else pd.Timedelta(0)
    )
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
            if day.get("status") == "passed" and day.get("inferred_volume_unit") in {
                "shares",
                "lots",
            }:
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
        raise RichDataError(
            "pass --reviewed-boundaries only after checking the first and last minute labels"
        )
    if bar_label not in {"start", "end"}:
        raise RichDataError("bar label must be 'start' or 'end'")
    if volume_unit not in {"shares", "lots"}:
        raise RichDataError("volume unit must be 'shares' or 'lots'")
    snapshot_path = snapshot_path.expanduser().resolve()
    snapshot = load_json_record(snapshot_path, kind="a_share_rich_data_snapshot")
    frequency = str(snapshot.get("frequency") or "")
    if (
        snapshot.get("dataset") != "minutes"
        or frequency not in MINUTE_EXPECTED_BARS_BY_FREQUENCY
    ):
        raise RichDataError(
            "minute alignment confirmation requires a supported minute snapshot"
        )
    if (
        snapshot.get("acceptance_status")
        != "automatic_checks_passed_pending_time_alignment"
    ):
        raise RichDataError(
            "minute snapshot has not passed automatic acceptance checks"
        )
    files = list(snapshot.get("files") or [])
    if not files:
        raise RichDataError("minute snapshot contains no files")

    expected_times = expected_minute_times(bar_label, frequency)
    expected_bars = MINUTE_EXPECTED_BARS_BY_FREQUENCY[frequency]
    complete_session_evidence: list[dict[str, Any]] = []
    for file_record in files:
        frame = load_snapshot_frame(file_record)
        if frame.empty:
            continue
        required = {
            "datetime",
            "symbol",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "provider",
        }
        if missing := sorted(required - set(frame.columns)):
            raise RichDataError(
                "minute snapshot file is missing canonical columns: "
                + ", ".join(missing)
            )
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
            if len(observed_times) == expected_bars:
                if observed_times != expected_times:
                    raise RichDataError(
                        f"declared {bar_label}-label convention conflicts with a {expected_bars}-bar session on "
                        f"{pd.Timestamp(trade_date).date().isoformat()}"
                    )
                complete_session_evidence.append(
                    {
                        "symbol": str(group["symbol"].iloc[0]),
                        "trade_date": pd.Timestamp(trade_date).date().isoformat(),
                        "first_bar": group.sort_values("_datetime")["_datetime"]
                        .iloc[0]
                        .isoformat(),
                        "last_bar": group.sort_values("_datetime")["_datetime"]
                        .iloc[-1]
                        .isoformat(),
                    }
                )
    if not complete_session_evidence:
        raise RichDataError(
            f"alignment confirmation needs at least one exact {expected_bars}-bar session as boundary evidence"
        )
    inferred_units = confirmation_volume_units(snapshot)
    if inferred_units != {volume_unit}:
        raise RichDataError(
            "declared volume unit conflicts with automatic reconciliation: "
            f"declared={volume_unit}, inferred={sorted(inferred_units)}"
        )

    interval_minutes = int(frequency.removesuffix("m"))
    run_id = new_run_id(f"{snapshot['provider']}_{frequency}_alignment")
    record = {
        "schema_version": 1,
        "kind": "a_share_minute_alignment_confirmation",
        "status": "passed_for_feature_research",
        "run_id": run_id,
        "confirmed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": snapshot["provider"],
        "frequency": frequency,
        "bar_timestamp_label": bar_label,
        "normalization_to_bar_end": (
            f"add_{interval_minutes}_minutes" if bar_label == "start" else "identity"
        ),
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
    destination = (
        output.expanduser().resolve()
        if output is not None
        else ALIGNMENTS_ROOT / f"{run_id}.json"
    )
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
        str(item.get("diagnostic_direction"))
        for item in features
        if isinstance(item, dict)
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
        and minute_contract.get("expected_regular_session_bars")
        == MINUTE_FEATURE_EXPECTED_BARS
        and holding_protocol.get("holding_period_trading_days") == 3
        and holding_protocol.get("non_overlapping_cohorts") is True
        and holding_protocol.get("topk") == 3
        and holding_protocol.get("open_cost") == 0.00012
        and holding_protocol.get("close_cost") == 0.00062
    )
    if not contract_ok:
        raise RichDataError(
            "minute factor preregistration does not match the frozen v1 feature catalog"
        )
    if (
        spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "minute factor preregistration must exclude forward returns and promotion"
        )
    return spec


def load_baostock_5m_factor_spec(
    path: Path = DEFAULT_BAOSTOCK_5M_FACTOR_SPEC,
) -> dict[str, Any]:
    """Load the immutable post-acceptance, pre-factor-value five-minute spec."""

    path = path.expanduser().resolve()
    if file_digest(path) != BAOSTOCK_5M_FACTOR_SPEC_SHA256:
        raise RichDataError(
            "BaoStock five-minute factor preregistration fingerprint mismatch"
        )
    spec = load_json_record(path, kind="a_share_baostock_5m_factor_preregistration")
    source_chain = spec.get("source_chain") or {}
    contract_link = source_chain.get("data_contract") or {}
    acceptance_link = source_chain.get("acceptance_snapshot") or {}
    alignment_link = source_chain.get("alignment_confirmation") or {}
    minute_contract = spec.get("minute_contract") or {}
    features = list(spec.get("features") or [])
    names = tuple(str(item.get("name")) for item in features if isinstance(item, dict))
    directions = tuple(
        str(item.get("diagnostic_direction"))
        for item in features
        if isinstance(item, dict)
    )
    development = spec.get("development_protocol") or {}
    coverage = spec.get("coverage_gate_before_forward_returns") or {}
    if (
        spec.get("version") != 1
        or spec.get("status")
        != "frozen_after_source_acceptance_before_five_minute_factor_values_or_forward_returns"
        or spec.get("preregistered_at") != "2026-07-14T21:02:19Z"
        or contract_link.get("sha256") != BAOSTOCK_5M_CONTRACT_SHA256
        or acceptance_link.get("sha256")
        != "e3d2160fab34c3a51b1524623a7c14f800abdc75164a66f0371386cf29ac68cd"
        or alignment_link.get("sha256")
        != "cf50051d254a3fcc2727d649b167ed053bbba2e2b3dfa2c939fae04166b54c6c"
        or names != BAOSTOCK_5M_FEATURE_NAMES
        or directions != BAOSTOCK_5M_FEATURE_DIRECTIONS
        or minute_contract.get("provider") != "baostock"
        or minute_contract.get("frequency") != "5m"
        or minute_contract.get("prices") != "raw_unadjusted"
        or minute_contract.get("timestamp_normalized_to") != "bar_end"
        or minute_contract.get("complete_regular_session_required") is not True
        or minute_contract.get("expected_regular_session_bars") != 48
        or development.get("start") != "2020-01-01"
        or development.get("end") != "2025-12-31"
        or development.get("holding_period_trading_days") != 3
        or development.get("non_overlapping_cohorts") is not True
        or development.get("topk") != 3
        or development.get("open_cost") != 0.00012
        or development.get("close_cost") != 0.00062
        or coverage.get("minimum_potential_non_overlapping_three_session_cohorts")
        != 200
        or spec.get("forward_return_fields_read") is not False
        or spec.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "BaoStock five-minute factor preregistration does not match the frozen protocol"
        )
    return spec


def load_baostock_5m_source_chain(
    factor_spec_path: Path = DEFAULT_BAOSTOCK_5M_FACTOR_SPEC,
) -> dict[str, Any]:
    """Fingerprint-validate the contract, acceptance and alignment records."""

    spec = load_baostock_5m_factor_spec(factor_spec_path)
    contract = load_baostock_5m_contract()
    chain = spec["source_chain"]
    acceptance_link = chain["acceptance_snapshot"]
    alignment_link = chain["alignment_confirmation"]
    acceptance_path = resolve_record_path(acceptance_link["path"])
    alignment_path = resolve_record_path(alignment_link["path"])
    if (
        not acceptance_path.exists()
        or file_digest(acceptance_path) != acceptance_link["sha256"]
    ):
        raise RichDataError("BaoStock five-minute acceptance fingerprint mismatch")
    if (
        not alignment_path.exists()
        or file_digest(alignment_path) != alignment_link["sha256"]
    ):
        raise RichDataError("BaoStock five-minute alignment fingerprint mismatch")
    acceptance = load_json_record(acceptance_path, kind="a_share_rich_data_snapshot")
    alignment = load_json_record(
        alignment_path, kind="a_share_minute_alignment_confirmation"
    )
    expected_symbols = {
        qlib_symbol(code) for code in contract["formal_acceptance"]["symbols"]
    }
    observed_symbols = {
        str(item.get("symbol")) for item in (acceptance.get("files") or [])
    }
    if (
        acceptance.get("provider") != "baostock"
        or acceptance.get("frequency") != "5m"
        or acceptance.get("prices") != "raw_unadjusted"
        or acceptance.get("acceptance_status")
        != "automatic_checks_passed_pending_time_alignment"
        or (acceptance.get("data_contract") or {}).get("sha256")
        != BAOSTOCK_5M_CONTRACT_SHA256
        or observed_symbols != expected_symbols
        or any(
            int(item.get("rows") or 0) != 48 for item in (acceptance.get("files") or [])
        )
        or alignment.get("status") != "passed_for_feature_research"
        or alignment.get("provider") != "baostock"
        or alignment.get("frequency") != "5m"
        or alignment.get("bar_timestamp_label") != "end"
        or alignment.get("volume_unit") != "shares"
        or resolve_record_path(
            (alignment.get("source_acceptance_snapshot") or {}).get("path") or ""
        )
        != acceptance_path
        or (alignment.get("source_acceptance_snapshot") or {}).get("sha256")
        != acceptance_link["sha256"]
    ):
        raise RichDataError(
            "BaoStock five-minute source chain violates the frozen protocol"
        )
    for file_record in acceptance.get("files") or []:
        frame = load_snapshot_frame(file_record)
        report = file_record.get("acceptance") or {}
        exact = report.get("baostock_5m_contract") or {}
        if (
            report.get("status") != "automatic_checks_passed_pending_time_alignment"
            or exact.get("exact_timestamp_grid_passed") is not True
            or (report.get("daily_reconciliation") or {}).get("status") != "passed"
        ):
            raise RichDataError(
                "BaoStock five-minute acceptance file failed its frozen checks"
            )
        if len(frame) != 48:
            raise RichDataError(
                "BaoStock five-minute acceptance data no longer has 48 rows"
            )
    return {
        "contract": contract,
        "factor_spec": spec,
        "acceptance_path": acceptance_path,
        "acceptance": acceptance,
        "alignment_path": alignment_path,
        "alignment": alignment,
    }


def load_baostock_5m_suspension_audit(
    path: Path = DEFAULT_BAOSTOCK_5M_SUSPENSION_AUDIT,
) -> dict[str, Any]:
    """Validate the frozen treatment of BaoStock zero-price suspension rows."""

    path = path.expanduser().resolve()
    if file_digest(path) != BAOSTOCK_5M_SUSPENSION_AUDIT_SHA256:
        raise RichDataError(
            "BaoStock five-minute suspension audit fingerprint mismatch"
        )
    audit = load_json_record(
        path, kind="a_share_baostock_5m_suspension_placeholder_audit"
    )
    failure = audit.get("failed_full_attempt") or {}
    raw = audit.get("isolated_raw_partition_audit") or {}
    policy = audit.get("frozen_normalization_and_eligibility_treatment") or {}
    verification = audit.get("post_change_partition_verification") or {}
    if (
        audit.get("status")
        != "resolved_within_frozen_missing_or_halted_session_policy_before_full_retry"
        or (failure.get("failed_partition") or {}).get("code") != "600027"
        or (failure.get("failed_partition") or {}).get("year") != 2024
        or failure.get("temporary_snapshot_deleted") is not True
        or failure.get("final_snapshot_written") is not False
        or raw.get("source_rows") != 11616
        or raw.get("zero_price_zero_volume_zero_amount_placeholder_rows") != 478
        or raw.get("placeholder_stock_sessions") != 10
        or policy.get("silent_deduplication") is not False
        or policy.get("fill_interpolate_or_borrow_another_source") is not False
        or verification.get("canonical_rows_written") != 11138
        or verification.get("complete_regular_positive_activity_sessions") != 232
        or audit.get("forward_return_fields_read") is not False
        or audit.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "BaoStock five-minute suspension audit violates its frozen protocol"
        )
    return audit


def load_baostock_5m_throttle_audit(
    path: Path = DEFAULT_BAOSTOCK_5M_THROTTLE_AUDIT,
) -> dict[str, Any]:
    """Validate the frozen low-call-count plan after anonymous throttling."""

    path = path.expanduser().resolve()
    if file_digest(path) != BAOSTOCK_5M_THROTTLE_AUDIT_SHA256:
        raise RichDataError("BaoStock five-minute throttle audit fingerprint mismatch")
    audit = load_json_record(path, kind="a_share_baostock_5m_request_throttle_audit")
    failure = audit.get("failed_attempt") or {}
    probe = audit.get("single_post_failure_probe") or {}
    plan = audit.get("frozen_reduced_request_plan") or {}
    if (
        audit.get("status") != "request_plan_reduced_before_any_post_blacklist_retry"
        or failure.get("planned_provider_requests") != 29246
        or failure.get("reported_partitions_completed_before_failure") != 9000
        or (failure.get("failed_request") or {}).get("provider_error")
        != "黑名单用户，请与管理员联系"
        or failure.get("temporary_snapshot_deleted") is not True
        or failure.get("final_snapshot_written") is not False
        or probe.get("login_status") != "rejected"
        or probe.get("history_query_issued") is not False
        or plan.get("provider_requests") != 5386
        or plan.get("yearly_parquet_storage_partitions") != 29246
        or plan.get("blacklist_error_is_immediately_fatal_without_retry") is not True
        or plan.get("partial_resume_allowed") is not False
        or audit.get("forward_return_fields_read") is not False
        or audit.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "BaoStock five-minute throttle audit violates its frozen protocol"
        )
    return audit


def require_baostock_5m_runtime() -> None:
    """Require the exact anonymous SDK version frozen by the source contract."""

    require_provider("baostock")
    try:
        version = importlib.metadata.version("baostock")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RichDataError("BaoStock SDK metadata is unavailable") from exc
    if version != "0.9.3":
        raise RichDataError(
            f"BaoStock five-minute sync requires baostock==0.9.3, found {version}"
        )


def baostock_5m_partition_tasks(
    intervals: pd.DataFrame,
    start: dt.date,
    end: dt.date,
) -> list[tuple[str, str, str, int]]:
    """Split point-in-time instrument intervals into calendar-year storage partitions."""

    tasks: list[tuple[str, str, str, int]] = []
    range_start = pd.Timestamp(start)
    range_end = pd.Timestamp(end)
    for row in intervals.itertuples(index=False):
        interval_start = max(pd.Timestamp(row.start_date), range_start)
        interval_end = min(pd.Timestamp(row.end_date), range_end)
        if interval_start > interval_end:
            continue
        code = str(row.instrument)[2:]
        for year in range(interval_start.year, interval_end.year + 1):
            partition_start = max(
                interval_start, pd.Timestamp(year=year, month=1, day=1)
            )
            partition_end = min(interval_end, pd.Timestamp(year=year, month=12, day=31))
            tasks.append(
                (
                    code,
                    partition_start.date().isoformat(),
                    partition_end.date().isoformat(),
                    year,
                )
            )
    keys = [(code, year) for code, _, _, year in tasks]
    if len(keys) != len(set(keys)):
        raise RichDataError(
            "BaoStock five-minute point-in-time tasks contain duplicate symbol-years"
        )
    return tasks


def baostock_5m_request_tasks(
    intervals: pd.DataFrame,
    start: dt.date,
    end: dt.date,
) -> list[tuple[str, str, str]]:
    """Create one low-rate provider request for each clipped PIT instrument interval."""

    tasks: list[tuple[str, str, str]] = []
    range_start = pd.Timestamp(start)
    range_end = pd.Timestamp(end)
    for row in intervals.itertuples(index=False):
        interval_start = max(pd.Timestamp(row.start_date), range_start)
        interval_end = min(pd.Timestamp(row.end_date), range_end)
        if interval_start > interval_end:
            continue
        tasks.append(
            (
                str(row.instrument)[2:],
                interval_start.date().isoformat(),
                interval_end.date().isoformat(),
            )
        )
    codes = [code for code, _, _ in tasks]
    if len(codes) != len(set(codes)):
        raise RichDataError(
            "BaoStock five-minute provider requests contain duplicate symbols"
        )
    return tasks


def split_baostock_5m_request_frame(
    frame: pd.DataFrame,
    storage_tasks: list[tuple[str, str, str, int]],
) -> Iterable[tuple[tuple[str, str, str, int], pd.DataFrame]]:
    """Split one instrument response into the frozen yearly Parquet partitions."""

    source_by_year = {
        int(year): int(count)
        for year, count in frame.attrs.get("source_rows_by_year", {}).items()
    }
    placeholders_by_year = {
        int(year): int(count)
        for year, count in frame.attrs.get(
            "zero_price_placeholder_rows_by_year", {}
        ).items()
    }
    placeholder_dates = [
        str(value)
        for value in frame.attrs.get("zero_price_placeholder_session_dates", [])
    ]
    timestamps = (
        pd.to_datetime(frame["datetime"], errors="coerce")
        if not frame.empty
        else pd.Series([], dtype="datetime64[ns]")
    )
    if not source_by_year and not frame.empty:
        source_by_year = {
            int(year): int(count)
            for year, count in timestamps.dt.year.value_counts().items()
        }
    for task in storage_tasks:
        _, start_value, end_value, year = task
        if frame.empty:
            partition = frame.copy()
        else:
            in_partition = timestamps.ge(pd.Timestamp(start_value)) & timestamps.lt(
                pd.Timestamp(end_value) + pd.Timedelta(days=1)
            )
            partition = frame.loc[in_partition].copy().reset_index(drop=True)
        year_placeholder_dates = [
            value for value in placeholder_dates if pd.Timestamp(value).year == year
        ]
        partition.attrs["source_rows"] = source_by_year.get(year, 0)
        partition.attrs["source_rows_by_year"] = {year: source_by_year.get(year, 0)}
        partition.attrs["zero_price_placeholder_rows_excluded"] = (
            placeholders_by_year.get(year, 0)
        )
        partition.attrs["zero_price_placeholder_rows_by_year"] = {
            year: placeholders_by_year.get(year, 0)
        }
        partition.attrs["zero_price_placeholder_session_dates"] = year_placeholder_dates
        yield task, partition


def validate_baostock_5m_partition(
    frame: pd.DataFrame,
    task: tuple[str, str, str, int],
    calendar: pd.DatetimeIndex,
) -> list[str]:
    """Validate one raw partition and return its exact complete-session dates."""

    code, start_value, end_value, year = task
    required = {
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
    }
    if missing := sorted(required - set(frame.columns)):
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition is missing columns: "
            + ", ".join(missing)
        )
    if frame.empty:
        return []
    timestamps = pd.to_datetime(frame["datetime"], errors="coerce")
    if timestamps.isna().any() or timestamps.duplicated().any():
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition has invalid or duplicate timestamps"
        )
    if not timestamps.is_monotonic_increasing:
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition is not sorted"
        )
    start_timestamp = pd.Timestamp(start_value)
    end_timestamp = pd.Timestamp(end_value) + pd.Timedelta(days=1)
    if timestamps.lt(start_timestamp).any() or timestamps.ge(end_timestamp).any():
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition escaped its task range"
        )
    expected_symbol = qlib_symbol(code)
    if (
        set(frame["symbol"].astype(str)) != {expected_symbol}
        or set(frame["source_symbol"].astype(str)) != {vendor_symbol(code, "baostock")}
        or set(frame["provider"].astype(str)) != {"baostock"}
    ):
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition identity mismatch"
        )
    calendar_dates = set(pd.DatetimeIndex(calendar).normalize())
    observed_dates = set(timestamps.dt.normalize())
    if not observed_dates.issubset(calendar_dates):
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition contains non-local-calendar dates"
        )
    expected_times = expected_minute_times("end", "5m")
    expected_time_set = set(expected_times)
    if not set(timestamps.dt.time).issubset(expected_time_set):
        raise RichDataError(
            f"BaoStock five-minute {code} {year} partition violates the frozen end-label grid"
        )
    complete_dates: list[str] = []
    work = frame.assign(_trade_date=timestamps.dt.normalize())
    for trade_date, group in work.groupby("_trade_date", sort=True):
        observed_times = tuple(pd.to_datetime(group["datetime"]).dt.time)
        if len(group) > len(expected_times):
            raise RichDataError(
                f"BaoStock five-minute {code} {trade_date.date()} has too many bars"
            )
        positive_activity = (
            pd.to_numeric(group["volume"], errors="coerce").sum() > 0.0
            and pd.to_numeric(group["amount"], errors="coerce").sum() > 0.0
        )
        if observed_times == expected_times and positive_activity:
            complete_dates.append(trade_date.date().isoformat())
    return complete_dates


def baostock_5m_coverage_report(
    intervals: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    complete_counts: dict[str, int],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Compute the frozen no-return point-in-time coverage and capacity gates."""

    active_counts = np.zeros(len(calendar), dtype=np.int64)
    for row in intervals.itertuples(index=False):
        left = int(calendar.searchsorted(pd.Timestamp(row.start_date), side="left"))
        right = int(calendar.searchsorted(pd.Timestamp(row.end_date), side="right"))
        if right > left:
            active_counts[left:right] += 1
    completed = np.asarray(
        [int(complete_counts.get(value.date().isoformat(), 0)) for value in calendar],
        dtype=np.int64,
    )
    if (completed > active_counts).any():
        raise RichDataError(
            "BaoStock five-minute complete-session count exceeds the PIT universe"
        )
    ratios = np.divide(
        completed,
        active_counts,
        out=np.full(len(calendar), np.nan, dtype=float),
        where=active_counts > 0,
    )
    valid_ratios = ratios[np.isfinite(ratios)]
    if valid_ratios.size == 0:
        raise RichDataError(
            "BaoStock five-minute coverage has no active PIT-universe sessions"
        )
    bulk = contract["bulk_snapshot_contract"]
    potential_indices = np.arange(0, max(len(calendar) - 3, 0), 3, dtype=int)
    potential_cohorts = int(
        (
            completed[potential_indices]
            >= int(bulk["minimum_names_per_factor_cross_section"])
        ).sum()
    )
    median_coverage = float(np.median(valid_ratios))
    p05_coverage = float(np.quantile(valid_ratios, 0.05))
    gate_passed = (
        median_coverage >= float(bulk["median_eligible_universe_coverage_min"])
        and p05_coverage >= float(bulk["p05_eligible_universe_coverage_min"])
        and potential_cohorts
        >= int(bulk["minimum_potential_non_overlapping_three_session_cohorts"])
    )
    return {
        "calendar_sessions": int(len(calendar)),
        "median_eligible_universe_coverage": median_coverage,
        "p05_eligible_universe_coverage": p05_coverage,
        "dates_with_at_least_fifty_complete_names": int(
            (completed >= int(bulk["minimum_names_per_factor_cross_section"])).sum()
        ),
        "potential_non_overlapping_three_session_cohorts": potential_cohorts,
        "gate_passed_before_prices": gate_passed,
        "daily": [
            {
                "trade_date": value.date().isoformat(),
                "active_pit_names": int(active),
                "complete_five_minute_names": int(complete),
                "eligible_universe_coverage": (
                    float(ratio) if np.isfinite(ratio) else None
                ),
            }
            for value, active, complete, ratio in zip(
                calendar, active_counts, completed, ratios, strict=True
            )
        ],
    }


def write_baostock_5m_preflight(
    *,
    data_root: Path = DATA_ROOT,
    universe_path: Path = DEFAULT_FACTOR_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
    factor_spec_path: Path = DEFAULT_BAOSTOCK_5M_FACTOR_SPEC,
) -> Path:
    """Record a source-chain and storage audit without issuing a network request."""

    source_chain = load_baostock_5m_source_chain(factor_spec_path)
    load_baostock_5m_suspension_audit()
    load_baostock_5m_throttle_audit()
    require_baostock_5m_runtime()
    contract = source_chain["contract"]
    bulk = contract["bulk_snapshot_contract"]
    start = dt.date.fromisoformat(str(bulk["development_start"]))
    end = dt.date.fromisoformat(str(bulk["development_end"]))
    intervals = load_factor_universe_intervals(universe_path)
    calendar = local_calendar_dates(start, end, calendar_path)
    if calendar.empty:
        raise RichDataError(
            "local calendar has no sessions in the BaoStock five-minute range"
        )
    storage_tasks = baostock_5m_partition_tasks(intervals, start, end)
    request_tasks = baostock_5m_request_tasks(intervals, start, end)
    if not storage_tasks or not request_tasks:
        raise RichDataError("factor universe has no BaoStock five-minute partitions")
    resolved_data_root = data_root.expanduser().resolve()
    resolved_data_root.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(resolved_data_root)
    passed = usage.free >= BAOSTOCK_5M_MINIMUM_FREE_BYTES
    run_id = new_run_id("baostock_5m_preflight")
    payload = {
        "schema_version": 1,
        "kind": "a_share_baostock_5m_preflight",
        "run_id": run_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": (
            "passed_before_network"
            if passed
            else "blocked_insufficient_disk_before_network"
        ),
        "data_root": str(resolved_data_root),
        "sdk_version": importlib.metadata.version("baostock"),
        "source_chain": {
            "data_contract_sha256": BAOSTOCK_5M_CONTRACT_SHA256,
            "factor_spec_sha256": BAOSTOCK_5M_FACTOR_SPEC_SHA256,
            "acceptance_snapshot": {
                "path": manifest_path(source_chain["acceptance_path"]),
                "sha256": file_digest(source_chain["acceptance_path"]),
            },
            "alignment_confirmation": {
                "path": manifest_path(source_chain["alignment_path"]),
                "sha256": file_digest(source_chain["alignment_path"]),
            },
            "suspension_placeholder_audit": {
                "path": manifest_path(DEFAULT_BAOSTOCK_5M_SUSPENSION_AUDIT.resolve()),
                "sha256": BAOSTOCK_5M_SUSPENSION_AUDIT_SHA256,
            },
            "request_throttle_audit": {
                "path": manifest_path(DEFAULT_BAOSTOCK_5M_THROTTLE_AUDIT.resolve()),
                "sha256": BAOSTOCK_5M_THROTTLE_AUDIT_SHA256,
            },
        },
        "development_start": start.isoformat(),
        "development_end": end.isoformat(),
        "point_in_time_instruments": int(len(intervals)),
        "provider_pit_interval_requests": int(len(request_tasks)),
        "yearly_storage_partitions": int(len(storage_tasks)),
        "calendar_sessions": int(len(calendar)),
        "universe": {
            "path": manifest_path(universe_path.expanduser().resolve()),
            "sha256": file_digest(universe_path.expanduser().resolve()),
        },
        "calendar": {
            "path": manifest_path(calendar_path.expanduser().resolve()),
            "sha256": file_digest(calendar_path.expanduser().resolve()),
        },
        "minimum_free_bytes": BAOSTOCK_5M_MINIMUM_FREE_BYTES,
        "observed_free_bytes": int(usage.free),
        "observed_free_gib": float(usage.free / 1024**3),
        "filesystem_device": int(resolved_data_root.stat().st_dev),
        "network_request_issued": False,
        "raw_or_derived_factor_values_read": False,
        "forward_return_fields_read": False,
        "selection_or_promotion_allowed": False,
    }
    destination = (
        resolved_data_root / "metadata" / "rich_data" / "preflights" / f"{run_id}.json"
    )
    atomic_write_json(payload, destination)
    return destination


def probe_baostock_5m_restoration(
    *,
    data_root: Path = DATA_ROOT,
) -> Path:
    """Issue one accepted-date request and record whether anonymous access recovered."""

    source_chain = load_baostock_5m_source_chain()
    load_baostock_5m_suspension_audit()
    load_baostock_5m_throttle_audit()
    require_baostock_5m_runtime()
    contract = source_chain["contract"]
    acceptance = contract["formal_acceptance"]
    code = str(acceptance["symbols"][0])
    trade_date = dt.date.fromisoformat(str(acceptance["trade_date"]))
    run_id = new_run_id("baostock_5m_restoration_probe")
    payload: dict[str, Any] = {
        "schema_version": 1,
        "kind": "a_share_baostock_5m_restoration_probe",
        "run_id": run_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider": "baostock",
        "sdk_version": importlib.metadata.version("baostock"),
        "code": code,
        "trade_date": trade_date.isoformat(),
        "frequency": "5m",
        "source_chain": {
            "data_contract_sha256": BAOSTOCK_5M_CONTRACT_SHA256,
            "factor_spec_sha256": BAOSTOCK_5M_FACTOR_SPEC_SHA256,
            "suspension_placeholder_audit_sha256": BAOSTOCK_5M_SUSPENSION_AUDIT_SHA256,
            "request_throttle_audit_sha256": BAOSTOCK_5M_THROTTLE_AUDIT_SHA256,
        },
        "anonymous_login_attempted": True,
        "history_query_succeeded": False,
        "network_request_issued": True,
        "raw_or_derived_factor_values_read": False,
        "daily_open_close_fields_read": False,
        "forward_return_fields_read": False,
        "selection_or_promotion_allowed": False,
    }
    try:
        raw = fetch_baostock_minutes(code, trade_date, trade_date, "5m")
        frame = canonicalize_baostock_5m_bars(raw, code, trade_date, trade_date)
        report = baostock_5m_acceptance_report(frame, contract)
        passed = (
            report.get("status") == "automatic_checks_passed_pending_time_alignment"
            and (report.get("baostock_5m_contract") or {}).get(
                "exact_timestamp_grid_passed"
            )
            is True
            and len(frame) == 48
        )
        payload.update(
            {
                "status": (
                    "passed_for_bulk_retry"
                    if passed
                    else "failed_acceptance_stop_before_bulk_retry"
                ),
                "history_query_succeeded": True,
                "rows": int(len(frame)),
                "frame_sha256": frame_digest(frame),
                "acceptance": report,
            }
        )
    except Exception as exc:  # noqa: BLE001 - rejection must be recorded without retry.
        payload.update(
            {
                "status": "provider_rejected_stop_before_bulk_retry",
                "rows": 0,
                "provider_error": str(exc),
            }
        )
    resolved_data_root = data_root.expanduser().resolve()
    destination = (
        resolved_data_root
        / "metadata"
        / "rich_data"
        / "availability"
        / f"{run_id}.json"
    )
    atomic_write_json(payload, destination)
    return destination


def load_baostock_5m_restoration_probe(
    data_root: Path,
    *,
    now: dt.datetime | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Require a recent passing isolated probe before any post-blacklist bulk retry."""

    root = data_root.expanduser().resolve() / "metadata" / "rich_data" / "availability"
    paths = sorted(root.glob("*.json")) if root.exists() else []
    if not paths:
        raise RichDataError(
            "BaoStock bulk retry requires one restoration probe after the provider blacklist; "
            "run probe-baostock-5m-restoration once after a cooldown"
        )
    path = paths[-1]
    record = load_json_record(path, kind="a_share_baostock_5m_restoration_probe")
    chain = record.get("source_chain") or {}
    created = pd.Timestamp(record.get("created_at"))
    current = pd.Timestamp(now or dt.datetime.now(dt.timezone.utc))
    age_minutes = float((current - created).total_seconds() / 60.0)
    if (
        record.get("status") != "passed_for_bulk_retry"
        or record.get("provider") != "baostock"
        or record.get("code") != "600519"
        or record.get("trade_date") != "2026-07-10"
        or record.get("rows") != 48
        or record.get("history_query_succeeded") is not True
        or chain.get("request_throttle_audit_sha256")
        != BAOSTOCK_5M_THROTTLE_AUDIT_SHA256
        or record.get("forward_return_fields_read") is not False
        or record.get("selection_or_promotion_allowed") is not False
        or not 0.0 <= age_minutes <= BAOSTOCK_5M_RESTORATION_PROBE_MAX_AGE_MINUTES
    ):
        raise RichDataError(
            "latest BaoStock restoration probe is rejected, invalid, or older than "
            f"{BAOSTOCK_5M_RESTORATION_PROBE_MAX_AGE_MINUTES} minutes: {path}"
        )
    return path.resolve(), record


def previous_comparable_close_map(symbol: str) -> dict[pd.Timestamp, float]:
    """Express the prior close on each current session's raw-price scale.

    ``raw_close[t-1]`` alone creates a false gap on an ex-rights date.  The
    accepted daily factor lets us carry yesterday's adjusted close onto
    today's raw scale as ``raw_close[t-1] * factor[t-1] / factor[t]``.
    """

    path = DAILY_RAW_DIR / f"{str(symbol).lower()}.parquet"
    if not path.exists():
        raise RichDataError(
            f"local daily raw history is missing for minute feature construction: {path}"
        )
    daily = pd.read_parquet(path)
    required = {"date", "raw_close", "factor", "price_basis"}
    if missing := sorted(required - set(daily.columns)):
        raise RichDataError(
            "local daily history is missing raw-price columns: " + ", ".join(missing)
        )
    bases = set(daily["price_basis"].dropna().astype(str))
    if bases != {REQUIRED_DAILY_PRICE_BASIS}:
        raise RichDataError(
            f"local daily history has an unaccepted price basis for {symbol}: {sorted(bases)}"
        )
    work = daily[["date", "raw_close", "factor"]].copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce").dt.normalize()
    work["raw_close"] = pd.to_numeric(work["raw_close"], errors="coerce")
    work["factor"] = pd.to_numeric(work["factor"], errors="coerce")
    work = (
        work.dropna()
        .sort_values("date", kind="stable")
        .drop_duplicates("date", keep="last")
    )
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
    frequency: str = "1m",
    feature_names: tuple[str, ...] = MINUTE_FEATURE_NAMES,
) -> pd.DataFrame:
    """Construct one frozen close-known intraday feature catalog without returns."""

    required = {
        "datetime",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "provider",
    }
    if missing := sorted(required - set(frame.columns)):
        raise RichDataError(
            "minute feature input is missing columns: " + ", ".join(missing)
        )
    if bar_label not in {"start", "end"}:
        raise RichDataError("bar label must be 'start' or 'end'")
    if frequency not in MINUTE_EXPECTED_BARS_BY_FREQUENCY:
        raise RichDataError(f"unsupported minute feature frequency: {frequency}")
    if len(feature_names) != 5:
        raise RichDataError(
            "minute feature catalog must contain exactly five ordered names"
        )
    interval_minutes = int(frequency.removesuffix("m"))
    if 30 % interval_minutes:
        raise RichDataError(
            "minute feature frequency must divide the frozen 30-minute late window"
        )
    expected_bars = MINUTE_EXPECTED_BARS_BY_FREQUENCY[frequency]
    late_bar_count = 30 // interval_minutes
    late_return_name, late_amount_name, late_vwap_name, gap_name, volatility_name = (
        feature_names
    )
    work = frame.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    if work["datetime"].isna().any():
        raise RichDataError("minute feature input contains invalid timestamps")
    work["bar_end"] = work["datetime"] + (
        pd.Timedelta(minutes=interval_minutes)
        if bar_label == "start"
        else pd.Timedelta(0)
    )
    numeric_columns = ["open", "high", "low", "close", "volume", "amount"]
    for column in numeric_columns:
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if not np.isfinite(work[numeric_columns].to_numpy(dtype=float)).all():
        raise RichDataError(
            "minute feature input contains non-finite OHLCV/amount values"
        )
    if (work[["open", "high", "low", "close"]] <= 0.0).any().any():
        raise RichDataError("minute feature input contains non-positive prices")
    if (work[["volume", "amount"]] < 0.0).any().any():
        raise RichDataError("minute feature input contains negative volume or amount")
    work["trade_date"] = work["bar_end"].dt.normalize()
    expected_bar_ends = expected_minute_times("end", frequency)
    rows: list[dict[str, Any]] = []
    for (symbol, trade_date), group in work.groupby(
        ["symbol", "trade_date"], sort=True
    ):
        group = group.sort_values("bar_end", kind="stable")
        observed_bar_ends = tuple(group["bar_end"].dt.time)
        complete = (
            len(group) == expected_bars and observed_bar_ends == expected_bar_ends
        )
        values = {name: float("nan") for name in feature_names}
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
            if (
                len(anchor) == 1
                and len(late) == late_bar_count
                and float(anchor["close"].iloc[0]) > 0.0
            ):
                values[late_return_name] = (
                    day_close / float(anchor["close"].iloc[0]) - 1.0
                )
            if total_amount > 0.0:
                values[late_amount_name] = late_amount / total_amount
            if (
                total_amount > 0.0
                and total_volume > 0.0
                and late_amount > 0.0
                and late_volume > 0.0
            ):
                values[late_vwap_name] = (late_amount / late_volume) / (
                    total_amount / total_volume
                ) - 1.0
            previous_close = previous_closes.get(str(symbol), {}).get(
                pd.Timestamp(trade_date)
            )
            if previous_close is not None and previous_close > 0.0 and day_open > 0.0:
                opening_gap_return = day_open / previous_close - 1.0
                values[gap_name] = -float(np.sign(opening_gap_return)) * (
                    day_close / day_open - 1.0
                )
            log_returns = (
                np.log(pd.to_numeric(group["close"], errors="coerce")).diff().dropna()
            )
            if len(log_returns) == expected_bars - 1 and np.isfinite(log_returns).all():
                values[volatility_name] = float(np.sqrt(np.square(log_returns).sum()))
        eligible = complete and all(np.isfinite(values[name]) for name in feature_names)
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
    return (
        pd.DataFrame(rows)
        .sort_values(["trade_date", "symbol"], kind="stable")
        .reset_index(drop=True)
    )


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
    alignment = load_json_record(
        alignment_path, kind="a_share_minute_alignment_confirmation"
    )
    spec_kind = load_json_record(factor_spec_path).get("kind")
    if spec_kind == "a_share_minute_factor_preregistration":
        spec = load_minute_factor_spec(factor_spec_path)
    elif spec_kind == "a_share_baostock_5m_factor_preregistration":
        spec = load_baostock_5m_factor_spec(factor_spec_path)
    else:
        raise RichDataError(
            f"unsupported minute factor preregistration kind: {spec_kind}"
        )
    minute_contract = spec["minute_contract"]
    frequency = str(minute_contract["frequency"])
    feature_names = tuple(str(item["name"]) for item in spec["features"])
    allowed_datasets = (
        {"minutes", "baostock_five_minute_history"}
        if spec_kind == "a_share_baostock_5m_factor_preregistration"
        else {"minutes"}
    )
    if (
        snapshot.get("dataset") not in allowed_datasets
        or snapshot.get("frequency") != frequency
    ):
        raise RichDataError(
            f"minute feature construction requires a {frequency} minute snapshot"
        )
    if snapshot.get("dataset") == "baostock_five_minute_history" and (
        snapshot.get("status")
        != "full_source_coverage_passed_pending_no_return_feature_materialization"
        or (snapshot.get("coverage") or {}).get("gate_passed_before_prices") is not True
        or snapshot.get("forward_return_fields_read") is not False
        or snapshot.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError(
            "BaoStock five-minute history must pass its no-return full-source coverage gate "
            "before feature materialization"
        )
    if snapshot.get("prices") != "raw_unadjusted":
        raise RichDataError(
            "minute feature construction requires raw unadjusted prices"
        )
    expected_provider = minute_contract.get("provider")
    if expected_provider is not None and snapshot.get("provider") != expected_provider:
        raise RichDataError(
            "minute snapshot provider does not match the frozen factor specification"
        )
    if alignment.get("status") != "passed_for_feature_research":
        raise RichDataError("minute alignment has not passed for feature research")
    if snapshot.get("provider") != alignment.get("provider") or snapshot.get(
        "frequency"
    ) != alignment.get("frequency"):
        raise RichDataError(
            "minute snapshot provider/frequency does not match the alignment confirmation"
        )
    source_acceptance = alignment.get("source_acceptance_snapshot") or {}
    source_acceptance_path = resolve_record_path(
        str(source_acceptance.get("path") or "")
    )
    if not source_acceptance.get("path") or not source_acceptance_path.exists():
        raise RichDataError(
            "alignment confirmation has no readable source acceptance snapshot"
        )
    if file_digest(source_acceptance_path) != source_acceptance.get("sha256"):
        raise RichDataError(
            "alignment confirmation source acceptance fingerprint mismatch"
        )
    acceptance_snapshot = load_json_record(
        source_acceptance_path, kind="a_share_rich_data_snapshot"
    )
    if (
        acceptance_snapshot.get("acceptance_status")
        != "automatic_checks_passed_pending_time_alignment"
        or acceptance_snapshot.get("provider") != alignment.get("provider")
        or acceptance_snapshot.get("frequency") != alignment.get("frequency")
    ):
        raise RichDataError(
            "alignment confirmation is not bound to a compatible accepted snapshot"
        )
    if spec_kind == "a_share_baostock_5m_factor_preregistration":
        chain = spec["source_chain"]
        expected_acceptance = chain["acceptance_snapshot"]
        expected_alignment = chain["alignment_confirmation"]
        if (
            resolve_record_path(expected_acceptance["path"]) != source_acceptance_path
            or expected_acceptance["sha256"] != file_digest(source_acceptance_path)
            or resolve_record_path(expected_alignment["path"]) != alignment_path
            or expected_alignment["sha256"] != file_digest(alignment_path)
        ):
            raise RichDataError(
                "BaoStock five-minute feature build is not bound to its frozen source chain"
            )
        if snapshot.get("dataset") == "baostock_five_minute_history":
            history_chain = snapshot.get("source_chain") or {}
            history_spec = history_chain.get("factor_spec") or {}
            history_acceptance = history_chain.get("acceptance_snapshot") or {}
            history_alignment = history_chain.get("alignment_confirmation") or {}
            if (
                history_spec.get("sha256") != file_digest(factor_spec_path)
                or history_acceptance.get("sha256") != expected_acceptance["sha256"]
                or history_alignment.get("sha256") != expected_alignment["sha256"]
            ):
                raise RichDataError(
                    "BaoStock five-minute history is not fingerprint-bound to the frozen "
                    "factor, acceptance, and alignment chain"
                )
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
            raise RichDataError(
                "minute snapshot file contains a mixed or unexpected provider"
            )
        symbols = frame["symbol"].dropna().astype(str).unique().tolist()
        if len(symbols) != 1:
            raise RichDataError(
                "each minute snapshot file must contain exactly one canonical symbol"
            )
        symbol = symbols[0]
        previous_closes.setdefault(symbol, previous_comparable_close_map(symbol))
        feature_frames.append(
            minute_feature_frame(
                frame,
                bar_label=str(alignment["bar_timestamp_label"]),
                previous_closes=previous_closes,
                frequency=frequency,
                feature_names=feature_names,
            )
        )
    if not feature_frames:
        raise RichDataError("minute snapshot contains no bars for feature construction")
    features = pd.concat(feature_frames, ignore_index=True).sort_values(
        ["trade_date", "symbol"], kind="stable"
    )
    eligible_rows = int(features["minute_feature_eligible"].sum())
    if eligible_rows == 0:
        raise RichDataError(
            "minute snapshot has no complete feature-eligible sessions; missing bars are not filled"
        )

    feature_version = "v1" if frequency == "1m" else "baostock_5m_v1"
    run_id = new_run_id(f"{snapshot['provider']}_{frequency}_features_v1")
    feature_path = (
        output.expanduser().resolve()
        if output is not None
        else DERIVED_ROOT
        / "minute_features"
        / feature_version
        / run_id
        / "features.parquet"
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
        "frequency": frequency,
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
            "incomplete_session_rows": int(
                (~features["complete_regular_session"]).sum()
            ),
            "calendar_start": pd.Timestamp(features["trade_date"].min())
            .date()
            .isoformat(),
            "calendar_end": pd.Timestamp(features["trade_date"].max())
            .date()
            .isoformat(),
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
    if provider == "baostock" and frequency != "5m":
        raise RichDataError(
            "the frozen BaoStock intraday contract supports only 5m bars"
        )
    require_provider(provider)
    validate_range(start, end, allow_large=allow_large, unit_count=len(codes))
    fetcher = MINUTE_FETCHERS[provider]
    rows_by_code: dict[str, pd.DataFrame] = {}
    acceptance_by_code: dict[str, dict[str, Any]] = {}
    for code in codes:
        raw = fetcher(code, start, end, frequency)
        rows_by_code[code] = (
            canonicalize_baostock_5m_bars(raw, code, start, end)
            if provider == "baostock"
            else canonicalize_minute_bars(raw, provider, code, start, end)
        )
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


def baostock_5m_acceptance_report(
    frame: pd.DataFrame, contract: dict[str, Any]
) -> dict[str, Any]:
    """Apply exact 48-bar end-label checks on top of raw daily reconciliation."""

    report = minute_acceptance_report(frame)
    acceptance = contract["formal_acceptance"]
    expected_times = expected_minute_times("end", "5m")
    observed_times = (
        tuple(pd.to_datetime(frame["datetime"]).dt.time) if not frame.empty else ()
    )
    exact = (
        len(frame) == int(acceptance["required_rows_per_symbol"])
        and observed_times == expected_times
    )
    report["baostock_5m_contract"] = {
        "required_rows": int(acceptance["required_rows_per_symbol"]),
        "observed_rows": int(len(frame)),
        "expected_bar_label": "end",
        "exact_timestamp_grid_passed": exact,
        "forward_return_fields_read": False,
    }
    if not exact:
        report["status"] = "automatic_checks_failed"
    return report


def sync_baostock_5m_acceptance() -> Path:
    """Persist the one fixed no-return BaoStock five-minute acceptance snapshot."""

    contract = load_baostock_5m_contract()
    acceptance = contract["formal_acceptance"]
    trade_date = dt.date.fromisoformat(str(acceptance["trade_date"]))
    codes = [str(code) for code in acceptance["symbols"]]
    require_provider("baostock")
    validate_range(trade_date, trade_date, allow_large=False, unit_count=len(codes))
    rows_by_code: dict[str, pd.DataFrame] = {}
    acceptance_by_code: dict[str, dict[str, Any]] = {}
    for code in codes:
        raw = fetch_baostock_minutes(code, trade_date, trade_date, "5m")
        frame = canonicalize_baostock_5m_bars(raw, code, trade_date, trade_date)
        rows_by_code[code] = frame
        acceptance_by_code[code] = baostock_5m_acceptance_report(frame, contract)
    return write_minute_snapshot(
        "baostock",
        "5m",
        trade_date,
        trade_date,
        rows_by_code,
        acceptance_by_code,
        data_contract={
            "path": manifest_path(DEFAULT_BAOSTOCK_5M_CONTRACT.resolve()),
            "sha256": file_digest(DEFAULT_BAOSTOCK_5M_CONTRACT),
            "kind": contract["kind"],
            "forward_return_fields_read": False,
        },
    )


def sync_baostock_5m_history(
    *,
    allow_large: bool = False,
    data_root: Path = DATA_ROOT,
    universe_path: Path = DEFAULT_FACTOR_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
    factor_spec_path: Path = DEFAULT_BAOSTOCK_5M_FACTOR_SPEC,
    workers: int = BAOSTOCK_5M_MAX_WORKERS,
) -> Path:
    """Run one locked full-history synchronization on the selected data root."""

    if not allow_large:
        raise RichDataError(
            "BaoStock full five-minute history requires explicit --allow-large"
        )
    resolved_data_root = data_root.expanduser().resolve()
    resolved_data_root.mkdir(parents=True, exist_ok=True)
    with RichDataProcessLock(resolved_data_root / ".a_share_baostock_5m.lock"):
        return _sync_baostock_5m_history_unlocked(
            allow_large=allow_large,
            data_root=resolved_data_root,
            universe_path=universe_path,
            calendar_path=calendar_path,
            factor_spec_path=factor_spec_path,
            workers=workers,
        )


def _sync_baostock_5m_history_unlocked(
    *,
    allow_large: bool = False,
    data_root: Path = DATA_ROOT,
    universe_path: Path = DEFAULT_FACTOR_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
    factor_spec_path: Path = DEFAULT_BAOSTOCK_5M_FACTOR_SPEC,
    workers: int = BAOSTOCK_5M_MAX_WORKERS,
) -> Path:
    """Store the frozen 2020--2025 PIT-universe BaoStock five-minute history."""

    if not allow_large:
        raise RichDataError(
            "BaoStock full five-minute history requires explicit --allow-large"
        )
    if not 1 <= workers <= BAOSTOCK_5M_MAX_WORKERS:
        raise RichDataError(
            f"BaoStock five-minute workers must be between 1 and {BAOSTOCK_5M_MAX_WORKERS}"
        )
    restoration_path, restoration = load_baostock_5m_restoration_probe(data_root)
    preflight_path = write_baostock_5m_preflight(
        data_root=data_root,
        universe_path=universe_path,
        calendar_path=calendar_path,
        factor_spec_path=factor_spec_path,
    )
    preflight = load_json_record(preflight_path, kind="a_share_baostock_5m_preflight")
    if preflight.get("status") != "passed_before_network":
        raise RichDataError(
            "BaoStock full five-minute history stopped before any network request: "
            f"{preflight['data_root']} has {float(preflight['observed_free_gib']):.2f} GiB free; "
            "pass --data-root pointing to a volume with at least 10 GiB. "
            f"Audit: {preflight_path}"
        )
    source_chain = load_baostock_5m_source_chain(factor_spec_path)
    contract = source_chain["contract"]
    require_baostock_5m_runtime()
    bulk = contract["bulk_snapshot_contract"]
    start = dt.date.fromisoformat(str(bulk["development_start"]))
    end = dt.date.fromisoformat(str(bulk["development_end"]))
    intervals = load_factor_universe_intervals(universe_path)
    calendar = local_calendar_dates(start, end, calendar_path)
    if calendar.empty:
        raise RichDataError(
            "local calendar has no sessions in the BaoStock five-minute range"
        )
    storage_tasks = baostock_5m_partition_tasks(intervals, start, end)
    request_tasks = baostock_5m_request_tasks(intervals, start, end)
    if not storage_tasks or not request_tasks:
        raise RichDataError("factor universe has no BaoStock five-minute partitions")

    resolved_data_root = data_root.expanduser().resolve()
    resolved_data_root.mkdir(parents=True, exist_ok=True)
    storage_device = int(resolved_data_root.stat().st_dev)
    if storage_device != int(preflight["filesystem_device"]):
        raise RichDataError(
            "BaoStock five-minute target filesystem changed after preflight"
        )
    disk_before = shutil.disk_usage(resolved_data_root)
    if disk_before.free < BAOSTOCK_5M_MINIMUM_FREE_BYTES:
        raise RichDataError(
            "BaoStock full five-minute history requires at least 10 GiB free before any "
            f"network request; {resolved_data_root} has {disk_before.free / 1024**3:.2f} GiB. "
            "Pass --data-root pointing to a larger volume."
        )

    run_id = new_run_id("baostock_5m_history")
    parent = (
        resolved_data_root
        / "raw"
        / "a_share"
        / "rich"
        / "baostock"
        / "minutes"
        / "5m"
        / "snapshots"
    )
    run_root = parent / run_id
    temporary_root = parent / f".{run_id}.partial"
    runs_root = resolved_data_root / "metadata" / "rich_data" / "runs"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"BaoStock five-minute snapshot already exists: {run_id}")
    temporary_root.mkdir(parents=True)

    task_by_key = {(task[0], task[3]): task for task in storage_tasks}
    tasks_by_code: dict[str, list[tuple[str, str, str, int]]] = {}
    for task in storage_tasks:
        tasks_by_code.setdefault(task[0], []).append(task)
    expected_requests = set(request_tasks)
    received_requests: set[tuple[str, str, str]] = set()
    received_partitions: set[tuple[str, int]] = set()
    complete_counts: dict[str, int] = {}
    files: list[dict[str, Any]] = []
    total_rows = 0
    source_rows = 0
    zero_price_placeholder_rows = 0
    zero_price_placeholder_sessions = 0
    complete_sessions = 0
    incomplete_sessions = 0
    download_started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    download_started_monotonic = time.monotonic()
    try:
        for (
            code,
            request_start,
            request_end,
            request_frame,
        ) in download_baostock_5m_requests(request_tasks, workers):
            request_key = (str(code), str(request_start), str(request_end))
            if request_key not in expected_requests:
                raise RichDataError(
                    "BaoStock five-minute downloader returned an unexpected PIT request: "
                    f"{request_key}"
                )
            if request_key in received_requests:
                raise RichDataError(
                    "BaoStock five-minute downloader returned a duplicate PIT request: "
                    f"{request_key}"
                )
            request_partition_rows = 0
            for task, frame in split_baostock_5m_request_frame(
                request_frame, tasks_by_code[str(code)]
            ):
                year = task[3]
                key = (str(code), int(year))
                if key not in task_by_key:
                    raise RichDataError(
                        "BaoStock five-minute downloader produced an unexpected storage "
                        f"partition: {key}"
                    )
                if key in received_partitions:
                    raise RichDataError(
                        "BaoStock five-minute downloader produced a duplicate storage "
                        f"partition: {key}"
                    )
                complete_dates = validate_baostock_5m_partition(frame, task, calendar)
                frame_dates = (
                    set(pd.to_datetime(frame["datetime"]).dt.date.astype(str))
                    if not frame.empty
                    else set()
                )
                placeholder_dates = set(
                    str(value)
                    for value in frame.attrs.get(
                        "zero_price_placeholder_session_dates", []
                    )
                )
                observed_dates = len(frame_dates | placeholder_dates)
                partition_source_rows = int(frame.attrs.get("source_rows", len(frame)))
                partition_placeholder_rows = int(
                    frame.attrs.get("zero_price_placeholder_rows_excluded", 0)
                )
                for trade_date in complete_dates:
                    complete_counts[trade_date] = complete_counts.get(trade_date, 0) + 1
                complete_sessions += len(complete_dates)
                incomplete_sessions += observed_dates - len(complete_dates)
                relative = Path(qlib_symbol(code).lower()) / f"{year}.parquet"
                temporary_destination = temporary_root / relative
                final_destination = run_root / relative
                try:
                    current_device = int(resolved_data_root.stat().st_dev)
                except FileNotFoundError as exc:
                    raise RichDataError(
                        "BaoStock five-minute target volume disappeared during download"
                    ) from exc
                if current_device != storage_device:
                    raise RichDataError(
                        "BaoStock five-minute target filesystem changed during download"
                    )
                atomic_write_frame(frame, temporary_destination)
                request_partition_rows += int(len(frame))
                total_rows += int(len(frame))
                source_rows += partition_source_rows
                zero_price_placeholder_rows += partition_placeholder_rows
                zero_price_placeholder_sessions += len(placeholder_dates)
                files.append(
                    {
                        "code": str(code),
                        "symbol": qlib_symbol(code),
                        "year": int(year),
                        "requested_start": task[1],
                        "requested_end": task[2],
                        "path": manifest_path(final_destination),
                        "rows": int(len(frame)),
                        "source_rows": partition_source_rows,
                        "zero_price_placeholder_rows_excluded": partition_placeholder_rows,
                        "zero_price_placeholder_sessions": len(placeholder_dates),
                        "observed_sessions": observed_dates,
                        "complete_regular_sessions": int(len(complete_dates)),
                        "sha256": frame_digest(frame),
                    }
                )
                received_partitions.add(key)
            if request_partition_rows != len(request_frame):
                raise RichDataError(
                    f"BaoStock five-minute yearly split lost rows for {code}: "
                    f"{request_partition_rows} != {len(request_frame)}"
                )
            received_requests.add(request_key)
            if len(received_requests) == 1 or len(received_requests) % 5 == 0:
                elapsed = max(time.monotonic() - download_started_monotonic, 0.001)
                print(
                    json.dumps(
                        {
                            "status": "downloading_baostock_5m",
                            "provider_requests_completed": len(received_requests),
                            "provider_requests_total": len(request_tasks),
                            "storage_partitions_completed": len(received_partitions),
                            "storage_partitions_total": len(storage_tasks),
                            "rows_written": total_rows,
                            "elapsed_minutes": round(elapsed / 60.0, 2),
                            "provider_requests_per_minute": round(
                                len(received_requests) / elapsed * 60.0, 2
                            ),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
        missing_requests = sorted(expected_requests - received_requests)
        if missing_requests:
            raise RichDataError(
                f"BaoStock five-minute downloader omitted {len(missing_requests)} requests; "
                f"first missing request: {missing_requests[0]}"
            )
        missing_partitions = sorted(set(task_by_key) - received_partitions)
        if missing_partitions:
            raise RichDataError(
                f"BaoStock five-minute downloader omitted {len(missing_partitions)} storage "
                f"partitions; first missing partition: {missing_partitions[0]}"
            )
        coverage = baostock_5m_coverage_report(
            intervals, calendar, complete_counts, contract
        )
        disk_after_download = shutil.disk_usage(resolved_data_root)
        files.sort(key=lambda item: (item["symbol"], item["year"]))
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "baostock_five_minute_history",
            "provider": "baostock",
            "frequency": "5m",
            "prices": "raw_unadjusted",
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "download_started_at": download_started_at,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "run_id": run_id,
            "status": (
                "full_source_coverage_passed_pending_no_return_feature_materialization"
                if coverage["gate_passed_before_prices"]
                else "full_source_coverage_failed_stop_before_forward_returns"
            ),
            "data_root": str(resolved_data_root),
            "source_chain": {
                "data_contract": {
                    "path": manifest_path(DEFAULT_BAOSTOCK_5M_CONTRACT.resolve()),
                    "sha256": BAOSTOCK_5M_CONTRACT_SHA256,
                },
                "factor_spec": {
                    "path": manifest_path(factor_spec_path.expanduser().resolve()),
                    "sha256": BAOSTOCK_5M_FACTOR_SPEC_SHA256,
                },
                "acceptance_snapshot": {
                    "path": manifest_path(source_chain["acceptance_path"]),
                    "sha256": file_digest(source_chain["acceptance_path"]),
                    "run_id": source_chain["acceptance"].get("run_id"),
                },
                "alignment_confirmation": {
                    "path": manifest_path(source_chain["alignment_path"]),
                    "sha256": file_digest(source_chain["alignment_path"]),
                    "run_id": source_chain["alignment"].get("run_id"),
                },
                "suspension_placeholder_audit": {
                    "path": manifest_path(
                        DEFAULT_BAOSTOCK_5M_SUSPENSION_AUDIT.resolve()
                    ),
                    "sha256": BAOSTOCK_5M_SUSPENSION_AUDIT_SHA256,
                },
                "request_throttle_audit": {
                    "path": manifest_path(DEFAULT_BAOSTOCK_5M_THROTTLE_AUDIT.resolve()),
                    "sha256": BAOSTOCK_5M_THROTTLE_AUDIT_SHA256,
                },
            },
            "storage_preflight_record": {
                "path": manifest_path(preflight_path),
                "sha256": file_digest(preflight_path),
                "status": preflight["status"],
                "network_request_issued": preflight["network_request_issued"],
            },
            "restoration_probe": {
                "path": manifest_path(restoration_path),
                "sha256": file_digest(restoration_path),
                "status": restoration["status"],
                "created_at": restoration["created_at"],
            },
            "request_protocol": {
                "sdk_version": importlib.metadata.version("baostock"),
                "frequency": "5",
                "adjustflag": "3",
                "fields": contract["source"]["requested_fields"],
                "provider_request_unit": "one_clipped_pit_interval_per_instrument",
                "yearly_parquet_storage_partitions": True,
                "partition_retries": BAOSTOCK_5M_PARTITION_RETRIES,
                "blacklist_error_retried": False,
                "workers": workers,
                "provider_request_count": len(request_tasks),
                "storage_partition_count": len(storage_tasks),
                "credentials_required_or_stored": False,
            },
            "storage_preflight": {
                "minimum_free_bytes": BAOSTOCK_5M_MINIMUM_FREE_BYTES,
                "free_bytes_before_network": int(disk_before.free),
                "free_bytes_after_download": int(disk_after_download.free),
                "passed_before_network": True,
                "temporary_snapshot_deleted_on_failure": True,
            },
            "universe": {
                "path": manifest_path(universe_path.expanduser().resolve()),
                "sha256": file_digest(universe_path.expanduser().resolve()),
                "point_in_time_intervals": int(len(intervals)),
            },
            "calendar": {
                "path": manifest_path(calendar_path.expanduser().resolve()),
                "sha256": file_digest(calendar_path.expanduser().resolve()),
                "sessions": int(len(calendar)),
            },
            "rows": total_rows,
            "normalization_quality": {
                "source_rows": source_rows,
                "rows_written": total_rows,
                "zero_price_placeholder_rows_excluded": zero_price_placeholder_rows,
                "zero_price_placeholder_sessions": zero_price_placeholder_sessions,
            },
            "complete_regular_sessions": complete_sessions,
            "incomplete_observed_sessions": incomplete_sessions,
            "files": files,
            "coverage": coverage,
            "raw_minute_price_fields_stored": ["open", "high", "low", "close"],
            "daily_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = runs_root / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise


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
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare event snapshot already exists: {run_id}")
    files: list[dict[str, Any]] = []
    quality_totals = {
        "source_rows": 0,
        "exact_duplicate_rows": 0,
        "duplicate_event_key_rows": 0,
    }
    try:
        for trade_date in pd.bdate_range(start, end):
            date = trade_date.date()
            for dataset in datasets:
                source_frame = fetch_tushare_event(dataset, date)
                quality = tushare_event_quality(source_frame, dataset, date)
                for field in quality_totals:
                    quality_totals[field] += int(quality[field])
                frame = source_frame.copy()
                frame["provider"] = "tushare"
                frame["dataset"] = dataset
                frame["retrieved_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
                temporary_destination = (
                    temporary_root / dataset / f"{date.isoformat()}.parquet"
                )
                final_destination = run_root / dataset / f"{date.isoformat()}.parquet"
                atomic_write_frame(frame, temporary_destination)
                files.append(
                    {
                        "dataset": dataset,
                        "trade_date": date.isoformat(),
                        "path": manifest_path(final_destination),
                        "rows": int(len(frame)),
                        "sha256": frame_digest(frame),
                        "minimum_permission_points": TUSHARE_EVENT_PERMISSION_POINTS[
                            dataset
                        ],
                        "quality": quality,
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
            "requested_datasets": datasets,
            "files": files,
            "source_quality": {
                **quality_totals,
                "raw_rows_preserved_without_deduplication": True,
            },
            "acceptance_status": "pending_event_time_alignment_and_canonicalization",
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        run_manifest_path = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, run_manifest_path)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return run_manifest_path
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def sync_tushare_northbound_top10_acceptance() -> Path:
    """Run the frozen one-session, two-market no-return entitlement check."""

    require_provider("tushare")
    contract = load_tushare_northbound_top10_contract()
    acceptance = contract["acceptance_protocol"]
    trade_date = dt.date.fromisoformat(acceptance["fixed_completed_session"])
    run_id = new_run_id("tushare_northbound_top10_acceptance")
    run_root = RAW_ROOT / "tushare" / "northbound_top10" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare Northbound acceptance already exists: {run_id}")
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        frames: list[pd.DataFrame] = []
        market_quality: list[dict[str, Any]] = []
        for market_type in TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES:
            raw = fetch_tushare_northbound_top10(trade_date, market_type)
            normalized, quality = canonicalize_tushare_northbound_top10(
                raw,
                trade_date,
                trade_date,
                expected_market_type=market_type,
            )
            observed_ranks = sorted(normalized["rank"].astype(int).tolist())
            if observed_ranks != list(range(1, 11)):
                raise RichDataError(
                    "Tushare hsgt_top10 acceptance must contain ranks 1 through 10 for "
                    f"market_type={market_type}; observed={observed_ranks}"
                )
            frames.append(normalized)
            market_quality.append(
                {
                    "market_type": market_type,
                    **quality,
                    "observed_ranks": observed_ranks,
                }
            )
        combined = (
            pd.concat(frames, ignore_index=True)
            .sort_values(["trade_date", "market_type", "rank"], kind="stable")
            .reset_index(drop=True)
        )
        if combined.duplicated(["instrument", "trade_date"]).any():
            raise RichDataError(
                "Tushare hsgt_top10 acceptance contains duplicate instrument/date keys"
            )
        temporary_destination = temporary_root / "northbound_top10.parquet"
        final_destination = run_root / "northbound_top10.parquet"
        atomic_write_frame(combined, temporary_destination)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_northbound_top10_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": trade_date.isoformat(),
            "requested_end": trade_date.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "hsgt_top10",
                "request_mode": "one completed local trading session and one market_type per call",
                "market_types": list(TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES),
                "fields": list(TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS),
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "files": [
                {
                    "path": manifest_path(final_destination),
                    "rows": int(len(combined)),
                    "sha256": frame_digest(combined),
                }
            ],
            "source_quality": {
                "market_requests": market_quality,
                "rows_written": int(len(combined)),
                "unique_instruments": int(combined["instrument"].nunique()),
                "duplicate_event_key_rows": int(
                    combined.duplicated(["instrument", "trade_date"]).sum()
                ),
                "factor_min": float(
                    combined["tushare_northbound_top10_net_buy_share"].min()
                ),
                "factor_max": float(
                    combined["tushare_northbound_top10_net_buy_share"].max()
                ),
            },
            "acceptance_status": "accepted_entitlement_and_formula_pending_full_history",
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_northbound_top10_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": trade_date.isoformat(),
            "requested_end": trade_date.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT),
            },
            "source_request": {
                "api": "hsgt_top10",
                "market_types": list(TUSHARE_NORTHBOUND_TOP10_MARKET_TYPES),
                "fields": list(TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS),
                "credentials_logged_or_stored": False,
            },
            "files": [],
            "acceptance_status": "entitlement_or_schema_rejected_stop_before_full_history",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{exc}; rejection_record={failure_path}") from exc


def sync_tushare_top_inst_acceptance() -> Path:
    """Run the single frozen no-return institution-seat acceptance request."""

    contract = load_tushare_top_inst_contract()
    prior_records = tushare_top_inst_acceptance_records()
    if prior_records:
        raise RichDataError(
            "Tushare top_inst acceptance is one-shot and was already consumed: "
            + ", ".join(str(path) for path in prior_records)
        )
    top_list = load_tushare_top_inst_top_list_context(contract)
    require_provider("tushare")
    acceptance = contract["acceptance_protocol"]
    trade_date = dt.date.fromisoformat(acceptance["fixed_completed_session"])
    validate_range(trade_date, trade_date, allow_large=False)
    run_id = new_run_id("tushare_top_inst_acceptance")
    run_root = RAW_ROOT / "tushare" / "top_inst" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare top_inst acceptance already exists: {run_id}")
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    provider_call_issued = False
    try:
        provider_call_issued = True
        raw = fetch_tushare_top_inst(trade_date)
        minimum_raw = int(acceptance["minimum_raw_institution_rows"])
        if len(raw) < minimum_raw:
            raise RichDataError(
                "Tushare top_inst acceptance returned too few institution-seat rows: "
                f"{len(raw)} < {minimum_raw}"
            )
        maximum_rows = int(
            contract["source_selection"]["provider_documented_maximum_rows_per_call"]
        )
        if len(raw) >= maximum_rows:
            raise RichDataError(
                "Tushare top_inst acceptance reached the possible truncation ceiling: "
                f"{len(raw)} >= {maximum_rows}"
            )
        normalized, quality = canonicalize_tushare_top_inst(raw, trade_date, trade_date)
        minimum_aggregated = int(acceptance["minimum_aggregated_stock_rows"])
        if len(normalized) < minimum_aggregated:
            raise RichDataError(
                "Tushare top_inst acceptance retained too few positive-activity stocks: "
                f"{len(normalized)} < {minimum_aggregated}"
            )
        observed_instruments = frozenset(normalized["instrument"].astype(str))
        absent_from_top_list = sorted(observed_instruments - top_list["instruments"])
        if absent_from_top_list:
            raise RichDataError(
                "Tushare top_inst stocks are absent from the accepted same-date top_list: "
                + ", ".join(absent_from_top_list)
            )
        temporary_destination = temporary_root / "top_inst.parquet"
        final_destination = run_root / "top_inst.parquet"
        atomic_write_frame(normalized, temporary_destination)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_top_inst_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": trade_date.isoformat(),
            "requested_end": trade_date.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_TOP_INST_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_TOP_INST_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "top_inst",
                "request_mode": "one completed local trading session per call",
                "provider_calls_issued": 1,
                "fields": list(TUSHARE_TOP_INST_RAW_FIELDS),
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "accepted_top_list_evidence": {
                "manifest_path": manifest_path(top_list["manifest_path"]),
                "manifest_sha256": top_list["manifest_sha256"],
                "frame_path": manifest_path(top_list["frame_path"]),
                "frame_content_sha256": top_list["frame_sha256"],
                "raw_rows": top_list["frame_rows"],
                "exact_duplicate_rows_preserved": top_list[
                    "exact_duplicate_rows_preserved"
                ],
                "unsupported_security_rows_excluded": top_list[
                    "unsupported_security_rows_excluded"
                ],
                "all_top_inst_stocks_present": True,
            },
            "files": [
                {
                    "path": manifest_path(final_destination),
                    "rows": int(len(normalized)),
                    "sha256": frame_digest(normalized),
                }
            ],
            "source_quality": {
                **quality,
                "unique_instruments": int(normalized["instrument"].nunique()),
                "factor_min": float(normalized["tushare_top_inst_net_buy_share"].min()),
                "factor_max": float(normalized["tushare_top_inst_net_buy_share"].max()),
                "duplicate_institution_seat_keys": 0,
                "provider_net_buy_used_only_for_integrity_reconciliation": True,
            },
            "availability_policy": {
                "documented_after_close_time": "20:00 Asia/Shanghai",
                "same_session_trade_allowed": False,
                "eligible_entry": "following local session open",
                "maximum_event_age_days": 0,
                "forward_fill_allowed": False,
            },
            "acceptance_status": (
                "accepted_entitlement_schema_formula_and_top_list_concordance_"
                "pending_full_history_protocol"
            ),
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        error = safe_exception_text(exc)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_top_inst_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": trade_date.isoformat(),
            "requested_end": trade_date.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_TOP_INST_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_TOP_INST_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "top_inst",
                "request_mode": "one completed local trading session per call",
                "provider_calls_issued": int(provider_call_issued),
                "fields": list(TUSHARE_TOP_INST_RAW_FIELDS),
                "credentials_logged_or_stored": False,
            },
            "accepted_top_list_evidence": {
                "manifest_path": manifest_path(top_list["manifest_path"]),
                "manifest_sha256": top_list["manifest_sha256"],
                "frame_path": manifest_path(top_list["frame_path"]),
                "frame_content_sha256": top_list["frame_sha256"],
                "unsupported_security_rows_excluded": top_list[
                    "unsupported_security_rows_excluded"
                ],
            },
            "files": [],
            "acceptance_status": "rejected_stop_before_full_history_or_returns",
            "error_type": type(exc).__name__,
            "error": error,
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{error}; rejection_record={failure_path}") from exc


def sync_tushare_top10_float_concentration_acceptance() -> Path:
    """Run the frozen three-call, no-return ownership acceptance exactly once."""

    contract = load_tushare_top10_float_concentration_contract()
    prior_records = tushare_top10_float_concentration_acceptance_records()
    if prior_records:
        raise RichDataError(
            "Tushare top-ten float concentration acceptance is one-shot and was "
            "already consumed: " + ", ".join(str(path) for path in prior_records)
        )
    context = validate_tushare_top10_float_local_context(contract)
    require_provider("tushare")
    acceptance = contract["acceptance_protocol"]
    symbols = tuple(str(value) for value in acceptance["fixed_symbols"])
    report_start = dt.datetime.strptime(
        str(acceptance["fixed_report_period_start"]), "%Y%m%d"
    ).date()
    report_end = dt.datetime.strptime(
        str(acceptance["fixed_report_period_end"]), "%Y%m%d"
    ).date()
    latest_announcement = dt.datetime.strptime(
        str(acceptance["latest_allowed_announcement_date"]), "%Y%m%d"
    ).date()
    run_id = new_run_id("tushare_top10_float_concentration_acceptance")
    run_root = (
        RAW_ROOT / "tushare" / "top10_float_concentration" / "acceptance" / run_id
    )
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(
            f"Tushare top-ten float concentration acceptance already exists: {run_id}"
        )
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    provider_calls_issued = 0
    source_rows_by_symbol: dict[str, int] = {}
    try:
        raw_by_symbol: dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            provider_calls_issued += 1
            raw = fetch_tushare_top10_float_holders(
                symbol,
                report_period_start=report_start,
                report_period_end=report_end,
            )
            raw_by_symbol[symbol] = raw
            source_rows_by_symbol[symbol] = int(len(raw))
        if provider_calls_issued != int(acceptance["provider_calls"]):
            raise RichDataError(
                "Tushare top10_floatholders acceptance did not issue exactly the "
                "frozen three requests"
            )

        source_frames: list[pd.DataFrame] = []
        factor_frames: list[pd.DataFrame] = []
        quality_by_symbol: dict[str, dict[str, int]] = {}
        minimum_groups = int(acceptance["minimum_complete_report_groups_per_symbol"])
        minimum_pairs = int(
            acceptance["minimum_factor_ready_consecutive_pairs_per_symbol"]
        )
        for symbol in symbols:
            raw = raw_by_symbol[symbol]
            if raw.empty:
                raise RichDataError(
                    f"Tushare top10_floatholders acceptance returned no rows for {symbol}"
                )
            normalized_source, factors, quality = (
                canonicalize_tushare_top10_float_holders(
                    raw,
                    expected_ts_code=symbol,
                    report_period_start=report_start,
                    report_period_end=report_end,
                    latest_announcement_date=latest_announcement,
                )
            )
            if quality["complete_report_groups"] < minimum_groups:
                raise RichDataError(
                    "Tushare top10_floatholders acceptance has too few complete "
                    f"report groups for {symbol}: "
                    f"{quality['complete_report_groups']} < {minimum_groups}"
                )
            if quality["factor_ready_consecutive_pairs"] < minimum_pairs:
                raise RichDataError(
                    "Tushare top10_floatholders acceptance has no frozen "
                    f"consecutive-quarter factor pair for {symbol}"
                )
            source_frames.append(normalized_source)
            factor_frames.append(factors)
            quality_by_symbol[symbol] = quality

        normalized_source = (
            pd.concat(source_frames, ignore_index=True)
            .sort_values(
                [
                    "instrument",
                    "report_period",
                    "announcement_date",
                    "holder_name_sha256",
                ],
                kind="stable",
            )
            .reset_index(drop=True)
        )
        factors = (
            pd.concat(factor_frames, ignore_index=True)
            .sort_values(
                ["instrument", "report_period", "announcement_date"], kind="stable"
            )
            .reset_index(drop=True)
        )
        if normalized_source.columns.tolist() != list(
            TUSHARE_TOP10_FLOAT_SOURCE_COLUMNS
        ):
            raise RichDataError(
                "top-ten float acceptance source columns do not match the frozen schema"
            )
        if factors.columns.tolist() != list(TUSHARE_TOP10_FLOAT_FACTOR_COLUMNS):
            raise RichDataError(
                "top-ten float acceptance factor columns do not match the frozen schema"
            )
        if normalized_source.duplicated(
            [
                "announcement_date",
                "report_period",
                "instrument",
                "holder_name_sha256",
            ]
        ).any():
            raise RichDataError(
                "top-ten float acceptance contains a duplicate persisted holder key"
            )
        if factors.duplicated(
            ["instrument", "announcement_date", "report_period"]
        ).any():
            raise RichDataError(
                "top-ten float acceptance contains a duplicate factor key"
            )

        temporary_source = temporary_root / "holders_hashed.parquet"
        temporary_factors = temporary_root / "concentration_changes.parquet"
        final_source = run_root / "holders_hashed.parquet"
        final_factors = run_root / "concentration_changes.parquet"
        atomic_write_frame(normalized_source, temporary_source)
        atomic_write_frame(factors, temporary_factors)
        changes = factors["top10_float_concentration_change_pp"]
        concentrations = factors["top10_float_concentration_pct"]
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_top10_float_concentration_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": report_start.isoformat(),
            "requested_end": report_end.isoformat(),
            "data_contract": {
                "path": manifest_path(
                    DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT
                ),
                "sha256": file_digest(
                    DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT
                ),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "top10_floatholders",
                "request_mode": "one stock and one frozen report-period range per call",
                "symbols": list(symbols),
                "provider_calls_issued": provider_calls_issued,
                "fields": list(TUSHARE_TOP10_FLOAT_RAW_FIELDS),
                "source_rows_returned_by_symbol": source_rows_by_symbol,
                "forbidden_fields_requested_or_stored": [],
                "plaintext_holder_names_logged_or_stored": False,
                "credentials_logged_or_stored": False,
            },
            "local_no_return_context": context,
            "files": [
                {
                    "role": "normalized_source_with_hashed_holder_identity",
                    "path": manifest_path(final_source),
                    "rows": int(len(normalized_source)),
                    "sha256": frame_digest(normalized_source),
                },
                {
                    "role": "first_disclosed_consecutive_quarter_factor",
                    "path": manifest_path(final_factors),
                    "rows": int(len(factors)),
                    "sha256": frame_digest(factors),
                },
            ],
            "source_quality": {
                "by_symbol": quality_by_symbol,
                "input_rows": int(sum(source_rows_by_symbol.values())),
                "source_rows_written": int(len(normalized_source)),
                "unique_instruments": int(normalized_source["instrument"].nunique()),
                "factor_ready_consecutive_pairs": int(len(factors)),
                "factor_min": float(changes.min()),
                "factor_max": float(changes.max()),
                "concentration_min": float(concentrations.min()),
                "concentration_max": float(concentrations.max()),
                "duplicate_persisted_holder_keys": 0,
                "duplicate_factor_keys": 0,
                "plaintext_holder_names_persisted": False,
                "holder_identity_hash": "sha256_nfkc_trimmed_whitespace_collapsed_utf8",
            },
            "availability_policy": {
                "source_time_field": "ann_date",
                "eligible_entry": "first local session open strictly after ann_date",
                "same_announcement_session_trade_allowed": False,
                "maximum_event_age_calendar_days": 3,
                "forward_fill_beyond_event_age_allowed": False,
            },
            "acceptance_status": acceptance["success_status"],
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        error = safe_exception_text(exc)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_top10_float_concentration_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": report_start.isoformat(),
            "requested_end": report_end.isoformat(),
            "data_contract": {
                "path": manifest_path(
                    DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT
                ),
                "sha256": file_digest(
                    DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT
                ),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "api": "top10_floatholders",
                "request_mode": "one stock and one frozen report-period range per call",
                "symbols": list(symbols),
                "provider_calls_issued": provider_calls_issued,
                "fields": list(TUSHARE_TOP10_FLOAT_RAW_FIELDS),
                "source_rows_returned_by_symbol": source_rows_by_symbol,
                "plaintext_holder_names_logged_or_stored": False,
                "credentials_logged_or_stored": False,
            },
            "local_no_return_context": context,
            "files": [],
            "acceptance_status": (
                "rejected_stop_before_full_history_capacity_uniqueness_or_returns"
            ),
            "error_type": type(exc).__name__,
            "error": error,
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{error}; rejection_record={failure_path}") from exc


def sync_tushare_cash_conversion_acceptance() -> Path:
    """Run the frozen six-call, no-return accounting acceptance exactly once."""

    contract = load_tushare_cash_conversion_contract()
    prior_records = tushare_cash_conversion_acceptance_records()
    if prior_records:
        raise RichDataError(
            "Tushare cash-conversion acceptance is one-shot and was already "
            "consumed: " + ", ".join(str(path) for path in prior_records)
        )
    context = validate_tushare_cash_conversion_local_context(contract)
    require_provider("tushare")
    acceptance = contract["acceptance_protocol"]
    symbols = tuple(str(value) for value in acceptance["fixed_symbols"])
    endpoints = tuple(str(value) for value in acceptance["endpoints_per_symbol"])
    announcement_start = dt.datetime.strptime(
        str(acceptance["fixed_announcement_start"]), "%Y%m%d"
    ).date()
    announcement_end = dt.datetime.strptime(
        str(acceptance["fixed_announcement_end"]), "%Y%m%d"
    ).date()
    latest_actual = dt.datetime.strptime(
        str(acceptance["latest_allowed_actual_announcement_date"]), "%Y%m%d"
    ).date()
    row_ceiling = int(
        contract["source_selection"]["provider_documented_maximum_rows_per_call"]
    )
    run_id = new_run_id("tushare_cash_conversion_acceptance")
    run_root = RAW_ROOT / "tushare" / "cash_conversion" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare cash-conversion acceptance exists: {run_id}")
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    provider_calls_issued = 0
    source_rows_by_symbol_endpoint: dict[str, dict[str, int]] = {
        symbol: {} for symbol in symbols
    }
    quality_by_symbol: dict[str, dict[str, Any]] = {}
    try:
        raw_by_symbol_endpoint: dict[tuple[str, str], pd.DataFrame] = {}
        for symbol in symbols:
            for endpoint in endpoints:
                provider_calls_issued += 1
                raw = fetch_tushare_cash_conversion_statement(
                    endpoint,
                    symbol,
                    announcement_start=announcement_start,
                    announcement_end=announcement_end,
                )
                raw_by_symbol_endpoint[(symbol, endpoint)] = raw
                source_rows_by_symbol_endpoint[symbol][endpoint] = int(len(raw))
        if provider_calls_issued != int(acceptance["provider_calls"]):
            raise RichDataError(
                "Tushare cash-conversion acceptance did not issue exactly six calls"
            )

        factor_frames: list[pd.DataFrame] = []
        minimum_periods = int(acceptance["minimum_usable_joined_periods_per_symbol"])
        for symbol in symbols:
            endpoint_frames: dict[str, pd.DataFrame] = {}
            endpoint_quality: dict[str, dict[str, Any]] = {}
            for endpoint in endpoints:
                raw = raw_by_symbol_endpoint[(symbol, endpoint)]
                if raw.empty:
                    raise RichDataError(
                        f"Tushare {endpoint} acceptance returned no rows for {symbol}"
                    )
                if len(raw) >= row_ceiling:
                    raise RichDataError(
                        f"Tushare {endpoint} acceptance reached the documented "
                        f"{row_ceiling}-row ceiling for {symbol}"
                    )
                canonical, quality = canonicalize_tushare_cash_conversion_endpoint(
                    raw,
                    endpoint=endpoint,
                    expected_ts_code=symbol,
                    announcement_start=announcement_start,
                    announcement_end=announcement_end,
                    latest_actual_announcement_date=latest_actual,
                )
                endpoint_frames[endpoint] = canonical
                endpoint_quality[endpoint] = quality
            factors, join_quality = derive_tushare_cash_conversion(
                endpoint_frames["income"], endpoint_frames["cashflow"]
            )
            if len(factors) < minimum_periods:
                raise RichDataError(
                    "Tushare cash-conversion acceptance has too few usable joined "
                    f"periods for {symbol}: {len(factors)} < {minimum_periods}"
                )
            quality_by_symbol[symbol] = {
                "income": endpoint_quality["income"],
                "cashflow": endpoint_quality["cashflow"],
                "join": join_quality,
            }
            factor_frames.append(factors)

        factors = (
            pd.concat(factor_frames, ignore_index=True)
            .sort_values(
                ["instrument", "report_period", "announcement_date"], kind="stable"
            )
            .reset_index(drop=True)
        )
        if factors.columns.tolist() != list(TUSHARE_CASH_CONVERSION_COLUMNS):
            raise RichDataError(
                "cash-conversion acceptance columns do not match the frozen schema"
            )
        if factors.duplicated(
            ["instrument", "announcement_date", "report_period"]
        ).any():
            raise RichDataError(
                "cash-conversion acceptance contains duplicate factor event keys"
            )
        observed_instruments = set(factors["instrument"].astype(str))
        expected_instruments = {
            qlib_symbol(symbol.split(".", 1)[0]) for symbol in symbols
        }
        if observed_instruments != expected_instruments:
            raise RichDataError(
                "cash-conversion acceptance does not retain every frozen instrument"
            )

        temporary_factor = temporary_root / "operating_cash_conversion.parquet"
        final_factor = run_root / "operating_cash_conversion.parquet"
        atomic_write_frame(factors, temporary_factor)
        values = factors["tushare_operating_cash_conversion"]
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_cash_conversion_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": announcement_start.isoformat(),
            "requested_end": announcement_end.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "apis": list(endpoints),
                "request_mode": (
                    "one stock and one frozen announcement-date range per "
                    "endpoint call"
                ),
                "symbols": list(symbols),
                "provider_calls_issued": provider_calls_issued,
                "fields_by_endpoint": {
                    "income": list(TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS),
                    "cashflow": list(TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS),
                },
                "source_rows_returned_by_symbol_endpoint": (
                    source_rows_by_symbol_endpoint
                ),
                "provider_documented_row_ceiling_per_call": row_ceiling,
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "local_no_return_context": context,
            "files": [
                {
                    "role": "joined_point_in_time_cash_conversion_factor",
                    "path": manifest_path(final_factor),
                    "rows": int(len(factors)),
                    "sha256": frame_digest(factors),
                }
            ],
            "source_quality": {
                "by_symbol": quality_by_symbol,
                "input_rows": int(
                    sum(
                        sum(endpoint_rows.values())
                        for endpoint_rows in source_rows_by_symbol_endpoint.values()
                    )
                ),
                "usable_joined_periods": int(len(factors)),
                "unique_instruments": int(factors["instrument"].nunique()),
                "factor_min": float(values.min()),
                "factor_max": float(values.max()),
                "duplicate_factor_event_keys": 0,
                "raw_statement_frames_persisted": False,
                "update_flag_use": "manifest_counts_only_never_value_selection",
            },
            "availability_policy": {
                "source_time_fields": ["income.f_ann_date", "cashflow.f_ann_date"],
                "signal_source_date": "later accepted actual announcement date",
                "eligible_entry": (
                    "first local session open strictly after the later actual "
                    "announcement date"
                ),
                "same_announcement_session_trade_allowed": False,
                "maximum_event_age_calendar_days": 3,
                "forward_fill_beyond_event_age_allowed": False,
            },
            "acceptance_status": acceptance["success_status"],
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        error = safe_exception_text(exc)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_cash_conversion_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": announcement_start.isoformat(),
            "requested_end": announcement_end.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "apis": list(endpoints),
                "request_mode": (
                    "one stock and one frozen announcement-date range per "
                    "endpoint call"
                ),
                "symbols": list(symbols),
                "provider_calls_issued": provider_calls_issued,
                "fields_by_endpoint": {
                    "income": list(TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS),
                    "cashflow": list(TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS),
                },
                "source_rows_returned_by_symbol_endpoint": (
                    source_rows_by_symbol_endpoint
                ),
                "provider_documented_row_ceiling_per_call": row_ceiling,
                "forbidden_fields_requested_or_stored": [],
                "raw_statement_frames_persisted": False,
                "credentials_logged_or_stored": False,
            },
            "local_no_return_context": context,
            "observed_quality_before_rejection": quality_by_symbol,
            "files": [],
            "acceptance_status": (
                "rejected_stop_before_full_history_capacity_uniqueness_or_returns"
            ),
            "error_type": type(exc).__name__,
            "error": error,
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{error}; rejection_record={failure_path}") from exc


def sync_tushare_daily_pb_acceptance(
    universe_path: Path = DEFAULT_BUYABLE_UNIVERSE,
) -> Path:
    """Run the frozen one-session daily PB entitlement and coverage check."""

    require_provider("tushare")
    contract = load_tushare_daily_pb_contract()
    acceptance = contract["acceptance_protocol"]
    trade_date = dt.date.fromisoformat(acceptance["fixed_completed_session"])
    run_id = new_run_id("tushare_daily_pb_acceptance")
    run_root = RAW_ROOT / "tushare" / "daily_pb" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare daily PB acceptance already exists: {run_id}")
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        raw = fetch_tushare_daily_pb(trade_date)
        if len(raw) < int(acceptance["minimum_all_market_source_rows"]):
            raise RichDataError(
                "Tushare daily_basic PB acceptance returned too few all-market rows: "
                f"{len(raw)} < {acceptance['minimum_all_market_source_rows']}"
            )
        row_ceiling = int(
            contract["snapshot_contract"]["partition_policy"][
                "provider_documented_maximum_rows_per_call"
            ]
        )
        if len(raw) >= row_ceiling:
            raise RichDataError(
                "Tushare daily_basic PB acceptance reached the provider row ceiling; "
                "the all-market response may be truncated"
            )
        normalized, quality = canonicalize_tushare_daily_pb(raw, trade_date, trade_date)
        intervals = load_factor_universe_intervals(universe_path)
        session = pd.Timestamp(trade_date)
        active_rows = intervals[
            intervals["start_date"].le(session) & intervals["end_date"].ge(session)
        ]
        active_instruments = set(active_rows["instrument"].astype(str))
        if not active_instruments:
            raise RichDataError(
                "buyable holding universe has no active acceptance-date names"
            )
        in_universe = normalized["instrument"].isin(active_instruments)
        outside_universe = int((~in_universe).sum())
        accepted = normalized.loc[in_universe].reset_index(drop=True)
        observed_names = int(accepted["instrument"].nunique())
        expected_names = int(len(active_instruments))
        coverage = observed_names / expected_names
        minimum_coverage = float(
            acceptance["minimum_positive_pb_holding_universe_coverage"]
        )
        if coverage < minimum_coverage:
            raise RichDataError(
                "Tushare daily_basic PB acceptance positive-PB holding coverage failed: "
                f"{coverage:.6f} < {minimum_coverage:.6f}"
            )
        temporary_destination = temporary_root / "daily_pb.parquet"
        final_destination = run_root / "daily_pb.parquet"
        atomic_write_frame(accepted, temporary_destination)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_daily_pb_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": trade_date.isoformat(),
            "requested_end": trade_date.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "point_in_time_holding_universe": {
                "path": manifest_path(universe_path.expanduser().resolve()),
                "sha256": file_digest(universe_path.expanduser().resolve()),
                "active_names": expected_names,
            },
            "source_request": {
                "api": "daily_basic",
                "request_mode": "one completed local trading session per call",
                "fields": list(TUSHARE_DAILY_PB_RAW_FIELDS),
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "files": [
                {
                    "path": manifest_path(final_destination),
                    "rows": int(len(accepted)),
                    "sha256": frame_digest(accepted),
                }
            ],
            "source_quality": {
                **quality,
                "outside_point_in_time_holding_universe_rows_excluded": outside_universe,
                "expected_active_holding_names": expected_names,
                "positive_pb_holding_names": observed_names,
                "positive_pb_holding_coverage": coverage,
                "duplicate_event_key_rows": int(
                    accepted.duplicated(["instrument", "trade_date"]).sum()
                ),
                "book_to_market_min": float(
                    accepted["tushare_positive_book_to_market"].min()
                ),
                "book_to_market_max": float(
                    accepted["tushare_positive_book_to_market"].max()
                ),
            },
            "acceptance_status": "accepted_entitlement_formula_and_current_coverage_pending_full_history",
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_daily_pb_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "requested_start": trade_date.isoformat(),
            "requested_end": trade_date.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
            },
            "source_request": {
                "api": "daily_basic",
                "fields": list(TUSHARE_DAILY_PB_RAW_FIELDS),
                "credentials_logged_or_stored": False,
            },
            "files": [],
            "acceptance_status": "entitlement_schema_or_current_coverage_rejected_stop_before_full_history",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{exc}; rejection_record={failure_path}") from exc


def sync_tushare_sw_industry_breadth_acceptance() -> Path:
    """Run the frozen no-price SW2021 classification and membership probe."""

    require_provider("tushare")
    contract = load_tushare_sw_industry_breadth_contract()
    for link in (contract.get("local_context") or {}).values():
        source_path = resolve_record_path(str(link["path"]))
        if not source_path.exists() or file_digest(source_path) != link["sha256"]:
            raise RichDataError(
                f"Tushare SW industry-breadth local context changed: {link['path']}"
            )
    acceptance = contract["acceptance_protocol"]
    representative_l1 = str(acceptance["representative_l1_code"])
    run_id = new_run_id("tushare_sw2021_l1_acceptance")
    run_root = RAW_ROOT / "tushare" / "sw2021_l1" / "acceptance" / run_id
    temporary_root = run_root.parent / f".{run_id}.tmp"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"Tushare SW2021 L1 acceptance already exists: {run_id}")
    retrieved_at = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        raw_classification = fetch_tushare_sw_classification()
        classification = canonicalize_tushare_sw_classification(raw_classification)
        minimum_classification = int(acceptance["minimum_classification_rows"])
        maximum_classification = int(acceptance["maximum_classification_rows"])
        if not minimum_classification <= len(classification) <= maximum_classification:
            raise RichDataError(
                "Tushare SW2021 L1 classification row count is outside the frozen range: "
                f"{len(classification)} not in [{minimum_classification}, "
                f"{maximum_classification}]"
            )
        if representative_l1 not in set(classification["index_code"].astype(str)):
            raise RichDataError(
                f"Tushare SW2021 classification lacks representative {representative_l1}"
            )

        provider_ceiling = int(
            contract["source_selection"]["provider_documented_maximum_rows_per_call"]
        )
        member_frames: list[pd.DataFrame] = []
        member_quality: list[dict[str, Any]] = []
        for is_new in contract["source"]["membership_is_new_values"]:
            raw_members = fetch_tushare_sw_members(representative_l1, str(is_new))
            if len(raw_members) >= provider_ceiling:
                raise RichDataError(
                    "Tushare SW membership acceptance reached the provider row ceiling: "
                    f"l1_code={representative_l1} is_new={is_new} rows={len(raw_members)}"
                )
            members, quality = canonicalize_tushare_sw_members(
                raw_members,
                expected_l1_code=representative_l1,
                expected_is_new=str(is_new),
            )
            minimum_key = (
                "minimum_current_representative_members"
                if is_new == "Y"
                else "minimum_historical_representative_members"
            )
            minimum_rows = int(acceptance[minimum_key])
            if len(members) < minimum_rows:
                raise RichDataError(
                    "Tushare SW membership acceptance returned too few rows: "
                    f"is_new={is_new} {len(members)} < {minimum_rows}"
                )
            member_frames.append(members)
            member_quality.append({"is_new": is_new, **quality})
        membership = (
            pd.concat(member_frames, ignore_index=True)
            .sort_values(
                ["l1_code", "l2_code", "l3_code", "instrument", "in_date", "is_new"],
                kind="stable",
            )
            .reset_index(drop=True)
        )
        duplicate_key = list(contract["full_snapshot_contract"]["duplicate_event_key"])
        if membership.duplicated(duplicate_key).any():
            raise RichDataError(
                "Tushare SW membership acceptance contains duplicate canonical intervals"
            )

        temporary_classification = temporary_root / "classification.parquet"
        temporary_membership = temporary_root / "membership.parquet"
        final_classification = run_root / "classification.parquet"
        final_membership = run_root / "membership.parquet"
        atomic_write_frame(classification, temporary_classification)
        atomic_write_frame(membership, temporary_membership)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_sw2021_l1_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_request": {
                "classification_api": "index_classify",
                "classification_parameters": contract["source"][
                    "classification_parameters"
                ],
                "classification_fields": list(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS),
                "membership_api": "index_member_all",
                "representative_l1_code": representative_l1,
                "membership_is_new_values": list(
                    contract["source"]["membership_is_new_values"]
                ),
                "membership_fields": list(TUSHARE_SW_MEMBERSHIP_RAW_FIELDS),
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "files": [
                {
                    "dataset": "classification",
                    "path": manifest_path(final_classification),
                    "rows": int(len(classification)),
                    "sha256": frame_digest(classification),
                },
                {
                    "dataset": "membership",
                    "path": manifest_path(final_membership),
                    "rows": int(len(membership)),
                    "sha256": frame_digest(membership),
                },
            ],
            "source_quality": {
                "classification_rows": int(len(classification)),
                "classification_codes": classification["index_code"]
                .astype(str)
                .tolist(),
                "classification_duplicate_codes": int(
                    classification["index_code"].duplicated().sum()
                ),
                "membership_requests": member_quality,
                "membership_rows": int(len(membership)),
                "membership_unique_instruments": int(
                    membership["instrument"].nunique()
                ),
                "membership_duplicate_interval_rows": int(
                    membership.duplicated(duplicate_key).sum()
                ),
                "minimum_in_date": membership["in_date"].min().date().isoformat(),
                "maximum_dated_out_date": membership["out_date"]
                .max()
                .date()
                .isoformat(),
            },
            "acceptance_status": (
                "accepted_entitlement_schema_and_point_in_time_intervals_"
                "pending_full_membership_snapshot"
            ),
            "price_fields_loaded": [],
            "factor_values_constructed": False,
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception as exc:
        shutil.rmtree(temporary_root, ignore_errors=True)
        failure = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "tushare_sw2021_l1_acceptance",
            "provider": "tushare",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "data_contract": {
                "path": manifest_path(DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT),
                "sha256": file_digest(DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT),
            },
            "source_request": {
                "classification_api": "index_classify",
                "membership_api": "index_member_all",
                "representative_l1_code": representative_l1,
                "classification_fields": list(TUSHARE_SW_CLASSIFICATION_RAW_FIELDS),
                "membership_fields": list(TUSHARE_SW_MEMBERSHIP_RAW_FIELDS),
                "credentials_logged_or_stored": False,
            },
            "files": [],
            "acceptance_status": (
                "entitlement_schema_or_interval_rejected_stop_before_full_membership"
            ),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "price_fields_loaded": [],
            "factor_values_constructed": False,
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        failure_path = RUNS_ROOT / f"{run_id}.json"
        atomic_write_json(failure, failure_path)
        raise RichDataError(f"{exc}; rejection_record={failure_path}") from exc


def _fetch_tushare_sw_members_with_policy(
    l1_code: str,
    is_new: str,
    *,
    minimum_interval: float,
    maximum_attempts: int,
    retry_backoffs: list[float],
    last_request_started: list[float | None],
) -> pd.DataFrame:
    """Apply the frozen sequential throttle and bounded retry policy to SW rows."""

    for attempt in range(maximum_attempts):
        previous = last_request_started[0]
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0.0:
                time.sleep(remaining)
        last_request_started[0] = time.monotonic()
        try:
            return fetch_tushare_sw_members(l1_code, is_new)
        except RichDataError:
            if attempt + 1 >= maximum_attempts:
                raise
            time.sleep(retry_backoffs[attempt])
    raise AssertionError("unreachable Tushare SW membership retry state")


def sync_tushare_sw_industry_membership(*, allow_large: bool = False) -> Path:
    """Store the frozen 31-code by two-state SW2021 membership snapshot."""

    if not allow_large:
        raise RichDataError(
            "the frozen SW2021 membership snapshot requires --allow-large after "
            "reviewing the accepted 62-call preregistration"
        )
    with RichDataProcessLock(METADATA_ROOT / ".tushare_sw2021_l1_membership.lock"):
        source_chain = load_tushare_sw_industry_breadth_source_chain()
        require_provider("tushare")
        spec = source_chain["spec"]
        snapshot = spec["full_membership_snapshot"]
        contract = source_chain["contract"]
        classification_codes = [
            str(value) for value in snapshot["classification_codes"]
        ]
        is_new_values = [str(value) for value in snapshot["is_new_values"]]
        total_calls = len(classification_codes) * len(is_new_values)
        if total_calls != int(snapshot["expected_provider_calls"]):
            raise RichDataError("Tushare SW full-snapshot call count changed")

        run_id = new_run_id("tushare_sw2021_l1_membership")
        parent = RAW_ROOT / "tushare" / "sw2021_l1" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(
                f"Tushare SW membership snapshot already exists: {run_id}"
            )
        temporary_root.mkdir(parents=True)
        minimum_interval = float(snapshot["minimum_seconds_between_calls"])
        maximum_attempts = int(snapshot["maximum_attempts_per_call"])
        retry_backoffs = [float(value) for value in snapshot["retry_backoff_seconds"]]
        if len(retry_backoffs) != maximum_attempts - 1:
            raise RichDataError("Tushare SW retry policy is internally inconsistent")
        provider_ceiling = int(snapshot["provider_documented_maximum_rows_per_call"])
        last_request_started: list[float | None] = [None]
        frames: list[pd.DataFrame] = []
        request_audit: list[dict[str, Any]] = []
        completed_calls = 0
        current_l1_code: str | None = None
        current_is_new: str | None = None
        try:
            for l1_code in classification_codes:
                for is_new in is_new_values:
                    current_l1_code = l1_code
                    current_is_new = is_new
                    raw = _fetch_tushare_sw_members_with_policy(
                        l1_code,
                        is_new,
                        minimum_interval=minimum_interval,
                        maximum_attempts=maximum_attempts,
                        retry_backoffs=retry_backoffs,
                        last_request_started=last_request_started,
                    )
                    if len(raw) >= provider_ceiling:
                        raise RichDataError(
                            "Tushare SW membership reached the provider row ceiling; "
                            f"l1_code={l1_code} is_new={is_new} rows={len(raw)}"
                        )
                    normalized, quality = canonicalize_tushare_sw_members(
                        raw,
                        expected_l1_code=l1_code,
                        expected_is_new=is_new,
                    )
                    if not normalized.empty:
                        frames.append(normalized)
                    request_audit.append(
                        {
                            "l1_code": l1_code,
                            "is_new": is_new,
                            **quality,
                        }
                    )
                    completed_calls += 1
                    if completed_calls % 10 == 0 or completed_calls == total_calls:
                        print(
                            json.dumps(
                                {
                                    "dataset": "tushare_sw2021_l1_membership",
                                    "progress_calls": completed_calls,
                                    "total_calls": total_calls,
                                    "latest_l1_code": l1_code,
                                    "latest_is_new": is_new,
                                },
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
            if completed_calls != total_calls or len(request_audit) != total_calls:
                raise RichDataError(
                    "Tushare SW membership did not complete every frozen call"
                )
            if not frames:
                raise RichDataError(
                    "Tushare SW full membership snapshot returned no rows"
                )
            membership = (
                pd.concat(frames, ignore_index=True)
                .sort_values(
                    [
                        "l1_code",
                        "l2_code",
                        "l3_code",
                        "instrument",
                        "in_date",
                        "out_date",
                        "is_new",
                    ],
                    kind="stable",
                    na_position="last",
                )
                .reset_index(drop=True)
            )
            duplicate_key = list(
                contract["full_snapshot_contract"]["duplicate_event_key"]
            )
            if (
                tuple(membership.columns) != TUSHARE_SW_MEMBERSHIP_COLUMNS
                or membership.duplicated(duplicate_key).any()
                or not set(membership["l1_code"].astype(str)).issubset(
                    set(classification_codes)
                )
                or not set(membership["is_new"].astype(str)).issubset(
                    set(is_new_values)
                )
                or not membership["provider"].eq("tushare").all()
            ):
                raise RichDataError(
                    "Tushare SW full membership frame failed integrity checks"
                )
            temporary_frame = temporary_root / "membership.parquet"
            final_frame = run_root / "membership.parquet"
            atomic_write_frame(membership, temporary_frame)
            stored = pd.read_parquet(temporary_frame)
            if tuple(stored.columns) != TUSHARE_SW_MEMBERSHIP_COLUMNS or frame_digest(
                stored
            ) != frame_digest(membership):
                raise RichDataError(
                    "Tushare SW stored membership frame failed reread audit"
                )

            current_rows = int(membership["is_new"].eq("Y").sum())
            historical_rows = int(membership["is_new"].eq("N").sum())
            empty_requests = [
                {"l1_code": row["l1_code"], "is_new": row["is_new"]}
                for row in request_audit
                if int(row["rows_written"]) == 0
            ]
            unsupported_symbol_rows = int(
                sum(
                    int(row["unsupported_provider_symbol_rows_excluded"])
                    for row in request_audit
                )
            )
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "tushare_sw2021_l1_membership",
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "no_return_preregistration": {
                    "path": manifest_path(source_chain["spec_path"]),
                    "sha256": file_digest(source_chain["spec_path"]),
                    "preregistered_at": spec["preregistered_at"],
                },
                "symbol_normalization_repair": {
                    "path": manifest_path(source_chain["symbol_repair_path"]),
                    "sha256": file_digest(source_chain["symbol_repair_path"]),
                    "factor_formula_or_membership_interval_changed": False,
                },
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                    "manifest_path": manifest_path(source_chain["manifest_path"]),
                    "manifest_sha256": file_digest(source_chain["manifest_path"]),
                    "run_id": source_chain["manifest"].get("run_id"),
                    "classification_frame_sha256": frame_digest(
                        source_chain["classification"]
                    ),
                    "membership_frame_sha256": frame_digest(source_chain["membership"]),
                },
                "source_request": {
                    "api": "index_member_all",
                    "classification_codes": classification_codes,
                    "is_new_values": is_new_values,
                    "expected_provider_calls": total_calls,
                    "completed_provider_calls": completed_calls,
                    "request_mode": "sequential_one_l1_code_and_one_is_new_state_per_call",
                    "fields": list(TUSHARE_SW_MEMBERSHIP_RAW_FIELDS),
                    "forbidden_fields_requested_or_stored": [],
                    "credentials_logged_or_stored": False,
                    "minimum_seconds_between_calls": minimum_interval,
                    "maximum_attempts_per_call": maximum_attempts,
                },
                "files": [
                    {
                        "dataset": "membership",
                        "path": manifest_path(final_frame),
                        "rows": int(len(membership)),
                        "sha256": frame_digest(membership),
                    }
                ],
                "source_quality": {
                    "requests": request_audit,
                    "empty_requests": empty_requests,
                    "unsupported_provider_symbol_rows_excluded": (
                        unsupported_symbol_rows
                    ),
                    "membership_rows": int(len(membership)),
                    "current_membership_rows": current_rows,
                    "historical_membership_rows": historical_rows,
                    "unique_instruments": int(membership["instrument"].nunique()),
                    "l1_codes_with_rows": int(membership["l1_code"].nunique()),
                    "duplicate_interval_rows": int(
                        membership.duplicated(duplicate_key).sum()
                    ),
                    "minimum_in_date": membership["in_date"].min().date().isoformat(),
                    "maximum_dated_out_date": (
                        membership["out_date"].max().date().isoformat()
                        if membership["out_date"].notna().any()
                        else None
                    ),
                },
                "acceptance_status": snapshot["required_success_status"],
                "price_fields_loaded": [],
                "factor_values_constructed": False,
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            message = str(exc)
            if "row ceiling" in message:
                failure_code = "provider_row_ceiling_possible_truncation"
            elif "duplicate" in message:
                failure_code = "source_duplicate_interval"
            elif "fields outside" in message or "lacks requested fields" in message:
                failure_code = "source_schema_mismatch"
            elif "missing" in message or "interval" in message:
                failure_code = "source_interval_integrity_failure"
            else:
                failure_code = "provider_or_local_snapshot_failure"
            failure_path = RUNS_ROOT / f"{run_id}_source_failure.json"
            atomic_write_json(
                {
                    "schema_version": 1,
                    "kind": "a_share_rich_data_source_failure",
                    "dataset": "tushare_sw2021_l1_membership",
                    "provider": "tushare",
                    "run_id": run_id,
                    "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "failed_l1_code": current_l1_code,
                    "failed_is_new": current_is_new,
                    "completed_provider_calls_before_failure": completed_calls,
                    "total_planned_provider_calls": total_calls,
                    "failure_code": failure_code,
                    "partial_snapshot_deleted": not temporary_root.exists(),
                    "final_snapshot_published": run_root.exists(),
                    "data_contract": {
                        "path": manifest_path(
                            DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT
                        ),
                        "sha256": file_digest(
                            DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT
                        ),
                    },
                    "no_return_preregistration": {
                        "path": manifest_path(source_chain["spec_path"]),
                        "sha256": file_digest(source_chain["spec_path"]),
                    },
                    "symbol_normalization_repair": {
                        "path": manifest_path(source_chain["symbol_repair_path"]),
                        "sha256": file_digest(source_chain["symbol_repair_path"]),
                    },
                    "credentials_logged_or_stored": False,
                    "price_fields_loaded": [],
                    "factor_values_constructed": False,
                    "open_close_or_forward_return_fields_read": False,
                    "forward_return_fields_read": False,
                    "selection_or_promotion_allowed": False,
                },
                failure_path,
            )
            if isinstance(exc, RichDataError):
                raise RichDataError(
                    f"{message}; rejection_record={failure_path}"
                ) from exc
            raise


def load_tushare_moneyflow_acceptance() -> tuple[Path, dict[str, Any]]:
    """Verify the bound completed-session Tushare entitlement/schema probe."""

    contract = load_tushare_moneyflow_contract()
    acceptance = contract["acceptance_protocol"]
    path = resolve_record_path(acceptance["bound_manifest_path"])
    if file_digest(path) != acceptance["bound_manifest_sha256"]:
        raise RichDataError(
            "Tushare moneyflow acceptance manifest fingerprint mismatch"
        )
    manifest = load_json_record(path, kind="a_share_rich_data_snapshot")
    if (
        manifest.get("dataset") != "tushare_events"
        or manifest.get("provider") != "tushare"
        or manifest.get("requested_start") != "2026-07-13"
        or manifest.get("requested_end") != "2026-07-13"
        or "moneyflow" not in set(manifest.get("requested_datasets") or [])
        or manifest.get("forward_return_fields_read") is not False
        or manifest.get("selection_or_promotion_allowed") is not False
    ):
        raise RichDataError("Tushare moneyflow acceptance manifest identity mismatch")
    records = [
        item
        for item in manifest.get("files") or []
        if item.get("dataset") == "moneyflow"
    ]
    if len(records) != 1:
        raise RichDataError("Tushare acceptance must contain one moneyflow frame")
    record = records[0]
    quality = record.get("quality") or {}
    if (
        int(record.get("rows") or -1) != 5197
        or int(quality.get("missing_key_rows") or 0) != 0
        or int(quality.get("outside_requested_date_rows") or 0) != 0
        or int(quality.get("duplicate_event_key_rows") or 0) != 0
    ):
        raise RichDataError("Tushare moneyflow acceptance key audit failed")
    frame = load_snapshot_frame(record)
    normalized, _ = canonicalize_tushare_moneyflow(
        frame, dt.date(2026, 7, 13), dt.date(2026, 7, 13)
    )
    if normalized.empty or normalized["trade_date"].nunique() != 1:
        raise RichDataError("Tushare moneyflow acceptance formula audit failed")
    return path, manifest


def tushare_ts_code_from_qlib_instrument(instrument: str) -> str:
    """Convert one frozen SH/SZ Qlib instrument into a Tushare stock code."""

    value = str(instrument).strip().upper()
    if len(value) != 8 or value[:2] not in {"SH", "SZ"} or not value[2:].isdigit():
        raise RichDataError(f"invalid Qlib instrument for Tushare: {instrument}")
    return f"{value[2:]}.{value[:2]}"


def _fetch_tushare_cash_conversion_with_policy(
    endpoint: str,
    ts_code: str,
    announcement_start: dt.date,
    announcement_end: dt.date,
    *,
    minimum_interval: float,
    maximum_attempts: int,
    last_request_started: list[float | None],
) -> pd.DataFrame:
    """Apply the frozen sequential throttle and bounded endpoint retry policy."""

    retry_backoffs = (1.0, 2.0)
    for attempt in range(maximum_attempts):
        previous = last_request_started[0]
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0.0:
                time.sleep(remaining)
        last_request_started[0] = time.monotonic()
        try:
            return fetch_tushare_cash_conversion_statement(
                endpoint,
                ts_code,
                announcement_start=announcement_start,
                announcement_end=announcement_end,
            )
        except RichDataError:
            if attempt + 1 >= maximum_attempts:
                raise
            time.sleep(retry_backoffs[min(attempt, len(retry_backoffs) - 1)])
    raise AssertionError("unreachable Tushare cash-conversion retry state")


def sync_tushare_cash_conversion(
    *,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_BUYABLE_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
) -> Path:
    """Store the frozen 2019-2025 PIT cash-conversion snapshot without prices."""

    with RichDataProcessLock(METADATA_ROOT / ".tushare_cash_conversion.lock"):
        source_chain = load_tushare_cash_conversion_source_chain()
        contract = source_chain["contract"]
        context = validate_tushare_cash_conversion_local_context(contract)
        prior_full = tushare_cash_conversion_full_snapshot_records()
        if prior_full:
            raise RichDataError(
                "Tushare cash-conversion full snapshot already exists and cannot be "
                "repeated: " + ", ".join(str(path) for path in prior_full)
            )
        if not allow_large:
            raise RichDataError(
                "Tushare cash-conversion full snapshot requires --allow-large"
            )
        universe_path = universe_path.expanduser().resolve()
        calendar_path = calendar_path.expanduser().resolve()
        universe_context = contract["local_context"]["holding_universe"]
        calendar_context = contract["local_context"]["calendar"]
        if (
            universe_path != resolve_record_path(universe_context["path"])
            or file_digest(universe_path) != universe_context["sha256"]
            or calendar_path != resolve_record_path(calendar_context["path"])
            or file_digest(calendar_path) != calendar_context["sha256"]
        ):
            raise RichDataError(
                "cash-conversion full snapshot universe or calendar is not the "
                "frozen point-in-time source"
            )
        require_provider("tushare")

        snapshot = contract["full_snapshot_contract"]
        gates = contract["no_return_gates"]
        completeness = gates["source_completeness"]
        acceptance = contract["acceptance_protocol"]
        announcement_start = dt.datetime.strptime(
            str(snapshot["announcement_start"]), "%Y%m%d"
        ).date()
        announcement_end = dt.datetime.strptime(
            str(snapshot["announcement_end"]), "%Y%m%d"
        ).date()
        development_start = dt.date.fromisoformat(snapshot["development_signal_start"])
        development_end = dt.date.fromisoformat(snapshot["development_signal_end"])
        latest_actual = dt.datetime.strptime(
            str(acceptance["latest_allowed_actual_announcement_date"]), "%Y%m%d"
        ).date()
        all_intervals = load_factor_universe_intervals(universe_path)
        overlap = all_intervals["start_date"].le(pd.Timestamp(development_end)) & (
            all_intervals["end_date"].ge(pd.Timestamp(development_start))
        )
        intervals = (
            all_intervals.loc[overlap].copy().sort_values("instrument", kind="stable")
        )
        if intervals.empty:
            raise RichDataError(
                "cash-conversion holding universe has no instruments in 2019-2025"
            )
        calendar = local_calendar_dates(development_start, latest_actual, calendar_path)
        if calendar.empty or calendar[-1] < pd.Timestamp(development_end):
            raise RichDataError(
                "cash-conversion local calendar cannot map the frozen signal range"
            )
        endpoints = ("income", "cashflow")
        total_planned_calls = int(len(intervals) * len(endpoints))
        row_ceiling = int(snapshot["provider_documented_maximum_rows_per_call"])
        minimum_interval = float(snapshot["minimum_seconds_between_calls"])
        maximum_attempts = int(snapshot["maximum_attempts_per_symbol_endpoint"])

        run_id = new_run_id("tushare_cash_conversion_full")
        parent = RAW_ROOT / "tushare" / "cash_conversion" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(
                f"Tushare cash-conversion full snapshot already exists: {run_id}"
            )
        temporary_root.mkdir(parents=True)
        yearly_frames: dict[int, list[pd.DataFrame]] = {
            year: [] for year in range(development_start.year, development_end.year + 1)
        }
        endpoint_quality_totals: dict[str, dict[str, int]] = {
            endpoint: {
                "input_rows": 0,
                "non_target_company_rows_excluded": 0,
                "target_company_periods_observed": 0,
                "adjustment_periods_excluded": 0,
                "no_type_one_periods_excluded": 0,
                "missing_metric_periods_excluded": 0,
                "ambiguous_type_one_periods_excluded": 0,
                "semantic_duplicate_rows_collapsed": 0,
                "accepted_periods": 0,
            }
            for endpoint in endpoints
        }
        update_flag_totals: dict[str, dict[str, int]] = {
            endpoint: {} for endpoint in endpoints
        }
        join_quality_totals = {
            "income_accepted_periods": 0,
            "cashflow_accepted_periods": 0,
            "income_only_periods_excluded": 0,
            "cashflow_only_periods_excluded": 0,
            "joined_periods_before_metric_policy": 0,
            "nonpositive_income_periods_excluded": 0,
            "nonfinite_cashflow_periods_excluded": 0,
            "nonfinite_derived_periods_excluded": 0,
            "usable_joined_periods": 0,
        }
        source_rows_by_endpoint = {endpoint: 0 for endpoint in endpoints}
        empty_responses_by_endpoint = {endpoint: 0 for endpoint in endpoints}
        signal_quality = {
            "without_next_calendar_session_excluded": 0,
            "outside_development_signal_range_excluded": 0,
            "outside_point_in_time_holding_interval_excluded": 0,
            "rows_written": 0,
        }
        no_factor_instruments = 0
        no_factor_instrument_examples: list[str] = []
        completed_provider_calls = 0
        completed_instruments = 0
        last_request_started: list[float | None] = [None]
        current_instrument: str | None = None
        current_endpoint: str | None = None
        started = time.monotonic()
        try:
            for interval in intervals.itertuples(index=False):
                current_instrument = str(interval.instrument)
                ts_code = tushare_ts_code_from_qlib_instrument(current_instrument)
                endpoint_frames: dict[str, pd.DataFrame] = {}
                for endpoint in endpoints:
                    current_endpoint = endpoint
                    raw = _fetch_tushare_cash_conversion_with_policy(
                        endpoint,
                        ts_code,
                        announcement_start,
                        announcement_end,
                        minimum_interval=minimum_interval,
                        maximum_attempts=maximum_attempts,
                        last_request_started=last_request_started,
                    )
                    completed_provider_calls += 1
                    source_rows_by_endpoint[endpoint] += int(len(raw))
                    if raw.empty:
                        empty_responses_by_endpoint[endpoint] += 1
                    if len(raw) >= row_ceiling:
                        raise RichDataError(
                            f"Tushare {endpoint} {ts_code} reached the documented "
                            f"{row_ceiling}-row ceiling; response may be truncated"
                        )
                    canonical, quality = canonicalize_tushare_cash_conversion_endpoint(
                        raw,
                        endpoint=endpoint,
                        expected_ts_code=ts_code,
                        announcement_start=announcement_start,
                        announcement_end=announcement_end,
                        latest_actual_announcement_date=latest_actual,
                    )
                    endpoint_frames[endpoint] = canonical
                    for key in endpoint_quality_totals[endpoint]:
                        endpoint_quality_totals[endpoint][key] += int(
                            quality.get(key, 0)
                        )
                    for flag, count in (
                        quality.get("update_flag_counts") or {}
                    ).items():
                        update_flag_totals[endpoint][str(flag)] = update_flag_totals[
                            endpoint
                        ].get(str(flag), 0) + int(count)

                factors, join_quality = derive_tushare_cash_conversion(
                    endpoint_frames["income"], endpoint_frames["cashflow"]
                )
                for key in join_quality_totals:
                    join_quality_totals[key] += int(join_quality.get(key, 0))
                if not factors.empty:
                    announcement_dates = pd.DatetimeIndex(
                        pd.to_datetime(factors["announcement_date"]).dt.normalize()
                    )
                    positions = calendar.searchsorted(announcement_dates, side="right")
                    signal_sessions = pd.Series(
                        pd.NaT, index=factors.index, dtype="datetime64[ns]"
                    )
                    has_next = positions < len(calendar)
                    if has_next.any():
                        signal_sessions.loc[has_next] = calendar.take(
                            positions[has_next]
                        ).to_numpy()
                    signal_quality["without_next_calendar_session_excluded"] += int(
                        (~has_next).sum()
                    )
                    in_development = signal_sessions.between(
                        pd.Timestamp(development_start), pd.Timestamp(development_end)
                    )
                    signal_quality["outside_development_signal_range_excluded"] += int(
                        (has_next & ~in_development).sum()
                    )
                    in_interval = signal_sessions.between(
                        pd.Timestamp(interval.start_date),
                        pd.Timestamp(interval.end_date),
                    )
                    signal_quality[
                        "outside_point_in_time_holding_interval_excluded"
                    ] += int((has_next & in_development & ~in_interval).sum())
                    retained = has_next & in_development & in_interval
                    factors = factors.loc[retained].copy()
                    signal_sessions = signal_sessions.loc[retained]
                    if not factors.empty:
                        factors["_signal_year"] = signal_sessions.dt.year.astype(int)
                        for year, year_frame in factors.groupby(
                            "_signal_year", sort=True, observed=True
                        ):
                            stored = year_frame.drop(columns="_signal_year").loc[
                                :, list(TUSHARE_CASH_CONVERSION_COLUMNS)
                            ]
                            yearly_frames[int(year)].append(stored)
                            signal_quality["rows_written"] += int(len(stored))
                if factors.empty:
                    no_factor_instruments += 1
                    if len(no_factor_instrument_examples) < 20:
                        no_factor_instrument_examples.append(current_instrument)
                completed_instruments += 1
                if completed_instruments % 25 == 0 or completed_instruments == len(
                    intervals
                ):
                    elapsed = max(time.monotonic() - started, 0.001)
                    print(
                        json.dumps(
                            {
                                "dataset": "tushare_operating_cash_conversion",
                                "completed_instruments": completed_instruments,
                                "total_instruments": int(len(intervals)),
                                "completed_provider_calls": completed_provider_calls,
                                "total_provider_calls": total_planned_calls,
                                "factor_rows_retained": signal_quality["rows_written"],
                                "elapsed_minutes": round(elapsed / 60.0, 2),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )

            if completed_provider_calls != total_planned_calls:
                raise RichDataError(
                    "cash-conversion full snapshot omitted one or more frozen calls"
                )
            files: list[dict[str, Any]] = []
            duplicate_event_keys = 0
            total_rows = 0
            for year in sorted(yearly_frames):
                frames = yearly_frames[year]
                if not frames:
                    continue
                partition = (
                    pd.concat(frames, ignore_index=True)
                    .sort_values(
                        ["announcement_date", "instrument", "report_period"],
                        kind="stable",
                    )
                    .reset_index(drop=True)
                )
                if tuple(partition.columns) != TUSHARE_CASH_CONVERSION_COLUMNS:
                    raise RichDataError(
                        f"cash-conversion {year} partition columns changed"
                    )
                duplicates = int(
                    partition.duplicated(
                        ["instrument", "announcement_date", "report_period"]
                    ).sum()
                )
                duplicate_event_keys += duplicates
                if duplicates:
                    raise RichDataError(
                        f"cash-conversion {year} partition has duplicate event keys"
                    )
                destination = temporary_root / f"{year}.parquet"
                atomic_write_frame(partition, destination)
                total_rows += int(len(partition))
                files.append(
                    {
                        "signal_year": int(year),
                        "path": manifest_path(run_root / destination.name),
                        "rows": int(len(partition)),
                        "sha256": frame_digest(partition),
                    }
                )
            observed_years = len(files)
            source_gate_passed = bool(
                total_rows >= int(completeness["minimum_complete_joined_factor_events"])
                and observed_years >= int(completeness["minimum_observed_signal_years"])
                and duplicate_event_keys == 0
            )
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "tushare_operating_cash_conversion",
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": announcement_start.isoformat(),
                "requested_end": announcement_end.isoformat(),
                "development_signal_start": development_start.isoformat(),
                "development_signal_end": development_end.isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                    "manifest_path": manifest_path(source_chain["manifest_path"]),
                    "manifest_sha256": file_digest(source_chain["manifest_path"]),
                    "factor_frame_path": manifest_path(source_chain["frame_path"]),
                    "factor_frame_content_sha256": frame_digest(source_chain["frame"]),
                },
                "local_no_return_context": context,
                "point_in_time_holding_universe": {
                    "path": manifest_path(universe_path),
                    "sha256": file_digest(universe_path),
                    "all_intervals": int(len(all_intervals)),
                    "requested_overlap_intervals": int(len(intervals)),
                },
                "local_calendar": {
                    "path": manifest_path(calendar_path),
                    "sha256": file_digest(calendar_path),
                    "mapping_sessions": int(len(calendar)),
                },
                "source_request": {
                    "apis": list(endpoints),
                    "request_mode": (
                        "one ts_code over the full frozen announcement-date range "
                        "for each endpoint"
                    ),
                    "fields_by_endpoint": {
                        "income": list(TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS),
                        "cashflow": list(TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS),
                    },
                    "planned_instruments": int(len(intervals)),
                    "planned_provider_calls": total_planned_calls,
                    "completed_provider_calls": completed_provider_calls,
                    "minimum_seconds_between_calls": minimum_interval,
                    "maximum_attempts_per_symbol_endpoint": maximum_attempts,
                    "retry_backoff_seconds": [1.0, 2.0],
                    "provider_documented_row_ceiling_per_call": row_ceiling,
                    "source_rows_by_endpoint": source_rows_by_endpoint,
                    "empty_responses_by_endpoint": empty_responses_by_endpoint,
                    "forbidden_fields_requested_or_stored": [],
                    "raw_statement_frames_persisted": False,
                    "credentials_logged_or_stored": False,
                },
                "files": files,
                "normalization_quality": {
                    "by_endpoint": endpoint_quality_totals,
                    "update_flag_counts_by_endpoint": update_flag_totals,
                    "join": join_quality_totals,
                    "signal_and_universe": signal_quality,
                    "instruments_without_retained_factor": no_factor_instruments,
                    "instruments_without_retained_factor_examples": (
                        no_factor_instrument_examples
                    ),
                },
                "source_completeness": {
                    "complete_joined_factor_events": total_rows,
                    "minimum_required_events": int(
                        completeness["minimum_complete_joined_factor_events"]
                    ),
                    "observed_signal_years": observed_years,
                    "minimum_required_signal_years": int(
                        completeness["minimum_observed_signal_years"]
                    ),
                    "duplicate_factor_event_keys": duplicate_event_keys,
                    "gate_passed_before_prices": source_gate_passed,
                },
                "acceptance_status": (
                    "full_source_completeness_passed_pending_no_return_capacity_and_uniqueness"
                    if source_gate_passed
                    else "full_source_completeness_failed_stop_before_capacity_uniqueness_or_prices"
                ),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            message = safe_exception_text(exc)
            if "row ceiling" in message:
                failure_code = "provider_row_ceiling_possible_truncation"
            elif "fields outside" in message or "lacks requested fields" in message:
                failure_code = "source_schema_mismatch"
            elif "duplicate" in message:
                failure_code = "source_duplicate_key"
            elif "statement keys" in message:
                failure_code = "source_statement_key_failure"
            elif "unknown report" in message or "unknown company" in message:
                failure_code = "source_statement_type_failure"
            else:
                failure_code = "provider_or_local_snapshot_failure"
            failure_path = RUNS_ROOT / f"{run_id}_source_failure.json"
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_source_failure",
                "dataset": "tushare_operating_cash_conversion",
                "provider": "tushare",
                "run_id": run_id,
                "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": announcement_start.isoformat(),
                "requested_end": announcement_end.isoformat(),
                "failed_instrument": current_instrument,
                "failed_endpoint": current_endpoint,
                "completed_instruments_before_failure": completed_instruments,
                "completed_provider_calls_before_failure": completed_provider_calls,
                "total_planned_provider_calls": total_planned_calls,
                "failure_code": failure_code,
                "error": message,
                "partial_snapshot_deleted": not temporary_root.exists(),
                "final_snapshot_published": run_root.exists(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT),
                },
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                },
                "credentials_logged_or_stored": False,
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            atomic_write_json(failure, failure_path)
            if isinstance(exc, RichDataError):
                raise RichDataError(
                    f"{message}; rejection_record={failure_path}"
                ) from exc
            raise


def _fetch_tushare_moneyflow_with_policy(
    trade_date: dt.date,
    *,
    minimum_interval: float,
    maximum_attempts: int,
    retry_backoffs: list[float],
    last_request_started: list[float | None],
) -> pd.DataFrame:
    """Apply the frozen sequential throttle and bounded retry policy."""

    for attempt in range(maximum_attempts):
        previous = last_request_started[0]
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0.0:
                time.sleep(remaining)
        last_request_started[0] = time.monotonic()
        try:
            return fetch_tushare_moneyflow(trade_date)
        except RichDataError:
            if attempt + 1 >= maximum_attempts:
                raise
            time.sleep(retry_backoffs[attempt])
    raise AssertionError("unreachable Tushare retry state")


def sync_tushare_moneyflow(
    *,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_FACTOR_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
) -> Path:
    """Store the frozen 2019-2025 Tushare classified-flow history without prices."""

    with RichDataProcessLock(METADATA_ROOT / ".tushare_moneyflow.lock"):
        contract = load_tushare_moneyflow_contract()
        require_provider("tushare")
        acceptance_record = load_tushare_moneyflow_acceptance()
        snapshot_contract = contract["snapshot_contract"]
        partition_policy = snapshot_contract["partition_policy"]
        start = dt.date.fromisoformat(snapshot_contract["development_start"])
        end = dt.date.fromisoformat(snapshot_contract["development_end"])
        validate_range(start, end, allow_large=allow_large, unit_count=1)
        intervals = load_factor_universe_intervals(universe_path)
        calendar = local_calendar_dates(start, end, calendar_path)
        if calendar.empty:
            raise RichDataError(
                "local calendar has no sessions in the Tushare moneyflow range"
            )
        overlap = intervals["start_date"].le(pd.Timestamp(end)) & intervals[
            "end_date"
        ].ge(pd.Timestamp(start))
        intervals = intervals.loc[overlap].copy()
        if intervals.empty:
            raise RichDataError(
                "factor universe has no instruments in the frozen range"
            )

        run_id = new_run_id("tushare_moneyflow_daily")
        parent = RAW_ROOT / "tushare" / "moneyflow" / "daily" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(f"Tushare moneyflow snapshot already exists: {run_id}")
        temporary_root.mkdir(parents=True)
        files: list[dict[str, Any]] = []
        all_daily_coverage: list[dict[str, Any]] = []
        quality_totals = {
            "input_rows": 0,
            "missing_rows_excluded": 0,
            "zero_denominator_rows_excluded": 0,
            "outside_point_in_time_universe_rows_excluded": 0,
            "rows_written": 0,
        }
        minimum_interval = float(partition_policy["minimum_seconds_between_calls"])
        maximum_attempts = int(partition_policy["maximum_attempts_per_session"])
        retry_backoffs = [
            float(value) for value in partition_policy["retry_backoff_seconds"]
        ]
        last_request_started: list[float | None] = [None]
        try:
            for year in range(start.year, end.year + 1):
                partition_start = max(start, dt.date(year, 1, 1))
                partition_end = min(end, dt.date(year, 12, 31))
                partition_calendar = calendar[
                    (calendar >= pd.Timestamp(partition_start))
                    & (calendar <= pd.Timestamp(partition_end))
                ]
                if partition_calendar.empty:
                    continue
                year_frames: list[pd.DataFrame] = []
                year_quality = {
                    "input_rows": 0,
                    "missing_rows_excluded": 0,
                    "zero_denominator_rows_excluded": 0,
                    "outside_point_in_time_universe_rows_excluded": 0,
                    "rows_written": 0,
                }
                for session in partition_calendar:
                    session_date = pd.Timestamp(session).date()
                    raw = _fetch_tushare_moneyflow_with_policy(
                        session_date,
                        minimum_interval=minimum_interval,
                        maximum_attempts=maximum_attempts,
                        retry_backoffs=retry_backoffs,
                        last_request_started=last_request_started,
                    )
                    if len(raw) >= int(
                        partition_policy["provider_documented_maximum_rows_per_call"]
                    ):
                        raise RichDataError(
                            f"Tushare moneyflow {session_date.isoformat()} reached the "
                            "provider row ceiling; the all-market response may be truncated"
                        )
                    normalized, quality = canonicalize_tushare_moneyflow(
                        raw, session_date, session_date
                    )
                    session_ts = pd.Timestamp(session)
                    active_rows = intervals[
                        intervals["start_date"].le(session_ts)
                        & intervals["end_date"].ge(session_ts)
                    ]
                    active_instruments = set(active_rows["instrument"].astype(str))
                    in_universe = normalized["instrument"].isin(active_instruments)
                    outside_universe = int((~in_universe).sum())
                    normalized = normalized.loc[in_universe].reset_index(drop=True)
                    quality["outside_point_in_time_universe_rows_excluded"] = (
                        outside_universe
                    )
                    quality["rows_written"] = int(len(normalized))
                    for key in year_quality:
                        year_quality[key] += int(quality.get(key, 0))
                    observed_names = int(normalized["instrument"].nunique())
                    expected_names = int(len(active_instruments))
                    all_daily_coverage.append(
                        {
                            "trade_date": session_date.isoformat(),
                            "expected_active_names": expected_names,
                            "positive_activity_factor_names": observed_names,
                            "coverage": (
                                observed_names / expected_names
                                if expected_names
                                else None
                            ),
                        }
                    )
                    if not normalized.empty:
                        year_frames.append(normalized)
                if not year_frames:
                    raise RichDataError(
                        f"Tushare moneyflow {year} partition has no eligible positive-activity rows"
                    )
                partition_frame = (
                    pd.concat(year_frames, ignore_index=True)
                    .sort_values(["trade_date", "instrument"], kind="stable")
                    .reset_index(drop=True)
                )
                if partition_frame.duplicated(["instrument", "trade_date"]).any():
                    raise RichDataError(
                        f"Tushare moneyflow {year} partition has duplicate stock-date keys"
                    )
                destination = temporary_root / f"{year}.parquet"
                atomic_write_frame(partition_frame, destination)
                for key in quality_totals:
                    quality_totals[key] += year_quality[key]
                files.append(
                    {
                        "year": year,
                        "requested_start": partition_start.isoformat(),
                        "requested_end": partition_end.isoformat(),
                        "provider_calls": int(len(partition_calendar)),
                        "path": manifest_path(run_root / destination.name),
                        "rows": int(len(partition_frame)),
                        "sha256": frame_digest(partition_frame),
                        "quality": year_quality,
                    }
                )
            if not files:
                raise RichDataError(
                    "Tushare moneyflow sync produced no completed partitions"
                )
            coverages = pd.Series(
                [
                    row["coverage"]
                    for row in all_daily_coverage
                    if row["coverage"] is not None
                ],
                dtype="float64",
            )
            median_coverage = float(coverages.median()) if len(coverages) else 0.0
            p05_coverage = float(coverages.quantile(0.05)) if len(coverages) else 0.0
            coverage_policy = contract["coverage_and_capacity_policy"]
            minimum_names = int(
                coverage_policy["minimum_eligible_names_per_cross_section"]
            )
            dates_with_minimum_names = int(
                sum(
                    row["positive_activity_factor_names"] >= minimum_names
                    for row in all_daily_coverage
                )
            )
            coverage_gate_passed = bool(
                len(coverages)
                and median_coverage
                >= float(coverage_policy["minimum_median_source_row_coverage"])
                and p05_coverage
                >= float(coverage_policy["minimum_p05_source_row_coverage"])
                and dates_with_minimum_names >= 200
            )
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "tushare_moneyflow_daily",
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_MONEYFLOW_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_MONEYFLOW_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "source_acceptance": {
                    "path": manifest_path(acceptance_record[0]),
                    "sha256": file_digest(acceptance_record[0]),
                    "run_id": acceptance_record[1].get("run_id"),
                    "status": contract["acceptance_protocol"]["status"],
                },
                "point_in_time_universe": {
                    "path": manifest_path(universe_path.expanduser().resolve()),
                    "sha256": file_digest(universe_path.expanduser().resolve()),
                    "intervals": int(
                        len(load_factor_universe_intervals(universe_path))
                    ),
                },
                "local_calendar": {
                    "path": manifest_path(calendar_path.expanduser().resolve()),
                    "sha256": file_digest(calendar_path.expanduser().resolve()),
                    "sessions_in_requested_range": int(len(calendar)),
                },
                "source_request": {
                    "api": "moneyflow",
                    "frequency": "daily",
                    "request_mode": "one completed local trading session per call",
                    "fields": list(TUSHARE_MONEYFLOW_RAW_FIELDS),
                    "forbidden_fields_requested_or_stored": [],
                    "credentials_logged_or_stored": False,
                    "minimum_seconds_between_calls": minimum_interval,
                    "maximum_attempts_per_session": maximum_attempts,
                },
                "files": files,
                "normalization_quality": quality_totals,
                "coverage": {
                    "calendar_sessions": int(len(calendar)),
                    "median_positive_activity_factor_coverage": median_coverage,
                    "p05_positive_activity_factor_coverage": p05_coverage,
                    "dates_with_at_least_fifty_factor_names": dates_with_minimum_names,
                    "gate_passed_before_prices": coverage_gate_passed,
                    "daily": all_daily_coverage,
                },
                "acceptance_status": (
                    "full_source_coverage_passed_pending_no_return_capacity"
                    if coverage_gate_passed
                    else "full_source_coverage_failed_stop_before_prices"
                ),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception:
            shutil.rmtree(temporary_root, ignore_errors=True)
            raise


def _fetch_tushare_daily_pb_with_policy(
    trade_date: dt.date,
    *,
    minimum_interval: float,
    maximum_attempts: int,
    retry_backoffs: list[float],
    last_request_started: list[float | None],
) -> pd.DataFrame:
    """Apply the frozen sequential throttle and bounded retry policy to PB."""

    for attempt in range(maximum_attempts):
        previous = last_request_started[0]
        if previous is not None:
            remaining = minimum_interval - (time.monotonic() - previous)
            if remaining > 0.0:
                time.sleep(remaining)
        last_request_started[0] = time.monotonic()
        try:
            return fetch_tushare_daily_pb(trade_date)
        except RichDataError:
            if attempt + 1 >= maximum_attempts:
                raise
            time.sleep(retry_backoffs[attempt])
    raise AssertionError("unreachable Tushare daily PB retry state")


def sync_tushare_daily_pb(
    *,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_BUYABLE_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
) -> Path:
    """Store the frozen 2019-2025 positive book-to-market history without prices."""

    with RichDataProcessLock(METADATA_ROOT / ".tushare_daily_pb.lock"):
        contract = load_tushare_daily_pb_contract()
        source_chain = load_tushare_daily_pb_source_chain()
        require_provider("tushare")
        snapshot_contract = contract["snapshot_contract"]
        partition_policy = snapshot_contract["partition_policy"]
        start = dt.date.fromisoformat(snapshot_contract["development_start"])
        end = dt.date.fromisoformat(snapshot_contract["development_end"])
        validate_range(start, end, allow_large=allow_large, unit_count=1)
        all_intervals = load_factor_universe_intervals(universe_path)
        calendar = local_calendar_dates(start, end, calendar_path)
        if calendar.empty:
            raise RichDataError(
                "local calendar has no sessions in the Tushare daily PB range"
            )
        overlap = all_intervals["start_date"].le(pd.Timestamp(end)) & all_intervals[
            "end_date"
        ].ge(pd.Timestamp(start))
        intervals = all_intervals.loc[overlap].copy()
        if intervals.empty:
            raise RichDataError(
                "holding universe has no instruments in the frozen PB range"
            )

        run_id = new_run_id("tushare_daily_pb")
        parent = RAW_ROOT / "tushare" / "daily_pb" / "snapshots"
        run_root = parent / run_id
        temporary_root = parent / f".{run_id}.partial"
        if run_root.exists() or temporary_root.exists():
            raise RichDataError(f"Tushare daily PB snapshot already exists: {run_id}")
        temporary_root.mkdir(parents=True)
        files: list[dict[str, Any]] = []
        all_daily_coverage: list[dict[str, Any]] = []
        quality_totals = {
            "input_rows": 0,
            "missing_pb_rows_excluded": 0,
            "nonpositive_pb_rows_excluded": 0,
            "outside_point_in_time_holding_universe_rows_excluded": 0,
            "rows_written": 0,
        }
        minimum_interval = float(partition_policy["minimum_seconds_between_calls"])
        maximum_attempts = int(partition_policy["maximum_attempts_per_session"])
        retry_backoffs = [
            float(value) for value in partition_policy["retry_backoff_seconds"]
        ]
        last_request_started: list[float | None] = [None]
        completed_calls = 0
        total_calls = int(len(calendar))
        current_session_date: dt.date | None = None
        try:
            for year in range(start.year, end.year + 1):
                partition_start = max(start, dt.date(year, 1, 1))
                partition_end = min(end, dt.date(year, 12, 31))
                partition_calendar = calendar[
                    (calendar >= pd.Timestamp(partition_start))
                    & (calendar <= pd.Timestamp(partition_end))
                ]
                if partition_calendar.empty:
                    continue
                year_frames: list[pd.DataFrame] = []
                year_quality = {
                    "input_rows": 0,
                    "missing_pb_rows_excluded": 0,
                    "nonpositive_pb_rows_excluded": 0,
                    "outside_point_in_time_holding_universe_rows_excluded": 0,
                    "rows_written": 0,
                }
                for session in partition_calendar:
                    session_date = pd.Timestamp(session).date()
                    current_session_date = session_date
                    raw = _fetch_tushare_daily_pb_with_policy(
                        session_date,
                        minimum_interval=minimum_interval,
                        maximum_attempts=maximum_attempts,
                        retry_backoffs=retry_backoffs,
                        last_request_started=last_request_started,
                    )
                    if len(raw) >= int(
                        partition_policy["provider_documented_maximum_rows_per_call"]
                    ):
                        raise RichDataError(
                            f"Tushare daily PB {session_date.isoformat()} reached the "
                            "provider row ceiling; the all-market response may be truncated"
                        )
                    normalized, quality = canonicalize_tushare_daily_pb(
                        raw, session_date, session_date
                    )
                    session_ts = pd.Timestamp(session)
                    active_rows = intervals[
                        intervals["start_date"].le(session_ts)
                        & intervals["end_date"].ge(session_ts)
                    ]
                    active_instruments = set(active_rows["instrument"].astype(str))
                    in_universe = normalized["instrument"].isin(active_instruments)
                    outside_universe = int((~in_universe).sum())
                    normalized = normalized.loc[in_universe].reset_index(drop=True)
                    quality["outside_point_in_time_holding_universe_rows_excluded"] = (
                        outside_universe
                    )
                    quality["rows_written"] = int(len(normalized))
                    for key in year_quality:
                        year_quality[key] += int(quality.get(key, 0))
                    observed_names = int(normalized["instrument"].nunique())
                    expected_names = int(len(active_instruments))
                    all_daily_coverage.append(
                        {
                            "trade_date": session_date.isoformat(),
                            "expected_active_holding_names": expected_names,
                            "positive_pb_holding_names": observed_names,
                            "coverage": (
                                observed_names / expected_names
                                if expected_names
                                else None
                            ),
                        }
                    )
                    if not normalized.empty:
                        year_frames.append(normalized)
                    completed_calls += 1
                    if completed_calls % 50 == 0 or completed_calls == total_calls:
                        print(
                            json.dumps(
                                {
                                    "dataset": "tushare_daily_pb",
                                    "progress_calls": completed_calls,
                                    "total_calls": total_calls,
                                    "latest_session": session_date.isoformat(),
                                },
                                ensure_ascii=False,
                            ),
                            flush=True,
                        )
                if not year_frames:
                    raise RichDataError(
                        f"Tushare daily PB {year} partition has no eligible positive-PB rows"
                    )
                partition_frame = (
                    pd.concat(year_frames, ignore_index=True)
                    .sort_values(["trade_date", "instrument"], kind="stable")
                    .reset_index(drop=True)
                )
                if tuple(partition_frame.columns) != TUSHARE_DAILY_PB_COLUMNS:
                    raise RichDataError(
                        f"Tushare daily PB {year} partition columns changed"
                    )
                if partition_frame.duplicated(["instrument", "trade_date"]).any():
                    raise RichDataError(
                        f"Tushare daily PB {year} partition has duplicate stock-date keys"
                    )
                destination = temporary_root / f"{year}.parquet"
                atomic_write_frame(partition_frame, destination)
                for key in quality_totals:
                    quality_totals[key] += year_quality[key]
                files.append(
                    {
                        "year": year,
                        "requested_start": partition_start.isoformat(),
                        "requested_end": partition_end.isoformat(),
                        "provider_calls": int(len(partition_calendar)),
                        "path": manifest_path(run_root / destination.name),
                        "rows": int(len(partition_frame)),
                        "sha256": frame_digest(partition_frame),
                        "quality": year_quality,
                    }
                )
                print(
                    json.dumps(
                        {
                            "dataset": "tushare_daily_pb",
                            "completed_year": year,
                            "rows": int(len(partition_frame)),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            if not files:
                raise RichDataError(
                    "Tushare daily PB sync produced no completed partitions"
                )
            coverages = pd.Series(
                [
                    row["coverage"]
                    for row in all_daily_coverage
                    if row["coverage"] is not None
                ],
                dtype="float64",
            )
            median_coverage = float(coverages.median()) if len(coverages) else 0.0
            p05_coverage = float(coverages.quantile(0.05)) if len(coverages) else 0.0
            coverage_policy = contract["source_completeness_policy"]
            dates_with_minimum_names = int(
                sum(
                    row["positive_pb_holding_names"] >= 50 for row in all_daily_coverage
                )
            )
            observed_years = len({int(item["year"]) for item in files})
            coverage_gate_passed = bool(
                len(coverages)
                and median_coverage
                >= float(
                    coverage_policy[
                        "minimum_median_positive_pb_holding_universe_coverage"
                    ]
                )
                and p05_coverage
                >= float(
                    coverage_policy["minimum_p05_positive_pb_holding_universe_coverage"]
                )
                and dates_with_minimum_names
                >= int(coverage_policy["minimum_sessions_with_fifty_positive_pb_names"])
                and observed_years
                >= int(coverage_policy["minimum_observed_source_years"])
            )
            spec = source_chain["spec"]
            manifest = {
                "schema_version": 1,
                "kind": "a_share_rich_data_snapshot",
                "dataset": "tushare_daily_pb",
                "provider": "tushare",
                "run_id": run_id,
                "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                    "preregistered_at": contract["preregistered_at"],
                },
                "no_return_preregistration": {
                    "path": manifest_path(source_chain["spec_path"]),
                    "sha256": file_digest(source_chain["spec_path"]),
                    "preregistered_at": spec["preregistered_at"],
                },
                "source_acceptance": {
                    "record_path": manifest_path(source_chain["record_path"]),
                    "record_sha256": file_digest(source_chain["record_path"]),
                    "manifest_path": manifest_path(source_chain["manifest_path"]),
                    "manifest_sha256": file_digest(source_chain["manifest_path"]),
                    "run_id": source_chain["manifest"].get("run_id"),
                    "frame_path": manifest_path(source_chain["frame_path"]),
                    "frame_content_sha256": (
                        source_chain["manifest"]["files"][0]["sha256"]
                    ),
                },
                "point_in_time_holding_universe": {
                    "path": manifest_path(universe_path.expanduser().resolve()),
                    "sha256": file_digest(universe_path.expanduser().resolve()),
                    "intervals": int(len(all_intervals)),
                },
                "local_calendar": {
                    "path": manifest_path(calendar_path.expanduser().resolve()),
                    "sha256": file_digest(calendar_path.expanduser().resolve()),
                    "sessions_in_requested_range": int(len(calendar)),
                },
                "source_request": {
                    "api": "daily_basic",
                    "frequency": "daily_after_close",
                    "request_mode": "one completed local trading session per call",
                    "fields": list(TUSHARE_DAILY_PB_RAW_FIELDS),
                    "forbidden_fields_requested_or_stored": [],
                    "credentials_logged_or_stored": False,
                    "minimum_seconds_between_calls": minimum_interval,
                    "maximum_attempts_per_session": maximum_attempts,
                },
                "files": files,
                "normalization_quality": quality_totals,
                "coverage": {
                    "calendar_sessions": int(len(calendar)),
                    "observed_source_years": observed_years,
                    "median_positive_pb_holding_universe_coverage": median_coverage,
                    "p05_positive_pb_holding_universe_coverage": p05_coverage,
                    "sessions_with_at_least_fifty_positive_pb_names": (
                        dates_with_minimum_names
                    ),
                    "gate_passed_before_prices": coverage_gate_passed,
                    "daily": all_daily_coverage,
                },
                "acceptance_status": (
                    "full_source_coverage_passed_pending_no_return_uniqueness_and_capacity"
                    if coverage_gate_passed
                    else "full_source_coverage_failed_stop_before_uniqueness_capacity_or_prices"
                ),
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            temporary_root.replace(run_root)
            destination = RUNS_ROOT / f"{run_id}.json"
            try:
                atomic_write_json(manifest, destination)
            except Exception:
                shutil.rmtree(run_root, ignore_errors=True)
                raise
            return destination
        except Exception as exc:
            shutil.rmtree(temporary_root, ignore_errors=True)
            message = str(exc)
            if "missing keys" in message:
                failure_code = "source_missing_instrument_or_trade_date_key"
            elif "row ceiling" in message:
                failure_code = "provider_row_ceiling_possible_truncation"
            elif "duplicate" in message:
                failure_code = "source_duplicate_key"
            elif "outside the request" in message:
                failure_code = "source_date_outside_request"
            elif "fields outside" in message or "lacks requested fields" in message:
                failure_code = "source_schema_mismatch"
            elif "negative" in message or "infinite" in message:
                failure_code = "source_value_domain_failure"
            else:
                failure_code = "provider_or_local_snapshot_failure"
            failure_path = RUNS_ROOT / f"{run_id}_source_failure.json"
            failure = {
                "schema_version": 1,
                "kind": "a_share_rich_data_source_failure",
                "dataset": "tushare_daily_pb",
                "provider": "tushare",
                "run_id": run_id,
                "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "failed_session": (
                    current_session_date.isoformat()
                    if current_session_date is not None
                    else None
                ),
                "completed_provider_calls_before_failure": completed_calls,
                "total_planned_provider_calls": total_calls,
                "failure_code": failure_code,
                "partial_snapshot_deleted": not temporary_root.exists(),
                "final_snapshot_published": run_root.exists(),
                "data_contract": {
                    "path": manifest_path(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                    "sha256": file_digest(DEFAULT_TUSHARE_DAILY_PB_CONTRACT),
                },
                "no_return_preregistration": {
                    "path": manifest_path(source_chain["spec_path"]),
                    "sha256": file_digest(source_chain["spec_path"]),
                },
                "credentials_logged_or_stored": False,
                "price_fields_loaded": [],
                "open_close_or_forward_return_fields_read": False,
                "forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            atomic_write_json(failure, failure_path)
            if isinstance(exc, RichDataError):
                raise RichDataError(
                    f"{message}; rejection_record={failure_path}"
                ) from exc
            raise


def load_jqdata_moneyflow_acceptance(
    runs_root: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Load and verify the latest accepted four-symbol entitlement snapshot."""

    expected_symbols = {qlib_symbol(code) for code in DEFAULT_ACCEPTANCE_SYMBOLS}
    root = (runs_root or RUNS_ROOT).expanduser()
    for path in reversed(sorted(root.glob("*.json"))):
        try:
            manifest = load_json_record(path, kind="a_share_rich_data_snapshot")
        except RichDataError:
            continue
        if manifest.get("dataset") != "jqdata_moneyflow_pro_daily":
            continue
        if (
            manifest.get("provider") != "jqdata"
            or manifest.get("acceptance_status")
            != "accepted_entitlement_and_formula_pending_full_history"
        ):
            continue
        contract = manifest.get("data_contract") or {}
        request = manifest.get("source_request") or {}
        if (
            contract.get("sha256") != JQDATA_MONEYFLOW_CONTRACT_SHA256
            or request.get("fields") != list(JQDATA_MONEYFLOW_RAW_FIELDS)
            or request.get("forbidden_fields_requested_or_stored") != []
            or request.get("credentials_logged_or_stored") is not False
            or manifest.get("price_fields_loaded") != []
            or manifest.get("forward_return_fields_read") is not False
            or manifest.get("selection_or_promotion_allowed") is not False
        ):
            raise RichDataError(
                "JQData moneyflow acceptance manifest violates the frozen contract"
            )
        files = list(manifest.get("files") or [])
        if len(files) != 1:
            raise RichDataError(
                "JQData moneyflow acceptance must contain one daily partition"
            )
        frame = load_snapshot_frame(files[0])
        if (
            tuple(frame.columns) != JQDATA_MONEYFLOW_COLUMNS
            or set(frame["instrument"].astype(str)) != expected_symbols
            or frame["trade_date"].nunique() != 1
            or not frame["jqdata_large_order_net_inflow_share"].between(-1.0, 1.0).all()
        ):
            raise RichDataError(
                "JQData moneyflow acceptance data violates the frozen schema"
            )
        return path.resolve(), manifest
    raise RichDataError(
        "no accepted JQData moneyflow entitlement snapshot exists; "
        "run acceptance-jqdata-moneyflow first"
    )


def sync_jqdata_moneyflow(
    *,
    acceptance_date: dt.date | None = None,
    allow_large: bool = False,
    universe_path: Path = DEFAULT_FACTOR_UNIVERSE,
    calendar_path: Path = DEFAULT_LOCAL_CALENDAR,
) -> Path:
    """Store the frozen JQData daily classified-flow snapshot without prices."""

    contract = load_jqdata_moneyflow_contract()
    require_provider("jqdata")
    acceptance = acceptance_date is not None
    if acceptance:
        start = end = acceptance_date
        codes = list(contract["acceptance_protocol"]["symbols"])
        intervals = None
        acceptance_record: tuple[Path, dict[str, Any]] | None = None
    else:
        acceptance_record = load_jqdata_moneyflow_acceptance()
        snapshot_contract = contract["snapshot_contract"]
        start = dt.date.fromisoformat(snapshot_contract["development_start"])
        end = dt.date.fromisoformat(snapshot_contract["development_end"])
        intervals = load_factor_universe_intervals(universe_path)
        overlap = intervals["start_date"].le(pd.Timestamp(end)) & intervals[
            "end_date"
        ].ge(pd.Timestamp(start))
        codes = intervals.loc[overlap, "instrument"].str[2:].astype(str).tolist()
        if not codes:
            raise RichDataError(
                "factor universe has no instruments in the frozen range"
            )
    validate_range(start, end, allow_large=allow_large, unit_count=len(codes))
    calendar = local_calendar_dates(start, end, calendar_path)
    if calendar.empty:
        raise RichDataError(
            "local calendar has no sessions in the JQData moneyflow range"
        )
    if acceptance and len(calendar) != 1:
        raise RichDataError(
            "JQData moneyflow acceptance date is not a local trading session"
        )

    run_id = new_run_id("jqdata_moneyflow_daily")
    parent = RAW_ROOT / "jqdata" / "moneyflow" / "daily" / "snapshots"
    run_root = parent / run_id
    temporary_root = parent / f".{run_id}.partial"
    if run_root.exists() or temporary_root.exists():
        raise RichDataError(f"JQData moneyflow snapshot already exists: {run_id}")
    temporary_root.mkdir(parents=True)
    files: list[dict[str, Any]] = []
    all_daily_coverage: list[dict[str, Any]] = []
    quality_totals = {
        "input_rows": 0,
        "missing_rows_excluded": 0,
        "zero_denominator_rows_excluded": 0,
        "outside_point_in_time_universe_rows_excluded": 0,
        "rows_written": 0,
    }
    try:
        for year in range(start.year, end.year + 1):
            partition_start = max(start, dt.date(year, 1, 1))
            partition_end = min(end, dt.date(year, 12, 31))
            partition_calendar = calendar[
                (calendar >= pd.Timestamp(partition_start))
                & (calendar <= pd.Timestamp(partition_end))
            ]
            if partition_calendar.empty:
                continue
            if intervals is None:
                partition_codes = codes
                partition_intervals = None
            else:
                overlap = intervals["start_date"].le(
                    pd.Timestamp(partition_end)
                ) & intervals["end_date"].ge(pd.Timestamp(partition_start))
                partition_intervals = intervals.loc[overlap].copy()
                partition_codes = (
                    partition_intervals["instrument"].str[2:].astype(str).tolist()
                )
            raw = fetch_jqdata_moneyflow_pro(
                partition_codes, partition_start, partition_end
            )
            if len(raw) >= int(
                contract["snapshot_contract"]["partition_policy"][
                    "provider_documented_maximum_rows_per_call"
                ]
            ):
                raise RichDataError(
                    f"JQData moneyflow {year} partition reached the provider row ceiling"
                )
            normalized, quality = canonicalize_jqdata_moneyflow(
                raw, partition_codes, partition_start, partition_end
            )
            outside_universe = 0
            if partition_intervals is not None and not normalized.empty:
                indexed = partition_intervals.set_index("instrument")
                starts = normalized["instrument"].map(indexed["start_date"])
                ends = normalized["instrument"].map(indexed["end_date"])
                in_universe = normalized["trade_date"].ge(starts) & normalized[
                    "trade_date"
                ].le(ends)
                outside_universe = int((~in_universe).sum())
                normalized = normalized.loc[in_universe].reset_index(drop=True)
            if normalized.empty:
                raise RichDataError(
                    f"JQData moneyflow {year} partition has no eligible positive-activity rows; "
                    "verify the separately purchased product entitlement"
                )
            if acceptance:
                observed = set(normalized["instrument"])
                expected = {qlib_symbol(code) for code in codes}
                if observed != expected:
                    missing = sorted(expected - observed)
                    raise RichDataError(
                        "JQData moneyflow acceptance did not return all four frozen symbols: "
                        + ", ".join(missing)
                    )
            observed_by_date = normalized.groupby("trade_date").size().to_dict()
            for date in partition_calendar:
                if partition_intervals is None:
                    expected_names = len(partition_codes)
                else:
                    expected_names = int(
                        (
                            partition_intervals["start_date"].le(date)
                            & partition_intervals["end_date"].ge(date)
                        ).sum()
                    )
                observed_names = int(observed_by_date.get(pd.Timestamp(date), 0))
                all_daily_coverage.append(
                    {
                        "trade_date": pd.Timestamp(date).date().isoformat(),
                        "expected_active_names": expected_names,
                        "positive_activity_factor_names": observed_names,
                        "coverage": (
                            observed_names / expected_names if expected_names else None
                        ),
                    }
                )
            destination = temporary_root / f"{year}.parquet"
            atomic_write_frame(normalized, destination)
            quality["outside_point_in_time_universe_rows_excluded"] = outside_universe
            quality["rows_written"] = int(len(normalized))
            for key in quality_totals:
                quality_totals[key] += int(quality.get(key, 0))
            files.append(
                {
                    "year": year,
                    "requested_start": partition_start.isoformat(),
                    "requested_end": partition_end.isoformat(),
                    "requested_symbols": len(partition_codes),
                    "path": manifest_path(run_root / destination.name),
                    "rows": int(len(normalized)),
                    "sha256": frame_digest(normalized),
                    "quality": quality,
                }
            )
        if not files:
            raise RichDataError(
                "JQData moneyflow sync produced no completed partitions"
            )
        coverages = pd.Series(
            [
                row["coverage"]
                for row in all_daily_coverage
                if row["coverage"] is not None
            ],
            dtype="float64",
        )
        median_coverage = float(coverages.median()) if len(coverages) else 0.0
        p05_coverage = float(coverages.quantile(0.05)) if len(coverages) else 0.0
        minimum_names = int(
            contract["coverage_and_capacity_policy"][
                "minimum_eligible_names_per_cross_section"
            ]
        )
        coverage_gate_passed = bool(
            len(coverages)
            and median_coverage
            >= float(
                contract["coverage_and_capacity_policy"][
                    "minimum_median_source_row_coverage"
                ]
            )
            and p05_coverage
            >= float(
                contract["coverage_and_capacity_policy"][
                    "minimum_p05_source_row_coverage"
                ]
            )
            and sum(
                row["positive_activity_factor_names"] >= minimum_names
                for row in all_daily_coverage
            )
            >= 200
        )
        manifest = {
            "schema_version": 1,
            "kind": "a_share_rich_data_snapshot",
            "dataset": "jqdata_moneyflow_pro_daily",
            "provider": "jqdata",
            "run_id": run_id,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
            "data_contract": {
                "path": manifest_path(DEFAULT_JQDATA_MONEYFLOW_CONTRACT),
                "sha256": file_digest(DEFAULT_JQDATA_MONEYFLOW_CONTRACT),
                "preregistered_at": contract["preregistered_at"],
            },
            "source_acceptance": (
                None
                if acceptance_record is None
                else {
                    "path": manifest_path(acceptance_record[0]),
                    "sha256": file_digest(acceptance_record[0]),
                    "run_id": acceptance_record[1].get("run_id"),
                    "status": acceptance_record[1].get("acceptance_status"),
                }
            ),
            "point_in_time_universe": (
                None
                if acceptance
                else {
                    "path": manifest_path(universe_path.expanduser().resolve()),
                    "sha256": file_digest(universe_path.expanduser().resolve()),
                    "intervals": int(len(intervals)),
                }
            ),
            "local_calendar": {
                "path": manifest_path(calendar_path.expanduser().resolve()),
                "sha256": file_digest(calendar_path.expanduser().resolve()),
                "sessions_in_requested_range": int(len(calendar)),
            },
            "source_request": {
                "api": "get_money_flow_pro",
                "frequency": "daily",
                "data_type": "money",
                "fields": list(JQDATA_MONEYFLOW_RAW_FIELDS),
                "forbidden_fields_requested_or_stored": [],
                "credentials_logged_or_stored": False,
            },
            "files": files,
            "normalization_quality": quality_totals,
            "coverage": {
                "calendar_sessions": int(len(calendar)),
                "median_positive_activity_factor_coverage": median_coverage,
                "p05_positive_activity_factor_coverage": p05_coverage,
                "dates_with_at_least_fifty_factor_names": int(
                    sum(
                        row["positive_activity_factor_names"] >= minimum_names
                        for row in all_daily_coverage
                    )
                ),
                "gate_passed_before_prices": coverage_gate_passed,
                "daily": all_daily_coverage,
            },
            "acceptance_status": (
                "accepted_entitlement_and_formula_pending_full_history"
                if acceptance
                else (
                    "full_source_coverage_passed_pending_no_return_capacity"
                    if coverage_gate_passed
                    else "full_source_coverage_failed_stop_before_prices"
                )
            ),
            "price_fields_loaded": [],
            "open_close_or_forward_return_fields_read": False,
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        }
        temporary_root.replace(run_root)
        destination = RUNS_ROOT / f"{run_id}.json"
        try:
            atomic_write_json(manifest, destination)
        except Exception:
            shutil.rmtree(run_root, ignore_errors=True)
            raise
        return destination
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def advisory_lock_status(path: Path) -> dict[str, Any]:
    """Inspect an advisory lock without deleting, truncating, or acquiring it long-term."""

    path = path.expanduser().resolve()
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "recorded_owner_pid": None,
            "advisory_lock_currently_held": False,
        }
    try:
        with path.open("r", encoding="utf-8") as handle:
            owner = handle.read().strip() or None
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                held = True
            else:
                held = False
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except FileNotFoundError:  # The owner may exit between exists() and open().
        return {
            "path": str(path),
            "exists": False,
            "recorded_owner_pid": None,
            "advisory_lock_currently_held": False,
        }
    return {
        "path": str(path),
        "exists": True,
        "recorded_owner_pid": owner,
        "advisory_lock_currently_held": held,
    }


def baostock_5m_storage_status(data_root: Path) -> dict[str, Any]:
    """Summarize one five-minute storage root without network access or mutation."""

    resolved = data_root.expanduser().resolve()
    raw_root = resolved / "raw" / "a_share" / "rich" / "baostock" / "minutes" / "5m"
    runs_root = resolved / "metadata" / "rich_data" / "runs"
    availability_root = resolved / "metadata" / "rich_data" / "availability"
    preflight_root = resolved / "metadata" / "rich_data" / "preflights"
    raw_files = sorted(raw_root.rglob("*.parquet")) if raw_root.exists() else []
    run_paths = sorted(runs_root.glob("*.json")) if runs_root.exists() else []
    history_manifests: list[Path] = []
    for path in run_paths:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if record.get("dataset") == "baostock_five_minute_history":
            history_manifests.append(path)

    availability_paths = (
        sorted(availability_root.glob("*.json")) if availability_root.exists() else []
    )
    latest_probe: dict[str, Any] | None = None
    if availability_paths:
        latest_path = availability_paths[-1]
        try:
            record = load_json_record(
                latest_path, kind="a_share_baostock_5m_restoration_probe"
            )
        except (RichDataError, ValueError, OSError, json.JSONDecodeError):
            latest_probe = {
                "path": str(latest_path.resolve()),
                "record_valid": False,
                "status": "invalid_record",
                "created_at": None,
                "history_query_succeeded": False,
                "rows": 0,
            }
        else:
            latest_probe = {
                "path": str(latest_path.resolve()),
                "record_valid": True,
                "status": str(record.get("status") or "unknown"),
                "created_at": record.get("created_at"),
                "history_query_succeeded": bool(
                    record.get("history_query_succeeded", False)
                ),
                "rows": int(record.get("rows") or 0),
            }

    preflight_paths = (
        sorted(preflight_root.glob("*.json")) if preflight_root.exists() else []
    )
    latest_preflight: dict[str, Any] | None = None
    if preflight_paths:
        latest_path = preflight_paths[-1]
        try:
            record = load_json_record(latest_path, kind="a_share_baostock_5m_preflight")
        except (RichDataError, ValueError, OSError, json.JSONDecodeError):
            latest_preflight = {
                "path": str(latest_path.resolve()),
                "record_valid": False,
                "status": "invalid_record",
            }
        else:
            latest_preflight = {
                "path": str(latest_path.resolve()),
                "record_valid": True,
                "status": str(record.get("status") or "unknown"),
                "observed_free_gib": record.get("observed_free_gib"),
                "network_request_issued": bool(
                    record.get("network_request_issued", False)
                ),
            }

    return {
        "data_root": str(resolved),
        "network_request_issued": False,
        "raw_parquet_file_count": len(raw_files),
        "history_manifest_count": len(history_manifests),
        "latest_history_manifest": (
            str(history_manifests[-1].resolve()) if history_manifests else None
        ),
        "latest_restoration_probe": latest_probe,
        "latest_preflight": latest_preflight,
        "process_lock": advisory_lock_status(resolved / ".a_share_baostock_5m.lock"),
    }


def status_payload(data_root: Path = DATA_ROOT) -> dict[str, Any]:
    """Return safe machine-readable readiness information."""

    manifests = sorted(RUNS_ROOT.glob("*.json")) if RUNS_ROOT.exists() else []
    alignments = (
        sorted(ALIGNMENTS_ROOT.glob("*.json")) if ALIGNMENTS_ROOT.exists() else []
    )
    feature_runs = (
        sorted(FEATURE_RUNS_ROOT.glob("*.json")) if FEATURE_RUNS_ROOT.exists() else []
    )
    return {
        "repository": str(REPO_ROOT),
        "data_root": str(DATA_ROOT),
        "providers": [
            asdict(provider_availability(provider))
            | {"ready": provider_availability(provider).ready}
            for provider in PROVIDER_REQUIREMENTS
        ],
        "snapshot_manifest_count": len(manifests),
        "latest_snapshot_manifest": str(manifests[-1]) if manifests else None,
        "alignment_confirmation_count": len(alignments),
        "latest_alignment_confirmation": str(alignments[-1]) if alignments else None,
        "minute_feature_run_count": len(feature_runs),
        "latest_minute_feature_run": str(feature_runs[-1]) if feature_runs else None,
        "baostock_five_minute_storage": baostock_5m_storage_status(data_root),
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    status = subparsers.add_parser(
        "status", help="show safe provider readiness and stored snapshots"
    )
    status.add_argument(
        "--data-root",
        type=Path,
        default=DATA_ROOT,
        help="inspect this BaoStock five-minute storage root without network access",
    )

    minute = subparsers.add_parser(
        "sync-minutes", help="download explicit-symbol minute bars"
    )
    minute.add_argument("--provider", choices=sorted(MINUTE_FETCHERS), required=True)
    minute.add_argument(
        "--symbols",
        type=parse_symbols,
        required=True,
        help="comma-separated six-digit A-share codes",
    )
    minute.add_argument("--start", type=parse_date, required=True)
    minute.add_argument("--end", type=parse_date, required=True)
    minute.add_argument("--frequency", default="1m")
    minute.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm a request above 100 symbol-sessions",
    )

    acceptance = subparsers.add_parser(
        "acceptance", help="run a small minute-data acceptance download"
    )
    acceptance.add_argument(
        "--provider", choices=sorted(MINUTE_FETCHERS), required=True
    )
    acceptance.add_argument(
        "--date", type=parse_date, default=latest_completed_session_date()
    )
    acceptance.add_argument(
        "--symbols", type=parse_symbols, default=list(DEFAULT_ACCEPTANCE_SYMBOLS)
    )
    acceptance.add_argument("--frequency", default="1m")

    subparsers.add_parser(
        "acceptance-baostock-5m",
        help="run the frozen four-symbol BaoStock five-minute acceptance",
    )

    baostock_preflight = subparsers.add_parser(
        "preflight-baostock-5m",
        help="audit the frozen source chain and target storage without a network request",
    )
    baostock_preflight.add_argument("--data-root", type=Path, default=DATA_ROOT)
    baostock_preflight.add_argument(
        "--universe-file", type=Path, default=DEFAULT_FACTOR_UNIVERSE
    )
    baostock_preflight.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )

    baostock_restoration = subparsers.add_parser(
        "probe-baostock-5m-restoration",
        help="issue one accepted-date probe after an anonymous-provider cooldown",
    )
    baostock_restoration.add_argument("--data-root", type=Path, default=DATA_ROOT)

    baostock_history = subparsers.add_parser(
        "sync-baostock-5m",
        help="download the frozen 2020--2025 PIT-universe BaoStock five-minute snapshot",
    )
    baostock_history.add_argument(
        "--data-root",
        type=Path,
        default=DATA_ROOT,
        help="raw/metadata root; use a large external volume when the repository disk is full",
    )
    baostock_history.add_argument(
        "--universe-file", type=Path, default=DEFAULT_FACTOR_UNIVERSE
    )
    baostock_history.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )
    baostock_history.add_argument(
        "--workers",
        type=int,
        choices=range(1, BAOSTOCK_5M_MAX_WORKERS + 1),
        default=BAOSTOCK_5M_MAX_WORKERS,
    )
    baostock_history.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the accepted full-universe, multi-year anonymous request",
    )

    events = subparsers.add_parser(
        "sync-tushare-events", help="download Tushare event tables after the close"
    )
    events.add_argument("--datasets", default=",".join(DEFAULT_EVENT_DATASETS))
    events.add_argument("--start", type=parse_date, required=True)
    events.add_argument("--end", type=parse_date, required=True)
    events.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm a request above 100 table-sessions",
    )

    ts_moneyflow = subparsers.add_parser(
        "sync-tushare-moneyflow",
        help="download the frozen 2019-2025 Tushare daily classified-moneyflow snapshot",
    )
    ts_moneyflow.add_argument(
        "--universe-file", type=Path, default=DEFAULT_FACTOR_UNIVERSE
    )
    ts_moneyflow.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )
    ts_moneyflow.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the licensed full-universe multi-year request after acceptance passes",
    )

    subparsers.add_parser(
        "acceptance-tushare-northbound-top10",
        help="run the frozen completed-session Northbound top-ten entitlement check",
    )

    subparsers.add_parser(
        "acceptance-tushare-top-inst",
        help="run the one-shot completed-session institution-seat acceptance",
    )

    subparsers.add_parser(
        "acceptance-tushare-top10-float-concentration",
        help="run the frozen three-symbol top-ten float concentration acceptance",
    )

    subparsers.add_parser(
        "acceptance-tushare-cash-conversion",
        help="run the frozen three-symbol income/cashflow accounting acceptance",
    )

    ts_cash_conversion = subparsers.add_parser(
        "sync-tushare-cash-conversion",
        help="download the frozen 2019-2025 PIT accounting cash-conversion snapshot",
    )
    ts_cash_conversion.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the accepted 9,588-call sequential licensed request",
    )

    ts_daily_pb_acceptance = subparsers.add_parser(
        "acceptance-tushare-daily-pb",
        help="run the frozen completed-session positive book-to-market acceptance",
    )
    ts_daily_pb_acceptance.add_argument(
        "--universe-file", type=Path, default=DEFAULT_BUYABLE_UNIVERSE
    )

    subparsers.add_parser(
        "acceptance-tushare-sw-industry-breadth",
        help="run the frozen no-price SW2021 L1 classification and interval probe",
    )

    ts_sw_membership = subparsers.add_parser(
        "sync-tushare-sw-industry-membership",
        help="download the frozen 31-code by two-state SW2021 L1 membership snapshot",
    )
    ts_sw_membership.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the accepted and preregistered 62-call licensed request",
    )

    ts_daily_pb = subparsers.add_parser(
        "sync-tushare-daily-pb",
        help="download the frozen 2019-2025 Tushare positive book-to-market snapshot",
    )
    ts_daily_pb.add_argument(
        "--universe-file", type=Path, default=DEFAULT_BUYABLE_UNIVERSE
    )
    ts_daily_pb.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )
    ts_daily_pb.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the licensed full-universe multi-year request after acceptance and preregistration",
    )

    jq_moneyflow_acceptance = subparsers.add_parser(
        "acceptance-jqdata-moneyflow",
        help="verify JQData professional daily moneyflow entitlement on four frozen symbols",
    )
    jq_moneyflow_acceptance.add_argument(
        "--date", type=parse_date, default=latest_completed_session_date()
    )

    jq_moneyflow = subparsers.add_parser(
        "sync-jqdata-moneyflow",
        help="download the frozen 2019-2025 JQData professional daily moneyflow snapshot",
    )
    jq_moneyflow.add_argument(
        "--universe-file", type=Path, default=DEFAULT_FACTOR_UNIVERSE
    )
    jq_moneyflow.add_argument(
        "--calendar-file", type=Path, default=DEFAULT_LOCAL_CALENDAR
    )
    jq_moneyflow.add_argument(
        "--allow-large",
        action="store_true",
        help="confirm the licensed full-universe multi-year request after acceptance passes",
    )

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
    features.add_argument(
        "--factor-spec", type=Path, default=DEFAULT_MINUTE_FACTOR_SPEC
    )
    features.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the rich-data CLI."""

    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            print(
                json.dumps(
                    status_payload(args.data_root),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "sync-minutes":
            manifest = sync_minutes(
                args.provider,
                args.symbols,
                args.start,
                args.end,
                args.frequency,
                args.allow_large,
            )
        elif args.command == "acceptance":
            manifest = sync_minutes(
                args.provider,
                args.symbols,
                args.date,
                args.date,
                args.frequency,
                False,
                acceptance=True,
            )
        elif args.command == "acceptance-baostock-5m":
            manifest = sync_baostock_5m_acceptance()
        elif args.command == "preflight-baostock-5m":
            manifest = write_baostock_5m_preflight(
                data_root=args.data_root,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
            )
        elif args.command == "probe-baostock-5m-restoration":
            manifest = probe_baostock_5m_restoration(data_root=args.data_root)
        elif args.command == "sync-baostock-5m":
            manifest = sync_baostock_5m_history(
                allow_large=args.allow_large,
                data_root=args.data_root,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
                workers=args.workers,
            )
        elif args.command == "sync-tushare-events":
            datasets = [
                item.strip() for item in args.datasets.split(",") if item.strip()
            ]
            manifest = sync_tushare_events(
                datasets, args.start, args.end, args.allow_large
            )
        elif args.command == "sync-tushare-moneyflow":
            manifest = sync_tushare_moneyflow(
                allow_large=args.allow_large,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
            )
        elif args.command == "acceptance-tushare-northbound-top10":
            manifest = sync_tushare_northbound_top10_acceptance()
        elif args.command == "acceptance-tushare-top-inst":
            manifest = sync_tushare_top_inst_acceptance()
        elif args.command == "acceptance-tushare-top10-float-concentration":
            manifest = sync_tushare_top10_float_concentration_acceptance()
        elif args.command == "acceptance-tushare-cash-conversion":
            manifest = sync_tushare_cash_conversion_acceptance()
        elif args.command == "sync-tushare-cash-conversion":
            manifest = sync_tushare_cash_conversion(allow_large=args.allow_large)
        elif args.command == "acceptance-tushare-daily-pb":
            manifest = sync_tushare_daily_pb_acceptance(
                universe_path=args.universe_file
            )
        elif args.command == "acceptance-tushare-sw-industry-breadth":
            manifest = sync_tushare_sw_industry_breadth_acceptance()
        elif args.command == "sync-tushare-sw-industry-membership":
            manifest = sync_tushare_sw_industry_membership(allow_large=args.allow_large)
        elif args.command == "sync-tushare-daily-pb":
            manifest = sync_tushare_daily_pb(
                allow_large=args.allow_large,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
            )
        elif args.command == "acceptance-jqdata-moneyflow":
            manifest = sync_jqdata_moneyflow(acceptance_date=args.date)
        elif args.command == "sync-jqdata-moneyflow":
            manifest = sync_jqdata_moneyflow(
                allow_large=args.allow_large,
                universe_path=args.universe_file,
                calendar_path=args.calendar_file,
            )
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
        "acceptance-jqdata-moneyflow": "stored_entitlement_acceptance",
        "acceptance-baostock-5m": "stored_five_minute_acceptance",
        "preflight-baostock-5m": "stored_no_network_preflight",
        "probe-baostock-5m-restoration": "stored_provider_restoration_probe",
        "sync-baostock-5m": "stored_pending_no_return_feature_materialization",
        "sync-jqdata-moneyflow": "stored_pending_no_return_capacity",
        "sync-tushare-moneyflow": "stored_pending_no_return_capacity",
        "sync-tushare-daily-pb": "stored_pending_no_return_uniqueness_and_capacity",
        "acceptance-tushare-top-inst": (
            "stored_no_return_entitlement_and_top_list_acceptance"
        ),
        "acceptance-tushare-top10-float-concentration": (
            "stored_no_return_ownership_concentration_acceptance"
        ),
        "acceptance-tushare-cash-conversion": (
            "stored_no_return_accounting_cash_conversion_acceptance"
        ),
        "sync-tushare-cash-conversion": (
            "stored_pending_no_return_cash_conversion_capacity_and_uniqueness"
        ),
        "acceptance-tushare-sw-industry-breadth": (
            "stored_no_price_membership_acceptance"
        ),
        "sync-tushare-sw-industry-membership": (
            "stored_pending_no_return_factor_capacity_and_uniqueness"
        ),
    }.get(args.command, "stored_pending_acceptance")
    print(
        json.dumps(
            {"manifest": str(manifest), "status": command_status}, ensure_ascii=False
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
