#!/usr/bin/env python3
"""Snapshot-bound Campaign060 ordered no-return audit implementation."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_AUDIT = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign059_no_return_audit.py"
BASE_AUDIT_SHA256 = "8c24d2e973b00d9a13f98435795703d79be1eb8279565976a57d540d6ee6953b"
BASE_FACTOR = "intraday_market_directional_sign_agreement_238m"
FACTOR_NAME = "intraday_day_over_day_directional_return_agreement_238b"
EXPECTED_COMPARISON_COUNT = 91
EXPECTED_COMPARISON_ORDER_SHA256 = "abbf08eef9022adec5dfa0be4d15ae79a2007f4d424b7aa1d29522d8319e9312"
SNAPSHOT_BINDING_SHA256 = "6226c6381bd5b11eec41061c99e906fb736acbb70c922831bf81d9ed974682bd"
SNAPSHOT_MANIFEST_SHA256 = "3f328039fb7806c66a260a7fd723a3297e2e0ce5ba23e9bb11f39d963e7250cd"
SNAPSHOT_DATASET_SHA256 = "052e5c8e5090c173c1e9486b545eafaa3b1301e038c1acc72434222e683d5735"
EXPECTED_ELIGIBLE_ROWS = 5_878_602

C59_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign059_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign059_feature_library_v1/snapshot_manifest.json"
)
C59_SNAPSHOT_SHA256 = "478597c0b06fe6d777dac906b6b70dc95f9b6e0a498c5f0e5eabf271dc2de9e6"
C59_DATASET_SHA256 = "53f0c782633885f150ff1625e2b75ebb3b27e9f6e53e58c2e133718ebebf5293"
C59_FACTOR = "intraday_market_directional_sign_agreement_238m"


def _local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _local_sha256(BASE_AUDIT) != BASE_AUDIT_SHA256:
    raise RuntimeError("frozen Campaign059 no-return audit changed")

_source = BASE_AUDIT.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign059", "Campaign060"),
    ("campaign059", "campaign060"),
    ("campaign_059", "campaign_060"),
    (BASE_FACTOR, FACTOR_NAME),
    ("9d8c277c68531ea2b2155e983c633d36c197ecb47109bb9043f3e162ad445d9a", SNAPSHOT_BINDING_SHA256),
    ("478597c0b06fe6d777dac906b6b70dc95f9b6e0a498c5f0e5eabf271dc2de9e6", SNAPSHOT_MANIFEST_SHA256),
    ("53f0c782633885f150ff1625e2b75ebb3b27e9f6e53e58c2e133718ebebf5293", SNAPSHOT_DATASET_SHA256),
    ("EXPECTED_ELIGIBLE_ROWS = 7_583_771", "EXPECTED_ELIGIBLE_ROWS = 5_878_602"),
    ("EXPECTED_COMPARISON_COUNT = 90", "EXPECTED_COMPARISON_COUNT = 91"),
    ("09bc36308ce5d3af7a484fd9b233a02a9f5d3f37cd5169d400ab72737071caee", EXPECTED_COMPARISON_ORDER_SHA256),
    ("all_90_must_pass", "all_91_must_pass"),
):
    _source = _source.replace(_old, _new)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign060_no_return_audit_runtime",
}
exec(compile(_source, str(BASE_AUDIT), "exec"), _runtime)
_inner_runtime: dict[str, Any] = _runtime["_runtime"]
_audit_engine: dict[str, Any] = _runtime["_audit_engine"]

from scripts import a_share_three_day_walkforward_campaign059_no_return_audit as c59_audit


Campaign060NoReturnAuditError = _runtime["Campaign060NoReturnAuditError"]
candidate = _runtime["candidate"]
prior_audit = _runtime["prior_audit"]
candidate._validate_manifest = candidate._runtime["_validate_manifest"]
DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT: Path = _runtime["DEFAULT_EXPERIMENT_ROOT"]
SNAPSHOT_BINDING: Path = _runtime["SNAPSHOT_BINDING"]
SNAPSHOT_MANIFEST_PATH: Path = _runtime["SNAPSHOT_MANIFEST_PATH"]
EXPECTED_ROWS = int(_runtime["EXPECTED_ROWS"])
EXPECTED_PARTITIONS = int(_runtime["EXPECTED_PARTITIONS"])

for _name, _value in {
    "SNAPSHOT_BINDING_SHA256": SNAPSHOT_BINDING_SHA256,
    "SNAPSHOT_MANIFEST_SHA256": SNAPSHOT_MANIFEST_SHA256,
    "SNAPSHOT_DATASET_SHA256": SNAPSHOT_DATASET_SHA256,
    "EXPECTED_ELIGIBLE_ROWS": EXPECTED_ELIGIBLE_ROWS,
    "EXPECTED_COMPARISON_COUNT": EXPECTED_COMPARISON_COUNT,
    "EXPECTED_COMPARISON_ORDER_SHA256": EXPECTED_COMPARISON_ORDER_SHA256,
}.items():
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
        raise Campaign060NoReturnAuditError(
            "Campaign060 audit identities are not frozen"
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
        raise Campaign060NoReturnAuditError("Campaign060 comparison order changed")
    gate["comparison_factors"] = comparisons
    return spec


_base_verify_static_bindings = _runtime["_base_verify_static_bindings"]


def verify_static_bindings() -> dict[str, Any]:
    _require_finalized_identities()
    result = _base_verify_static_bindings()
    calendar = candidate.DEFAULT_CALENDAR.resolve()
    if not calendar.is_file() or _local_sha256(calendar) != candidate.CALENDAR_SHA256:
        raise Campaign060NoReturnAuditError("Campaign060 accepted calendar changed")
    return {**result, "calendar_sha256": candidate.CALENDAR_SHA256}


def _load_bound_prior_snapshots(workers: int) -> dict[str, Any]:
    snapshots = c59_audit._load_bound_prior_snapshots(workers)
    path = C59_SNAPSHOT_PATH.resolve()
    if not path.is_file() or _local_sha256(path) != C59_SNAPSHOT_SHA256:
        raise Campaign060NoReturnAuditError("Campaign059 terminal snapshot changed")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("dataset_sha256") != C59_DATASET_SHA256:
        raise Campaign060NoReturnAuditError("Campaign059 snapshot dataset changed")
    verification = c59_audit.candidate.verify_snapshot_files(path, workers=workers)
    return {
        **snapshots,
        "c59_manifest": manifest,
        "c59_verification": verification,
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
    comparisons, verifications = c59_audit._append_all_prior_comparisons(
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
        snapshots["c59_manifest"], [C59_FACTOR], keys
    )[C59_FACTOR]
    comparisons.append(
        comparison_engine._aligned_comparison_result(
            candidate_keys=keys,
            candidate_values=values,
            comparison_values=comparison_values,
            comparison=C59_FACTOR,
            direction=directions[C59_FACTOR],
            gate=gate,
        )
    )
    del comparison_values
    gc.collect()
    return comparisons, {
        **verifications,
        "campaign059_snapshot_file_verification": snapshots["c59_verification"],
    }


for _name, _value in {
    "_load_protocol": _load_protocol,
    "verify_static_bindings": verify_static_bindings,
    "_load_bound_prior_snapshots": _load_bound_prior_snapshots,
    "_append_all_prior_comparisons": _append_all_prior_comparisons,
}.items():
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
                list(c59_audit.c58_audit.QUALITY_SOURCE_FIELDS)
                if comparisons_loaded
                else []
            ),
            "minute_open_high_low_volume_or_amount_fields_read": [],
            "candidate49_historical_return_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "provider_request_issued_by_campaign060_audit": False,
        }
    )
    _, foundation, _, _, _, _ = prior_audit.terminal.campaign044._context()
    foundation.atomic_write_json(record, destination)
    return destination


for _name, _value in {
    "run_no_return_audit": run_no_return_audit,
}.items():
    _inner_runtime["_generated"][_name] = _value
    _audit_engine[_name] = _value

load_candidate_frame = _inner_runtime["_generated"]["load_candidate_frame"]
status = _inner_runtime["_generated"]["status"]
main = _inner_runtime["_generated"]["main"]


if __name__ == "__main__":
    raise SystemExit(main())
