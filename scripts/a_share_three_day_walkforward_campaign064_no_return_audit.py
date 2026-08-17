#!/usr/bin/env python3
"""Run the frozen coverage-first Campaign064 no-return audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from scripts import a_share_three_day_walkforward_campaign062_features as c62_features
from scripts import a_share_three_day_walkforward_campaign062_no_return_audit as c62_audit
from scripts import a_share_three_day_walkforward_campaign063_features as c63_features
from scripts import a_share_three_day_walkforward_campaign064_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = candidate.FACTOR_NAME
PROTOCOL_SHA256 = candidate.PROTOCOL_SHA256
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_064_feature_snapshot_binding_20260805.json"
)
SNAPSHOT_BINDING_SHA256 = (
    "ece4c6c3899d186a7d23d3408c3d4056ab6c062f754bb45eafa8d72661ed430d"
)
SNAPSHOT_MANIFEST_PATH = (
    candidate.output_root(candidate.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "768ddf9babf07fc759d06b9e5d06bf4203d2e816bb8091e2daeb34f4ea21ea89"
)
SNAPSHOT_DATASET_SHA256 = (
    "676afa66570844ca8b5484f458801a95452249da0e277c9664eefd087acb152d"
)
EXPECTED_ROWS = 7_724_498
EXPECTED_PARTITIONS = 33_015
EXPECTED_ELIGIBLE_ROWS = 7_724_498
EXPECTED_COMPARISON_COUNT = 95
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.COMPARISON_ORDER_SHA256
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_064_no_return_audit_implementation_freeze_v3_20260805.json"
)
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_064/no_return"
)
C62_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign062_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign062_feature_library_v1/snapshot_manifest.json"
)
C62_SNAPSHOT_SHA256 = (
    "518131c1ecac2820a426d2d7de46552daf9009b476ed7efbf3d69ba555f1ac45"
)
C62_DATASET_SHA256 = (
    "5012eebb056fff75b6931390acaa5272629e70267ee5a32f46377c60994571a0"
)
C62_FACTOR = c62_features.FACTOR_NAME
C63_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign063_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign063_feature_library_v1/snapshot_manifest.json"
)
C63_SNAPSHOT_SHA256 = (
    "12fc8d8bf7df432608f4cb63b7c5337f2cd46d2a029c34d8b3e60c0f8906a098"
)
C63_DATASET_SHA256 = (
    "fd040477f3af2948976fda9a71f6d04a0bd9b9713a1b9b5a6dedf2f06f0c76df"
)
C63_FACTOR = c63_features.FACTOR_NAME


class Campaign064NoReturnAuditError(RuntimeError):
    """Fail-closed Campaign064 no-return audit error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign064NoReturnAuditError(f"{label} changed")


def load_protocol() -> dict[str, Any]:
    spec = candidate.load_protocol()
    comparisons = candidate.reconstruct_comparisons(spec)
    if (
        len(comparisons) != EXPECTED_COMPARISON_COUNT
        or candidate._comparison_order_digest(comparisons)
        != EXPECTED_COMPARISON_ORDER_SHA256
        or comparisons[-2:] != [
            {"name": C62_FACTOR, "score_direction": "higher"},
            {"name": C63_FACTOR, "score_direction": "higher"},
        ]
    ):
        raise Campaign064NoReturnAuditError("Campaign064 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return spec


def verify_static_bindings() -> dict[str, Any]:
    _require(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "snapshot manifest")
    binding_report = candidate.bindings.validate_record(
        SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT
    )
    if binding_report.get("all_bindings_passed") is not True:
        raise Campaign064NoReturnAuditError("snapshot binding validation failed")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    candidate._validate_manifest(manifest)
    if not (
        manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        == EXPECTED_ELIGIBLE_ROWS
    ):
        raise Campaign064NoReturnAuditError("candidate snapshot identity changed")
    prior_snapshots = (
        (
            "Campaign062",
            C62_SNAPSHOT_PATH,
            C62_SNAPSHOT_SHA256,
            C62_DATASET_SHA256,
        ),
        (
            "Campaign063",
            C63_SNAPSHOT_PATH,
            C63_SNAPSHOT_SHA256,
            C63_DATASET_SHA256,
        ),
    )
    for label, path, manifest_sha256, dataset_sha256 in prior_snapshots:
        _require(path, manifest_sha256, f"{label} snapshot")
        prior_manifest = json.loads(path.read_text(encoding="utf-8"))
        if prior_manifest.get("dataset_sha256") != dataset_sha256:
            raise Campaign064NoReturnAuditError(f"{label} dataset changed")
    return {
        "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256,
        "candidate_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": SNAPSHOT_DATASET_SHA256,
        "campaign062_manifest_sha256": C62_SNAPSHOT_SHA256,
        "campaign062_dataset_sha256": C62_DATASET_SHA256,
        "campaign063_manifest_sha256": C63_SNAPSHOT_SHA256,
        "campaign063_dataset_sha256": C63_DATASET_SHA256,
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": EXPECTED_COMPARISON_ORDER_SHA256,
    }


def _load_audit_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign064NoReturnAuditError("audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = record.get("audit_runner") or {}
    binding = record.get("snapshot_binding") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign064_no_return_audit_implementation_freeze_v3"
        and record.get("status")
        == "c62_verifier_binding_repair_frozen_after_coverage_and_first_93_comparisons_before_c62_c63_daily_price_or_return_values"
        and (REPO_ROOT / str(runner.get("path") or "")).resolve()
        == Path(__file__).resolve()
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and binding.get("sha256") == SNAPSHOT_BINDING_SHA256
        and record.get("quality_listing_keys_read_before_freeze") is True
        and record.get("candidate_snapshot_values_read_before_freeze") is True
        and record.get("coverage_or_capacity_metrics_computed_before_freeze") is True
        and record.get("coverage_gate_passed_before_freeze") is True
        and record.get("comparison_values_read_before_freeze") is True
        and record.get("completed_comparison_factor_count_before_freeze") == 93
        and record.get("campaign062_comparison_values_read_before_freeze") is False
        and record.get("campaign063_comparison_values_read_before_freeze") is False
        and record.get("historical_daily_price_fields_read_before_freeze") == []
        and record.get("historical_forward_returns_read_before_freeze") is False
    ):
        raise Campaign064NoReturnAuditError("audit implementation freeze changed")
    return record


def _install_frozen_candidate_range(engine: Any) -> None:
    expected = (0.0, 1.0)
    if (
        set(candidate.FACTOR_RANGES) != {FACTOR_NAME}
        or tuple(candidate.FACTOR_RANGES[FACTOR_NAME]) != expected
    ):
        raise Campaign064NoReturnAuditError("candidate factor range changed")
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    if FACTOR_NAME in ranges and tuple(ranges[FACTOR_NAME]) != expected:
        raise Campaign064NoReturnAuditError(
            "reused engine has a conflicting Campaign064 factor range"
        )
    ranges[FACTOR_NAME] = expected
    engine.FACTOR_RANGES = ranges


def _append_snapshot_comparison(
    *,
    comparisons: list[dict[str, Any]],
    verifications: dict[str, Any],
    manifest_path: Path,
    factor: str,
    verification_key: str,
    verify: Callable[[dict[str, Any], Path, int], dict[str, Any]],
    keys: Any,
    values: Any,
    gate: dict[str, Any],
    directions: dict[str, str],
    workers: int,
    engine: Any,
    comparison_engine: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verification = verify(manifest, manifest_path, workers)
    comparison_values = engine._load_filtered_comparison_values_explicit(
        manifest, [factor], keys
    )[factor]
    comparisons.append(
        comparison_engine._aligned_comparison_result(
            candidate_keys=keys,
            candidate_values=values,
            comparison_values=comparison_values,
            comparison=factor,
            direction=directions[factor],
            gate=gate,
        )
    )
    del comparison_values
    gc.collect()
    return comparisons, {**verifications, verification_key: verification}


def _verify_c62(manifest: dict[str, Any], path: Path, workers: int) -> dict[str, Any]:
    _install_c62_verifier_globals()
    return c62_features.verify_snapshot_files(manifest, path, workers)


def _install_c62_verifier_globals() -> None:
    c62_features._install_engine_globals()
    observed = tuple(
        c62_features.base._engine_globals.get("OUTPUT_COLUMNS") or ()
    )
    if observed != tuple(c62_features.OUTPUT_COLUMNS):
        raise Campaign064NoReturnAuditError(
            "Campaign062 verifier output columns were not restored"
        )


def _verify_c63(manifest: dict[str, Any], path: Path, workers: int) -> dict[str, Any]:
    del manifest
    return c63_features.verify_snapshot_files(path, workers=workers)


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    _load_audit_implementation_freeze()
    static = verify_static_bindings()
    spec = load_protocol()
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign064NoReturnAuditError("Campaign064 data root changed")
    experiment_root = experiment_root.expanduser().resolve()
    existing = sorted(experiment_root.glob("*_campaign064_no_return_audit.json"))
    if existing:
        raise Campaign064NoReturnAuditError("Campaign064 no-return audit already exists")
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    verification = candidate.verify_snapshot_files(
        SNAPSHOT_MANIFEST_PATH, workers=workers
    )
    prior, foundation, engine, _, candidate49, comparison_engine = (
        c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
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
        directions = {
            str(item["name"]): str(item["score_direction"])
            for item in gate["comparison_factors"]
        }
        keys, values = engine._sorted_candidate_arrays(quality_frame, FACTOR_NAME)
        snapshots = c62_audit.c61_audit._load_bound_prior_snapshots(workers)
        comparisons, source_verifications = (
            c62_audit.c61_audit._append_all_prior_comparisons(
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
        )
        comparisons, source_verifications = c62_audit._append_campaign061(
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
        comparisons, source_verifications = _append_snapshot_comparison(
            comparisons=comparisons,
            verifications=source_verifications,
            manifest_path=C62_SNAPSHOT_PATH,
            factor=C62_FACTOR,
            verification_key="campaign062_snapshot_file_verification",
            verify=_verify_c62,
            keys=keys,
            values=values,
            gate=gate,
            directions=directions,
            workers=workers,
            engine=engine,
            comparison_engine=comparison_engine,
        )
        comparisons, source_verifications = _append_snapshot_comparison(
            comparisons=comparisons,
            verifications=source_verifications,
            manifest_path=C63_SNAPSHOT_PATH,
            factor=C63_FACTOR,
            verification_key="campaign063_snapshot_file_verification",
            verify=_verify_c63,
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
    del quality_frame
    gc.collect()
    admitted = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_required_comparisons_passed"]
    )
    timestamp = prior.research._timestamp()
    run_id = f"{timestamp}_campaign064_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign064_no_return_audit",
        "status": "completed_with_one_admissible_factor_pending_walkforward_preregistration"
        if admitted
        else "completed_zero_admissible_factors_stop_before_historical_daily_prices_or_returns",
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
        "next_action": "freeze the exact one-trial Campaign064 walk-forward before reading 2019-2023 returns"
        if admitted
        else "record the no-return rejection and start only a genuinely new campaign",
        "minute_source_fields_read": list(candidate.RAW_COLUMNS),
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
        experiment_root.expanduser().resolve().glob("*_campaign064_no_return_audit.json")
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
        command.add_argument(
            "--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT
        )
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
