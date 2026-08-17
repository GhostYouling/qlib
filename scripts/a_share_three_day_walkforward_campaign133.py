#!/usr/bin/env python3
"""Run Campaign133's frozen anchored marginal PAVA development campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import (
    a_share_three_day_walkforward_campaign132_v3 as frozen_v3,
)  # noqa: E402

base = frozen_v3.frozen_v1
legacy = base.legacy
design = base.design

REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_133_preregistration_20260814.json"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_133_development_implementation_freeze_v3_20260814.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign133.py"
)
CONCEPT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_133_concept_scouting_20260814.json"
)
MODEL_AUDIT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_133_model_overlap_audit_20260814.json"
)
RUNTIME_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_133_bare_python_runtime_failure_20260814.json"
)
V1_LINT_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_133_v1_runner_ruff_unused_import_failure_20260814.json"
)
V2_INVOCATION_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_133_v2_direct_invocation_import_failure_20260814.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_133/walkforward_v3"
)

PROTOCOL_SHA256 = "533cb1cc7738bf91afd0d08bd97757638fc07cc85edf8af35ff57c69031b7371"
CONCEPT_SHA256 = "3cd3e99ccc3fecca997b0d618e46591395376a0b35742ed540ea704312518e12"
MODEL_AUDIT_SHA256 = "28890b1f0abd00c3936fc4817769ae0fa75abc90ab05217efe844466d9ef63b9"
RUNTIME_FAILURE_SHA256 = (
    "12a36dad6df94ef8957c163e02b113d61f0b0b848a3b3cbf72b3889512953693"
)
V1_LINT_FAILURE_SHA256 = (
    "cd5be21fd916eb2e32d8521fb39bdc8ac3c2722fa4e734047576643aaca4e9d1"
)
V2_INVOCATION_FAILURE_SHA256 = (
    "c859a6abfe7dac478da39deac31c0e66aa176f89ff1a6cdde212649f6d20a960"
)
FROZEN_V3_RUNNER_SHA256 = (
    "d2c22b1a9ca49768023c58f2bdf3118a8de53fa5f385476c8dcb8ee035e51ba2"
)
DESIGN_MANIFEST_SHA256 = base.DESIGN_MANIFEST_SHA256
DESIGN_DATASET_SHA256 = base.DESIGN_DATASET_SHA256
DESIGN_AUDIT_SHA256 = base.DESIGN_AUDIT_SHA256
TRIAL_ID = "wf133_complete140_anchor50_decile_pava_additive"
BIN_COUNT = 10
ANCHOR_WEIGHT = 0.5
NEUTRAL_FILL = 0.5
CHAIN_GENESIS = "0" * 64
_BASE_CONFIGURED = False


class Campaign133Error(RuntimeError):
    """Fail closed when a Campaign133 invariant or chronological gate changes."""


def ensure_base_runtime() -> None:
    """Install the audited Campaign132 design-support shim exactly once."""
    global _BASE_CONFIGURED
    if not _BASE_CONFIGURED:
        frozen_v3.configure_runtime()
        _BASE_CONFIGURED = True


def require_file(path: Path, expected: str, label: str) -> None:
    if len(expected) != 64 or not path.is_file() or base.file_sha256(path) != expected:
        raise Campaign133Error(f"{label} changed: {path}")


def implementation_freeze() -> dict[str, Any]:
    record = base.load_json(IMPLEMENTATION_FREEZE_PATH)
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign133_development_implementation_freeze_v3"
        and record.get("revision") == 3
        and record.get("status")
        == "frozen_before_first_campaign133_model_fit_or_training_return_read"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("design_manifest") or {}).get("sha256")
        == DESIGN_MANIFEST_SHA256
        and (record.get("design_audit") or {}).get("sha256") == DESIGN_AUDIT_SHA256
        and (record.get("frozen_campaign132_v3_runner") or {}).get("sha256")
        == FROZEN_V3_RUNNER_SHA256
        and (record.get("runner") or {}).get("sha256")
        == base.file_sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == base.file_sha256(TEST_PATH)
        and record.get("campaign133_model_fit_before_freeze") is False
        and record.get("campaign133_training_or_validation_return_read_before_freeze")
        is False
        and record.get("lockbox_2024_2025_return_read_before_freeze") is False
        and record.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise Campaign133Error("Campaign133 development implementation freeze changed")
    return record


def load_frozen_context() -> tuple[dict[str, Any], dict[str, Any]]:
    ensure_base_runtime()
    bindings = (
        (PROTOCOL_PATH, PROTOCOL_SHA256, "Campaign133 protocol"),
        (CONCEPT_PATH, CONCEPT_SHA256, "Campaign133 concept catalog"),
        (MODEL_AUDIT_PATH, MODEL_AUDIT_SHA256, "Campaign133 model audit"),
        (RUNTIME_FAILURE_PATH, RUNTIME_FAILURE_SHA256, "Campaign133 runtime failure"),
        (V1_LINT_FAILURE_PATH, V1_LINT_FAILURE_SHA256, "Campaign133 v1 lint failure"),
        (
            V2_INVOCATION_FAILURE_PATH,
            V2_INVOCATION_FAILURE_SHA256,
            "Campaign133 v2 invocation failure",
        ),
        (
            Path(frozen_v3.__file__).resolve(),
            FROZEN_V3_RUNNER_SHA256,
            "frozen Campaign132 v3 runner",
        ),
    )
    for path, expected, label in bindings:
        require_file(path, expected, label)
    protocol = base.load_json(PROTOCOL_PATH)
    _, template = base.load_frozen_context()
    catalog = protocol.get("trial_catalog") or []
    search = protocol.get("search_multiplicity") or {}
    algorithm = protocol.get("frozen_model_algorithm") or {}
    feature_library = protocol.get("complete_feature_library") or {}
    if not (
        protocol.get("kind")
        == "a_share_three_day_walkforward_campaign133_preregistration"
        and [item.get("trial_id") for item in catalog] == [TRIAL_ID]
        and search.get("trial_count") == 1
        and search.get("bin_count") == BIN_COUNT
        and search.get("anchor_weight_on_fitted_pava_level") == ANCHOR_WEIGHT
        and search.get("anchor_weight_on_original_favorable_percentile")
        == ANCHOR_WEIGHT
        and feature_library.get("numeric_feature_count") == design.FEATURE_COUNT
        and feature_library.get("numeric_feature_order_sha256")
        == design.FEATURE_ORDER_SHA256
        and (feature_library.get("design_support") or {}).get(
            "minimum_finite_components"
        )
        == design.MINIMUM_FINITE_COMPONENTS
        and (feature_library.get("design_support") or {}).get(
            "model_input_missing_fill"
        )
        == NEUTRAL_FILL
        and algorithm.get("cross_component_fitted_weights") is False
        and algorithm.get("interactions_or_trees") is False
        and len(protocol.get("walkforward_folds") or []) == 3
    ):
        raise Campaign133Error("Campaign133 frozen protocol semantics changed")
    return protocol, template


def bin_indices(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(matrix, dtype=np.float64)
    if values.ndim != 2:
        raise Campaign133Error("calibration input must be a matrix")
    finite = np.isfinite(values)
    if np.any((values[finite] < 0.0) | (values[finite] > 1.0)):
        raise Campaign133Error("favorable percentile outside [0,1]")
    filled = np.where(finite, values, NEUTRAL_FILL)
    bins = np.minimum(np.floor(filled * BIN_COUNT).astype(np.int8), BIN_COUNT - 1)
    return filled, bins


def weighted_pava(means: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Fit nondecreasing weighted means using deterministic adjacent pooling."""
    values = np.asarray(means, dtype=np.float64)
    mass = np.asarray(weights, dtype=np.float64)
    if (
        values.ndim != 1
        or mass.shape != values.shape
        or len(values) == 0
        or not np.isfinite(values).all()
        or not np.isfinite(mass).all()
        or np.any(mass <= 0.0)
    ):
        raise Campaign133Error("invalid weighted PAVA inputs")
    blocks: list[list[float | int]] = []
    for index, (value, weight) in enumerate(zip(values, mass, strict=True)):
        blocks.append([index, index + 1, float(weight), float(value * weight)])
        while len(blocks) >= 2:
            left = blocks[-2]
            right = blocks[-1]
            left_mean = float(left[3]) / float(left[2])
            right_mean = float(right[3]) / float(right[2])
            if left_mean <= right_mean:
                break
            blocks[-2:] = [
                [
                    int(left[0]),
                    int(right[1]),
                    float(left[2]) + float(right[2]),
                    float(left[3]) + float(right[3]),
                ]
            ]
    fitted = np.empty(len(values), dtype=np.float64)
    for start, end, weight, total in blocks:
        fitted[int(start) : int(end)] = float(total) / float(weight)
    if np.any(fitted[1:] < fitted[:-1]):
        raise Campaign133Error("weighted PAVA monotonicity failed")
    return fitted


def fit_calibration(
    matrix: np.ndarray,
    target: np.ndarray,
    weights: np.ndarray,
    valid: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    values = np.asarray(matrix, dtype=np.float64)
    y = np.asarray(target, dtype=np.float64)
    mass = np.asarray(weights, dtype=np.float64)
    support = np.asarray(valid, dtype=bool)
    if (
        values.ndim != 2
        or values.shape[1] != design.FEATURE_COUNT
        or len(y) != len(values)
        or len(mass) != len(values)
        or len(support) != len(values)
        or not np.any(support)
        or not np.isfinite(y[support]).all()
        or not np.isfinite(mass[support]).all()
        or np.any(mass[support] <= 0.0)
        or not math.isclose(float(mass[support].sum()), 1.0, abs_tol=1e-12)
    ):
        raise Campaign133Error("invalid calibration fit inputs")
    _, bins = bin_indices(values)
    levels = np.empty((design.FEATURE_COUNT, BIN_COUNT), dtype=np.float64)
    observed_bin_counts: list[int] = []
    for feature in range(design.FEATURE_COUNT):
        feature_bins = bins[support, feature].astype(np.int64)
        bin_mass = np.bincount(feature_bins, weights=mass[support], minlength=BIN_COUNT)
        bin_total = np.bincount(
            feature_bins, weights=mass[support] * y[support], minlength=BIN_COUNT
        )
        observed = np.flatnonzero(bin_mass > 0.0)
        if len(observed) == 0:
            raise Campaign133Error("calibration feature has no observed training bin")
        means = bin_total[observed] / bin_mass[observed]
        fitted = weighted_pava(means, bin_mass[observed])
        levels[feature] = np.interp(
            np.arange(BIN_COUNT, dtype=np.float64), observed, fitted
        )
        observed_bin_counts.append(int(len(observed)))
    if (
        not np.isfinite(levels).all()
        or np.any(levels < 0.0)
        or np.any(levels > 1.0)
        or np.any(levels[:, 1:] < levels[:, :-1])
    ):
        raise Campaign133Error(
            "calibration levels violate frozen range or monotonicity"
        )
    return levels, {
        "feature_count": design.FEATURE_COUNT,
        "bin_count": BIN_COUNT,
        "minimum_observed_bins_per_feature": min(observed_bin_counts),
        "maximum_observed_bins_per_feature": max(observed_bin_counts),
        "all_levels_nondecreasing": True,
        "levels_sha256": hashlib.sha256(levels.astype("<f8").tobytes()).hexdigest(),
    }


def calibration_scores(
    levels: np.ndarray, matrix: np.ndarray, eligible: np.ndarray
) -> np.ndarray:
    fitted = np.asarray(levels, dtype=np.float64)
    values = np.asarray(matrix, dtype=np.float64)
    support = np.asarray(eligible, dtype=bool)
    if (
        fitted.shape != (design.FEATURE_COUNT, BIN_COUNT)
        or values.ndim != 2
        or values.shape[1] != design.FEATURE_COUNT
        or len(support) != len(values)
    ):
        raise Campaign133Error("calibration score inputs changed")
    filled, bins = bin_indices(values)
    calibrated = fitted[np.arange(design.FEATURE_COUNT)[None, :], bins]
    scores = np.mean(
        ANCHOR_WEIGHT * calibrated + ANCHOR_WEIGHT * filled,
        axis=1,
        dtype=np.float64,
    )
    scores[~support] = np.nan
    if not np.isfinite(scores[support]).all():
        raise Campaign133Error("eligible calibration score is nonfinite")
    return scores


def fit_fold(
    template: dict[str, Any],
    fold: dict[str, Any],
    batch_size: int,
    output_root: Path,
) -> tuple[dict[str, Any], np.ndarray, dict[str, Any]]:
    training_start, training_end = fold["training"]
    panel, quotes, calendar, schedule, matrix, eligible = base.build_training_panel(
        template, training_end, batch_size
    )
    returns = pd.to_numeric(panel["forward_gross_return"], errors="coerce").copy()
    returns.loc[~eligible] = np.nan
    target = legacy.target_percentiles(panel["signal_date"], returns)
    valid, weights, weight_statistics = base.training_weights(
        panel["signal_date"], target, eligible
    )
    levels, calibration_statistics = fit_calibration(
        matrix, np.asarray(target, dtype=np.float64), weights, valid
    )
    model_path = output_root / f"fold_{fold['fold']}_models" / f"{TRIAL_ID}.f64"
    base.atomic_binary(model_path, levels.astype("<f8").tobytes())
    scores = calibration_scores(levels, matrix, eligible)
    panel[legacy._score_column(TRIAL_ID)] = scores
    trial = {"feature_set": [TRIAL_ID], "weights": [1.0]}
    training_metrics = legacy.engine.evaluate_trial_period(
        panel,
        quotes,
        calendar,
        schedule,
        trial,
        training_start,
        training_end,
        base.PURGE_SIGNAL_SESSIONS,
        include_sensitivity=False,
    )
    fit = {
        "family": "complete_140_numeric_library_anchor50_decile_pava_additive_calibration",
        "training": weight_statistics,
        "calibration": calibration_statistics,
        "anchor_weight_on_pava": ANCHOR_WEIGHT,
        "anchor_weight_on_original_percentile": ANCHOR_WEIGHT,
        "equal_component_weight": 1.0 / design.FEATURE_COUNT,
        "model_binary": {
            "path": str(model_path),
            "sha256": base.file_sha256(model_path),
            "bytes": model_path.stat().st_size,
            "dtype": "little_endian_float64",
            "shape": [design.FEATURE_COUNT, BIN_COUNT],
        },
    }
    return fit, levels, training_metrics


def validation_prefit_audit(
    fold: dict[str, Any],
    fit: dict[str, Any],
    levels: np.ndarray,
    output_root: Path,
) -> tuple[dict[str, Any], np.ndarray, pd.DataFrame]:
    validation_start, validation_end = fold["validation"]
    identities, matrix, _, eligible = base.load_design_years(
        [pd.Timestamp(validation_start).year]
    )
    scores = calibration_scores(levels, matrix, eligible)
    uniqueness = base.uniqueness_audit(
        identities["stock_day_key"].to_numpy(dtype=np.int64),
        matrix,
        scores,
        design.component_columns(),
    )
    score_binding = legacy.write_score_snapshot(
        output_root / f"fold_{fold['fold']}_validation_scores.parquet",
        identities,
        {TRIAL_ID: scores},
    )
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign133_fold_prefit_uniqueness",
        "status": "frozen_before_fold_validation_return_read",
        "created_at": base.utc_now(),
        "fold": int(fold["fold"]),
        "training": list(fold["training"]),
        "validation": [validation_start, validation_end],
        "fit": fit,
        "validation_score_snapshot": score_binding,
        "uniqueness": uniqueness,
        "all_140_comparisons_audited_before_validation_returns": True,
        "validation_daily_price_fields_read_before_record": [],
        "validation_forward_return_fields_read_before_record": False,
        "lockbox_2024_2025_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }
    path = output_root / f"fold_{fold['fold']}_prefit_uniqueness.json"
    legacy.atomic_json(path, payload)
    payload["record_binding"] = {"path": str(path), "sha256": base.file_sha256(path)}
    return payload, scores, identities


def concept_and_failure_entries() -> list[dict[str, Any]]:
    concept = base.load_json(CONCEPT_PATH)
    entries: list[dict[str, Any]] = []
    for item in concept["finite_prevalue_concept_catalog"]:
        entries.append(
            {
                "attempt_id": item["catalog_id"],
                "phase": "prevalue_concept_scouting",
                "name": item["name"],
                "outcome": item["decision"],
                "reason": item["reason"],
                "evidence": {"path": str(CONCEPT_PATH), "sha256": CONCEPT_SHA256},
                "component_values_read": False,
                "historical_forward_return_fields_read": False,
            }
        )
    for failure_path, failure_sha256 in (
        (RUNTIME_FAILURE_PATH, RUNTIME_FAILURE_SHA256),
        (V1_LINT_FAILURE_PATH, V1_LINT_FAILURE_SHA256),
        (V2_INVOCATION_FAILURE_PATH, V2_INVOCATION_FAILURE_SHA256),
    ):
        failure = base.load_json(failure_path)
        entries.append(
            {
                "attempt_id": failure["attempt_id"],
                "phase": "infrastructure_failure",
                "stage": failure["stage"],
                "outcome": failure["status"],
                "evidence": {
                    "path": str(failure_path),
                    "sha256": failure_sha256,
                },
                "scientific_result_changed": False,
                "historical_forward_return_fields_read": False,
            }
        )
    return entries


def build_ledger(trial_record: dict[str, Any]) -> dict[str, Any]:
    previous = CHAIN_GENESIS
    entries: list[dict[str, Any]] = []
    for record in [*concept_and_failure_entries(), trial_record]:
        entry = {**record, "previous_entry_sha256": previous}
        entry["entry_sha256"] = base.value_sha256(entry)
        previous = entry["entry_sha256"]
        entries.append(entry)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign133_trial_ledger",
        "append_only": True,
        "campaign": {"protocol_sha256": PROTOCOL_SHA256},
        "chain_genesis": CHAIN_GENESIS,
        "entries": entries,
        "entry_count": len(entries),
        "prevalue_concept_attempt_count": 6,
        "infrastructure_failure_attempt_count": 3,
        "model_trial_attempt_count": 1,
        "chain_tip_sha256": previous,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }


def run_development(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_run:
        raise Campaign133Error("run-development requires --confirm-run")
    implementation_freeze()
    protocol, template = load_frozen_context()
    verification = design.verify_snapshot(base.DEFAULT_DESIGN_MANIFEST)
    output_root = Path(args.output_root).expanduser().resolve()
    report_path = output_root / "development_report.json"
    if report_path.exists():
        report = base.load_json(report_path)
        return {
            "status": "development_already_complete_idempotent",
            "report_path": str(report_path),
            "report_sha256": base.file_sha256(report_path),
            "survivor_count": report["survivor_count"],
        }
    output_root.mkdir(parents=True, exist_ok=True)
    if list(output_root.iterdir()):
        raise Campaign133Error(
            "incomplete Campaign133 output exists; preserve it and use an explicit recovery revision"
        )
    intent = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign133_development_intent",
        "status": "training_return_open_pending_chronological_completion",
        "opened_at": base.utc_now(),
        "protocol_sha256": PROTOCOL_SHA256,
        "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
        "design_audit_sha256": DESIGN_AUDIT_SHA256,
        "runner_sha256": base.file_sha256(Path(__file__).resolve()),
        "validation_returns_may_be_read_only_after_each_fold_prefit_uniqueness_record": True,
        "lockbox_2024_2025_remains_closed": True,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }
    legacy.atomic_json(output_root / "development_intent.json", intent)
    folds = [
        {
            "fold": int(item["fold"]),
            "training": list(item["training"]),
            "validation": list(item["validation"]),
        }
        for item in protocol["walkforward_folds"]
    ]
    record: dict[str, Any] = {
        "attempt_id": TRIAL_ID,
        "trial_id": TRIAL_ID,
        "phase": "development_walkforward",
        "created_at": intent["opened_at"],
        "formula": "mean_j(0.5*training_PAVA10_j[bin(x_j)]+0.5*x_j) over the frozen 140 favorable percentiles",
        "direction": "higher",
        "source_feature_count": design.FEATURE_COUNT,
        "source_feature_order_sha256": design.FEATURE_ORDER_SHA256,
        "bin_count": BIN_COUNT,
        "anchor_weight": ANCHOR_WEIGHT,
        "component_weight": 1.0 / design.FEATURE_COUNT,
        "folds": [],
        "validation_metrics": [],
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    live = True
    try:
        for fold in folds:
            if not live:
                break
            print(
                f"fold {fold['fold']}: loading contained training returns and fitting PAVA maps",
                flush=True,
            )
            fit, levels, training_metrics = fit_fold(
                template, fold, args.batch_size, output_root
            )
            print(
                f"fold {fold['fold']}: auditing validation score against all 140 components before returns",
                flush=True,
            )
            prefit, scores, identities = validation_prefit_audit(
                fold, fit, levels, output_root
            )
            fold_record = {
                "fold": fold["fold"],
                "fit": fit,
                "training_metrics": training_metrics,
                "prefit_uniqueness_record": prefit["record_binding"],
                "uniqueness": prefit["uniqueness"],
                "validation_metrics": None,
            }
            record["folds"].append(fold_record)
            if not prefit["uniqueness"]["all_required_comparisons_passed"]:
                record["terminal_before_validation_return_reason"] = (
                    f"fold_{fold['fold']}_uniqueness_failed"
                )
                live = False
                continue
            print(
                f"fold {fold['fold']}: uniqueness passed; reading contained validation returns",
                flush=True,
            )
            validation = legacy.evaluate_validation(
                template,
                fold,
                {TRIAL_ID: scores},
                identities,
                args.batch_size,
            )
            metrics_payload = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign133_fold_validation_metrics",
                "status": "completed_after_bound_prefit_uniqueness",
                "created_at": base.utc_now(),
                "fold": fold["fold"],
                "prefit_uniqueness_record": prefit["record_binding"],
                "validation_metrics": validation,
                "lockbox_2024_2025_return_fields_read": False,
                "candidate49_historical_return_read": False,
                "candidate49_ledgers_changed": False,
            }
            metrics_path = output_root / f"fold_{fold['fold']}_validation_metrics.json"
            legacy.atomic_json(metrics_path, metrics_payload)
            fold_record["validation_metrics"] = validation[TRIAL_ID]
            fold_record["validation_metrics_binding"] = {
                "path": str(metrics_path),
                "sha256": base.file_sha256(metrics_path),
            }
            record["validation_metrics"].append(validation[TRIAL_ID])
        record["decision"] = legacy.survivor_decision(record)
        record["status"] = (
            "development_survivor_gate_passed"
            if record["decision"]["passed"]
            else "development_rejected"
        )
        survivors = [TRIAL_ID] if record["decision"]["passed"] else []
        ledger = build_ledger(record)
        ledger_path = output_root / "trial_ledger.json"
        legacy.atomic_json(ledger_path, ledger)
        survivor_record = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign133_development_survivors",
            "status": "frozen_before_2024_2025_return_read",
            "created_at": base.utc_now(),
            "ledger": {
                "path": str(ledger_path),
                "sha256": base.file_sha256(ledger_path),
            },
            "trial_decisions": {TRIAL_ID: record["decision"]},
            "selected_lockbox_survivor_trial_ids": survivors,
            "selected_survivor_count": len(survivors),
            "maximum_survivors": 1,
            "lockbox_return_fields_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
        }
        survivor_path = output_root / "development_survivors.json"
        legacy.atomic_json(survivor_path, survivor_record)
        report = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign133_development_report",
            "status": "development_complete_survivors_frozen",
            "created_at": base.utc_now(),
            "protocol_sha256": PROTOCOL_SHA256,
            "design_verification": verification,
            "trial_count": 1,
            "ledger_entry_count": ledger["entry_count"],
            "validation_return_reading_trial_count": int(
                len(record["validation_metrics"]) == 3
            ),
            "survivor_count": len(survivors),
            "selected_survivor_trial_ids": survivors,
            "ledger": {
                "path": str(ledger_path),
                "sha256": base.file_sha256(ledger_path),
            },
            "survivors": {
                "path": str(survivor_path),
                "sha256": base.file_sha256(survivor_path),
            },
            "lockbox_2024_2025_opened": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "investment_advice": False,
        }
        legacy.atomic_json(report_path, report)
        return {
            "status": report["status"],
            "trial_count": 1,
            "survivor_count": len(survivors),
            "selected_survivor_trial_ids": survivors,
            "report_path": str(report_path),
            "report_sha256": base.file_sha256(report_path),
        }
    except BaseException as error:
        failure = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign133_development_failure",
            "status": "failed_preserved_requires_explicit_recovery_revision",
            "created_at": base.utc_now(),
            "error_type": type(error).__name__,
            "error": str(error),
            "training_or_validation_returns_may_have_been_read": True,
            "lockbox_2024_2025_return_fields_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
        }
        legacy.atomic_json(output_root / "development_failure.json", failure)
        raise


def plan(args: argparse.Namespace) -> dict[str, Any]:
    implementation_freeze()
    protocol, _ = load_frozen_context()
    verification = design.verify_snapshot(base.DEFAULT_DESIGN_MANIFEST)
    output_root = Path(args.output_root).expanduser().resolve()
    empty_or_absent = not output_root.exists() or not list(output_root.iterdir())
    ready = bool(
        empty_or_absent
        and verification.get("dataset_sha256") == DESIGN_DATASET_SHA256
        and len(protocol.get("walkforward_folds") or []) == 3
    )
    return {
        "status": (
            "ready_to_open_2019_2023_training_returns"
            if ready
            else "not_ready_preserve_existing_output"
        ),
        "ready": ready,
        "trial_count": 1,
        "fold_count": 3,
        "output_root": str(output_root),
        "design_verification": verification,
        "historical_daily_price_or_forward_return_values_read_by_plan": False,
        "lockbox_2024_2025_return_fields_read_by_plan": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }


def status(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root).expanduser().resolve()
    result: dict[str, Any] = {
        "status": "frozen_pending_development",
        "output_root": str(output_root),
        "implementation_freeze_exists": IMPLEMENTATION_FREEZE_PATH.is_file(),
        "historical_daily_price_or_return_values_read_by_status": False,
        "lockbox_2024_2025_return_fields_read_by_status": False,
        "candidate49_ledgers_changed_by_status": False,
        "provider_request_issued_by_status": False,
    }
    if (output_root / "development_intent.json").exists():
        result["status"] = "development_opened_or_incomplete"
    if (output_root / "development_failure.json").exists():
        result["status"] = "development_failed_preserved"
    if (output_root / "development_report.json").exists():
        report = base.load_json(output_root / "development_report.json")
        result["status"] = report["status"]
        result["survivor_count"] = report["survivor_count"]
        result["selected_survivor_trial_ids"] = report["selected_survivor_trial_ids"]
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    subcommands = value.add_subparsers(dest="command", required=True)
    subcommands.add_parser("status")
    subcommands.add_parser("plan")
    development = subcommands.add_parser("run-development")
    development.add_argument("--batch-size", type=int, default=100)
    development.add_argument("--confirm-run", action="store_true")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "status":
            payload = status(args)
        elif args.command == "plan":
            payload = plan(args)
        elif args.command == "run-development":
            payload = run_development(args)
        else:
            raise Campaign133Error(f"unsupported command: {args.command}")
    except (
        Campaign133Error,
        base.Campaign132Error,
        ValueError,
        FileNotFoundError,
    ) as error:
        print(
            json.dumps(
                {"status": "failed", "error": str(error)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
            default=legacy.engine.research._json_default,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
