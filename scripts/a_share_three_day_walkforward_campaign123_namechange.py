"""Pure Campaign123 adapter and formula for official pure security renames.

This module deliberately contains no transport or credential handling.  It only
canonicalizes already-supplied projected rows and evaluates the frozen
point-in-time formula against an explicitly supplied accepted-session calendar.
"""

from __future__ import annotations

import hashlib
from bisect import bisect_right
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_123_namechange_source_contract_20260814.json"
)
CONTRACT_SHA256 = "00cae705f293de929c7c9c168500efce1506b1ac0ceb2dd902b3c451039d9d8c"

FACTOR_NAME = "official_pure_security_rename_recency_60s"
PROVIDER = "tushare_namechange"
PURE_RENAME_REASON = "改名"
ACTIVE_WINDOW_SESSIONS = 60
SOURCE_FIELDS = (
    "ts_code",
    "start_date",
    "end_date",
    "ann_date",
    "change_reason",
)
NORMALIZED_FIELDS = (
    "instrument",
    "start_date",
    "ann_date",
    "end_date",
    "change_reason",
    "provider",
)

SSE_MAIN_PREFIXES = frozenset(("600", "601", "603", "605"))
SZSE_MAIN_CHINEXT_PREFIXES = frozenset(("000", "001", "002", "003", "300", "301"))
SSE_CROSS_EXCHANGE_PREFIXES = frozenset(
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
        "600",
        "601",
        "603",
        "605",
        "688",
        "689",
        "900",
    )
)
SZSE_CROSS_EXCHANGE_PREFIXES = frozenset(
    (
        "000",
        "001",
        "002",
        "003",
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
        "300",
        "301",
    )
)


class NamechangeContractError(ValueError):
    """Raised when supplied rows or calendar values violate the frozen contract."""


def file_sha256(path: Path) -> str:
    """Return the content fingerprint of *path* without interpreting its bytes."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_frozen_contract() -> None:
    """Fail closed when the bound Campaign123 source contract has changed."""

    if not CONTRACT_PATH.is_file() or file_sha256(CONTRACT_PATH) != CONTRACT_SHA256:
        raise NamechangeContractError("Campaign123 source contract fingerprint changed")


def _strict_yyyymmdd(value: Any, field: str) -> tuple[str, date]:
    if not isinstance(value, str):
        raise NamechangeContractError(f"{field} must be a string")
    if len(value) != 8 or not value.isascii() or not value.isdecimal():
        raise NamechangeContractError(f"{field} must be strict YYYYMMDD")
    try:
        parsed = date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError as exc:
        raise NamechangeContractError(f"{field} must be a valid date") from exc
    if parsed.strftime("%Y%m%d") != value:
        raise NamechangeContractError(f"{field} must be strict YYYYMMDD")
    return value, parsed


def _strict_iso_session(value: Any) -> tuple[str, date]:
    if not isinstance(value, str) or len(value) != 10:
        raise NamechangeContractError("calendar session must be strict YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise NamechangeContractError("calendar session must be a valid date") from exc
    if parsed.isoformat() != value:
        raise NamechangeContractError("calendar session must be strict YYYY-MM-DD")
    return value, parsed


def _canonical_instrument(value: Any) -> str | None:
    if not isinstance(value, str):
        raise NamechangeContractError("ts_code must be a string")
    if len(value) != 9 or value[6] != ".":
        raise NamechangeContractError(
            "ts_code must be six ASCII digits plus .SH or .SZ"
        )
    code = value[:6]
    suffix = value[7:]
    if not code.isascii() or not code.isdecimal() or suffix not in {"SH", "SZ"}:
        raise NamechangeContractError(
            "ts_code must be six ASCII digits plus .SH or .SZ"
        )
    prefix = code[:3]
    if suffix == "SH":
        if prefix in SSE_MAIN_PREFIXES:
            return f"SH{code}"
        if prefix in SZSE_CROSS_EXCHANGE_PREFIXES:
            raise NamechangeContractError("ts_code prefix conflicts with .SH suffix")
        return None
    if prefix in SZSE_MAIN_CHINEXT_PREFIXES:
        return f"SZ{code}"
    if prefix in SSE_CROSS_EXCHANGE_PREFIXES:
        raise NamechangeContractError("ts_code prefix conflicts with .SZ suffix")
    return None


def canonicalize_pure_rename_rows(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int | bool]]:
    """Validate and canonicalize projected rows without network or text parsing."""

    assert_frozen_contract()
    if isinstance(rows, (str, bytes)):
        raise NamechangeContractError("rows must be a sequence of mappings")

    normalized_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
    state_by_identity: dict[tuple[str, str], tuple[str, str | None, str]] = {}
    unsupported = 0
    non_pure_reason = 0
    repeated = 0
    for row in rows:
        if not isinstance(row, Mapping):
            raise NamechangeContractError("source row must be a mapping")
        if set(row) != set(SOURCE_FIELDS) or len(row) != len(SOURCE_FIELDS):
            raise NamechangeContractError(
                "source row must contain exactly the frozen five-field projection"
            )
        reason = row["change_reason"]
        if not isinstance(reason, str) or not reason:
            raise NamechangeContractError("change_reason must be a nonempty string")
        instrument = _canonical_instrument(row["ts_code"])
        start_text, start_date = _strict_yyyymmdd(row["start_date"], "start_date")
        ann_text, _ = _strict_yyyymmdd(row["ann_date"], "ann_date")
        end_value = row["end_date"]
        end_text: str | None
        if end_value is None:
            end_text = None
        else:
            end_text, end_date = _strict_yyyymmdd(end_value, "end_date")
            if end_date < start_date:
                raise NamechangeContractError("end_date must not precede start_date")
        if instrument is None:
            unsupported += 1
            continue

        identity = (instrument, start_text)
        state = (ann_text, end_text, reason)
        if identity in state_by_identity and state_by_identity[identity] != state:
            raise NamechangeContractError(
                "instrument and start_date identity has conflicting source state"
            )
        state_by_identity[identity] = state
        if reason != PURE_RENAME_REASON:
            non_pure_reason += 1
            continue

        event = {
            "instrument": instrument,
            "start_date": start_text,
            "ann_date": ann_text,
            "end_date": end_text,
            "change_reason": reason,
            "provider": PROVIDER,
        }
        key = (instrument, start_text, ann_text, reason)
        if key in normalized_by_key:
            if normalized_by_key[key] != event:
                raise NamechangeContractError(
                    "normalized event key has conflicting state"
                )
            repeated += 1
            continue
        normalized_by_key[key] = event

    events = sorted(
        normalized_by_key.values(),
        key=lambda event: (
            str(event["instrument"]),
            str(event["start_date"]),
            str(event["ann_date"]),
        ),
    )
    stats: dict[str, int | bool] = {
        "input_rows": len(rows),
        "pure_rename_events": len(events),
        "non_pure_reason_rows_excluded": non_pure_reason,
        "unsupported_complete_codes_excluded": unsupported,
        "exact_repeated_events_collapsed": repeated,
        "security_name_read_requested_or_persisted": False,
        "network_or_credential_access_performed": False,
    }
    return events, stats


def _accepted_calendar(
    calendar: Sequence[str],
) -> tuple[tuple[str, ...], tuple[date, ...], dict[str, int]]:
    if isinstance(calendar, (str, bytes)):
        raise NamechangeContractError("calendar must be an ordered sequence")
    parsed = [_strict_iso_session(value) for value in calendar]
    labels = tuple(value for value, _ in parsed)
    dates = tuple(value for _, value in parsed)
    if len(labels) != len(set(labels)):
        raise NamechangeContractError("calendar sessions must be unique")
    if any(left >= right for left, right in zip(dates, dates[1:])):
        raise NamechangeContractError("calendar sessions must be strictly increasing")
    return labels, dates, {value: index for index, value in enumerate(labels)}


def pure_rename_recency_on_session(
    events: Sequence[Mapping[str, Any]],
    calendar: Sequence[str],
    instrument: str,
    signal_session: str,
) -> float | None:
    """Return the frozen factor on one session, or missing when inactive."""

    assert_frozen_contract()
    labels, calendar_dates, calendar_index = _accepted_calendar(calendar)
    if signal_session not in calendar_index:
        raise NamechangeContractError("signal_session is not in the accepted calendar")
    if not isinstance(instrument, str) or not instrument:
        raise NamechangeContractError("instrument must be a complete canonical string")
    signal_index = calendar_index[signal_session]

    latest_effective_index: int | None = None
    for event in events:
        if not isinstance(event, Mapping) or tuple(event) != NORMALIZED_FIELDS:
            raise NamechangeContractError("event must use exact normalized field order")
        if event["instrument"] != instrument:
            continue
        if (
            event["change_reason"] != PURE_RENAME_REASON
            or event["provider"] != PROVIDER
        ):
            raise NamechangeContractError("event is not a canonical pure rename")
        _, start_date = _strict_yyyymmdd(event["start_date"], "start_date")
        _, ann_date = _strict_yyyymmdd(event["ann_date"], "ann_date")
        information_date = max(start_date, ann_date)
        effective_index = bisect_right(calendar_dates, information_date)
        if effective_index >= len(labels) or effective_index > signal_index:
            continue
        if latest_effective_index is None or effective_index > latest_effective_index:
            latest_effective_index = effective_index

    if latest_effective_index is None:
        return None
    age = signal_index - latest_effective_index
    if age < 0 or age >= ACTIVE_WINDOW_SESSIONS:
        return None
    return (ACTIVE_WINDOW_SESSIONS - 1 - age) / (ACTIVE_WINDOW_SESSIONS - 1)
