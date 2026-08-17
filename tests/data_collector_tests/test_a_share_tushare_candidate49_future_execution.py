from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_rich_data as rich  # noqa: E402
import a_share_tushare_candidate49_future_execution as execution  # noqa: E402
import a_share_tushare_candidate49_future_observation as observation  # noqa: E402
import a_share_tushare_intraday_cumulative_vwap_crossing_rate as candidate  # noqa: E402


SIGNAL_DATE = dt.date(2026, 7, 27)
ENTRY_DATE = dt.date(2026, 7, 28)
EXIT_DATE = dt.date(2026, 7, 30)


def test_execution_raw_daily_fields_match_frozen_protocol() -> None:
    protocol = execution.load_execution_protocol()
    assert tuple(protocol["tradeability"]["required_daily_fields"]) == (
        execution.RAW_DAILY_FIELDS
    )
    assert "daily_source" not in execution.RAW_DAILY_FIELDS


def _symbols() -> list[str]:
    return [f"SZ{value:06d}" for value in range(1, 51)]


def _factor_frame(
    signal_date: dt.date = SIGNAL_DATE,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index, symbol in enumerate(_symbols(), start=1):
        rows.append(
            {
                "trade_date": pd.Timestamp(signal_date),
                "symbol": symbol,
                "provider": "tushare",
                candidate.FACTOR_NAME: index / 100.0,
                f"{candidate.FACTOR_NAME}_formula_eligible": True,
                "source_exact_241_grid": True,
                "source_close_volume_amount_reconciled": True,
                "listing_age_sessions": 100,
                "listing_seasoning_eligible": True,
                "quality_effective_date": pd.Timestamp("2026-06-02"),
                "quality_age_days": 55,
                "roe": 10.0,
                "net_profit": 1_000_000.0,
                "revenue_yoy": 10.0,
                "profit_yoy": 10.0,
                "fundamental_quality_eligible": True,
                "quality_listing_eligible": True,
                f"{candidate.FACTOR_NAME}_eligible": True,
                "ineligibility_reasons": "",
            }
        )
    return pd.DataFrame(rows).loc[:, observation.FACTOR_COLUMNS]


def _append_signal(
    root: Path,
    signal_path: Path,
    signal_date: dt.date = SIGNAL_DATE,
) -> None:
    raw_root = root / "raw" / signal_date.isoformat()
    raw_context_root = raw_root / "context"
    raw_context_root.mkdir(parents=True)
    raw_quality_path = raw_context_root / "quarterly_quality.parquet"
    pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "report_date": [pd.Timestamp("2026-03-31")],
            "announcement_date": [pd.Timestamp("2026-06-01")],
            "roe": [10.0],
            "net_profit": [1_000_000.0],
            "revenue_yoy": [10.0],
            "profit_yoy": [10.0],
        }
    ).to_parquet(raw_quality_path, index=False)
    raw_quality_manifest_path = (
        raw_context_root / "quarterly_quality_manifest.json"
    )
    rich.atomic_write_json(
        {"sha256": rich.file_digest(raw_quality_path)},
        raw_quality_manifest_path,
    )
    raw_quality_records = {
        "quarterly_quality": {
            "source_path": str(raw_quality_path.resolve()),
            "path_below_snapshot_root": "context/quarterly_quality.parquet",
            "sha256": rich.file_digest(raw_quality_path),
        },
        "quarterly_quality_manifest": {
            "source_path": str(raw_quality_manifest_path.resolve()),
            "path_below_snapshot_root": (
                "context/quarterly_quality_manifest.json"
            ),
            "sha256": rich.file_digest(raw_quality_manifest_path),
        },
    }
    raw_dataset_sha256 = rich.frame_digest(_factor_frame(signal_date))
    raw_manifest = {
        "schema_version": 1,
        "kind": observation.RAW_SNAPSHOT_KIND,
        "status": "atomically_published_immutable_future_raw_session",
        "registration_id": candidate.FUTURE_REGISTRATION_ID,
        "registration_sha256": candidate.FUTURE_REGISTRATION_SHA256,
        "future_only_policy_sha256": candidate.POLICY_SHA256,
        "session_date": signal_date.isoformat(),
        "dataset_sha256": raw_dataset_sha256,
        "provider_calls": 50,
        "frozen_context": {"files": raw_quality_records},
        "files": [],
        "forward_return_fields_read": False,
        "historical_backfill_allowed": False,
    }
    raw_manifest_path = raw_root / "snapshot_manifest.json"
    rich.atomic_write_json(raw_manifest, raw_manifest_path)

    factor_root = root / "factor" / signal_date.isoformat()
    factor_root.mkdir(parents=True)
    frame = _factor_frame(signal_date)
    factor_path = factor_root / "factor.parquet"
    rich.atomic_write_frame(frame, factor_path)
    factor_context_root = factor_root / "context"
    factor_context_root.mkdir()
    factor_quality_path = factor_context_root / "quarterly_quality.parquet"
    factor_quality_manifest_path = (
        factor_context_root / "quarterly_quality_manifest.json"
    )
    shutil.copy2(raw_quality_path, factor_quality_path)
    shutil.copy2(raw_quality_manifest_path, factor_quality_manifest_path)
    factor_quality_records = {
        "quarterly_quality": {
            "source_path": str(raw_quality_path.resolve()),
            "path_below_snapshot_root": "context/quarterly_quality.parquet",
            "sha256": rich.file_digest(factor_quality_path),
        },
        "quarterly_quality_manifest": {
            "source_path": str(raw_quality_manifest_path.resolve()),
            "path_below_snapshot_root": (
                "context/quarterly_quality_manifest.json"
            ),
            "sha256": rich.file_digest(factor_quality_manifest_path),
        },
    }
    manifest = {
        "schema_version": 1,
        "kind": observation.FACTOR_SNAPSHOT_KIND,
        "status": "eligible_for_deterministic_future_signal",
        "created_at": f"{signal_date.isoformat()}T08:45:00+00:00",
        "registration_id": candidate.FUTURE_REGISTRATION_ID,
        "registration_sha256": candidate.FUTURE_REGISTRATION_SHA256,
        "future_only_policy_sha256": candidate.POLICY_SHA256,
        "session_date": signal_date.isoformat(),
        "raw_snapshot": {
            "path": str(raw_manifest_path),
            "sha256": rich.file_digest(raw_manifest_path),
            "dataset_sha256": raw_dataset_sha256,
        },
        "factor_name": candidate.FACTOR_NAME,
        "factor_direction": "higher",
        "formula": candidate.FACTOR_FORMULA,
        "formula_or_direction_changed": False,
        "source_fields": list(candidate.RAW_COLUMNS),
        "source_open_high_low_loaded_for_factor": False,
        "source_09_30_row_loaded_for_factor": False,
        "factor_byte_sha256": rich.file_digest(factor_path),
        "factor_frame_sha256": rich.frame_digest(frame),
        "rows": 50,
        "formula_eligible_rows": 50,
        "quality_listing_eligible_rows": 50,
        "eligible_rows": 50,
        "minimum_signal_names": observation.MINIMUM_SIGNAL_NAMES,
        "quality_context": factor_quality_records,
        "quality_source_fields": list(observation.FUTURE_QUALITY_COLUMNS),
        "quality_rows_after_signal_date_loaded": False,
        "open_high_low_used_for_formula_or_eligibility": False,
        "missing_incomplete_or_suspended_stock_days_imputed": False,
        "historical_daily_price_fields_read": [],
        "future_daily_fields_read_only_for_source_reconciliation": list(
            observation.FUTURE_DAILY_RECONCILIATION_FIELDS
        ),
        "forward_return_fields_read": False,
        "execution_fields_read": [],
        "selection_performed": False,
    }
    manifest_path = factor_root / "factor_manifest.json"
    rich.atomic_write_json(manifest, manifest_path)
    payload = observation._signal_payload(
        session_date=signal_date,
        raw_manifest_path=raw_manifest_path,
        raw_manifest=raw_manifest,
        factor_manifest_path=manifest_path,
        factor_manifest=manifest,
        factor_frame=frame,
    )
    assert payload is not None
    candidate.append_future_ledger_entry(
        path=signal_path,
        kind=candidate.FUTURE_SIGNAL_LEDGER_KIND,
        payload=payload,
    )


def _fixture(
    tmp_path: Path,
    *,
    daily_source: str = "baostock",
) -> dict[str, Path]:
    active_root = tmp_path / "active-root"
    provider_uri = active_root / "qlib" / "cn_a_share"
    (provider_uri / "calendars").mkdir(parents=True)
    (provider_uri / "instruments").mkdir(parents=True)
    calendar = pd.bdate_range("2026-06-15", "2026-09-30")
    (provider_uri / "calendars" / "day.txt").write_text(
        "".join(f"{value.date().isoformat()}\n" for value in calendar),
        encoding="utf-8",
    )
    (provider_uri / "instruments" / "buyable_main_chinext.txt").write_text(
        "".join(
            f"{symbol}\t2026-06-15\t2026-09-30\n" for symbol in _symbols()
        ),
        encoding="utf-8",
    )
    (provider_uri / "price_basis.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "price_basis": candidate.research.REQUIRED_PRICE_BASIS,
                "failures": {},
                "daily_sources": [daily_source],
            }
        ),
        encoding="utf-8",
    )
    daily_root = active_root / "raw" / "a_share" / "daily"
    daily_root.mkdir(parents=True)
    for index, symbol in enumerate(_symbols(), start=1):
        base = 10.0 + index / 100.0
        rows: list[dict[str, object]] = []
        for value in calendar:
            date_value = value.date()
            raw_open = base
            raw_close = (
                base * (1.0 + index / 1000.0)
                if date_value == EXIT_DATE
                else base
            )
            rows.append(
                {
                    "date": value,
                    "raw_open": raw_open,
                    "raw_high": max(raw_open, raw_close) * 1.01,
                    "raw_low": min(raw_open, raw_close) * 0.99,
                    "raw_close": raw_close,
                    "raw_volume": 100_000.0,
                    "amount": 1_000_000_000.0,
                    "price_basis": candidate.research.REQUIRED_PRICE_BASIS,
                    "daily_source": daily_source,
                }
            )
        pd.DataFrame(rows).to_parquet(
            daily_root / f"{symbol.lower()}.parquet",
            index=False,
        )
    data_root = tmp_path / "external"
    signal_path = tmp_path / "signal.json"
    execution_path = tmp_path / "execution.json"
    candidate.initialize_future_ledgers(
        signal_path=signal_path,
        execution_path=execution_path,
    )
    _append_signal(tmp_path, signal_path)
    return {
        "active_root": active_root,
        "provider_uri": provider_uri,
        "daily_root": daily_root,
        "data_root": data_root,
        "signal_path": signal_path,
        "execution_path": execution_path,
        "evaluation_root": tmp_path / "evaluations",
    }


def _settle(
    paths: dict[str, Path],
    through_session: dt.date,
    *,
    now: dt.datetime | None = None,
    provider_uri: Path | None = None,
    daily_raw_root: Path | None = None,
) -> dict[str, object]:
    resolved_provider_uri = provider_uri or paths["provider_uri"]
    resolved_daily_raw_root = daily_raw_root or paths["daily_root"]
    if now is None:
        calendar = pd.DatetimeIndex(
            pd.to_datetime(
                (
                    resolved_provider_uri / "calendars" / "day.txt"
                ).read_text(encoding="utf-8").splitlines()
            )
        )
        position = int(calendar.searchsorted(pd.Timestamp(through_session)))
        ready_date = (
            calendar[position + 2].date()
            if position + 2 < len(calendar)
            else through_session
        )
        now = dt.datetime(
            ready_date.year,
            ready_date.month,
            ready_date.day,
            17,
            0,
            tzinfo=candidate.CHINA_TZ,
        )
    return execution.settle_through_session(
        data_root=paths["data_root"],
        through_session=through_session,
        provider_uri=resolved_provider_uri,
        daily_raw_root=resolved_daily_raw_root,
        signal_path=paths["signal_path"],
        execution_path=paths["execution_path"],
        evaluation_root=paths["evaluation_root"],
        now=now,
    )


def _milestone_entries(
    count: int,
    *,
    mean_rank_ic: float,
    cumulative_net_return: float,
    maximum_drawdown: float = -0.1,
    positive_fraction: float = 0.6,
    affordability: float = 1.0,
    participation: float = 0.001,
    unresolved: int = 0,
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    previous_sha256 = candidate._ledger_genesis(
        candidate.FUTURE_EXECUTION_LEDGER_KIND
    )
    for completed in range(1, count + 1):
        positive = min(
            completed,
            max(0, int(round(positive_fraction * completed))),
        )
        state = execution._empty_state()
        state.update(
            {
                "cumulative_net_return": cumulative_net_return,
                "maximum_drawdown": maximum_drawdown,
                "entry_opportunities": completed * 3,
                "board_lot_affordable_opportunities": int(
                    round(completed * 3 * affordability)
                ),
                "board_lot_affordability": affordability,
                "maximum_observed_amount_participation": participation,
                "completed_rank_ic_signals": completed,
                "rank_ic_sum": mean_rank_ic * completed,
                "mean_rank_ic": mean_rank_ic,
                "positive_rank_ic_signals": positive,
                "positive_rank_ic_rate": positive / completed,
                "processed_signal_entry_ids": [
                    f"signal:{value}" for value in range(1, completed + 1)
                ],
                "terminal_unresolved_lots": unresolved,
            }
        )
        session_date = (
            pd.Timestamp("2026-07-27") + pd.offsets.BDay(completed)
        ).date()
        entry = {
            "entry_id": f"execution:{completed}",
            "session_date": session_date.isoformat(),
            "settled_at": f"{session_date.isoformat()}T09:00:00+00:00",
            "ending_state": state,
            "ending_state_sha256": execution._canonical_digest(state),
            "evaluation": execution._evaluation_flags(state),
            "ordinal": completed,
            "previous_entry_sha256": previous_sha256,
        }
        entry["entry_sha256"] = candidate._ledger_entry_digest(entry)
        previous_sha256 = str(entry["entry_sha256"])
        entries.append(entry)
    return entries


def _evaluation_sync(
    tmp_path: Path,
    entries: list[dict[str, object]],
) -> dict[str, object]:
    execution_path = _write_milestone_execution_ledger(tmp_path, entries)
    return execution.synchronize_evaluation_records(
        entries=entries,  # type: ignore[arg-type]
        execution_path=execution_path,
        evaluation_root=tmp_path / "evaluations",
    )


def _write_milestone_execution_ledger(
    tmp_path: Path,
    entries: list[dict[str, object]],
) -> Path:
    previous_sha256 = candidate._ledger_genesis(
        candidate.FUTURE_EXECUTION_LEDGER_KIND
    )
    for ordinal, entry in enumerate(entries, start=1):
        entry["ordinal"] = ordinal
        entry["previous_entry_sha256"] = previous_sha256
        entry["entry_sha256"] = candidate._ledger_entry_digest(entry)
        previous_sha256 = str(entry["entry_sha256"])
    execution_path = tmp_path / "execution.json"
    if execution_path.is_file():
        ledger = json.loads(execution_path.read_text(encoding="utf-8"))
    else:
        ledger = candidate._empty_future_ledger(
            candidate.FUTURE_EXECUTION_LEDGER_KIND
        )
    ledger.update(
        {
            "status": (
                "active_append_only_future_observation"
                if entries
                else "empty_pending_first_eligible_future_session"
            ),
            "entries": entries,
            "chain_tip_sha256": (
                entries[-1]["entry_sha256"]
                if entries
                else ledger["genesis_sha256"]
            ),
        }
    )
    rich.atomic_write_json(ledger, execution_path)
    candidate.validate_future_ledger(
        execution_path,
        candidate.FUTURE_EXECUTION_LEDGER_KIND,
    )
    return execution_path


def test_exact_sixty_signal_joint_nonpositive_gate_is_terminal_and_immutable(
    tmp_path: Path,
) -> None:
    before = _evaluation_sync(
        tmp_path,
        _milestone_entries(
            59,
            mean_rank_ic=-0.01,
            cumulative_net_return=-0.02,
            positive_fraction=0.4,
        ),
    )
    assert before["status"] == "awaiting_60_completed_future_rank_ic_signals"
    assert before["remaining_completed_future_rank_ic_signals"] == 1
    assert not (tmp_path / "evaluations").exists()

    entries = _milestone_entries(
        60,
        mean_rank_ic=-0.01,
        cumulative_net_return=-0.02,
        positive_fraction=0.4,
    )
    result = _evaluation_sync(tmp_path, entries)
    assert result["status"] == "terminal_early_rejection"
    assert result["execution_stop_required"] is True
    assert result["candidate50_activation_allowed"] is True
    record_path = Path(str(result["early_record"]))
    first_sha = rich.file_digest(record_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["decision"]["metrics"]["completed_future_rank_ic_signals"] == 60
    assert record["decision"]["gates"] == {
        "mean_future_rank_ic_nonpositive": True,
        "shared_portfolio_net_cumulative_return_nonpositive": True,
        "joint_early_rejection_condition": True,
    }
    repeated = _evaluation_sync(tmp_path, entries)
    assert rich.file_digest(Path(str(repeated["early_record"]))) == first_sha

    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="continued after terminal early rejection",
    ):
        _evaluation_sync(
            tmp_path,
            _milestone_entries(
                61,
                mean_rank_ic=-0.01,
                cumulative_net_return=-0.02,
                positive_fraction=0.4,
            ),
        )


def test_sixty_signal_interim_cannot_promote_and_exact_200_can_pass(
    tmp_path: Path,
) -> None:
    interim = _evaluation_sync(
        tmp_path,
        _milestone_entries(
            60,
            mean_rank_ic=0.02,
            cumulative_net_return=0.03,
        ),
    )
    assert interim["status"] == "interim_continue_to_200_without_promotion"
    assert interim["execution_stop_required"] is False
    assert interim["candidate50_activation_allowed"] is False
    early = json.loads(
        Path(str(interim["early_record"])).read_text(encoding="utf-8")
    )["decision"]
    assert early["full_evaluation_complete"] is False
    assert early["aggregation_allowed"] is False

    full_entries = _milestone_entries(
        60,
        mean_rank_ic=0.02,
        cumulative_net_return=0.03,
    )
    full_entries.extend(
        _milestone_entries(
            200,
            mean_rank_ic=0.02,
            cumulative_net_return=0.08,
            maximum_drawdown=-0.1,
            positive_fraction=0.6,
            affordability=0.95,
            participation=0.005,
        )[60:]
    )
    full = _evaluation_sync(tmp_path, full_entries)
    assert full["status"] == "full_gate_passed_continue_paper_observation_only"
    assert full["execution_stop_required"] is False
    assert full["candidate50_activation_allowed"] is True
    decision = json.loads(
        Path(str(full["full_record"])).read_text(encoding="utf-8")
    )["decision"]
    assert decision["full_gate_passed"] is True
    assert all(decision["gates"].values())
    assert decision["aggregation_allowed"] is False
    assert (
        decision["current_scoring_selection_sizing_or_live_orders_allowed"]
        is False
    )


def test_exact_200_signal_failure_is_terminal_without_posthoc_recovery(
    tmp_path: Path,
) -> None:
    result = _evaluation_sync(
        tmp_path,
        _milestone_entries(
            200,
            mean_rank_ic=0.02,
            cumulative_net_return=0.08,
            maximum_drawdown=-0.25,
            positive_fraction=0.6,
            affordability=0.95,
            participation=0.005,
        ),
    )
    assert result["status"] == "terminal_full_gate_rejection"
    assert result["execution_stop_required"] is True
    decision = json.loads(
        Path(str(result["full_record"])).read_text(encoding="utf-8")
    )["decision"]
    assert decision["gates"]["maximum_drawdown_no_worse_than_minus_0_2"] is False
    assert sum(not value for value in decision["gates"].values()) == 1

    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="continued after terminal full-gate rejection",
    ):
        _evaluation_sync(
            tmp_path,
            _milestone_entries(
                201,
                mean_rank_ic=0.02,
                cumulative_net_return=0.08,
                maximum_drawdown=-0.25,
                positive_fraction=0.6,
                affordability=0.95,
                participation=0.005,
            ),
        )


def test_changed_evaluation_record_is_rejected(
    tmp_path: Path,
) -> None:
    entries = _milestone_entries(
        60,
        mean_rank_ic=0.02,
        cumulative_net_return=0.03,
    )
    result = _evaluation_sync(tmp_path, entries)
    path = Path(str(result["early_record"]))
    record = json.loads(path.read_text(encoding="utf-8"))
    record["decision"]["status"] = "changed"
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="evaluation record changed",
    ):
        _evaluation_sync(tmp_path, entries)


def test_evaluation_record_with_false_ledger_observation_is_rejected(
    tmp_path: Path,
) -> None:
    entries = _milestone_entries(
        60,
        mean_rank_ic=0.02,
        cumulative_net_return=0.03,
    )
    result = _evaluation_sync(tmp_path, entries)
    path = Path(str(result["early_record"]))
    record = json.loads(path.read_text(encoding="utf-8"))
    record["execution_ledger_observation"][
        "chain_tip_sha256_at_evaluation"
    ] = "f" * 64
    rich.atomic_write_json(record, path)

    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="evaluation record changed",
    ):
        _evaluation_sync(tmp_path, entries)


def test_read_only_milestone_validation_never_creates_a_missing_record(
    tmp_path: Path,
) -> None:
    entries = _milestone_entries(
        60,
        mean_rank_ic=0.02,
        cumulative_net_return=0.03,
    )
    execution_path = _write_milestone_execution_ledger(tmp_path, entries)
    evaluation_root = tmp_path / "evaluations"
    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="evaluation record is missing",
    ):
        execution.synchronize_evaluation_records(
            entries=entries,  # type: ignore[arg-type]
            execution_path=execution_path,
            evaluation_root=evaluation_root,
            write_missing_records=False,
        )
    assert not evaluation_root.exists()

    written = execution.synchronize_evaluation_records(
        entries=entries,  # type: ignore[arg-type]
        execution_path=execution_path,
        evaluation_root=evaluation_root,
    )
    read_only = execution.synchronize_evaluation_records(
        entries=entries,  # type: ignore[arg-type]
        execution_path=execution_path,
        evaluation_root=evaluation_root,
        write_missing_records=False,
    )
    assert read_only["status"] == "interim_continue_to_200_without_promotion"
    assert read_only["early_record_sha256"] == written["early_record_sha256"]


def test_shared_cash_costs_three_session_exit_and_rank_ic_are_reproducible(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    result = _settle(paths, EXIT_DATE)
    assert result["status"] == "paper_execution_sessions_appended"
    assert result["execution_entries_appended"] == 3
    state = result["ending_state"]
    assert state["positions"] == []
    assert state["entry_opportunities"] == 3
    assert state["board_lot_affordable_opportunities"] == 3
    assert state["board_lot_affordability"] == 1.0
    assert state["completed_rank_ic_signals"] == 1
    assert state["mean_rank_ic"] == pytest.approx(1.0)
    assert state["positive_rank_ic_rate"] == 1.0
    assert state["cumulative_buy_fees_cny"] > 0.0
    assert state["cumulative_sell_fees_cny"] > 0.0
    assert state["cumulative_slippage_cost_cny"] > 0.0
    assert state["maximum_observed_amount_participation"] < 0.01
    ledger = candidate.validate_future_ledger(
        paths["execution_path"],
        candidate.FUTURE_EXECUTION_LEDGER_KIND,
    )
    assert [entry["session_date"] for entry in ledger["entries"]] == [
        "2026-07-28",
        "2026-07-29",
        "2026-07-30",
    ]
    entry_events = ledger["entries"][0]["entry_events"]
    assert [event["symbol"] for event in entry_events] == [
        "SZ000050",
        "SZ000049",
        "SZ000048",
    ]
    assert all(event["filled_shares"] % 100 == 0 for event in entry_events)
    exits = ledger["entries"][-1]["exit_events"]
    assert len(exits) == 3
    assert all(event["status"] == "filled" for event in exits)
    assert (
        ledger["entries"][-1]["future_rank_ic_outcomes"][0]["rank_ic"]
        == pytest.approx(1.0)
    )
    first_snapshot = json.loads(
        Path(
            ledger["entries"][0]["daily_execution_snapshot"]["path"]
        ).read_text(encoding="utf-8")
    )
    assert first_snapshot["accepted_daily_source"] == "baostock"
    assert first_snapshot["raw_daily_fields_read"] == list(
        execution.RAW_DAILY_FIELDS
    )
    assert "daily_source" not in first_snapshot["raw_daily_fields_read"]

    repeated = _settle(paths, EXIT_DATE)
    assert repeated["status"] == "execution_already_settled_idempotent"
    assert repeated["execution_entries_appended"] == 0
    assert len(
        candidate.validate_future_ledger(
            paths["execution_path"],
            candidate.FUTURE_EXECUTION_LEDGER_KIND,
        )["entries"]
    ) == 3


def test_reporting_validation_replays_state_and_allows_a_pending_signal(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    settled = _settle(paths, EXIT_DATE)
    _append_signal(
        tmp_path,
        paths["signal_path"],
        signal_date=dt.date(2026, 9, 30),
    )
    before = {
        str(path.relative_to(tmp_path)): rich.file_digest(path)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    validated = execution.validate_reporting_state(
        signal_path=paths["signal_path"],
        execution_path=paths["execution_path"],
        evaluation_root=paths["evaluation_root"],
        provider_uri=paths["provider_uri"],
    )

    after = {
        str(path.relative_to(tmp_path)): rich.file_digest(path)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert len(validated["signal_entries"]) == 2
    assert len(validated["execution_entries"]) == 3
    assert validated["ending_state"] == settled["ending_state"]
    assert validated["latest_execution_session"] == EXIT_DATE.isoformat()
    assert (
        validated["evaluation"]["status"]
        == "awaiting_60_completed_future_rank_ic_signals"
    )
    assert validated["filesystem_write_performed"] is False


def test_tushare_daily_source_settles_t_plus_one_through_t_plus_three(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path, daily_source="tushare")
    result = _settle(paths, EXIT_DATE)
    assert result["status"] == "paper_execution_sessions_appended"
    assert result["execution_entries_appended"] == 3

    ledger = candidate.validate_future_ledger(
        paths["execution_path"],
        candidate.FUTURE_EXECUTION_LEDGER_KIND,
    )
    assert ledger["entries"][-1]["ending_state"][
        "completed_rank_ic_signals"
    ] == 1
    for entry in ledger["entries"]:
        manifest = json.loads(
            Path(entry["daily_execution_snapshot"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        assert manifest["accepted_daily_source"] == "tushare"
        assert (
            Path(manifest["daily_raw_root"]["path"])
            == paths["daily_root"]
        )
        assert manifest["raw_daily_fields_read"] == list(
            execution.RAW_DAILY_FIELDS
        )
        assert "daily_source" not in manifest["raw_daily_fields_read"]


def test_versioned_tushare_daily_root_rollover_preserves_old_context(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path, daily_source="tushare")
    _settle(paths, ENTRY_DATE)

    next_active_root = tmp_path / "active-root-next-session"
    shutil.copytree(paths["active_root"], next_active_root)
    next_provider_uri = next_active_root / "qlib" / "cn_a_share"
    next_daily_root = next_active_root / "raw" / "a_share" / "daily"
    result = _settle(
        paths,
        dt.date(2026, 7, 29),
        provider_uri=next_provider_uri,
        daily_raw_root=next_daily_root,
    )
    assert result["execution_entries_appended"] == 1

    ledger = candidate.validate_future_ledger(
        paths["execution_path"],
        candidate.FUTURE_EXECUTION_LEDGER_KIND,
    )
    manifests = [
        json.loads(
            Path(entry["daily_execution_snapshot"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        for entry in ledger["entries"]
    ]
    assert Path(manifests[0]["source_context"]["calendar"]["path"]).is_relative_to(
        paths["provider_uri"]
    )
    assert Path(manifests[1]["source_context"]["calendar"]["path"]).is_relative_to(
        next_provider_uri
    )
    assert all(
        manifest["accepted_daily_source"] == "tushare"
        for manifest in manifests
    )
    assert Path(manifests[0]["daily_raw_root"]["path"]) == paths["daily_root"]
    assert (
        Path(manifests[1]["daily_raw_root"]["path"])
        == next_daily_root
    )

    repeated = _settle(
        paths,
        dt.date(2026, 7, 29),
        provider_uri=next_provider_uri,
        daily_raw_root=next_daily_root,
    )
    assert repeated["status"] == "execution_already_settled_idempotent"
    assert repeated["execution_entries_appended"] == 0


def test_daily_raw_root_must_belong_to_the_accepted_provider_root(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path, daily_source="tushare")
    unrelated_daily_root = tmp_path / "unrelated-daily-root"
    shutil.copytree(paths["daily_root"], unrelated_daily_root)

    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="daily_raw_root_not_bound_to_accepted_provider_root",
    ):
        _settle(
            paths,
            ENTRY_DATE,
            daily_raw_root=unrelated_daily_root,
        )
    final, partial = execution._daily_snapshot_roots(
        paths["data_root"],
        ENTRY_DATE,
    )
    assert not final.exists()
    assert not partial.exists()
    assert (
        candidate.validate_future_ledger(
            paths["execution_path"],
            candidate.FUTURE_EXECUTION_LEDGER_KIND,
        )["entries"]
        == []
    )


def test_execution_does_not_read_unregistered_daily_source_field(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _fixture(tmp_path)
    target = paths["daily_root"] / "sz000001.parquet"
    daily = pd.read_parquet(target)
    daily = daily.drop(columns=["daily_source"])
    daily.to_parquet(target, index=False)
    original_read_parquet = pd.read_parquet
    target_reads: list[dict[str, object]] = []

    def projected_read_parquet(
        path: object,
        *args: object,
        **kwargs: object,
    ) -> pd.DataFrame:
        result = original_read_parquet(path, *args, **kwargs)
        if Path(path) == target:
            target_reads.append(
                {
                    **kwargs,
                    "maximum_returned_date": pd.to_datetime(
                        result["date"]
                    ).max(),
                }
            )
        return result

    monkeypatch.setattr(execution.pd, "read_parquet", projected_read_parquet)
    result = _settle(paths, ENTRY_DATE)
    assert result["execution_entries_appended"] == 1
    final, partial = execution._daily_snapshot_roots(
        paths["data_root"],
        ENTRY_DATE,
    )
    assert final.is_dir()
    assert not partial.exists()
    manifest = json.loads(
        (final / "snapshot_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["raw_daily_fields_read"] == list(
        execution.RAW_DAILY_FIELDS
    )
    assert "daily_source" not in manifest["raw_daily_fields_read"]
    assert target_reads == [
        {
            "columns": list(execution.RAW_DAILY_FIELDS),
            "filters": [("date", "<=", pd.Timestamp(ENTRY_DATE))],
            "maximum_returned_date": pd.Timestamp(ENTRY_DATE),
        }
    ]


def test_one_price_up_entry_is_cash_without_replacement(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    target = paths["daily_root"] / "sz000050.parquet"
    frame = pd.read_parquet(target)
    entry = frame["date"].eq(pd.Timestamp(ENTRY_DATE))
    prior_close = float(
        frame.loc[frame["date"].lt(pd.Timestamp(ENTRY_DATE)), "raw_close"].iloc[-1]
    )
    blocked = prior_close * 1.1
    for column in ("raw_open", "raw_high", "raw_low", "raw_close"):
        frame.loc[entry, column] = blocked
    frame.to_parquet(target, index=False)
    result = _settle(paths, ENTRY_DATE)
    state = result["ending_state"]
    assert state["entry_opportunities"] == 3
    assert state["board_lot_affordable_opportunities"] == 2
    assert len(state["positions"]) == 2
    ledger = candidate.validate_future_ledger(
        paths["execution_path"],
        candidate.FUTURE_EXECUTION_LEDGER_KIND,
    )
    blocked_event = ledger["entries"][0]["entry_events"][0]
    assert blocked_event["symbol"] == "SZ000050"
    assert blocked_event["status"] == "unfilled"
    assert blocked_event["reason"] == "one_price_up_day"
    assert blocked_event["replacement_used"] is False


def test_same_close_exit_proceeds_cannot_fund_the_earlier_open(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    calendar = execution._read_calendar(paths["provider_uri"])
    signals = execution._validated_signals(paths["signal_path"], calendar)
    state = execution._empty_state()
    state.update(
        {
            "cash_cny": 0.0,
            "equity_cny": 200_000.0,
            "positions": [
                {
                    "lot_id": "older-signal:rank:1",
                    "signal_entry_id": "older-signal",
                    "signal_session": "2026-07-23",
                    "rank": 1,
                    "symbol": "SZ000001",
                    "entry_session": "2026-07-24",
                    "scheduled_exit_session": ENTRY_DATE.isoformat(),
                    "shares": 100,
                    "raw_entry_price": 10.0,
                    "execution_entry_price": 10.01,
                    "buy_execution_notional_cny": 1_001.0,
                    "buy_fees_cny": 0.12012,
                    "buy_cash_debit_cny": 1_001.12012,
                    "exit_attempts": 0,
                    "last_mark_price": 10.0,
                    "last_mark_session": "2026-07-27",
                    "status": "open",
                }
            ],
        }
    )
    manifest_path, _, frame = execution._publish_daily_snapshot(
        data_root=paths["data_root"],
        provider_uri=paths["provider_uri"],
        daily_raw_root=paths["daily_root"],
        session_date=ENTRY_DATE,
        symbols=_symbols(),
        expected_daily_source="baostock",
    )
    payload = execution._session_payload(
        data_root=paths["data_root"],
        session_date=ENTRY_DATE,
        calendar=calendar,
        state=state,
        signals=signals,
        snapshot_manifest_path=manifest_path,
        snapshot_frame=frame,
    )
    assert all(
        event["status"] == "unfilled" for event in payload["entry_events"]
    )
    assert all(
        event["reason"] == "target_or_shared_cash_cannot_afford_one_board_lot"
        for event in payload["entry_events"]
    )
    assert payload["exit_events"][0]["status"] == "filled"
    assert payload["ending_state"]["cash_cny"] > 0.0
    assert payload["ending_state"]["positions"] == []


def test_twenty_blocked_exit_attempts_become_terminal_unresolved(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    target = paths["daily_root"] / "sz000050.parquet"
    frame = pd.read_parquet(target)
    calendar = pd.DatetimeIndex(
        pd.to_datetime(
            (
                paths["provider_uri"] / "calendars" / "day.txt"
            ).read_text(encoding="utf-8").splitlines()
        )
    )
    exit_position = int(calendar.get_loc(pd.Timestamp(EXIT_DATE)))
    twentieth_attempt = calendar[
        exit_position + execution.MAX_EXIT_ATTEMPTS - 1
    ].date()
    prior = None
    for timestamp in calendar:
        date_value = timestamp.date()
        mask = frame["date"].eq(timestamp)
        if not mask.any():
            continue
        if date_value >= EXIT_DATE:
            assert prior is not None
            blocked = prior * 0.9
            for column in ("raw_open", "raw_high", "raw_low", "raw_close"):
                frame.loc[mask, column] = blocked
            prior = blocked
        else:
            prior = float(frame.loc[mask, "raw_close"].iloc[-1])
    frame.to_parquet(target, index=False)
    result = _settle(paths, twentieth_attempt)
    state = result["ending_state"]
    assert state["terminal_unresolved_lots"] == 1
    unresolved = [
        position
        for position in state["positions"]
        if position["status"] == "terminal_unresolved"
    ]
    assert len(unresolved) == 1
    assert unresolved[0]["symbol"] == "SZ000050"
    assert unresolved[0]["exit_attempts"] == 20
    assert result["full_gate_passed"] is False


def test_before_close_stops_before_daily_snapshot_or_ledger_write(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="stopped before daily snapshot or ledger write",
    ):
        _settle(
            paths,
            ENTRY_DATE,
            now=dt.datetime(
                2026,
                7,
                28,
                15,
                0,
                tzinfo=candidate.CHINA_TZ,
            ),
        )
    final, partial = execution._daily_snapshot_roots(
        paths["data_root"],
        ENTRY_DATE,
    )
    assert not final.exists()
    assert not partial.exists()
    assert (
        candidate.validate_future_ledger(
            paths["execution_path"],
            candidate.FUTURE_EXECUTION_LEDGER_KIND,
        )["entries"]
        == []
    )


def test_execution_waits_until_two_later_accepted_sessions_exist(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    calendar_path = paths["provider_uri"] / "calendars" / "day.txt"
    calendar = [
        value
        for value in calendar_path.read_text(encoding="utf-8").splitlines()
        if value <= ENTRY_DATE.isoformat()
    ]
    calendar_path.write_text(
        "".join(f"{value}\n" for value in calendar),
        encoding="utf-8",
    )
    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="two_later_accepted_sessions_required",
    ):
        _settle(paths, ENTRY_DATE)
    assert (
        candidate.validate_future_ledger(
            paths["execution_path"],
            candidate.FUTURE_EXECUTION_LEDGER_KIND,
        )["entries"]
        == []
    )


def test_execution_waits_until_two_later_sessions_are_complete(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="two_later_accepted_sessions_not_yet_complete",
    ):
        _settle(
            paths,
            ENTRY_DATE,
            now=dt.datetime(
                ENTRY_DATE.year,
                ENTRY_DATE.month,
                ENTRY_DATE.day,
                17,
                0,
                tzinfo=candidate.CHINA_TZ,
            ),
        )
    assert (
        candidate.validate_future_ledger(
            paths["execution_path"],
            candidate.FUTURE_EXECUTION_LEDGER_KIND,
        )["entries"]
        == []
    )


def test_idempotent_rerun_rejects_a_signal_added_after_its_entry_session(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    settled_through = dt.date(2026, 7, 29)
    _settle(paths, settled_through)
    _append_signal(
        tmp_path,
        paths["signal_path"],
        signal_date=dt.date(2026, 7, 28),
    )
    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="signal appeared after its entry session was already settled",
    ):
        _settle(paths, settled_through)
    ledger = candidate.validate_future_ledger(
        paths["execution_path"],
        candidate.FUTURE_EXECUTION_LEDGER_KIND,
    )
    assert [entry["session_date"] for entry in ledger["entries"]] == [
        "2026-07-28",
        "2026-07-29",
    ]


def test_idempotent_rerun_rejects_a_rehashed_but_false_execution_price(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    _settle(paths, ENTRY_DATE)
    ledger = json.loads(paths["execution_path"].read_text(encoding="utf-8"))
    ledger["entries"][0]["entry_events"][0]["execution_price"] += 1.0
    ledger["entries"][0]["entry_sha256"] = candidate._ledger_entry_digest(
        ledger["entries"][0]
    )
    ledger["chain_tip_sha256"] = ledger["entries"][0]["entry_sha256"]
    rich.atomic_write_json(ledger, paths["execution_path"])

    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="candidate49 execution ledger payload changed",
    ):
        _settle(paths, ENTRY_DATE)


def test_changed_published_daily_snapshot_breaks_state_before_append(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    _settle(paths, ENTRY_DATE)
    final, _ = execution._daily_snapshot_roots(
        paths["data_root"],
        ENTRY_DATE,
    )
    with (final / "daily.parquet").open("ab") as handle:
        handle.write(b"changed")
    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="daily snapshot",
    ):
        _settle(paths, dt.date(2026, 7, 29))
    assert len(
        candidate.validate_future_ledger(
            paths["execution_path"],
            candidate.FUTURE_EXECUTION_LEDGER_KIND,
        )["entries"]
    ) == 1


def test_changed_bound_source_context_breaks_state_before_append(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    _settle(paths, ENTRY_DATE)
    universe_path = (
        paths["provider_uri"]
        / "instruments"
        / "buyable_main_chinext.txt"
    )
    universe_path.write_text(
        universe_path.read_text(encoding="utf-8")
        + "SZ999999\t2026-06-15\t2026-09-30\n",
        encoding="utf-8",
    )

    with pytest.raises(
        execution.Candidate49FutureExecutionError,
        match="source context",
    ):
        _settle(paths, dt.date(2026, 7, 29))
    assert len(
        candidate.validate_future_ledger(
            paths["execution_path"],
            candidate.FUTURE_EXECUTION_LEDGER_KIND,
        )["entries"]
    ) == 1
