#!/usr/bin/env python3
"""Finalize Campaign288 after reconciling its preserved infrastructure failure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign288 as campaign
from scripts import a_share_three_day_walkforward_campaign288_recovery as recovery


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = recovery.RECOVERY_OUTPUT_ROOT
SOURCE_LEDGER_PATH = OUTPUT_ROOT / "trial_ledger.json"
SOURCE_LEDGER_SHA256 = "cb1cdfd602b3452cf3a4d613730aba763596b94378e89d5f2a18462fd1b5914a"
SOURCE_REPORT_PATH = OUTPUT_ROOT / "development_report.json"
SOURCE_REPORT_SHA256 = "07fedff926ea0befd503f1ed97860776d81a00f9d1b63b2a258549a969682c2c"
SOURCE_SURVIVORS_PATH = OUTPUT_ROOT / "development_survivors.json"
SOURCE_SURVIVORS_SHA256 = "dc502a76e035bddfa5ab1242cf56ab935d8d4822d5fd0b5d479b8d1921be2eff"
RECOVERY_INTENT_PATH = OUTPUT_ROOT / "recovery_intent.json"
RECOVERY_INTENT_SHA256 = "12aaeb36b91f0d67616a1d004ac4f6668ce4674ffde4fd07248f14b9c0222d53"
FAILURE_RECORD_PATH = recovery.FAILURE_RECORD_PATH
FAILURE_RECORD_SHA256 = recovery.FAILURE_RECORD_SHA256
TERMINAL_LEDGER_PATH = OUTPUT_ROOT / "terminal_trial_ledger.json"
TERMINAL_REPORT_PATH = OUTPUT_ROOT / "terminal_development_report.json"
FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_288_finalizer_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign288_finalize.py"
)


class Campaign288FinalizationError(RuntimeError):
    """Fail closed when Campaign288 terminal evidence changes."""


def validate_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    campaign.validate_common()
    recovery.validate_failure_bindings()
    bindings = (
        (SOURCE_LEDGER_PATH, SOURCE_LEDGER_SHA256, "Campaign288 source ledger"),
        (SOURCE_REPORT_PATH, SOURCE_REPORT_SHA256, "Campaign288 source report"),
        (SOURCE_SURVIVORS_PATH, SOURCE_SURVIVORS_SHA256, "Campaign288 source survivors"),
        (RECOVERY_INTENT_PATH, RECOVERY_INTENT_SHA256, "Campaign288 recovery intent"),
        (FAILURE_RECORD_PATH, FAILURE_RECORD_SHA256, "Campaign288 failure record"),
    )
    for path, expected, label in bindings:
        campaign.require_file(path, expected, label)
    ledger = campaign.load_json(SOURCE_LEDGER_PATH)
    report = campaign.load_json(SOURCE_REPORT_PATH)
    survivors = campaign.load_json(SOURCE_SURVIVORS_PATH)
    entries = ledger.get("entries") or []
    model_entries = [entry for entry in entries if entry.get("trial_id") == campaign.TRIAL_ID]
    if not (
        ledger.get("kind") == "a_share_three_day_walkforward_campaign288_trial_ledger"
        and ledger.get("entry_count") == len(entries) == 9
        and ledger.get("prevalue_concept_attempt_count") == 8
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
        raise Campaign288FinalizationError("Campaign288 source terminal semantics changed")
    return ledger, report, model_entries[0]


def validate_freeze() -> dict[str, Any]:
    if not FREEZE_PATH.is_file():
        raise Campaign288FinalizationError("Campaign288 finalizer freeze missing")
    record = campaign.load_json(FREEZE_PATH)
    runner = record.get("runner") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign288_finalizer_implementation_freeze"
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
        raise Campaign288FinalizationError("Campaign288 finalizer freeze changed")
    return record


def validate_chain(ledger: dict[str, Any]) -> str:
    previous = campaign.CHAIN_GENESIS
    for entry in ledger.get("entries") or []:
        payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
        if not (
            entry.get("previous_entry_sha256") == previous
            and entry.get("entry_sha256") == campaign.engine.value_sha256(payload)
        ):
            raise Campaign288FinalizationError("Campaign288 source ledger chain changed")
        previous = str(entry["entry_sha256"])
    if ledger.get("chain_tip_sha256") != previous:
        raise Campaign288FinalizationError("Campaign288 source ledger tip changed")
    return previous


def build_terminal_ledger() -> dict[str, Any]:
    ledger, _, _ = validate_inputs()
    previous = validate_chain(ledger)
    reconciliation = {
        "attempt_id": "c288_infra_01",
        "phase": "post_run_attempt_reconciliation",
        "name": "training_projection_center_peer_set_implementation_failure",
        "outcome": "failed_before_model_fit_or_validation_return_read_then_recovered_without_model_change",
        "reason": "The original runner re-ranked after the market quality filter instead of preserving the preregistered design peer set. The failure occurred before a model fit or validation return read; a frozen recovery applied the design ordinal map before the join and reread fold-1 training returns once.",
        "occurred_before_model_trial_completion": True,
        "appended_after_model_trial_to_preserve_the_already_written_source_ledger": True,
        "evidence": {
            "path": str(FAILURE_RECORD_PATH.relative_to(REPO_ROOT)),
            "sha256": FAILURE_RECORD_SHA256,
        },
        "recovery_runner": {
            "path": str(Path(recovery.__file__).resolve().relative_to(REPO_ROOT)),
            "sha256": campaign.file_sha256(Path(recovery.__file__).resolve()),
        },
        "fold1_training_return_reread": True,
        "validation_return_read_by_failed_attempt": False,
        "model_fit_by_failed_attempt": False,
        "lockbox_2024_2025_opened": False,
        "candidate49_ledgers_changed": False,
        "previous_entry_sha256": previous,
    }
    reconciliation["entry_sha256"] = campaign.engine.value_sha256(reconciliation)
    terminal = {
        **ledger,
        "kind": "a_share_three_day_walkforward_campaign288_terminal_trial_ledger",
        "reconciled_from": {
            "path": str(SOURCE_LEDGER_PATH),
            "sha256": SOURCE_LEDGER_SHA256,
        },
        "entries": [*ledger["entries"], reconciliation],
        "entry_count": 10,
        "infrastructure_failure_attempt_count": 1,
        "chain_tip_sha256": reconciliation["entry_sha256"],
        "fold1_training_return_reread_count_for_infrastructure_recovery": 1,
        "lockbox_2024_2025_opened": False,
    }
    return terminal


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
        "kind": "a_share_three_day_walkforward_campaign288_finalization_plan",
        "status": "ready_for_terminal_reconciliation" if not existing else "not_ready_preserve_terminal_outputs",
        "ready": not existing,
        "existing_terminal_outputs": existing,
        "historical_return_reread_by_plan": False,
        "model_refit_by_plan": False,
        "lockbox_2024_2025_return_read_by_plan": False,
        "candidate49_ledgers_changed": False,
    }


def run_finalize(confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise Campaign288FinalizationError("finalize requires --confirm-finalize")
    payload = plan_finalize()
    if payload["ready"] is not True:
        raise Campaign288FinalizationError("Campaign288 finalization plan is not ready")
    _, _, trial = validate_inputs()
    ledger = build_terminal_ledger()
    campaign.engine.atomic_write_json(TERMINAL_LEDGER_PATH, ledger)
    validations = trial["validation_metrics"]
    decision = trial["decision"]
    fold_results = []
    for fold, metrics in enumerate(validations, start=1):
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
        "kind": "a_share_three_day_walkforward_campaign288_terminal_development_report",
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
        "aggregate_decision": decision,
        "attempt_accounting": {
            "prevalue_concept_attempt_count": 8,
            "infrastructure_failure_attempt_count": 1,
            "model_trial_attempt_count": 1,
            "total_attempt_count": 10,
            "return_reading_development_trial_count": 1,
            "model_fold_validation_return_read_count": 3,
            "fold1_training_return_reread_count_for_recovery": 1,
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
        raise Campaign288FinalizationError(f"unsupported command: {args.command}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
