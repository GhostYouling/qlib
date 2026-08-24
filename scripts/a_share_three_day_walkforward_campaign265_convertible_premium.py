#!/usr/bin/env python3
"""Pure zero-network Campaign265 convertible-premium adapter and formula."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import unicodedata
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CONTRACT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_convertible_premium_source_contract_20260824.json"
)
SOURCE_CONTRACT_SHA256 = (
    "efe7884d3ea0fd7f974e0d3347432e68e9e01ceefe0e6ebdca7fdd3e6349301c"
)

FACTOR_NAME = "convertible_bond_equity_parity_premium_compression_3s"
FACTOR_DIRECTION = "higher"
PROVIDER = "tushare"
CB_BASIC_FIELDS = (
    "ts_code",
    "cb_type",
    "stk_code",
    "list_date",
    "delist_date",
    "exchange",
)
CB_DAILY_FIELDS = ("ts_code", "trade_date", "amount", "cb_over_rate")
NORMALIZED_BASIC_FIELDS = (
    "bond_code",
    "bond_type",
    "instrument",
    "list_date",
    "delist_date",
    "exchange",
)
NORMALIZED_DAILY_FIELDS = (
    "bond_code",
    "trade_date",
    "amount",
    "cb_over_rate",
)
FACTOR_OUTPUT_FIELDS = (
    "signal_session",
    "lag_session",
    "instrument",
    "factor_name",
    "factor_direction",
    "active_cb_count",
    "eligible_cb_count",
    "factor_value",
)
CB_DAILY_ROW_LIMIT = 2000
LAG_ACCEPTED_SESSIONS = 3

SSE_EQUITY_PREFIXES = frozenset(("600", "601", "603", "605", "688", "689"))
SZSE_EQUITY_PREFIXES = frozenset(("000", "001", "002", "003", "300", "301"))


class Campaign265AdapterError(RuntimeError):
    """Raised when an input violates the immutable Campaign265 contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source_contract(path: Path = SOURCE_CONTRACT) -> dict[str, Any]:
    """Load and semantically verify the frozen zero-row source contract."""

    target = path.expanduser().resolve()
    if target != SOURCE_CONTRACT.resolve():
        raise Campaign265AdapterError("Campaign265 source-contract path changed")
    if not target.is_file() or _sha256(target) != SOURCE_CONTRACT_SHA256:
        raise Campaign265AdapterError("Campaign265 source-contract fingerprint changed")
    contract = json.loads(target.read_text(encoding="utf-8"))
    source = contract.get("official_source_contract") or {}
    basic = source.get("cb_basic") or {}
    daily = source.get("cb_daily") or {}
    factor = contract.get("single_factor_definition") or {}
    next_stage = contract.get("mandatory_next_stage") or {}
    boundary = contract.get("research_boundary") or {}
    if not (
        contract.get("kind")
        == "a_share_three_day_walkforward_campaign265_convertible_premium_source_contract"
        and source.get("provider") == "Tushare Pro"
        and source.get("minimum_points_required") == 2000
        and source.get("five_thousand_points_required") is False
        and tuple(basic.get("exact_fields") or ()) == CB_BASIC_FIELDS
        and tuple(daily.get("exact_fields") or ()) == CB_DAILY_FIELDS
        and basic.get("single_call_limit") == CB_DAILY_ROW_LIMIT
        and daily.get("single_call_limit") == CB_DAILY_ROW_LIMIT
        and factor.get("name") == FACTOR_NAME
        and factor.get("score_direction") == FACTOR_DIRECTION
        and "cb_over_rate(t_minus_3) - cb_over_rate(t)"
        in str(factor.get("per_bond_formula"))
        and next_stage.get("provider_request_authorized_by_this_contract") is False
        and next_stage.get("candidate_or_comparator_value_authorized_by_this_contract")
        is False
        and boundary.get("provider_api_request_issued") is False
        and boundary.get("provider_credential_value_or_digest_read") is False
        and boundary.get("candidate_or_comparator_value_read") is False
        and boundary.get("historical_daily_price_or_forward_return_value_read") is False
    ):
        raise Campaign265AdapterError("Campaign265 source-contract semantics changed")
    return contract


def _normalize_text(
    value: Any, field: str, *, missing_allowed: bool = False
) -> str | None:
    if value is None or pd.isna(value):
        if missing_allowed:
            return None
        raise Campaign265AdapterError(f"{field} is missing")
    if not isinstance(value, str):
        raise Campaign265AdapterError(f"{field} must be text")
    normalized = unicodedata.normalize("NFKC", value).strip().upper()
    if not normalized:
        if missing_allowed:
            return None
        raise Campaign265AdapterError(f"{field} is empty")
    return normalized


def _normalize_tushare_code(value: Any, field: str) -> tuple[str, str, str]:
    normalized = _normalize_text(value, field)
    assert normalized is not None
    if (
        len(normalized) != 9
        or normalized[6] != "."
        or not normalized[:6].isascii()
        or not normalized[:6].isdecimal()
        or normalized[7:] not in {"SH", "SZ"}
    ):
        raise Campaign265AdapterError(
            f"{field} must be six ASCII digits plus .SH or .SZ"
        )
    return normalized, normalized[:6], normalized[7:]


def _normalize_exchange(value: Any) -> str:
    normalized = _normalize_text(value, "exchange")
    if normalized in {"SSE", "SH"}:
        return "SH"
    if normalized in {"SZSE", "SZ"}:
        return "SZ"
    raise Campaign265AdapterError("exchange is outside SSE/SZSE/SH/SZ")


def _canonical_equity(value: Any) -> str:
    normalized, code, suffix = _normalize_tushare_code(value, "stk_code")
    prefix = code[:3]
    if suffix == "SH" and prefix in SSE_EQUITY_PREFIXES:
        return f"SH{code}"
    if suffix == "SZ" and prefix in SZSE_EQUITY_PREFIXES:
        return f"SZ{code}"
    raise Campaign265AdapterError(
        f"exact-CB {normalized} underlying is not a supported A-share identity"
    )


def _strict_provider_date(
    value: Any,
    field: str,
    *,
    missing_allowed: bool,
) -> date | None:
    if value is None or pd.isna(value):
        if missing_allowed:
            return None
        raise Campaign265AdapterError(f"{field} is missing")
    if not isinstance(value, str):
        raise Campaign265AdapterError(f"{field} must be strict YYYYMMDD text")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized:
        if missing_allowed:
            return None
        raise Campaign265AdapterError(f"{field} is empty")
    if len(normalized) != 8 or not normalized.isascii() or not normalized.isdecimal():
        raise Campaign265AdapterError(f"{field} must be strict YYYYMMDD")
    try:
        parsed = date(int(normalized[:4]), int(normalized[4:6]), int(normalized[6:]))
    except ValueError as exc:
        raise Campaign265AdapterError(f"{field} is not a valid date") from exc
    if parsed.strftime("%Y%m%d") != normalized:
        raise Campaign265AdapterError(f"{field} must be strict YYYYMMDD")
    return parsed


def _strict_iso_session(value: Any, field: str = "calendar session") -> date:
    if not isinstance(value, str):
        raise Campaign265AdapterError(f"{field} must be strict YYYY-MM-DD text")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if len(normalized) != 10:
        raise Campaign265AdapterError(f"{field} must be strict YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(normalized)
    except ValueError as exc:
        raise Campaign265AdapterError(f"{field} is not a valid date") from exc
    if parsed.isoformat() != normalized:
        raise Campaign265AdapterError(f"{field} must be strict YYYY-MM-DD")
    return parsed


def _assert_exact_frame_schema(
    frame: pd.DataFrame, fields: tuple[str, ...], source: str
) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise Campaign265AdapterError(f"{source} input must be a pandas DataFrame")
    if tuple(frame.columns) != fields:
        raise Campaign265AdapterError(
            f"{source} columns must exactly equal the frozen ordered projection"
        )


def canonicalize_cb_basic(
    raw: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int | bool]]:
    """Canonicalize only the frozen cb_basic projection without transport."""

    load_source_contract()
    _assert_exact_frame_schema(raw, CB_BASIC_FIELDS, "cb_basic")
    if raw.empty or len(raw) >= CB_DAILY_ROW_LIMIT:
        raise Campaign265AdapterError(
            "cb_basic is empty or reaches the source row limit"
        )

    rows: list[dict[str, Any]] = []
    rejected_type_rows = 0
    exact_cb_rows = 0
    seen_bonds: set[str] = set()
    for source_row in raw.itertuples(index=False, name=None):
        row = dict(zip(CB_BASIC_FIELDS, source_row, strict=True))
        bond_code, _, bond_suffix = _normalize_tushare_code(row["ts_code"], "ts_code")
        if bond_code in seen_bonds:
            raise Campaign265AdapterError(
                "cb_basic bond identity is not exactly unique"
            )
        seen_bonds.add(bond_code)
        bond_type = _normalize_text(row["cb_type"], "cb_type", missing_allowed=True)
        exchange = _normalize_exchange(row["exchange"])
        if exchange != bond_suffix:
            raise Campaign265AdapterError("bond suffix conflicts with exchange")
        list_date = _strict_provider_date(
            row["list_date"], "list_date", missing_allowed=True
        )
        delist_date = _strict_provider_date(
            row["delist_date"], "delist_date", missing_allowed=True
        )
        if (
            list_date is not None
            and delist_date is not None
            and delist_date < list_date
        ):
            raise Campaign265AdapterError("delist_date precedes list_date")
        instrument: str | None = None
        if bond_type == "CB":
            exact_cb_rows += 1
            instrument = _canonical_equity(row["stk_code"])
            if instrument[:2] != exchange:
                raise Campaign265AdapterError(
                    "exact-CB underlying conflicts with exchange"
                )
        else:
            rejected_type_rows += 1
        rows.append(
            {
                "bond_code": bond_code,
                "bond_type": bond_type,
                "instrument": instrument,
                "list_date": list_date,
                "delist_date": delist_date,
                "exchange": exchange,
            }
        )
    frame = pd.DataFrame(rows, columns=NORMALIZED_BASIC_FIELDS).sort_values(
        "bond_code", kind="stable"
    )
    frame = frame.reset_index(drop=True)
    return frame, {
        "source_rows": len(raw),
        "exact_cb_rows": exact_cb_rows,
        "rejected_non_cb_or_missing_type_rows": rejected_type_rows,
        "network_or_credential_access_performed": False,
        "forbidden_fields_read": False,
    }


def _optional_numeric(value: Any, field: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise Campaign265AdapterError(f"{field} must not be boolean")
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return math.nan
    return parsed if math.isfinite(parsed) else math.nan


def canonicalize_cb_daily(
    raw: pd.DataFrame,
    expected_session: str,
) -> tuple[pd.DataFrame, dict[str, int | bool]]:
    """Canonicalize one exact trade-date cb_daily projection without transport."""

    load_source_contract()
    _assert_exact_frame_schema(raw, CB_DAILY_FIELDS, "cb_daily")
    expected = _strict_iso_session(expected_session, "expected session")
    if len(raw) >= CB_DAILY_ROW_LIMIT:
        raise Campaign265AdapterError("cb_daily reaches the source row limit")

    rows: list[dict[str, Any]] = []
    seen_bonds: set[str] = set()
    for source_row in raw.itertuples(index=False, name=None):
        row = dict(zip(CB_DAILY_FIELDS, source_row, strict=True))
        bond_code, _, _ = _normalize_tushare_code(row["ts_code"], "ts_code")
        if bond_code in seen_bonds:
            raise Campaign265AdapterError("cb_daily bond/date identity is not unique")
        seen_bonds.add(bond_code)
        observed = _strict_provider_date(
            row["trade_date"], "trade_date", missing_allowed=False
        )
        if observed != expected:
            raise Campaign265AdapterError(
                "cb_daily trade_date differs from request date"
            )
        rows.append(
            {
                "bond_code": bond_code,
                "trade_date": expected,
                "amount": _optional_numeric(row["amount"], "amount"),
                "cb_over_rate": _optional_numeric(row["cb_over_rate"], "cb_over_rate"),
            }
        )
    frame = pd.DataFrame(rows, columns=NORMALIZED_DAILY_FIELDS).sort_values(
        "bond_code", kind="stable"
    )
    frame = frame.reset_index(drop=True)
    amount = frame["amount"].to_numpy(dtype=np.float64, copy=False)
    premium = frame["cb_over_rate"].to_numpy(dtype=np.float64, copy=False)
    endpoint_eligible = np.isfinite(amount) & (amount > 0.0) & np.isfinite(premium)
    return frame, {
        "source_rows": len(raw),
        "finite_positive_amount_and_premium_rows": int(endpoint_eligible.sum()),
        "ineligible_endpoint_rows": int((~endpoint_eligible).sum()),
        "network_or_credential_access_performed": False,
        "forbidden_fields_read": False,
    }


def _accepted_calendar(
    calendar: Sequence[str],
) -> tuple[tuple[str, ...], tuple[date, ...]]:
    if isinstance(calendar, (str, bytes)):
        raise Campaign265AdapterError("calendar must be an ordered sequence")
    labels = tuple(calendar)
    parsed = tuple(_strict_iso_session(value) for value in labels)
    if not labels or len(labels) != len(set(labels)):
        raise Campaign265AdapterError("calendar sessions must be nonempty and unique")
    if any(left >= right for left, right in zip(parsed, parsed[1:])):
        raise Campaign265AdapterError("calendar sessions must be strictly increasing")
    return labels, parsed


def _factor_universe(instruments: Sequence[str]) -> frozenset[str]:
    if isinstance(instruments, (str, bytes)):
        raise Campaign265AdapterError("factor universe must be a sequence")
    normalized: list[str] = []
    for value in instruments:
        text = _normalize_text(value, "factor-universe instrument")
        assert text is not None
        if (
            len(text) != 8
            or text[:2] not in {"SH", "SZ"}
            or not text[2:].isascii()
            or not text[2:].isdecimal()
        ):
            raise Campaign265AdapterError("factor-universe instrument is invalid")
        normalized.append(text)
    if len(normalized) != len(set(normalized)):
        raise Campaign265AdapterError("factor-universe instruments must be unique")
    return frozenset(normalized)


def _is_active(row: Any, session: date) -> bool:
    return bool(
        row.list_date is not None
        and row.list_date <= session
        and (row.delist_date is None or session <= row.delist_date)
    )


def compute_factor_on_session(
    cb_basic: pd.DataFrame,
    lag_cb_daily: pd.DataFrame,
    signal_cb_daily: pd.DataFrame,
    *,
    accepted_calendar: Sequence[str],
    factor_universe: Sequence[str],
    signal_session: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Compute the frozen issuer-median compression on one synthetic session."""

    load_source_contract()
    labels, parsed_calendar = _accepted_calendar(accepted_calendar)
    signal_date = _strict_iso_session(signal_session, "signal session")
    if signal_session not in labels:
        raise Campaign265AdapterError("signal session is not in the accepted calendar")
    signal_index = labels.index(signal_session)
    if signal_index < LAG_ACCEPTED_SESSIONS:
        raise Campaign265AdapterError("signal session has no exact t-minus-3 session")
    lag_session = labels[signal_index - LAG_ACCEPTED_SESSIONS]
    lag_date = parsed_calendar[signal_index - LAG_ACCEPTED_SESSIONS]
    universe = _factor_universe(factor_universe)

    basic, basic_stats = canonicalize_cb_basic(cb_basic)
    lag_daily, lag_stats = canonicalize_cb_daily(lag_cb_daily, lag_session)
    signal_daily, signal_stats = canonicalize_cb_daily(signal_cb_daily, signal_session)
    basic_bonds = frozenset(basic["bond_code"])
    observed_bonds = frozenset(lag_daily["bond_code"]) | frozenset(
        signal_daily["bond_code"]
    )
    if not observed_bonds.issubset(basic_bonds):
        raise Campaign265AdapterError("cb_daily bond lacks an exact cb_basic identity")

    lag_by_bond = lag_daily.set_index("bond_code", verify_integrity=True)
    signal_by_bond = signal_daily.set_index("bond_code", verify_integrity=True)
    active_by_instrument: dict[str, list[Any]] = {}
    for row in basic.itertuples(index=False):
        if (
            row.bond_type == "CB"
            and row.instrument in universe
            and _is_active(row, signal_date)
        ):
            active_by_instrument.setdefault(row.instrument, []).append(row)

    output: list[dict[str, Any]] = []
    total_eligible_bonds = 0
    for instrument in sorted(active_by_instrument):
        active_rows = active_by_instrument[instrument]
        compression: list[float] = []
        for row in active_rows:
            if not _is_active(row, lag_date):
                continue
            if row.bond_code not in lag_by_bond.index:
                continue
            if row.bond_code not in signal_by_bond.index:
                continue
            lag_row = lag_by_bond.loc[row.bond_code]
            signal_row = signal_by_bond.loc[row.bond_code]
            endpoint_values = (
                float(lag_row["amount"]),
                float(lag_row["cb_over_rate"]),
                float(signal_row["amount"]),
                float(signal_row["cb_over_rate"]),
            )
            if not all(math.isfinite(value) for value in endpoint_values):
                continue
            if endpoint_values[0] <= 0.0 or endpoint_values[2] <= 0.0:
                continue
            value = endpoint_values[1] - endpoint_values[3]
            if not math.isfinite(value):
                continue
            compression.append(value)
        total_eligible_bonds += len(compression)
        score = (
            float(statistics.median(sorted(compression))) if compression else math.nan
        )
        output.append(
            {
                "signal_session": signal_session,
                "lag_session": lag_session,
                "instrument": instrument,
                "factor_name": FACTOR_NAME,
                "factor_direction": FACTOR_DIRECTION,
                "active_cb_count": len(active_rows),
                "eligible_cb_count": len(compression),
                "factor_value": score,
            }
        )
    frame = pd.DataFrame(output, columns=FACTOR_OUTPUT_FIELDS)
    if not frame.empty:
        frame = frame.sort_values("instrument", kind="stable").reset_index(drop=True)
    return frame, {
        "signal_session": signal_session,
        "lag_session": lag_session,
        "denominator_equity_count": len(frame),
        "eligible_equity_count": int(frame["factor_value"].notna().sum()),
        "active_cb_count": int(frame["active_cb_count"].sum()),
        "eligible_cb_count": total_eligible_bonds,
        "cb_basic": basic_stats,
        "lag_cb_daily": lag_stats,
        "signal_cb_daily": signal_stats,
        "missing_factor_is_zero": False,
        "network_or_credential_access_performed": False,
        "candidate49_or_return_data_read": False,
    }


__all__ = [
    "CB_BASIC_FIELDS",
    "CB_DAILY_FIELDS",
    "FACTOR_DIRECTION",
    "FACTOR_NAME",
    "FACTOR_OUTPUT_FIELDS",
    "SOURCE_CONTRACT",
    "SOURCE_CONTRACT_SHA256",
    "Campaign265AdapterError",
    "canonicalize_cb_basic",
    "canonicalize_cb_daily",
    "compute_factor_on_session",
    "load_source_contract",
]
