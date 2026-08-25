#!/usr/bin/env python3
"""Recover Campaign289 v1 by neutral-filling only ineligible joined rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign289 as campaign
from scripts import a_share_three_day_walkforward_campaign289_recovery as recovery_v1


REPO_ROOT = Path(__file__).resolve().parents[1]
RECOVERY_V1_OUTPUT_ROOT = recovery_v1.RECOVERY_OUTPUT_ROOT
RECOVERY_V2_OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_289/binary_hash_cell_mean_recovery_v2"
)
FAILURE_V2_RECORD_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_289_recovery_v1_non_support_nan_failure_20260825.json"
)
FAILURE_V2_RECORD_SHA256 = (
    "d20ae5d23784f656faadfa0fe6f760e2435f49f79d72dad159eb41623e021009"
)
V1_RECOVERY_INTENT_PATH = RECOVERY_V1_OUTPUT_ROOT / "recovery_intent.json"
V1_RECOVERY_INTENT_SHA256 = (
    "7b3d50c80ac06ac5f1866b01c3c4ec53ad97b6d321c33c80d2221944e4efa471"
)
V1_DEVELOPMENT_INTENT_PATH = RECOVERY_V1_OUTPUT_ROOT / "development_intent.json"
V1_DEVELOPMENT_INTENT_SHA256 = (
    "d9e5696ad6b3597e1857a885081168db10d4d79ed5c64651ace7094006f5e304"
)
V1_FAILURE_PATH = RECOVERY_V1_OUTPUT_ROOT / "development_failure.json"
V1_FAILURE_SHA256 = "ba39bc93f7b81153c0cd3166ed16dcb89f6db8a093118a01c13311a53b800f1d"
RECOVERY_V2_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_289_non_support_neutral_recovery_v2_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign289_recovery_v2.py"
)


class Campaign289RecoveryV2Error(RuntimeError):
    """Fail closed when the second bounded Campaign289 recovery changes."""


def validate_v1_failure_bindings() -> None:
    recovery_v1.validate_failure_bindings()
    recovery_v1.validate_recovery_freeze()
    bindings = (
        (
            FAILURE_V2_RECORD_PATH,
            FAILURE_V2_RECORD_SHA256,
            "Campaign289 recovery-v1 failure record",
        ),
        (
            V1_RECOVERY_INTENT_PATH,
            V1_RECOVERY_INTENT_SHA256,
            "Campaign289 recovery-v1 intent",
        ),
        (
            V1_DEVELOPMENT_INTENT_PATH,
            V1_DEVELOPMENT_INTENT_SHA256,
            "Campaign289 recovery-v1 development intent",
        ),
        (V1_FAILURE_PATH, V1_FAILURE_SHA256, "Campaign289 recovery-v1 failure"),
    )
    for path, expected, label in bindings:
        campaign.require_file(path, expected, label)
    existing = sorted(path.name for path in RECOVERY_V1_OUTPUT_ROOT.iterdir())
    if existing != [
        "development_failure.json",
        "development_intent.json",
        "recovery_intent.json",
    ]:
        raise Campaign289RecoveryV2Error("recovery-v1 failed output root changed")
    failure = campaign.load_json(V1_FAILURE_PATH)
    if not (
        failure.get("error") == "random hyperplane hash input changed"
        and failure.get("lockbox_2024_2025_return_fields_read") is False
        and failure.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign289RecoveryV2Error("recovery-v1 failure semantics changed")


def validate_recovery_v2_freeze() -> dict[str, Any]:
    if not RECOVERY_V2_FREEZE_PATH.is_file():
        raise Campaign289RecoveryV2Error("Campaign289 recovery-v2 freeze missing")
    record = campaign.load_json(RECOVERY_V2_FREEZE_PATH)
    runner = record.get("runner") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign289_non_support_neutral_recovery_v2_implementation_freeze"
        and record.get("status")
        == "frozen_after_recovery_v1_failure_before_third_fold1_training_return_read"
        and (record.get("protocol") or {}).get("sha256") == campaign.PROTOCOL_SHA256
        and (record.get("failure_record") or {}).get("sha256")
        == FAILURE_V2_RECORD_SHA256
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == campaign.file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == campaign.file_sha256(TEST_PATH)
        and boundary.get("recovery_v2_training_return_reread_before_freeze") is False
        and boundary.get("validation_return_read_before_freeze") is False
        and boundary.get("lockbox_2024_2025_return_read_before_freeze") is False
        and boundary.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise Campaign289RecoveryV2Error("Campaign289 recovery-v2 freeze changed")
    return record


def neutralize_ineligible_rows(
    matrix: np.ndarray, eligible: np.ndarray
) -> dict[str, Any]:
    values = np.asarray(matrix)
    support = np.asarray(eligible, dtype=bool)
    if not (
        values.ndim == 2
        and values.shape[1] == campaign.FEATURE_COUNT
        and len(values) == len(support)
        and np.isfinite(values[support]).all()
        and np.isin(values[support], [-1.0, 0.0, 1.0]).all()
    ):
        raise Campaign289RecoveryV2Error("eligible joined binary states changed")
    nonfinite_before = int((~np.isfinite(values[~support])).sum())
    values[~support] = 0.0
    if not (np.isfinite(values).all() and np.isin(values, [-1.0, 0.0, 1.0]).all()):
        raise Campaign289RecoveryV2Error("ineligible neutral fill failed")
    return {
        "eligible_row_count": int(support.sum()),
        "ineligible_row_count": int((~support).sum()),
        "nonfinite_ineligible_cells_replaced": nonfinite_before,
        "eligible_values_changed": False,
        "ineligible_fill": 0.0,
    }


def fit_training_fold_recovery_v2(
    fold: dict[str, Any],
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    batch_size: int,
) -> tuple[dict[str, Any], campaign.RandomHyperplaneCellMeanRegressor, dict[str, Any]]:
    bundle = campaign.fold_design_bundle(fold, manifest)
    campaign.compare_fold_design(bundle, evidence)
    (
        panel,
        quotes,
        calendar,
        schedule,
        matrix,
        eligible,
        selected_design,
        binary_stats,
    ) = recovery_v1.build_training_panel_with_frozen_peer_set(
        fold, manifest, batch_size
    )
    if binary_stats != bundle["record"]["session_binary_transform"]:
        raise Campaign289RecoveryV2Error("recovered binary peer-set evidence changed")
    neutral_fill = neutralize_ineligible_rows(matrix, eligible)
    panel_keys = campaign.campaign286.design.compact_stock_day_keys(
        panel["signal_date"], panel["instrument"]
    )
    sampled = np.isin(panel_keys, bundle["sample_keys"], assume_unique=False) & eligible
    sample_frame = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(panel["signal_date"]).dt.normalize(),
            "sampled": sampled,
        }
    )
    sample_counts = (
        sample_frame.loc[sample_frame["sampled"]]
        .groupby("signal_date", sort=True)
        .size()
        .to_numpy(dtype=np.int64)
    )
    if (
        len(sample_counts) < campaign.MINIMUM_RETAINED_TRAINING_SESSIONS
        or int(sample_counts.min()) != campaign.SAMPLE_SIZE_PER_SESSION
        or int(sample_counts.max()) != campaign.SAMPLE_SIZE_PER_SESSION
    ):
        raise Campaign289RecoveryV2Error("recovered sampled panel coverage changed")
    returns = pd.to_numeric(panel["forward_gross_return"], errors="coerce").copy()
    returns.loc[~eligible] = np.nan
    target = campaign.campaign286.target_percentiles(panel["signal_date"], returns)
    valid, target_weights, weight_stats = campaign.session_equal_target_weights(
        panel["signal_date"], target, sampled
    )
    hyperplanes, _ = campaign.random_hyperplanes()
    cells = campaign.hash_cells(matrix, hyperplanes)
    model = campaign.RandomHyperplaneCellMeanRegressor(
        dict(campaign.MODEL_PARAMETERS)
    ).fit(cells[valid], target[valid], target_weights[valid])
    model_path = (
        campaign.OUTPUT_ROOT / f"fold_{fold['fold']}_model" / f"{campaign.TRIAL_ID}.npz"
    )
    model.save(model_path)
    score = campaign.model_scores(model, matrix, eligible)
    panel[campaign.engine.factor_score_column(campaign.TRIAL_ID)] = score
    training_metrics = campaign.engine.evaluate_trial_period(
        panel,
        quotes,
        calendar,
        schedule,
        {"feature_set": [campaign.TRIAL_ID], "weights": [1.0]},
        fold["train"][0],
        fold["train"][1],
        campaign.PURGE_SIGNAL_SESSIONS,
        include_sensitivity=False,
    )
    fit = {
        "trial_id": campaign.TRIAL_ID,
        "resolved_parameters": campaign.MODEL_PARAMETERS,
        "training": weight_stats,
        "selected_design": selected_design,
        "zero_return_fold_design_sha256": bundle["record"]["fold_design_sha256"],
        "session_binary_transform": binary_stats,
        "random_hyperplane_representation": bundle["record"][
            "random_hyperplane_representation"
        ],
        "frozen_peer_set_recovery": {
            "binary_map_computed_before_market_quality_filter": True,
            "sampled_panel_session_count": len(sample_counts),
            "minimum_sampled_panel_names_per_session": int(sample_counts.min()),
            "maximum_sampled_panel_names_per_session": int(sample_counts.max()),
            "sampled_panel_counts_sha256": campaign.hash_array(sample_counts, "<i8"),
            "frozen_hash_hyperplanes_and_cells_used_unchanged": True,
            "fold1_training_return_reread_due_infrastructure_recovery_v2": int(
                fold["fold"]
            )
            == 1,
            "non_support_neutral_fill": neutral_fill,
        },
        "fit_statistics": model.fit_statistics_,
        "model_artifact": {
            "path": str(model_path),
            "sha256": campaign.file_sha256(model_path),
            "bytes": model_path.stat().st_size,
        },
        "numpy_version": np.__version__,
        "scipy_version": campaign.scipy.__version__,
    }
    return fit, model, training_metrics


def plan_recovery_v2() -> dict[str, Any]:
    campaign.validate_common()
    campaign.validate_development_freeze()
    validate_v1_failure_bindings()
    validate_recovery_v2_freeze()
    existing = (
        sorted(path.name for path in RECOVERY_V2_OUTPUT_ROOT.iterdir())
        if RECOVERY_V2_OUTPUT_ROOT.exists()
        else []
    )
    ready = not existing
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign289_recovery_v2_plan",
        "status": (
            "ready_for_bounded_recovery_v2"
            if ready
            else "not_ready_preserve_existing_recovery_v2_output"
        ),
        "ready": ready,
        "existing_outputs": existing,
        "third_fold1_training_return_read_by_plan": False,
        "validation_return_read_by_plan": False,
        "lockbox_2024_2025_return_read_by_plan": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }


def run_recovery_v2(confirm: bool, batch_size: int) -> dict[str, Any]:
    if not confirm:
        raise Campaign289RecoveryV2Error("run-recovery-v2 requires --confirm-run")
    payload = plan_recovery_v2()
    if payload["ready"] is not True:
        raise Campaign289RecoveryV2Error("Campaign289 recovery-v2 plan is not ready")
    RECOVERY_V2_OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    recovery_intent = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign289_non_support_neutral_recovery_v2_intent",
        "status": "bounded_recovery_v2_open_pending_chronological_completion",
        "opened_at": campaign.campaign286.utc_now(),
        "protocol_sha256": campaign.PROTOCOL_SHA256,
        "design_evidence_sha256": campaign.file_sha256(campaign.DESIGN_EVIDENCE_PATH),
        "failure_record_sha256": FAILURE_V2_RECORD_SHA256,
        "recovery_runner_sha256": campaign.file_sha256(Path(__file__).resolve()),
        "only_ineligible_rows_neutral_filled": True,
        "frozen_design_sample_binary_hash_model_cost_and_gates_unchanged": True,
        "third_fold1_training_return_read_disclosed": True,
        "validation_scores_frozen_before_each_validation_return_read": True,
        "lockbox_2024_2025_remains_closed": True,
        "candidate49_ledgers_changed": False,
    }
    campaign.engine.atomic_write_json(
        RECOVERY_V2_OUTPUT_ROOT / "recovery_v2_intent.json", recovery_intent
    )

    def forced_plan() -> dict[str, Any]:
        return {
            "ready": True,
            "status": "ready_for_bounded_recovery_v2_after_preserved_failures",
        }

    original_file = campaign.__file__
    original_output = campaign.OUTPUT_ROOT
    original_fit = campaign.fit_training_fold
    original_plan = campaign.plan_development
    try:
        campaign.__file__ = __file__
        campaign.OUTPUT_ROOT = RECOVERY_V2_OUTPUT_ROOT
        campaign.fit_training_fold = fit_training_fold_recovery_v2
        campaign.plan_development = forced_plan
        result = campaign.run_development(True, batch_size)
    finally:
        campaign.__file__ = original_file
        campaign.OUTPUT_ROOT = original_output
        campaign.fit_training_fold = original_fit
        campaign.plan_development = original_plan
    result["recovery_v2_output_root"] = str(RECOVERY_V2_OUTPUT_ROOT)
    result["original_and_recovery_v1_failed_outputs_preserved"] = True
    result["fold1_training_return_read_total_due_recovery"] = 3
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("plan-recovery-v2")
    run = subcommands.add_parser("run-recovery-v2")
    run.add_argument("--confirm-run", action="store_true")
    run.add_argument("--batch-size", type=int, default=512)
    args = parser.parse_args()
    if args.command == "plan-recovery-v2":
        payload = plan_recovery_v2()
    elif args.command == "run-recovery-v2":
        payload = run_recovery_v2(args.confirm_run, args.batch_size)
    else:
        raise Campaign289RecoveryV2Error(f"unsupported command: {args.command}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
