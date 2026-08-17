from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/a_share_tushare_limit_up_queue_development.py"
SPEC = importlib.util.spec_from_file_location("campaign115_development", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _session_hash(sessions: tuple[dt.date, ...]) -> str:
    payload = "".join(f"{session.isoformat()}\n" for session in sessions).encode()
    return hashlib.sha256(payload).hexdigest()


def _set_tiny_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = tmp_path / "development"
    partial = base / ".partial"
    final = base / "final"
    monkeypatch.setattr(MODULE, "BASE_ROOT", base)
    monkeypatch.setattr(MODULE, "PARTIAL_ROOT", partial)
    monkeypatch.setattr(MODULE, "FINAL_ROOT", final)
    monkeypatch.setattr(MODULE, "INTERNAL_MANIFEST", final / "source_manifest.json")
    monkeypatch.setattr(MODULE, "RUN_MANIFEST", tmp_path / "run.json")
    monkeypatch.setattr(MODULE, "FAILURE_RECORD", tmp_path / "failure.json")
    monkeypatch.setattr(MODULE, "LOCK_PATH", tmp_path / "development.lock")


def _set_tiny_calendar(
    sessions: tuple[dt.date, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(MODULE, "SESSION_COUNT", len(sessions))
    monkeypatch.setattr(MODULE, "SESSION_ORDER_SHA256", _session_hash(sessions))
    monkeypatch.setattr(MODULE, "_development_sessions", lambda: sessions)


def _raw(session: dt.date) -> pd.DataFrame:
    return pd.DataFrame(
        [
            [
                "000001.SZ",
                session.strftime("%Y%m%d"),
                "U",
                "145500",
                0,
            ]
        ],
        columns=MODULE.ADAPTER.RAW_FIELDS,
    )


def test_development_calendar_is_exactly_frozen() -> None:
    sessions = MODULE._development_sessions()
    assert len(sessions) == 1214
    assert sessions[0] == dt.date(2019, 1, 2)
    assert sessions[-1] == dt.date(2023, 12, 29)
    assert _session_hash(sessions) == MODULE.SESSION_ORDER_SHA256


def test_active_universe_uses_recorded_session_spans() -> None:
    spans = (
        ("SZ000001", "2019-01-01", "2023-12-31"),
        ("SH600000", "2020-01-01", "2023-12-31"),
    )
    assert MODULE._active_instruments(dt.date(2019, 1, 2), spans) == ("SZ000001",)
    assert MODULE._active_instruments(dt.date(2020, 1, 2), spans) == (
        "SH600000",
        "SZ000001",
    )


def test_real_plan_is_zero_credential_and_zero_provider_before_acceptance() -> None:
    plan = MODULE.build_plan(entitlement_confirmed=False)
    assert plan["ready"] is False
    assert plan["credential_loaded"] is False
    assert plan["provider_request_issued"] is False
    assert "acceptance_success_committed" in plan["blockers"]
    assert "manual_5000_point_entitlement_confirmation" in plan["blockers"]


def test_prefix_resume_requires_exact_checkpoint_and_request_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = (dt.date(2019, 1, 2), dt.date(2019, 1, 3))
    spans = (("SZ000001", "2019-01-01", "2023-12-31"),)
    _set_tiny_paths(tmp_path, monkeypatch)
    _set_tiny_calendar(sessions, monkeypatch)
    MODULE._create_overall_intent()
    MODULE._create_request_intent(sessions[0], 0)
    active = MODULE._active_instruments(sessions[0], spans)
    factor, quality = MODULE.ADAPTER.canonicalize_limit_queue_response(
        _raw(sessions[0]),
        trade_date=sessions[0],
        active_instruments=active,
    )
    MODULE._publish_session(sessions[0], factor, quality, active)

    prefix = MODULE._prefix_state(MODULE.PARTIAL_ROOT, sessions, spans)
    assert prefix["valid"] is True
    assert prefix["completed_sessions"] == 1
    assert prefix["next_session"] == "2019-01-03"

    MODULE._create_request_intent(sessions[1], 1)
    interrupted = MODULE._prefix_state(MODULE.PARTIAL_ROOT, sessions, spans)
    assert interrupted["valid"] is False
    assert interrupted["inflight_request_without_checkpoint"] is True
    assert interrupted["reason"] == "inflight_request_is_terminal_no_retry"


def test_prefix_rejects_unknown_or_nonprefix_partition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = (dt.date(2019, 1, 2), dt.date(2019, 1, 3))
    spans = (("SZ000001", "2019-01-01", "2023-12-31"),)
    _set_tiny_paths(tmp_path, monkeypatch)
    _set_tiny_calendar(sessions, monkeypatch)
    MODULE._create_overall_intent()
    (MODULE.PARTIAL_ROOT / "sessions" / ".orphan.tmp").mkdir()
    state = MODULE._prefix_state(MODULE.PARTIAL_ROOT, sessions, spans)
    assert state == {
        "valid": False,
        "exists": True,
        "reason": "unknown_session_entry",
    }


def test_tiny_development_sync_publishes_all_sessions_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = (dt.date(2019, 1, 2), dt.date(2019, 1, 3))
    spans = (("SZ000001", "2019-01-01", "2023-12-31"),)
    calls: list[dict[str, object]] = []

    class Client:
        def limit_list_d(self, **kwargs: object) -> pd.DataFrame:
            calls.append(kwargs)
            date_text = str(kwargs["trade_date"])
            return _raw(dt.datetime.strptime(date_text, "%Y%m%d").date())

    _set_tiny_paths(tmp_path, monkeypatch)
    _set_tiny_calendar(sessions, monkeypatch)
    monkeypatch.setattr(MODULE, "MINIMUM_U_SESSIONS", 1)
    monkeypatch.setattr(MODULE, "REQUEST_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(MODULE, "_instrument_spans", lambda: spans)
    monkeypatch.setattr(MODULE, "build_plan", lambda **_kwargs: {"ready": True})
    monkeypatch.setattr(MODULE.ACCEPTANCE, "_load_token", lambda _path: "dummy")
    monkeypatch.setattr(MODULE, "_create_client", lambda _token: Client())

    result = MODULE.run_sync(
        entitlement_confirmed=True,
        allow_network=True,
        confirm_development_sync=True,
    )
    assert result == 0
    assert [call["trade_date"] for call in calls] == ["20190102", "20190103"]
    assert all(
        call["fields"] == "ts_code,trade_date,limit,last_time,open_times"
        for call in calls
    )
    assert not MODULE.PARTIAL_ROOT.exists()
    assert MODULE.FINAL_ROOT.is_dir()
    assert MODULE.RUN_MANIFEST.is_file()
    manifest = json.loads(MODULE.RUN_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source"]["sessions"] == 2
    assert manifest["source"]["provider_calls_lifetime"] == 2
    assert manifest["daily_price_comparator_or_forward_return_fields_read"] is False


def test_provider_failure_deletes_partial_and_publishes_terminal_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = (dt.date(2019, 1, 2),)
    spans = (("SZ000001", "2019-01-01", "2023-12-31"),)

    class Client:
        @staticmethod
        def limit_list_d(**_kwargs: object) -> pd.DataFrame:
            raise RuntimeError("synthetic provider failure")

    _set_tiny_paths(tmp_path, monkeypatch)
    _set_tiny_calendar(sessions, monkeypatch)
    monkeypatch.setattr(MODULE, "_instrument_spans", lambda: spans)
    monkeypatch.setattr(MODULE, "build_plan", lambda **_kwargs: {"ready": True})
    monkeypatch.setattr(MODULE.ACCEPTANCE, "_load_token", lambda _path: "dummy")
    monkeypatch.setattr(MODULE, "_create_client", lambda _token: Client())

    with pytest.raises(MODULE.DevelopmentSourceError, match="failed closed"):
        MODULE.run_sync(
            entitlement_confirmed=True,
            allow_network=True,
            confirm_development_sync=True,
        )
    assert not MODULE.PARTIAL_ROOT.exists()
    assert not MODULE.FINAL_ROOT.exists()
    failure = json.loads(MODULE.FAILURE_RECORD.read_text(encoding="utf-8"))
    assert failure["provider_calls_issued_this_run"] == 1
    assert failure["failure_code"] == "provider_permission_or_request_failure"
    assert failure["retry_allowed"] is False
    assert failure["plaintext_provider_error_persisted"] is False


def test_sync_rejects_missing_flags_before_any_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_tiny_paths(tmp_path, monkeypatch)
    with pytest.raises(MODULE.DevelopmentSourceError, match="all explicit"):
        MODULE.run_sync(
            entitlement_confirmed=False,
            allow_network=False,
            confirm_development_sync=False,
        )
    assert not MODULE.PARTIAL_ROOT.exists()
    assert not MODULE.RUN_MANIFEST.exists()
    assert not MODULE.FAILURE_RECORD.exists()


def test_exclusive_lock_rejects_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.lock"
    target.write_text("", encoding="utf-8")
    link = tmp_path / "development.lock"
    link.symlink_to(target)
    monkeypatch.setattr(MODULE, "LOCK_PATH", link)
    with pytest.raises(MODULE.DevelopmentSourceError, match="lock open failed"):
        with MODULE._exclusive_lock():
            pytest.fail("symlink lock must never be acquired")
