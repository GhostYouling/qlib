"""Offline contract tests for credentialed A-share rich-data ingestion."""

import copy
import datetime as dt
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "a_share_rich_data.py"
SPEC = importlib.util.spec_from_file_location("a_share_rich_data", SCRIPT_PATH)
RICH = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = RICH
SPEC.loader.exec_module(RICH)


def complete_minute_frame(
    trade_date: str = "2026-07-13",
    *,
    bar_label: str = "end",
    symbol: str = "SH600519",
    provider: str = "tushare",
) -> pd.DataFrame:
    times = RICH.expected_minute_times(bar_label)
    datetimes = [
        pd.Timestamp.combine(pd.Timestamp(trade_date).date(), value) for value in times
    ]
    close = pd.Series(
        [10.0 + index * 0.001 for index in range(len(datetimes))], dtype=float
    )
    volume = pd.Series([100.0 + index for index in range(len(datetimes))], dtype=float)
    return pd.DataFrame(
        {
            "datetime": pd.to_datetime(datetimes),
            "symbol": symbol,
            "source_symbol": "600519.SH",
            "open": close,
            "high": close + 0.01,
            "low": close - 0.01,
            "close": close,
            "volume": volume,
            "amount": volume * close,
            "provider": provider,
        }
    )


def write_accepted_snapshot(tmp_path: Path, frame: pd.DataFrame) -> Path:
    data_path = tmp_path / "accepted_minutes.parquet"
    RICH.atomic_write_frame(frame, data_path)
    manifest = {
        "kind": "a_share_rich_data_snapshot",
        "dataset": "minutes",
        "provider": str(frame["provider"].iloc[0]),
        "frequency": "1m",
        "prices": "raw_unadjusted",
        "run_id": "accepted-test-run",
        "files": [
            {
                "path": str(data_path),
                "sha256": RICH.frame_digest(frame),
                "acceptance": {
                    "status": "automatic_checks_passed_pending_time_alignment",
                    "daily_reconciliation": {
                        "status": "passed",
                        "days": [
                            {
                                "status": "passed",
                                "inferred_volume_unit": "shares",
                            }
                        ],
                    },
                },
            }
        ],
        "acceptance_status": "automatic_checks_passed_pending_time_alignment",
    }
    manifest_path = tmp_path / "accepted_snapshot.json"
    RICH.atomic_write_json(manifest, manifest_path)
    return manifest_path


def complete_baostock_5m_frame(trade_dates: list[str]) -> pd.DataFrame:
    frames = []
    times = RICH.expected_minute_times("end", "5m")
    for trade_date in trade_dates:
        datetimes = [
            pd.Timestamp.combine(pd.Timestamp(trade_date).date(), value)
            for value in times
        ]
        close = pd.Series(
            [10.0 + index * 0.001 for index in range(len(datetimes))], dtype=float
        )
        volume = pd.Series(
            [100.0 + index for index in range(len(datetimes))], dtype=float
        )
        frames.append(
            pd.DataFrame(
                {
                    "datetime": datetimes,
                    "symbol": "SH600519",
                    "source_symbol": "sh.600519",
                    "open": close,
                    "high": close + 0.01,
                    "low": close - 0.01,
                    "close": close,
                    "volume": volume,
                    "amount": volume * close,
                    "provider": "baostock",
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def permissive_baostock_source_chain() -> dict:
    chain = copy.deepcopy(RICH.load_baostock_5m_source_chain())
    bulk = chain["contract"]["bulk_snapshot_contract"]
    bulk["median_eligible_universe_coverage_min"] = 1.0
    bulk["p05_eligible_universe_coverage_min"] = 1.0
    bulk["minimum_names_per_factor_cross_section"] = 1
    bulk["minimum_potential_non_overlapping_three_session_cohorts"] = 1
    return chain


def test_vendor_symbol_mapping_and_symbol_validation():
    assert RICH.vendor_symbol("600519", "baostock") == "sh.600519"
    assert RICH.vendor_symbol("000001", "baostock") == "sz.000001"
    assert RICH.vendor_symbol("600519", "tushare") == "600519.SH"
    assert RICH.vendor_symbol("000001", "jqdata") == "000001.XSHE"
    assert RICH.vendor_symbol("688981", "rqdata") == "688981.XSHG"
    assert RICH.parse_symbols("600519,000001,600519") == ["600519", "000001"]
    with pytest.raises(Exception, match="unsupported A-share code"):
        RICH.parse_symbols("430047")


def test_provider_status_never_returns_credential_values(monkeypatch):
    monkeypatch.setenv("TUSHARE_TOKEN", "this-is-a-secret")
    availability = RICH.provider_availability("tushare")
    rendered = str(availability)
    assert "this-is-a-secret" not in rendered
    assert availability.missing_environment == ()
    assert RICH.provider_availability("baostock").missing_environment == ()


def test_status_reports_external_baostock_storage_without_mutation(tmp_path):
    data_root = tmp_path / "rich-root"
    raw_path = (
        data_root
        / "raw/a_share/rich/baostock/minutes/5m/snapshots/example/600519/2025.parquet"
    )
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(b"test-only-placeholder")
    lock_path = data_root / ".a_share_baostock_5m.lock"
    lock_path.write_text("999999", encoding="utf-8")
    probe_path = (
        data_root
        / "metadata/rich_data/availability/20260715T000353Z_baostock_5m_probe.json"
    )
    RICH.atomic_write_json(
        {
            "kind": "a_share_baostock_5m_restoration_probe",
            "status": "provider_rejected_stop_before_bulk_retry",
            "created_at": "2026-07-15T00:03:53+00:00",
            "history_query_succeeded": False,
            "rows": 0,
        },
        probe_path,
    )
    preflight_path = (
        data_root
        / "metadata/rich_data/preflights/20260714T222229Z_baostock_5m_preflight.json"
    )
    RICH.atomic_write_json(
        {
            "kind": "a_share_baostock_5m_preflight",
            "status": "passed_before_network",
            "observed_free_gib": 100.0,
            "network_request_issued": False,
        },
        preflight_path,
    )
    before_lock = lock_path.read_bytes()

    payload = RICH.status_payload(data_root)
    storage = payload["baostock_five_minute_storage"]
    assert storage["data_root"] == str(data_root.resolve())
    assert storage["network_request_issued"] is False
    assert storage["raw_parquet_file_count"] == 1
    assert storage["history_manifest_count"] == 0
    assert storage["latest_restoration_probe"] == {
        "path": str(probe_path.resolve()),
        "record_valid": True,
        "status": "provider_rejected_stop_before_bulk_retry",
        "created_at": "2026-07-15T00:03:53+00:00",
        "history_query_succeeded": False,
        "rows": 0,
    }
    assert storage["latest_preflight"] == {
        "path": str(preflight_path.resolve()),
        "record_valid": True,
        "status": "passed_before_network",
        "observed_free_gib": 100.0,
        "network_request_issued": False,
    }
    assert storage["process_lock"] == {
        "path": str(lock_path.resolve()),
        "exists": True,
        "recorded_owner_pid": "999999",
        "advisory_lock_currently_held": False,
    }
    assert lock_path.read_bytes() == before_lock


def test_advisory_lock_status_distinguishes_active_and_inactive_marker(tmp_path):
    lock_path = tmp_path / "baostock.lock"
    with RICH.RichDataProcessLock(lock_path):
        active = RICH.advisory_lock_status(lock_path)
        assert active["exists"] is True
        assert active["recorded_owner_pid"] == str(RICH.os.getpid())
        assert active["advisory_lock_currently_held"] is True

    inactive = RICH.advisory_lock_status(lock_path)
    assert inactive["exists"] is True
    assert inactive["recorded_owner_pid"] == str(RICH.os.getpid())
    assert inactive["advisory_lock_currently_held"] is False


def test_baostock_5m_contract_is_fingerprint_frozen(tmp_path):
    contract = RICH.load_baostock_5m_contract()
    assert contract["source"]["requested_fields"] == [
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
    assert contract["formal_acceptance"]["trade_date"] == "2026-07-10"
    assert (
        contract["timestamp_contract"]["expected_bars_per_complete_regular_session"]
        == 48
    )
    assert contract["forward_return_fields_read"] is False

    changed = RICH.json.loads(RICH.DEFAULT_BAOSTOCK_5M_CONTRACT.read_text())
    changed["source"]["adjustflag"] = "2"
    changed_path = tmp_path / "changed_baostock_contract.json"
    RICH.atomic_write_json(changed, changed_path)
    with pytest.raises(RICH.RichDataError, match="fingerprint mismatch"):
        RICH.load_baostock_5m_contract(changed_path)


def test_baostock_5m_request_uses_only_raw_frozen_fields(monkeypatch):
    captured = {}

    class Response:
        error_code = "0"
        error_msg = "success"
        fields = [
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

        def __init__(self):
            self.rows = iter(
                [
                    [
                        "2026-07-10",
                        "20260710093500000",
                        "sh.600519",
                        "10",
                        "10",
                        "10",
                        "10",
                        "100",
                        "1000",
                        "3",
                    ]
                ]
            )
            self.current = None

        def next(self):
            self.current = next(self.rows, None)
            return self.current is not None

        def get_row_data(self):
            return self.current

    def query(symbol, fields, **kwargs):
        captured.update({"symbol": symbol, "fields": fields, **kwargs})
        return Response()

    fake = SimpleNamespace(
        login=lambda: SimpleNamespace(error_code="0", error_msg="success"),
        logout=lambda: SimpleNamespace(error_code="0", error_msg="success"),
        query_history_k_data_plus=query,
    )
    monkeypatch.setitem(sys.modules, "baostock", fake)
    frame = RICH.fetch_baostock_minutes(
        "600519", dt.date(2026, 7, 10), dt.date(2026, 7, 10), "5m"
    )
    assert captured == {
        "symbol": "sh.600519",
        "fields": "date,time,code,open,high,low,close,volume,amount,adjustflag",
        "start_date": "2026-07-10",
        "end_date": "2026-07-10",
        "frequency": "5",
        "adjustflag": "3",
    }
    assert frame["datetime"].dt.strftime("%H:%M:%S").tolist() == ["09:35:00"]
    with pytest.raises(RICH.RichDataError, match="only 5m"):
        RICH.fetch_baostock_minutes(
            "600519", dt.date(2026, 7, 10), dt.date(2026, 7, 10), "1m"
        )


def test_baostock_5m_canonicalization_rejects_duplicate_timestamps():
    frame = complete_baostock_5m_frame(["2026-07-10"])
    duplicated = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(RICH.RichDataError, match="forbids silent deduplication"):
        RICH.canonicalize_baostock_5m_bars(
            duplicated,
            "600519",
            dt.date(2026, 7, 10),
            dt.date(2026, 7, 10),
        )


def test_baostock_5m_zero_price_suspension_placeholders_are_counted_and_ineligible():
    suspended = complete_baostock_5m_frame(["2024-07-19"])
    suspended[["open", "high", "low", "close", "volume", "amount"]] = 0.0
    normalized = RICH.canonicalize_baostock_5m_bars(
        suspended,
        "600519",
        dt.date(2024, 7, 19),
        dt.date(2024, 7, 19),
    )
    assert normalized.empty
    assert normalized.attrs["source_rows"] == 48
    assert normalized.attrs["zero_price_placeholder_rows_excluded"] == 48
    assert normalized.attrs["zero_price_placeholder_session_dates"] == ["2024-07-19"]

    non_placeholder_zero = suspended.copy()
    non_placeholder_zero.loc[0, "volume"] = 1.0
    with pytest.raises(RICH.RichDataError, match="invalid minute bars"):
        RICH.canonicalize_baostock_5m_bars(
            non_placeholder_zero,
            "600519",
            dt.date(2024, 7, 19),
            dt.date(2024, 7, 19),
        )

    zero_activity = complete_baostock_5m_frame(["2024-07-19"])
    zero_activity[["volume", "amount"]] = 0.0
    assert (
        RICH.validate_baostock_5m_partition(
            zero_activity,
            ("600519", "2024-07-19", "2024-07-19", 2024),
            pd.DatetimeIndex(["2024-07-19"]),
        )
        == []
    )


def test_baostock_5m_source_chain_and_pit_year_partitioning_are_frozen():
    chain = RICH.load_baostock_5m_source_chain()
    suspension = RICH.load_baostock_5m_suspension_audit()
    assert chain["acceptance"]["run_id"] == "20260714T210140Z_baostock_5m_be9dfe63"
    assert chain["alignment"]["bar_timestamp_label"] == "end"
    assert (
        suspension["post_change_partition_verification"]["canonical_rows_written"]
        == 11138
    )
    assert suspension["forward_return_fields_read"] is False
    intervals = pd.DataFrame(
        {
            "instrument": ["SH600519"],
            "start_date": pd.to_datetime(["2019-12-15"]),
            "end_date": pd.to_datetime(["2021-02-03"]),
        }
    )
    assert RICH.baostock_5m_partition_tasks(
        intervals, dt.date(2020, 1, 1), dt.date(2021, 12, 31)
    ) == [
        ("600519", "2020-01-01", "2020-12-31", 2020),
        ("600519", "2021-01-01", "2021-02-03", 2021),
    ]
    assert RICH.baostock_5m_request_tasks(
        intervals, dt.date(2020, 1, 1), dt.date(2021, 12, 31)
    ) == [("600519", "2020-01-01", "2021-02-03")]
    throttle = RICH.load_baostock_5m_throttle_audit()
    assert throttle["frozen_reduced_request_plan"]["provider_requests"] == 5386


def test_baostock_5m_full_interval_response_splits_into_yearly_storage():
    frame = complete_baostock_5m_frame(["2020-12-31", "2021-01-04"])
    frame.attrs["source_rows_by_year"] = {2020: 48, 2021: 48}
    tasks = [
        ("600519", "2020-12-31", "2020-12-31", 2020),
        ("600519", "2021-01-01", "2021-01-04", 2021),
    ]
    partitions = list(RICH.split_baostock_5m_request_frame(frame, tasks))
    assert [len(partition) for _, partition in partitions] == [48, 48]
    assert [partition.attrs["source_rows"] for _, partition in partitions] == [48, 48]


def test_baostock_blacklist_error_is_not_retried(monkeypatch):
    calls = 0

    class BlacklistedClient:
        def query_history_k_data_plus(self, *args, **kwargs):
            nonlocal calls
            calls += 1
            return SimpleNamespace(
                error_code="1", error_msg="黑名单用户，请与管理员联系"
            )

    monkeypatch.setattr(RICH, "_BAOSTOCK_WORKER_CLIENT", BlacklistedClient())
    with pytest.raises(RICH.RichDataError, match="after 1 attempt"):
        RICH.fetch_baostock_5m_request_worker(("600519", "2020-01-01", "2025-12-31"))
    assert calls == 1


def test_baostock_restoration_probe_must_pass_and_remain_recent(tmp_path, monkeypatch):
    frame = complete_baostock_5m_frame(["2026-07-10"])
    monkeypatch.setattr(RICH, "require_baostock_5m_runtime", lambda: None)
    monkeypatch.setattr(
        RICH,
        "fetch_baostock_minutes",
        lambda code, start, end, frequency: frame,
    )
    monkeypatch.setattr(
        RICH,
        "minute_daily_reconciliation",
        lambda source: {"status": "passed", "days": [{"status": "passed"}]},
    )
    path = RICH.probe_baostock_5m_restoration(data_root=tmp_path)
    record = RICH.json.loads(path.read_text())
    assert record["status"] == "passed_for_bulk_retry"
    assert record["rows"] == 48
    assert record["forward_return_fields_read"] is False
    created = pd.Timestamp(record["created_at"]).to_pydatetime()
    loaded_path, _ = RICH.load_baostock_5m_restoration_probe(
        tmp_path, now=created + dt.timedelta(minutes=10)
    )
    assert loaded_path == path.resolve()
    with pytest.raises(RICH.RichDataError, match="older than"):
        RICH.load_baostock_5m_restoration_probe(
            tmp_path, now=created + dt.timedelta(minutes=31)
        )


def test_jqdata_moneyflow_contract_is_fingerprint_frozen(tmp_path):
    contract = RICH.load_jqdata_moneyflow_contract()
    assert contract["factor"]["name"] == "jqdata_large_order_net_inflow_share"
    assert contract["source"]["requested_fields"] == list(
        RICH.JQDATA_MONEYFLOW_RAW_FIELDS
    )
    assert contract["source_selection"]["separate_product_entitlement_required"] is True
    assert contract["forward_return_fields_read"] is False

    changed = RICH.json.loads(RICH.DEFAULT_JQDATA_MONEYFLOW_CONTRACT.read_text())
    changed["factor"]["direction"] = "lower_is_better"
    changed_path = tmp_path / "changed_jqdata_moneyflow_contract.json"
    RICH.atomic_write_json(changed, changed_path)
    with pytest.raises(RICH.RichDataError, match="fingerprint mismatch"):
        RICH.load_jqdata_moneyflow_contract(changed_path)


def test_jqdata_moneyflow_request_uses_only_frozen_fields(monkeypatch):
    captured = {}

    def auth(username, password):
        captured["auth"] = (username, password)
        return True

    def get_money_flow_pro(security_list, **kwargs):
        captured["security_list"] = security_list
        captured.update(kwargs)
        return pd.DataFrame()

    monkeypatch.setenv("JQDATA_USERNAME", "user")
    monkeypatch.setenv("JQDATA_PASSWORD", "secret")
    monkeypatch.setitem(
        sys.modules,
        "jqdatasdk",
        SimpleNamespace(auth=auth, get_money_flow_pro=get_money_flow_pro),
    )
    RICH.fetch_jqdata_moneyflow_pro(
        ["600519", "000001"], dt.date(2024, 4, 30), dt.date(2024, 4, 30)
    )
    assert captured["security_list"] == ["600519.XSHG", "000001.XSHE"]
    assert captured["frequency"] == "daily"
    assert captured["data_type"] == "money"
    assert captured["fields"] == list(RICH.JQDATA_MONEYFLOW_RAW_FIELDS)
    forbidden = set(
        RICH.load_jqdata_moneyflow_contract()["source"]["explicitly_forbidden_fields"]
    )
    assert set(captured["fields"]).isdisjoint(forbidden)


def test_jqdata_moneyflow_normalization_derives_ratio_and_excludes_missing_zero():
    raw = pd.DataFrame(
        [
            {
                "time": "2024-04-30",
                "code": "000001.XSHE",
                "inflow_xl": 60,
                "inflow_l": 40,
                "inflow_m": 10,
                "inflow_s": 10,
                "outflow_xl": 10,
                "outflow_l": 10,
                "outflow_m": 30,
                "outflow_s": 30,
            },
            {
                "time": "2024-04-30",
                "code": "600519.XSHG",
                **{field: 0 for field in RICH.JQDATA_MONEYFLOW_RAW_FIELDS},
            },
            {
                "time": "2024-04-30",
                "code": "300750.XSHE",
                **{
                    field: (None if field == "inflow_xl" else 1)
                    for field in RICH.JQDATA_MONEYFLOW_RAW_FIELDS
                },
            },
        ]
    )
    normalized, quality = RICH.canonicalize_jqdata_moneyflow(
        raw,
        ["000001", "600519", "300750"],
        dt.date(2024, 4, 30),
        dt.date(2024, 4, 30),
    )
    assert normalized.columns.tolist() == list(RICH.JQDATA_MONEYFLOW_COLUMNS)
    assert normalized["instrument"].tolist() == ["SZ000001"]
    assert normalized["jqdata_large_order_net_inflow_share"].item() == pytest.approx(
        0.4
    )
    assert quality == {
        "input_rows": 3,
        "missing_rows_excluded": 1,
        "zero_denominator_rows_excluded": 1,
        "rows_written": 1,
    }
    assert normalized["provider"].tolist() == ["jqdata"]
    assert not ({"change_pct", "close", "netflow_xl"} & set(normalized.columns))


def test_jqdata_moneyflow_normalization_rejects_negative_raw_amount():
    row = {
        "time": "2024-04-30",
        "code": "000001.XSHE",
        **{field: 1 for field in RICH.JQDATA_MONEYFLOW_RAW_FIELDS},
    }
    row["outflow_l"] = -1
    with pytest.raises(RICH.RichDataError, match="negative raw flow"):
        RICH.canonicalize_jqdata_moneyflow(
            pd.DataFrame([row]),
            ["000001"],
            dt.date(2024, 4, 30),
            dt.date(2024, 4, 30),
        )


def test_jqdata_moneyflow_sync_writes_immutable_no_price_snapshot(
    tmp_path, monkeypatch
):
    contract = RICH.json.loads(RICH.DEFAULT_JQDATA_MONEYFLOW_CONTRACT.read_text())
    contract["snapshot_contract"]["development_start"] = "2024-04-29"
    contract["snapshot_contract"]["development_end"] = "2024-04-30"
    universe = tmp_path / "universe.txt"
    universe.write_text(
        "SH600519\t2020-01-01\t2025-12-31\nSZ000001\t2020-01-01\t2025-12-31\n",
        encoding="utf-8",
    )
    calendar = tmp_path / "day.txt"
    calendar.write_text("2024-04-29\n2024-04-30\n", encoding="utf-8")
    monkeypatch.setattr(RICH, "load_jqdata_moneyflow_contract", lambda: contract)
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "validate_range", lambda *args, **kwargs: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    acceptance_path = tmp_path / "accepted.json"
    RICH.atomic_write_json({"run_id": "accepted"}, acceptance_path)
    monkeypatch.setattr(
        RICH,
        "load_jqdata_moneyflow_acceptance",
        lambda: (
            acceptance_path,
            {
                "run_id": "accepted",
                "acceptance_status": "accepted_entitlement_and_formula_pending_full_history",
            },
        ),
    )

    def fake_fetch(codes, start, end):
        rows = []
        for date in pd.date_range(start, end, freq="D"):
            for position, code in enumerate(codes, start=1):
                rows.append(
                    {
                        "time": date,
                        "code": RICH.vendor_symbol(code, "jqdata"),
                        "inflow_xl": 60 + position,
                        "inflow_l": 40,
                        "inflow_m": 10,
                        "inflow_s": 10,
                        "outflow_xl": 10,
                        "outflow_l": 10,
                        "outflow_m": 30,
                        "outflow_s": 30,
                    }
                )
        return pd.DataFrame(rows)

    monkeypatch.setattr(RICH, "fetch_jqdata_moneyflow_pro", fake_fetch)
    manifest_path = RICH.sync_jqdata_moneyflow(
        allow_large=True,
        universe_path=universe,
        calendar_path=calendar,
    )
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["dataset"] == "jqdata_moneyflow_pro_daily"
    assert manifest["source_request"]["fields"] == list(
        RICH.JQDATA_MONEYFLOW_RAW_FIELDS
    )
    assert manifest["source_request"]["credentials_logged_or_stored"] is False
    assert manifest["source_acceptance"]["run_id"] == "accepted"
    assert manifest["point_in_time_universe"] == {
        "path": str(universe),
        "sha256": RICH.file_digest(universe),
        "intervals": 2,
    }
    assert manifest["local_calendar"] == {
        "path": str(calendar),
        "sha256": RICH.file_digest(calendar),
        "sessions_in_requested_range": 2,
    }
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    assert (
        manifest["acceptance_status"]
        == "full_source_coverage_failed_stop_before_prices"
    )
    stored = pd.read_parquet(RICH.resolve_record_path(manifest["files"][0]["path"]))
    assert stored.columns.tolist() == list(RICH.JQDATA_MONEYFLOW_COLUMNS)
    assert len(stored) == 4
    assert not list((tmp_path / "raw").rglob("*.partial"))


def test_jqdata_moneyflow_full_sync_requires_fingerprinted_acceptance(tmp_path):
    with pytest.raises(
        RICH.RichDataError, match="run acceptance-jqdata-moneyflow first"
    ):
        RICH.load_jqdata_moneyflow_acceptance(tmp_path)

    amounts = {f"{field}_amount": 1.0 for field in RICH.JQDATA_MONEYFLOW_RAW_FIELDS}
    frame = pd.DataFrame(
        [
            {
                "trade_date": pd.Timestamp("2026-07-13"),
                "instrument": RICH.qlib_symbol(code),
                **amounts,
                "jqdata_large_order_net_inflow_share": 0.0,
                "provider": "jqdata",
            }
            for code in RICH.DEFAULT_ACCEPTANCE_SYMBOLS
        ],
        columns=RICH.JQDATA_MONEYFLOW_COLUMNS,
    )
    data_path = tmp_path / "acceptance.parquet"
    RICH.atomic_write_frame(frame, data_path)
    manifest = {
        "kind": "a_share_rich_data_snapshot",
        "dataset": "jqdata_moneyflow_pro_daily",
        "provider": "jqdata",
        "run_id": "accepted",
        "acceptance_status": "accepted_entitlement_and_formula_pending_full_history",
        "data_contract": {"sha256": RICH.JQDATA_MONEYFLOW_CONTRACT_SHA256},
        "source_request": {
            "fields": list(RICH.JQDATA_MONEYFLOW_RAW_FIELDS),
            "forbidden_fields_requested_or_stored": [],
            "credentials_logged_or_stored": False,
        },
        "files": [{"path": str(data_path), "sha256": RICH.frame_digest(frame)}],
        "price_fields_loaded": [],
        "forward_return_fields_read": False,
        "selection_or_promotion_allowed": False,
    }
    manifest_path = tmp_path / "accepted_manifest.json"
    RICH.atomic_write_json(manifest, manifest_path)
    path, loaded = RICH.load_jqdata_moneyflow_acceptance(tmp_path)
    assert path == manifest_path.resolve()
    assert loaded["run_id"] == "accepted"


def test_tushare_moneyflow_contract_is_fingerprint_frozen(tmp_path):
    contract = RICH.load_tushare_moneyflow_contract()
    assert contract["factor"]["name"] == "tushare_large_order_net_inflow_share"
    assert contract["source"]["requested_fields"] == list(
        RICH.TUSHARE_MONEYFLOW_RAW_FIELDS
    )
    assert (
        contract["mechanism_identity"][
            "jqdata_and_tushare_may_be_combined_as_independent_factors"
        ]
        is False
    )
    assert contract["forward_return_fields_read"] is False

    changed = RICH.json.loads(RICH.DEFAULT_TUSHARE_MONEYFLOW_CONTRACT.read_text())
    changed["factor"]["direction"] = "lower_is_better"
    changed_path = tmp_path / "changed_tushare_moneyflow_contract.json"
    RICH.atomic_write_json(changed, changed_path)
    with pytest.raises(RICH.RichDataError, match="fingerprint mismatch"):
        RICH.load_tushare_moneyflow_contract(changed_path)


def test_tushare_moneyflow_request_uses_only_frozen_fields(monkeypatch):
    captured = {}

    class Pro:
        def moneyflow(self, **kwargs):
            captured.update(kwargs)
            return pd.DataFrame()

    monkeypatch.setattr(
        RICH,
        "_import_tushare",
        lambda: SimpleNamespace(pro_api=lambda: Pro()),
    )
    RICH.fetch_tushare_moneyflow(dt.date(2024, 4, 30))
    assert captured["trade_date"] == "20240430"
    assert captured["fields"].split(",") == list(RICH.TUSHARE_MONEYFLOW_RAW_FIELDS)
    forbidden = set(
        RICH.load_tushare_moneyflow_contract()["source"]["explicitly_forbidden_fields"]
    )
    assert set(captured["fields"].split(",")).isdisjoint(forbidden)


def test_tushare_moneyflow_normalization_derives_ratio_and_excludes_missing_zero():
    rows = [
        {
            "ts_code": "000001.SZ",
            "trade_date": "20240430",
            "buy_sm_amount": 10,
            "sell_sm_amount": 30,
            "buy_md_amount": 10,
            "sell_md_amount": 30,
            "buy_lg_amount": 40,
            "sell_lg_amount": 10,
            "buy_elg_amount": 60,
            "sell_elg_amount": 10,
        },
        {
            "ts_code": "600519.SH",
            "trade_date": "20240430",
            **{field: 0 for field in RICH.TUSHARE_MONEYFLOW_AMOUNT_FIELDS},
        },
        {
            "ts_code": "300750.SZ",
            "trade_date": "20240430",
            **{
                field: (None if field == "buy_elg_amount" else 1)
                for field in RICH.TUSHARE_MONEYFLOW_AMOUNT_FIELDS
            },
        },
    ]
    normalized, quality = RICH.canonicalize_tushare_moneyflow(
        pd.DataFrame(rows), dt.date(2024, 4, 30), dt.date(2024, 4, 30)
    )
    assert normalized.columns.tolist() == list(RICH.TUSHARE_MONEYFLOW_COLUMNS)
    assert normalized["instrument"].tolist() == ["SZ000001"]
    assert normalized["tushare_large_order_net_inflow_share"].item() == pytest.approx(
        0.4
    )
    assert quality == {
        "input_rows": 3,
        "missing_rows_excluded": 1,
        "zero_denominator_rows_excluded": 1,
        "rows_written": 1,
    }
    assert normalized["provider"].tolist() == ["tushare"]
    assert not ({"net_mf_amount", "close", "buy_lg_vol"} & set(normalized.columns))


def test_tushare_moneyflow_normalization_rejects_negative_raw_amount():
    row = {
        "ts_code": "000001.SZ",
        "trade_date": "20240430",
        **{field: 1 for field in RICH.TUSHARE_MONEYFLOW_AMOUNT_FIELDS},
    }
    row["sell_lg_amount"] = -1
    with pytest.raises(RICH.RichDataError, match="negative raw flow"):
        RICH.canonicalize_tushare_moneyflow(
            pd.DataFrame([row]), dt.date(2024, 4, 30), dt.date(2024, 4, 30)
        )


def test_tushare_moneyflow_sync_writes_immutable_no_price_snapshot(
    tmp_path, monkeypatch
):
    contract = RICH.json.loads(RICH.DEFAULT_TUSHARE_MONEYFLOW_CONTRACT.read_text())
    contract["snapshot_contract"]["development_start"] = "2024-04-29"
    contract["snapshot_contract"]["development_end"] = "2024-04-30"
    contract["snapshot_contract"]["partition_policy"][
        "minimum_seconds_between_calls"
    ] = 0
    universe = tmp_path / "universe.txt"
    universe.write_text(
        "SH600519\t2020-01-01\t2025-12-31\n" "SZ000001\t2020-01-01\t2025-12-31\n",
        encoding="utf-8",
    )
    calendar = tmp_path / "day.txt"
    calendar.write_text("2024-04-29\n2024-04-30\n", encoding="utf-8")
    monkeypatch.setattr(RICH, "load_tushare_moneyflow_contract", lambda: contract)
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "validate_range", lambda *args, **kwargs: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(RICH, "METADATA_ROOT", tmp_path / "metadata")
    acceptance_path = tmp_path / "accepted.json"
    RICH.atomic_write_json({"run_id": "accepted"}, acceptance_path)
    monkeypatch.setattr(
        RICH,
        "load_tushare_moneyflow_acceptance",
        lambda: (acceptance_path, {"run_id": "accepted"}),
    )

    def fake_fetch(trade_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": code,
                    "trade_date": trade_date.strftime("%Y%m%d"),
                    **{
                        field: float(position + index + 1)
                        for index, field in enumerate(
                            RICH.TUSHARE_MONEYFLOW_AMOUNT_FIELDS
                        )
                    },
                }
                for position, code in enumerate(("600519.SH", "000001.SZ"))
            ]
        )

    monkeypatch.setattr(RICH, "fetch_tushare_moneyflow", fake_fetch)
    manifest_path = RICH.sync_tushare_moneyflow(
        allow_large=True,
        universe_path=universe,
        calendar_path=calendar,
    )
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["dataset"] == "tushare_moneyflow_daily"
    assert manifest["source_request"]["fields"] == list(
        RICH.TUSHARE_MONEYFLOW_RAW_FIELDS
    )
    assert manifest["source_request"]["credentials_logged_or_stored"] is False
    assert manifest["source_acceptance"]["run_id"] == "accepted"
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    assert (
        manifest["acceptance_status"]
        == "full_source_coverage_failed_stop_before_prices"
    )
    stored = pd.read_parquet(RICH.resolve_record_path(manifest["files"][0]["path"]))
    assert stored.columns.tolist() == list(RICH.TUSHARE_MONEYFLOW_COLUMNS)
    assert len(stored) == 4
    assert not list((tmp_path / "raw").rglob("*.partial"))


def test_tushare_northbound_top10_contract_is_fingerprint_frozen(tmp_path):
    contract = RICH.load_tushare_northbound_top10_contract()
    assert contract["factor"]["name"] == "tushare_northbound_top10_net_buy_share"
    assert contract["source"]["requested_fields"] == list(
        RICH.TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS
    )
    assert contract["source"]["market_types"] == ["1", "3"]
    assert contract["freeze_evidence"]["provider_interface_rows_observed"] is False
    assert contract["forward_return_fields_read"] is False

    changed = RICH.json.loads(
        RICH.DEFAULT_TUSHARE_NORTHBOUND_TOP10_CONTRACT.read_text()
    )
    changed["factor"]["direction"] = "lower_is_better"
    changed_path = tmp_path / "changed_northbound_contract.json"
    RICH.atomic_write_json(changed, changed_path)
    with pytest.raises(RICH.RichDataError, match="fingerprint mismatch"):
        RICH.load_tushare_northbound_top10_contract(changed_path)


def test_tushare_northbound_top10_request_uses_only_frozen_fields(monkeypatch):
    captured = {}

    class Pro:
        def hsgt_top10(self, **kwargs):
            captured.update(kwargs)
            return pd.DataFrame()

    monkeypatch.setattr(
        RICH,
        "_import_tushare",
        lambda: SimpleNamespace(pro_api=lambda: Pro()),
    )
    RICH.fetch_tushare_northbound_top10(dt.date(2026, 7, 13), "3")
    assert captured["trade_date"] == "20260713"
    assert captured["market_type"] == "3"
    assert captured["fields"].split(",") == list(
        RICH.TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS
    )
    forbidden = set(
        RICH.load_tushare_northbound_top10_contract()["source"][
            "explicitly_forbidden_fields"
        ]
    )
    assert set(captured["fields"].split(",")).isdisjoint(forbidden)


def test_tushare_northbound_top10_normalization_derives_ratio_and_reconciles():
    rows = [
        {
            "trade_date": "20260713",
            "ts_code": "600519.SH",
            "rank": 1,
            "market_type": "1",
            "amount": 100.0,
            "buy": 70.0,
            "sell": 30.0,
        },
        {
            "trade_date": "20260713",
            "ts_code": "600000.SH",
            "rank": 2,
            "market_type": "1",
            "amount": 0.0,
            "buy": 0.0,
            "sell": 0.0,
        },
        {
            "trade_date": "20260713",
            "ts_code": None,
            "rank": 3,
            "market_type": "1",
            "amount": 100.0,
            "buy": 50.0,
            "sell": 50.0,
        },
    ]
    normalized, quality = RICH.canonicalize_tushare_northbound_top10(
        pd.DataFrame(rows),
        dt.date(2026, 7, 13),
        dt.date(2026, 7, 13),
        expected_market_type="1",
    )
    assert normalized.columns.tolist() == list(RICH.TUSHARE_NORTHBOUND_TOP10_COLUMNS)
    assert normalized["instrument"].tolist() == ["SH600519"]
    assert normalized["tushare_northbound_top10_net_buy_share"].item() == pytest.approx(
        0.4
    )
    assert quality == {
        "input_rows": 3,
        "missing_rows_excluded": 1,
        "zero_denominator_rows_excluded": 1,
        "rows_written": 1,
    }
    assert not ({"close", "change", "net_amount"} & set(normalized.columns))

    bad = pd.DataFrame(
        [
            {
                "trade_date": "20260713",
                "ts_code": "600519.SH",
                "rank": 1,
                "market_type": "1",
                "amount": 98.0,
                "buy": 70.0,
                "sell": 30.0,
            }
        ]
    )
    with pytest.raises(RICH.RichDataError, match="does not reconcile"):
        RICH.canonicalize_tushare_northbound_top10(
            bad,
            dt.date(2026, 7, 13),
            dt.date(2026, 7, 13),
            expected_market_type="1",
        )


def test_tushare_northbound_top10_acceptance_writes_no_price_snapshot(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")

    def fake_fetch(trade_date, market_type):
        prefix = "600" if market_type == "1" else "000"
        return pd.DataFrame(
            [
                {
                    "trade_date": trade_date.strftime("%Y%m%d"),
                    "ts_code": f"{prefix}{rank:03d}.{'SH' if market_type == '1' else 'SZ'}",
                    "rank": rank,
                    "market_type": market_type,
                    "amount": 1000.0 + rank,
                    "buy": 600.0 + rank,
                    "sell": 400.0,
                }
                for rank in range(1, 11)
            ],
            columns=RICH.TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS,
        )

    monkeypatch.setattr(RICH, "fetch_tushare_northbound_top10", fake_fetch)
    manifest_path = RICH.sync_tushare_northbound_top10_acceptance()
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["dataset"] == "tushare_northbound_top10_acceptance"
    assert manifest["acceptance_status"] == (
        "accepted_entitlement_and_formula_pending_full_history"
    )
    assert manifest["source_request"]["fields"] == list(
        RICH.TUSHARE_NORTHBOUND_TOP10_RAW_FIELDS
    )
    assert manifest["source_quality"]["rows_written"] == 20
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    stored = pd.read_parquet(RICH.resolve_record_path(manifest["files"][0]["path"]))
    assert stored.columns.tolist() == list(RICH.TUSHARE_NORTHBOUND_TOP10_COLUMNS)
    assert len(stored) == 20


def write_top_inst_top_list_context(tmp_path: Path, codes: list[str]) -> dict:
    """Point a copied top_inst contract at one immutable local top-list fixture."""

    contract = copy.deepcopy(RICH.load_tushare_top_inst_contract())
    frame = pd.DataFrame(
        {
            "trade_date": ["20260713"] * len(codes),
            "ts_code": codes,
            "reason": [f"reason-{index}" for index in range(len(codes))],
        }
    )
    frame_path = tmp_path / "accepted_top_list.parquet"
    RICH.atomic_write_frame(frame, frame_path)
    frame_sha = RICH.frame_digest(frame)
    manifest = {
        "kind": "a_share_rich_data_snapshot",
        "dataset": "tushare_events",
        "provider": "tushare",
        "requested_start": "2026-07-13",
        "requested_end": "2026-07-13",
        "files": [
            {
                "dataset": "top-list",
                "path": str(frame_path),
                "rows": len(frame),
                "sha256": frame_sha,
                "quality": {
                    "exact_duplicate_rows": 0,
                    "missing_key_rows": 0,
                    "outside_requested_date_rows": 0,
                    "raw_rows_preserved_without_deduplication": True,
                },
            }
        ],
        "acceptance_status": "pending_event_time_alignment_and_canonicalization",
        "forward_return_fields_read": False,
        "selection_or_promotion_allowed": False,
    }
    manifest_path = tmp_path / "accepted_top_list_manifest.json"
    RICH.atomic_write_json(manifest, manifest_path)
    contract["local_context"]["accepted_top_list_manifest"] = {
        "path": str(manifest_path),
        "sha256": RICH.file_digest(manifest_path),
    }
    contract["local_context"]["accepted_top_list_frame"] = {
        "path": str(frame_path),
        "sha256": frame_sha,
        "raw_rows": len(frame),
        "exact_duplicate_rows_preserved": 0,
    }
    return contract


def test_tushare_top_inst_contract_is_fingerprint_frozen(tmp_path):
    contract = RICH.load_tushare_top_inst_contract()
    assert contract["factor"]["name"] == "tushare_top_inst_net_buy_share"
    assert contract["source"]["requested_fields"] == list(
        RICH.TUSHARE_TOP_INST_RAW_FIELDS
    )
    assert contract["acceptance_protocol"]["provider_calls"] == 1
    assert contract["freeze_evidence"]["provider_top_inst_rows_observed"] is False
    assert contract["forward_return_fields_read"] is False

    changed = RICH.json.loads(RICH.DEFAULT_TUSHARE_TOP_INST_CONTRACT.read_text())
    changed["factor"]["direction"] = "lower_is_better"
    changed_path = tmp_path / "changed_top_inst_contract.json"
    RICH.atomic_write_json(changed, changed_path)
    with pytest.raises(RICH.RichDataError, match="fingerprint mismatch"):
        RICH.load_tushare_top_inst_contract(changed_path)


def test_tushare_top_inst_request_uses_only_frozen_fields(monkeypatch):
    captured = {}

    class Pro:
        def top_inst(self, **kwargs):
            captured.update(kwargs)
            return pd.DataFrame()

    monkeypatch.setattr(
        RICH,
        "_import_tushare",
        lambda: SimpleNamespace(pro_api=lambda: Pro()),
    )
    RICH.fetch_tushare_top_inst(dt.date(2026, 7, 13))
    assert captured["trade_date"] == "20260713"
    assert captured["fields"].split(",") == list(RICH.TUSHARE_TOP_INST_RAW_FIELDS)
    forbidden = set(
        RICH.load_tushare_top_inst_contract()["source"]["explicitly_forbidden_fields"]
    )
    assert set(captured["fields"].split(",")).isdisjoint(forbidden)


def test_tushare_top_inst_normalization_aggregates_and_reconciles_unique_seats():
    rows = [
        {
            "trade_date": "20260713",
            "ts_code": "600519.SH",
            "exalter": "institution-a",
            "buy": 60.0,
            "sell": 40.0,
            "net_buy": 20.0,
        },
        {
            "trade_date": "20260713",
            "ts_code": "600519.SH",
            "exalter": "institution-b",
            "buy": 30.0,
            "sell": 70.0,
            "net_buy": -40.0,
        },
        {
            "trade_date": "20260713",
            "ts_code": "600000.SH",
            "exalter": "institution-c",
            "buy": 0.0,
            "sell": 0.0,
            "net_buy": 0.0,
        },
    ]
    normalized, quality = RICH.canonicalize_tushare_top_inst(
        pd.DataFrame(rows, columns=RICH.TUSHARE_TOP_INST_RAW_FIELDS),
        dt.date(2026, 7, 13),
        dt.date(2026, 7, 13),
    )
    assert normalized.columns.tolist() == list(RICH.TUSHARE_TOP_INST_COLUMNS)
    assert normalized["instrument"].tolist() == ["SH600519"]
    assert normalized["institution_seat_count"].item() == 2
    assert normalized["buy"].item() == pytest.approx(90.0)
    assert normalized["sell"].item() == pytest.approx(110.0)
    assert normalized["tushare_top_inst_net_buy_share"].item() == pytest.approx(-0.1)
    assert quality == {
        "input_rows": 3,
        "institution_seat_rows_reconciled": 3,
        "zero_denominator_stock_days_excluded": 1,
        "rows_written": 1,
    }
    assert not ({"exalter", "net_buy", "close", "reason"} & set(normalized.columns))

    bad_reconciliation = pd.DataFrame(
        [rows[0]], columns=RICH.TUSHARE_TOP_INST_RAW_FIELDS
    )
    bad_reconciliation.loc[0, "net_buy"] = 19.0
    with pytest.raises(RICH.RichDataError, match="does not reconcile"):
        RICH.canonicalize_tushare_top_inst(
            bad_reconciliation,
            dt.date(2026, 7, 13),
            dt.date(2026, 7, 13),
        )

    duplicate = pd.DataFrame(
        [rows[0], rows[0]], columns=RICH.TUSHARE_TOP_INST_RAW_FIELDS
    )
    with pytest.raises(RICH.RichDataError, match="duplicate institution-seat keys"):
        RICH.canonicalize_tushare_top_inst(
            duplicate,
            dt.date(2026, 7, 13),
            dt.date(2026, 7, 13),
        )


def test_tushare_top_inst_acceptance_writes_no_price_snapshot_and_is_one_shot(
    tmp_path, monkeypatch
):
    contract = write_top_inst_top_list_context(
        tmp_path, ["600519.SH", "000001.SZ", "118069.SH", "920081.BJ"]
    )
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(RICH, "load_tushare_top_inst_contract", lambda: contract)
    calls = []

    def fake_fetch(trade_date):
        calls.append(trade_date)
        return pd.DataFrame(
            [
                {
                    "trade_date": "20260713",
                    "ts_code": "600519.SH",
                    "exalter": "institution-a",
                    "buy": 60.0,
                    "sell": 40.0,
                    "net_buy": 20.0,
                },
                {
                    "trade_date": "20260713",
                    "ts_code": "600519.SH",
                    "exalter": "institution-b",
                    "buy": 30.0,
                    "sell": 70.0,
                    "net_buy": -40.0,
                },
                {
                    "trade_date": "20260713",
                    "ts_code": "000001.SZ",
                    "exalter": "institution-c",
                    "buy": 100.0,
                    "sell": 0.0,
                    "net_buy": 100.0,
                },
            ],
            columns=RICH.TUSHARE_TOP_INST_RAW_FIELDS,
        )

    monkeypatch.setattr(RICH, "fetch_tushare_top_inst", fake_fetch)
    manifest_path = RICH.sync_tushare_top_inst_acceptance()
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["dataset"] == "tushare_top_inst_acceptance"
    assert manifest["acceptance_status"] == (
        "accepted_entitlement_schema_formula_and_top_list_concordance_"
        "pending_full_history_protocol"
    )
    assert manifest["source_request"]["provider_calls_issued"] == 1
    assert manifest["source_request"]["fields"] == list(
        RICH.TUSHARE_TOP_INST_RAW_FIELDS
    )
    assert manifest["accepted_top_list_evidence"]["all_top_inst_stocks_present"] is True
    assert (
        manifest["accepted_top_list_evidence"]["unsupported_security_rows_excluded"]
        == 2
    )
    assert manifest["source_quality"]["institution_seat_rows_reconciled"] == 3
    assert (
        manifest["source_quality"][
            "provider_net_buy_used_only_for_integrity_reconciliation"
        ]
        is True
    )
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    stored = pd.read_parquet(RICH.resolve_record_path(manifest["files"][0]["path"]))
    assert stored.columns.tolist() == list(RICH.TUSHARE_TOP_INST_COLUMNS)
    assert len(stored) == 2
    assert len(calls) == 1

    with pytest.raises(RICH.RichDataError, match="one-shot.*already consumed"):
        RICH.sync_tushare_top_inst_acceptance()
    assert len(calls) == 1


def test_tushare_top_inst_acceptance_rejects_stock_absent_from_top_list(
    tmp_path, monkeypatch
):
    contract = write_top_inst_top_list_context(tmp_path, ["600519.SH"])
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(RICH, "load_tushare_top_inst_contract", lambda: contract)
    monkeypatch.setattr(
        RICH,
        "fetch_tushare_top_inst",
        lambda trade_date: pd.DataFrame(
            [
                {
                    "trade_date": "20260713",
                    "ts_code": "000001.SZ",
                    "exalter": "institution-a",
                    "buy": 60.0,
                    "sell": 40.0,
                    "net_buy": 20.0,
                }
            ],
            columns=RICH.TUSHARE_TOP_INST_RAW_FIELDS,
        ),
    )
    with pytest.raises(RICH.RichDataError, match="absent from.*top_list"):
        RICH.sync_tushare_top_inst_acceptance()
    records = RICH.tushare_top_inst_acceptance_records()
    assert len(records) == 1
    rejection = RICH.json.loads(records[0].read_text())
    assert rejection["acceptance_status"] == (
        "rejected_stop_before_full_history_or_returns"
    )
    assert rejection["source_request"]["provider_calls_issued"] == 1
    assert rejection["files"] == []
    assert rejection["price_fields_loaded"] == []
    assert rejection["forward_return_fields_read"] is False

    with pytest.raises(RICH.RichDataError, match="one-shot.*already consumed"):
        RICH.sync_tushare_top_inst_acceptance()


def top10_float_rows(
    ts_code: str,
    ann_date: str,
    end_date: str,
    *,
    count: int = 10,
    ratio_start: float = 0.5,
    holder_prefix: str = "holder",
) -> list[dict]:
    return [
        {
            "ts_code": ts_code,
            "ann_date": ann_date,
            "end_date": end_date,
            "holder_name": f"{holder_prefix}-{index}",
            "hold_float_ratio": ratio_start + index * 0.01,
        }
        for index in range(count)
    ]


def test_tushare_top10_float_concentration_contract_is_fingerprint_frozen(
    tmp_path,
):
    contract = RICH.load_tushare_top10_float_concentration_contract()
    assert contract["factor"]["name"] == "top10_float_concentration_change_pp"
    assert contract["source"]["requested_fields"] == list(
        RICH.TUSHARE_TOP10_FLOAT_RAW_FIELDS
    )
    assert contract["acceptance_protocol"]["fixed_symbols"] == list(
        RICH.TUSHARE_TOP10_FLOAT_ACCEPTANCE_SYMBOLS
    )
    assert (
        contract["freeze_evidence"]["provider_top10_floatholders_rows_observed"]
        is False
    )
    assert contract["forward_return_fields_read"] is False

    changed = RICH.json.loads(
        RICH.DEFAULT_TUSHARE_TOP10_FLOAT_CONCENTRATION_CONTRACT.read_text()
    )
    changed["factor"]["direction"] = "lower_is_better"
    changed_path = tmp_path / "changed_top10_float_contract.json"
    RICH.atomic_write_json(changed, changed_path)
    with pytest.raises(RICH.RichDataError, match="fingerprint mismatch"):
        RICH.load_tushare_top10_float_concentration_contract(changed_path)


def test_tushare_top10_float_request_uses_only_frozen_fields(monkeypatch):
    captured = {}

    class Pro:
        def top10_floatholders(self, **kwargs):
            captured.update(kwargs)
            return pd.DataFrame()

    monkeypatch.setattr(
        RICH,
        "_import_tushare",
        lambda: SimpleNamespace(pro_api=lambda: Pro()),
    )
    RICH.fetch_tushare_top10_float_holders(
        "600519.SH",
        dt.date(2024, 12, 31),
        dt.date(2025, 12, 31),
    )
    assert captured == {
        "ts_code": "600519.SH",
        "start_date": "20241231",
        "end_date": "20251231",
        "fields": ",".join(RICH.TUSHARE_TOP10_FLOAT_RAW_FIELDS),
    }
    forbidden = set(
        RICH.load_tushare_top10_float_concentration_contract()["source"][
            "explicitly_forbidden_fields"
        ]
    )
    assert set(captured["fields"].split(",")).isdisjoint(forbidden)


def test_tushare_top10_float_normalization_hashes_names_and_uses_first_complete_version():
    rows = [
        *top10_float_rows("600519.SH", "20250401", "20241231", ratio_start=0.5),
        *top10_float_rows("600519.SH", "20250430", "20250331", ratio_start=0.6),
        *top10_float_rows(
            "600519.SH",
            "20250510",
            "20250331",
            ratio_start=0.8,
            holder_prefix="revision-holder",
        ),
        *top10_float_rows(
            "600519.SH", "20250830", "20250630", count=9, ratio_start=0.7
        ),
    ]
    source, factors, quality = RICH.canonicalize_tushare_top10_float_holders(
        pd.DataFrame(rows, columns=RICH.TUSHARE_TOP10_FLOAT_RAW_FIELDS),
        expected_ts_code="600519.SH",
        report_period_start=dt.date(2024, 12, 31),
        report_period_end=dt.date(2025, 12, 31),
        latest_announcement_date=dt.date(2026, 7, 16),
    )
    assert source.columns.tolist() == list(RICH.TUSHARE_TOP10_FLOAT_SOURCE_COLUMNS)
    assert factors.columns.tolist() == list(RICH.TUSHARE_TOP10_FLOAT_FACTOR_COLUMNS)
    assert "holder_name" not in source.columns
    assert source["holder_name_sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
    assert len(factors) == 1
    factor = factors.iloc[0]
    assert factor["report_period"] == pd.Timestamp("2025-03-31")
    assert factor["previous_report_period"] == pd.Timestamp("2024-12-31")
    assert factor["top10_float_concentration_pct"] == pytest.approx(6.45)
    assert factor["top10_float_concentration_change_pp"] == pytest.approx(1.0)
    assert quality == {
        "input_rows": 39,
        "source_rows_written": 39,
        "report_groups_observed": 4,
        "complete_report_groups": 3,
        "incomplete_report_groups_excluded": 1,
        "first_complete_report_periods": 2,
        "later_complete_revision_groups_not_used": 1,
        "factor_ready_consecutive_pairs": 1,
    }

    duplicate = pd.DataFrame(
        [rows[0], rows[0]], columns=RICH.TUSHARE_TOP10_FLOAT_RAW_FIELDS
    )
    with pytest.raises(RICH.RichDataError, match="duplicate holder event keys"):
        RICH.canonicalize_tushare_top10_float_holders(
            duplicate,
            expected_ts_code="600519.SH",
            report_period_start=dt.date(2024, 12, 31),
            report_period_end=dt.date(2025, 12, 31),
            latest_announcement_date=dt.date(2026, 7, 16),
        )

    invalid_ratio = pd.DataFrame(
        [dict(rows[0], hold_float_ratio=101.0)],
        columns=RICH.TUSHARE_TOP10_FLOAT_RAW_FIELDS,
    )
    with pytest.raises(RICH.RichDataError, match=r"outside \[0, 100\]"):
        RICH.canonicalize_tushare_top10_float_holders(
            invalid_ratio,
            expected_ts_code="600519.SH",
            report_period_start=dt.date(2024, 12, 31),
            report_period_end=dt.date(2025, 12, 31),
            latest_announcement_date=dt.date(2026, 7, 16),
        )


def test_tushare_top10_float_acceptance_persists_hashes_without_prices_and_is_one_shot(
    tmp_path, monkeypatch
):
    contract = copy.deepcopy(RICH.load_tushare_top10_float_concentration_contract())
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(
        RICH,
        "load_tushare_top10_float_concentration_contract",
        lambda: contract,
    )
    monkeypatch.setattr(
        RICH,
        "validate_tushare_top10_float_local_context",
        lambda value: {"fixture": {"path": "fixture", "sha256": "0" * 64}},
    )
    calls = []

    def fake_fetch(symbol, report_period_start, report_period_end):
        calls.append((symbol, report_period_start, report_period_end))
        rows = [
            *top10_float_rows(
                symbol,
                "20250401",
                "20241231",
                ratio_start=0.5,
                holder_prefix=f"{symbol}-previous",
            ),
            *top10_float_rows(
                symbol,
                "20250430",
                "20250331",
                ratio_start=0.6,
                holder_prefix=f"{symbol}-current",
            ),
        ]
        return pd.DataFrame(rows, columns=RICH.TUSHARE_TOP10_FLOAT_RAW_FIELDS)

    monkeypatch.setattr(RICH, "fetch_tushare_top10_float_holders", fake_fetch)
    manifest_path = RICH.sync_tushare_top10_float_concentration_acceptance()
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["dataset"] == "tushare_top10_float_concentration_acceptance"
    assert manifest["acceptance_status"] == (
        "accepted_entitlement_schema_and_concentration_formula_pending_full_history"
    )
    assert manifest["source_request"]["provider_calls_issued"] == 3
    assert manifest["source_request"]["fields"] == list(
        RICH.TUSHARE_TOP10_FLOAT_RAW_FIELDS
    )
    assert (
        manifest["source_request"]["plaintext_holder_names_logged_or_stored"] is False
    )
    assert manifest["source_quality"]["input_rows"] == 60
    assert manifest["source_quality"]["factor_ready_consecutive_pairs"] == 3
    assert manifest["source_quality"]["plaintext_holder_names_persisted"] is False
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    assert len(calls) == 3
    source_file = next(
        item for item in manifest["files"] if item["role"].startswith("normalized")
    )
    factor_file = next(
        item for item in manifest["files"] if item["role"].startswith("first")
    )
    stored_source = pd.read_parquet(RICH.resolve_record_path(source_file["path"]))
    stored_factors = pd.read_parquet(RICH.resolve_record_path(factor_file["path"]))
    assert stored_source.columns.tolist() == list(
        RICH.TUSHARE_TOP10_FLOAT_SOURCE_COLUMNS
    )
    assert stored_factors.columns.tolist() == list(
        RICH.TUSHARE_TOP10_FLOAT_FACTOR_COLUMNS
    )
    assert len(stored_source) == 60
    assert len(stored_factors) == 3

    with pytest.raises(RICH.RichDataError, match="one-shot.*already consumed"):
        RICH.sync_tushare_top10_float_concentration_acceptance()
    assert len(calls) == 3


def test_tushare_top10_float_acceptance_rejects_insufficient_consecutive_history_once(
    tmp_path, monkeypatch
):
    contract = copy.deepcopy(RICH.load_tushare_top10_float_concentration_contract())
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(
        RICH,
        "load_tushare_top10_float_concentration_contract",
        lambda: contract,
    )
    monkeypatch.setattr(
        RICH,
        "validate_tushare_top10_float_local_context",
        lambda value: {"fixture": {"path": "fixture", "sha256": "0" * 64}},
    )
    calls = []

    def fake_fetch(symbol, report_period_start, report_period_end):
        calls.append(symbol)
        periods = [("20250401", "20241231", 0.5)]
        if symbol != "300750.SZ":
            periods.append(("20250430", "20250331", 0.6))
        rows = []
        for announcement, period, ratio in periods:
            rows.extend(
                top10_float_rows(
                    symbol,
                    announcement,
                    period,
                    ratio_start=ratio,
                    holder_prefix=f"{symbol}-{period}",
                )
            )
        return pd.DataFrame(rows, columns=RICH.TUSHARE_TOP10_FLOAT_RAW_FIELDS)

    monkeypatch.setattr(RICH, "fetch_tushare_top10_float_holders", fake_fetch)
    with pytest.raises(RICH.RichDataError, match="too few complete report groups"):
        RICH.sync_tushare_top10_float_concentration_acceptance()
    assert len(calls) == 3
    records = RICH.tushare_top10_float_concentration_acceptance_records()
    assert len(records) == 1
    rejection = RICH.json.loads(records[0].read_text())
    assert rejection["source_request"]["provider_calls_issued"] == 3
    assert rejection["files"] == []
    assert rejection["price_fields_loaded"] == []
    assert rejection["forward_return_fields_read"] is False

    with pytest.raises(RICH.RichDataError, match="one-shot.*already consumed"):
        RICH.sync_tushare_top10_float_concentration_acceptance()
    assert len(calls) == 3


def cash_statement_row(
    ts_code: str,
    endpoint: str,
    ann_date: str,
    f_ann_date: str,
    end_date: str,
    value,
    *,
    report_type: str = "1",
    comp_type: str = "1",
    update_flag: str = "1",
) -> dict:
    row = {
        "ts_code": ts_code,
        "ann_date": ann_date,
        "f_ann_date": f_ann_date,
        "end_date": end_date,
        "report_type": report_type,
        "comp_type": comp_type,
        "update_flag": update_flag,
    }
    if endpoint == "income":
        row["n_income_attr_p"] = value
    else:
        row["n_cashflow_act"] = value
    return row


def clean_cash_statement_frame(
    ts_code: str,
    endpoint: str,
    *,
    periods: int = 5,
) -> pd.DataFrame:
    schedule = [
        ("20240330", "20240401", "20231231"),
        ("20240429", "20240430", "20240331"),
        ("20240829", "20240830", "20240630"),
        ("20241030", "20241031", "20240930"),
        ("20250330", "20250331", "20241231"),
    ]
    rows = []
    for index, (ann_date, f_ann_date, end_date) in enumerate(schedule[:periods]):
        value = 100.0 + index * 10.0
        if endpoint == "cashflow":
            value += 20.0
        rows.append(
            cash_statement_row(
                ts_code,
                endpoint,
                ann_date,
                f_ann_date,
                end_date,
                value,
            )
        )
    fields = (
        RICH.TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS
        if endpoint == "income"
        else RICH.TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS
    )
    return pd.DataFrame(rows, columns=fields)


def forecast_row(
    ts_code: str,
    ann_date: str,
    end_date: str,
    forecast_type: str,
    lower,
    upper,
    *,
    first_ann_date: str | None = None,
) -> dict:
    return {
        "ts_code": ts_code,
        "ann_date": ann_date,
        "end_date": end_date,
        "type": forecast_type,
        "p_change_min": lower,
        "p_change_max": upper,
        "first_ann_date": first_ann_date or ann_date,
    }


def test_tushare_earnings_forecast_contract_is_frozen_before_rows():
    assert (
        RICH.file_digest(RICH.DEFAULT_TUSHARE_EARNINGS_FORECAST_CONTRACT)
        == RICH.TUSHARE_EARNINGS_FORECAST_CONTRACT_SHA256
    )
    contract = RICH.load_tushare_earnings_forecast_contract()
    assert contract["source"]["requested_fields"] == list(
        RICH.TUSHARE_EARNINGS_FORECAST_RAW_FIELDS
    )
    assert contract["factor"]["formula"] == (
        "(p_change_min + p_change_max) / 2"
    )
    assert contract["freeze_evidence"]["provider_forecast_rows_observed"] is False
    assert contract["forward_return_fields_read"] is False


def test_tushare_earnings_forecast_request_uses_only_frozen_fields(monkeypatch):
    captured = []

    class Pro:
        def forecast(self, **kwargs):
            captured.append(kwargs)
            return pd.DataFrame()

    monkeypatch.setattr(
        RICH,
        "_import_tushare",
        lambda: SimpleNamespace(pro_api=lambda: Pro()),
    )
    RICH.fetch_tushare_earnings_forecast(
        "002594.SZ", dt.date(2019, 1, 1), dt.date(2025, 12, 31)
    )
    assert captured == [
        {
            "ts_code": "002594.SZ",
            "start_date": "20190101",
            "end_date": "20251231",
            "fields": ",".join(RICH.TUSHARE_EARNINGS_FORECAST_RAW_FIELDS),
        }
    ]


def test_tushare_earnings_forecast_canonicalization_is_type_and_bound_strict():
    rows = [
        forecast_row("002594.SZ", "20241220", "20241231", "预增", 10.0, 20.0),
        forecast_row("002594.SZ", "20241220", "20241231", "预增", 10.0, 20.0),
        forecast_row(
            "002594.SZ",
            "20250420",
            "20250331",
            "扭亏",
            None,
            None,
            first_ann_date=None,
        ),
        forecast_row("002594.SZ", "20250820", "20250630", "略减", None, -5.0),
        forecast_row("002594.SZ", "20251020", "20250930", "预减", -20.0, -30.0),
    ]
    frame = pd.DataFrame(rows, columns=RICH.TUSHARE_EARNINGS_FORECAST_RAW_FIELDS)
    accepted, quality = RICH.canonicalize_tushare_earnings_forecast(
        frame,
        expected_ts_code="002594.SZ",
        announcement_start=dt.date(2019, 1, 1),
        announcement_end=dt.date(2025, 12, 31),
    )
    assert accepted.columns.tolist() == list(RICH.TUSHARE_EARNINGS_FORECAST_COLUMNS)
    assert accepted["tushare_earnings_forecast_growth_midpoint"].tolist() == [15.0]
    assert quality["exact_semantic_duplicate_rows_collapsed"] == 1
    assert quality["noncomparable_type_counts"] == {"扭亏": 1}
    assert quality["missing_or_nonfinite_bound_rows_excluded"] == 1
    assert quality["reversed_bound_rows_excluded"] == 1
    assert quality["rows_written"] == 1

    unknown = frame.iloc[[0]].copy()
    unknown.loc[:, "type"] = "不确定"
    with pytest.raises(RICH.RichDataError, match="unknown types"):
        RICH.canonicalize_tushare_earnings_forecast(
            unknown,
            expected_ts_code="002594.SZ",
            announcement_start=dt.date(2019, 1, 1),
            announcement_end=dt.date(2025, 12, 31),
        )

    conflict = frame.iloc[[0, 0]].copy().reset_index(drop=True)
    conflict.loc[1, "p_change_max"] = 21.0
    with pytest.raises(RICH.RichDataError, match="conflicting duplicate"):
        RICH.canonicalize_tushare_earnings_forecast(
            conflict,
            expected_ts_code="002594.SZ",
            announcement_start=dt.date(2019, 1, 1),
            announcement_end=dt.date(2025, 12, 31),
        )


def test_tushare_earnings_forecast_acceptance_is_atomic_and_one_shot(
    tmp_path, monkeypatch
):
    contract = copy.deepcopy(RICH.load_tushare_earnings_forecast_contract())
    monkeypatch.setattr(
        RICH, "load_tushare_earnings_forecast_contract", lambda: contract
    )
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(
        RICH,
        "DEFAULT_TUSHARE_EARNINGS_FORECAST_ACCEPTANCE_RECORD",
        tmp_path / "no_terminal_forecast_record.json",
    )
    calls = []

    def fake_fetch(symbol, announcement_start, announcement_end):
        calls.append((symbol, announcement_start, announcement_end))
        rows = [
            forecast_row(symbol, "20250120", "20241231", "预增", 10.0, 20.0),
            forecast_row(symbol, "20250420", "20250331", "续亏", None, None),
        ]
        return pd.DataFrame(rows, columns=RICH.TUSHARE_EARNINGS_FORECAST_RAW_FIELDS)

    monkeypatch.setattr(RICH, "fetch_tushare_earnings_forecast", fake_fetch)
    manifest_path = RICH.sync_tushare_earnings_forecast_acceptance()
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["acceptance_status"] == (
        "accepted_entitlement_schema_type_policy_and_formula_pending_full_history"
    )
    assert manifest["source_request"]["provider_calls_issued"] == 3
    assert manifest["source_request"]["forecast_vip_requested"] is False
    assert manifest["source_quality"]["source_rows"] == 6
    assert manifest["source_quality"]["rows_written"] == 3
    assert manifest["source_quality"]["symbols_with_comparable_events"] == 3
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    assert len(calls) == 3
    with pytest.raises(RICH.RichDataError, match="already consumed"):
        RICH.sync_tushare_earnings_forecast_acceptance()
    assert len(calls) == 3


def test_tushare_earnings_forecast_terminal_record_blocks_before_provider(
    tmp_path, monkeypatch
):
    record = RICH.load_tushare_earnings_forecast_acceptance_record()
    assert record["status"] == (
        "terminal_rejected_after_one_call_before_factor_values_with_prior_mechanism_overlap"
    )
    assert record["acceptance_failure"]["provider_calls_issued"] == 1
    assert record["implementation_audit"]["retry_authorized"] is False
    assert record["prior_mechanism_overlap"]["accepted_price_rebuild"][
        "qualified_factor_count"
    ] == 0
    assert record["forward_return_fields_read"] is False

    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(
        RICH,
        "load_tushare_earnings_forecast_contract",
        lambda: pytest.fail("terminal gate must run before contract/provider work"),
    )
    with pytest.raises(RICH.RichDataError, match="branch is terminal.*forbidden"):
        RICH.sync_tushare_earnings_forecast_acceptance()


def disclosure_plan_row(
    ts_code: str,
    ann_date: str,
    end_date: str,
    pre_date: str,
    modify_date: str | None = None,
) -> dict:
    return {
        "ts_code": ts_code,
        "ann_date": ann_date,
        "end_date": end_date,
        "pre_date": pre_date,
        "modify_date": modify_date,
    }


def test_tushare_disclosure_promptness_contract_is_frozen_before_rows():
    assert (
        RICH.file_digest(RICH.DEFAULT_TUSHARE_DISCLOSURE_PROMPTNESS_CONTRACT)
        == RICH.TUSHARE_DISCLOSURE_PROMPTNESS_CONTRACT_SHA256
    )
    contract = RICH.load_tushare_disclosure_promptness_contract()
    assert contract["source"]["requested_fields"] == list(
        RICH.TUSHARE_DISCLOSURE_PROMPTNESS_RAW_FIELDS
    )
    assert contract["factor"]["formula"] == (
        "calendar_days(pre_date - ann_date)"
    )
    assert contract["factor"]["direction"] == "lower_is_better"
    assert contract["freeze_evidence"]["provider_disclosure_date_rows_observed"] is False
    assert contract["forward_return_fields_read"] is False


def test_tushare_disclosure_promptness_request_uses_only_frozen_fields(monkeypatch):
    captured = []

    class Pro:
        def disclosure_date(self, **kwargs):
            captured.append(kwargs)
            return pd.DataFrame()

    monkeypatch.setattr(
        RICH,
        "_import_tushare",
        lambda: SimpleNamespace(pro_api=lambda: Pro()),
    )
    RICH.fetch_tushare_disclosure_plan(dt.date(2024, 12, 31))
    assert captured == [
        {
            "end_date": "20241231",
            "fields": ",".join(RICH.TUSHARE_DISCLOSURE_PROMPTNESS_RAW_FIELDS),
        }
    ]


def test_tushare_disclosure_promptness_canonicalization_is_strict():
    rows = [
        disclosure_plan_row(
            "600000.SH", "20241228", "20241231", "20250415", "20250410"
        ),
        disclosure_plan_row(
            "600000.SH", "20241228", "20241231", "20250415", "20250410"
        ),
        disclosure_plan_row("000001.SZ", "20241229", "20241231", "20250331"),
        disclosure_plan_row("430001.BJ", "20241229", "20241231", "20250420"),
    ]
    frame = pd.DataFrame(
        rows, columns=RICH.TUSHARE_DISCLOSURE_PROMPTNESS_RAW_FIELDS
    )
    accepted, quality = RICH.canonicalize_tushare_disclosure_plan(
        frame, dt.date(2024, 12, 31)
    )
    assert accepted.columns.tolist() == list(
        RICH.TUSHARE_DISCLOSURE_PROMPTNESS_COLUMNS
    )
    assert accepted["instrument"].tolist() == ["SH600000", "SZ000001"]
    assert accepted["tushare_disclosure_plan_lead_days"].tolist() == [108, 92]
    assert quality["outside_target_bj_rows_excluded"] == 1
    assert quality["exact_semantic_duplicate_rows_collapsed"] == 1
    assert quality["modify_date_context_rows"] == 2
    assert quality["rows_written"] == 2

    conflict = frame.iloc[[0, 0]].copy().reset_index(drop=True)
    conflict.loc[1, "pre_date"] = "20250416"
    with pytest.raises(RICH.RichDataError, match="conflicting stock-period"):
        RICH.canonicalize_tushare_disclosure_plan(
            conflict, dt.date(2024, 12, 31)
        )

    negative = frame.iloc[[0]].copy()
    negative.loc[:, "pre_date"] = "20241227"
    with pytest.raises(RICH.RichDataError, match="announcement after its planned"):
        RICH.canonicalize_tushare_disclosure_plan(
            negative, dt.date(2024, 12, 31)
        )

    unknown_exchange = frame.iloc[[0]].copy()
    unknown_exchange.loc[:, "ts_code"] = "600000.HK"
    with pytest.raises(RICH.RichDataError, match="invalid keys or dates"):
        RICH.canonicalize_tushare_disclosure_plan(
            unknown_exchange, dt.date(2024, 12, 31)
        )


def test_tushare_disclosure_promptness_acceptance_is_atomic_and_one_shot(
    tmp_path, monkeypatch
):
    contract = copy.deepcopy(RICH.load_tushare_disclosure_promptness_contract())
    monkeypatch.setattr(
        RICH, "load_tushare_disclosure_promptness_contract", lambda: contract
    )
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(
        RICH,
        "DEFAULT_TUSHARE_DISCLOSURE_PROMPTNESS_ACCEPTANCE_RECORD",
        tmp_path / "no_terminal_disclosure_record.json",
    )
    calls = []

    def fake_fetch(report_period):
        calls.append(report_period)
        ann_date = report_period - dt.timedelta(days=3)
        rows = []
        for index in range(2500):
            code = f"{600000 + index:06d}.SH"
            planned = ann_date + dt.timedelta(days=index % 20)
            rows.append(
                disclosure_plan_row(
                    code,
                    ann_date.strftime("%Y%m%d"),
                    report_period.strftime("%Y%m%d"),
                    planned.strftime("%Y%m%d"),
                )
            )
        return pd.DataFrame(
            rows, columns=RICH.TUSHARE_DISCLOSURE_PROMPTNESS_RAW_FIELDS
        )

    monkeypatch.setattr(RICH, "fetch_tushare_disclosure_plan", fake_fetch)
    manifest_path = RICH.sync_tushare_disclosure_promptness_acceptance()
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["acceptance_status"] == (
        "accepted_entitlement_schema_point_in_time_policy_and_formula_pending_full_history"
    )
    assert manifest["source_request"]["provider_calls_issued"] == 3
    assert manifest["source_request"]["actual_date_requested_or_stored"] is False
    assert manifest["source_request"]["modify_date_values_persisted"] is False
    assert manifest["source_quality"]["source_rows"] == 7500
    assert manifest["source_quality"]["rows_written"] == 7500
    assert manifest["source_quality"]["factor_distinct_values"] == 20
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    assert len(calls) == 3
    with pytest.raises(RICH.RichDataError, match="one-shot.*already consumed"):
        RICH.sync_tushare_disclosure_promptness_acceptance()
    assert len(calls) == 3


def test_tushare_disclosure_promptness_terminal_record_blocks_before_provider(
    tmp_path, monkeypatch
):
    record = RICH.load_tushare_disclosure_promptness_acceptance_record()
    assert record["status"] == (
        "terminal_rejected_on_first_report_period_before_factor_values_or_returns"
    )
    assert record["acceptance_failure"]["provider_calls_issued"] == 1
    assert record["acceptance_failure"]["invalid_key_or_date_rows"] == 25
    assert record["decision"]["acceptance_retry_allowed"] is False
    assert record["forward_return_fields_read"] is False

    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(
        RICH,
        "load_tushare_disclosure_promptness_contract",
        lambda: pytest.fail("terminal gate must run before contract/provider work"),
    )
    with pytest.raises(RICH.RichDataError, match="branch is terminal.*forbidden"):
        RICH.sync_tushare_disclosure_promptness_acceptance()


def test_tushare_cash_conversion_contract_is_fingerprint_frozen(tmp_path):
    contract = RICH.load_tushare_cash_conversion_contract()
    assert contract["factor"]["name"] == "tushare_operating_cash_conversion"
    assert contract["factor"]["formula"] == "n_cashflow_act / n_income_attr_p"
    assert contract["source"]["income_requested_fields"] == list(
        RICH.TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS
    )
    assert contract["source"]["cashflow_requested_fields"] == list(
        RICH.TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS
    )
    assert contract["freeze_evidence"]["provider_income_rows_observed"] is False
    assert contract["freeze_evidence"]["provider_cashflow_rows_observed"] is False
    assert contract["forward_return_fields_read"] is False

    changed = RICH.json.loads(RICH.DEFAULT_TUSHARE_CASH_CONVERSION_CONTRACT.read_text())
    changed["factor"]["direction"] = "lower_is_better"
    changed_path = tmp_path / "changed_cash_conversion_contract.json"
    RICH.atomic_write_json(changed, changed_path)
    with pytest.raises(RICH.RichDataError, match="fingerprint mismatch"):
        RICH.load_tushare_cash_conversion_contract(changed_path)


def test_tushare_cash_conversion_requests_use_only_endpoint_whitelists(monkeypatch):
    captured = []

    class Pro:
        def income(self, **kwargs):
            captured.append(("income", kwargs))
            return pd.DataFrame()

        def cashflow(self, **kwargs):
            captured.append(("cashflow", kwargs))
            return pd.DataFrame()

    monkeypatch.setattr(
        RICH,
        "_import_tushare",
        lambda: SimpleNamespace(pro_api=lambda: Pro()),
    )
    for endpoint in ("income", "cashflow"):
        RICH.fetch_tushare_cash_conversion_statement(
            endpoint,
            "600519.SH",
            dt.date(2024, 1, 1),
            dt.date(2026, 6, 30),
        )
    assert captured == [
        (
            "income",
            {
                "ts_code": "600519.SH",
                "start_date": "20240101",
                "end_date": "20260630",
                "fields": ",".join(RICH.TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS),
            },
        ),
        (
            "cashflow",
            {
                "ts_code": "600519.SH",
                "start_date": "20240101",
                "end_date": "20260630",
                "fields": ",".join(RICH.TUSHARE_CASH_CONVERSION_CASHFLOW_RAW_FIELDS),
            },
        ),
    ]
    forbidden = set(
        RICH.load_tushare_cash_conversion_contract()["source"][
            "explicitly_forbidden_fields"
        ]
    )
    for _, kwargs in captured:
        assert set(kwargs["fields"].split(",")).isdisjoint(forbidden)


def test_tushare_cash_conversion_endpoint_enforces_frozen_version_policy():
    rows = [
        cash_statement_row(
            "600519.SH", "income", "20240330", "20240401", "20231231", 100.0
        ),
        cash_statement_row(
            "600519.SH",
            "income",
            "20240330",
            "20240401",
            "20231231",
            100.0,
            update_flag="0",
        ),
        cash_statement_row(
            "600519.SH", "income", "20240429", "20240430", "20240331", 110.0
        ),
        cash_statement_row(
            "600519.SH",
            "income",
            "20240502",
            "20240503",
            "20240331",
            111.0,
            report_type="4",
        ),
        cash_statement_row(
            "600519.SH", "income", "20240829", "20240830", "20240630", 120.0
        ),
        cash_statement_row(
            "600519.SH", "income", "20240830", "20240831", "20240630", 121.0
        ),
        cash_statement_row(
            "600519.SH", "income", "20241030", "20241031", "20240930", None
        ),
        cash_statement_row(
            "600519.SH",
            "income",
            "20250330",
            "20250331",
            "20241231",
            130.0,
            report_type="2",
        ),
        cash_statement_row(
            "600519.SH",
            "income",
            "20250429",
            "20250430",
            "20250331",
            140.0,
            comp_type="2",
        ),
        cash_statement_row(
            "600519.SH", "income", "20250829", "20250830", "20250630", 150.0
        ),
    ]
    frame = pd.DataFrame(rows, columns=RICH.TUSHARE_CASH_CONVERSION_INCOME_RAW_FIELDS)
    accepted, quality = RICH.canonicalize_tushare_cash_conversion_endpoint(
        frame,
        endpoint="income",
        expected_ts_code="600519.SH",
        announcement_start=dt.date(2024, 1, 1),
        announcement_end=dt.date(2026, 6, 30),
        latest_actual_announcement_date=dt.date(2026, 7, 16),
    )
    assert accepted.columns.tolist() == list(
        RICH.TUSHARE_CASH_CONVERSION_INCOME_COLUMNS
    )
    assert accepted["report_period"].tolist() == [
        pd.Timestamp("2023-12-31"),
        pd.Timestamp("2025-06-30"),
    ]
    assert quality == {
        "input_rows": 10,
        "non_target_company_rows_excluded": 1,
        "non_target_company_type_counts": {"2": 1},
        "target_company_periods_observed": 6,
        "adjustment_periods_excluded": 1,
        "no_type_one_periods_excluded": 1,
        "missing_metric_periods_excluded": 1,
        "ambiguous_type_one_periods_excluded": 1,
        "semantic_duplicate_rows_collapsed": 1,
        "accepted_periods": 2,
        "update_flag_counts": {"0": 1, "1": 9},
    }

    invalid = frame.copy()
    invalid.loc[0, "f_ann_date"] = None
    with pytest.raises(RICH.RichDataError, match="invalid statement keys"):
        RICH.canonicalize_tushare_cash_conversion_endpoint(
            invalid,
            endpoint="income",
            expected_ts_code="600519.SH",
            announcement_start=dt.date(2024, 1, 1),
            announcement_end=dt.date(2026, 6, 30),
            latest_actual_announcement_date=dt.date(2026, 7, 16),
        )


def test_tushare_cash_conversion_company_type_repair_only_excludes_complete_non_target_integers():
    frame = clean_cash_statement_frame("002961.SZ", "income")
    frame.loc[:, "comp_type"] = "7"

    with pytest.raises(RICH.RichDataError, match="unknown company types: \\[7\\]"):
        RICH.canonicalize_tushare_cash_conversion_endpoint(
            frame,
            endpoint="income",
            expected_ts_code="002961.SZ",
            announcement_start=dt.date(2024, 1, 1),
            announcement_end=dt.date(2026, 6, 30),
            latest_actual_announcement_date=dt.date(2026, 7, 16),
        )

    accepted, quality = RICH.canonicalize_tushare_cash_conversion_endpoint(
        frame,
        endpoint="income",
        expected_ts_code="002961.SZ",
        announcement_start=dt.date(2024, 1, 1),
        announcement_end=dt.date(2026, 6, 30),
        latest_actual_announcement_date=dt.date(2026, 7, 16),
        allow_complete_integer_non_target_company_type_codes=True,
    )
    assert accepted.empty
    assert quality["non_target_company_rows_excluded"] == len(frame)
    assert quality["non_target_company_type_counts"] == {"7": len(frame)}
    assert quality["accepted_periods"] == 0

    invalid = frame.copy()
    invalid.loc[0, "comp_type"] = "7.5"
    with pytest.raises(RICH.RichDataError, match="invalid statement keys"):
        RICH.canonicalize_tushare_cash_conversion_endpoint(
            invalid,
            endpoint="income",
            expected_ts_code="002961.SZ",
            announcement_start=dt.date(2024, 1, 1),
            announcement_end=dt.date(2026, 6, 30),
            latest_actual_announcement_date=dt.date(2026, 7, 16),
            allow_complete_integer_non_target_company_type_codes=True,
        )


def test_tushare_cash_conversion_join_uses_later_actual_date_and_positive_income():
    income_raw = clean_cash_statement_frame("600519.SH", "income", periods=4)
    income_raw.loc[:, "n_income_attr_p"] = [100.0, -10.0, 0.0, 50.0]
    cashflow_raw = clean_cash_statement_frame("600519.SH", "cashflow", periods=4)
    cashflow_raw.loc[:, "f_ann_date"] = [
        "20240402",
        "20240501",
        "20240831",
        "20241101",
    ]
    cashflow_raw.loc[:, "n_cashflow_act"] = [120.0, 30.0, -5.0, -20.0]
    income, _ = RICH.canonicalize_tushare_cash_conversion_endpoint(
        income_raw,
        endpoint="income",
        expected_ts_code="600519.SH",
        announcement_start=dt.date(2024, 1, 1),
        announcement_end=dt.date(2026, 6, 30),
        latest_actual_announcement_date=dt.date(2026, 7, 16),
    )
    cashflow, _ = RICH.canonicalize_tushare_cash_conversion_endpoint(
        cashflow_raw,
        endpoint="cashflow",
        expected_ts_code="600519.SH",
        announcement_start=dt.date(2024, 1, 1),
        announcement_end=dt.date(2026, 6, 30),
        latest_actual_announcement_date=dt.date(2026, 7, 16),
    )
    factors, quality = RICH.derive_tushare_cash_conversion(income, cashflow)
    assert factors.columns.tolist() == list(RICH.TUSHARE_CASH_CONVERSION_COLUMNS)
    assert factors["report_period"].tolist() == [
        pd.Timestamp("2023-12-31"),
        pd.Timestamp("2024-09-30"),
    ]
    assert factors["announcement_date"].tolist() == [
        pd.Timestamp("2024-04-02"),
        pd.Timestamp("2024-11-01"),
    ]
    assert factors["tushare_operating_cash_conversion"].tolist() == pytest.approx(
        [1.2, -0.4]
    )
    assert quality["nonpositive_income_periods_excluded"] == 2
    assert quality["nonfinite_cashflow_periods_excluded"] == 0
    assert quality["usable_joined_periods"] == 2


def test_tushare_cash_conversion_acceptance_publishes_only_factor_and_is_one_shot(
    tmp_path, monkeypatch
):
    contract = copy.deepcopy(RICH.load_tushare_cash_conversion_contract())
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(RICH, "load_tushare_cash_conversion_contract", lambda: contract)
    monkeypatch.setattr(
        RICH,
        "validate_tushare_cash_conversion_local_context",
        lambda value: {"fixture": {"path": "fixture", "sha256": "0" * 64}},
    )
    calls = []

    def fake_fetch(endpoint, symbol, announcement_start, announcement_end):
        calls.append((endpoint, symbol, announcement_start, announcement_end))
        return clean_cash_statement_frame(symbol, endpoint)

    monkeypatch.setattr(RICH, "fetch_tushare_cash_conversion_statement", fake_fetch)
    manifest_path = RICH.sync_tushare_cash_conversion_acceptance()
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["dataset"] == "tushare_cash_conversion_acceptance"
    assert manifest["acceptance_status"] == (
        "accepted_entitlement_schema_version_policy_and_formula_pending_full_history"
    )
    assert manifest["source_request"]["provider_calls_issued"] == 6
    assert manifest["source_quality"]["input_rows"] == 30
    assert manifest["source_quality"]["usable_joined_periods"] == 15
    assert manifest["source_quality"]["raw_statement_frames_persisted"] is False
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    assert len(manifest["files"]) == 1
    factor_frame = pd.read_parquet(
        RICH.resolve_record_path(manifest["files"][0]["path"])
    )
    assert factor_frame.columns.tolist() == list(RICH.TUSHARE_CASH_CONVERSION_COLUMNS)
    assert len(factor_frame) == 15
    assert len(calls) == 6

    with pytest.raises(RICH.RichDataError, match="one-shot.*already consumed"):
        RICH.sync_tushare_cash_conversion_acceptance()
    assert len(calls) == 6


def test_tushare_cash_conversion_acceptance_rejects_low_join_count_once(
    tmp_path, monkeypatch
):
    contract = copy.deepcopy(RICH.load_tushare_cash_conversion_contract())
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(RICH, "load_tushare_cash_conversion_contract", lambda: contract)
    monkeypatch.setattr(
        RICH,
        "validate_tushare_cash_conversion_local_context",
        lambda value: {"fixture": {"path": "fixture", "sha256": "0" * 64}},
    )
    calls = []

    def fake_fetch(endpoint, symbol, announcement_start, announcement_end):
        calls.append((endpoint, symbol))
        periods = 3 if symbol == "300750.SZ" else 5
        return clean_cash_statement_frame(symbol, endpoint, periods=periods)

    monkeypatch.setattr(RICH, "fetch_tushare_cash_conversion_statement", fake_fetch)
    with pytest.raises(RICH.RichDataError, match="too few usable joined periods"):
        RICH.sync_tushare_cash_conversion_acceptance()
    assert len(calls) == 6
    records = RICH.tushare_cash_conversion_acceptance_records()
    assert len(records) == 1
    rejection = RICH.json.loads(records[0].read_text())
    assert rejection["source_request"]["provider_calls_issued"] == 6
    assert rejection["files"] == []
    assert rejection["price_fields_loaded"] == []
    assert rejection["forward_return_fields_read"] is False

    with pytest.raises(RICH.RichDataError, match="one-shot.*already consumed"):
        RICH.sync_tushare_cash_conversion_acceptance()
    assert len(calls) == 6


def configure_cash_conversion_full_sync_fixture(tmp_path, monkeypatch):
    contract = copy.deepcopy(RICH.load_tushare_cash_conversion_contract())
    contract["full_snapshot_contract"]["minimum_seconds_between_calls"] = 0.0
    contract["full_snapshot_contract"]["maximum_attempts_per_symbol_endpoint"] = 1
    contract["no_return_gates"]["source_completeness"][
        "minimum_complete_joined_factor_events"
    ] = 1
    contract["no_return_gates"]["source_completeness"][
        "minimum_observed_signal_years"
    ] = 1
    universe_path = tmp_path / "buyable.txt"
    universe_path.write_text(
        "SH600519\t2019-01-01\t2025-12-31\n" "SZ000333\t2019-01-01\t2025-12-31\n",
        encoding="utf-8",
    )
    calendar_path = tmp_path / "day.txt"
    calendar_path.write_text(
        "2019-01-02\n"
        "2024-04-02\n"
        "2024-05-06\n"
        "2024-09-02\n"
        "2024-11-01\n"
        "2025-04-01\n"
        "2025-12-31\n"
        "2026-01-05\n"
        "2026-07-16\n",
        encoding="utf-8",
    )
    contract["local_context"]["holding_universe"] = {
        "path": str(universe_path),
        "sha256": RICH.file_digest(universe_path),
    }
    contract["local_context"]["calendar"] = {
        "path": str(calendar_path),
        "sha256": RICH.file_digest(calendar_path),
    }
    record_path = tmp_path / "acceptance_record.json"
    manifest_path = tmp_path / "acceptance_manifest.json"
    frame_path = tmp_path / "acceptance.parquet"
    record_path.write_text("{}\n", encoding="utf-8")
    manifest_path.write_text("{}\n", encoding="utf-8")
    acceptance_frame = pd.DataFrame(columns=RICH.TUSHARE_CASH_CONVERSION_COLUMNS)
    RICH.atomic_write_frame(acceptance_frame, frame_path)
    source_chain = {
        "contract": contract,
        "record_path": record_path,
        "manifest_path": manifest_path,
        "frame_path": frame_path,
        "frame": acceptance_frame,
    }
    monkeypatch.setattr(
        RICH, "load_tushare_cash_conversion_source_chain", lambda: source_chain
    )
    monkeypatch.setattr(
        RICH,
        "validate_tushare_cash_conversion_local_context",
        lambda value: {"fixture": {"path": "fixture", "sha256": "0" * 64}},
    )
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(RICH, "METADATA_ROOT", tmp_path / "metadata")
    monkeypatch.setattr(
        RICH,
        "DEFAULT_TUSHARE_CASH_CONVERSION_RESEARCH_RECORD",
        tmp_path / "no_terminal_cash_conversion_record.json",
    )
    return contract, universe_path, calendar_path


def test_tushare_cash_conversion_full_sync_is_atomic_pit_and_no_return(
    tmp_path, monkeypatch
):
    _, universe_path, calendar_path = configure_cash_conversion_full_sync_fixture(
        tmp_path, monkeypatch
    )
    calls = []

    def fake_fetch(endpoint, symbol, announcement_start, announcement_end):
        calls.append((endpoint, symbol, announcement_start, announcement_end))
        return clean_cash_statement_frame(symbol, endpoint)

    monkeypatch.setattr(RICH, "fetch_tushare_cash_conversion_statement", fake_fetch)
    manifest_path = RICH.sync_tushare_cash_conversion(
        allow_large=True,
        universe_path=universe_path,
        calendar_path=calendar_path,
    )
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["dataset"] == "tushare_operating_cash_conversion"
    assert manifest["acceptance_status"] == (
        "full_source_completeness_passed_pending_no_return_capacity_and_uniqueness"
    )
    assert manifest["source_request"]["planned_provider_calls"] == 4
    assert manifest["source_request"]["completed_provider_calls"] == 4
    assert manifest["source_request"]["raw_statement_frames_persisted"] is False
    assert manifest["source_completeness"]["complete_joined_factor_events"] == 10
    assert manifest["source_completeness"]["gate_passed_before_prices"] is True
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    assert [item["signal_year"] for item in manifest["files"]] == [2024, 2025]
    partition = pd.concat(
        [
            pd.read_parquet(RICH.resolve_record_path(item["path"]))
            for item in manifest["files"]
        ],
        ignore_index=True,
    )
    assert partition.columns.tolist() == list(RICH.TUSHARE_CASH_CONVERSION_COLUMNS)
    assert len(partition) == 10
    assert set(partition["instrument"]) == {"SH600519", "SZ000333"}
    assert len(calls) == 4

    with pytest.raises(RICH.RichDataError, match="already exists.*cannot be repeated"):
        RICH.sync_tushare_cash_conversion(
            allow_large=True,
            universe_path=universe_path,
            calendar_path=calendar_path,
        )
    assert len(calls) == 4


def test_tushare_cash_conversion_full_sync_deletes_partial_on_failure(
    tmp_path, monkeypatch
):
    _, universe_path, calendar_path = configure_cash_conversion_full_sync_fixture(
        tmp_path, monkeypatch
    )
    calls = []

    def fake_fetch(endpoint, symbol, announcement_start, announcement_end):
        calls.append((endpoint, symbol))
        if endpoint == "cashflow" and symbol == "000333.SZ":
            raise RICH.RichDataError("synthetic provider failure")
        return clean_cash_statement_frame(symbol, endpoint)

    monkeypatch.setattr(RICH, "fetch_tushare_cash_conversion_statement", fake_fetch)
    with pytest.raises(RICH.RichDataError, match="rejection_record"):
        RICH.sync_tushare_cash_conversion(
            allow_large=True,
            universe_path=universe_path,
            calendar_path=calendar_path,
        )
    assert len(calls) == 4
    failures = sorted((tmp_path / "runs").glob("*_source_failure.json"))
    assert len(failures) == 1
    failure = RICH.json.loads(failures[0].read_text())
    assert failure["failed_instrument"] == "SZ000333"
    assert failure["failed_endpoint"] == "cashflow"
    assert failure["completed_provider_calls_before_failure"] == 3
    assert failure["partial_snapshot_deleted"] is True
    assert failure["final_snapshot_published"] is False
    assert failure["price_fields_loaded"] == []
    assert failure["forward_return_fields_read"] is False
    snapshot_parent = tmp_path / "raw" / "tushare" / "cash_conversion" / "snapshots"
    assert not list(snapshot_parent.glob(".*.partial"))


def test_tushare_cash_conversion_company_type_repair_is_one_full_retry(
    tmp_path, monkeypatch
):
    _, universe_path, calendar_path = configure_cash_conversion_full_sync_fixture(
        tmp_path, monkeypatch
    )
    prior_failure_path = (
        tmp_path
        / "runs"
        / "20260716T141556Z_tushare_cash_conversion_full_b2e31205_source_failure.json"
    )
    prior_failure_path.parent.mkdir(parents=True)
    prior_failure_path.write_text(
        RICH.json.dumps(
            {
                "kind": "a_share_rich_data_source_failure",
                "dataset": "tushare_operating_cash_conversion",
                "run_id": "20260716T141556Z_tushare_cash_conversion_full_b2e31205",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    repair_path = RICH.DEFAULT_TUSHARE_CASH_CONVERSION_COMPANY_TYPE_REPAIR
    monkeypatch.setattr(
        RICH,
        "load_tushare_cash_conversion_company_type_repair",
        lambda: {
            "repair_path": repair_path,
            "repair": {
                "unchanged_source_protocol": {
                    "point_in_time_instrument_count": 2,
                    "provider_calls": 4,
                }
            },
            "failure_path": prior_failure_path,
            "failure": RICH.json.loads(prior_failure_path.read_text()),
        },
    )
    calls = []

    def fake_fetch(endpoint, symbol, announcement_start, announcement_end):
        calls.append((endpoint, symbol, announcement_start, announcement_end))
        frame = clean_cash_statement_frame(symbol, endpoint)
        if endpoint == "income" and symbol == "000333.SZ":
            frame.loc[0, "comp_type"] = "7"
        return frame

    monkeypatch.setattr(RICH, "fetch_tushare_cash_conversion_statement", fake_fetch)
    manifest_path = RICH.sync_tushare_cash_conversion(
        allow_large=True,
        universe_path=universe_path,
        calendar_path=calendar_path,
    )
    manifest = RICH.json.loads(manifest_path.read_text())
    repair = manifest["company_type_source_repair"]
    assert repair["full_from_scratch_restart"] is True
    assert repair["partial_snapshot_resumed"] is False
    assert repair["candidate_company_type"] == 1
    assert repair["complete_integer_non_target_company_types_excluded"] is True
    assert repair["bound_first_failure_path"] == RICH.manifest_path(
        prior_failure_path
    )
    assert manifest["source_request"]["completed_provider_calls"] == 4
    assert manifest["normalization_quality"][
        "non_target_company_type_counts_by_endpoint"
    ] == {"income": {"7": 1}, "cashflow": {}}
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    assert len(calls) == 4

    with pytest.raises(RICH.RichDataError, match="repair retry already exists"):
        RICH.sync_tushare_cash_conversion(
            allow_large=True,
            universe_path=universe_path,
            calendar_path=calendar_path,
        )
    assert len(calls) == 4


def test_tushare_cash_conversion_terminal_record_forbids_another_full_sync(
    tmp_path, monkeypatch
):
    record = RICH.load_tushare_cash_conversion_research_record()
    assert record["status"] == (
        "terminal_rejected_at_full_source_after_single_repair_retry"
    )
    assert record["source_gate"]["complete_full_snapshot_published"] is False
    assert record["downstream_gates"]["capacity_audit_run"] is False
    assert record["forward_return_fields_read"] is False

    monkeypatch.setattr(RICH, "METADATA_ROOT", tmp_path / "metadata")
    monkeypatch.setattr(
        RICH,
        "load_tushare_cash_conversion_source_chain",
        lambda: pytest.fail("terminal gate must run before source-chain loading"),
    )
    with pytest.raises(RICH.RichDataError, match="terminal.*forbidden"):
        RICH.sync_tushare_cash_conversion(allow_large=True)


def test_tushare_daily_pb_contract_is_fingerprint_frozen(tmp_path):
    contract = RICH.load_tushare_daily_pb_contract()
    assert contract["factor"]["name"] == "tushare_positive_book_to_market"
    assert contract["source"]["requested_fields"] == list(
        RICH.TUSHARE_DAILY_PB_RAW_FIELDS
    )
    assert contract["freeze_evidence"]["provider_daily_basic_rows_observed"] is False
    assert (
        contract["no_return_uniqueness_policy"][
            "maximum_allowed_absolute_median_daily_rank_correlation"
        ]
        == 0.8
    )
    assert contract["forward_return_fields_read"] is False

    changed = RICH.json.loads(RICH.DEFAULT_TUSHARE_DAILY_PB_CONTRACT.read_text())
    changed["factor"]["formula"] = "-pb"
    changed_path = tmp_path / "changed_daily_pb_contract.json"
    RICH.atomic_write_json(changed, changed_path)
    with pytest.raises(RICH.RichDataError, match="fingerprint mismatch"):
        RICH.load_tushare_daily_pb_contract(changed_path)

    assert (
        RICH.file_digest(RICH.DEFAULT_TUSHARE_DAILY_PB_CAPACITY_SPEC)
        == RICH.TUSHARE_DAILY_PB_CAPACITY_SPEC_SHA256
    )
    capacity_spec = RICH.json.loads(
        RICH.DEFAULT_TUSHARE_DAILY_PB_CAPACITY_SPEC.read_text()
    )
    assert capacity_spec["run_order"][1] == (
        "run_three_session_capacity_without_open_close_or_forward_returns"
    )
    assert capacity_spec["uniqueness_contract"]["comparison_field_count"] == 43
    assert (
        capacity_spec["no_return_gate_policy"][
            "capacity_must_run_before_close_known_comparison_fields"
        ]
        is True
    )


def test_tushare_daily_pb_request_uses_only_frozen_fields(monkeypatch):
    captured = {}

    class Pro:
        def daily_basic(self, **kwargs):
            captured.update(kwargs)
            return pd.DataFrame()

    monkeypatch.setattr(
        RICH,
        "_import_tushare",
        lambda: SimpleNamespace(pro_api=lambda: Pro()),
    )
    RICH.fetch_tushare_daily_pb(dt.date(2026, 7, 13))
    assert captured["trade_date"] == "20260713"
    assert captured["fields"].split(",") == list(RICH.TUSHARE_DAILY_PB_RAW_FIELDS)
    forbidden = set(
        RICH.load_tushare_daily_pb_contract()["source"]["explicitly_forbidden_fields"]
    )
    assert set(captured["fields"].split(",")).isdisjoint(forbidden)


def test_tushare_daily_pb_normalization_derives_positive_book_to_market():
    raw = pd.DataFrame(
        [
            {"ts_code": "600519.SH", "trade_date": "20260713", "pb": 2.5},
            {"ts_code": "832317.BJ", "trade_date": "20260713", "pb": 5.0},
            {"ts_code": "000001.SZ", "trade_date": "20260713", "pb": None},
            {"ts_code": "300750.SZ", "trade_date": "20260713", "pb": -1.0},
        ],
        columns=RICH.TUSHARE_DAILY_PB_RAW_FIELDS,
    )
    normalized, quality = RICH.canonicalize_tushare_daily_pb(
        raw, dt.date(2026, 7, 13), dt.date(2026, 7, 13)
    )
    assert normalized.columns.tolist() == list(RICH.TUSHARE_DAILY_PB_COLUMNS)
    assert normalized["instrument"].tolist() == ["BJ832317", "SH600519"]
    assert normalized["tushare_positive_book_to_market"].tolist() == pytest.approx(
        [0.2, 0.4]
    )
    assert quality == {
        "input_rows": 4,
        "missing_pb_rows_excluded": 1,
        "nonpositive_pb_rows_excluded": 1,
        "rows_written": 2,
    }
    assert not ({"close", "pe", "total_mv", "turnover_rate"} & set(normalized))


def test_tushare_daily_pb_acceptance_writes_current_coverage_snapshot(
    tmp_path, monkeypatch
):
    contract = RICH.json.loads(RICH.DEFAULT_TUSHARE_DAILY_PB_CONTRACT.read_text())
    contract["acceptance_protocol"]["minimum_all_market_source_rows"] = 2
    universe = tmp_path / "buyable.txt"
    universe.write_text(
        "SH600519\t2020-01-01\t2026-12-31\n" "SZ000001\t2020-01-01\t2026-12-31\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "load_tushare_daily_pb_contract", lambda: contract)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(
        RICH,
        "fetch_tushare_daily_pb",
        lambda trade_date: pd.DataFrame(
            [
                {"ts_code": "600519.SH", "trade_date": "20260713", "pb": 2.0},
                {"ts_code": "000001.SZ", "trade_date": "20260713", "pb": 1.0},
                {"ts_code": "688981.SH", "trade_date": "20260713", "pb": 4.0},
            ],
            columns=RICH.TUSHARE_DAILY_PB_RAW_FIELDS,
        ),
    )
    manifest_path = RICH.sync_tushare_daily_pb_acceptance(universe_path=universe)
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["dataset"] == "tushare_daily_pb_acceptance"
    assert manifest["acceptance_status"] == (
        "accepted_entitlement_formula_and_current_coverage_pending_full_history"
    )
    assert manifest["source_request"]["fields"] == list(
        RICH.TUSHARE_DAILY_PB_RAW_FIELDS
    )
    assert manifest["source_quality"]["positive_pb_holding_coverage"] == 1.0
    assert (
        manifest["source_quality"][
            "outside_point_in_time_holding_universe_rows_excluded"
        ]
        == 1
    )
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    stored = pd.read_parquet(RICH.resolve_record_path(manifest["files"][0]["path"]))
    assert stored.columns.tolist() == list(RICH.TUSHARE_DAILY_PB_COLUMNS)
    assert stored["instrument"].tolist() == ["SH600519", "SZ000001"]


def test_tushare_sw_industry_breadth_contract_is_fingerprint_frozen(tmp_path):
    contract = RICH.load_tushare_sw_industry_breadth_contract()
    assert contract["factor"]["name"] == "sw1_three_session_leave_one_out_breadth"
    assert contract["factor"]["stock_self_direction_included"] is False
    assert contract["factor"]["minimum_other_valid_peers_each_session"] == 10
    assert contract["source"]["membership_requested_fields"] == list(
        RICH.TUSHARE_SW_MEMBERSHIP_RAW_FIELDS
    )
    assert contract["freeze_evidence"]["index_member_all_rows_observed"] is False
    assert contract["forward_return_fields_read"] is False

    changed = RICH.json.loads(
        RICH.DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT.read_text()
    )
    changed["factor"]["three_session_formula"] = "mean of five sessions"
    changed_path = tmp_path / "changed_sw_industry_contract.json"
    RICH.atomic_write_json(changed, changed_path)
    with pytest.raises(RICH.RichDataError, match="fingerprint mismatch"):
        RICH.load_tushare_sw_industry_breadth_contract(changed_path)

    assert (
        RICH.file_digest(RICH.DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC)
        == RICH.TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC_SHA256
    )
    capacity_spec = RICH.json.loads(
        RICH.DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC.read_text()
    )
    assert capacity_spec["full_membership_snapshot"]["expected_provider_calls"] == 62
    assert (
        len(
            capacity_spec["combined_no_return_audit"]["uniqueness"][
                "comparison_factors"
            ]
        )
        == 45
    )
    assert (
        RICH.file_digest(RICH.DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_SYMBOL_REPAIR)
        == RICH.TUSHARE_SW_INDUSTRY_BREADTH_SYMBOL_REPAIR_SHA256
    )


def test_tushare_sw_requests_use_only_frozen_fields(monkeypatch):
    captured = []

    class Pro:
        def index_classify(self, **kwargs):
            captured.append(("classification", kwargs))
            return pd.DataFrame()

        def index_member_all(self, **kwargs):
            captured.append(("membership", kwargs))
            return pd.DataFrame()

    monkeypatch.setattr(
        RICH,
        "_import_tushare",
        lambda: SimpleNamespace(pro_api=lambda: Pro()),
    )
    RICH.fetch_tushare_sw_classification()
    RICH.fetch_tushare_sw_members("801010.SI", "N")
    assert captured[0][1] == {
        "level": "L1",
        "src": "SW2021",
        "fields": ",".join(RICH.TUSHARE_SW_CLASSIFICATION_RAW_FIELDS),
    }
    assert captured[1][1] == {
        "l1_code": "801010.SI",
        "is_new": "N",
        "fields": ",".join(RICH.TUSHARE_SW_MEMBERSHIP_RAW_FIELDS),
    }
    forbidden = set(
        RICH.load_tushare_sw_industry_breadth_contract()["source"][
            "explicitly_forbidden_fields"
        ]
    )
    assert set(captured[0][1]["fields"].split(",")).isdisjoint(forbidden)
    assert set(captured[1][1]["fields"].split(",")).isdisjoint(forbidden)


def test_tushare_sw_normalization_preserves_point_in_time_intervals():
    classification = RICH.canonicalize_tushare_sw_classification(
        pd.DataFrame(
            [
                {
                    "index_code": "801010.SI",
                    "industry_name": "农林牧渔",
                    "level": "L1",
                    "src": "SW2021",
                },
                {
                    "index_code": "801030.SI",
                    "industry_name": "基础化工",
                    "level": "L1",
                    "src": "SW2021",
                },
            ],
            columns=RICH.TUSHARE_SW_CLASSIFICATION_RAW_FIELDS,
        )
    )
    assert classification["index_code"].tolist() == ["801010.SI", "801030.SI"]

    raw = pd.DataFrame(
        [
            {
                "l1_code": "801010.SI",
                "l1_name": "农林牧渔",
                "l2_code": "801011.SI",
                "l2_name": "林业",
                "l3_code": "850111.SI",
                "l3_name": "种植业",
                "ts_code": "600519.SH",
                "in_date": "20190102",
                "out_date": "20200102",
                "is_new": "N",
            }
        ],
        columns=RICH.TUSHARE_SW_MEMBERSHIP_RAW_FIELDS,
    )
    normalized, quality = RICH.canonicalize_tushare_sw_members(
        raw, expected_l1_code="801010.SI", expected_is_new="N"
    )
    assert normalized.columns.tolist() == list(RICH.TUSHARE_SW_MEMBERSHIP_COLUMNS)
    assert normalized["instrument"].tolist() == ["SH600519"]
    assert normalized["in_date"].dt.strftime("%Y-%m-%d").tolist() == ["2019-01-02"]
    assert normalized["out_date"].dt.strftime("%Y-%m-%d").tolist() == ["2020-01-02"]
    assert quality == {
        "input_rows": 1,
        "rows_written": 1,
        "missing_out_date_rows": 0,
        "unsupported_provider_symbol_rows_excluded": 0,
    }
    assert not ({"name", "close", "amount", "pb"} & set(normalized.columns))

    unsupported = raw.copy()
    unsupported.loc[0, "ts_code"] = "T00018.SH"
    excluded, excluded_quality = RICH.canonicalize_tushare_sw_members(
        unsupported, expected_l1_code="801010.SI", expected_is_new="N"
    )
    assert excluded.empty
    assert excluded_quality["unsupported_provider_symbol_rows_excluded"] == 1
    assert excluded_quality["rows_written"] == 0

    bad = raw.copy()
    bad.loc[0, "out_date"] = None
    with pytest.raises(RICH.RichDataError, match="lacks out_date"):
        RICH.canonicalize_tushare_sw_members(
            bad, expected_l1_code="801010.SI", expected_is_new="N"
        )


def test_tushare_sw_acceptance_writes_no_price_membership_snapshot(
    tmp_path, monkeypatch
):
    contract = RICH.json.loads(
        RICH.DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT.read_text()
    )
    context_file = tmp_path / "context.txt"
    context_file.write_text("frozen\n", encoding="utf-8")
    context_sha = RICH.file_digest(context_file)
    for link in contract["local_context"].values():
        link["path"] = str(context_file)
        link["sha256"] = context_sha
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(
        RICH, "load_tushare_sw_industry_breadth_contract", lambda: contract
    )
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    classification_rows = [
        {
            "index_code": "801010.SI" if index == 0 else f"{801010 + index:06d}.SI",
            "industry_name": f"行业{index}",
            "level": "L1",
            "src": "SW2021",
        }
        for index in range(25)
    ]
    monkeypatch.setattr(
        RICH,
        "fetch_tushare_sw_classification",
        lambda: pd.DataFrame(
            classification_rows, columns=RICH.TUSHARE_SW_CLASSIFICATION_RAW_FIELDS
        ),
    )

    def member_row(code, *, is_new, position):
        return {
            "l1_code": "801010.SI",
            "l1_name": "农林牧渔",
            "l2_code": "801011.SI",
            "l2_name": "林业",
            "l3_code": "850111.SI",
            "l3_name": "种植业",
            "ts_code": code,
            "in_date": "20190102",
            "out_date": None if is_new == "Y" else "20200102",
            "is_new": is_new,
        }

    def fake_members(l1_code, is_new):
        if is_new == "Y":
            rows = [
                member_row(f"{600000 + index:06d}.SH", is_new="Y", position=index)
                for index in range(20)
            ]
        else:
            rows = [member_row("600999.SH", is_new="N", position=0)]
        return pd.DataFrame(rows, columns=RICH.TUSHARE_SW_MEMBERSHIP_RAW_FIELDS)

    monkeypatch.setattr(RICH, "fetch_tushare_sw_members", fake_members)
    manifest_path = RICH.sync_tushare_sw_industry_breadth_acceptance()
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["dataset"] == "tushare_sw2021_l1_acceptance"
    assert manifest["acceptance_status"] == (
        "accepted_entitlement_schema_and_point_in_time_intervals_"
        "pending_full_membership_snapshot"
    )
    assert manifest["source_quality"]["classification_rows"] == 25
    assert manifest["source_quality"]["membership_rows"] == 21
    assert manifest["price_fields_loaded"] == []
    assert manifest["factor_values_constructed"] is False
    assert manifest["forward_return_fields_read"] is False
    stored = {
        item["dataset"]: pd.read_parquet(RICH.resolve_record_path(item["path"]))
        for item in manifest["files"]
    }
    assert stored["classification"].columns.tolist() == list(
        RICH.TUSHARE_SW_CLASSIFICATION_RAW_FIELDS
    )
    assert stored["membership"].columns.tolist() == list(
        RICH.TUSHARE_SW_MEMBERSHIP_COLUMNS
    )
    assert not ({"name", "close", "amount", "return"} & set(stored["membership"]))


def test_tushare_sw_full_membership_sync_is_atomic_and_no_price(tmp_path, monkeypatch):
    with pytest.raises(RICH.RichDataError, match="requires --allow-large"):
        RICH.sync_tushare_sw_industry_membership(allow_large=False)

    spec = copy.deepcopy(
        RICH.json.loads(
            RICH.DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CAPACITY_SPEC.read_text()
        )
    )
    spec["full_membership_snapshot"]["minimum_seconds_between_calls"] = 0
    contract = RICH.json.loads(
        RICH.DEFAULT_TUSHARE_SW_INDUSTRY_BREADTH_CONTRACT.read_text()
    )
    spec_path = tmp_path / "capacity_spec.json"
    record_path = tmp_path / "acceptance_record.json"
    acceptance_manifest_path = tmp_path / "acceptance_manifest.json"
    symbol_repair_path = tmp_path / "symbol_repair.json"
    for path in (
        spec_path,
        record_path,
        acceptance_manifest_path,
        symbol_repair_path,
    ):
        path.write_text("{}\n", encoding="utf-8")
    classification = pd.DataFrame(
        [
            {
                "index_code": code,
                "industry_name": f"行业{index}",
                "level": "L1",
                "src": "SW2021",
            }
            for index, code in enumerate(
                spec["full_membership_snapshot"]["classification_codes"]
            )
        ],
        columns=RICH.TUSHARE_SW_CLASSIFICATION_RAW_FIELDS,
    )
    accepted_membership = pd.DataFrame(columns=RICH.TUSHARE_SW_MEMBERSHIP_COLUMNS)
    monkeypatch.setattr(
        RICH,
        "load_tushare_sw_industry_breadth_source_chain",
        lambda: {
            "spec_path": spec_path,
            "spec": spec,
            "contract": contract,
            "record_path": record_path,
            "record": {},
            "manifest_path": acceptance_manifest_path,
            "manifest": {"run_id": "accepted-sw"},
            "classification": classification,
            "membership": accepted_membership,
            "context_paths": {},
            "symbol_repair_path": symbol_repair_path,
            "symbol_repair": {},
        },
    )
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(RICH, "METADATA_ROOT", tmp_path / "metadata")
    monkeypatch.setattr(
        RICH,
        "new_run_id",
        lambda prefix: "20260716T120000Z_tushare_sw2021_l1_membership_test",
    )
    calls = []

    def fake_fetch(l1_code, is_new):
        calls.append((l1_code, is_new))
        return pd.DataFrame(
            [
                {
                    "l1_code": l1_code,
                    "l1_name": f"行业{l1_code}",
                    "l2_code": "801011.SI",
                    "l2_name": "二级行业",
                    "l3_code": "850111.SI",
                    "l3_name": "三级行业",
                    "ts_code": "600519.SH",
                    "in_date": "20200101" if is_new == "Y" else "20100101",
                    "out_date": None if is_new == "Y" else "20191231",
                    "is_new": is_new,
                }
            ],
            columns=RICH.TUSHARE_SW_MEMBERSHIP_RAW_FIELDS,
        )

    monkeypatch.setattr(RICH, "fetch_tushare_sw_members", fake_fetch)
    manifest_path = RICH.sync_tushare_sw_industry_membership(allow_large=True)
    manifest = RICH.json.loads(manifest_path.read_text())
    assert len(calls) == 62
    assert calls[0] == ("801010.SI", "Y")
    assert calls[-1] == ("801980.SI", "N")
    assert manifest["dataset"] == "tushare_sw2021_l1_membership"
    assert manifest["source_acceptance"]["run_id"] == "accepted-sw"
    assert manifest["source_request"]["completed_provider_calls"] == 62
    assert manifest["source_request"]["fields"] == list(
        RICH.TUSHARE_SW_MEMBERSHIP_RAW_FIELDS
    )
    assert manifest["source_quality"]["membership_rows"] == 62
    assert manifest["source_quality"]["current_membership_rows"] == 31
    assert manifest["source_quality"]["historical_membership_rows"] == 31
    assert manifest["source_quality"]["unsupported_provider_symbol_rows_excluded"] == 0
    assert manifest["source_quality"]["duplicate_interval_rows"] == 0
    assert manifest["acceptance_status"] == (
        "full_membership_snapshot_passed_pending_no_return_factor_capacity_and_uniqueness"
    )
    assert manifest["price_fields_loaded"] == []
    assert manifest["factor_values_constructed"] is False
    assert manifest["forward_return_fields_read"] is False
    stored = RICH.load_snapshot_frame(manifest["files"][0])
    assert stored.columns.tolist() == list(RICH.TUSHARE_SW_MEMBERSHIP_COLUMNS)
    assert len(stored) == 62
    assert not ({"price", "open", "close", "return"} & set(stored.columns))
    assert not list((tmp_path / "raw").rglob("*.partial"))


def test_tushare_daily_pb_sync_writes_immutable_no_return_snapshot(
    tmp_path, monkeypatch
):
    contract = RICH.json.loads(RICH.DEFAULT_TUSHARE_DAILY_PB_CONTRACT.read_text())
    contract["snapshot_contract"]["development_start"] = "2024-04-29"
    contract["snapshot_contract"]["development_end"] = "2024-04-30"
    contract["snapshot_contract"]["partition_policy"][
        "minimum_seconds_between_calls"
    ] = 0
    universe = tmp_path / "buyable.txt"
    universe.write_text(
        "SH600519\t2020-01-01\t2025-12-31\n" "SZ000001\t2020-01-01\t2025-12-31\n",
        encoding="utf-8",
    )
    calendar = tmp_path / "day.txt"
    calendar.write_text("2024-04-29\n2024-04-30\n", encoding="utf-8")
    monkeypatch.setattr(RICH, "load_tushare_daily_pb_contract", lambda: contract)
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(RICH, "validate_range", lambda *args, **kwargs: None)
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(RICH, "METADATA_ROOT", tmp_path / "metadata")
    spec_path = tmp_path / "capacity_spec.json"
    record_path = tmp_path / "acceptance_record.json"
    acceptance_manifest_path = tmp_path / "acceptance_manifest.json"
    frame_path = tmp_path / "acceptance.parquet"
    spec_path.write_text("{}\n", encoding="utf-8")
    record_path.write_text("{}\n", encoding="utf-8")
    acceptance_manifest_path.write_text("{}\n", encoding="utf-8")
    frame_path.write_bytes(b"test-only")
    monkeypatch.setattr(
        RICH,
        "load_tushare_daily_pb_source_chain",
        lambda: {
            "spec_path": spec_path,
            "spec": {"preregistered_at": "2026-07-16T10:05:41Z"},
            "record_path": record_path,
            "record": {},
            "manifest_path": acceptance_manifest_path,
            "manifest": {
                "run_id": "accepted-pb",
                "files": [{"sha256": "acceptance-frame-content"}],
            },
            "frame_path": frame_path,
        },
    )

    def fake_fetch(trade_date):
        return pd.DataFrame(
            [
                {
                    "ts_code": "600519.SH",
                    "trade_date": trade_date.strftime("%Y%m%d"),
                    "pb": 2.0,
                },
                {
                    "ts_code": "000001.SZ",
                    "trade_date": trade_date.strftime("%Y%m%d"),
                    "pb": 1.0,
                },
            ],
            columns=RICH.TUSHARE_DAILY_PB_RAW_FIELDS,
        )

    monkeypatch.setattr(RICH, "fetch_tushare_daily_pb", fake_fetch)
    manifest_path = RICH.sync_tushare_daily_pb(
        allow_large=True,
        universe_path=universe,
        calendar_path=calendar,
    )
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["dataset"] == "tushare_daily_pb"
    assert manifest["source_request"]["fields"] == list(
        RICH.TUSHARE_DAILY_PB_RAW_FIELDS
    )
    assert manifest["source_request"]["credentials_logged_or_stored"] is False
    assert manifest["source_acceptance"]["run_id"] == "accepted-pb"
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    assert manifest["acceptance_status"] == (
        "full_source_coverage_failed_stop_before_uniqueness_capacity_or_prices"
    )
    stored = pd.read_parquet(RICH.resolve_record_path(manifest["files"][0]["path"]))
    assert stored.columns.tolist() == list(RICH.TUSHARE_DAILY_PB_COLUMNS)
    assert len(stored) == 4
    assert stored["tushare_positive_book_to_market"].tolist() == pytest.approx(
        [0.5, 1.0, 0.5, 1.0]
    )
    assert not list((tmp_path / "raw").rglob("*.partial"))


def test_canonicalize_minutes_handles_provider_column_names_and_sorts_rows():
    raw = pd.DataFrame(
        {
            "trade_time": [
                "2026-07-13 09:31:00",
                "2026-07-13 09:30:00",
                "2026-07-13 09:30:00",
            ],
            "open": [10.1, 10.0, 10.0],
            "high": [10.2, 10.1, 10.1],
            "low": [10.0, 9.9, 9.9],
            "close": [10.15, 10.05, 10.04],
            "vol": [200, 100, 101],
            "money": [2030, 1005, 1014],
        }
    )
    normalized = RICH.canonicalize_minute_bars(
        raw, "tushare", "600519", dt.date(2026, 7, 13), dt.date(2026, 7, 13)
    )
    assert normalized["datetime"].dt.strftime("%H:%M:%S").tolist() == [
        "09:30:00",
        "09:31:00",
    ]
    assert normalized["close"].tolist() == pytest.approx([10.04, 10.15])
    assert normalized["symbol"].tolist() == ["SH600519", "SH600519"]
    assert normalized["amount"].tolist() == pytest.approx([1014.0, 2030.0])


def test_canonicalize_minutes_rejects_invalid_ohlc():
    raw = pd.DataFrame(
        {
            "datetime": ["2026-07-13 09:30:00"],
            "open": [10.0],
            "high": [9.0],
            "low": [9.5],
            "close": [9.8],
            "volume": [100.0],
            "amount": [1000.0],
        }
    )
    with pytest.raises(RICH.RichDataError, match="invalid minute bars"):
        RICH.canonicalize_minute_bars(
            raw, "rqdata", "000001", dt.date(2026, 7, 13), dt.date(2026, 7, 13)
        )


def test_minute_acceptance_reconciles_only_against_raw_daily_fields(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(RICH, "DAILY_RAW_DIR", tmp_path / "daily")
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2026-07-13 09:31:00", "2026-07-13 09:32:00"]),
            "symbol": ["SH600519", "SH600519"],
            "source_symbol": ["600519.SH", "600519.SH"],
            "open": [10.0, 10.1],
            "high": [10.15, 10.3],
            "low": [9.8, 10.0],
            "close": [10.1, 10.1],
            "volume": [1.0, 2.0],
            "amount": [10.0, 20.0],
            "provider": ["tushare", "tushare"],
        }
    )
    (tmp_path / "daily").mkdir()
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-13"]),
            "symbol": ["SH600519"],
            "open": [20.0],
            "high": [20.6],
            "low": [19.6],
            "close": [20.2],
            "volume": [1.5],
            "amount": [30.0],
            "raw_open": [10.0],
            "raw_high": [10.3],
            "raw_low": [9.8],
            "raw_close": [10.1],
            "raw_volume": [3.0],
            "price_basis": [RICH.REQUIRED_DAILY_PRICE_BASIS],
        }
    ).to_parquet(tmp_path / "daily" / "sh600519.parquet", index=False)
    report = RICH.minute_acceptance_report(frame)
    assert report["status"] == "automatic_checks_passed_pending_time_alignment"
    assert (
        report["daily_reconciliation"]["daily_price_basis"]
        == "raw_unadjusted_to_raw_daily"
    )
    assert report["daily_reconciliation"]["days"][0]["inferred_volume_unit"] == "lots"


def test_minute_session_check_rejects_lunch_break_timestamp():
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2026-07-13 12:00:00"]),
            "symbol": ["SH600519"],
            "open": [10.0],
            "high": [10.0],
            "low": [10.0],
            "close": [10.0],
            "volume": [1.0],
            "amount": [10.0],
        }
    )
    assert RICH.minute_session_check(frame)["status"] == "failed"


def test_tushare_minute_request_uses_explicit_session_timestamps(monkeypatch):
    captured = {}

    class FakeTushare:
        @staticmethod
        def pro_bar(**kwargs):
            captured.update(kwargs)
            return pd.DataFrame()

    monkeypatch.setattr(RICH, "_import_tushare", lambda: FakeTushare())
    RICH.fetch_tushare_minutes(
        "600519", dt.date(2026, 7, 13), dt.date(2026, 7, 13), "1m"
    )
    assert captured["start_date"] == "2026-07-13 09:00:00"
    assert captured["end_date"] == "2026-07-13 17:00:00"


def test_tushare_event_defaults_fit_3000_points_and_record_raw_duplicates(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "metadata" / "runs")
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    monkeypatch.setattr(
        RICH, "new_run_id", lambda prefix: "20260716T000000Z_tushare_events_test"
    )

    def fake_fetch(dataset, trade_date):
        row = {"trade_date": "20260713", "ts_code": "600519.SH"}
        if dataset == "top-list":
            row["reason"] = "test reason"
            return pd.DataFrame([row, row])
        return pd.DataFrame([row])

    monkeypatch.setattr(RICH, "fetch_tushare_event", fake_fetch)
    parser = RICH.build_parser()
    args = parser.parse_args(
        ["sync-tushare-events", "--start", "2026-07-13", "--end", "2026-07-13"]
    )
    assert args.datasets == ",".join(RICH.DEFAULT_EVENT_DATASETS)
    assert (
        max(
            RICH.TUSHARE_EVENT_PERMISSION_POINTS[name]
            for name in RICH.DEFAULT_EVENT_DATASETS
        )
        == 3_000
    )

    manifest_path = RICH.sync_tushare_events(
        list(RICH.DEFAULT_EVENT_DATASETS),
        dt.date(2026, 7, 13),
        dt.date(2026, 7, 13),
        False,
    )
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["requested_datasets"] == list(RICH.DEFAULT_EVENT_DATASETS)
    assert manifest["source_quality"]["source_rows"] == 5
    assert manifest["source_quality"]["exact_duplicate_rows"] == 1
    assert manifest["source_quality"]["duplicate_event_key_rows"] == 1
    assert (
        manifest["source_quality"]["raw_rows_preserved_without_deduplication"] is True
    )
    assert (
        manifest["acceptance_status"]
        == "pending_event_time_alignment_and_canonicalization"
    )
    assert manifest["forward_return_fields_read"] is False
    assert manifest["selection_or_promotion_allowed"] is False
    top_list_file = next(
        item for item in manifest["files"] if item["dataset"] == "top-list"
    )
    assert (
        top_list_file["quality"]["status"]
        == "raw_duplicates_present_pending_canonicalization"
    )
    assert len(pd.read_parquet(top_list_file["path"])) == 2
    assert not list((tmp_path / "raw").rglob("*.tmp"))


def test_tushare_event_failure_removes_temporary_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "metadata" / "runs")
    monkeypatch.setattr(RICH, "require_provider", lambda provider: None)
    run_id = "20260716T000001Z_tushare_events_failure"
    monkeypatch.setattr(RICH, "new_run_id", lambda prefix: run_id)

    def fake_fetch(dataset, trade_date):
        if dataset == "limit-price":
            raise RICH.RichDataError("provider permission denied")
        return pd.DataFrame([{"trade_date": "20260713", "ts_code": "600519.SH"}])

    monkeypatch.setattr(RICH, "fetch_tushare_event", fake_fetch)
    with pytest.raises(RICH.RichDataError, match="permission denied"):
        RICH.sync_tushare_events(
            ["moneyflow", "limit-price"],
            dt.date(2026, 7, 13),
            dt.date(2026, 7, 13),
            False,
        )
    snapshot_parent = tmp_path / "raw" / "tushare" / "events" / "snapshots"
    assert not (snapshot_parent / run_id).exists()
    assert not (snapshot_parent / f".{run_id}.tmp").exists()
    assert not (tmp_path / "metadata" / "runs" / f"{run_id}.json").exists()


def test_validate_range_requires_completed_session_and_large_request_confirmation():
    completed = RICH.latest_completed_session_date()
    with pytest.raises(RICH.RichDataError, match="not a completed"):
        future = completed + dt.timedelta(days=1)
        RICH.validate_range(future, future, False)
    with pytest.raises(RICH.RichDataError, match="allow-large"):
        RICH.validate_range(
            dt.date(2026, 1, 1), dt.date(2026, 7, 13), False, unit_count=4
        )


def test_snapshot_write_records_checksum_and_minute_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "metadata" / "runs")
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2026-07-13 09:30:00", "2026-07-13 09:31:00"]),
            "symbol": ["SH600519", "SH600519"],
            "source_symbol": ["600519.SH", "600519.SH"],
            "open": [10.0, 10.1],
            "high": [10.1, 10.2],
            "low": [9.9, 10.0],
            "close": [10.05, 10.15],
            "volume": [100.0, 200.0],
            "amount": [1005.0, 2030.0],
            "provider": ["tushare", "tushare"],
        }
    )
    manifest_path = RICH.write_minute_snapshot(
        "tushare", "1m", dt.date(2026, 7, 13), dt.date(2026, 7, 13), {"600519": frame}
    )
    manifest = RICH.json.loads(manifest_path.read_text())
    assert manifest["prices"] == "raw_unadjusted"
    assert manifest["files"][0]["rows"] == 2
    assert len(manifest["files"][0]["sha256"]) == 64
    assert manifest["files"][0]["daily_summary"][0]["bars"] == 2


def test_expected_minute_times_are_exact_for_start_and_end_labels():
    start = RICH.expected_minute_times("start")
    end = RICH.expected_minute_times("end")
    assert len(start) == len(end) == 240
    assert (start[0], start[119], start[120], start[-1]) == (
        dt.time(9, 30),
        dt.time(11, 29),
        dt.time(13, 0),
        dt.time(14, 59),
    )
    assert (end[0], end[119], end[120], end[-1]) == (
        dt.time(9, 31),
        dt.time(11, 30),
        dt.time(13, 1),
        dt.time(15, 0),
    )
    five_start = RICH.expected_minute_times("start", "5m")
    five_end = RICH.expected_minute_times("end", "5m")
    assert len(five_start) == len(five_end) == 48
    assert (five_start[0], five_start[23], five_start[24], five_start[-1]) == (
        dt.time(9, 30),
        dt.time(11, 25),
        dt.time(13, 0),
        dt.time(14, 55),
    )
    assert (five_end[0], five_end[23], five_end[24], five_end[-1]) == (
        dt.time(9, 35),
        dt.time(11, 30),
        dt.time(13, 5),
        dt.time(15, 0),
    )


def test_baostock_5m_acceptance_requires_exact_end_label_grid(monkeypatch):
    contract = RICH.load_baostock_5m_contract()
    times = RICH.expected_minute_times("end", "5m")
    frame = pd.DataFrame(
        {
            "datetime": [
                pd.Timestamp.combine(dt.date(2026, 7, 10), value) for value in times
            ],
            "symbol": "SH600519",
            "source_symbol": "sh.600519",
            "open": 10.0,
            "high": 10.0,
            "low": 10.0,
            "close": 10.0,
            "volume": 100.0,
            "amount": 1000.0,
            "provider": "baostock",
        }
    )
    monkeypatch.setattr(
        RICH,
        "minute_daily_reconciliation",
        lambda source: {"status": "passed", "days": [{"status": "passed"}]},
    )
    accepted = RICH.baostock_5m_acceptance_report(frame, contract)
    assert accepted["status"] == "automatic_checks_passed_pending_time_alignment"
    assert accepted["baostock_5m_contract"]["exact_timestamp_grid_passed"] is True
    rejected = RICH.baostock_5m_acceptance_report(frame.iloc[:-1], contract)
    assert rejected["status"] == "automatic_checks_failed"
    assert rejected["baostock_5m_contract"]["exact_timestamp_grid_passed"] is False


def test_baostock_5m_full_sync_stops_at_disk_gate_before_downloader(
    tmp_path, monkeypatch
):
    universe = tmp_path / "universe.txt"
    universe.write_text("SH600519\t2020-01-02\t2020-01-07\n", encoding="utf-8")
    calendar = tmp_path / "calendar.txt"
    calendar.write_text(
        "2020-01-02\n2020-01-03\n2020-01-06\n2020-01-07\n", encoding="utf-8"
    )
    called = False

    def forbidden_download(tasks, workers):
        nonlocal called
        called = True
        return iter(())

    monkeypatch.setattr(RICH, "require_baostock_5m_runtime", lambda: None)
    monkeypatch.setattr(
        RICH,
        "load_baostock_5m_restoration_probe",
        lambda data_root: (
            RICH.DEFAULT_BAOSTOCK_5M_THROTTLE_AUDIT,
            {"status": "passed_for_bulk_retry", "created_at": "2026-07-14T22:00:00Z"},
        ),
    )
    monkeypatch.setattr(RICH, "BAOSTOCK_5M_MINIMUM_FREE_BYTES", 10**30)
    monkeypatch.setattr(RICH, "download_baostock_5m_requests", forbidden_download)
    with pytest.raises(RICH.RichDataError, match="before any network request"):
        RICH.sync_baostock_5m_history(
            allow_large=True,
            data_root=tmp_path / "external",
            universe_path=universe,
            calendar_path=calendar,
        )
    assert called is False


def test_baostock_5m_full_sync_is_external_atomic_and_no_return(tmp_path, monkeypatch):
    dates = ["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"]
    universe = tmp_path / "universe.txt"
    universe.write_text("SH600519\t2020-01-02\t2020-01-07\n", encoding="utf-8")
    calendar = tmp_path / "calendar.txt"
    calendar.write_text("\n".join(dates) + "\n", encoding="utf-8")
    frame = complete_baostock_5m_frame(dates)
    chain = permissive_baostock_source_chain()
    monkeypatch.setattr(RICH, "load_baostock_5m_source_chain", lambda path: chain)
    monkeypatch.setattr(RICH, "require_baostock_5m_runtime", lambda: None)
    monkeypatch.setattr(
        RICH,
        "load_baostock_5m_restoration_probe",
        lambda data_root: (
            RICH.DEFAULT_BAOSTOCK_5M_THROTTLE_AUDIT,
            {"status": "passed_for_bulk_retry", "created_at": "2026-07-14T22:00:00Z"},
        ),
    )
    monkeypatch.setattr(RICH, "BAOSTOCK_5M_MINIMUM_FREE_BYTES", 1)
    monkeypatch.setattr(RICH.importlib.metadata, "version", lambda package: "0.9.3")
    monkeypatch.setattr(
        RICH,
        "download_baostock_5m_requests",
        lambda tasks, workers: iter([("600519", "2020-01-02", "2020-01-07", frame)]),
    )
    data_root = tmp_path / "external"
    manifest_path = RICH.sync_baostock_5m_history(
        allow_large=True,
        data_root=data_root,
        universe_path=universe,
        calendar_path=calendar,
    )
    manifest = RICH.json.loads(manifest_path.read_text())
    stored = Path(manifest["files"][0]["path"])
    assert manifest_path.is_relative_to(data_root)
    assert stored.is_relative_to(data_root)
    assert stored.exists()
    assert manifest["rows"] == 4 * 48
    assert manifest["normalization_quality"] == {
        "source_rows": 4 * 48,
        "rows_written": 4 * 48,
        "zero_price_placeholder_rows_excluded": 0,
        "zero_price_placeholder_sessions": 0,
    }
    assert manifest["coverage"]["gate_passed_before_prices"] is True
    assert manifest["forward_return_fields_read"] is False
    assert manifest["daily_or_forward_return_fields_read"] is False
    assert manifest["selection_or_promotion_allowed"] is False
    assert not list(data_root.rglob("*.partial"))


def test_baostock_5m_full_sync_deletes_partial_snapshot_on_partition_failure(
    tmp_path, monkeypatch
):
    universe = tmp_path / "universe.txt"
    universe.write_text("SH600519\t2020-01-02\t2020-01-07\n", encoding="utf-8")
    calendar = tmp_path / "calendar.txt"
    calendar.write_text(
        "2020-01-02\n2020-01-03\n2020-01-06\n2020-01-07\n", encoding="utf-8"
    )
    chain = permissive_baostock_source_chain()

    def failed_download(tasks, workers):
        raise RICH.RichDataError("simulated partition failure")
        yield  # pragma: no cover

    monkeypatch.setattr(RICH, "load_baostock_5m_source_chain", lambda path: chain)
    monkeypatch.setattr(RICH, "require_baostock_5m_runtime", lambda: None)
    monkeypatch.setattr(
        RICH,
        "load_baostock_5m_restoration_probe",
        lambda data_root: (
            RICH.DEFAULT_BAOSTOCK_5M_THROTTLE_AUDIT,
            {"status": "passed_for_bulk_retry", "created_at": "2026-07-14T22:00:00Z"},
        ),
    )
    monkeypatch.setattr(RICH, "BAOSTOCK_5M_MINIMUM_FREE_BYTES", 1)
    monkeypatch.setattr(RICH, "download_baostock_5m_requests", failed_download)
    monkeypatch.setattr(RICH, "new_run_id", lambda prefix: "fixed-failed-run")
    data_root = tmp_path / "external"
    with pytest.raises(RICH.RichDataError, match="simulated partition failure"):
        RICH.sync_baostock_5m_history(
            allow_large=True,
            data_root=data_root,
            universe_path=universe,
            calendar_path=calendar,
        )
    snapshots = (
        data_root
        / "raw"
        / "a_share"
        / "rich"
        / "baostock"
        / "minutes"
        / "5m"
        / "snapshots"
    )
    assert not snapshots.exists() or not list(snapshots.iterdir())
    assert list((data_root / "metadata" / "rich_data" / "preflights").glob("*.json"))


def test_frozen_minute_factor_spec_rejects_direction_changes(tmp_path):
    spec = RICH.load_minute_factor_spec()
    assert tuple(item["name"] for item in spec["features"]) == RICH.MINUTE_FEATURE_NAMES
    changed = RICH.json.loads(RICH.DEFAULT_MINUTE_FACTOR_SPEC.read_text())
    changed["features"][0]["diagnostic_direction"] = "lower"
    changed_path = tmp_path / "changed_spec.json"
    RICH.atomic_write_json(changed, changed_path)
    with pytest.raises(RICH.RichDataError, match="frozen v1"):
        RICH.load_minute_factor_spec(changed_path)


def test_frozen_baostock_5m_factor_spec_rejects_direction_changes(tmp_path):
    spec = RICH.load_baostock_5m_factor_spec()
    assert (
        tuple(item["name"] for item in spec["features"])
        == RICH.BAOSTOCK_5M_FEATURE_NAMES
    )
    assert tuple(item["diagnostic_direction"] for item in spec["features"]) == (
        RICH.BAOSTOCK_5M_FEATURE_DIRECTIONS
    )
    assert spec["minute_contract"]["expected_regular_session_bars"] == 48
    assert spec["forward_return_fields_read"] is False
    changed = RICH.json.loads(RICH.DEFAULT_BAOSTOCK_5M_FACTOR_SPEC.read_text())
    changed["features"][0]["diagnostic_direction"] = "lower"
    changed_path = tmp_path / "changed_5m_spec.json"
    RICH.atomic_write_json(changed, changed_path)
    with pytest.raises(RICH.RichDataError, match="fingerprint mismatch"):
        RICH.load_baostock_5m_factor_spec(changed_path)


def test_alignment_confirmation_requires_review_and_matching_semantics(tmp_path):
    frame = complete_minute_frame()
    snapshot_path = write_accepted_snapshot(tmp_path, frame)
    original_snapshot = snapshot_path.read_bytes()
    output = tmp_path / "alignment.json"

    with pytest.raises(RICH.RichDataError, match="reviewed-boundaries"):
        RICH.confirm_minute_alignment(
            snapshot_path,
            bar_label="end",
            volume_unit="shares",
            reviewed_boundaries=False,
            output=output,
        )
    with pytest.raises(RICH.RichDataError, match="conflicts"):
        RICH.confirm_minute_alignment(
            snapshot_path,
            bar_label="start",
            volume_unit="shares",
            reviewed_boundaries=True,
            output=output,
        )
    with pytest.raises(RICH.RichDataError, match="volume unit conflicts"):
        RICH.confirm_minute_alignment(
            snapshot_path,
            bar_label="end",
            volume_unit="lots",
            reviewed_boundaries=True,
            output=output,
        )

    result = RICH.confirm_minute_alignment(
        snapshot_path,
        bar_label="end",
        volume_unit="shares",
        reviewed_boundaries=True,
        output=output,
    )
    record = RICH.json.loads(result.read_text())
    assert snapshot_path.read_bytes() == original_snapshot
    assert record["status"] == "passed_for_feature_research"
    assert record["complete_session_evidence"][0]["first_bar"].endswith("09:31:00")
    assert record["complete_session_evidence"][0]["last_bar"].endswith("15:00:00")
    assert record["forward_return_fields_read"] is False


def test_alignment_confirmation_supports_exact_baostock_5m_grid(tmp_path):
    times = RICH.expected_minute_times("end", "5m")
    frame = pd.DataFrame(
        {
            "datetime": [
                pd.Timestamp.combine(dt.date(2026, 7, 10), value) for value in times
            ],
            "symbol": "SH600519",
            "source_symbol": "sh.600519",
            "open": 10.0,
            "high": 10.0,
            "low": 10.0,
            "close": 10.0,
            "volume": 100.0,
            "amount": 1000.0,
            "provider": "baostock",
        }
    )
    data_path = tmp_path / "accepted_5m.parquet"
    RICH.atomic_write_frame(frame, data_path)
    snapshot = {
        "kind": "a_share_rich_data_snapshot",
        "dataset": "minutes",
        "provider": "baostock",
        "frequency": "5m",
        "prices": "raw_unadjusted",
        "run_id": "accepted-5m-test",
        "files": [
            {
                "path": str(data_path),
                "sha256": RICH.frame_digest(frame),
                "acceptance": {
                    "daily_reconciliation": {
                        "status": "passed",
                        "days": [
                            {"status": "passed", "inferred_volume_unit": "shares"}
                        ],
                    }
                },
            }
        ],
        "acceptance_status": "automatic_checks_passed_pending_time_alignment",
    }
    snapshot_path = tmp_path / "accepted_5m.json"
    RICH.atomic_write_json(snapshot, snapshot_path)
    result = RICH.confirm_minute_alignment(
        snapshot_path,
        bar_label="end",
        volume_unit="shares",
        reviewed_boundaries=True,
        output=tmp_path / "alignment_5m.json",
    )
    record = RICH.json.loads(result.read_text())
    assert record["frequency"] == "5m"
    assert record["normalization_to_bar_end"] == "identity"
    assert record["complete_session_evidence"][0]["first_bar"].endswith("09:35:00")


def test_minute_features_require_exact_complete_session_and_never_fill_gaps():
    frame = complete_minute_frame()
    trade_date = pd.Timestamp("2026-07-13")
    previous = {"SH600519": {trade_date: 9.9}}
    result = RICH.minute_feature_frame(frame, bar_label="end", previous_closes=previous)
    row = result.iloc[0]
    late = frame.loc[frame["datetime"].dt.time > dt.time(14, 30)]
    anchor_close = frame.loc[
        frame["datetime"].dt.time == dt.time(14, 30), "close"
    ].iloc[0]
    expected_late_vwap = (late["amount"].sum() / late["volume"].sum()) / (
        frame["amount"].sum() / frame["volume"].sum()
    ) - 1.0
    assert row["minute_feature_eligible"]
    assert row["late_return_30m"] == pytest.approx(
        frame["close"].iloc[-1] / anchor_close - 1.0
    )
    assert row["late_amount_share_30m"] == pytest.approx(
        late["amount"].sum() / frame["amount"].sum()
    )
    assert row["late_vwap_to_day_vwap_30m"] == pytest.approx(expected_late_vwap)
    assert row["opening_gap_digestion"] == pytest.approx(
        -(frame["close"].iloc[-1] / frame["open"].iloc[0] - 1.0)
    )
    assert row["intraday_realized_volatility"] > 0.0

    missing = RICH.minute_feature_frame(
        frame.drop(index=100), bar_label="end", previous_closes=previous
    ).iloc[0]
    duplicate = RICH.minute_feature_frame(
        pd.concat([frame, frame.iloc[[100]]], ignore_index=True),
        bar_label="end",
        previous_closes=previous,
    ).iloc[0]
    assert not missing["complete_regular_session"]
    assert not missing["minute_feature_eligible"]
    assert not duplicate["complete_regular_session"]
    assert not duplicate["minute_feature_eligible"]
    assert pd.isna(missing["late_return_30m"])


def test_baostock_5m_features_use_six_late_bars_and_distinct_names():
    times = RICH.expected_minute_times("end", "5m")
    datetimes = [pd.Timestamp.combine(dt.date(2026, 7, 10), value) for value in times]
    close = pd.Series([10.0 + index * 0.01 for index in range(48)], dtype=float)
    volume = pd.Series([100.0 + index for index in range(48)], dtype=float)
    frame = pd.DataFrame(
        {
            "datetime": datetimes,
            "symbol": "SH600519",
            "source_symbol": "sh.600519",
            "open": close,
            "high": close + 0.01,
            "low": close - 0.01,
            "close": close,
            "volume": volume,
            "amount": volume * close,
            "provider": "baostock",
        }
    )
    trade_date = pd.Timestamp("2026-07-10")
    result = RICH.minute_feature_frame(
        frame,
        bar_label="end",
        previous_closes={"SH600519": {trade_date: 9.9}},
        frequency="5m",
        feature_names=RICH.BAOSTOCK_5M_FEATURE_NAMES,
    )
    row = result.iloc[0]
    late = frame.loc[pd.to_datetime(frame["datetime"]).dt.time > dt.time(14, 30)]
    anchor_close = frame.loc[
        pd.to_datetime(frame["datetime"]).dt.time == dt.time(14, 30), "close"
    ].iloc[0]
    assert len(late) == 6
    assert row["minute_bars"] == 48
    assert row["minute_feature_eligible"]
    assert row["late_return_30m_5m"] == pytest.approx(
        close.iloc[-1] / anchor_close - 1.0
    )
    assert row["late_amount_share_30m_5m"] == pytest.approx(
        late["amount"].sum() / frame["amount"].sum()
    )
    assert row["intraday_realized_volatility_5m"] > 0.0
    assert not (set(RICH.MINUTE_FEATURE_NAMES) & set(result.columns))


def test_previous_close_is_scaled_across_factor_change(tmp_path, monkeypatch):
    daily_root = tmp_path / "daily"
    daily_root.mkdir()
    monkeypatch.setattr(RICH, "DAILY_RAW_DIR", daily_root)
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-10", "2026-07-13"]),
            "raw_close": [100.0, 80.0],
            "factor": [1.0, 1.25],
            "price_basis": [RICH.REQUIRED_DAILY_PRICE_BASIS] * 2,
        }
    ).to_parquet(daily_root / "sh600519.parquet", index=False)
    comparable = RICH.previous_comparable_close_map("SH600519")
    assert comparable[pd.Timestamp("2026-07-13")] == pytest.approx(80.0)


def test_feature_builder_binds_snapshot_alignment_and_frozen_spec(
    tmp_path, monkeypatch
):
    frame = complete_minute_frame()
    snapshot_path = write_accepted_snapshot(tmp_path, frame)
    alignment_path = RICH.confirm_minute_alignment(
        snapshot_path,
        bar_label="end",
        volume_unit="shares",
        reviewed_boundaries=True,
        output=tmp_path / "alignment.json",
    )
    daily_root = tmp_path / "daily"
    daily_root.mkdir()
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-10", "2026-07-13"]),
            "raw_close": [9.9, float(frame["close"].iloc[-1])],
            "factor": [1.0, 1.0],
            "price_basis": [RICH.REQUIRED_DAILY_PRICE_BASIS] * 2,
        }
    ).to_parquet(daily_root / "sh600519.parquet", index=False)
    monkeypatch.setattr(RICH, "DAILY_RAW_DIR", daily_root)
    monkeypatch.setattr(RICH, "DERIVED_ROOT", tmp_path / "derived")
    monkeypatch.setattr(RICH, "FEATURE_RUNS_ROOT", tmp_path / "feature_runs")

    feature_manifest_path = RICH.build_minute_features(snapshot_path, alignment_path)
    feature_manifest = RICH.json.loads(feature_manifest_path.read_text())
    output_path = RICH.resolve_record_path(feature_manifest["output"]["path"])
    output_frame = pd.read_parquet(output_path)
    assert feature_manifest["output"]["eligible_rows"] == 1
    assert feature_manifest["forward_return_fields_read"] is False
    assert feature_manifest["future_price_fields_read"] is False
    assert feature_manifest["selection_or_promotion_allowed"] is False
    assert output_frame["minute_feature_eligible"].tolist() == [True]

    snapshot_path.write_text(snapshot_path.read_text() + "\n", encoding="utf-8")
    with pytest.raises(RICH.RichDataError, match="fingerprint mismatch"):
        RICH.build_minute_features(
            snapshot_path,
            alignment_path,
            output=tmp_path / "tampered.parquet",
        )


def test_feature_builder_accepts_passed_baostock_5m_history_snapshot(
    tmp_path, monkeypatch
):
    frame = complete_baostock_5m_frame(["2025-12-31"])
    data_path = tmp_path / "sh600519" / "2025.parquet"
    RICH.atomic_write_frame(frame, data_path)
    snapshot_path = tmp_path / "baostock_5m_history.json"
    RICH.atomic_write_json(
        {
            "kind": "a_share_rich_data_snapshot",
            "dataset": "baostock_five_minute_history",
            "provider": "baostock",
            "frequency": "5m",
            "prices": "raw_unadjusted",
            "run_id": "full-5m-test",
            "status": "full_source_coverage_passed_pending_no_return_feature_materialization",
            "coverage": {"gate_passed_before_prices": True},
            "source_chain": {
                "factor_spec": {
                    "sha256": RICH.BAOSTOCK_5M_FACTOR_SPEC_SHA256,
                },
                "acceptance_snapshot": {
                    "sha256": (
                        "e3d2160fab34c3a51b1524623a7c14f800abdc75164a66f0371386cf29ac68cd"
                    ),
                },
                "alignment_confirmation": {
                    "sha256": (
                        "cf50051d254a3fcc2727d649b167ed053bbba2e2b3dfa2c939fae04166b54c6c"
                    ),
                },
            },
            "files": [{"path": str(data_path), "sha256": RICH.frame_digest(frame)}],
            "forward_return_fields_read": False,
            "selection_or_promotion_allowed": False,
        },
        snapshot_path,
    )
    alignment_path = (
        RICH.REPO_ROOT
        / "data/metadata/rich_data/alignments/20260714T210154Z_baostock_5m_alignment_2b1ad30e.json"
    )
    daily_root = tmp_path / "daily"
    daily_root.mkdir()
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-12-30", "2025-12-31"]),
            "raw_close": [9.9, float(frame["close"].iloc[-1])],
            "factor": [1.0, 1.0],
            "price_basis": [RICH.REQUIRED_DAILY_PRICE_BASIS] * 2,
        }
    ).to_parquet(daily_root / "sh600519.parquet", index=False)
    monkeypatch.setattr(RICH, "DAILY_RAW_DIR", daily_root)
    monkeypatch.setattr(RICH, "FEATURE_RUNS_ROOT", tmp_path / "feature_runs")
    output = tmp_path / "features.parquet"

    feature_manifest_path = RICH.build_minute_features(
        snapshot_path,
        alignment_path,
        factor_spec_path=RICH.DEFAULT_BAOSTOCK_5M_FACTOR_SPEC,
        output=output,
    )
    feature_manifest = RICH.json.loads(feature_manifest_path.read_text())
    features = pd.read_parquet(output)
    assert feature_manifest["frequency"] == "5m"
    assert feature_manifest["output"]["eligible_rows"] == 1
    assert (
        tuple(column for column in RICH.BAOSTOCK_5M_FEATURE_NAMES if column in features)
        == RICH.BAOSTOCK_5M_FEATURE_NAMES
    )
    assert features["minute_bars"].tolist() == [48]
    assert feature_manifest["forward_return_fields_read"] is False
