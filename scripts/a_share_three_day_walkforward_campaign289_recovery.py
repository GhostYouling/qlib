#!/usr/bin/env python3
"""Recover Campaign289 by applying the frozen binary map before market filtering."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign289 as campaign


REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_OUTPUT_ROOT = campaign.OUTPUT_ROOT
RECOVERY_OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_289/binary_hash_cell_mean_recovery_v1"
)
FAILURE_RECORD_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_289_training_binary_peer_failure_20260825.json"
)
FAILURE_RECORD_SHA256 = (
    "b215bb6d90b42964a4ed161ef34232b47a5a7f26e1d2999c93fdc1cb63a9da66"
)
ORIGINAL_INTENT_PATH = ORIGINAL_OUTPUT_ROOT / "development_intent.json"
ORIGINAL_INTENT_SHA256 = (
    "9914945bbbbb8e5892bc124a1ea85a4cbd1b918b7ac1318732e047af64163fd2"
)
ORIGINAL_FAILURE_PATH = ORIGINAL_OUTPUT_ROOT / "development_failure.json"
ORIGINAL_FAILURE_SHA256 = (
    "33fc6bfe06937227dcaf82fe272c56722efe8127428435de5d8910ee89b1375a"
)
RECOVERY_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_289_binary_peer_recovery_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign289_recovery.py"
)


class Campaign289RecoveryError(RuntimeError):
    """Fail closed when the bounded Campaign289 recovery changes."""


def validate_failure_bindings() -> None:
    bindings = (
        (FAILURE_RECORD_PATH, FAILURE_RECORD_SHA256, "Campaign289 failure record"),
        (ORIGINAL_INTENT_PATH, ORIGINAL_INTENT_SHA256, "Campaign289 original intent"),
        (
            ORIGINAL_FAILURE_PATH,
            ORIGINAL_FAILURE_SHA256,
            "Campaign289 original failure",
        ),
    )
    for path, expected, label in bindings:
        campaign.require_file(path, expected, label)
    existing = sorted(path.name for path in ORIGINAL_OUTPUT_ROOT.iterdir())
    if existing != [
        "design_evidence.json",
        "development_failure.json",
        "development_intent.json",
    ]:
        raise Campaign289RecoveryError("original failed output root changed")
    failure = campaign.load_json(ORIGINAL_FAILURE_PATH)
    if not (
        failure.get("error")
        == "training binary state or hash cells differ from zero-return design"
        and failure.get("lockbox_2024_2025_return_fields_read") is False
        and failure.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign289RecoveryError("original failure semantics changed")


def validate_recovery_freeze() -> dict[str, Any]:
    if not RECOVERY_FREEZE_PATH.is_file():
        raise Campaign289RecoveryError("Campaign289 recovery freeze missing")
    record = campaign.load_json(RECOVERY_FREEZE_PATH)
    runner = record.get("runner") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign289_binary_peer_recovery_implementation_freeze"
        and record.get("status")
        == "frozen_after_fold1_infrastructure_failure_before_recovery_return_reread"
        and (record.get("protocol") or {}).get("sha256") == campaign.PROTOCOL_SHA256
        and (record.get("failure_record") or {}).get("sha256") == FAILURE_RECORD_SHA256
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == campaign.file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == campaign.file_sha256(TEST_PATH)
        and boundary.get("recovery_training_return_reread_before_freeze") is False
        and boundary.get("validation_return_read_before_freeze") is False
        and boundary.get("lockbox_2024_2025_return_read_before_freeze") is False
        and boundary.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise Campaign289RecoveryError("Campaign289 recovery freeze changed")
    return record


def factor_frame(
    identities: pd.DataFrame, binary_matrix: np.ndarray, eligible: np.ndarray
) -> pd.DataFrame:
    values = np.asarray(binary_matrix, dtype=np.float32)
    support = np.asarray(eligible, dtype=bool)
    if not (
        values.ndim == 2
        and values.shape[1] == campaign.FEATURE_COUNT
        and len(identities) == len(values) == len(support)
        and np.isin(values, [-1.0, 0.0, 1.0]).all()
    ):
        raise Campaign289RecoveryError("precomputed binary factor frame changed")
    columns = [f"alpha158_{index:03d}" for index in range(campaign.FEATURE_COUNT)]
    frame = pd.concat(
        [
            identities[["trade_date", "instrument"]].reset_index(drop=True),
            pd.DataFrame(values, columns=columns),
        ],
        axis=1,
    )
    frame["model_support_eligible"] = support
    return frame


def build_training_panel_with_frozen_peer_set(
    fold: dict[str, Any], manifest: dict[str, Any], batch_size: int
) -> tuple[
    pd.DataFrame,
    Any,
    pd.DatetimeIndex,
    pd.DataFrame,
    np.ndarray,
    np.ndarray,
    dict[str, Any],
    dict[str, Any],
]:
    context = campaign.campaign286.model_context()
    market, calendar = campaign.engine.load_market_context(
        context, fold["train"][1], "2019-01-01", batch_size
    )
    schedule = campaign.engine.global_signal_schedule(calendar)
    period = campaign.engine.purged_period_schedule(
        schedule,
        fold["train"][0],
        fold["train"][1],
        campaign.PURGE_SIGNAL_SESSIONS,
    )
    years = range(2019, pd.Timestamp(fold["train"][1]).year + 1)
    identities, matrix, eligible, design_stats = campaign.campaign286.load_design_years(
        years, manifest, allowed_dates=period["signal_date"]
    )
    binary_stats = campaign.session_binary_transform_inplace(
        matrix, identities["trade_date"], eligible
    )
    factors = factor_frame(identities, matrix, eligible)
    panel = campaign.engine.build_signal_panel(market, factors, schedule)
    columns = [f"alpha158_{index:03d}" for index in range(campaign.FEATURE_COUNT)]
    panel_matrix = panel[columns].to_numpy(dtype=np.float32, copy=True)
    panel_eligible = panel["model_support_eligible"].fillna(False).to_numpy(dtype=bool)
    return (
        panel,
        campaign.engine.quote_lookup(market),
        calendar,
        schedule,
        panel_matrix,
        panel_eligible,
        design_stats,
        binary_stats,
    )


def fit_training_fold_recovery(
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
    ) = build_training_panel_with_frozen_peer_set(fold, manifest, batch_size)
    if binary_stats != bundle["record"]["session_binary_transform"]:
        raise Campaign289RecoveryError("recovered binary peer-set evidence changed")
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
        raise Campaign289RecoveryError("recovered sampled panel coverage changed")
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
            "fold1_training_return_reread_due_infrastructure_recovery": int(
                fold["fold"]
            )
            == 1,
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


def plan_recovery() -> dict[str, Any]:
    campaign.validate_common()
    campaign.validate_development_freeze()
    validate_failure_bindings()
    validate_recovery_freeze()
    existing = (
        sorted(path.name for path in RECOVERY_OUTPUT_ROOT.iterdir())
        if RECOVERY_OUTPUT_ROOT.exists()
        else []
    )
    ready = not existing
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign289_recovery_plan",
        "status": (
            "ready_for_bounded_recovery"
            if ready
            else "not_ready_preserve_existing_recovery_output"
        ),
        "ready": ready,
        "existing_outputs": existing,
        "fold1_training_return_reread_by_plan": False,
        "validation_return_read_by_plan": False,
        "lockbox_2024_2025_return_read_by_plan": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }


def run_recovery(confirm: bool, batch_size: int) -> dict[str, Any]:
    if not confirm:
        raise Campaign289RecoveryError("run-recovery requires --confirm-run")
    payload = plan_recovery()
    if payload["ready"] is not True:
        raise Campaign289RecoveryError("Campaign289 recovery plan is not ready")
    RECOVERY_OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    recovery_intent = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign289_binary_peer_recovery_intent",
        "status": "bounded_recovery_open_pending_chronological_completion",
        "opened_at": campaign.campaign286.utc_now(),
        "protocol_sha256": campaign.PROTOCOL_SHA256,
        "design_evidence_sha256": campaign.file_sha256(campaign.DESIGN_EVIDENCE_PATH),
        "failure_record_sha256": FAILURE_RECORD_SHA256,
        "recovery_runner_sha256": campaign.file_sha256(Path(__file__).resolve()),
        "frozen_design_sample_binary_hash_model_cost_and_gates_unchanged": True,
        "fold1_training_return_reread_disclosed": True,
        "validation_scores_frozen_before_each_validation_return_read": True,
        "lockbox_2024_2025_remains_closed": True,
        "candidate49_ledgers_changed": False,
    }
    campaign.engine.atomic_write_json(
        RECOVERY_OUTPUT_ROOT / "recovery_intent.json", recovery_intent
    )

    def forced_plan() -> dict[str, Any]:
        return {
            "ready": True,
            "status": "ready_for_bounded_recovery_after_preserved_failure",
        }

    original_file = campaign.__file__
    original_output = campaign.OUTPUT_ROOT
    original_fit = campaign.fit_training_fold
    original_plan = campaign.plan_development
    try:
        campaign.__file__ = __file__
        campaign.OUTPUT_ROOT = RECOVERY_OUTPUT_ROOT
        campaign.fit_training_fold = fit_training_fold_recovery
        campaign.plan_development = forced_plan
        result = campaign.run_development(True, batch_size)
    finally:
        campaign.__file__ = original_file
        campaign.OUTPUT_ROOT = original_output
        campaign.fit_training_fold = original_fit
        campaign.plan_development = original_plan
    result["recovery_output_root"] = str(RECOVERY_OUTPUT_ROOT)
    result["original_failed_output_preserved"] = True
    result["fold1_training_return_reread_due_infrastructure_recovery"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("plan-recovery")
    run = subcommands.add_parser("run-recovery")
    run.add_argument("--confirm-run", action="store_true")
    run.add_argument("--batch-size", type=int, default=512)
    args = parser.parse_args()
    if args.command == "plan-recovery":
        payload = plan_recovery()
    elif args.command == "run-recovery":
        payload = run_recovery(args.confirm_run, args.batch_size)
    else:
        raise Campaign289RecoveryError(f"unsupported command: {args.command}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
