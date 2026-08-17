#!/usr/bin/env python3
"""Frozen Campaign115 2019-2023 limit-queue development source workflow."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import shutil
import stat
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, TextIO

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_tushare_limit_up_queue_acceptance as ACCEPTANCE  # noqa: E402
import a_share_tushare_limit_up_queue_persistence as ADAPTER  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_development_source_protocol_20260809.json"
)
PROTOCOL_SHA256 = "836f10c9465c8cff03cf44233adf284f6e003d144c169ae003dd450a78c486e2"
RUNNER_FREEZE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_development_source_runner_freeze_v1_20260809.json"
)
RUNNER_TEST = (
    ROOT
    / "tests/data_collector_tests/test_a_share_tushare_limit_up_queue_development.py"
)
ADAPTER_SHA256 = "807d06f7dec4ca0a94beb28912b686e8cb01fbf36c7f473e69564de16af5f5dd"
ACCEPTANCE_RUNNER_SHA256 = (
    "920cd2183444c7a28c653f71846468aa8f0baf5031a039e7bdd17b59beac9b52"
)
CALENDAR = ROOT / "data/qlib/cn_a_share/calendars/day.txt"
CALENDAR_SHA256 = "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
UNIVERSE = ROOT / "data/qlib/cn_a_share/instruments/buyable_main_chinext.txt"
UNIVERSE_SHA256 = "77ccf8de2ed1e447e73b5d5ff1703fc2a8656d6adab34ef44017481730249db1"
SESSION_COUNT = 1214
SESSION_ORDER_SHA256 = (
    "63559370c9abfe3b8e24d133d1cc102658e9f3a144c507a1c12928d93ad95059"
)
MINIMUM_U_SESSIONS = 200
REQUEST_INTERVAL_SECONDS = 1.05

BASE_ROOT = (
    ROOT / "data/raw/a_share/rich/tushare/limit_up_queue_persistence/development"
)
PARTIAL_ROOT = BASE_ROOT / ".campaign115_2019_2023.partial"
FINAL_ROOT = BASE_ROOT / "campaign115_2019_2023"
INTERNAL_MANIFEST = FINAL_ROOT / "source_manifest.json"
RUN_MANIFEST = (
    ROOT
    / "data/metadata/rich_data/runs/campaign115_tushare_limit_queue_development_2019_2023.json"
)
FAILURE_RECORD = RUN_MANIFEST.with_name(
    "campaign115_tushare_limit_queue_development_2019_2023_failure.json"
)
LOCK_PATH = ROOT / "data/.campaign115_tushare_limit_queue_development.lock"
DOTENV = ROOT / ".env"


class DevelopmentSourceError(RuntimeError):
    """Fail-closed Campaign115 development source error."""


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError(
                "short write while publishing Campaign115 development evidence"
            )
        remaining = remaining[written:]


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def _exclusive_lock() -> Iterator[TextIO]:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(LOCK_PATH, flags, 0o600)
    except OSError as exc:
        raise DevelopmentSourceError("development lock open failed") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise DevelopmentSourceError("development lock identity is invalid")
        os.fchmod(descriptor, 0o600)
        handle = os.fdopen(descriptor, "a+", encoding="utf-8")
        descriptor = -1
        with handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise DevelopmentSourceError(
                    "another development sync is active"
                ) from exc
            yield handle
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _atomic_json(record: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    published = False
    try:
        descriptor = os.open(temporary, flags, 0o600)
        payload = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode(
            "utf-8"
        )
        _write_all(descriptor, payload)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, destination)
        published = True
        _fsync_directory(destination.parent)
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        cleanup = destination if published else temporary
        try:
            cleanup.unlink()
            _fsync_directory(destination.parent)
        except OSError:
            pass
        raise


def _runtime_bindings_valid() -> bool:
    try:
        freeze = json.loads(RUNNER_FREEZE.read_text(encoding="utf-8"))
        implementation = freeze["implementation"]
        return bool(
            freeze.get("kind")
            == "a_share_three_day_walkforward_campaign115_development_source_runner_freeze"
            and freeze.get("status")
            == "runner_v1_frozen_zero_network_before_development_source_access"
            and freeze.get("protocol", {}).get("sha256") == PROTOCOL_SHA256
            and digest(PROTOCOL) == PROTOCOL_SHA256
            and implementation.get("runner_path")
            == "scripts/a_share_tushare_limit_up_queue_development.py"
            and implementation.get("runner_sha256") == digest(Path(__file__).resolve())
            and implementation.get("test_path")
            == "tests/data_collector_tests/test_a_share_tushare_limit_up_queue_development.py"
            and implementation.get("test_sha256") == digest(RUNNER_TEST)
            and implementation.get("adapter_sha256") == ADAPTER_SHA256
            and digest(Path(ADAPTER.__file__).resolve()) == ADAPTER_SHA256
            and implementation.get("acceptance_runner_sha256")
            == ACCEPTANCE_RUNNER_SHA256
            and digest(Path(ACCEPTANCE.__file__).resolve()) == ACCEPTANCE_RUNNER_SHA256
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _development_sessions() -> tuple[dt.date, ...]:
    dates = tuple(
        dt.date.fromisoformat(line)
        for line in CALENDAR.read_text(encoding="utf-8").splitlines()
        if "2019-01-01" <= line <= "2023-12-31"
    )
    payload = "".join(f"{value.isoformat()}\n" for value in dates).encode("utf-8")
    if (
        len(dates) != SESSION_COUNT
        or hashlib.sha256(payload).hexdigest() != SESSION_ORDER_SHA256
    ):
        raise DevelopmentSourceError("development session order mismatch")
    return dates


def _instrument_spans() -> tuple[tuple[str, str, str], ...]:
    records: list[tuple[str, str, str]] = []
    for line in UNIVERSE.read_text(encoding="utf-8").splitlines():
        instrument, start, end = line.split("\t")
        records.append((instrument, start, end))
    return tuple(records)


def _active_instruments(
    session: dt.date, spans: tuple[tuple[str, str, str], ...]
) -> tuple[str, ...]:
    date_text = session.isoformat()
    result = tuple(
        sorted(
            {
                instrument
                for instrument, start, end in spans
                if start <= date_text <= end
            }
        )
    )
    if not result:
        raise DevelopmentSourceError(f"empty active universe for {date_text}")
    return result


def _ordered_digest(values: tuple[str, ...]) -> str:
    payload = "".join(f"{value}\n" for value in values).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise DevelopmentSourceError(f"JSON record is not an object: {path}")
    return record


def _intent_record() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign115_development_source_intent",
        "status": "development_source_prefix_sync_started",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol_sha256": PROTOCOL_SHA256,
        "runner_freeze_sha256": digest(RUNNER_FREEZE),
        "session_count": SESSION_COUNT,
        "session_order_sha256": SESSION_ORDER_SHA256,
        "fields": list(ADAPTER.RAW_FIELDS),
        "maximum_lifetime_provider_calls": SESSION_COUNT,
        "credential_value_printed_hashed_or_persisted": False,
    }


def _intent_valid(record: dict[str, Any]) -> bool:
    return bool(
        record.get("schema_version") == 1
        and record.get("kind")
        == "a_share_three_day_walkforward_campaign115_development_source_intent"
        and record.get("status") == "development_source_prefix_sync_started"
        and record.get("protocol_sha256") == PROTOCOL_SHA256
        and record.get("runner_freeze_sha256") == digest(RUNNER_FREEZE)
        and record.get("session_count") == SESSION_COUNT
        and record.get("session_order_sha256") == SESSION_ORDER_SHA256
        and record.get("fields") == list(ADAPTER.RAW_FIELDS)
        and record.get("maximum_lifetime_provider_calls") == SESSION_COUNT
        and record.get("credential_value_printed_hashed_or_persisted") is False
    )


def _session_paths(root: Path, session: dt.date) -> tuple[Path, Path]:
    session_root = root / "sessions" / session.isoformat()
    return session_root / "factor.parquet", session_root / "checkpoint.json"


def _request_intent_path(root: Path, session: dt.date) -> Path:
    return root / "requests" / f"{session.isoformat()}.json"


def _request_intent_valid(root: Path, session: dt.date, sequence_index: int) -> bool:
    path = _request_intent_path(root, session)
    if not path.is_file() or path.is_symlink():
        return False
    try:
        record = _read_json(path)
    except (OSError, ValueError, json.JSONDecodeError, DevelopmentSourceError):
        return False
    return bool(
        record.get("schema_version") == 1
        and record.get("kind")
        == "a_share_three_day_walkforward_campaign115_development_session_request_intent"
        and record.get("status") == "provider_call_authorized_and_may_have_started"
        and record.get("trade_date") == session.isoformat()
        and record.get("provider_calls_completed_before_this_intent") == sequence_index
        and record.get("provider_calls_authorized_including_this_intent")
        == sequence_index + 1
        and record.get("fields") == list(ADAPTER.RAW_FIELDS)
        and record.get("protocol_sha256") == PROTOCOL_SHA256
        and record.get("credential_value_printed_hashed_or_persisted") is False
    )


def _checkpoint_valid(
    root: Path,
    session: dt.date,
    active_instruments: tuple[str, ...],
    sequence_index: int,
) -> bool:
    frame_path, checkpoint_path = _session_paths(root, session)
    if (
        not frame_path.is_file()
        or frame_path.is_symlink()
        or not checkpoint_path.is_file()
        or checkpoint_path.is_symlink()
    ):
        return False
    try:
        checkpoint = _read_json(checkpoint_path)
    except (OSError, ValueError, json.JSONDecodeError, DevelopmentSourceError):
        return False
    return bool(
        checkpoint.get("schema_version") == 1
        and checkpoint.get("kind")
        == "a_share_three_day_walkforward_campaign115_development_session_checkpoint"
        and checkpoint.get("status") == "complete_immutable_session_partition"
        and checkpoint.get("trade_date") == session.isoformat()
        and checkpoint.get("fields") == list(ADAPTER.RAW_FIELDS)
        and checkpoint.get("protocol_sha256") == PROTOCOL_SHA256
        and checkpoint.get("adapter_sha256") == ADAPTER_SHA256
        and checkpoint.get("active_universe_names") == len(active_instruments)
        and checkpoint.get("active_universe_order_sha256")
        == _ordered_digest(active_instruments)
        and checkpoint.get("factor_rows") == len(active_instruments)
        and checkpoint.get("factor_byte_sha256") == digest(frame_path)
        and _request_intent_valid(root, session, sequence_index)
        and checkpoint.get("raw_provider_response_persisted") is False
        and checkpoint.get("daily_price_comparator_or_forward_return_fields_read")
        is False
    )


def _prefix_state(
    root: Path,
    sessions: tuple[dt.date, ...],
    spans: tuple[tuple[str, str, str], ...],
) -> dict[str, Any]:
    if not root.exists():
        return {
            "valid": True,
            "exists": False,
            "completed_sessions": 0,
            "next_session": sessions[0].isoformat(),
            "inflight_request_without_checkpoint": False,
        }
    intent_path = root / "intent.json"
    if (
        not root.is_dir()
        or root.is_symlink()
        or not intent_path.is_file()
        or intent_path.is_symlink()
    ):
        return {"valid": False, "exists": True, "reason": "partial_intent_missing"}
    try:
        if not _intent_valid(_read_json(intent_path)):
            return {"valid": False, "exists": True, "reason": "partial_intent_invalid"}
    except (OSError, ValueError, json.JSONDecodeError, DevelopmentSourceError):
        return {"valid": False, "exists": True, "reason": "partial_intent_invalid"}
    allowed_root_names = {"intent.json", "sessions", "requests", "source_manifest.json"}
    if any(item.name not in allowed_root_names for item in root.iterdir()):
        return {"valid": False, "exists": True, "reason": "unknown_partial_root_entry"}
    sessions_root = root / "sessions"
    requests_root = root / "requests"
    if not (
        sessions_root.is_dir()
        and not sessions_root.is_symlink()
        and requests_root.is_dir()
        and not requests_root.is_symlink()
    ):
        return {"valid": False, "exists": True, "reason": "partial_subroot_invalid"}
    expected_names = {session.isoformat() for session in sessions}
    actual_session_names = set()
    for item in sessions_root.iterdir():
        if item.name not in expected_names or not item.is_dir() or item.is_symlink():
            return {"valid": False, "exists": True, "reason": "unknown_session_entry"}
        actual_session_names.add(item.name)
    actual_request_names = set()
    for item in requests_root.iterdir():
        if (
            item.suffix != ".json"
            or item.stem not in expected_names
            or not item.is_file()
            or item.is_symlink()
        ):
            return {"valid": False, "exists": True, "reason": "unknown_request_entry"}
        actual_request_names.add(item.stem)
    completed = 0
    seen_gap = False
    inflight = False
    for sequence_index, session in enumerate(sessions):
        active = _active_instruments(session, spans)
        partition_present = session.isoformat() in actual_session_names
        request_present = session.isoformat() in actual_request_names
        valid_request = (
            _request_intent_valid(root, session, sequence_index)
            if request_present
            else False
        )
        if request_present and not valid_request:
            return {"valid": False, "exists": True, "reason": "request_intent_invalid"}
        valid_partition = (
            _checkpoint_valid(root, session, active, sequence_index)
            if partition_present
            else False
        )
        if valid_partition and not seen_gap and request_present:
            completed += 1
            continue
        if valid_partition or partition_present:
            return {
                "valid": False,
                "exists": True,
                "reason": "checkpoint_gap_incomplete_or_request_intent_missing",
            }
        seen_gap = True
        if request_present:
            inflight = True
        if inflight:
            break
    next_session = (
        sessions[completed].isoformat() if completed < len(sessions) else None
    )
    return {
        "valid": not inflight,
        "exists": True,
        "completed_sessions": completed,
        "next_session": next_session,
        "inflight_request_without_checkpoint": inflight,
        "reason": "inflight_request_is_terminal_no_retry" if inflight else None,
    }


def _acceptance_state() -> dict[str, Any]:
    return ACCEPTANCE.inspect_attempt_journal()


def build_plan(*, entitlement_confirmed: bool) -> dict[str, Any]:
    sessions: tuple[dt.date, ...] = ()
    spans: tuple[tuple[str, str, str], ...] = ()
    checks: dict[str, bool] = {
        "protocol_fingerprint": PROTOCOL.is_file()
        and digest(PROTOCOL) == PROTOCOL_SHA256,
        "runner_v1_runtime_binding": _runtime_bindings_valid(),
        "adapter_fingerprint": digest(Path(ADAPTER.__file__).resolve())
        == ADAPTER_SHA256,
        "acceptance_runner_fingerprint": digest(Path(ACCEPTANCE.__file__).resolve())
        == ACCEPTANCE_RUNNER_SHA256,
        "calendar_fingerprint": CALENDAR.is_file()
        and digest(CALENDAR) == CALENDAR_SHA256,
        "universe_fingerprint": UNIVERSE.is_file()
        and digest(UNIVERSE) == UNIVERSE_SHA256,
        "manual_5000_point_entitlement_confirmation": entitlement_confirmed,
        "no_terminal_development_failure": not FAILURE_RECORD.exists(),
        "no_prior_repository_manifest": not RUN_MANIFEST.exists(),
    }
    try:
        sessions = _development_sessions()
        spans = _instrument_spans()
        checks["development_session_order"] = True
    except (OSError, ValueError, DevelopmentSourceError):
        checks["development_session_order"] = False
    acceptance = _acceptance_state()
    checks["acceptance_success_committed"] = bool(
        acceptance.get("valid") is True
        and acceptance.get("terminal_evidence_state") == "success_committed"
    )
    partial = (
        _prefix_state(PARTIAL_ROOT, sessions, spans)
        if sessions and spans
        else {"valid": False, "exists": PARTIAL_ROOT.exists()}
    )
    checks["partial_prefix_valid_or_absent"] = bool(partial.get("valid"))
    final_pending = FINAL_ROOT.exists() and not RUN_MANIFEST.exists()
    checks["no_unfinalized_final_root"] = not final_pending
    checks["no_final_root_before_sync"] = not FINAL_ROOT.exists()
    blockers = [name for name, passed in checks.items() if not passed]
    ready = all(checks.values())
    return {
        "ready": ready,
        "exit_code_if_executed": 0 if ready else 2,
        "provider": "tushare",
        "api": "limit_list_d",
        "fields": list(ADAPTER.RAW_FIELDS),
        "development_start": "2019-01-01",
        "development_end": "2023-12-31",
        "session_count": len(sessions) if sessions else None,
        "completed_session_prefix": partial.get("completed_sessions", 0),
        "remaining_provider_calls": (
            len(sessions) - int(partial.get("completed_sessions", 0))
            if sessions
            else None
        ),
        "partial_state": partial,
        "checks": checks,
        "blockers": blockers,
        "credential_loaded": False,
        "provider_request_issued": False,
        "daily_price_comparator_or_forward_return_fields_read": False,
    }


def _create_overall_intent() -> None:
    PARTIAL_ROOT.mkdir(parents=True, exist_ok=False)
    (PARTIAL_ROOT / "sessions").mkdir()
    (PARTIAL_ROOT / "requests").mkdir()
    _atomic_json(_intent_record(), PARTIAL_ROOT / "intent.json")
    _fsync_directory(PARTIAL_ROOT)
    _fsync_directory(PARTIAL_ROOT.parent)


def _create_request_intent(session: dt.date, completed: int) -> None:
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign115_development_session_request_intent",
        "status": "provider_call_authorized_and_may_have_started",
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "trade_date": session.isoformat(),
        "provider_calls_completed_before_this_intent": completed,
        "provider_calls_authorized_including_this_intent": completed + 1,
        "fields": list(ADAPTER.RAW_FIELDS),
        "protocol_sha256": PROTOCOL_SHA256,
        "credential_value_printed_hashed_or_persisted": False,
    }
    _atomic_json(record, _request_intent_path(PARTIAL_ROOT, session))


def _create_client(token: str) -> Any:
    import tushare as ts

    ts.set_token(token)
    return ts.pro_api()


def _fetch_session(client: Any, session: dt.date) -> pd.DataFrame:
    result = client.limit_list_d(
        trade_date=session.strftime("%Y%m%d"),
        fields=",".join(ADAPTER.RAW_FIELDS),
    )
    if result is None:
        raise DevelopmentSourceError("provider returned None")
    return result.copy()


def _publish_session(
    session: dt.date,
    factor: pd.DataFrame,
    quality: dict[str, Any],
    active_instruments: tuple[str, ...],
) -> dict[str, Any]:
    sessions_root = PARTIAL_ROOT / "sessions"
    temporary = sessions_root / f".{session.isoformat()}.{os.getpid()}.tmp"
    final = sessions_root / session.isoformat()
    if temporary.exists() or final.exists():
        raise DevelopmentSourceError("session publication destination already exists")
    temporary.mkdir()
    frame_path = temporary / "factor.parquet"
    factor.to_parquet(frame_path, index=False)
    with frame_path.open("rb") as handle:
        os.fsync(handle.fileno())
    checkpoint = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign115_development_session_checkpoint",
        "status": "complete_immutable_session_partition",
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "trade_date": session.isoformat(),
        "fields": list(ADAPTER.RAW_FIELDS),
        "protocol_sha256": PROTOCOL_SHA256,
        "adapter_sha256": ADAPTER_SHA256,
        "active_universe_names": len(active_instruments),
        "active_universe_order_sha256": _ordered_digest(active_instruments),
        "source_rows": int(quality["source_rows"]),
        "valid_upper_limit_names": int(quality["valid_upper_limit_names"]),
        "factor_rows": int(len(factor)),
        "factor_byte_sha256": digest(frame_path),
        "raw_provider_response_persisted": False,
        "daily_price_comparator_or_forward_return_fields_read": False,
    }
    _atomic_json(checkpoint, temporary / "checkpoint.json")
    _fsync_directory(temporary)
    os.replace(temporary, final)
    _fsync_directory(sessions_root)
    return checkpoint


def _completed_checkpoints(
    root: Path,
    sessions: tuple[dt.date, ...],
) -> list[dict[str, Any]]:
    return [_read_json(_session_paths(root, session)[1]) for session in sessions]


def _internal_manifest_record(
    checkpoints: list[dict[str, Any]],
    provider_calls_this_run: int,
    resumed_sessions: int,
) -> dict[str, Any]:
    checkpoint_hashes = tuple(
        str(checkpoint["factor_byte_sha256"]) for checkpoint in checkpoints
    )
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign115_development_source",
        "status": "complete_2019_2023_source_pending_no_return_audit",
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": PROTOCOL_SHA256,
        },
        "runner_freeze": {
            "path": str(RUNNER_FREEZE.relative_to(ROOT)),
            "sha256": digest(RUNNER_FREEZE),
        },
        "source": {
            "provider": "tushare",
            "api": "limit_list_d",
            "fields": list(ADAPTER.RAW_FIELDS),
            "development_start": "2019-01-01",
            "development_end": "2023-12-31",
            "sessions": len(checkpoints),
            "provider_calls_lifetime": len(checkpoints),
            "provider_calls_this_run": provider_calls_this_run,
            "resumed_sessions": resumed_sessions,
        },
        "quality": {
            "sessions_with_valid_upper_limit_names": sum(
                int(checkpoint["valid_upper_limit_names"] > 0)
                for checkpoint in checkpoints
            ),
            "source_rows": sum(
                int(checkpoint["source_rows"]) for checkpoint in checkpoints
            ),
            "factor_rows": sum(
                int(checkpoint["factor_rows"]) for checkpoint in checkpoints
            ),
            "minimum_u_session_gate": MINIMUM_U_SESSIONS,
        },
        "checkpoint_factor_byte_order_sha256": _ordered_digest(checkpoint_hashes),
        "raw_provider_responses_persisted": False,
        "daily_price_comparator_or_forward_return_fields_read": False,
        "stress_2024_2025_opened": False,
        "selection_or_promotion_allowed": False,
    }


def _failure_code(exc: Exception) -> str:
    if isinstance(exc, ADAPTER.LimitQueueContractError):
        return "source_schema_or_formula_contract_failure"
    if isinstance(exc, DevelopmentSourceError):
        return "local_binding_checkpoint_or_publication_failure"
    return "provider_permission_or_request_failure"


def run_sync(
    *,
    entitlement_confirmed: bool,
    allow_network: bool,
    confirm_development_sync: bool,
) -> int:
    if not (entitlement_confirmed and allow_network and confirm_development_sync):
        raise DevelopmentSourceError("all explicit development sync flags are required")
    plan = build_plan(entitlement_confirmed=entitlement_confirmed)
    if not plan["ready"]:
        raise DevelopmentSourceError("development source plan is not ready")
    with _exclusive_lock():
        sessions = _development_sessions()
        spans = _instrument_spans()
        if not PARTIAL_ROOT.exists():
            _create_overall_intent()
        prefix = _prefix_state(PARTIAL_ROOT, sessions, spans)
        if not prefix.get("valid"):
            raise DevelopmentSourceError("partial prefix is not safely resumable")
        completed = int(prefix["completed_sessions"])
        resumed = completed
        completed_total = completed
        token = ACCEPTANCE._load_token(DOTENV)
        if not token:
            raise DevelopmentSourceError("Tushare token became unavailable")
        client = _create_client(token)
        token = None
        provider_calls_this_run = 0
        last_call_started: float | None = None
        try:
            for index, session in enumerate(sessions[completed:], start=completed):
                if last_call_started is not None:
                    remaining = REQUEST_INTERVAL_SECONDS - (
                        time.monotonic() - last_call_started
                    )
                    if remaining > 0:
                        time.sleep(remaining)
                _create_request_intent(session, index)
                last_call_started = time.monotonic()
                provider_calls_this_run += 1
                raw = _fetch_session(client, session)
                active = _active_instruments(session, spans)
                factor, quality = ADAPTER.canonicalize_limit_queue_response(
                    raw,
                    trade_date=session,
                    active_instruments=active,
                )
                if len(factor) != len(active):
                    raise DevelopmentSourceError("factor row count mismatch")
                _publish_session(session, factor, quality, active)
                completed_total = index + 1
            checkpoints = _completed_checkpoints(PARTIAL_ROOT, sessions)
            manifest = _internal_manifest_record(
                checkpoints,
                provider_calls_this_run,
                resumed,
            )
            if (
                manifest["quality"]["sessions_with_valid_upper_limit_names"]
                < MINIMUM_U_SESSIONS
            ):
                raise DevelopmentSourceError("minimum valid-U session gate failed")
            _atomic_json(manifest, PARTIAL_ROOT / "source_manifest.json")
            os.replace(PARTIAL_ROOT, FINAL_ROOT)
            _fsync_directory(FINAL_ROOT.parent)
            _atomic_json(manifest, RUN_MANIFEST)
            print(
                json.dumps(
                    {
                        "status": manifest["status"],
                        "sessions": SESSION_COUNT,
                        "provider_calls_this_run": provider_calls_this_run,
                        "resumed_sessions": resumed,
                        "provider_request_issued": provider_calls_this_run > 0,
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        except Exception as exc:
            shutil.rmtree(PARTIAL_ROOT, ignore_errors=True)
            if PARTIAL_ROOT.parent.exists():
                _fsync_directory(PARTIAL_ROOT.parent)
            failure = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign115_development_source_failure",
                "status": "terminal_development_source_failure_no_retry",
                "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "protocol_sha256": PROTOCOL_SHA256,
                "completed_sessions_before_failure": completed_total,
                "provider_calls_issued_this_run": provider_calls_this_run,
                "failure_code": _failure_code(exc),
                "plaintext_provider_error_persisted": False,
                "raw_provider_response_persisted": False,
                "credential_value_printed_hashed_or_persisted": False,
                "daily_price_comparator_or_forward_return_fields_read": False,
                "retry_allowed": False,
            }
            _atomic_json(failure, FAILURE_RECORD)
            raise DevelopmentSourceError(
                f"Campaign115 development sync failed closed: {failure['failure_code']}"
            ) from exc


def finalize_local() -> int:
    with _exclusive_lock():
        if RUN_MANIFEST.exists():
            raise DevelopmentSourceError(
                "repository development manifest already exists"
            )
        if not FINAL_ROOT.is_dir() or not INTERNAL_MANIFEST.is_file():
            raise DevelopmentSourceError("complete final root is unavailable")
        sessions = _development_sessions()
        spans = _instrument_spans()
        for sequence_index, session in enumerate(sessions):
            if not _checkpoint_valid(
                FINAL_ROOT,
                session,
                _active_instruments(session, spans),
                sequence_index,
            ):
                raise DevelopmentSourceError("final root checkpoint validation failed")
        manifest = _read_json(INTERNAL_MANIFEST)
        if not (
            manifest.get("kind")
            == "a_share_three_day_walkforward_campaign115_development_source"
            and manifest.get("status")
            == "complete_2019_2023_source_pending_no_return_audit"
            and manifest.get("protocol", {}).get("sha256") == PROTOCOL_SHA256
            and manifest.get("source", {}).get("sessions") == SESSION_COUNT
        ):
            raise DevelopmentSourceError("internal source manifest is invalid")
        _atomic_json(manifest, RUN_MANIFEST)
    print(
        json.dumps(
            {
                "status": "repository_manifest_finalized_locally",
                "provider_request_issued": False,
                "credential_loaded": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("--confirm-current-account-has-5000-points", action="store_true")
    run = subparsers.add_parser("run")
    run.add_argument("--confirm-current-account-has-5000-points", action="store_true")
    run.add_argument("--allow-network", action="store_true")
    run.add_argument("--confirm-development-sync", action="store_true")
    subparsers.add_parser("finalize-local")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "plan":
        plan = build_plan(
            entitlement_confirmed=bool(args.confirm_current_account_has_5000_points)
        )
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return int(plan["exit_code_if_executed"])
    if args.command == "finalize-local":
        return finalize_local()
    return run_sync(
        entitlement_confirmed=bool(args.confirm_current_account_has_5000_points),
        allow_network=bool(args.allow_network),
        confirm_development_sync=bool(args.confirm_development_sync),
    )


if __name__ == "__main__":
    raise SystemExit(main())
