#!/usr/bin/env python3
"""Run Campaign073's frozen coverage-first, no-return uniqueness audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import a_share_three_day_walkforward_campaign068_features_v2 as c68
from scripts import a_share_three_day_walkforward_campaign069_features as c69
from scripts import a_share_three_day_walkforward_campaign070_features as c70
from scripts import a_share_three_day_walkforward_campaign071_features as c71
from scripts import a_share_three_day_walkforward_campaign072_features as c72
from scripts import a_share_three_day_walkforward_campaign073_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_073/no_return"
)
SNAPSHOT_MANIFEST_PATH = candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
SNAPSHOT_MANIFEST_SHA256 = "6b281be298be7df908300db6735e3ed3efc7d7c13b44c2ae679bf5a2073940e4"
SNAPSHOT_DATASET_SHA256 = "2cea2e0502be1c5cc70f93260a96175abac5f36af50482847c35746a80252a5f"
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_073_feature_snapshot_binding_20260806.json"
)
SNAPSHOT_BINDING_SHA256 = "0bf34d781cff79f9f8e8262173a78699232cfa5271bd12b2fb897a9173698ae7"
SEQUENCE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_073_audit_freeze_sequence_record_20260806.json"
)
SEQUENCE_RECORD_SHA256 = "3a424a8fb29ad2d691a2692d65b11e0dacf784a8b4cbf7755892ce8660489d52"
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_073_no_return_audit_implementation_freeze_20260806.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_073_no_return_audit_activation_binding_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign073_no_return_audit.py"
)
EXPECTED_ROWS = 7_724_498
EXPECTED_PARTITIONS = 33_015
EXPECTED_ELIGIBLE_ROWS = 7_724_498
EXPECTED_COMPARISON_COUNT = 103
EXPECTED_COMPLETE_DEFINITION_COUNT = 104
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.COMPARISON_ORDER_SHA256
EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256 = candidate.FULL_DEFINITION_ORDER_SHA256
CACHE_MANIFEST_PATH = cache_v4.DEFAULT_OUTPUT_ROOT / "snapshot_manifest.json"
C68_SNAPSHOT_MANIFEST_PATH = c68.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C69_SNAPSHOT_MANIFEST_PATH = c69.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C70_SNAPSHOT_MANIFEST_PATH = c70.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C71_SNAPSHOT_MANIFEST_PATH = c71.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C72_SNAPSHOT_MANIFEST_PATH = c72.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
STRUCTURALLY_NONNUMERIC_FACTOR = (
    "intraday_cross_sectional_standardized_return_state_stability_236p"
)


class Campaign073NoReturnAuditError(RuntimeError):
    """Fail-closed Campaign073 no-return audit error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign073NoReturnAuditError(f"{label} changed: {path}")


def load_protocol() -> dict[str, Any]:
    spec = candidate.load_protocol()
    comparisons = candidate.reconstruct_comparisons()
    complete = candidate.reconstruct_complete_definitions()
    if not (
        len(comparisons) == EXPECTED_COMPARISON_COUNT
        and candidate._comparison_order_digest(comparisons)
        == EXPECTED_COMPARISON_ORDER_SHA256
        and len(complete) == EXPECTED_COMPLETE_DEFINITION_COUNT
        and candidate._comparison_order_digest(complete)
        == EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256
        and STRUCTURALLY_NONNUMERIC_FACTOR
        in [str(item["name"]) for item in complete]
        and STRUCTURALLY_NONNUMERIC_FACTOR
        not in [str(item["name"]) for item in comparisons]
    ):
        raise Campaign073NoReturnAuditError("Campaign073 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign073NoReturnAuditError("audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign073_no_return_audit_implementation_freeze"
        and record.get("status")
        == "frozen_after_verified_snapshot_before_coverage_or_comparison_values"
        and (record.get("audit_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("sequence_record") or {}).get("sha256")
        == SEQUENCE_RECORD_SHA256
        and record.get("coverage_or_capacity_metrics_computed_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get("historical_daily_price_fields_read_before_freeze") == []
        and record.get("historical_forward_returns_read_before_freeze") is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign073NoReturnAuditError("audit implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign073NoReturnAuditError("audit activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign073_no_return_audit_activation_binding"
        and record.get("status") == "frozen_before_coverage_or_comparison_values"
        and (record.get("implementation_freeze") or {}).get("sha256")
        == _sha256(AUDIT_IMPLEMENTATION_FREEZE)
        and (record.get("snapshot_binding") or {}).get("sha256")
        == SNAPSHOT_BINDING_SHA256
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST_PATH.resolve())
        and snapshot.get("sha256") == SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and record.get("coverage_or_capacity_metrics_computed_before_activation")
        is False
        and record.get("comparison_values_read_before_activation") is False
        and record.get("historical_daily_price_fields_read_before_activation") == []
        and record.get("historical_forward_returns_read_before_activation") is False
        and record.get("provider_request_issued_before_activation") is False
    ):
        raise Campaign073NoReturnAuditError("audit activation binding changed")
    return record


def verify_static_bindings() -> dict[str, Any]:
    _load_activation_binding()
    _require(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "candidate snapshot")
    _require(SEQUENCE_RECORD, SEQUENCE_RECORD_SHA256, "sequence record")
    _require(CACHE_MANIFEST_PATH, candidate.CACHE_MANIFEST_SHA256, "compact cache")
    for path, expected, label in (
        (C68_SNAPSHOT_MANIFEST_PATH, candidate.C68_MANIFEST_SHA256, "Campaign068"),
        (C69_SNAPSHOT_MANIFEST_PATH, candidate.C69_MANIFEST_SHA256, "Campaign069"),
        (C70_SNAPSHOT_MANIFEST_PATH, candidate.C70_MANIFEST_SHA256, "Campaign070"),
        (C71_SNAPSHOT_MANIFEST_PATH, candidate.C71_MANIFEST_SHA256, "Campaign071"),
        (C72_SNAPSHOT_MANIFEST_PATH, candidate.C72_MANIFEST_SHA256, "Campaign072"),
    ):
        _require(path, expected, f"{label} snapshot manifest")
    report = candidate.bindings.validate_record(
        SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign073NoReturnAuditError("snapshot binding validation failed")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    if not (
        manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        == EXPECTED_ELIGIBLE_ROWS
        and len(candidate.reconstruct_comparisons()) == EXPECTED_COMPARISON_COUNT
    ):
        raise Campaign073NoReturnAuditError("static snapshot identity changed")
    return {
        "audit_implementation_freeze_sha256": _sha256(AUDIT_IMPLEMENTATION_FREEZE),
        "audit_activation_binding_sha256": _sha256(AUDIT_ACTIVATION_BINDING),
        "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256,
        "candidate_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": SNAPSHOT_DATASET_SHA256,
        "candidate_eligible_rows": EXPECTED_ELIGIBLE_ROWS,
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": EXPECTED_COMPARISON_ORDER_SHA256,
        "complete_definition_count": EXPECTED_COMPLETE_DEFINITION_COUNT,
        "complete_definition_order_sha256": EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256,
        "comparator_values_read": False,
    }


def _install_frozen_ranges(engine: Any) -> None:
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    expected = {
        FACTOR_NAME: (0.0, 1.0),
        candidate.C68_FACTOR: (-1.0, 1.0),
        candidate.C69_FACTOR: (-1.0, 1.0),
        candidate.C70_FACTOR: (0.0, 1.0),
        candidate.C71_FACTOR: (0.0, 1.0),
        candidate.C72_FACTOR: (0.0, 1.0),
    }
    for name, value_range in expected.items():
        if name in ranges and tuple(ranges[name]) != value_range:
            raise Campaign073NoReturnAuditError(f"conflicting range for {name}")
        ranges[name] = value_range
    engine.FACTOR_RANGES = ranges


def _sorted_comparator_arrays(
    frame: pd.DataFrame, factor: str, comparison_engine: Any
) -> tuple[np.ndarray, np.ndarray]:
    keys = comparison_engine._compact_stock_day_keys(
        frame["trade_date"], frame["symbol"]
    )
    values = pd.to_numeric(frame[factor], errors="coerce").to_numpy(dtype=float)
    order = np.argsort(keys, kind="stable")
    keys, values = keys[order], values[order]
    if len(np.unique(keys)) != len(keys):
        raise Campaign073NoReturnAuditError(f"{factor} comparator keys are not unique")
    return keys, values


def _append_snapshot_comparison(
    *,
    manifest_path: Path,
    factor: str,
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    gate: dict[str, Any],
    engine: Any,
    comparison_engine: Any,
    workers: int,
    verifier: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    verification = verifier(manifest_path, workers=workers)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frame = engine.load_factor_frame(manifest_path, manifest, factor)
    keys, values = _sorted_comparator_arrays(frame, factor, comparison_engine)
    del frame
    positions = np.searchsorted(keys, candidate_keys, side="left")
    if not (
        np.all(positions < len(keys))
        and np.array_equal(keys[positions], candidate_keys)
    ):
        raise Campaign073NoReturnAuditError(f"{factor} snapshot misses candidate keys")
    result = comparison_engine._aligned_comparison_result(
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        comparison_values=values[positions],
        comparison=factor,
        direction="higher",
        gate=gate,
    )
    del keys, values, positions
    gc.collect()
    return result, verification


def _load_comparisons_after_coverage(
    *,
    coverage: dict[str, Any],
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    gate: dict[str, Any],
    engine: Any,
    comparison_engine: Any,
    workers: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if coverage.get("gate_passed_before_comparison_values") is not True:
        raise Campaign073NoReturnAuditError(
            "comparison values forbidden before all coverage gates pass"
        )
    cache_receipt = cache_v4.verify_cache(CACHE_MANIFEST_PATH, full_equivalence=False)
    cache_manifest = json.loads(CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    layout = cache_v4._library_layout()
    cache_keys, physical_matrix = cache_v4.v1._load_cache_matrix(
        root=CACHE_MANIFEST_PATH.parent,
        records=list(cache_manifest["files"]),
        names=list(layout["physical_names"]),
    )
    positions = np.searchsorted(cache_keys, candidate_keys, side="left")
    if not (
        np.all(positions < len(cache_keys))
        and np.array_equal(cache_keys[positions], candidate_keys)
    ):
        raise Campaign073NoReturnAuditError("compact cache misses candidate keys")
    logical = cache_v4._logical_values_from_physical(
        candidate_keys=candidate_keys,
        candidate_positions=positions,
        physical_matrix=physical_matrix,
        layout=layout,
    )
    comparisons = [
        comparison_engine._aligned_comparison_result(
            candidate_keys=candidate_keys,
            candidate_values=candidate_values,
            comparison_values=logical[str(definition["name"])],
            comparison=str(definition["name"]),
            direction=str(definition["score_direction"]),
            gate=gate,
        )
        for definition in layout["definitions"]
    ]
    del logical, physical_matrix, cache_keys, positions
    gc.collect()
    receipts: dict[str, Any] = {
        "compact_cache": cache_receipt,
        "compact_cache_dynamic_quality_values_rebuilt_after_candidate_intersection": True,
    }
    append_specs = (
        (C68_SNAPSHOT_MANIFEST_PATH, candidate.C68_FACTOR, c68.verify_snapshot_files, "campaign068_snapshot"),
        (C69_SNAPSHOT_MANIFEST_PATH, candidate.C69_FACTOR, c69.verify_snapshot_files, "campaign069_snapshot"),
        (C70_SNAPSHOT_MANIFEST_PATH, candidate.C70_FACTOR, c70.verify_snapshot_files, "campaign070_snapshot"),
        (C71_SNAPSHOT_MANIFEST_PATH, candidate.C71_FACTOR, c71.verify_snapshot_files, "campaign071_snapshot"),
        (C72_SNAPSHOT_MANIFEST_PATH, candidate.C72_FACTOR, c72.verify_snapshot_files, "campaign072_snapshot"),
    )
    for manifest_path, factor, verifier, receipt_name in append_specs:
        result, receipt = _append_snapshot_comparison(
            manifest_path=manifest_path,
            factor=factor,
            candidate_keys=candidate_keys,
            candidate_values=candidate_values,
            gate=gate,
            engine=engine,
            comparison_engine=comparison_engine,
            workers=workers,
            verifier=verifier,
        )
        comparisons.append(result)
        receipts[receipt_name] = receipt
    receipts["all_103_sources_loaded_in_frozen_order"] = True
    if len(comparisons) != EXPECTED_COMPARISON_COUNT:
        raise Campaign073NoReturnAuditError("Campaign073 comparison count changed")
    return comparisons, receipts


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    static = verify_static_bindings()
    spec = load_protocol()
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign073NoReturnAuditError("Campaign073 data root changed")
    experiment_root = experiment_root.expanduser().resolve()
    if list(experiment_root.glob("*_campaign073_no_return_audit.json")):
        raise Campaign073NoReturnAuditError("Campaign073 no-return audit already exists")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    verification = candidate.verify_snapshot_files(
        SNAPSHOT_MANIFEST_PATH, workers=workers
    )
    prior, foundation, engine, _, _, comparison_engine = (
        cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    _install_frozen_ranges(engine)
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    frame = engine.load_factor_frame(SNAPSHOT_MANIFEST_PATH, manifest, FACTOR_NAME)
    quality_frame, coverage = engine.coverage_and_capacity(
        frame, eligible_keys, spec, FACTOR_NAME
    )
    del frame, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        expected_order = [str(item["name"]) for item in gate["comparison_factors"]]
        keys, values = engine._sorted_candidate_arrays(quality_frame, FACTOR_NAME)
        comparisons, receipts = _load_comparisons_after_coverage(
            coverage=coverage,
            candidate_keys=keys,
            candidate_values=values,
            gate=gate,
            engine=engine,
            comparison_engine=comparison_engine,
            workers=workers,
        )
        observed_order = [str(item["comparison_factor"]) for item in comparisons]
        correlations = [
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = bool(
            observed_order == expected_order
            and len(comparisons) == EXPECTED_COMPARISON_COUNT
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": len(comparisons),
            "comparison_order_matches_preregistration": observed_order == expected_order,
            "comparison_source_verification": receipts,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": max(correlations)
            if correlations
            else None,
            "all_required_numeric_comparisons_passed": passed,
            "structurally_nonnumeric_mechanism_challenges": [
                {
                    "name": STRUCTURALLY_NONNUMERIC_FACTOR,
                    "numeric_status": "undefined_not_pass_not_fail",
                    "mechanism_overlap_status": "explicitly_challenged_before_values",
                }
            ],
        }
        del keys, values
    else:
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": False,
            "comparison_factor_count": 0,
            "compact_cache_values_read": False,
            "campaign068_to_campaign072_comparator_values_read": False,
            "comparisons": [],
            "all_required_numeric_comparisons_passed": False,
            "failure_reason": "coverage_gate_failed",
            "structurally_nonnumeric_mechanism_challenges": [
                {
                    "name": STRUCTURALLY_NONNUMERIC_FACTOR,
                    "numeric_status": "undefined_not_pass_not_fail",
                    "mechanism_overlap_status": "explicitly_challenged_before_values",
                }
            ],
        }
    del quality_frame
    gc.collect()
    admitted = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_required_numeric_comparisons_passed"]
    )
    timestamp = prior.research._timestamp()
    run_id = f"{timestamp}_campaign073_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign073_no_return_audit",
        "status": "completed_with_one_admissible_factor_pending_walkforward_preregistration"
        if admitted
        else "completed_zero_admissible_factors_stop_before_historical_daily_prices_or_returns",
        "run_id": run_id,
        "created_at": prior.research._timestamp(),
        "protocol": {
            "path": str(candidate.DEFAULT_PROTOCOL.resolve()),
            "sha256": candidate.PROTOCOL_SHA256,
        },
        "static_bindings": static,
        "candidate_snapshot": {
            "path": str(SNAPSHOT_MANIFEST_PATH),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": SNAPSHOT_DATASET_SHA256,
        },
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": "freeze and run the exact one Campaign073 development trial"
        if admitted
        else "record this no-return rejection and begin only a genuinely new campaign",
        "minute_source_fields_read": list(candidate.RAW_COLUMNS),
        "stock_day_identity_fields_read": list(candidate.IDENTITY_COLUMNS),
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "training_or_model_fitting_performed": False,
        "provider_request_issued": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "current_listing_snapshot_survivorship_limitation": True,
        "current_quarterly_snapshot_revision_limitation_for_comparators": True,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    audits = sorted(
        experiment_root.expanduser().resolve().glob("*_campaign073_no_return_audit.json")
    )
    return {
        "audit_implementation_freeze_exists": AUDIT_IMPLEMENTATION_FREEZE.is_file(),
        "audit_activation_binding_exists": AUDIT_ACTIVATION_BINDING.is_file(),
        "candidate_snapshot_exists": SNAPSHOT_MANIFEST_PATH.is_file(),
        "audit_count": len(audits),
        "coverage_or_capacity_metrics_computed_by_status": False,
        "comparison_values_read_by_status": False,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "provider_request_issued": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("status")
    inspect.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    run = sub.add_parser("run")
    run.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    run.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    run.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    payload: Any = (
        status(args.experiment_root)
        if args.command == "status"
        else {
            "audit": str(
                run_no_return_audit(
                    data_root=args.data_root,
                    experiment_root=args.experiment_root,
                    workers=args.workers,
                )
            )
        }
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
