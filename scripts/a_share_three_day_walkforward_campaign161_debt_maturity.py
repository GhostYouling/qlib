#!/usr/bin/env python3
"""One-shot Campaign161 Eastmoney debt-maturity source acceptance.

The plan command is deliberately local-only.  The acceptance command is the
only path that can issue the single frozen 2023-Q4, count-complete request.
Neither command reads credentials, prices, returns, or Candidate49 values.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import shutil
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = Path(__file__).resolve()
TEST_PATH = (
    REPO_ROOT / "tests/data_collector_tests/"
    "test_a_share_three_day_walkforward_campaign161_debt_maturity.py"
)
CONTRACT_PATH = (
    REPO_ROOT
    / "docs/a_share_eastmoney_debt_maturity_resilience_data_contract_20260815.json"
)
CONTRACT_RECORDED_PATH = (
    "docs/a_share_eastmoney_debt_maturity_resilience_data_contract_20260815.json"
)
CONTRACT_SHA256 = "c901436aecec2927c722e6f5d59d8d4e82fe73ec611dafe6f4be7403c1a42831"
CONTRACT_BINDING_CORRECTION_PATH = (
    REPO_ROOT
    / "docs/a_share_eastmoney_debt_maturity_resilience_data_contract_binding_correction_20260815.json"
)
CONTRACT_BINDING_CORRECTION_SHA256 = (
    "a53aedd8a87eeaa0e47cba75e3d9d78de10eaddc89de324c1c329abd811993e9"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_161_debt_maturity_implementation_freeze_v3_20260815.json"
)
NUMERIC_POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v224_20260815.json"
)
MANAGE_DATA_SKILL_PATH = Path(
    "/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md"
)
HOLDING_UNIVERSE_PATH = (
    REPO_ROOT / "data/qlib/cn_a_share/instruments/buyable_main_chinext.txt"
)
CANDIDATE49_SIGNAL_LEDGER_PATH = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
CANDIDATE49_EXECUTION_LEDGER_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)

SOURCE_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_161/source"
)
ACCEPTED_ROOT = SOURCE_ROOT / "acceptance_2023q4_v1"
DATA_NAME = "eastmoney_debt_maturity_resilience_2023q4.parquet"
MANIFEST_NAME = "snapshot_manifest.json"
INTENT_PATH = SOURCE_ROOT / "acceptance_2023q4_intent_v1.json"
ACCEPTANCE_RECORD_PATH = SOURCE_ROOT / "acceptance_2023q4_record_v1.json"
FAILURE_RECORD_PATH = SOURCE_ROOT / "acceptance_2023q4_failure_v1.json"
LOCK_PATH = SOURCE_ROOT / ".acceptance_2023q4.lock"

FIXED_REPORT_DATE = date(2023, 12, 31)
ENDPOINT = "https://datacenter-web.eastmoney.com/api/data/v1/get"
REPORT_NAME = "RPT_DMSK_FN_BALANCE"
RAW_COLUMNS = (
    "SECUCODE",
    "SECURITY_CODE",
    "REPORT_DATE",
    "NOTICE_DATE",
    "SHORT_LOAN",
    "SHORT_BOND_PAYABLE",
    "NONCURRENT_LIAB_1YEAR",
    "LONG_LOAN",
    "BOND_PAYABLE",
)
BORROWING_FIELDS = (
    "SHORT_LOAN",
    "SHORT_BOND_PAYABLE",
    "NONCURRENT_LIAB_1YEAR",
    "LONG_LOAN",
    "BOND_PAYABLE",
)
NORMALIZED_COLUMNS = (
    "instrument",
    "report_date",
    "announcement_date",
    "short_loan",
    "short_bond_payable",
    "noncurrent_liability_due_within_one_year",
    "long_loan",
    "bond_payable",
    "near_term_borrowing",
    "long_term_borrowing",
    "eastmoney_debt_maturity_resilience",
    "provider",
)
PAGE_SIZE = 500
MAXIMUM_PAGES = 20
MAXIMUM_ATTEMPTS_PER_PAGE = 4
RETRY_BACKOFF_SECONDS = (0.5, 1.0, 2.0, 4.0)
MINIMUM_SECONDS_BETWEEN_REQUESTS = 0.25
MINIMUM_ADVERTISED_ROWS = 1000
MINIMUM_VALID_HOLDING_NAMES = 50
MINIMUM_DISTINCT_VALUES = 20


class Campaign161Error(RuntimeError):
    """Fail closed on any divergence from the frozen Campaign161 contract."""


class Campaign161SchemaError(Campaign161Error):
    """A terminal provider schema or partition-integrity failure."""


@dataclass(frozen=True)
class AcceptancePaths:
    """All one-shot paths, injectable only to keep tests isolated."""

    source_root: Path
    accepted_root: Path
    intent: Path
    acceptance_record: Path
    failure_record: Path
    lock: Path

    @property
    def data(self) -> Path:
        return self.accepted_root / DATA_NAME

    @property
    def manifest(self) -> Path:
        return self.accepted_root / MANIFEST_NAME


DEFAULT_PATHS = AcceptancePaths(
    source_root=SOURCE_ROOT,
    accepted_root=ACCEPTED_ROOT,
    intent=INTENT_PATH,
    acceptance_record=ACCEPTANCE_RECORD_PATH,
    failure_record=FAILURE_RECORD_PATH,
    lock=LOCK_PATH,
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def _json_bytes(record: Mapping[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic_write_json(record: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_json_bytes(record))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _load_json(path: Path, error_code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Campaign161Error(error_code) from exc
    if not isinstance(value, dict):
        raise Campaign161Error(error_code)
    return value


def _require_bound_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected_sha256:
        raise Campaign161Error(f"binding_changed:{label}")


def load_contract() -> dict[str, Any]:
    """Load and semantically verify the pre-row contract and its local links."""

    _require_bound_file(CONTRACT_PATH, CONTRACT_SHA256, "contract")
    _require_bound_file(
        CONTRACT_BINDING_CORRECTION_PATH,
        CONTRACT_BINDING_CORRECTION_SHA256,
        "contract_binding_correction",
    )
    contract = _load_json(CONTRACT_PATH, "contract_unreadable")
    correction = _load_json(
        CONTRACT_BINDING_CORRECTION_PATH, "contract_binding_correction_unreadable"
    )
    corrected = correction.get("corrected_binding") or {}
    superseded = correction.get("supersedes_without_rewriting") or {}
    if not (
        correction.get("kind")
        == "a_share_eastmoney_debt_maturity_resilience_data_contract_binding_correction"
        and correction.get("status")
        == "effective_additive_binding_correction_frozen_before_eastmoney_financial_data_api_request"
        and superseded.get("path") == CONTRACT_RECORDED_PATH
        and superseded.get("sha256") == CONTRACT_SHA256
        and corrected.get("label") == "historical_walkforward_policy"
        and corrected.get("path")
        == "docs/a_share_three_day_historical_walkforward_research_policy_20260727.json"
        and corrected.get("recorded_sha256_in_v1")
        == "38426d6161b9bfed323c58caba18feca168b8c9d53e294951a8ba90c01a798bb"
        and corrected.get("effective_sha256")
        == "38426d6161b9bfed323c58caba18feca668b8c9d53e294951a8ba90c01a798bb"
        and correction.get("semantic_change") is False
        and (correction.get("research_boundary_at_correction") or {}).get(
            "eastmoney_financial_data_api_request_issued"
        )
        is False
    ):
        raise Campaign161Error("contract_binding_correction_semantics_changed")
    source = contract.get("source") or {}
    request = source.get("request_parameters") or {}
    schema = source.get("schema_policy") or {}
    factor = contract.get("factor") or {}
    normalized = contract.get("normalized_snapshot") or {}
    acceptance = contract.get("acceptance_protocol") or {}
    boundary = contract.get("research_boundary_at_freeze") or {}
    if not (
        contract.get("kind")
        == "a_share_eastmoney_debt_maturity_resilience_data_contract"
        and contract.get("status")
        == "frozen_before_eastmoney_financial_data_api_rows_candidate_values_comparators_prices_or_returns"
        and source.get("endpoint") == ENDPOINT
        and source.get("report_name") == REPORT_NAME
        and request.get("pageSize") == PAGE_SIZE
        and request.get("columns") == ",".join(RAW_COLUMNS)
        and tuple(schema.get("required_raw_keys") or ()) == RAW_COLUMNS
        and source.get("maximum_pages_per_partition") == MAXIMUM_PAGES
        and source.get("maximum_attempts_per_page") == MAXIMUM_ATTEMPTS_PER_PAGE
        and tuple(source.get("retry_backoff_seconds") or ()) == RETRY_BACKOFF_SECONDS
        and source.get("minimum_seconds_between_requests")
        == MINIMUM_SECONDS_BETWEEN_REQUESTS
        and source.get("credentials_required") == []
        and source.get(
            "authentication_cookie_proxy_retail_session_or_credential_allowed"
        )
        is False
        and factor.get("name") == "eastmoney_debt_maturity_resilience"
        and factor.get("direction") == "higher_is_better"
        and factor.get("formula") == "long_term / (near_term + long_term)"
        and tuple(normalized.get("columns") or ()) == NORMALIZED_COLUMNS
        and tuple(normalized.get("event_key") or ()) == ("instrument", "report_date")
        and acceptance.get("fixed_report_date") == FIXED_REPORT_DATE.isoformat()
        and acceptance.get("minimum_provider_advertised_rows")
        == MINIMUM_ADVERTISED_ROWS
        and acceptance.get("minimum_valid_main_chinext_names")
        == MINIMUM_VALID_HOLDING_NAMES
        and acceptance.get("minimum_distinct_factor_values") == MINIMUM_DISTINCT_VALUES
        and acceptance.get("one_shot") is True
        and boundary.get("eastmoney_financial_data_api_request_issued") is False
        and boundary.get("provider_response_row_or_column_value_read") is False
        and boundary.get("historical_daily_price_or_forward_return_value_read") is False
        and boundary.get("stress_2024_2025_opened") is False
        and boundary.get("provider_credential_presence_value_or_digest_read") is False
    ):
        raise Campaign161Error("contract_semantics_changed")

    for label, link in (contract.get("authoritative_inputs") or {}).items():
        if not isinstance(link, Mapping):
            raise Campaign161Error(f"contract_link_invalid:{label}")
        path_value = link.get("path")
        expected = link.get("sha256")
        if not isinstance(path_value, str) or not isinstance(expected, str):
            raise Campaign161Error(f"contract_link_invalid:{label}")
        effective_expected = (
            corrected["effective_sha256"]
            if label == corrected["label"] and path_value == corrected["path"]
            else expected
        )
        _require_bound_file(
            REPO_ROOT / path_value, effective_expected, f"contract:{label}"
        )
    return contract


def validate_implementation_freeze() -> dict[str, Any]:
    """Verify the non-circular freeze that binds this runner and its tests."""

    freeze = _load_json(
        IMPLEMENTATION_FREEZE_PATH, "implementation_freeze_unreadable_or_absent"
    )
    implementation = freeze.get("frozen_implementation") or {}
    bindings = freeze.get("frozen_local_bindings") or {}
    outputs = freeze.get("one_shot_outputs") or {}
    expected_bindings = {
        "numeric_eligibility_policy_v224": (
            NUMERIC_POLICY_PATH,
            relative(NUMERIC_POLICY_PATH),
        ),
        "manage_qlib_a_share_data_skill": (
            MANAGE_DATA_SKILL_PATH,
            str(MANAGE_DATA_SKILL_PATH),
        ),
        "holding_universe": (HOLDING_UNIVERSE_PATH, relative(HOLDING_UNIVERSE_PATH)),
        "candidate49_signal_ledger": (
            CANDIDATE49_SIGNAL_LEDGER_PATH,
            relative(CANDIDATE49_SIGNAL_LEDGER_PATH),
        ),
        "candidate49_execution_ledger": (
            CANDIDATE49_EXECUTION_LEDGER_PATH,
            relative(CANDIDATE49_EXECUTION_LEDGER_PATH),
        ),
    }
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign161_debt_maturity_implementation_freeze"
        and freeze.get("status")
        == "acceptance_runner_frozen_before_eastmoney_financial_data_api_request"
        and freeze.get("contract_sha256") == CONTRACT_SHA256
        and implementation.get("workflow_path") == relative(WORKFLOW_PATH)
        and implementation.get("workflow_sha256") == file_sha256(WORKFLOW_PATH)
        and implementation.get("test_path") == relative(TEST_PATH)
        and TEST_PATH.is_file()
        and implementation.get("test_sha256") == file_sha256(TEST_PATH)
        and outputs.get("accepted_root") == relative(ACCEPTED_ROOT)
        and outputs.get("data_path") == relative(ACCEPTED_ROOT / DATA_NAME)
        and outputs.get("manifest_path") == relative(ACCEPTED_ROOT / MANIFEST_NAME)
        and outputs.get("intent_path") == relative(INTENT_PATH)
        and outputs.get("acceptance_record_path") == relative(ACCEPTANCE_RECORD_PATH)
        and outputs.get("failure_record_path") == relative(FAILURE_RECORD_PATH)
        and outputs.get("one_shot") is True
    ):
        raise Campaign161Error("implementation_freeze_semantics_changed")
    for label, (bound_path, recorded_path) in expected_bindings.items():
        link = bindings.get(label) or {}
        if not (
            isinstance(link, Mapping)
            and link.get("path") == recorded_path
            and isinstance(link.get("sha256"), str)
            and bound_path.is_file()
            and link.get("sha256") == file_sha256(bound_path)
        ):
            raise Campaign161Error(f"implementation_binding_changed:{label}")
    return freeze


def _one_shot_checks(paths: AcceptancePaths) -> dict[str, bool]:
    return {
        "intent_absent": not paths.intent.exists(),
        "acceptance_record_absent": not paths.acceptance_record.exists(),
        "failure_record_absent": not paths.failure_record.exists(),
        "accepted_root_absent": not paths.accepted_root.exists(),
        "accepted_data_absent": not paths.data.exists(),
        "accepted_manifest_absent": not paths.manifest.exists(),
    }


def build_plan(paths: AcceptancePaths | None = None) -> dict[str, Any]:
    """Return a credential-free, network-free acceptance plan."""

    active_paths = paths or DEFAULT_PATHS
    checks: dict[str, bool] = {}
    blockers: list[str] = []
    try:
        load_contract()
        checks["contract_and_authoritative_links_bound"] = True
    except Campaign161Error as exc:
        checks["contract_and_authoritative_links_bound"] = False
        blockers.append(str(exc))
    try:
        validate_implementation_freeze()
        checks["implementation_freeze_and_local_bindings_bound"] = True
    except Campaign161Error as exc:
        checks["implementation_freeze_and_local_bindings_bound"] = False
        blockers.append(str(exc))
    checks.update(_one_shot_checks(active_paths))
    checks.update(
        {
            "fixed_report_date_exact": FIXED_REPORT_DATE.isoformat() == "2023-12-31",
            "fixed_projection_exact": RAW_COLUMNS
            == (
                "SECUCODE",
                "SECURITY_CODE",
                "REPORT_DATE",
                "NOTICE_DATE",
                "SHORT_LOAN",
                "SHORT_BOND_PAYABLE",
                "NONCURRENT_LIAB_1YEAR",
                "LONG_LOAN",
                "BOND_PAYABLE",
            ),
            "request_is_one_public_partition": True,
            "credentials_not_required": True,
            "price_or_return_access_forbidden": True,
            "candidate49_mutation_forbidden": True,
            "stress_2024_2025_open_forbidden": True,
        }
    )
    blockers.extend(name for name, passed in checks.items() if not passed)
    blockers = list(dict.fromkeys(blockers))
    ready = not blockers and all(checks.values())
    return {
        "campaign": 161,
        "command": "plan-acceptance",
        "ready": ready,
        "exit_code_if_executed": 0 if ready else 2,
        "fixed_report_date": FIXED_REPORT_DATE.isoformat(),
        "provider": "eastmoney_public_datacenter",
        "report_name": REPORT_NAME,
        "requested_columns": list(RAW_COLUMNS),
        "checks": checks,
        "blockers": blockers,
        "provider_request_issued": False,
        "provider_response_value_read": False,
        "credential_presence_value_or_digest_read": False,
        "price_or_return_value_read": False,
        "stress_2024_2025_opened": False,
        "candidate49_ledgers_changed": False,
    }


def _coerce_nonnegative_finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(parsed) or parsed < 0.0:
        return None
    return parsed


def compute_debt_maturity_resilience(
    values: Mapping[str, Any],
) -> tuple[float, float, float] | None:
    """Return ``(near, long, score)`` under the sole frozen formula."""

    parsed = [
        _coerce_nonnegative_finite(values.get(field)) for field in BORROWING_FIELDS
    ]
    if any(value is None for value in parsed):
        return None
    numbers = [float(value) for value in parsed if value is not None]
    try:
        near_term = math.fsum(numbers[:3])
        long_term = math.fsum(numbers[3:])
        total = math.fsum((near_term, long_term))
    except OverflowError:
        return None
    if not all(math.isfinite(value) for value in (near_term, long_term, total)):
        return None
    if total <= 0.0:
        return None
    score = long_term / total
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        return None
    return near_term, long_term, score


def _canonical_supported_instrument(security_code: Any, secucode: Any) -> str | None:
    if not isinstance(security_code, str):
        return None
    code = security_code.strip()
    if len(code) != 6 or not code.isascii() or not code.isdecimal():
        return None
    prefix = code[:3]
    exchange: str | None = None
    if prefix in {"600", "601", "603", "605"}:
        exchange = "SH"
    elif prefix in {"000", "001", "002", "003", "300", "301"}:
        exchange = "SZ"
    if exchange is None:
        return None
    if (
        not isinstance(secucode, str)
        or secucode.strip().upper() != f"{code}.{exchange}"
    ):
        raise Campaign161SchemaError("supported_security_identity_mismatch")
    return f"{exchange}{code}"


def _provider_date(value: Any, field: str, *, missing_allowed: bool) -> date | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        if missing_allowed:
            return None
        raise Campaign161SchemaError(f"missing_{field}")
    if isinstance(value, bool):
        raise Campaign161SchemaError(f"malformed_{field}")
    try:
        parsed = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise Campaign161SchemaError(f"malformed_{field}") from exc
    if pd.isna(parsed):
        if missing_allowed:
            return None
        raise Campaign161SchemaError(f"malformed_{field}")
    if parsed.tzinfo is not None:
        parsed = parsed.tz_convert(None)
    return parsed.date()


def canonicalize_rows(
    rows: Sequence[Mapping[str, Any]], report_date: date = FIXED_REPORT_DATE
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Validate projected rows and derive only the frozen normalized columns."""

    if not rows:
        raise Campaign161SchemaError("empty_partition")
    normalized: list[dict[str, Any]] = []
    seen_event_keys: set[tuple[str, date]] = set()
    unsupported = 0
    missing_announcement = 0
    invalid_components = 0
    nonpositive_total = 0
    for row in rows:
        if not isinstance(row, Mapping):
            raise Campaign161SchemaError("non_object_source_row")
        missing_keys = [field for field in RAW_COLUMNS if field not in row]
        if missing_keys:
            raise Campaign161SchemaError("missing_required_raw_key")
        observed_report_date = _provider_date(
            row["REPORT_DATE"], "report_date", missing_allowed=False
        )
        if observed_report_date != report_date:
            raise Campaign161SchemaError("inconsistent_report_date_partition")
        instrument = _canonical_supported_instrument(
            row["SECURITY_CODE"], row["SECUCODE"]
        )
        if instrument is None:
            unsupported += 1
            continue
        event_key = (instrument, observed_report_date)
        if event_key in seen_event_keys:
            raise Campaign161SchemaError("duplicate_instrument_report_period")
        seen_event_keys.add(event_key)
        announcement = _provider_date(
            row["NOTICE_DATE"], "notice_date", missing_allowed=True
        )
        if announcement is None:
            missing_announcement += 1
            continue
        formula = compute_debt_maturity_resilience(row)
        if formula is None:
            parsed = [
                _coerce_nonnegative_finite(row[field]) for field in BORROWING_FIELDS
            ]
            if (
                all(value is not None for value in parsed)
                and math.fsum(float(value) for value in parsed if value is not None)
                <= 0.0
            ):
                nonpositive_total += 1
            else:
                invalid_components += 1
            continue
        near_term, long_term, score = formula
        values = [
            float(row_value)
            for row_value in (
                _coerce_nonnegative_finite(row[field]) for field in BORROWING_FIELDS
            )
            if row_value is not None
        ]
        normalized.append(
            {
                "instrument": instrument,
                "report_date": report_date.isoformat(),
                "announcement_date": announcement.isoformat(),
                "short_loan": values[0],
                "short_bond_payable": values[1],
                "noncurrent_liability_due_within_one_year": values[2],
                "long_loan": values[3],
                "bond_payable": values[4],
                "near_term_borrowing": near_term,
                "long_term_borrowing": long_term,
                "eastmoney_debt_maturity_resilience": score,
                "provider": "eastmoney",
            }
        )
    frame = pd.DataFrame(normalized, columns=NORMALIZED_COLUMNS)
    frame = frame.sort_values(["report_date", "instrument"], kind="stable").reset_index(
        drop=True
    )
    if frame.duplicated(["instrument", "report_date"]).any():
        raise Campaign161SchemaError("duplicate_normalized_event_key")
    if not frame.empty:
        score = frame["eastmoney_debt_maturity_resilience"]
        recomputed = frame["long_term_borrowing"] / (
            frame["near_term_borrowing"] + frame["long_term_borrowing"]
        )
        if (
            not score.map(math.isfinite).all()
            or not score.between(0.0, 1.0).all()
            or not (score == recomputed).all()
        ):
            raise Campaign161SchemaError("normalized_formula_integrity_failure")
    return frame, {
        "input_rows": len(rows),
        "supported_unique_instrument_report_keys": len(seen_event_keys),
        "unsupported_board_or_malformed_identity_rows_excluded": unsupported,
        "missing_notice_date_rows_excluded": missing_announcement,
        "missing_nonfinite_or_negative_component_rows_excluded": invalid_components,
        "nonpositive_total_borrowing_rows_excluded": nonpositive_total,
        "valid_supported_rows_before_holding_universe": len(frame),
        "raw_response_persisted": False,
        "unused_transported_fields_persisted": False,
    }


def _request_parameters(report_date: date, page_number: int) -> dict[str, str]:
    return {
        "sortColumns": "NOTICE_DATE,SECURITY_CODE",
        "sortTypes": "-1,-1",
        "pageSize": str(PAGE_SIZE),
        "pageNumber": str(page_number),
        "reportName": REPORT_NAME,
        "columns": ",".join(RAW_COLUMNS),
        "filter": (
            '(SECURITY_TYPE_CODE in ("058001001","058001008"))'
            '(TRADE_MARKET_CODE!="069001017")'
            f"(REPORT_DATE='{report_date.isoformat()}')"
        ),
    }


def fetch_partition(
    report_date: date = FIXED_REPORT_DATE,
    *,
    session: Any | None = None,
    sleeper: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch one count-complete partition with bounded transport retries."""

    if report_date != FIXED_REPORT_DATE:
        raise Campaign161Error("report_date_not_frozen")
    if session is None:
        try:
            import requests
        except ImportError as exc:  # pragma: no cover - workspace dependency.
            raise Campaign161Error("requests_dependency_unavailable") from exc
        requester = requests
    else:
        requester = session

    last_request_at: float | None = None
    http_attempts = 0

    def fetch_page(page_number: int) -> dict[str, Any]:
        nonlocal http_attempts, last_request_at
        for attempt in range(MAXIMUM_ATTEMPTS_PER_PAGE):
            if last_request_at is not None:
                wait = MINIMUM_SECONDS_BETWEEN_REQUESTS - (
                    monotonic() - last_request_at
                )
                if wait > 0.0:
                    sleeper(wait)
            try:
                http_attempts += 1
                response = requester.get(
                    ENDPOINT,
                    params=_request_parameters(report_date, page_number),
                    timeout=30,
                )
                last_request_at = monotonic()
                if hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                payload = response.json()
            except Exception as exc:
                last_request_at = monotonic()
                if attempt + 1 >= MAXIMUM_ATTEMPTS_PER_PAGE:
                    raise Campaign161Error(
                        "eastmoney_transport_attempts_exhausted"
                    ) from exc
                sleeper(RETRY_BACKOFF_SECONDS[attempt])
                continue
            result = payload.get("result") if isinstance(payload, Mapping) else None
            if not isinstance(result, Mapping):
                raise Campaign161SchemaError("response_result_object_missing")
            data = result.get("data")
            if not isinstance(data, list):
                raise Campaign161SchemaError("response_data_list_missing")
            if any(not isinstance(row, Mapping) for row in data):
                raise Campaign161SchemaError("response_contains_non_object_row")
            return dict(result)
        raise AssertionError("unreachable")

    first = fetch_page(1)
    try:
        advertised_pages = int(first["pages"])
        advertised_rows = int(first["count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise Campaign161SchemaError("invalid_advertised_pages_or_count") from exc
    if not (1 <= advertised_pages <= MAXIMUM_PAGES) or advertised_rows <= 0:
        raise Campaign161SchemaError("advertised_pages_or_count_out_of_bounds")

    rows: list[dict[str, Any]] = []
    requested_pages: list[int] = []
    page_row_counts: list[int] = []
    for page_number in range(1, advertised_pages + 1):
        result = first if page_number == 1 else fetch_page(page_number)
        try:
            result_pages = int(result["pages"])
            result_count = int(result["count"])
        except (KeyError, TypeError, ValueError) as exc:
            raise Campaign161SchemaError("invalid_page_metadata") from exc
        if result_pages != advertised_pages or result_count != advertised_rows:
            raise Campaign161SchemaError("pagination_metadata_changed")
        page_rows = result["data"]
        if any(any(field not in row for field in RAW_COLUMNS) for row in page_rows):
            raise Campaign161SchemaError("missing_required_raw_key")
        rows.extend(dict(row) for row in page_rows)
        requested_pages.append(page_number)
        page_row_counts.append(len(page_rows))
    if requested_pages != list(range(1, advertised_pages + 1)):
        raise Campaign161SchemaError("page_schedule_not_count_complete")
    if len(rows) != advertised_rows:
        raise Campaign161SchemaError("received_row_count_mismatch")
    return rows, {
        "report_date": report_date.isoformat(),
        "advertised_pages": advertised_pages,
        "advertised_rows": advertised_rows,
        "requested_pages": requested_pages,
        "page_row_counts": page_row_counts,
        "received_rows": len(rows),
        "successful_page_count": len(requested_pages),
        "http_attempts": http_attempts,
        "maximum_attempts_per_page": MAXIMUM_ATTEMPTS_PER_PAGE,
        "provider_raw_response_persisted": False,
        "credential_access_performed": False,
    }


def active_holding_instruments(
    path: Path = HOLDING_UNIVERSE_PATH, on_date: date = FIXED_REPORT_DATE
) -> set[str]:
    """Load the bound point-in-time holding universe for one report date."""

    instruments: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise Campaign161Error("holding_universe_unreadable") from exc
    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue
        parts = raw_line.split("\t")
        if len(parts) != 3:
            raise Campaign161Error("holding_universe_schema_changed")
        instrument, start_text, end_text = parts
        try:
            start = date.fromisoformat(start_text)
            end = date.fromisoformat(end_text)
        except ValueError as exc:
            raise Campaign161Error("holding_universe_date_malformed") from exc
        if start > end:
            raise Campaign161Error("holding_universe_interval_invalid")
        if not (
            len(instrument) == 8
            and instrument[:2] in {"SH", "SZ"}
            and instrument[2:].isascii()
            and instrument[2:].isdecimal()
        ):
            raise Campaign161Error(
                f"holding_universe_instrument_malformed:{line_number}"
            )
        if start <= on_date <= end:
            instruments.add(instrument)
    if not instruments:
        raise Campaign161Error("holding_universe_empty_for_report_date")
    return instruments


def _frame_content_sha256(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _publish_snapshot(
    frame: pd.DataFrame,
    request_receipt: Mapping[str, Any],
    normalization: Mapping[str, Any],
    paths: AcceptancePaths,
) -> dict[str, Any]:
    paths.source_root.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(
        tempfile.mkdtemp(prefix=".acceptance_2023q4_", dir=paths.source_root)
    )
    try:
        data_path = temporary_root / DATA_NAME
        manifest_path = temporary_root / MANIFEST_NAME
        frame.to_parquet(data_path, index=False)
        data_file_sha256 = file_sha256(data_path)
        content_sha256 = _frame_content_sha256(frame)
        final_data_path = paths.accepted_root / DATA_NAME
        manifest = {
            "version": 1,
            "kind": "a_share_campaign161_debt_maturity_acceptance_snapshot",
            "status": "accepted_schema_formula_and_2023q4_coverage_pending_2019_2023_full_source",
            "created_at": datetime.now(UTC).isoformat(),
            "campaign": 161,
            "contract": {
                "path": relative(CONTRACT_PATH),
                "sha256": CONTRACT_SHA256,
            },
            "report_date": FIXED_REPORT_DATE.isoformat(),
            "request_receipt": dict(request_receipt),
            "normalization": dict(normalization),
            "file": {
                "path": relative(final_data_path),
                "rows": len(frame),
                "columns": list(frame.columns),
                "file_sha256": data_file_sha256,
                "content_sha256": content_sha256,
            },
            "provider_raw_response_persisted": False,
            "credential_presence_value_or_digest_read": False,
            "price_or_return_value_read": False,
            "stress_2024_2025_opened": False,
            "candidate49_ledgers_changed": False,
            "current_scoring_selection_sizing_positions_or_orders_performed": False,
        }
        atomic_write_json(manifest, manifest_path)
        if paths.accepted_root.exists():
            raise Campaign161Error("accepted_root_appeared_during_publication")
        os.replace(temporary_root, paths.accepted_root)
        return manifest
    finally:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)


def _record_link(path: Path) -> dict[str, Any]:
    return {"path": relative(path), "sha256": file_sha256(path)}


def run_acceptance(
    *,
    confirm_run: bool,
    paths: AcceptancePaths | None = None,
    session: Any | None = None,
    sleeper: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Consume the one-shot acceptance authorization and publish or reject."""

    if not confirm_run:
        raise Campaign161Error("confirm_run_required")
    active_paths = paths or DEFAULT_PATHS
    active_paths.source_root.mkdir(parents=True, exist_ok=True)
    with active_paths.lock.open("a+b") as lock_handle:
        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Campaign161Error("acceptance_lock_busy") from exc
        plan = build_plan(active_paths)
        if not plan["ready"]:
            raise Campaign161Error("acceptance_plan_not_ready")
        intent = {
            "version": 1,
            "kind": "a_share_campaign161_debt_maturity_acceptance_intent",
            "status": "one_shot_authorization_consumed_before_provider_request",
            "created_at": datetime.now(UTC).isoformat(),
            "campaign": 161,
            "fixed_report_date": FIXED_REPORT_DATE.isoformat(),
            "requested_columns": list(RAW_COLUMNS),
            "contract": _record_link(CONTRACT_PATH),
            "implementation_freeze": _record_link(IMPLEMENTATION_FREEZE_PATH),
            "workflow": _record_link(WORKFLOW_PATH),
            "workflow_test": _record_link(TEST_PATH),
            "provider_request_issued_at_intent_write": False,
            "credential_presence_value_or_digest_read": False,
            "price_or_return_value_read": False,
            "stress_2024_2025_opened": False,
        }
        atomic_write_json(intent, active_paths.intent)
        provider_request_attempted = False
        try:
            provider_request_attempted = True
            rows, request_receipt = fetch_partition(
                session=session, sleeper=sleeper, monotonic=monotonic
            )
            if request_receipt["advertised_rows"] < MINIMUM_ADVERTISED_ROWS:
                raise Campaign161Error("minimum_provider_advertised_rows_failed")
            normalized, normalization = canonicalize_rows(rows)
            holding = active_holding_instruments()
            accepted = normalized.loc[
                normalized["instrument"].isin(holding), list(NORMALIZED_COLUMNS)
            ].reset_index(drop=True)
            valid_names = int(accepted["instrument"].nunique())
            distinct_values = int(
                accepted["eastmoney_debt_maturity_resilience"].nunique(dropna=True)
            )
            normalization = {
                **normalization,
                "point_in_time_holding_names": len(holding),
                "valid_main_chinext_holding_names": valid_names,
                "distinct_factor_values": distinct_values,
                "published_rows": len(accepted),
            }
            if valid_names < MINIMUM_VALID_HOLDING_NAMES:
                raise Campaign161Error("minimum_valid_main_chinext_names_failed")
            if distinct_values < MINIMUM_DISTINCT_VALUES:
                raise Campaign161Error("minimum_distinct_factor_values_failed")
            if tuple(accepted.columns) != NORMALIZED_COLUMNS:
                raise Campaign161Error("published_projection_changed")
            manifest = _publish_snapshot(
                accepted, request_receipt, normalization, active_paths
            )
            record = {
                "version": 1,
                "kind": "a_share_campaign161_debt_maturity_acceptance_record",
                "status": "accepted_schema_formula_and_2023q4_coverage_pending_2019_2023_full_source",
                "created_at": datetime.now(UTC).isoformat(),
                "campaign": 161,
                "contract": _record_link(CONTRACT_PATH),
                "implementation_freeze": _record_link(IMPLEMENTATION_FREEZE_PATH),
                "intent": _record_link(active_paths.intent),
                "manifest": _record_link(active_paths.manifest),
                "accepted_frame": {
                    "path": relative(active_paths.data),
                    "file_sha256": file_sha256(active_paths.data),
                    "content_sha256": manifest["file"]["content_sha256"],
                    "rows": len(accepted),
                    "columns": list(accepted.columns),
                },
                "request_receipt": request_receipt,
                "observed_acceptance": normalization,
                "provider_raw_response_persisted": False,
                "unused_transported_fields_persisted": False,
                "credential_presence_value_or_digest_read": False,
                "price_or_return_value_read": False,
                "stress_2024_2025_opened": False,
                "candidate49_ledgers_changed": False,
                "current_scoring_selection_sizing_positions_or_orders_performed": False,
                "next_gate": "freeze_then_run_one_atomic_2019_2023_development_source_snapshot",
                "acceptance_retry_allowed": False,
            }
            atomic_write_json(record, active_paths.acceptance_record)
            return record
        except Exception as exc:
            error_code = (
                str(exc)
                if isinstance(exc, Campaign161Error)
                else "unexpected_acceptance_failure"
            )
            failure = {
                "version": 1,
                "kind": "a_share_campaign161_debt_maturity_acceptance_failure",
                "status": "terminal_source_rejection_before_development_source_comparators_prices_or_returns",
                "created_at": datetime.now(UTC).isoformat(),
                "campaign": 161,
                "fixed_report_date": FIXED_REPORT_DATE.isoformat(),
                "error_type": type(exc).__name__,
                "error_code": error_code,
                "provider_request_attempted": provider_request_attempted,
                "provider_raw_response_persisted": False,
                "unused_transported_fields_persisted": False,
                "credential_presence_value_or_digest_read": False,
                "price_or_return_value_read": False,
                "stress_2024_2025_opened": False,
                "candidate49_ledgers_changed": False,
                "partial_temporary_snapshot_deleted": True,
                "published_files": (
                    [relative(active_paths.data), relative(active_paths.manifest)]
                    if active_paths.accepted_root.exists()
                    else []
                ),
                "acceptance_retry_allowed": False,
            }
            if not active_paths.failure_record.exists():
                atomic_write_json(failure, active_paths.failure_record)
            raise Campaign161Error(error_code) from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "plan-acceptance", help="perform local-only one-shot readiness checks"
    )
    acceptance = subparsers.add_parser(
        "acceptance", help="consume the frozen one-shot public source request"
    )
    acceptance.add_argument("--confirm-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "plan-acceptance":
        plan = build_plan()
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0 if plan["ready"] else 2
    try:
        record = run_acceptance(confirm_run=bool(args.confirm_run))
    except Campaign161Error as exc:
        print(
            json.dumps(
                {
                    "campaign": 161,
                    "status": "acceptance_failed_closed",
                    "error_code": str(exc),
                    "provider_raw_response_printed": False,
                    "credential_value_printed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 3
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
