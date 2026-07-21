"""Offline tests for the fixed QMT/XtQuant one-minute exporter."""

import datetime as dt
import gzip
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "export_qmt_one_minute.py"
SPEC = importlib.util.spec_from_file_location("export_qmt_one_minute", SCRIPT_PATH)
QMT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(QMT)

RICH_SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "a_share_rich_data.py"
)
RICH_SPEC = importlib.util.spec_from_file_location(
    "a_share_rich_data_qmt_import_tests", RICH_SCRIPT_PATH
)
RICH = importlib.util.module_from_spec(RICH_SPEC)
assert RICH_SPEC.loader is not None
sys.modules[RICH_SPEC.name] = RICH
RICH_SPEC.loader.exec_module(RICH)


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


def build_qmt_bundle(tmp_path: Path) -> Path:
    """Create one deterministic end-labelled acceptance bundle."""

    return QMT.export_qmt_acceptance_bundle(
        tmp_path / "acceptance-bundle",
        xtdata_module=FakeXtData(),
        generated_at=dt.datetime(2026, 7, 21, 12, 0, tzinfo=dt.timezone.utc),
    )


def rewrite_bundle_file(
    manifest_path: Path,
    source_symbol: str,
    transform,
) -> None:
    """Rewrite one deterministic gzip member and update only its byte hash."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = next(
        item for item in manifest["files"] if item["source_symbol"] == source_symbol
    )
    path = manifest_path.parent / record["path"]
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        frame = pd.read_csv(stream)
    QMT.write_deterministic_gzip_csv(transform(frame), path)
    record["sha256"] = QMT.file_sha256(path)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_matching_daily_references(
    manifest_path: Path,
    daily_root: Path,
    *,
    close_multiplier: float = 1.0,
) -> None:
    """Derive local raw daily references from the isolated fake export."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    daily_root.mkdir(parents=True)
    for code, record in zip(manifest["symbols"], manifest["files"], strict=True):
        with gzip.open(
            manifest_path.parent / record["path"],
            "rt",
            encoding="utf-8",
            newline="",
        ) as stream:
            minute = pd.read_csv(stream)
        daily = pd.DataFrame(
            {
                "date": pd.to_datetime([manifest["trade_date"]]),
                "raw_open": [float(minute["open"].iloc[0])],
                "raw_high": [float(minute["high"].max())],
                "raw_low": [float(minute["low"].min())],
                "raw_close": [float(minute["close"].iloc[-1]) * close_multiplier],
                "raw_volume": [float(minute["volume"].sum()) / 100.0],
                "amount": [float(minute["amount"].sum())],
                "price_basis": [RICH.REQUIRED_DAILY_PRICE_BASIS],
            }
        )
        daily.to_parquet(
            daily_root / f"{RICH.qlib_symbol(str(code)).lower()}.parquet",
            index=False,
        )


def accept_fake_qmt_bundle(
    manifest_path: Path,
    tmp_path: Path,
    monkeypatch,
    *,
    close_multiplier: float = 1.0,
) -> Path:
    """Run strict import against isolated daily references and no network."""

    daily_root = tmp_path / "daily"
    write_matching_daily_references(
        manifest_path,
        daily_root,
        close_multiplier=close_multiplier,
    )
    monkeypatch.setattr(RICH, "DAILY_RAW_DIR", daily_root)
    monkeypatch.setattr(
        RICH,
        "validate_qmt_xtquant_one_minute_local_context",
        lambda contract: None,
    )
    return RICH.accept_qmt_xtquant_one_minute_export(
        manifest_path,
        data_root=tmp_path / "accepted-data",
        imported_at=dt.datetime(2026, 7, 21, 12, 30, tzinfo=dt.timezone.utc),
    )


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


def test_qmt_importer_accepts_all_four_files_atomically(tmp_path, monkeypatch):
    manifest_path = build_qmt_bundle(tmp_path)
    accepted_manifest_path = accept_fake_qmt_bundle(
        manifest_path, tmp_path, monkeypatch
    )

    accepted = json.loads(accepted_manifest_path.read_text(encoding="utf-8"))
    assert accepted["provider"] == "qmt_xtquant_export"
    assert accepted["automatic_timestamp_grid"] == {
        "observed_label": "end",
        "bars_per_symbol": 240,
        "explicit_separate_confirmation_required": True,
    }
    assert accepted["automatic_volume_unit"] == "shares"
    assert accepted["minute_factor_values_persisted"] is False
    assert accepted["full_history_persisted"] is False
    assert accepted["forward_return_fields_read"] is False
    assert accepted["selection_or_promotion_allowed"] is False
    assert len(accepted["files"]) == 4
    for record in accepted["files"]:
        frame = pd.read_parquet(record["path"])
        assert tuple(frame.columns) == RICH.QMT_XTQUANT_NORMALIZED_COLUMNS
        assert len(frame) == 240
        assert frame["provider"].eq("qmt_xtquant_export").all()
        assert record["acceptance"]["daily_reconciliation"]["status"] == "passed"

    confirmation = RICH.confirm_minute_alignment(
        accepted_manifest_path,
        bar_label="end",
        volume_unit="shares",
        reviewed_boundaries=True,
        output=tmp_path / "alignment.json",
    )
    alignment = json.loads(confirmation.read_text(encoding="utf-8"))
    assert alignment["status"] == (
        "passed_pending_separate_full_source_no_return_protocol"
    )
    assert len(alignment["complete_session_evidence"]) == 4

    with pytest.raises(RICH.RichDataError, match="not passed for feature research"):
        RICH.build_minute_features(accepted_manifest_path, confirmation)


def test_qmt_importer_rejects_byte_tampering_and_consumes_failure(
    tmp_path, monkeypatch
):
    manifest_path = build_qmt_bundle(tmp_path)
    source_file = next(manifest_path.parent.glob("*.csv.gz"))
    source_file.write_bytes(source_file.read_bytes() + b"tampered")
    monkeypatch.setattr(
        RICH,
        "validate_qmt_xtquant_one_minute_local_context",
        lambda contract: None,
    )
    data_root = tmp_path / "accepted-data"

    with pytest.raises(RICH.RichDataError, match="byte fingerprint mismatch"):
        RICH.accept_qmt_xtquant_one_minute_export(
            manifest_path, data_root=data_root
        )
    rejection_records = list(
        (data_root / "metadata" / "rich_data" / "runs").glob("*_rejection.json")
    )
    assert len(rejection_records) == 1
    rejection = json.loads(rejection_records[0].read_text(encoding="utf-8"))
    assert rejection["failed_stage"] == "bundle_validation"
    assert rejection["published_snapshot_files"] == 0
    assert not (
        data_root
        / "raw"
        / "a_share"
        / "rich"
        / "qmt_xtquant_export"
        / "minutes"
        / "1m"
        / "snapshots"
    ).exists()

    with pytest.raises(RICH.RichDataError, match="already consumed"):
        RICH.accept_qmt_xtquant_one_minute_export(
            manifest_path, data_root=data_root
        )
    assert len(
        list(
            (data_root / "metadata" / "rich_data" / "runs").glob(
                "*_rejection.json"
            )
        )
    ) == 1


def test_qmt_importer_rejects_mixed_timestamp_labels(tmp_path, monkeypatch):
    manifest_path = build_qmt_bundle(tmp_path)
    rewrite_bundle_file(
        manifest_path,
        "600519.SH",
        lambda frame: frame.assign(timetag_ms=frame["timetag_ms"] - 60_000),
    )

    with pytest.raises(RICH.RichDataError, match="mixed timestamp-label grids"):
        accept_fake_qmt_bundle(manifest_path, tmp_path, monkeypatch)
    rejection = next(
        (tmp_path / "accepted-data" / "metadata" / "rich_data" / "runs").glob(
            "*_rejection.json"
        )
    )
    assert json.loads(rejection.read_text(encoding="utf-8"))["failed_stage"] == (
        "strict_csv_normalization"
    )


def test_qmt_importer_rejects_unexpected_bundle_member(tmp_path, monkeypatch):
    manifest_path = build_qmt_bundle(tmp_path)
    (manifest_path.parent / ".DS_Store").write_bytes(b"unexpected")
    monkeypatch.setattr(
        RICH,
        "validate_qmt_xtquant_one_minute_local_context",
        lambda contract: None,
    )

    with pytest.raises(RICH.RichDataError, match="unexpected or missing file"):
        RICH.accept_qmt_xtquant_one_minute_export(
            manifest_path, data_root=tmp_path / "accepted-data"
        )


def test_qmt_importer_rejects_csv_schema_change(tmp_path, monkeypatch):
    manifest_path = build_qmt_bundle(tmp_path)
    rewrite_bundle_file(
        manifest_path,
        "600519.SH",
        lambda frame: frame.assign(unexpected=1),
    )

    with pytest.raises(RICH.RichDataError, match="column order or schema"):
        accept_fake_qmt_bundle(manifest_path, tmp_path, monkeypatch)


def test_qmt_importer_rejects_daily_reconciliation_mismatch(tmp_path, monkeypatch):
    manifest_path = build_qmt_bundle(tmp_path)

    with pytest.raises(RICH.RichDataError, match="daily reconciliation"):
        accept_fake_qmt_bundle(
            manifest_path,
            tmp_path,
            monkeypatch,
            close_multiplier=1.1,
        )
    rejection = next(
        (tmp_path / "accepted-data" / "metadata" / "rich_data" / "runs").glob(
            "*_rejection.json"
        )
    )
    payload = json.loads(rejection.read_text(encoding="utf-8"))
    assert payload["failed_stage"] == "local_daily_reconciliation"
    assert payload["local_daily_fields_loaded_for_reconciliation"] == [
        "raw_open",
        "raw_high",
        "raw_low",
        "raw_close",
        "raw_volume",
        "amount",
        "price_basis",
    ]


def test_qmt_importer_records_unexpected_publish_failure(tmp_path, monkeypatch):
    manifest_path = build_qmt_bundle(tmp_path)
    daily_root = tmp_path / "daily"
    write_matching_daily_references(manifest_path, daily_root)
    monkeypatch.setattr(RICH, "DAILY_RAW_DIR", daily_root)
    monkeypatch.setattr(
        RICH,
        "validate_qmt_xtquant_one_minute_local_context",
        lambda contract: None,
    )
    monkeypatch.setattr(
        RICH,
        "_publish_qmt_xtquant_acceptance_snapshot",
        lambda **kwargs: (_ for _ in ()).throw(OSError("do not persist this detail")),
    )
    data_root = tmp_path / "accepted-data"

    with pytest.raises(RICH.RichDataError, match="unexpected OSError"):
        RICH.accept_qmt_xtquant_one_minute_export(
            manifest_path, data_root=data_root
        )
    rejection = next(
        (data_root / "metadata" / "rich_data" / "runs").glob(
            "*_rejection.json"
        )
    )
    payload = json.loads(rejection.read_text(encoding="utf-8"))
    assert payload["failed_stage"] == "atomic_publish"
    assert payload["error"] == (
        "QMT acceptance stopped on an unexpected OSError without preserving source values"
    )
    assert "do not persist this detail" not in rejection.read_text(encoding="utf-8")
