#!/usr/bin/env python3
"""Settle registered candidate49 signals in one shared paper portfolio.

The engine reads only post-registration immutable signal/factor snapshots and
accepted raw daily rows.  It writes one immutable daily execution snapshot and
one hash-linked execution-ledger entry per processed session.  It never places
an order and never reads a candidate49 historical return.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_rich_data as rich  # noqa: E402
import a_share_tushare_candidate49_future_observation as observation  # noqa: E402
import a_share_tushare_intraday_cumulative_vwap_crossing_rate as candidate  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_candidate49_future_execution_protocol.json"
)
PROTOCOL_SHA256 = "b9b4ea8906924c8303cb7a434db5f21ed6383ce7d794e50936b675acfa869486"
DAILY_SNAPSHOT_KIND = "a_share_candidate49_future_execution_daily_snapshot"
INITIAL_CASH = 200_000.0
SLOT_FRACTION = 0.05
SIGNAL_FRACTION = 0.15
LOT_SIZE = 100
COMMISSION_RATE = 0.0001
TRANSFER_FEE_RATE = 0.00002
STAMP_DUTY_RATE = 0.0005
SLIPPAGE_RATE = 0.001
MAX_EXIT_ATTEMPTS = 20
MAX_AMOUNT_PARTICIPATION = 0.01
ONE_PRICE_TOLERANCE = 1e-12
MINIMUM_RANK_IC_NAMES = 50
EARLY_EVALUATION_SIGNAL_COUNT = 60
FULL_EVALUATION_SIGNAL_COUNT = 200
MINIMUM_POSITIVE_RANK_IC_RATE = 0.5
MINIMUM_BOARD_LOT_AFFORDABILITY = 0.9
MAXIMUM_ALLOWED_DRAWDOWN = -0.2
EVALUATION_RECORD_KIND = "a_share_candidate49_future_evaluation_milestone"
DEFAULT_EVALUATION_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "candidate49_future_evaluations"
)
EXECUTION_DAILY_ROOT_BELOW_DATA_ROOT = (
    "prospective/a_share/rich/tushare/execution_daily/candidate49"
)
DAILY_COLUMNS = (
    "trade_date",
    "symbol",
    "raw_open",
    "raw_high",
    "raw_low",
    "raw_close",
    "raw_volume",
    "amount",
    "prior_raw_close",
    "price_basis",
    "source_file_sha256",
    "source_row_status",
)
RAW_DAILY_FIELDS = (
    "date",
    "raw_open",
    "raw_high",
    "raw_low",
    "raw_close",
    "raw_volume",
    "amount",
    "price_basis",
)


class Candidate49FutureExecutionError(RuntimeError):
    """Raised when frozen paper-execution semantics or state are violated."""


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _canonical_digest(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _atomic_json_digest(payload: Any) -> str:
    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_execution_protocol() -> dict[str, Any]:
    if (
        not DEFAULT_PROTOCOL.is_file()
        or rich.file_digest(DEFAULT_PROTOCOL) != PROTOCOL_SHA256
    ):
        raise Candidate49FutureExecutionError(
            "candidate49 future execution protocol fingerprint changed"
        )
    protocol = rich.load_json_record(
        DEFAULT_PROTOCOL,
        kind="a_share_tushare_candidate49_future_execution_protocol",
    )
    timing = protocol.get("session_timing") or {}
    portfolio = protocol.get("portfolio") or {}
    costs = protocol.get("costs") or {}
    tradeability = protocol.get("tradeability") or {}
    rank_ic = protocol.get("future_rank_ic") or {}
    storage = protocol.get("storage") or {}
    evaluation = protocol.get("evaluation") or {}
    full_gate = evaluation.get("full_gate") or {}
    current = protocol.get("current_state") or {}
    if not (
        protocol.get("status")
        == "frozen_before_first_eligible_future_signal_entry_open_or_outcome"
        and protocol.get("registration_id") == candidate.FUTURE_REGISTRATION_ID
        and (
            (protocol.get("source_chain") or {}).get(
                "future_observation_registration"
            )
            or {}
        ).get("sha256")
        == candidate.FUTURE_REGISTRATION_SHA256
        and timing.get("entry_session") == "the next accepted local session, t+1"
        and str(timing.get("scheduled_exit_session", "")).startswith("t+3,")
        and str(timing.get("processing_lag", "")).startswith(
            "an execution session is appended only after two later accepted"
        )
        and portfolio.get("initial_cash_cny") == 200000
        and portfolio.get("lot_size_shares") == 100
        and costs.get("commission_rate_each_side") == COMMISSION_RATE
        and costs.get("commission_minimum_cny") == 0
        and costs.get("transfer_fee_rate_each_side") == TRANSFER_FEE_RATE
        and costs.get("sell_stamp_duty_rate") == STAMP_DUTY_RATE
        and costs.get("primary_adverse_slippage_rate_each_side") == SLIPPAGE_RATE
        and tradeability.get("one_price_equality_tolerance")
        == ONE_PRICE_TOLERANCE
        and tuple(tradeability.get("required_daily_fields") or ())
        == RAW_DAILY_FIELDS
        and rank_ic.get("minimum_valid_names") == MINIMUM_RANK_IC_NAMES
        and storage.get("future_execution_daily_root_below_data_root")
        == EXECUTION_DAILY_ROOT_BELOW_DATA_ROOT
        and tuple(storage.get("daily_snapshot_columns") or ()) == DAILY_COLUMNS
        and evaluation.get("early_rejection_after_completed_rank_ic_signals")
        == EARLY_EVALUATION_SIGNAL_COUNT
        and evaluation.get("full_gate_after_completed_rank_ic_signals")
        == FULL_EVALUATION_SIGNAL_COUNT
        and full_gate.get("mean_future_rank_ic_greater_than") == 0
        and full_gate.get("positive_rank_ic_rate_at_least")
        == MINIMUM_POSITIVE_RANK_IC_RATE
        and full_gate.get("shared_portfolio_net_cumulative_return_greater_than")
        == 0
        and full_gate.get("maximum_drawdown_at_least")
        == MAXIMUM_ALLOWED_DRAWDOWN
        and full_gate.get("board_lot_affordability_at_least")
        == MINIMUM_BOARD_LOT_AFFORDABILITY
        and full_gate.get("maximum_daily_amount_participation_at_most")
        == MAX_AMOUNT_PARTICIPATION
        and full_gate.get("terminal_unresolved_positions") == 0
        and current.get("real_future_signal_count") == 0
        and current.get("portfolio_return_exists") is False
    ):
        raise Candidate49FutureExecutionError(
            "candidate49 future execution protocol semantics changed"
        )
    return protocol


def _read_calendar(provider_uri: Path) -> pd.DatetimeIndex:
    return observation._read_calendar(provider_uri / "calendars" / "day.txt")


def _session_position(
    calendar: pd.DatetimeIndex,
    session_date: dt.date,
) -> int:
    timestamp = pd.Timestamp(session_date)
    position = int(calendar.searchsorted(timestamp, side="left"))
    if position >= len(calendar) or calendar[position] != timestamp:
        raise Candidate49FutureExecutionError(
            f"session is absent from accepted local calendar: {session_date}"
        )
    return position


def _calendar_date(
    calendar: pd.DatetimeIndex,
    position: int,
) -> dt.date:
    if position < 0 or position >= len(calendar):
        raise Candidate49FutureExecutionError(
            "accepted calendar does not yet contain a required execution session"
        )
    return calendar[position].date()


def _signal_timing(
    entry: dict[str, Any],
    calendar: pd.DatetimeIndex,
) -> tuple[dt.date, dt.date, dt.date]:
    signal = dt.date.fromisoformat(str(entry["session_date"]))
    signal_position = _session_position(calendar, signal)
    return (
        signal,
        _calendar_date(calendar, signal_position + 1),
        _calendar_date(calendar, signal_position + 3),
    )


def _load_signal_factor(
    entry: dict[str, Any],
) -> tuple[dict[str, Any], pd.DataFrame]:
    factor_link = entry.get("factor_snapshot") or {}
    manifest_path = Path(str(factor_link.get("path") or "")).expanduser().resolve()
    if (
        not manifest_path.is_file()
        or rich.file_digest(manifest_path) != factor_link.get("sha256")
    ):
        raise Candidate49FutureExecutionError(
            f"candidate49 signal factor manifest changed: {manifest_path}"
        )
    manifest = rich.load_json_record(
        manifest_path,
        kind=observation.FACTOR_SNAPSHOT_KIND,
    )
    factor_path = manifest_path.parent / "factor.parquet"
    if not (
        manifest.get("registration_sha256")
        == candidate.FUTURE_REGISTRATION_SHA256
        and manifest.get("session_date") == entry.get("session_date")
        and manifest.get("factor_name") == candidate.FACTOR_NAME
        and manifest.get("factor_direction") == "higher"
        and manifest.get("factor_frame_sha256")
        == factor_link.get("frame_sha256")
        and factor_path.is_file()
        and rich.file_digest(factor_path) == manifest.get("factor_byte_sha256")
    ):
        raise Candidate49FutureExecutionError(
            f"candidate49 signal factor contract changed: {manifest_path}"
        )
    frame = pd.read_parquet(factor_path)
    if (
        tuple(frame.columns) != observation.FACTOR_COLUMNS
        or rich.frame_digest(frame) != manifest.get("factor_frame_sha256")
    ):
        raise Candidate49FutureExecutionError(
            f"candidate49 signal factor frame changed: {factor_path}"
        )
    eligible = frame.loc[
        frame[f"{candidate.FACTOR_NAME}_eligible"].astype(bool)
    ].copy()
    eligible[candidate.FACTOR_NAME] = pd.to_numeric(
        eligible[candidate.FACTOR_NAME], errors="coerce"
    )
    eligible = eligible.loc[
        np.isfinite(eligible[candidate.FACTOR_NAME].to_numpy(dtype=float))
    ]
    ranked = eligible.sort_values(
        [candidate.FACTOR_NAME, "symbol"],
        ascending=[False, True],
        kind="stable",
    ).head(3)
    expected = [
        {
            "rank": rank,
            "symbol": str(row.symbol),
            "factor_value": float(getattr(row, candidate.FACTOR_NAME)),
        }
        for rank, row in enumerate(ranked.itertuples(index=False), start=1)
    ]
    if (
        len(eligible) < MINIMUM_RANK_IC_NAMES
        or int(entry.get("eligible_names", -1)) != len(eligible)
        or entry.get("ranking")
        != "descending_factor_then_ascending_stock_code"
        or entry.get("topk") != 3
        or entry.get("selections") != expected
    ):
        raise Candidate49FutureExecutionError(
            f"candidate49 signal ranking changed: {entry.get('entry_id')}"
        )
    return manifest, frame


def _validated_signals(
    signal_path: Path,
    calendar: pd.DatetimeIndex,
) -> list[dict[str, Any]]:
    try:
        entries = observation.validate_signal_ledger_semantics(signal_path)
    except (
        observation.Candidate49FutureObservationError,
        candidate.IntradayCumulativeVwapCrossingRateError,
    ) as exc:
        raise Candidate49FutureExecutionError(
            "candidate49 signal ledger semantics changed"
        ) from exc
    dates = [dt.date.fromisoformat(str(entry["session_date"])) for entry in entries]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise Candidate49FutureExecutionError(
            "candidate49 signal ledger is not strictly chronological"
        )
    for entry in entries:
        _session_position(
            calendar,
            dt.date.fromisoformat(str(entry["session_date"])),
        )
        _load_signal_factor(entry)
        if not (
            entry.get("registration_sha256")
            == candidate.FUTURE_REGISTRATION_SHA256
            and entry.get("factor_name") == candidate.FACTOR_NAME
            and entry.get("factor_direction") == "higher"
            and entry.get("forward_return_fields_read") is False
            and entry.get("execution_or_order_performed") is False
        ):
            raise Candidate49FutureExecutionError(
                f"candidate49 signal semantics changed: {entry.get('entry_id')}"
            )
    return entries


def _validate_signal_execution_consistency(
    *,
    signals: list[dict[str, Any]],
    execution_entries: list[dict[str, Any]],
    state: dict[str, Any],
    last_session: dt.date | None,
    calendar: pd.DatetimeIndex,
) -> None:
    """Cross-check both ledgers before an idempotent return or new append."""

    signal_ids = [str(signal["entry_id"]) for signal in signals]
    known_signal_ids = set(signal_ids)
    processed_ids = [
        str(value) for value in state.get("processed_signal_entry_ids") or []
    ]
    if (
        len(processed_ids) != len(set(processed_ids))
        or any(value not in known_signal_ids for value in processed_ids)
    ):
        raise Candidate49FutureExecutionError(
            "candidate49 processed-signal state contains an unknown or "
            "duplicate signal identity"
        )
    expected_processed_ids = (
        []
        if last_session is None
        else [
            str(signal["entry_id"])
            for signal in signals
            if (
                (
                    entry_session := _available_signal_session(
                        signal,
                        calendar,
                        offset=1,
                    )
                )
                is not None
                and entry_session <= last_session
            )
        ]
    )
    if processed_ids != expected_processed_ids:
        missing = [
            value for value in expected_processed_ids if value not in processed_ids
        ]
        if missing:
            raise Candidate49FutureExecutionError(
                "candidate49 signal appeared after its entry session was "
                "already settled: " + ",".join(missing)
            )
        raise Candidate49FutureExecutionError(
            "candidate49 processed-signal chronology changed"
        )
    for execution_entry in execution_entries:
        session_date = dt.date.fromisoformat(
            str(execution_entry["session_date"])
        )
        entering = [
            signal
            for signal in signals
            if _available_signal_session(signal, calendar, offset=1)
            == session_date
        ]
        expected_entering = [
            {
                "entry_id": signal["entry_id"],
                "session_date": signal["session_date"],
                "entry_sha256": signal["entry_sha256"],
            }
            for signal in entering
        ]
        if execution_entry.get("signals_entering") != expected_entering:
            raise Candidate49FutureExecutionError(
                "candidate49 execution-to-signal entry links changed"
            )
        expected_outcomes = [
            str(signal["entry_id"])
            for signal in signals
            if _available_signal_session(signal, calendar, offset=3)
            == session_date
        ]
        actual_outcomes = [
            str(item.get("signal_entry_id"))
            for item in execution_entry.get("future_rank_ic_outcomes") or []
        ]
        if (
            actual_outcomes != expected_outcomes
            or execution_entry.get(
                "forward_outcomes_read_only_for_registered_signals"
            )
            != expected_outcomes
        ):
            raise Candidate49FutureExecutionError(
                "candidate49 execution-to-signal outcome links changed"
            )


def _available_signal_session(
    entry: dict[str, Any],
    calendar: pd.DatetimeIndex,
    *,
    offset: int,
) -> dt.date | None:
    signal = dt.date.fromisoformat(str(entry["session_date"]))
    position = _session_position(calendar, signal)
    target = position + offset
    if target >= len(calendar):
        return None
    return _calendar_date(calendar, target)


def _empty_state() -> dict[str, Any]:
    return {
        "cash_cny": INITIAL_CASH,
        "positions": [],
        "equity_cny": INITIAL_CASH,
        "high_watermark_cny": INITIAL_CASH,
        "cumulative_net_return": 0.0,
        "maximum_drawdown": 0.0,
        "entry_opportunities": 0,
        "board_lot_affordable_opportunities": 0,
        "board_lot_affordability": None,
        "cumulative_buy_fees_cny": 0.0,
        "cumulative_sell_fees_cny": 0.0,
        "cumulative_slippage_cost_cny": 0.0,
        "maximum_observed_amount_participation": 0.0,
        "completed_rank_ic_signals": 0,
        "rank_ic_sum": 0.0,
        "mean_rank_ic": None,
        "positive_rank_ic_signals": 0,
        "positive_rank_ic_rate": None,
        "processed_signal_entry_ids": [],
        "terminal_unresolved_lots": 0,
    }


def _evaluation_flags(state: dict[str, Any]) -> dict[str, bool]:
    """Evaluate the frozen gates on the state currently in the hash chain."""

    completed = int(state["completed_rank_ic_signals"])
    early_ready = completed >= EARLY_EVALUATION_SIGNAL_COUNT
    early_triggered = bool(
        early_ready
        and float(state["mean_rank_ic"]) <= 0.0
        and float(state["cumulative_net_return"]) <= 0.0
    )
    full_ready = completed >= FULL_EVALUATION_SIGNAL_COUNT
    full_passed = bool(
        full_ready
        and float(state["mean_rank_ic"]) > 0.0
        and float(state["positive_rank_ic_rate"])
        >= MINIMUM_POSITIVE_RANK_IC_RATE
        and float(state["cumulative_net_return"]) > 0.0
        and float(state["maximum_drawdown"]) >= MAXIMUM_ALLOWED_DRAWDOWN
        and float(state["board_lot_affordability"] or 0.0)
        >= MINIMUM_BOARD_LOT_AFFORDABILITY
        and float(state["maximum_observed_amount_participation"])
        <= MAX_AMOUNT_PARTICIPATION
        and int(state["terminal_unresolved_lots"]) == 0
    )
    return {
        "early_rejection_ready": early_ready,
        "early_rejection_triggered": early_triggered,
        "full_gate_ready": full_ready,
        "full_gate_passed": full_passed,
        "aggregation_allowed": False,
        "live_order_allowed": False,
    }


def _validate_evaluation_progression(
    entries: list[dict[str, Any]],
) -> None:
    """Require exact, monotone Rank-IC counts and correctly derived live flags."""

    previous_completed = 0
    for entry in entries:
        state = entry.get("ending_state") or {}
        completed = state.get("completed_rank_ic_signals")
        positive = state.get("positive_rank_ic_signals")
        if (
            isinstance(completed, bool)
            or not isinstance(completed, int)
            or completed < previous_completed
            or completed - previous_completed > 1
            or isinstance(positive, bool)
            or not isinstance(positive, int)
            or positive < 0
            or positive > completed
        ):
            raise Candidate49FutureExecutionError(
                "candidate49 completed Rank-IC progression changed"
            )
        rank_ic_sum = float(state.get("rank_ic_sum", math.nan))
        mean_rank_ic = state.get("mean_rank_ic")
        positive_rate = state.get("positive_rank_ic_rate")
        if completed == 0:
            summary_valid = (
                np.isfinite(rank_ic_sum)
                and abs(rank_ic_sum) <= 1e-12
                and mean_rank_ic is None
                and positive_rate is None
            )
        else:
            summary_valid = bool(
                np.isfinite(rank_ic_sum)
                and mean_rank_ic is not None
                and np.isfinite(float(mean_rank_ic))
                and math.isclose(
                    float(mean_rank_ic),
                    rank_ic_sum / completed,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
                and positive_rate is not None
                and np.isfinite(float(positive_rate))
                and math.isclose(
                    float(positive_rate),
                    positive / completed,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            )
        if not summary_valid or entry.get("evaluation") != _evaluation_flags(state):
            raise Candidate49FutureExecutionError(
                "candidate49 evaluation summary changed"
            )
        previous_completed = completed


def _milestone_entry(
    entries: list[dict[str, Any]],
    milestone: int,
) -> tuple[int, dict[str, Any]] | None:
    previous_completed = 0
    for index, entry in enumerate(entries):
        completed = int(entry["ending_state"]["completed_rank_ic_signals"])
        if previous_completed < milestone <= completed:
            if completed != milestone:
                raise Candidate49FutureExecutionError(
                    "candidate49 evaluation milestone was skipped"
                )
            return index, entry
        previous_completed = completed
    return None


def _evaluation_record_path(root: Path, milestone: int) -> Path:
    return root / f"candidate49_future_evaluation_{milestone:03d}.json"


def _evaluation_ledger_observation(
    *,
    execution_path: Path,
    entries: list[dict[str, Any]],
    entry: dict[str, Any],
) -> dict[str, Any]:
    ledger = candidate.validate_future_ledger(
        execution_path,
        candidate.FUTURE_EXECUTION_LEDGER_KIND,
    )
    if ledger["entries"] != entries:
        raise Candidate49FutureExecutionError(
            "candidate49 evaluation entries differ from the execution ledger"
        )
    matching = [
        index
        for index, value in enumerate(entries)
        if (
            value.get("entry_id") == entry.get("entry_id")
            and value.get("entry_sha256") == entry.get("entry_sha256")
        )
    ]
    if len(matching) != 1:
        raise Candidate49FutureExecutionError(
            "candidate49 evaluation milestone entry identity changed"
        )
    prefix = entries[: matching[0] + 1]
    prefix_ledger = {
        **ledger,
        "status": "active_append_only_future_observation",
        "entries": prefix,
        "chain_tip_sha256": entry["entry_sha256"],
    }
    return {
        "path": str(execution_path),
        "sha256_at_evaluation": _atomic_json_digest(prefix_ledger),
        "entry_count_at_evaluation": len(prefix),
        "chain_tip_sha256_at_evaluation": entry["entry_sha256"],
        "entry_prefix_sha256_at_evaluation": _canonical_digest(prefix),
    }


def _evaluation_decision(
    *,
    entry: dict[str, Any],
    milestone: int,
) -> dict[str, Any]:
    state = entry["ending_state"]
    metrics = {
        "completed_future_rank_ic_signals": int(
            state["completed_rank_ic_signals"]
        ),
        "mean_future_rank_ic": float(state["mean_rank_ic"]),
        "positive_future_rank_ic_rate": float(state["positive_rank_ic_rate"]),
        "shared_portfolio_net_cumulative_return": float(
            state["cumulative_net_return"]
        ),
        "maximum_drawdown": float(state["maximum_drawdown"]),
        "board_lot_affordability": (
            None
            if state["board_lot_affordability"] is None
            else float(state["board_lot_affordability"])
        ),
        "maximum_daily_amount_participation": float(
            state["maximum_observed_amount_participation"]
        ),
        "terminal_unresolved_positions": int(
            state["terminal_unresolved_lots"]
        ),
    }
    source = {
        "execution_entry_id": str(entry["entry_id"]),
        "execution_entry_sha256": str(entry["entry_sha256"]),
        "execution_session": str(entry["session_date"]),
        "ending_state_sha256": str(entry["ending_state_sha256"]),
        "execution_protocol_sha256": PROTOCOL_SHA256,
        "future_registration_sha256": candidate.FUTURE_REGISTRATION_SHA256,
    }
    if milestone == EARLY_EVALUATION_SIGNAL_COUNT:
        gates = {
            "mean_future_rank_ic_nonpositive": (
                metrics["mean_future_rank_ic"] <= 0.0
            ),
            "shared_portfolio_net_cumulative_return_nonpositive": (
                metrics["shared_portfolio_net_cumulative_return"] <= 0.0
            ),
        }
        gates["joint_early_rejection_condition"] = all(gates.values())
        triggered = bool(gates["joint_early_rejection_condition"])
        return {
            "milestone": "early_rejection_060_completed_future_rank_ic_signals",
            "milestone_completed_future_rank_ic_signals": milestone,
            "status": (
                "terminal_early_rejection"
                if triggered
                else "interim_continue_to_200_without_promotion"
            ),
            "metrics": metrics,
            "gates": gates,
            "early_rejection_triggered": triggered,
            "full_evaluation_complete": False,
            "candidate50_activation_allowed": triggered,
            "execution_stop_required": triggered,
            "paper_observation_continuation_allowed": not triggered,
            "aggregation_allowed": False,
            "current_scoring_selection_sizing_or_live_orders_allowed": False,
            "source": source,
        }
    if milestone != FULL_EVALUATION_SIGNAL_COUNT:
        raise Candidate49FutureExecutionError(
            f"unsupported candidate49 evaluation milestone: {milestone}"
        )
    gates = {
        "mean_future_rank_ic_positive": metrics["mean_future_rank_ic"] > 0.0,
        "positive_future_rank_ic_rate_at_least_0_5": (
            metrics["positive_future_rank_ic_rate"]
            >= MINIMUM_POSITIVE_RANK_IC_RATE
        ),
        "shared_portfolio_net_cumulative_return_positive": (
            metrics["shared_portfolio_net_cumulative_return"] > 0.0
        ),
        "maximum_drawdown_no_worse_than_minus_0_2": (
            metrics["maximum_drawdown"] >= MAXIMUM_ALLOWED_DRAWDOWN
        ),
        "board_lot_affordability_at_least_0_9": (
            (metrics["board_lot_affordability"] or 0.0)
            >= MINIMUM_BOARD_LOT_AFFORDABILITY
        ),
        "maximum_daily_amount_participation_at_most_0_01": (
            metrics["maximum_daily_amount_participation"]
            <= MAX_AMOUNT_PARTICIPATION
        ),
        "terminal_unresolved_positions_zero": (
            metrics["terminal_unresolved_positions"] == 0
        ),
    }
    passed = all(gates.values())
    return {
        "milestone": "full_evaluation_200_completed_future_rank_ic_signals",
        "milestone_completed_future_rank_ic_signals": milestone,
        "status": (
            "full_gate_passed_continue_paper_observation_only"
            if passed
            else "terminal_full_gate_rejection"
        ),
        "metrics": metrics,
        "gates": gates,
        "full_gate_passed": passed,
        "full_evaluation_complete": True,
        "candidate50_activation_allowed": True,
        "execution_stop_required": not passed,
        "paper_observation_continuation_allowed": passed,
        "aggregation_allowed": False,
        "current_scoring_selection_sizing_or_live_orders_allowed": False,
        "source": source,
    }


def _publish_evaluation_record(
    *,
    evaluation_root: Path,
    execution_path: Path,
    entries: list[dict[str, Any]],
    milestone: int,
    entry: dict[str, Any],
    create_missing: bool,
) -> dict[str, Any]:
    decision = _evaluation_decision(entry=entry, milestone=milestone)
    ledger_observation = _evaluation_ledger_observation(
        execution_path=execution_path,
        entries=entries,
        entry=entry,
    )
    created_at = str(entry.get("settled_at") or "")
    try:
        created_timestamp = dt.datetime.fromisoformat(
            created_at.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise Candidate49FutureExecutionError(
            "candidate49 evaluation milestone settled_at changed"
        ) from exc
    if created_timestamp.tzinfo is None:
        raise Candidate49FutureExecutionError(
            "candidate49 evaluation milestone settled_at changed"
        )
    expected_record = {
        "schema_version": 1,
        "kind": EVALUATION_RECORD_KIND,
        "created_at": created_at,
        "registration_id": candidate.FUTURE_REGISTRATION_ID,
        "registration_sha256": candidate.FUTURE_REGISTRATION_SHA256,
        "execution_protocol": {
            "path": str(DEFAULT_PROTOCOL),
            "sha256": PROTOCOL_SHA256,
        },
        "execution_protocol_sha256": PROTOCOL_SHA256,
        "execution_ledger_observation": ledger_observation,
        "decision": decision,
        "decision_sha256": _canonical_digest(decision),
        "historical_candidate49_price_or_return_fields_read": [],
        "provider_request_issued": False,
        "live_order_performed": False,
        "investment_advice": False,
    }
    path = _evaluation_record_path(evaluation_root, milestone)
    if path.is_file():
        record = rich.load_json_record(path, kind=EVALUATION_RECORD_KIND)
        if record != expected_record:
            raise Candidate49FutureExecutionError(
                f"candidate49 future evaluation record changed: {path}"
            )
        return record
    if path.exists():
        raise Candidate49FutureExecutionError(
            f"candidate49 future evaluation path is not a file: {path}"
        )
    if not create_missing:
        raise Candidate49FutureExecutionError(
            f"candidate49 future evaluation record is missing: {path}"
        )
    evaluation_root.mkdir(parents=True, exist_ok=True)
    rich.atomic_write_json(expected_record, path)
    return rich.load_json_record(path, kind=EVALUATION_RECORD_KIND)


def synchronize_evaluation_records(
    *,
    entries: list[dict[str, Any]],
    execution_path: Path,
    evaluation_root: Path = DEFAULT_EVALUATION_ROOT,
    write_missing_records: bool = True,
) -> dict[str, Any]:
    """Validate or freeze exact 60/200 decisions without using latest state."""

    execution_path = execution_path.expanduser().resolve()
    evaluation_root = evaluation_root.expanduser().resolve()
    _validate_evaluation_progression(entries)
    completed = (
        0
        if not entries
        else int(entries[-1]["ending_state"]["completed_rank_ic_signals"])
    )
    result: dict[str, Any] = {
        "status": "awaiting_60_completed_future_rank_ic_signals",
        "completed_future_rank_ic_signals": completed,
        "next_milestone": EARLY_EVALUATION_SIGNAL_COUNT,
        "remaining_completed_future_rank_ic_signals": max(
            EARLY_EVALUATION_SIGNAL_COUNT - completed,
            0,
        ),
        "early_record": None,
        "full_record": None,
        "execution_stop_required": False,
        "candidate50_activation_allowed": False,
        "aggregation_allowed": False,
        "provider_request_issued": False,
        "live_order_performed": False,
    }
    early = _milestone_entry(entries, EARLY_EVALUATION_SIGNAL_COUNT)
    early_path = _evaluation_record_path(
        evaluation_root,
        EARLY_EVALUATION_SIGNAL_COUNT,
    )
    if early is None:
        if early_path.exists():
            raise Candidate49FutureExecutionError(
                "candidate49 early evaluation record exists before its milestone"
            )
        return result
    early_index, early_entry = early
    early_record = _publish_evaluation_record(
        evaluation_root=evaluation_root,
        execution_path=execution_path,
        entries=entries,
        milestone=EARLY_EVALUATION_SIGNAL_COUNT,
        entry=early_entry,
        create_missing=write_missing_records,
    )
    early_decision = early_record["decision"]
    result.update(
        {
            "status": early_decision["status"],
            "early_record": str(early_path),
            "early_record_sha256": rich.file_digest(early_path),
            "next_milestone": FULL_EVALUATION_SIGNAL_COUNT,
            "remaining_completed_future_rank_ic_signals": max(
                FULL_EVALUATION_SIGNAL_COUNT - completed,
                0,
            ),
            "execution_stop_required": bool(
                early_decision["execution_stop_required"]
            ),
            "candidate50_activation_allowed": bool(
                early_decision["candidate50_activation_allowed"]
            ),
        }
    )
    if early_decision["execution_stop_required"]:
        if early_index != len(entries) - 1:
            raise Candidate49FutureExecutionError(
                "candidate49 execution continued after terminal early rejection"
            )
        result["next_milestone"] = None
        result["remaining_completed_future_rank_ic_signals"] = None
        return result
    full = _milestone_entry(entries, FULL_EVALUATION_SIGNAL_COUNT)
    full_path = _evaluation_record_path(
        evaluation_root,
        FULL_EVALUATION_SIGNAL_COUNT,
    )
    if full is None:
        if full_path.exists():
            raise Candidate49FutureExecutionError(
                "candidate49 full evaluation record exists before its milestone"
            )
        return result
    full_index, full_entry = full
    full_record = _publish_evaluation_record(
        evaluation_root=evaluation_root,
        execution_path=execution_path,
        entries=entries,
        milestone=FULL_EVALUATION_SIGNAL_COUNT,
        entry=full_entry,
        create_missing=write_missing_records,
    )
    full_decision = full_record["decision"]
    result.update(
        {
            "status": full_decision["status"],
            "full_record": str(full_path),
            "full_record_sha256": rich.file_digest(full_path),
            "next_milestone": None,
            "remaining_completed_future_rank_ic_signals": None,
            "execution_stop_required": bool(
                full_decision["execution_stop_required"]
            ),
            "candidate50_activation_allowed": True,
        }
    )
    if full_decision["execution_stop_required"] and full_index != len(entries) - 1:
        raise Candidate49FutureExecutionError(
            "candidate49 execution continued after terminal full-gate rejection"
        )
    return result


def _validate_engine_ledger(
    execution_path: Path,
    calendar: pd.DatetimeIndex,
    *,
    data_root: Path,
    signals: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dt.date | None]:
    ledger = candidate.validate_future_ledger(
        execution_path,
        candidate.FUTURE_EXECUTION_LEDGER_KIND,
    )
    signal_by_id = {
        str(signal["entry_id"]): signal for signal in signals
    }
    replay_signal_ids: set[str] = set()
    for entry in ledger["entries"]:
        for link in entry.get("signals_entering") or []:
            signal_id = str(link.get("entry_id") or "")
            if signal_id not in signal_by_id:
                raise Candidate49FutureExecutionError(
                    "candidate49 execution ledger references an unknown signal"
                )
            replay_signal_ids.add(signal_id)
    replay_signals = [
        signal
        for signal in signals
        if str(signal["entry_id"]) in replay_signal_ids
    ]
    state = _empty_state()
    previous_date: dt.date | None = None
    for entry in ledger["entries"]:
        session_date = dt.date.fromisoformat(str(entry["session_date"]))
        if not (
            entry.get("entry_id")
            == (
                f"{candidate.FUTURE_REGISTRATION_ID}:execution:"
                f"{session_date.isoformat()}"
            )
            and entry.get("execution_protocol_sha256") == PROTOCOL_SHA256
            and entry.get("registration_sha256")
            == candidate.FUTURE_REGISTRATION_SHA256
            and entry.get("historical_candidate49_price_or_return_fields_read")
            == []
            and entry.get("provider_request_issued") is False
            and entry.get("live_order_performed") is False
            and entry.get("investment_advice") is False
        ):
            raise Candidate49FutureExecutionError(
                "candidate49 execution ledger fixed semantics changed"
            )
        if previous_date is not None:
            previous_position = _session_position(calendar, previous_date)
            if _calendar_date(calendar, previous_position + 1) != session_date:
                raise Candidate49FutureExecutionError(
                    "candidate49 execution ledger skipped or reordered a session"
                )
        if entry.get("starting_state_sha256") != _canonical_digest(state):
            raise Candidate49FutureExecutionError(
                "candidate49 execution ledger starting state link changed"
            )
        ending = entry.get("ending_state")
        if (
            not isinstance(ending, dict)
            or entry.get("ending_state_sha256") != _canonical_digest(ending)
        ):
            raise Candidate49FutureExecutionError(
                "candidate49 execution ledger ending state changed"
            )
        snapshot = entry.get("daily_execution_snapshot") or {}
        manifest_path = Path(str(snapshot.get("path") or "")).expanduser().resolve()
        expected_snapshot_root, _ = _daily_snapshot_roots(
            data_root,
            session_date,
        )
        if (
            manifest_path != expected_snapshot_root / "snapshot_manifest.json"
            or not manifest_path.is_file()
            or rich.file_digest(manifest_path) != snapshot.get("sha256")
        ):
            raise Candidate49FutureExecutionError(
                f"candidate49 execution daily snapshot changed: {manifest_path}"
            )
        _, frame = _validate_daily_snapshot(
            manifest_path,
            session_date=session_date,
        )
        if snapshot.get("frame_sha256") != rich.frame_digest(frame):
            raise Candidate49FutureExecutionError(
                "candidate49 execution daily snapshot frame link changed"
            )
        settled_value = str(entry.get("settled_at") or "")
        try:
            settled_at = dt.datetime.fromisoformat(
                settled_value.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise Candidate49FutureExecutionError(
                "candidate49 execution ledger settled_at changed"
            ) from exc
        if (
            settled_at.tzinfo is None
            or settled_at.astimezone(candidate.CHINA_TZ).date()
            < session_date
        ):
            raise Candidate49FutureExecutionError(
                "candidate49 execution ledger settled_at changed"
            )
        expected_payload = _session_payload(
            data_root=data_root,
            session_date=session_date,
            calendar=calendar,
            state=state,
            signals=replay_signals,
            snapshot_manifest_path=manifest_path,
            snapshot_frame=frame,
        )
        observed_payload = {
            key: value
            for key, value in entry.items()
            if key not in {"ordinal", "previous_entry_sha256", "entry_sha256"}
        }
        expected_payload.pop("settled_at")
        observed_payload.pop("settled_at")
        if observed_payload != expected_payload:
            raise Candidate49FutureExecutionError(
                "candidate49 execution ledger payload changed: "
                f"{entry.get('entry_id')}"
            )
        state = expected_payload["ending_state"]
        previous_date = session_date
    _validate_evaluation_progression(list(ledger["entries"]))
    return ledger, state, previous_date


def _daily_snapshot_roots(
    data_root: Path,
    session_date: dt.date,
) -> tuple[Path, Path]:
    final = (
        data_root
        / EXECUTION_DAILY_ROOT_BELOW_DATA_ROOT
        / session_date.isoformat()
    ).resolve()
    partial = final.parent / f".{final.name}.partial"
    return final, partial


def _daily_row(
    *,
    daily_raw_root: Path,
    symbol: str,
    session_date: dt.date,
) -> dict[str, Any]:
    path = daily_raw_root / f"{symbol.lower()}.parquet"
    base = {
        "trade_date": pd.Timestamp(session_date),
        "symbol": symbol,
        "raw_open": np.nan,
        "raw_high": np.nan,
        "raw_low": np.nan,
        "raw_close": np.nan,
        "raw_volume": np.nan,
        "amount": np.nan,
        "prior_raw_close": np.nan,
        "price_basis": None,
        "source_file_sha256": None,
        "source_row_status": "missing_source_file",
    }
    if not path.is_file():
        return base
    source_sha256 = rich.file_digest(path)
    try:
        daily = pd.read_parquet(
            path,
            columns=list(RAW_DAILY_FIELDS),
            filters=[("date", "<=", pd.Timestamp(session_date))],
        )
    except Exception as exc:
        base["source_file_sha256"] = source_sha256
        base["source_row_status"] = (
            "required_projection_failed:" + type(exc).__name__
        )
        return base
    if rich.file_digest(path) != source_sha256:
        raise Candidate49FutureExecutionError(
            f"candidate49 raw daily file changed while being read: {path}"
        )
    base["source_file_sha256"] = source_sha256
    if tuple(daily.columns) != RAW_DAILY_FIELDS:
        raise Candidate49FutureExecutionError(
            f"candidate49 raw daily projection changed: {path}"
        )
    daily["date"] = pd.to_datetime(daily["date"], errors="coerce").dt.normalize()
    if daily["date"].gt(pd.Timestamp(session_date)).any():
        raise Candidate49FutureExecutionError(
            f"candidate49 raw daily projection crossed session boundary: {path}"
        )
    selected = daily.loc[daily["date"].eq(pd.Timestamp(session_date))]
    prior = daily.loc[daily["date"].lt(pd.Timestamp(session_date))]
    if not prior.empty:
        prior_row = prior.sort_values("date", kind="stable").iloc[-1]
        if (
            str(prior_row["price_basis"])
            == candidate.research.REQUIRED_PRICE_BASIS
        ):
            base["prior_raw_close"] = pd.to_numeric(
                prior_row["raw_close"],
                errors="coerce",
            )
    if selected.empty:
        base["source_row_status"] = "missing_session_row"
        return base
    row = selected.iloc[-1]
    for field in (
        "raw_open",
        "raw_high",
        "raw_low",
        "raw_close",
        "raw_volume",
        "amount",
    ):
        base[field] = pd.to_numeric(row[field], errors="coerce")
    base["price_basis"] = str(row["price_basis"])
    finite = all(
        np.isfinite(float(base[field]))
        for field in (
            "raw_open",
            "raw_high",
            "raw_low",
            "raw_close",
            "raw_volume",
            "amount",
        )
    )
    if base["price_basis"] != candidate.research.REQUIRED_PRICE_BASIS:
        base["source_row_status"] = "unaccepted_price_basis"
    elif not finite:
        base["source_row_status"] = "nonfinite_required_value"
    elif min(
        float(base["raw_open"]),
        float(base["raw_high"]),
        float(base["raw_low"]),
        float(base["raw_close"]),
    ) <= 0.0:
        base["source_row_status"] = "nonpositive_price"
    elif (
        float(base["raw_high"])
        < max(
            float(base["raw_open"]),
            float(base["raw_low"]),
            float(base["raw_close"]),
        )
        or float(base["raw_low"])
        > min(
            float(base["raw_open"]),
            float(base["raw_high"]),
            float(base["raw_close"]),
        )
    ):
        base["source_row_status"] = "invalid_ohlc_envelope"
    elif float(base["raw_volume"]) < 0.0 or float(base["amount"]) < 0.0:
        base["source_row_status"] = "negative_activity"
    else:
        base["source_row_status"] = "accepted"
    return base


def _validate_daily_snapshot(
    manifest_path: Path,
    *,
    session_date: dt.date,
) -> tuple[dict[str, Any], pd.DataFrame]:
    manifest = rich.load_json_record(manifest_path, kind=DAILY_SNAPSHOT_KIND)
    frame_path = manifest_path.parent / "daily.parquet"
    if not (
        manifest.get("status")
        == "atomically_published_immutable_future_execution_daily_snapshot"
        and manifest.get("execution_protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("registration_sha256")
        == candidate.FUTURE_REGISTRATION_SHA256
        and manifest.get("session_date") == session_date.isoformat()
        and manifest.get("daily_columns") == list(DAILY_COLUMNS)
        and manifest.get("accepted_daily_source")
        in {"eastmoney", "baostock", "tushare"}
        and manifest.get("raw_daily_fields_read") == list(RAW_DAILY_FIELDS)
        and manifest.get("forward_return_fields_read") is False
        and frame_path.is_file()
        and rich.file_digest(frame_path) == manifest.get("frame_byte_sha256")
    ):
        raise Candidate49FutureExecutionError(
            f"candidate49 execution daily snapshot header changed: {manifest_path}"
        )
    source_context = manifest.get("source_context")
    daily_raw_root = manifest.get("daily_raw_root")
    if not (
        isinstance(source_context, dict)
        and set(source_context)
        == {"calendar", "buyable_universe", "price_basis"}
        and all(
            isinstance(source_context[name], dict)
            and set(source_context[name]) == {"path", "sha256"}
            and isinstance(source_context[name].get("path"), str)
            and len(str(source_context[name].get("sha256") or "")) == 64
            for name in source_context
        )
        and isinstance(daily_raw_root, dict)
        and set(daily_raw_root)
        == {"path", "layout", "source_file_sha256_column"}
        and isinstance(daily_raw_root.get("path"), str)
        and daily_raw_root.get("layout") == "lowercase_symbol_parquet"
        and daily_raw_root.get("source_file_sha256_column")
        == "source_file_sha256"
    ):
        raise Candidate49FutureExecutionError(
            f"candidate49 execution source context changed: {manifest_path}"
        )
    for name, link in source_context.items():
        source_path = Path(str(link["path"])).expanduser()
        if (
            not source_path.is_file()
            or rich.file_digest(source_path) != link["sha256"]
        ):
            raise Candidate49FutureExecutionError(
                "candidate49 execution source context link changed: "
                f"{name}:{source_path}"
            )
    provider_uri = Path(
        str(source_context["price_basis"]["path"])
    ).parent.resolve()
    if Path(str(daily_raw_root["path"])).expanduser().resolve() != (
        _expected_daily_raw_root(provider_uri)
    ):
        raise Candidate49FutureExecutionError(
            "candidate49 execution daily raw root binding changed: "
            f"{manifest_path}"
        )
    frame = pd.read_parquet(frame_path)
    if tuple(frame.columns) != DAILY_COLUMNS:
        raise Candidate49FutureExecutionError(
            f"candidate49 execution daily frame changed: {frame_path}"
        )
    accepted_rows = int(frame["source_row_status"].eq("accepted").sum())
    if (
        len(frame) != int(manifest.get("rows", -1))
        or len(frame) != int(manifest.get("symbols", -1))
        or accepted_rows != int(manifest.get("accepted_rows", -1))
        or len(frame) - accepted_rows
        != int(manifest.get("missing_or_invalid_rows", -1))
        or rich.frame_digest(frame) != manifest.get("frame_sha256")
        or frame["symbol"].duplicated().any()
        or frame["symbol"].astype(str).tolist()
        != sorted(frame["symbol"].astype(str).tolist())
        or not pd.to_datetime(
            frame["trade_date"],
            errors="coerce",
        ).eq(pd.Timestamp(session_date)).all()
        or not frame.loc[
            frame["source_row_status"].eq("accepted"),
            "price_basis",
        ].eq(candidate.research.REQUIRED_PRICE_BASIS).all()
        or frame.loc[
            ~frame["source_row_status"].eq("missing_source_file"),
            "source_file_sha256",
        ].map(lambda value: isinstance(value, str) and len(value) == 64).eq(
            False
        ).any()
        or frame.loc[
            frame["source_row_status"].eq("missing_source_file"),
            "source_file_sha256",
        ].notna().any()
    ):
        raise Candidate49FutureExecutionError(
            f"candidate49 execution daily frame changed: {frame_path}"
        )
    return manifest, frame


def _required_snapshot_symbols(
    *,
    provider_uri: Path,
    session_date: dt.date,
    state: dict[str, Any],
    entering_signals: list[dict[str, Any]],
    outcome_signals: list[dict[str, Any]],
) -> list[str]:
    instrument_path = (
        provider_uri / "instruments" / "buyable_main_chinext.txt"
    )
    symbols = set(
        candidate._active_buyable_symbols(instrument_path, session_date)
    )
    symbols.update(
        str(position["symbol"]) for position in state.get("positions") or []
    )
    for entry in entering_signals:
        symbols.update(str(item["symbol"]) for item in entry["selections"])
    for entry in outcome_signals:
        _, factor = _load_signal_factor(entry)
        symbols.update(
            factor.loc[
                factor[f"{candidate.FACTOR_NAME}_eligible"].astype(bool),
                "symbol",
            ].astype(str)
        )
    return sorted(symbols)


def _current_source_context(provider_uri: Path) -> dict[str, dict[str, str]]:
    paths = {
        "calendar": provider_uri / "calendars" / "day.txt",
        "buyable_universe": (
            provider_uri / "instruments" / "buyable_main_chinext.txt"
        ),
        "price_basis": provider_uri / "price_basis.json",
    }
    return {
        name: {"path": str(path), "sha256": rich.file_digest(path)}
        for name, path in paths.items()
    }


def _expected_daily_raw_root(provider_uri: Path) -> Path:
    provider_uri = provider_uri.expanduser().resolve()
    if (
        provider_uri.name != "cn_a_share"
        or provider_uri.parent.name != "qlib"
    ):
        raise Candidate49FutureExecutionError(
            "provider_uri_not_under_active_root_qlib_cn_a_share"
        )
    return (
        provider_uri.parent.parent / "raw" / "a_share" / "daily"
    ).resolve()


def _publish_daily_snapshot(
    *,
    data_root: Path,
    provider_uri: Path,
    daily_raw_root: Path,
    session_date: dt.date,
    symbols: list[str],
    expected_daily_source: str,
) -> tuple[Path, dict[str, Any], pd.DataFrame]:
    final, partial = _daily_snapshot_roots(data_root, session_date)
    final_manifest = final / "snapshot_manifest.json"
    if final.exists():
        if not final_manifest.is_file():
            raise Candidate49FutureExecutionError(
                f"published execution daily root has no manifest: {final}"
            )
        manifest, frame = _validate_daily_snapshot(
            final_manifest,
            session_date=session_date,
        )
        if frame["symbol"].astype(str).tolist() != symbols:
            raise Candidate49FutureExecutionError(
                "candidate49 existing execution snapshot symbol scope changed"
            )
        return final_manifest, manifest, frame
    if partial.exists():
        raise Candidate49FutureExecutionError(
            "candidate49 execution daily partial exists without publication; "
            "inspect it before removal because outcome snapshots are not resumable"
        )
    partial.mkdir(parents=True, exist_ok=False)
    try:
        rows = [
            _daily_row(
                daily_raw_root=daily_raw_root,
                symbol=symbol,
                session_date=session_date,
            )
            for symbol in symbols
        ]
        frame = pd.DataFrame(rows).loc[:, DAILY_COLUMNS]
        frame = frame.sort_values("symbol", kind="stable").reset_index(drop=True)
        frame_path = partial / "daily.parquet"
        rich.atomic_write_frame(frame, frame_path)
        manifest = {
            "schema_version": 1,
            "kind": DAILY_SNAPSHOT_KIND,
            "status": (
                "atomically_published_immutable_future_execution_daily_snapshot"
            ),
            "created_at": _utc_now(),
            "execution_protocol": {
                "path": str(DEFAULT_PROTOCOL),
                "sha256": PROTOCOL_SHA256,
            },
            "execution_protocol_sha256": PROTOCOL_SHA256,
            "registration_id": candidate.FUTURE_REGISTRATION_ID,
            "registration_sha256": candidate.FUTURE_REGISTRATION_SHA256,
            "session_date": session_date.isoformat(),
            "accepted_daily_source": expected_daily_source,
            "symbol_scope": (
                "active_buyable_union_open_positions_entries_and_due_rank_ic"
            ),
            "symbols": len(symbols),
            "rows": len(frame),
            "accepted_rows": int(
                frame["source_row_status"].eq("accepted").sum()
            ),
            "missing_or_invalid_rows": int(
                (~frame["source_row_status"].eq("accepted")).sum()
            ),
            "daily_columns": list(DAILY_COLUMNS),
            "frame_byte_sha256": rich.file_digest(frame_path),
            "frame_sha256": rich.frame_digest(frame),
            "source_context": _current_source_context(provider_uri),
            "daily_raw_root": {
                "path": str(daily_raw_root),
                "layout": "lowercase_symbol_parquet",
                "source_file_sha256_column": "source_file_sha256",
            },
            "raw_daily_fields_read": list(RAW_DAILY_FIELDS),
            "adjusted_execution_price_fields_read": [],
            "historical_candidate49_price_or_return_fields_read": [],
            "forward_return_fields_read": False,
            "live_order_performed": False,
            "missing_values_imputed": False,
        }
        rich.atomic_write_json(manifest, partial / "snapshot_manifest.json")
        partial.replace(final)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return (
        final_manifest,
        *_validate_daily_snapshot(final_manifest, session_date=session_date),
    )


def _quote_map(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return {
        str(row["symbol"]): row.to_dict() for _, row in frame.iterrows()
    }


def _finite_positive(value: Any) -> bool:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return bool(np.isfinite(numeric) and numeric > 0.0)


def _one_price(
    row: dict[str, Any],
    field: str,
    compared_fields: tuple[str, ...],
) -> bool:
    reference = float(row[field])
    return all(
        math.isclose(
            float(row[column]),
            reference,
            rel_tol=0.0,
            abs_tol=ONE_PRICE_TOLERANCE,
        )
        for column in compared_fields
    )


def _entry_block_reason(row: dict[str, Any] | None) -> str | None:
    if row is None or row.get("source_row_status") != "accepted":
        return "missing_or_unaccepted_daily_row"
    if not (
        _finite_positive(row.get("raw_open"))
        and _finite_positive(row.get("prior_raw_close"))
        and _finite_positive(row.get("raw_volume"))
        and _finite_positive(row.get("amount"))
    ):
        return "missing_nonpositive_quote_activity_or_prior_close"
    if _one_price(
        row,
        "raw_open",
        ("raw_open", "raw_high", "raw_low"),
    ) and float(row["raw_open"]) > float(
        row["prior_raw_close"]
    ):
        return "one_price_up_day"
    return None


def _exit_block_reason(row: dict[str, Any] | None) -> str | None:
    if row is None or row.get("source_row_status") != "accepted":
        return "missing_or_unaccepted_daily_row"
    if not (
        _finite_positive(row.get("raw_close"))
        and _finite_positive(row.get("prior_raw_close"))
        and _finite_positive(row.get("raw_volume"))
        and _finite_positive(row.get("amount"))
    ):
        return "missing_nonpositive_quote_activity_or_prior_close"
    if _one_price(
        row,
        "raw_close",
        ("raw_close", "raw_high", "raw_low"),
    ) and float(row["raw_close"]) < float(
        row["prior_raw_close"]
    ):
        return "one_price_down_day"
    return None


def _entry_events(
    *,
    state: dict[str, Any],
    entering_signals: list[dict[str, Any]],
    session_date: dt.date,
    calendar: pd.DatetimeIndex,
    quotes: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
    cash = float(state["cash_cny"])
    prior_equity = float(state["equity_cny"])
    positions = [dict(position) for position in state["positions"]]
    events: list[dict[str, Any]] = []
    for signal in entering_signals:
        signal_id = str(signal["entry_id"])
        if signal_id in set(state["processed_signal_entry_ids"]):
            raise Candidate49FutureExecutionError(
                f"candidate49 signal was already processed: {signal_id}"
            )
        _, expected_entry, expected_exit = _signal_timing(signal, calendar)
        if expected_entry != session_date:
            raise Candidate49FutureExecutionError(
                "candidate49 entry timing changed"
            )
        target_slot = prior_equity * SLOT_FRACTION
        signal_target_cap = prior_equity * SIGNAL_FRACTION
        planned_notional = 0.0
        for selection in sorted(
            signal["selections"],
            key=lambda item: (int(item["rank"]), str(item["symbol"])),
        ):
            symbol = str(selection["symbol"])
            row = quotes.get(symbol)
            block_reason = _entry_block_reason(row)
            target_shares = 0
            shares = 0
            execution_price: float | None = None
            raw_notional = 0.0
            buy_fees = 0.0
            cash_debit = 0.0
            participation: float | None = None
            if block_reason is None:
                assert row is not None
                execution_price = float(row["raw_open"]) * (1.0 + SLIPPAGE_RATE)
                remaining_cap = max(signal_target_cap - planned_notional, 0.0)
                allowed_target = min(target_slot, remaining_cap)
                target_shares = (
                    int(allowed_target // (execution_price * LOT_SIZE)) * LOT_SIZE
                )
                per_lot_debit = (
                    LOT_SIZE
                    * execution_price
                    * (1.0 + COMMISSION_RATE + TRANSFER_FEE_RATE)
                )
                cash_lots = int(cash // per_lot_debit)
                shares = min(target_shares, cash_lots * LOT_SIZE)
                if shares < LOT_SIZE:
                    shares = 0
                    block_reason = (
                        "target_or_shared_cash_cannot_afford_one_board_lot"
                    )
                else:
                    raw_notional = shares * float(row["raw_open"])
                    execution_notional = shares * execution_price
                    buy_fees = execution_notional * (
                        COMMISSION_RATE + TRANSFER_FEE_RATE
                    )
                    cash_debit = execution_notional + buy_fees
                    cash -= cash_debit
                    planned_notional += raw_notional
                    participation = raw_notional / float(row["amount"])
                    lot_id = f"{signal_id}:rank:{int(selection['rank'])}"
                    positions.append(
                        {
                            "lot_id": lot_id,
                            "signal_entry_id": signal_id,
                            "signal_session": signal["session_date"],
                            "rank": int(selection["rank"]),
                            "symbol": symbol,
                            "entry_session": session_date.isoformat(),
                            "scheduled_exit_session": expected_exit.isoformat(),
                            "shares": shares,
                            "raw_entry_price": float(row["raw_open"]),
                            "execution_entry_price": execution_price,
                            "buy_execution_notional_cny": execution_notional,
                            "buy_fees_cny": buy_fees,
                            "buy_cash_debit_cny": cash_debit,
                            "exit_attempts": 0,
                            "last_mark_price": float(row["raw_open"]),
                            "last_mark_session": session_date.isoformat(),
                            "status": "open",
                        }
                    )
            events.append(
                {
                    "signal_entry_id": signal_id,
                    "signal_session": signal["session_date"],
                    "rank": int(selection["rank"]),
                    "symbol": symbol,
                    "target_slot_notional_cny": target_slot,
                    "target_shares": target_shares,
                    "filled_shares": shares,
                    "raw_open": (
                        None if row is None else float(row["raw_open"])
                        if _finite_positive(row.get("raw_open"))
                        else None
                    ),
                    "execution_price": execution_price,
                    "raw_notional_cny": raw_notional,
                    "buy_fees_cny": buy_fees,
                    "cash_debit_cny": cash_debit,
                    "amount_participation": participation,
                    "board_lot_affordable": shares >= LOT_SIZE,
                    "status": "filled" if shares >= LOT_SIZE else "unfilled",
                    "reason": block_reason,
                    "replacement_used": False,
                }
            )
    return events, positions, cash


def _exit_events(
    *,
    positions: list[dict[str, Any]],
    cash: float,
    session_date: dt.date,
    quotes: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
    events: list[dict[str, Any]] = []
    remaining: list[dict[str, Any]] = []
    for original in positions:
        position = dict(original)
        if (
            position["status"] != "open"
            or dt.date.fromisoformat(position["scheduled_exit_session"])
            > session_date
        ):
            remaining.append(position)
            continue
        position["exit_attempts"] = int(position["exit_attempts"]) + 1
        row = quotes.get(str(position["symbol"]))
        block_reason = _exit_block_reason(row)
        if block_reason is None:
            assert row is not None
            raw_close = float(row["raw_close"])
            execution_price = raw_close * (1.0 - SLIPPAGE_RATE)
            execution_notional = int(position["shares"]) * execution_price
            sell_fees = execution_notional * (
                COMMISSION_RATE + TRANSFER_FEE_RATE + STAMP_DUTY_RATE
            )
            cash_credit = execution_notional - sell_fees
            cash += cash_credit
            raw_notional = int(position["shares"]) * raw_close
            participation = raw_notional / float(row["amount"])
            events.append(
                {
                    "lot_id": position["lot_id"],
                    "signal_entry_id": position["signal_entry_id"],
                    "symbol": position["symbol"],
                    "shares": position["shares"],
                    "scheduled_exit_session": position[
                        "scheduled_exit_session"
                    ],
                    "actual_exit_session": session_date.isoformat(),
                    "exit_attempt": position["exit_attempts"],
                    "raw_close": raw_close,
                    "execution_price": execution_price,
                    "raw_notional_cny": raw_notional,
                    "sell_fees_cny": sell_fees,
                    "cash_credit_cny": cash_credit,
                    "realized_net_pnl_cny": (
                        cash_credit - float(position["buy_cash_debit_cny"])
                    ),
                    "amount_participation": participation,
                    "status": "filled",
                    "reason": None,
                }
            )
        else:
            if int(position["exit_attempts"]) >= MAX_EXIT_ATTEMPTS:
                position["status"] = "terminal_unresolved"
                status = "terminal_unresolved_after_twenty_attempts"
            else:
                status = "blocked_retry_pending"
            remaining.append(position)
            events.append(
                {
                    "lot_id": position["lot_id"],
                    "signal_entry_id": position["signal_entry_id"],
                    "symbol": position["symbol"],
                    "shares": position["shares"],
                    "scheduled_exit_session": position[
                        "scheduled_exit_session"
                    ],
                    "actual_exit_session": None,
                    "exit_attempt": position["exit_attempts"],
                    "raw_close": (
                        float(row["raw_close"])
                        if row is not None and _finite_positive(row.get("raw_close"))
                        else None
                    ),
                    "execution_price": None,
                    "raw_notional_cny": 0.0,
                    "sell_fees_cny": 0.0,
                    "cash_credit_cny": 0.0,
                    "realized_net_pnl_cny": None,
                    "amount_participation": None,
                    "status": status,
                    "reason": block_reason,
                }
            )
    return events, remaining, cash


def _execution_snapshot_frame(
    manifest_path: Path,
    session_date: dt.date,
) -> pd.DataFrame:
    _, frame = _validate_daily_snapshot(
        manifest_path,
        session_date=session_date,
    )
    return frame


def _rank_ic_outcomes(
    *,
    data_root: Path,
    outcome_signals: list[dict[str, Any]],
    session_date: dt.date,
    calendar: pd.DatetimeIndex,
    exit_frame: pd.DataFrame,
) -> list[dict[str, Any]]:
    exit_quotes = exit_frame.set_index("symbol")
    outcomes: list[dict[str, Any]] = []
    for signal in outcome_signals:
        _, entry_session, expected_exit = _signal_timing(signal, calendar)
        if expected_exit != session_date:
            raise Candidate49FutureExecutionError(
                "candidate49 fixed Rank IC horizon changed"
            )
        entry_root, _ = _daily_snapshot_roots(data_root, entry_session)
        entry_manifest = entry_root / "snapshot_manifest.json"
        if not entry_manifest.is_file():
            raise Candidate49FutureExecutionError(
                f"candidate49 entry daily snapshot is missing: {entry_manifest}"
            )
        entry_frame = _execution_snapshot_frame(entry_manifest, entry_session)
        entry_quotes = entry_frame.set_index("symbol")
        factor_manifest, factor = _load_signal_factor(signal)
        eligible = factor.loc[
            factor[f"{candidate.FACTOR_NAME}_eligible"].astype(bool),
            ["symbol", candidate.FACTOR_NAME],
        ].copy()
        rows: list[dict[str, Any]] = []
        for row in eligible.itertuples(index=False):
            symbol = str(row.symbol)
            entry_row = (
                entry_quotes.loc[symbol]
                if symbol in entry_quotes.index
                else None
            )
            exit_row = (
                exit_quotes.loc[symbol] if symbol in exit_quotes.index else None
            )
            raw_open = (
                float(entry_row["raw_open"])
                if entry_row is not None
                and entry_row["source_row_status"] == "accepted"
                and _finite_positive(entry_row["raw_open"])
                else np.nan
            )
            raw_close = (
                float(exit_row["raw_close"])
                if exit_row is not None
                and exit_row["source_row_status"] == "accepted"
                and _finite_positive(exit_row["raw_close"])
                else np.nan
            )
            if np.isfinite(raw_open) and np.isfinite(raw_close):
                rows.append(
                    {
                        "symbol": symbol,
                        "factor": float(
                            getattr(row, candidate.FACTOR_NAME)
                        ),
                        "return": raw_close / raw_open - 1.0,
                    }
                )
        values = pd.DataFrame(rows)
        valid_names = len(values)
        rank_ic: float | None = None
        status = "unusable_fewer_than_50_valid_names"
        if valid_names >= MINIMUM_RANK_IC_NAMES:
            rank_ic_value = values["factor"].rank(method="average").corr(
                values["return"].rank(method="average")
            )
            if pd.notna(rank_ic_value) and np.isfinite(float(rank_ic_value)):
                rank_ic = float(rank_ic_value)
                status = "completed"
            else:
                status = "unusable_nonfinite_rank_ic"
        outcomes.append(
            {
                "signal_entry_id": signal["entry_id"],
                "signal_session": signal["session_date"],
                "entry_session": entry_session.isoformat(),
                "exit_session": session_date.isoformat(),
                "factor_manifest_sha256": rich.file_digest(
                    Path(signal["factor_snapshot"]["path"])
                ),
                "eligible_names": int(
                    factor[
                        f"{candidate.FACTOR_NAME}_eligible"
                    ].astype(bool).sum()
                ),
                "valid_outcome_names": valid_names,
                "minimum_valid_names": MINIMUM_RANK_IC_NAMES,
                "rank_ic": rank_ic,
                "positive_rank_ic": (
                    None if rank_ic is None else rank_ic > 0.0
                ),
                "status": status,
                "outcome": "raw_close_t_plus_3/raw_open_t_plus_1_minus_1",
                "tradeability_filter_applied": False,
                "factor_snapshot_created_at": factor_manifest["created_at"],
            }
        )
    return outcomes


def _mark_positions(
    *,
    positions: list[dict[str, Any]],
    quotes: dict[str, dict[str, Any]],
    session_date: dt.date,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
    marked: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    value = 0.0
    for original in positions:
        position = dict(original)
        row = quotes.get(str(position["symbol"]))
        if (
            row is not None
            and row.get("source_row_status") == "accepted"
            and _finite_positive(row.get("raw_close"))
        ):
            position["last_mark_price"] = float(row["raw_close"])
            position["last_mark_session"] = session_date.isoformat()
        else:
            stale.append(
                {
                    "lot_id": position["lot_id"],
                    "symbol": position["symbol"],
                    "carried_mark_price": position["last_mark_price"],
                    "last_mark_session": position["last_mark_session"],
                }
            )
        value += int(position["shares"]) * float(position["last_mark_price"])
        marked.append(position)
    return marked, stale, value


def _session_payload(
    *,
    data_root: Path,
    session_date: dt.date,
    calendar: pd.DatetimeIndex,
    state: dict[str, Any],
    signals: list[dict[str, Any]],
    snapshot_manifest_path: Path,
    snapshot_frame: pd.DataFrame,
    settled_at: str | None = None,
) -> dict[str, Any]:
    entering = [
        signal
        for signal in signals
        if _signal_timing(signal, calendar)[1] == session_date
    ]
    outcomes_due = [
        signal
        for signal in signals
        if _signal_timing(signal, calendar)[2] == session_date
    ]
    starting_state_sha256 = _canonical_digest(state)
    quotes = _quote_map(snapshot_frame)
    entry_events, positions_after_entries, cash_after_entries = _entry_events(
        state=state,
        entering_signals=entering,
        session_date=session_date,
        calendar=calendar,
        quotes=quotes,
    )
    exit_events, positions_after_exits, ending_cash = _exit_events(
        positions=positions_after_entries,
        cash=cash_after_entries,
        session_date=session_date,
        quotes=quotes,
    )
    rank_ic_outcomes = _rank_ic_outcomes(
        data_root=data_root,
        outcome_signals=outcomes_due,
        session_date=session_date,
        calendar=calendar,
        exit_frame=snapshot_frame,
    )
    marked_positions, stale_marks, position_value = _mark_positions(
        positions=positions_after_exits,
        quotes=quotes,
        session_date=session_date,
    )
    ending_equity = ending_cash + position_value
    high_watermark = max(float(state["high_watermark_cny"]), ending_equity)
    drawdown = ending_equity / high_watermark - 1.0
    prior_max_drawdown = float(state["maximum_drawdown"])
    completed = [
        item for item in rank_ic_outcomes if item["status"] == "completed"
    ]
    completed_count = int(state["completed_rank_ic_signals"]) + len(completed)
    rank_ic_sum = float(state["rank_ic_sum"]) + sum(
        float(item["rank_ic"]) for item in completed
    )
    positive_count = int(state["positive_rank_ic_signals"]) + sum(
        bool(item["positive_rank_ic"]) for item in completed
    )
    opportunities = int(state["entry_opportunities"]) + len(entry_events)
    affordable = int(state["board_lot_affordable_opportunities"]) + sum(
        bool(item["board_lot_affordable"]) for item in entry_events
    )
    buy_fees = sum(float(item["buy_fees_cny"]) for item in entry_events)
    sell_fees = sum(float(item["sell_fees_cny"]) for item in exit_events)
    slippage = sum(
        (
            float(item["filled_shares"])
            * float(item["raw_open"])
            * SLIPPAGE_RATE
        )
        for item in entry_events
        if item["status"] == "filled"
    ) + sum(
        (
            int(item["shares"])
            * float(item["raw_close"])
            * SLIPPAGE_RATE
        )
        for item in exit_events
        if item["status"] == "filled"
    )
    participations = [
        float(item["amount_participation"])
        for item in [*entry_events, *exit_events]
        if item.get("amount_participation") is not None
    ]
    processed_signal_ids = [
        *state["processed_signal_entry_ids"],
        *[str(signal["entry_id"]) for signal in entering],
    ]
    if len(processed_signal_ids) != len(set(processed_signal_ids)):
        raise Candidate49FutureExecutionError(
            "candidate49 processed-signal identity duplicated"
        )
    ending_state = {
        "cash_cny": ending_cash,
        "positions": sorted(
            marked_positions,
            key=lambda item: str(item["lot_id"]),
        ),
        "equity_cny": ending_equity,
        "high_watermark_cny": high_watermark,
        "cumulative_net_return": ending_equity / INITIAL_CASH - 1.0,
        "maximum_drawdown": min(prior_max_drawdown, drawdown),
        "entry_opportunities": opportunities,
        "board_lot_affordable_opportunities": affordable,
        "board_lot_affordability": (
            affordable / opportunities if opportunities else None
        ),
        "cumulative_buy_fees_cny": (
            float(state["cumulative_buy_fees_cny"]) + buy_fees
        ),
        "cumulative_sell_fees_cny": (
            float(state["cumulative_sell_fees_cny"]) + sell_fees
        ),
        "cumulative_slippage_cost_cny": (
            float(state["cumulative_slippage_cost_cny"]) + slippage
        ),
        "maximum_observed_amount_participation": max(
            float(state["maximum_observed_amount_participation"]),
            max(participations, default=0.0),
        ),
        "completed_rank_ic_signals": completed_count,
        "rank_ic_sum": rank_ic_sum,
        "mean_rank_ic": (
            rank_ic_sum / completed_count if completed_count else None
        ),
        "positive_rank_ic_signals": positive_count,
        "positive_rank_ic_rate": (
            positive_count / completed_count if completed_count else None
        ),
        "processed_signal_entry_ids": processed_signal_ids,
        "terminal_unresolved_lots": sum(
            position["status"] == "terminal_unresolved"
            for position in marked_positions
        ),
    }
    evaluation = _evaluation_flags(ending_state)
    return {
        "entry_id": (
            f"{candidate.FUTURE_REGISTRATION_ID}:execution:"
            f"{session_date.isoformat()}"
        ),
        "session_date": session_date.isoformat(),
        "settled_at": settled_at or _utc_now(),
        "execution_protocol": {
            "path": str(DEFAULT_PROTOCOL),
            "sha256": PROTOCOL_SHA256,
        },
        "execution_protocol_sha256": PROTOCOL_SHA256,
        "registration_sha256": candidate.FUTURE_REGISTRATION_SHA256,
        "daily_execution_snapshot": {
            "path": str(snapshot_manifest_path),
            "sha256": rich.file_digest(snapshot_manifest_path),
            "frame_sha256": rich.frame_digest(snapshot_frame),
        },
        "starting_state_sha256": starting_state_sha256,
        "signals_entering": [
            {
                "entry_id": signal["entry_id"],
                "session_date": signal["session_date"],
                "entry_sha256": signal["entry_sha256"],
            }
            for signal in entering
        ],
        "entry_events": entry_events,
        "exit_events": exit_events,
        "future_rank_ic_outcomes": rank_ic_outcomes,
        "stale_marks": stale_marks,
        "session_costs": {
            "buy_fees_cny": buy_fees,
            "sell_fees_cny": sell_fees,
            "estimated_adverse_slippage_cost_cny": slippage,
        },
        "ending_state": ending_state,
        "ending_state_sha256": _canonical_digest(ending_state),
        "evaluation": evaluation,
        "historical_candidate49_price_or_return_fields_read": [],
        "forward_outcomes_read_only_for_registered_signals": [
            item["signal_entry_id"] for item in rank_ic_outcomes
        ],
        "provider_request_issued": False,
        "live_order_performed": False,
        "investment_advice": False,
    }


def _preflight(
    *,
    through_session: dt.date,
    provider_uri: Path,
    daily_raw_root: Path,
    now: dt.datetime | None,
) -> tuple[pd.DatetimeIndex, dict[str, Any]]:
    load_execution_protocol()
    local_now = now or dt.datetime.now(candidate.CHINA_TZ)
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=candidate.CHINA_TZ)
    else:
        local_now = local_now.astimezone(candidate.CHINA_TZ)
    failures: list[str] = []
    if through_session < candidate.EARLIEST_FUTURE_SESSION:
        failures.append("session_precedes_future_registration_boundary")
    if through_session > local_now.date() or (
        through_session == local_now.date()
        and local_now.time().replace(tzinfo=None)
        < candidate.SESSION_CLOSE_READINESS_TIME
    ):
        failures.append("session_not_complete_after_close_buffer")
    try:
        expected_daily_raw_root = _expected_daily_raw_root(provider_uri)
    except Candidate49FutureExecutionError:
        failures.append("provider_uri_not_under_active_root_qlib_cn_a_share")
    else:
        if daily_raw_root != expected_daily_raw_root:
            failures.append(
                "daily_raw_root_not_bound_to_accepted_provider_root"
            )
    price_basis_path = provider_uri / "price_basis.json"
    price_basis: dict[str, Any] = {}
    if price_basis_path.is_file():
        price_basis = json.loads(price_basis_path.read_text(encoding="utf-8"))
    if not (
        price_basis.get("status") == "passed"
        and price_basis.get("price_basis")
        == candidate.research.REQUIRED_PRICE_BASIS
        and not price_basis.get("failures")
    ):
        failures.append("local_daily_price_basis_not_passed")
    daily_sources = price_basis.get("daily_sources")
    if not (
        isinstance(daily_sources, list)
        and len(daily_sources) == 1
        and daily_sources[0] in {"eastmoney", "baostock", "tushare"}
    ):
        failures.append("local_daily_source_not_single_accepted_provider")
    processing_lag_ready_session: dt.date | None = None
    try:
        calendar = _read_calendar(provider_uri)
        through_position = _session_position(calendar, through_session)
        if through_position + 2 >= len(calendar):
            failures.append(
                "two_later_accepted_sessions_required_to_freeze_t_plus_3_exit"
            )
        else:
            processing_lag_ready_session = _calendar_date(
                calendar,
                through_position + 2,
            )
            if (
                processing_lag_ready_session > local_now.date()
                or (
                    processing_lag_ready_session == local_now.date()
                    and local_now.time().replace(tzinfo=None)
                    < candidate.SESSION_CLOSE_READINESS_TIME
                )
            ):
                failures.append(
                    "two_later_accepted_sessions_not_yet_complete_after_close_buffer"
                )
    except Exception:
        calendar = pd.DatetimeIndex([])
        failures.append("session_not_in_valid_accepted_local_calendar")
    result = {
        "status": (
            "ready_for_local_paper_settlement"
            if not failures
            else "not_ready_no_execution_write"
        ),
        "through_session": through_session.isoformat(),
        "processing_lag_ready_session": (
            None
            if processing_lag_ready_session is None
            else processing_lag_ready_session.isoformat()
        ),
        "local_now": local_now.isoformat(),
        "accepted_daily_sources": (
            daily_sources if isinstance(daily_sources, list) else []
        ),
        "failures": failures,
        "ready": not failures,
        "provider_request_issued": False,
        "live_order_performed": False,
    }
    if failures:
        raise Candidate49FutureExecutionError(
            "candidate49 execution stopped before daily snapshot or ledger write: "
            + ",".join(failures)
        )
    return calendar, result


def settle_through_session(
    *,
    data_root: Path,
    through_session: dt.date,
    provider_uri: Path = candidate.DEFAULT_PROVIDER_URI,
    daily_raw_root: Path = observation.DEFAULT_DAILY_RAW_ROOT,
    signal_path: Path = candidate.FUTURE_SIGNAL_LEDGER,
    execution_path: Path = candidate.FUTURE_EXECUTION_LEDGER,
    evaluation_root: Path = DEFAULT_EVALUATION_ROOT,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Settle every not-yet-processed accepted session through the target."""

    data_root = data_root.expanduser().resolve()
    provider_uri = provider_uri.expanduser().resolve()
    daily_raw_root = daily_raw_root.expanduser().resolve()
    signal_path = signal_path.expanduser().resolve()
    execution_path = execution_path.expanduser().resolve()
    evaluation_root = evaluation_root.expanduser().resolve()
    calendar, preflight = _preflight(
        through_session=through_session,
        provider_uri=provider_uri,
        daily_raw_root=daily_raw_root,
        now=now,
    )
    expected_daily_source = str(preflight["accepted_daily_sources"][0])
    candidate.initialize_future_ledgers(
        signal_path=signal_path,
        execution_path=execution_path,
    )
    signals = _validated_signals(signal_path, calendar)
    if not signals:
        execution_ledger = candidate.validate_future_ledger(
            execution_path,
            candidate.FUTURE_EXECUTION_LEDGER_KIND,
        )
        if execution_ledger["entries"]:
            raise Candidate49FutureExecutionError(
                "candidate49 execution ledger exists without its signal ledger"
            )
        return {
            "status": "no_registered_signal_to_settle",
            "through_session": through_session.isoformat(),
            "execution_entries_appended": 0,
            "provider_request_issued": False,
            "live_order_performed": False,
        }
    lock_path = data_root / ".candidate49_future_execution.lock"
    with candidate.foundation.ProcessLock(lock_path):
        ledger, state, last_session = _validate_engine_ledger(
            execution_path,
            calendar,
            data_root=data_root,
            signals=signals,
        )
        _validate_signal_execution_consistency(
            signals=signals,
            execution_entries=list(ledger["entries"]),
            state=state,
            last_session=last_session,
            calendar=calendar,
        )
        evaluation_status = synchronize_evaluation_records(
            entries=list(ledger["entries"]),
            execution_path=execution_path,
            evaluation_root=evaluation_root,
        )
        if evaluation_status["execution_stop_required"]:
            return {
                "status": evaluation_status["status"],
                "through_session": through_session.isoformat(),
                "execution_entries_appended": 0,
                "latest_execution_session": (
                    None if last_session is None else last_session.isoformat()
                ),
                "ending_state": state,
                "evaluation": evaluation_status,
                "provider_request_issued": False,
                "live_order_performed": False,
            }
        actionable_signals = [
            signal
            for signal in signals
            if _session_position(
                calendar,
                dt.date.fromisoformat(str(signal["session_date"])),
            )
            + 3
            < len(calendar)
            and _signal_timing(signal, calendar)[1] <= through_session
        ]
        if not actionable_signals:
            return {
                "status": "no_mature_registered_signal_to_settle",
                "through_session": through_session.isoformat(),
                "execution_entries_appended": 0,
                "evaluation": evaluation_status,
                "provider_request_issued": False,
                "live_order_performed": False,
            }
        first_entry = min(
            _signal_timing(signal, calendar)[1] for signal in actionable_signals
        )
        if last_session is None:
            next_session = first_entry
        else:
            if through_session <= last_session:
                return {
                    "status": "execution_already_settled_idempotent",
                    "through_session": through_session.isoformat(),
                    "execution_entries_appended": 0,
                    "latest_execution_session": last_session.isoformat(),
                    "ending_state": state,
                    "evaluation": evaluation_status,
                    "provider_request_issued": False,
                    "live_order_performed": False,
                }
            next_session = _calendar_date(
                calendar,
                _session_position(calendar, last_session) + 1,
            )
        if next_session > through_session:
            return {
                "status": "execution_already_settled_idempotent",
                "through_session": through_session.isoformat(),
                "execution_entries_appended": 0,
                "latest_execution_session": (
                    None if last_session is None else last_session.isoformat()
                ),
                "ending_state": state,
                "evaluation": evaluation_status,
                "provider_request_issued": False,
                "live_order_performed": False,
            }
        start_position = _session_position(calendar, next_session)
        end_position = _session_position(calendar, through_session)
        appended: list[dict[str, Any]] = []
        ledger_entries = list(ledger["entries"])
        for timestamp in calendar[start_position : end_position + 1]:
            session_date = timestamp.date()
            entering = [
                signal
                for signal in actionable_signals
                if _signal_timing(signal, calendar)[1] == session_date
            ]
            outcomes_due = [
                signal
                for signal in actionable_signals
                if _signal_timing(signal, calendar)[2] == session_date
            ]
            source_context_before = _current_source_context(provider_uri)
            symbols = _required_snapshot_symbols(
                provider_uri=provider_uri,
                session_date=session_date,
                state=state,
                entering_signals=entering,
                outcome_signals=outcomes_due,
            )
            manifest_path, _, frame = _publish_daily_snapshot(
                data_root=data_root,
                provider_uri=provider_uri,
                daily_raw_root=daily_raw_root,
                session_date=session_date,
                symbols=symbols,
                expected_daily_source=expected_daily_source,
            )
            published_manifest = rich.load_json_record(
                manifest_path,
                kind=DAILY_SNAPSHOT_KIND,
            )
            if (
                _current_source_context(provider_uri) != source_context_before
                or published_manifest.get("source_context")
                != source_context_before
            ):
                raise Candidate49FutureExecutionError(
                    "candidate49 accepted daily context changed while the "
                    "execution snapshot was being frozen"
                )
            payload = _session_payload(
                data_root=data_root,
                session_date=session_date,
                calendar=calendar,
                state=state,
                signals=actionable_signals,
                snapshot_manifest_path=manifest_path,
                snapshot_frame=frame,
                settled_at=dt.datetime.fromisoformat(
                    str(preflight["local_now"])
                )
                .astimezone(dt.timezone.utc)
                .isoformat(),
            )
            entry = candidate.append_future_ledger_entry(
                path=execution_path,
                kind=candidate.FUTURE_EXECUTION_LEDGER_KIND,
                payload=payload,
            )
            appended.append(entry)
            ledger_entries.append(entry)
            state = payload["ending_state"]
            evaluation_status = synchronize_evaluation_records(
                entries=ledger_entries,
                execution_path=execution_path,
                evaluation_root=evaluation_root,
            )
            if evaluation_status["execution_stop_required"]:
                break
        candidate.validate_future_ledger(
            execution_path,
            candidate.FUTURE_EXECUTION_LEDGER_KIND,
        )
        return {
            "status": (
                evaluation_status["status"]
                if evaluation_status["execution_stop_required"]
                else "paper_execution_sessions_appended"
            ),
            "through_session": through_session.isoformat(),
            "execution_entries_appended": len(appended),
            "first_appended_session": appended[0]["session_date"],
            "latest_execution_session": appended[-1]["session_date"],
            "ending_state": state,
            "early_rejection_ready": appended[-1]["evaluation"][
                "early_rejection_ready"
            ],
            "early_rejection_triggered": appended[-1]["evaluation"][
                "early_rejection_triggered"
            ],
            "full_gate_ready": appended[-1]["evaluation"]["full_gate_ready"],
            "full_gate_passed": appended[-1]["evaluation"]["full_gate_passed"],
            "evaluation": evaluation_status,
            "provider_request_issued": False,
            "live_order_performed": False,
        }


def _reporting_data_root(
    execution_entries: list[dict[str, Any]],
) -> Path:
    latest = execution_entries[-1]
    session_date = dt.date.fromisoformat(str(latest["session_date"]))
    snapshot = latest.get("daily_execution_snapshot") or {}
    manifest_path = Path(
        str(snapshot.get("path") or "")
    ).expanduser().resolve()
    relative = (
        Path(EXECUTION_DAILY_ROOT_BELOW_DATA_ROOT)
        / session_date.isoformat()
        / "snapshot_manifest.json"
    )
    try:
        data_root = manifest_path.parents[len(relative.parts) - 1]
    except IndexError as exc:
        raise Candidate49FutureExecutionError(
            "candidate49 reporting execution snapshot path changed"
        ) from exc
    if (data_root / relative).resolve() != manifest_path:
        raise Candidate49FutureExecutionError(
            "candidate49 reporting execution snapshot path changed"
        )
    return data_root


def validate_reporting_state(
    *,
    signal_path: Path = candidate.FUTURE_SIGNAL_LEDGER,
    execution_path: Path = candidate.FUTURE_EXECUTION_LEDGER,
    evaluation_root: Path = DEFAULT_EVALUATION_ROOT,
    provider_uri: Path | None = None,
) -> dict[str, Any]:
    """Rebuild all live Candidate49 state read-only for unified reporting."""

    load_execution_protocol()
    signal_path = signal_path.expanduser().resolve()
    execution_path = execution_path.expanduser().resolve()
    evaluation_root = evaluation_root.expanduser().resolve()
    try:
        signals = observation.validate_signal_ledger_semantics(signal_path)
    except (
        observation.Candidate49FutureObservationError,
        candidate.IntradayCumulativeVwapCrossingRateError,
    ) as exc:
        raise Candidate49FutureExecutionError(
            "candidate49 reporting signal ledger semantics changed"
        ) from exc
    generic_execution = candidate.validate_future_ledger(
        execution_path,
        candidate.FUTURE_EXECUTION_LEDGER_KIND,
    )
    execution_entries = list(generic_execution["entries"])
    state = _empty_state()
    last_session: dt.date | None = None
    if execution_entries:
        resolved_provider_uri = (
            candidate.DEFAULT_PROVIDER_URI
            if provider_uri is None
            else provider_uri
        ).expanduser().resolve()
        calendar = _read_calendar(resolved_provider_uri)
        signals = _validated_signals(signal_path, calendar)
        data_root = _reporting_data_root(execution_entries)
        replayed_ledger, state, last_session = _validate_engine_ledger(
            execution_path,
            calendar,
            data_root=data_root,
            signals=signals,
        )
        execution_entries = list(replayed_ledger["entries"])
        _validate_signal_execution_consistency(
            signals=signals,
            execution_entries=execution_entries,
            state=state,
            last_session=last_session,
            calendar=calendar,
        )
    evaluation_status = synchronize_evaluation_records(
        entries=execution_entries,
        execution_path=execution_path,
        evaluation_root=evaluation_root,
        write_missing_records=False,
    )
    return {
        "status": "candidate49_reporting_state_semantically_validated_read_only",
        "signal_entries": signals,
        "execution_entries": execution_entries,
        "ending_state": state,
        "latest_execution_session": (
            None if last_session is None else last_session.isoformat()
        ),
        "evaluation": evaluation_status,
        "provider_request_issued": False,
        "live_order_performed": False,
        "filesystem_write_performed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument(
        "--through-session",
        type=dt.date.fromisoformat,
        required=True,
    )
    parser.add_argument(
        "--provider-uri",
        type=Path,
        default=candidate.DEFAULT_PROVIDER_URI,
    )
    parser.add_argument(
        "--daily-raw-root",
        type=Path,
        default=observation.DEFAULT_DAILY_RAW_ROOT,
    )
    parser.add_argument(
        "--evaluation-root",
        type=Path,
        default=DEFAULT_EVALUATION_ROOT,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = settle_through_session(
        data_root=args.data_root,
        through_session=args.through_session,
        provider_uri=args.provider_uri,
        daily_raw_root=args.daily_raw_root,
        evaluation_root=args.evaluation_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
