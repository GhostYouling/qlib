#!/usr/bin/env python3
"""One-shot, fail-closed Campaign127 convertible-issue source acceptance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = Path(__file__).resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign127_convertible_issue as adapter,
)

WORKFLOW_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign127_convertible_issue_acceptance.py"
)
AUTHORIZATION_POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v133_20260814.json"
)
DOTENV_PATH = REPO_ROOT / ".env"
DOTENV_MAX_BYTES = 64 * 1024
TOKEN_ENV = "TUSHARE_TOKEN"

BASELINE_BINDINGS = {
    "numeric_policy_v132": (
        "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v132_20260814.json",
        "5885b81d98adda0a7c64a20203e826a5b9638bef4eae558036e170910b54114b",
    ),
    "source_contract": (
        "docs/a_share_three_day_walkforward_campaign_127_convertible_issue_source_contract_20260814.json",
        "66e8ed362c0f5d9efb67de659ab39e83899b0fc8f0e92a0eb5e3399cd8c064a5",
    ),
    "adapter": (
        "scripts/a_share_three_day_walkforward_campaign127_convertible_issue.py",
        "1edcd09dcb9b6ede6a574f8a55218b2cba993b992a94eabce1ab90d207d27c2b",
    ),
    "adapter_tests": (
        "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign127_convertible_issue.py",
        "58d25ac17b386e499e794e7dd6b44faed062af284633879f71abcb849dc23bb9",
    ),
    "adapter_formula_freeze": (
        "docs/a_share_three_day_walkforward_campaign_127_convertible_issue_adapter_formula_freeze_20260814.json",
        "d2826be2485a6fe75022ab526f5abf78630072257c2b6d63ade1822d7ef8a0de",
    ),
    "attempt_ledger_v1": (
        "data/experiments/short_horizon/historical_walkforward/campaign_127/research_attempt_ledger_v1.json",
        "f39a8cc53d42cca2c3fa907060572a75db6170635a6c2ebcbd97343b6ce2b931",
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

REQUEST_YEARS = tuple(range(2018, 2026))
ACCEPTANCE_YEARS = tuple(range(2019, 2024))
BASIC_FIELDS = adapter.BASIC_SOURCE_FIELDS
ISSUE_FIELDS = adapter.ISSUE_SOURCE_FIELDS
MAXIMUM_PROVIDER_CALLS = 1 + len(REQUEST_YEARS)
SUSPECT_RESPONSE_ROW_LIMIT = 2000
MINIMUM_EVENTS_PER_ACCEPTANCE_YEAR = 20
MINIMUM_EVENTS_TOTAL_2019_2023 = 150

SNAPSHOT_PATH = (
    REPO_ROOT
    / "data/raw/a_share/rich/tushare/cb_issue/snapshots/campaign127_2018_2025_v1.json"
)
MANIFEST_PATH = (
    REPO_ROOT
    / "data/metadata/rich_data/runs/campaign127_convertible_issue_acceptance_v1.json"
)
INTENT_PATH = (
    REPO_ROOT
    / "data/metadata/rich_data/runs/campaign127_convertible_issue_acceptance_intent_v1.json"
)
FAILURE_PATH = (
    REPO_ROOT
    / "data/metadata/rich_data/runs/campaign127_convertible_issue_acceptance_failure_v1.json"
)


class Campaign127AcceptanceError(RuntimeError):
    """Raised when any frozen Campaign127 acceptance gate fails."""


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
        raise Campaign127AcceptanceError("dotenv_safe_open_failed") from exc
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise Campaign127AcceptanceError("dotenv_not_regular")
        if stat.S_IMODE(file_stat.st_mode) != 0o600:
            raise Campaign127AcceptanceError("dotenv_mode_not_0600")
        if file_stat.st_size > DOTENV_MAX_BYTES:
            raise Campaign127AcceptanceError("dotenv_too_large")
        payload = os.read(descriptor, DOTENV_MAX_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(payload) > DOTENV_MAX_BYTES:
        raise Campaign127AcceptanceError("dotenv_too_large")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise Campaign127AcceptanceError("dotenv_not_utf8") from exc

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
                raise Campaign127AcceptanceError("dotenv_token_quote_invalid")
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        values.append(value.strip())
    if len(values) > 1:
        raise Campaign127AcceptanceError("dotenv_duplicate_token_key")
    return values[0] if values and values[0] else None


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Campaign127AcceptanceError("authorization_policy_unreadable") from exc
    if not isinstance(value, dict):
        raise Campaign127AcceptanceError("authorization_policy_not_object")
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
            "authorization_policy_version": policy.get("version") == 133,
            "authorization_enabled": authorization.get("authorized") is True,
            "authorization_one_shot": authorization.get("one_shot") is True,
            "authorization_no_retry": authorization.get("retry_allowed") is False,
            "authorization_maximum_calls": authorization.get("maximum_provider_calls")
            == MAXIMUM_PROVIDER_CALLS,
            "authorization_basic_projection": tuple(
                authorization.get("cb_basic_request_fields", ())
            )
            == BASIC_FIELDS,
            "authorization_issue_projection": tuple(
                authorization.get("cb_issue_request_fields", ())
            )
            == ISSUE_FIELDS,
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
            "request_schedule_finite": REQUEST_YEARS == tuple(range(2018, 2026)),
            "acceptance_schedule_finite": ACCEPTANCE_YEARS == tuple(range(2019, 2024)),
            "maximum_provider_calls_exact": MAXIMUM_PROVIDER_CALLS == 9,
            "cb_basic_projection_exact": BASIC_FIELDS
            == ("ts_code", "stk_code", "cb_type"),
            "cb_issue_projection_exact": ISSUE_FIELDS
            == ("ts_code", "ann_date", "res_ann_date", "onl_pch_excess"),
        }
    )
    if inspect_credential:
        checks["tushare_token_present"] = bool(_safe_dotenv_token(DOTENV_PATH))
    ready = all(checks.values())
    return {
        "ready": ready,
        "exit_code_if_executed": 0 if ready else 2,
        "campaign": 127,
        "provider": "tushare",
        "apis": ["cb_basic", "cb_issue"],
        "cb_issue_request_years": list(REQUEST_YEARS),
        "cb_basic_request_fields": list(BASIC_FIELDS),
        "cb_issue_request_fields": list(ISSUE_FIELDS),
        "maximum_provider_calls": MAXIMUM_PROVIDER_CALLS,
        "checks": checks,
        "blockers": [name for name, passed in checks.items() if not passed],
        "provider_request_issued": False,
        "credential_value_printed_hashed_or_persisted": False,
    }


def _provider_client(token: str):
    import tushare as ts

    return ts.pro_api(token)


def _project_frame(frame: Any, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    if frame is None:
        frame = pd.DataFrame(columns=fields)
    if not isinstance(frame, pd.DataFrame):
        raise Campaign127AcceptanceError("provider_response_not_dataframe")
    if tuple(frame.columns) != fields:
        raise Campaign127AcceptanceError("provider_projection_mismatch")
    if len(frame) >= SUSPECT_RESPONSE_ROW_LIMIT:
        raise Campaign127AcceptanceError("provider_response_possible_truncation")
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def collect_projected_rows(
    client: Any, *, provider_call_counter: list[int] | None = None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    counter = provider_call_counter if provider_call_counter is not None else [0]
    if len(counter) != 1 or counter[0] != 0:
        raise Campaign127AcceptanceError("provider_call_counter_not_zero")
    receipts: list[dict[str, Any]] = []

    counter[0] += 1
    basic_rows = _project_frame(
        client.cb_basic(fields=",".join(BASIC_FIELDS)), BASIC_FIELDS
    )
    receipts.append({"api": "cb_basic", "year": None, "rows": len(basic_rows)})

    issue_rows: list[dict[str, Any]] = []
    for year in REQUEST_YEARS:
        counter[0] += 1
        records = _project_frame(
            client.cb_issue(
                start_date=f"{year}0101",
                end_date=f"{year}1231",
                fields=",".join(ISSUE_FIELDS),
            ),
            ISSUE_FIELDS,
        )
        issue_rows.extend(records)
        receipts.append({"api": "cb_issue", "year": year, "rows": len(records)})
    return basic_rows, issue_rows, receipts


def evaluate_source_acceptance(
    basic_rows: list[dict[str, Any]],
    issue_rows: list[dict[str, Any]],
    receipts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(receipts) != MAXIMUM_PROVIDER_CALLS:
        raise Campaign127AcceptanceError("provider_call_receipt_count_mismatch")
    if receipts[0].get("api") != "cb_basic" or receipts[0].get("year") is not None:
        raise Campaign127AcceptanceError("cb_basic_receipt_mismatch")
    issue_receipts = receipts[1:]
    if tuple(receipt.get("api") for receipt in issue_receipts) != ("cb_issue",) * len(
        REQUEST_YEARS
    ):
        raise Campaign127AcceptanceError("cb_issue_receipt_api_mismatch")
    if tuple(receipt.get("year") for receipt in issue_receipts) != REQUEST_YEARS:
        raise Campaign127AcceptanceError("cb_issue_receipt_year_mismatch")

    events, stats = adapter.canonicalize_convertible_issue_rows(basic_rows, issue_rows)
    event_year_counts = {year: 0 for year in REQUEST_YEARS}
    distinct_multiples_2019_2023: set[float] = set()
    for event in events:
        year = int(str(event["res_ann_date"])[:4])
        if year in event_year_counts:
            event_year_counts[year] += 1
        if year in ACCEPTANCE_YEARS:
            distinct_multiples_2019_2023.add(float(event["online_excess_multiple"]))

    acceptance_total = sum(event_year_counts[year] for year in ACCEPTANCE_YEARS)
    checks = {
        **{
            f"{year}_minimum_supported_events": event_year_counts[year]
            >= MINIMUM_EVENTS_PER_ACCEPTANCE_YEAR
            for year in ACCEPTANCE_YEARS
        },
        "minimum_supported_events_total_2019_2023": acceptance_total
        >= MINIMUM_EVENTS_TOTAL_2019_2023,
        "minimum_two_distinct_multiples_2019_2023": len(distinct_multiples_2019_2023)
        >= 2,
    }
    if not all(checks.values()):
        raise Campaign127AcceptanceError("source_acceptance_coverage_gate_failed")
    evidence = {
        "checks": checks,
        "cb_basic_projected_input_rows": len(basic_rows),
        "cb_issue_projected_input_rows": len(issue_rows),
        "canonical_supported_events": len(events),
        "supported_events_total_2019_2023": acceptance_total,
        "distinct_online_excess_values_2019_2023": len(distinct_multiples_2019_2023),
        "event_result_year_counts": {
            str(year): count for year, count in event_year_counts.items()
        },
        "provider_call_receipts": receipts,
        "adapter_stats": stats,
        "factor_panel_comparator_price_or_forward_return_values_read": False,
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
                raise Campaign127AcceptanceError("atomic_write_failed")
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
            raise Campaign127AcceptanceError("acceptance_output_already_exists")
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
        "kind": "a_share_three_day_walkforward_campaign127_convertible_issue_acceptance_intent",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "one_shot": True,
        "retry_allowed": False,
        "cb_issue_request_years": list(REQUEST_YEARS),
        "cb_basic_request_fields": list(BASIC_FIELDS),
        "cb_issue_request_fields": list(ISSUE_FIELDS),
        "maximum_provider_calls": MAXIMUM_PROVIDER_CALLS,
        "plan_checks": dict(plan["checks"]),
        "credential_value_printed_hashed_or_persisted": False,
    }
    _exclusive_write(INTENT_PATH, _json_bytes(intent))


def _write_failure(failure_code: str, provider_calls_issued: int) -> None:
    failure = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign127_convertible_issue_acceptance_failure",
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
        raise Campaign127AcceptanceError("explicit_confirmation_flags_required")
    plan = build_plan(inspect_credential=True)
    if not plan["ready"]:
        raise Campaign127AcceptanceError("acceptance_plan_not_ready")
    _write_intent(plan)
    provider_call_counter = [0]
    try:
        token = _safe_dotenv_token(DOTENV_PATH)
        if not token:
            raise Campaign127AcceptanceError("tushare_token_unavailable")
        client = _provider_client(token)
        basic_rows, issue_rows, receipts = collect_projected_rows(
            client, provider_call_counter=provider_call_counter
        )
        events, evidence = evaluate_source_acceptance(basic_rows, issue_rows, receipts)
        recorded_at = datetime.now().astimezone().isoformat(timespec="seconds")
        snapshot = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign127_convertible_issue_snapshot",
            "status": "accepted_normalized_convertible_issue_online_demand_events",
            "recorded_at": recorded_at,
            "source_apis": ["cb_basic", "cb_issue"],
            "cb_basic_request_fields": list(BASIC_FIELDS),
            "cb_issue_request_fields": list(ISSUE_FIELDS),
            "forbidden_fields_requested_read_or_persisted": False,
            "events": events,
        }
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign127_convertible_issue_acceptance",
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
            exc, Campaign127AcceptanceError
        ):
            failure_code = str(exc)
        elif isinstance(exc, adapter.Campaign127ContractError):
            failure_code = "source_schema_or_canonicalization_contract_failure"
        elif isinstance(exc, Campaign127AcceptanceError):
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
    except Campaign127AcceptanceError as exc:
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
