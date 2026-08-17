#!/usr/bin/env python3
"""One-shot Campaign115 Tushare limit-list acceptance workflow."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, TextIO

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_tushare_limit_up_queue_persistence as ADAPTER  # noqa: E402
from a_share_tushare_candidate49_future_session_workflow import (  # noqa: E402
    _load_token,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = (
    ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_115_source_acceptance_protocol_20260809.json"
)
PROTOCOL_SHA256 = "ad9b789fccada781e77662f95d7d3edaffc5371d605a85a9304a178e3ad4cc6c"
RUNNER_FREEZE = (
    ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_115_source_acceptance_runner_freeze_v5_20260809.json"
)
RUNNER_TEST = (
    ROOT
    / "tests/data_collector_tests/test_a_share_tushare_limit_up_queue_acceptance.py"
)
CONTRACT_SHA256 = ADAPTER.CONTRACT_SHA256
ADAPTER_SHA256 = "807d06f7dec4ca0a94beb28912b686e8cb01fbf36c7f473e69564de16af5f5dd"
UNIVERSE = ROOT / "data/qlib/cn_a_share/instruments/buyable_main_chinext.txt"
UNIVERSE_SHA256 = "77ccf8de2ed1e447e73b5d5ff1703fc2a8656d6adab34ef44017481730249db1"
CALENDAR = ROOT / "data/qlib/cn_a_share/calendars/day.txt"
CALENDAR_SHA256 = "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
DOTENV = ROOT / ".env"
TRADE_DATE = dt.date(2026, 7, 13)
EXPECTED_ACTIVE_NAMES = 4592
SUCCESS_MANIFEST = (
    ROOT
    / "data/metadata/rich_data/runs/campaign115_tushare_limit_queue_acceptance_20260713.json"
)
FAILURE_RECORD = (
    ROOT
    / "data/metadata/rich_data/runs/campaign115_tushare_limit_queue_acceptance_20260713_failure.json"
)
FINAL_ROOT = (
    ROOT
    / "data/raw/a_share/rich/tushare/limit_up_queue_persistence/acceptance/campaign115_20260713"
)
FINAL_FRAME = FINAL_ROOT / "factor.parquet"
FINAL_FRAME_RELATIVE = (
    "data/raw/a_share/rich/tushare/limit_up_queue_persistence/acceptance/"
    "campaign115_20260713/factor.parquet"
)
TEMP_ROOT = FINAL_ROOT.parent / ".campaign115_20260713.tmp"
LOCK_PATH = ROOT / "data/.campaign115_tushare_limit_queue_acceptance.lock"
MAX_ATTEMPT_JOURNAL_BYTES = 64 * 1024


class AcceptanceError(RuntimeError):
    """Fail-closed Campaign115 acceptance error."""


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _active_instruments() -> tuple[str, ...]:
    values: list[str] = []
    for line in UNIVERSE.read_text(encoding="utf-8").splitlines():
        instrument, start, end = line.split("\t")
        if start <= TRADE_DATE.isoformat() <= end:
            values.append(instrument)
    result = tuple(sorted(set(values)))
    if len(result) != EXPECTED_ACTIVE_NAMES:
        raise AcceptanceError("fixed-date active universe count mismatch")
    return result


def _dotenv_state(*, inspect_token: bool = True) -> dict[str, Any]:
    regular = DOTENV.is_file() and not DOTENV.is_symlink()
    mode = f"{stat.S_IMODE(DOTENV.stat().st_mode):04o}" if regular else None
    ignored = (
        subprocess.run(
            ["git", "check-ignore", "-q", "--", str(DOTENV)],
            cwd=ROOT,
            check=False,
        ).returncode
        == 0
    )
    present = None
    if inspect_token:
        token = _load_token(DOTENV)
        present = bool(token)
        token = None
    return {
        "regular_non_symlink": regular,
        "mode": mode,
        "git_ignored": ignored,
        "token_present": present,
        "secret_printed_hashed_or_persisted": False,
    }


def _runtime_bindings_valid() -> bool:
    """Require the external v5 freeze to bind this exact executable and test."""

    try:
        freeze = json.loads(RUNNER_FREEZE.read_text(encoding="utf-8"))
        implementation = freeze["implementation"]
        protocol = freeze["protocol"]
        return bool(
            freeze.get("kind")
            == "a_share_three_day_walkforward_campaign115_source_acceptance_runner_freeze"
            and freeze.get("status")
            == "runner_v5_read_only_attempt_journal_forensics_frozen"
            and protocol.get("sha256") == PROTOCOL_SHA256
            and digest(PROTOCOL) == PROTOCOL_SHA256
            and implementation.get("runner_path")
            == "scripts/a_share_tushare_limit_up_queue_acceptance.py"
            and implementation.get("runner_sha256") == digest(Path(__file__).resolve())
            and implementation.get("test_path")
            == "tests/data_collector_tests/test_a_share_tushare_limit_up_queue_acceptance.py"
            and implementation.get("test_sha256") == digest(RUNNER_TEST)
            and implementation.get("adapter_sha256") == ADAPTER_SHA256
            and digest(Path(ADAPTER.__file__).resolve()) == ADAPTER_SHA256
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _attempt_intent_state_valid(
    owned_identity: tuple[int, int] | None = None,
) -> bool:
    """Accept no marker for a public plan, or only this run's pinned marker."""

    if owned_identity is None:
        return not LOCK_PATH.exists() and not LOCK_PATH.is_symlink()
    try:
        metadata = LOCK_PATH.lstat()
    except OSError:
        return False
    return bool(
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_nlink == 1
        and stat.S_IMODE(metadata.st_mode) == 0o600
        and (metadata.st_dev, metadata.st_ino) == owned_identity
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("short write while publishing Campaign115 evidence")
        remaining = remaining[written:]


def _create_attempt_intent() -> tuple[TextIO, tuple[int, int]]:
    """Durably consume the one allowed attempt before any provider request."""

    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(LOCK_PATH, flags, 0o600)
    except FileExistsError as exc:
        raise AcceptanceError(
            "Campaign115 one-shot attempt is already consumed"
        ) from exc
    try:
        metadata = os.fstat(descriptor)
        identity = (metadata.st_dev, metadata.st_ino)
        intent = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign115_source_acceptance_attempt_intent",
            "status": "one_shot_attempt_consumed_before_provider_request",
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "trade_date": TRADE_DATE.isoformat(),
            "provider": "tushare",
            "api": "limit_list_d",
            "maximum_provider_calls": 1,
            "protocol_sha256": PROTOCOL_SHA256,
            "credential_value_printed_hashed_or_persisted": False,
        }
        payload = (json.dumps(intent, ensure_ascii=False) + "\n").encode("utf-8")
        _write_all(descriptor, payload)
        os.fsync(descriptor)
        _fsync_directory(LOCK_PATH.parent)
        handle = os.fdopen(descriptor, "r+", encoding="utf-8")
        descriptor = -1
        return handle, identity
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _append_attempt_event(
    lock: TextIO,
    identity: tuple[int, int],
    *,
    status_value: str,
    provider_calls_issued: int,
    details: dict[str, Any] | None = None,
) -> None:
    """Append and durably publish a credential-safe attempt-journal event."""

    if not _attempt_intent_state_valid(identity):
        raise AcceptanceError("attempt intent identity changed")
    metadata = os.fstat(lock.fileno())
    if (metadata.st_dev, metadata.st_ino) != identity:
        raise AcceptanceError("attempt intent handle identity changed")
    event: dict[str, Any] = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign115_source_acceptance_attempt_event",
        "status": status_value,
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provider_calls_issued": provider_calls_issued,
        "credential_value_printed_hashed_or_persisted": False,
    }
    if details:
        event["details"] = details
    lock.seek(0, os.SEEK_END)
    lock.write(json.dumps(event, ensure_ascii=False) + "\n")
    lock.flush()
    os.fsync(lock.fileno())


def _aware_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _read_attempt_journal() -> tuple[list[dict[str, Any]] | None, str | None]:
    """Read the bounded private journal without loading a credential."""

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(LOCK_PATH, flags)
    except FileNotFoundError:
        return None, None
    except OSError:
        return None, "attempt_journal_open_failed"
    try:
        metadata = os.fstat(descriptor)
        try:
            path_metadata = LOCK_PATH.lstat()
        except OSError:
            return None, "attempt_journal_path_changed_during_read"
        if not (
            stat.S_ISREG(metadata.st_mode)
            and metadata.st_nlink == 1
            and stat.S_IMODE(metadata.st_mode) == 0o600
            and (metadata.st_dev, metadata.st_ino)
            == (path_metadata.st_dev, path_metadata.st_ino)
        ):
            return None, "attempt_journal_file_identity_or_mode_invalid"
        if metadata.st_size <= 0 or metadata.st_size > MAX_ATTEMPT_JOURNAL_BYTES:
            return None, "attempt_journal_size_invalid"
        chunks: list[bytes] = []
        remaining = metadata.st_size + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(remaining, 8192))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) != metadata.st_size or not payload.endswith(b"\n"):
            return None, "attempt_journal_incomplete_read_or_line"
        try:
            lines = payload.decode("utf-8").splitlines()
            records = [json.loads(line) for line in lines]
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, "attempt_journal_json_invalid"
        if not all(isinstance(record, dict) for record in records):
            return None, "attempt_journal_record_type_invalid"
        return records, None
    finally:
        os.close(descriptor)


def _read_private_json_record(
    path: Path, *, label: str
) -> tuple[dict[str, Any] | None, str | None]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return None, f"{label}_open_failed"
    try:
        metadata = os.fstat(descriptor)
        try:
            path_metadata = path.lstat()
        except OSError:
            return None, f"{label}_path_changed_during_read"
        if not (
            stat.S_ISREG(metadata.st_mode)
            and metadata.st_nlink == 1
            and stat.S_IMODE(metadata.st_mode) == 0o600
            and (metadata.st_dev, metadata.st_ino)
            == (path_metadata.st_dev, path_metadata.st_ino)
        ):
            return None, f"{label}_file_identity_or_mode_invalid"
        if metadata.st_size <= 0 or metadata.st_size > MAX_ATTEMPT_JOURNAL_BYTES:
            return None, f"{label}_size_invalid"
        chunks: list[bytes] = []
        remaining = metadata.st_size + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(remaining, 8192))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) != metadata.st_size or not payload.endswith(b"\n"):
            return None, f"{label}_incomplete_read_or_line"
        try:
            record = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, f"{label}_json_invalid"
        if not isinstance(record, dict):
            return None, f"{label}_record_type_invalid"
        return record, None
    finally:
        os.close(descriptor)


def _validate_success_evidence(record: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    expected_keys = {
        "schema_version",
        "kind",
        "status",
        "recorded_at",
        "protocol",
        "contract",
        "request",
        "factor_frame",
        "quality",
        "raw_provider_response_persisted",
        "credential_value_printed_hashed_or_persisted",
        "daily_price_comparator_or_forward_return_fields_read",
        "selection_or_promotion_allowed",
    }
    if set(record) != expected_keys:
        blockers.append("success_manifest_keys_invalid")
    if not (
        record.get("schema_version") == 1
        and record.get("kind")
        == "a_share_three_day_walkforward_campaign115_source_acceptance"
        and record.get("status")
        == "accepted_entitlement_schema_formula_and_single_session_pending_2019_2023_atomic_source"
        and _aware_timestamp(record.get("recorded_at"))
        and record.get("protocol")
        == {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": PROTOCOL_SHA256,
        }
        and record.get("contract")
        == {
            "path": str(ADAPTER.DEFAULT_CONTRACT.relative_to(ROOT)),
            "sha256": CONTRACT_SHA256,
        }
        and record.get("request")
        == {
            "provider": "tushare",
            "api": "limit_list_d",
            "trade_date": TRADE_DATE.isoformat(),
            "fields": list(ADAPTER.RAW_FIELDS),
            "provider_calls_issued": 1,
        }
        and record.get("raw_provider_response_persisted") is False
        and record.get("credential_value_printed_hashed_or_persisted") is False
        and record.get("daily_price_comparator_or_forward_return_fields_read") is False
        and record.get("selection_or_promotion_allowed") is False
    ):
        blockers.append("success_manifest_fixed_values_invalid")
    frame = record.get("factor_frame")
    if not (
        isinstance(frame, dict)
        and set(frame) == {"path", "sha256", "rows"}
        and frame.get("path") == FINAL_FRAME_RELATIVE
        and isinstance(frame.get("sha256"), str)
        and len(frame["sha256"]) == 64
        and all(character in "0123456789abcdef" for character in frame["sha256"])
        and frame.get("rows") == EXPECTED_ACTIVE_NAMES
        and FINAL_FRAME.is_file()
        and not FINAL_FRAME.is_symlink()
        and digest(FINAL_FRAME) == frame["sha256"]
    ):
        blockers.append("success_factor_frame_binding_invalid")
    quality = record.get("quality")
    if not (
        isinstance(quality, dict)
        and type(quality.get("valid_upper_limit_names")) is int
        and quality["valid_upper_limit_names"] >= 1
    ):
        blockers.append("success_quality_summary_invalid")
    return blockers


def _validate_failure_evidence(
    record: dict[str, Any], last_event: dict[str, Any] | None
) -> list[str]:
    blockers: list[str] = []
    expected_keys = {
        "schema_version",
        "kind",
        "status",
        "recorded_at",
        "trade_date",
        "provider_calls_issued",
        "failure_code",
        "plaintext_provider_error_persisted",
        "raw_provider_response_persisted",
        "credential_value_printed_hashed_or_persisted",
        "daily_price_comparator_or_forward_return_fields_read",
        "retry_allowed",
    }
    if set(record) != expected_keys:
        blockers.append("failure_record_keys_invalid")
    failure_code = record.get("failure_code")
    provider_calls = record.get("provider_calls_issued")
    if not (
        record.get("schema_version") == 1
        and record.get("kind")
        == "a_share_three_day_walkforward_campaign115_source_acceptance_failure"
        and record.get("status") == "terminal_source_acceptance_failure_no_retry"
        and _aware_timestamp(record.get("recorded_at"))
        and record.get("trade_date") == TRADE_DATE.isoformat()
        and type(provider_calls) is int
        and provider_calls in (0, 1)
        and failure_code
        in {
            "source_schema_or_formula_contract_failure",
            "local_binding_or_atomic_publication_failure",
            "provider_permission_or_request_failure",
        }
        and record.get("plaintext_provider_error_persisted") is False
        and record.get("raw_provider_response_persisted") is False
        and record.get("credential_value_printed_hashed_or_persisted") is False
        and record.get("daily_price_comparator_or_forward_return_fields_read") is False
        and record.get("retry_allowed") is False
    ):
        blockers.append("failure_record_fixed_values_invalid")
    if not (
        isinstance(last_event, dict)
        and last_event.get("status") == "failure_record_publication_started"
        and last_event.get("provider_calls_issued") == provider_calls
        and isinstance(last_event.get("details"), dict)
        and last_event["details"].get("failure_code") == failure_code
    ):
        blockers.append("failure_record_journal_binding_invalid")
    return blockers


def _validate_attempt_journal(records: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if not records:
        return ["attempt_journal_empty"]
    initial = records[0]
    expected_initial = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign115_source_acceptance_attempt_intent",
        "status": "one_shot_attempt_consumed_before_provider_request",
        "trade_date": TRADE_DATE.isoformat(),
        "provider": "tushare",
        "api": "limit_list_d",
        "maximum_provider_calls": 1,
        "protocol_sha256": PROTOCOL_SHA256,
        "credential_value_printed_hashed_or_persisted": False,
    }
    if set(initial) != set(expected_initial) | {"created_at"}:
        blockers.append("attempt_intent_keys_invalid")
    if any(initial.get(key) != value for key, value in expected_initial.items()):
        blockers.append("attempt_intent_values_invalid")
    if not _aware_timestamp(initial.get("created_at")):
        blockers.append("attempt_intent_timestamp_invalid")

    transitions = {
        "one_shot_attempt_consumed_before_provider_request": {
            "provider_call_authorized_and_may_have_started",
            "terminal_failure_detected",
        },
        "provider_call_authorized_and_may_have_started": {
            "provider_response_received",
            "terminal_failure_detected",
        },
        "provider_response_received": {
            "accepted_output_ready_for_publication",
            "terminal_failure_detected",
        },
        "accepted_output_ready_for_publication": {
            "success_manifest_publication_started",
            "terminal_failure_detected",
        },
        "success_manifest_publication_started": set(),
        "terminal_failure_detected": {"failure_record_publication_started"},
        "failure_record_publication_started": set(),
    }
    no_details = {
        "provider_call_authorized_and_may_have_started",
        "success_manifest_publication_started",
    }
    previous_status = str(initial.get("status"))
    previous_provider_calls = 0
    previous_failure_code: str | None = None
    for index, event in enumerate(records[1:], start=1):
        common_keys = {
            "schema_version",
            "kind",
            "status",
            "recorded_at",
            "provider_calls_issued",
            "credential_value_printed_hashed_or_persisted",
        }
        status_value = event.get("status")
        status_text = status_value if isinstance(status_value, str) else ""
        allowed_keys = common_keys | (
            {"details"} if status_text not in no_details else set()
        )
        if set(event) != allowed_keys:
            blockers.append(f"attempt_event_{index}_keys_invalid")
        if not (
            event.get("schema_version") == 1
            and event.get("kind")
            == "a_share_three_day_walkforward_campaign115_source_acceptance_attempt_event"
            and event.get("credential_value_printed_hashed_or_persisted") is False
            and _aware_timestamp(event.get("recorded_at"))
        ):
            blockers.append(f"attempt_event_{index}_common_values_invalid")
        if status_text not in transitions.get(previous_status, set()):
            blockers.append(f"attempt_event_{index}_transition_invalid")
        provider_calls = event.get("provider_calls_issued")
        if type(provider_calls) is not int or provider_calls not in (0, 1):
            blockers.append(f"attempt_event_{index}_provider_call_count_invalid")
            provider_calls = previous_provider_calls
        if provider_calls < previous_provider_calls:
            blockers.append(f"attempt_event_{index}_provider_call_count_decreased")
        if status_text != "provider_call_authorized_and_may_have_started" and (
            provider_calls != previous_provider_calls
        ):
            blockers.append(f"attempt_event_{index}_provider_call_count_changed")
        if (
            status_text
            in {
                "provider_call_authorized_and_may_have_started",
                "provider_response_received",
                "accepted_output_ready_for_publication",
                "success_manifest_publication_started",
            }
            and provider_calls != 1
        ):
            blockers.append(f"attempt_event_{index}_provider_call_count_wrong")
        details = event.get("details")
        if status_text == "provider_response_received":
            if not (
                isinstance(details, dict)
                and set(details) == {"response_rows"}
                and type(details["response_rows"]) is int
                and details["response_rows"] >= 0
            ):
                blockers.append(f"attempt_event_{index}_response_details_invalid")
        elif status_text == "accepted_output_ready_for_publication":
            if not (
                isinstance(details, dict)
                and set(details) == {"factor_frame_sha256", "factor_frame_rows"}
                and isinstance(details["factor_frame_sha256"], str)
                and len(details["factor_frame_sha256"]) == 64
                and all(
                    character in "0123456789abcdef"
                    for character in details["factor_frame_sha256"]
                )
                and details["factor_frame_rows"] == EXPECTED_ACTIVE_NAMES
            ):
                blockers.append(f"attempt_event_{index}_output_details_invalid")
        elif status_text in {
            "terminal_failure_detected",
            "failure_record_publication_started",
        }:
            if not (
                isinstance(details, dict)
                and set(details) == {"failure_code"}
                and details["failure_code"]
                in {
                    "source_schema_or_formula_contract_failure",
                    "local_binding_or_atomic_publication_failure",
                    "provider_permission_or_request_failure",
                }
            ):
                blockers.append(f"attempt_event_{index}_failure_details_invalid")
            elif (
                status_text == "failure_record_publication_started"
                and previous_failure_code is not None
                and details["failure_code"] != previous_failure_code
            ):
                blockers.append(f"attempt_event_{index}_failure_code_changed")
            else:
                previous_failure_code = str(details["failure_code"])
        elif status_text in no_details and details is not None:
            blockers.append(f"attempt_event_{index}_unexpected_details")
        previous_status = status_text
        previous_provider_calls = int(provider_calls)
    return blockers


def inspect_attempt_journal() -> dict[str, Any]:
    """Summarize one-shot state without credentials, provider access, or raw rows."""

    records, read_error = _read_attempt_journal()
    if records is None and read_error is None:
        return {
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
    blockers = [read_error] if read_error else _validate_attempt_journal(records or [])
    statuses = [str(record.get("status")) for record in records or []]
    success_exists = SUCCESS_MANIFEST.exists() or SUCCESS_MANIFEST.is_symlink()
    failure_exists = FAILURE_RECORD.exists() or FAILURE_RECORD.is_symlink()
    final_frame_exists = FINAL_FRAME.is_file()
    last_status = statuses[-1] if statuses else None
    last_event = records[-1] if records else None
    if success_exists:
        success_record, success_error = _read_private_json_record(
            SUCCESS_MANIFEST, label="success_manifest"
        )
        if success_error:
            blockers.append(success_error)
        elif success_record is not None:
            blockers.extend(_validate_success_evidence(success_record))
    if failure_exists:
        failure_record, failure_error = _read_private_json_record(
            FAILURE_RECORD, label="failure_record"
        )
        if failure_error:
            blockers.append(failure_error)
        elif failure_record is not None:
            blockers.extend(_validate_failure_evidence(failure_record, last_event))
    if success_exists and not failure_exists and final_frame_exists:
        terminal_state = "success_committed"
        if last_status != "success_manifest_publication_started":
            blockers.append("success_evidence_journal_mismatch")
    elif failure_exists and not success_exists and not FINAL_ROOT.exists():
        terminal_state = "failure_committed"
        if last_status != "failure_record_publication_started":
            blockers.append("failure_evidence_journal_mismatch")
    elif success_exists or failure_exists or FINAL_ROOT.exists():
        terminal_state = "terminal_evidence_inconsistent"
        blockers.append("terminal_evidence_inconsistent")
    else:
        terminal_state = "interrupted_attempt_terminal_no_retry"
    if blockers and terminal_state in {"success_committed", "failure_committed"}:
        terminal_state = "terminal_evidence_invalid"
    blockers = [str(blocker) for blocker in blockers if blocker]
    return {
        "status": (
            "attempt_journal_valid" if not blockers else "attempt_journal_invalid"
        ),
        "valid": not blockers,
        "exit_code": 0 if not blockers else 2,
        "attempt_journal_exists": True,
        "record_count": len(records or []),
        "last_status": last_status,
        "provider_call_may_have_been_issued": "provider_call_authorized_and_may_have_started"
        in statuses,
        "provider_response_received": "provider_response_received" in statuses,
        "terminal_evidence_state": terminal_state,
        "blockers": blockers,
        "retry_authorized_by_inspection": False,
        "credential_loaded": False,
        "provider_request_issued_by_inspection": False,
    }


def build_plan(
    *,
    entitlement_confirmed: bool,
    owned_attempt_identity: tuple[int, int] | None = None,
    inspect_credential: bool = True,
) -> dict[str, Any]:
    checks: dict[str, bool] = {
        "protocol_fingerprint": PROTOCOL.is_file()
        and digest(PROTOCOL) == PROTOCOL_SHA256,
        "contract_fingerprint": ADAPTER.DEFAULT_CONTRACT.is_file()
        and digest(ADAPTER.DEFAULT_CONTRACT) == CONTRACT_SHA256,
        "adapter_fingerprint": ADAPTER.__file__ is not None
        and digest(Path(ADAPTER.__file__)) == ADAPTER_SHA256,
        "runner_v5_runtime_binding": _runtime_bindings_valid(),
        "universe_fingerprint": UNIVERSE.is_file()
        and digest(UNIVERSE) == UNIVERSE_SHA256,
        "calendar_fingerprint": CALENDAR.is_file()
        and digest(CALENDAR) == CALENDAR_SHA256,
        "fixed_date_is_calendar_session": CALENDAR.is_file()
        and TRADE_DATE.isoformat() in CALENDAR.read_text(encoding="utf-8").splitlines(),
        "no_prior_success": not SUCCESS_MANIFEST.exists() and not FINAL_ROOT.exists(),
        "no_prior_failure": not FAILURE_RECORD.exists(),
        "no_temporary_root": not TEMP_ROOT.exists(),
        "one_shot_attempt_intent_available": _attempt_intent_state_valid(
            owned_attempt_identity
        ),
        "manual_5000_point_entitlement_confirmation": entitlement_confirmed,
    }
    dotenv = _dotenv_state(inspect_token=inspect_credential)
    checks.update(
        {
            "dotenv_regular_non_symlink": bool(dotenv["regular_non_symlink"]),
            "dotenv_mode_0600": dotenv["mode"] == "0600",
            "dotenv_git_ignored": bool(dotenv["git_ignored"]),
        }
    )
    if inspect_credential:
        checks["tushare_token_present"] = bool(dotenv["token_present"])
    active_count = None
    if checks["universe_fingerprint"]:
        try:
            active_count = len(_active_instruments())
            checks["fixed_active_name_count"] = active_count == EXPECTED_ACTIVE_NAMES
        except AcceptanceError:
            checks["fixed_active_name_count"] = False
    else:
        checks["fixed_active_name_count"] = False
    ready = all(checks.values())
    blockers = [name for name, passed in checks.items() if not passed]
    return {
        "ready": ready,
        "exit_code_if_executed": 0 if ready else 2,
        "trade_date": TRADE_DATE.isoformat(),
        "provider": "tushare",
        "api": "limit_list_d",
        "fields": list(ADAPTER.RAW_FIELDS),
        "maximum_provider_calls": 1,
        "active_names": active_count,
        "checks": checks,
        "blockers": blockers,
        "provider_request_issued": False,
        "credential_value_printed_hashed_or_persisted": False,
    }


def _fetch_once(token: str) -> pd.DataFrame:
    import tushare as ts

    ts.set_token(token)
    client = ts.pro_api()
    result = client.limit_list_d(
        trade_date=TRADE_DATE.strftime("%Y%m%d"),
        fields=",".join(ADAPTER.RAW_FIELDS),
    )
    if result is None:
        return pd.DataFrame(columns=ADAPTER.RAW_FIELDS)
    return result.copy()


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
        cleanup_path = destination if published else temporary
        try:
            cleanup_path.unlink()
            _fsync_directory(destination.parent)
        except OSError:
            pass
        raise


def _failure_code(exc: Exception) -> str:
    if isinstance(exc, ADAPTER.LimitQueueContractError):
        return "source_schema_or_formula_contract_failure"
    if isinstance(exc, AcceptanceError):
        return "local_binding_or_atomic_publication_failure"
    return "provider_permission_or_request_failure"


def run_acceptance(*, entitlement_confirmed: bool, confirm_run: bool) -> int:
    if not confirm_run or not entitlement_confirmed:
        raise AcceptanceError("both explicit confirmation flags are required")
    plan = build_plan(
        entitlement_confirmed=entitlement_confirmed,
        inspect_credential=False,
    )
    if not plan["ready"]:
        raise AcceptanceError("acceptance plan is not ready")
    lock, intent_identity = _create_attempt_intent()
    with lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AcceptanceError(
                "another Campaign115 acceptance process is active"
            ) from exc
        provider_calls = 0
        try:
            plan = build_plan(
                entitlement_confirmed=entitlement_confirmed,
                owned_attempt_identity=intent_identity,
            )
            if not plan["ready"]:
                raise AcceptanceError("acceptance plan changed after intent creation")
            token = _load_token(DOTENV)
            if not token:
                raise AcceptanceError("Tushare token became unavailable")
            _append_attempt_event(
                lock,
                intent_identity,
                status_value="provider_call_authorized_and_may_have_started",
                provider_calls_issued=1,
            )
            provider_calls = 1
            raw = _fetch_once(token)
            token = None
            _append_attempt_event(
                lock,
                intent_identity,
                status_value="provider_response_received",
                provider_calls_issued=provider_calls,
                details={"response_rows": int(len(raw))},
            )
            if raw.empty:
                raise AcceptanceError("fixed-date source response is empty")
            instruments = _active_instruments()
            factor, quality = ADAPTER.canonicalize_limit_queue_response(
                raw,
                trade_date=TRADE_DATE,
                active_instruments=instruments,
            )
            if quality["valid_upper_limit_names"] < 1:
                raise AcceptanceError("fixed-date source has no valid U event")
            if len(factor) != EXPECTED_ACTIVE_NAMES:
                raise AcceptanceError("factor frame does not cover the fixed universe")
            TEMP_ROOT.mkdir(parents=True, exist_ok=False)
            temp_frame = TEMP_ROOT / "factor.parquet"
            factor.to_parquet(temp_frame, index=False)
            frame_sha = digest(temp_frame)
            with temp_frame.open("rb") as handle:
                os.fsync(handle.fileno())
            _fsync_directory(TEMP_ROOT)
            manifest = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign115_source_acceptance",
                "status": "accepted_entitlement_schema_formula_and_single_session_pending_2019_2023_atomic_source",
                "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "protocol": {
                    "path": str(PROTOCOL.relative_to(ROOT)),
                    "sha256": PROTOCOL_SHA256,
                },
                "contract": {
                    "path": str(ADAPTER.DEFAULT_CONTRACT.relative_to(ROOT)),
                    "sha256": CONTRACT_SHA256,
                },
                "request": {
                    "provider": "tushare",
                    "api": "limit_list_d",
                    "trade_date": TRADE_DATE.isoformat(),
                    "fields": list(ADAPTER.RAW_FIELDS),
                    "provider_calls_issued": provider_calls,
                },
                "factor_frame": {
                    "path": FINAL_FRAME_RELATIVE,
                    "sha256": frame_sha,
                    "rows": int(len(factor)),
                },
                "quality": quality,
                "raw_provider_response_persisted": False,
                "credential_value_printed_hashed_or_persisted": False,
                "daily_price_comparator_or_forward_return_fields_read": False,
                "selection_or_promotion_allowed": False,
            }
            _append_attempt_event(
                lock,
                intent_identity,
                status_value="accepted_output_ready_for_publication",
                provider_calls_issued=provider_calls,
                details={
                    "factor_frame_sha256": frame_sha,
                    "factor_frame_rows": int(len(factor)),
                },
            )
            os.replace(TEMP_ROOT, FINAL_ROOT)
            _fsync_directory(FINAL_ROOT.parent)
            try:
                _append_attempt_event(
                    lock,
                    intent_identity,
                    status_value="success_manifest_publication_started",
                    provider_calls_issued=provider_calls,
                )
                _atomic_json(manifest, SUCCESS_MANIFEST)
            except Exception:
                shutil.rmtree(FINAL_ROOT, ignore_errors=True)
                _fsync_directory(FINAL_ROOT.parent)
                raise
            print(
                json.dumps(
                    {
                        "status": manifest["status"],
                        "manifest": str(SUCCESS_MANIFEST),
                        "provider_calls_issued": 1,
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        except Exception as exc:
            shutil.rmtree(TEMP_ROOT, ignore_errors=True)
            shutil.rmtree(FINAL_ROOT, ignore_errors=True)
            _fsync_directory(FINAL_ROOT.parent)
            failure_code = _failure_code(exc)
            _append_attempt_event(
                lock,
                intent_identity,
                status_value="terminal_failure_detected",
                provider_calls_issued=provider_calls,
                details={"failure_code": failure_code},
            )
            record = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign115_source_acceptance_failure",
                "status": "terminal_source_acceptance_failure_no_retry",
                "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "trade_date": TRADE_DATE.isoformat(),
                "provider_calls_issued": provider_calls,
                "failure_code": failure_code,
                "plaintext_provider_error_persisted": False,
                "raw_provider_response_persisted": False,
                "credential_value_printed_hashed_or_persisted": False,
                "daily_price_comparator_or_forward_return_fields_read": False,
                "retry_allowed": False,
            }
            _append_attempt_event(
                lock,
                intent_identity,
                status_value="failure_record_publication_started",
                provider_calls_issued=provider_calls,
                details={"failure_code": failure_code},
            )
            _atomic_json(record, FAILURE_RECORD)
            raise AcceptanceError(
                f"Campaign115 acceptance failed closed: {record['failure_code']}"
            ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run"):
        command = subparsers.add_parser(name)
        command.add_argument(
            "--confirm-current-account-has-5000-points", action="store_true"
        )
        if name == "run":
            command.add_argument("--confirm-run", action="store_true")
    subparsers.add_parser("inspect-attempt")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "inspect-attempt":
        inspection = inspect_attempt_journal()
        print(json.dumps(inspection, ensure_ascii=False, indent=2))
        return int(inspection["exit_code"])
    entitlement = bool(args.confirm_current_account_has_5000_points)
    if args.command == "plan":
        plan = build_plan(entitlement_confirmed=entitlement)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return int(plan["exit_code_if_executed"])
    return run_acceptance(
        entitlement_confirmed=entitlement,
        confirm_run=bool(args.confirm_run),
    )


if __name__ == "__main__":
    raise SystemExit(main())
