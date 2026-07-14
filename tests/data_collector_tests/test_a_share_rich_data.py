"""Offline contract tests for credentialed A-share rich-data ingestion."""

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
    datetimes = [pd.Timestamp.combine(pd.Timestamp(trade_date).date(), value) for value in times]
    close = pd.Series([10.0 + index * 0.001 for index in range(len(datetimes))], dtype=float)
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


def test_baostock_5m_contract_is_fingerprint_frozen(tmp_path):
    contract = RICH.load_baostock_5m_contract()
    assert contract["source"]["requested_fields"] == [
        "date", "time", "code", "open", "high", "low", "close", "volume", "amount", "adjustflag"
    ]
    assert contract["formal_acceptance"]["trade_date"] == "2026-07-10"
    assert contract["timestamp_contract"]["expected_bars_per_complete_regular_session"] == 48
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
            "date", "time", "code", "open", "high", "low", "close", "volume", "amount", "adjustflag"
        ]

        def __init__(self):
            self.rows = iter(
                [["2026-07-10", "20260710093500000", "sh.600519", "10", "10", "10", "10", "100", "1000", "3"]]
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


def test_jqdata_moneyflow_contract_is_fingerprint_frozen(tmp_path):
    contract = RICH.load_jqdata_moneyflow_contract()
    assert contract["factor"]["name"] == "jqdata_large_order_net_inflow_share"
    assert contract["source"]["requested_fields"] == list(RICH.JQDATA_MONEYFLOW_RAW_FIELDS)
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
    forbidden = set(RICH.load_jqdata_moneyflow_contract()["source"]["explicitly_forbidden_fields"])
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
    assert normalized["jqdata_large_order_net_inflow_share"].item() == pytest.approx(0.4)
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


def test_jqdata_moneyflow_sync_writes_immutable_no_price_snapshot(tmp_path, monkeypatch):
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
    assert manifest["source_request"]["fields"] == list(RICH.JQDATA_MONEYFLOW_RAW_FIELDS)
    assert manifest["source_request"]["credentials_logged_or_stored"] is False
    assert manifest["source_acceptance"]["run_id"] == "accepted"
    assert manifest["price_fields_loaded"] == []
    assert manifest["forward_return_fields_read"] is False
    assert manifest["acceptance_status"] == "full_source_coverage_failed_stop_before_prices"
    stored = pd.read_parquet(RICH.resolve_record_path(manifest["files"][0]["path"]))
    assert stored.columns.tolist() == list(RICH.JQDATA_MONEYFLOW_COLUMNS)
    assert len(stored) == 4
    assert not list((tmp_path / "raw").rglob("*.partial"))


def test_jqdata_moneyflow_full_sync_requires_fingerprinted_acceptance(tmp_path):
    with pytest.raises(RICH.RichDataError, match="run acceptance-jqdata-moneyflow first"):
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


def test_canonicalize_minutes_handles_provider_column_names_and_sorts_rows():
    raw = pd.DataFrame(
        {
            "trade_time": ["2026-07-13 09:31:00", "2026-07-13 09:30:00", "2026-07-13 09:30:00"],
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
    assert normalized["datetime"].dt.strftime("%H:%M:%S").tolist() == ["09:30:00", "09:31:00"]
    assert normalized["close"].tolist() == pytest.approx([10.04, 10.15])
    assert normalized["symbol"].tolist() == ["SH600519", "SH600519"]
    assert normalized["amount"].tolist() == pytest.approx([1014.0, 2030.0])


def test_canonicalize_minutes_rejects_invalid_ohlc():
    raw = pd.DataFrame(
        {
            "datetime": ["2026-07-13 09:30:00"],
            "open": [10.0], "high": [9.0], "low": [9.5], "close": [9.8],
            "volume": [100.0], "amount": [1000.0],
        }
    )
    with pytest.raises(RICH.RichDataError, match="invalid minute bars"):
        RICH.canonicalize_minute_bars(raw, "rqdata", "000001", dt.date(2026, 7, 13), dt.date(2026, 7, 13))


def test_minute_acceptance_reconciles_only_against_raw_daily_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(RICH, "DAILY_RAW_DIR", tmp_path / "daily")
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2026-07-13 09:31:00", "2026-07-13 09:32:00"]),
            "symbol": ["SH600519", "SH600519"],
            "source_symbol": ["600519.SH", "600519.SH"],
            "open": [10.0, 10.1], "high": [10.15, 10.3], "low": [9.8, 10.0], "close": [10.1, 10.1],
            "volume": [1.0, 2.0], "amount": [10.0, 20.0], "provider": ["tushare", "tushare"],
        }
    )
    (tmp_path / "daily").mkdir()
    pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-07-13"]), "symbol": ["SH600519"],
            "open": [20.0], "high": [20.6], "low": [19.6], "close": [20.2],
            "volume": [1.5], "amount": [30.0],
            "raw_open": [10.0], "raw_high": [10.3], "raw_low": [9.8], "raw_close": [10.1],
            "raw_volume": [3.0], "price_basis": [RICH.REQUIRED_DAILY_PRICE_BASIS],
        }
    ).to_parquet(tmp_path / "daily" / "sh600519.parquet", index=False)
    report = RICH.minute_acceptance_report(frame)
    assert report["status"] == "automatic_checks_passed_pending_time_alignment"
    assert report["daily_reconciliation"]["daily_price_basis"] == "raw_unadjusted_to_raw_daily"
    assert report["daily_reconciliation"]["days"][0]["inferred_volume_unit"] == "lots"


def test_minute_session_check_rejects_lunch_break_timestamp():
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2026-07-13 12:00:00"]), "symbol": ["SH600519"],
            "open": [10.0], "high": [10.0], "low": [10.0], "close": [10.0], "volume": [1.0], "amount": [10.0],
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
    RICH.fetch_tushare_minutes("600519", dt.date(2026, 7, 13), dt.date(2026, 7, 13), "1m")
    assert captured["start_date"] == "2026-07-13 09:00:00"
    assert captured["end_date"] == "2026-07-13 17:00:00"


def test_validate_range_requires_completed_session_and_large_request_confirmation():
    completed = RICH.latest_completed_session_date()
    with pytest.raises(RICH.RichDataError, match="not a completed"):
        future = completed + dt.timedelta(days=1)
        RICH.validate_range(future, future, False)
    with pytest.raises(RICH.RichDataError, match="allow-large"):
        RICH.validate_range(dt.date(2026, 1, 1), dt.date(2026, 7, 13), False, unit_count=4)


def test_snapshot_write_records_checksum_and_minute_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(RICH, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(RICH, "RUNS_ROOT", tmp_path / "metadata" / "runs")
    frame = pd.DataFrame(
        {
            "datetime": pd.to_datetime(["2026-07-13 09:30:00", "2026-07-13 09:31:00"]),
            "symbol": ["SH600519", "SH600519"],
            "source_symbol": ["600519.SH", "600519.SH"],
            "open": [10.0, 10.1], "high": [10.1, 10.2], "low": [9.9, 10.0], "close": [10.05, 10.15],
            "volume": [100.0, 200.0], "amount": [1005.0, 2030.0], "provider": ["tushare", "tushare"],
        }
    )
    manifest_path = RICH.write_minute_snapshot("tushare", "1m", dt.date(2026, 7, 13), dt.date(2026, 7, 13), {"600519": frame})
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
        dt.time(9, 30), dt.time(11, 29), dt.time(13, 0), dt.time(14, 59)
    )
    assert (end[0], end[119], end[120], end[-1]) == (
        dt.time(9, 31), dt.time(11, 30), dt.time(13, 1), dt.time(15, 0)
    )
    five_start = RICH.expected_minute_times("start", "5m")
    five_end = RICH.expected_minute_times("end", "5m")
    assert len(five_start) == len(five_end) == 48
    assert (five_start[0], five_start[23], five_start[24], five_start[-1]) == (
        dt.time(9, 30), dt.time(11, 25), dt.time(13, 0), dt.time(14, 55)
    )
    assert (five_end[0], five_end[23], five_end[24], five_end[-1]) == (
        dt.time(9, 35), dt.time(11, 30), dt.time(13, 5), dt.time(15, 0)
    )


def test_baostock_5m_acceptance_requires_exact_end_label_grid(monkeypatch):
    contract = RICH.load_baostock_5m_contract()
    times = RICH.expected_minute_times("end", "5m")
    frame = pd.DataFrame(
        {
            "datetime": [pd.Timestamp.combine(dt.date(2026, 7, 10), value) for value in times],
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
    assert tuple(item["name"] for item in spec["features"]) == RICH.BAOSTOCK_5M_FEATURE_NAMES
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
            "datetime": [pd.Timestamp.combine(dt.date(2026, 7, 10), value) for value in times],
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
                        "days": [{"status": "passed", "inferred_volume_unit": "shares"}],
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
    anchor_close = frame.loc[frame["datetime"].dt.time == dt.time(14, 30), "close"].iloc[0]
    expected_late_vwap = (late["amount"].sum() / late["volume"].sum()) / (
        frame["amount"].sum() / frame["volume"].sum()
    ) - 1.0
    assert row["minute_feature_eligible"]
    assert row["late_return_30m"] == pytest.approx(frame["close"].iloc[-1] / anchor_close - 1.0)
    assert row["late_amount_share_30m"] == pytest.approx(late["amount"].sum() / frame["amount"].sum())
    assert row["late_vwap_to_day_vwap_30m"] == pytest.approx(expected_late_vwap)
    assert row["opening_gap_digestion"] == pytest.approx(-(frame["close"].iloc[-1] / frame["open"].iloc[0] - 1.0))
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
    assert row["late_return_30m_5m"] == pytest.approx(close.iloc[-1] / anchor_close - 1.0)
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


def test_feature_builder_binds_snapshot_alignment_and_frozen_spec(tmp_path, monkeypatch):
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
