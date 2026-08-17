#!/usr/bin/env python3
"""Run the frozen coverage-first Campaign062 no-return audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign061_features as c61_features
from scripts import a_share_three_day_walkforward_campaign061_no_return_audit as c61_audit
from scripts import a_share_three_day_walkforward_campaign062_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = candidate.FACTOR_NAME
PROTOCOL_SHA256 = candidate.PROTOCOL_SHA256
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_062_feature_snapshot_binding_20260805.json"
)
SNAPSHOT_BINDING_SHA256 = (
    "7143546783e59f7872cb4771385672311b4efcdd229353194d743ad5daf10d32"
)
SNAPSHOT_MANIFEST_PATH = candidate.output_root(candidate.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
SNAPSHOT_MANIFEST_SHA256 = (
    "518131c1ecac2820a426d2d7de46552daf9009b476ed7efbf3d69ba555f1ac45"
)
SNAPSHOT_DATASET_SHA256 = (
    "5012eebb056fff75b6931390acaa5272629e70267ee5a32f46377c60994571a0"
)
EXPECTED_ROWS = 7_724_498
EXPECTED_PARTITIONS = 33_015
EXPECTED_ELIGIBLE_ROWS = 7_233_196
EXPECTED_COMPARISON_COUNT = 93
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.COMPARISON_ORDER_SHA256
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_062_no_return_audit_implementation_freeze_20260805.json"
)
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_062/no_return"
)
C61_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign061_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign061_feature_library_v1/snapshot_manifest.json"
)
C61_SNAPSHOT_SHA256 = (
    "15ed4b46192402f301218e20b1fe37233dd7547256fb9786692ce544fae20b3c"
)
C61_DATASET_SHA256 = (
    "a8a6261eaa92cd8eca7c25513236abf73f84f500da368a7b325634808fbb576a"
)
C61_FACTOR = "intraday_day_over_day_realized_variance_stability_238b"


class Campaign062NoReturnAuditError(RuntimeError):
    """Fail-closed Campaign062 no-return audit error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign062NoReturnAuditError(f"{label} changed")


def load_protocol() -> dict[str, Any]:
    spec = candidate.load_protocol()
    comparisons = candidate.reconstruct_comparisons(spec)
    if (
        len(comparisons) != EXPECTED_COMPARISON_COUNT
        or candidate._comparison_order_digest(comparisons)
        != EXPECTED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign062NoReturnAuditError("Campaign062 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return spec


def verify_static_bindings() -> dict[str, Any]:
    _require(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "snapshot manifest")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    candidate._validate_snapshot_manifest(
        manifest, require_fingerprint_constants=False
    )
    if not (
        manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        == EXPECTED_ELIGIBLE_ROWS
    ):
        raise Campaign062NoReturnAuditError("candidate snapshot identity changed")
    _require(C61_SNAPSHOT_PATH, C61_SNAPSHOT_SHA256, "Campaign061 snapshot")
    c61_manifest = json.loads(C61_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    if c61_manifest.get("dataset_sha256") != C61_DATASET_SHA256:
        raise Campaign062NoReturnAuditError("Campaign061 dataset changed")
    return {
        "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256,
        "candidate_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": SNAPSHOT_DATASET_SHA256,
        "campaign061_manifest_sha256": C61_SNAPSHOT_SHA256,
        "campaign061_dataset_sha256": C61_DATASET_SHA256,
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": EXPECTED_COMPARISON_ORDER_SHA256,
    }


def _load_audit_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign062NoReturnAuditError("audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = record.get("audit_runner") or {}
    binding = record.get("snapshot_binding") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign062_no_return_audit_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign062_comparison_daily_price_or_return_values"
        and (REPO_ROOT / str(runner.get("path") or "")).resolve()
        == Path(__file__).resolve()
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and binding.get("sha256") == SNAPSHOT_BINDING_SHA256
        and record.get("comparison_values_read_before_freeze") is False
        and record.get("historical_daily_price_fields_read_before_freeze") == []
        and record.get("historical_forward_returns_read_before_freeze") is False
    ):
        raise Campaign062NoReturnAuditError("audit implementation freeze changed")
    return record


def _append_campaign061(
    *,
    comparisons: list[dict[str, Any]],
    verifications: dict[str, Any],
    keys: Any,
    values: Any,
    gate: dict[str, Any],
    directions: dict[str, str],
    workers: int,
    engine: Any,
    comparison_engine: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads(C61_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    verification = c61_features.verify_snapshot_files(
        C61_SNAPSHOT_PATH, workers=workers
    )
    comparison_values = engine._load_filtered_comparison_values_explicit(
        manifest, [C61_FACTOR], keys
    )[C61_FACTOR]
    comparisons.append(
        comparison_engine._aligned_comparison_result(
            candidate_keys=keys,
            candidate_values=values,
            comparison_values=comparison_values,
            comparison=C61_FACTOR,
            direction=directions[C61_FACTOR],
            gate=gate,
        )
    )
    del comparison_values
    gc.collect()
    return comparisons, {
        **verifications,
        "campaign061_snapshot_file_verification": verification,
    }


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    _load_audit_implementation_freeze()
    static = verify_static_bindings()
    spec = load_protocol()
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    existing = sorted(experiment_root.glob("*_campaign062_no_return_audit.json"))
    if existing:
        raise Campaign062NoReturnAuditError("Campaign062 no-return audit already exists")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    verification = candidate.verify_snapshot_files(
        manifest, SNAPSHOT_MANIFEST_PATH, workers
    )
    prior, foundation, engine, _, candidate49, comparison_engine = (
        c61_audit.prior_audit.terminal.campaign044._context()
    )
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
        directions = {
            str(item["name"]): str(item["score_direction"])
            for item in gate["comparison_factors"]
        }
        keys, values = engine._sorted_candidate_arrays(quality_frame, FACTOR_NAME)
        snapshots = c61_audit._load_bound_prior_snapshots(workers)
        comparisons, source_verifications = c61_audit._append_all_prior_comparisons(
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
        comparisons, source_verifications = _append_campaign061(
            comparisons=comparisons,
            verifications=source_verifications,
            keys=keys,
            values=values,
            gate=gate,
            directions=directions,
            workers=workers,
            engine=engine,
            comparison_engine=comparison_engine,
        )
        observed_order = [str(item["comparison_factor"]) for item in comparisons]
        observed_correlations = [
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
            "source_snapshot_verifications": source_verifications,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": max(
                observed_correlations
            )
            if observed_correlations
            else None,
            "all_required_comparisons_passed": passed,
        }
        del keys, values
        gc.collect()
    else:
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": False,
            "comparison_factor_count": 0,
            "comparisons": [],
            "all_required_comparisons_passed": False,
            "failure_reason": "coverage_gate_failed",
        }
    admitted = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_required_comparisons_passed"]
    )
    timestamp = prior.research._timestamp()
    run_id = f"{timestamp}_campaign062_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign062_no_return_audit",
        "status": "completed_with_one_admissible_factor_pending_walkforward_preregistration"
        if admitted
        else "completed_zero_admissible_factors_stop_before_historical_returns",
        "run_id": run_id,
        "created_at": prior.research._timestamp(),
        "protocol": {
            "path": str(candidate.DEFAULT_PROTOCOL.resolve()),
            "sha256": PROTOCOL_SHA256,
        },
        "static_bindings": static,
        "candidate_snapshot": {
            "path": str(SNAPSHOT_MANIFEST_PATH),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": SNAPSHOT_DATASET_SHA256,
        },
        "snapshot_binding": {
            "path": str(SNAPSHOT_BINDING.resolve()),
            "sha256": SNAPSHOT_BINDING_SHA256,
        },
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": "freeze the exact one-trial Campaign062 walk-forward before reading 2019-2023 returns"
        if admitted
        else "record the no-return rejection and start only a genuinely new campaign",
        "stock_day_identity_fields_read": list(candidate.RAW_COLUMNS),
        "quarterly_disclosure_fields_read": list(candidate.EVENT_FIELDS),
        "quarterly_value_fields_read": [],
        "minute_open_high_low_close_volume_amount_fields_read": [],
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


def status(experiment_root: Path) -> dict[str, Any]:
    audits = sorted(
        experiment_root.expanduser().resolve().glob("*_campaign062_no_return_audit.json")
    )
    return {
        "static_bindings": verify_static_bindings(),
        "audit_implementation_freeze_exists": AUDIT_IMPLEMENTATION_FREEZE.is_file(),
        "audit_count": len(audits),
        "comparison_values_read_by_status": False,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "provider_request_issued": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "run"):
        command = sub.add_parser(name)
        command.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
        command.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
        command.add_argument("--workers", type=int, default=4)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        payload = status(args.experiment_root)
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
