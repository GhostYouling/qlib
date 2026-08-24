#!/usr/bin/env python3
"""Plan or run Campaign265's frozen coverage-first no-return audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import stat
import sys
import tempfile
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign263_ordered_uniqueness as c263,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign265_convertible_premium as adapter,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_no_return_audit_protocol_20260824.json"
)
PROTOCOL_SHA256 = "16a9d7d49fd8b7b3d0211e4ec674c35300260c2671d1b0431e2c3c6dd5fb171f"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_no_return_audit_implementation_freeze_20260824.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_no_return_audit.py"
)
CALENDAR_PATH = REPO_ROOT / "data/qlib/cn_a_share/calendars/day.txt"
UNIVERSE_PATH = (
    REPO_ROOT / "data/qlib/cn_a_share/instruments/factor_main_chinext_star.txt"
)
SOURCE_MANIFEST_RELATIVE = Path(
    "data/metadata/rich_data/runs/campaign265_convertible_premium_acceptance_v1.json"
)
SOURCE_ROOT_RELATIVE = Path(
    "data/raw/a_share/rich/tushare/convertible_premium/campaign265_2019_2025_v1"
)
OUTPUT_PATH = (
    REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_265/"
    "no_return/campaign265_no_return_audit.json"
)

FIRST_SESSION = "2019-01-02"
LAST_SESSION = "2025-12-31"
EXPECTED_SESSION_COUNT = 1699
EXPECTED_REQUEST_COUNT = 1700
EXPECTED_REQUEST_SEQUENCE_SHA256 = (
    "3f9cccb3134b7e9e22f5d34fd8bc07f89e1d8047dd775d07c3257443a97b4c58"
)
EXPECTED_COMPARATOR_COUNT = 143
EXPECTED_COMPARATOR_ORDER_SHA256 = (
    "f4fbf3d578e2c80c29425716a30d60a3df01d67d04e37f1651236c4dff899588"
)
MINIMUM_MEDIAN_COVERAGE = 0.95
MINIMUM_P05_COVERAGE = 0.90
MINIMUM_P05_ELIGIBLE_NAMES = 50
MINIMUM_NONCONSTANT_SESSIONS = 200
MINIMUM_NON_OVERLAPPING_COHORTS = 200
MINIMUM_OBSERVED_YEARS = 5
MINIMUM_PAIRWISE_NAMES = 50
MINIMUM_PAIRWISE_SESSIONS = 100
MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION = 0.8
LAG_SESSIONS = 3
FILE_MODE = 0o600


class Campaign265NoReturnAuditError(RuntimeError):
    """Fail closed when a Campaign265 no-return invariant changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Campaign265NoReturnAuditError(f"JSON binding unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Campaign265NoReturnAuditError(f"JSON binding is not an object: {path}")
    return value


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign265NoReturnAuditError(f"{label} fingerprint changed")


def comparison_definitions() -> list[dict[str, str]]:
    definitions = [dict(item) for item in c263.comparison_definitions()]
    definitions.append(
        {"name": c263.candidate.FACTOR_NAME, "score_direction": "higher"}
    )
    if not (
        len(definitions) == EXPECTED_COMPARATOR_COUNT
        and c263.candidate._order_digest(definitions)  # noqa: SLF001
        == EXPECTED_COMPARATOR_ORDER_SHA256
    ):
        raise Campaign265NoReturnAuditError("numeric comparator order changed")
    return definitions


def load_protocol() -> dict[str, Any]:
    _require(PROTOCOL_PATH, PROTOCOL_SHA256, "no-return protocol")
    spec = load_json(PROTOCOL_PATH)
    source = spec.get("accepted_source_snapshot") or {}
    factor = spec.get("candidate_construction") or {}
    coverage = spec.get("coverage_first_gate") or {}
    uniqueness = spec.get("ordered_numeric_uniqueness") or {}
    output = spec.get("output_contract") or {}
    boundary = spec.get("research_boundary") or {}
    for label, binding in (spec.get("authoritative_inputs") or {}).items():
        target = REPO_ROOT / str(binding.get("path", ""))
        _require(target, str(binding.get("sha256", "")), label)
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign265_no_return_audit_protocol"
        and spec.get("status")
        == "frozen_before_accepted_source_candidate_comparator_price_or_return_values"
        and source.get("repository_manifest") == str(SOURCE_MANIFEST_RELATIVE)
        and source.get("final_root") == str(SOURCE_ROOT_RELATIVE)
        and source.get("accepted_session_count") == EXPECTED_SESSION_COUNT
        and source.get("exact_checkpoint_count") == EXPECTED_REQUEST_COUNT
        and factor.get("factor_name") == adapter.FACTOR_NAME
        and factor.get("score_direction") == adapter.FACTOR_DIRECTION
        and factor.get("lag_accepted_sessions") == LAG_SESSIONS
        and coverage.get("median_daily_coverage_minimum") == MINIMUM_MEDIAN_COVERAGE
        and coverage.get("p05_daily_coverage_minimum") == MINIMUM_P05_COVERAGE
        and coverage.get("p05_eligible_equity_count_minimum")
        == MINIMUM_P05_ELIGIBLE_NAMES
        and coverage.get("nonconstant_cross_sectional_sessions_minimum")
        == MINIMUM_NONCONSTANT_SESSIONS
        and coverage.get("non_overlapping_three_signal_session_cohorts_minimum")
        == MINIMUM_NON_OVERLAPPING_COHORTS
        and coverage.get("observed_calendar_years_minimum") == MINIMUM_OBSERVED_YEARS
        and uniqueness.get("comparator_count") == len(comparison_definitions())
        and uniqueness.get("comparator_order_sha256")
        == EXPECTED_COMPARATOR_ORDER_SHA256
        and uniqueness.get("minimum_pair_names_per_session") == MINIMUM_PAIRWISE_NAMES
        and uniqueness.get("minimum_pair_sessions_per_comparator")
        == MINIMUM_PAIRWISE_SESSIONS
        and uniqueness.get("strict_absolute_median_maximum")
        == MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
        and uniqueness.get("ordered_early_stop") is True
        and output.get("path") == relative(OUTPUT_PATH)
        and boundary.get("candidate_or_comparator_value_read_before_protocol") is False
        and boundary.get("historical_daily_price_or_forward_return_value_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign265NoReturnAuditError("no-return protocol semantics changed")
    return spec


def load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign265NoReturnAuditError("no-return implementation freeze absent")
    record = load_json(IMPLEMENTATION_FREEZE_PATH)
    frozen = record.get("frozen_implementation") or {}
    tests = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign265_no_return_audit_implementation_freeze"
        and record.get("status")
        == "source_coverage_ordered_143_early_stop_runner_frozen_before_source_values"
        and frozen.get("protocol_sha256") == PROTOCOL_SHA256
        and frozen.get("runner_sha256") == file_sha256(Path(__file__).resolve())
        and frozen.get("test_sha256") == file_sha256(TEST_PATH)
        and frozen.get("comparator_count") == EXPECTED_COMPARATOR_COUNT
        and frozen.get("comparator_order_sha256") == EXPECTED_COMPARATOR_ORDER_SHA256
        and frozen.get("output_path") == relative(OUTPUT_PATH)
        and tests.get("exit_code") == 0
        and int(tests.get("passed", 0)) >= 8
        and boundary.get("accepted_source_parquet_value_read_before_freeze") is False
        and boundary.get("candidate_or_comparator_value_read_before_freeze") is False
        and boundary.get("historical_daily_price_or_forward_return_value_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign265NoReturnAuditError(
            "no-return implementation freeze semantics changed"
        )
    return record


def accepted_sessions(calendar_path: Path = CALENDAR_PATH) -> list[str]:
    values = [
        line.strip() for line in calendar_path.read_text(encoding="utf-8").splitlines()
    ]
    if not values or any(not value for value in values):
        raise Campaign265NoReturnAuditError("accepted calendar is empty or malformed")
    parsed: list[str] = []
    for value in values:
        try:
            observed = date.fromisoformat(value)
        except ValueError as exc:
            raise Campaign265NoReturnAuditError(
                "calendar date is not strict ISO"
            ) from exc
        if observed.isoformat() != value:
            raise Campaign265NoReturnAuditError("calendar date is not strict ISO")
        parsed.append(value)
    if parsed != sorted(set(parsed)):
        raise Campaign265NoReturnAuditError("calendar is not increasing and unique")
    selected = [value for value in parsed if FIRST_SESSION <= value <= LAST_SESSION]
    if not (
        len(selected) == EXPECTED_SESSION_COUNT
        and selected[0] == FIRST_SESSION
        and selected[-1] == LAST_SESSION
    ):
        raise Campaign265NoReturnAuditError("accepted Campaign265 sessions changed")
    return selected


def factor_universe(path: Path = UNIVERSE_PATH) -> tuple[str, ...]:
    instruments: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.strip().split("\t")
        if len(fields) != 3:
            raise Campaign265NoReturnAuditError("factor universe row changed")
        instrument = fields[0].strip().upper()
        if (
            len(instrument) != 8
            or instrument[:2] not in {"SH", "SZ"}
            or not instrument[2:].isascii()
            or not instrument[2:].isdecimal()
        ):
            raise Campaign265NoReturnAuditError("factor universe identity changed")
        instruments.append(instrument)
    if len(instruments) != 5451 or len(instruments) != len(set(instruments)):
        raise Campaign265NoReturnAuditError("factor universe cardinality changed")
    return tuple(instruments)


def request_sequence(dates: Sequence[str]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = [
        {
            "api": "cb_basic",
            "fields": list(adapter.CB_BASIC_FIELDS),
            "ordinal": 1,
            "parameters": {},
        }
    ]
    requests.extend(
        {
            "api": "cb_daily",
            "fields": list(adapter.CB_DAILY_FIELDS),
            "ordinal": ordinal,
            "parameters": {"trade_date": session.replace("-", "")},
        }
        for ordinal, session in enumerate(dates, start=2)
    )
    return requests


def _real_directory_under(root: Path, target: Path) -> bool:
    root = Path(os.path.abspath(root))
    target = Path(os.path.abspath(target))
    try:
        relative_target = target.relative_to(root)
    except ValueError:
        return False
    cursor = root
    try:
        root_stat = cursor.lstat()
    except OSError:
        return False
    if not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode):
        return False
    for component in relative_target.parts:
        cursor /= component
        try:
            metadata = cursor.lstat()
        except OSError:
            return False
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            return False
    return True


def _regular_private_file(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return bool(
        stat.S_ISREG(metadata.st_mode)
        and not stat.S_ISLNK(metadata.st_mode)
        and metadata.st_nlink == 1
        and stat.S_IMODE(metadata.st_mode) == FILE_MODE
    )


def _source_checkpoint(
    source_root: Path, request: Mapping[str, Any]
) -> tuple[Path, tuple[str, ...]]:
    if request["api"] == "cb_basic":
        return source_root / "cb_basic.parquet", adapter.NORMALIZED_BASIC_FIELDS
    trade_date = str(request["parameters"]["trade_date"])
    return (
        source_root / "cb_daily" / f"{trade_date}.parquet",
        adapter.NORMALIZED_DAILY_FIELDS,
    )


def verify_accepted_source_snapshot(
    *,
    repo_root: Path,
    dates: Sequence[str],
    expected_request_count: int = EXPECTED_REQUEST_COUNT,
    expected_request_digest: str = EXPECTED_REQUEST_SEQUENCE_SHA256,
) -> dict[str, Any]:
    """Verify accepted source metadata and checkpoint bytes without Parquet decoding."""

    root = Path(os.path.abspath(repo_root))
    repository_manifest = root / SOURCE_MANIFEST_RELATIVE
    source_root = root / SOURCE_ROOT_RELATIVE
    if not _regular_private_file(repository_manifest):
        raise Campaign265NoReturnAuditError(
            "source_acceptance_manifest_absent_or_unsafe"
        )
    if not _real_directory_under(root, source_root):
        raise Campaign265NoReturnAuditError("source_final_root_absent_or_unsafe")
    repository = load_json(repository_manifest)
    internal_path = source_root / "source_manifest.json"
    requests = request_sequence(dates)
    if not (
        len(requests) == expected_request_count
        and canonical_json_sha256(requests) == expected_request_digest
        and repository.get("kind")
        == "a_share_three_day_walkforward_campaign265_source_acceptance_manifest"
        and repository.get("status")
        == "accepted_source_snapshot_pending_coverage_and_ordered_uniqueness"
        and repository.get("final_root") == str(SOURCE_ROOT_RELATIVE)
        and repository.get("internal_manifest")
        == str(SOURCE_ROOT_RELATIVE / "source_manifest.json")
        and repository.get("committed_request_count") == expected_request_count
        and repository.get("request_sequence_canonical_json_sha256")
        == expected_request_digest
        and repository.get("credential_value_or_digest_persisted") is False
        and repository.get("raw_provider_response_persisted") is False
        and repository.get("candidate_or_comparator_value_read") is False
        and repository.get("daily_price_or_forward_return_read") is False
        and repository.get("current_use_authorized") is False
        and _regular_private_file(internal_path)
        and repository.get("internal_manifest_sha256") == file_sha256(internal_path)
    ):
        raise Campaign265NoReturnAuditError("source_acceptance_manifest_invalid")
    internal = load_json(internal_path)
    sidecar_order: list[dict[str, Any]] = []
    for request in requests:
        checkpoint, schema = _source_checkpoint(source_root, request)
        sidecar_path = checkpoint.with_suffix(checkpoint.suffix + ".meta.json")
        if not (
            _regular_private_file(checkpoint) and _regular_private_file(sidecar_path)
        ):
            raise Campaign265NoReturnAuditError("source_checkpoint_absent_or_unsafe")
        sidecar = load_json(sidecar_path)
        relative_checkpoint = str(checkpoint.relative_to(source_root))
        counters = sidecar.get("counters") or {}
        if not (
            sidecar.get("kind")
            == "a_share_three_day_walkforward_campaign265_source_checkpoint"
            and sidecar.get("request_ordinal") == request["ordinal"]
            and sidecar.get("api") == request["api"]
            and sidecar.get("parameters") == request["parameters"]
            and sidecar.get("fields") == request["fields"]
            and sidecar.get("checkpoint_relative_path") == relative_checkpoint
            and sidecar.get("schema") == list(schema)
            and sidecar.get("checkpoint_sha256") == file_sha256(checkpoint)
            and len(str(sidecar.get("frame_sha256", ""))) == 64
            and int(counters.get("source_rows", 0)) > 0
            and int(counters.get("source_rows", 0)) < adapter.CB_DAILY_ROW_LIMIT
            and counters.get("network_or_credential_access_performed") is False
            and counters.get("forbidden_fields_read") is False
            and sidecar.get("raw_provider_response_persisted") is False
        ):
            raise Campaign265NoReturnAuditError("source_checkpoint_binding_invalid")
        sidecar_order.append(
            {
                "request_ordinal": sidecar["request_ordinal"],
                "checkpoint_relative_path": sidecar["checkpoint_relative_path"],
                "checkpoint_sha256": sidecar["checkpoint_sha256"],
                "frame_sha256": sidecar["frame_sha256"],
            }
        )
    if not (
        internal.get("kind")
        == "a_share_three_day_walkforward_campaign265_source_manifest"
        and internal.get("status")
        == "complete_source_snapshot_pending_coverage_and_uniqueness"
        and internal.get("provider") == "Tushare Pro"
        and internal.get("request_sequence_canonical_json_sha256")
        == expected_request_digest
        and internal.get("committed_request_count") == expected_request_count
        and internal.get("checkpoint_order_sha256")
        == canonical_json_sha256(sidecar_order)
        and internal.get("raw_provider_response_persisted") is False
        and internal.get("daily_price_or_forward_return_read") is False
    ):
        raise Campaign265NoReturnAuditError("source_internal_manifest_invalid")
    return {
        "repository_manifest_path": str(repository_manifest),
        "repository_manifest_sha256": file_sha256(repository_manifest),
        "final_root": str(source_root),
        "internal_manifest_sha256": file_sha256(internal_path),
        "request_sequence_canonical_json_sha256": expected_request_digest,
        "checkpoint_count": len(sidecar_order),
        "checkpoint_byte_hashes_verified": len(sidecar_order),
        "parquet_rows_decoded": 0,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
    }


def validate_static_bindings() -> dict[str, Any]:
    load_protocol()
    adapter.load_source_contract()
    freeze = load_implementation_freeze()
    comparator = c263.validate_static_bindings()
    sessions = accepted_sessions()
    universe = factor_universe()
    requests = request_sequence(sessions)
    if not (
        len(requests) == EXPECTED_REQUEST_COUNT
        and canonical_json_sha256(requests) == EXPECTED_REQUEST_SEQUENCE_SHA256
        and len(comparison_definitions()) == EXPECTED_COMPARATOR_COUNT
    ):
        raise Campaign265NoReturnAuditError("static no-return bindings changed")
    return {
        "protocol_sha256": PROTOCOL_SHA256,
        "implementation_freeze_sha256": file_sha256(IMPLEMENTATION_FREEZE_PATH),
        "source_contract_sha256": adapter.SOURCE_CONTRACT_SHA256,
        "calendar_sha256": file_sha256(CALENDAR_PATH),
        "accepted_session_count": len(sessions),
        "factor_universe_sha256": file_sha256(UNIVERSE_PATH),
        "factor_universe_instrument_count": len(universe),
        "request_sequence_canonical_json_sha256": EXPECTED_REQUEST_SEQUENCE_SHA256,
        "comparator_count": EXPECTED_COMPARATOR_COUNT,
        "comparator_order_sha256": EXPECTED_COMPARATOR_ORDER_SHA256,
        "comparator_static_bindings": comparator,
        "freeze_status": freeze["status"],
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
    }


def build_plan(
    *, repo_root: Path = REPO_ROOT, output_path: Path = OUTPUT_PATH
) -> dict[str, Any]:
    static = validate_static_bindings()
    sessions = accepted_sessions()
    blockers: list[str] = []
    receipt: dict[str, Any] | None = None
    try:
        receipt = verify_accepted_source_snapshot(repo_root=repo_root, dates=sessions)
    except Campaign265NoReturnAuditError as exc:
        blockers.append(str(exc))
    target = output_path.expanduser().resolve()
    if os.path.lexists(target):
        blockers.append("no_return_audit_output_already_exists")
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_no_return_audit_plan",
        "ready": not blockers,
        "blockers": blockers,
        "factor": adapter.FACTOR_NAME,
        "direction": adapter.FACTOR_DIRECTION,
        "output_path": str(target),
        "static_bindings": static,
        "accepted_source_snapshot": receipt,
        "coverage_first": True,
        "ordered_early_stop_comparator_count": EXPECTED_COMPARATOR_COUNT,
        "source_parquet_rows_decoded": 0,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_client_imported_or_created": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "filesystem_write_performed": False,
    }


def _strict_date_value(value: Any, field: str) -> date:
    try:
        observed = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise Campaign265NoReturnAuditError(f"normalized {field} is invalid") from exc
    if pd.isna(observed) or observed.time() != datetime.min.time():
        raise Campaign265NoReturnAuditError(f"normalized {field} is invalid")
    return observed.date()


def _optional_date_value(value: Any, field: str) -> date | None:
    if value is None or pd.isna(value):
        return None
    return _strict_date_value(value, field)


def load_normalized_basic(path: Path) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if tuple(frame.columns) != adapter.NORMALIZED_BASIC_FIELDS or not (
        0 < len(frame) < adapter.CB_DAILY_ROW_LIMIT
    ):
        raise Campaign265NoReturnAuditError("normalized cb_basic schema changed")
    work = frame.copy()
    if work["bond_code"].astype(str).duplicated().any():
        raise Campaign265NoReturnAuditError("normalized cb_basic identity duplicated")
    rows: list[dict[str, Any]] = []
    for row in work.itertuples(index=False):
        bond_code, _, suffix = adapter._normalize_tushare_code(  # noqa: SLF001
            row.bond_code, "bond_code"
        )
        bond_type = (
            None
            if row.bond_type is None or pd.isna(row.bond_type)
            else str(row.bond_type)
        )
        exchange = str(row.exchange)
        list_date = _optional_date_value(row.list_date, "list_date")
        delist_date = _optional_date_value(row.delist_date, "delist_date")
        instrument = (
            None
            if row.instrument is None or pd.isna(row.instrument)
            else str(row.instrument).upper()
        )
        if (
            exchange not in {"SH", "SZ"}
            or exchange != suffix
            or (
                list_date is not None
                and delist_date is not None
                and delist_date < list_date
            )
            or (bond_type == "CB" and instrument is None)
            or (bond_type != "CB" and instrument is not None)
        ):
            raise Campaign265NoReturnAuditError("normalized cb_basic semantics changed")
        if (
            instrument is not None
            and adapter._canonical_equity(  # noqa: SLF001
                f"{instrument[2:]}.{instrument[:2]}"
            )
            != instrument
        ):
            raise Campaign265NoReturnAuditError("normalized equity identity changed")
        rows.append(
            {
                "bond_code": bond_code,
                "bond_type": bond_type,
                "instrument": instrument,
                "list_date": list_date,
                "delist_date": delist_date,
                "exchange": exchange,
            }
        )
    return (
        pd.DataFrame(rows, columns=adapter.NORMALIZED_BASIC_FIELDS)
        .sort_values("bond_code", kind="stable")
        .reset_index(drop=True)
    )


def load_normalized_daily(
    path: Path, *, session: str, basic_bonds: frozenset[str]
) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if tuple(frame.columns) != adapter.NORMALIZED_DAILY_FIELDS or not (
        0 < len(frame) < adapter.CB_DAILY_ROW_LIMIT
    ):
        raise Campaign265NoReturnAuditError("normalized cb_daily schema changed")
    work = frame.copy()
    work["bond_code"] = work["bond_code"].astype(str)
    if work["bond_code"].duplicated().any() or not set(work["bond_code"]).issubset(
        basic_bonds
    ):
        raise Campaign265NoReturnAuditError("normalized cb_daily identity changed")
    expected = date.fromisoformat(session)
    observed = work["trade_date"].map(
        lambda value: _strict_date_value(value, "trade_date")
    )
    if not observed.eq(expected).all():
        raise Campaign265NoReturnAuditError("normalized cb_daily session changed")
    work["trade_date"] = observed
    for column in ("amount", "cb_over_rate"):
        if work[column].map(lambda value: isinstance(value, (bool, np.bool_))).any():
            raise Campaign265NoReturnAuditError("normalized cb_daily boolean numeric")
        work[column] = pd.to_numeric(work[column], errors="coerce").astype(float)
    return work.sort_values("bond_code", kind="stable").reset_index(drop=True)


def _active(record: Any, session: date) -> bool:
    return bool(
        record.list_date is not None
        and record.list_date <= session
        and (record.delist_date is None or session <= record.delist_date)
    )


def factor_values_on_session(
    basic: pd.DataFrame,
    lag_daily: pd.DataFrame,
    signal_daily: pd.DataFrame,
    *,
    lag_session: str,
    signal_session: str,
    universe: frozenset[str],
) -> tuple[list[tuple[str, float]], dict[str, int]]:
    lag_date = date.fromisoformat(lag_session)
    signal_date = date.fromisoformat(signal_session)
    lag_index = lag_daily.set_index("bond_code", verify_integrity=True)
    signal_index = signal_daily.set_index("bond_code", verify_integrity=True)
    active: dict[str, list[Any]] = {}
    for record in basic.itertuples(index=False):
        if (
            record.bond_type == "CB"
            and record.instrument in universe
            and _active(record, signal_date)
        ):
            active.setdefault(record.instrument, []).append(record)
    finite_values: list[tuple[str, float]] = []
    eligible_bonds = 0
    for instrument in sorted(active):
        values: list[float] = []
        for record in active[instrument]:
            if (
                not _active(record, lag_date)
                or record.bond_code not in lag_index.index
                or record.bond_code not in signal_index.index
            ):
                continue
            lag = lag_index.loc[record.bond_code]
            signal = signal_index.loc[record.bond_code]
            endpoints = np.asarray(
                [
                    lag["amount"],
                    lag["cb_over_rate"],
                    signal["amount"],
                    signal["cb_over_rate"],
                ],
                dtype=np.float64,
            )
            if (
                not np.isfinite(endpoints).all()
                or endpoints[0] <= 0.0
                or endpoints[2] <= 0.0
            ):
                continue
            value = float(endpoints[1] - endpoints[3])
            if math.isfinite(value):
                values.append(value)
        eligible_bonds += len(values)
        if values:
            finite_values.append((instrument, float(np.median(np.asarray(values)))))
    return finite_values, {
        "denominator_equity_count": len(active),
        "eligible_equity_count": len(finite_values),
        "active_cb_count": sum(len(records) for records in active.values()),
        "eligible_cb_count": eligible_bonds,
    }


def _daily_aggregate_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    material = [
        {
            "signal_session": str(row["signal_session"]),
            "denominator_equity_count": int(row["denominator_equity_count"]),
            "eligible_equity_count": int(row["eligible_equity_count"]),
            "coverage_hex": float(row["coverage"]).hex(),
            "distinct_candidate_values": int(row["distinct_candidate_values"]),
        }
        for row in rows
    ]
    return canonical_json_sha256(material)


def coverage_and_variation(
    daily: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not daily:
        raise Campaign265NoReturnAuditError("candidate daily coverage is empty")
    aggregate: list[dict[str, Any]] = []
    for row in daily:
        denominator = int(row["denominator_equity_count"])
        values = np.asarray(row["finite_values"], dtype=np.float64)
        if (
            denominator <= 0
            or len(values) > denominator
            or not np.isfinite(values).all()
        ):
            raise Campaign265NoReturnAuditError("candidate daily coverage is invalid")
        aggregate.append(
            {
                "signal_session": str(row["signal_session"]),
                "denominator_equity_count": denominator,
                "eligible_equity_count": len(values),
                "coverage": len(values) / denominator,
                "distinct_candidate_values": int(np.unique(values).size),
            }
        )
    denominators = np.asarray(
        [row["denominator_equity_count"] for row in aggregate], dtype=np.int64
    )
    numerators = np.asarray(
        [row["eligible_equity_count"] for row in aggregate], dtype=np.int64
    )
    ratios = np.asarray([row["coverage"] for row in aggregate], dtype=np.float64)
    distinct = np.asarray(
        [row["distinct_candidate_values"] for row in aggregate], dtype=np.int64
    )
    cohort_indices = np.arange(0, max(len(aggregate) - LAG_SESSIONS, 0), LAG_SESSIONS)
    cohort_indices = cohort_indices[
        numerators[cohort_indices] >= MINIMUM_P05_ELIGIBLE_NAMES
    ]
    cohort_years = sorted(
        {int(str(aggregate[index]["signal_session"])[:4]) for index in cohort_indices}
    )
    variation_indices = np.flatnonzero(distinct >= 2)
    variation_years = sorted(
        {
            int(str(aggregate[index]["signal_session"])[:4])
            for index in variation_indices
        }
    )
    median = float(np.median(ratios))
    p05 = float(np.quantile(ratios, 0.05))
    names_p05 = float(np.quantile(numerators, 0.05))
    passed = bool(
        median >= MINIMUM_MEDIAN_COVERAGE
        and p05 >= MINIMUM_P05_COVERAGE
        and names_p05 >= MINIMUM_P05_ELIGIBLE_NAMES
        and len(variation_indices) >= MINIMUM_NONCONSTANT_SESSIONS
        and len(cohort_indices) >= MINIMUM_NON_OVERLAPPING_COHORTS
        and len(cohort_years) >= MINIMUM_OBSERVED_YEARS
    )
    return {
        "signal_session_count": len(aggregate),
        "denominator_equity_rows": int(denominators.sum()),
        "candidate_eligible_rows": int(numerators.sum()),
        "median_daily_coverage": median,
        "p05_daily_coverage": p05,
        "eligible_names_minimum": int(numerators.min()),
        "eligible_names_p05": names_p05,
        "eligible_names_median": float(np.median(numerators)),
        "nonconstant_cross_sectional_sessions": len(variation_indices),
        "observed_nonconstant_cross_sectional_years": variation_years,
        "potential_non_overlapping_three_signal_session_cohorts": len(cohort_indices),
        "observed_cohort_years": cohort_years,
        "maximum_distinct_candidate_values_in_one_session": int(distinct.max()),
        "gate_passed_before_comparator_values": passed,
        "daily_aggregate_frame_sha256": _daily_aggregate_sha256(aggregate),
        "gate": {
            "median_daily_coverage_minimum": MINIMUM_MEDIAN_COVERAGE,
            "p05_daily_coverage_minimum": MINIMUM_P05_COVERAGE,
            "p05_eligible_equity_count_minimum": MINIMUM_P05_ELIGIBLE_NAMES,
            "nonconstant_cross_sectional_sessions_minimum": MINIMUM_NONCONSTANT_SESSIONS,
            "non_overlapping_three_signal_session_cohorts_minimum": MINIMUM_NON_OVERLAPPING_COHORTS,
            "observed_calendar_years_minimum": MINIMUM_OBSERVED_YEARS,
        },
    }


def build_candidate_panel(
    *, source_root: Path, sessions: Sequence[str], universe: Sequence[str]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    basic = load_normalized_basic(source_root / "cb_basic.parquet")
    basic_bonds = frozenset(str(value) for value in basic["bond_code"])
    accepted_universe = frozenset(universe)
    daily_window: deque[tuple[str, pd.DataFrame]] = deque(maxlen=LAG_SESSIONS + 1)
    candidate_rows: list[dict[str, Any]] = []
    daily_coverage: list[dict[str, Any]] = []
    decoded_daily_rows = 0
    for session in sessions:
        daily = load_normalized_daily(
            source_root / "cb_daily" / f"{session.replace('-', '')}.parquet",
            session=session,
            basic_bonds=basic_bonds,
        )
        decoded_daily_rows += len(daily)
        daily_window.append((session, daily))
        if len(daily_window) <= LAG_SESSIONS:
            continue
        lag_session, lag_daily = daily_window[0]
        values, stats = factor_values_on_session(
            basic,
            lag_daily,
            daily,
            lag_session=lag_session,
            signal_session=session,
            universe=accepted_universe,
        )
        daily_coverage.append(
            {
                "signal_session": session,
                "denominator_equity_count": stats["denominator_equity_count"],
                "finite_values": [value for _, value in values],
            }
        )
        candidate_rows.extend(
            {"trade_date": session, "symbol": instrument, adapter.FACTOR_NAME: value}
            for instrument, value in values
        )
    coverage = coverage_and_variation(daily_coverage)
    frame = pd.DataFrame(
        candidate_rows, columns=("trade_date", "symbol", adapter.FACTOR_NAME)
    )
    if frame.empty or frame.duplicated(["trade_date", "symbol"]).any():
        raise Campaign265NoReturnAuditError("candidate panel is empty or duplicated")
    values = frame[adapter.FACTOR_NAME].to_numpy(dtype=np.float64)
    if not np.isfinite(values).all():
        raise Campaign265NoReturnAuditError("candidate panel contains nonfinite values")
    return frame, {
        "normalized_cb_basic_rows_decoded": len(basic),
        "normalized_cb_daily_rows_decoded": decoded_daily_rows,
        "candidate_eligible_rows": len(frame),
        "candidate_value_order_independent_sha256": canonical_json_sha256(
            sorted(
                [
                    [
                        str(row.trade_date),
                        str(row.symbol),
                        float(row.factor_value).hex(),
                    ]
                    for row in frame.rename(
                        columns={adapter.FACTOR_NAME: "factor_value"}
                    ).itertuples(index=False)
                ]
            )
        ),
        "coverage_and_variation": coverage,
    }


def candidate_arrays(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    keys = c263.base.design.compact_stock_day_keys(frame["trade_date"], frame["symbol"])
    values = frame[adapter.FACTOR_NAME].to_numpy(dtype=np.float64)
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    values = values[order]
    if len(np.unique(keys)) != len(keys) or not np.isfinite(values).all():
        raise Campaign265NoReturnAuditError("candidate compact keys changed")
    return keys, values


def _aligned_values(
    *, source_keys: np.ndarray, source_values: np.ndarray, target_keys: np.ndarray
) -> tuple[np.ndarray, int]:
    order = np.argsort(source_keys, kind="stable")
    source_keys = np.asarray(source_keys, dtype=np.int64)[order]
    source_values = np.asarray(source_values, dtype=np.float64)[order]
    if len(np.unique(source_keys)) != len(source_keys):
        raise Campaign265NoReturnAuditError("comparator source keys duplicated")
    positions = np.searchsorted(source_keys, target_keys)
    matched = positions < len(source_keys)
    matched[matched] &= source_keys[positions[matched]] == target_keys[matched]
    aligned = np.full(len(target_keys), np.nan, dtype=np.float64)
    aligned[matched] = source_values[positions[matched]]
    return aligned, int(matched.sum())


def _comparison_from_aligned(
    *,
    definition: dict[str, str],
    candidate_keys_value: np.ndarray,
    candidate_values: np.ndarray,
    comparison_values: np.ndarray,
) -> dict[str, Any]:
    rows = c263.base.base.daily_rank_rows(
        candidate_keys_value,
        candidate_values,
        comparison_values,
        minimum_names=MINIMUM_PAIRWISE_NAMES,
    )
    return c263.base.base.comparison_result(definition=definition, daily_rows=rows)


def _design_comparator(
    *,
    definition: dict[str, str],
    candidate_keys_value: np.ndarray,
    candidate_values: np.ndarray,
    manifest: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    name = definition["name"]
    candidate_days = candidate_keys_value // 4_000_000
    candidate_years = pd.DatetimeIndex(
        candidate_days.astype("datetime64[D]")
    ).year.to_numpy()
    daily_rows: list[list[Any]] = []
    matched_total = 0
    source_rows = 0
    for record in manifest["files"]:
        path = c263.base.resolve_design_partition(record)
        c263.base.require_file(
            path, str(record["sha256"]), f"design partition {record['year']}"
        )
        frame = pd.read_parquet(path, columns=["stock_day_key", name])
        source_keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        source_values = pd.to_numeric(frame[name], errors="coerce").to_numpy(
            dtype=np.float64
        )
        finite = source_values[np.isfinite(source_values)]
        if finite.size and ((finite <= 0.0).any() or (finite > 1.0).any()):
            raise Campaign265NoReturnAuditError(
                f"design comparator range changed: {name}"
            )
        target_indices = np.flatnonzero(candidate_years == int(record["year"]))
        aligned, matched = _aligned_values(
            source_keys=source_keys,
            source_values=source_values,
            target_keys=candidate_keys_value[target_indices],
        )
        daily_rows.extend(
            c263.base.base.daily_rank_rows(
                candidate_keys_value[target_indices],
                candidate_values[target_indices],
                aligned,
                minimum_names=MINIMUM_PAIRWISE_NAMES,
            )
        )
        matched_total += matched
        source_rows += len(frame)
        del frame, source_keys, source_values, aligned
        gc.collect()
    result = c263.base.base.comparison_result(
        definition=definition, daily_rows=daily_rows
    )
    return result, {
        "source": "campaign132_numeric140_design",
        "source_rows_read": source_rows,
        "matched_candidate_rows": matched_total,
    }


def _snapshot_comparator(
    *,
    frame: pd.DataFrame,
    factor: str,
    definition: dict[str, str],
    candidate_keys_value: np.ndarray,
    candidate_values: np.ndarray,
    minimum: float | None,
    maximum: float | None,
    source: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    eligible_column = f"{factor}_eligible"
    required = {"trade_date", "symbol", factor, eligible_column}
    if not required.issubset(frame.columns):
        raise Campaign265NoReturnAuditError(
            f"snapshot comparator schema changed: {factor}"
        )
    eligible = frame[eligible_column].astype("boolean").fillna(False).astype(bool)
    numeric = pd.to_numeric(frame[factor], errors="coerce")
    selected = frame.loc[eligible & numeric.notna(), ["trade_date", "symbol"]].copy()
    selected[factor] = numeric.loc[eligible & numeric.notna()].to_numpy()
    source_values = selected[factor].to_numpy(dtype=np.float64)
    if (
        not np.isfinite(source_values).all()
        or (minimum is not None and (source_values < minimum).any())
        or (maximum is not None and (source_values > maximum).any())
    ):
        raise Campaign265NoReturnAuditError(
            f"snapshot comparator values changed: {factor}"
        )
    source_keys = c263.base.design.compact_stock_day_keys(
        selected["trade_date"], selected["symbol"]
    )
    aligned, matched = _aligned_values(
        source_keys=source_keys,
        source_values=source_values,
        target_keys=candidate_keys_value,
    )
    result = _comparison_from_aligned(
        definition=definition,
        candidate_keys_value=candidate_keys_value,
        candidate_values=candidate_values,
        comparison_values=aligned,
    )
    return result, {
        "source": source,
        "eligible_source_rows": len(selected),
        "matched_candidate_rows": matched,
        "unmatched_candidate_rows": len(candidate_keys_value) - matched,
    }


ComparatorLoader = Callable[
    [int, dict[str, str]], tuple[dict[str, Any], dict[str, Any]]
]


def audit_ordered_comparators(
    definitions: Sequence[dict[str, str]], loader: ComparatorLoader
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int | None]:
    results: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    failed_ordinal: int | None = None
    for ordinal, definition in enumerate(definitions, start=1):
        result, receipt = loader(ordinal, dict(definition))
        if result.get("comparison_factor") != definition["name"]:
            raise Campaign265NoReturnAuditError("comparator loader order changed")
        results.append(result)
        receipts.append({"ordinal": ordinal, **receipt})
        if result.get("gate_passed") is not True:
            failed_ordinal = ordinal
            break
    return results, receipts, failed_ordinal


def real_comparator_loader(
    *, candidate_keys_value: np.ndarray, candidate_values: np.ndarray
) -> ComparatorLoader:
    design_manifest = c263.base.validate_design_manifest_metadata()

    def load(
        ordinal: int, definition: dict[str, str]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if ordinal <= 140:
            return _design_comparator(
                definition=definition,
                candidate_keys_value=candidate_keys_value,
                candidate_values=candidate_values,
                manifest=design_manifest,
            )
        if ordinal == 141:
            frame = c263.base.c136_coverage.load_candidate_frame()
            try:
                return _snapshot_comparator(
                    frame=frame,
                    factor=c263.base.c136_formula.FACTOR_NAME,
                    definition=definition,
                    candidate_keys_value=candidate_keys_value,
                    candidate_values=candidate_values,
                    minimum=0.0,
                    maximum=None,
                    source="campaign136_verified_snapshot",
                )
            finally:
                del frame
                gc.collect()
        if ordinal == 142:
            load_c146 = c263.base.frozen_coverage._generated[  # noqa: SLF001
                "_load_candidate_frame"
            ]
            frame = load_c146(c263.base.recovery.EXPECTED_ELIGIBLE_ROWS)
            try:
                return _snapshot_comparator(
                    frame=frame,
                    factor=c263.c146.FACTOR_NAME,
                    definition=definition,
                    candidate_keys_value=candidate_keys_value,
                    candidate_values=candidate_values,
                    minimum=-1.0,
                    maximum=1.0,
                    source="campaign146_recovery_verified_snapshot",
                )
            finally:
                del frame
                gc.collect()
        if ordinal == 143:
            load_c263 = c263.coverage._generated[
                "_load_candidate_frame"
            ]  # noqa: SLF001
            frame = load_c263(c263.candidate.EXPECTED_ROWS)
            try:
                return _snapshot_comparator(
                    frame=frame,
                    factor=c263.candidate.FACTOR_NAME,
                    definition=definition,
                    candidate_keys_value=candidate_keys_value,
                    candidate_values=candidate_values,
                    minimum=0.0,
                    maximum=1.0,
                    source="campaign263_verified_snapshot",
                )
            finally:
                del frame
                gc.collect()
        raise Campaign265NoReturnAuditError("comparator ordinal outside frozen order")

    return load


def atomic_exclusive_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, FILE_MODE)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise Campaign265NoReturnAuditError(
                "no-return audit output already exists"
            ) from exc
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def run_no_return_audit(*, confirm: bool) -> Path:
    if not confirm:
        raise Campaign265NoReturnAuditError(
            "no-return audit requires --confirm-no-return-audit"
        )
    plan = build_plan()
    if plan["ready"] is not True:
        raise Campaign265NoReturnAuditError("no-return audit plan is not ready")
    sessions = accepted_sessions()
    universe = factor_universe()
    source_root = REPO_ROOT / SOURCE_ROOT_RELATIVE
    candidate_frame, candidate_receipt = build_candidate_panel(
        source_root=source_root,
        sessions=sessions,
        universe=universe,
    )
    coverage = candidate_receipt["coverage_and_variation"]
    definitions = comparison_definitions()
    results: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    failed_ordinal: int | None = None
    if coverage["gate_passed_before_comparator_values"] is True:
        keys, values = candidate_arrays(candidate_frame)
        loader = real_comparator_loader(
            candidate_keys_value=keys, candidate_values=values
        )
        results, receipts, failed_ordinal = audit_ordered_comparators(
            definitions, loader
        )
        del keys, values
    comparator_count = len(results)
    all_passed = bool(
        coverage["gate_passed_before_comparator_values"] is True
        and comparator_count == EXPECTED_COMPARATOR_COUNT
        and failed_ordinal is None
        and all(item.get("gate_passed") is True for item in results)
    )
    if coverage["gate_passed_before_comparator_values"] is not True:
        status = "coverage_failed_terminal_before_comparator_values"
    elif all_passed:
        status = "all_143_no_return_gates_passed_ready_to_freeze_one_development_trial"
    else:
        status = "ordered_uniqueness_failed_terminal_before_returns"
    result = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_no_return_audit",
        "status": status,
        "recorded_at": datetime.now(UTC).isoformat(),
        "factor": adapter.FACTOR_NAME,
        "direction": adapter.FACTOR_DIRECTION,
        "static_bindings": plan["static_bindings"],
        "source_snapshot_verification": plan["accepted_source_snapshot"],
        "candidate_snapshot_receipt": {
            key: value
            for key, value in candidate_receipt.items()
            if key != "coverage_and_variation"
        },
        "coverage_and_variation": coverage,
        "comparison_order_sha256": EXPECTED_COMPARATOR_ORDER_SHA256,
        "ordered_comparisons": results,
        "ordered_comparator_receipts": receipts,
        "numeric_comparator_count_read": comparator_count,
        "first_failed_comparator_ordinal": failed_ordinal,
        "later_comparator_values_left_closed": (
            EXPECTED_COMPARATOR_COUNT - comparator_count
        ),
        "all_143_no_return_gates_passed": all_passed,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_values_read": False,
        "stress_2024_2025_return_values_opened": False,
        "training_or_model_fitting_performed": False,
        "provider_client_imported_or_created": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "current_scoring_selection_sizing_positions_or_orders_performed": False,
        "investment_advice": False,
        "next_action": (
            "freeze exactly one 2019-2023 Campaign265 development trial before any price or return value"
            if all_passed
            else "terminalize Campaign265 without any price or return read"
        ),
    }
    del candidate_frame
    gc.collect()
    atomic_exclusive_json(OUTPUT_PATH, result)
    return OUTPUT_PATH


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    subparsers = value.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    audit = subparsers.add_parser("audit")
    audit.add_argument("--confirm-no-return-audit", action="store_true")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "plan":
            value = build_plan()
            print(json.dumps(value, ensure_ascii=False, sort_keys=True))
            return 0 if value["ready"] else 2
        path = run_no_return_audit(confirm=args.confirm_no_return_audit)
        print(json.dumps({"no_return_audit_path": str(path)}, sort_keys=True))
        return 0
    except Campaign265NoReturnAuditError as exc:
        print(
            json.dumps(
                {
                    "ready": False,
                    "error_code": "campaign265_no_return_audit_contract_failure",
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
