#!/usr/bin/env python3
"""Pure pre-provider adapter for Campaign115's official limit-queue state.

This module deliberately has no network command.  It validates the immutable
source contract and canonicalizes an already supplied response or synthetic
frame.  A separate fingerprint-bound acceptance command may be added only
after this zero-row/synthetic stage and its tests are frozen.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_limit_up_queue_persistence_data_contract_20260809.json"
)
CONTRACT_SHA256 = "41627b182e3d5f6d5de663f589abc06b204bd425971afe1de4a7c20d237caa42"
RAW_FIELDS = ("ts_code", "trade_date", "limit", "last_time", "open_times")
OUTPUT_COLUMNS = (
    "trade_date",
    "instrument",
    "tushare_official_limit_up_queue_persistence",
    "is_official_limit_up_event",
    "provider",
)
VALID_LIMIT_STATES = frozenset({"U", "D", "Z"})
FACTOR_NAME = "tushare_official_limit_up_queue_persistence"


class LimitQueueContractError(RuntimeError):
    """Raised when the frozen Campaign115 contract or one source frame fails."""


def file_digest(path: Path) -> str:
    """Return a streaming SHA-256 digest without reading source data."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract(path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    """Load and structurally verify the exact pre-provider contract."""

    resolved = path.expanduser().resolve()
    if resolved != DEFAULT_CONTRACT.resolve():
        raise LimitQueueContractError(
            "alternate Campaign115 contract path is forbidden"
        )
    if file_digest(resolved) != CONTRACT_SHA256:
        raise LimitQueueContractError(
            "Campaign115 source contract fingerprint mismatch"
        )
    contract = json.loads(resolved.read_text(encoding="utf-8"))
    source = contract.get("source") or {}
    factor = contract.get("factor") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    if (
        contract.get("kind")
        != "a_share_tushare_limit_up_queue_persistence_data_contract"
        or contract.get("status")
        != "frozen_before_zero_row_adapter_provider_rows_candidate_values_or_returns"
        or source.get("provider") != "tushare"
        or source.get("api") != "limit_list_d"
        or tuple(source.get("requested_fields_in_exact_order") or ()) != RAW_FIELDS
        or source.get("provider_row_ceiling") != 5000
        or factor.get("name") != FACTOR_NAME
        or factor.get("direction") != "higher_is_better"
        or factor.get("eligible_event_category")
        != "limit equals the exact uppercase string U"
        or factor.get(
            "alternate_event_category_field_time_anchor_denominator_transform_direction_threshold_window_filter_subset_weight_fit_model_or_combination_search"
        )
        is not False
        or acceptance.get("fixed_completed_session") != "2026-07-13"
        or acceptance.get("maximum_provider_attempts") != 1
    ):
        raise LimitQueueContractError("Campaign115 source contract semantics mismatch")
    return contract


def _canonical_instrument(ts_code: object) -> str:
    value = str(ts_code).strip().upper()
    if len(value) != 9 or value[6] != ".":
        raise LimitQueueContractError(f"invalid Tushare instrument key: {value!r}")
    digits, exchange = value[:6], value[7:]
    if not digits.isdigit() or exchange not in {"SH", "SZ"}:
        raise LimitQueueContractError(f"invalid Tushare instrument key: {value!r}")
    return f"{exchange}{digits}"


def _canonical_date(value: object) -> dt.date:
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    try:
        return dt.date.fromisoformat(text)
    except ValueError as exc:
        raise LimitQueueContractError(f"invalid source trade_date: {value!r}") from exc


def _canonical_hhmmss(value: object) -> tuple[int, int, int]:
    if pd.isna(value):
        raise LimitQueueContractError("upper-limit last_time is missing")
    if isinstance(value, bool):
        raise LimitQueueContractError("upper-limit last_time is boolean")
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise LimitQueueContractError("upper-limit last_time is not HHMMSS")
        text = str(int(value))
    elif isinstance(value, int):
        text = str(value)
    else:
        text = str(value).strip()
        if text.endswith(".0") and text[:-2].isdigit():
            text = text[:-2]
    if not text.isdigit() or len(text) > 6:
        raise LimitQueueContractError("upper-limit last_time is not HHMMSS")
    text = text.zfill(6)
    hour, minute, second = int(text[:2]), int(text[2:4]), int(text[4:])
    if hour > 23 or minute > 59 or second > 59:
        raise LimitQueueContractError("upper-limit last_time is outside clock domain")
    return hour, minute, second


def remaining_session_minutes(last_time: object) -> int:
    """Count full tradable minutes after the final seal, excluding lunch."""

    hour, minute, second = _canonical_hhmmss(last_time)
    clock_seconds = hour * 3600 + minute * 60 + second
    morning_start = 9 * 3600 + 25 * 60
    morning_end = 11 * 3600 + 30 * 60
    afternoon_start = 13 * 3600
    close = 15 * 3600
    if morning_start <= clock_seconds <= morning_end:
        remaining_seconds = (morning_end - clock_seconds) + (close - afternoon_start)
    elif afternoon_start <= clock_seconds <= close:
        remaining_seconds = close - clock_seconds
    else:
        raise LimitQueueContractError(
            "upper-limit last_time is outside the frozen event clock"
        )
    return int(remaining_seconds // 60)


def _open_count(value: object) -> int:
    if pd.isna(value) or isinstance(value, bool):
        raise LimitQueueContractError("upper-limit open_times is missing or boolean")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise LimitQueueContractError("upper-limit open_times is not numeric") from exc
    if not math.isfinite(parsed) or parsed < 0 or not parsed.is_integer():
        raise LimitQueueContractError(
            "upper-limit open_times is not a nonnegative integer"
        )
    return int(parsed)


def canonicalize_limit_queue_response(
    frame: pd.DataFrame,
    *,
    trade_date: dt.date,
    active_instruments: Iterable[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Map one complete source roster to one full-universe factor cross-section."""

    load_contract()
    if tuple(frame.columns) != RAW_FIELDS:
        raise LimitQueueContractError(
            "Tushare limit_list_d response does not match the exact frozen field order"
        )
    if len(frame) >= 5000:
        raise LimitQueueContractError(
            "Tushare limit_list_d response reached the frozen row ceiling"
        )
    universe = tuple(sorted({str(item).strip().upper() for item in active_instruments}))
    if not universe or any(
        len(item) != 8 or item[:2] not in {"SH", "SZ"} or not item[2:].isdigit()
        for item in universe
    ):
        raise LimitQueueContractError(
            "active point-in-time universe is empty or invalid"
        )

    observed: dict[str, tuple[str, object, object]] = {}
    category_counts = {state: 0 for state in sorted(VALID_LIMIT_STATES)}
    for row in frame.itertuples(index=False, name=None):
        ts_code, raw_date, raw_limit, last_time, open_times = row
        source_date = _canonical_date(raw_date)
        if source_date != trade_date:
            raise LimitQueueContractError("source response contains another trade_date")
        instrument = _canonical_instrument(ts_code)
        if instrument in observed:
            raise LimitQueueContractError(
                "source response has duplicate stock-date keys"
            )
        limit_state = str(raw_limit).strip()
        if limit_state not in VALID_LIMIT_STATES:
            raise LimitQueueContractError(
                f"source response has an unknown limit state: {limit_state!r}"
            )
        observed[instrument] = (limit_state, last_time, open_times)
        category_counts[limit_state] += 1

    records: list[dict[str, Any]] = []
    valid_u_rows = 0
    outside_universe_rows = len(set(observed).difference(universe))
    for instrument in universe:
        event = observed.get(instrument)
        score = 0.0
        is_limit_up = False
        if event is not None and event[0] == "U":
            remaining = remaining_session_minutes(event[1])
            opens = _open_count(event[2])
            score = remaining / (245.0 * (1.0 + opens))
            is_limit_up = True
            valid_u_rows += 1
        if not 0.0 <= score <= 1.0 or not math.isfinite(score):
            raise LimitQueueContractError("derived queue score is outside [0, 1]")
        records.append(
            {
                "trade_date": pd.Timestamp(trade_date),
                "instrument": instrument,
                FACTOR_NAME: float(score),
                "is_official_limit_up_event": is_limit_up,
                "provider": "tushare",
            }
        )
    result = pd.DataFrame.from_records(records, columns=OUTPUT_COLUMNS)
    quality = {
        "source_rows": int(len(frame)),
        "source_rows_by_limit_state": category_counts,
        "outside_active_universe_rows_excluded": int(outside_universe_rows),
        "active_universe_names": int(len(universe)),
        "valid_upper_limit_names": int(valid_u_rows),
        "valid_no_event_or_non_u_names": int(len(universe) - valid_u_rows),
        "duplicate_stock_date_keys": 0,
        "row_ceiling_reached": False,
        "candidate_values_read_from_history": False,
        "daily_prices_or_forward_returns_read": False,
    }
    return result, quality


def run_validate_contract(_: argparse.Namespace) -> int:
    contract = load_contract()
    print(
        json.dumps(
            {
                "ready": True,
                "contract_path": str(DEFAULT_CONTRACT),
                "contract_sha256": CONTRACT_SHA256,
                "factor": contract["factor"]["name"],
                "provider_request_issued": False,
                "provider_rows_read": False,
                "candidate_or_return_values_read": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser(
        "validate-contract", help="verify the frozen contract without network or data"
    )
    validate.set_defaults(func=run_validate_contract)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
