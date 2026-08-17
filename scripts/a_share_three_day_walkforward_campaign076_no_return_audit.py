#!/usr/bin/env python3
"""Run Campaign076's frozen coverage-first no-return uniqueness audit."""

from __future__ import annotations

import argparse
import concurrent.futures
import gc
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import a_share_three_day_walkforward_campaign075_features as c75_features
from scripts import a_share_three_day_walkforward_campaign075_no_return_audit_v5 as c75_v5
from scripts import a_share_three_day_walkforward_campaign076_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_076/no_return"
SNAPSHOT_MANIFEST_PATH = candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
SNAPSHOT_MANIFEST_SHA256 = "dc23177c4125142fb2287fb3e19a4be8a3cd53b70abd3be91718979aaf200f32"
SNAPSHOT_DATASET_SHA256 = "aef7cfb7cbc3ccaabe5552a4ed4f81ea8582d5f739153dd405b70e2a73b3a952"
SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_076_feature_snapshot_binding_20260806.json"
SNAPSHOT_BINDING_SHA256 = "ab89095b907d597bd1291baad8aa6443e5e14e9e20952df8e98d2ed65cfe4b09"
AUDIT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_076_no_return_audit_implementation_freeze_20260806.json"
AUDIT_ACTIVATION_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_076_no_return_audit_activation_binding_20260806.json"
TEST_PATH = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign076_no_return_audit.py"
EXPECTED_ROWS = 7_724_498
EXPECTED_PARTITIONS = 33_015
EXPECTED_ELIGIBLE_ROWS = 7_724_498
EXPECTED_COMPARISON_COUNT = 106
EXPECTED_COMPLETE_DEFINITION_COUNT = 107
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.COMPARISON_ORDER_SHA256
EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256 = candidate.FULL_DEFINITION_ORDER_SHA256
C75_SNAPSHOT_MANIFEST_PATH = candidate.C75_MANIFEST_PATH
STRUCTURALLY_NONNUMERIC_FACTOR = "intraday_cross_sectional_standardized_return_state_stability_236p"


class Campaign076NoReturnAuditError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign076NoReturnAuditError(f"{label} changed: {path}")


def load_protocol() -> dict[str, Any]:
    spec = candidate.load_protocol()
    comparisons = candidate.reconstruct_comparisons()
    complete = candidate.reconstruct_complete_definitions()
    if not (len(comparisons) == EXPECTED_COMPARISON_COUNT and candidate._comparison_order_digest(comparisons) == EXPECTED_COMPARISON_ORDER_SHA256 and len(complete) == EXPECTED_COMPLETE_DEFINITION_COUNT and candidate._comparison_order_digest(complete) == EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256 and STRUCTURALLY_NONNUMERIC_FACTOR in [str(x["name"]) for x in complete] and STRUCTURALLY_NONNUMERIC_FACTOR not in [str(x["name"]) for x in comparisons]):
        raise Campaign076NoReturnAuditError("Campaign076 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factors"] = comparisons
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign076NoReturnAuditError("audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (record.get("kind") == "a_share_three_day_walkforward_campaign076_no_return_audit_implementation_freeze" and record.get("status") == "frozen_after_verified_snapshot_before_coverage_or_comparison_values" and (record.get("audit_runner") or {}).get("sha256") == _sha256(Path(__file__).resolve()) and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH) and (record.get("snapshot_binding") or {}).get("sha256") == SNAPSHOT_BINDING_SHA256 and record.get("coverage_or_capacity_metrics_computed_before_freeze") is False and record.get("comparison_values_read_before_freeze") is False and record.get("historical_daily_price_fields_read_before_freeze") == [] and record.get("historical_forward_returns_read_before_freeze") is False and record.get("provider_request_issued_before_freeze") is False):
        raise Campaign076NoReturnAuditError("audit implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign076NoReturnAuditError("audit activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    if not (record.get("kind") == "a_share_three_day_walkforward_campaign076_no_return_audit_activation_binding" and record.get("status") == "frozen_before_coverage_or_comparison_values" and (record.get("implementation_freeze") or {}).get("sha256") == _sha256(AUDIT_IMPLEMENTATION_FREEZE) and (record.get("snapshot_binding") or {}).get("sha256") == SNAPSHOT_BINDING_SHA256 and snapshot.get("path") == str(SNAPSHOT_MANIFEST_PATH.resolve()) and snapshot.get("sha256") == SNAPSHOT_MANIFEST_SHA256 and snapshot.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256 and record.get("coverage_or_capacity_metrics_computed_before_activation") is False and record.get("comparison_values_read_before_activation") is False and record.get("historical_daily_price_fields_read_before_activation") == [] and record.get("historical_forward_returns_read_before_activation") is False and record.get("provider_request_issued_before_activation") is False):
        raise Campaign076NoReturnAuditError("audit activation binding changed")
    return record


def _verify_runtime_independent_snapshot(
    manifest_path: Path,
    *,
    expected_path: Path,
    manifest_sha256: str,
    dataset_sha256: str,
    factor: str,
    expected_eligible: int,
    validate_manifest: Callable[[dict[str, Any]], None],
    validate_values: Callable[[pd.DataFrame], tuple[int, int]],
    output_columns: tuple[str, ...],
    digest: Callable[[Any], str],
    workers: int,
) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    if manifest_path != expected_path.resolve():
        raise Campaign076NoReturnAuditError("snapshot path changed")
    _require(manifest_path, manifest_sha256, "snapshot manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    files = list(manifest.get("files") or [])
    if not (manifest.get("dataset_sha256") == dataset_sha256 and manifest.get("factor_names") == [factor] and manifest.get("rows") == EXPECTED_ROWS and manifest.get("partitions") == EXPECTED_PARTITIONS and len(files) == EXPECTED_PARTITIONS and (manifest.get("factor_eligible_rows") or {}).get(factor) == expected_eligible):
        raise Campaign076NoReturnAuditError("snapshot aggregate semantics changed")
    partition_root = (manifest_path.parent / "partitions").resolve()
    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"] or pq.ParquetFile(path).metadata.num_rows != int(item["rows"]):
            raise Campaign076NoReturnAuditError(f"snapshot partition changed: {path}")
        frame = pd.read_parquet(path)
        if tuple(frame.columns) != output_columns:
            raise Campaign076NoReturnAuditError(f"snapshot schema changed: {path}")
        return validate_values(frame)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        totals = list(pool.map(verify, files))
    digest_rows = [[x["relative_path"], x["output_byte_sha256"], x["output_frame_sha256"], x["rows"]] for x in files]
    if digest(digest_rows) != dataset_sha256 or sum(x[0] for x in totals) != EXPECTED_ROWS or sum(x[1] for x in totals) != expected_eligible:
        raise Campaign076NoReturnAuditError("snapshot compatibility totals changed")
    return {"status": "verified_runtime_independent_bytes_schema_values_and_stored_digest", "manifest_sha256": manifest_sha256, "dataset_sha256": dataset_sha256, "partitions": len(totals), "rows": sum(x[0] for x in totals), "eligible_rows": sum(x[1] for x in totals), "runtime_sensitive_frame_hash_recomputation_skipped": True, "historical_daily_price_or_forward_return_values_read": False, "provider_request_issued": False}


def verify_candidate_snapshot(manifest_path: Path, *, workers: int = 4) -> dict[str, Any]:
    return _verify_runtime_independent_snapshot(manifest_path, expected_path=SNAPSHOT_MANIFEST_PATH, manifest_sha256=SNAPSHOT_MANIFEST_SHA256, dataset_sha256=SNAPSHOT_DATASET_SHA256, factor=FACTOR_NAME, expected_eligible=EXPECTED_ELIGIBLE_ROWS, validate_manifest=candidate._validate_manifest, validate_values=candidate.validate_value_semantics, output_columns=candidate.OUTPUT_COLUMNS, digest=candidate._json_digest, workers=workers)


def verify_campaign075_snapshot(manifest_path: Path, *, workers: int = 4) -> dict[str, Any]:
    c75_features.load_protocol()
    c75_features._validate_implementation_freeze()
    return _verify_runtime_independent_snapshot(manifest_path, expected_path=C75_SNAPSHOT_MANIFEST_PATH, manifest_sha256=candidate.C75_MANIFEST_SHA256, dataset_sha256=candidate.C75_DATASET_SHA256, factor=candidate.C75_FACTOR, expected_eligible=7_689_881, validate_manifest=lambda x: None, validate_values=c75_features.validate_value_semantics, output_columns=c75_features.OUTPUT_COLUMNS, digest=c75_features._json_digest, workers=workers)


def verify_static_bindings() -> dict[str, Any]:
    _load_activation_binding()
    _require(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "candidate snapshot")
    _require(C75_SNAPSHOT_MANIFEST_PATH, candidate.C75_MANIFEST_SHA256, "Campaign075 snapshot")
    report = candidate.bindings.validate_record(SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign076NoReturnAuditError("snapshot binding validation failed")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    if not (manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256 and manifest.get("rows") == EXPECTED_ROWS and manifest.get("partitions") == EXPECTED_PARTITIONS and (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME) == EXPECTED_ELIGIBLE_ROWS and len(candidate.reconstruct_comparisons()) == EXPECTED_COMPARISON_COUNT):
        raise Campaign076NoReturnAuditError("static snapshot identity changed")
    return {"audit_implementation_freeze_sha256": _sha256(AUDIT_IMPLEMENTATION_FREEZE), "audit_activation_binding_sha256": _sha256(AUDIT_ACTIVATION_BINDING), "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256, "candidate_manifest_sha256": SNAPSHOT_MANIFEST_SHA256, "candidate_dataset_sha256": SNAPSHOT_DATASET_SHA256, "candidate_eligible_rows": EXPECTED_ELIGIBLE_ROWS, "comparison_count": EXPECTED_COMPARISON_COUNT, "comparison_order_sha256": EXPECTED_COMPARISON_ORDER_SHA256, "complete_definition_count": EXPECTED_COMPLETE_DEFINITION_COUNT, "complete_definition_order_sha256": EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256, "comparator_values_read": False}


def _install_frozen_ranges(engine: Any) -> None:
    c75_v5.v4.v3.v1._install_frozen_ranges(engine)
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    if FACTOR_NAME in ranges and tuple(ranges[FACTOR_NAME]) != (0.0, 1.0):
        raise Campaign076NoReturnAuditError("conflicting Campaign076 range")
    ranges[FACTOR_NAME] = (0.0, 1.0)
    engine.FACTOR_RANGES = ranges


def _load_comparisons_after_coverage(*, coverage: dict[str, Any], candidate_keys: np.ndarray, candidate_values: np.ndarray, gate: dict[str, Any], engine: Any, comparison_engine: Any, workers: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    v3 = c75_v5.v4.v3
    v1 = v3.v1
    targets = [(v1.base.base.c68, 68), (v1.base.base.c69, 69), (v1.base.base.c70, 70), (v1.base.base.c71, 71), (v1.base.base.c72, 72), (v1.base.c73, 73), (v1.c74_features, 74)]
    originals = [(module, module.verify_snapshot_files) for module, _ in targets]
    original_configs = v3._snapshot_configs
    try:
        v3._snapshot_configs = c75_v5._corrected_snapshot_configs
        for module, campaign in targets:
            module.verify_snapshot_files = v3._verifier(campaign)
        comparisons, receipts = v1._load_comparisons_after_coverage(coverage=coverage, candidate_keys=candidate_keys, candidate_values=candidate_values, gate=gate, engine=engine, comparison_engine=comparison_engine, workers=workers)
    finally:
        v3._snapshot_configs = original_configs
        for module, original in originals:
            module.verify_snapshot_files = original
    result, receipt = v1.base.base._append_snapshot_comparison(manifest_path=C75_SNAPSHOT_MANIFEST_PATH, factor=candidate.C75_FACTOR, candidate_keys=candidate_keys, candidate_values=candidate_values, gate=gate, engine=engine, comparison_engine=comparison_engine, workers=workers, verifier=verify_campaign075_snapshot)
    comparisons.append(result)
    receipts["campaign075_snapshot"] = receipt
    receipts.pop("all_105_sources_loaded_in_frozen_order", None)
    receipts["all_106_sources_loaded_in_frozen_order"] = True
    if len(comparisons) != EXPECTED_COMPARISON_COUNT:
        raise Campaign076NoReturnAuditError("Campaign076 comparison count changed")
    return comparisons, receipts


def run_no_return_audit(*, data_root: Path, experiment_root: Path, workers: int) -> Path:
    static = verify_static_bindings()
    spec = load_protocol()
    if data_root.expanduser().resolve() != DEFAULT_DATA_ROOT.resolve():
        raise Campaign076NoReturnAuditError("Campaign076 data root changed")
    experiment_root = experiment_root.expanduser().resolve()
    if list(experiment_root.glob("*_campaign076_no_return_audit.json")):
        raise Campaign076NoReturnAuditError("Campaign076 no-return audit already exists")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    verification = verify_candidate_snapshot(SNAPSHOT_MANIFEST_PATH, workers=workers)
    prior, foundation, engine, _, _, comparison_engine = cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    _install_frozen_ranges(engine)
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    frame = engine.load_factor_frame(SNAPSHOT_MANIFEST_PATH, manifest, FACTOR_NAME)
    quality_frame, coverage = engine.coverage_and_capacity(frame, eligible_keys, spec, FACTOR_NAME)
    del frame, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        expected_order = [str(x["name"]) for x in gate["comparison_factors"]]
        keys, values = engine._sorted_candidate_arrays(quality_frame, FACTOR_NAME)
        comparisons, receipts = _load_comparisons_after_coverage(coverage=coverage, candidate_keys=keys, candidate_values=values, gate=gate, engine=engine, comparison_engine=comparison_engine, workers=workers)
        observed_order = [str(x["comparison_factor"]) for x in comparisons]
        correlations = [float(x["absolute_median_daily_rank_correlation"]) for x in comparisons if x["absolute_median_daily_rank_correlation"] is not None]
        passed = bool(observed_order == expected_order and len(comparisons) == EXPECTED_COMPARISON_COUNT and all(x["gate_passed"] for x in comparisons))
        uniqueness = {"comparison_values_loaded_after_coverage_pass": True, "comparison_factor_count": len(comparisons), "comparison_order_matches_preregistration": observed_order == expected_order, "comparison_source_verification": receipts, "comparisons": comparisons, "maximum_observed_absolute_median_daily_rank_correlation": max(correlations) if correlations else None, "all_required_numeric_comparisons_passed": passed, "structurally_nonnumeric_mechanism_challenges": [{"name": STRUCTURALLY_NONNUMERIC_FACTOR, "numeric_status": "undefined_not_pass_not_fail", "mechanism_overlap_status": "explicitly_challenged_before_values"}]}
    else:
        uniqueness = {"comparison_values_loaded_after_coverage_pass": False, "comparison_factor_count": 0, "comparisons": [], "all_required_numeric_comparisons_passed": False, "failure_reason": "coverage_gate_failed", "structurally_nonnumeric_mechanism_challenges": [{"name": STRUCTURALLY_NONNUMERIC_FACTOR, "numeric_status": "undefined_not_pass_not_fail", "mechanism_overlap_status": "explicitly_challenged_before_values"}]}
    del quality_frame
    gc.collect()
    admitted = bool(coverage["gate_passed_before_comparison_values"] and uniqueness["all_required_numeric_comparisons_passed"])
    prior_engine = cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044
    timestamp = prior_engine.research._timestamp()
    run_id = f"{timestamp}_campaign076_no_return_audit"
    record = {"schema_version": 1, "kind": "a_share_three_day_walkforward_campaign076_no_return_audit", "status": "completed_with_one_admissible_factor_pending_walkforward_preregistration" if admitted else "completed_zero_admissible_factors_stop_before_historical_daily_prices_or_returns", "run_id": run_id, "created_at": prior_engine.research._timestamp(), "protocol": {"path": str(candidate.DEFAULT_PROTOCOL.resolve()), "sha256": candidate.PROTOCOL_SHA256}, "static_bindings": static, "candidate_snapshot": {"path": str(SNAPSHOT_MANIFEST_PATH), "sha256": SNAPSHOT_MANIFEST_SHA256, "dataset_sha256": SNAPSHOT_DATASET_SHA256}, "snapshot_file_verification": verification, "coverage_and_capacity": {FACTOR_NAME: coverage}, "uniqueness": {FACTOR_NAME: uniqueness}, "admissible_factor_names": [FACTOR_NAME] if admitted else [], "admissible_factor_count": 1 if admitted else 0, "failed_factor_names": [] if admitted else [FACTOR_NAME], "next_action": "freeze and run the exact one Campaign076 development trial" if admitted else "record this no-return rejection and begin only a genuinely new campaign", "candidate_source_fields_read": list(candidate.RAW_COLUMNS), "stock_day_identity_fields_read": list(candidate.IDENTITY_COLUMNS), "historical_daily_price_fields_read": [], "historical_forward_return_fields_read": False, "candidate49_historical_return_read": False, "candidate49_prospective_ledgers_changed": False, "second_prospective_candidate_created": False, "training_or_model_fitting_performed": False, "provider_request_issued": False, "current_scoring_selection_sizing_or_orders_performed": False, "current_quarterly_snapshot_revision_limitation_for_comparators": True}
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    audits = sorted(experiment_root.expanduser().resolve().glob("*_campaign076_no_return_audit.json"))
    return {"audit_implementation_freeze_exists": AUDIT_IMPLEMENTATION_FREEZE.is_file(), "audit_activation_binding_exists": AUDIT_ACTIVATION_BINDING.is_file(), "candidate_snapshot_exists": SNAPSHOT_MANIFEST_PATH.is_file(), "audit_count": len(audits), "coverage_or_capacity_metrics_computed_by_status": False, "comparison_values_read_by_status": False, "historical_daily_price_fields_read": [], "historical_forward_return_fields_read": False, "candidate49_historical_return_read": False, "provider_request_issued": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run"); run.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT); run.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT); run.add_argument("--workers", type=int, default=4)
    inspect = sub.add_parser("status"); inspect.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    args = parser.parse_args()
    payload = {"audit": str(run_no_return_audit(data_root=args.data_root, experiment_root=args.experiment_root, workers=args.workers))} if args.command == "run" else status(args.experiment_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
