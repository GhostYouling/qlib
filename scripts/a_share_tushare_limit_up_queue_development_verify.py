#!/usr/bin/env python3
"""Verify and fingerprint the frozen Campaign115 development source locally."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
import stat
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, TextIO

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_tushare_limit_up_queue_development as SOURCE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_development_source_semantic_verification_protocol_20260809.json"
)
PROTOCOL_SHA256 = "4422a3d054746ad9b1f47f18f67e8bb40dfd5c62ecb0223262dd96ba8c7792f6"
IMPLEMENTATION_FREEZE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_development_source_semantic_verifier_freeze_v4_20260809.json"
)
TEST_PATH = (
    ROOT
    / "tests/data_collector_tests/test_a_share_tushare_limit_up_queue_development_verify.py"
)
SOURCE_RUNNER_SHA256 = (
    "73e1d2a9f2c81c99aa9ab812cad1df9e04e37c8290992ba3edc584aa9094df82"
)
SOURCE_RUNNER_FREEZE_SHA256 = (
    "7991e43b7737a6de8e65cdf6c8675ff6a3d6db194f69772a053959f1665aa909"
)
ADAPTER_SHA256 = "807d06f7dec4ca0a94beb28912b686e8cb01fbf36c7f473e69564de16af5f5dd"
RECEIPT = (
    ROOT / "data/metadata/rich_data/runs/"
    "campaign115_tushare_limit_queue_development_semantic_verification_2019_2023.json"
)
LOCK_PATH = ROOT / "data/.campaign115_tushare_limit_queue_development_verify.lock"


class DevelopmentSourceVerificationError(RuntimeError):
    """Fail-closed error for the local-only Campaign115 semantic verifier."""


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _json_digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise DevelopmentSourceVerificationError(
            f"invalid JSON object: {path}"
        ) from exc
    if not isinstance(value, dict):
        raise DevelopmentSourceVerificationError(f"JSON is not an object: {path}")
    return value


def _protocol_valid() -> bool:
    try:
        record = _read_object(PROTOCOL)
        inputs = record.get("authoritative_inputs") or {}
        interface = record.get("bounded_interface") or {}
        source = record.get("source_semantic_contract") or {}
        receipt = record.get("immutable_receipt") or {}
        boundary = record.get("research_boundary") or {}
        return bool(
            digest(PROTOCOL) == PROTOCOL_SHA256
            and record.get("kind")
            == "a_share_three_day_walkforward_campaign115_development_source_semantic_verification_protocol"
            and record.get("status")
            == "frozen_before_development_source_candidate_or_comparator_values"
            and (inputs.get("development_source_runner") or {}).get("sha256")
            == SOURCE_RUNNER_SHA256
            and (inputs.get("development_source_runner_freeze_v1") or {}).get("sha256")
            == SOURCE_RUNNER_FREEZE_SHA256
            and (inputs.get("factor_adapter") or {}).get("sha256") == ADAPTER_SHA256
            and interface.get(
                "alternate_source_root_manifest_receipt_or_output_path_allowed"
            )
            is False
            and interface.get("plan_reads_parquet_candidate_values") is False
            and source.get("exact_session_count") == 1214
            and source.get("exact_session_order_sha256") == SOURCE.SESSION_ORDER_SHA256
            and source.get("exact_factor_columns")
            == list(SOURCE.ADAPTER.OUTPUT_COLUMNS)
            and source.get("minimum_sessions_with_valid_upper_limit_names") == 200
            and receipt.get("path") == str(RECEIPT.relative_to(ROOT))
            and receipt.get("existing_receipt_is_never_overwritten") is True
            and boundary.get("comparison_values_read") is False
            and boundary.get("historical_daily_price_or_forward_return_values_read")
            is False
            and boundary.get("stress_2024_2025_opened") is False
        )
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        DevelopmentSourceVerificationError,
    ):
        return False


def _implementation_binding_valid() -> bool:
    try:
        freeze = _read_object(IMPLEMENTATION_FREEZE)
        implementation = freeze.get("implementation") or {}
        return bool(
            freeze.get("kind")
            == "a_share_three_day_walkforward_campaign115_development_source_semantic_verifier_freeze"
            and freeze.get("status")
            == "verifier_effective_frozen_before_development_source_candidate_or_comparator_values"
            and (freeze.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
            and implementation.get("verifier_path")
            == "scripts/a_share_tushare_limit_up_queue_development_verify.py"
            and implementation.get("verifier_sha256")
            == digest(Path(__file__).resolve())
            and implementation.get("test_path")
            == "tests/data_collector_tests/test_a_share_tushare_limit_up_queue_development_verify.py"
            and implementation.get("test_sha256") == digest(TEST_PATH)
            and implementation.get("source_runner_sha256") == SOURCE_RUNNER_SHA256
            and implementation.get("source_runner_freeze_sha256")
            == SOURCE_RUNNER_FREEZE_SHA256
            and implementation.get("adapter_sha256") == ADAPTER_SHA256
        )
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        DevelopmentSourceVerificationError,
    ):
        return False


def runtime_bindings_valid() -> bool:
    try:
        return bool(
            _protocol_valid()
            and _implementation_binding_valid()
            and digest(Path(SOURCE.__file__).resolve()) == SOURCE_RUNNER_SHA256
            and digest(SOURCE.RUNNER_FREEZE) == SOURCE_RUNNER_FREEZE_SHA256
            and digest(Path(SOURCE.ADAPTER.__file__).resolve()) == ADAPTER_SHA256
            and SOURCE._runtime_bindings_valid()
        )
    except (OSError, TypeError, ValueError):
        return False


def _regular_private_file(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    return stat.S_ISREG(mode) and not stat.S_ISLNK(mode)


def _manifests_byte_identical() -> bool:
    try:
        return (
            _regular_private_file(SOURCE.INTERNAL_MANIFEST)
            and _regular_private_file(SOURCE.RUN_MANIFEST)
            and SOURCE.INTERNAL_MANIFEST.read_bytes()
            == SOURCE.RUN_MANIFEST.read_bytes()
        )
    except OSError:
        return False


def build_plan() -> dict[str, Any]:
    checks = {
        "protocol_fingerprint": _protocol_valid(),
        "verifier_runtime_binding": runtime_bindings_valid(),
        "source_terminal_failure_absent": not SOURCE.FAILURE_RECORD.exists(),
        "source_partial_root_absent": not SOURCE.PARTIAL_ROOT.exists(),
        "source_final_root_present": SOURCE.FINAL_ROOT.is_dir()
        and not SOURCE.FINAL_ROOT.is_symlink(),
        "internal_source_manifest_present": _regular_private_file(
            SOURCE.INTERNAL_MANIFEST
        ),
        "repository_source_manifest_present": _regular_private_file(
            SOURCE.RUN_MANIFEST
        ),
        "source_manifests_byte_identical": _manifests_byte_identical(),
        "semantic_verification_receipt_absent": not RECEIPT.exists(),
    }
    blockers = [name for name, passed in checks.items() if not passed]
    return {
        "ready": not blockers,
        "exit_code_if_executed": 0 if not blockers else 2,
        "checks": checks,
        "blockers": blockers,
        "source_root": str(SOURCE.FINAL_ROOT),
        "source_manifest": str(SOURCE.RUN_MANIFEST),
        "receipt": str(RECEIPT),
        "parquet_candidate_values_read": False,
        "comparison_values_read": False,
        "daily_price_or_forward_return_values_read": False,
        "stress_2024_2025_opened": False,
        "credential_loaded": False,
        "provider_request_issued": False,
    }


@contextmanager
def _exclusive_lock() -> Iterator[TextIO]:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(LOCK_PATH, flags, 0o600)
        os.fchmod(descriptor, 0o600)
        handle = os.fdopen(descriptor, "r+", encoding="utf-8")
        descriptor = -1
        with handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield handle
    except (FileExistsError, OSError, BlockingIOError) as exc:
        if descriptor >= 0:
            os.close(descriptor)
        raise DevelopmentSourceVerificationError(
            "verification lock unavailable"
        ) from exc


def _semantic_frame_digest(frame: pd.DataFrame, session: dt.date) -> str:
    records = [
        [
            session.isoformat(),
            str(instrument),
            float(value).hex(),
            bool(event),
            str(provider),
        ]
        for instrument, value, event, provider in frame[
            [
                "instrument",
                SOURCE.ADAPTER.FACTOR_NAME,
                "is_official_limit_up_event",
                "provider",
            ]
        ].itertuples(index=False, name=None)
    ]
    return _json_digest(records)


def _verify_frame(
    frame: pd.DataFrame,
    session: dt.date,
    active: tuple[str, ...],
    checkpoint: dict[str, Any],
) -> str:
    factor_name = SOURCE.ADAPTER.FACTOR_NAME
    if tuple(frame.columns) != SOURCE.ADAPTER.OUTPUT_COLUMNS:
        raise DevelopmentSourceVerificationError("factor frame columns changed")
    if len(frame) != len(active) or frame["instrument"].astype(str).tolist() != list(
        active
    ):
        raise DevelopmentSourceVerificationError("factor frame universe order changed")
    dates = pd.to_datetime(frame["trade_date"], errors="coerce")
    if dates.isna().any() or not (dates == pd.Timestamp(session)).all():
        raise DevelopmentSourceVerificationError("factor frame trade_date changed")
    if frame["instrument"].duplicated().any():
        raise DevelopmentSourceVerificationError(
            "factor frame has duplicate instruments"
        )
    if not pd.api.types.is_bool_dtype(frame["is_official_limit_up_event"].dtype):
        raise DevelopmentSourceVerificationError("event flag is not boolean")
    if not (frame["provider"].astype(str) == "tushare").all():
        raise DevelopmentSourceVerificationError("factor frame provider changed")
    values = pd.to_numeric(frame[factor_name], errors="coerce").astype(float)
    if any(not math.isfinite(value) for value in values.tolist()):
        raise DevelopmentSourceVerificationError(
            "factor frame contains nonfinite values"
        )
    if ((values < 0.0) | (values > 1.0)).any():
        raise DevelopmentSourceVerificationError("factor frame value is outside [0, 1]")
    events = frame["is_official_limit_up_event"]
    if not (values.loc[~events] == 0.0).all():
        raise DevelopmentSourceVerificationError("non-event row has a nonzero factor")
    if int(events.sum()) != int(checkpoint["valid_upper_limit_names"]):
        raise DevelopmentSourceVerificationError("event count differs from checkpoint")
    source_rows = checkpoint.get("source_rows")
    if not isinstance(source_rows, int) or not 0 <= source_rows < 5000:
        raise DevelopmentSourceVerificationError(
            "checkpoint source row count is invalid"
        )
    return _semantic_frame_digest(frame, session)


def _validate_source_manifest(
    manifest: dict[str, Any],
    checkpoints: list[dict[str, Any]],
) -> None:
    source = manifest.get("source") or {}
    quality = manifest.get("quality") or {}
    hashes = tuple(str(checkpoint["factor_byte_sha256"]) for checkpoint in checkpoints)
    sessions_with_u = sum(
        int(int(checkpoint["valid_upper_limit_names"]) > 0)
        for checkpoint in checkpoints
    )
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign115_development_source"
        and manifest.get("status")
        == "complete_2019_2023_source_pending_no_return_audit"
        and (manifest.get("protocol") or {}).get("sha256") == SOURCE.PROTOCOL_SHA256
        and (manifest.get("runner_freeze") or {}).get("sha256")
        == SOURCE_RUNNER_FREEZE_SHA256
        and source.get("provider") == "tushare"
        and source.get("api") == "limit_list_d"
        and source.get("fields") == list(SOURCE.ADAPTER.RAW_FIELDS)
        and source.get("development_start") == "2019-01-01"
        and source.get("development_end") == "2023-12-31"
        and source.get("sessions") == SOURCE.SESSION_COUNT
        and source.get("provider_calls_lifetime") == SOURCE.SESSION_COUNT
        and isinstance(source.get("provider_calls_this_run"), int)
        and isinstance(source.get("resumed_sessions"), int)
        and source["provider_calls_this_run"] + source["resumed_sessions"]
        == SOURCE.SESSION_COUNT
        and quality.get("sessions_with_valid_upper_limit_names") == sessions_with_u
        and quality.get("source_rows")
        == sum(int(checkpoint["source_rows"]) for checkpoint in checkpoints)
        and quality.get("factor_rows")
        == sum(int(checkpoint["factor_rows"]) for checkpoint in checkpoints)
        and quality.get("minimum_u_session_gate") == SOURCE.MINIMUM_U_SESSIONS
        and sessions_with_u >= SOURCE.MINIMUM_U_SESSIONS
        and manifest.get("checkpoint_factor_byte_order_sha256")
        == SOURCE._ordered_digest(hashes)
        and manifest.get("raw_provider_responses_persisted") is False
        and manifest.get("daily_price_comparator_or_forward_return_fields_read")
        is False
        and manifest.get("stress_2024_2025_opened") is False
        and manifest.get("selection_or_promotion_allowed") is False
    ):
        raise DevelopmentSourceVerificationError("source manifest semantics changed")


def _verify_source() -> dict[str, Any]:
    sessions = SOURCE._development_sessions()
    spans = SOURCE._instrument_spans()
    expected_root_entries = {
        "intent.json",
        "requests",
        "sessions",
        "source_manifest.json",
    }
    if (
        SOURCE.FINAL_ROOT.is_symlink()
        or {item.name for item in SOURCE.FINAL_ROOT.iterdir()} != expected_root_entries
        or any(item.is_symlink() for item in SOURCE.FINAL_ROOT.iterdir())
    ):
        raise DevelopmentSourceVerificationError("source root entries changed")
    prefix = SOURCE._prefix_state(SOURCE.FINAL_ROOT, sessions, spans)
    if not (
        prefix.get("valid") is True
        and prefix.get("completed_sessions") == len(sessions)
        and prefix.get("next_session") is None
        and prefix.get("inflight_request_without_checkpoint") is False
    ):
        raise DevelopmentSourceVerificationError("source checkpoint prefix is invalid")
    session_names = {session.isoformat() for session in sessions}
    actual_session_names = {
        item.name for item in (SOURCE.FINAL_ROOT / "sessions").iterdir()
    }
    actual_request_names = {
        item.stem for item in (SOURCE.FINAL_ROOT / "requests").iterdir()
    }
    if actual_session_names != session_names or actual_request_names != session_names:
        raise DevelopmentSourceVerificationError("source session identity set changed")

    checkpoints: list[dict[str, Any]] = []
    dataset_records: list[dict[str, Any]] = []
    total_rows = 0
    total_events = 0
    for index, session in enumerate(sessions):
        active = SOURCE._active_instruments(session, spans)
        frame_path, checkpoint_path = SOURCE._session_paths(SOURCE.FINAL_ROOT, session)
        session_root = frame_path.parent
        if {item.name for item in session_root.iterdir()} != {
            "factor.parquet",
            "checkpoint.json",
        } or any(item.is_symlink() for item in session_root.iterdir()):
            raise DevelopmentSourceVerificationError(
                "session partition entries changed"
            )
        if not SOURCE._checkpoint_valid(SOURCE.FINAL_ROOT, session, active, index):
            raise DevelopmentSourceVerificationError("session checkpoint changed")
        checkpoint = _read_object(checkpoint_path)
        frame = pd.read_parquet(frame_path)
        semantic_sha256 = _verify_frame(frame, session, active, checkpoint)
        checkpoints.append(checkpoint)
        total_rows += len(frame)
        total_events += int(frame["is_official_limit_up_event"].sum())
        dataset_records.append(
            {
                "trade_date": session.isoformat(),
                "factor_byte_sha256": checkpoint["factor_byte_sha256"],
                "semantic_frame_sha256": semantic_sha256,
                "factor_rows": len(frame),
                "source_rows": checkpoint["source_rows"],
                "valid_upper_limit_names": checkpoint["valid_upper_limit_names"],
                "active_universe_names": len(active),
            }
        )
    manifest = _read_object(SOURCE.INTERNAL_MANIFEST)
    _validate_source_manifest(manifest, checkpoints)
    if SOURCE.INTERNAL_MANIFEST.read_bytes() != SOURCE.RUN_MANIFEST.read_bytes():
        raise DevelopmentSourceVerificationError(
            "source manifests are not byte-identical"
        )
    return {
        "dataset_sha256": _json_digest(dataset_records),
        "session_count": len(sessions),
        "session_order_sha256": SOURCE.SESSION_ORDER_SHA256,
        "factor_rows": total_rows,
        "official_limit_up_event_rows": total_events,
        "sessions_with_valid_upper_limit_names": sum(
            int(int(checkpoint["valid_upper_limit_names"]) > 0)
            for checkpoint in checkpoints
        ),
        "checkpoint_factor_byte_order_sha256": manifest[
            "checkpoint_factor_byte_order_sha256"
        ],
        "source_manifest_sha256": digest(SOURCE.RUN_MANIFEST),
    }


def _receipt_record(verification: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign115_development_source_semantic_verification",
        "status": "complete_semantically_verified_2019_2023_candidate_snapshot_pending_ordered_no_return_audit",
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": PROTOCOL_SHA256,
        },
        "implementation_freeze": {
            "path": str(IMPLEMENTATION_FREEZE.relative_to(ROOT)),
            "sha256": digest(IMPLEMENTATION_FREEZE),
        },
        "source_manifest": {
            "path": _display_path(SOURCE.RUN_MANIFEST),
            "sha256": verification["source_manifest_sha256"],
        },
        "factor": {
            "name": SOURCE.ADAPTER.FACTOR_NAME,
            "direction": "higher_is_better",
            "columns": list(SOURCE.ADAPTER.OUTPUT_COLUMNS),
            "value_range_inclusive": [0.0, 1.0],
        },
        "verification": {
            key: verification[key]
            for key in (
                "dataset_sha256",
                "session_count",
                "session_order_sha256",
                "factor_rows",
                "official_limit_up_event_rows",
                "sessions_with_valid_upper_limit_names",
                "checkpoint_factor_byte_order_sha256",
            )
        },
        "candidate_or_comparator_values_embedded": False,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "stress_2024_2025_opened": False,
        "candidate49_ledgers_changed": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "selection_or_promotion_allowed": False,
    }


def _publish_exclusive_private_json(record: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        raise DevelopmentSourceVerificationError("verification receipt already exists")
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    payload = (
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    descriptor = os.open(temporary, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        view = memoryview(payload)
        while view:
            view = view[os.write(descriptor, view) :]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, destination, follow_symlinks=False)
        directory = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    temporary.unlink()


def verify_and_publish(*, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise DevelopmentSourceVerificationError(
            "--confirm-semantic-verification is required"
        )
    plan = build_plan()
    if not plan["ready"]:
        raise DevelopmentSourceVerificationError(
            "semantic verification plan is not ready"
        )
    with _exclusive_lock():
        verification = _verify_source()
        record = _receipt_record(verification)
        _publish_exclusive_private_json(record, RECEIPT)
    return record


def inspect_receipt() -> dict[str, Any]:
    if not RECEIPT.exists():
        return {
            "valid": True,
            "status": "no_semantic_verification_receipt",
            "credential_loaded": False,
            "provider_request_issued": False,
        }
    if not _regular_private_file(RECEIPT):
        raise DevelopmentSourceVerificationError("verification receipt is not regular")
    record = _read_object(RECEIPT)
    verification = record.get("verification") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign115_development_source_semantic_verification"
        and record.get("status")
        == "complete_semantically_verified_2019_2023_candidate_snapshot_pending_ordered_no_return_audit"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("implementation_freeze") or {}).get("sha256")
        == digest(IMPLEMENTATION_FREEZE)
        and verification.get("session_count") == SOURCE.SESSION_COUNT
        and verification.get("session_order_sha256") == SOURCE.SESSION_ORDER_SHA256
        and isinstance(verification.get("dataset_sha256"), str)
        and len(verification["dataset_sha256"]) == 64
        and record.get("candidate_or_comparator_values_embedded") is False
        and record.get("comparison_values_read") is False
        and record.get("historical_daily_price_or_forward_return_values_read") is False
        and record.get("stress_2024_2025_opened") is False
        and record.get("provider_request_issued") is False
        and record.get("credential_loaded") is False
        and record.get("selection_or_promotion_allowed") is False
    ):
        raise DevelopmentSourceVerificationError(
            "verification receipt semantics changed"
        )
    return {
        "valid": True,
        "status": record["status"],
        "receipt_sha256": digest(RECEIPT),
        "dataset_sha256": verification["dataset_sha256"],
        "credential_loaded": False,
        "provider_request_issued": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan")
    verify = commands.add_parser("verify")
    verify.add_argument("--confirm-semantic-verification", action="store_true")
    commands.add_parser("inspect-receipt")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "plan":
            payload = build_plan()
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return int(payload["exit_code_if_executed"])
        if args.command == "verify":
            payload = verify_and_publish(confirmed=args.confirm_semantic_verification)
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return 0
        payload = inspect_receipt()
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    except DevelopmentSourceVerificationError as exc:
        print(
            json.dumps(
                {
                    "status": "failed_closed",
                    "reason": str(exc),
                    "credential_loaded": False,
                    "provider_request_issued": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
