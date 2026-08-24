#!/usr/bin/env python3
"""Credential-safe one-shot Campaign265 source-acceptance workflow.

The currently authorized public CLI is plan-only.  A run command is added only
when a separately published v420 policy validates the exact frozen workflow,
tests, protocol, implementation freeze, and plan result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign265_convertible_premium as ADAPTER  # noqa: E402
import a_share_three_day_walkforward_campaign265_source_acceptance_plan as PLANNER  # noqa: E402


WORKFLOW_PATH = Path(__file__).resolve()
WORKFLOW_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py"
)
EXECUTION_PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_protocol_20260824.json"
)
EXECUTION_PROTOCOL_SHA256 = (
    "766172caa77a9ffa90867e7299e1ac77816934469b8cafd5f63fd27281d9c04c"
)
PLAN_AUTHORIZATION_POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v419_20260824_execution_path_hardening_v2.json"
)
RUN_AUTHORIZATION_POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v420_20260824.json"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_workflow_implementation_freeze_v2_20260824.json"
)
PLAN_RESULT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_workflow_plan_result_v2_20260824.json"
)
DOTENV_PATH = REPO_ROOT / ".env"
DOTENV_MAX_BYTES = 64 * 1024
TOKEN_ENV = "TUSHARE_TOKEN"

ZERO_SHA256 = "0" * 64
FILE_MODE = 0o600
MAX_JOURNAL_BYTES = 8 * 1024 * 1024

BASELINE_BINDINGS = {
    "latest_state": (
        "docs/a_share_three_day_iteration_status_20260824_campaign265_source_acceptance_plan_ready_v2.json",
        "38a9e8b3834643db861dedb4b16e9b3d316d117582e166980a27ecf8351cff48",
    ),
    "numeric_policy_v418": (
        "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v418_20260824.json",
        "f1ba460fda8fe9b51388edfb4a2de7c8a7940c0df1650a75e8d142ccef3d36a0",
    ),
    "source_contract": (
        "docs/a_share_three_day_walkforward_campaign_265_convertible_premium_source_contract_20260824.json",
        "efe7884d3ea0fd7f974e0d3347432e68e9e01ceefe0e6ebdca7fdd3e6349301c",
    ),
    "adapter": (
        "scripts/a_share_three_day_walkforward_campaign265_convertible_premium.py",
        "58b9fddbbeef97955d4961f9f708028aa63d90fc56f2656db68098de7d3543e8",
    ),
    "source_acceptance_preregistration": (
        "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_preregistration_20260824.json",
        "474e5a995703f46005053268bbbd6c1c20835c99233f82e727a24a6085198ffd",
    ),
    "planner": (
        "scripts/a_share_three_day_walkforward_campaign265_source_acceptance_plan.py",
        "1702119cc43c58843cc27575a9681214121b45084ccd0ff84489ea362eac7c05",
    ),
    "planner_result": (
        "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_plan_result_20260824.json",
        "03c05e8586d97d2c0e2fccb9978ab858a7f99bd77b49d5266a7706383ef2b3a5",
    ),
    "planner_validation_v2": (
        "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_plan_validation_v2_20260824.json",
        "4925d75621fe0625d9b34a269c2c5867fe15109e1d03a9cbee869b6d344d39bc",
    ),
    "execution_protocol": (
        "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_protocol_20260824.json",
        EXECUTION_PROTOCOL_SHA256,
    ),
    "calendar": PLANNER.BASELINE_BINDINGS["calendar"],
    "factor_universe": PLANNER.BASELINE_BINDINGS["factor_universe"],
    "candidate49_signal_ledger": PLANNER.BASELINE_BINDINGS["candidate49_signal_ledger"],
    "candidate49_execution_ledger": PLANNER.BASELINE_BINDINGS[
        "candidate49_execution_ledger"
    ],
}

DESTINATIONS = dict(PLANNER.DESTINATIONS)


class Campaign265WorkflowError(RuntimeError):
    """Raised when a frozen workflow boundary fails closed."""


class Provider(Protocol):
    def cb_basic(self, *, fields: str) -> pd.DataFrame: ...

    def cb_daily(self, *, trade_date: str, fields: str) -> pd.DataFrame: ...


@dataclass(frozen=True)
class AttemptPaths:
    staging_root: Path
    final_root: Path
    intent: Path
    journal: Path
    terminal_failure: Path
    repository_manifest: Path

    @classmethod
    def from_root(cls, root: Path) -> "AttemptPaths":
        return cls(
            staging_root=root / DESTINATIONS["staging_root"],
            final_root=root / DESTINATIONS["final_root"],
            intent=root / DESTINATIONS["intent"],
            journal=root / DESTINATIONS["attempt_journal"],
            terminal_failure=root / DESTINATIONS["terminal_failure"],
            repository_manifest=root / DESTINATIONS["repository_acceptance_manifest"],
        )


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _binding_display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Campaign265WorkflowError("json_binding_unreadable") from exc
    if not isinstance(value, dict):
        raise Campaign265WorkflowError("json_binding_not_object")
    return value


def _regular_private_file(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return bool(
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_nlink == 1
        and stat.S_IMODE(metadata.st_mode) == FILE_MODE
    )


def _assert_destination_directory_tree(root: Path, paths: AttemptPaths) -> None:
    root_absolute = Path(os.path.abspath(root))
    try:
        root_metadata = root_absolute.lstat()
    except OSError as exc:
        raise Campaign265WorkflowError("repository_root_identity_failed") from exc
    if not stat.S_ISDIR(root_metadata.st_mode) or stat.S_ISLNK(root_metadata.st_mode):
        raise Campaign265WorkflowError("repository_root_identity_failed")

    for target in (
        paths.staging_root,
        paths.final_root,
        paths.intent,
        paths.journal,
        paths.terminal_failure,
        paths.repository_manifest,
    ):
        target_absolute = Path(os.path.abspath(target))
        try:
            relative = target_absolute.relative_to(root_absolute)
        except ValueError as exc:
            raise Campaign265WorkflowError("destination_outside_repository") from exc
        cursor = root_absolute
        for component in relative.parts[:-1]:
            cursor /= component
            if not os.path.lexists(cursor):
                break
            metadata = cursor.lstat()
            if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
                raise Campaign265WorkflowError("destination_parent_not_real_directory")


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
            raise OSError("short private evidence write")
        remaining = remaining[written:]


def _create_exclusive_private(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, FILE_MODE)
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)
    if not _regular_private_file(path):
        raise Campaign265WorkflowError("exclusive_private_file_identity_failed")


def _atomic_private_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(path):
        raise Campaign265WorkflowError("immutable_destination_already_exists")
    temporary = path.parent / f".{path.name}.tmp.{os.getpid()}"
    if os.path.lexists(temporary):
        raise Campaign265WorkflowError("private_temporary_path_already_exists")
    _create_exclusive_private(temporary, payload)
    os.replace(temporary, path)
    _fsync_directory(path.parent)
    if not _regular_private_file(path):
        raise Campaign265WorkflowError("atomic_private_file_identity_failed")


def _atomic_private_parquet(path: Path, frame: pd.DataFrame) -> tuple[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(path):
        raise Campaign265WorkflowError("immutable_checkpoint_already_exists")
    temporary = path.parent / f".{path.name}.tmp.{os.getpid()}"
    if os.path.lexists(temporary):
        raise Campaign265WorkflowError("checkpoint_temporary_path_already_exists")
    try:
        frame.to_parquet(temporary, index=False)
        os.chmod(temporary, FILE_MODE)
        descriptor = os.open(temporary, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if os.path.lexists(temporary):
            temporary.unlink()
    if not _regular_private_file(path):
        raise Campaign265WorkflowError("checkpoint_identity_failed")
    return file_sha256(path), _frame_sha256(frame)


def _frame_sha256(frame: pd.DataFrame) -> str:
    normalized = frame.copy()
    for column in normalized.columns:
        if normalized[column].dtype == object:
            normalized[column] = normalized[column].map(
                lambda value: (
                    value.isoformat()
                    if hasattr(value, "isoformat") and value is not None
                    else value
                )
            )
    payload = {
        "columns": list(normalized.columns),
        "dtypes": [str(value) for value in normalized.dtypes],
        "records": normalized.where(pd.notna(normalized), None).to_dict(
            orient="records"
        ),
    }
    return _canonical_json_sha256(payload)


def _request_sequence(dates: Sequence[str]) -> list[dict[str, Any]]:
    return PLANNER._request_sequence(list(dates))


def _plan_authorization_checks() -> dict[str, bool]:
    checks = {
        "plan_authorization_policy_exists": PLAN_AUTHORIZATION_POLICY_PATH.is_file()
    }
    if not checks["plan_authorization_policy_exists"]:
        return checks
    try:
        policy = _load_json(PLAN_AUTHORIZATION_POLICY_PATH)
        authorization = policy[
            "campaign265_source_acceptance_execution_workflow_plan_authorization"
        ]
        workflow = authorization["workflow"]
        tests = authorization["workflow_tests"]
        protocol = authorization["execution_protocol"]
        freeze = authorization["implementation_freeze"]
        checks.update(
            {
                "plan_authorization_policy_version": policy.get("version") == 419,
                "plan_only_authorized": authorization.get("authorized") is True
                and authorization.get("plan_only") is True,
                "credential_inspection_forbidden": authorization.get(
                    "credential_inspection_allowed"
                )
                is False,
                "provider_request_forbidden": authorization.get(
                    "provider_request_allowed"
                )
                is False,
                "run_interface_forbidden_without_v420": authorization.get(
                    "run_interface_allowed"
                )
                is False,
                "workflow_hash_authorized": workflow.get("path")
                == str(WORKFLOW_PATH.relative_to(REPO_ROOT))
                and workflow.get("sha256") == file_sha256(WORKFLOW_PATH),
                "workflow_test_hash_authorized": tests.get("path")
                == str(WORKFLOW_TEST_PATH.relative_to(REPO_ROOT))
                and WORKFLOW_TEST_PATH.is_file()
                and tests.get("sha256") == file_sha256(WORKFLOW_TEST_PATH),
                "execution_protocol_hash_authorized": protocol.get("path")
                == str(EXECUTION_PROTOCOL_PATH.relative_to(REPO_ROOT))
                and protocol.get("sha256") == EXECUTION_PROTOCOL_SHA256
                and file_sha256(EXECUTION_PROTOCOL_PATH) == EXECUTION_PROTOCOL_SHA256,
                "implementation_freeze_hash_authorized": freeze.get("path")
                == str(IMPLEMENTATION_FREEZE_PATH.relative_to(REPO_ROOT))
                and IMPLEMENTATION_FREEZE_PATH.is_file()
                and freeze.get("sha256") == file_sha256(IMPLEMENTATION_FREEZE_PATH),
            }
        )
    except (KeyError, OSError, TypeError, Campaign265WorkflowError):
        checks["plan_authorization_policy_semantics"] = False
    return checks


def _run_authorization_checks() -> dict[str, bool]:
    checks = {
        "run_authorization_policy_exists": RUN_AUTHORIZATION_POLICY_PATH.is_file()
    }
    if not checks["run_authorization_policy_exists"]:
        return checks
    try:
        policy = _load_json(RUN_AUTHORIZATION_POLICY_PATH)
        authorization = policy["campaign265_source_acceptance_run_authorization"]
        checks.update(
            {
                "run_authorization_policy_version": policy.get("version") == 420,
                "one_shot_run_authorized": authorization.get("authorized") is True
                and authorization.get("one_shot") is True,
                "explicit_confirmation_required": authorization.get(
                    "explicit_confirm_run_required"
                )
                is True,
                "retry_forbidden": authorization.get("retry_allowed") is False,
                "exact_provider_call_count": authorization.get(
                    "exact_provider_call_count"
                )
                == PLANNER.EXACT_PROVIDER_CALL_COUNT,
                "workflow_hash_bound": authorization.get("workflow", {}).get("path")
                == str(WORKFLOW_PATH.relative_to(REPO_ROOT))
                and authorization.get("workflow", {}).get("sha256")
                == file_sha256(WORKFLOW_PATH),
                "workflow_test_hash_bound": authorization.get("workflow_tests", {}).get(
                    "path"
                )
                == str(WORKFLOW_TEST_PATH.relative_to(REPO_ROOT))
                and authorization.get("workflow_tests", {}).get("sha256")
                == file_sha256(WORKFLOW_TEST_PATH),
                "protocol_hash_bound": authorization.get("execution_protocol", {}).get(
                    "sha256"
                )
                == EXECUTION_PROTOCOL_SHA256,
                "freeze_hash_bound": authorization.get("implementation_freeze", {}).get(
                    "sha256"
                )
                == file_sha256(IMPLEMENTATION_FREEZE_PATH),
                "plan_result_hash_bound": authorization.get(
                    "workflow_plan_result", {}
                ).get("path")
                == str(PLAN_RESULT_PATH.relative_to(REPO_ROOT))
                and PLAN_RESULT_PATH.is_file()
                and authorization.get("workflow_plan_result", {}).get("sha256")
                == file_sha256(PLAN_RESULT_PATH),
                "schedule_digest_bound": authorization.get(
                    "request_sequence_canonical_json_sha256"
                )
                == PLANNER.REQUEST_SEQUENCE_SHA256,
            }
        )
    except (KeyError, OSError, TypeError, Campaign265WorkflowError):
        checks["run_authorization_policy_semantics"] = False
    return checks


def _run_authorized() -> bool:
    checks = _run_authorization_checks()
    return bool(checks and all(checks.values()))


def build_plan() -> dict[str, Any]:
    """Build the zero-network, zero-write workflow plan."""

    checks: dict[str, bool] = {}
    for name, (relative, expected) in BASELINE_BINDINGS.items():
        path = REPO_ROOT / relative
        checks[f"binding_{name}"] = path.is_file() and file_sha256(path) == expected

    planner_plan = PLANNER.build_plan()
    dates = list(planner_plan.get("accepted_trade_dates") or ())
    requests = _request_sequence(dates)
    paths = AttemptPaths.from_root(REPO_ROOT)
    try:
        _assert_destination_directory_tree(REPO_ROOT, paths)
        checks["destination_directory_tree_safe"] = True
    except Campaign265WorkflowError:
        checks["destination_directory_tree_safe"] = False
    checks.update(
        {
            "planner_ready": planner_plan.get("ready") is True,
            "planner_actual_schedule_exact": len(dates) == PLANNER.ACCEPTED_DATE_COUNT
            and len(requests) == PLANNER.EXACT_PROVIDER_CALL_COUNT,
            "request_sequence_digest_exact": _canonical_json_sha256(requests)
            == PLANNER.REQUEST_SEQUENCE_SHA256,
            "execution_protocol_semantics": _load_json(EXECUTION_PROTOCOL_PATH).get(
                "status"
            )
            == "frozen_execution_workflow_contract_before_credential_provider_source_candidate_comparator_price_or_return_values",
            "staging_root_absent": not os.path.lexists(paths.staging_root),
            "final_root_absent": not os.path.lexists(paths.final_root),
            "intent_absent": not os.path.lexists(paths.intent),
            "attempt_journal_absent": not os.path.lexists(paths.journal),
            "terminal_failure_absent": not os.path.lexists(paths.terminal_failure),
            "repository_manifest_absent": not os.path.lexists(
                paths.repository_manifest
            ),
        }
    )
    checks.update(_plan_authorization_checks())
    ready = all(checks.values())
    run_checks = _run_authorization_checks()
    run_authorized = bool(run_checks and all(run_checks.values()))
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_source_acceptance_execution_workflow_plan",
        "status": (
            "ready_zero_network_execution_workflow_plan_only"
            if ready
            else "blocked_fail_closed"
        ),
        "ready": ready,
        "exit_code_if_executed": 0 if ready else 2,
        "campaign": 265,
        "accepted_trade_dates": dates,
        "accepted_trade_date_count": len(dates),
        "exact_provider_call_count": len(requests),
        "request_sequence_canonical_json_sha256": _canonical_json_sha256(requests),
        "minimum_seconds_between_provider_entries": PLANNER.MINIMUM_REQUEST_INTERVAL_SECONDS,
        "strict_response_rows_less_than": PLANNER.STRICT_ROW_CEILING,
        "destinations": DESTINATIONS,
        "intent_payload_constructed": False,
        "intent_payload_deferred_until_valid_v420": True,
        "checks": checks,
        "blockers": [name for name, passed in checks.items() if not passed],
        "future_run_authorization_checks": run_checks,
        "future_run_authorized": run_authorized,
        "run_interface_exposed": run_authorized,
        "credential_file_or_environment_inspected": False,
        "credential_value_or_digest_read": False,
        "provider_client_imported_or_created": False,
        "provider_request_issued": False,
        "source_candidate_comparator_price_or_return_value_read": False,
        "filesystem_write_performed": False,
        "ready_does_not_authorize_credential_load_or_provider_request": True,
    }


def _intent_payload(
    dates: Sequence[str], requests: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_source_acceptance_intent",
        "status": "one_shot_attempt_consumed_before_credential_load",
        "campaign": 265,
        "provider": "Tushare Pro",
        "accepted_trade_dates": list(dates),
        "accepted_trade_dates_canonical_newline_sha256": hashlib.sha256(
            ("\n".join(dates) + "\n").encode("utf-8")
        ).hexdigest(),
        "requests": list(requests),
        "request_sequence_canonical_json_sha256": _canonical_json_sha256(requests),
        "exact_provider_call_count": len(requests),
        "minimum_seconds_between_provider_entries": PLANNER.MINIMUM_REQUEST_INTERVAL_SECONDS,
        "minimum_response_rows_per_call": 1,
        "strict_response_rows_less_than": PLANNER.STRICT_ROW_CEILING,
        "retry_allowed": False,
        "destinations": DESTINATIONS,
        "bindings": {
            name: {"path": relative, "sha256": expected}
            for name, (relative, expected) in BASELINE_BINDINGS.items()
        }
        | {
            "workflow": {
                "path": _binding_display_path(WORKFLOW_PATH),
                "sha256": file_sha256(WORKFLOW_PATH),
            },
            "workflow_tests": {
                "path": _binding_display_path(WORKFLOW_TEST_PATH),
                "sha256": file_sha256(WORKFLOW_TEST_PATH),
            },
            "implementation_freeze": {
                "path": _binding_display_path(IMPLEMENTATION_FREEZE_PATH),
                "sha256": file_sha256(IMPLEMENTATION_FREEZE_PATH),
            },
            "run_authorization_policy": {
                "path": _binding_display_path(RUN_AUTHORIZATION_POLICY_PATH),
                "sha256": file_sha256(RUN_AUTHORIZATION_POLICY_PATH),
            },
            "workflow_plan_result": {
                "path": _binding_display_path(PLAN_RESULT_PATH),
                "sha256": file_sha256(PLAN_RESULT_PATH),
            },
        },
        "safety": {
            "credential_value_printed_hashed_logged_or_persisted": False,
            "failure_plaintext_provider_error_or_raw_values_persisted": False,
            "authorized_request_without_checkpoint_retry_allowed": False,
            "source_candidate_comparator_price_or_return_value_authorized": False,
        },
    }


def _safe_dotenv_token(path: Path = DOTENV_PATH) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise Campaign265WorkflowError("credential_file_safe_open_failed") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise Campaign265WorkflowError("credential_file_identity_failed")
        if stat.S_IMODE(metadata.st_mode) != FILE_MODE:
            raise Campaign265WorkflowError("credential_file_mode_not_0600")
        if metadata.st_size > DOTENV_MAX_BYTES:
            raise Campaign265WorkflowError("credential_file_too_large")
        payload = os.read(descriptor, DOTENV_MAX_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(payload) > DOTENV_MAX_BYTES:
        raise Campaign265WorkflowError("credential_file_too_large")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise Campaign265WorkflowError("credential_file_not_utf8") from exc
    values: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()
        key, separator, raw_value = line.partition("=")
        if not separator or key.strip() != TOKEN_ENV:
            continue
        value = raw_value.strip()
        if value and value[0] in {"'", '"'}:
            quote = value[0]
            if len(value) < 2 or value[-1] != quote:
                raise Campaign265WorkflowError("credential_quote_invalid")
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values.append(value.strip())
    if len(values) != 1 or not values[0]:
        raise Campaign265WorkflowError("credential_assignment_not_exactly_one_nonempty")
    return values[0]


def _default_provider_factory(token: str) -> Provider:
    import tushare  # type: ignore[import-not-found]

    return tushare.pro_api(token)


def _event_payload(
    *,
    event_index: int,
    previous_event_sha256: str,
    status_value: str,
    request: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_index": event_index,
        "previous_event_sha256": previous_event_sha256,
        "status": status_value,
    }
    if request is not None:
        event.update(
            {
                "request_ordinal": request["ordinal"],
                "api": request["api"],
                "parameters": request["parameters"],
                "fields": request["fields"],
            }
        )
    if extra:
        event.update(extra)
    event["event_sha256"] = hashlib.sha256(
        (
            "campaign265|"
            + str(event_index)
            + "|"
            + previous_event_sha256
            + "|"
            + status_value
            + "|"
            + _canonical_json_sha256(
                {key: value for key, value in event.items() if key != "event_sha256"}
            )
        ).encode("utf-8")
    ).hexdigest()
    return event


def _append_event(
    path: Path,
    *,
    previous: Mapping[str, Any] | None,
    status_value: str,
    request: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    event = _event_payload(
        event_index=1 if previous is None else int(previous["event_index"]) + 1,
        previous_event_sha256=(
            ZERO_SHA256 if previous is None else str(previous["event_sha256"])
        ),
        status_value=status_value,
        request=request,
        extra=extra,
    )
    flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not (
            stat.S_ISREG(metadata.st_mode)
            and metadata.st_nlink == 1
            and stat.S_IMODE(metadata.st_mode) == FILE_MODE
        ):
            raise Campaign265WorkflowError("journal_identity_failed")
        _write_all(descriptor, _canonical_json_bytes(event) + b"\n")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)
    return event


def _read_journal(path: Path) -> list[dict[str, Any]]:
    if not _regular_private_file(path) or path.stat().st_size > MAX_JOURNAL_BYTES:
        raise Campaign265WorkflowError("journal_identity_or_size_failed")
    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise Campaign265WorkflowError("journal_unreadable") from exc
    if not raw_lines:
        raise Campaign265WorkflowError("journal_empty")
    events: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for raw_line in raw_lines:
        try:
            observed = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise Campaign265WorkflowError("journal_line_invalid") from exc
        if not isinstance(observed, dict):
            raise Campaign265WorkflowError("journal_event_not_object")
        event_index = 1 if previous is None else int(previous["event_index"]) + 1
        previous_sha = (
            ZERO_SHA256 if previous is None else str(previous["event_sha256"])
        )
        unsigned = {
            key: value for key, value in observed.items() if key != "event_sha256"
        }
        expected_sha = hashlib.sha256(
            (
                "campaign265|"
                + str(event_index)
                + "|"
                + previous_sha
                + "|"
                + str(observed.get("status"))
                + "|"
                + _canonical_json_sha256(unsigned)
            ).encode("utf-8")
        ).hexdigest()
        if not (
            observed.get("event_index") == event_index
            and observed.get("previous_event_sha256") == previous_sha
            and observed.get("event_sha256") == expected_sha
        ):
            raise Campaign265WorkflowError("journal_chain_or_payload_invalid")
        events.append(observed)
        previous = observed
    return events


def _checkpoint_path(root: Path, request: Mapping[str, Any]) -> Path:
    if request["api"] == "cb_basic":
        return root / "cb_basic.parquet"
    trade_date = str(request["parameters"]["trade_date"])
    return root / "cb_daily" / f"{trade_date}.parquet"


def _sidecar_path(checkpoint: Path) -> Path:
    return checkpoint.with_suffix(checkpoint.suffix + ".meta.json")


def _canonicalize_response(
    response: Any, request: Mapping[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not isinstance(response, pd.DataFrame):
        raise Campaign265WorkflowError("provider_response_not_dataframe")
    if not 1 <= len(response) < PLANNER.STRICT_ROW_CEILING:
        raise Campaign265WorkflowError("provider_response_row_gate_failed")
    if request["api"] == "cb_basic":
        frame, counters = ADAPTER.canonicalize_cb_basic(response)
    else:
        trade_date = str(request["parameters"]["trade_date"])
        iso_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}"
        frame, counters = ADAPTER.canonicalize_cb_daily(response, iso_date)
    if frame.empty:
        raise Campaign265WorkflowError("canonical_checkpoint_empty")
    return frame, dict(counters)


def _sanitized_counters(counters: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "source_rows",
        "exact_cb_rows",
        "rejected_non_cb_or_missing_type_rows",
        "finite_positive_amount_and_premium_rows",
        "ineligible_endpoint_rows",
        "network_or_credential_access_performed",
        "forbidden_fields_read",
    }
    return {key: counters[key] for key in sorted(allowed & counters.keys())}


def _commit_checkpoint(
    paths: AttemptPaths,
    request: Mapping[str, Any],
    frame: pd.DataFrame,
    counters: Mapping[str, Any],
) -> dict[str, Any]:
    checkpoint = _checkpoint_path(paths.staging_root, request)
    byte_sha, frame_sha = _atomic_private_parquet(checkpoint, frame)
    sidecar = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_source_checkpoint",
        "request_ordinal": request["ordinal"],
        "api": request["api"],
        "parameters": request["parameters"],
        "fields": request["fields"],
        "checkpoint_relative_path": str(checkpoint.relative_to(paths.staging_root)),
        "checkpoint_sha256": byte_sha,
        "frame_sha256": frame_sha,
        "schema": list(frame.columns),
        "counters": _sanitized_counters(counters),
        "raw_provider_response_persisted": False,
    }
    _atomic_private_write(_sidecar_path(checkpoint), _pretty_json_bytes(sidecar))
    return sidecar


def _validate_checkpoint(
    paths: AttemptPaths, request: Mapping[str, Any]
) -> dict[str, Any]:
    checkpoint = _checkpoint_path(paths.staging_root, request)
    sidecar_path = _sidecar_path(checkpoint)
    if not _regular_private_file(checkpoint) or not _regular_private_file(sidecar_path):
        raise Campaign265WorkflowError("committed_checkpoint_identity_failed")
    sidecar = _load_json(sidecar_path)
    if not (
        sidecar.get("request_ordinal") == request["ordinal"]
        and sidecar.get("api") == request["api"]
        and sidecar.get("parameters") == request["parameters"]
        and sidecar.get("fields") == request["fields"]
        and sidecar.get("checkpoint_sha256") == file_sha256(checkpoint)
    ):
        raise Campaign265WorkflowError("committed_checkpoint_binding_failed")
    frame = pd.read_parquet(checkpoint)
    if sidecar.get("frame_sha256") != _frame_sha256(frame):
        raise Campaign265WorkflowError("committed_checkpoint_frame_hash_failed")
    expected_schema = (
        list(ADAPTER.NORMALIZED_BASIC_FIELDS)
        if request["api"] == "cb_basic"
        else list(ADAPTER.NORMALIZED_DAILY_FIELDS)
    )
    if (
        list(frame.columns) != expected_schema
        or sidecar.get("schema") != expected_schema
    ):
        raise Campaign265WorkflowError("committed_checkpoint_schema_failed")
    return sidecar


def _journal_committed_prefix(
    events: Sequence[Mapping[str, Any]], requests: Sequence[Mapping[str, Any]]
) -> int:
    if events[0].get("status") != "attempt_created":
        raise Campaign265WorkflowError("journal_header_missing")
    committed = 0
    cursor = 1
    while cursor < len(events):
        if committed >= len(requests):
            if (
                events[cursor].get("status") == "success_committed"
                and cursor == len(events) - 1
            ):
                return committed
            raise Campaign265WorkflowError(
                "journal_event_after_complete_prefix_invalid"
            )
        request = requests[committed]
        expected_statuses = (
            "request_authorized",
            "response_received",
            "checkpoint_committed",
        )
        remaining = events[cursor : cursor + 3]
        if len(remaining) < 3:
            raise Campaign265WorkflowError("authorized_request_without_checkpoint")
        for event, status_value in zip(remaining, expected_statuses, strict=True):
            if not (
                event.get("status") == status_value
                and event.get("request_ordinal") == request["ordinal"]
                and event.get("api") == request["api"]
                and event.get("parameters") == request["parameters"]
                and event.get("fields") == request["fields"]
            ):
                raise Campaign265WorkflowError("journal_request_transition_invalid")
        committed += 1
        cursor += 3
    return committed


def _publish_failure(
    paths: AttemptPaths,
    *,
    stage_code: str,
    request_ordinal: int | None,
) -> None:
    if os.path.lexists(paths.terminal_failure):
        return
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_source_acceptance_failure",
        "status": "terminal_no_retry",
        "stage_code": stage_code,
        "request_ordinal": request_ordinal,
        "credential_value_or_digest_persisted": False,
        "raw_provider_row_or_value_persisted": False,
        "provider_response_row_count_persisted": False,
        "plaintext_provider_error_persisted": False,
        "same_request_retry_allowed": False,
    }
    _atomic_private_write(paths.terminal_failure, _pretty_json_bytes(record))


def _initialize_or_resume(
    paths: AttemptPaths,
    *,
    intent: Mapping[str, Any],
    requests: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    intent_exists = os.path.lexists(paths.intent)
    journal_exists = os.path.lexists(paths.journal)
    if intent_exists != journal_exists:
        raise Campaign265WorkflowError("intent_journal_pair_incomplete")
    if not intent_exists:
        if any(
            os.path.lexists(path)
            for path in (
                paths.staging_root,
                paths.final_root,
                paths.terminal_failure,
                paths.repository_manifest,
            )
        ):
            raise Campaign265WorkflowError("attempt_artifact_exists_without_intent")
        _create_exclusive_private(paths.intent, _pretty_json_bytes(intent))
        intent_sha = file_sha256(paths.intent)
        _create_exclusive_private(paths.journal, b"")
        header = _append_event(
            paths.journal,
            previous=None,
            status_value="attempt_created",
            extra={"intent_sha256": intent_sha},
        )
        return [header], 0

    if not _regular_private_file(paths.intent) or not _regular_private_file(
        paths.journal
    ):
        raise Campaign265WorkflowError("intent_or_journal_identity_failed")
    if _load_json(paths.intent) != intent:
        raise Campaign265WorkflowError("intent_payload_changed")
    events = _read_journal(paths.journal)
    if events[0].get("intent_sha256") != file_sha256(paths.intent):
        raise Campaign265WorkflowError("journal_intent_binding_failed")
    committed = _journal_committed_prefix(events, requests)
    for request in requests[:committed]:
        _validate_checkpoint(paths, request)
    if committed and not paths.staging_root.is_dir():
        raise Campaign265WorkflowError("committed_prefix_staging_root_missing")
    return events, committed


def _call_provider(provider: Provider, request: Mapping[str, Any]) -> pd.DataFrame:
    fields = ",".join(str(value) for value in request["fields"])
    if request["api"] == "cb_basic":
        return provider.cb_basic(fields=fields)
    return provider.cb_daily(
        trade_date=str(request["parameters"]["trade_date"]), fields=fields
    )


def _publish_success(
    paths: AttemptPaths,
    *,
    requests: Sequence[Mapping[str, Any]],
    sidecars: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if (
        len(sidecars) != len(requests)
        or len(requests) != PLANNER.EXACT_PROVIDER_CALL_COUNT
    ):
        raise Campaign265WorkflowError("success_request_count_not_exact")
    internal = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_source_manifest",
        "status": "complete_source_snapshot_pending_coverage_and_uniqueness",
        "provider": "Tushare Pro",
        "request_sequence_canonical_json_sha256": _canonical_json_sha256(requests),
        "committed_request_count": len(requests),
        "checkpoint_order_sha256": _canonical_json_sha256(
            [
                {
                    "request_ordinal": sidecar["request_ordinal"],
                    "checkpoint_relative_path": sidecar["checkpoint_relative_path"],
                    "checkpoint_sha256": sidecar["checkpoint_sha256"],
                    "frame_sha256": sidecar["frame_sha256"],
                }
                for sidecar in sidecars
            ]
        ),
        "raw_provider_response_persisted": False,
        "daily_price_or_forward_return_read": False,
    }
    internal_path = paths.staging_root / "source_manifest.json"
    _atomic_private_write(internal_path, _pretty_json_bytes(internal))
    internal_sha = file_sha256(internal_path)
    if os.path.lexists(paths.final_root):
        raise Campaign265WorkflowError("final_root_already_exists")
    paths.final_root.parent.mkdir(parents=True, exist_ok=True)
    if paths.staging_root.stat().st_dev != paths.final_root.parent.stat().st_dev:
        raise Campaign265WorkflowError("staging_final_filesystem_differs")
    os.replace(paths.staging_root, paths.final_root)
    _fsync_directory(paths.final_root.parent)
    repository = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_source_acceptance_manifest",
        "status": "accepted_source_snapshot_pending_coverage_and_ordered_uniqueness",
        "final_root": DESTINATIONS["final_root"],
        "internal_manifest": DESTINATIONS["final_root"] + "/source_manifest.json",
        "internal_manifest_sha256": internal_sha,
        "committed_request_count": len(requests),
        "request_sequence_canonical_json_sha256": _canonical_json_sha256(requests),
        "credential_value_or_digest_persisted": False,
        "raw_provider_response_persisted": False,
        "candidate_or_comparator_value_read": False,
        "daily_price_or_forward_return_read": False,
        "current_use_authorized": False,
    }
    _atomic_private_write(paths.repository_manifest, _pretty_json_bytes(repository))
    return repository


def execute_authorized_workflow(
    *,
    confirm_run: bool,
    token_loader: Callable[[], str] = _safe_dotenv_token,
    provider_factory: Callable[[str], Provider] = _default_provider_factory,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    repo_root: Path = REPO_ROOT,
    accepted_dates: Sequence[str] | None = None,
    require_v420_authorization: bool = True,
) -> int:
    """Execute or resume the exact one-shot state machine.

    Synthetic tests may set ``require_v420_authorization=False`` and a temporary
    root.  The public CLI never does so.
    """

    if not confirm_run:
        raise Campaign265WorkflowError("explicit_confirm_run_required")
    if require_v420_authorization and not _run_authorized():
        raise Campaign265WorkflowError("v420_run_authorization_not_accepted")

    dates = (
        list(accepted_dates)
        if accepted_dates is not None
        else PLANNER._accepted_dates()
    )
    requests = _request_sequence(dates)
    if accepted_dates is None and not (
        len(dates) == PLANNER.ACCEPTED_DATE_COUNT
        and len(requests) == PLANNER.EXACT_PROVIDER_CALL_COUNT
        and _canonical_json_sha256(requests) == PLANNER.REQUEST_SEQUENCE_SHA256
    ):
        raise Campaign265WorkflowError("frozen_request_schedule_changed")
    paths = AttemptPaths.from_root(repo_root)
    _assert_destination_directory_tree(repo_root, paths)
    if os.path.lexists(paths.terminal_failure):
        raise Campaign265WorkflowError("terminal_failure_already_consumed_attempt")
    if os.path.lexists(paths.repository_manifest):
        raise Campaign265WorkflowError("successful_attempt_already_consumed")

    intent = _intent_payload(dates, requests)
    try:
        events, committed = _initialize_or_resume(
            paths, intent=intent, requests=requests
        )
    except Campaign265WorkflowError:
        if os.path.lexists(paths.intent) or os.path.lexists(paths.journal):
            _publish_failure(
                paths,
                stage_code="existing_attempt_evidence_invalid_or_inflight",
                request_ordinal=None,
            )
            return 1
        raise
    previous = events[-1]
    sidecars = [
        _validate_checkpoint(paths, request) for request in requests[:committed]
    ]

    try:
        token = token_loader()
        if not isinstance(token, str) or not token:
            raise Campaign265WorkflowError("credential_not_nonempty_text")
    except Exception:
        _publish_failure(
            paths,
            stage_code="credential_not_accepted_after_attempt_consumption",
            request_ordinal=None,
        )
        return 1
    try:
        provider = provider_factory(token)
    except Exception:
        token = ""
        _publish_failure(
            paths,
            stage_code="provider_client_creation_failed",
            request_ordinal=None,
        )
        return 1
    token = ""

    last_provider_entry: float | None = None
    for request in requests[committed:]:
        ordinal = int(request["ordinal"])
        try:
            if last_provider_entry is not None:
                wait_seconds = PLANNER.MINIMUM_REQUEST_INTERVAL_SECONDS - (
                    monotonic() - last_provider_entry
                )
                if wait_seconds > 0:
                    sleep(wait_seconds)
            previous = _append_event(
                paths.journal,
                previous=previous,
                status_value="request_authorized",
                request=request,
            )
            last_provider_entry = monotonic()
            response = _call_provider(provider, request)
            previous = _append_event(
                paths.journal,
                previous=previous,
                status_value="response_received",
                request=request,
            )
            frame, counters = _canonicalize_response(response, request)
            sidecar = _commit_checkpoint(paths, request, frame, counters)
            previous = _append_event(
                paths.journal,
                previous=previous,
                status_value="checkpoint_committed",
                request=request,
                extra={
                    "checkpoint_sha256": sidecar["checkpoint_sha256"],
                    "frame_sha256": sidecar["frame_sha256"],
                },
            )
            sidecars.append(sidecar)
        except Exception:
            _publish_failure(
                paths,
                stage_code="request_response_schema_or_persistence_failed",
                request_ordinal=ordinal,
            )
            return 1

    try:
        repository = _publish_success(paths, requests=requests, sidecars=sidecars)
        previous = _append_event(
            paths.journal,
            previous=previous,
            status_value="success_committed",
            extra={
                "repository_manifest_sha256": file_sha256(paths.repository_manifest),
                "committed_request_count": repository["committed_request_count"],
            },
        )
        if previous.get("status") != "success_committed":
            raise Campaign265WorkflowError("success_journal_commit_failed")
    except Exception:
        _publish_failure(
            paths,
            stage_code="final_publication_failed",
            request_ordinal=None,
        )
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    if _run_authorized():
        run = subparsers.add_parser("run")
        run.add_argument("--confirm-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.command == "plan":
        plan = build_plan()
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return int(plan["exit_code_if_executed"])
    if arguments.command == "run":
        return execute_authorized_workflow(confirm_run=bool(arguments.confirm_run))
    raise Campaign265WorkflowError("unsupported_command")


if __name__ == "__main__":
    raise SystemExit(main())
