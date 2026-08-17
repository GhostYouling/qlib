#!/usr/bin/env python3
"""Run Campaign075's frozen coverage-first, no-return uniqueness audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import a_share_three_day_walkforward_campaign074_features as c74_features
from scripts import a_share_three_day_walkforward_campaign074_no_return_audit as base
from scripts import a_share_three_day_walkforward_campaign075_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_075/no_return"
)
SNAPSHOT_MANIFEST_PATH = candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
SNAPSHOT_MANIFEST_SHA256 = "d621c73d8f32fa0187c0b8f834a170548eeb8deb04e1fade7a12da08f160aef4"
SNAPSHOT_DATASET_SHA256 = "63b3bd548fa3f2d7f88e19542eb6be5e4ee7cc6f9d83f5dc874868efade98936"
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_feature_snapshot_binding_20260806.json"
)
SNAPSHOT_BINDING_SHA256 = "c57aaeecc579a2cf6ad86e4c8b1c21fe19c0de4e933cd3e4cd3ad9e8863fc146"
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_no_return_audit_implementation_freeze_20260806.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_no_return_audit_activation_binding_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign075_no_return_audit.py"
)
EXPECTED_ROWS = 7_724_498
EXPECTED_PARTITIONS = 33_015
EXPECTED_ELIGIBLE_ROWS = 7_689_881
EXPECTED_COMPARISON_COUNT = 105
EXPECTED_COMPLETE_DEFINITION_COUNT = 106
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.COMPARISON_ORDER_SHA256
EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256 = candidate.FULL_DEFINITION_ORDER_SHA256
C74_SNAPSHOT_MANIFEST_PATH = candidate.C74_MANIFEST_PATH
STRUCTURALLY_NONNUMERIC_FACTOR = (
    "intraday_cross_sectional_standardized_return_state_stability_236p"
)


class Campaign075NoReturnAuditError(RuntimeError):
    """Fail-closed Campaign075 no-return audit error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign075NoReturnAuditError(f"{label} changed: {path}")


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
        raise Campaign075NoReturnAuditError("Campaign075 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign075NoReturnAuditError("audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign075_no_return_audit_implementation_freeze"
        and record.get("status")
        == "frozen_after_verified_snapshot_before_coverage_or_comparison_values"
        and (record.get("audit_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("snapshot_binding") or {}).get("sha256")
        == SNAPSHOT_BINDING_SHA256
        and record.get("coverage_or_capacity_metrics_computed_before_freeze")
        is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get("historical_daily_price_fields_read_before_freeze") == []
        and record.get("historical_forward_returns_read_before_freeze") is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign075NoReturnAuditError("audit implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign075NoReturnAuditError("audit activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign075_no_return_audit_activation_binding"
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
        raise Campaign075NoReturnAuditError("audit activation binding changed")
    return record


def verify_static_bindings() -> dict[str, Any]:
    _load_activation_binding()
    _require(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "candidate snapshot")
    _require(C74_SNAPSHOT_MANIFEST_PATH, candidate.C74_MANIFEST_SHA256, "Campaign074 snapshot")
    report = candidate.bindings.validate_record(
        SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign075NoReturnAuditError("snapshot binding validation failed")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    c74_manifest = json.loads(C74_SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    if not (
        manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        == EXPECTED_ELIGIBLE_ROWS
        and c74_manifest.get("dataset_sha256") == candidate.C74_DATASET_SHA256
        and len(candidate.reconstruct_comparisons()) == EXPECTED_COMPARISON_COUNT
    ):
        raise Campaign075NoReturnAuditError("static snapshot identity changed")
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
    base._install_frozen_ranges(engine)
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    expected = {
        FACTOR_NAME: (-float(np.finfo(np.float64).max), -20.0),
        candidate.C74_FACTOR: (0.0, 1.0),
    }
    for name, value_range in expected.items():
        if name in ranges and tuple(ranges[name]) != value_range:
            raise Campaign075NoReturnAuditError(f"conflicting range for {name}")
        ranges[name] = value_range
    engine.FACTOR_RANGES = ranges


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
    comparisons, receipts = base._load_comparisons_after_coverage(
        coverage=coverage,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        engine=engine,
        comparison_engine=comparison_engine,
        workers=workers,
    )
    result, receipt = base.base._append_snapshot_comparison(
        manifest_path=C74_SNAPSHOT_MANIFEST_PATH,
        factor=candidate.C74_FACTOR,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        engine=engine,
        comparison_engine=comparison_engine,
        workers=workers,
        verifier=c74_features.verify_snapshot_files,
    )
    comparisons.append(result)
    receipts["campaign074_snapshot"] = receipt
    receipts.pop("all_104_sources_loaded_in_frozen_order", None)
    receipts["all_105_sources_loaded_in_frozen_order"] = True
    if len(comparisons) != EXPECTED_COMPARISON_COUNT:
        raise Campaign075NoReturnAuditError("Campaign075 comparison count changed")
    return comparisons, receipts


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    static = verify_static_bindings()
    spec = load_protocol()
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign075NoReturnAuditError("Campaign075 data root changed")
    experiment_root = experiment_root.expanduser().resolve()
    if list(experiment_root.glob("*_campaign075_no_return_audit.json")):
        raise Campaign075NoReturnAuditError("Campaign075 no-return audit already exists")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    verification = candidate.verify_snapshot_files(SNAPSHOT_MANIFEST_PATH, workers=workers)
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
            "campaign068_to_campaign074_comparator_values_read": False,
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
    run_id = f"{timestamp}_campaign075_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign075_no_return_audit",
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
        "next_action": "freeze and run the exact one Campaign075 development trial"
        if admitted
        else "record this no-return rejection and begin only a genuinely new campaign",
        "candidate_source_fields_read": [
            "instrument",
            "accepted_instrument_start_date",
            "accepted_instrument_end_date",
        ],
        "stock_day_identity_fields_read": list(candidate.IDENTITY_COLUMNS),
        "campaign074_factor_values_read_for_candidate_materialization": False,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "training_or_model_fitting_performed": False,
        "provider_request_issued": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "current_listing_snapshot_survivorship_limitation": True,
        "accepted_instrument_start_left_censoring_limitation": True,
        "current_quarterly_snapshot_revision_limitation_for_comparators": True,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    audits = sorted(
        experiment_root.expanduser().resolve().glob("*_campaign075_no_return_audit.json")
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
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    run.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    run.add_argument("--workers", type=int, default=4)
    inspect = subparsers.add_parser("status")
    inspect.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    args = parser.parse_args()
    if args.command == "run":
        payload = {
            "audit": str(
                run_no_return_audit(
                    data_root=args.data_root,
                    experiment_root=args.experiment_root,
                    workers=args.workers,
                )
            )
        }
    else:
        payload = status(args.experiment_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
