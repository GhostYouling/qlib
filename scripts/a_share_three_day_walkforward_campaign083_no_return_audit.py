#!/usr/bin/env python3
"""Run Campaign083's frozen coverage-first no-return uniqueness audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import (
    a_share_three_day_walkforward_campaign082_no_return_audit as c82_audit,
)
from scripts import a_share_three_day_walkforward_campaign083_features as candidate

REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_083/no_return"
)
SNAPSHOT_MANIFEST_PATH = (
    candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "e462a154f2da5374be671955b04d0e70b2bc02821a397e978e346dca75bf0618"
)
SNAPSHOT_DATASET_SHA256 = (
    "b9b9a54d1a1a040d22cae0dbabe1cdb556312a97f604efe1da38e437478cde52"
)
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_083_feature_snapshot_binding_20260806.json"
)
SNAPSHOT_BINDING_SHA256 = (
    "6a37b02574f506e4f2043b91788bef9c8a93e3535985867293531bde22be5b2c"
)
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_083_no_return_audit_implementation_freeze_20260806.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_083_no_return_audit_activation_binding_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign083_no_return_audit.py"
)
EXPECTED_ROWS = 7_724_498
EXPECTED_PARTITIONS = 33_015
EXPECTED_ELIGIBLE_ROWS = 7_724_498
EXPECTED_COMPARISON_COUNT = 112
EXPECTED_COMPLETE_DEFINITION_COUNT = 114
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.COMPARISON_ORDER_SHA256
EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256 = candidate.FULL_DEFINITION_ORDER_SHA256
C82_SNAPSHOT_MANIFEST_PATH = candidate.C82_MANIFEST_PATH
STRUCTURALLY_NONNUMERIC_FACTOR = (
    "intraday_cross_sectional_standardized_return_state_stability_236p"
)
PREVALUE_TERMINAL_NONNUMERIC_FACTOR = "signal_day_turnover_rate_pct"


class Campaign083NoReturnAuditError(RuntimeError):
    """Fail-closed Campaign083 no-return audit error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign083NoReturnAuditError(f"{label} changed: {path}")


def load_protocol() -> dict[str, Any]:
    spec = candidate.load_protocol()
    comparisons = candidate.reconstruct_comparisons()
    complete = candidate.reconstruct_complete_definitions()
    complete_names = [str(item["name"]) for item in complete]
    comparison_names = [str(item["name"]) for item in comparisons]
    if not (
        len(comparisons) == EXPECTED_COMPARISON_COUNT
        and candidate._comparison_order_digest(comparisons)
        == EXPECTED_COMPARISON_ORDER_SHA256
        and len(complete) == EXPECTED_COMPLETE_DEFINITION_COUNT
        and candidate._comparison_order_digest(complete)
        == EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256
        and STRUCTURALLY_NONNUMERIC_FACTOR in complete_names
        and STRUCTURALLY_NONNUMERIC_FACTOR not in comparison_names
        and PREVALUE_TERMINAL_NONNUMERIC_FACTOR in complete_names
        and PREVALUE_TERMINAL_NONNUMERIC_FACTOR not in comparison_names
    ):
        raise Campaign083NoReturnAuditError("Campaign083 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign083NoReturnAuditError("audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign083_no_return_audit_implementation_freeze"
        and record.get("status")
        == "frozen_after_verified_snapshot_before_coverage_or_comparison_values"
        and (record.get("audit_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("snapshot_binding") or {}).get("sha256")
        == SNAPSHOT_BINDING_SHA256
        and record.get("coverage_or_capacity_metrics_computed_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get("historical_daily_price_fields_read_before_freeze") == []
        and record.get("historical_forward_returns_read_before_freeze") is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign083NoReturnAuditError("audit implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign083NoReturnAuditError("audit activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign083_no_return_audit_activation_binding"
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
        raise Campaign083NoReturnAuditError("audit activation binding changed")
    return record


def verify_candidate_snapshot(*, workers: int = 4) -> dict[str, Any]:
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "candidate snapshot")
    result = candidate.verify_snapshot_files(SNAPSHOT_MANIFEST_PATH, workers=workers)
    if not (
        result.get("status") == "verified"
        and result.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and result.get("partitions") == EXPECTED_PARTITIONS
        and result.get("rows") == EXPECTED_ROWS
        and result.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and result.get("comparison_values_read") is False
    ):
        raise Campaign083NoReturnAuditError("candidate snapshot verification changed")
    return result


def verify_campaign082_snapshot(*, workers: int = 4) -> dict[str, Any]:
    return c82_audit.verify_candidate_snapshot(workers=workers)


def verify_static_bindings() -> dict[str, Any]:
    _load_activation_binding()
    _require(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "candidate snapshot")
    _require(
        C82_SNAPSHOT_MANIFEST_PATH,
        candidate.C82_MANIFEST_SHA256,
        "Campaign082 snapshot",
    )
    report = candidate.bindings.validate_record(
        SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign083NoReturnAuditError("snapshot binding validation failed")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    if not (
        manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        == EXPECTED_ELIGIBLE_ROWS
        and len(candidate.reconstruct_comparisons()) == EXPECTED_COMPARISON_COUNT
    ):
        raise Campaign083NoReturnAuditError("static snapshot identity changed")
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
    c82_audit._install_frozen_ranges(engine)
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    if FACTOR_NAME in ranges and tuple(ranges[FACTOR_NAME]) != (0.0, 1.0):
        raise Campaign083NoReturnAuditError("conflicting Campaign083 range")
    ranges[FACTOR_NAME] = (0.0, 1.0)
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
    comparisons, receipts = c82_audit._load_comparisons_after_coverage(
        coverage=coverage,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        engine=engine,
        comparison_engine=comparison_engine,
        workers=workers,
    )
    helper = (
        c82_audit.c81_audit.c80_audit.c78_audit.c77_audit.c76_audit.c75_v5.v4.v3.v1.base.base._append_snapshot_comparison
    )
    result, receipt = helper(
        manifest_path=C82_SNAPSHOT_MANIFEST_PATH,
        factor=candidate.C82_FACTOR,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        engine=engine,
        comparison_engine=comparison_engine,
        workers=workers,
        verifier=lambda _path, workers=workers: verify_campaign082_snapshot(
            workers=workers
        ),
    )
    comparisons.append(result)
    receipts["campaign082_snapshot"] = receipt
    receipts.pop("all_111_sources_loaded_in_frozen_order", None)
    receipts["all_112_sources_loaded_in_frozen_order"] = True
    if len(comparisons) != EXPECTED_COMPARISON_COUNT:
        raise Campaign083NoReturnAuditError("Campaign083 comparison count changed")
    return comparisons, receipts


def _run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    static = verify_static_bindings()
    spec = load_protocol()
    if data_root.expanduser().resolve() != DEFAULT_DATA_ROOT.resolve():
        raise Campaign083NoReturnAuditError("Campaign083 data root changed")
    experiment_root = experiment_root.expanduser().resolve()
    if list(experiment_root.glob("*_campaign083_no_return_audit.json")):
        raise Campaign083NoReturnAuditError(
            "Campaign083 no-return audit already exists"
        )
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    verification = verify_candidate_snapshot(workers=workers)
    context = (
        cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    prior, foundation, engine, _, _, comparison_engine = context
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
            "comparison_order_matches_preregistration": observed_order
            == expected_order,
            "comparison_source_verification": receipts,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": (
                max(correlations) if correlations else None
            ),
            "all_required_numeric_comparisons_passed": passed,
            "structurally_nonnumeric_mechanism_challenges": [
                {
                    "name": STRUCTURALLY_NONNUMERIC_FACTOR,
                    "numeric_status": "undefined_not_pass_not_fail",
                    "mechanism_overlap_status": "explicitly_challenged_before_values",
                },
                {
                    "name": PREVALUE_TERMINAL_NONNUMERIC_FACTOR,
                    "numeric_status": "ineligible_no_values_exist",
                    "mechanism_overlap_status": "explicitly_challenged_before_values",
                },
            ],
        }
    else:
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": False,
            "comparison_factor_count": 0,
            "comparisons": [],
            "all_required_numeric_comparisons_passed": False,
            "failure_reason": "coverage_gate_failed",
            "structurally_nonnumeric_mechanism_challenges": [
                {
                    "name": STRUCTURALLY_NONNUMERIC_FACTOR,
                    "numeric_status": "undefined_not_pass_not_fail",
                    "mechanism_overlap_status": "explicitly_challenged_before_values",
                },
                {
                    "name": PREVALUE_TERMINAL_NONNUMERIC_FACTOR,
                    "numeric_status": "ineligible_no_values_exist",
                    "mechanism_overlap_status": "explicitly_challenged_before_values",
                },
            ],
        }
    del quality_frame
    gc.collect()
    admitted = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_required_numeric_comparisons_passed"]
    )
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{timestamp}_campaign083_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign083_no_return_audit",
        "status": (
            "completed_with_one_admissible_factor_pending_walkforward_preregistration"
            if admitted
            else "completed_zero_admissible_factors_stop_before_historical_daily_prices_or_returns"
        ),
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
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
        "next_action": (
            "freeze and run the exact one Campaign083 development trial"
            if admitted
            else "record this no-return rejection and begin only a genuinely new campaign"
        ),
        "candidate_source_fields_read": list(candidate.RAW_COLUMNS),
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
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    """Run once with the frozen legacy comparison-runtime binding."""

    repair = c82_audit.c81_audit.c80_audit.c78_audit.c77_audit_v2
    repair.load_repair_protocol()
    repair.load_repair_protocol()
    with repair._temporary_runtime_version_binding():
        return _run_no_return_audit(
            data_root=data_root, experiment_root=experiment_root, workers=workers
        )


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    audits = sorted(
        experiment_root.expanduser()
        .resolve()
        .glob("*_campaign083_no_return_audit.json")
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
    run = sub.add_parser("run")
    run.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    run.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    run.add_argument("--workers", type=int, default=4)
    inspect = sub.add_parser("status")
    inspect.add_argument(
        "--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT
    )
    args = parser.parse_args()
    payload = (
        {
            "audit": str(
                run_no_return_audit(
                    data_root=args.data_root,
                    experiment_root=args.experiment_root,
                    workers=args.workers,
                )
            )
        }
        if args.command == "run"
        else status(args.experiment_root)
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
