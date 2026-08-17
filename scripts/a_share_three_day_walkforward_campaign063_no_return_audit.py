#!/usr/bin/env python3
"""Run the frozen coverage-first Campaign063 no-return terminal audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign062_no_return_audit as c62_audit
from scripts import a_share_three_day_walkforward_campaign063_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = candidate.FACTOR_NAME
PROTOCOL_SHA256 = candidate.PROTOCOL_SHA256
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_063_feature_snapshot_binding_20260805.json"
)
SNAPSHOT_BINDING_SHA256 = "96b6ba12cd59db5bfce6afc58704fb283e209f135a3bc38be55698938899db91"
SNAPSHOT_MANIFEST_PATH = candidate.output_root(candidate.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
SNAPSHOT_MANIFEST_SHA256 = "12fc8d8bf7df432608f4cb63b7c5337f2cd46d2a029c34d8b3e60c0f8906a098"
SNAPSHOT_DATASET_SHA256 = "fd040477f3af2948976fda9a71f6d04a0bd9b9713a1b9b5a6dedf2f06f0c76df"
STRUCTURAL_DIAGNOSIS = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_063_structural_peer_variance_diagnosis_20260805.json"
)
STRUCTURAL_DIAGNOSIS_SHA256 = "4795d140af58aecfb638eaf5abdd97fe513f18bffead731ec93fe16c72fd0171"
EXPECTED_ROWS = 7_724_498
EXPECTED_PARTITIONS = 33_015
EXPECTED_ELIGIBLE_ROWS = 0
EXPECTED_COMPARISON_COUNT = 94
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.COMPARISON_ORDER_SHA256
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_063_no_return_audit_implementation_freeze_20260805.json"
)
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_063/no_return"
)


class Campaign063NoReturnAuditError(RuntimeError):
    """Fail-closed Campaign063 no-return audit error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign063NoReturnAuditError(f"{label} changed")


def load_protocol() -> dict[str, Any]:
    spec = candidate.load_protocol()
    comparisons = candidate.reconstruct_comparisons(spec)
    if (
        len(comparisons) != EXPECTED_COMPARISON_COUNT
        or candidate._comparison_order_digest(comparisons)
        != EXPECTED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign063NoReturnAuditError("Campaign063 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return spec


def verify_static_bindings() -> dict[str, Any]:
    _require(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "snapshot manifest")
    _require(STRUCTURAL_DIAGNOSIS, STRUCTURAL_DIAGNOSIS_SHA256, "structural diagnosis")
    binding_report = candidate.bindings.validate_record(
        SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT
    )
    if binding_report.get("all_bindings_passed") is not True:
        raise Campaign063NoReturnAuditError("snapshot binding validation failed")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    candidate._validate_manifest(manifest)
    quality = manifest.get("quality") or {}
    if not (
        manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        == EXPECTED_ELIGIBLE_ROWS
        and quality.get(f"{FACTOR_NAME}__complete_stock_return_rows")
        == EXPECTED_ROWS
        and quality.get(f"{FACTOR_NAME}__nonpositive_variance_rows")
        == EXPECTED_ROWS
        and quality.get(f"{FACTOR_NAME}__eligible_rows") == 0
    ):
        raise Campaign063NoReturnAuditError("candidate snapshot identity changed")
    return {
        "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256,
        "candidate_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": SNAPSHOT_DATASET_SHA256,
        "structural_diagnosis_sha256": STRUCTURAL_DIAGNOSIS_SHA256,
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": EXPECTED_COMPARISON_ORDER_SHA256,
        "eligible_rows": EXPECTED_ELIGIBLE_ROWS,
    }


def _load_audit_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign063NoReturnAuditError("audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = record.get("audit_runner") or {}
    binding = record.get("snapshot_binding") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign063_no_return_audit_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign063_quality_listing_coverage_comparison_daily_price_or_return_values"
        and (REPO_ROOT / str(runner.get("path") or "")).resolve()
        == Path(__file__).resolve()
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and binding.get("sha256") == SNAPSHOT_BINDING_SHA256
        and record.get("quality_listing_keys_read_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get("historical_daily_price_fields_read_before_freeze") == []
        and record.get("historical_forward_returns_read_before_freeze") is False
    ):
        raise Campaign063NoReturnAuditError("audit implementation freeze changed")
    return record


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    _load_audit_implementation_freeze()
    static = verify_static_bindings()
    spec = load_protocol()
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign063NoReturnAuditError("Campaign063 data root changed")
    experiment_root = experiment_root.expanduser().resolve()
    existing = sorted(experiment_root.glob("*_campaign063_no_return_audit.json"))
    if existing:
        raise Campaign063NoReturnAuditError("Campaign063 no-return audit already exists")
    verification = candidate.verify_snapshot_files(
        SNAPSHOT_MANIFEST_PATH, workers=workers
    )
    prior, foundation, engine, _, _, _ = (
        c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    candidate_frame = engine.load_factor_frame(
        SNAPSHOT_MANIFEST_PATH, manifest, FACTOR_NAME
    )
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate_frame, eligible_keys, spec, FACTOR_NAME
    )
    del candidate_frame, eligible_keys, quality_frame
    gc.collect()
    if coverage.get("gate_passed_before_comparison_values") is not False:
        raise Campaign063NoReturnAuditError(
            "zero-eligible Campaign063 unexpectedly passed coverage"
        )
    uniqueness = {
        "comparison_values_loaded_after_coverage_pass": False,
        "comparison_factor_count": 0,
        "comparison_order_sha256_frozen_but_values_unopened": EXPECTED_COMPARISON_ORDER_SHA256,
        "comparisons": [],
        "all_required_comparisons_passed": False,
        "failure_reason": "coverage_gate_failed_zero_eligible_rows_due_structural_position236_zero_peer_variance",
    }
    timestamp = prior.research._timestamp()
    run_id = f"{timestamp}_campaign063_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign063_no_return_audit",
        "status": "completed_zero_admissible_factors_stop_before_comparison_values_historical_daily_prices_or_returns",
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
        "structural_variance_diagnosis": {
            "path": str(STRUCTURAL_DIAGNOSIS.resolve()),
            "sha256": STRUCTURAL_DIAGNOSIS_SHA256,
        },
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [],
        "admissible_factor_count": 0,
        "failed_factor_names": [FACTOR_NAME],
        "next_action": "record Campaign063 terminal without comparison or return access; start only a genuinely new factor definition in a later campaign",
        "minute_source_fields_read": list(candidate.RAW_COLUMNS),
        "cross_sectional_moment_fields_read": list(candidate.campaign031.market.BENCHMARK_COLUMNS),
        "comparison_factor_values_read": False,
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
        experiment_root.expanduser().resolve().glob("*_campaign063_no_return_audit.json")
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
