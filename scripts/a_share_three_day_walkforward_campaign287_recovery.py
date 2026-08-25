#!/usr/bin/env python3
"""Recover Campaign287 after the frozen DatetimeIndex.eq prefit API failure."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign as engine
from scripts import a_share_three_day_walkforward_campaign287 as campaign


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = campaign.OUTPUT_ROOT
FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_287_prefit_api_recovery_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign287_recovery.py"
)
FAILURE_EVIDENCE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_287_prefit_datetimeindex_api_failure_20260825.json"
)
FAILURE_EVIDENCE_SHA256 = (
    "cf9d1fc8828415cbdd4ff5c2528e187bd2322c37c1b99c71252aa86e5be704b9"
)
ARTIFACT_SHA256 = {
    "design_evidence.json": "286a269d238659d91f7abe58e8efd5a7d5ad172a8d70fd9b224c7d8d5473d2e5",
    "development_intent.json": "19c9385f11fe817f7a38f4ebc43420a63aaa82d289616534b6b7dd19250e723c",
    "development_failure.json": "6d4d89fd88ecfb329c7565f2e771e942c4fcdea8e671e64875c1ae3799762930",
    f"fold_1_model/{campaign.TRIAL_ID}.npz": "8288228b3737b4ebdfd6bbc3d9e279188cbdd7282b599e6f6251aae2efd756cf",
}


class Campaign287RecoveryError(RuntimeError):
    """Fail closed when the exact Campaign287 recovery boundary changes."""


def require_file(path: Path, expected: str, label: str) -> None:
    try:
        campaign.require_file(path, expected, label)
    except campaign.Campaign287Error as error:
        raise Campaign287RecoveryError(str(error)) from error


def validate_artifacts() -> None:
    require_file(
        FAILURE_EVIDENCE_PATH, FAILURE_EVIDENCE_SHA256, "Campaign287 failure evidence"
    )
    for relative, expected in ARTIFACT_SHA256.items():
        require_file(OUTPUT_ROOT / relative, expected, f"Campaign287 {relative}")


def validate_freeze() -> dict[str, Any]:
    campaign.validate_development_freeze()
    campaign.validate_common()
    validate_artifacts()
    if not FREEZE_PATH.is_file():
        raise Campaign287RecoveryError("Campaign287 recovery freeze is missing")
    record = campaign.load_json(FREEZE_PATH)
    runner = record.get("runner") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign287_prefit_api_recovery_implementation_freeze"
        and record.get("status")
        == "frozen_after_fold1_training_api_failure_before_any_validation_return_read"
        and (record.get("protocol") or {}).get("sha256") == campaign.PROTOCOL_SHA256
        and (record.get("failure_evidence") or {}).get("sha256")
        == FAILURE_EVIDENCE_SHA256
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == campaign.file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == campaign.file_sha256(TEST_PATH)
        and boundary.get("fold1_training_return_reread_by_recovery") is False
        and boundary.get("validation_return_read_before_recovery_freeze") is False
        and boundary.get("model_formula_weights_or_gate_change") is False
        and boundary.get("lockbox_2024_2025_return_read") is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign287RecoveryError("Campaign287 recovery freeze changed")
    return record


def load_fold1_model() -> campaign.WeightedMLPRegressor:
    path = OUTPUT_ROOT / f"fold_1_model/{campaign.TRIAL_ID}.npz"
    with np.load(path, allow_pickle=False) as payload:
        parameters = json.loads(str(payload["parameters_json"].item()))
        if parameters != campaign.MODEL_PARAMETERS:
            raise Campaign287RecoveryError("persisted fold1 model parameters changed")
        model = campaign.WeightedMLPRegressor(parameters)
        model.weights_ = {
            name: np.asarray(payload[name], dtype=np.float32)
            for name in ("w1", "b1", "w2", "b2")
        }
        model.loss_curve_ = np.asarray(payload["loss_curve"], dtype=np.float64).tolist()
    probe = np.zeros((2, campaign.FEATURE_COUNT), dtype=np.float32)
    if not np.isfinite(model.predict(probe)).all():
        raise Campaign287RecoveryError("persisted fold1 model is invalid")
    return model


def reconstructed_fold1_fit(
    manifest: dict[str, Any], evidence: dict[str, Any]
) -> dict[str, Any]:
    bundle = campaign.fold_design_bundle(campaign.FOLDS[0], manifest)
    campaign.compare_fold_design(bundle, evidence)
    path = OUTPUT_ROOT / f"fold_1_model/{campaign.TRIAL_ID}.npz"
    model = load_fold1_model()
    return {
        "trial_id": campaign.TRIAL_ID,
        "resolved_parameters": campaign.MODEL_PARAMETERS,
        "training": {
            "status": "not_persisted_before_prefit_api_failure",
            "fold1_training_return_reread_by_recovery": False,
        },
        "selected_design": bundle["record"]["selected_design"],
        "zero_return_fold_design_sha256": bundle["record"]["fold_design_sha256"],
        "preprocessing": bundle["record"]["preprocessing"],
        "loss_curve": model.loss_curve_,
        "initial_loss": model.loss_curve_[0],
        "final_loss": model.loss_curve_[-1],
        "model_artifact": {
            "path": str(path),
            "sha256": ARTIFACT_SHA256[f"fold_1_model/{campaign.TRIAL_ID}.npz"],
            "bytes": path.stat().st_size,
        },
        "numpy_version": np.__version__,
        "recovered_without_model_refit": True,
    }


def fixed_validation_prefit(
    fold: dict[str, Any],
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    model: campaign.WeightedMLPRegressor,
    fit: dict[str, Any],
) -> tuple[dict[str, np.ndarray], pd.DataFrame, dict[str, Any]]:
    """Identical frozen prefit logic with only DatetimeIndex equality repaired."""

    bundle = campaign.fold_design_bundle(fold, manifest)
    campaign.compare_fold_design(bundle, evidence)
    year = pd.Timestamp(fold["validation"][0]).year
    identities, matrix, eligible, design_stats = campaign.campaign286.load_design_years(
        [year], manifest
    )
    score = campaign.model_scores(
        model, matrix, eligible, bundle["centers"], bundle["scales"]
    )
    calendar = campaign.local_calendar()
    schedule = engine.purged_period_schedule(
        engine.global_signal_schedule(calendar),
        fold["validation"][0],
        fold["validation"][1],
        campaign.PURGE_SIGNAL_SESSIONS,
    )
    dates = pd.DatetimeIndex(identities["trade_date"]).normalize()
    good_sessions = 0
    minimum_finite = None
    minimum_unique = None
    for session in schedule["signal_date"]:
        mask = (dates == pd.Timestamp(session)) & eligible & np.isfinite(score)
        count = int(mask.sum())
        unique = int(np.unique(score[mask]).size)
        minimum_finite = count if minimum_finite is None else min(minimum_finite, count)
        minimum_unique = unique if minimum_unique is None else min(minimum_unique, unique)
        if count >= 50 and unique >= 2:
            good_sessions += 1
    gate_passed = bool(
        good_sessions >= 60
        and minimum_finite is not None
        and minimum_finite >= 50
        and minimum_unique is not None
        and minimum_unique >= 2
    )
    snapshot = campaign.campaign286.write_score_snapshot(
        OUTPUT_ROOT / f"fold_{fold['fold']}_validation_scores.parquet",
        identities,
        {campaign.TRIAL_ID: score},
    )
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign287_fold_prefit_scores",
        "status": (
            "frozen_score_gate_passed_before_validation_return_read"
            if gate_passed
            else "frozen_score_gate_failed_validation_returns_remain_unread"
        ),
        "created_at": campaign.campaign286.utc_now(),
        "fold": int(fold["fold"]),
        "training": list(fold["train"]),
        "validation": list(fold["validation"]),
        "fit": fit,
        "validation_design": design_stats,
        "validation_score_snapshot": snapshot,
        "score_gate": {
            "passed": gate_passed,
            "scheduled_validation_signals": len(schedule),
            "good_nonconstant_score_sessions": good_sessions,
            "minimum_finite_scores_per_scheduled_signal": minimum_finite,
            "minimum_unique_scores_per_scheduled_signal": minimum_unique,
        },
        "recovery": {
            "change": "DatetimeIndex.eq replaced by elementwise == only",
            "failure_evidence_sha256": FAILURE_EVIDENCE_SHA256,
            "model_refit": False if int(fold["fold"]) == 1 else None,
        },
        "validation_daily_price_fields_read_before_record": [],
        "validation_forward_return_fields_read_before_record": False,
        "lockbox_2024_2025_return_fields_read": False,
        "candidate49_ledgers_changed": False,
    }
    path = OUTPUT_ROOT / f"fold_{fold['fold']}_prefit_scores.json"
    engine.atomic_write_json(path, payload)
    payload["record_binding"] = {
        "path": str(path),
        "sha256": campaign.file_sha256(path),
    }
    return {campaign.TRIAL_ID: score}, identities, payload


def write_validation_metrics(
    fold: dict[str, Any], prefit: dict[str, Any], validation: dict[str, Any]
) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign287_fold_validation_metrics",
        "status": "completed_after_bound_prefit_scores",
        "created_at": campaign.campaign286.utc_now(),
        "fold": fold["fold"],
        "prefit_score_record": prefit["record_binding"],
        "validation_metrics": {campaign.TRIAL_ID: validation},
        "lockbox_2024_2025_return_fields_read": False,
        "candidate49_ledgers_changed": False,
    }
    path = OUTPUT_ROOT / f"fold_{fold['fold']}_validation_metrics.json"
    engine.atomic_write_json(path, payload)
    return {"path": str(path), "sha256": campaign.file_sha256(path)}


def infrastructure_entry() -> dict[str, Any]:
    failure = campaign.load_json(FAILURE_EVIDENCE_PATH)
    return {
        "attempt_id": failure["attempt_id"],
        "phase": "infrastructure_failure",
        "stage": failure["stage"],
        "outcome": failure["status"],
        "evidence": {
            "path": str(FAILURE_EVIDENCE_PATH.relative_to(REPO_ROOT)),
            "sha256": FAILURE_EVIDENCE_SHA256,
        },
        "scientific_result_changed": False,
        "fold1_training_return_fields_read": True,
        "validation_return_fields_read_before_failure": False,
        "lockbox_2024_2025_return_fields_read": False,
    }


def build_ledger(trial: dict[str, Any]) -> dict[str, Any]:
    entries = []
    previous = campaign.CHAIN_GENESIS
    for record in [*campaign.prevalue_entries(), infrastructure_entry(), trial]:
        entry = {**record, "previous_entry_sha256": previous}
        entry["entry_sha256"] = engine.value_sha256(entry)
        previous = entry["entry_sha256"]
        entries.append(entry)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign287_trial_ledger",
        "append_only": True,
        "campaign": {
            "protocol_sha256": campaign.PROTOCOL_SHA256,
            "design_dataset_sha256": campaign.campaign286.DESIGN_DATASET_SHA256,
            "design_evidence_sha256": ARTIFACT_SHA256["design_evidence.json"],
        },
        "chain_genesis": campaign.CHAIN_GENESIS,
        "entries": entries,
        "entry_count": len(entries),
        "prevalue_concept_attempt_count": 7,
        "infrastructure_failure_attempt_count": 1,
        "model_trial_attempt_count": 1,
        "validation_return_fold_count": len(trial.get("validation_metrics") or []),
        "chain_tip_sha256": previous,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }


def plan() -> dict[str, Any]:
    validate_freeze()
    forbidden = (
        "recovery_intent.json",
        "fold_1_prefit_scores.json",
        "fold_1_validation_scores.parquet",
        "fold_1_validation_metrics.json",
        "fold_2_prefit_scores.json",
        "fold_2_validation_scores.parquet",
        "fold_2_validation_metrics.json",
        "fold_3_prefit_scores.json",
        "fold_3_validation_scores.parquet",
        "fold_3_validation_metrics.json",
        "trial_ledger.json",
        "development_survivors.json",
        "development_report.json",
        "recovery_failure.json",
    )
    ready = all(not (OUTPUT_ROOT / name).exists() for name in forbidden)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign287_recovery_plan",
        "status": (
            "ready_to_reuse_fold1_model_and_resume_before_validation_returns"
            if ready
            else "not_ready_preserve_existing_recovery_output"
        ),
        "ready": ready,
        "fold1_model_refit": False,
        "fold1_training_return_reread": False,
        "validation_return_values_read_by_plan": False,
        "lockbox_2024_2025_return_fields_read_by_plan": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }


def run(confirm: bool, batch_size: int) -> dict[str, Any]:
    if not confirm:
        raise Campaign287RecoveryError("recover requires --confirm-recovery")
    payload = plan()
    if payload["ready"] is not True:
        raise Campaign287RecoveryError("Campaign287 recovery plan is not ready")
    _, manifest = campaign.validate_common()
    evidence = campaign.load_json(campaign.DESIGN_EVIDENCE_PATH)
    intent = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign287_recovery_intent",
        "status": "reuse_fold1_model_pending_repaired_prefit_and_chronological_completion",
        "created_at": campaign.campaign286.utc_now(),
        "failure_evidence_sha256": FAILURE_EVIDENCE_SHA256,
        "fold1_model_sha256": ARTIFACT_SHA256[
            f"fold_1_model/{campaign.TRIAL_ID}.npz"
        ],
        "fold1_training_return_reread": False,
        "fold1_model_refit": False,
        "lockbox_2024_2025_return_fields_read": False,
        "candidate49_ledgers_changed": False,
    }
    engine.atomic_write_json(OUTPUT_ROOT / "recovery_intent.json", intent)
    trial: dict[str, Any] = {
        "attempt_id": campaign.TRIAL_ID,
        "trial_id": campaign.TRIAL_ID,
        "parent_trial_id": None,
        "campaign_id": "campaign_287",
        "created_at": intent["created_at"],
        "phase": "development_walkforward",
        "economic_hypothesis": "Smooth distributed nonlinear interactions across the complete raw Alpha158 library may generalize differently from Campaign286's boosted decision trees.",
        "formula": "fixed weighted one-hidden-layer ReLU MLP over all 158 training-fold median/IQR standardized Alpha158 features",
        "direction": "higher predicted within-session gross-return percentile",
        "feature_set": "complete Alpha158 in frozen order",
        "window_transform_threshold_filter_and_weight_configuration": {
            "sample_size_per_session": campaign.SAMPLE_SIZE_PER_SESSION,
            "preprocessing": "training-sample median/IQR, missing zero after scaling, clip [-8,8]",
            "model_parameters": campaign.MODEL_PARAMETERS,
        },
        "training_and_validation_folds": [
            {"fold": f["fold"], "train": list(f["train"]), "validation": list(f["validation"])}
            for f in campaign.FOLDS
        ],
        "data_and_code_fingerprints": {
            "protocol_sha256": campaign.PROTOCOL_SHA256,
            "design_dataset_sha256": campaign.campaign286.DESIGN_DATASET_SHA256,
            "design_evidence_sha256": ARTIFACT_SHA256["design_evidence.json"],
            "frozen_runner_sha256": "672ffcc772f22e43ecc068ebc28c6d86c2f0700157a2753110bb14e209f2e59d",
            "recovery_runner_sha256": campaign.file_sha256(Path(__file__).resolve()),
        },
        "fixed_execution_policy_fingerprints": {
            "prospective_execution_policy_sha256": "72c3c3871e153372ed9e7691c9d89ba1aeb2f6d02cc839761fefa5fee085e1bc",
            "pilot_execution_policy_sha256": "72235cd29fc14d43538238150bb2823dae1dd05b027b2c86a9872de89cc0d3f9",
        },
        "folds": [],
        "training_metrics": [],
        "validation_metrics": [],
        "locked_backtest_metrics_when_opened": None,
        "recovery_limitation": "Fold1 training metrics were not persisted before the API failure and its training returns were not reread solely to reconstruct them.",
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    try:
        for fold in campaign.FOLDS:
            if int(fold["fold"]) == 1:
                print("fold 1: reusing frozen model without training return reread", flush=True)
                model = load_fold1_model()
                fit = reconstructed_fold1_fit(manifest, evidence)
                training_metrics: dict[str, Any] = {
                    "status": "not_persisted_before_prefit_api_failure",
                    "historical_training_returns_reread_by_recovery": False,
                }
            else:
                print(f"fold {fold['fold']}: fitting unchanged frozen weighted MLP", flush=True)
                fit, model, training_metrics = campaign.fit_training_fold(
                    fold, manifest, evidence, batch_size
                )
            print(f"fold {fold['fold']}: freezing repaired prefit scores", flush=True)
            scores, identities, prefit = fixed_validation_prefit(
                fold, manifest, evidence, model, fit
            )
            fold_record: dict[str, Any] = {
                "fold": fold["fold"],
                "fit": fit,
                "training_metrics": training_metrics,
                "prefit_score_record": prefit["record_binding"],
                "score_gate": prefit["score_gate"],
            }
            trial["training_metrics"].append(training_metrics)
            if prefit["score_gate"]["passed"] is not True:
                fold_record["validation_metrics"] = None
                trial["folds"].append(fold_record)
                trial["status"] = "development_rejected_prefit_score_gate"
                trial["decision"] = {
                    "passed": False,
                    "operationally_admissible": False,
                    "rejection_reasons": [f"fold_{fold['fold']}_prefit_score_gate_failed"],
                }
                break
            print(f"fold {fold['fold']}: reading contained validation returns", flush=True)
            validation = campaign.campaign286.evaluate_validation(
                campaign.campaign286.model_context(),
                fold,
                scores,
                identities,
                batch_size,
            )[campaign.TRIAL_ID]
            fold_record["validation_metrics_binding"] = write_validation_metrics(
                fold, prefit, validation
            )
            fold_record["validation_metrics"] = validation
            trial["folds"].append(fold_record)
            trial["validation_metrics"].append(validation)
            del fit, model, training_metrics, scores, identities, validation
            gc.collect()
        if "decision" not in trial:
            trial["decision"] = campaign.campaign286.survivor_decision(trial)
            trial["status"] = (
                "development_survivor_gate_passed"
                if trial["decision"]["passed"]
                else "development_rejected"
            )
        survivors = [campaign.TRIAL_ID] if trial["decision"]["passed"] else []
        ledger = build_ledger(trial)
        ledger_path = OUTPUT_ROOT / "trial_ledger.json"
        engine.atomic_write_json(ledger_path, ledger)
        survivor_payload = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign287_development_survivors",
            "status": "frozen_before_2024_2025_return_read",
            "created_at": campaign.campaign286.utc_now(),
            "ledger": {"path": str(ledger_path), "sha256": campaign.file_sha256(ledger_path)},
            "trial_decisions": {campaign.TRIAL_ID: trial["decision"]},
            "selected_lockbox_survivor_trial_ids": survivors,
            "selected_survivor_count": len(survivors),
            "maximum_survivors": 1,
            "lockbox_return_fields_read": False,
            "candidate49_ledgers_changed": False,
        }
        survivor_path = OUTPUT_ROOT / "development_survivors.json"
        engine.atomic_write_json(survivor_path, survivor_payload)
        report = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign287_development_report",
            "status": "development_complete_survivors_frozen",
            "created_at": campaign.campaign286.utc_now(),
            "protocol_sha256": campaign.PROTOCOL_SHA256,
            "design_evidence_sha256": ARTIFACT_SHA256["design_evidence.json"],
            "trial_count": 1,
            "ledger_entry_count": ledger["entry_count"],
            "validation_return_reading_trial_count": 1 if trial["validation_metrics"] else 0,
            "model_fold_validation_return_reads": len(trial["validation_metrics"]),
            "survivor_count": len(survivors),
            "selected_survivor_trial_ids": survivors,
            "ledger": {"path": str(ledger_path), "sha256": campaign.file_sha256(ledger_path)},
            "survivors": {
                "path": str(survivor_path),
                "sha256": campaign.file_sha256(survivor_path),
            },
            "recovery": {
                "failure_evidence_sha256": FAILURE_EVIDENCE_SHA256,
                "fold1_model_refit": False,
                "fold1_training_return_reread": False,
                "fold1_training_metrics_persisted": False,
            },
            "lockbox_2024_2025_opened": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "investment_advice": False,
        }
        report_path = OUTPUT_ROOT / "development_report.json"
        engine.atomic_write_json(report_path, report)
        return {
            "status": report["status"],
            "survivor_count": len(survivors),
            "selected_survivor_trial_ids": survivors,
            "model_fold_validation_return_reads": len(trial["validation_metrics"]),
            "fold1_training_return_reread": False,
            "report_path": str(report_path),
            "report_sha256": campaign.file_sha256(report_path),
        }
    except BaseException as error:
        engine.atomic_write_json(
            OUTPUT_ROOT / "recovery_failure.json",
            {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign287_recovery_failure",
                "status": "failed_preserved_requires_new_explicit_recovery_revision",
                "created_at": campaign.campaign286.utc_now(),
                "error_type": type(error).__name__,
                "error": str(error),
                "training_or_validation_returns_may_have_been_read": True,
                "fold1_training_return_reread": False,
                "lockbox_2024_2025_return_fields_read": False,
                "provider_request_issued": False,
                "candidate49_ledgers_changed": False,
            },
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "recover"))
    parser.add_argument("--confirm-recovery", action="store_true")
    parser.add_argument("--batch-size", type=int, default=512)
    args = parser.parse_args()
    payload = plan() if args.command == "plan" else run(args.confirm_recovery, args.batch_size)
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
