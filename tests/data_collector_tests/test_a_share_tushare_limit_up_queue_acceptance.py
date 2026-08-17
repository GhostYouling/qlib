from __future__ import annotations

import importlib.util
import json
import stat
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "a_share_tushare_limit_up_queue_acceptance.py"
SPEC = importlib.util.spec_from_file_location("campaign115_acceptance", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _attempt_journal(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def test_plan_requires_manual_entitlement_and_is_zero_request() -> None:
    before = (
        MODULE.SUCCESS_MANIFEST.exists(),
        MODULE.FAILURE_RECORD.exists(),
        MODULE.FINAL_ROOT.exists(),
    )
    plan = MODULE.build_plan(entitlement_confirmed=False)
    after = (
        MODULE.SUCCESS_MANIFEST.exists(),
        MODULE.FAILURE_RECORD.exists(),
        MODULE.FINAL_ROOT.exists(),
    )
    assert plan["ready"] is False
    assert plan["exit_code_if_executed"] == 2
    assert plan["provider_request_issued"] is False
    assert plan["blockers"] == ["manual_5000_point_entitlement_confirmation"]
    assert before == after


def test_existing_attempt_intent_blocks_public_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    intent = tmp_path / "campaign115.intent"
    intent.write_text("consumed\n", encoding="utf-8")
    intent.chmod(0o600)
    monkeypatch.setattr(MODULE, "LOCK_PATH", intent)
    plan = MODULE.build_plan(entitlement_confirmed=True)
    assert plan["ready"] is False
    assert plan["blockers"] == ["one_shot_attempt_intent_available"]


def test_inspect_without_attempt_journal_is_zero_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(MODULE, "LOCK_PATH", tmp_path / "campaign115.intent")
    monkeypatch.setattr(MODULE, "SUCCESS_MANIFEST", tmp_path / "success.json")
    monkeypatch.setattr(MODULE, "FAILURE_RECORD", tmp_path / "failure.json")
    monkeypatch.setattr(MODULE, "FINAL_ROOT", tmp_path / "final")
    monkeypatch.setattr(MODULE, "FINAL_FRAME", tmp_path / "final/factor.parquet")
    monkeypatch.setattr(
        MODULE,
        "_load_token",
        lambda _path: pytest.fail("inspection must not load a credential"),
    )
    monkeypatch.setattr(
        MODULE,
        "_fetch_once",
        lambda _token: pytest.fail("inspection must not call the provider"),
    )

    inspection = MODULE.inspect_attempt_journal()
    assert inspection == {
        "status": "no_attempt_journal",
        "valid": True,
        "exit_code": 0,
        "attempt_journal_exists": False,
        "provider_call_may_have_been_issued": False,
        "provider_response_received": False,
        "terminal_evidence_state": "not_started",
        "retry_authorized_by_inspection": False,
        "credential_loaded": False,
        "provider_request_issued_by_inspection": False,
    }


def test_inspect_rejects_symlink_attempt_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target"
    target.write_text("{}\n", encoding="utf-8")
    target.chmod(0o600)
    intent = tmp_path / "campaign115.intent"
    intent.symlink_to(target)
    monkeypatch.setattr(MODULE, "LOCK_PATH", intent)
    monkeypatch.setattr(MODULE, "SUCCESS_MANIFEST", tmp_path / "success.json")
    monkeypatch.setattr(MODULE, "FAILURE_RECORD", tmp_path / "failure.json")
    monkeypatch.setattr(MODULE, "FINAL_ROOT", tmp_path / "final")
    monkeypatch.setattr(MODULE, "FINAL_FRAME", tmp_path / "final/factor.parquet")

    inspection = MODULE.inspect_attempt_journal()
    assert inspection["valid"] is False
    assert inspection["exit_code"] == 2
    assert inspection["attempt_journal_exists"] is True
    assert inspection["provider_request_issued_by_inspection"] is False


def test_owned_private_attempt_intent_is_valid_for_same_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    intent = tmp_path / "campaign115.intent"
    monkeypatch.setattr(MODULE, "LOCK_PATH", intent)
    lock, identity = MODULE._create_attempt_intent()
    try:
        plan = MODULE.build_plan(
            entitlement_confirmed=True,
            owned_attempt_identity=identity,
        )
        assert plan["ready"] is True
        assert plan["checks"]["one_shot_attempt_intent_available"] is True
    finally:
        lock.close()


def test_crash_safe_intent_prevents_a_second_provider_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call_count = 0

    def fail_after_provider_call(_token: str) -> pd.DataFrame:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("simulated transport failure")

    monkeypatch.setattr(MODULE, "LOCK_PATH", tmp_path / "campaign115.intent")
    monkeypatch.setattr(MODULE, "SUCCESS_MANIFEST", tmp_path / "success.json")
    monkeypatch.setattr(MODULE, "FAILURE_RECORD", tmp_path / "failure.json")
    monkeypatch.setattr(MODULE, "FINAL_ROOT", tmp_path / "final")
    monkeypatch.setattr(MODULE, "FINAL_FRAME", tmp_path / "final/factor.parquet")
    monkeypatch.setattr(MODULE, "TEMP_ROOT", tmp_path / ".partial")
    monkeypatch.setattr(MODULE, "_fetch_once", fail_after_provider_call)

    with pytest.raises(MODULE.AcceptanceError, match="failed closed"):
        MODULE.run_acceptance(entitlement_confirmed=True, confirm_run=True)
    assert call_count == 1
    assert MODULE.LOCK_PATH.is_file()
    assert MODULE.FAILURE_RECORD.is_file()
    assert [record["status"] for record in _attempt_journal(MODULE.LOCK_PATH)] == [
        "one_shot_attempt_consumed_before_provider_request",
        "provider_call_authorized_and_may_have_started",
        "terminal_failure_detected",
        "failure_record_publication_started",
    ]
    inspection = MODULE.inspect_attempt_journal()
    assert inspection["valid"] is True
    assert inspection["provider_call_may_have_been_issued"] is True
    assert inspection["provider_response_received"] is False
    assert inspection["terminal_evidence_state"] == "failure_committed"

    MODULE.FAILURE_RECORD.unlink()
    interrupted = MODULE.inspect_attempt_journal()
    assert interrupted["valid"] is True
    assert (
        interrupted["terminal_evidence_state"]
        == "interrupted_attempt_terminal_no_retry"
    )
    plan = MODULE.build_plan(entitlement_confirmed=True)
    assert plan["ready"] is False
    assert plan["blockers"] == ["one_shot_attempt_intent_available"]
    with pytest.raises(MODULE.AcceptanceError, match="plan is not ready"):
        MODULE.run_acceptance(entitlement_confirmed=True, confirm_run=True)
    assert call_count == 1


def test_run_creates_attempt_intent_before_loading_credential(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    credential_loads_after_intent: list[bool] = []
    provider_journal_state: list[str] = []

    def load_token_after_intent(_path: Path) -> str:
        credential_loads_after_intent.append(MODULE.LOCK_PATH.is_file())
        return "dummy"

    def fail_before_real_provider(_token: str) -> pd.DataFrame:
        provider_journal_state.append(
            str(_attempt_journal(MODULE.LOCK_PATH)[-1]["status"])
        )
        raise RuntimeError("synthetic no-network stop")

    monkeypatch.setattr(MODULE, "LOCK_PATH", tmp_path / "campaign115.intent")
    monkeypatch.setattr(MODULE, "SUCCESS_MANIFEST", tmp_path / "success.json")
    monkeypatch.setattr(MODULE, "FAILURE_RECORD", tmp_path / "failure.json")
    monkeypatch.setattr(MODULE, "FINAL_ROOT", tmp_path / "final")
    monkeypatch.setattr(MODULE, "FINAL_FRAME", tmp_path / "final/factor.parquet")
    monkeypatch.setattr(MODULE, "TEMP_ROOT", tmp_path / ".partial")
    monkeypatch.setattr(MODULE, "_load_token", load_token_after_intent)
    monkeypatch.setattr(MODULE, "_fetch_once", fail_before_real_provider)

    with pytest.raises(MODULE.AcceptanceError, match="failed closed"):
        MODULE.run_acceptance(entitlement_confirmed=True, confirm_run=True)
    assert credential_loads_after_intent
    assert all(credential_loads_after_intent)
    assert provider_journal_state == ["provider_call_authorized_and_may_have_started"]


def test_atomic_json_publishes_private_file_and_fsyncs_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "record.json"
    fsynced_directories: list[Path] = []
    real_fsync_directory = MODULE._fsync_directory

    def observe_directory_fsync(path: Path) -> None:
        fsynced_directories.append(path)
        real_fsync_directory(path)

    monkeypatch.setattr(MODULE, "_fsync_directory", observe_directory_fsync)
    MODULE._atomic_json({"status": "complete"}, destination)

    assert json.loads(destination.read_text(encoding="utf-8")) == {"status": "complete"}
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert fsynced_directories == [tmp_path]
    assert list(tmp_path.glob(".record.json.*.tmp")) == []


def test_write_all_retries_partial_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    written = bytearray()

    def partial_write(_descriptor: int, payload: memoryview) -> int:
        chunk = bytes(payload[:2])
        written.extend(chunk)
        return len(chunk)

    monkeypatch.setattr(MODULE.os, "write", partial_write)
    MODULE._write_all(123, b"abcdefg")
    assert bytes(written) == b"abcdefg"


def test_atomic_json_removes_published_record_when_directory_fsync_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "record.json"

    def fail_directory_fsync(_path: Path) -> None:
        raise OSError("synthetic directory fsync failure")

    monkeypatch.setattr(MODULE, "_fsync_directory", fail_directory_fsync)
    with pytest.raises(OSError, match="directory fsync failure"):
        MODULE._atomic_json({"status": "complete"}, destination)
    assert not destination.exists()
    assert list(tmp_path.glob(".record.json.*.tmp")) == []


def test_inspect_rejects_out_of_order_attempt_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    intent = tmp_path / "campaign115.intent"
    monkeypatch.setattr(MODULE, "LOCK_PATH", intent)
    monkeypatch.setattr(MODULE, "SUCCESS_MANIFEST", tmp_path / "success.json")
    monkeypatch.setattr(MODULE, "FAILURE_RECORD", tmp_path / "failure.json")
    monkeypatch.setattr(MODULE, "FINAL_ROOT", tmp_path / "final")
    monkeypatch.setattr(MODULE, "FINAL_FRAME", tmp_path / "final/factor.parquet")
    lock, _identity = MODULE._create_attempt_intent()
    lock.close()
    invalid_event = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign115_source_acceptance_attempt_event",
        "status": "provider_response_received",
        "recorded_at": "2026-08-09T00:00:00+00:00",
        "provider_calls_issued": 1,
        "credential_value_printed_hashed_or_persisted": False,
        "details": {"response_rows": 1},
    }
    with intent.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(invalid_event) + "\n")

    inspection = MODULE.inspect_attempt_journal()
    assert inspection["valid"] is False
    assert inspection["exit_code"] == 2
    assert "attempt_event_1_transition_invalid" in inspection["blockers"]


def test_success_journal_stops_at_publication_started_before_manifest_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    instruments = tuple(f"TEST{i:04d}" for i in range(MODULE.EXPECTED_ACTIVE_NAMES))
    factor = pd.DataFrame(
        {
            "ts_code": instruments,
            "trade_date": [MODULE.TRADE_DATE.isoformat()] * len(instruments),
            "limit_up_queue_persistence": [0.0] * len(instruments),
        }
    )

    monkeypatch.setattr(MODULE, "LOCK_PATH", tmp_path / "campaign115.intent")
    monkeypatch.setattr(MODULE, "SUCCESS_MANIFEST", tmp_path / "success.json")
    monkeypatch.setattr(MODULE, "FAILURE_RECORD", tmp_path / "failure.json")
    monkeypatch.setattr(MODULE, "FINAL_ROOT", tmp_path / "final")
    monkeypatch.setattr(MODULE, "TEMP_ROOT", tmp_path / ".partial")
    monkeypatch.setattr(MODULE, "_active_instruments", lambda: instruments)
    monkeypatch.setattr(
        MODULE,
        "_fetch_once",
        lambda _token: pd.DataFrame({"ts_code": ["000001.SZ"]}),
    )
    monkeypatch.setattr(
        MODULE.ADAPTER,
        "canonicalize_limit_queue_response",
        lambda *_args, **_kwargs: (factor, {"valid_upper_limit_names": 1}),
    )

    assert MODULE.run_acceptance(entitlement_confirmed=True, confirm_run=True) == 0
    assert MODULE.SUCCESS_MANIFEST.is_file()
    assert (MODULE.FINAL_ROOT / "factor.parquet").is_file()
    assert not MODULE.FAILURE_RECORD.exists()
    assert [record["status"] for record in _attempt_journal(MODULE.LOCK_PATH)] == [
        "one_shot_attempt_consumed_before_provider_request",
        "provider_call_authorized_and_may_have_started",
        "provider_response_received",
        "accepted_output_ready_for_publication",
        "success_manifest_publication_started",
    ]
    monkeypatch.setattr(MODULE, "FINAL_FRAME", MODULE.FINAL_ROOT / "factor.parquet")
    inspection = MODULE.inspect_attempt_journal()
    assert inspection["valid"] is True
    assert inspection["provider_call_may_have_been_issued"] is True
    assert inspection["provider_response_received"] is True
    assert inspection["terminal_evidence_state"] == "success_committed"

    tampered_manifest = json.loads(MODULE.SUCCESS_MANIFEST.read_text(encoding="utf-8"))
    tampered_manifest["status"] = "tampered"
    MODULE.SUCCESS_MANIFEST.write_text(
        json.dumps(tampered_manifest) + "\n", encoding="utf-8"
    )
    tampered_inspection = MODULE.inspect_attempt_journal()
    assert tampered_inspection["valid"] is False
    assert tampered_inspection["terminal_evidence_state"] == "terminal_evidence_invalid"
    assert "success_manifest_fixed_values_invalid" in tampered_inspection["blockers"]


def test_runtime_binding_rejects_a_tampered_freeze(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    changed = tmp_path / "changed-freeze.json"
    changed.write_text(
        '{"kind":"a_share_three_day_walkforward_campaign115_source_acceptance_runner_freeze"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(MODULE, "RUNNER_FREEZE", changed)
    assert MODULE._runtime_bindings_valid() is False


def test_plan_is_ready_only_when_manual_entitlement_is_asserted() -> None:
    plan = MODULE.build_plan(entitlement_confirmed=True)
    assert plan["ready"] is True
    assert plan["exit_code_if_executed"] == 0
    assert all(plan["checks"].values())


def test_run_rejects_missing_confirmations_before_writes() -> None:
    with pytest.raises(MODULE.AcceptanceError, match="both explicit"):
        MODULE.run_acceptance(entitlement_confirmed=False, confirm_run=False)
    assert not MODULE.SUCCESS_MANIFEST.exists()
    assert not MODULE.FAILURE_RECORD.exists()


def test_fetch_once_uses_exact_fixed_request(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class Client:
        def limit_list_d(self, **kwargs: object) -> pd.DataFrame:
            captured.update(kwargs)
            return pd.DataFrame(columns=MODULE.ADAPTER.RAW_FIELDS)

    class Tushare:
        @staticmethod
        def set_token(token: str) -> None:
            captured["token_seen_only_in_memory"] = token == "dummy"

        @staticmethod
        def pro_api() -> Client:
            return Client()

    monkeypatch.setitem(__import__("sys").modules, "tushare", Tushare)
    result = MODULE._fetch_once("dummy")
    assert result.empty
    assert captured == {
        "token_seen_only_in_memory": True,
        "trade_date": "20260713",
        "fields": "ts_code,trade_date,limit,last_time,open_times",
    }
