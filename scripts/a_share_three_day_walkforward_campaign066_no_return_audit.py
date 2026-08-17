#!/usr/bin/env python3
"""Run the frozen coverage-first Campaign066 no-return audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign062_no_return_audit as c62_audit
from scripts import a_share_three_day_walkforward_campaign065_features as c65_features
from scripts import a_share_three_day_walkforward_campaign065_no_return_audit as prior_audit
from scripts import a_share_three_day_walkforward_campaign066_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = candidate.FACTOR_NAME
PROTOCOL_SHA256 = candidate.PROTOCOL_SHA256
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_066/no_return"
SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_066_feature_snapshot_binding_20260805.json"
SNAPSHOT_BINDING_SHA256 = "8e32d9dfed246b98feb042e253055afd05324c7cfe4d62f7fb46d5d4e52e48f3"
SNAPSHOT_MANIFEST_PATH = candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
SNAPSHOT_MANIFEST_SHA256 = "e46a0647007700e8b5682d76bffec6a9602f9b615a7801bf1554e4a72c442354"
SNAPSHOT_DATASET_SHA256 = "8727bae79ee4450e530268be882c89fed710eff599d549ee68d8023ebfb2dd0d"
EXPECTED_ROWS = 7_724_498
EXPECTED_PARTITIONS = 33_015
EXPECTED_ELIGIBLE_ROWS = 7_228_585
EXPECTED_COMPARISON_COUNT = 96
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.COMPARISON_ORDER_SHA256
EXPECTED_COMPLETE_DEFINITION_COUNT = 97
EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256 = candidate.FULL_DEFINITION_ORDER_SHA256
STRUCTURALLY_NONNUMERIC_FACTOR = candidate.C63_FACTOR
AUDIT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_066_no_return_audit_implementation_freeze_20260805.json"
C65_SNAPSHOT_PATH = c65_features.output_root(c65_features.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C65_SNAPSHOT_SHA256 = "d67f6553a0890c2fe63735ba3e3671ba070a7d9cb28a5c92df3be079b17383e8"
C65_DATASET_SHA256 = "c0bce8bd42317fcbd1e946f13ba2873e485ceed196734ee63e59135cd1895ad4"
C65_FACTOR = c65_features.FACTOR_NAME


class Campaign066NoReturnAuditError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign066NoReturnAuditError(f"{label} changed")


def reconstruct_complete_definitions(comparisons: list[dict[str, str]]) -> list[dict[str, str]]:
    if comparisons[-3:] != [
        {"name": prior_audit.C62_FACTOR, "score_direction": "higher"},
        {"name": prior_audit.C64_FACTOR, "score_direction": "higher"},
        {"name": C65_FACTOR, "score_direction": "higher"},
    ]:
        raise Campaign066NoReturnAuditError("Campaign066 comparison tail changed")
    full = comparisons[:-2] + [{"name": STRUCTURALLY_NONNUMERIC_FACTOR, "score_direction": "higher"}] + comparisons[-2:]
    if len(full) != EXPECTED_COMPLETE_DEFINITION_COUNT or candidate._comparison_order_digest(full) != EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256:
        raise Campaign066NoReturnAuditError("Campaign066 complete definition order changed")
    return full


def load_protocol() -> dict[str, Any]:
    spec = candidate.load_protocol()
    comparisons = candidate.reconstruct_comparisons(spec)
    full = reconstruct_complete_definitions(comparisons)
    if (
        len(comparisons) != EXPECTED_COMPARISON_COUNT
        or candidate._comparison_order_digest(comparisons) != EXPECTED_COMPARISON_ORDER_SHA256
        or STRUCTURALLY_NONNUMERIC_FACTOR not in [item["name"] for item in full]
        or STRUCTURALLY_NONNUMERIC_FACTOR in [item["name"] for item in comparisons]
    ):
        raise Campaign066NoReturnAuditError("Campaign066 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factors"] = comparisons
    return spec


def verify_static_bindings() -> dict[str, Any]:
    _require(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "candidate snapshot")
    _require(C65_SNAPSHOT_PATH, C65_SNAPSHOT_SHA256, "Campaign065 snapshot")
    report = candidate.bindings.validate_record(SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign066NoReturnAuditError("snapshot binding validation failed")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    candidate._validate_manifest(manifest)
    c65_manifest = json.loads(C65_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    comparisons = candidate.reconstruct_comparisons(load_protocol())
    if not (
        manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME) == EXPECTED_ELIGIBLE_ROWS
        and c65_manifest.get("dataset_sha256") == C65_DATASET_SHA256
        and len(comparisons) == EXPECTED_COMPARISON_COUNT
    ):
        raise Campaign066NoReturnAuditError("static snapshot identity changed")
    return {
        "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256,
        "candidate_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": SNAPSHOT_DATASET_SHA256,
        "campaign065_manifest_sha256": C65_SNAPSHOT_SHA256,
        "campaign065_dataset_sha256": C65_DATASET_SHA256,
        "complete_definition_count": EXPECTED_COMPLETE_DEFINITION_COUNT,
        "complete_definition_order_sha256": EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256,
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": EXPECTED_COMPARISON_ORDER_SHA256,
        "structurally_nonnumeric_mechanism_challenge": STRUCTURALLY_NONNUMERIC_FACTOR,
    }


def _load_audit_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign066NoReturnAuditError("audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = record.get("audit_runner") or {}
    binding = record.get("snapshot_binding") or {}
    if not (
        record.get("kind") == "a_share_three_day_walkforward_campaign066_no_return_audit_implementation_freeze"
        and record.get("status") == "frozen_before_campaign066_coverage_metrics_or_comparison_values"
        and (REPO_ROOT / str(runner.get("path") or "")).resolve() == Path(__file__).resolve()
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and binding.get("sha256") == SNAPSHOT_BINDING_SHA256
        and record.get("candidate_snapshot_materialized_and_fully_verified_before_freeze") is True
        and record.get("coverage_or_capacity_metrics_computed_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get("historical_daily_price_fields_read_before_freeze") == []
        and record.get("historical_forward_returns_read_before_freeze") is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign066NoReturnAuditError("audit implementation freeze changed")
    return record


def _install_frozen_candidate_range(engine: Any) -> None:
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    expected = (0.0, 1.0)
    if FACTOR_NAME in ranges and tuple(ranges[FACTOR_NAME]) != expected:
        raise Campaign066NoReturnAuditError("reused engine has a conflicting Campaign066 factor range")
    ranges[FACTOR_NAME] = expected
    engine.FACTOR_RANGES = ranges


def _verify_c65(manifest: dict[str, Any], path: Path, workers: int) -> dict[str, Any]:
    del manifest
    return c65_features.verify_snapshot_files(path, workers=workers)


def run_no_return_audit(*, data_root: Path, experiment_root: Path, workers: int) -> Path:
    _load_audit_implementation_freeze()
    static = verify_static_bindings()
    spec = load_protocol()
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign066NoReturnAuditError("Campaign066 data root changed")
    experiment_root = experiment_root.expanduser().resolve()
    if list(experiment_root.glob("*_campaign066_no_return_audit.json")):
        raise Campaign066NoReturnAuditError("Campaign066 no-return audit already exists")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    verification = candidate.verify_snapshot_files(SNAPSHOT_MANIFEST_PATH, workers=workers)
    prior, foundation, engine, _, candidate49, comparison_engine = c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    _install_frozen_candidate_range(engine)
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    candidate_frame = engine.load_factor_frame(SNAPSHOT_MANIFEST_PATH, manifest, FACTOR_NAME)
    quality_frame, coverage = engine.coverage_and_capacity(candidate_frame, eligible_keys, spec, FACTOR_NAME)
    del candidate_frame, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        expected_order = [str(item["name"]) for item in gate["comparison_factors"]]
        directions = {str(item["name"]): str(item["score_direction"]) for item in gate["comparison_factors"]}
        keys, values = engine._sorted_candidate_arrays(quality_frame, FACTOR_NAME)
        snapshots = c62_audit.c61_audit._load_bound_prior_snapshots(workers)
        comparisons, source_verifications = c62_audit.c61_audit._append_all_prior_comparisons(
            data_root=data_root, workers=workers, keys=keys, values=values, gate=gate,
            directions=directions, snapshots=snapshots, engine=engine,
            candidate49=candidate49, comparison_engine=comparison_engine,
        )
        comparisons, source_verifications = c62_audit._append_campaign061(
            comparisons=comparisons, verifications=source_verifications, keys=keys,
            values=values, gate=gate, directions=directions, workers=workers,
            engine=engine, comparison_engine=comparison_engine,
        )
        comparisons, source_verifications = prior_audit._append_snapshot_comparison(
            comparisons=comparisons, verifications=source_verifications,
            manifest_path=prior_audit.C62_SNAPSHOT_PATH, factor=prior_audit.C62_FACTOR,
            verification_key="campaign062_snapshot_file_verification", verify=prior_audit._verify_c62,
            keys=keys, values=values, gate=gate, directions=directions, workers=workers,
            engine=engine, comparison_engine=comparison_engine,
        )
        comparisons, source_verifications = prior_audit._append_snapshot_comparison(
            comparisons=comparisons, verifications=source_verifications,
            manifest_path=prior_audit.C64_SNAPSHOT_PATH, factor=prior_audit.C64_FACTOR,
            verification_key="campaign064_snapshot_file_verification", verify=prior_audit._verify_c64,
            keys=keys, values=values, gate=gate, directions=directions, workers=workers,
            engine=engine, comparison_engine=comparison_engine,
        )
        comparisons, source_verifications = prior_audit._append_snapshot_comparison(
            comparisons=comparisons, verifications=source_verifications,
            manifest_path=C65_SNAPSHOT_PATH, factor=C65_FACTOR,
            verification_key="campaign065_snapshot_file_verification", verify=_verify_c65,
            keys=keys, values=values, gate=gate, directions=directions, workers=workers,
            engine=engine, comparison_engine=comparison_engine,
        )
        observed_order = [str(item["comparison_factor"]) for item in comparisons]
        correlations = [float(item["absolute_median_daily_rank_correlation"]) for item in comparisons if item["absolute_median_daily_rank_correlation"] is not None]
        passed = observed_order == expected_order and len(comparisons) == EXPECTED_COMPARISON_COUNT and all(item["gate_passed"] for item in comparisons)
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": len(comparisons),
            "comparison_order_matches_preregistration": observed_order == expected_order,
            "source_snapshot_verifications": source_verifications,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": max(correlations) if correlations else None,
            "all_required_numeric_comparisons_passed": passed,
            "structurally_nonnumeric_mechanism_challenges": [{"name": STRUCTURALLY_NONNUMERIC_FACTOR, "numeric_status": "undefined_not_pass_not_fail", "mechanism_overlap_status": "explicitly_challenged_before_values"}],
        }
        del keys, values
        gc.collect()
    else:
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": False,
            "comparison_factor_count": 0,
            "comparisons": [],
            "all_required_numeric_comparisons_passed": False,
            "failure_reason": "coverage_gate_failed",
            "structurally_nonnumeric_mechanism_challenges": [{"name": STRUCTURALLY_NONNUMERIC_FACTOR, "numeric_status": "undefined_not_pass_not_fail", "mechanism_overlap_status": "explicitly_challenged_before_values"}],
        }
    del quality_frame
    gc.collect()
    admitted = bool(coverage["gate_passed_before_comparison_values"] and uniqueness["all_required_numeric_comparisons_passed"])
    timestamp = prior.research._timestamp()
    run_id = f"{timestamp}_campaign066_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign066_no_return_audit",
        "status": "completed_with_one_admissible_factor_pending_walkforward_preregistration" if admitted else "completed_zero_admissible_factors_stop_before_historical_daily_prices_or_returns",
        "run_id": run_id,
        "created_at": prior.research._timestamp(),
        "protocol": {"path": str(candidate.DEFAULT_PROTOCOL.resolve()), "sha256": PROTOCOL_SHA256},
        "static_bindings": static,
        "candidate_snapshot": {"path": str(SNAPSHOT_MANIFEST_PATH), "sha256": SNAPSHOT_MANIFEST_SHA256, "dataset_sha256": SNAPSHOT_DATASET_SHA256},
        "snapshot_binding": {"path": str(SNAPSHOT_BINDING.resolve()), "sha256": SNAPSHOT_BINDING_SHA256},
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": "freeze the exact one-trial Campaign066 walk-forward before reading 2019-2023 returns" if admitted else "record the no-return rejection and start only a genuinely new campaign",
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
    audits = sorted(experiment_root.expanduser().resolve().glob("*_campaign066_no_return_audit.json"))
    return {"static_bindings": verify_static_bindings(), "audit_implementation_freeze_exists": AUDIT_IMPLEMENTATION_FREEZE.is_file(), "audit_count": len(audits), "comparison_values_read_by_status": False, "historical_daily_price_fields_read": [], "historical_forward_return_fields_read": False, "candidate49_historical_return_read": False, "provider_request_issued": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "run"):
        command = sub.add_parser(name)
        command.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
        command.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
        command.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    payload = status(args.experiment_root) if args.command == "status" else {"audit": str(run_no_return_audit(data_root=args.data_root, experiment_root=args.experiment_root, workers=args.workers))}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
