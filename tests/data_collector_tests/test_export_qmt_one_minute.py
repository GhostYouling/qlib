"""Offline tests for the fixed QMT/XtQuant one-minute exporter."""

import datetime as dt
import gzip
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "export_qmt_one_minute.py"
SPEC = importlib.util.spec_from_file_location("export_qmt_one_minute", SCRIPT_PATH)
QMT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(QMT)


class FakeXtData:
    """Record the two frozen XtData calls and return deterministic raw bars."""

    __version__ = "test-runtime"

    def __init__(self, *, malformed_symbol: str | None = None) -> None:
        self.malformed_symbol = malformed_symbol
        self.download_calls = []
        self.read_calls = []

    def download_history_data2(self, *args, **kwargs):
        self.download_calls.append((args, kwargs))

    def get_market_data_ex(self, fields, symbols, **kwargs):
        self.read_calls.append(((fields, symbols), kwargs))
        morning = pd.date_range(
            pd.Timestamp("2026-07-13 09:31:00", tz="Asia/Shanghai"),
            periods=120,
            freq="min",
        )
        afternoon = pd.date_range(
            pd.Timestamp("2026-07-13 13:01:00", tz="Asia/Shanghai"),
            periods=120,
            freq="min",
        )
        timestamps = morning.append(afternoon)
        timetag_ms = [
            int(value.tz_convert("UTC").timestamp() * 1000) for value in timestamps
        ]
        response = {}
        for symbol_index, symbol in enumerate(symbols):
            close = pd.Series(
                [10.0 + symbol_index + index / 10000 for index in range(240)],
                dtype="float64",
            )
            volume = pd.Series([1000.0 + index for index in range(240)])
            frame = pd.DataFrame(
                {
                    "time": timetag_ms,
                    "open": close,
                    "high": close + 0.01,
                    "low": close - 0.01,
                    "close": close,
                    "volume": volume,
                    "amount": volume * close,
                    "suspendFlag": 0,
                }
            )
            if symbol == self.malformed_symbol:
                frame = frame.drop(columns=["amount"])
            response[symbol] = frame
        return response


def test_qmt_exporter_writes_fixed_privacy_minimized_bundle(tmp_path):
    fake = FakeXtData()
    output = tmp_path / "acceptance-bundle"
    manifest_path = QMT.export_qmt_acceptance_bundle(
        output,
        xtdata_module=fake,
        generated_at=dt.datetime(2026, 7, 21, 12, 0, tzinfo=dt.timezone.utc),
    )

    download_args, download_kwargs = fake.download_calls[0]
    assert list(download_args[0]) == [
        "600519.SH",
        "000001.SZ",
        "300750.SZ",
        "688981.SH",
    ]
    assert download_kwargs == {
        "period": "1m",
        "start_time": "20260713",
        "end_time": "20260713",
    }
    read_args, read_kwargs = fake.read_calls[0]
    assert read_args[0] == [
        "time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "suspendFlag",
    ]
    assert read_args[1] == download_args[0]
    assert read_kwargs == {
        "period": "1m",
        "start_time": "20260713",
        "end_time": "20260713",
        "count": -1,
        "dividend_type": "none",
        "fill_data": False,
    }

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = QMT.load_contract()["bundle_manifest_contract"][
        "required_top_level_fields"
    ]
    assert set(manifest) == set(required)
    assert manifest["trade_date"] == "2026-07-13"
    assert manifest["privacy"] == {
        "credential_account_cookie_token_client_path_machine_name_or_username_persisted": False,
        "trading_or_level2_api_used": False,
        "raw_qmt_cache_or_client_database_copied": False,
    }
    assert len(manifest["files"]) == 4
    for entry in manifest["files"]:
        path = output / entry["path"]
        assert entry["rows"] == 240
        assert entry["sha256"] == QMT.file_sha256(path)
        with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
            frame = pd.read_csv(stream)
        assert list(frame.columns) == entry["columns"]
        assert len(frame) == 240
        assert frame["source_symbol"].eq(entry["source_symbol"]).all()
    rendered = json.dumps(manifest, sort_keys=True)
    assert "TUSHARE_TOKEN" not in rendered
    assert "account_id" not in rendered


def test_qmt_exporter_failure_is_atomic(tmp_path):
    output = tmp_path / "broken-bundle"
    fake = FakeXtData(malformed_symbol="300750.SZ")
    with pytest.raises(QMT.QmtExportError, match="field order or schema"):
        QMT.export_qmt_acceptance_bundle(output, xtdata_module=fake)
    assert not output.exists()
    assert not (tmp_path / ".broken-bundle.partial").exists()


def test_qmt_exporter_rejects_existing_destination_before_runtime_call(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    fake = FakeXtData()
    with pytest.raises(QMT.QmtExportError, match="already exists"):
        QMT.export_qmt_acceptance_bundle(output, xtdata_module=fake)
    assert fake.download_calls == []
    assert fake.read_calls == []
