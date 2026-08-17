from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import os
import stat
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/a_share_tushare_limit_up_queue_development_verify.py"
SPEC = importlib.util.spec_from_file_location("campaign115_development_verify", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _session_hash(sessions: tuple[dt.date, ...]) -> str:
    payload = "".join(f"{session.isoformat()}\n" for session in sessions).encode()
    return hashlib.sha256(payload).hexdigest()


def _raw(session: dt.date, *, event: bool = True) -> pd.DataFrame:
    records = (
        [["000001.SZ", session.strftime("%Y%m%d"), "U", "145500", 0]] if event else []
    )
    return pd.DataFrame(records, columns=MODULE.SOURCE.ADAPTER.RAW_FIELDS)


def _set_tiny_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = MODULE.SOURCE
    base = tmp_path / "development"
    partial = base / ".partial"
    final = base / "final"
    monkeypatch.setattr(source, "BASE_ROOT", base)
    monkeypatch.setattr(source, "PARTIAL_ROOT", partial)
    monkeypatch.setattr(source, "FINAL_ROOT", final)
    monkeypatch.setattr(source, "INTERNAL_MANIFEST", final / "source_manifest.json")
    monkeypatch.setattr(source, "RUN_MANIFEST", tmp_path / "source_run.json")
    monkeypatch.setattr(source, "FAILURE_RECORD", tmp_path / "source_failure.json")
    monkeypatch.setattr(source, "LOCK_PATH", tmp_path / "source.lock")
    monkeypatch.setattr(MODULE, "RECEIPT", tmp_path / "semantic_receipt.json")
    monkeypatch.setattr(MODULE, "LOCK_PATH", tmp_path / "verify.lock")
    monkeypatch.setattr(MODULE, "_protocol_valid", lambda: True)
    monkeypatch.setattr(MODULE, "runtime_bindings_valid", lambda: True)


def _publish_tiny_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    second_event: bool = True,
) -> tuple[dt.date, ...]:
    source = MODULE.SOURCE
    sessions = (dt.date(2019, 1, 2), dt.date(2019, 1, 3))
    spans = (("SZ000001", "2019-01-01", "2023-12-31"),)
    _set_tiny_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(source, "SESSION_COUNT", len(sessions))
    monkeypatch.setattr(source, "SESSION_ORDER_SHA256", _session_hash(sessions))
    monkeypatch.setattr(source, "MINIMUM_U_SESSIONS", 1)
    monkeypatch.setattr(source, "_development_sessions", lambda: sessions)
    monkeypatch.setattr(source, "_instrument_spans", lambda: spans)

    source._create_overall_intent()
    for index, session in enumerate(sessions):
        source._create_request_intent(session, index)
        active = source._active_instruments(session, spans)
        frame, quality = source.ADAPTER.canonicalize_limit_queue_response(
            _raw(session, event=second_event if index else True),
            trade_date=session,
            active_instruments=active,
        )
        source._publish_session(session, frame, quality, active)
    checkpoints = source._completed_checkpoints(source.PARTIAL_ROOT, sessions)
    manifest = source._internal_manifest_record(checkpoints, len(sessions), 0)
    source._atomic_json(manifest, source.PARTIAL_ROOT / "source_manifest.json")
    os.replace(source.PARTIAL_ROOT, source.FINAL_ROOT)
    source._atomic_json(manifest, source.RUN_MANIFEST)
    return sessions


def test_frozen_protocol_and_real_plan_are_zero_network() -> None:
    assert MODULE._protocol_valid() is True
    plan = MODULE.build_plan()
    assert plan["ready"] is False
    assert plan["parquet_candidate_values_read"] is False
    assert plan["comparison_values_read"] is False
    assert plan["daily_price_or_forward_return_values_read"] is False
    assert plan["credential_loaded"] is False
    assert plan["provider_request_issued"] is False


def test_plan_never_reads_parquet_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _publish_tiny_source(tmp_path, monkeypatch)

    def forbidden(*_args: object, **_kwargs: object) -> pd.DataFrame:
        raise AssertionError("plan must not read Parquet")

    monkeypatch.setattr(MODULE.pd, "read_parquet", forbidden)
    plan = MODULE.build_plan()
    assert plan["ready"] is True
    assert plan["parquet_candidate_values_read"] is False


def test_tiny_source_is_deeply_verified_and_published_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = _publish_tiny_source(tmp_path, monkeypatch)
    receipt = MODULE.verify_and_publish(confirmed=True)
    assert receipt["verification"]["session_count"] == len(sessions)
    assert receipt["verification"]["factor_rows"] == len(sessions)
    assert len(receipt["verification"]["dataset_sha256"]) == 64
    assert receipt["candidate_or_comparator_values_embedded"] is False
    assert receipt["historical_daily_price_or_forward_return_values_read"] is False
    assert receipt["provider_request_issued"] is False
    assert stat.S_IMODE(MODULE.RECEIPT.stat().st_mode) == 0o600

    inspected = MODULE.inspect_receipt()
    assert inspected["valid"] is True
    assert inspected["dataset_sha256"] == receipt["verification"]["dataset_sha256"]
    original = MODULE.RECEIPT.read_bytes()
    with pytest.raises(
        MODULE.DevelopmentSourceVerificationError,
        match="plan is not ready",
    ):
        MODULE.verify_and_publish(confirmed=True)
    assert MODULE.RECEIPT.read_bytes() == original


def test_verify_requires_explicit_local_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _publish_tiny_source(tmp_path, monkeypatch)
    with pytest.raises(
        MODULE.DevelopmentSourceVerificationError,
        match="confirm-semantic-verification",
    ):
        MODULE.verify_and_publish(confirmed=False)
    assert not MODULE.RECEIPT.exists()


def test_semantic_non_event_nonzero_tamper_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = _publish_tiny_source(tmp_path, monkeypatch)
    source = MODULE.SOURCE
    frame_path, checkpoint_path = source._session_paths(source.FINAL_ROOT, sessions[1])
    frame = pd.read_parquet(frame_path)
    frame.loc[:, "is_official_limit_up_event"] = False
    frame.loc[:, source.ADAPTER.FACTOR_NAME] = 0.1
    frame.to_parquet(frame_path, index=False)
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["factor_byte_sha256"] = source.digest(frame_path)
    checkpoint["valid_upper_limit_names"] = 0
    source._atomic_json(checkpoint, checkpoint_path)

    with pytest.raises(
        MODULE.DevelopmentSourceVerificationError,
        match="non-event row has a nonzero factor",
    ):
        MODULE.verify_and_publish(confirmed=True)
    assert not MODULE.RECEIPT.exists()


def test_unknown_session_file_fails_before_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = _publish_tiny_source(tmp_path, monkeypatch)
    session_root = MODULE.SOURCE._session_paths(MODULE.SOURCE.FINAL_ROOT, sessions[0])[
        0
    ].parent
    (session_root / "unexpected.bin").write_bytes(b"x")
    with pytest.raises(
        MODULE.DevelopmentSourceVerificationError,
        match="session partition entries changed",
    ):
        MODULE.verify_and_publish(confirmed=True)
    assert not MODULE.RECEIPT.exists()


def test_absent_and_malformed_receipt_are_credential_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_tiny_paths(tmp_path, monkeypatch)
    absent = MODULE.inspect_receipt()
    assert absent == {
        "valid": True,
        "status": "no_semantic_verification_receipt",
        "credential_loaded": False,
        "provider_request_issued": False,
    }
    MODULE.RECEIPT.write_text("{}\n", encoding="utf-8")
    with pytest.raises(
        MODULE.DevelopmentSourceVerificationError,
        match="receipt semantics changed",
    ):
        MODULE.inspect_receipt()
