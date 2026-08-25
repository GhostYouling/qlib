#!/usr/bin/env python3
"""Finalize Campaign289 after reconciling both preserved infrastructure failures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign289 as campaign
from scripts import a_share_three_day_walkforward_campaign289_recovery as recovery_v1
from scripts import a_share_three_day_walkforward_campaign289_recovery_v2 as recovery_v2


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = recovery_v2.RECOVERY_V2_OUTPUT_ROOT
SOURCE_LEDGER_PATH = OUTPUT_ROOT / "trial_ledger.json"
SOURCE_LEDGER_SHA256 = (
    "1fa4523341296cb464ca54382d2be66e6f60a6ca742ee1374a5b186649c9e2cd"
)
SOURCE_REPORT_PATH = OUTPUT_ROOT / "development_report.json"
SOURCE_REPORT_SHA256 = (
    "0f9c5b79e65dfe87089b30bda9556ccd52817ab0248c3fcf678fbbeb59c8bf99"
)
SOURCE_SURVIVORS_PATH = OUTPUT_ROOT / "development_survivors.json"
SOURCE_SURVIVORS_SHA256 = (
    "74137ce34b4b8a22763e2f2ae2d7941bc3b07579d152d4dab59d6b0a53094846"
)
RECOVERY_V2_INTENT_PATH = OUTPUT_ROOT / "recovery_v2_intent.json"
RECOVERY_V2_INTENT_SHA256 = (
    "71660a7c89eff6a6fa3007134ab8ec3f1168dfdc97759e3e2f203a3ea46d0f9f"
)
FAILURE_V1_RECORD_PATH = recovery_v1.FAILURE_RECORD_PATH
FAILURE_V1_RECORD_SHA256 = recovery_v1.FAILURE_RECORD_SHA256
FAILURE_V2_RECORD_PATH = recovery_v2.FAILURE_V2_RECORD_PATH
FAILURE_V2_RECORD_SHA256 = recovery_v2.FAILURE_V2_RECORD_SHA256
TERMINAL_LEDGER_PATH = OUTPUT_ROOT / "terminal_trial_ledger.json"
TERMINAL_REPORT_PATH = OUTPUT_ROOT / "terminal_development_report.json"
FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_289_finalizer_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign289_finalize.py"
)


class Campaign289FinalizationError(RuntimeError):
    """Fail closed when Campaign289 terminal evidence changes."""


def validate_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    campaign.validate_common()
    recovery_v2.validate_v1_failure_bindings()
    recovery_v2.validate_recovery_v2_freeze()
    bindings = (
        (SOURCE_LEDGER_PATH, SOURCE_LEDGER_SHA256, "Campaign289 source ledger"),
        (SOURCE_REPORT_PATH, SOURCE_REPORT_SHA256, "Campaign289 source report"),
        (
            SOURCE_SURVIVORS_PATH,
            SOURCE_SURVIVORS_SHA256,
            "Campaign289 source survivors",
        ),
        (
            RECOVERY_V2_INTENT_PATH,
            RECOVERY_V2_INTENT_SHA256,
            "Campaign289 recovery-v2 intent",
        ),
        (
            FAILURE_V1_RECORD_PATH,
            FAILURE_V1_RECORD_SHA256,
            "Campaign289 first failure record",
        ),
        (
            FAILURE_V2_RECORD_PATH,
            FAILURE_V2_RECORD_SHA256,
            "Campaign289 second failure record",
        ),
    )
    for path, expected, label in bindings:
        campaign.require_file(path, expected, label)
    ledger = campaign.load_json(SOURCE_LEDGER_PATH)
    report = campaign.load_json(SOURCE_REPORT_PATH)
    survivors = campaign.load_json(SOURCE_SURVIVORS_PATH)
    entries = ledger.get("entries") or []
    model_entries = [
        entry for entry in entries if entry.get("trial_id") == campaign.TRIAL_ID
    ]
    if not (
        ledger.get("kind") == "a_share_three_day_walkforward_campaign289_trial_ledger"
        and ledger.get("entry_count") == len(entries) == 8
        and ledger.get("prevalue_concept_attempt_count") == 7
        and ledger.get("infrastructure_failure_attempt_count") == 0
        and ledger.get("model_trial_attempt_count") == 1
        and ledger.get("validation_return_fold_count") == 3
        and len(model_entries) == 1
        and model_entries[0].get("status") == "development_rejected"
        and (model_entries[0].get("decision") or {}).get("passed") is False
        and report.get("survivor_count") == 0
        and report.get("lockbox_2024_2025_opened") is False
        and survivors.get("selected_survivor_count") == 0
        and survivors.get("lockbox_return_fields_read") is False
    ):
        raise Campaign289FinalizationError(
            "Campaign289 source terminal semantics changed"
        )
    return ledger, report, model_entries[0]


def validate_freeze() -> dict[str, Any]:
    if not FREEZE_PATH.is_file():
        raise Campaign289FinalizationError("Campaign289 finalizer freeze missing")
    record = campaign.load_json(FREEZE_PATH)
    runner = record.get("runner") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign289_finalizer_implementation_freeze"
        and record.get("status")
        == "frozen_after_development_rejection_before_terminal_ledger_reconciliation"
        and (record.get("protocol") or {}).get("sha256") == campaign.PROTOCOL_SHA256
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == campaign.file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == campaign.file_sha256(TEST_PATH)
        and boundary.get("historical_return_reread_by_finalizer") is False
        and boundary.get("model_refit_by_finalizer") is False
        and boundary.get("lockbox_2024_2025_return_read_by_finalizer") is False
        and boundary.get("candidate49_ledgers_changed_by_finalizer") is False
    ):
        raise Campaign289FinalizationError("Campaign289 finalizer freeze changed")
    return record


def validate_chain(ledger: dict[str, Any]) -> str:
    previous = campaign.CHAIN_GENESIS
    for entry in ledger.get("entries") or []:
        payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
        if not (
            entry.get("previous_entry_sha256") == previous
            and entry.get("entry_sha256") == campaign.engine.value_sha256(payload)
        ):
            raise Campaign289FinalizationError(
                "Campaign289 source ledger chain changed"
            )
        previous = str(entry["entry_sha256"])
    if ledger.get("chain_tip_sha256") != previous:
        raise Campaign289FinalizationError("Campaign289 source ledger tip changed")
    return previous


def reconciliation_entries(previous: str) -> list[dict[str, Any]]:
    first = {
        "attempt_id": "c289_infra_01",
        "phase": "post_run_attempt_reconciliation",
        "name": "training_binary_peer_set_implementation_failure",
        "outcome": "failed_after_fold1_training_return_read_before_model_fit_or_validation_return_read",
        "reason": "The original runner recomputed medians after market filtering instead of preserving the preregistered design peer set. Recovery v1 applied the frozen peer-set map and reread fold-1 training returns once.",
        "occurred_before_model_trial_completion": True,
        "appended_after_model_trial_to_preserve_the_already_written_source_ledger": True,
        "evidence": {
            "path": str(FAILURE_V1_RECORD_PATH.relative_to(REPO_ROOT)),
            "sha256": FAILURE_V1_RECORD_SHA256,
        },
        "recovery_runner": {
            "path": str(Path(recovery_v1.__file__).resolve().relative_to(REPO_ROOT)),
            "sha256": campaign.file_sha256(Path(recovery_v1.__file__).resolve()),
        },
        "fold1_training_return_reread": True,
        "validation_return_read_by_failed_attempt": False,
        "model_fit_by_failed_attempt": False,
        "lockbox_2024_2025_opened": False,
        "candidate49_ledgers_changed": False,
        "previous_entry_sha256": previous,
    }
    first["entry_sha256"] = campaign.engine.value_sha256(first)
    second = {
        "attempt_id": "c289_infra_02",
        "phase": "post_run_attempt_reconciliation",
        "name": "recovery_v1_ineligible_nan_hash_input_failure",
        "outcome": "failed_after_second_fold1_training_return_read_before_model_fit_or_validation_return_read",
        "reason": "Recovery v1 preserved eligible peer states but left NaN placeholders in already-ineligible joined rows. Recovery v2 neutral-filled only those ignored rows and reread fold-1 training returns once more.",
        "occurred_before_model_trial_completion": True,
        "appended_after_model_trial_to_preserve_the_already_written_source_ledger": True,
        "evidence": {
            "path": str(FAILURE_V2_RECORD_PATH.relative_to(REPO_ROOT)),
            "sha256": FAILURE_V2_RECORD_SHA256,
        },
        "recovery_runner": {
            "path": str(Path(recovery_v2.__file__).resolve().relative_to(REPO_ROOT)),
            "sha256": campaign.file_sha256(Path(recovery_v2.__file__).resolve()),
        },
        "fold1_training_return_reread": True,
        "validation_return_read_by_failed_attempt": False,
        "model_fit_by_failed_attempt": False,
        "lockbox_2024_2025_opened": False,
        "candidate49_ledgers_changed": False,
        "previous_entry_sha256": first["entry_sha256"],
    }
    second["entry_sha256"] = campaign.engine.value_sha256(second)
    return [first, second]


def build_terminal_ledger() -> dict[str, Any]:
    ledger, _, _ = validate_inputs()
    additions = reconciliation_entries(validate_chain(ledger))
    return {
        **ledger,
        "kind": "a_share_three_day_walkforward_campaign289_terminal_trial_ledger",
        "reconciled_from": {
            "path": str(SOURCE_LEDGER_PATH),
            "sha256": SOURCE_LEDGER_SHA256,
        },
        "entries": [*ledger["entries"], *additions],
        "entry_count": 10,
        "infrastructure_failure_attempt_count": 2,
        "chain_tip_sha256": additions[-1]["entry_sha256"],
        "fold1_training_return_read_count_total": 3,
        "fold1_training_return_reread_count_for_infrastructure_recovery": 2,
        "lockbox_2024_2025_opened": False,
    }


def plan_finalize() -> dict[str, Any]:
    validate_inputs()
    validate_freeze()
    existing = [
        path.name
        for path in (TERMINAL_LEDGER_PATH, TERMINAL_REPORT_PATH)
        if path.exists()
    ]
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign289_finalization_plan",
        "status": (
            "ready_for_terminal_reconciliation"
            if not existing
            else "not_ready_preserve_terminal_outputs"
        ),
        "ready": not existing,
        "existing_terminal_outputs": existing,
        "historical_return_reread_by_plan": False,
        "model_refit_by_plan": False,
        "lockbox_2024_2025_return_read_by_plan": False,
        "candidate49_ledgers_changed": False,
    }


def run_finalize(confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise Campaign289FinalizationError("finalize requires --confirm-finalize")
    payload = plan_finalize()
    if payload["ready"] is not True:
        raise Campaign289FinalizationError("Campaign289 finalization plan is not ready")
    _, _, trial = validate_inputs()
    ledger = build_terminal_ledger()
    campaign.engine.atomic_write_json(TERMINAL_LEDGER_PATH, ledger)
    fold_results = []
    for fold, metrics in enumerate(trial["validation_metrics"], start=1):
        association = metrics["association"]
        normalized = metrics["normalized_execution"]
        pilot = metrics["pilot_execution_primary_10bp"]
        sensitivity = metrics["pilot_slippage_sensitivity"]
        fold_results.append(
            {
                "fold": fold,
                "validation_year": int(str(metrics["start"])[:4]),
                "cohorts": association["cohorts"],
                "mean_rank_ic": association["mean_rank_ic"],
                "mean_top3_minus_bottom3_gross_return": association[
                    "mean_top3_minus_bottom3_gross_return"
                ],
                "normalized_net_return": normalized["net_cumulative_return"],
                "normalized_maximum_drawdown": normalized["maximum_drawdown"],
                "pilot_10bp_net_return": pilot["net_cumulative_return"],
                "pilot_20bp_net_return": sensitivity["0.0020"]["net_cumulative_return"],
                "board_lot_affordability_rate": pilot["board_lot_affordability_rate"],
                "maximum_amount_participation": pilot[
                    "maximum_filled_trade_daily_amount_participation"
                ],
            }
        )
    report = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign289_terminal_development_report",
        "status": "terminal_no_survivor_lockbox_closed",
        "created_at": campaign.campaign286.utc_now(),
        "protocol_sha256": campaign.PROTOCOL_SHA256,
        "source_development_report": {
            "path": str(SOURCE_REPORT_PATH),
            "sha256": SOURCE_REPORT_SHA256,
        },
        "terminal_ledger": {
            "path": str(TERMINAL_LEDGER_PATH),
            "sha256": campaign.file_sha256(TERMINAL_LEDGER_PATH),
        },
        "trial_id": campaign.TRIAL_ID,
        "fold_results": fold_results,
        "aggregate_decision": trial["decision"],
        "attempt_accounting": {
            "prevalue_concept_attempt_count": 7,
            "infrastructure_failure_attempt_count": 2,
            "model_trial_attempt_count": 1,
            "total_attempt_count": 10,
            "return_reading_development_trial_count": 1,
            "model_fold_validation_return_read_count": 3,
            "fold1_training_return_read_count_total": 3,
            "fold1_training_return_reread_count_for_recovery": 2,
        },
        "development_survivor_count": 0,
        "selected_survivor_trial_ids": [],
        "lockbox_2024_2025_opened": False,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
        "provider_request_issued": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "investment_advice": False,
    }
    campaign.engine.atomic_write_json(TERMINAL_REPORT_PATH, report)
    return {
        "status": report["status"],
        "terminal_ledger_path": str(TERMINAL_LEDGER_PATH),
        "terminal_ledger_sha256": campaign.file_sha256(TERMINAL_LEDGER_PATH),
        "terminal_report_path": str(TERMINAL_REPORT_PATH),
        "terminal_report_sha256": campaign.file_sha256(TERMINAL_REPORT_PATH),
        "total_attempt_count": 10,
        "survivor_count": 0,
        "lockbox_2024_2025_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("plan")
    run = subcommands.add_parser("run")
    run.add_argument("--confirm-finalize", action="store_true")
    args = parser.parse_args()
    if args.command == "plan":
        payload = plan_finalize()
    elif args.command == "run":
        payload = run_finalize(args.confirm_finalize)
    else:
        raise Campaign289FinalizationError(f"unsupported command: {args.command}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
