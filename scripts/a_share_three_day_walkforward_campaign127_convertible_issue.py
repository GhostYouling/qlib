"""Pure zero-network Campaign127 convertible-issue demand adapter and formula."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from datetime import date
from numbers import Real
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_127_convertible_issue_source_contract_20260814.json"
)
CONTRACT_SHA256 = "66e8ed362c0f5d9efb67de659ab39e83899b0fc8f0e92a0eb5e3399cd8c064a5"

FACTOR_NAME = "convertible_issue_online_demand_180d"
PROVIDER = "tushare_cb_issue"
BASIC_SOURCE_FIELDS = ("ts_code", "stk_code", "cb_type")
ISSUE_SOURCE_FIELDS = (
    "ts_code",
    "ann_date",
    "res_ann_date",
    "onl_pch_excess",
)
NORMALIZED_FIELDS = (
    "instrument",
    "bond_code",
    "ann_date",
    "res_ann_date",
    "online_excess_multiple",
    "provider",
)
MAXIMUM_EVENT_AGE_CALENDAR_DAYS = 180

SSE_MAIN_PREFIXES = frozenset(("600", "601", "603", "605"))
SZSE_MAIN_CHINEXT_PREFIXES = frozenset(("000", "001", "002", "003", "300", "301"))
SSE_STOCK_PREFIXES = SSE_MAIN_PREFIXES | frozenset(
    (
        "500",
        "501",
        "502",
        "503",
        "505",
        "506",
        "508",
        "510",
        "511",
        "512",
        "513",
        "515",
        "516",
        "517",
        "518",
        "519",
        "560",
        "561",
        "562",
        "563",
        "588",
        "688",
        "689",
        "900",
    )
)
SZSE_STOCK_PREFIXES = SZSE_MAIN_CHINEXT_PREFIXES | frozenset(
    (
        "101",
        "102",
        "103",
        "104",
        "105",
        "106",
        "107",
        "108",
        "109",
        "111",
        "112",
        "113",
        "114",
        "115",
        "116",
        "117",
        "118",
        "119",
        "123",
        "127",
        "128",
        "131",
        "159",
        "160",
        "161",
        "162",
        "163",
        "164",
        "165",
        "166",
        "167",
        "168",
        "169",
        "180",
        "200",
    )
)
SSE_BOND_PREFIXES = frozenset(("100", "110", "111", "113", "118", "120", "132"))
SZSE_BOND_PREFIXES = frozenset(("125", "126", "127", "128", "129", "123"))


class Campaign127ContractError(ValueError):
    """Raised when supplied rows violate the frozen Campaign127 contract."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_frozen_contract() -> None:
    if not CONTRACT_PATH.is_file() or file_sha256(CONTRACT_PATH) != CONTRACT_SHA256:
        raise Campaign127ContractError(
            "Campaign127 source contract fingerprint changed"
        )


def _strict_yyyymmdd(value: Any, field: str) -> tuple[str, date]:
    if not isinstance(value, str):
        raise Campaign127ContractError(f"{field} must be a string")
    if len(value) != 8 or not value.isascii() or not value.isdecimal():
        raise Campaign127ContractError(f"{field} must be strict YYYYMMDD")
    try:
        parsed = date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError as exc:
        raise Campaign127ContractError(f"{field} must be a valid date") from exc
    if parsed.strftime("%Y%m%d") != value:
        raise Campaign127ContractError(f"{field} must be strict YYYYMMDD")
    return value, parsed


def _strict_iso_session(value: Any) -> tuple[str, date]:
    if not isinstance(value, str) or len(value) != 10:
        raise Campaign127ContractError("calendar session must be strict YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise Campaign127ContractError("calendar session must be a valid date") from exc
    if parsed.isoformat() != value:
        raise Campaign127ContractError("calendar session must be strict YYYY-MM-DD")
    return value, parsed


def _split_code(value: Any, field: str) -> tuple[str, str, str]:
    if not isinstance(value, str):
        raise Campaign127ContractError(f"{field} must be a string")
    if len(value) != 9 or value[6] != ".":
        raise Campaign127ContractError(
            f"{field} must be six ASCII digits plus .SH or .SZ"
        )
    code = value[:6]
    suffix = value[7:]
    if not code.isascii() or not code.isdecimal() or suffix not in {"SH", "SZ"}:
        raise Campaign127ContractError(
            f"{field} must be six ASCII digits plus .SH or .SZ"
        )
    return code, suffix, code[:3]


def _canonical_bond_code(value: Any) -> str:
    code, suffix, prefix = _split_code(value, "bond ts_code")
    if suffix == "SH" and prefix in SZSE_BOND_PREFIXES:
        raise Campaign127ContractError("bond-code prefix conflicts with .SH suffix")
    if suffix == "SZ" and prefix in SSE_BOND_PREFIXES:
        raise Campaign127ContractError("bond-code prefix conflicts with .SZ suffix")
    return f"{code}.{suffix}"


def _canonical_instrument(value: Any) -> str | None:
    code, suffix, prefix = _split_code(value, "stk_code")
    if suffix == "SH":
        if prefix in SSE_MAIN_PREFIXES:
            return f"SH{code}"
        if prefix in SZSE_STOCK_PREFIXES:
            raise Campaign127ContractError("stk_code prefix conflicts with .SH suffix")
        return None
    if prefix in SZSE_MAIN_CHINEXT_PREFIXES:
        return f"SZ{code}"
    if prefix in SSE_STOCK_PREFIXES:
        raise Campaign127ContractError("stk_code prefix conflicts with .SZ suffix")
    return None


def _strict_cb_type(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise Campaign127ContractError("cb_type must be a nonempty string")
    if value != value.strip():
        raise Campaign127ContractError("cb_type must not contain surrounding space")
    return value


def _strict_positive_multiple(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise Campaign127ContractError("onl_pch_excess must be numeric and not boolean")
    multiple = float(value)
    if not math.isfinite(multiple) or multiple <= 0.0:
        raise Campaign127ContractError(
            "onl_pch_excess must be finite and strictly positive"
        )
    return multiple


def canonicalize_convertible_issue_rows(
    basic_rows: Sequence[Mapping[str, Any]],
    issue_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int | bool]]:
    """Validate, join and canonicalize exact projections without transport."""

    assert_frozen_contract()
    if isinstance(basic_rows, (str, bytes)) or isinstance(issue_rows, (str, bytes)):
        raise Campaign127ContractError("source rows must be sequences of mappings")

    relation_by_bond: dict[str, dict[str, Any]] = {}
    basic_repeats = 0
    for row in basic_rows:
        if not isinstance(row, Mapping):
            raise Campaign127ContractError("cb_basic row must be a mapping")
        if set(row) != set(BASIC_SOURCE_FIELDS) or len(row) != len(BASIC_SOURCE_FIELDS):
            raise Campaign127ContractError(
                "cb_basic row must contain exactly the frozen three-field projection"
            )
        bond_code = _canonical_bond_code(row["ts_code"])
        relation = {
            "bond_code": bond_code,
            "instrument": _canonical_instrument(row["stk_code"]),
            "cb_type": _strict_cb_type(row["cb_type"]),
        }
        if bond_code in relation_by_bond:
            if relation_by_bond[bond_code] != relation:
                raise Campaign127ContractError("bond has conflicting cb_basic relation")
            basic_repeats += 1
            continue
        relation_by_bond[bond_code] = relation

    issue_by_bond: dict[str, dict[str, Any]] = {}
    issue_repeats = 0
    for row in issue_rows:
        if not isinstance(row, Mapping):
            raise Campaign127ContractError("cb_issue row must be a mapping")
        if set(row) != set(ISSUE_SOURCE_FIELDS) or len(row) != len(ISSUE_SOURCE_FIELDS):
            raise Campaign127ContractError(
                "cb_issue row must contain exactly the frozen four-field projection"
            )
        bond_code = _canonical_bond_code(row["ts_code"])
        ann_text, ann_date = _strict_yyyymmdd(row["ann_date"], "ann_date")
        result_text, result_date = _strict_yyyymmdd(row["res_ann_date"], "res_ann_date")
        if result_date < ann_date:
            raise Campaign127ContractError("res_ann_date must not precede ann_date")
        issue = {
            "bond_code": bond_code,
            "ann_date": ann_text,
            "res_ann_date": result_text,
            "online_excess_multiple": _strict_positive_multiple(row["onl_pch_excess"]),
        }
        if bond_code in issue_by_bond:
            if issue_by_bond[bond_code] != issue:
                raise Campaign127ContractError("bond has conflicting cb_issue event")
            issue_repeats += 1
            continue
        issue_by_bond[bond_code] = issue

    events: list[dict[str, Any]] = []
    non_cb_excluded = 0
    unsupported_stock_excluded = 0
    for bond_code in sorted(issue_by_bond):
        relation = relation_by_bond.get(bond_code)
        if relation is None:
            raise Campaign127ContractError("cb_issue event lacks cb_basic relation")
        if relation["cb_type"] != "CB":
            non_cb_excluded += 1
            continue
        if relation["instrument"] is None:
            unsupported_stock_excluded += 1
            continue
        issue = issue_by_bond[bond_code]
        events.append(
            {
                "instrument": relation["instrument"],
                "bond_code": bond_code,
                "ann_date": issue["ann_date"],
                "res_ann_date": issue["res_ann_date"],
                "online_excess_multiple": issue["online_excess_multiple"],
                "provider": PROVIDER,
            }
        )
    events.sort(
        key=lambda event: (
            event["instrument"],
            event["res_ann_date"],
            event["bond_code"],
        )
    )
    return events, {
        "cb_basic_input_rows": len(basic_rows),
        "cb_issue_input_rows": len(issue_rows),
        "canonical_supported_events": len(events),
        "exact_basic_repeats_collapsed": basic_repeats,
        "exact_issue_repeats_collapsed": issue_repeats,
        "non_cb_issues_excluded": non_cb_excluded,
        "unsupported_underlying_issues_excluded": unsupported_stock_excluded,
        "forbidden_fields_read_requested_or_persisted": False,
        "network_or_credential_access_performed": False,
    }


def _accepted_calendar(
    calendar: Sequence[str],
) -> tuple[tuple[str, ...], dict[str, date]]:
    if isinstance(calendar, (str, bytes)):
        raise Campaign127ContractError("calendar must be an ordered sequence")
    parsed = [_strict_iso_session(value) for value in calendar]
    labels = tuple(value for value, _ in parsed)
    dates = tuple(value for _, value in parsed)
    if len(labels) != len(set(labels)):
        raise Campaign127ContractError("calendar sessions must be unique")
    if any(left >= right for left, right in zip(dates, dates[1:])):
        raise Campaign127ContractError("calendar sessions must be strictly increasing")
    return labels, dict(parsed)


def convertible_issue_online_demand_on_session(
    events: Sequence[Mapping[str, Any]],
    calendar: Sequence[str],
    instrument: str,
    signal_session: str,
) -> float | None:
    """Evaluate the latest result-announced issue within the frozen 180-day support."""

    assert_frozen_contract()
    _, calendar_dates = _accepted_calendar(calendar)
    if signal_session not in calendar_dates:
        raise Campaign127ContractError("signal_session is not in the accepted calendar")
    signal_date = calendar_dates[signal_session]
    matches: list[tuple[date, Mapping[str, Any]]] = []
    for event in events:
        if not isinstance(event, Mapping) or tuple(event) != NORMALIZED_FIELDS:
            raise Campaign127ContractError(
                "event must use exact normalized field order"
            )
        if event["provider"] != PROVIDER:
            raise Campaign127ContractError("event provider is not frozen")
        if event["instrument"] != instrument:
            continue
        _, result_date = _strict_yyyymmdd(event["res_ann_date"], "res_ann_date")
        age_days = (signal_date - result_date).days
        if 1 <= age_days <= MAXIMUM_EVENT_AGE_CALENDAR_DAYS:
            matches.append((result_date, event))
    if not matches:
        return None
    latest_date = max(result_date for result_date, _ in matches)
    latest = [event for result_date, event in matches if result_date == latest_date]
    if len(latest) != 1:
        raise Campaign127ContractError(
            "stock has multiple bonds on the maximal res_ann_date"
        )
    multiple = _strict_positive_multiple(latest[0]["online_excess_multiple"])
    score = math.log1p(multiple)
    if not math.isfinite(score) or score <= 0.0:
        raise Campaign127ContractError("derived online-demand score is invalid")
    return score
