#!/usr/bin/env python3
"""Snapshot-bound Campaign056 ordered no-return audit implementation."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset

from scripts import a_share_three_day_walkforward_campaign055_features_v7 as prior_audit
from scripts import a_share_three_day_walkforward_campaign056_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_056"
)
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_056_feature_snapshot_binding_20260804.json"
)
SNAPSHOT_BINDING_SHA256 = "c9e8e1edeeb1ded3bb1d913d078f7cf26c06f5b2c9e88124aa774355a57e92f2"
SNAPSHOT_MANIFEST_PATH = (
    DEFAULT_DATA_ROOT
    / "derived/a_share/rich/tushare/minute_walkforward_campaign056_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign056_feature_library_v1/"
    "snapshot_manifest.json"
)
SNAPSHOT_MANIFEST_SHA256 = "cec4ce7db7a5a0a1715a8a117a09b74afe75bd94e3042df52493678ca6d6031b"
SNAPSHOT_DATASET_SHA256 = "b29accb9698fd6d62238540f49b85a32c6a3e7fd882bc64cb7fabd7ef1ec1d02"
EXPECTED_ROWS = 7_724_498
EXPECTED_PARTITIONS = 33_015
EXPECTED_ELIGIBLE_ROWS = 7_715_898
EXPECTED_COMPARISON_COUNT = 79
EXPECTED_COMPARISON_ORDER_SHA256 = (
    "669a996cc0b8d2582f8a1c0cd2f7d9a8503fdcfe7fb5f1b79033ac7832bb4e67"
)
C55_SNAPSHOT_PATH = (
    prior_audit.runner.output_root(prior_audit.runner.DEFAULT_DATA_ROOT)
    / "snapshot_manifest.json"
)


class Campaign056NoReturnAuditError(RuntimeError):
    """Fail-closed Campaign056 no-return audit error."""


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    path = path.expanduser().resolve()
    if not path.is_file() or candidate._sha256(path) != expected_sha256:
        raise Campaign056NoReturnAuditError(f"{label} changed: {path}")


def _load_protocol() -> dict[str, Any]:
    spec = candidate._load_protocol()
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    if (
        len(comparisons) != EXPECTED_COMPARISON_COUNT
        or candidate._comparison_order_digest(comparisons)
        != EXPECTED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign056NoReturnAuditError(
            "Campaign056 comparison order changed"
        )
    return spec


def verify_static_bindings() -> dict[str, Any]:
    """Verify every Campaign056 identity needed before any value load."""

    _require_file(
        candidate.DEFAULT_PROTOCOL,
        candidate.PROTOCOL_SHA256,
        "Campaign056 no-return protocol",
    )
    _require_file(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    _require_file(
        SNAPSHOT_MANIFEST_PATH,
        SNAPSHOT_MANIFEST_SHA256,
        "authoritative Campaign056 snapshot manifest",
    )
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    candidate._validate_manifest(manifest)
    if manifest.get("dataset_sha256") != SNAPSHOT_DATASET_SHA256:
        raise Campaign056NoReturnAuditError("Campaign056 snapshot dataset changed")
    spec = _load_protocol()
    comparisons = spec["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    return {
        "snapshot_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "snapshot_dataset_sha256": SNAPSHOT_DATASET_SHA256,
        "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256,
        "comparison_count": len(comparisons),
        "comparison_order_sha256": candidate._comparison_order_digest(comparisons),
        "comparison_first": comparisons[0],
        "comparison_last": comparisons[-1],
    }


def load_candidate_frame(
    manifest_path: Path,
    manifest: dict[str, Any],
) -> pd.DataFrame:
    """Load only the bound Campaign056 factor and eligibility flag."""

    manifest_path = manifest_path.expanduser().resolve()
    records = list(manifest.get("files") or [])
    if (
        manifest_path != SNAPSHOT_MANIFEST_PATH.resolve()
        or len(records) != EXPECTED_PARTITIONS
        or manifest.get("partitions") != EXPECTED_PARTITIONS
        or manifest.get("rows") != EXPECTED_ROWS
        or manifest.get("dataset_sha256") != SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign056NoReturnAuditError(
            "Campaign056 candidate-loader manifest identity changed"
        )
    root = (manifest_path.parent / "partitions").resolve()
    paths: list[str] = []
    for record in records:
        path = Path(str(record.get("path"))).expanduser().resolve()
        if path.parent.parent != root:
            raise Campaign056NoReturnAuditError(
                f"Campaign056 candidate partition escapes root: {path}"
            )
        paths.append(str(path))
    factor = candidate.FACTOR_NAME
    columns = ["trade_date", "symbol", factor, f"{factor}_eligible"]
    dataset = pa_dataset.dataset(paths, format="parquet")
    table = dataset.to_table(columns=columns, use_threads=True)
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    if len(frame) != EXPECTED_ROWS:
        raise Campaign056NoReturnAuditError(
            "Campaign056 candidate-loader row count changed"
        )
    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"], errors="coerce"
    ).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    frame[f"{factor}_eligible"] = (
        frame[f"{factor}_eligible"].astype("boolean").fillna(False).astype(bool)
    )
    frame[factor] = pd.to_numeric(frame[factor], errors="coerce")
    eligible = frame[f"{factor}_eligible"]
    values = frame.loc[eligible, factor].to_numpy(dtype=float)
    if (
        frame["trade_date"].isna().any()
        or frame.duplicated(["trade_date", "symbol"]).any()
        or not np.isfinite(values).all()
        or (values < candidate.LOWER_BOUND).any()
        or (values > candidate.UPPER_BOUND).any()
        or frame.loc[~eligible, factor].notna().any()
        or int(eligible.sum()) != EXPECTED_ELIGIBLE_ROWS
    ):
        raise Campaign056NoReturnAuditError(
            "Campaign056 candidate-loader values or keys are invalid"
        )
    frame["symbol"] = frame["symbol"].astype("category")
    return frame


def _load_bound_prior_snapshots(workers: int) -> dict[str, Any]:
    """Load and verify the C52-C55 snapshot identities used by the prior chain."""

    c55_path = C55_SNAPSHOT_PATH.resolve()
    _require_file(
        c55_path,
        prior_audit.EXPECTED_SNAPSHOT_MANIFEST_SHA256,
        "Campaign055 terminal snapshot",
    )
    c55_manifest = json.loads(c55_path.read_text(encoding="utf-8"))
    if c55_manifest.get("dataset_sha256") != prior_audit.EXPECTED_SNAPSHOT_DATASET_SHA256:
        raise Campaign056NoReturnAuditError("Campaign055 snapshot dataset changed")
    prior_audit.runner._install_engine_globals()
    c55_verification = prior_audit.runner.verify_snapshot_files(
        c55_manifest, c55_path, workers
    )

    c54 = prior_audit.c54
    c54_path = prior_audit.C54_SNAPSHOT_PATH
    _require_file(
        c54_path,
        prior_audit.EXPECTED_C54_SNAPSHOT_SHA256,
        "Campaign054 terminal snapshot",
    )
    c54_manifest = json.loads(c54_path.read_text(encoding="utf-8"))
    if c54_manifest.get("dataset_sha256") != prior_audit.EXPECTED_C54_DATASET_SHA256:
        raise Campaign056NoReturnAuditError("Campaign054 snapshot dataset changed")
    c54._install_engine_globals()
    c54_verification = c54.verify_snapshot_files(c54_manifest, c54_path, workers)

    c53_path = prior_audit.prior_audit.C53_SNAPSHOT_PATH
    _require_file(
        c53_path,
        prior_audit.prior_audit.C53_SNAPSHOT_SHA256,
        "Campaign053 terminal snapshot",
    )
    c53_manifest = json.loads(c53_path.read_text(encoding="utf-8"))
    if c53_manifest.get("dataset_sha256") != prior_audit.prior_audit.C53_DATASET_SHA256:
        raise Campaign056NoReturnAuditError("Campaign053 snapshot dataset changed")
    prior_audit.terminal._install_engine_globals()
    c53_verification = prior_audit.terminal.verify_snapshot_files(
        c53_manifest, c53_path, workers
    )

    c52_path = prior_audit.terminal.C52_SNAPSHOT_PATH
    _require_file(
        c52_path,
        prior_audit.terminal.C52_SNAPSHOT_SHA256,
        "Campaign052 terminal snapshot",
    )
    c52_manifest = json.loads(c52_path.read_text(encoding="utf-8"))
    if c52_manifest.get("dataset_sha256") != prior_audit.terminal.C52_DATASET_SHA256:
        raise Campaign056NoReturnAuditError("Campaign052 snapshot dataset changed")
    prior_audit.terminal.previous._install_engine_globals()
    c52_verification = prior_audit.terminal.previous.verify_snapshot_files(
        c52_manifest, c52_path, workers
    )
    return {
        "c52_manifest": c52_manifest,
        "c52_verification": c52_verification,
        "c53_manifest": c53_manifest,
        "c53_verification": c53_verification,
        "c54_manifest": c54_manifest,
        "c54_verification": c54_verification,
        "c55_manifest": c55_manifest,
        "c55_verification": c55_verification,
    }


def _append_all_prior_comparisons(
    *,
    data_root: Path,
    workers: int,
    keys: np.ndarray,
    values: np.ndarray,
    gate: dict[str, Any],
    directions: dict[str, str],
    snapshots: dict[str, Any],
    engine: Any,
    candidate49: Any,
    comparison_engine: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reconstruct the exact 79-factor order: prior 78, then C55."""

    comparisons, verifications = prior_audit._append_prior_comparisons(
        data_root=data_root,
        workers=workers,
        keys=keys,
        values=values,
        gate=gate,
        directions=directions,
        c52_manifest=snapshots["c52_manifest"],
        c52_verification=snapshots["c52_verification"],
        c53_manifest=snapshots["c53_manifest"],
        c53_verification=snapshots["c53_verification"],
        engine=engine,
        candidate49=candidate49,
        comparison_engine=comparison_engine,
    )
    for factor, manifest in (
        (prior_audit.c54.FACTOR_NAME, snapshots["c54_manifest"]),
        (prior_audit.runner.FACTOR_NAME, snapshots["c55_manifest"]),
    ):
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
    verifications = {
        **verifications,
        "campaign054_snapshot_file_verification": snapshots["c54_verification"],
        "campaign055_snapshot_file_verification": snapshots["c55_verification"],
    }
    return comparisons, verifications


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Run coverage first, uniqueness second, and stop before all returns."""

    if workers < 1:
        raise Campaign056NoReturnAuditError("workers must be positive")
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign056NoReturnAuditError("Campaign056 data root changed")
    verify_static_bindings()
    spec = _load_protocol()
    manifest_path = SNAPSHOT_MANIFEST_PATH.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing = sorted(experiment_root.glob("*_campaign056_no_return_audit.json"))
    if existing:
        if len(existing) != 1:
            raise Campaign056NoReturnAuditError(
                "existing Campaign056 audit is ambiguous"
            )
        return existing[0]

    candidate_verification = candidate.verify_snapshot_files(
        manifest_path, workers=workers
    )
    prior_audit.runner._install_engine_globals()
    prior, foundation, engine, _, candidate49, comparison_engine = (
        prior_audit.terminal.campaign044._context()
    )
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    candidate_frame = load_candidate_frame(manifest_path, manifest)
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate_frame,
        eligible_keys,
        spec,
        candidate.FACTOR_NAME,
    )
    del candidate_frame, eligible_keys
    gc.collect()

    if coverage["gate_passed_before_comparison_values"]:
        snapshots = _load_bound_prior_snapshots(workers)
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        expected_order = [str(item["name"]) for item in gate["comparison_factors"]]
        directions = {
            str(item["name"]): str(item["score_direction"])
            for item in gate["comparison_factors"]
        }
        keys, values = engine._sorted_candidate_arrays(
            quality_frame, candidate.FACTOR_NAME
        )
        comparisons, comparison_verifications = _append_all_prior_comparisons(
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
        observed_order = [str(item["comparison_factor"]) for item in comparisons]
        observed_correlations = [
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        uniqueness_passed = bool(
            observed_order == expected_order
            and len(comparisons) == EXPECTED_COMPARISON_COUNT
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": len(comparisons),
            "comparison_order_matches_preregistration": observed_order == expected_order,
            **comparison_verifications,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": (
                max(observed_correlations) if observed_correlations else None
            ),
            "all_required_comparisons_passed": uniqueness_passed,
        }
        del keys, values, snapshots
        gc.collect()
    else:
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": False,
            "comparisons": [],
            "all_required_comparisons_passed": False,
            "failure_reason": "coverage_gate_failed",
        }

    admitted = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_required_comparisons_passed"]
    )
    run_id = f"{prior.research._timestamp()}_campaign056_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign056_no_return_audit",
        "status": (
            "completed_with_one_admissible_factor_pending_walkforward_preregistration"
            if admitted
            else "completed_zero_admissible_factors_stop_before_historical_returns"
        ),
        "run_id": run_id,
        "created_at": prior.research._timestamp(),
        "protocol": {
            "path": str(candidate.DEFAULT_PROTOCOL.resolve()),
            "sha256": candidate.PROTOCOL_SHA256,
        },
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": SNAPSHOT_DATASET_SHA256,
        },
        "snapshot_publication_binding": {
            "path": str(SNAPSHOT_BINDING.resolve()),
            "sha256": SNAPSHOT_BINDING_SHA256,
        },
        "snapshot_file_verification": candidate_verification,
        "coverage_and_capacity": {candidate.FACTOR_NAME: coverage},
        "uniqueness": {candidate.FACTOR_NAME: uniqueness},
        "admissible_factor_names": [candidate.FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [candidate.FACTOR_NAME],
        "next_action": (
            "freeze the exact one-trial Campaign056 walk-forward catalog before reading 2019-2023 returns"
            if admitted
            else "record the no-return rejection and design a genuinely new campaign"
        ),
        "source_fields_read": list(candidate.RAW_COLUMNS),
        "minute_amount_fields_read": ["amount"],
        "minute_open_high_low_close_volume_fields_read": [],
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "provider_request_issued": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


def status(
    data_root: Path = DEFAULT_DATA_ROOT,
    experiment_root: Path = DEFAULT_EXPERIMENT_ROOT,
) -> dict[str, Any]:
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    bindings = verify_static_bindings() if data_root == DEFAULT_DATA_ROOT.resolve() else None
    audits = sorted(experiment_root.glob("*_campaign056_no_return_audit.json"))
    return {
        **(bindings or {}),
        "data_root": str(data_root),
        "snapshot_manifest_path": str(SNAPSHOT_MANIFEST_PATH.resolve()),
        "snapshot_exists": SNAPSHOT_MANIFEST_PATH.is_file(),
        "audit_count": len(audits),
        "audit_paths": [str(path.resolve()) for path in audits],
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("no-return-audit")
    audit.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    audit.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    audit.add_argument("--workers", type=int, default=4)
    inspect = subparsers.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    inspect.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "no-return-audit":
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
        payload = status(args.data_root, args.experiment_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
