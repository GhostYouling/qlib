from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import threading
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_rich_data as rich  # noqa: E402
import a_share_tushare_candidate49_future_observation as observation  # noqa: E402
import a_share_tushare_candidate49_future_execution as execution  # noqa: E402
import a_share_tushare_candidate49_future_session_workflow as workflow  # noqa: E402
import a_share_tushare_intraday_cumulative_vwap_crossing_rate as candidate  # noqa: E402


SESSION = dt.date(2026, 7, 27)
AFTER_CLOSE = dt.datetime(
    2026,
    7,
    27,
    17,
    0,
    tzinfo=candidate.CHINA_TZ,
)
NEXT_DAY = dt.datetime(
    2026,
    7,
    28,
    17,
    0,
    tzinfo=candidate.CHINA_TZ,
)


def _symbols() -> list[str]:
    return [f"SZ{value:06d}" for value in range(1, 51)]


def _source_frame(code: str, crossings: int) -> pd.DataFrame:
    source_times = rich.expected_tushare_one_minute_source_times()
    signs = np.ones(240, dtype=int)
    for position in range(1, min(crossings, 239) + 1):
        signs[position] = -signs[position - 1]
    if crossings + 1 < len(signs):
        signs[crossings + 1 :] = signs[crossings]
    closes = np.where(signs > 0, 11.0, 9.0)
    timestamps = [
        pd.Timestamp.combine(SESSION, value) for value in source_times
    ]
    # Deliberately nonsensical OHLC envelopes demonstrate that candidate49
    # preserves these fields but never uses them for eligibility or ranking.
    frame = pd.DataFrame(
        {
            "ts_code": rich.vendor_symbol(code, "tushare"),
            "trade_time": timestamps,
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": np.r_[10.0, closes],
            "vol": np.r_[0.0, np.full(240, 100.0)],
            "amount": np.r_[0.0, np.full(240, 1000.0)],
        }
    )
    return frame.iloc[::-1].reset_index(drop=True)


def _fixture(tmp_path: Path) -> dict[str, Path]:
    active_root = tmp_path / "active-root"
    provider_uri = active_root / "qlib" / "cn_a_share"
    (provider_uri / "calendars").mkdir(parents=True)
    (provider_uri / "instruments").mkdir(parents=True)
    calendar = pd.bdate_range("2026-05-25", SESSION)
    (provider_uri / "calendars" / "day.txt").write_text(
        "".join(f"{value.date().isoformat()}\n" for value in calendar),
        encoding="utf-8",
    )
    (provider_uri / "instruments" / "buyable_main_chinext.txt").write_text(
        "".join(
            f"{symbol}\t2026-05-25\t{SESSION.isoformat()}\n"
            for symbol in _symbols()
        ),
        encoding="utf-8",
    )
    (provider_uri / "price_basis.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "price_basis": candidate.research.REQUIRED_PRICE_BASIS,
                "failures": [],
                "daily_sources": ["baostock"],
            }
        ),
        encoding="utf-8",
    )
    daily_root = active_root / "raw" / "a_share" / "daily"
    daily_root.mkdir(parents=True)
    for index, symbol in enumerate(_symbols(), start=1):
        source = _source_frame(symbol[2:], index)
        ordered = source.sort_values("trade_time", kind="stable")
        pd.DataFrame(
            {
                "date": [pd.Timestamp(SESSION)],
                "raw_close": [float(ordered["close"].iloc[-1])],
                "raw_volume": [float(ordered["vol"].sum() / 100.0)],
                "amount": [float(ordered["amount"].sum())],
                "price_basis": [candidate.research.REQUIRED_PRICE_BASIS],
                "daily_source": ["baostock"],
            }
        ).to_parquet(daily_root / f"{symbol.lower()}.parquet", index=False)
    fundamentals = (
        active_root
        / "raw"
        / "a_share"
        / "fundamentals"
        / "quarterly_quality_future.parquet"
    )
    fundamentals.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "instrument": _symbols(),
            "report_date": pd.Timestamp("2026-03-31"),
            "announcement_date": pd.Timestamp("2026-06-01"),
            "roe": 10.0,
            "net_profit": 1_000_000.0,
            "revenue_yoy": 10.0,
            "profit_yoy": 10.0,
        }
    ).to_parquet(fundamentals, index=False)
    fundamentals_manifest = (
        active_root / "metadata" / "quarterly_quality_future_manifest.json"
    )
    fundamentals_manifest.parent.mkdir(parents=True)
    fundamentals_manifest.write_text(
        json.dumps(
            {
                "status": "completed",
                "report_frequency": "quarterly",
                "report_dates": [
                    "2026-03-31",
                    "2026-06-30",
                ],
                "rows_by_report_date": {
                    "2026-03-31": 50,
                    "2026-06-30": 0,
                },
                "through_report_date": "2026-06-30",
                "latest_completed_quarter_end_at_sync": "2026-06-30",
                "rows_written": 50,
                "output": str(fundamentals.resolve()),
                "sha256": rich.file_digest(fundamentals),
                "source": {
                    "provider": "Eastmoney public datacenter",
                    "retrieved_at": "2026-07-27T09:00:00+00:00",
                },
            }
        ),
        encoding="utf-8",
    )
    return {
        "active_root": active_root,
        "provider_uri": provider_uri,
        "daily_root": daily_root,
        "fundamentals": fundamentals,
        "fundamentals_manifest": fundamentals_manifest,
        "data_root": tmp_path / "external",
        "signal_path": tmp_path / "signal.json",
        "execution_path": tmp_path / "execution.json",
    }


def _run(
    paths: dict[str, Path],
    fetcher: observation.FetchFunction,
    **overrides: object,
) -> dict[str, object]:
    arguments: dict[str, object] = {
        "data_root": paths["data_root"],
        "session_date": SESSION,
        "allow_large": True,
        "provider_uri": paths["provider_uri"],
        "daily_raw_root": paths["daily_root"],
        "fundamentals_path": paths["fundamentals"],
        "fundamentals_manifest_path": paths["fundamentals_manifest"],
        "signal_path": paths["signal_path"],
        "execution_path": paths["execution_path"],
        "now": AFTER_CLOSE,
        "token_configured": True,
        "fetcher": fetcher,
        "provider_check": lambda: None,
        "workers": 4,
        "request_interval_seconds": 0.0,
    }
    arguments.update(overrides)
    return observation.collect_future_session(**arguments)  # type: ignore[arg-type]


def test_future_session_is_atomic_deterministic_and_idempotent(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    calls: list[str] = []
    lock = threading.Lock()

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        assert (start, end, frequency) == (SESSION, SESSION, "1m")
        with lock:
            calls.append(code)
        return _source_frame(code, int(code))

    result = _run(paths, fetcher)
    assert result["status"] == "future_signal_appended"
    assert result["eligible_names"] == 50
    assert len(calls) == 50
    assert [row["symbol"] for row in result["selections"]] == [
        "SZ000050",
        "SZ000049",
        "SZ000048",
    ]
    assert [row["factor_value"] for row in result["selections"]] == pytest.approx(
        [50 / 239, 49 / 239, 48 / 239]
    )
    raw_manifest = Path(str(result["raw_manifest"]))
    factor_manifest = Path(str(result["factor_manifest"]))
    assert raw_manifest.is_file()
    assert factor_manifest.is_file()
    raw = json.loads(raw_manifest.read_text(encoding="utf-8"))
    assert raw["rows"] == 50 * 241
    assert raw["exact_241_source_grid_symbols"] == 50
    assert raw["accepted_daily_source"] == "baostock"
    assert raw["frozen_context"]["active_root_binding"] == {
        "active_root": str(paths["active_root"]),
        "provider_uri": str(paths["provider_uri"]),
        "daily_raw_root": str(paths["daily_root"]),
        "daily_file_layout": "lowercase_symbol_parquet",
    }
    first_daily_identity = raw["files"][0]["quality"][
        "close_volume_amount_reconciliation"
    ]["daily_file_identity"]
    assert first_daily_identity["resolved_path"] == str(
        paths["daily_root"] / "sz000001.parquet"
    )
    assert first_daily_identity["link_count"] == 1
    assert raw["open_high_low_used_for_candidate49_eligibility"] is False
    assert raw["forward_return_fields_read"] is False
    signal = candidate.validate_future_ledger(
        paths["signal_path"],
        candidate.FUTURE_SIGNAL_LEDGER_KIND,
    )
    execution = candidate.validate_future_ledger(
        paths["execution_path"],
        candidate.FUTURE_EXECUTION_LEDGER_KIND,
    )
    assert len(signal["entries"]) == 1
    assert execution["entries"] == []

    provider_check_calls = 0

    def forbidden_provider_check() -> None:
        nonlocal provider_check_calls
        provider_check_calls += 1
        raise AssertionError("an idempotent rerun must not check or call the provider")

    def forbidden_fetcher(*_: object) -> pd.DataFrame:
        raise AssertionError("an idempotent rerun must not fetch")

    repeated = _run(
        paths,
        forbidden_fetcher,  # type: ignore[arg-type]
        token_configured=False,
        provider_check=forbidden_provider_check,
    )
    assert repeated["status"] == "future_signal_already_present_idempotent"
    assert repeated["provider_calls_this_invocation"] == 0
    assert provider_check_calls == 0
    assert len(
        candidate.validate_future_ledger(
            paths["signal_path"],
            candidate.FUTURE_SIGNAL_LEDGER_KIND,
        )["entries"]
    ) == 1

    cross_day = _run(
        paths,
        forbidden_fetcher,  # type: ignore[arg-type]
        now=NEXT_DAY,
        token_configured=False,
        provider_check=forbidden_provider_check,
    )
    assert cross_day["status"] == "future_signal_already_present_idempotent"
    assert cross_day["provider_calls_this_invocation"] == 0
    assert provider_check_calls == 0


def test_workflow_summary_is_rebuilt_from_published_candidate49_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    paths = _fixture(tmp_path)

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        return _source_frame(code, int(code))

    result = _run(paths, fetcher)
    monkeypatch.setattr(
        workflow,
        "SIGNAL_LEDGER_PATH",
        paths["signal_path"],
    )
    summary = workflow._candidate49_artifact_summary(
        workflow.WorkflowConfig(
            session=SESSION,
            staging_root=paths["active_root"],
            minute_data_root=paths["data_root"],
        )
    )

    assert summary == {
        "active_data_root": str(paths["active_root"]),
        "raw_manifest_path": str(Path(str(result["raw_manifest"]))),
        "raw_manifest_sha256": str(result["raw_manifest_sha256"]),
        "factor_manifest_path": str(Path(str(result["factor_manifest"]))),
        "factor_manifest_sha256": str(result["factor_manifest_sha256"]),
        "eligible_names": 50,
        "signal_entry_sha256": str(result["signal_entry_sha256"]),
        "raw_provider_calls": 50,
    }


def test_raw_manifest_rejects_false_provider_call_total(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        return _source_frame(code, int(code))

    result = _run(paths, fetcher)
    raw_manifest_path = Path(str(result["raw_manifest"]))
    manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    manifest["provider_calls"] = 0
    raw_manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="aggregate counters changed",
    ):
        observation._validate_raw_manifest(
            raw_manifest_path,
            session_date=SESSION,
        )


@pytest.mark.parametrize(
    "tamper",
    [
        "raw_dataset_sha256",
        "quality_context",
        "formula",
        "eligible_rows",
    ],
)
def test_factor_snapshot_rejects_provenance_or_count_tampering(
    tmp_path: Path,
    tamper: str,
) -> None:
    paths = _fixture(tmp_path)

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        return _source_frame(code, int(code))

    result = _run(paths, fetcher)
    raw_manifest_path = Path(str(result["raw_manifest"]))
    factor_manifest_path = Path(str(result["factor_manifest"]))
    manifest = json.loads(factor_manifest_path.read_text(encoding="utf-8"))
    if tamper == "raw_dataset_sha256":
        manifest["raw_snapshot"]["dataset_sha256"] = "0" * 64
    elif tamper == "quality_context":
        manifest["quality_context"] = {}
    elif tamper == "formula":
        manifest["formula"] = "tampered_formula"
    else:
        manifest["eligible_rows"] = 0
    factor_manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="candidate49 factor snapshot",
    ):
        observation._validate_factor_snapshot(
            factor_manifest_path,
            session_date=SESSION,
            raw_manifest_path=raw_manifest_path,
            raw_manifest=json.loads(
                raw_manifest_path.read_text(encoding="utf-8")
            ),
        )


def test_combined_preflight_rejects_a_rehashed_but_false_signal_ranking(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        return _source_frame(code, int(code))

    _run(paths, fetcher)
    ledger = json.loads(paths["signal_path"].read_text(encoding="utf-8"))
    ledger["entries"][0]["selections"][0]["symbol"] = "SZ999999"
    ledger["entries"][0]["entry_sha256"] = candidate._ledger_entry_digest(
        ledger["entries"][0]
    )
    ledger["chain_tip_sha256"] = ledger["entries"][0]["entry_sha256"]
    rich.atomic_write_json(ledger, paths["signal_path"])

    result = observation.preflight_future_session(
        data_root=paths["data_root"],
        session_date=SESSION,
        provider_uri=paths["provider_uri"],
        daily_raw_root=paths["daily_root"],
        fundamentals_path=paths["fundamentals"],
        fundamentals_manifest_path=paths["fundamentals_manifest"],
        signal_path=paths["signal_path"],
        execution_path=paths["execution_path"],
        now=AFTER_CLOSE,
        token_configured=True,
    )
    assert result["status"] == "not_ready_no_provider_request"
    assert result["ready"] is False
    assert result["recommended_cli_exit_code"] == 2
    assert result["failures"] == [
        "candidate49_signal_ledger_semantics_not_accepted"
    ]
    assert "payload changed" in result["signal_ledger_semantic_failure"]
    assert result["provider_request_issued"] is False
    assert result["filesystem_write_performed"] is False


def test_fresh_collection_rejects_a_daily_root_from_another_active_root(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    unrelated_daily_root = tmp_path / "unrelated-daily-root"
    shutil.copytree(paths["daily_root"], unrelated_daily_root)
    provider_checks = 0
    fetches = 0

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="daily_raw_root_not_bound_to_accepted_provider_root",
    ):
        _run(
            paths,
            fetcher,
            daily_raw_root=unrelated_daily_root,
            provider_check=provider_check,
        )
    assert provider_checks == 0
    assert fetches == 0
    assert not paths["data_root"].exists()
    assert not paths["signal_path"].exists()
    assert not paths["execution_path"].exists()


def test_fresh_collection_rejects_a_symlinked_daily_root_before_any_side_effect(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    outside = tmp_path / "outside-daily-root"
    paths["daily_root"].replace(outside)
    paths["daily_root"].symlink_to(outside, target_is_directory=True)
    provider_checks = 0
    fetches = 0

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="candidate49_daily_raw_root_symlink_forbidden",
    ):
        _run(
            paths,
            fetcher,
            provider_check=provider_check,
        )
    assert provider_checks == 0
    assert fetches == 0
    assert not paths["data_root"].exists()
    assert not paths["signal_path"].exists()
    assert not paths["execution_path"].exists()


@pytest.mark.parametrize(
    ("link_kind", "failure"),
    [
        ("symlink", "candidate49_daily_source_file_symlink_forbidden"),
        ("hardlink", "candidate49_daily_source_file_hardlink_forbidden"),
    ],
)
def test_fresh_collection_rejects_linked_daily_source_before_any_side_effect(
    tmp_path: Path,
    link_kind: str,
    failure: str,
) -> None:
    paths = _fixture(tmp_path)
    target = paths["daily_root"] / "sz000001.parquet"
    outside = tmp_path / "outside-sz000001.parquet"
    target.replace(outside)
    if link_kind == "symlink":
        target.symlink_to(outside)
    else:
        os.link(outside, target)
    provider_checks = 0
    fetches = 0

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match=failure,
    ):
        _run(
            paths,
            fetcher,
            provider_check=provider_check,
        )
    assert provider_checks == 0
    assert fetches == 0
    assert not paths["data_root"].exists()
    assert not paths["signal_path"].exists()
    assert not paths["execution_path"].exists()


def test_reconciliation_does_not_read_unregistered_daily_source_field(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _fixture(tmp_path)
    target = paths["daily_root"] / "sz000001.parquet"
    daily = pd.read_parquet(target)
    daily["daily_source"] = "eastmoney"
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
            target_reads.append(dict(kwargs))
        return result

    monkeypatch.setattr(observation.pd, "read_parquet", projected_read_parquet)
    source = observation._canonicalize_source_response(
        _source_frame("000001", 1),
        symbol="SZ000001",
        session_date=SESSION,
    )
    reconciliation = observation._daily_close_volume_amount_reconciliation(
        source,
        symbol="SZ000001",
        session_date=SESSION,
        daily_raw_root=paths["daily_root"],
    )
    assert reconciliation["status"] == "passed"
    assert reconciliation["fields_compared"] == list(
        observation.FUTURE_DAILY_RECONCILIATION_FIELDS
    )
    assert "daily_source" not in reconciliation["fields_compared"]
    assert target_reads == [
        {
            "columns": [
                "date",
                *observation.FUTURE_DAILY_RECONCILIATION_FIELDS,
            ],
            "filters": [("date", "==", pd.Timestamp(SESSION))],
        }
    ]


def test_future_quality_validation_projects_only_frozen_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _fixture(tmp_path)
    original_read_parquet = pd.read_parquet
    observed_reads: list[dict[str, object]] = []

    def projected_read_parquet(
        path: object,
        *args: object,
        **kwargs: object,
    ) -> pd.DataFrame:
        result = original_read_parquet(path, *args, **kwargs)
        if Path(path) == paths["fundamentals"]:
            observed_reads.append(dict(kwargs))
        return result

    monkeypatch.setattr(observation.pd, "read_parquet", projected_read_parquet)
    observation._validate_future_quality_source(
        fundamentals_path=paths["fundamentals"],
        fundamentals_manifest_path=paths["fundamentals_manifest"],
        session_date=SESSION,
    )
    assert observed_reads == [
        {
            "columns": list(observation.FUTURE_QUALITY_COLUMNS),
        }
    ]


def test_quality_materialization_projects_fields_and_excludes_same_or_later_announcements(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _fixture(tmp_path)
    fundamentals = pd.read_parquet(paths["fundamentals"])
    same_day = fundamentals.iloc[[0]].copy()
    same_day["announcement_date"] = pd.Timestamp(SESSION)
    same_day["roe"] = 99.0
    pd.concat([fundamentals, same_day], ignore_index=True).to_parquet(
        paths["fundamentals"],
        index=False,
    )
    original_read_parquet = pd.read_parquet
    observed_reads: list[dict[str, object]] = []

    def projected_read_parquet(
        path: object,
        *args: object,
        **kwargs: object,
    ) -> pd.DataFrame:
        result = original_read_parquet(path, *args, **kwargs)
        if Path(path) == paths["fundamentals"]:
            observed_reads.append(dict(kwargs))
        return result

    monkeypatch.setattr(observation.pd, "read_parquet", projected_read_parquet)
    active = observation._active_interval_rows(
        paths["provider_uri"]
        / "instruments"
        / "buyable_main_chinext.txt",
        SESSION,
    )
    calendar = observation._read_calendar(
        paths["provider_uri"] / "calendars" / "day.txt"
    )
    result = observation._quality_rows_for_session(
        active=active,
        calendar=calendar,
        session_date=SESSION,
        fundamentals_path=paths["fundamentals"],
    )
    assert result["roe"].eq(10.0).all()
    assert observed_reads == [
        {
            "columns": list(observation.FUTURE_QUALITY_COLUMNS),
            "filters": [
                (
                    "announcement_date",
                    "<",
                    pd.Timestamp(SESSION),
                )
            ],
        }
    ]


def test_factor_materialization_projects_only_formula_fields_and_continuous_grid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _fixture(tmp_path)
    original_read_parquet = pd.read_parquet
    observed_reads: list[dict[str, object]] = []

    def projected_read_parquet(
        path: object,
        *args: object,
        **kwargs: object,
    ) -> pd.DataFrame:
        result = original_read_parquet(path, *args, **kwargs)
        path_value = Path(path)
        if (
            path_value.name == "sz000001.parquet"
            and path_value.parent.name == "partitions"
            and "columns" in kwargs
        ):
            observed_reads.append(dict(kwargs))
        return result

    monkeypatch.setattr(observation.pd, "read_parquet", projected_read_parquet)
    result = _run(paths, lambda code, *_: _source_frame(code, int(code)))
    assert result["status"] == "future_signal_appended"
    assert observed_reads == [
        {
            "columns": list(candidate.RAW_COLUMNS),
            "filters": [
                [
                    (
                        "datetime",
                        ">=",
                        pd.Timestamp.combine(SESSION, dt.time(9, 31)),
                    ),
                    (
                        "datetime",
                        "<=",
                        pd.Timestamp.combine(SESSION, dt.time(11, 30)),
                    ),
                ],
                [
                    (
                        "datetime",
                        ">=",
                        pd.Timestamp.combine(SESSION, dt.time(13, 1)),
                    ),
                    (
                        "datetime",
                        "<=",
                        pd.Timestamp.combine(SESSION, dt.time(15, 0)),
                    ),
                ],
            ],
        }
    ]


def test_incomplete_stock_day_is_preserved_without_fill_and_blocks_signal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    paths = _fixture(tmp_path)

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        frame = _source_frame(code, int(code))
        return frame.iloc[1:].reset_index(drop=True) if code == "000001" else frame

    result = _run(paths, fetcher)
    assert (
        result["status"]
        == "future_session_frozen_without_signal_fewer_than_50_names"
    )
    assert result["eligible_names"] == 49
    assert result["selections"] == []
    raw_manifest = json.loads(
        Path(str(result["raw_manifest"])).read_text(encoding="utf-8")
    )
    record = next(
        item for item in raw_manifest["files"] if item["symbol"] == "SZ000001"
    )
    assert record["rows"] == 240
    assert record["quality"]["exact_241_source_grid"] is False
    raw_path = (
        Path(str(result["raw_manifest"])).parent
        / record["path_below_session_root"]
    )
    assert len(pd.read_parquet(raw_path)) == 240
    factor_path = Path(str(result["factor_manifest"])).parent / "factor.parquet"
    factor = pd.read_parquet(factor_path).set_index("symbol")
    assert not factor.loc[
        "SZ000001", f"{candidate.FACTOR_NAME}_eligible"
    ]
    assert "not_exact_241_source_grid" in factor.loc[
        "SZ000001", "ineligibility_reasons"
    ]
    assert (
        candidate.validate_future_ledger(
            paths["signal_path"],
            candidate.FUTURE_SIGNAL_LEDGER_KIND,
        )["entries"]
        == []
    )
    monkeypatch.setattr(
        workflow,
        "SIGNAL_LEDGER_PATH",
        paths["signal_path"],
    )
    summary = workflow._candidate49_artifact_summary(
        workflow.WorkflowConfig(
            session=SESSION,
            staging_root=paths["active_root"],
            minute_data_root=paths["data_root"],
        )
    )
    assert summary["eligible_names"] == 49
    assert summary["signal_entry_sha256"] is None
    assert summary["raw_provider_calls"] == 50


def test_interrupted_collection_resumes_only_hash_verified_partitions(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    failed = False
    first_calls: list[str] = []
    call_lock = threading.Lock()

    def flaky_fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal failed
        with call_lock:
            first_calls.append(code)
            should_fail = code == "000010" and not failed
            if should_fail:
                failed = True
        if should_fail:
            raise RuntimeError("transient fixture failure")
        return _source_frame(code, int(code))

    with pytest.raises(RuntimeError, match="transient fixture failure"):
        _run(paths, flaky_fetcher)
    raw_final, raw_partial, _, _ = observation._session_roots(
        paths["data_root"], SESSION
    )
    assert not raw_final.exists()
    checkpoint = json.loads(
        (raw_partial / ".metadata" / "checkpoint.json").read_text(encoding="utf-8")
    )
    assert checkpoint["status"] == "interrupted_resumable"
    completed_before_resume = len(
        list((raw_partial / ".metadata" / "partitions").glob("*.json"))
    )
    assert 0 < completed_before_resume < 50

    resumed_calls: list[str] = []

    def healthy_fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        with call_lock:
            resumed_calls.append(code)
        return _source_frame(code, int(code))

    result = _run(paths, healthy_fetcher)
    assert result["status"] == "future_signal_appended"
    assert len(resumed_calls) == 50 - completed_before_resume
    manifest = json.loads(
        Path(str(result["raw_manifest"])).read_text(encoding="utf-8")
    )
    assert manifest["resumed_partitions"] == completed_before_resume
    assert manifest["provider_calls_this_invocation"] == len(resumed_calls)


def test_future_boundary_fails_before_provider_check_or_request(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    provider_checks = 0
    fetches = 0

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="stopped before provider request",
    ):
        _run(
            paths,
            fetcher,
            session_date=dt.date(2026, 7, 24),
            now=dt.datetime(
                2026,
                7,
                24,
                17,
                0,
                tzinfo=candidate.CHINA_TZ,
            ),
            provider_check=provider_check,
        )
    assert provider_checks == 0
    assert fetches == 0


def test_terminal_evaluation_stops_new_signal_before_provider_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _fixture(tmp_path)
    candidate.initialize_future_ledgers(
        signal_path=paths["signal_path"],
        execution_path=paths["execution_path"],
    )
    provider_checks = 0
    fetches = 0

    def terminal_evaluation(**kwargs: object) -> dict[str, object]:
        assert kwargs["write_missing_records"] is False
        return {
            "status": "terminal_full_gate_rejection",
            "execution_stop_required": True,
            "candidate50_activation_allowed": True,
        }

    monkeypatch.setattr(
        execution,
        "synchronize_evaluation_records",
        terminal_evaluation,
    )

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="candidate49_terminal_evaluation_stops_new_signals",
    ):
        _run(
            paths,
            fetcher,
            provider_check=provider_check,
        )
    assert provider_checks == 0
    assert fetches == 0
    assert not paths["data_root"].exists()


def test_delayed_new_session_stops_before_any_write_or_provider_request(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    provider_checks = 0
    fetches = 0

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="past_session_delayed_source_to_signal_backfill_forbidden",
    ):
        _run(
            paths,
            fetcher,
            now=NEXT_DAY,
            provider_check=provider_check,
        )
    assert provider_checks == 0
    assert fetches == 0
    assert not paths["data_root"].exists()
    assert not paths["signal_path"].exists()
    assert not paths["execution_path"].exists()


def test_interrupted_partial_cannot_resume_after_the_signal_date(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    failed = False
    call_lock = threading.Lock()

    def flaky_fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal failed
        with call_lock:
            should_fail = code == "000010" and not failed
            if should_fail:
                failed = True
        if should_fail:
            raise RuntimeError("cross-date fixture interruption")
        return _source_frame(code, int(code))

    with pytest.raises(RuntimeError, match="cross-date fixture interruption"):
        _run(paths, flaky_fetcher)
    raw_final, raw_partial, _, _ = observation._session_roots(
        paths["data_root"], SESSION
    )
    assert not raw_final.exists()
    assert raw_partial.is_dir()
    before = {
        path.relative_to(paths["data_root"]): rich.file_digest(path)
        for path in paths["data_root"].rglob("*")
        if path.is_file()
    }
    provider_checks = 0
    fetches = 0

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def forbidden_fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="past_session_delayed_source_to_signal_backfill_forbidden",
    ):
        _run(
            paths,
            forbidden_fetcher,
            now=NEXT_DAY,
            provider_check=provider_check,
        )
    after = {
        path.relative_to(paths["data_root"]): rich.file_digest(path)
        for path in paths["data_root"].rglob("*")
        if path.is_file()
    }
    assert after == before
    assert provider_checks == 0
    assert fetches == 0
    assert not raw_final.exists()
    assert raw_partial.is_dir()


def test_running_collection_that_crosses_midnight_preserves_partial_without_signal(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    clock_calls = 0
    fetches = 0
    call_lock = threading.Lock()

    def advancing_clock() -> dt.datetime:
        nonlocal clock_calls
        with call_lock:
            clock_calls += 1
            return AFTER_CLOSE if clock_calls <= 20 else NEXT_DAY

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        with call_lock:
            fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="past_session_delayed_source_to_signal_backfill_forbidden",
    ):
        _run(
            paths,
            fetcher,
            clock=advancing_clock,
        )
    raw_final, raw_partial, factor_final, _ = observation._session_roots(
        paths["data_root"], SESSION
    )
    assert 0 < fetches < 50
    assert not raw_final.exists()
    assert not factor_final.exists()
    assert raw_partial.is_dir()
    checkpoint = json.loads(
        (raw_partial / ".metadata" / "checkpoint.json").read_text(
            encoding="utf-8"
        )
    )
    assert (
        checkpoint["status"]
        == "interrupted_after_signal_date_preserved_not_resumable"
    )
    assert (
        candidate.validate_future_ledger(
            paths["signal_path"],
            candidate.FUTURE_SIGNAL_LEDGER_KIND,
        )["entries"]
        == []
    )


def test_raw_only_publication_cannot_be_completed_into_a_delayed_factor(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    clock_calls = 0
    fetches = 0
    call_lock = threading.Lock()

    def advancing_clock() -> dt.datetime:
        nonlocal clock_calls
        with call_lock:
            clock_calls += 1
            return AFTER_CLOSE if clock_calls <= 152 else NEXT_DAY

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        with call_lock:
            fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="factor publication stopped after the signal date",
    ):
        _run(
            paths,
            fetcher,
            clock=advancing_clock,
        )
    raw_final, _, factor_final, _ = observation._session_roots(
        paths["data_root"], SESSION
    )
    assert fetches == 50
    assert (raw_final / "snapshot_manifest.json").is_file()
    assert not factor_final.exists()
    assert (
        candidate.validate_future_ledger(
            paths["signal_path"],
            candidate.FUTURE_SIGNAL_LEDGER_KIND,
        )["entries"]
        == []
    )
    before = {
        path.relative_to(paths["data_root"]): rich.file_digest(path)
        for path in paths["data_root"].rglob("*")
        if path.is_file()
    }
    provider_checks = 0
    delayed_fetches = 0

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def forbidden_fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal delayed_fetches
        delayed_fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="past_session_delayed_source_to_signal_backfill_forbidden",
    ):
        _run(
            paths,
            forbidden_fetcher,
            now=NEXT_DAY,
            provider_check=provider_check,
        )
    after = {
        path.relative_to(paths["data_root"]): rich.file_digest(path)
        for path in paths["data_root"].rglob("*")
        if path.is_file()
    }
    assert after == before
    assert provider_checks == 0
    assert delayed_fetches == 0
    assert not factor_final.exists()


def test_historical_quality_path_is_rejected_before_provider_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _fixture(tmp_path)
    monkeypatch.setattr(
        observation,
        "HISTORICAL_FUNDAMENTALS",
        paths["fundamentals"],
    )
    provider_checks = 0
    fetches = 0

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="must not reuse or overwrite",
    ):
        _run(
            paths,
            fetcher,
            provider_check=provider_check,
        )
    assert provider_checks == 0
    assert fetches == 0


def test_historical_quality_manifest_path_is_rejected_before_provider_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _fixture(tmp_path)
    monkeypatch.setattr(
        observation,
        "HISTORICAL_FUNDAMENTALS_MANIFEST",
        paths["fundamentals_manifest"],
    )
    provider_checks = 0
    fetches = 0

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="quarterly_quality_manifest.json",
    ):
        _run(
            paths,
            fetcher,
            provider_check=provider_check,
        )
    assert provider_checks == 0
    assert fetches == 0


def test_stale_future_quality_snapshot_is_rejected_before_provider_request(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    manifest = json.loads(
        paths["fundamentals_manifest"].read_text(encoding="utf-8")
    )
    manifest["source"]["retrieved_at"] = "2026-07-25T09:00:00+00:00"
    paths["fundamentals_manifest"].write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    provider_checks = 0
    fetches = 0

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="refreshed after 16:00",
    ):
        _run(
            paths,
            fetcher,
            provider_check=provider_check,
        )
    assert provider_checks == 0
    assert fetches == 0


def test_future_quality_must_cover_latest_completed_quarter_before_provider_request(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    manifest = json.loads(
        paths["fundamentals_manifest"].read_text(encoding="utf-8")
    )
    manifest["through_report_date"] = "2026-03-31"
    manifest["latest_completed_quarter_end_at_sync"] = "2026-03-31"
    paths["fundamentals_manifest"].write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    provider_checks = 0
    fetches = 0

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="latest completed quarter 2026-06-30",
    ):
        _run(
            paths,
            fetcher,
            provider_check=provider_check,
        )
    assert provider_checks == 0
    assert fetches == 0


def test_combined_preflight_accepts_every_local_gate_without_any_write(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    candidate.initialize_future_ledgers(
        signal_path=paths["signal_path"],
        execution_path=paths["execution_path"],
    )
    before = {
        path.relative_to(tmp_path): rich.file_digest(path)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    result = observation.preflight_future_session(
        data_root=paths["data_root"],
        session_date=SESSION,
        provider_uri=paths["provider_uri"],
        daily_raw_root=paths["daily_root"],
        fundamentals_path=paths["fundamentals"],
        fundamentals_manifest_path=paths["fundamentals_manifest"],
        signal_path=paths["signal_path"],
        execution_path=paths["execution_path"],
        now=AFTER_CLOSE,
        token_configured=True,
    )
    after = {
        path.relative_to(tmp_path): rich.file_digest(path)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert result["status"] == (
        "ready_for_explicit_future_source_to_signal_collection"
    )
    assert result["ready"] is True
    assert result["recommended_cli_exit_code"] == 0
    assert result["failures"] == []
    assert result["future_quarterly_quality_ready"] is True
    assert result["daily_file_identity_preflight"] == {
        "active_symbols_checked": 50,
        "regular_private_daily_files": 50,
        "missing_daily_files": 0,
        "symlinks_allowed": False,
        "hardlinks_allowed": False,
        "provider_request_issued": False,
    }
    assert result["provider_request_issued"] is False
    assert result["minute_rows_read"] is False
    assert result["signal_or_execution_entry_written"] is False
    assert result["filesystem_write_performed"] is False
    assert before == after
    assert not paths["data_root"].exists()


def test_combined_preflight_rejects_a_linked_daily_file_without_any_write(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    candidate.initialize_future_ledgers(
        signal_path=paths["signal_path"],
        execution_path=paths["execution_path"],
    )
    target = paths["daily_root"] / "sz000001.parquet"
    outside = tmp_path / "outside-sz000001.parquet"
    target.replace(outside)
    target.symlink_to(outside)
    before = {
        path.relative_to(tmp_path): rich.file_digest(path)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    result = observation.preflight_future_session(
        data_root=paths["data_root"],
        session_date=SESSION,
        provider_uri=paths["provider_uri"],
        daily_raw_root=paths["daily_root"],
        fundamentals_path=paths["fundamentals"],
        fundamentals_manifest_path=paths["fundamentals_manifest"],
        signal_path=paths["signal_path"],
        execution_path=paths["execution_path"],
        now=AFTER_CLOSE,
        token_configured=True,
    )
    after = {
        path.relative_to(tmp_path): rich.file_digest(path)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert result["status"] == "not_ready_no_provider_request"
    assert result["ready"] is False
    assert result["recommended_cli_exit_code"] == 2
    assert result["failures"] == [
        "candidate49_daily_source_file_symlink_forbidden:"
        f"{target}"
    ]
    assert result["daily_file_identity_preflight"] is None
    assert result["provider_request_issued"] is False
    assert result["filesystem_write_performed"] is False
    assert before == after
    assert not paths["data_root"].exists()


def test_combined_preflight_reports_stale_quality_without_provider_request(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    candidate.initialize_future_ledgers(
        signal_path=paths["signal_path"],
        execution_path=paths["execution_path"],
    )
    manifest = json.loads(
        paths["fundamentals_manifest"].read_text(encoding="utf-8")
    )
    manifest["source"]["retrieved_at"] = "2026-07-25T09:00:00+00:00"
    paths["fundamentals_manifest"].write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    result = observation.preflight_future_session(
        data_root=paths["data_root"],
        session_date=SESSION,
        provider_uri=paths["provider_uri"],
        daily_raw_root=paths["daily_root"],
        fundamentals_path=paths["fundamentals"],
        fundamentals_manifest_path=paths["fundamentals_manifest"],
        signal_path=paths["signal_path"],
        execution_path=paths["execution_path"],
        now=AFTER_CLOSE,
        token_configured=True,
    )
    assert result["status"] == "not_ready_no_provider_request"
    assert result["ready"] is False
    assert result["recommended_cli_exit_code"] == 2
    assert result["failures"] == ["future_quarterly_quality_not_accepted"]
    assert result["future_quarterly_quality_ready"] is False
    assert "refreshed after 16:00" in result["future_quarterly_quality_failure"]
    assert result["provider_request_issued"] is False
    assert result["filesystem_write_performed"] is False
    assert not paths["data_root"].exists()


def test_combined_preflight_rejects_cross_root_daily_without_any_write(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    candidate.initialize_future_ledgers(
        signal_path=paths["signal_path"],
        execution_path=paths["execution_path"],
    )
    unrelated_daily_root = tmp_path / "unrelated-daily-root"
    shutil.copytree(paths["daily_root"], unrelated_daily_root)
    before = {
        path.relative_to(tmp_path): rich.file_digest(path)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    result = observation.preflight_future_session(
        data_root=paths["data_root"],
        session_date=SESSION,
        provider_uri=paths["provider_uri"],
        daily_raw_root=unrelated_daily_root,
        fundamentals_path=paths["fundamentals"],
        fundamentals_manifest_path=paths["fundamentals_manifest"],
        signal_path=paths["signal_path"],
        execution_path=paths["execution_path"],
        now=AFTER_CLOSE,
        token_configured=True,
    )
    after = {
        path.relative_to(tmp_path): rich.file_digest(path)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert result["status"] == "not_ready_no_provider_request"
    assert result["ready"] is False
    assert result["recommended_cli_exit_code"] == 2
    assert result["failures"] == [
        "daily_raw_root_not_bound_to_accepted_provider_root"
    ]
    assert result["active_root_binding"] is None
    assert result["provider_request_issued"] is False
    assert result["filesystem_write_performed"] is False
    assert before == after
    assert not paths["data_root"].exists()


@pytest.mark.parametrize(("ready", "expected"), [(True, 0), (False, 2)])
def test_combined_preflight_cli_exit_code_matches_readiness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    ready: bool,
    expected: int,
) -> None:
    monkeypatch.setattr(
        observation,
        "parse_args",
        lambda: argparse.Namespace(
            data_root=tmp_path / "external",
            session=SESSION,
            provider_uri=tmp_path / "provider",
            daily_raw_root=tmp_path / "daily",
            fundamentals=tmp_path / "quality.parquet",
            fundamentals_manifest=tmp_path / "quality.json",
            preflight_only=True,
        ),
    )
    monkeypatch.setattr(
        observation,
        "preflight_future_session",
        lambda **_: {
            "status": (
                "ready_for_explicit_future_source_to_signal_collection"
                if ready
                else "not_ready_no_provider_request"
            ),
            "ready": ready,
            "recommended_cli_exit_code": expected,
        },
    )

    assert observation.main() == expected
    assert json.loads(capsys.readouterr().out)["ready"] is ready


def test_resume_rejects_a_changed_completed_partition_before_request(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    failed = False
    lock = threading.Lock()

    def flaky_fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal failed
        with lock:
            should_fail = code == "000010" and not failed
            if should_fail:
                failed = True
        if should_fail:
            raise RuntimeError("schema fixture failure")
        return _source_frame(code, int(code))

    with pytest.raises(RuntimeError, match="schema fixture failure"):
        _run(paths, flaky_fetcher)
    _, raw_partial, _, _ = observation._session_roots(
        paths["data_root"], SESSION
    )
    sidecars = sorted(
        (raw_partial / ".metadata" / "partitions").glob("*.json")
    )
    assert sidecars
    sidecar = json.loads(sidecars[0].read_text(encoding="utf-8"))
    data_path = raw_partial / sidecar["path_below_session_root"]
    with data_path.open("ab") as handle:
        handle.write(b"changed")
    provider_checks = 0
    fetches = 0

    def provider_check() -> None:
        nonlocal provider_checks
        provider_checks += 1

    def forbidden_fetcher(
        code: str,
        start: dt.date,
        end: dt.date,
        frequency: str,
    ) -> pd.DataFrame:
        nonlocal fetches
        fetches += 1
        return _source_frame(code, int(code))

    with pytest.raises(
        observation.Candidate49FutureObservationError,
        match="checkpoint changed",
    ):
        _run(
            paths,
            forbidden_fetcher,
            provider_check=provider_check,
        )
    assert provider_checks == 0
    assert fetches == 0
