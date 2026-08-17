#!/usr/bin/env python3
"""Snapshot-bound Campaign059 ordered no-return audit implementation."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_AUDIT = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign058_no_return_audit.py"
BASE_AUDIT_SHA256 = "84bf18ce4ccda2292235bd86cbc7be707560e04622ede15d0dfd2747ef79f8a0"
BASE_FACTOR = "quarterly_profit_revenue_growth_spread_pp"
FACTOR_NAME = "intraday_market_directional_sign_agreement_238m"
EXPECTED_COMPARISON_COUNT = 90
EXPECTED_COMPARISON_ORDER_SHA256 = "09bc36308ce5d3af7a484fd9b233a02a9f5d3f37cd5169d400ab72737071caee"
SNAPSHOT_BINDING_SHA256 = "9d8c277c68531ea2b2155e983c633d36c197ecb47109bb9043f3e162ad445d9a"
SNAPSHOT_MANIFEST_SHA256 = "478597c0b06fe6d777dac906b6b70dc95f9b6e0a498c5f0e5eabf271dc2de9e6"
SNAPSHOT_DATASET_SHA256 = "53f0c782633885f150ff1625e2b75ebb3b27e9f6e53e58c2e133718ebebf5293"
EXPECTED_ELIGIBLE_ROWS = 7_583_771

C58_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign058_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign058_feature_library_v1/snapshot_manifest.json"
)
C58_SNAPSHOT_SHA256 = "c5bf57a70a2af71f30be87eec254710db65550f5dd7e041f219e862b4d97c00f"
C58_DATASET_SHA256 = "59fb5ed46c76a4737bbc60de9707f7f3b10223b692de4f4a88fec4143891cd4c"
C58_FACTOR = "quarterly_profit_revenue_growth_spread_pp"


def _local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _local_sha256(BASE_AUDIT) != BASE_AUDIT_SHA256:
    raise RuntimeError("frozen Campaign058 no-return audit changed")

_source = BASE_AUDIT.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign058", "Campaign059"),
    ("campaign058", "campaign059"),
    ("campaign_058", "campaign_059"),
    (BASE_FACTOR, FACTOR_NAME),
    ("0cf92fd4c788a2250eb6b9359062e92908b7c17663b47732445d28c56cb9cf65", SNAPSHOT_BINDING_SHA256),
    ("c5bf57a70a2af71f30be87eec254710db65550f5dd7e041f219e862b4d97c00f", SNAPSHOT_MANIFEST_SHA256),
    ("59fb5ed46c76a4737bbc60de9707f7f3b10223b692de4f4a88fec4143891cd4c", SNAPSHOT_DATASET_SHA256),
    ("EXPECTED_ELIGIBLE_ROWS = 7_231_483", "EXPECTED_ELIGIBLE_ROWS = 7_583_771"),
    ("EXPECTED_COMPARISON_COUNT = 89", "EXPECTED_COMPARISON_COUNT = 90"),
    ("c4100bc923fad2ea5fb8898ccb102afe44307c8ab03ee2df8b0972d9b71bbbc1", EXPECTED_COMPARISON_ORDER_SHA256),
    ('"minute_open_high_low_close_volume_fields_read": [],', '"minute_open_high_low_close_volume_fields_read": ["close"],'),
):
    _source = _source.replace(_old, _new)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign059_no_return_audit_runtime",
}
exec(compile(_source, str(BASE_AUDIT), "exec"), _runtime)
_audit_engine: dict[str, Any] = _runtime["_audit_engine"]

from scripts import a_share_three_day_walkforward_campaign058_no_return_audit as c58_audit


Campaign059NoReturnAuditError = _runtime["Campaign059NoReturnAuditError"]
candidate = _runtime["candidate"]
prior_audit = _runtime["prior_audit"]
DEFAULT_DATA_ROOT = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = _runtime["DEFAULT_EXPERIMENT_ROOT"]
SNAPSHOT_BINDING = _runtime["SNAPSHOT_BINDING"]
SNAPSHOT_MANIFEST_PATH = _runtime["SNAPSHOT_MANIFEST_PATH"]
EXPECTED_ROWS = _runtime["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _runtime["EXPECTED_PARTITIONS"]

for _name, _value in {
    "SNAPSHOT_BINDING_SHA256": SNAPSHOT_BINDING_SHA256,
    "SNAPSHOT_MANIFEST_SHA256": SNAPSHOT_MANIFEST_SHA256,
    "SNAPSHOT_DATASET_SHA256": SNAPSHOT_DATASET_SHA256,
    "EXPECTED_ELIGIBLE_ROWS": EXPECTED_ELIGIBLE_ROWS,
    "EXPECTED_COMPARISON_COUNT": EXPECTED_COMPARISON_COUNT,
    "EXPECTED_COMPARISON_ORDER_SHA256": EXPECTED_COMPARISON_ORDER_SHA256,
}.items():
    _runtime["_generated"][_name] = _value
    _audit_engine[_name] = _value


def _audit_require_file(path: Path, expected_sha256: str, label: str) -> None:
    path = path.expanduser().resolve()
    if not path.is_file() or _local_sha256(path) != expected_sha256:
        raise Campaign059NoReturnAuditError(f"{label} changed: {path}")


def _load_protocol() -> dict[str, Any]:
    spec = json.loads(json.dumps(candidate.load_protocol()))
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    comparisons = candidate.reconstruct_comparisons(spec)
    if (
        len(comparisons) != EXPECTED_COMPARISON_COUNT
        or candidate._comparison_order_digest(comparisons)
        != EXPECTED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign059NoReturnAuditError("Campaign059 comparison order changed")
    gate["comparison_factors"] = comparisons
    return spec


_runtime["_generated"]["_require_file"] = _audit_require_file
_runtime["_generated"]["_load_protocol"] = _load_protocol
_audit_engine["_require_file"] = _audit_require_file
_audit_engine["_load_protocol"] = _load_protocol


def _require_finalized_identities() -> None:
    values = (
        SNAPSHOT_BINDING_SHA256,
        SNAPSHOT_MANIFEST_SHA256,
        SNAPSHOT_DATASET_SHA256,
    )
    if EXPECTED_ELIGIBLE_ROWS < 0 or any(value.startswith("__") for value in values):
        raise Campaign059NoReturnAuditError("Campaign059 audit identities are not frozen")


_base_verify_static_bindings = _runtime["_base_verify_static_bindings"]


def verify_static_bindings() -> dict[str, Any]:
    _require_finalized_identities()
    result = _base_verify_static_bindings()
    source_chain = _load_protocol().get("source_chain") or {}
    benchmark_manifest = source_chain.get("frozen_market_benchmark_manifest") or {}
    benchmark_frame = source_chain.get("frozen_market_benchmark_frame") or {}
    for path, expected, label in (
        (
            DEFAULT_DATA_ROOT / str(benchmark_manifest.get("path_below_data_root") or ""),
            candidate.MARKET_BENCHMARK_MANIFEST_SHA256,
            "market benchmark manifest",
        ),
        (
            DEFAULT_DATA_ROOT / str(benchmark_frame.get("path_below_data_root") or ""),
            candidate.MARKET_BENCHMARK_BYTE_SHA256,
            "market benchmark frame",
        ),
        (candidate.DEFAULT_CALENDAR, candidate.CALENDAR_SHA256, "accepted calendar"),
    ):
        if not path.is_file() or _local_sha256(path) != expected:
            raise Campaign059NoReturnAuditError(f"Campaign059 {label} changed: {path}")
    return {
        **result,
        "market_benchmark_manifest_sha256": candidate.MARKET_BENCHMARK_MANIFEST_SHA256,
        "market_benchmark_byte_sha256": candidate.MARKET_BENCHMARK_BYTE_SHA256,
        "market_benchmark_frame_sha256": candidate.MARKET_BENCHMARK_FRAME_SHA256,
        "calendar_sha256": candidate.CALENDAR_SHA256,
    }


def _load_bound_prior_snapshots(workers: int) -> dict[str, Any]:
    snapshots = c58_audit._load_bound_prior_snapshots(workers)
    path = C58_SNAPSHOT_PATH.resolve()
    if not path.is_file() or _local_sha256(path) != C58_SNAPSHOT_SHA256:
        raise Campaign059NoReturnAuditError("Campaign058 terminal snapshot changed")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("dataset_sha256") != C58_DATASET_SHA256:
        raise Campaign059NoReturnAuditError("Campaign058 snapshot dataset changed")
    verification = c58_audit.candidate.verify_snapshot_files(path, workers=workers)
    return {
        **snapshots,
        "c58_manifest": manifest,
        "c58_verification": verification,
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
    comparisons, verifications = c58_audit._append_all_prior_comparisons(
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
    c58_values = engine._load_filtered_comparison_values_explicit(
        snapshots["c58_manifest"], [C58_FACTOR], keys
    )[C58_FACTOR]
    comparisons.append(
        comparison_engine._aligned_comparison_result(
            candidate_keys=keys,
            candidate_values=values,
            comparison_values=c58_values,
            comparison=C58_FACTOR,
            direction=directions[C58_FACTOR],
            gate=gate,
        )
    )
    del c58_values
    gc.collect()
    return comparisons, {
        **verifications,
        "campaign058_snapshot_file_verification": snapshots["c58_verification"],
    }


for _name, _value in {
    "verify_static_bindings": verify_static_bindings,
    "_load_bound_prior_snapshots": _load_bound_prior_snapshots,
    "_append_all_prior_comparisons": _append_all_prior_comparisons,
}.items():
    _runtime["_generated"][_name] = _value
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
            "market_benchmark_fields_in_bound_snapshot": [
                "trade_date",
                "return_position",
                "return_sum",
                "valid_stock_count",
            ],
            "quarterly_candidate_fields_in_bound_snapshot": [],
            "quarterly_comparison_fields_read": (
                list(c58_audit.QUALITY_SOURCE_FIELDS) if comparisons_loaded else []
            ),
            "minute_open_high_low_volume_or_amount_fields_read": [],
            "candidate49_historical_return_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "provider_request_issued_by_campaign059_audit": False,
        }
    )
    prior, foundation, _, _, _, _ = prior_audit.terminal.campaign044._context()
    foundation.atomic_write_json(record, destination)
    return destination


_runtime["_generated"]["run_no_return_audit"] = run_no_return_audit
_audit_engine["run_no_return_audit"] = run_no_return_audit
load_candidate_frame = _runtime["_generated"]["load_candidate_frame"]
status = _runtime["_generated"]["status"]
main = _runtime["_generated"]["main"]


if __name__ == "__main__":
    raise SystemExit(main())
