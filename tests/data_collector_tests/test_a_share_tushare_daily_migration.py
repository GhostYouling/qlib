"""Offline tests for isolated Tushare daily-provider migration."""

import datetime as dt
import importlib.util
import json
import os
import sys
from contextlib import nullcontext
from pathlib import Path

import pandas as pd
import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "a_share_tushare_daily_migration.py"
)
SPEC = importlib.util.spec_from_file_location(
    "a_share_tushare_daily_migration",
    SCRIPT_PATH,
)
MIGRATION = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MIGRATION
SPEC.loader.exec_module(MIGRATION)
REAL_LOAD_SOURCE_MANIFEST = MIGRATION._load_source_manifest  # pylint: disable=protected-access


def daily_frame(
    trade_date: str = "20150105",
    code: str = "600000.SH",
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ts_code": code,
                "trade_date": trade_date,
                "open": 10.0,
                "high": 10.5,
                "low": 9.8,
                "close": 10.2,
                "pre_close": 10.0,
                "change": 0.2,
                "pct_chg": 2.0,
                "vol": 1000.0,
                "amount": 1010.0,
            }
        ]
    )


def daily_basic_frame(
    trade_date: str = "20150105",
    code: str = "600000.SH",
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ts_code": code,
                "trade_date": trade_date,
                "turnover_rate": 1.25,
            }
        ]
    )


def stock_basic_frame(
    *,
    code: str = "600000.SH",
    list_status: str = "L",
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ts_code": code,
                "symbol": code.split(".", maxsplit=1)[0],
                "name": "测试股票",
                "market": "主板",
                "list_date": "19991110",
                "delist_date": "",
                "list_status": list_status,
            }
        ]
    )


def test_daily_basic_requires_exact_date_schema_and_nonnegative_turnover() -> None:
    result = MIGRATION.canonicalize_daily_basic(
        daily_basic_frame(),
        dt.date(2015, 1, 5),
    )
    assert tuple(result.columns) == MIGRATION.DAILY_BASIC_FIELDS
    assert result.loc[0, "turnover_rate"] == pytest.approx(1.25)

    invalid = daily_basic_frame()
    invalid.loc[0, "turnover_rate"] = -0.01
    with pytest.raises(
        MIGRATION.TushareDailyMigrationError,
        match="daily_basic values",
    ):
        MIGRATION.canonicalize_daily_basic(invalid, dt.date(2015, 1, 5))


@pytest.mark.parametrize(
    ("frames", "message"),
    [
        ([stock_basic_frame(code="INVALID")], "invalid ts_code"),
        ([stock_basic_frame(list_status="G")], "list_status outside L/D/P"),
        (
            [
                stock_basic_frame(list_status="L"),
                stock_basic_frame(list_status="D"),
            ],
            "duplicate ts_code identities",
        ),
    ],
)
def test_stock_basic_identity_failures_report_the_exact_rejected_gate(
    frames: list[pd.DataFrame],
    message: str,
) -> None:
    with pytest.raises(MIGRATION.TushareDailyMigrationError, match=message):
        MIGRATION.canonicalize_stock_basic(frames)


def test_merged_year_preserves_tushare_units_and_never_cross_fills_turnover() -> None:
    daily = MIGRATION.concordance.canonicalize_tushare_daily(
        daily_frame(),
        dt.date(2015, 1, 5),
    )
    basic = MIGRATION.canonicalize_daily_basic(
        daily_basic_frame(),
        dt.date(2015, 1, 5),
    )
    result, audit = MIGRATION.canonicalize_merged_daily_year(daily, basic)

    assert result.loc[0, "symbol"] == "SH600000"
    assert result.loc[0, "amount"] == pytest.approx(1_010_000.0)
    assert result.loc[0, "raw_volume"] == pytest.approx(1000.0)
    assert result.loc[0, "raw_vwap"] == pytest.approx(10.1)
    assert result.loc[0, "turnover"] == pytest.approx(1.25)
    assert audit["daily_basic_common_key_share"] == 1.0


def test_symbol_build_accepts_tushare_as_one_point_in_time_daily_source() -> None:
    rows = []
    for date, close, pre_close, pct_chg in (
        ("2015-01-05", 10.0, 9.9, None),
        ("2015-01-06", 10.2, 10.0, 2.0),
    ):
        rows.append(
            {
                "date": pd.Timestamp(date),
                "symbol": "SH600000",
                "pre_close": pre_close,
                "pct_chg": pct_chg,
                "amount": 1_010_000.0,
                "turnover": 1.0,
                "raw_open": close - 0.1,
                "raw_high": close + 0.2,
                "raw_low": close - 0.2,
                "raw_close": close,
                "raw_volume": 1000.0,
                "raw_vwap": close,
                "daily_source": "tushare",
            }
        )
    result = MIGRATION.build_symbol_bars(pd.DataFrame(rows), "SH600000")
    counts = MIGRATION.pipeline.price_basis_quality_counts(result)

    assert set(result["daily_source"]) == {"tushare"}
    assert set(result["price_basis"]) == {
        MIGRATION.pipeline.POINT_IN_TIME_PRICE_BASIS
    }
    assert not {
        key: value
        for key, value in counts.items()
        if value and key not in MIGRATION.pipeline.NON_FAILURE_PRICE_BASIS_COUNTS
    }


def test_preflight_missing_token_is_zero_write_and_zero_network(
    tmp_path,
    monkeypatch,
) -> None:
    staging = tmp_path / "staging"
    active = tmp_path / "active"
    active.mkdir()
    monkeypatch.setattr(
        MIGRATION,
        "validate_reference_snapshot",
        lambda path: ({"rows": 1}, "reference-sha"),
    )
    monkeypatch.setattr(MIGRATION, "resolve_data_root", lambda root: active)
    monkeypatch.setattr(
        MIGRATION.pipeline,
        "inspect_existing_daily_sources",
        lambda path: ({"baostock"}, []),
    )
    monkeypatch.setattr(
        MIGRATION,
        "latest_completed_session_date",
        lambda: dt.date(2026, 7, 24),
    )
    before = list(tmp_path.rglob("*"))
    result = MIGRATION.preflight(
        staging_root=staging,
        through_date=dt.date(2026, 7, 24),
        token_configured=False,
    )

    assert result["ready"] is False
    assert result["recommended_cli_exit_code"] == 2
    assert result["provider_request_issued"] is False
    assert result["filesystem_write_performed"] is False
    assert list(tmp_path.rglob("*")) == before


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def trade_cal(self, **kwargs):
        self.calls.append(("trade_cal", kwargs))
        return pd.DataFrame(
            [
                {
                    "cal_date": "20150105",
                    "is_open": 1,
                    "pretrade_date": "20141231",
                }
            ]
        )

    def stock_basic(self, **kwargs):
        self.calls.append(("stock_basic", kwargs))
        if kwargs["list_status"] != "L":
            return pd.DataFrame(columns=MIGRATION.STOCK_BASIC_FIELDS)
        return pd.DataFrame(
            [
                {
                    "ts_code": "600000.SH",
                    "symbol": "600000",
                    "name": "浦发银行",
                    "market": "主板",
                    "list_date": "19991110",
                    "delist_date": "",
                    "list_status": "L",
                }
            ]
        )

    def daily(self, **kwargs):
        self.calls.append(("daily", kwargs))
        return daily_frame()

    def daily_basic(self, **kwargs):
        self.calls.append(("daily_basic", kwargs))
        return daily_basic_frame()


def _prepare_accepted_tushare_parent(
    *,
    tmp_path: Path,
    monkeypatch,
) -> tuple[Path, Path, Path, dict]:
    parent = (tmp_path / "accepted-parent").resolve()
    staging = (tmp_path / "refresh-staging").resolve()
    reference = tmp_path / "reference.json"
    reference.write_text("{}\n", encoding="utf-8")
    parent_paths = MIGRATION.storage_paths(parent)
    trade_date = dt.date(2015, 1, 5)
    daily = MIGRATION.concordance.canonicalize_tushare_daily(
        daily_frame(),
        trade_date,
    )
    basic = MIGRATION.canonicalize_daily_basic(
        daily_basic_frame(),
        trade_date,
    )
    daily_path, daily_sidecar = MIGRATION._session_paths(  # pylint: disable=protected-access
        parent_paths["daily_sessions"],
        trade_date,
    )
    basic_path, basic_sidecar = MIGRATION._session_paths(  # pylint: disable=protected-access
        parent_paths["daily_basic_sessions"],
        trade_date,
    )
    daily_record = MIGRATION._frame_checkpoint(  # pylint: disable=protected-access
        kind="a_share_tushare_daily_session",
        frame=daily,
        data_path=daily_path,
        sidecar_path=daily_sidecar,
        trade_date=trade_date,
    )
    basic_record = MIGRATION._frame_checkpoint(  # pylint: disable=protected-access
        kind="a_share_tushare_daily_basic_session",
        frame=basic,
        data_path=basic_path,
        sidecar_path=basic_sidecar,
        trade_date=trade_date,
    )
    parent_manifest = {
        "version": 1,
        "kind": "a_share_tushare_daily_provider_migration_source_snapshot",
        "status": "complete_pending_canonical_build_and_acceptance",
        "protocol_sha256": MIGRATION.PROTOCOL_SHA256,
        "history_start": "2015-01-01",
        "through_date": trade_date.isoformat(),
        "new_daily_session_records": [daily_record],
        "daily_basic_session_records": [basic_record],
        "credential_value_persisted": False,
        "active_root_mutated": False,
        "forward_return_fields_read": False,
        "factor_values_read": False,
    }
    MIGRATION.atomic_write_json(parent_manifest, parent_paths["source_manifest"])
    parent_acceptance = {
        "status": "accepted_staging_pending_explicit_crash_safe_activation",
        "daily_source": "tushare",
        "through_date": trade_date.isoformat(),
        "source_manifest_path": str(parent_paths["source_manifest"]),
        "source_manifest_sha256": MIGRATION.canonical_file_digest(
            parent_paths["source_manifest"]
        ),
    }
    MIGRATION.atomic_write_json(
        parent_acceptance,
        parent_paths["acceptance_manifest"],
    )
    monkeypatch.setattr(MIGRATION, "resolve_data_root", lambda *args: parent)
    monkeypatch.setattr(
        MIGRATION,
        "latest_completed_session_date",
        lambda: dt.date(2015, 1, 6),
    )
    monkeypatch.setattr(
        MIGRATION,
        "validate_staging_acceptance",
        lambda root: parent_acceptance,
    )
    monkeypatch.setattr(
        MIGRATION,
        "_load_source_manifest",
        lambda **kwargs: (parent_manifest, {"rows": 123}),
    )
    return parent, staging, reference, parent_manifest


def test_refresh_seed_copies_verified_source_without_hardlinks_or_active_mutation(
    tmp_path,
    monkeypatch,
) -> None:
    parent, staging, reference, parent_manifest = _prepare_accepted_tushare_parent(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    parent_paths = MIGRATION.storage_paths(parent)
    parent_manifest_bytes = parent_paths["source_manifest"].read_bytes()

    result = MIGRATION.seed_refresh_source(
        parent_root=parent,
        staging_root=staging,
        through_date=dt.date(2015, 1, 6),
        reference_manifest=reference,
    )

    seed = json.loads(result.read_text(encoding="utf-8"))
    staging_paths = MIGRATION.storage_paths(staging)
    seeded_daily = Path(
        parent_manifest["new_daily_session_records"][0]["path"]
    )
    copied_daily, _ = MIGRATION._session_paths(  # pylint: disable=protected-access
        staging_paths["daily_sessions"],
        dt.date(2015, 1, 5),
    )
    assert seed["seeded_session_checkpoints"] == 2
    assert seed["hardlinks_used"] is False
    assert seed["provider_request_issued"] is False
    assert seed["active_root_mutated"] is False
    assert copied_daily.read_bytes() == seeded_daily.read_bytes()
    assert copied_daily.stat().st_ino != seeded_daily.stat().st_ino
    assert not staging_paths["calendar"].exists()
    assert not staging_paths["stock_basic"].exists()
    assert not staging_paths["raw_daily"].exists()
    assert not staging_paths["qlib"].exists()
    assert parent_paths["source_manifest"].read_bytes() == parent_manifest_bytes


def test_interrupted_refresh_seed_resumes_only_verified_missing_checkpoint(
    tmp_path,
    monkeypatch,
) -> None:
    parent, staging, reference, _ = _prepare_accepted_tushare_parent(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    first = MIGRATION.seed_refresh_source(
        parent_root=parent,
        staging_root=staging,
        through_date=dt.date(2015, 1, 6),
        reference_manifest=reference,
    )
    paths = MIGRATION.storage_paths(staging)
    daily_path, daily_sidecar = MIGRATION._session_paths(  # pylint: disable=protected-access
        paths["daily_sessions"],
        dt.date(2015, 1, 5),
    )
    basic_path, basic_sidecar = MIGRATION._session_paths(  # pylint: disable=protected-access
        paths["daily_basic_sessions"],
        dt.date(2015, 1, 5),
    )
    preserved_basic = basic_path.read_bytes()
    first.unlink()
    daily_path.unlink()
    daily_sidecar.unlink()

    resumed = MIGRATION.seed_refresh_source(
        parent_root=parent,
        staging_root=staging,
        through_date=dt.date(2015, 1, 6),
        reference_manifest=reference,
    )
    seed = json.loads(resumed.read_text(encoding="utf-8"))

    assert seed["copied_checkpoints_this_invocation"] == 1
    assert daily_path.is_file() and daily_sidecar.is_file()
    assert basic_path.read_bytes() == preserved_basic
    assert basic_sidecar.is_file()


def test_refresh_seed_rejects_a_hardlinked_checkpoint(
    tmp_path,
    monkeypatch,
) -> None:
    parent, staging, reference, _ = _prepare_accepted_tushare_parent(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    MIGRATION.seed_refresh_source(
        parent_root=parent,
        staging_root=staging,
        through_date=dt.date(2015, 1, 6),
        reference_manifest=reference,
    )
    parent_daily, _ = MIGRATION._session_paths(  # pylint: disable=protected-access
        MIGRATION.storage_paths(parent)["daily_sessions"],
        dt.date(2015, 1, 5),
    )
    seeded_daily, _ = MIGRATION._session_paths(  # pylint: disable=protected-access
        MIGRATION.storage_paths(staging)["daily_sessions"],
        dt.date(2015, 1, 5),
    )
    seeded_daily.unlink()
    os.link(parent_daily, seeded_daily)

    with pytest.raises(
        MIGRATION.TushareDailyMigrationError,
        match="hardlink is forbidden",
    ):
        MIGRATION.validate_refresh_seed(
            staging_root=staging,
            through_date=dt.date(2015, 1, 6),
            require_parent_active=True,
        )


class TwoSessionFakeProvider(FakeProvider):
    def trade_cal(self, **kwargs):
        self.calls.append(("trade_cal", kwargs))
        return pd.DataFrame(
            [
                {
                    "cal_date": "20150105",
                    "is_open": 1,
                    "pretrade_date": "20141231",
                },
                {
                    "cal_date": "20150106",
                    "is_open": 1,
                    "pretrade_date": "20150105",
                },
            ]
        )

    def daily(self, **kwargs):
        self.calls.append(("daily", kwargs))
        return daily_frame(trade_date=kwargs["trade_date"])

    def daily_basic(self, **kwargs):
        self.calls.append(("daily_basic", kwargs))
        return daily_basic_frame(trade_date=kwargs["trade_date"])


def test_seeded_refresh_sync_requests_only_sessions_after_parent_cutoff(
    tmp_path,
    monkeypatch,
) -> None:
    parent, staging, reference, parent_manifest = _prepare_accepted_tushare_parent(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    MIGRATION.seed_refresh_source(
        parent_root=parent,
        staging_root=staging,
        through_date=dt.date(2015, 1, 6),
        reference_manifest=reference,
    )
    monkeypatch.setattr(
        MIGRATION,
        "preflight",
        lambda **kwargs: {"ready": True, "failures": []},
    )
    monkeypatch.setattr(
        MIGRATION,
        "validate_reference_snapshot",
        lambda path, deep=False: ({"rows": 123}, "reference-sha"),
    )
    provider = TwoSessionFakeProvider()

    result = MIGRATION.sync_source(
        staging_root=staging,
        through_date=dt.date(2015, 1, 6),
        reference_manifest=reference,
        provider=provider,
        limiter=MIGRATION.AggregateRateLimiter(minimum_interval_seconds=0.0),
    )
    manifest = json.loads(result.read_text(encoding="utf-8"))
    requested_daily_dates = [
        kwargs["trade_date"]
        for name, kwargs in provider.calls
        if name == "daily"
    ]
    requested_basic_dates = [
        kwargs["trade_date"]
        for name, kwargs in provider.calls
        if name == "daily_basic"
    ]

    assert requested_daily_dates == ["20150106"]
    assert requested_basic_dates == ["20150106"]
    assert manifest["provider_calls_this_invocation"] == 6
    assert manifest["requested_daily_sessions_this_invocation"] == 1
    assert manifest["requested_daily_basic_sessions_this_invocation"] == 1
    assert manifest["reused_daily_checkpoints_this_invocation"] == 1
    assert manifest["reused_daily_basic_checkpoints_this_invocation"] == 1
    assert manifest["refresh_seed"]["parent_through_date"] == "2015-01-05"
    assert parent_manifest["through_date"] == "2015-01-05"
    validated, _ = REAL_LOAD_SOURCE_MANIFEST(
        staging_root=staging,
        reference_manifest=reference,
    )
    assert validated["through_date"] == "2015-01-06"


def test_changed_refresh_parent_manifest_stops_before_provider_request(
    tmp_path,
    monkeypatch,
) -> None:
    parent, staging, reference, _ = _prepare_accepted_tushare_parent(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    MIGRATION.seed_refresh_source(
        parent_root=parent,
        staging_root=staging,
        through_date=dt.date(2015, 1, 6),
        reference_manifest=reference,
    )
    parent_source = MIGRATION.storage_paths(parent)["source_manifest"]
    parent_source.write_text('{"changed":true}\n', encoding="utf-8")
    provider = TwoSessionFakeProvider()
    monkeypatch.setattr(
        MIGRATION,
        "preflight",
        lambda **kwargs: {"ready": True, "failures": []},
    )

    with pytest.raises(
        MIGRATION.TushareDailyMigrationError,
        match="parent manifest changed",
    ):
        MIGRATION.sync_source(
            staging_root=staging,
            through_date=dt.date(2015, 1, 6),
            reference_manifest=reference,
            provider=provider,
            limiter=MIGRATION.AggregateRateLimiter(
                minimum_interval_seconds=0.0,
            ),
        )

    assert provider.calls == []


def test_source_sync_is_resumable_and_reuses_completed_session_checkpoints(
    tmp_path,
    monkeypatch,
) -> None:
    staging = tmp_path / "staging"
    reference = tmp_path / "reference.json"
    reference.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        MIGRATION,
        "preflight",
        lambda **kwargs: {"ready": True, "failures": []},
    )
    monkeypatch.setattr(
        MIGRATION,
        "validate_reference_snapshot",
        lambda path, deep=False: ({"rows": 123}, "reference-sha"),
    )
    provider = FakeProvider()
    limiter = MIGRATION.AggregateRateLimiter(
        minimum_interval_seconds=0.0,
    )
    first = MIGRATION.sync_source(
        staging_root=staging,
        through_date=dt.date(2015, 1, 5),
        reference_manifest=reference,
        provider=provider,
        limiter=limiter,
    )
    first_manifest = json.loads(first.read_text(encoding="utf-8"))

    assert first_manifest["open_sessions"] == 1
    assert first_manifest["provider_calls_this_invocation"] == 6
    assert (
        first_manifest[
            "reference_daily_sessions_requested_this_invocation"
        ]
        == 0
    )
    assert [name for name, _ in provider.calls].count("daily") == 1
    assert [name for name, _ in provider.calls].count("daily_basic") == 1

    provider.calls.clear()
    second = MIGRATION.sync_source(
        staging_root=staging,
        through_date=dt.date(2015, 1, 5),
        reference_manifest=reference,
        provider=provider,
        limiter=limiter,
    )
    second_manifest = json.loads(second.read_text(encoding="utf-8"))

    assert second_manifest["provider_calls_this_invocation"] == 6
    assert provider.calls == []
    assert [name for name, _ in provider.calls].count("daily") == 0
    assert [name for name, _ in provider.calls].count("daily_basic") == 0


def test_completed_source_snapshot_cutoff_is_immutable_without_provider_calls(
    tmp_path,
    monkeypatch,
) -> None:
    staging = tmp_path / "staging"
    reference = tmp_path / "reference.json"
    reference.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        MIGRATION,
        "preflight",
        lambda **kwargs: {"ready": True, "failures": []},
    )
    monkeypatch.setattr(
        MIGRATION,
        "validate_reference_snapshot",
        lambda path, deep=False: ({"rows": 123}, "reference-sha"),
    )
    provider = FakeProvider()
    first = MIGRATION.sync_source(
        staging_root=staging,
        through_date=dt.date(2015, 1, 5),
        reference_manifest=reference,
        provider=provider,
        limiter=MIGRATION.AggregateRateLimiter(minimum_interval_seconds=0.0),
    )
    original = first.read_bytes()
    provider.calls.clear()

    with pytest.raises(
        MIGRATION.TushareDailyMigrationError,
        match="cutoff is immutable",
    ):
        MIGRATION.sync_source(
            staging_root=staging,
            through_date=dt.date(2015, 1, 6),
            reference_manifest=reference,
            provider=provider,
            limiter=MIGRATION.AggregateRateLimiter(
                minimum_interval_seconds=0.0,
            ),
        )

    assert provider.calls == []
    assert first.read_bytes() == original


def test_source_preflight_rejects_canonical_build_state_without_writes(
    tmp_path,
    monkeypatch,
) -> None:
    staging = tmp_path / "staging"
    active = tmp_path / "active"
    (staging / "raw" / "a_share" / "daily").mkdir(parents=True)
    universe = staging / "metadata" / "universe_latest.json"
    universe.parent.mkdir(parents=True)
    universe.write_text("symbol\n", encoding="utf-8")
    active.mkdir()
    monkeypatch.setattr(
        MIGRATION,
        "validate_reference_snapshot",
        lambda path: ({"rows": 1}, "reference-sha"),
    )
    monkeypatch.setattr(MIGRATION, "resolve_data_root", lambda root: active)
    monkeypatch.setattr(
        MIGRATION.pipeline,
        "inspect_existing_daily_sources",
        lambda path: ({"baostock"}, []),
    )
    monkeypatch.setattr(
        MIGRATION,
        "latest_completed_session_date",
        lambda: dt.date(2026, 7, 24),
    )
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    result = MIGRATION.preflight(
        staging_root=staging,
        through_date=dt.date(2026, 7, 24),
        token_configured=True,
    )

    assert result["ready"] is False
    assert "staging_canonical_daily_build_already_exists" in result["failures"]
    assert "staging_universe_manifest_already_exists" in result["failures"]
    assert result["provider_request_issued"] is False
    assert result["filesystem_write_performed"] is False
    assert sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")) == before


def test_completed_source_manifest_rejects_changed_checkpoint_sidecar(
    tmp_path,
    monkeypatch,
) -> None:
    staging = tmp_path / "staging"
    reference = tmp_path / "reference.json"
    reference.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        MIGRATION,
        "preflight",
        lambda **kwargs: {"ready": True, "failures": []},
    )
    monkeypatch.setattr(
        MIGRATION,
        "validate_reference_snapshot",
        lambda path, deep=False: ({"rows": 123}, "reference-sha"),
    )
    provider = FakeProvider()
    MIGRATION.sync_source(
        staging_root=staging,
        through_date=dt.date(2015, 1, 5),
        reference_manifest=reference,
        provider=provider,
        limiter=MIGRATION.AggregateRateLimiter(minimum_interval_seconds=0.0),
    )
    provider.calls.clear()
    paths = MIGRATION.storage_paths(staging)
    _, sidecar = MIGRATION._session_paths(  # pylint: disable=protected-access
        paths["daily_basic_sessions"],
        dt.date(2015, 1, 5),
    )
    changed = json.loads(sidecar.read_text(encoding="utf-8"))
    changed["rows"] = int(changed["rows"]) + 1
    sidecar.write_text(
        json.dumps(changed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        MIGRATION.TushareDailyMigrationError,
        match="checkpoint binding changed",
    ):
        MIGRATION.sync_source(
            staging_root=staging,
            through_date=dt.date(2015, 1, 5),
            reference_manifest=reference,
            provider=provider,
            limiter=MIGRATION.AggregateRateLimiter(
                minimum_interval_seconds=0.0,
            ),
        )
    assert provider.calls == []


def test_valid_raw_build_can_resume_materialization_without_rebuilding(
    tmp_path,
    monkeypatch,
) -> None:
    staging = tmp_path / "staging"
    paths = MIGRATION.storage_paths(staging)
    paths["raw_daily"].mkdir(parents=True)
    paths["universe"].parent.mkdir(parents=True, exist_ok=True)
    paths["source_manifest"].parent.mkdir(parents=True, exist_ok=True)
    paths["source_manifest"].write_text('{"source":"bound"}\n', encoding="utf-8")
    paths["universe"].write_text("[]\n", encoding="utf-8")
    for index in range(5000):
        (paths["raw_daily"] / f"sh{index:06d}.parquet").touch()
    source_manifest = {"through_date": "2026-07-24"}
    build = {
        "kind": "a_share_tushare_daily_provider_canonical_build",
        "status": "raw_passed_pending_optional_qlib_materialization",
        "protocol_sha256": MIGRATION.PROTOCOL_SHA256,
        "source_manifest_path": str(paths["source_manifest"]),
        "source_manifest_sha256": MIGRATION.canonical_file_digest(
            paths["source_manifest"]
        ),
        "through_date": "2026-07-24",
        "universe_path": str(paths["universe"]),
        "universe_sha256": MIGRATION.canonical_file_digest(paths["universe"]),
        "price_basis_audit": {
            "status": "passed",
            "daily_sources": ["tushare"],
            "failures": {},
        },
        "universe_counts": {
            "current_buyable_main_chinext": 4500,
            "current_factor_main_chinext_star": 5000,
        },
        "raw_files": 5000,
        "active_root_mutated": False,
        "forward_return_fields_read": False,
        "factor_values_read": False,
    }
    MIGRATION.atomic_write_json(build, paths["build_manifest"])
    monkeypatch.setattr(
        MIGRATION.pipeline,
        "inspect_existing_daily_sources",
        lambda path: ({"tushare"}, []),
    )

    validated = MIGRATION._validate_canonical_build_for_resume(  # pylint: disable=protected-access
        paths=paths,
        source_manifest=source_manifest,
    )

    assert validated["raw_files"] == 5000
    paths["universe"].write_text("[1]\n", encoding="utf-8")
    with pytest.raises(
        MIGRATION.TushareDailyMigrationError,
        match="canonical build is rejected",
    ):
        MIGRATION._validate_canonical_build_for_resume(  # pylint: disable=protected-access
            paths=paths,
            source_manifest=source_manifest,
        )


def test_staging_boundary_allows_only_activation_recovery_when_already_active(
    tmp_path,
    monkeypatch,
) -> None:
    staging = (tmp_path / "staging").resolve()
    monkeypatch.setattr(MIGRATION, "resolve_data_root", lambda *args: staging)

    with pytest.raises(
        MIGRATION.TushareDailyMigrationError,
        match="must differ from the active data root",
    ):
        MIGRATION.validate_staging_boundary(staging)
    assert (
        MIGRATION.validate_staging_boundary(staging, allow_active=True)
        == staging
    )


def test_activation_preflight_is_local_and_does_not_write(
    tmp_path,
    monkeypatch,
) -> None:
    active = (tmp_path / "active").resolve()
    staging = (tmp_path / "staging").resolve()
    active.mkdir()
    staging.mkdir()
    monkeypatch.delenv(MIGRATION.DATA_ROOT_ENV, raising=False)
    monkeypatch.setattr(
        MIGRATION,
        "validate_staging_boundary",
        lambda root, allow_active=False: Path(root).resolve(),
    )
    monkeypatch.setattr(
        MIGRATION,
        "validate_staging_acceptance",
        lambda root: {"through_date": "2026-07-24"},
    )
    monkeypatch.setattr(MIGRATION, "resolve_data_root", lambda *args: active)
    monkeypatch.setattr(
        MIGRATION.pipeline,
        "inspect_existing_daily_sources",
        lambda path: ({"baostock"}, []),
    )
    monkeypatch.setattr(
        MIGRATION,
        "_pointer_path",
        lambda: tmp_path / ".qlib_a_share_data_root",
    )
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    result = MIGRATION.activation_preflight(staging_root=staging)

    assert result["ready"] is True
    assert result["status"] == "ready_for_explicit_atomic_pointer_activation"
    assert result["filesystem_copy_performed"] is False
    assert result["pointer_write_performed"] is False
    assert sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")) == before


def _prepare_activation_test(
    *,
    tmp_path: Path,
    monkeypatch,
) -> tuple[Path, Path, dict[str, Path], dict[str, Path]]:
    active = (tmp_path / "active").resolve()
    staging = (tmp_path / "staging").resolve()
    active.mkdir()
    staging.mkdir()
    paths = MIGRATION.storage_paths(staging)
    paths["acceptance_manifest"].parent.mkdir(parents=True)
    paths["acceptance_manifest"].write_text(
        '{"status":"accepted"}\n',
        encoding="utf-8",
    )
    state = {"current": active}
    monkeypatch.delenv(MIGRATION.DATA_ROOT_ENV, raising=False)
    monkeypatch.setattr(
        MIGRATION,
        "validate_staging_boundary",
        lambda root, allow_active=False: Path(root).resolve(),
    )
    monkeypatch.setattr(
        MIGRATION,
        "validate_staging_acceptance",
        lambda root: {"through_date": "2026-07-24"},
    )
    monkeypatch.setattr(
        MIGRATION,
        "resolve_data_root",
        lambda *args: state["current"],
    )
    monkeypatch.setattr(
        MIGRATION.pipeline,
        "inspect_existing_daily_sources",
        lambda path: ({"baostock"}, []),
    )
    monkeypatch.setattr(
        MIGRATION,
        "seed_auxiliary_data",
        lambda **kwargs: {
            "copied_files_this_invocation": 0,
            "old_daily_root_copied": False,
            "old_qlib_root_copied": False,
        },
    )
    monkeypatch.setattr(
        MIGRATION.concordance,
        "ProcessLock",
        lambda path: nullcontext(),
    )
    monkeypatch.setattr(
        MIGRATION,
        "_pointer_path",
        lambda: tmp_path / ".qlib_a_share_data_root",
    )
    monkeypatch.setattr(MIGRATION, "_read_data_root_pointer_text", lambda: None)
    return active, staging, paths, state


def test_activation_writes_intent_switches_pointer_and_records_fresh_status(
    tmp_path,
    monkeypatch,
) -> None:
    active, staging, paths, state = _prepare_activation_test(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    switches: list[Path] = []

    def switch(target: Path) -> str:
        resolved = Path(target).resolve()
        switches.append(resolved)
        state["current"] = resolved
        return "pointer-sha"

    monkeypatch.setattr(MIGRATION, "_atomic_write_data_root_pointer", switch)
    monkeypatch.setattr(
        MIGRATION,
        "_fresh_status_with_pointer",
        lambda: {
            "data_root": str(staging),
            "qlib_calendar_end": "2026-07-24",
            "raw_parquet_files": 5_500,
            "price_basis": {
                "status": "passed",
                "daily_sources": ["tushare"],
                "price_basis": MIGRATION.pipeline.POINT_IN_TIME_PRICE_BASIS,
            },
        },
    )

    record_path = MIGRATION.activate_staging(
        staging_root=staging,
        confirm_activation=True,
    )

    assert record_path == paths["activation_record"]
    assert switches == [staging]
    intent = json.loads(paths["activation_intent"].read_text(encoding="utf-8"))
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert intent["previous_data_root"] == str(active)
    assert intent["previous_pointer_existed"] is False
    assert intent["previous_pointer_text"] is None
    assert record["status"] == "active_via_atomic_repository_pointer"
    assert record["daily_source"] == "tushare"
    assert record["old_daily_or_qlib_file_mutated"] is False


def test_activation_failure_restores_absent_pointer_state(
    tmp_path,
    monkeypatch,
) -> None:
    active, staging, paths, state = _prepare_activation_test(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    calls: list[tuple[str, object]] = []

    def switch(target: Path) -> str:
        resolved = Path(target).resolve()
        calls.append(("switch", resolved))
        state["current"] = resolved
        return "pointer-sha"

    def restore(previous_text: str | None) -> str | None:
        calls.append(("restore", previous_text))
        state["current"] = active
        return None

    monkeypatch.setattr(MIGRATION, "_atomic_write_data_root_pointer", switch)
    monkeypatch.setattr(MIGRATION, "_restore_data_root_pointer", restore)
    monkeypatch.setattr(
        MIGRATION,
        "_fresh_status_with_pointer",
        lambda: (_ for _ in ()).throw(
            MIGRATION.TushareDailyMigrationError("fresh status rejected")
        ),
    )

    with pytest.raises(
        MIGRATION.TushareDailyMigrationError,
        match="fresh status rejected",
    ):
        MIGRATION.activate_staging(
            staging_root=staging,
            confirm_activation=True,
        )

    assert calls == [("switch", staging), ("restore", None)]
    assert state["current"] == active
    failure = json.loads(paths["activation_failure"].read_text(encoding="utf-8"))
    assert failure["status"] == "failed_and_previous_pointer_restored"
    assert failure["previous_pointer_existed"] is False
    assert failure["previous_pointer_restored_exactly"] is True
