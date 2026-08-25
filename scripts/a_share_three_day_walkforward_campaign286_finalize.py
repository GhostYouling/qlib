#!/usr/bin/env python3
"""Finalize Campaign286 from frozen persisted metrics without rereading returns."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

import lightgbm as lgb
import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign as engine
from scripts import a_share_three_day_walkforward_campaign286 as campaign


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = campaign.OUTPUT_ROOT
FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_finalizer_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign286_finalize.py"
)
FAILURE_EVIDENCE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_none_metric_finalization_failure_20260825.json"
)
FAILURE_EVIDENCE_SHA256 = (
    "0b771ee16dbbdbf06c316e58de5a6a9c5297c87b0d263b03f00ba00885742aac"
)
DEVELOPMENT_FREEZE_SHA256 = (
    "c33babdf096b8e09668f37bda1a766d5e25abde7af06f5aabd608663f52e55fd"
)
ARTIFACT_SHA256 = {
    "development_intent.json": "2cc789f1dd509ce09e544daf2245a384c0780751575125d415b980c84ab59ba3",
    "development_failure.json": "a55abf3dd56f70b446171b657638deaeacb6f57e65334733adae16c53fae8295",
    "fold_1_prefit_scores.json": "2cb136713b479ca9159279cce44380921b729443a204c2daa4b4cb048e5b2f1b",
    "fold_2_prefit_scores.json": "5f35ba8bbe169080ac9fd9c39789606fa832978d307bdd70c184dda5ec40caf5",
    "fold_3_prefit_scores.json": "c9b561ec53d3e1d4614088400067eada270292410fceba2a58ba01d4ec77b43d",
    "fold_1_validation_metrics.json": "23460bcff0f61551f11bcead26aebf8011a4f75bb05714f7fb7a54adbc9ac46c",
    "fold_2_validation_metrics.json": "771e77511a6810cff596f2d859b3d64faf4b8435d6181292da6abb30b3a87d57",
    "fold_3_validation_metrics.json": "925561c2031172920d8df3c88a406c30668eff78a91ff4d01177fbec9dca7360",
    "fold_1_validation_scores.parquet": "6feda952e45e344b85590ecf7825ad08bf304a54518e663329ed8921bc395699",
    "fold_2_validation_scores.parquet": "c8c475f97ff8adfdeff7dd2f1474b80e341d72389031d06f5fd49b5b861fa328",
    "fold_3_validation_scores.parquet": "88869d82367464c7571abf4958c30d9c4f30227ec04e980f2d737fb585ebd670",
    "fold_1_models/wf286_lgb_deep_158f.txt": "d0aa65c15add00e08b667984011510d9508b68ab295de35da85721e8591ac37a",
    "fold_1_models/wf286_lgb_medium_158f.txt": "1ef3b213ab0d75d38642698bae125b7582f768faf4105a55ab38573668ba4b81",
    "fold_1_models/wf286_lgb_shallow_158f.txt": "4def771ccf7fbb11aced8882b8a3c80a7427d82d3d0e9aa93e1626e28398b8e7",
    "fold_2_models/wf286_lgb_deep_158f.txt": "b9978e584b357d5acc41130700c6f219e0f7897bf66e3ebdba8fd7d0fc2b8e5e",
    "fold_2_models/wf286_lgb_medium_158f.txt": "327724a29a8d77deb47af1f072380325c2aa698f4eee237d708399293573e3ec",
    "fold_2_models/wf286_lgb_shallow_158f.txt": "858e17cd0e7ba9638b1d6859704ab29fa6f019ba77094fe020f05203901a3da2",
    "fold_3_models/wf286_lgb_deep_158f.txt": "be0695b1710a5ad0aea836e3b93a3cc024d14509afa847720116cee9fef68136",
    "fold_3_models/wf286_lgb_medium_158f.txt": "df10a0722b89f9b53acdb00abf6e7532dcb8c1178218d20fe1d0d50c36f20c35",
    "fold_3_models/wf286_lgb_shallow_158f.txt": "507c42d2986d75c24623d43d0d55d001e63ac0d24a78ed13f1ef5af716711054",
}


class Campaign286FinalizeError(RuntimeError):
    """Fail closed when persisted Campaign286 evidence changes."""


def require_file(path: Path, expected: str, label: str) -> None:
    try:
        campaign.require_file(path, expected, label)
    except campaign.Campaign286Error as error:
        raise Campaign286FinalizeError(str(error)) from error


def validate_artifacts() -> None:
    require_file(
        campaign.IMPLEMENTATION_FREEZE_PATH,
        DEVELOPMENT_FREEZE_SHA256,
        "development implementation freeze",
    )
    require_file(
        FAILURE_EVIDENCE_PATH, FAILURE_EVIDENCE_SHA256, "finalization failure evidence"
    )
    require_file(
        campaign.SOURCE_SIGNAL_LEDGER_PATH,
        campaign.SIGNAL_LEDGER_SHA256,
        "Candidate49 signal ledger",
    )
    require_file(
        campaign.SOURCE_EXECUTION_LEDGER_PATH,
        campaign.EXECUTION_LEDGER_SHA256,
        "Candidate49 execution ledger",
    )
    for relative, expected in ARTIFACT_SHA256.items():
        require_file(OUTPUT_ROOT / relative, expected, f"persisted artifact {relative}")


def validate_freeze() -> dict[str, Any]:
    if not FREEZE_PATH.is_file():
        raise Campaign286FinalizeError("Campaign286 finalizer freeze absent")
    record = campaign.load_json(FREEZE_PATH)
    runner = record.get("finalizer") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign286_finalizer_implementation_freeze"
        and record.get("status")
        == "frozen_after_nine_validation_reads_before_read_only_finalization"
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == campaign.file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == campaign.file_sha256(TEST_PATH)
        and boundary.get("historical_return_reread_by_finalizer") is False
        and boundary.get("model_refit_by_finalizer") is False
        and boundary.get("threshold_or_model_change") is False
        and boundary.get("lockbox_2024_2025_return_read") is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign286FinalizeError("Campaign286 finalizer freeze changed")
    validate_artifacts()
    return record


def score_diagnostics() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for fold in range(1, 4):
        frame = pd.read_parquet(OUTPUT_ROOT / f"fold_{fold}_validation_scores.parquet")
        fold_result: dict[str, Any] = {}
        for trial_id in campaign.TRIAL_ORDER:
            values = pd.to_numeric(frame[trial_id], errors="coerce").dropna()
            model_path = OUTPUT_ROOT / f"fold_{fold}_models" / f"{trial_id}.txt"
            model = lgb.Booster(model_file=str(model_path))
            fold_result[trial_id] = {
                "finite_score_count": len(values),
                "unique_score_count": int(values.nunique()),
                "score_standard_deviation": float(values.std()),
                "model_tree_count": int(model.num_trees()),
                "nonzero_feature_count": int((model.feature_importance() > 0).sum()),
                "split_gain_sum": float(
                    model.feature_importance(importance_type="gain").sum()
                ),
            }
        result[str(fold)] = fold_result
    deep = [result[str(fold)]["wf286_lgb_deep_158f"] for fold in range(1, 4)]
    if not all(
        item["unique_score_count"] == 1
        and item["model_tree_count"] == 1
        and item["nonzero_feature_count"] == 0
        and item["split_gain_sum"] == 0.0
        for item in deep
    ):
        raise Campaign286FinalizeError("deep constant-model diagnostic changed")
    return result


def compound(values: Iterable[float]) -> float:
    result = 1.0
    for value in values:
        result *= 1.0 + float(value)
    return float(result - 1.0)


def safe_survivor_decision(record: dict[str, Any]) -> dict[str, Any]:
    validations = list(record.get("validation_metrics") or [])
    if len(validations) == 3 and all(
        (item.get("association") or {}).get("mean_rank_ic") is not None
        and (item.get("association") or {}).get("mean_top3_minus_bottom3_gross_return")
        is not None
        for item in validations
    ):
        return campaign.survivor_decision(record)
    reasons: list[str] = []
    if len(validations) != 3:
        reasons.append("incomplete_validation_fold_count")
    for index, result in enumerate(validations, start=1):
        association = result.get("association") or {}
        normalized = result.get("normalized_execution") or {}
        pilot = result.get("pilot_execution_primary_10bp") or {}
        if int(association.get("cohorts") or 0) < 60:
            reasons.append(f"fold_{index}_insufficient_association_cohorts")
        if association.get("mean_rank_ic") is None:
            reasons.append(f"fold_{index}_undefined_mean_rank_ic")
        if association.get("mean_top3_minus_bottom3_gross_return") is None:
            reasons.append(f"fold_{index}_undefined_spread")
        if int(normalized.get("terminal_unresolved_position_count") or 0) != 0:
            reasons.append(f"fold_{index}_normalized_unresolved_positions")
        if int(pilot.get("terminal_unresolved_position_count") or 0) != 0:
            reasons.append(f"fold_{index}_pilot_unresolved_positions")
        affordability = pilot.get("board_lot_affordability_rate")
        if affordability is None or float(affordability) < 0.9:
            reasons.append(f"fold_{index}_board_lot_affordability")
        participation = pilot.get("maximum_filled_trade_daily_amount_participation")
        if participation is None or float(participation) > 0.01:
            reasons.append(f"fold_{index}_amount_participation")
    normalized_returns = [
        float(item["normalized_execution"]["net_cumulative_return"])
        for item in validations
    ]
    pilot10 = [
        float(item["pilot_execution_primary_10bp"]["net_cumulative_return"])
        for item in validations
    ]
    pilot20 = [
        float(item["pilot_slippage_sensitivity"]["0.0020"]["net_cumulative_return"])
        for item in validations
    ]
    finite_ics = [
        float(value)
        for value in [
            (item.get("association") or {}).get("mean_rank_ic") for item in validations
        ]
        if value is not None and math.isfinite(float(value))
    ]
    finite_spreads = [
        float(value)
        for value in [
            (item.get("association") or {}).get("mean_top3_minus_bottom3_gross_return")
            for item in validations
        ]
        if value is not None and math.isfinite(float(value))
    ]
    return {
        "passed": False,
        "operationally_admissible": False,
        "validation_quality_and_aggregate_passed": False,
        "rejection_reasons": reasons,
        "positive_mean_rank_ic_fold_count": sum(value > 0 for value in finite_ics),
        "positive_normalized_return_fold_count": sum(
            value > 0 for value in normalized_returns
        ),
        "positive_pilot_10bp_return_fold_count": sum(value > 0 for value in pilot10),
        "median_validation_mean_rank_ic": (
            float(statistics.median(finite_ics)) if finite_ics else None
        ),
        "median_validation_spread": (
            float(statistics.median(finite_spreads)) if finite_spreads else None
        ),
        "median_validation_pilot_10bp_return": float(statistics.median(pilot10)),
        "worst_validation_normalized_drawdown": min(
            float(item["normalized_execution"]["maximum_drawdown"])
            for item in validations
        ),
        "development_aggregate": {
            "normalized_return": compound(normalized_returns),
            "pilot_10bp_return": compound(pilot10),
            "pilot_20bp_return": compound(pilot20),
        },
        "undefined_metrics_are_explicit_gate_failures": True,
    }


def load_evidence() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    protocol, _ = campaign.validate_context()
    diagnostics = score_diagnostics()
    prefits = {
        fold: campaign.load_json(OUTPUT_ROOT / f"fold_{fold}_prefit_scores.json")
        for fold in range(1, 4)
    }
    metrics = {
        fold: campaign.load_json(OUTPUT_ROOT / f"fold_{fold}_validation_metrics.json")
        for fold in range(1, 4)
    }
    trials: list[dict[str, Any]] = []
    for trial in campaign.trial_catalog(protocol):
        trial_id = str(trial["trial_id"])
        folds: list[dict[str, Any]] = []
        validation: list[dict[str, Any]] = []
        for fold in range(1, 4):
            metric = metrics[fold]["validation_metrics"][trial_id]
            validation.append(metric)
            folds.append(
                {
                    "fold": fold,
                    "fit": prefits[fold]["fits"][trial_id],
                    "training_metrics": {
                        "status": "not_persisted_before_finalization_failure",
                        "historical_training_returns_reread_by_finalizer": False,
                    },
                    "prefit_score_record": {
                        "path": str(OUTPUT_ROOT / f"fold_{fold}_prefit_scores.json"),
                        "sha256": ARTIFACT_SHA256[f"fold_{fold}_prefit_scores.json"],
                    },
                    "validation_metrics_binding": {
                        "path": str(
                            OUTPUT_ROOT / f"fold_{fold}_validation_metrics.json"
                        ),
                        "sha256": ARTIFACT_SHA256[
                            f"fold_{fold}_validation_metrics.json"
                        ],
                    },
                    "score_and_model_diagnostic": diagnostics[str(fold)][trial_id],
                    "validation_metrics": metric,
                }
            )
        record = {
            "attempt_id": trial_id,
            "trial_id": trial_id,
            "phase": "development_walkforward",
            "formula": "LightGBM regression over the complete frozen raw Alpha158 feature family",
            "direction": "higher predicted within-session gross-return percentile",
            "trial_configuration": trial,
            "shared_parameters": campaign.SHARED_MODEL_PARAMETERS,
            "source_feature_count": campaign.FEATURE_COUNT,
            "source_feature_library_sha256": campaign.design.FEATURE_LIBRARY_SHA256,
            "folds": folds,
            "validation_metrics": validation,
            "validation_return_fold_count": len(validation),
            "training_metric_persistence_limitation": (
                "Training evaluation metrics remained in memory and were not persisted "
                "before the finalization exception; models, fit statistics, validation "
                "scores, and all validation metrics are preserved. Returns were not reread."
            ),
            "candidate49_historical_return_read": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        }
        record["decision"] = safe_survivor_decision(record)
        record["status"] = "development_rejected"
        trials.append(record)
    return protocol, trials, diagnostics


def build_ledger(trials: list[dict[str, Any]]) -> dict[str, Any]:
    failure = campaign.load_json(FAILURE_EVIDENCE_PATH)
    finalization_failure_entry = {
        "attempt_id": failure["attempt_id"],
        "phase": "infrastructure_failure",
        "stage": failure["stage"],
        "outcome": failure["status"],
        "evidence": {
            "path": str(FAILURE_EVIDENCE_PATH.relative_to(REPO_ROOT)),
            "sha256": FAILURE_EVIDENCE_SHA256,
        },
        "scientific_result_changed": False,
        "historical_forward_return_fields_read": True,
        "total_model_fold_validation_return_reads_before_failure": 9,
        "lockbox_2024_2025_return_fields_read": False,
    }
    previous = campaign.CHAIN_GENESIS
    entries: list[dict[str, Any]] = []
    for record in [
        *campaign.prevalue_entries(),
        finalization_failure_entry,
        *trials,
    ]:
        entry = {**record, "previous_entry_sha256": previous}
        entry["entry_sha256"] = engine.value_sha256(entry)
        previous = entry["entry_sha256"]
        entries.append(entry)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_trial_ledger",
        "append_only": True,
        "campaign": {
            "protocol_sha256": campaign.PROTOCOL_SHA256,
            "design_dataset_sha256": campaign.DESIGN_DATASET_SHA256,
        },
        "chain_genesis": campaign.CHAIN_GENESIS,
        "entries": entries,
        "entry_count": len(entries),
        "prevalue_concept_attempt_count": 6,
        "infrastructure_failure_attempt_count": 7,
        "model_trial_attempt_count": len(trials),
        "chain_tip_sha256": previous,
        "training_return_fold_count": 3,
        "validation_return_fold_count": 3,
        "total_model_fold_validation_return_reads": 9,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }


def plan() -> dict[str, Any]:
    validate_freeze()
    _, trials, diagnostics = load_evidence()
    outputs_absent = all(
        not (OUTPUT_ROOT / name).exists()
        for name in (
            "trial_ledger.json",
            "development_survivors.json",
            "development_report.json",
        )
    )
    ready = bool(
        outputs_absent
        and len(trials) == 3
        and all(len(record["validation_metrics"]) == 3 for record in trials)
        and all(not record["decision"]["passed"] for record in trials)
        and all(
            diagnostics[str(fold)]["wf286_lgb_deep_158f"]["unique_score_count"] == 1
            for fold in range(1, 4)
        )
    )
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_finalization_plan",
        "status": (
            "ready_to_finalize_without_return_reread_and_keep_lockbox_closed"
            if ready
            else "not_ready_preserve_existing_state"
        ),
        "ready": ready,
        "trial_count": len(trials),
        "validation_return_fold_count_by_trial": {
            record["trial_id"]: len(record["validation_metrics"]) for record in trials
        },
        "development_survivor_count": sum(
            record["decision"]["passed"] for record in trials
        ),
        "historical_return_values_reread_by_plan": False,
        "model_refit_by_plan": False,
        "lockbox_2024_2025_return_fields_read_by_plan": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }


def finalize() -> dict[str, Any]:
    payload = plan()
    if payload["ready"] is not True:
        raise Campaign286FinalizeError("Campaign286 finalization plan is not ready")
    _, trials, diagnostics = load_evidence()
    ledger = build_ledger(trials)
    ledger_path = OUTPUT_ROOT / "trial_ledger.json"
    engine.atomic_write_json(ledger_path, ledger)
    survivor_payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_development_survivors",
        "status": "frozen_no_survivor_lockbox_remains_closed",
        "created_at": campaign.utc_now(),
        "ledger": {
            "path": str(ledger_path),
            "sha256": campaign.file_sha256(ledger_path),
        },
        "trial_decisions": {
            record["trial_id"]: record["decision"] for record in trials
        },
        "selected_lockbox_survivor_trial_ids": [],
        "selected_survivor_count": 0,
        "maximum_survivors": 1,
        "lockbox_return_fields_read": False,
        "candidate49_ledgers_changed": False,
    }
    survivor_path = OUTPUT_ROOT / "development_survivors.json"
    engine.atomic_write_json(survivor_path, survivor_payload)
    report = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_development_report",
        "status": "development_complete_no_survivor_lockbox_closed",
        "created_at": campaign.utc_now(),
        "protocol_sha256": campaign.PROTOCOL_SHA256,
        "design_manifest_sha256": campaign.DESIGN_MANIFEST_SHA256,
        "design_dataset_sha256": campaign.DESIGN_DATASET_SHA256,
        "frozen_development_failure": {
            "path": str(OUTPUT_ROOT / "development_failure.json"),
            "sha256": ARTIFACT_SHA256["development_failure.json"],
        },
        "finalization_failure_evidence": {
            "path": str(FAILURE_EVIDENCE_PATH),
            "sha256": FAILURE_EVIDENCE_SHA256,
        },
        "trial_count": len(trials),
        "ledger_entry_count": ledger["entry_count"],
        "validation_return_reading_trial_count": 3,
        "total_model_fold_validation_return_reads": 9,
        "survivor_count": 0,
        "selected_survivor_trial_ids": [],
        "score_and_model_diagnostics": diagnostics,
        "ledger": {
            "path": str(ledger_path),
            "sha256": campaign.file_sha256(ledger_path),
        },
        "survivors": {
            "path": str(survivor_path),
            "sha256": campaign.file_sha256(survivor_path),
        },
        "training_metrics_persisted": False,
        "training_metrics_limitation": (
            "The original runner did not persist training evaluation metrics before the "
            "finalization exception. No historical returns were reread to reconstruct them."
        ),
        "historical_returns_reread_by_finalizer": False,
        "model_refit_by_finalizer": False,
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
        "trial_count": report["trial_count"],
        "survivor_count": 0,
        "selected_survivor_trial_ids": [],
        "lockbox_2024_2025_opened": False,
        "report_path": str(report_path),
        "report_sha256": campaign.file_sha256(report_path),
        "historical_returns_reread_by_finalizer": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "finalize"))
    parser.add_argument("--confirm-finalize", action="store_true")
    args = parser.parse_args()
    if args.command == "plan":
        payload = plan()
    else:
        if not args.confirm_finalize:
            raise Campaign286FinalizeError("finalize requires --confirm-finalize")
        payload = finalize()
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
