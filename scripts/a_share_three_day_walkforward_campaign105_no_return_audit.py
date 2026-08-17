#!/usr/bin/env python3
"""Run Campaign105's frozen coverage-first all-131 no-return audit."""

from __future__ import annotations

import argparse
import gc
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import a_share_three_day_walkforward_campaign102_design as c102
from scripts import a_share_three_day_walkforward_campaign103_features as c103
from scripts import a_share_three_day_walkforward_campaign105_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_105/no_return"
)
SNAPSHOT_MANIFEST_PATH = (
    candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_feature_snapshot_binding_20260808.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_no_return_audit_activation_binding_20260808.json"
)

C102_MANIFEST_PATH = c103.C102_MANIFEST_PATH
C102_MANIFEST_SHA256 = c103.C102_MANIFEST_SHA256
C102_DATASET_SHA256 = c103.C102_DATASET_SHA256
C103_MANIFEST_PATH = c103.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C103_MANIFEST_SHA256 = (
    "8a939feb53edfb31be8f133c2683920ed13424e716a4f4b5ed0d1a300588603b"
)
C103_DATASET_SHA256 = "57afdd9f8a246fb9f513f85b3b631f70cf734655bd226ff211201bf7e084ea13"
C103_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_103_feature_snapshot_binding_20260807.json"
)
C103_BINDING_SHA256 = "86f9f76a6a5d98db1826a8f58d3a4a9e2a165e9d7e74b89bc72298eaed3351a3"

EXPECTED_ROWS = candidate.EXPECTED_ROWS
EXPECTED_PARTITIONS = candidate.EXPECTED_PARTITIONS
EXPECTED_COMPARISON_COUNT = candidate.NUMERIC_COMPARATOR_COUNT
COMPARISON_BATCH_SIZE = 8


class Campaign105NoReturnAuditError(RuntimeError):
    """Fail closed when Campaign105's ordered no-return boundary changes."""


def _sha256(path: Path) -> str:
    return candidate._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or _sha256(resolved) != expected:
        raise Campaign105NoReturnAuditError(f"Campaign105 {label} changed: {resolved}")


def load_protocol() -> dict[str, Any]:
    """Return a runtime view of the frozen prose gates without reading values."""

    frozen = candidate.load_protocol()
    gates = list(frozen.get("ordered_no_return_gates") or [])
    if [item.get("gate") for item in gates] != [1, 2, 3]:
        raise Campaign105NoReturnAuditError("Campaign105 gate order changed")
    coverage_text = str(gates[1].get("rule") or "")
    uniqueness_text = str(gates[2].get("rule") or "")
    if not (
        ">=0.95" in coverage_text
        and ">=0.90" in coverage_text
        and ">=50" in coverage_text
        and "at least 200" in coverage_text
        and "at least five" in coverage_text
        and "at least 50" in uniqueness_text
        and "at least 100" in uniqueness_text
        and "strictly below 0.8" in uniqueness_text
    ):
        raise Campaign105NoReturnAuditError("Campaign105 numeric gate text changed")
    comparisons = candidate.reconstruct_comparisons()
    runtime = json.loads(json.dumps(frozen))
    runtime["frozen_ordered_no_return_gates"] = runtime["ordered_no_return_gates"]
    runtime["ordered_no_return_gates"] = {
        "coverage_and_capacity_before_comparison_values": {
            "holding_period_sessions": 3,
            "minimum_median_coverage": 0.95,
            "minimum_p05_coverage": 0.90,
            "minimum_p05_eligible_names": 50,
            "minimum_non_overlapping_three_session_cohorts": 200,
            "minimum_observed_calendar_years": 5,
        },
        "uniqueness_after_coverage_only": {
            "comparison_factors": comparisons,
            "minimum_pairwise_names_per_session": 50,
            "minimum_pairwise_sessions_per_comparison": 100,
            "maximum_allowed_absolute_median_daily_rank_correlation": 0.8,
            "all_numeric_comparators_must_pass": True,
            "insufficient_pairwise_overlap_fails_closed": True,
        },
    }
    return runtime


def _load_activation_binding() -> dict[str, Any]:
    candidate._validate_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign105NoReturnAuditError("Campaign105 audit activation is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    binding = record.get("snapshot_binding") or {}
    c102_source = record.get("first_130_directional_comparators") or {}
    c103_source = record.get("final_comparator") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign105_no_return_audit_activation_binding"
        and record.get("status")
        == "frozen_after_verified_candidate_snapshot_before_coverage_or_comparator_values"
        and (record.get("implementation_freeze") or {}).get("sha256")
        == _sha256(candidate.DEFAULT_IMPLEMENTATION_FREEZE)
        and binding.get("path") == str(SNAPSHOT_BINDING.relative_to(REPO_ROOT))
        and len(str(binding.get("sha256") or "")) == 64
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST_PATH.resolve())
        and len(str(snapshot.get("sha256") or "")) == 64
        and len(str(snapshot.get("dataset_sha256") or "")) == 64
        and snapshot.get("partitions") == EXPECTED_PARTITIONS
        and snapshot.get("rows") == EXPECTED_ROWS
        and 0 <= int(snapshot.get("eligible_rows", -1)) <= EXPECTED_ROWS
        and c102_source.get("path") == str(C102_MANIFEST_PATH)
        and c102_source.get("sha256") == C102_MANIFEST_SHA256
        and c102_source.get("dataset_sha256") == C102_DATASET_SHA256
        and c102_source.get("factor_count") == 130
        and c103_source.get("path") == str(C103_MANIFEST_PATH)
        and c103_source.get("sha256") == C103_MANIFEST_SHA256
        and c103_source.get("dataset_sha256") == C103_DATASET_SHA256
        and c103_source.get("factor") == c103.FACTOR_NAME
        and record.get("coverage_or_capacity_metrics_computed_before_activation")
        is False
        and record.get("comparator_values_read_before_activation") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_activation"
        )
        is False
        and record.get("provider_request_issued_before_activation") is False
        and record.get("single_use") is True
    ):
        raise Campaign105NoReturnAuditError("Campaign105 activation semantics changed")
    return record


def verify_static_bindings() -> dict[str, Any]:
    activation = _load_activation_binding()
    snapshot_binding = activation["snapshot_binding"]
    _require(
        SNAPSHOT_BINDING,
        str(snapshot_binding["sha256"]),
        "candidate snapshot binding",
    )
    _require(C102_MANIFEST_PATH, C102_MANIFEST_SHA256, "Campaign102 matrix manifest")
    _require(C103_MANIFEST_PATH, C103_MANIFEST_SHA256, "Campaign103 manifest")
    _require(C103_BINDING, C103_BINDING_SHA256, "Campaign103 snapshot binding")
    report = candidate.bindings.validate_record(
        SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign105NoReturnAuditError("Campaign105 snapshot binding failed")
    return {
        "implementation_freeze_sha256": _sha256(
            candidate.DEFAULT_IMPLEMENTATION_FREEZE
        ),
        "audit_activation_binding_sha256": _sha256(AUDIT_ACTIVATION_BINDING),
        "snapshot_binding_sha256": snapshot_binding["sha256"],
        "candidate_manifest_sha256": activation["candidate_snapshot"]["sha256"],
        "candidate_dataset_sha256": activation["candidate_snapshot"]["dataset_sha256"],
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": candidate.NUMERIC_COMPARATOR_ORDER_SHA256,
        "complete_definition_count": candidate.COMPLETE_DEFINITION_COUNT,
        "complete_definition_order_sha256": candidate.COMPLETE_DEFINITION_ORDER_SHA256,
        "comparator_values_read": False,
    }


def verify_candidate_snapshot(*, workers: int = 4) -> dict[str, Any]:
    activation = _load_activation_binding()
    expected = activation["candidate_snapshot"]
    _require(SNAPSHOT_MANIFEST_PATH, str(expected["sha256"]), "candidate snapshot")
    result = candidate.verify_snapshot_files(SNAPSHOT_MANIFEST_PATH, workers=workers)
    if not (
        result.get("status") == "verified"
        and result.get("manifest_sha256") == expected["sha256"]
        and result.get("dataset_sha256") == expected["dataset_sha256"]
        and result.get("partitions") == expected["partitions"]
        and result.get("rows") == expected["rows"]
        and result.get("eligible_rows") == expected["eligible_rows"]
        and result.get("comparison_values_read") is False
        and result.get("historical_daily_price_or_forward_return_values_read") is False
        and result.get("provider_request_issued") is False
    ):
        raise Campaign105NoReturnAuditError("candidate snapshot verification changed")
    return result


def _record_path(manifest_path: Path, record: dict[str, Any]) -> Path:
    path = Path(str(record["path"]))
    return (
        path.resolve()
        if path.is_absolute()
        else (manifest_path.parent / path).resolve()
    )


def _aligned_columns(
    *,
    manifest_path: Path,
    records: list[dict[str, Any]],
    names: list[str],
    candidate_keys: np.ndarray,
) -> np.ndarray:
    """Read a frozen yearly snapshot batch exactly aligned to candidate keys."""

    output = np.full((len(candidate_keys), len(names)), np.nan, dtype=np.float64)
    covered = np.zeros(len(candidate_keys), dtype=bool)
    for record in records:
        path = _record_path(manifest_path, record)
        expected = str(record.get("sha256") or record.get("output_byte_sha256") or "")
        _require(path, expected, f"comparison partition {record.get('year')}")
        frame = pd.read_parquet(path, columns=["stock_day_key", *names])
        source_keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        if (
            len(source_keys) != int(record["rows"])
            or len(source_keys) == 0
            or not np.all(source_keys[1:] > source_keys[:-1])
        ):
            raise Campaign105NoReturnAuditError("comparison source identity changed")
        start = int(np.searchsorted(candidate_keys, source_keys[0], side="left"))
        stop = int(np.searchsorted(candidate_keys, source_keys[-1], side="right"))
        selected = candidate_keys[start:stop]
        positions = np.searchsorted(source_keys, selected, side="left")
        if len(selected) and (
            np.any(positions >= len(source_keys))
            or not np.array_equal(source_keys[positions], selected)
        ):
            raise Campaign105NoReturnAuditError("candidate/comparator identity changed")
        if len(selected):
            output[start:stop, :] = frame[names].to_numpy(dtype=np.float64)[
                positions, :
            ]
            covered[start:stop] = True
        del frame, source_keys, selected, positions
    if not covered.all():
        raise Campaign105NoReturnAuditError(
            "comparison source does not cover candidate"
        )
    return output


def _directionally_normalized_result(
    *,
    comparison_engine: Any,
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    values: np.ndarray,
    definition: dict[str, str],
    gate: dict[str, Any],
) -> dict[str, Any]:
    """Compare already direction-normalized C102 percentiles as higher-is-better."""

    result = comparison_engine._aligned_comparison_result(
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        comparison_values=values,
        comparison=definition["name"],
        direction="higher",
        gate=gate,
    )
    result["source_score_direction"] = definition["score_direction"]
    result["score_direction"] = "higher_after_frozen_direction_normalization"
    result["comparison_value_semantics"] = (
        "Campaign102 same-session average-tie percentile in frozen higher-is-better direction"
    )
    return result


def _load_comparisons_after_coverage(
    *,
    coverage: dict[str, Any],
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    gate: dict[str, Any],
    comparison_engine: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if coverage.get("gate_passed_before_comparison_values") is not True:
        raise Campaign105NoReturnAuditError(
            "comparison loader called before Campaign105 coverage pass"
        )
    definitions = candidate.reconstruct_comparisons()
    c102_verification = c102.verify_snapshot(C102_MANIFEST_PATH)
    c103_verification = c103.verify_snapshot(C103_MANIFEST_PATH)
    c102_manifest = json.loads(C102_MANIFEST_PATH.read_text(encoding="utf-8"))
    c103_manifest = json.loads(C103_MANIFEST_PATH.read_text(encoding="utf-8"))
    first = definitions[:130]
    if not (
        c102_verification.get("dataset_sha256") == C102_DATASET_SHA256
        and c102_manifest.get("components") == first
        and c102_manifest.get("component_count") == 130
        and c102_manifest.get("component_order_sha256") == c102.NUMERIC_ORDER_SHA256
        and c103_verification.get("dataset_sha256") == C103_DATASET_SHA256
        and c103_manifest.get("factor") == c103.FACTOR_NAME
        and definitions[-1] == {"name": c103.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign105NoReturnAuditError("frozen comparator snapshots changed")
    results: list[dict[str, Any]] = []
    c102_records = list(c102_manifest.get("files") or [])
    for offset in range(0, len(first), COMPARISON_BATCH_SIZE):
        batch = first[offset : offset + COMPARISON_BATCH_SIZE]
        names = [item["name"] for item in batch]
        matrix = _aligned_columns(
            manifest_path=C102_MANIFEST_PATH,
            records=c102_records,
            names=names,
            candidate_keys=candidate_keys,
        )
        for index, definition in enumerate(batch):
            results.append(
                _directionally_normalized_result(
                    comparison_engine=comparison_engine,
                    candidate_keys=candidate_keys,
                    candidate_values=candidate_values,
                    values=matrix[:, index],
                    definition=definition,
                    gate=gate,
                )
            )
        del matrix
        gc.collect()
    final_values = _aligned_columns(
        manifest_path=C103_MANIFEST_PATH,
        records=list(c103_manifest.get("files") or []),
        names=[c103.FACTOR_NAME],
        candidate_keys=candidate_keys,
    )[:, 0]
    final_result = comparison_engine._aligned_comparison_result(
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        comparison_values=final_values,
        comparison=c103.FACTOR_NAME,
        direction="higher",
        gate=gate,
    )
    final_result["source_score_direction"] = "higher"
    final_result["comparison_value_semantics"] = "frozen Campaign103 factor value"
    results.append(final_result)
    if [item["comparison_factor"] for item in results] != [
        item["name"] for item in definitions
    ]:
        raise Campaign105NoReturnAuditError("Campaign105 comparison order changed")
    receipts = {
        "campaign102_directional_rank_matrix": {
            "manifest_path": str(C102_MANIFEST_PATH),
            "manifest_sha256": C102_MANIFEST_SHA256,
            "dataset_sha256": C102_DATASET_SHA256,
            "factor_count": 130,
            "verification": c102_verification,
        },
        "campaign103_final_comparator": {
            "manifest_path": str(C103_MANIFEST_PATH),
            "manifest_sha256": C103_MANIFEST_SHA256,
            "dataset_sha256": C103_DATASET_SHA256,
            "factor": c103.FACTOR_NAME,
            "verification": c103_verification,
        },
        "all_131_sources_loaded_in_frozen_order": True,
    }
    return results, receipts


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
    confirm_run: bool = False,
) -> Path:
    if not confirm_run:
        raise Campaign105NoReturnAuditError("Campaign105 audit requires --confirm-run")
    if data_root.expanduser().resolve() != DEFAULT_DATA_ROOT.resolve():
        raise Campaign105NoReturnAuditError("Campaign105 data root changed")
    experiment_root = experiment_root.expanduser().resolve()
    if list(experiment_root.glob("*_campaign105_no_return_audit.json")):
        raise Campaign105NoReturnAuditError("Campaign105 audit already exists")
    static = verify_static_bindings()
    spec = load_protocol()
    verification = verify_candidate_snapshot(workers=workers)
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    context = (
        cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    prior, foundation, engine, _, _, comparison_engine = context
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    ranges[FACTOR_NAME] = (0.0, 1.0)
    engine.FACTOR_RANGES = ranges
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    frame = engine.load_factor_frame(SNAPSHOT_MANIFEST_PATH, manifest, FACTOR_NAME)
    quality_frame, coverage = engine.coverage_and_capacity(
        frame, eligible_keys, spec, FACTOR_NAME
    )
    del frame, eligible_keys
    gc.collect()
    comparisons: list[dict[str, Any]] = []
    receipts: dict[str, Any] = {}
    if coverage["gate_passed_before_comparison_values"]:
        keys, values = engine._sorted_candidate_arrays(quality_frame, FACTOR_NAME)
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        comparisons, receipts = _load_comparisons_after_coverage(
            coverage=coverage,
            candidate_keys=keys,
            candidate_values=values,
            gate=gate,
            comparison_engine=comparison_engine,
        )
    expected_order = [
        item["name"]
        for item in spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
            "comparison_factors"
        ]
    ]
    observed_order = [item["comparison_factor"] for item in comparisons]
    all_passed = bool(
        len(comparisons) == EXPECTED_COMPARISON_COUNT
        and observed_order == expected_order
        and all(item.get("gate_passed") is True for item in comparisons)
    )
    correlations = [
        float(item["absolute_median_daily_rank_correlation"])
        for item in comparisons
        if item.get("absolute_median_daily_rank_correlation") is not None
    ]
    admitted = bool(coverage["gate_passed_before_comparison_values"] and all_passed)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{timestamp}_campaign105_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign105_no_return_audit",
        "status": (
            "completed_one_admissible_factor_ready_for_exact_frozen_development_trial"
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
            "sha256": verification["manifest_sha256"],
            "dataset_sha256": verification["dataset_sha256"],
        },
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {
            FACTOR_NAME: {
                "comparison_values_loaded_after_coverage_pass": bool(comparisons),
                "comparison_factor_count": len(comparisons),
                "comparison_order_matches_preregistration": observed_order
                == expected_order,
                "all_required_numeric_comparisons_passed": all_passed,
                "maximum_observed_absolute_median_daily_rank_correlation": (
                    max(correlations) if correlations else None
                ),
                "comparisons": comparisons,
                "comparison_source_verification": receipts,
            }
        },
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": (
            "run exactly the preregistered single 2019-2023 development trial"
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
    candidate.source._atomic_json(record, destination)
    return destination


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    audits = sorted(
        experiment_root.expanduser()
        .resolve()
        .glob("*_campaign105_no_return_audit.json")
    )
    return {
        "implementation_freeze_exists": candidate.DEFAULT_IMPLEMENTATION_FREEZE.is_file(),
        "audit_activation_binding_exists": AUDIT_ACTIVATION_BINDING.is_file(),
        "candidate_snapshot_exists": SNAPSHOT_MANIFEST_PATH.is_file(),
        "audit_count": len(audits),
        "coverage_or_capacity_metrics_computed_by_status": False,
        "comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "run"))
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--confirm-run", action="store_true")
    args = parser.parse_args()
    if args.command == "status":
        print(
            json.dumps(status(args.experiment_root), ensure_ascii=False, sort_keys=True)
        )
        return 0
    print(
        run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
            confirm_run=args.confirm_run,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
