#!/usr/bin/env python3
"""Run Campaign115's frozen 2019-2023 ordered no-return audit."""

from __future__ import annotations

import argparse
import concurrent.futures
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

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
for import_root in (ROOT, SCRIPT_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import a_share_tushare_limit_up_queue_development as SOURCE  # noqa: E402
import a_share_tushare_limit_up_queue_development_verify as VERIFIER  # noqa: E402

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign102_design as C102,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign103_features as C103,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign105_features as C105,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign109_features as C109,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign110_features as C110,
)

PROTOCOL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_audit_protocol_20260809.json"
)
PROTOCOL_SHA256 = "6d94e7fb638aed9f0423179a60ee3ad1a768b12c0de14a64c6dcc81168e6d12d"
IMPLEMENTATION_FREEZE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_audit_implementation_freeze_v5_20260809.json"
)
IMPLEMENTATION_FREEZE_V1 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_audit_implementation_freeze_v1_20260809.json"
)
IMPLEMENTATION_FREEZE_V1_SHA256 = (
    "2e6f5987456ff0449abca1eaff9dea4690a48d458da6b9832564118bb6d870e4"
)
STATIC_DIGEST_FIELD_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_static_partition_digest_field_failure_20260809.json"
)
STATIC_DIGEST_FIELD_FAILURE_SHA256 = (
    "2387f27314390a265a3e6fb285ac6b3762b9f0dd2f103f0f0374ae169b72b0b2"
)
PATCH_CONTEXT_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_v2_patch_context_failure_20260809.json"
)
PATCH_CONTEXT_FAILURE_SHA256 = (
    "f0579e3dfbd1d785f0e652447e68e281399c2be58dc1f9f5b903db6d13002645"
)
IMPLEMENTATION_FREEZE_V2 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_audit_implementation_freeze_v2_20260809.json"
)
IMPLEMENTATION_FREEZE_V2_SHA256 = (
    "ba0346705f7bd2e115e86eb05e45e5eb67a951bc915b5abe0bfd8ddba90cbab3"
)
MANIFEST_SEMANTIC_KEY_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_v2_manifest_semantic_key_failure_20260809.json"
)
MANIFEST_SEMANTIC_KEY_FAILURE_SHA256 = (
    "f3c7a34277a34ef9373b718bad04384341a09fecdb28329a813b4575830b1572"
)
IMPLEMENTATION_FREEZE_V3 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_audit_implementation_freeze_v3_20260809.json"
)
IMPLEMENTATION_FREEZE_V3_SHA256 = (
    "b87297788226fbbfc2d8400dc02ffa5bb536f9d2330118489eb7927cc86019eb"
)
LEGACY_CAMPAIGN110_REGRESSION_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_legacy_campaign110_report_binding_regression_failure_20260809.json"
)
LEGACY_CAMPAIGN110_REGRESSION_FAILURE_SHA256 = (
    "5a7797bf03d475448697048f96f8732cde01bcb38a2cf8782aaf7d8a695af928"
)
RUFF_IMPORT_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_v3_ruff_import_failure_20260809.json"
)
RUFF_IMPORT_FAILURE_SHA256 = (
    "02c2ff317c784c03ea56ceffe316ec3ce072e3d92b3846506ade8ac779c24b10"
)
RUFF_SORT_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_v4_ruff_sort_failure_20260809.json"
)
RUFF_SORT_FAILURE_SHA256 = (
    "fefcc71c4bbd2813ec8a8d0c32f012aa5fa5d6c3c3616cc427cb82fb62215cc3"
)
RUFF_POSTFIX_E402_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_v4_ruff_postfix_e402_failure_20260809.json"
)
RUFF_POSTFIX_E402_FAILURE_SHA256 = (
    "3ceda95f328e26f235fde0dbdec332e9aea6db07603c6c5f8d9d8a7871d6e8b0"
)
IMPLEMENTATION_FREEZE_V4 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_audit_implementation_freeze_v4_20260809.json"
)
IMPLEMENTATION_FREEZE_V4_SHA256 = (
    "3b79bdea2ca29133e3b03a4bc7b60fa07549a240372cf07b2b4a6e7330538b57"
)
DIRECT_ENTRY_IMPORT_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_115_ordered_no_return_direct_entry_import_failure_20260809.json"
)
DIRECT_ENTRY_IMPORT_FAILURE_SHA256 = (
    "c5dec31aeb0c7cfc1668865ad7664ce5e5f6868da577577da02f33facf0931fc"
)
TEST_PATH = (
    ROOT
    / "tests/data_collector_tests/test_a_share_tushare_limit_up_queue_no_return_audit.py"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260809_campaign115_semantic_verifier_ready_v7.json"
)
STATE_SHA256 = "0913315da1b67ae5c2808e9bcb69fddc7eb736a4fb843ad79ff34e7f4408bdfe"
NUMERIC_POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v92_20260809.json"
)
NUMERIC_POLICY_SHA256 = (
    "a3d2a1c81c6fd71e7a7e931156ad25182823043f8ab516085f074d6080b924a2"
)
AUDIT_PATH = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_115/no_return/"
    "campaign115_ordered_no_return_audit_2019_2023.json"
)
LOCK_PATH = ROOT / "data/.campaign115_ordered_no_return_audit.lock"

C102_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign102_design_matrix/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign102_design_matrix_v1/snapshot_manifest.json"
)
C102_MANIFEST_SHA256 = (
    "fc9ab498462439731785a0eabbde370c1fd883c8d771eba312c85aa912d3cebe"
)
C102_DATASET_SHA256 = "cceec2b790d134a89914e83e0697c1e6abff605a85fd85be74de68067faddb92"
C102_COMPONENT_ORDER_SHA256 = (
    "c80d9b929536dd509d6c1a904f790831050e68200393de381f92ad9293ef69e7"
)

DEVELOPMENT_YEARS = tuple(range(2019, 2024))
EXPECTED_SESSION_COUNT = 1214
EXPECTED_SESSION_ORDER_SHA256 = (
    "63559370c9abfe3b8e24d133d1cc102658e9f3a144c507a1c12928d93ad95059"
)
EXPECTED_COMPARATOR_COUNT = 134
EXPECTED_COMPARATOR_ORDER_SHA256 = (
    "31d788db467f558a0ac538315343090f1b3ad4cb27a26136a49ebaa88b2fdbf2"
)
MINIMUM_MEDIAN_COVERAGE = 0.95
MINIMUM_P05_COVERAGE = 0.90
MINIMUM_P05_NAMES = 50
MINIMUM_COHORTS = 200
MINIMUM_YEARS = 5
MINIMUM_PAIRWISE_NAMES = 50
MINIMUM_PAIRWISE_SESSIONS = 100
MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION = 0.8


class OrderedNoReturnAuditError(RuntimeError):
    """Fail-closed error for Campaign115's local no-return audit."""


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


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise OrderedNoReturnAuditError(f"invalid JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise OrderedNoReturnAuditError(f"JSON is not an object: {path}")
    return value


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _regular_file(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    return stat.S_ISREG(mode) and not stat.S_ISLNK(mode)


def _private_unique_file(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return bool(
        stat.S_ISREG(info.st_mode)
        and not stat.S_ISLNK(info.st_mode)
        and info.st_nlink == 1
        and stat.S_IMODE(info.st_mode) == 0o600
    )


def _record_path(manifest_path: Path, record: dict[str, Any]) -> Path:
    raw = Path(str(record.get("path") or ""))
    path = (
        raw.resolve() if raw.is_absolute() else (manifest_path.parent / raw).resolve()
    )
    if not path.is_relative_to(manifest_path.parent.resolve()):
        raise OrderedNoReturnAuditError(
            "comparator partition escapes its manifest root"
        )
    return path


def _partition_digest(record: dict[str, Any]) -> str:
    observed = [
        str(value)
        for value in (record.get("sha256"), record.get("output_byte_sha256"))
        if value not in {None, ""}
    ]
    if len(set(observed)) != 1:
        raise OrderedNoReturnAuditError("partition digest receipt is ambiguous")
    value = observed[0]
    try:
        valid = len(value) == 64 and int(value, 16) >= 0
    except ValueError:
        valid = False
    if not valid:
        raise OrderedNoReturnAuditError("partition digest receipt is ambiguous")
    return value


def _comparator_definitions() -> list[dict[str, str]]:
    definitions = [dict(item) for item in C110.reconstruct_comparisons()]
    definitions.append({"name": C110.FACTOR_NAME, "score_direction": "higher"})
    if not (
        len(definitions) == EXPECTED_COMPARATOR_COUNT
        and C110._order_digest(definitions) == EXPECTED_COMPARATOR_ORDER_SHA256
    ):
        raise OrderedNoReturnAuditError("frozen 134-comparator order changed")
    return definitions


INCREMENTAL_SOURCES: tuple[dict[str, Any], ...] = (
    {
        "ordinal": 131,
        "name": C103.FACTOR_NAME,
        "direction": "higher",
        "range": (0.0, 1.0),
        "manifest": C103.output_root(C103.DEFAULT_DATA_ROOT) / "snapshot_manifest.json",
        "manifest_sha256": "8a939feb53edfb31be8f133c2683920ed13424e716a4f4b5ed0d1a300588603b",
        "dataset_sha256": "57afdd9f8a246fb9f513f85b3b631f70cf734655bd226ff211201bf7e084ea13",
        "key_kind": "compact",
        "columns": tuple(C103.OUTPUT_COLUMNS),
    },
    {
        "ordinal": 132,
        "name": C105.FACTOR_NAME,
        "direction": "higher",
        "range": (0.0, 1.0),
        "manifest": C105.output_root(C105.DEFAULT_DATA_ROOT) / "snapshot_manifest.json",
        "manifest_sha256": "56e2d016087ff09643ef98dd00cad0ac9c771e815d19ec9941cea9f5904824a5",
        "dataset_sha256": "912625c3763fe3868adb4c4f410b6a6ab72c9272f78b8b57db620daaf970018c",
        "key_kind": "stock_day",
        "columns": tuple(C105.OUTPUT_COLUMNS),
    },
    {
        "ordinal": 133,
        "name": C109.FACTOR_NAME,
        "direction": "higher",
        "range": (-1.0, 1.0),
        "manifest": C109.output_root(C109.DEFAULT_DATA_ROOT) / "snapshot_manifest.json",
        "manifest_sha256": "b212eac0921bbca2c3a84c6eceb7f6741939c52ccb96a21e3897d1533c8b6aba",
        "dataset_sha256": "f222c80e80acb9872cc7e29a0fc89ab37e51bc1ee02f40f19f683c3757fcdb90",
        "key_kind": "stock_day",
        "columns": tuple(C109.OUTPUT_COLUMNS),
    },
    {
        "ordinal": 134,
        "name": C110.FACTOR_NAME,
        "direction": "higher",
        "range": (-1.0, 1.0),
        "manifest": C110.output_root(C110.DEFAULT_DATA_ROOT) / "snapshot_manifest.json",
        "manifest_sha256": "e3ae3c01e0a6eadd8dfce0362520e13bc4c047ff8357cdc7be2d1f9b31e93b72",
        "dataset_sha256": "9082b74891ea2e1c107309637941e42acdc9afeec0b44748e2242506c1a68c4b",
        "key_kind": "stock_day",
        "columns": tuple(C110.OUTPUT_COLUMNS),
    },
)


def _protocol_valid() -> bool:
    try:
        record = _read_object(PROTOCOL)
        inputs = record.get("authoritative_inputs") or {}
        interface = record.get("bounded_interface") or {}
        candidate = record.get("candidate_source_contract") or {}
        coverage = record.get("coverage_identity_source") or {}
        comparisons = record.get("comparison_contract") or {}
        artifact = record.get("audit_artifact") or {}
        boundary = record.get("research_boundary") or {}
        prohibitions = record.get("prohibitions") or {}
        return bool(
            digest(PROTOCOL) == PROTOCOL_SHA256
            and record.get("kind")
            == "a_share_three_day_walkforward_campaign115_ordered_no_return_audit_protocol"
            and record.get("status")
            == "frozen_before_campaign115_development_candidate_or_comparator_values"
            and (inputs.get("iteration_state_v7") or {}).get("sha256") == STATE_SHA256
            and (inputs.get("numeric_policy_v92") or {}).get("sha256")
            == NUMERIC_POLICY_SHA256
            and interface.get(
                "alternate_source_comparator_manifest_output_or_audit_path_allowed"
            )
            is False
            and interface.get("plan_reads_parquet_candidate_or_comparator_values")
            is False
            and interface.get("plan_reads_2024_2025_partitions") is False
            and interface.get("any_command_loads_credential_or_issues_provider_request")
            is False
            and candidate.get("factor") == SOURCE.ADAPTER.FACTOR_NAME
            and candidate.get("direction") == "higher"
            and candidate.get("exact_session_count") == EXPECTED_SESSION_COUNT
            and candidate.get("exact_session_order_sha256")
            == EXPECTED_SESSION_ORDER_SHA256
            and (coverage.get("manifest") or {}).get("sha256") == C102_MANIFEST_SHA256
            and coverage.get("precoverage_allowed_partition_years")
            == list(DEVELOPMENT_YEARS)
            and coverage.get("precoverage_allowed_parquet_columns") == ["stock_day_key"]
            and coverage.get(
                "unknown_year_partition_or_2024_2025_partition_read_allowed"
            )
            is False
            and comparisons.get("eligible_numeric_comparator_count")
            == EXPECTED_COMPARATOR_COUNT
            and comparisons.get("eligible_numeric_comparator_order_sha256")
            == EXPECTED_COMPARATOR_ORDER_SHA256
            and comparisons.get("allowed_partition_years") == list(DEVELOPMENT_YEARS)
            and comparisons.get("partition_year_2024_or_2025_read_allowed") is False
            and len(comparisons.get("incremental_sources") or ()) == 4
            and artifact.get("path") == str(AUDIT_PATH.relative_to(ROOT))
            and artifact.get("existing_artifact_is_never_overwritten") is True
            and artifact.get("candidate_or_comparator_row_values_embedded") is False
            and boundary.get(
                "development_source_candidate_values_read_during_protocol_freeze"
            )
            is False
            and boundary.get("comparison_values_read_during_protocol_freeze") is False
            and boundary.get("historical_daily_price_or_forward_return_values_read")
            is False
            and boundary.get("partition_year_2024_or_2025_values_read") is False
            and prohibitions.get("read_comparator_values_before_coverage_pass") is True
            and len(_comparator_definitions()) == EXPECTED_COMPARATOR_COUNT
        )
    except (OSError, KeyError, TypeError, ValueError, OrderedNoReturnAuditError):
        return False


def _implementation_binding_valid() -> bool:
    try:
        record = _read_object(IMPLEMENTATION_FREEZE)
        implementation = record.get("implementation") or {}
        superseded = record.get("supersedes_implementation_freeze_v1") or {}
        superseded_v2 = record.get("supersedes_implementation_freeze_v2") or {}
        superseded_v3 = record.get("supersedes_implementation_freeze_v3") or {}
        superseded_v4 = record.get("supersedes_implementation_freeze_v4") or {}
        failures = record.get("recorded_failures") or {}
        boundary = record.get("research_boundary") or {}
        return bool(
            record.get("kind")
            == "a_share_three_day_walkforward_campaign115_ordered_no_return_audit_implementation_freeze"
            and record.get("status")
            == "direct_protocol_entry_import_repair_frozen_before_campaign115_candidate_or_comparator_values"
            and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
            and superseded.get("sha256") == IMPLEMENTATION_FREEZE_V1_SHA256
            and digest(IMPLEMENTATION_FREEZE_V1) == IMPLEMENTATION_FREEZE_V1_SHA256
            and (failures.get("static_partition_digest_field_failure") or {}).get(
                "sha256"
            )
            == STATIC_DIGEST_FIELD_FAILURE_SHA256
            and digest(STATIC_DIGEST_FIELD_FAILURE)
            == STATIC_DIGEST_FIELD_FAILURE_SHA256
            and (failures.get("patch_context_failure") or {}).get("sha256")
            == PATCH_CONTEXT_FAILURE_SHA256
            and digest(PATCH_CONTEXT_FAILURE) == PATCH_CONTEXT_FAILURE_SHA256
            and superseded_v2.get("sha256") == IMPLEMENTATION_FREEZE_V2_SHA256
            and digest(IMPLEMENTATION_FREEZE_V2) == IMPLEMENTATION_FREEZE_V2_SHA256
            and (failures.get("manifest_semantic_key_failure") or {}).get("sha256")
            == MANIFEST_SEMANTIC_KEY_FAILURE_SHA256
            and digest(MANIFEST_SEMANTIC_KEY_FAILURE)
            == MANIFEST_SEMANTIC_KEY_FAILURE_SHA256
            and superseded_v3.get("sha256") == IMPLEMENTATION_FREEZE_V3_SHA256
            and digest(IMPLEMENTATION_FREEZE_V3) == IMPLEMENTATION_FREEZE_V3_SHA256
            and (failures.get("legacy_campaign110_regression_failure") or {}).get(
                "sha256"
            )
            == LEGACY_CAMPAIGN110_REGRESSION_FAILURE_SHA256
            and digest(LEGACY_CAMPAIGN110_REGRESSION_FAILURE)
            == LEGACY_CAMPAIGN110_REGRESSION_FAILURE_SHA256
            and (failures.get("ruff_import_failure") or {}).get("sha256")
            == RUFF_IMPORT_FAILURE_SHA256
            and digest(RUFF_IMPORT_FAILURE) == RUFF_IMPORT_FAILURE_SHA256
            and (failures.get("ruff_sort_failure") or {}).get("sha256")
            == RUFF_SORT_FAILURE_SHA256
            and digest(RUFF_SORT_FAILURE) == RUFF_SORT_FAILURE_SHA256
            and (failures.get("ruff_postfix_e402_failure") or {}).get("sha256")
            == RUFF_POSTFIX_E402_FAILURE_SHA256
            and digest(RUFF_POSTFIX_E402_FAILURE) == RUFF_POSTFIX_E402_FAILURE_SHA256
            and superseded_v4.get("sha256") == IMPLEMENTATION_FREEZE_V4_SHA256
            and digest(IMPLEMENTATION_FREEZE_V4) == IMPLEMENTATION_FREEZE_V4_SHA256
            and (failures.get("direct_protocol_entry_import_failure") or {}).get(
                "sha256"
            )
            == DIRECT_ENTRY_IMPORT_FAILURE_SHA256
            and digest(DIRECT_ENTRY_IMPORT_FAILURE)
            == DIRECT_ENTRY_IMPORT_FAILURE_SHA256
            and implementation.get("runner_path")
            == "scripts/a_share_tushare_limit_up_queue_no_return_audit.py"
            and implementation.get("runner_sha256") == digest(Path(__file__).resolve())
            and implementation.get("test_path")
            == "tests/data_collector_tests/test_a_share_tushare_limit_up_queue_no_return_audit.py"
            and implementation.get("test_sha256") == digest(TEST_PATH)
            and boundary.get("candidate_values_read_before_freeze") is False
            and boundary.get("comparator_values_read_before_freeze") is False
            and boundary.get("daily_price_or_forward_return_values_read_before_freeze")
            is False
            and boundary.get("partition_year_2024_or_2025_values_read_before_freeze")
            is False
            and boundary.get("provider_request_issued_before_freeze") is False
        )
    except (OSError, KeyError, TypeError, ValueError, OrderedNoReturnAuditError):
        return False


def runtime_bindings_valid() -> bool:
    try:
        return bool(
            _protocol_valid()
            and _implementation_binding_valid()
            and digest(STATE) == STATE_SHA256
            and digest(NUMERIC_POLICY) == NUMERIC_POLICY_SHA256
            and VERIFIER.runtime_bindings_valid()
        )
    except (OSError, TypeError, ValueError):
        return False


def _manifest_records_for_years(
    manifest_path: Path,
    expected_manifest_sha256: str,
    expected_dataset_sha256: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if (
        not _regular_file(manifest_path)
        or digest(manifest_path) != expected_manifest_sha256
    ):
        raise OrderedNoReturnAuditError(f"comparator manifest changed: {manifest_path}")
    manifest = _read_object(manifest_path)
    if manifest.get("dataset_sha256") != expected_dataset_sha256:
        raise OrderedNoReturnAuditError("comparator dataset fingerprint changed")
    records = list(manifest.get("files") or ())
    selected = [
        record for record in records if int(record.get("year", -1)) in DEVELOPMENT_YEARS
    ]
    years = {int(record.get("year", -1)) for record in selected}
    if years != set(DEVELOPMENT_YEARS):
        raise OrderedNoReturnAuditError(
            "comparator development-year partition set changed"
        )
    for record in selected:
        path = _record_path(manifest_path, record)
        _partition_digest(record)
        if not _regular_file(path):
            raise OrderedNoReturnAuditError(
                "comparator development partition is absent"
            )
    return manifest, selected


def _manifest_no_return_boundary_valid(
    source: dict[str, Any], manifest: dict[str, Any]
) -> bool:
    if int(source["ordinal"]) == 131:
        return manifest.get("historical_forward_return_fields_read") is False
    return bool(
        manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
    )


def _static_comparator_metadata_valid() -> bool:
    try:
        definitions = _comparator_definitions()
        manifest, records = _manifest_records_for_years(
            C102_MANIFEST,
            C102_MANIFEST_SHA256,
            C102_DATASET_SHA256,
        )
        if not (
            manifest.get("kind")
            == "a_share_three_day_walkforward_campaign102_design_matrix_snapshot"
            and manifest.get("component_count") == 130
            and manifest.get("component_order_sha256") == C102_COMPONENT_ORDER_SHA256
            and manifest.get("components") == definitions[:130]
            and len(records) == len(DEVELOPMENT_YEARS)
        ):
            return False
        for source, expected in zip(
            INCREMENTAL_SOURCES, definitions[130:], strict=True
        ):
            manifest, selected = _manifest_records_for_years(
                Path(source["manifest"]),
                str(source["manifest_sha256"]),
                str(source["dataset_sha256"]),
            )
            if not (
                source["name"] == expected["name"]
                and source["direction"] == expected["score_direction"]
                and selected
                and _manifest_no_return_boundary_valid(source, manifest)
                and manifest.get("provider_request_issued") is False
            ):
                return False
        return True
    except (OSError, TypeError, ValueError, OrderedNoReturnAuditError):
        return False


def build_plan() -> dict[str, Any]:
    receipt = VERIFIER.inspect_receipt()
    checks = {
        "protocol_fingerprint": _protocol_valid(),
        "audit_runtime_binding": runtime_bindings_valid(),
        "state_v7_fingerprint": _regular_file(STATE) and digest(STATE) == STATE_SHA256,
        "numeric_policy_v92_fingerprint": _regular_file(NUMERIC_POLICY)
        and digest(NUMERIC_POLICY) == NUMERIC_POLICY_SHA256,
        "semantic_verification_receipt_valid": receipt.get("status")
        == "complete_semantically_verified_2019_2023_candidate_snapshot_pending_ordered_no_return_audit",
        "source_final_root_present": SOURCE.FINAL_ROOT.is_dir()
        and not SOURCE.FINAL_ROOT.is_symlink(),
        "all_134_comparator_metadata_bindings_valid": _static_comparator_metadata_valid(),
        "audit_artifact_absent": not AUDIT_PATH.exists()
        and not AUDIT_PATH.is_symlink(),
    }
    blockers = [name for name, passed in checks.items() if not passed]
    return {
        "ready": not blockers,
        "exit_code_if_executed": 0 if not blockers else 2,
        "checks": checks,
        "blockers": blockers,
        "candidate_factor": SOURCE.ADAPTER.FACTOR_NAME,
        "candidate_session_count": EXPECTED_SESSION_COUNT,
        "comparator_count": EXPECTED_COMPARATOR_COUNT,
        "comparator_order_sha256": EXPECTED_COMPARATOR_ORDER_SHA256,
        "allowed_partition_years": list(DEVELOPMENT_YEARS),
        "semantic_receipt": str(VERIFIER.RECEIPT),
        "audit_artifact": str(AUDIT_PATH),
        "parquet_candidate_values_read": False,
        "parquet_comparator_values_read": False,
        "daily_price_or_forward_return_values_read": False,
        "partition_year_2024_or_2025_values_read": False,
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
        raise OrderedNoReturnAuditError("no-return audit lock unavailable") from exc


def _compact_keys(trade_dates: pd.Series, instruments: pd.Series) -> np.ndarray:
    dates = pd.to_datetime(trade_dates, errors="coerce").dt.normalize()
    text = instruments.astype("string").str.upper()
    exchange = text.str.slice(0, 2).map({"SH": 1, "SZ": 2, "BJ": 3})
    codes = pd.to_numeric(text.str.slice(2), errors="coerce")
    if dates.isna().any() or exchange.isna().any() or codes.isna().any():
        raise OrderedNoReturnAuditError("stock-day identity cannot be compacted")
    day_number = dates.to_numpy(dtype="datetime64[D]").astype(np.int64, copy=False)
    security_number = exchange.to_numpy(dtype=np.int64) * 1_000_000 + codes.to_numpy(
        dtype=np.int64
    )
    return day_number * 4_000_000 + security_number


def _verify_partition_hashes(
    manifest_path: Path, records: list[dict[str, Any]], workers: int
) -> list[dict[str, Any]]:
    if workers < 1 or workers > 16:
        raise OrderedNoReturnAuditError("workers must be between 1 and 16")

    def verify(record: dict[str, Any]) -> dict[str, Any]:
        path = _record_path(manifest_path, record)
        expected = _partition_digest(record)
        if digest(path) != expected:
            raise OrderedNoReturnAuditError(f"partition byte hash changed: {path}")
        return {
            "year": int(record["year"]),
            "path": str(path),
            "rows": int(record["rows"]),
            "sha256": expected,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(verify, records))


def _load_base_keys(*, workers: int) -> tuple[np.ndarray, dict[str, Any]]:
    manifest, records = _manifest_records_for_years(
        C102_MANIFEST,
        C102_MANIFEST_SHA256,
        C102_DATASET_SHA256,
    )
    records = sorted(records, key=lambda item: int(item["year"]))
    receipts = _verify_partition_hashes(C102_MANIFEST, records, workers)
    arrays: list[np.ndarray] = []
    for record in records:
        path = _record_path(C102_MANIFEST, record)
        frame = pd.read_parquet(path, columns=["stock_day_key"])
        keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        if len(keys) != int(record["rows"]) or len(np.unique(keys)) != len(keys):
            raise OrderedNoReturnAuditError("coverage identity partition changed")
        days = keys // 4_000_000
        years = pd.to_datetime(days, unit="D", origin="unix").year
        if not np.all(years == int(record["year"])):
            raise OrderedNoReturnAuditError("coverage identity year changed")
        arrays.append(keys)
    keys = np.concatenate(arrays).astype(np.int64, copy=False)
    if len(np.unique(keys)) != len(keys) or np.any(keys[1:] <= keys[:-1]):
        raise OrderedNoReturnAuditError("coverage identity order changed")
    session_count = len(np.unique(keys // 4_000_000))
    if session_count != EXPECTED_SESSION_COUNT:
        raise OrderedNoReturnAuditError("coverage identity session count changed")
    return keys, {
        "manifest_path": str(C102_MANIFEST),
        "manifest_sha256": C102_MANIFEST_SHA256,
        "dataset_sha256": manifest["dataset_sha256"],
        "selected_partition_years": list(DEVELOPMENT_YEARS),
        "selected_partitions": receipts,
        "rows": len(keys),
        "sessions": session_count,
        "stock_day_key_order_sha256": hashlib.sha256(
            keys.astype("<i8", copy=False).tobytes()
        ).hexdigest(),
        "parquet_columns_read_before_coverage": ["stock_day_key"],
        "comparator_values_read_before_coverage": False,
        "partition_year_2024_or_2025_read": False,
    }


def _source_receipt_and_verification() -> tuple[dict[str, Any], dict[str, Any]]:
    if not _private_unique_file(VERIFIER.RECEIPT):
        raise OrderedNoReturnAuditError("semantic receipt is not private and unique")
    receipt = _read_object(VERIFIER.RECEIPT)
    inspected = VERIFIER.inspect_receipt()
    verification = VERIFIER._verify_source()
    expected = receipt.get("verification") or {}
    for key in (
        "dataset_sha256",
        "session_count",
        "session_order_sha256",
        "factor_rows",
        "official_limit_up_event_rows",
        "sessions_with_valid_upper_limit_names",
        "checkpoint_factor_byte_order_sha256",
    ):
        if verification.get(key) != expected.get(key):
            raise OrderedNoReturnAuditError("semantic source changed after its receipt")
    if inspected.get("dataset_sha256") != verification.get("dataset_sha256"):
        raise OrderedNoReturnAuditError("semantic receipt inspection changed")
    return receipt, verification


def _load_candidate_on_base(base_keys: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    values = np.full(len(base_keys), np.nan, dtype=np.float64)
    assigned = np.zeros(len(base_keys), dtype=bool)
    rows_read = 0
    for session in SOURCE._development_sessions():
        frame_path, _ = SOURCE._session_paths(SOURCE.FINAL_ROOT, session)
        frame = pd.read_parquet(
            frame_path,
            columns=["trade_date", "instrument", SOURCE.ADAPTER.FACTOR_NAME],
        )
        keys = _compact_keys(frame["trade_date"], frame["instrument"])
        candidate = pd.to_numeric(
            frame[SOURCE.ADAPTER.FACTOR_NAME], errors="coerce"
        ).to_numpy(dtype=np.float64)
        if (
            not np.isfinite(candidate).all()
            or np.any(candidate < 0.0)
            or np.any(candidate > 1.0)
            or len(np.unique(keys)) != len(keys)
        ):
            raise OrderedNoReturnAuditError("candidate session values changed")
        locations = np.searchsorted(base_keys, keys, side="left")
        matched = locations < len(base_keys)
        if matched.any():
            indices = np.flatnonzero(matched)
            matched[indices] = base_keys[locations[indices]] == keys[indices]
        selected = locations[matched]
        if assigned[selected].any():
            raise OrderedNoReturnAuditError("candidate stock-day key repeated")
        values[selected] = candidate[matched]
        assigned[selected] = True
        rows_read += len(frame)
    return values, {
        "source_factor_rows_read": rows_read,
        "coverage_base_rows_matched": int(assigned.sum()),
        "candidate_value_sha256": _value_digest(values),
        "candidate_rows_embedded_in_audit": False,
    }


def _value_digest(values: np.ndarray) -> str:
    array = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(array)
    canonical = np.where(finite, array, 0.0).astype("<f8", copy=False)
    hasher = hashlib.sha256()
    hasher.update(finite.astype(np.uint8, copy=False).tobytes())
    hasher.update(canonical.tobytes())
    return hasher.hexdigest()


def _coverage_and_capacity(
    base_keys: np.ndarray, candidate_values: np.ndarray
) -> dict[str, Any]:
    if candidate_values.shape != base_keys.shape:
        raise OrderedNoReturnAuditError("candidate/base shape changed")
    sessions = base_keys // 4_000_000
    boundaries = np.flatnonzero(np.r_[True, sessions[1:] != sessions[:-1], True])
    daily_rows: list[list[Any]] = []
    for start, stop in zip(boundaries[:-1], boundaries[1:], strict=True):
        finite = int(np.isfinite(candidate_values[start:stop]).sum())
        total = stop - start
        daily_rows.append([int(sessions[start]), total, finite, finite / total])
    coverages = np.asarray([row[3] for row in daily_rows], dtype=np.float64)
    names = np.asarray([row[2] for row in daily_rows], dtype=np.int64)
    indices = np.arange(0, max(len(daily_rows) - 3, 0), 3)
    potential_mask = names[indices] >= MINIMUM_P05_NAMES
    potential = int(potential_mask.sum())
    cohort_days = np.asarray(
        [daily_rows[index][0] for index in indices[potential_mask]]
    )
    years = sorted(
        int(value)
        for value in pd.to_datetime(cohort_days, unit="D", origin="unix")
        .year.unique()
        .tolist()
    )
    median = float(np.median(coverages))
    p05 = float(np.quantile(coverages, 0.05))
    names_p05 = float(np.quantile(names, 0.05))
    passed = bool(
        median >= MINIMUM_MEDIAN_COVERAGE
        and p05 >= MINIMUM_P05_COVERAGE
        and names_p05 >= MINIMUM_P05_NAMES
        and potential >= MINIMUM_COHORTS
        and len(years) >= MINIMUM_YEARS
    )
    hash_rows = [
        [
            dt.date(1970, 1, 1).__add__(dt.timedelta(days=int(row[0]))).isoformat(),
            int(row[1]),
            int(row[2]),
            float(row[3]).hex(),
        ]
        for row in daily_rows
    ]
    return {
        "quality_current_listing_base_rows": len(base_keys),
        "candidate_eligible_rows": int(np.isfinite(candidate_values).sum()),
        "calendar_sessions": len(daily_rows),
        "median_coverage": median,
        "p05_coverage": p05,
        "eligible_names_minimum": int(names.min()),
        "eligible_names_p05": names_p05,
        "eligible_names_median": float(np.median(names)),
        "potential_non_overlapping_three_session_cohorts": potential,
        "observed_cohort_years": years,
        "daily_coverage_frame_sha256": _json_digest(hash_rows),
        "daily_coverage_rows_embedded": False,
        "gate": {
            "minimum_median_coverage": MINIMUM_MEDIAN_COVERAGE,
            "minimum_p05_coverage": MINIMUM_P05_COVERAGE,
            "minimum_p05_eligible_names": MINIMUM_P05_NAMES,
            "minimum_non_overlapping_three_session_cohorts": MINIMUM_COHORTS,
            "minimum_observed_calendar_years": MINIMUM_YEARS,
        },
        "gate_passed_before_comparator_values": passed,
    }


def _daily_correlation_rows(
    keys: np.ndarray,
    candidate_values: np.ndarray,
    comparison_values: np.ndarray,
) -> list[list[Any]]:
    sessions = keys // 4_000_000
    boundaries = np.flatnonzero(np.r_[True, sessions[1:] != sessions[:-1], True])
    rows: list[list[Any]] = []
    for start, stop in zip(boundaries[:-1], boundaries[1:], strict=True):
        left = candidate_values[start:stop]
        right = comparison_values[start:stop]
        finite = np.isfinite(left) & np.isfinite(right)
        names = int(finite.sum())
        if names < MINIMUM_PAIRWISE_NAMES:
            continue
        left = left[finite]
        right = right[finite]
        if np.unique(left).size < 2 or np.unique(right).size < 2:
            continue
        left_rank = pd.Series(left).rank(method="average", pct=True)
        right_rank = pd.Series(right).rank(method="average", pct=True)
        correlation = float(left_rank.corr(right_rank, method="pearson"))
        if math.isfinite(correlation):
            rows.append([int(sessions[start]), names, correlation])
    return rows


def _comparison_result(
    definition: dict[str, str], rows: list[list[Any]], value_sha256: str
) -> dict[str, Any]:
    correlations = np.asarray([row[2] for row in rows], dtype=np.float64)
    median = float(np.median(correlations)) if len(correlations) else math.nan
    passed = bool(
        len(correlations) >= MINIMUM_PAIRWISE_SESSIONS
        and math.isfinite(median)
        and abs(median) < MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
    )
    digest_rows = [
        [
            dt.date(1970, 1, 1).__add__(dt.timedelta(days=int(row[0]))).isoformat(),
            int(row[1]),
            float(row[2]).hex(),
        ]
        for row in rows
    ]
    return {
        "comparison_factor": definition["name"],
        "source_score_direction": definition["score_direction"],
        "pairwise_sessions": len(rows),
        "minimum_pairwise_names_observed": (
            min(int(row[1]) for row in rows) if rows else 0
        ),
        "median_daily_rank_correlation": median if math.isfinite(median) else None,
        "absolute_median_daily_rank_correlation": (
            abs(median) if math.isfinite(median) else None
        ),
        "daily_rank_correlation_p05": (
            float(np.quantile(correlations, 0.05)) if len(correlations) else None
        ),
        "daily_rank_correlation_p95": (
            float(np.quantile(correlations, 0.95)) if len(correlations) else None
        ),
        "comparison_value_sha256": value_sha256,
        "daily_correlation_frame_sha256": _json_digest(digest_rows),
        "daily_correlation_rows_embedded": False,
        "gate_passed": passed,
    }


def _first_130_comparisons(
    *,
    base_keys: np.ndarray,
    candidate_values: np.ndarray,
    workers: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest, records = _manifest_records_for_years(
        C102_MANIFEST,
        C102_MANIFEST_SHA256,
        C102_DATASET_SHA256,
    )
    records = sorted(records, key=lambda item: int(item["year"]))
    partition_receipts = _verify_partition_hashes(C102_MANIFEST, records, workers)
    definitions = _comparator_definitions()[:130]
    rows: list[list[list[Any]]] = [[] for _ in definitions]
    value_hashers = [hashlib.sha256() for _ in definitions]
    for record in records:
        keys, matrix, _, _ = C102._read_partition(C102_MANIFEST, record)
        start = int(np.searchsorted(base_keys, keys[0], side="left"))
        stop = start + len(keys)
        if stop > len(base_keys) or not np.array_equal(base_keys[start:stop], keys):
            raise OrderedNoReturnAuditError("Campaign102/base identity changed")
        local_candidate = candidate_values[start:stop]
        for index in range(len(definitions)):
            values = matrix[:, index].astype(np.float64, copy=False)
            value_hashers[index].update(bytes.fromhex(_value_digest(values)))
            rows[index].extend(_daily_correlation_rows(keys, local_candidate, values))
    results = [
        _comparison_result(definition, rows[index], value_hashers[index].hexdigest())
        for index, definition in enumerate(definitions)
    ]
    return results, {
        "manifest_path": str(C102_MANIFEST),
        "manifest_sha256": C102_MANIFEST_SHA256,
        "dataset_sha256": manifest["dataset_sha256"],
        "component_count": 130,
        "component_order_sha256": manifest["component_order_sha256"],
        "selected_partition_years": list(DEVELOPMENT_YEARS),
        "selected_partitions": partition_receipts,
        "partition_year_2024_or_2025_read": False,
    }


def _load_incremental_values(
    source: dict[str, Any], target_keys: np.ndarray, workers: int
) -> tuple[np.ndarray, dict[str, Any]]:
    manifest_path = Path(source["manifest"])
    manifest, records = _manifest_records_for_years(
        manifest_path,
        str(source["manifest_sha256"]),
        str(source["dataset_sha256"]),
    )
    records = sorted(
        records,
        key=lambda item: (int(item["year"]), str(item.get("path") or "")),
    )
    partition_receipts = _verify_partition_hashes(manifest_path, records, workers)
    paths = [str(_record_path(manifest_path, record)) for record in records]
    factor = str(source["name"])
    eligible_column = f"{factor}_eligible"
    columns = list(source["columns"])
    required = (
        ["stock_day_key", factor, eligible_column]
        if source["key_kind"] == "compact"
        else ["trade_date", "symbol", "provider", factor, eligible_column]
    )
    if any(column not in columns for column in required):
        raise OrderedNoReturnAuditError("incremental comparator schema changed")
    values = np.full(len(target_keys), np.nan, dtype=np.float64)
    assigned = np.zeros(len(target_keys), dtype=bool)
    rows_read = 0
    dataset = pa_dataset.dataset(paths, format="parquet")
    scanner = dataset.scanner(columns=required, batch_size=262_144, use_threads=True)
    lower, upper = source["range"]
    for batch in scanner.to_batches():
        frame = batch.to_pandas(split_blocks=True, self_destruct=True)
        rows_read += len(frame)
        if source["key_kind"] == "compact":
            keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        else:
            if not (frame["provider"].astype(str) == "tushare").all():
                raise OrderedNoReturnAuditError(
                    "incremental comparator provider changed"
                )
            keys = _compact_keys(frame["trade_date"], frame["symbol"])
        raw = pd.to_numeric(frame[factor], errors="coerce").to_numpy(dtype=np.float64)
        eligible = (
            frame[eligible_column].astype("boolean").fillna(False).to_numpy(dtype=bool)
        )
        if (
            not np.isfinite(raw[eligible]).all()
            or np.any(raw[eligible] < lower)
            or np.any(raw[eligible] > upper)
            or np.isfinite(raw[~eligible]).any()
        ):
            raise OrderedNoReturnAuditError("incremental comparator values changed")
        locations = np.searchsorted(target_keys, keys, side="left")
        matched = locations < len(target_keys)
        if matched.any():
            indices = np.flatnonzero(matched)
            matched[indices] = target_keys[locations[indices]] == keys[indices]
        matched &= eligible
        selected = locations[matched]
        if assigned[selected].any():
            raise OrderedNoReturnAuditError("incremental comparator key repeated")
        values[selected] = raw[matched]
        assigned[selected] = True
    return values, {
        "manifest_path": str(manifest_path),
        "manifest_sha256": source["manifest_sha256"],
        "dataset_sha256": manifest["dataset_sha256"],
        "factor": factor,
        "selected_partition_years": list(DEVELOPMENT_YEARS),
        "selected_partition_count": len(records),
        "selected_partition_rows": rows_read,
        "selected_partitions_sha256": _json_digest(partition_receipts),
        "matched_candidate_rows": int(assigned.sum()),
        "partition_year_2024_or_2025_read": False,
    }


def _all_comparisons(
    *, base_keys: np.ndarray, candidate_values: np.ndarray, workers: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results, first_receipt = _first_130_comparisons(
        base_keys=base_keys,
        candidate_values=candidate_values,
        workers=workers,
    )
    definitions = _comparator_definitions()
    incremental_receipts: list[dict[str, Any]] = []
    for source, definition in zip(INCREMENTAL_SOURCES, definitions[130:], strict=True):
        values, receipt = _load_incremental_values(source, base_keys, workers)
        rows = _daily_correlation_rows(base_keys, candidate_values, values)
        results.append(_comparison_result(definition, rows, _value_digest(values)))
        incremental_receipts.append(receipt)
    if [item["comparison_factor"] for item in results] != [
        item["name"] for item in definitions
    ]:
        raise OrderedNoReturnAuditError("observed comparator order changed")
    return results, {
        "first_130": first_receipt,
        "incremental_131_to_134": incremental_receipts,
        "all_134_loaded_in_frozen_order": True,
        "partition_year_2024_or_2025_read": False,
    }


def _audit_record(
    *,
    semantic_receipt: dict[str, Any],
    source_verification: dict[str, Any],
    base_receipt: dict[str, Any],
    candidate_receipt: dict[str, Any],
    coverage: dict[str, Any],
    comparisons: list[dict[str, Any]],
    comparator_receipt: dict[str, Any],
) -> dict[str, Any]:
    coverage_passed = coverage["gate_passed_before_comparator_values"] is True
    all_comparators_passed = bool(
        coverage_passed
        and len(comparisons) == EXPECTED_COMPARATOR_COUNT
        and all(item.get("gate_passed") is True for item in comparisons)
    )
    if not coverage_passed:
        status = (
            "completed_zero_admissible_factor_coverage_stop_before_comparator_values"
        )
    elif all_comparators_passed:
        status = (
            "completed_one_no_return_admissible_factor_pending_frozen_development_trial"
        )
    else:
        status = (
            "completed_zero_admissible_factor_uniqueness_stop_before_prices_or_returns"
        )
    correlations = [
        float(item["absolute_median_daily_rank_correlation"])
        for item in comparisons
        if item.get("absolute_median_daily_rank_correlation") is not None
    ]
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign115_ordered_no_return_audit",
        "status": status,
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": PROTOCOL_SHA256,
        },
        "implementation_freeze": {
            "path": str(IMPLEMENTATION_FREEZE.relative_to(ROOT)),
            "sha256": digest(IMPLEMENTATION_FREEZE),
        },
        "semantic_source": {
            "receipt_path": _display_path(VERIFIER.RECEIPT),
            "receipt_sha256": digest(VERIFIER.RECEIPT),
            "dataset_sha256": source_verification["dataset_sha256"],
            "session_count": source_verification["session_count"],
            "session_order_sha256": source_verification["session_order_sha256"],
            "factor_rows": source_verification["factor_rows"],
            "receipt_status": semantic_receipt["status"],
            "semantic_revalidation_matched_receipt": True,
        },
        "coverage_identity": base_receipt,
        "candidate": {
            "factor": SOURCE.ADAPTER.FACTOR_NAME,
            "direction": "higher",
            "value_range_inclusive": [0.0, 1.0],
            **candidate_receipt,
        },
        "coverage_and_capacity": coverage,
        "uniqueness": {
            "comparison_values_loaded_after_coverage_pass": bool(comparisons),
            "comparison_count": len(comparisons),
            "comparison_order_sha256": EXPECTED_COMPARATOR_ORDER_SHA256,
            "comparison_order_matches_preregistration": [
                item["comparison_factor"] for item in comparisons
            ]
            == [item["name"] for item in _comparator_definitions()],
            "all_required_numeric_comparisons_passed": all_comparators_passed,
            "maximum_observed_absolute_median_daily_rank_correlation": (
                max(correlations) if correlations else None
            ),
            "comparisons": comparisons,
            "comparison_source_verification": comparator_receipt,
        },
        "admissible_factor_names": (
            [SOURCE.ADAPTER.FACTOR_NAME] if all_comparators_passed else []
        ),
        "admissible_factor_count": 1 if all_comparators_passed else 0,
        "next_action": (
            "freeze the exact single 2019-2023 development trial before any price or return read"
            if all_comparators_passed
            else "preserve this terminal no-return result without rescue or return access"
        ),
        "candidate_or_comparator_row_values_embedded": False,
        "daily_coverage_or_correlation_rows_embedded": False,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "partition_year_2024_or_2025_values_read": False,
        "stress_2024_2025_opened": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "training_or_model_fitting_performed": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "selection_or_promotion_allowed": False,
        "investment_advice": False,
        "current_listing_snapshot_survivorship_limitation": True,
    }


def _publish_exclusive_private_json(record: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        raise OrderedNoReturnAuditError("no-return audit artifact already exists")
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


def run_audit(*, confirmed: bool, workers: int = 4) -> dict[str, Any]:
    if not confirmed:
        raise OrderedNoReturnAuditError("--confirm-no-return-audit is required")
    plan = build_plan()
    if not plan["ready"]:
        raise OrderedNoReturnAuditError("ordered no-return audit plan is not ready")
    with _exclusive_lock():
        semantic_receipt, source_verification = _source_receipt_and_verification()
        base_keys, base_receipt = _load_base_keys(workers=workers)
        candidate_values, candidate_receipt = _load_candidate_on_base(base_keys)
        coverage = _coverage_and_capacity(base_keys, candidate_values)
        comparisons: list[dict[str, Any]] = []
        comparator_receipt: dict[str, Any] = {
            "comparator_values_read": False,
            "reason": "coverage_gate_failed_before_comparator_values",
            "partition_year_2024_or_2025_read": False,
        }
        if coverage["gate_passed_before_comparator_values"]:
            comparisons, comparator_receipt = _all_comparisons(
                base_keys=base_keys,
                candidate_values=candidate_values,
                workers=workers,
            )
            comparator_receipt["comparator_values_read"] = True
        record = _audit_record(
            semantic_receipt=semantic_receipt,
            source_verification=source_verification,
            base_receipt=base_receipt,
            candidate_receipt=candidate_receipt,
            coverage=coverage,
            comparisons=comparisons,
            comparator_receipt=comparator_receipt,
        )
        _publish_exclusive_private_json(record, AUDIT_PATH)
    return record


def inspect_audit() -> dict[str, Any]:
    if not AUDIT_PATH.exists():
        return {
            "valid": True,
            "status": "no_ordered_no_return_audit",
            "credential_loaded": False,
            "provider_request_issued": False,
        }
    if not _private_unique_file(AUDIT_PATH):
        raise OrderedNoReturnAuditError("no-return audit artifact is not private")
    record = _read_object(AUDIT_PATH)
    status = str(record.get("status") or "")
    coverage = record.get("coverage_and_capacity") or {}
    uniqueness = record.get("uniqueness") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign115_ordered_no_return_audit"
        and status
        in {
            "completed_zero_admissible_factor_coverage_stop_before_comparator_values",
            "completed_zero_admissible_factor_uniqueness_stop_before_prices_or_returns",
            "completed_one_no_return_admissible_factor_pending_frozen_development_trial",
        }
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("implementation_freeze") or {}).get("sha256")
        == digest(IMPLEMENTATION_FREEZE)
        and coverage.get("calendar_sessions") == EXPECTED_SESSION_COUNT
        and uniqueness.get("comparison_count") in {0, EXPECTED_COMPARATOR_COUNT}
        and record.get("candidate_or_comparator_row_values_embedded") is False
        and record.get("daily_coverage_or_correlation_rows_embedded") is False
        and record.get("historical_daily_price_fields_read") == []
        and record.get("historical_forward_return_fields_read") is False
        and record.get("partition_year_2024_or_2025_values_read") is False
        and record.get("stress_2024_2025_opened") is False
        and record.get("provider_request_issued") is False
        and record.get("credential_loaded") is False
        and record.get("selection_or_promotion_allowed") is False
    ):
        raise OrderedNoReturnAuditError("no-return audit artifact semantics changed")
    return {
        "valid": True,
        "status": status,
        "audit_sha256": digest(AUDIT_PATH),
        "coverage_gate_passed": coverage.get("gate_passed_before_comparator_values"),
        "comparison_count": uniqueness.get("comparison_count"),
        "admissible_factor_count": record.get("admissible_factor_count"),
        "daily_price_or_forward_return_values_read": False,
        "partition_year_2024_or_2025_values_read": False,
        "credential_loaded": False,
        "provider_request_issued": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan")
    audit = commands.add_parser("audit")
    audit.add_argument("--confirm-no-return-audit", action="store_true")
    audit.add_argument("--workers", type=int, default=4)
    commands.add_parser("inspect-audit")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "plan":
            payload = build_plan()
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return int(payload["exit_code_if_executed"])
        if args.command == "audit":
            payload = run_audit(
                confirmed=args.confirm_no_return_audit,
                workers=args.workers,
            )
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return 0
        payload = inspect_audit()
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    except OrderedNoReturnAuditError as exc:
        print(
            json.dumps(
                {
                    "status": "failed_closed",
                    "reason": str(exc),
                    "daily_price_or_forward_return_values_read": False,
                    "partition_year_2024_or_2025_values_read": False,
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
