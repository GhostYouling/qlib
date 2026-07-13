#!/usr/bin/env python3
"""Research short-horizon A-share price-volume factors with a quality gate.

The script deliberately separates two operations:

``sync-fundamentals``
    Downloads annual-report quality fields from Eastmoney and preserves the
    public announcement date needed for a conservative point-in-time join.

``run``
    Evaluates predefined five-session long-only factor combinations.  Every
    candidate is written to its own JSON file below ``data/experiments``;
    selection uses only the development period and is then reported on the
    later, untouched test period.

This is a research harness, not investment advice or an execution system.  It
does not claim exchange-grade point-in-time accounting data or
limit-up/limit-down execution.  The ``plan`` command adds auditable A-share
lot sizing for a current screen, but it is deliberately separate from the
adjusted-price historical research backtest.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data"
DEFAULT_PROVIDER_URI = DATA_ROOT / "qlib" / "cn_a_share"
DEFAULT_FUNDAMENTALS = DATA_ROOT / "raw" / "a_share" / "fundamentals" / "annual_quality.parquet"
DEFAULT_FUNDAMENTAL_MANIFEST = DATA_ROOT / "metadata" / "annual_quality_manifest.json"
DEFAULT_EXPERIMENT_ROOT = DATA_ROOT / "experiments" / "short_horizon"
DEFAULT_PILOT_CAPITALS = (200_000.0,)

EASTMONEY_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
EASTMONEY_REPORT = "RPT_LICO_FN_CPD"
FUNDAMENTAL_COLUMNS = (
    "instrument",
    "report_date",
    "announcement_date",
    "roe",
    "net_profit",
    "revenue_yoy",
    "profit_yoy",
)


@dataclass(frozen=True)
class Candidate:
    """One predeclared factor combination used in the first research sweep."""

    name: str
    description: str
    weights: dict[str, float]


@dataclass(frozen=True)
class AShareExecutionRules:
    """Execution conventions for a small, long-only A-share pilot.

    ``commission_rate`` is the user's all-in broker commission quote.  The
    exchange handling fee is intentionally not added a second time because it
    is commonly embedded in that quote; configure it separately only if a
    broker statement proves it is charged separately.
    """

    lot_size: int = 100
    commission_rate: float = 0.0001
    commission_min: float = 0.0
    transfer_fee_rate: float = 0.00002
    stamp_duty_rate: float = 0.0005
    max_gross_exposure: float = 0.15
    target_weight: float = 0.05

    def validate(self) -> None:
        if self.lot_size < 1:
            raise ValueError("lot_size must be positive")
        for name, value in (
            ("commission_rate", self.commission_rate),
            ("commission_min", self.commission_min),
            ("transfer_fee_rate", self.transfer_fee_rate),
            ("stamp_duty_rate", self.stamp_duty_rate),
            ("max_gross_exposure", self.max_gross_exposure),
            ("target_weight", self.target_weight),
        ):
            if value < 0:
                raise ValueError(f"{name} must not be negative")
        if self.max_gross_exposure > 1.0 or self.target_weight > 1.0:
            raise ValueError("portfolio weights must be no greater than one")


# All candidates intentionally use the same accounting-quality gate.  This
# makes their comparison about the short-horizon price-volume signal rather
# than about a different quality universe.
CANDIDATES = (
    Candidate(
        name="quality_breakout",
        description="Five/ten-day continuation with volume and turnover expansion near a 20-day high.",
        weights={
            "momentum_5": 0.20,
            "momentum_10": 0.20,
            "volume_surge": 0.20,
            "turnover_surge": 0.15,
            "near_high_20": 0.10,
            "volatility_target": 0.05,
            "quality_score": 0.10,
        },
    ),
    Candidate(
        name="quality_acceleration",
        description="Volume/turnover acceleration with positive intraday strength and moderate-high volatility.",
        weights={
            "momentum_10": 0.20,
            "volume_surge": 0.25,
            "turnover_surge": 0.20,
            "intraday_strength": 0.15,
            "volatility_target": 0.10,
            "near_high_20": 0.05,
            "quality_score": 0.05,
        },
    ),
    Candidate(
        name="quality_pullback",
        description="Short-term pullback/reversal inside a profitable, growing-company universe.",
        weights={
            "reversal_3": 0.30,
            "volume_surge": 0.15,
            "turnover_surge": 0.15,
            "intraday_strength": 0.05,
            "volatility_target": 0.10,
            "near_high_20": 0.05,
            "quality_score": 0.20,
        },
    ),
    Candidate(
        name="quality_trend_pullback",
        description="Three-day pullback within a ten-day uptrend, near a 20-day high and without a volume spike.",
        weights={
            "reversal_3": 0.25,
            "momentum_10": 0.25,
            "near_high_20": 0.15,
            "volume_dry_up": 0.10,
            "turnover_surge": 0.05,
            "volatility_target": 0.05,
            "quality_score": 0.15,
        },
    ),
    Candidate(
        name="quality_balanced",
        description="Balanced continuation, liquidity, intraday strength and quality composite.",
        weights={
            "momentum_5": 0.15,
            "momentum_10": 0.15,
            "volume_surge": 0.15,
            "turnover_surge": 0.15,
            "near_high_20": 0.10,
            "intraday_strength": 0.10,
            "volatility_target": 0.05,
            "quality_score": 0.15,
        },
    ),
)


def _timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _atomic_write_text(destination: Path, content: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(destination)


def _atomic_write_parquet(destination: Path, frame: pd.DataFrame) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".parquet", dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
    frame.to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(destination)


def _json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def a_share_trade_fees(notional: float, side: str, rules: AShareExecutionRules) -> dict[str, float]:
    """Calculate the configurable fees for one ordinary A-share stock trade."""

    rules.validate()
    if notional < 0:
        raise ValueError("notional must not be negative")
    if side not in {"buy", "sell"}:
        raise ValueError("side must be 'buy' or 'sell'")
    commission = max(notional * rules.commission_rate, rules.commission_min) if notional else 0.0
    transfer_fee = notional * rules.transfer_fee_rate
    stamp_duty = notional * rules.stamp_duty_rate if side == "sell" else 0.0
    return {
        "commission": float(commission),
        "transfer_fee": float(transfer_fee),
        "stamp_duty": float(stamp_duty),
        "total": float(commission + transfer_fee + stamp_duty),
    }


def buy_cash_required(price: float, quantity: int, rules: AShareExecutionRules) -> float:
    """Return cash needed to buy an integer number of shares, including fees."""

    if price <= 0:
        raise ValueError("price must be positive")
    if quantity < 0 or quantity % rules.lot_size:
        raise ValueError("quantity must be a non-negative whole number of board lots")
    notional = price * quantity
    return float(notional + a_share_trade_fees(notional, "buy", rules)["total"])


def affordable_board_lots(price: float, budget: float, rules: AShareExecutionRules) -> int:
    """Return the largest board-lot quantity whose buy cash does not exceed budget."""

    if budget < 0:
        raise ValueError("budget must not be negative")
    if price <= 0:
        raise ValueError("price must be positive")
    one_lot_cost = buy_cash_required(price, rules.lot_size, rules)
    if one_lot_cost > budget:
        return 0
    estimated_lots = int(budget // (price * rules.lot_size * (1.0 + rules.commission_rate + rules.transfer_fee_rate)))
    lots = max(1, estimated_lots)
    while lots and buy_cash_required(price, lots * rules.lot_size, rules) > budget + 1e-9:
        lots -= 1
    return lots * rules.lot_size


def plan_lot_orders(
    candidates: list[dict[str, Any]], capital: float, rules: AShareExecutionRules
) -> dict[str, Any]:
    """Create an order-sized pilot plan without redistributing skipped slots.

    A skipped expensive stock intentionally leaves cash unused.  Reassigning
    that cash to a lower-ranked name would make a different, untested strategy.
    """

    rules.validate()
    if capital <= 0:
        raise ValueError("capital must be positive")
    if not candidates:
        raise ValueError("at least one candidate is required")
    if len(candidates) * rules.target_weight > rules.max_gross_exposure + 1e-12:
        raise ValueError("candidate target weights exceed max_gross_exposure")

    target_cash = capital * rules.target_weight
    orders: list[dict[str, Any]] = []
    for fallback_rank, candidate in enumerate(candidates, start=1):
        price = float(candidate["reference_close"])
        quantity = affordable_board_lots(price, target_cash, rules)
        rank = int(candidate.get("rank", fallback_rank))
        name = str(candidate.get("name", ""))
        instrument = str(candidate["instrument"])
        if quantity == 0:
            one_lot_cash = buy_cash_required(price, rules.lot_size, rules)
            orders.append(
                {
                    "rank": rank,
                    "instrument": instrument,
                    "name": name,
                    "reference_close": price,
                    "target_weight": rules.target_weight,
                    "status": "skipped_insufficient_budget_for_one_lot",
                    "minimum_one_lot_cash": one_lot_cash,
                    "target_cash": target_cash,
                    "reason": "Cash is not reallocated to preserve the declared equal-weight candidate rule.",
                }
            )
            continue

        notional = price * quantity
        buy_fees = a_share_trade_fees(notional, "buy", rules)
        sell_fees_at_reference = a_share_trade_fees(notional, "sell", rules)
        buy_cash = notional + buy_fees["total"]
        orders.append(
            {
                "rank": rank,
                "instrument": instrument,
                "name": name,
                "reference_close": price,
                "target_weight": rules.target_weight,
                "status": "planned_at_reference_price",
                "quantity": quantity,
                "board_lots": quantity // rules.lot_size,
                "notional": notional,
                "buy_fees": buy_fees,
                "estimated_buy_cash": buy_cash,
                "estimated_sell_fees_at_reference": sell_fees_at_reference,
                "estimated_round_trip_fees_at_reference": buy_fees["total"] + sell_fees_at_reference["total"],
                "actual_portfolio_weight": buy_cash / capital,
            }
        )

    planned = [order for order in orders if order["status"] == "planned_at_reference_price"]
    total_buy_cash = float(sum(order["estimated_buy_cash"] for order in planned))
    max_buy_cash = capital * rules.max_gross_exposure
    if total_buy_cash > max_buy_cash + 1e-9:
        raise RuntimeError("lot plan exceeds configured max_gross_exposure")
    return {
        "capital": capital,
        "rules": {
            "lot_size": rules.lot_size,
            "commission_rate": rules.commission_rate,
            "commission_min": rules.commission_min,
            "transfer_fee_rate": rules.transfer_fee_rate,
            "stamp_duty_rate": rules.stamp_duty_rate,
            "max_gross_exposure": rules.max_gross_exposure,
            "target_weight": rules.target_weight,
        },
        "target_cash_per_candidate": target_cash,
        "max_pilot_cash": max_buy_cash,
        "orders": orders,
        "summary": {
            "requested_candidates": len(candidates),
            "planned_candidates": len(planned),
            "skipped_candidates": len(candidates) - len(planned),
            "estimated_buy_cash": total_buy_cash,
            "actual_gross_exposure": total_buy_cash / capital,
            "cash_remaining_after_plan": capital - total_buy_cash,
            "unused_pilot_budget": max_buy_cash - total_buy_cash,
        },
        "limitations": [
            "Reference close is for sizing only; it is not a live quote, order price, or buy instruction.",
            "The plan does not model intraday price movement, limit-up/limit-down, suspension, slippage, or order fills.",
            "Skipped slots are not reallocated; changing that rule requires a separately tested portfolio construction policy.",
        ],
    }


def file_sha256(path: Path) -> str:
    """Return the content fingerprint recorded alongside every experiment."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def qlib_symbol(code: Any) -> str | None:
    """Convert a mainland A-share code to the Qlib symbol form used locally."""

    raw = str(code).strip().zfill(6)
    if raw.startswith("6"):
        return f"SH{raw}"
    if raw.startswith(("0", "3")):
        return f"SZ{raw}"
    return None


def annual_report_dates(start_year: int, end_year: int) -> list[str]:
    """Return inclusive annual accounting-period dates in ISO form."""

    if end_year < start_year:
        raise ValueError("--end-year must not be earlier than --start-year")
    return [f"{year}-12-31" for year in range(start_year, end_year + 1)]


def _eastmoney_request(session: requests.Session, report_date: str, page_number: int) -> dict[str, Any]:
    params = {
        "reportName": EASTMONEY_REPORT,
        "columns": "ALL",
        "filter": f"(REPORTDATE='{report_date}')",
        "pageNumber": page_number,
        "pageSize": 500,
        "sortTypes": "1,1",
        "sortColumns": "SECURITY_CODE,NOTICE_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    errors: list[str] = []
    for attempt in range(4):
        try:
            response = session.get(EASTMONEY_DATACENTER_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload.get("result"), dict):
                raise ValueError("Eastmoney response does not contain a result object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"cannot fetch annual report {report_date} page {page_number}: {errors[-1]}")


def fetch_annual_report_rows(session: requests.Session, report_date: str) -> list[dict[str, Any]]:
    """Fetch all pages for one annual report period from the public endpoint."""

    first = _eastmoney_request(session, report_date, page_number=1)
    result = first["result"]
    pages = int(result.get("pages") or 0)
    if pages < 1:
        return []
    rows = list(result.get("data") or [])
    for page_number in range(2, pages + 1):
        payload = _eastmoney_request(session, report_date, page_number=page_number)
        rows.extend((payload.get("result") or {}).get("data") or [])
    return rows


def normalize_fundamental_rows(rows: Iterable[dict[str, Any]], report_date: str) -> pd.DataFrame:
    """Reduce provider-specific financial rows to the PIT fields needed by research.

    Eastmoney can expose later corrections for a prior report.  Keeping the
    earliest notice per instrument/report period is a conservative approximation
    of the first public disclosure, but it is not an immutable vendor PIT data
    set; that caveat is carried into every experiment record.
    """

    raw = pd.DataFrame(rows)
    if raw.empty:
        return pd.DataFrame(columns=FUNDAMENTAL_COLUMNS)
    frame = pd.DataFrame(
        {
            "instrument": raw.get("SECURITY_CODE", pd.Series(dtype="object")).map(qlib_symbol),
            "report_date": pd.to_datetime(report_date),
            "announcement_date": pd.to_datetime(raw.get("NOTICE_DATE"), errors="coerce"),
            "roe": pd.to_numeric(raw.get("WEIGHTAVG_ROE"), errors="coerce"),
            "net_profit": pd.to_numeric(raw.get("PARENT_NETPROFIT"), errors="coerce"),
            "revenue_yoy": pd.to_numeric(raw.get("YSTZ"), errors="coerce"),
            "profit_yoy": pd.to_numeric(raw.get("SJLTZ"), errors="coerce"),
        }
    )
    frame = frame.dropna(subset=["instrument", "announcement_date"])
    frame = frame.sort_values(["instrument", "report_date", "announcement_date"], kind="stable")
    return frame.drop_duplicates(["instrument", "report_date"], keep="first").reset_index(drop=True)


def sync_fundamentals(start_year: int, end_year: int, output: Path, manifest: Path) -> dict[str, Any]:
    """Download annual quality inputs and write an auditable local snapshot."""

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://data.eastmoney.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        }
    )
    frames: list[pd.DataFrame] = []
    counts: dict[str, int] = {}
    for report_date in annual_report_dates(start_year, end_year):
        rows = fetch_annual_report_rows(session, report_date)
        normalized = normalize_fundamental_rows(rows, report_date)
        frames.append(normalized)
        counts[report_date] = len(normalized)
        print(f"{report_date}: {len(normalized)} normalized annual-report rows")

    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=FUNDAMENTAL_COLUMNS)
    merged = merged.sort_values(["instrument", "report_date", "announcement_date"], kind="stable")
    merged = merged.drop_duplicates(["instrument", "report_date"], keep="first").reset_index(drop=True)
    if merged.empty:
        raise RuntimeError("annual-report sync produced no usable rows")
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "report_dates": annual_report_dates(start_year, end_year),
        "rows_by_report_date": counts,
        "rows_written": len(merged),
        "output": str(output.resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "The public source is queried as it exists today; later corrections may not reproduce the original disclosure values.",
            "The research join waits until the trading day after announcement_date, but it is not a substitute for an exchange-grade point-in-time fundamentals vendor.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return result


def load_fundamentals(path: Path) -> pd.DataFrame:
    """Load and validate the local accounting-quality snapshot."""

    if not path.exists():
        raise FileNotFoundError(f"fundamental snapshot does not exist: {path}; run sync-fundamentals first")
    frame = pd.read_parquet(path)
    missing = sorted(set(FUNDAMENTAL_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"fundamental snapshot is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, list(FUNDAMENTAL_COLUMNS)].copy()
    for column in ("report_date", "announcement_date"):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    for column in ("roe", "net_profit", "revenue_yoy", "profit_yoy"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["instrument", "report_date", "announcement_date"])
    return frame.sort_values(["instrument", "announcement_date", "report_date"], kind="stable").reset_index(drop=True)


def _first_trading_day_after(calendar: pd.DatetimeIndex, announced: pd.Series) -> pd.Series:
    """Map announcements to the strictly next local trading day.

    The source does not tell us whether a filing was made before market open,
    therefore using the next session avoids same-day information leakage.
    """

    lookup = calendar.searchsorted(pd.DatetimeIndex(announced), side="right")
    mapped = pd.Series(pd.NaT, index=announced.index, dtype="datetime64[ns]")
    valid = lookup < len(calendar)
    mapped.loc[valid] = calendar.take(lookup[valid]).values
    return mapped


def attach_quality_asof(market: pd.DataFrame, fundamentals: pd.DataFrame, max_age_days: int = 550) -> pd.DataFrame:
    """Attach only already-announced accounting data to every market row.

    The operation is performed on a combined per-instrument timeline instead
    of a global ``merge_asof`` so a filing cannot be carried into another
    instrument.  ``quality_effective_date`` is retained for audit checks.
    """

    required_market = {"instrument", "datetime"}
    if missing := sorted(required_market - set(market.columns)):
        raise ValueError(f"market frame is missing columns: {', '.join(missing)}")
    market = market.reset_index(drop=True).copy()
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(market["datetime"]).dropna().unique()))
    events = fundamentals.copy()
    events["quality_effective_date"] = _first_trading_day_after(calendar, events["announcement_date"])
    events = events.dropna(subset=["quality_effective_date"])
    events = events.sort_values(
        ["instrument", "quality_effective_date", "report_date", "announcement_date"], kind="stable"
    ).drop_duplicates(["instrument", "quality_effective_date"], keep="last")

    quality_columns = ["report_date", "announcement_date", "roe", "net_profit", "revenue_yoy", "profit_yoy", "quality_effective_date"]
    daily = market[["instrument", "datetime"]].copy()
    daily["_kind"] = 1
    daily["_row"] = np.arange(len(daily))
    for column in ("report_date", "announcement_date", "quality_effective_date"):
        daily[column] = pd.NaT
    for column in ("roe", "net_profit", "revenue_yoy", "profit_yoy"):
        daily[column] = np.nan
    event_rows = events.rename(columns={"quality_effective_date": "datetime"})[
        ["instrument", "datetime", *[column for column in quality_columns if column != "quality_effective_date"]]
    ].copy()
    event_rows["quality_effective_date"] = event_rows["datetime"]
    event_rows["_kind"] = 0
    event_rows["_row"] = np.nan
    combined = pd.concat([daily, event_rows], ignore_index=True, sort=False)
    combined = combined.sort_values(["instrument", "datetime", "_kind"], kind="stable")
    combined[quality_columns] = combined.groupby("instrument", sort=False)[quality_columns].ffill()
    attached = combined.loc[combined["_row"].notna(), ["_row", *quality_columns]].copy()
    attached["_row"] = attached["_row"].astype(int)
    result = market.copy()
    result = result.join(attached.set_index("_row"), how="left")
    result["quality_age_days"] = (pd.to_datetime(result["datetime"]) - pd.to_datetime(result["quality_effective_date"])).dt.days
    result["quality_eligible"] = (
        result["roe"].ge(5.0)
        & result["net_profit"].gt(0.0)
        & result["revenue_yoy"].gt(0.0)
        & result["profit_yoy"].gt(0.0)
        & result["quality_age_days"].between(0, max_age_days)
    )
    return result


def load_market_data(provider_uri: Path, start: str, end: str | None, batch_size: int) -> pd.DataFrame:
    """Load the local buyable universe and precompute only non-forward factors."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import qlib
    from qlib.data import D

    if batch_size < 1:
        raise ValueError("--batch-size must be positive")
    provider_uri = provider_uri.expanduser().resolve()
    if not provider_uri.exists():
        raise FileNotFoundError(f"Qlib provider directory does not exist: {provider_uri}")
    qlib.init(provider_uri=str(provider_uri), region="cn", kernels=1)
    market = D.instruments(market="buyable_main_chinext")
    instruments = D.list_instruments(market, start_time=start, end_time=end, as_list=True)
    if not instruments:
        raise RuntimeError("buyable_main_chinext has no local instruments in the requested window")
    fields = {
        "close": "$close",
        "open": "$open",
        "momentum_3": "$close/Ref($close, 3) - 1",
        "momentum_5": "$close/Ref($close, 5) - 1",
        "momentum_10": "$close/Ref($close, 10) - 1",
        "volume_surge": "Mean($volume, 5)/Mean($volume, 20) - 1",
        "turnover_surge": "Mean($turnover, 5)/Mean($turnover, 20) - 1",
        "volatility_10": "Std($close/Ref($close, 1) - 1, 10)",
        "near_high_20": "$close/Max($high, 20) - 1",
        "intraday_strength": "$close/$open - 1",
    }
    frames: list[pd.DataFrame] = []
    expressions = list(fields.values())
    for offset in range(0, len(instruments), batch_size):
        batch = instruments[offset : offset + batch_size]
        frame = D.features(batch, expressions, start_time=start, end_time=end, freq="day")
        frame = frame.rename(columns={expression: name for name, expression in fields.items()}).reset_index()
        frames.append(frame)
        print(f"loaded {min(offset + len(batch), len(instruments))}/{len(instruments)} instruments")
    result = pd.concat(frames, ignore_index=True)
    result["datetime"] = pd.to_datetime(result["datetime"])
    result["instrument"] = result["instrument"].astype(str)
    return result.sort_values(["datetime", "instrument"], kind="stable").reset_index(drop=True)


def rank_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Turn raw factors into daily comparable [0, 1] scores without look-ahead."""

    result = frame.copy()
    raw_columns = [
        "momentum_3",
        "momentum_5",
        "momentum_10",
        "volume_surge",
        "turnover_surge",
        "volatility_10",
        "near_high_20",
        "intraday_strength",
        "roe",
        "revenue_yoy",
        "profit_yoy",
    ]
    for column in raw_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    eligible = result["quality_eligible"].fillna(False)
    for column in raw_columns:
        ranked = result.loc[eligible].groupby("datetime", sort=False)[column].rank(pct=True)
        result.loc[eligible, f"rank_{column}"] = ranked
    result["reversal_3"] = 1.0 - result["rank_momentum_3"]
    result["volume_dry_up"] = 1.0 - result["rank_volume_surge"]
    result["volatility_target"] = 1.0 - (result["rank_volatility_10"] - 0.65).abs()
    result["quality_score"] = result[["rank_roe", "rank_revenue_yoy", "rank_profit_yoy"]].mean(axis=1)
    result["momentum_5"] = result["rank_momentum_5"]
    result["momentum_10"] = result["rank_momentum_10"]
    result["volume_surge"] = result["rank_volume_surge"]
    result["turnover_surge"] = result["rank_turnover_surge"]
    result["near_high_20"] = result["rank_near_high_20"]
    result["intraday_strength"] = result["rank_intraday_strength"]
    return result


def score_candidate(ranked: pd.DataFrame, candidate: Candidate) -> pd.DataFrame:
    """Apply a predeclared factor mix and discard rows with incomplete signals."""

    if not math.isclose(sum(candidate.weights.values()), 1.0, abs_tol=1e-9):
        raise ValueError(f"candidate weights must sum to one: {candidate.name}")
    missing = sorted(set(candidate.weights) - set(ranked.columns))
    if missing:
        raise ValueError(f"candidate {candidate.name} refers to missing factors: {', '.join(missing)}")
    result = ranked.loc[ranked["quality_eligible"].fillna(False)].copy()
    result["score"] = sum(result[column] * weight for column, weight in candidate.weights.items())
    required = ["instrument", "datetime", "open", "close", "score", *candidate.weights]
    return result.dropna(subset=required)


def evaluate_candidate(
    scored: pd.DataFrame,
    candidate: Candidate,
    hold_days: int,
    topk: int,
    open_cost: float,
    close_cost: float,
    development_end: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run non-overlapping five-session cohorts from close signal to next-open entry.

    A signal is formed after the market close.  The portfolio buys on the next
    session's open and sells on the close after ``hold_days`` sessions.  This
    deliberately avoids using a future price in factor ranking.
    """

    if hold_days < 1 or topk < 1:
        raise ValueError("--hold-days and --topk must both be positive")
    calendar = pd.DatetimeIndex(sorted(scored["datetime"].unique()))
    if len(calendar) <= hold_days + 1:
        raise ValueError("research window is too short for the requested holding period")
    date_to_position = {date: position for position, date in enumerate(calendar)}
    rebalances = calendar[: -(hold_days + 1) : hold_days]
    pool = scored.loc[scored["datetime"].isin(rebalances)].copy()
    pool = pool.sort_values(["datetime", "score", "instrument"], ascending=[True, False, True], kind="stable")
    selected = pool.groupby("datetime", sort=False).head(topk).copy()
    selected["entry_date"] = selected["datetime"].map(lambda value: calendar[date_to_position[value] + 1])
    selected["exit_date"] = selected["datetime"].map(lambda value: calendar[date_to_position[value] + hold_days])

    quotes = scored[["datetime", "instrument", "open", "close"]].drop_duplicates(["datetime", "instrument"])
    entry = quotes.rename(columns={"datetime": "entry_date", "open": "entry_open"})[["entry_date", "instrument", "entry_open"]]
    exit_quote = quotes.rename(columns={"datetime": "exit_date", "close": "exit_close"})[["exit_date", "instrument", "exit_close"]]
    trades = selected.merge(entry, on=["entry_date", "instrument"], how="left")
    trades = trades.merge(exit_quote, on=["exit_date", "instrument"], how="left")
    trades = trades.dropna(subset=["entry_open", "exit_close"])
    trades = trades.loc[(trades["entry_open"] > 0) & (trades["exit_close"] > 0)].copy()
    trades["gross_return"] = trades["exit_close"] / trades["entry_open"] - 1.0
    trades["net_return"] = (1.0 - open_cost) * (1.0 + trades["gross_return"]) * (1.0 - close_cost) - 1.0
    rounds = (
        trades.groupby(["datetime", "entry_date", "exit_date"], sort=True)
        .agg(net_return=("net_return", "mean"), gross_return=("gross_return", "mean"), holdings=("instrument", "nunique"))
        .reset_index()
        .rename(columns={"datetime": "signal_date"})
    )
    rounds = rounds.loc[rounds["holdings"] >= max(5, math.ceil(topk * 0.8))].copy()
    rounds["segment"] = np.where(rounds["signal_date"] <= pd.Timestamp(development_end), "development", "test")
    summary = {
        "candidate": candidate.name,
        "description": candidate.description,
        "weights": candidate.weights,
        "development": return_metrics(rounds.loc[rounds["segment"] == "development"], hold_days),
        "test": return_metrics(rounds.loc[rounds["segment"] == "test"], hold_days),
        "metrics_by_signal_year": {
            str(year): return_metrics(group, hold_days)
            for year, group in rounds.groupby(rounds["signal_date"].dt.year, sort=True)
        },
        "cohorts": [
            {
                "signal_date": row.signal_date.date().isoformat(),
                "entry_date": row.entry_date.date().isoformat(),
                "exit_date": row.exit_date.date().isoformat(),
                "segment": row.segment,
                "gross_return": float(row.gross_return),
                "net_return": float(row.net_return),
                "holdings": int(row.holdings),
            }
            for row in rounds.itertuples(index=False)
        ],
    }
    development = summary["development"]
    # Precommitted selection function.  The test metrics are deliberately not
    # referenced here: they remain an untouched check on the winner.
    summary["development_selection_score"] = (
        development["annualized_return"] - 0.5 * abs(development["max_drawdown"])
        if development["rounds"]
        else None
    )
    return rounds, summary


def return_metrics(rounds: pd.DataFrame, hold_days: int) -> dict[str, float | int | None]:
    """Calculate net return, risk and drawdown from non-overlapping cohorts."""

    if rounds.empty:
        return {
            "rounds": 0,
            "gross_cumulative_return": None,
            "net_cumulative_return": None,
            "annualized_return": None,
            "annualized_volatility": None,
            "sharpe_like": None,
            "max_drawdown": None,
            "win_rate": None,
            "median_holdings": None,
        }
    net = rounds["net_return"].astype(float)
    gross = rounds["gross_return"].astype(float)
    equity = (1.0 + net).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    periods_per_year = 252.0 / hold_days
    annualized_volatility = float(net.std(ddof=0) * math.sqrt(periods_per_year))
    return {
        "rounds": int(len(rounds)),
        "gross_cumulative_return": float((1.0 + gross).prod() - 1.0),
        "net_cumulative_return": float(equity.iloc[-1] - 1.0),
        "annualized_return": float(equity.iloc[-1] ** (periods_per_year / len(rounds)) - 1.0),
        "annualized_volatility": annualized_volatility,
        "sharpe_like": float(net.mean() / net.std(ddof=0) * math.sqrt(periods_per_year)) if net.std(ddof=0) else None,
        "max_drawdown": float(drawdown.min()),
        "win_rate": float((net > 0).mean()),
        "median_holdings": float(rounds["holdings"].median()),
    }


def choose_winner(summaries: list[dict[str, Any]]) -> str | None:
    """Choose only from development-period results; reject missing metrics."""

    eligible = [item for item in summaries if item.get("development_selection_score") is not None]
    if not eligible:
        return None
    winner = max(eligible, key=lambda item: float(item["development_selection_score"]))
    return str(winner["candidate"])


def candidate_by_name(name: str) -> Candidate:
    """Return a predefined candidate, rejecting arbitrary unrecorded weights."""

    for candidate in CANDIDATES:
        if candidate.name == name:
            return candidate
    choices = ", ".join(candidate.name for candidate in CANDIDATES)
    raise ValueError(f"unknown candidate {name!r}; choose one of: {choices}")


def latest_provider_date(provider_uri: Path) -> pd.Timestamp:
    """Read the latest local Qlib session without consulting a network source."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import qlib
    from qlib.data import D

    provider_uri = provider_uri.expanduser().resolve()
    qlib.init(provider_uri=str(provider_uri), region="cn", kernels=1)
    calendar = pd.DatetimeIndex(D.calendar(freq="day"))
    if calendar.empty:
        raise RuntimeError("the local Qlib provider has no daily calendar")
    return pd.Timestamp(calendar[-1])


def _universe_metadata() -> dict[str, dict[str, Any]]:
    """Load latest local names and ST flags for an explicit screen safety filter."""

    path = DATA_ROOT / "metadata" / "universe_latest.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(item["symbol"]): {
            "name": str(item.get("name") or ""),
            "is_st": bool(item.get("is_st", False)),
        }
        for item in payload
    }


def filter_st_candidates(screen: pd.DataFrame, metadata: dict[str, dict[str, Any]], include_st: bool) -> pd.DataFrame:
    """Exclude current ST-tagged names by default from a buyable research screen."""

    if include_st:
        return screen
    is_st = screen["instrument"].map(lambda symbol: bool(metadata.get(symbol, {}).get("is_st", False)))
    return screen.loc[~is_st].copy()


def run_latest_screen(args: argparse.Namespace) -> dict[str, Any]:
    """Create an auditable latest-available candidate screen from local data."""

    candidate = candidate_by_name(args.candidate)
    provider_uri = Path(args.provider_uri).expanduser()
    fundamentals_path = Path(args.fundamentals).expanduser()
    latest_local_date = latest_provider_date(provider_uri)
    end = args.as_of or latest_local_date.date().isoformat()
    start = args.start or (pd.Timestamp(end) - pd.Timedelta(days=args.lookback_calendar_days)).date().isoformat()
    fundamentals = load_fundamentals(fundamentals_path)
    market = load_market_data(provider_uri, start=start, end=end, batch_size=args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    scored = score_candidate(ranked, candidate)
    as_of = pd.Timestamp(scored["datetime"].max())
    screen = scored.loc[scored["datetime"] == as_of].sort_values(["score", "instrument"], ascending=[False, True])
    metadata = _universe_metadata()
    screen = filter_st_candidates(screen, metadata, include_st=args.include_st)
    screen = screen.head(args.topk).copy()
    if len(screen) < args.topk:
        raise RuntimeError(f"only {len(screen)} complete candidates exist on {as_of.date()}, need {args.topk}")
    factor_columns = list(candidate.weights)
    records: list[dict[str, Any]] = []
    for rank, row in enumerate(screen.itertuples(index=False), start=1):
        records.append(
            {
                "rank": rank,
                "instrument": row.instrument,
                "name": str(metadata.get(row.instrument, {}).get("name", "")),
                "score": float(row.score),
                "reference_close": float(row.close),
                "roe": float(row.roe),
                "revenue_yoy": float(row.revenue_yoy),
                "profit_yoy": float(row.profit_yoy),
                "quality_report_date": pd.Timestamp(row.report_date).date().isoformat(),
                "quality_announcement_date": pd.Timestamp(row.announcement_date).date().isoformat(),
                "quality_age_days": int(row.quality_age_days),
                "factor_percentiles": {column: float(getattr(row, column)) for column in factor_columns},
            }
        )
    run_id = _timestamp()
    report = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "latest_available_research_screen_not_trade_instruction",
        "as_of": as_of.date().isoformat(),
        "latest_local_provider_date": latest_local_date.date().isoformat(),
        "candidate": candidate.name,
        "description": candidate.description,
        "weights": candidate.weights,
        "universe": "buyable_main_chinext",
        "exclude_current_st": not args.include_st,
        "topk": args.topk,
        "quality_gate": {
            "source": str(fundamentals_path.resolve()),
            "sha256": file_sha256(fundamentals_path),
            "annual_report_only": True,
            "effective_date": "strictly next local trading day after announcement_date",
        },
        "top_candidates": records,
        "limitations": [
            "This is a model screen using the latest locally available daily close, not a buy/sell instruction.",
            "It does not model intraday news, current-day limits, suspensions, lot-size constraints, tax, or order execution.",
            "A public financial-data snapshot and a current listing universe cannot eliminate accounting-restatement and survivorship bias.",
        ],
    }
    root = Path(args.experiment_root).expanduser()
    destination = root / f"{run_id}_screen_{candidate.name}.json"
    _atomic_write_text(destination, json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    report["screen_path"] = str(destination.resolve())
    return report


def run_execution_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Size a fresh model screen into auditable A-share board-lot plans."""

    screen_path = Path(args.screen_path).expanduser().resolve()
    screen = json.loads(screen_path.read_text(encoding="utf-8"))
    candidates = list(screen.get("top_candidates") or [])[: args.topk]
    if not candidates:
        raise ValueError("screen file does not contain top_candidates")
    missing_prices = [str(item.get("instrument", "")) for item in candidates if "reference_close" not in item]
    if missing_prices:
        raise ValueError(
            "screen file lacks reference_close for "
            + ", ".join(missing_prices)
            + "; generate a new screen with the current script before planning"
        )
    rules = AShareExecutionRules(
        lot_size=args.lot_size,
        commission_rate=args.commission_rate,
        commission_min=args.commission_min,
        transfer_fee_rate=args.transfer_fee_rate,
        stamp_duty_rate=args.stamp_duty_rate,
        max_gross_exposure=args.max_gross_exposure,
        target_weight=args.target_weight,
    )
    capitals = tuple(args.capital) if args.capital else DEFAULT_PILOT_CAPITALS
    plans = [plan_lot_orders(candidates, capital, rules) for capital in capitals]
    report = {
        "run_id": _timestamp(),
        "status": "completed",
        "purpose": "research_execution_plan_not_trade_instruction",
        "source_screen": str(screen_path),
        "screen_as_of": screen.get("as_of"),
        "candidate": screen.get("candidate"),
        "candidate_count": len(candidates),
        "reference_price": "latest local daily close recorded in the source screen",
        "plans": plans,
        "fee_assumptions": {
            "commission": "0.01% per side by default (the user's stated RMB 1 per RMB 10,000), with no minimum by default",
            "transfer_fee": "0.002% per side by default",
            "stamp_duty": "0.05% on the sell side by default",
            "exchange_handling_fee": "not separately added to avoid double-counting an all-in broker commission quote",
        },
    }
    output = Path(args.output).expanduser() if args.output else screen_path.parent / f"{report['run_id']}_execution_plan.json"
    _atomic_write_text(output, json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    report["plan_path"] = str(output.resolve())
    return report


def write_experiment_record(root: Path, record: dict[str, Any]) -> Path:
    """Persist one self-contained candidate result without overwriting history."""

    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"{record['run_id']}_{record['candidate']}.json"
    _atomic_write_text(destination, json.dumps(record, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return destination


def run_research(args: argparse.Namespace) -> dict[str, Any]:
    """Run all candidate combinations and write a record for each one."""

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    run_id = _timestamp()
    common = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "research_only_not_investment_advice",
        "strategy": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "rebalancing": "non_overlapping_every_holding_period",
            "topk": args.topk,
            "signal_time": "market close",
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "annual_report_only": True,
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
            "requirements": {
                "weighted_average_roe_gte": 5.0,
                "parent_net_profit_gt": 0.0,
                "revenue_yoy_gt": 0.0,
                "profit_yoy_gt": 0.0,
            },
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "market_rows": int(len(market)),
            "eligible_rows": int(market["quality_eligible"].sum()),
            "development_end": args.development_end,
        },
        "limitations": [
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
            "Eastmoney public data are a present-day snapshot; retaining the earliest visible notice date reduces but does not eliminate accounting restatement bias.",
            "Prices are qfq-adjusted and the provider lacks Qlib restoration factors; this is not an exact lot-size, dividend, tax, or limit-up/limit-down execution simulation.",
            "The winner is selected only on development data. Its later test result is evidence for further research, never a promise of future return.",
        ],
    }
    summaries: list[dict[str, Any]] = []
    records: list[tuple[dict[str, Any], Path]] = []
    for candidate in CANDIDATES:
        scored = score_candidate(ranked, candidate)
        _, summary = evaluate_candidate(
            scored,
            candidate,
            hold_days=args.hold_days,
            topk=args.topk,
            open_cost=args.open_cost,
            close_cost=args.close_cost,
            development_end=args.development_end,
        )
        record = {**common, **summary, "candidate": candidate.name}
        destination = write_experiment_record(experiment_root, record)
        records.append((record, destination))
        summaries.append(summary)
        print(f"{candidate.name}: {destination}")
    winner = choose_winner(summaries)
    for record, destination in records:
        record["selected_by_development"] = record["candidate"] == winner
        _atomic_write_text(destination, json.dumps(record, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    study = {
        "run_id": run_id,
        "status": "completed",
        "selection_rule": "maximize development annualized_return - 0.5 * abs(development max_drawdown)",
        "winner_selected_on_development_only": winner,
        "experiments": [
            {
                "candidate": record["candidate"],
                "path": str(destination.resolve()),
                "development_selection_score": record["development_selection_score"],
                "development": record["development"],
                "test": record["test"],
            }
            for record, destination in records
        ],
    }
    study_path = experiment_root / f"{run_id}_study.json"
    _atomic_write_text(study_path, json.dumps(study, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    study["study_path"] = str(study_path.resolve())
    return study


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync = subparsers.add_parser("sync-fundamentals", help="download annual ROE/profit/revenue quality inputs")
    sync.add_argument("--start-year", type=int, default=2022)
    sync.add_argument("--end-year", type=int, default=2025)
    sync.add_argument("--output", default=str(DEFAULT_FUNDAMENTALS))
    sync.add_argument("--manifest", default=str(DEFAULT_FUNDAMENTAL_MANIFEST))

    run = subparsers.add_parser("run", help="run the predeclared short-horizon factor sweep")
    run.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    run.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    run.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    run.add_argument("--start", default="2024-01-01")
    run.add_argument("--end", help="defaults to the local Qlib calendar end")
    run.add_argument("--development-end", default="2025-12-31")
    run.add_argument("--hold-days", type=int, default=5)
    run.add_argument("--topk", type=int, default=30)
    run.add_argument("--open-cost", type=float, default=0.0015)
    run.add_argument("--close-cost", type=float, default=0.0025)
    run.add_argument("--max-quality-age-days", type=int, default=550)
    run.add_argument("--batch-size", type=int, default=500)

    screen = subparsers.add_parser("screen", help="rank latest locally available candidates with a recorded factor mix")
    screen.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    screen.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    screen.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    screen.add_argument("--candidate", default="quality_trend_pullback")
    screen.add_argument("--as-of", help="latest local daily session by default")
    screen.add_argument("--start", help="optional feature-history start; defaults to a local rolling lookback")
    screen.add_argument("--lookback-calendar-days", type=int, default=100)
    screen.add_argument("--topk", type=int, default=20)
    screen.add_argument("--include-st", action="store_true", help="include current ST-tagged names; disabled by default")
    screen.add_argument("--max-quality-age-days", type=int, default=550)
    screen.add_argument("--batch-size", type=int, default=500)

    plan = subparsers.add_parser(
        "plan", help="turn a fresh screen into A-share board-lot plans for the configured pilot capital"
    )
    plan.add_argument("--screen-path", required=True, help="path emitted by the screen command")
    plan.add_argument("--topk", type=int, default=3, help="number of ranked candidates to size")
    plan.add_argument(
        "--capital",
        type=float,
        action="append",
        help="repeat for one or more account sizes; defaults to RMB 200k",
    )
    plan.add_argument("--lot-size", type=int, default=100)
    plan.add_argument("--commission-rate", type=float, default=0.0001, help="per-side broker commission; default is RMB 1 per RMB 10k")
    plan.add_argument("--commission-min", type=float, default=0.0, help="per-order commission minimum; default follows the supplied zero-minimum quote")
    plan.add_argument("--transfer-fee-rate", type=float, default=0.00002, help="per-side transfer/settlement fee")
    plan.add_argument("--stamp-duty-rate", type=float, default=0.0005, help="sell-side stamp duty rate")
    plan.add_argument("--max-gross-exposure", type=float, default=0.15)
    plan.add_argument("--target-weight", type=float, default=0.05)
    plan.add_argument("--output", help="optional JSON output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "sync-fundamentals":
        report = sync_fundamentals(args.start_year, args.end_year, Path(args.output), Path(args.manifest))
    elif args.command == "run":
        report = run_research(args)
    elif args.command == "plan":
        report = run_execution_plan(args)
    else:
        report = run_latest_screen(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
