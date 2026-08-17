#!/usr/bin/env python3
"""Fail-closed orchestration for one registered Candidate49 future session.

The workflow keeps the daily-provider migration, quarterly-quality refresh,
and minute source-to-signal collection in separate child processes.  It never
places the Tushare Token on a command line and never reads a historical
Candidate49 return.
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import fcntl
import hashlib
import json
import os
import stat
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_candidate49_future_session_workflow_protocol.json"
)
PROTOCOL_SHA256 = (
    "6ff5636a3f7ef65e93452098186b3aecf9231d68873ab8a1070afb91d699ef7c"
)
AUTHORITATIVE_STATE_PATH = (
    REPO_ROOT / "docs" / "a_share_three_day_iteration_status_20260725_future_only.json"
)
AUTHORITATIVE_STATE_SHA256 = (
    "d44e1cb3707cce194eed37e99cc90f865396b1de8c35e02a393a2a243d973466"
)
FUTURE_POLICY_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_future_only_minute_research_policy_20260725.json"
)
FUTURE_POLICY_SHA256 = (
    "52ca8bfa7201509fe891d0af3d1c87aeebd64e47e6ec6641e897849411df408c"
)
REGISTRATION_PATH = (
    REPO_ROOT
    / "docs"
    / (
        "a_share_tushare_intraday_cumulative_vwap_crossing_rate_"
        "future_observation_registration.json"
    )
)
REGISTRATION_SHA256 = (
    "431cb0b3b078823f08b888bf4c499bcc5088309a2e58e9de5cb9a9aaa849ffa9"
)
DAILY_MIGRATION_PROTOCOL_PATH = (
    REPO_ROOT / "docs" / "a_share_tushare_daily_provider_migration_protocol.json"
)
DAILY_MIGRATION_PROTOCOL_SHA256 = (
    "bf3278511b5b0fe7911e1cca44ac5dae3ce8a2b0633a9928aff727dfcfd25e1c"
)
DAILY_REFERENCE_MANIFEST_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/raw/a_share/rich/tushare/daily/"
    "snapshots/tushare_daily_2019_2025_acf72e28/snapshot_manifest.json"
)
DAILY_REFERENCE_MANIFEST_SHA256 = (
    "87feded06b6726d282abf52c8fd1c30340728ae37c2de201a3a8f30e1a556e2d"
)
DAILY_REFERENCE_ROWS = 7_989_350
DAILY_REFERENCE_START = "2019-01-01"
DAILY_REFERENCE_END = "2025-12-31"

PYTHON = sys.executable
PIPELINE_SCRIPT = REPO_ROOT / "scripts" / "a_share_data_pipeline.py"
MIGRATION_SCRIPT = REPO_ROOT / "scripts" / "a_share_tushare_daily_migration.py"
RESEARCH_SCRIPT = (
    REPO_ROOT / "scripts" / "a_share_short_horizon_factor_research.py"
)
OBSERVATION_SCRIPT = (
    REPO_ROOT / "scripts" / "a_share_tushare_candidate49_future_observation.py"
)

CHINA_TZ = ZoneInfo("Asia/Shanghai")
EARLIEST_SESSION = dt.date(2026, 7, 27)
NOT_BEFORE_LOCAL_TIME = dt.time(16, 30)
FIXED_MINUTE_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DATA_ROOT_ENV = "QLIB_A_SHARE_DATA_ROOT"
TOKEN_ENV = "TUSHARE_TOKEN"
REPO_DOTENV_PATH = REPO_ROOT / ".env"
DOTENV_MAX_BYTES = 64 * 1024
FINAL_RECORD_KIND = "a_share_tushare_candidate49_future_session_workflow"
FINAL_RECORD_STATUS = "completed_future_session_source_to_signal_workflow"
SIGNAL_LEDGER_PATH = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER_PATH = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "candidate49_future_execution_ledger.json"
)


class Candidate49FutureSessionWorkflowError(RuntimeError):
    """Raised when a workflow boundary or child result is rejected."""


@dataclass(frozen=True)
class WorkflowConfig:
    session: dt.date
    staging_root: Path
    minute_data_root: Path


@dataclass(frozen=True)
class CommandOutcome:
    returncode: int
    stdout: str
    stderr: str


CommandExecutor = Callable[
    [str, Sequence[str], Mapping[str, str]],
    CommandOutcome,
]
TokenLoader = Callable[[], str | None]
LockFactory = Callable[[Path], Any]


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Candidate49FutureSessionWorkflowError(
            f"required JSON is unreadable: {path}"
        ) from exc
    if not isinstance(value, dict):
        raise Candidate49FutureSessionWorkflowError(
            f"required JSON is not an object: {path}"
        )
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise Candidate49FutureSessionWorkflowError(message)


def validate_static_evidence() -> dict[str, str]:
    """Verify every frozen control file before a child or provider call."""

    expected = {
        PROTOCOL_PATH: PROTOCOL_SHA256,
        AUTHORITATIVE_STATE_PATH: AUTHORITATIVE_STATE_SHA256,
        FUTURE_POLICY_PATH: FUTURE_POLICY_SHA256,
        REGISTRATION_PATH: REGISTRATION_SHA256,
        DAILY_MIGRATION_PROTOCOL_PATH: DAILY_MIGRATION_PROTOCOL_SHA256,
    }
    observed: dict[str, str] = {}
    for path, wanted in expected.items():
        if not path.is_file():
            raise Candidate49FutureSessionWorkflowError(
                f"required frozen evidence is missing: {path}"
            )
        actual = file_digest(path)
        if actual != wanted:
            raise Candidate49FutureSessionWorkflowError(
                f"required frozen evidence changed: {path}"
            )
        observed[str(path.relative_to(REPO_ROOT))] = actual

    protocol = _read_json(PROTOCOL_PATH)
    _require(
        protocol.get("kind")
        == "a_share_tushare_candidate49_future_session_workflow_protocol",
        "Candidate49 future-session workflow protocol kind changed",
    )
    _require(
        protocol.get("status")
        == "frozen_before_first_future_session_provider_request",
        "Candidate49 future-session workflow protocol is not frozen",
    )
    fixed_paths = protocol.get("fixed_paths", {})
    daily_provider = protocol.get("daily_provider", {})
    _require(
        protocol.get("version") == 2
        and fixed_paths.get("accepted_tushare_daily_reference_manifest")
        == str(DAILY_REFERENCE_MANIFEST_PATH)
        and fixed_paths.get(
            "accepted_tushare_daily_reference_manifest_sha256"
        )
        == DAILY_REFERENCE_MANIFEST_SHA256
        and daily_provider.get("accepted_reference_range")
        == [DAILY_REFERENCE_START, DAILY_REFERENCE_END]
        and daily_provider.get("accepted_reference_rows")
        == DAILY_REFERENCE_ROWS
        and daily_provider.get(
            "covered_reference_daily_sessions_may_be_requested_again"
        )
        is False,
        "Candidate49 daily-reference reuse protocol changed",
    )
    state = _read_json(AUTHORITATIVE_STATE_PATH)
    _require(
        state.get("status")
        == (
            "aggregation_blocked_candidate49_future_only_registered_"
            "pending_first_post_registration_session"
        ),
        "authoritative three-session state changed",
    )
    counts = state.get("research_counts", {})
    decision = state.get("decision", {})
    _require(
        counts.get("terminal_mechanism_count") == 48
        and counts.get("active_future_only_candidate_count") == 1
        and counts.get("dual_gate_qualified_factor_count") == 0,
        "authoritative Candidate49 frontier counts changed",
    )
    _require(
        decision.get("aggregation_allowed") is False
        and decision.get("current_scoring_allowed") is False
        and decision.get("selection_allowed") is False
        and decision.get("sizing_allowed") is False
        and decision.get("orders_allowed") is False
        and decision.get("candidate50_activation_allowed") is False,
        "authoritative Candidate49 research boundary changed",
    )
    registration = _read_json(REGISTRATION_PATH)
    _require(
        registration.get("registration_id")
        == "candidate49_intraday_cumulative_vwap_crossing_rate_240m_v1",
        "Candidate49 registration identity changed",
    )
    return observed


def normalize_config(config: WorkflowConfig) -> WorkflowConfig:
    if not config.staging_root.is_absolute():
        raise Candidate49FutureSessionWorkflowError(
            "--staging-root must be an explicit absolute path"
        )
    if not config.minute_data_root.is_absolute():
        raise Candidate49FutureSessionWorkflowError(
            "--minute-data-root must be an explicit absolute path"
        )
    staging = config.staging_root.expanduser().resolve()
    minute = config.minute_data_root.expanduser().resolve()
    fixed_minute = FIXED_MINUTE_DATA_ROOT.expanduser().resolve()
    _require(
        config.session >= EARLIEST_SESSION,
        "Candidate49 session precedes its frozen future-only boundary",
    )
    _require(
        minute == fixed_minute,
        "Candidate49 minute root differs from the user-authorized frozen root",
    )
    _require(
        minute.is_dir(),
        "Candidate49 minute root is missing; do not recreate the accepted root",
    )
    _require(
        staging != minute and staging not in minute.parents and minute not in staging.parents,
        "daily staging and minute roots must be disjoint",
    )
    _require(
        staging != REPO_ROOT and REPO_ROOT not in staging.parents,
        "daily staging root must remain outside the repository",
    )
    return WorkflowConfig(
        session=config.session,
        staging_root=staging,
        minute_data_root=minute,
    )


def _time_failures(session: dt.date, now: dt.datetime) -> list[str]:
    local = now.astimezone(CHINA_TZ) if now.tzinfo else now.replace(tzinfo=CHINA_TZ)
    failures: list[str] = []
    if local.date() < session:
        failures.append("signal_session_has_not_arrived")
    elif local.date() > session:
        failures.append("past_session_delayed_source_to_signal_backfill_forbidden")
    elif local.time().replace(tzinfo=None) < NOT_BEFORE_LOCAL_TIME:
        failures.append("signal_session_close_buffer_not_finished")
    return failures


def _parse_dotenv_token(path: Path) -> str | None:
    """Read TUSHARE_TOKEN from a small, regular, non-symlink dotenv file."""

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise Candidate49FutureSessionWorkflowError(
            f"repository dotenv cannot be opened safely: {path}"
        ) from exc

    try:
        file_stat = os.fstat(descriptor)
        _require(
            stat.S_ISREG(file_stat.st_mode),
            f"repository dotenv is not a regular file: {path}",
        )
        _require(
            file_stat.st_size <= DOTENV_MAX_BYTES,
            f"repository dotenv exceeds {DOTENV_MAX_BYTES} bytes: {path}",
        )
        payload = os.read(descriptor, DOTENV_MAX_BYTES + 1)
    finally:
        os.close(descriptor)

    _require(
        len(payload) <= DOTENV_MAX_BYTES,
        f"repository dotenv exceeds {DOTENV_MAX_BYTES} bytes: {path}",
    )
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise Candidate49FutureSessionWorkflowError(
            f"repository dotenv is not UTF-8: {path}"
        ) from exc

    matches: list[tuple[int, str]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
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
            _require(
                len(value) >= 2 and value[-1] == quote,
                (
                    f"repository dotenv has an unterminated {TOKEN_ENV} quote "
                    f"at line {line_number}"
                ),
            )
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        matches.append((line_number, value.strip()))

    _require(
        len(matches) <= 1,
        f"repository dotenv declares {TOKEN_ENV} more than once: {path}",
    )
    if not matches:
        return None
    return matches[0][1] or None


def _load_token(dotenv_path: Path = REPO_DOTENV_PATH) -> str | None:
    token = os.environ.get(TOKEN_ENV, "").strip()
    if token:
        return token
    token = _parse_dotenv_token(dotenv_path)
    if token:
        return token
    try:
        completed = subprocess.run(
            ["launchctl", "getenv", TOKEN_ENV],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError:
        return None
    token = completed.stdout.strip() if completed.returncode == 0 else ""
    return token or None


def _child_environment(token: str | None = None) -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop(DATA_ROOT_ENV, None)
    environment.pop(TOKEN_ENV, None)
    if token:
        environment[TOKEN_ENV] = token
    return environment


def _default_executor(
    step: str,
    argv: Sequence[str],
    environment: Mapping[str, str],
) -> CommandOutcome:
    del step
    completed = subprocess.run(
        list(argv),
        cwd=REPO_ROOT,
        env=dict(environment),
        check=False,
        text=True,
        capture_output=True,
    )
    return CommandOutcome(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _redacted_tail(value: str, token: str | None, limit: int = 1200) -> str:
    safe = value
    if token:
        safe = safe.replace(token, "[REDACTED]")
    return " ".join(safe.split())[-limit:]


def _last_json_object(value: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    last: dict[str, Any] | None = None
    for index, character in enumerate(value):
        if character != "{":
            continue
        try:
            parsed, end = decoder.raw_decode(value[index:])
        except json.JSONDecodeError:
            continue
        if value[index + end :].strip():
            continue
        if isinstance(parsed, dict):
            last = parsed
    if last is None:
        raise Candidate49FutureSessionWorkflowError(
            "child command did not return a final JSON object"
        )
    return last


def _step_summary(
    name: str,
    outcome: CommandOutcome,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    keys = (
        "status",
        "ready",
        "recommended_cli_exit_code",
        "manifest_path",
        "manifest_sha256",
        "active_data_root",
        "provider_request_issued",
        "provider_calls_this_invocation",
        "raw_manifest",
        "raw_manifest_sha256",
        "factor_manifest",
        "factor_manifest_sha256",
        "eligible_names",
        "signal_entry_sha256",
        "forward_return_fields_read",
        "execution_or_order_performed",
    )
    return {
        "name": name,
        "returncode": outcome.returncode,
        **{key: payload[key] for key in keys if key in payload},
    }


def _run_json(
    *,
    name: str,
    argv: Sequence[str],
    environment: Mapping[str, str],
    executor: CommandExecutor,
    token: str | None = None,
    allowed_returncodes: set[int] | None = None,
    steps: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], int]:
    allowed = allowed_returncodes or {0}
    print(f"[candidate49-workflow] starting {name}", file=sys.stderr, flush=True)
    outcome = executor(name, argv, environment)
    if outcome.returncode not in allowed:
        detail = _redacted_tail(
            outcome.stderr or outcome.stdout,
            token,
        )
        raise Candidate49FutureSessionWorkflowError(
            f"{name} failed with exit {outcome.returncode}: {detail}"
        )
    try:
        payload = _last_json_object(outcome.stdout)
    except Candidate49FutureSessionWorkflowError as exc:
        detail = _redacted_tail(
            outcome.stderr or outcome.stdout,
            token,
        )
        raise Candidate49FutureSessionWorkflowError(
            f"{name} returned invalid JSON: {detail}"
        ) from exc
    if steps is not None:
        steps.append(_step_summary(name, outcome, payload))
    print(
        f"[candidate49-workflow] completed {name} "
        f"status={payload.get('status', 'unspecified')}",
        file=sys.stderr,
        flush=True,
    )
    return payload, outcome.returncode


def _run_text(
    *,
    name: str,
    argv: Sequence[str],
    environment: Mapping[str, str],
    executor: CommandExecutor,
    steps: list[dict[str, Any]] | None = None,
) -> str:
    print(f"[candidate49-workflow] starting {name}", file=sys.stderr, flush=True)
    outcome = executor(name, argv, environment)
    if outcome.returncode != 0:
        detail = _redacted_tail(outcome.stderr or outcome.stdout, None)
        raise Candidate49FutureSessionWorkflowError(
            f"{name} failed with exit {outcome.returncode}: {detail}"
        )
    value = outcome.stdout.strip()
    _require(bool(value), f"{name} returned empty output")
    if steps is not None:
        steps.append(
            {
                "name": name,
                "returncode": outcome.returncode,
                "resolved_path": value,
            }
        )
    print(f"[candidate49-workflow] completed {name}", file=sys.stderr, flush=True)
    return value


def _pipeline_status(
    *,
    executor: CommandExecutor,
    steps: list[dict[str, Any]] | None = None,
    name: str = "active-daily-status",
) -> dict[str, Any]:
    payload, _ = _run_json(
        name=name,
        argv=[PYTHON, str(PIPELINE_SCRIPT), "status"],
        environment=_child_environment(),
        executor=executor,
        steps=steps,
    )
    _require(
        isinstance(payload.get("price_basis"), dict),
        "active daily status lacks price-basis evidence",
    )
    return payload


def _migration_status(
    *,
    staging_root: Path,
    reference_manifest_path: Path = DAILY_REFERENCE_MANIFEST_PATH,
    reference_manifest_sha256: str = DAILY_REFERENCE_MANIFEST_SHA256,
    executor: CommandExecutor,
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    reference_manifest_path = reference_manifest_path.expanduser().resolve()
    payload, _ = _run_json(
        name="daily-migration-status",
        argv=[
            PYTHON,
            str(MIGRATION_SCRIPT),
            "status",
            "--staging-root",
            str(staging_root),
            "--reference-manifest",
            str(reference_manifest_path),
        ],
        environment=_child_environment(),
        executor=executor,
        steps=steps,
    )
    _require(
        payload.get("kind") == "a_share_tushare_daily_provider_migration_status",
        "daily migration status kind changed",
    )
    reference = payload.get("reference_snapshot")
    _require(
        payload.get("reference_manifest_valid") is True
        and payload.get("reference_manifest_sha256")
        == reference_manifest_sha256
        and payload.get("reference_error") is None
        and isinstance(reference, dict)
        and Path(str(reference.get("path", ""))).expanduser().resolve()
        == reference_manifest_path
        and reference.get("sha256") == reference_manifest_sha256
        and reference.get("provider") == "tushare"
        and reference.get("requested_start") == DAILY_REFERENCE_START
        and reference.get("requested_end") == DAILY_REFERENCE_END
        and reference.get("rows") == DAILY_REFERENCE_ROWS
        and reference.get("annual_partitions") == 7
        and isinstance(reference.get("sessions"), int)
        and reference["sessions"] > 0
        and reference.get("valid") is True,
        "accepted 2019-2025 Tushare daily reference changed",
    )
    return payload


def _active_daily_source(status: Mapping[str, Any]) -> str:
    price_basis = status.get("price_basis", {})
    sources = price_basis.get("daily_sources", [])
    _require(
        isinstance(sources, list) and len(sources) == 1,
        "active daily status must expose exactly one source",
    )
    source = str(sources[0])
    _require(
        source in {"baostock", "tushare"},
        "active daily source is not supported by the frozen workflow",
    )
    return source


def _calendar_end(status: Mapping[str, Any]) -> dt.date:
    value = status.get("qlib_calendar_end")
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError as exc:
        raise Candidate49FutureSessionWorkflowError(
            "active daily calendar cutoff is invalid"
        ) from exc


def _load_accepted_active_root(
    *,
    status: Mapping[str, Any],
    session: dt.date,
) -> tuple[Path, Path]:
    root = Path(str(status.get("data_root", ""))).expanduser().resolve()
    price_basis = status.get("price_basis", {})
    _require(
        price_basis.get("status") == "passed"
        and price_basis.get("daily_sources") == ["tushare"]
        and not price_basis.get("failures"),
        "active daily root is not an accepted one-source Tushare provider",
    )
    _require(
        _calendar_end(status) == session,
        "active Tushare calendar cutoff does not equal the signal session",
    )
    acceptance_path = (
        root / "metadata" / "tushare_daily_provider_acceptance.json"
    )
    activation_path = root / "metadata" / "tushare_daily_activation.json"
    acceptance = _read_json(acceptance_path)
    activation = _read_json(activation_path)
    _require(
        acceptance.get("status")
        == "accepted_staging_pending_explicit_crash_safe_activation"
        and acceptance.get("protocol_sha256") == DAILY_MIGRATION_PROTOCOL_SHA256
        and acceptance.get("through_date") == session.isoformat()
        and acceptance.get("daily_source") == "tushare",
        "active Tushare acceptance record changed",
    )
    _require(
        activation.get("status") == "active_via_atomic_repository_pointer"
        and activation.get("protocol_sha256") == DAILY_MIGRATION_PROTOCOL_SHA256
        and Path(str(activation.get("staging_root", ""))).resolve() == root,
        "active Tushare activation record changed",
    )
    return root, activation_path


def _load_daily_reference_reuse_evidence(
    *,
    active_root: Path,
    activation_path: Path,
    session: dt.date,
    reference_manifest_path: Path = DAILY_REFERENCE_MANIFEST_PATH,
    reference_manifest_sha256: str = DAILY_REFERENCE_MANIFEST_SHA256,
) -> dict[str, Any]:
    reference_manifest_path = reference_manifest_path.expanduser().resolve()
    activation = _read_json(activation_path)
    acceptance_path = (
        active_root / "metadata" / "tushare_daily_provider_acceptance.json"
    )
    _require(
        Path(
            str(activation.get("acceptance_manifest_path", ""))
        ).expanduser().resolve()
        == acceptance_path
        and isinstance(activation.get("acceptance_manifest_sha256"), str),
        "daily activation does not bind the accepted staging manifest",
    )
    acceptance_link = _validate_link(
        acceptance_path,
        str(activation["acceptance_manifest_sha256"]),
    )
    acceptance = _read_json(acceptance_path)
    source_manifest_path = (
        active_root
        / "raw"
        / "a_share"
        / "rich"
        / "tushare"
        / "daily_provider_migration_v1"
        / "source_manifest.json"
    )
    _require(
        Path(
            str(acceptance.get("source_manifest_path", ""))
        ).expanduser().resolve()
        == source_manifest_path
        and isinstance(acceptance.get("source_manifest_sha256"), str),
        "daily acceptance does not bind its source manifest",
    )
    source_link = _validate_link(
        source_manifest_path,
        str(acceptance["source_manifest_sha256"]),
    )
    reference_link = _validate_link(
        reference_manifest_path,
        reference_manifest_sha256,
    )
    source = _read_json(source_manifest_path)
    count_fields = (
        "reference_daily_sessions_reused",
        "reference_daily_sessions_requested_this_invocation",
        "requested_daily_sessions_this_invocation",
        "requested_daily_basic_sessions_this_invocation",
        "provider_calls_this_invocation",
    )
    _require(
        all(
            isinstance(source.get(field), int) and source[field] >= 0
            for field in count_fields
        ),
        "daily source reuse counters are invalid",
    )
    _require(
        source.get("kind")
        == "a_share_tushare_daily_provider_migration_source_snapshot"
        and source.get("status")
        == "complete_pending_canonical_build_and_acceptance"
        and source.get("protocol_sha256") == DAILY_MIGRATION_PROTOCOL_SHA256
        and source.get("through_date") == session.isoformat()
        and source.get("accepted_reference_manifest_path")
        == str(reference_manifest_path)
        and source.get("accepted_reference_manifest_sha256")
        == reference_manifest_sha256
        and source.get("accepted_reference_rows") == DAILY_REFERENCE_ROWS
        and source["reference_daily_sessions_reused"] > 0
        and source["reference_daily_sessions_requested_this_invocation"] == 0
        and source.get("active_root_mutated") is False
        and source.get("forward_return_fields_read") is False
        and source.get("factor_values_read") is False,
        "daily source manifest does not prove accepted historical reuse",
    )
    return {
        "accepted_reference_link": reference_link,
        "acceptance_link": acceptance_link,
        "source_manifest_link": source_link,
        "accepted_reference_range": [
            DAILY_REFERENCE_START,
            DAILY_REFERENCE_END,
        ],
        "accepted_reference_rows": DAILY_REFERENCE_ROWS,
        "reference_daily_sessions_reused": source[
            "reference_daily_sessions_reused"
        ],
        "reference_daily_sessions_requested_this_invocation": 0,
        "requested_daily_sessions_this_invocation": source[
            "requested_daily_sessions_this_invocation"
        ],
        "requested_daily_basic_sessions_this_invocation": source[
            "requested_daily_basic_sessions_this_invocation"
        ],
        "daily_provider_calls_this_invocation": source[
            "provider_calls_this_invocation"
        ],
    }


def latest_completed_quarter_end(value: dt.date) -> dt.date:
    quarter_start = ((value.month - 1) // 3) * 3 + 1
    current_end_month = quarter_start + 2
    current_end = dt.date(
        value.year,
        current_end_month,
        calendar.monthrange(value.year, current_end_month)[1],
    )
    if value >= current_end:
        return current_end
    previous_end_month = quarter_start - 1
    previous_year = value.year
    if previous_end_month == 0:
        previous_end_month = 12
        previous_year -= 1
    return dt.date(
        previous_year,
        previous_end_month,
        calendar.monthrange(previous_year, previous_end_month)[1],
    )


def _candidate_argv(
    *,
    config: WorkflowConfig,
    active_root: Path,
    preflight_only: bool,
) -> list[str]:
    argv = [
        PYTHON,
        str(OBSERVATION_SCRIPT),
        "--data-root",
        str(config.minute_data_root),
        "--session",
        config.session.isoformat(),
        "--provider-uri",
        str(active_root / "qlib" / "cn_a_share"),
        "--daily-raw-root",
        str(active_root / "raw" / "a_share" / "daily"),
        "--fundamentals",
        str(
            active_root
            / "raw"
            / "a_share"
            / "fundamentals"
            / "quarterly_quality_future.parquet"
        ),
        "--fundamentals-manifest",
        str(active_root / "metadata" / "quarterly_quality_future_manifest.json"),
    ]
    argv.append("--preflight-only" if preflight_only else "--allow-large")
    return argv


def _validate_candidate_preflight(payload: Mapping[str, Any]) -> None:
    _require(
        payload.get("ready") is True
        and payload.get("recommended_cli_exit_code") == 0
        and payload.get("status")
        == "ready_for_explicit_future_source_to_signal_collection",
        "Candidate49 combined preflight did not return the frozen ready state",
    )
    _require(
        payload.get("provider_request_issued") is False
        and payload.get("minute_rows_read") is False
        and payload.get("signal_or_execution_entry_written") is False
        and payload.get("filesystem_write_performed") is False,
        "Candidate49 combined preflight crossed its zero-request/zero-write boundary",
    )


def _validate_link(path: Path, expected_sha256: str) -> dict[str, str]:
    resolved = path.expanduser().resolve()
    _require(resolved.is_file(), f"workflow evidence link is missing: {resolved}")
    actual = file_digest(resolved)
    _require(
        actual == expected_sha256,
        f"workflow evidence link changed: {resolved}",
    )
    return {"path": str(resolved), "sha256": actual}


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _atomic_json_digest(value: Mapping[str, Any]) -> str:
    payload = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _ledger_observation(path: Path, kind: str) -> dict[str, Any]:
    import a_share_tushare_intraday_cumulative_vwap_crossing_rate as candidate

    resolved = path.expanduser().resolve()
    ledger = candidate.validate_future_ledger(resolved, kind)
    entries = list(ledger["entries"])
    return {
        "path": str(resolved),
        "sha256_at_workflow": file_digest(resolved),
        "entry_count_at_workflow": len(entries),
        "chain_tip_sha256_at_workflow": ledger["chain_tip_sha256"],
        "entry_prefix_sha256_at_workflow": _canonical_digest(entries),
    }


def _validate_ledger_observation(
    observed: Any,
    *,
    path: Path,
    kind: str,
) -> None:
    import a_share_tushare_intraday_cumulative_vwap_crossing_rate as candidate

    _require(
        isinstance(observed, dict),
        "existing workflow ledger observation is invalid",
    )
    resolved = path.expanduser().resolve()
    ledger = candidate.validate_future_ledger(resolved, kind)
    count = observed.get("entry_count_at_workflow")
    _require(
        isinstance(count, int)
        and not isinstance(count, bool)
        and 0 <= count <= len(ledger["entries"]),
        "existing workflow ledger observation count changed",
    )
    prefix = list(ledger["entries"][:count])
    chain_tip = (
        ledger["genesis_sha256"]
        if not prefix
        else prefix[-1]["entry_sha256"]
    )
    prefix_ledger = {
        **ledger,
        "status": (
            "empty_pending_first_eligible_future_session"
            if not prefix
            else "active_append_only_future_observation"
        ),
        "entries": prefix,
        "chain_tip_sha256": chain_tip,
    }
    expected = {
        "path": str(resolved),
        "sha256_at_workflow": _atomic_json_digest(prefix_ledger),
        "entry_count_at_workflow": count,
        "chain_tip_sha256_at_workflow": chain_tip,
        "entry_prefix_sha256_at_workflow": _canonical_digest(prefix),
    }
    _require(
        observed == expected,
        "existing workflow ledger observation changed",
    )


def _candidate49_artifact_summary(
    config: WorkflowConfig,
) -> dict[str, Any]:
    import a_share_tushare_candidate49_future_observation as observation

    raw_root, _, factor_root, _ = observation._session_roots(
        config.minute_data_root,
        config.session,
    )
    raw_manifest_path = raw_root / "snapshot_manifest.json"
    factor_manifest_path = factor_root / "factor_manifest.json"
    signals = observation.validate_signal_ledger_semantics(
        SIGNAL_LEDGER_PATH
    )
    matching = [
        entry
        for entry in signals
        if entry.get("session_date") == config.session.isoformat()
    ]
    if matching:
        signal = matching[0]
        _require(
            Path(
                str((signal.get("raw_snapshot") or {}).get("path") or "")
            ).expanduser().resolve()
            == raw_manifest_path
            and Path(
                str(
                    (signal.get("factor_snapshot") or {}).get("path")
                    or ""
                )
            ).expanduser().resolve()
            == factor_manifest_path,
            "Candidate49 workflow signal evidence path changed",
        )
        raw_manifest = _read_json(raw_manifest_path)
        factor_manifest = _read_json(factor_manifest_path)
    else:
        raw_manifest = observation._validate_raw_manifest(
            raw_manifest_path,
            session_date=config.session,
        )
        factor_manifest, _ = observation._validate_factor_snapshot(
            factor_manifest_path,
            session_date=config.session,
            raw_manifest_path=raw_manifest_path,
            raw_manifest=raw_manifest,
        )
    eligible_names = int(factor_manifest["eligible_rows"])
    if eligible_names >= observation.MINIMUM_SIGNAL_NAMES:
        _require(
            len(matching) == 1,
            "Candidate49 workflow artifacts lack the deterministic signal",
        )
    else:
        _require(
            not matching,
            "Candidate49 workflow artifacts contain an ineligible signal",
        )
    binding = (
        (raw_manifest.get("frozen_context") or {}).get(
            "active_root_binding"
        )
        or {}
    )
    active_root = Path(
        str(binding.get("active_root") or "")
    ).expanduser().resolve()
    _require(
        active_root.is_dir(),
        "Candidate49 workflow raw evidence active root changed",
    )
    return {
        "active_data_root": str(active_root),
        "raw_manifest_path": str(raw_manifest_path),
        "raw_manifest_sha256": file_digest(raw_manifest_path),
        "factor_manifest_path": str(factor_manifest_path),
        "factor_manifest_sha256": file_digest(factor_manifest_path),
        "eligible_names": eligible_names,
        "signal_entry_sha256": (
            None if not matching else matching[0]["entry_sha256"]
        ),
        "raw_provider_calls": int(
            sum(
                int(record["provider_calls"])
                for record in raw_manifest["files"]
            )
        ),
    }


def _validate_candidate49_ledgers_semantically() -> None:
    import a_share_tushare_candidate49_future_execution as execution

    execution.validate_reporting_state(
        signal_path=SIGNAL_LEDGER_PATH,
        execution_path=EXECUTION_LEDGER_PATH,
        evaluation_root=(
            EXECUTION_LEDGER_PATH.parent
            / "candidate49_future_evaluations"
        ),
    )


def _candidate49_outcome(
    summary: Mapping[str, Any],
) -> str:
    eligible = int(summary["eligible_names"])
    signal_sha256 = summary["signal_entry_sha256"]
    if signal_sha256 is None:
        _require(
            eligible < 50,
            "Candidate49 no-signal artifacts meet the signal-name gate",
        )
        return "future_session_frozen_without_signal_fewer_than_50_names"
    _require(
        eligible >= 50,
        "Candidate49 signal artifacts fail the signal-name gate",
    )
    return "future_signal_present"


def _validate_candidate49_child_status(
    *,
    status: Any,
    summary: Mapping[str, Any],
) -> str:
    outcome = _candidate49_outcome(summary)
    if outcome == "future_session_frozen_without_signal_fewer_than_50_names":
        _require(
            status
            == "future_session_frozen_without_signal_fewer_than_50_names"
            and summary["signal_entry_sha256"] is None,
            "existing workflow Candidate49 no-signal status changed",
        )
    else:
        _require(
            status
            in {
                "future_signal_appended",
                "future_signal_already_present_idempotent",
            }
            and summary["signal_entry_sha256"] is not None,
            "existing workflow Candidate49 signal status changed",
        )
    return outcome


def _phase_receipts(
    *,
    config: WorkflowConfig,
    active_root: Path,
    daily_reuse: Mapping[str, Any],
    evidence: Mapping[str, Mapping[str, str]],
    summary: Mapping[str, Any],
) -> list[dict[str, Any]]:
    outcome = _candidate49_outcome(summary)
    return [
        {
            "ordinal": 1,
            "phase": "static_research_boundary",
            "status": "validated",
            "protocol_sha256": PROTOCOL_SHA256,
            "authoritative_state_sha256": AUTHORITATIVE_STATE_SHA256,
        },
        {
            "ordinal": 2,
            "phase": "tushare_daily_root",
            "status": "accepted_active_exact_session",
            "active_data_root": str(active_root),
            "calendar_cutoff": config.session.isoformat(),
            "accepted_reference_sha256": evidence[
                "accepted_tushare_daily_reference"
            ]["sha256"],
            "source_manifest_sha256": evidence["daily_source_manifest"][
                "sha256"
            ],
            "acceptance_sha256": evidence["daily_acceptance"]["sha256"],
            "activation_sha256": evidence["daily_activation"]["sha256"],
            "reference_daily_sessions_reused": int(
                daily_reuse["reference_daily_sessions_reused"]
            ),
            "reference_daily_sessions_requested": int(
                daily_reuse[
                    "reference_daily_sessions_requested_this_invocation"
                ]
            ),
        },
        {
            "ordinal": 3,
            "phase": "future_quarterly_quality",
            "status": "accepted_same_session_context",
            "through_report_date": latest_completed_quarter_end(
                config.session
            ).isoformat(),
            "data_sha256": evidence["future_quarterly_quality"]["sha256"],
            "manifest_sha256": evidence[
                "future_quarterly_quality_manifest"
            ]["sha256"],
        },
        {
            "ordinal": 4,
            "phase": "candidate49_source_to_signal",
            "status": outcome,
            "raw_manifest_sha256": summary["raw_manifest_sha256"],
            "factor_manifest_sha256": summary["factor_manifest_sha256"],
            "eligible_names": int(summary["eligible_names"]),
            "signal_entry_sha256": summary["signal_entry_sha256"],
            "raw_provider_calls_total": int(summary["raw_provider_calls"]),
        },
    ]


def _final_record_path(config: WorkflowConfig) -> Path:
    return (
        config.minute_data_root
        / "metadata"
        / "rich_data"
        / "candidate49_future_workflows"
        / f"{config.session.isoformat()}.json"
    )


def _require_real_directory(path: Path, *, label: str) -> os.stat_result:
    try:
        identity = path.lstat()
    except OSError as exc:
        raise Candidate49FutureSessionWorkflowError(
            f"{label} identity is unavailable"
        ) from exc
    _require(
        stat.S_ISDIR(identity.st_mode) and not stat.S_ISLNK(identity.st_mode),
        f"{label} identity changed",
    )
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise Candidate49FutureSessionWorkflowError(
            f"{label} identity is unavailable"
        ) from exc
    _require(
        resolved == path,
        f"{label} identity changed",
    )
    return identity


def _require_existing_real_directory_chain(path: Path, *, label: str) -> None:
    current = path
    while True:
        try:
            current.lstat()
        except FileNotFoundError:
            parent = current.parent
            _require(
                parent != current,
                f"{label} identity is unavailable",
            )
            current = parent
            continue
        except OSError as exc:
            raise Candidate49FutureSessionWorkflowError(
                f"{label} identity is unavailable"
            ) from exc
        _require_real_directory(current, label=label)
        return


def _ensure_real_directory_tree(path: Path, *, label: str) -> None:
    missing: list[Path] = []
    current = path
    while True:
        try:
            current.lstat()
        except FileNotFoundError:
            missing.append(current)
            parent = current.parent
            _require(
                parent != current,
                f"{label} identity is unavailable",
            )
            current = parent
            continue
        except OSError as exc:
            raise Candidate49FutureSessionWorkflowError(
                f"{label} identity is unavailable"
            ) from exc
        _require_real_directory(current, label=label)
        break
    for directory in reversed(missing):
        try:
            directory.mkdir()
        except FileExistsError:
            pass
        except OSError as exc:
            raise Candidate49FutureSessionWorkflowError(
                f"{label} could not be created"
            ) from exc
        _require_real_directory(directory, label=label)


def _require_unique_regular_file(
    path: Path,
    *,
    label: str,
) -> os.stat_result:
    try:
        identity = path.lstat()
    except OSError as exc:
        raise Candidate49FutureSessionWorkflowError(
            f"{label} identity is unavailable"
        ) from exc
    _require(
        stat.S_ISREG(identity.st_mode) and not stat.S_ISLNK(identity.st_mode),
        f"{label} identity changed",
    )
    _require(
        identity.st_nlink == 1,
        f"{label} identity changed",
    )
    _require_real_directory(path.parent, label=f"{label} parent directory")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise Candidate49FutureSessionWorkflowError(
            f"{label} identity is unavailable"
        ) from exc
    _require(
        resolved == path,
        f"{label} identity changed",
    )
    return identity


def _read_unique_regular_json(
    path: Path,
    *,
    label: str,
) -> tuple[dict[str, Any], str]:
    expected_identity = _require_unique_regular_file(path, label=label)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise Candidate49FutureSessionWorkflowError(
            f"{label} identity changed during read"
        ) from exc
    chunks: list[bytes] = []
    digest = hashlib.sha256()
    try:
        try:
            opened_identity = os.fstat(descriptor)
        except OSError as exc:
            raise Candidate49FutureSessionWorkflowError(
                f"{label} identity changed during read"
            ) from exc
        _require(
            stat.S_ISREG(opened_identity.st_mode)
            and opened_identity.st_nlink == 1
            and opened_identity.st_dev == expected_identity.st_dev
            and opened_identity.st_ino == expected_identity.st_ino,
            f"{label} identity changed during read",
        )
        try:
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
                digest.update(chunk)
            finished_identity = os.fstat(descriptor)
        except OSError as exc:
            raise Candidate49FutureSessionWorkflowError(
                f"required JSON is unreadable: {path}"
            ) from exc
        _require(
            stat.S_ISREG(finished_identity.st_mode)
            and finished_identity.st_nlink == 1
            and finished_identity.st_dev == opened_identity.st_dev
            and finished_identity.st_ino == opened_identity.st_ino
            and finished_identity.st_size == opened_identity.st_size
            and finished_identity.st_mtime_ns == opened_identity.st_mtime_ns
            and finished_identity.st_ctime_ns == opened_identity.st_ctime_ns,
            f"{label} identity changed during read",
        )
    finally:
        os.close(descriptor)
    try:
        value = json.loads(b"".join(chunks).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Candidate49FutureSessionWorkflowError(
            f"required JSON is unreadable: {path}"
        ) from exc
    if not isinstance(value, dict):
        raise Candidate49FutureSessionWorkflowError(
            f"required JSON is not an object: {path}"
        )
    final_identity = _require_unique_regular_file(path, label=label)
    _require(
        final_identity.st_dev == opened_identity.st_dev
        and final_identity.st_ino == opened_identity.st_ino
        and final_identity.st_size == opened_identity.st_size
        and final_identity.st_mtime_ns == opened_identity.st_mtime_ns
        and final_identity.st_ctime_ns == opened_identity.st_ctime_ns,
        f"{label} identity changed during read",
    )
    return value, digest.hexdigest()


def validate_existing_final_record(
    config: WorkflowConfig,
    *,
    reference_manifest_path: Path = DAILY_REFERENCE_MANIFEST_PATH,
    reference_manifest_sha256: str = DAILY_REFERENCE_MANIFEST_SHA256,
) -> tuple[Path, dict[str, Any], str] | None:
    path = _final_record_path(config)
    _require_existing_real_directory_chain(
        path.parent,
        label="Candidate49 workflow record parent directory",
    )
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise Candidate49FutureSessionWorkflowError(
            "Candidate49 workflow record file identity is unavailable"
        ) from exc
    record, record_sha256 = _read_unique_regular_json(
        path,
        label="Candidate49 workflow record file",
    )
    expected_keys = {
        "version",
        "kind",
        "status",
        "protocol_path",
        "protocol_sha256",
        "authoritative_state_path",
        "authoritative_state_sha256",
        "session_date",
        "daily_staging_root_requested",
        "active_data_root",
        "minute_data_root",
        "daily_provider",
        "daily_calendar_cutoff",
        "daily_reference_reuse",
        "future_quarterly_quality_through_report_date",
        "candidate49_outcome",
        "candidate49_eligible_names",
        "candidate49_signal_entry_sha256",
        "candidate49_raw_provider_calls_total",
        "static_evidence",
        "phase_receipts",
        "evidence",
        "ledger_observations",
        "credential_value_logged_hashed_or_persisted",
        "historical_candidate49_return_diagnostic_run",
        "forward_return_fields_read",
        "paper_execution_or_order_performed",
        "aggregation_scoring_selection_or_sizing_performed",
        "candidate50_activated",
        "Level2_intake_performed_or_justified",
    }
    _require(
        set(record) == expected_keys
        and record.get("version") == 1
        and record.get("kind") == FINAL_RECORD_KIND
        and record.get("status") == FINAL_RECORD_STATUS
        and record.get("protocol_path")
        == str(PROTOCOL_PATH.relative_to(REPO_ROOT))
        and record.get("protocol_sha256") == PROTOCOL_SHA256
        and record.get("authoritative_state_path")
        == str(AUTHORITATIVE_STATE_PATH.relative_to(REPO_ROOT))
        and record.get("authoritative_state_sha256") == AUTHORITATIVE_STATE_SHA256
        and record.get("session_date") == config.session.isoformat()
        and Path(
            str(record.get("daily_staging_root_requested", ""))
        ).resolve()
        == config.staging_root
        and Path(str(record.get("minute_data_root", ""))).resolve()
        == config.minute_data_root
        and record.get("daily_provider") == "tushare"
        and record.get("daily_calendar_cutoff")
        == config.session.isoformat()
        and record.get("future_quarterly_quality_through_report_date")
        == latest_completed_quarter_end(config.session).isoformat(),
        "existing Candidate49 workflow record header changed",
    )
    _require(
        record.get("credential_value_logged_hashed_or_persisted") is False
        and record.get("forward_return_fields_read") is False
        and record.get("historical_candidate49_return_diagnostic_run") is False
        and record.get("paper_execution_or_order_performed") is False
        and record.get(
            "aggregation_scoring_selection_or_sizing_performed"
        )
        is False
        and record.get("candidate50_activated") is False
        and record.get("Level2_intake_performed_or_justified") is False,
        "existing Candidate49 workflow research boundary changed",
    )
    static_evidence = validate_static_evidence()
    _require(
        record.get("static_evidence") == static_evidence,
        "existing workflow static evidence changed",
    )
    summary = _candidate49_artifact_summary(config)
    active_root = Path(str(summary["active_data_root"])).resolve()
    _require(
        Path(str(record.get("active_data_root", ""))).resolve()
        == active_root,
        "existing workflow active data root changed",
    )
    activation_path = (
        active_root / "metadata" / "tushare_daily_activation.json"
    )
    activation = _read_json(activation_path)
    _require(
        activation.get("status") == "active_via_atomic_repository_pointer"
        and activation.get("protocol_sha256")
        == DAILY_MIGRATION_PROTOCOL_SHA256
        and Path(str(activation.get("staging_root", ""))).resolve()
        == active_root,
        "existing workflow daily activation changed",
    )
    daily_reuse = _load_daily_reference_reuse_evidence(
        active_root=active_root,
        activation_path=activation_path,
        session=config.session,
        reference_manifest_path=reference_manifest_path,
        reference_manifest_sha256=reference_manifest_sha256,
    )
    expected_daily_reuse = {
        "accepted_reference_range": list(
            daily_reuse["accepted_reference_range"]
        ),
        "accepted_reference_rows": int(
            daily_reuse["accepted_reference_rows"]
        ),
        "reference_daily_sessions_reused": int(
            daily_reuse["reference_daily_sessions_reused"]
        ),
        "reference_daily_sessions_requested_this_invocation": int(
            daily_reuse[
                "reference_daily_sessions_requested_this_invocation"
            ]
        ),
        "requested_daily_sessions_this_invocation": int(
            daily_reuse["requested_daily_sessions_this_invocation"]
        ),
        "requested_daily_basic_sessions_this_invocation": int(
            daily_reuse[
                "requested_daily_basic_sessions_this_invocation"
            ]
        ),
        "daily_provider_calls_this_invocation": int(
            daily_reuse["daily_provider_calls_this_invocation"]
        ),
    }
    _require(
        record.get("daily_reference_reuse") == expected_daily_reuse,
        "existing workflow historical daily reuse evidence changed",
    )
    quality_path, quality_manifest_path = _quality_paths(active_root)
    expected_evidence = {
        "accepted_tushare_daily_reference": dict(
            daily_reuse["accepted_reference_link"]
        ),
        "daily_source_manifest": dict(daily_reuse["source_manifest_link"]),
        "daily_acceptance": dict(daily_reuse["acceptance_link"]),
        "daily_activation": _validate_link(
            activation_path,
            file_digest(activation_path),
        ),
        "future_quarterly_quality": _validate_link(
            quality_path,
            file_digest(quality_path),
        ),
        "future_quarterly_quality_manifest": _validate_link(
            quality_manifest_path,
            file_digest(quality_manifest_path),
        ),
        "candidate49_raw_manifest": _validate_link(
            Path(str(summary["raw_manifest_path"])),
            str(summary["raw_manifest_sha256"]),
        ),
        "candidate49_factor_manifest": _validate_link(
            Path(str(summary["factor_manifest_path"])),
            str(summary["factor_manifest_sha256"]),
        ),
    }
    _require(
        record.get("evidence") == expected_evidence,
        "existing workflow evidence changed",
    )
    _validate_candidate49_ledgers_semantically()
    observations = record.get("ledger_observations")
    _require(
        isinstance(observations, dict)
        and set(observations) == {"signal", "execution"},
        "existing workflow ledger observations changed",
    )
    import a_share_tushare_intraday_cumulative_vwap_crossing_rate as candidate

    _validate_ledger_observation(
        observations["signal"],
        path=SIGNAL_LEDGER_PATH,
        kind=candidate.FUTURE_SIGNAL_LEDGER_KIND,
    )
    _validate_ledger_observation(
        observations["execution"],
        path=EXECUTION_LEDGER_PATH,
        kind=candidate.FUTURE_EXECUTION_LEDGER_KIND,
    )
    outcome = _candidate49_outcome(summary)
    _require(
        record.get("candidate49_outcome") == outcome,
        "existing workflow Candidate49 outcome changed",
    )
    provider_calls = record.get("candidate49_raw_provider_calls_total")
    _require(
        record.get("candidate49_eligible_names")
        == summary["eligible_names"]
        and record.get("candidate49_signal_entry_sha256")
        == summary["signal_entry_sha256"],
        "existing workflow Candidate49 summary changed",
    )
    _require(
        isinstance(provider_calls, int)
        and not isinstance(provider_calls, bool)
        and provider_calls == int(summary["raw_provider_calls"]),
        "existing workflow Candidate49 provider-call evidence changed",
    )
    receipts = _phase_receipts(
        config=config,
        active_root=active_root,
        daily_reuse=daily_reuse,
        evidence=expected_evidence,
        summary=summary,
    )
    _require(
        record.get("phase_receipts") == receipts,
        "existing workflow phase receipts changed",
    )
    return path, record, record_sha256


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    _ensure_real_directory_tree(
        path.parent,
        label="Candidate49 workflow record parent directory",
    )
    initial_identity: os.stat_result | None
    try:
        path.lstat()
    except FileNotFoundError:
        initial_identity = None
    except OSError as exc:
        raise Candidate49FutureSessionWorkflowError(
            "Candidate49 workflow record file identity is unavailable"
        ) from exc
    else:
        initial_identity = _require_unique_regular_file(
            path,
            label="Candidate49 workflow record file",
        )
    temporary = path.with_name(f".{path.name}.{os.getpid()}.partial")
    data = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _require_real_directory(
            path.parent,
            label="Candidate49 workflow record parent directory",
        )
        try:
            current_identity = path.lstat()
        except FileNotFoundError:
            current_identity = None
        except OSError as exc:
            raise Candidate49FutureSessionWorkflowError(
                "Candidate49 workflow record file identity is unavailable"
            ) from exc
        if initial_identity is None:
            _require(
                current_identity is None,
                "Candidate49 workflow record appeared concurrently",
            )
        else:
            _require(
                current_identity is not None
                and current_identity.st_dev == initial_identity.st_dev
                and current_identity.st_ino == initial_identity.st_ino,
                "Candidate49 workflow record file identity changed concurrently",
            )
            _require_unique_regular_file(
                path,
                label="Candidate49 workflow record file",
            )
        os.replace(temporary, path)
        directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        directory_fd = os.open(path.parent, directory_flags)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        _require_unique_regular_file(
            path,
            label="Candidate49 workflow record file",
        )
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def _process_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Candidate49FutureSessionWorkflowError(
                "another Candidate49 future-session workflow holds the lock"
            ) from exc
        handle.seek(0)
        handle.truncate()
        handle.write(f"{os.getpid()}\n")
        handle.flush()
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _migration_source_ready(
    migration: Mapping[str, Any],
    session: dt.date,
) -> bool:
    source = migration.get("source_snapshot")
    if not isinstance(source, dict):
        return False
    _require(
        source.get("through_date") == session.isoformat(),
        "completed daily source snapshot cutoff differs from signal session",
    )
    return True


def _migration_acceptance_ready(
    migration: Mapping[str, Any],
    session: dt.date,
) -> bool:
    acceptance = migration.get("acceptance")
    if not isinstance(acceptance, dict):
        return False
    _require(
        acceptance.get("status")
        == "accepted_staging_pending_explicit_crash_safe_activation"
        and acceptance.get("through_date") == session.isoformat()
        and acceptance.get("daily_source") == "tushare"
        and acceptance.get("protocol_sha256") == DAILY_MIGRATION_PROTOCOL_SHA256,
        "daily staging acceptance changed",
    )
    return True


def _stock_basic_failure_blocks_session(
    migration: Mapping[str, Any],
    session: dt.date,
) -> bool:
    failure = migration.get("latest_failure")
    if not isinstance(failure, dict):
        return False
    return (
        failure.get("through_date") == session.isoformat()
        and failure.get("failure_stage") == "stock_basic"
        and failure.get("status")
        == "failed_preserving_active_root_and_completed_checkpoints"
    )


def _prepare_daily_root(
    *,
    config: WorkflowConfig,
    token: str,
    reference_manifest_path: Path,
    reference_manifest_sha256: str,
    executor: CommandExecutor,
    steps: list[dict[str, Any]],
) -> tuple[Path, Path]:
    reference_manifest_path = reference_manifest_path.expanduser().resolve()
    active = _pipeline_status(executor=executor, steps=steps)
    active_source = _active_daily_source(active)
    active_root = Path(str(active["data_root"])).expanduser().resolve()
    active_calendar_end = _calendar_end(active)
    if (
        active_source == "tushare"
        and active_calendar_end == config.session
        and active.get("price_basis", {}).get("status") == "passed"
    ):
        return _load_accepted_active_root(
            status=active,
            session=config.session,
        )
    _require(
        active_calendar_end < config.session,
        "active daily calendar is later than the requested future session",
    )
    _require(
        active_root != config.staging_root,
        "active staging root does not contain the required signal-session cutoff",
    )

    migration = _migration_status(
        staging_root=config.staging_root,
        reference_manifest_path=reference_manifest_path,
        reference_manifest_sha256=reference_manifest_sha256,
        executor=executor,
        steps=steps,
    )
    _require(
        not _stock_basic_failure_blocks_session(migration, config.session),
        "daily migration stock_basic failed for this signal session; "
        "provider continuation is forbidden",
    )
    source_ready = _migration_source_ready(migration, config.session)
    if active_source == "tushare":
        if not source_ready:
            if migration.get("refresh_seed") is None:
                seed, _ = _run_json(
                    name="daily-seed-refresh",
                    argv=[
                        PYTHON,
                        str(MIGRATION_SCRIPT),
                        "seed-refresh",
                        "--parent-root",
                        str(active_root),
                        "--staging-root",
                        str(config.staging_root),
                        "--through-date",
                        config.session.isoformat(),
                        "--reference-manifest",
                        str(reference_manifest_path),
                    ],
                    environment=_child_environment(),
                    executor=executor,
                    steps=steps,
                )
                _require(
                    seed.get("status")
                    == "source_checkpoints_seeded_pending_incremental_sync"
                    and seed.get("provider_request_issued") is False
                    and seed.get("hardlinks_used") is False
                    and seed.get("active_root_mutated") is False,
                    "daily refresh seed crossed its frozen boundary",
                )
                migration = _migration_status(
                    staging_root=config.staging_root,
                    reference_manifest_path=reference_manifest_path,
                    reference_manifest_sha256=reference_manifest_sha256,
                    executor=executor,
                    steps=steps,
                )
            _require(
                isinstance(migration.get("refresh_seed"), dict),
                "accepted Tushare parent requires a completed refresh seed",
            )
        else:
            _require(
                isinstance(migration.get("refresh_seed"), dict),
                "completed incremental source snapshot lacks its refresh seed",
            )
    else:
        _require(
            migration.get("refresh_seed") is None
            and migration.get("refresh_seed_intent") is None,
            "the first BaoStock-to-Tushare migration must not use refresh seed",
        )

    if not source_ready:
        preflight, _ = _run_json(
            name="daily-migration-preflight",
            argv=[
                PYTHON,
                str(MIGRATION_SCRIPT),
                "preflight",
                "--staging-root",
                str(config.staging_root),
                "--through-date",
                config.session.isoformat(),
                "--reference-manifest",
                str(reference_manifest_path),
            ],
            environment=_child_environment(token),
            executor=executor,
            token=token,
            steps=steps,
        )
        _require(
            preflight.get("ready") is True
            and preflight.get("recommended_cli_exit_code") == 0
            and preflight.get("status")
            == "ready_for_explicit_tushare_source_sync"
            and preflight.get("provider_request_issued") is False
            and preflight.get("filesystem_write_performed") is False,
            "daily migration preflight did not return the frozen ready state",
        )
        synced, _ = _run_json(
            name="daily-source-sync",
            argv=[
                PYTHON,
                str(MIGRATION_SCRIPT),
                "sync-source",
                "--staging-root",
                str(config.staging_root),
                "--through-date",
                config.session.isoformat(),
                "--reference-manifest",
                str(reference_manifest_path),
                "--allow-network",
            ],
            environment=_child_environment(token),
            executor=executor,
            token=token,
            steps=steps,
        )
        _require(
            synced.get("status") == "source_snapshot_complete"
            and synced.get("active_root_mutated") is False,
            "daily source sync did not publish its immutable source manifest",
        )
        migration = _migration_status(
            staging_root=config.staging_root,
            reference_manifest_path=reference_manifest_path,
            reference_manifest_sha256=reference_manifest_sha256,
            executor=executor,
            steps=steps,
        )
        _require(
            _migration_source_ready(migration, config.session),
            "daily source snapshot is incomplete after sync",
        )

    if not _migration_acceptance_ready(migration, config.session):
        built, _ = _run_json(
            name="daily-build-and-accept",
            argv=[
                PYTHON,
                str(MIGRATION_SCRIPT),
                "build",
                "--staging-root",
                str(config.staging_root),
                "--reference-manifest",
                str(reference_manifest_path),
            ],
            environment=_child_environment(),
            executor=executor,
            steps=steps,
        )
        _require(
            built.get("status")
            == "accepted_staging_pending_explicit_crash_safe_activation"
            and built.get("active_root_mutated") is False,
            "daily build did not reach accepted staging state",
        )
        migration = _migration_status(
            staging_root=config.staging_root,
            reference_manifest_path=reference_manifest_path,
            reference_manifest_sha256=reference_manifest_sha256,
            executor=executor,
            steps=steps,
        )
        _require(
            _migration_acceptance_ready(migration, config.session),
            "daily staging acceptance is incomplete after build",
        )

    activation_preflight, _ = _run_json(
        name="daily-activation-preflight",
        argv=[
            PYTHON,
            str(MIGRATION_SCRIPT),
            "activation-preflight",
            "--staging-root",
            str(config.staging_root),
        ],
        environment=_child_environment(),
        executor=executor,
        steps=steps,
    )
    _require(
        activation_preflight.get("ready") is True
        and activation_preflight.get("recommended_cli_exit_code") == 0
        and activation_preflight.get("accepted_through_date")
        == config.session.isoformat()
        and activation_preflight.get("environment_override_present") is False
        and activation_preflight.get("provider_request_issued") is False,
        "daily activation preflight did not return the frozen ready state",
    )
    activated, _ = _run_json(
        name="daily-atomic-activation",
        argv=[
            PYTHON,
            str(MIGRATION_SCRIPT),
            "activate",
            "--staging-root",
            str(config.staging_root),
            "--confirm-activation",
        ],
        environment=_child_environment(),
        executor=executor,
        steps=steps,
    )
    _require(
        activated.get("status") == "active_via_atomic_repository_pointer"
        and Path(str(activated.get("active_data_root", ""))).resolve()
        == config.staging_root
        and activated.get("old_daily_or_qlib_file_mutated") is False,
        "daily activation did not point to the accepted staging root",
    )
    active = _pipeline_status(
        executor=executor,
        steps=steps,
        name="post-activation-daily-status",
    )
    return _load_accepted_active_root(
        status=active,
        session=config.session,
    )


def _validate_price_basis(
    *,
    executor: CommandExecutor,
    steps: list[dict[str, Any]],
) -> None:
    audit, _ = _run_json(
        name="post-activation-price-basis-audit",
        argv=[PYTHON, str(PIPELINE_SCRIPT), "price-basis-audit"],
        environment=_child_environment(),
        executor=executor,
        steps=steps,
    )
    _require(
        audit.get("status") == "passed"
        and audit.get("daily_sources") == ["tushare"]
        and not audit.get("failures"),
        "post-activation price-basis audit did not pass as one Tushare source",
    )


def _quality_paths(active_root: Path) -> tuple[Path, Path]:
    return (
        active_root
        / "raw"
        / "a_share"
        / "fundamentals"
        / "quarterly_quality_future.parquet",
        active_root / "metadata" / "quarterly_quality_future_manifest.json",
    )


def _prepare_quality_and_final_preflight(
    *,
    config: WorkflowConfig,
    active_root: Path,
    token: str,
    executor: CommandExecutor,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_argv = _candidate_argv(
        config=config,
        active_root=active_root,
        preflight_only=True,
    )
    probe, returncode = _run_json(
        name="candidate49-quality-readiness-probe",
        argv=candidate_argv,
        environment=_child_environment(token),
        executor=executor,
        token=token,
        allowed_returncodes={0, 2},
        steps=steps,
    )
    if returncode == 0:
        _validate_candidate_preflight(probe)
        return probe

    failures = probe.get("failures")
    _require(
        failures == ["future_quarterly_quality_not_accepted"]
        and probe.get("future_quarterly_quality_ready") is False
        and probe.get("provider_request_issued") is False
        and probe.get("filesystem_write_performed") is False,
        "Candidate49 has a non-quality blocker; stop before quality network access",
    )
    quality_path, quality_manifest = _quality_paths(active_root)
    through = latest_completed_quarter_end(config.session)
    quality, _ = _run_json(
        name="future-quarterly-quality-refresh",
        argv=[
            PYTHON,
            str(RESEARCH_SCRIPT),
            "sync-quarterly-fundamentals",
            "--start-year",
            "2019",
            "--end-year",
            str(config.session.year),
            "--through-report-date",
            through.isoformat(),
            "--output",
            str(quality_path),
            "--manifest",
            str(quality_manifest),
        ],
        environment=_child_environment(),
        executor=executor,
        steps=steps,
    )
    _require(
        quality.get("status") == "completed"
        and quality.get("report_frequency") == "quarterly"
        and quality.get("through_report_date") == through.isoformat()
        and quality.get("latest_completed_quarter_end_at_sync")
        == through.isoformat()
        and Path(str(quality.get("output", ""))).resolve() == quality_path,
        "future quarterly-quality refresh changed its frozen boundary",
    )
    preflight, _ = _run_json(
        name="candidate49-final-combined-preflight",
        argv=candidate_argv,
        environment=_child_environment(token),
        executor=executor,
        token=token,
        steps=steps,
    )
    _validate_candidate_preflight(preflight)
    return preflight


def _collect_candidate49(
    *,
    config: WorkflowConfig,
    active_root: Path,
    token: str,
    executor: CommandExecutor,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    collected, _ = _run_json(
        name="candidate49-source-to-signal-collection",
        argv=_candidate_argv(
            config=config,
            active_root=active_root,
            preflight_only=False,
        ),
        environment=_child_environment(token),
        executor=executor,
        token=token,
        steps=steps,
    )
    _require(
        collected.get("status")
        in {
            "future_signal_appended",
            "future_signal_already_present_idempotent",
            "future_session_frozen_without_signal_fewer_than_50_names",
        }
        and collected.get("session_date") == config.session.isoformat()
        and collected.get("forward_return_fields_read") is False
        and collected.get("execution_or_order_performed") is False
        and collected.get("historical_backfill_allowed") is False,
        "Candidate49 source-to-signal result changed its frozen boundary",
    )
    _validate_link(
        Path(str(collected["raw_manifest"])),
        str(collected["raw_manifest_sha256"]),
    )
    _validate_link(
        Path(str(collected["factor_manifest"])),
        str(collected["factor_manifest_sha256"]),
    )
    return collected


def _build_final_record(
    *,
    config: WorkflowConfig,
    static_evidence: Mapping[str, str],
    active_root: Path,
    activation_path: Path,
    daily_reuse: Mapping[str, Any],
    preflight: Mapping[str, Any],
    collected: Mapping[str, Any],
) -> dict[str, Any]:
    quality_path, quality_manifest = _quality_paths(active_root)
    summary = _candidate49_artifact_summary(config)
    _require(
        Path(str(summary["active_data_root"])).resolve() == active_root
        and Path(str(collected["raw_manifest"])).resolve()
        == Path(str(summary["raw_manifest_path"])).resolve()
        and collected["raw_manifest_sha256"]
        == summary["raw_manifest_sha256"]
        and Path(str(collected["factor_manifest"])).resolve()
        == Path(str(summary["factor_manifest_path"])).resolve()
        and collected["factor_manifest_sha256"]
        == summary["factor_manifest_sha256"]
        and int(collected["eligible_names"]) == summary["eligible_names"]
        and collected.get("signal_entry_sha256")
        == summary["signal_entry_sha256"],
        "Candidate49 source-to-signal result differs from published artifacts",
    )
    outcome = _validate_candidate49_child_status(
        status=collected.get("status"),
        summary=summary,
    )
    candidate_provider_calls_this_invocation = int(
        collected["provider_calls_this_invocation"]
    )
    _require(
        0
        <= candidate_provider_calls_this_invocation
        <= int(summary["raw_provider_calls"]),
        "Candidate49 source-to-signal provider-call count changed",
    )
    _validate_candidate49_ledgers_semantically()
    evidence = {
        "accepted_tushare_daily_reference": dict(
            daily_reuse["accepted_reference_link"]
        ),
        "daily_source_manifest": dict(daily_reuse["source_manifest_link"]),
        "daily_acceptance": dict(daily_reuse["acceptance_link"]),
        "daily_activation": _validate_link(
            activation_path,
            file_digest(activation_path),
        ),
        "future_quarterly_quality": _validate_link(
            quality_path,
            str(preflight["future_quarterly_quality_sha256"]),
        ),
        "future_quarterly_quality_manifest": _validate_link(
            quality_manifest,
            str(preflight["future_quarterly_quality_manifest_sha256"]),
        ),
        "candidate49_raw_manifest": _validate_link(
            Path(str(collected["raw_manifest"])),
            str(collected["raw_manifest_sha256"]),
        ),
        "candidate49_factor_manifest": _validate_link(
            Path(str(collected["factor_manifest"])),
            str(collected["factor_manifest_sha256"]),
        ),
    }
    import a_share_tushare_intraday_cumulative_vwap_crossing_rate as candidate

    ledger_observations = {
        "signal": _ledger_observation(
            SIGNAL_LEDGER_PATH,
            candidate.FUTURE_SIGNAL_LEDGER_KIND,
        ),
        "execution": _ledger_observation(
            EXECUTION_LEDGER_PATH,
            candidate.FUTURE_EXECUTION_LEDGER_KIND,
        ),
    }
    phase_receipts = _phase_receipts(
        config=config,
        active_root=active_root,
        daily_reuse=daily_reuse,
        evidence=evidence,
        summary=summary,
    )
    return {
        "version": 1,
        "kind": FINAL_RECORD_KIND,
        "status": FINAL_RECORD_STATUS,
        "protocol_path": str(PROTOCOL_PATH.relative_to(REPO_ROOT)),
        "protocol_sha256": PROTOCOL_SHA256,
        "authoritative_state_path": str(
            AUTHORITATIVE_STATE_PATH.relative_to(REPO_ROOT)
        ),
        "authoritative_state_sha256": AUTHORITATIVE_STATE_SHA256,
        "session_date": config.session.isoformat(),
        "daily_staging_root_requested": str(config.staging_root),
        "active_data_root": str(active_root),
        "minute_data_root": str(config.minute_data_root),
        "daily_provider": "tushare",
        "daily_calendar_cutoff": config.session.isoformat(),
        "daily_reference_reuse": {
            "accepted_reference_range": list(
                daily_reuse["accepted_reference_range"]
            ),
            "accepted_reference_rows": int(
                daily_reuse["accepted_reference_rows"]
            ),
            "reference_daily_sessions_reused": int(
                daily_reuse["reference_daily_sessions_reused"]
            ),
            "reference_daily_sessions_requested_this_invocation": int(
                daily_reuse[
                    "reference_daily_sessions_requested_this_invocation"
                ]
            ),
            "requested_daily_sessions_this_invocation": int(
                daily_reuse["requested_daily_sessions_this_invocation"]
            ),
            "requested_daily_basic_sessions_this_invocation": int(
                daily_reuse[
                    "requested_daily_basic_sessions_this_invocation"
                ]
            ),
            "daily_provider_calls_this_invocation": int(
                daily_reuse["daily_provider_calls_this_invocation"]
            ),
        },
        "future_quarterly_quality_through_report_date": (
            latest_completed_quarter_end(config.session).isoformat()
        ),
        "candidate49_outcome": outcome,
        "candidate49_eligible_names": int(summary["eligible_names"]),
        "candidate49_signal_entry_sha256": summary["signal_entry_sha256"],
        "candidate49_raw_provider_calls_total": int(
            summary["raw_provider_calls"]
        ),
        "static_evidence": dict(static_evidence),
        "phase_receipts": phase_receipts,
        "evidence": evidence,
        "ledger_observations": ledger_observations,
        "credential_value_logged_hashed_or_persisted": False,
        "historical_candidate49_return_diagnostic_run": False,
        "forward_return_fields_read": False,
        "paper_execution_or_order_performed": False,
        "aggregation_scoring_selection_or_sizing_performed": False,
        "candidate50_activated": False,
        "Level2_intake_performed_or_justified": False,
    }


def inspect_plan(
    config: WorkflowConfig,
    *,
    executor: CommandExecutor = _default_executor,
    token_loader: TokenLoader = _load_token,
    now: dt.datetime | None = None,
    reference_manifest_path: Path = DAILY_REFERENCE_MANIFEST_PATH,
    reference_manifest_sha256: str = DAILY_REFERENCE_MANIFEST_SHA256,
) -> dict[str, Any]:
    static_evidence = validate_static_evidence()
    config = normalize_config(config)
    existing = validate_existing_final_record(
        config,
        reference_manifest_path=reference_manifest_path,
        reference_manifest_sha256=reference_manifest_sha256,
    )
    local_now = now or dt.datetime.now(CHINA_TZ)
    if existing is not None:
        path, _, record_sha256 = existing
        return {
            "status": "completed_workflow_record_validated_no_provider_request",
            "session_date": config.session.isoformat(),
            "record_path": str(path),
            "record_sha256": record_sha256,
            "provider_request_issued": False,
            "filesystem_write_performed": False,
        }
    active = _pipeline_status(executor=executor)
    migration = _migration_status(
        staging_root=config.staging_root,
        reference_manifest_path=reference_manifest_path,
        reference_manifest_sha256=reference_manifest_sha256,
        executor=executor,
    )
    reference = migration["reference_snapshot"]
    token = token_loader()
    token_present = bool(token)
    token = None
    time_failures = _time_failures(config.session, local_now)
    active_source = _active_daily_source(active)
    active_calendar_end = _calendar_end(active)
    if active_source == "tushare" and active_calendar_end == config.session:
        next_phase = "validate_active_daily_then_prepare_future_quality"
    elif migration.get("source_snapshot") is not None:
        next_phase = "resume_daily_build_or_activation"
    elif active_source == "tushare":
        next_phase = "seed_refresh_then_incremental_daily_sync"
    else:
        next_phase = "initial_tushare_daily_migration_from_baostock"
    failures = list(time_failures)
    if not token_present:
        failures.append("TUSHARE_TOKEN_not_available_to_workflow")
    if _stock_basic_failure_blocks_session(migration, config.session):
        failures.append(
            "daily_migration_stock_basic_failure_for_session_forbids_provider_retry"
        )
    return {
        "version": 1,
        "kind": "a_share_tushare_candidate49_future_session_workflow_plan",
        "status": "ready_for_explicit_run" if not failures else "not_ready_no_write",
        "ready": not failures,
        "recommended_cli_exit_code": 0 if not failures else 2,
        "session_date": config.session.isoformat(),
        "staging_root": str(config.staging_root),
        "minute_data_root": str(config.minute_data_root),
        "active_data_root": str(active["data_root"]),
        "active_daily_source": active_source,
        "active_calendar_end": active_calendar_end.isoformat(),
        "existing_tushare_daily_reference": {
            "path": reference["path"],
            "sha256": reference["sha256"],
            "requested_start": reference["requested_start"],
            "requested_end": reference["requested_end"],
            "rows": reference["rows"],
            "annual_partitions": reference["annual_partitions"],
            "sessions": reference["sessions"],
            "valid": True,
            "covered_daily_sessions_will_be_requested_again": False,
        },
        "staging_source_snapshot_present": isinstance(
            migration.get("source_snapshot"),
            dict,
        ),
        "staging_acceptance_present": isinstance(
            migration.get("acceptance"),
            dict,
        ),
        "token_present": token_present,
        "time_failures": time_failures,
        "failures": failures,
        "next_phase": next_phase,
        "static_evidence": static_evidence,
        "provider_request_issued": False,
        "filesystem_write_performed": False,
        "historical_candidate49_return_diagnostic_run": False,
        "forward_return_fields_read": False,
    }


def run_workflow(
    config: WorkflowConfig,
    *,
    confirm_run: bool,
    executor: CommandExecutor = _default_executor,
    token_loader: TokenLoader = _load_token,
    now: dt.datetime | None = None,
    lock_factory: LockFactory = _process_lock,
    reference_manifest_path: Path = DAILY_REFERENCE_MANIFEST_PATH,
    reference_manifest_sha256: str = DAILY_REFERENCE_MANIFEST_SHA256,
) -> dict[str, Any]:
    static_evidence = validate_static_evidence()
    config = normalize_config(config)
    existing = validate_existing_final_record(
        config,
        reference_manifest_path=reference_manifest_path,
        reference_manifest_sha256=reference_manifest_sha256,
    )
    if existing is not None:
        path, record, record_sha256 = existing
        return {
            "status": "completed_workflow_record_validated_no_provider_request",
            "session_date": config.session.isoformat(),
            "record_path": str(path),
            "record_sha256": record_sha256,
            "candidate49_outcome": record["candidate49_outcome"],
            "provider_request_issued": False,
            "filesystem_write_performed": False,
        }
    _require(
        confirm_run,
        "run requires explicit --confirm-run",
    )
    local_now = now or dt.datetime.now(CHINA_TZ)
    timing_failures = _time_failures(config.session, local_now)
    _require(
        not timing_failures,
        "Candidate49 workflow time boundary failed: " + ",".join(timing_failures),
    )
    token = token_loader()
    _require(
        bool(token),
        "TUSHARE_TOKEN is unavailable in the process environment, repository "
        ".env, and launchctl",
    )
    assert token is not None
    lock_path = (
        config.minute_data_root / ".candidate49_future_session_workflow.lock"
    )
    steps: list[dict[str, Any]] = []
    with lock_factory(lock_path):
        existing = validate_existing_final_record(
            config,
            reference_manifest_path=reference_manifest_path,
            reference_manifest_sha256=reference_manifest_sha256,
        )
        if existing is not None:
            path, record, record_sha256 = existing
            token = ""
            return {
                "status": "completed_workflow_record_validated_no_provider_request",
                "session_date": config.session.isoformat(),
                "record_path": str(path),
                "record_sha256": record_sha256,
                "candidate49_outcome": record["candidate49_outcome"],
                "provider_request_issued": False,
                "filesystem_write_performed": False,
            }
        active_root, activation_path = _prepare_daily_root(
            config=config,
            token=token,
            reference_manifest_path=reference_manifest_path,
            reference_manifest_sha256=reference_manifest_sha256,
            executor=executor,
            steps=steps,
        )
        daily_reuse = _load_daily_reference_reuse_evidence(
            active_root=active_root,
            activation_path=activation_path,
            session=config.session,
            reference_manifest_path=reference_manifest_path,
            reference_manifest_sha256=reference_manifest_sha256,
        )
        _validate_price_basis(executor=executor, steps=steps)
        resolved_text = _run_text(
            name="resolve-active-data-root",
            argv=[PYTHON, str(PIPELINE_SCRIPT), "data-root"],
            environment=_child_environment(),
            executor=executor,
            steps=steps,
        )
        resolved_root = Path(resolved_text).expanduser().resolve()
        _require(
            resolved_root == active_root,
            "fresh data-root resolution differs from activated Tushare root",
        )
        final_preflight = _prepare_quality_and_final_preflight(
            config=config,
            active_root=active_root,
            token=token,
            executor=executor,
            steps=steps,
        )
        collected = _collect_candidate49(
            config=config,
            active_root=active_root,
            token=token,
            executor=executor,
            steps=steps,
        )
        record = _build_final_record(
            config=config,
            static_evidence=static_evidence,
            active_root=active_root,
            activation_path=activation_path,
            daily_reuse=daily_reuse,
            preflight=final_preflight,
            collected=collected,
        )
        record_path = _final_record_path(config)
        _require(
            not record_path.exists(),
            "Candidate49 workflow record appeared concurrently",
        )
        _atomic_write_json(record_path, record)
        persisted_record, record_sha256 = _read_unique_regular_json(
            record_path,
            label="Candidate49 workflow record file",
        )
        _require(
            persisted_record == record,
            "Candidate49 workflow record changed after publication",
        )
    token = ""
    return {
        "status": FINAL_RECORD_STATUS,
        "session_date": config.session.isoformat(),
        "record_path": str(record_path),
        "record_sha256": record_sha256,
        "active_data_root": str(active_root),
        "candidate49_status": collected["status"],
        "candidate49_outcome": record["candidate49_outcome"],
        "candidate49_eligible_names": int(collected["eligible_names"]),
        "candidate49_signal_entry_sha256": collected.get("signal_entry_sha256"),
        "reference_daily_sessions_reused": int(
            daily_reuse["reference_daily_sessions_reused"]
        ),
        "reference_daily_sessions_requested_this_invocation": 0,
        "requested_daily_sessions_this_invocation": int(
            daily_reuse["requested_daily_sessions_this_invocation"]
        ),
        "requested_daily_basic_sessions_this_invocation": int(
            daily_reuse["requested_daily_basic_sessions_this_invocation"]
        ),
        "provider_calls_this_invocation": int(
            collected["provider_calls_this_invocation"]
        ),
        "forward_return_fields_read": False,
        "paper_execution_or_order_performed": False,
    }


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--session",
        type=dt.date.fromisoformat,
        required=True,
    )
    parser.add_argument(
        "--staging-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--minute-data-root",
        type=Path,
        required=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser(
        "plan",
        help="inspect the next phase without provider requests or writes",
    )
    _add_common_arguments(plan)
    run = subparsers.add_parser(
        "run",
        help="run every accepted daily/quality/minute phase and stop on first failure",
    )
    _add_common_arguments(run)
    run.add_argument(
        "--confirm-run",
        action="store_true",
        help="required acknowledgement for the bounded provider workflow",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = WorkflowConfig(
        session=args.session,
        staging_root=args.staging_root,
        minute_data_root=args.minute_data_root,
    )
    try:
        if args.command == "plan":
            result = inspect_plan(config)
        else:
            result = run_workflow(
                config,
                confirm_run=args.confirm_run,
            )
    except Candidate49FutureSessionWorkflowError as exc:
        print(
            json.dumps(
                {
                    "status": "failed_closed",
                    "error": str(exc),
                    "provider_continuation_allowed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.command == "plan":
        return int(result.get("recommended_cli_exit_code", 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
