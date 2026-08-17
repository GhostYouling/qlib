"""Pure zero-network Campaign124 new-share ballot adapter and formula."""

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
    / "docs/a_share_three_day_walkforward_campaign_124_new_share_source_contract_20260814.json"
)
CONTRACT_SHA256 = "6efcc73fac8f6a24335e869c82c83e15880ada55894569dec098b1eddf5836f1"

FACTOR_NAME = "ipo_retail_ballot_scarcity_20to79s"
PROVIDER = "tushare_new_share"
SOURCE_FIELDS = ("ts_code", "ipo_date", "issue_date", "ballot")
NORMALIZED_FIELDS = ("instrument", "ipo_date", "issue_date", "ballot", "provider")
MINIMUM_LISTING_AGE = 20
MAXIMUM_LISTING_AGE = 79

SSE_MAIN_PREFIXES = frozenset(("600", "601", "603", "605"))
SZSE_MAIN_CHINEXT_PREFIXES = frozenset(("000", "001", "002", "003", "300", "301"))
SSE_EXCHANGE_PREFIXES = SSE_MAIN_PREFIXES | frozenset(
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
SZSE_EXCHANGE_PREFIXES = SZSE_MAIN_CHINEXT_PREFIXES | frozenset(
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


class Campaign124ContractError(ValueError):
    """Raised when synthetic or later supplied values violate the frozen contract."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_frozen_contract() -> None:
    if not CONTRACT_PATH.is_file() or file_sha256(CONTRACT_PATH) != CONTRACT_SHA256:
        raise Campaign124ContractError(
            "Campaign124 source contract fingerprint changed"
        )


def _strict_yyyymmdd(value: Any, field: str) -> tuple[str, date]:
    if not isinstance(value, str):
        raise Campaign124ContractError(f"{field} must be a string")
    if len(value) != 8 or not value.isascii() or not value.isdecimal():
        raise Campaign124ContractError(f"{field} must be strict YYYYMMDD")
    try:
        parsed = date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError as exc:
        raise Campaign124ContractError(f"{field} must be a valid date") from exc
    if parsed.strftime("%Y%m%d") != value:
        raise Campaign124ContractError(f"{field} must be strict YYYYMMDD")
    return value, parsed


def _strict_iso_session(value: Any) -> tuple[str, date]:
    if not isinstance(value, str) or len(value) != 10:
        raise Campaign124ContractError("calendar session must be strict YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise Campaign124ContractError("calendar session must be a valid date") from exc
    if parsed.isoformat() != value:
        raise Campaign124ContractError("calendar session must be strict YYYY-MM-DD")
    return value, parsed


def _canonical_instrument(value: Any) -> str | None:
    if not isinstance(value, str):
        raise Campaign124ContractError("ts_code must be a string")
    if len(value) != 9 or value[6] != ".":
        raise Campaign124ContractError(
            "ts_code must be six ASCII digits plus .SH or .SZ"
        )
    code = value[:6]
    suffix = value[7:]
    if not code.isascii() or not code.isdecimal() or suffix not in {"SH", "SZ"}:
        raise Campaign124ContractError(
            "ts_code must be six ASCII digits plus .SH or .SZ"
        )
    prefix = code[:3]
    if suffix == "SH":
        if prefix in SSE_MAIN_PREFIXES:
            return f"SH{code}"
        if prefix in SZSE_EXCHANGE_PREFIXES:
            raise Campaign124ContractError("ts_code prefix conflicts with .SH suffix")
        return None
    if prefix in SZSE_MAIN_CHINEXT_PREFIXES:
        return f"SZ{code}"
    if prefix in SSE_EXCHANGE_PREFIXES:
        raise Campaign124ContractError("ts_code prefix conflicts with .SZ suffix")
    return None


def _strict_ballot(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise Campaign124ContractError("ballot must be numeric and not boolean")
    ballot = float(value)
    if not math.isfinite(ballot) or ballot <= 0.0 or ballot > 100.0:
        raise Campaign124ContractError("ballot must satisfy 0 < ballot <= 100")
    return ballot


def canonicalize_new_share_rows(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int | bool]]:
    """Canonicalize exact projected rows without transport or forbidden fields."""

    assert_frozen_contract()
    if isinstance(rows, (str, bytes)):
        raise Campaign124ContractError("rows must be a sequence of mappings")
    event_by_instrument: dict[str, dict[str, Any]] = {}
    unsupported = 0
    repeated = 0
    for row in rows:
        if not isinstance(row, Mapping):
            raise Campaign124ContractError("source row must be a mapping")
        if set(row) != set(SOURCE_FIELDS) or len(row) != len(SOURCE_FIELDS):
            raise Campaign124ContractError(
                "source row must contain exactly the frozen four-field projection"
            )
        instrument = _canonical_instrument(row["ts_code"])
        ipo_text, ipo_date = _strict_yyyymmdd(row["ipo_date"], "ipo_date")
        issue_text, issue_date = _strict_yyyymmdd(row["issue_date"], "issue_date")
        if issue_date < ipo_date:
            raise Campaign124ContractError("issue_date must not precede ipo_date")
        ballot = _strict_ballot(row["ballot"])
        if instrument is None:
            unsupported += 1
            continue
        event = {
            "instrument": instrument,
            "ipo_date": ipo_text,
            "issue_date": issue_text,
            "ballot": ballot,
            "provider": PROVIDER,
        }
        if instrument in event_by_instrument:
            if event_by_instrument[instrument] != event:
                raise Campaign124ContractError(
                    "supported instrument has conflicting IPO event"
                )
            repeated += 1
            continue
        event_by_instrument[instrument] = event
    events = [event_by_instrument[key] for key in sorted(event_by_instrument)]
    return events, {
        "input_rows": len(rows),
        "canonical_supported_events": len(events),
        "unsupported_complete_codes_excluded": unsupported,
        "exact_repeated_events_collapsed": repeated,
        "forbidden_fields_read_requested_or_persisted": False,
        "network_or_credential_access_performed": False,
    }


def _accepted_calendar(
    calendar: Sequence[str],
) -> tuple[tuple[str, ...], dict[str, int]]:
    if isinstance(calendar, (str, bytes)):
        raise Campaign124ContractError("calendar must be an ordered sequence")
    parsed = [_strict_iso_session(value) for value in calendar]
    labels = tuple(value for value, _ in parsed)
    dates = tuple(value for _, value in parsed)
    if len(labels) != len(set(labels)):
        raise Campaign124ContractError("calendar sessions must be unique")
    if any(left >= right for left, right in zip(dates, dates[1:])):
        raise Campaign124ContractError("calendar sessions must be strictly increasing")
    return labels, {value: index for index, value in enumerate(labels)}


def ipo_ballot_scarcity_on_session(
    events: Sequence[Mapping[str, Any]],
    calendar: Sequence[str],
    instrument: str,
    signal_session: str,
) -> float | None:
    """Evaluate the fixed -ballot score only at listing ages 20 through 79."""

    assert_frozen_contract()
    _, calendar_index = _accepted_calendar(calendar)
    if signal_session not in calendar_index:
        raise Campaign124ContractError("signal_session is not in the accepted calendar")
    matches = []
    for event in events:
        if not isinstance(event, Mapping) or tuple(event) != NORMALIZED_FIELDS:
            raise Campaign124ContractError(
                "event must use exact normalized field order"
            )
        if event["instrument"] == instrument:
            matches.append(event)
    if not matches:
        return None
    if len(matches) != 1:
        raise Campaign124ContractError("instrument must have exactly one IPO event")
    event = matches[0]
    if event["provider"] != PROVIDER:
        raise Campaign124ContractError("event provider is not frozen")
    issue_text, _ = _strict_yyyymmdd(event["issue_date"], "issue_date")
    issue_session = date(
        int(issue_text[:4]), int(issue_text[4:6]), int(issue_text[6:8])
    ).isoformat()
    if issue_session not in calendar_index:
        raise Campaign124ContractError("issue_date is not an accepted local session")
    signal_index = calendar_index[signal_session]
    issue_index = calendar_index[issue_session]
    listing_age = signal_index - issue_index + 1
    if listing_age < MINIMUM_LISTING_AGE or listing_age > MAXIMUM_LISTING_AGE:
        return None
    ballot = _strict_ballot(event["ballot"])
    return -ballot
