#!/usr/bin/env python3
"""Zero-network, plan-only Campaign265 source-acceptance planner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PLANNER_PATH = Path(__file__).resolve()
PLANNER_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_source_acceptance_plan.py"
)
AUTHORIZATION_POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v418_20260824.json"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_planner_implementation_freeze_20260824.json"
)

BASELINE_BINDINGS = {
    "adapter_ready_state": (
        "docs/a_share_three_day_iteration_status_20260824_campaign265_adapter_ready.json",
        "926cb5336c11225106711964ac5cc566289f9dc467edc52d83edba80ea23ce6e",
    ),
    "numeric_policy_v417": (
        "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v417_20260824.json",
        "62805389b141904fe6b519bb7ff345410802fb5475f3804615e6f12ff81da39f",
    ),
    "source_contract": (
        "docs/a_share_three_day_walkforward_campaign_265_convertible_premium_source_contract_20260824.json",
        "efe7884d3ea0fd7f974e0d3347432e68e9e01ceefe0e6ebdca7fdd3e6349301c",
    ),
    "adapter": (
        "scripts/a_share_three_day_walkforward_campaign265_convertible_premium.py",
        "58b9fddbbeef97955d4961f9f708028aa63d90fc56f2656db68098de7d3543e8",
    ),
    "adapter_tests": (
        "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_convertible_premium.py",
        "b681af4d0d6f3d7081adac6207dab438c7166945bfea27c72ac4ea61ea481f4a",
    ),
    "adapter_implementation_freeze": (
        "docs/a_share_three_day_walkforward_campaign_265_adapter_implementation_freeze_20260824.json",
        "2429588261bf35e46c3a68daeab85b23405c247a6fd98195e081c2b43c1f638e",
    ),
    "source_acceptance_preregistration": (
        "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_preregistration_20260824.json",
        "474e5a995703f46005053268bbbd6c1c20835c99233f82e727a24a6085198ffd",
    ),
    "attempt_ledger_v3": (
        "data/experiments/short_horizon/historical_walkforward/campaign_265/research_attempt_ledger_v3.json",
        "7edd5202c77ed575f84efc6e8ecbc51bb2367f631783b1f3810e2378d094bdf0",
    ),
    "calendar": (
        "data/qlib/cn_a_share/calendars/day.txt",
        "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a",
    ),
    "factor_universe": (
        "data/qlib/cn_a_share/instruments/factor_main_chinext_star.txt",
        "cdded13c831b78045f4cfe80ba5d9a49f82152c615fef4267d00f992e7f53762",
    ),
    "candidate49_signal_ledger": (
        "data/experiments/short_horizon/candidate49_future_signal_ledger.json",
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79",
    ),
    "candidate49_execution_ledger": (
        "data/experiments/short_horizon/candidate49_future_execution_ledger.json",
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f",
    ),
}

FIRST_DATE = "2019-01-02"
LAST_DATE = "2025-12-31"
ACCEPTED_DATE_COUNT = 1699
ACCEPTED_DATE_LIST_SHA256 = (
    "f9205c3cfdeb51b808d18b66edb8cf66bf57df94f696fb3b6bd5743b9a0bc769"
)
REQUEST_SEQUENCE_SHA256 = (
    "3f9cccb3134b7e9e22f5d34fd8bc07f89e1d8047dd775d07c3257443a97b4c58"
)
FACTOR_UNIVERSE_COUNT = 5451
CB_BASIC_FIELDS = (
    "ts_code",
    "cb_type",
    "stk_code",
    "list_date",
    "delist_date",
    "exchange",
)
CB_DAILY_FIELDS = ("ts_code", "trade_date", "amount", "cb_over_rate")
EXACT_PROVIDER_CALL_COUNT = 1700
STRICT_ROW_CEILING = 2000
MINIMUM_REQUEST_INTERVAL_SECONDS = 1.05

DESTINATIONS = {
    "staging_root": "data/raw/a_share/rich/tushare/convertible_premium/campaign265_2019_2025_v1.staging",
    "final_root": "data/raw/a_share/rich/tushare/convertible_premium/campaign265_2019_2025_v1",
    "cb_basic_checkpoint": "data/raw/a_share/rich/tushare/convertible_premium/campaign265_2019_2025_v1.staging/cb_basic.parquet",
    "cb_daily_checkpoint_template": "data/raw/a_share/rich/tushare/convertible_premium/campaign265_2019_2025_v1.staging/cb_daily/{trade_date}.parquet",
    "internal_manifest": "data/raw/a_share/rich/tushare/convertible_premium/campaign265_2019_2025_v1.staging/source_manifest.json",
    "intent": "data/metadata/rich_data/runs/campaign265_convertible_premium_acceptance_intent_v1.json",
    "attempt_journal": "data/metadata/rich_data/runs/campaign265_convertible_premium_acceptance_attempt_v1.jsonl",
    "terminal_failure": "data/metadata/rich_data/runs/campaign265_convertible_premium_acceptance_failure_v1.json",
    "repository_acceptance_manifest": "data/metadata/rich_data/runs/campaign265_convertible_premium_acceptance_v1.json",
}


class Campaign265PlanError(RuntimeError):
    """Raised when immutable planner metadata is malformed."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Campaign265PlanError("authorization_policy_unreadable") from exc
    if not isinstance(value, dict):
        raise Campaign265PlanError("authorization_policy_not_object")
    return value


def _accepted_dates() -> list[str]:
    calendar_path = REPO_ROOT / BASELINE_BINDINGS["calendar"][0]
    raw_dates = [line.strip() for line in calendar_path.read_text().splitlines()]
    if not raw_dates or any(not value for value in raw_dates):
        raise Campaign265PlanError("calendar_contains_blank_or_is_empty")
    parsed: list[str] = []
    for value in raw_dates:
        try:
            observed = date.fromisoformat(value)
        except ValueError as exc:
            raise Campaign265PlanError("calendar_date_not_strict_iso") from exc
        if observed.isoformat() != value:
            raise Campaign265PlanError("calendar_date_not_strict_iso")
        parsed.append(value)
    if parsed != sorted(set(parsed)):
        raise Campaign265PlanError("calendar_not_strictly_increasing_unique")
    return [value for value in parsed if FIRST_DATE <= value <= LAST_DATE]


def _request_sequence(dates: list[str]) -> list[dict[str, Any]]:
    sequence: list[dict[str, Any]] = [
        {
            "api": "cb_basic",
            "fields": list(CB_BASIC_FIELDS),
            "ordinal": 1,
            "parameters": {},
        }
    ]
    sequence.extend(
        {
            "api": "cb_daily",
            "fields": list(CB_DAILY_FIELDS),
            "ordinal": ordinal,
            "parameters": {"trade_date": trade_date.replace("-", "")},
        }
        for ordinal, trade_date in enumerate(dates, start=2)
    )
    return sequence


def _artifact_absent(relative: str) -> bool:
    return not os.path.lexists(REPO_ROOT / relative)


def _authorization_checks() -> dict[str, bool]:
    checks = {"plan_authorization_policy_exists": AUTHORIZATION_POLICY_PATH.is_file()}
    if not checks["plan_authorization_policy_exists"]:
        return checks
    policy = _load_json(AUTHORIZATION_POLICY_PATH)
    authorization = policy.get("campaign265_source_acceptance_plan_authorization") or {}
    planner = authorization.get("planner") or {}
    tests = authorization.get("planner_tests") or {}
    preregistration = authorization.get("preregistration") or {}
    freeze = authorization.get("implementation_freeze") or {}
    checks.update(
        {
            "plan_authorization_policy_version": policy.get("version") == 418,
            "plan_only_authorized": authorization.get("authorized") is True
            and authorization.get("plan_only") is True,
            "credential_load_forbidden": authorization.get("credential_load_allowed")
            is False,
            "provider_request_forbidden": authorization.get("provider_request_allowed")
            is False,
            "run_interface_forbidden": authorization.get("run_interface_allowed")
            is False,
            "exact_call_count_authorized": authorization.get(
                "exact_provider_call_count"
            )
            == EXACT_PROVIDER_CALL_COUNT,
            "planner_hash_authorized": planner.get("path")
            == str(PLANNER_PATH.relative_to(REPO_ROOT))
            and planner.get("sha256") == file_sha256(PLANNER_PATH),
            "planner_test_hash_authorized": tests.get("path")
            == str(PLANNER_TEST_PATH.relative_to(REPO_ROOT))
            and PLANNER_TEST_PATH.is_file()
            and tests.get("sha256") == file_sha256(PLANNER_TEST_PATH),
            "preregistration_hash_authorized": preregistration.get("path")
            == BASELINE_BINDINGS["source_acceptance_preregistration"][0]
            and preregistration.get("sha256")
            == BASELINE_BINDINGS["source_acceptance_preregistration"][1],
            "implementation_freeze_hash_authorized": isinstance(freeze.get("path"), str)
            and freeze.get("path")
            == str(IMPLEMENTATION_FREEZE_PATH.relative_to(REPO_ROOT))
            and IMPLEMENTATION_FREEZE_PATH.is_file()
            and freeze.get("sha256") == file_sha256(IMPLEMENTATION_FREEZE_PATH),
        }
    )
    return checks


def build_plan() -> dict[str, Any]:
    """Return the deterministic source intent without credentials, network or writes."""

    checks: dict[str, bool] = {}
    for name, (relative, expected) in BASELINE_BINDINGS.items():
        path = REPO_ROOT / relative
        checks[f"binding_{name}"] = path.is_file() and file_sha256(path) == expected

    try:
        accepted_dates = _accepted_dates()
    except (OSError, UnicodeError, Campaign265PlanError):
        accepted_dates = []
    accepted_payload = ("\n".join(accepted_dates) + "\n").encode("utf-8")
    request_sequence = _request_sequence(accepted_dates)
    universe_path = REPO_ROOT / BASELINE_BINDINGS["factor_universe"][0]
    try:
        universe_count = sum(
            1 for line in universe_path.read_text().splitlines() if line.strip()
        )
    except (OSError, UnicodeError):
        universe_count = -1

    checks.update(
        {
            "accepted_date_count_exact": len(accepted_dates) == ACCEPTED_DATE_COUNT,
            "accepted_date_endpoints_exact": bool(accepted_dates)
            and accepted_dates[0] == FIRST_DATE
            and accepted_dates[-1] == LAST_DATE,
            "accepted_date_list_digest_exact": hashlib.sha256(
                accepted_payload
            ).hexdigest()
            == ACCEPTED_DATE_LIST_SHA256,
            "factor_universe_count_exact": universe_count == FACTOR_UNIVERSE_COUNT,
            "request_sequence_count_exact": len(request_sequence)
            == EXACT_PROVIDER_CALL_COUNT,
            "request_sequence_digest_exact": _canonical_json_sha256(request_sequence)
            == REQUEST_SEQUENCE_SHA256,
            "request_projections_exact": request_sequence[:1]
            == [
                {
                    "api": "cb_basic",
                    "fields": list(CB_BASIC_FIELDS),
                    "ordinal": 1,
                    "parameters": {},
                }
            ]
            and all(
                item["api"] == "cb_daily" and item["fields"] == list(CB_DAILY_FIELDS)
                for item in request_sequence[1:]
            ),
            "strict_row_ceiling_exact": STRICT_ROW_CEILING == 2000,
            "minimum_request_interval_exact": MINIMUM_REQUEST_INTERVAL_SECONDS == 1.05,
            "staging_root_absent": _artifact_absent(DESTINATIONS["staging_root"]),
            "final_root_absent": _artifact_absent(DESTINATIONS["final_root"]),
            "intent_absent": _artifact_absent(DESTINATIONS["intent"]),
            "attempt_journal_absent": _artifact_absent(DESTINATIONS["attempt_journal"]),
            "terminal_failure_absent": _artifact_absent(
                DESTINATIONS["terminal_failure"]
            ),
            "repository_acceptance_manifest_absent": _artifact_absent(
                DESTINATIONS["repository_acceptance_manifest"]
            ),
        }
    )
    try:
        checks.update(_authorization_checks())
    except (OSError, Campaign265PlanError):
        checks["plan_authorization_policy_semantics"] = False

    ready = all(checks.values())
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_source_acceptance_plan",
        "status": "ready_zero_network_plan_only" if ready else "blocked_fail_closed",
        "ready": ready,
        "exit_code_if_executed": 0 if ready else 2,
        "campaign": 265,
        "provider": "Tushare Pro",
        "apis": ["cb_basic", "cb_daily"],
        "accepted_trade_dates": accepted_dates,
        "accepted_trade_date_count": len(accepted_dates),
        "accepted_trade_dates_canonical_newline_sha256": hashlib.sha256(
            accepted_payload
        ).hexdigest(),
        "cb_basic_fields": list(CB_BASIC_FIELDS),
        "cb_daily_fields": list(CB_DAILY_FIELDS),
        "exact_provider_call_count": len(request_sequence),
        "request_sequence_canonical_json_sha256": _canonical_json_sha256(
            request_sequence
        ),
        "strict_response_rows_less_than": STRICT_ROW_CEILING,
        "minimum_response_rows_per_call": 1,
        "minimum_seconds_between_provider_entries": MINIMUM_REQUEST_INTERVAL_SECONDS,
        "destinations": DESTINATIONS,
        "checks": checks,
        "blockers": [name for name, passed in checks.items() if not passed],
        "credential_file_or_environment_inspected": False,
        "credential_value_or_digest_read": False,
        "provider_client_imported_or_created": False,
        "provider_request_issued": False,
        "source_candidate_comparator_price_or_return_value_read": False,
        "filesystem_write_performed": False,
        "run_or_confirmation_interface_exposed": False,
        "ready_does_not_authorize_credential_load_or_provider_request": True,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.command != "plan":
        raise Campaign265PlanError("unsupported_command")
    plan = build_plan()
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return int(plan["exit_code_if_executed"])


if __name__ == "__main__":
    raise SystemExit(main())
