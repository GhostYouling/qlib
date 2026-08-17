#!/usr/bin/env python3
"""Snapshot-bound Campaign061 ordered no-return audit implementation."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_AUDIT = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign060_no_return_audit.py"
BASE_AUDIT_SHA256 = "ecedad2aec0cf823c603001e2733411879c87d9b2522c4d09d5b6a212fa19977"
BASE_FACTOR = "intraday_day_over_day_directional_return_agreement_238b"
FACTOR_NAME = "intraday_day_over_day_realized_variance_stability_238b"
EXPECTED_COMPARISON_COUNT = 92
EXPECTED_COMPARISON_ORDER_SHA256 = "c6b4ce432891c251443d8672705d1ecf0977912c1f3e82d42c00863001288c76"
SNAPSHOT_BINDING_SHA256 = "232117b95fe4ff426c8ca6a4742f647d53a0697f9a4497479ef557fe59d919ce"
SNAPSHOT_MANIFEST_SHA256 = "15ed4b46192402f301218e20b1fe37233dd7547256fb9786692ce544fae20b3c"
SNAPSHOT_DATASET_SHA256 = "a8a6261eaa92cd8eca7c25513236abf73f84f500da368a7b325634808fbb576a"
EXPECTED_ELIGIBLE_ROWS = 7_671_540

C60_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign060_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign060_feature_library_v1/snapshot_manifest.json"
)
C60_SNAPSHOT_SHA256 = "3f328039fb7806c66a260a7fd723a3297e2e0ce5ba23e9bb11f39d963e7250cd"
C60_DATASET_SHA256 = "052e5c8e5090c173c1e9486b545eafaa3b1301e038c1acc72434222e683d5735"
C60_FACTOR = "intraday_day_over_day_directional_return_agreement_238b"


def _local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _local_sha256(BASE_AUDIT) != BASE_AUDIT_SHA256:
    raise RuntimeError("frozen Campaign060 no-return audit changed")

_source = BASE_AUDIT.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign060", "Campaign061"),
    ("campaign060", "campaign061"),
    ("campaign_060", "campaign_061"),
    (BASE_FACTOR, FACTOR_NAME),
    ("6226c6381bd5b11eec41061c99e906fb736acbb70c922831bf81d9ed974682bd", SNAPSHOT_BINDING_SHA256),
    ("3f328039fb7806c66a260a7fd723a3297e2e0ce5ba23e9bb11f39d963e7250cd", SNAPSHOT_MANIFEST_SHA256),
    ("052e5c8e5090c173c1e9486b545eafaa3b1301e038c1acc72434222e683d5735", SNAPSHOT_DATASET_SHA256),
    ("EXPECTED_ELIGIBLE_ROWS = 5_878_602", "EXPECTED_ELIGIBLE_ROWS = 7_671_540"),
    ("EXPECTED_COMPARISON_COUNT = 91", "EXPECTED_COMPARISON_COUNT = 92"),
    ("abbf08eef9022adec5dfa0be4d15ae79a2007f4d424b7aa1d29522d8319e9312", EXPECTED_COMPARISON_ORDER_SHA256),
    ("all_91_must_pass", "all_92_must_pass"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign061_no_return_audit_runtime",
}
exec(compile(_source, str(BASE_AUDIT), "exec"), _generated)
_runtime: dict[str, Any] = _generated["_runtime"]
_inner_runtime: dict[str, Any] = _runtime["_runtime"]
_audit_engine: dict[str, Any] = _runtime["_audit_engine"]

from scripts import a_share_three_day_walkforward_campaign060_no_return_audit as c60_audit


Campaign061NoReturnAuditError = _runtime["Campaign061NoReturnAuditError"]
candidate = _runtime["candidate"]
prior_audit = _runtime["prior_audit"]
candidate._validate_manifest = candidate._runtime["_validate_manifest"]
DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT: Path = _runtime["DEFAULT_EXPERIMENT_ROOT"]
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_061_feature_snapshot_binding_20260805.json"
)
SNAPSHOT_MANIFEST_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign061_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign061_feature_library_v1/snapshot_manifest.json"
)
EXPECTED_ROWS = int(_runtime["EXPECTED_ROWS"])
EXPECTED_PARTITIONS = int(_runtime["EXPECTED_PARTITIONS"])

for _name, _value in {
    "SNAPSHOT_BINDING": SNAPSHOT_BINDING,
    "SNAPSHOT_MANIFEST_PATH": SNAPSHOT_MANIFEST_PATH,
    "SNAPSHOT_BINDING_SHA256": SNAPSHOT_BINDING_SHA256,
    "SNAPSHOT_MANIFEST_SHA256": SNAPSHOT_MANIFEST_SHA256,
    "SNAPSHOT_DATASET_SHA256": SNAPSHOT_DATASET_SHA256,
    "EXPECTED_ELIGIBLE_ROWS": EXPECTED_ELIGIBLE_ROWS,
    "EXPECTED_COMPARISON_COUNT": EXPECTED_COMPARISON_COUNT,
    "EXPECTED_COMPARISON_ORDER_SHA256": EXPECTED_COMPARISON_ORDER_SHA256,
}.items():
    _runtime[_name] = _value
    _inner_runtime["_generated"][_name] = _value
    _audit_engine[_name] = _value


def _require_finalized_identities() -> None:
    if EXPECTED_ELIGIBLE_ROWS < 0 or any(
        value.startswith("__")
        for value in (
            SNAPSHOT_BINDING_SHA256,
            SNAPSHOT_MANIFEST_SHA256,
            SNAPSHOT_DATASET_SHA256,
        )
    ):
        raise Campaign061NoReturnAuditError(
            "Campaign061 audit identities are not frozen"
        )


def _load_protocol() -> dict[str, Any]:
    spec = json.loads(json.dumps(candidate.load_protocol()))
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    comparisons = candidate.reconstruct_comparisons(spec)
    if (
        len(comparisons) != EXPECTED_COMPARISON_COUNT
        or candidate._comparison_order_digest(comparisons)
        != EXPECTED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign061NoReturnAuditError("Campaign061 comparison order changed")
    gate["comparison_factors"] = comparisons
    return spec


_base_verify_static_bindings = _runtime["_base_verify_static_bindings"]


def verify_static_bindings() -> dict[str, Any]:
    _require_finalized_identities()
    result = _base_verify_static_bindings()
    calendar = candidate.DEFAULT_CALENDAR.resolve()
    if not calendar.is_file() or _local_sha256(calendar) != candidate.CALENDAR_SHA256:
        raise Campaign061NoReturnAuditError("Campaign061 accepted calendar changed")
    return {**result, "calendar_sha256": candidate.CALENDAR_SHA256}


def _load_bound_prior_snapshots(workers: int) -> dict[str, Any]:
    snapshots = c60_audit._load_bound_prior_snapshots(workers)
    path = C60_SNAPSHOT_PATH.resolve()
    if not path.is_file() or _local_sha256(path) != C60_SNAPSHOT_SHA256:
        raise Campaign061NoReturnAuditError("Campaign060 terminal snapshot changed")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("dataset_sha256") != C60_DATASET_SHA256:
        raise Campaign061NoReturnAuditError("Campaign060 snapshot dataset changed")
    verification = c60_audit.candidate.verify_snapshot_files(path, workers=workers)
    return {
        **snapshots,
        "c60_manifest": manifest,
        "c60_verification": verification,
    }


def _append_all_prior_comparisons(
    *,
    data_root: Path,
    workers: int,
    keys: Any,
    values: Any,
    gate: dict[str, Any],
    directions: dict[str, str],
    snapshots: dict[str, Any],
    engine: Any,
    candidate49: Any,
    comparison_engine: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    comparisons, verifications = c60_audit._append_all_prior_comparisons(
        data_root=data_root,
        workers=workers,
        keys=keys,
        values=values,
        gate=gate,
        directions=directions,
        snapshots=snapshots,
        engine=engine,
        candidate49=candidate49,
        comparison_engine=comparison_engine,
    )
    comparison_values = engine._load_filtered_comparison_values_explicit(
        snapshots["c60_manifest"], [C60_FACTOR], keys
    )[C60_FACTOR]
    comparisons.append(
        comparison_engine._aligned_comparison_result(
            candidate_keys=keys,
            candidate_values=values,
            comparison_values=comparison_values,
            comparison=C60_FACTOR,
            direction=directions[C60_FACTOR],
            gate=gate,
        )
    )
    del comparison_values
    gc.collect()
    return comparisons, {
        **verifications,
        "campaign060_snapshot_file_verification": snapshots["c60_verification"],
    }


for _name, _value in {
    "_load_protocol": _load_protocol,
    "verify_static_bindings": verify_static_bindings,
    "_load_bound_prior_snapshots": _load_bound_prior_snapshots,
    "_append_all_prior_comparisons": _append_all_prior_comparisons,
}.items():
    _runtime[_name] = _value
    _inner_runtime["_generated"][_name] = _value
    _audit_engine[_name] = _value

_base_run_no_return_audit = _runtime["_base_run_no_return_audit"]


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    destination = _base_run_no_return_audit(
        data_root=data_root,
        experiment_root=experiment_root,
        workers=workers,
    )
    record = json.loads(destination.read_text(encoding="utf-8"))
    factor_result = (record.get("uniqueness") or {}).get(FACTOR_NAME) or {}
    comparisons_loaded = bool(
        factor_result.get("comparison_values_loaded_after_coverage_pass")
    )
    record.update(
        {
            "minute_candidate_fields_in_bound_snapshot": ["close"],
            "cross_session_calendar_lag_in_bound_snapshot": 1,
            "market_benchmark_fields_in_bound_snapshot": [],
            "quarterly_candidate_fields_in_bound_snapshot": [],
            "quarterly_comparison_fields_read": (
                list(c60_audit.c59_audit.c58_audit.QUALITY_SOURCE_FIELDS)
                if comparisons_loaded
                else []
            ),
            "minute_open_high_low_volume_or_amount_fields_read": [],
            "candidate49_historical_return_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "provider_request_issued_by_campaign061_audit": False,
        }
    )
    _, foundation, _, _, _, _ = prior_audit.terminal.campaign044._context()
    foundation.atomic_write_json(record, destination)
    return destination


for _name, _value in {
    "run_no_return_audit": run_no_return_audit,
}.items():
    _runtime[_name] = _value
    _inner_runtime["_generated"][_name] = _value
    _audit_engine[_name] = _value

load_candidate_frame = _inner_runtime["_generated"]["load_candidate_frame"]
status = _inner_runtime["_generated"]["status"]
main = _inner_runtime["_generated"]["main"]


if __name__ == "__main__":
    raise SystemExit(main())
