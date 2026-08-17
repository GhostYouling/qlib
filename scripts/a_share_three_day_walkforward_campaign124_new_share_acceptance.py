#!/usr/bin/env python3
"""One-shot, fail-closed Campaign124 new-share source acceptance workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = Path(__file__).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign124_new_share as adapter,
)

WORKFLOW_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign124_new_share_acceptance.py"
)
AUTHORIZATION_POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v126_20260814.json"
)
DOTENV_PATH = REPO_ROOT / ".env"
DOTENV_MAX_BYTES = 64 * 1024
TOKEN_ENV = "TUSHARE_TOKEN"

BASELINE_BINDINGS = {
    "numeric_policy_v125": (
        "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v125_20260814.json",
        "641c64681b43649b9c20dbb266bbdacd578e4688f2dc9607756c964daacf1bda",
    ),
    "source_contract": (
        "docs/a_share_three_day_walkforward_campaign_124_new_share_source_contract_20260814.json",
        "6efcc73fac8f6a24335e869c82c83e15880ada55894569dec098b1eddf5836f1",
    ),
    "adapter": (
        "scripts/a_share_three_day_walkforward_campaign124_new_share.py",
        "32cb20464702061ea30d48e585018e3979152f8943acac17937d687541979224",
    ),
    "adapter_tests": (
        "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign124_new_share.py",
        "28d03dd0b0d12944d596e50dd7700ba216a96cda0e848a3ca221ded97566f001",
    ),
    "adapter_formula_freeze": (
        "docs/a_share_three_day_walkforward_campaign_124_new_share_adapter_formula_freeze_20260814.json",
        "defa631557c37fe794f81caffca4e1a09a6b481313fb52163298b3b2dad0f272",
    ),
    "attempt_ledger_v1": (
        "data/experiments/short_horizon/historical_walkforward/campaign_124/research_attempt_ledger_v1.json",
        "f2a4a84ef3758ba8bf926aef25343490ac282d4d78c2bf8dbe74e3b3ea4b8835",
    ),
    "holding_universe": (
        "data/qlib/cn_a_share/instruments/buyable_main_chinext.txt",
        "77ccf8de2ed1e447e73b5d5ff1703fc2a8656d6adab34ef44017481730249db1",
    ),
    "local_calendar": (
        "data/qlib/cn_a_share/calendars/day.txt",
        "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a",
    ),
}

REQUEST_YEARS = tuple(range(2019, 2026))
ACCEPTANCE_YEARS = tuple(range(2019, 2024))
REQUEST_FIELDS = adapter.SOURCE_FIELDS
MAXIMUM_PROVIDER_CALLS = len(REQUEST_YEARS)
SUSPECT_RESPONSE_ROW_LIMIT = 2000
MINIMUM_EVENTS_PER_ACCEPTANCE_YEAR = 20
MINIMUM_EVENTS_TOTAL_2019_2023 = 150

SNAPSHOT_PATH = (
    REPO_ROOT
    / "data/raw/a_share/rich/tushare/new_share/snapshots/campaign124_2019_2025_v1.json"
)
MANIFEST_PATH = (
    REPO_ROOT / "data/metadata/rich_data/runs/campaign124_new_share_acceptance_v1.json"
)
INTENT_PATH = (
    REPO_ROOT
    / "data/metadata/rich_data/runs/campaign124_new_share_acceptance_intent_v1.json"
)
FAILURE_PATH = (
    REPO_ROOT
    / "data/metadata/rich_data/runs/campaign124_new_share_acceptance_failure_v1.json"
)
CALENDAR_PATH = REPO_ROOT / BASELINE_BINDINGS["local_calendar"][0]


class Campaign124AcceptanceError(RuntimeError):
    """Raised when any frozen acceptance gate fails."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_bytes(record: Mapping[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _safe_dotenv_token(path: Path) -> str | None:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise Campaign124AcceptanceError("dotenv_safe_open_failed") from exc
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise Campaign124AcceptanceError("dotenv_not_regular")
        if stat.S_IMODE(file_stat.st_mode) != 0o600:
            raise Campaign124AcceptanceError("dotenv_mode_not_0600")
        if file_stat.st_size > DOTENV_MAX_BYTES:
            raise Campaign124AcceptanceError("dotenv_too_large")
        payload = os.read(descriptor, DOTENV_MAX_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(payload) > DOTENV_MAX_BYTES:
        raise Campaign124AcceptanceError("dotenv_too_large")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise Campaign124AcceptanceError("dotenv_not_utf8") from exc

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
                raise Campaign124AcceptanceError("dotenv_token_quote_invalid")
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values.append(value.strip())
    if len(values) > 1:
        raise Campaign124AcceptanceError("dotenv_duplicate_token_key")
    return values[0] if values and values[0] else None


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Campaign124AcceptanceError("authorization_policy_unreadable") from exc
    if not isinstance(value, dict):
        raise Campaign124AcceptanceError("authorization_policy_not_object")
    return value


def _authorization_checks() -> dict[str, bool]:
    checks = {"authorization_policy_exists": AUTHORIZATION_POLICY_PATH.is_file()}
    if not checks["authorization_policy_exists"]:
        return checks
    policy = _load_json(AUTHORIZATION_POLICY_PATH)
    authorization = policy.get("source_acceptance_authorization", {})
    workflow = authorization.get("workflow", {})
    tests = authorization.get("workflow_tests", {})
    freeze = authorization.get("workflow_freeze", {})
    checks.update(
        {
            "authorization_policy_version": policy.get("version") == 126,
            "authorization_enabled": authorization.get("authorized") is True,
            "authorization_one_shot": authorization.get("one_shot") is True,
            "authorization_no_retry": authorization.get("retry_allowed") is False,
            "authorization_maximum_calls": authorization.get("maximum_provider_calls")
            == MAXIMUM_PROVIDER_CALLS,
            "authorization_projection": tuple(authorization.get("request_fields", ()))
            == REQUEST_FIELDS,
            "authorization_workflow_hash": workflow.get("path")
            == str(WORKFLOW_PATH.relative_to(REPO_ROOT))
            and workflow.get("sha256") == file_sha256(WORKFLOW_PATH),
            "authorization_test_hash": tests.get("path")
            == str(WORKFLOW_TEST_PATH.relative_to(REPO_ROOT))
            and WORKFLOW_TEST_PATH.is_file()
            and tests.get("sha256") == file_sha256(WORKFLOW_TEST_PATH),
            "authorization_freeze_hash": isinstance(freeze.get("path"), str)
            and isinstance(freeze.get("sha256"), str)
            and (REPO_ROOT / freeze["path"]).is_file()
            and file_sha256(REPO_ROOT / freeze["path"]) == freeze["sha256"],
        }
    )
    return checks


def build_plan(*, inspect_credential: bool = True) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    for name, (relative, expected) in BASELINE_BINDINGS.items():
        path = REPO_ROOT / relative
        checks[f"binding_{name}"] = path.is_file() and file_sha256(path) == expected
    checks.update(_authorization_checks())
    checks.update(
        {
            "snapshot_absent": not SNAPSHOT_PATH.exists(),
            "manifest_absent": not MANIFEST_PATH.exists(),
            "intent_absent": not INTENT_PATH.exists(),
            "failure_absent": not FAILURE_PATH.exists(),
            "request_schedule_finite": REQUEST_YEARS == tuple(range(2019, 2026)),
            "acceptance_schedule_finite": ACCEPTANCE_YEARS == tuple(range(2019, 2024)),
            "maximum_provider_calls_exact": MAXIMUM_PROVIDER_CALLS == 7,
            "request_projection_exact": REQUEST_FIELDS
            == ("ts_code", "ipo_date", "issue_date", "ballot"),
            "forbidden_fields_excluded": not set(REQUEST_FIELDS)
            & {
                "sub_code",
                "name",
                "amount",
                "market_amount",
                "price",
                "pe",
                "limit_amount",
                "funds",
            },
        }
    )
    if inspect_credential:
        checks["tushare_token_present"] = bool(_safe_dotenv_token(DOTENV_PATH))
    ready = all(checks.values())
    return {
        "ready": ready,
        "exit_code_if_executed": 0 if ready else 2,
        "campaign": 124,
        "provider": "tushare",
        "api": "new_share",
        "request_years": list(REQUEST_YEARS),
        "request_fields": list(REQUEST_FIELDS),
        "maximum_provider_calls": MAXIMUM_PROVIDER_CALLS,
        "checks": checks,
        "blockers": [name for name, passed in checks.items() if not passed],
        "provider_request_issued": False,
        "credential_value_printed_hashed_or_persisted": False,
    }


def _provider_client(token: str):
    import tushare as ts

    return ts.pro_api(token)


def collect_projected_rows(
    client: Any, *, provider_call_counter: list[int] | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, int]]]:
    rows: list[dict[str, Any]] = []
    receipts: list[dict[str, int]] = []
    fields = ",".join(REQUEST_FIELDS)
    counter = provider_call_counter if provider_call_counter is not None else [0]
    if len(counter) != 1 or counter[0] != 0:
        raise Campaign124AcceptanceError("provider_call_counter_not_zero")
    for year in REQUEST_YEARS:
        counter[0] += 1
        frame = client.new_share(
            start_date=f"{year}0101",
            end_date=f"{year}1231",
            fields=fields,
        )
        if frame is None:
            frame = pd.DataFrame(columns=REQUEST_FIELDS)
        if not isinstance(frame, pd.DataFrame):
            raise Campaign124AcceptanceError("provider_response_not_dataframe")
        if tuple(frame.columns) != REQUEST_FIELDS:
            raise Campaign124AcceptanceError("provider_projection_mismatch")
        if len(frame) >= SUSPECT_RESPONSE_ROW_LIMIT:
            raise Campaign124AcceptanceError("provider_response_possible_truncation")
        clean = frame.astype(object).where(pd.notna(frame), None)
        records = clean.to_dict(orient="records")
        rows.extend(records)
        receipts.append({"year": year, "rows": len(records)})
    return rows, receipts


def load_accepted_calendar(path: Path = CALENDAR_PATH) -> tuple[str, ...]:
    try:
        sessions = tuple(
            line.strip() for line in path.read_text(encoding="utf-8").splitlines()
        )
    except OSError as exc:
        raise Campaign124AcceptanceError("accepted_calendar_unreadable") from exc
    if not sessions or any(not session for session in sessions):
        raise Campaign124AcceptanceError("accepted_calendar_empty_or_blank")
    try:
        parsed = tuple(date.fromisoformat(session) for session in sessions)
    except ValueError as exc:
        raise Campaign124AcceptanceError("accepted_calendar_invalid") from exc
    if any(parsed[index] >= parsed[index + 1] for index in range(len(parsed) - 1)):
        raise Campaign124AcceptanceError("accepted_calendar_not_strictly_increasing")
    return sessions


def evaluate_source_acceptance(
    projected_rows: list[dict[str, Any]],
    receipts: list[dict[str, int]],
    *,
    accepted_calendar: Sequence[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(receipts) != MAXIMUM_PROVIDER_CALLS:
        raise Campaign124AcceptanceError("provider_call_receipt_count_mismatch")
    if tuple(receipt.get("year") for receipt in receipts) != REQUEST_YEARS:
        raise Campaign124AcceptanceError("provider_call_receipt_year_mismatch")
    events, stats = adapter.canonicalize_new_share_rows(projected_rows)
    calendar_set = set(accepted_calendar or load_accepted_calendar())
    event_year_counts = {year: 0 for year in REQUEST_YEARS}
    distinct_ballots_2019_2023: set[float] = set()
    for event in events:
        issue_date = str(event["issue_date"])
        issue_session = date(
            int(issue_date[:4]), int(issue_date[4:6]), int(issue_date[6:8])
        ).isoformat()
        if issue_session not in calendar_set:
            raise Campaign124AcceptanceError("issue_date_not_accepted_local_session")
        year = int(issue_date[:4])
        if year not in event_year_counts:
            raise Campaign124AcceptanceError("event_issue_date_outside_scope")
        event_year_counts[year] += 1
        if year in ACCEPTANCE_YEARS:
            distinct_ballots_2019_2023.add(float(event["ballot"]))

    acceptance_total = sum(event_year_counts[year] for year in ACCEPTANCE_YEARS)
    checks = {
        **{
            f"{year}_minimum_supported_events": event_year_counts[year]
            >= MINIMUM_EVENTS_PER_ACCEPTANCE_YEAR
            for year in ACCEPTANCE_YEARS
        },
        "minimum_supported_events_total_2019_2023": acceptance_total
        >= MINIMUM_EVENTS_TOTAL_2019_2023,
    }
    if not all(checks.values()):
        raise Campaign124AcceptanceError("source_acceptance_coverage_gate_failed")
    evidence = {
        "checks": checks,
        "projected_input_rows": len(projected_rows),
        "canonical_supported_events": len(events),
        "supported_events_total_2019_2023": acceptance_total,
        "distinct_ballot_values_2019_2023": len(distinct_ballots_2019_2023),
        "event_year_counts": {
            str(year): count for year, count in event_year_counts.items()
        },
        "provider_call_receipts": receipts,
        "adapter_stats": stats,
        "price_or_forward_return_values_read": False,
    }
    return events, evidence


def _exclusive_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise Campaign124AcceptanceError("atomic_write_failed")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_pair(snapshot: dict[str, Any], manifest: dict[str, Any]) -> None:
    snapshot_payload = _json_bytes(snapshot)
    manifest["snapshot_sha256"] = hashlib.sha256(snapshot_payload).hexdigest()
    manifest_payload = _json_bytes(manifest)
    snapshot_temp = SNAPSHOT_PATH.with_name(f".{SNAPSHOT_PATH.name}.{os.getpid()}.tmp")
    manifest_temp = MANIFEST_PATH.with_name(f".{MANIFEST_PATH.name}.{os.getpid()}.tmp")
    published: list[Path] = []
    try:
        _exclusive_write(snapshot_temp, snapshot_payload)
        _exclusive_write(manifest_temp, manifest_payload)
        if SNAPSHOT_PATH.exists() or MANIFEST_PATH.exists():
            raise Campaign124AcceptanceError("acceptance_output_already_exists")
        os.replace(snapshot_temp, SNAPSHOT_PATH)
        published.append(SNAPSHOT_PATH)
        os.replace(manifest_temp, MANIFEST_PATH)
        published.append(MANIFEST_PATH)
    except Exception:
        for path in (snapshot_temp, manifest_temp, *published):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise


def _write_intent(plan: Mapping[str, Any]) -> None:
    intent = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign124_new_share_acceptance_intent",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "one_shot": True,
        "retry_allowed": False,
        "request_years": list(REQUEST_YEARS),
        "request_fields": list(REQUEST_FIELDS),
        "maximum_provider_calls": MAXIMUM_PROVIDER_CALLS,
        "plan_checks": dict(plan["checks"]),
        "credential_value_printed_hashed_or_persisted": False,
    }
    _exclusive_write(INTENT_PATH, _json_bytes(intent))


def _write_failure(failure_code: str, provider_calls_issued: int) -> None:
    failure = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign124_new_share_acceptance_failure",
        "status": "terminal_source_acceptance_failure_no_retry",
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "failure_code": failure_code,
        "provider_calls_issued": provider_calls_issued,
        "retry_allowed": False,
        "exception_message_persisted": False,
        "credential_value_printed_hashed_or_persisted": False,
        "raw_provider_rows_or_counts_persisted": False,
        "candidate_comparator_price_or_return_values_read": False,
    }
    try:
        _exclusive_write(FAILURE_PATH, _json_bytes(failure))
    except FileExistsError:
        pass


def run_acceptance(*, confirm_run: bool, confirm_provider_request: bool) -> int:
    if not confirm_run or not confirm_provider_request:
        raise Campaign124AcceptanceError("explicit_confirmation_flags_required")
    plan = build_plan(inspect_credential=True)
    if not plan["ready"]:
        raise Campaign124AcceptanceError("acceptance_plan_not_ready")
    _write_intent(plan)
    provider_call_counter = [0]
    try:
        token = _safe_dotenv_token(DOTENV_PATH)
        if not token:
            raise Campaign124AcceptanceError("tushare_token_unavailable")
        client = _provider_client(token)
        projected_rows, receipts = collect_projected_rows(
            client, provider_call_counter=provider_call_counter
        )
        events, evidence = evaluate_source_acceptance(projected_rows, receipts)
        recorded_at = datetime.now().astimezone().isoformat(timespec="seconds")
        snapshot = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign124_new_share_snapshot",
            "status": "accepted_normalized_new_share_ballot_events",
            "recorded_at": recorded_at,
            "source_api": "new_share",
            "request_fields": list(REQUEST_FIELDS),
            "forbidden_fields_requested_read_or_persisted": False,
            "events": events,
        }
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign124_new_share_acceptance",
            "status": "source_accepted_before_factor_comparator_price_or_return_values",
            "recorded_at": recorded_at,
            "snapshot_path": str(SNAPSHOT_PATH.relative_to(REPO_ROOT)),
            "source_evidence": evidence,
            "provider_calls_issued": provider_call_counter[0],
            "raw_provider_rows_persisted": False,
            "credential_value_printed_hashed_or_persisted": False,
            "candidate_comparator_price_or_return_values_read": False,
        }
        _publish_pair(snapshot, manifest)
    except Exception as exc:
        if provider_call_counter[0] == 0 and isinstance(
            exc, Campaign124AcceptanceError
        ):
            failure_code = str(exc)
        elif isinstance(exc, adapter.Campaign124ContractError):
            failure_code = "source_schema_or_canonicalization_contract_failure"
        elif isinstance(exc, Campaign124AcceptanceError):
            failure_code = str(exc)
        else:
            failure_code = "provider_permission_or_request_failure"
        _write_failure(failure_code, provider_call_counter[0])
        return 2
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    run = subparsers.add_parser("run")
    run.add_argument("--confirm-run", action="store_true")
    run.add_argument("--confirm-provider-request", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.command == "plan":
        plan = build_plan(inspect_credential=True)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return int(plan["exit_code_if_executed"])
    try:
        return run_acceptance(
            confirm_run=arguments.confirm_run,
            confirm_provider_request=arguments.confirm_provider_request,
        )
    except Campaign124AcceptanceError as exc:
        print(
            json.dumps(
                {
                    "status": "blocked_before_provider_request",
                    "failure_code": str(exc),
                    "credential_value_printed_hashed_or_persisted": False,
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
