#!/usr/bin/env python3
"""Run Campaign089's frozen coverage-first no-return uniqueness audit."""

from __future__ import annotations

import argparse
import gc
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import (
    a_share_three_day_walkforward_campaign088_no_return_audit as c88_audit,
)
from scripts import a_share_three_day_walkforward_campaign089_features as definitions

REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = definitions.FACTOR_NAME
DEFAULT_DATA_ROOT = definitions.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_089/no_return"
)
SNAPSHOT_MANIFEST_PATH = (
    definitions.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "3ab55cc6f61bebb6713aeacb9e54125c20183295b862717617be0b13c9d0a204"
)
SNAPSHOT_DATASET_SHA256 = (
    "c4f8794f42f1fffe2847ade875232827c8ca532a7fd75dd1123686c41456655a"
)
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_089_feature_snapshot_binding_20260807.json"
)
SNAPSHOT_BINDING_SHA256 = (
    "3d7fc48e6cbe0fae14300ba9d09004f72e0d11a9570c59f4550fa9c42f0f478a"
)
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_089_no_return_audit_implementation_freeze_20260807.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_089_no_return_audit_activation_binding_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign089_no_return_audit.py"
)
EXPECTED_ROWS = 1_331_759
EXPECTED_PARTITIONS = 7
EXPECTED_ELIGIBLE_ROWS = 1_327_577
EXPECTED_SESSIONS = 1_632
EXPECTED_COMPARISON_COUNT = 118
EXPECTED_COMPLETE_DEFINITION_COUNT = 120
STRUCTURALLY_NONNUMERIC_FACTOR = (
    "intraday_cross_sectional_standardized_return_state_stability_236p"
)
PREVALUE_TERMINAL_NONNUMERIC_FACTOR = "signal_day_turnover_rate_pct"
C88_MANIFEST_PATH = c88_audit.SNAPSHOT_MANIFEST_PATH
C88_MANIFEST_SHA256 = c88_audit.SNAPSHOT_MANIFEST_SHA256
C88_FACTOR_NAME = c88_audit.FACTOR_NAME


class Campaign089NoReturnAuditError(RuntimeError):
    """Fail-closed Campaign089 no-return audit error."""


def _sha256(path: Path) -> str:
    return definitions._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign089NoReturnAuditError(f"Campaign089 {label} changed: {path}")


def load_protocol() -> dict[str, Any]:
    spec = definitions.load_protocol()
    comparisons = definitions.reconstruct_comparisons()
    complete = definitions.reconstruct_complete_definitions()
    complete_names = [str(item["name"]) for item in complete]
    comparison_names = [str(item["name"]) for item in comparisons]
    if not (
        len(comparisons) == EXPECTED_COMPARISON_COUNT
        and definitions._comparison_order_digest(comparisons)
        == definitions.COMPARISON_ORDER_SHA256
        and len(complete) == EXPECTED_COMPLETE_DEFINITION_COUNT
        and definitions._comparison_order_digest(complete)
        == definitions.FULL_DEFINITION_ORDER_SHA256
        and STRUCTURALLY_NONNUMERIC_FACTOR in complete_names
        and STRUCTURALLY_NONNUMERIC_FACTOR not in comparison_names
        and PREVALUE_TERMINAL_NONNUMERIC_FACTOR in complete_names
        and PREVALUE_TERMINAL_NONNUMERIC_FACTOR not in comparison_names
        and comparisons[-1] == {"name": C88_FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign089NoReturnAuditError("Campaign089 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign089NoReturnAuditError("audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign089_no_return_audit_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign089_coverage_or_comparison_values"
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
        raise Campaign089NoReturnAuditError("audit implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign089NoReturnAuditError("audit activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign089_no_return_audit_activation_binding"
        and record.get("status")
        == "frozen_before_campaign089_coverage_or_comparison_values"
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
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_activation"
        )
        == []
        and record.get("historical_forward_returns_read_before_activation") is False
        and record.get("provider_request_issued_before_activation") is False
    ):
        raise Campaign089NoReturnAuditError("audit activation binding changed")
    return record


def verify_candidate_snapshot() -> dict[str, Any]:
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "candidate snapshot")
    result = definitions.verify_snapshot_files(SNAPSHOT_MANIFEST_PATH)
    if not (
        result.get("status") == "verified"
        and result.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and result.get("partitions") == EXPECTED_PARTITIONS
        and result.get("rows") == EXPECTED_ROWS
        and result.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and result.get("comparison_values_read") is False
    ):
        raise Campaign089NoReturnAuditError("candidate snapshot verification changed")
    return result


def verify_static_bindings() -> dict[str, Any]:
    _load_activation_binding()
    _require(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    report = definitions.bindings.validate_record(
        SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign089NoReturnAuditError("snapshot binding validation failed")
    return {
        "audit_implementation_freeze_sha256": _sha256(AUDIT_IMPLEMENTATION_FREEZE),
        "audit_activation_binding_sha256": _sha256(AUDIT_ACTIVATION_BINDING),
        "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256,
        "candidate_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": SNAPSHOT_DATASET_SHA256,
        "candidate_eligible_rows": EXPECTED_ELIGIBLE_ROWS,
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": definitions.COMPARISON_ORDER_SHA256,
        "complete_definition_count": EXPECTED_COMPLETE_DEFINITION_COUNT,
        "complete_definition_order_sha256": definitions.FULL_DEFINITION_ORDER_SHA256,
        "comparator_values_read": False,
    }


def load_candidate_arrays() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    keys: list[np.ndarray] = []
    values: list[np.ndarray] = []
    years: list[np.ndarray] = []
    for record in manifest.get("files") or []:
        frame = pd.read_parquet(
            SNAPSHOT_MANIFEST_PATH.parent / str(record["path"]),
            columns=["stock_day_key", FACTOR_NAME],
        )
        keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
        values.append(frame[FACTOR_NAME].to_numpy(dtype=np.float64))
        years.append(np.full(len(frame), int(record["year"]), dtype=np.int64))
    all_keys = np.concatenate(keys)
    all_values = np.concatenate(values)
    all_years = np.concatenate(years)
    if not (
        len(all_keys) == EXPECTED_ROWS
        and all_years.shape == all_keys.shape
        and len(np.unique(all_keys)) == EXPECTED_ROWS
        and np.all(all_keys[1:] > all_keys[:-1])
        and int(np.isfinite(all_values).sum()) == EXPECTED_ELIGIBLE_ROWS
        and np.array_equal(np.unique(all_years), np.arange(2019, 2026))
    ):
        raise Campaign089NoReturnAuditError("candidate arrays changed")
    return all_keys, all_values, all_years


def coverage_and_capacity(
    keys: np.ndarray,
    values: np.ndarray,
    years: np.ndarray,
    spec: dict[str, Any],
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    return c88_audit.coverage_and_capacity(keys, values, years, spec)


def _install_frozen_ranges(engine: Any) -> None:
    c88_audit._install_frozen_ranges(engine)
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    if FACTOR_NAME in ranges and tuple(ranges[FACTOR_NAME]) != (-1.0, 1.0):
        raise Campaign089NoReturnAuditError("conflicting Campaign089 range")
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
    comparisons, receipts = c88_audit._load_comparisons_after_coverage(
        coverage=coverage,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        engine=engine,
        comparison_engine=comparison_engine,
        workers=workers,
    )
    if len(comparisons) != 117:
        raise Campaign089NoReturnAuditError("first 117 comparison order changed")
    result, receipt = c88_audit.c87_audit._compact_snapshot_comparison(
        manifest_path=C88_MANIFEST_PATH,
        expected_manifest_sha256=C88_MANIFEST_SHA256,
        factor=C88_FACTOR_NAME,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        comparison_engine=comparison_engine,
        verifier=c88_audit.verify_candidate_snapshot,
    )
    comparisons.append(result)
    receipts["campaign088_compact_snapshot"] = receipt
    receipts.pop("all_117_sources_loaded_in_frozen_order", None)
    receipts["all_118_sources_loaded_in_frozen_order"] = True
    if not (
        len(comparisons) == EXPECTED_COMPARISON_COUNT
        and comparisons[-1]["comparison_factor"] == C88_FACTOR_NAME
    ):
        raise Campaign089NoReturnAuditError("Campaign089 comparison order changed")
    del result
    gc.collect()
    return comparisons, receipts


def _run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int, confirm_run: bool
) -> Path:
    if not confirm_run:
        raise Campaign089NoReturnAuditError("Campaign089 audit requires --confirm-run")
    static = verify_static_bindings()
    spec = load_protocol()
    if data_root.expanduser().resolve() != DEFAULT_DATA_ROOT.resolve():
        raise Campaign089NoReturnAuditError("Campaign089 data root changed")
    experiment_root = experiment_root.expanduser().resolve()
    if list(experiment_root.glob("*_campaign089_no_return_audit.json")):
        raise Campaign089NoReturnAuditError("Campaign089 audit already exists")
    verification = verify_candidate_snapshot()
    keys, values, years = load_candidate_arrays()
    coverage, finite_keys, finite_values = coverage_and_capacity(
        keys, values, years, spec
    )
    comparisons: list[dict[str, Any]] = []
    receipts: dict[str, Any] = {}
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        context = (
            cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
        )
        _, _, engine, _, _, comparison_engine = context
        _install_frozen_ranges(engine)
        comparisons, receipts = _load_comparisons_after_coverage(
            coverage=coverage,
            candidate_keys=finite_keys,
            candidate_values=finite_values,
            gate=gate,
            engine=engine,
            comparison_engine=comparison_engine,
            workers=workers,
        )
    all_comparisons_passed = bool(comparisons) and all(
        item.get("gate_passed") is True for item in comparisons
    )
    maximum_correlation = (
        max(
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item.get("absolute_median_daily_rank_correlation") is not None
        )
        if comparisons
        else None
    )
    admissible = int(
        coverage["gate_passed_before_comparison_values"]
        and all_comparisons_passed
        and len(comparisons) == EXPECTED_COMPARISON_COUNT
    )
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign089_no_return_audit",
        "status": (
            "completed_one_admissible_factor_ready_for_frozen_development_trial"
            if admissible
            else "completed_zero_admissible_factors_stop_before_historical_daily_prices_or_returns"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": f"{run_id}_campaign089_no_return_audit",
        "protocol": {
            "path": str(definitions.DEFAULT_PROTOCOL.resolve()),
            "sha256": definitions.PROTOCOL_SHA256,
        },
        "candidate_snapshot": {
            "path": str(SNAPSHOT_MANIFEST_PATH.resolve()),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": SNAPSHOT_DATASET_SHA256,
        },
        "static_bindings": static,
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {
            FACTOR_NAME: {
                "comparison_values_loaded_after_coverage_pass": bool(comparisons),
                "comparison_factor_count": len(comparisons),
                "comparison_order_matches_preregistration": (
                    [item["comparison_factor"] for item in comparisons]
                    == [
                        item["name"]
                        for item in spec["ordered_no_return_gates"][
                            "uniqueness_after_coverage_only"
                        ]["comparison_factors"]
                    ]
                    if comparisons
                    else False
                ),
                "all_required_numeric_comparisons_passed": all_comparisons_passed,
                "maximum_observed_absolute_median_daily_rank_correlation": maximum_correlation,
                "comparisons": comparisons,
                "comparison_source_verification": receipts,
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
        },
        "admissible_factor_count": admissible,
        "admissible_factor_names": [FACTOR_NAME] if admissible else [],
        "failed_factor_names": [] if admissible else [FACTOR_NAME],
        "next_action": (
            "freeze and run exactly the preregistered single development trial"
            if admissible
            else "record no-return rejection and begin only a genuinely new campaign"
        ),
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "training_or_model_fitting_performed": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "provider_request_issued": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "current_listing_snapshot_survivorship_limitation": True,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    path = experiment_root / f"{payload['run_id']}.json"
    definitions.c85._atomic_json(payload, path)
    return path


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    return {
        "status": (
            "ready_for_single_audit"
            if AUDIT_ACTIVATION_BINDING.is_file()
            else "activation_binding_absent"
        ),
        "candidate_snapshot_exists": SNAPSHOT_MANIFEST_PATH.is_file(),
        "audit_count": len(
            list(
                experiment_root.expanduser()
                .resolve()
                .glob("*_campaign089_no_return_audit.json")
            )
        ),
        "coverage_or_capacity_metrics_computed": False,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "run"))
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--confirm-run", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        print(json.dumps(status(args.experiment_root), sort_keys=True))
        return 0
    print(
        _run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
            confirm_run=args.confirm_run,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
