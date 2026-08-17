#!/usr/bin/env python3
"""Run the frozen coverage-first Campaign069 no-return audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import a_share_three_day_walkforward_campaign068_features as c68
from scripts import a_share_three_day_walkforward_campaign068_features_v2 as c68_v2
from scripts import a_share_three_day_walkforward_campaign069_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_069/no_return"
)
SNAPSHOT_MANIFEST_PATH = candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_069_feature_snapshot_binding_20260806.json"
)
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_069_no_return_audit_implementation_freeze_20260806.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_069_no_return_audit_activation_binding_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign069_no_return_audit.py"
)
EXPECTED_ROWS = 7_724_498
EXPECTED_PARTITIONS = 33_015
EXPECTED_COMPARISON_COUNT = 99
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.COMPARISON_ORDER_SHA256
EXPECTED_COMPLETE_DEFINITION_COUNT = 100
EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256 = candidate.FULL_DEFINITION_ORDER_SHA256
CACHE_PUBLICATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_v4_publication_binding_20260806.json"
)
CACHE_PUBLICATION_BINDING_SHA256 = candidate.CACHE_PUBLICATION_BINDING_SHA256
CACHE_MANIFEST_PATH = cache_v4.DEFAULT_OUTPUT_ROOT / "snapshot_manifest.json"
CACHE_MANIFEST_SHA256 = candidate.CACHE_MANIFEST_SHA256
CACHE_DATASET_SHA256 = candidate.CACHE_DATASET_SHA256
C68_SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_068_feature_snapshot_binding_v2_20260806.json"
)
C68_SNAPSHOT_BINDING_SHA256 = candidate.C68_SNAPSHOT_BINDING_SHA256
C68_SNAPSHOT_MANIFEST_PATH = c68_v2.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C68_SNAPSHOT_MANIFEST_SHA256 = candidate.C68_SNAPSHOT_MANIFEST_SHA256
C68_SNAPSHOT_DATASET_SHA256 = candidate.C68_SNAPSHOT_DATASET_SHA256
STRUCTURALLY_NONNUMERIC_FACTOR = (
    "intraday_cross_sectional_standardized_return_state_stability_236p"
)


class Campaign069NoReturnAuditError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign069NoReturnAuditError(f"{label} changed")


def load_protocol() -> dict[str, Any]:
    spec = candidate.load_protocol()
    comparisons = candidate.reconstruct_comparisons(spec)
    layout = cache_v4._library_layout()
    expected_comparisons = [
        {
            "name": str(item["name"]),
            "score_direction": str(item["score_direction"]),
        }
        for item in layout["definitions"]
    ]
    expected_comparisons.append(
        {"name": candidate.C68_FACTOR, "score_direction": "higher"}
    )
    complete = [
        {
            "name": str(item["name"]),
            "score_direction": str(item["score_direction"]),
        }
        for item in layout["complete_definitions"]
    ]
    complete.append({"name": candidate.C68_FACTOR, "score_direction": "higher"})
    if not (
        comparisons == expected_comparisons
        and len(comparisons) == EXPECTED_COMPARISON_COUNT
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
        raise Campaign069NoReturnAuditError("Campaign069 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return spec


def _load_audit_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign069NoReturnAuditError("audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = record.get("audit_runner") or {}
    tests = record.get("tests") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign069_no_return_audit_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign069_source_rows_candidate_values_coverage_metrics_or_comparison_values"
        and runner.get("path")
        == "scripts/a_share_three_day_walkforward_campaign069_no_return_audit.py"
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and tests.get("path")
        == "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign069_no_return_audit.py"
        and tests.get("sha256") == _sha256(TEST_PATH)
        and record.get("candidate_snapshot_existed_before_freeze") is False
        and record.get("campaign069_source_or_candidate_values_read_before_freeze")
        is False
        and record.get("coverage_or_capacity_metrics_computed_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get("historical_daily_price_fields_read_before_freeze") == []
        and record.get("historical_forward_returns_read_before_freeze") is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign069NoReturnAuditError("audit implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    freeze = _load_audit_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign069NoReturnAuditError("audit activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    binding = record.get("snapshot_binding") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign069_no_return_audit_activation_binding"
        and record.get("status")
        == "frozen_after_independent_snapshot_verification_before_coverage_metrics_or_comparison_values"
        and (record.get("implementation_freeze") or {}).get("sha256")
        == _sha256(AUDIT_IMPLEMENTATION_FREEZE)
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST_PATH.resolve())
        and snapshot.get("sha256") == _sha256(SNAPSHOT_MANIFEST_PATH)
        and binding.get("path")
        == "docs/a_share_three_day_walkforward_campaign_069_feature_snapshot_binding_20260806.json"
        and binding.get("sha256") == _sha256(SNAPSHOT_BINDING)
        and record.get("candidate_snapshot_fully_verified_before_activation") is True
        and record.get("coverage_or_capacity_metrics_computed_before_activation") is False
        and record.get("comparison_values_read_before_activation") is False
        and record.get("historical_daily_price_fields_read_before_activation") == []
        and record.get("historical_forward_returns_read_before_activation") is False
        and record.get("provider_request_issued_before_activation") is False
        and freeze.get("candidate_snapshot_existed_before_freeze") is False
    ):
        raise Campaign069NoReturnAuditError("audit activation binding changed")
    return record


def verify_static_bindings() -> dict[str, Any]:
    activation = _load_activation_binding()
    snapshot = activation["candidate_snapshot"]
    _require(SNAPSHOT_BINDING, activation["snapshot_binding"]["sha256"], "snapshot binding")
    _require(SNAPSHOT_MANIFEST_PATH, snapshot["sha256"], "candidate snapshot")
    _require(
        CACHE_PUBLICATION_BINDING,
        CACHE_PUBLICATION_BINDING_SHA256,
        "compact-cache publication binding",
    )
    _require(CACHE_MANIFEST_PATH, CACHE_MANIFEST_SHA256, "compact-cache manifest")
    _require(
        C68_SNAPSHOT_BINDING,
        C68_SNAPSHOT_BINDING_SHA256,
        "Campaign068 snapshot binding",
    )
    _require(
        C68_SNAPSHOT_MANIFEST_PATH,
        C68_SNAPSHOT_MANIFEST_SHA256,
        "Campaign068 snapshot manifest",
    )
    binding = candidate.bindings.validate_record(
        SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT
    )
    if binding.get("all_bindings_passed") is not True:
        raise Campaign069NoReturnAuditError("snapshot binding validation failed")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    cache_manifest = json.loads(CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    c68_manifest = json.loads(C68_SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    layout = cache_v4._library_layout()
    cache_v4.load_protocol()
    cache_v4._validate_manifest(cache_manifest, layout)
    comparisons = candidate.reconstruct_comparisons(load_protocol())
    if not (
        manifest.get("dataset_sha256") == snapshot.get("dataset_sha256")
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        == snapshot.get("eligible_rows")
        and cache_manifest.get("dataset_sha256") == CACHE_DATASET_SHA256
        and cache_manifest.get("logical_numeric_comparator_count") == 98
        and c68_manifest.get("dataset_sha256") == C68_SNAPSHOT_DATASET_SHA256
        and c68_manifest.get("factor_names") == [candidate.C68_FACTOR]
        and len(comparisons) == EXPECTED_COMPARISON_COUNT
    ):
        raise Campaign069NoReturnAuditError("static snapshot identity changed")
    return {
        "audit_implementation_freeze_sha256": _sha256(AUDIT_IMPLEMENTATION_FREEZE),
        "audit_activation_binding_sha256": _sha256(AUDIT_ACTIVATION_BINDING),
        "snapshot_binding_sha256": activation["snapshot_binding"]["sha256"],
        "candidate_manifest_sha256": snapshot["sha256"],
        "candidate_dataset_sha256": snapshot["dataset_sha256"],
        "candidate_eligible_rows": snapshot["eligible_rows"],
        "compact_cache_publication_binding_sha256": CACHE_PUBLICATION_BINDING_SHA256,
        "compact_cache_manifest_sha256": CACHE_MANIFEST_SHA256,
        "compact_cache_dataset_sha256": CACHE_DATASET_SHA256,
        "campaign068_snapshot_binding_sha256": C68_SNAPSHOT_BINDING_SHA256,
        "campaign068_manifest_sha256": C68_SNAPSHOT_MANIFEST_SHA256,
        "campaign068_dataset_sha256": C68_SNAPSHOT_DATASET_SHA256,
        "complete_definition_count": EXPECTED_COMPLETE_DEFINITION_COUNT,
        "complete_definition_order_sha256": EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256,
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": EXPECTED_COMPARISON_ORDER_SHA256,
        "structurally_nonnumeric_mechanism_challenge": STRUCTURALLY_NONNUMERIC_FACTOR,
        "comparator_values_read": False,
    }


def _install_frozen_candidate_range(engine: Any) -> None:
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    if FACTOR_NAME in ranges and tuple(ranges[FACTOR_NAME]) != (-1.0, 1.0):
        raise Campaign069NoReturnAuditError("conflicting Campaign069 factor range")
    ranges[FACTOR_NAME] = (-1.0, 1.0)
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
    if coverage.get("gate_passed_before_comparison_values") is not True:
        raise Campaign069NoReturnAuditError(
            "comparison values forbidden before all coverage gates pass"
        )
    cache_receipt = cache_v4.verify_cache(CACHE_MANIFEST_PATH, full_equivalence=False)
    manifest = json.loads(CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    layout = cache_v4._library_layout()
    cache_keys, physical_matrix = cache_v4.v1._load_cache_matrix(
        root=CACHE_MANIFEST_PATH.parent,
        records=list(manifest["files"]),
        names=list(layout["physical_names"]),
    )
    positions = np.searchsorted(cache_keys, candidate_keys, side="left")
    if not (
        np.all(positions < len(cache_keys))
        and np.array_equal(cache_keys[positions], candidate_keys)
    ):
        raise Campaign069NoReturnAuditError("compact cache misses candidate keys")
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

    c68_verification = c68_v2.verify_snapshot_files(
        C68_SNAPSHOT_MANIFEST_PATH, workers=workers
    )
    c68_manifest = json.loads(C68_SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    c68_frame = engine.load_factor_frame(
        C68_SNAPSHOT_MANIFEST_PATH, c68_manifest, candidate.C68_FACTOR
    )
    c68_keys, c68_values = engine._sorted_candidate_arrays(
        c68_frame, candidate.C68_FACTOR
    )
    del c68_frame
    c68_positions = np.searchsorted(c68_keys, candidate_keys, side="left")
    if not (
        np.all(c68_positions < len(c68_keys))
        and np.array_equal(c68_keys[c68_positions], candidate_keys)
    ):
        raise Campaign069NoReturnAuditError("Campaign068 snapshot misses candidate keys")
    comparisons.append(
        comparison_engine._aligned_comparison_result(
            candidate_keys=candidate_keys,
            candidate_values=candidate_values,
            comparison_values=c68_values[c68_positions],
            comparison=candidate.C68_FACTOR,
            direction="higher",
            gate=gate,
        )
    )
    del c68_keys, c68_values, c68_positions
    gc.collect()
    return comparisons, {
        "compact_cache": cache_receipt,
        "compact_cache_dynamic_quality_values_rebuilt_after_candidate_intersection": True,
        "campaign068_snapshot": c68_verification,
        "campaign068_values_loaded_after_coverage_pass": True,
        "all_99_sources_loaded_in_frozen_order": True,
    }


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    static = verify_static_bindings()
    spec = load_protocol()
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign069NoReturnAuditError("Campaign069 data root changed")
    experiment_root = experiment_root.expanduser().resolve()
    if list(experiment_root.glob("*_campaign069_no_return_audit.json")):
        raise Campaign069NoReturnAuditError("Campaign069 no-return audit already exists")

    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    verification = candidate.verify_snapshot_files(
        SNAPSHOT_MANIFEST_PATH, workers=workers
    )
    prior, foundation, engine, _, _, comparison_engine = (
        cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    _install_frozen_candidate_range(engine)
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    candidate_frame = engine.load_factor_frame(
        SNAPSHOT_MANIFEST_PATH, manifest, FACTOR_NAME
    )
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate_frame, eligible_keys, spec, FACTOR_NAME
    )
    del candidate_frame, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        expected_order = [str(item["name"]) for item in gate["comparison_factors"]]
        keys, values = engine._sorted_candidate_arrays(quality_frame, FACTOR_NAME)
        comparisons, source_receipt = _load_comparisons_after_coverage(
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
        passed = (
            observed_order == expected_order
            and len(comparisons) == EXPECTED_COMPARISON_COUNT
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": len(comparisons),
            "comparison_order_matches_preregistration": observed_order
            == expected_order,
            "comparison_source_verification": source_receipt,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": max(
                correlations
            )
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
            "campaign068_comparator_values_read": False,
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
    run_id = f"{timestamp}_campaign069_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign069_no_return_audit",
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
            "sha256": static["candidate_manifest_sha256"],
            "dataset_sha256": static["candidate_dataset_sha256"],
        },
        "snapshot_binding": {
            "path": str(SNAPSHOT_BINDING.resolve()),
            "sha256": static["snapshot_binding_sha256"],
        },
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": "freeze the exact one-trial Campaign069 walk-forward before reading 2019-2023 returns"
        if admitted
        else "record the no-return rejection and begin only a genuinely new historical campaign",
        "quarterly_source_fields_read": list(candidate.EVENT_FIELDS),
        "stock_day_identity_fields_read": ["trade_date", "symbol", "provider"],
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "training_or_model_fitting_performed": False,
        "provider_request_issued": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "current_listing_snapshot_survivorship_limitation": True,
        "current_quarterly_snapshot_revision_limitation": True,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    audits = sorted(
        experiment_root.expanduser().resolve().glob("*_campaign069_no_return_audit.json")
    )
    return {
        "audit_implementation_freeze_exists": AUDIT_IMPLEMENTATION_FREEZE.is_file(),
        "audit_activation_binding_exists": AUDIT_ACTIVATION_BINDING.is_file(),
        "candidate_snapshot_exists": SNAPSHOT_MANIFEST_PATH.is_file(),
        "audit_count": len(audits),
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
    if args.command == "status":
        payload: Any = status(args.experiment_root)
    else:
        payload = {
            "audit": str(
                run_no_return_audit(
                    data_root=args.data_root,
                    experiment_root=args.experiment_root,
                    workers=args.workers,
                )
            )
        }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
