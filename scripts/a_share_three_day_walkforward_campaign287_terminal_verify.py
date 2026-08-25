#!/usr/bin/env python3
"""Read-only terminal verification for Campaign287."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign287 as campaign


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = campaign.OUTPUT_ROOT
FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_287_terminal_verifier_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign287_terminal_verify.py"
)
EXPECTED_ARTIFACT_SHA256 = {
    "design_evidence.json": "286a269d238659d91f7abe58e8efd5a7d5ad172a8d70fd9b224c7d8d5473d2e5",
    "development_failure.json": "6d4d89fd88ecfb329c7565f2e771e942c4fcdea8e671e64875c1ae3799762930",
    "development_intent.json": "19c9385f11fe817f7a38f4ebc43420a63aaa82d289616534b6b7dd19250e723c",
    "recovery_intent.json": "e65412819c1e158e1656ec94e2e31356f6ecdaa0d61d254b314d0daf69b07fc9",
    f"fold_1_model/{campaign.TRIAL_ID}.npz": "8288228b3737b4ebdfd6bbc3d9e279188cbdd7282b599e6f6251aae2efd756cf",
    f"fold_2_model/{campaign.TRIAL_ID}.npz": "4a7d8763ab7bbe144326e36b75876b2da727f3ddc84d18cd0f1e9d1acf7dbf7d",
    f"fold_3_model/{campaign.TRIAL_ID}.npz": "2c7cc3eaa8dcd266d7e6a51bf1430bae0c0fb577affcf83d5a1bc061caa933c8",
    "fold_1_prefit_scores.json": "b9b675bd57aef15452b01270e826935bb0f2361dad8a130be0c1e8f2ea50675b",
    "fold_2_prefit_scores.json": "7f9a343dbefe884e5c1da26254619a2c55ffb183e0f2183d44b9efc85f08bbfc",
    "fold_3_prefit_scores.json": "e82f66b31fab7f657fc25969e5a2b5ea5838e52f9f85f4a3d130e0be9761deb6",
    "fold_1_validation_scores.parquet": "f928255ab12b6cd734bfc66e8630df20607fd02b594e732c5d6f90b65f38f97e",
    "fold_2_validation_scores.parquet": "cb229102d7fd204fef7210681b969e6a1cb2319d5b7d8ec02ead6932287258bc",
    "fold_3_validation_scores.parquet": "cf86c1bc2f9302717927cdb573e201e599fbfcb31daf48b2c8f652f87c0da982",
    "fold_1_validation_metrics.json": "ec6a89b80af6c9297697e77236c57f6b7c02a2261f150130a65b86eae39f1a4d",
    "fold_2_validation_metrics.json": "98f73b7912fe0d070e96f13fba27078fa18f17b4b93389e51db8049f2b948ad1",
    "fold_3_validation_metrics.json": "fe08acfad210c4ab87f72a50764ef8b28d7ea21bf666332fb7d5e6e0da63427b",
    "trial_ledger.json": "9d46cbd7fd55fcab8aaad583042a182a42937665c7aecd2fda83cc6f56dbe8ca",
    "development_survivors.json": "4253e68503b595d26c0150ff1ee610cc28c1c96c0d3f02ca914fde11590b1bf8",
    "development_report.json": "b513668cd79f17f5dacd88257a8cff0bf345d1b4b76cd807707b09ba4dc88a66",
}


class Campaign287TerminalVerificationError(RuntimeError):
    """Fail closed when terminal Campaign287 evidence changes."""


def load_json(path: Path) -> dict[str, Any]:
    value = campaign.load_json(path)
    if not isinstance(value, dict):
        raise Campaign287TerminalVerificationError(f"expected object: {path}")
    return value


def require_file(path: Path, expected: str, label: str) -> None:
    try:
        campaign.require_file(path, expected, label)
    except campaign.Campaign287Error as error:
        raise Campaign287TerminalVerificationError(str(error)) from error


def validate_freeze() -> dict[str, Any]:
    if not FREEZE_PATH.is_file():
        raise Campaign287TerminalVerificationError("terminal verifier freeze missing")
    record = load_json(FREEZE_PATH)
    verifier = record.get("verifier") or {}
    tests = record.get("tests") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign287_terminal_verifier_implementation_freeze"
        and record.get("status") == "frozen_after_terminal_outputs_before_verification"
        and verifier.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and verifier.get("sha256") == campaign.file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == campaign.file_sha256(TEST_PATH)
        and (record.get("terminal_artifacts") or {}) == EXPECTED_ARTIFACT_SHA256
    ):
        raise Campaign287TerminalVerificationError("terminal verifier freeze changed")
    return record


def validate_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    entries = ledger.get("entries") or []
    if not (
        ledger.get("kind") == "a_share_three_day_walkforward_campaign287_trial_ledger"
        and ledger.get("append_only") is True
        and ledger.get("chain_genesis") == "0" * 64
        and ledger.get("entry_count") == 9
        and len(entries) == 9
        and ledger.get("prevalue_concept_attempt_count") == 7
        and ledger.get("infrastructure_failure_attempt_count") == 1
        and ledger.get("model_trial_attempt_count") == 1
        and ledger.get("validation_return_fold_count") == 3
        and ledger.get("candidate49_historical_return_read") is False
        and ledger.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign287TerminalVerificationError("terminal ledger semantics changed")
    previous = "0" * 64
    for entry in entries:
        payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
        if not (
            entry.get("previous_entry_sha256") == previous
            and entry.get("entry_sha256") == campaign.engine.value_sha256(payload)
        ):
            raise Campaign287TerminalVerificationError("terminal ledger hash chain changed")
        previous = str(entry["entry_sha256"])
    if ledger.get("chain_tip_sha256") != previous:
        raise Campaign287TerminalVerificationError("terminal ledger chain tip changed")
    model_entries = [entry for entry in entries if entry.get("trial_id") == campaign.TRIAL_ID]
    if len(model_entries) != 1:
        raise Campaign287TerminalVerificationError("terminal model entry changed")
    return model_entries[0]


def verify() -> dict[str, Any]:
    validate_freeze()
    campaign.validate_common()
    for relative, expected in EXPECTED_ARTIFACT_SHA256.items():
        require_file(OUTPUT_ROOT / relative, expected, f"Campaign287 {relative}")
    require_file(
        campaign.campaign286.SOURCE_SIGNAL_LEDGER_PATH,
        campaign.campaign286.SIGNAL_LEDGER_SHA256,
        "Candidate49 signal ledger",
    )
    require_file(
        campaign.campaign286.SOURCE_EXECUTION_LEDGER_PATH,
        campaign.campaign286.EXECUTION_LEDGER_SHA256,
        "Candidate49 execution ledger",
    )
    ledger = load_json(OUTPUT_ROOT / "trial_ledger.json")
    trial = validate_ledger(ledger)
    decision = trial.get("decision") or {}
    validations = trial.get("validation_metrics") or []
    if not (
        trial.get("status") == "development_rejected"
        and len(validations) == 3
        and decision.get("passed") is False
        and decision.get("operationally_admissible") is True
        and decision.get("positive_mean_rank_ic_fold_count") == 3
        and decision.get("positive_normalized_return_fold_count") == 2
        and decision.get("positive_pilot_10bp_return_fold_count") == 2
        and decision.get("median_validation_mean_rank_ic") == 0.0138881059957977
        and decision.get("median_validation_spread") == 0.0037658851423829393
        and decision.get("median_validation_pilot_10bp_return")
        == 0.018914845321379437
        and decision.get("worst_validation_normalized_drawdown")
        == -0.35842432847095207
        and (decision.get("development_aggregate") or {}).get("pilot_20bp_return")
        == -0.06076703513604231
        and decision.get("rejection_reasons")
        == ["development_quality_or_aggregate_gate_failed"]
    ):
        raise Campaign287TerminalVerificationError("terminal trial decision changed")
    report = load_json(OUTPUT_ROOT / "development_report.json")
    survivors = load_json(OUTPUT_ROOT / "development_survivors.json")
    if not (
        report.get("status") == "development_complete_survivors_frozen"
        and report.get("trial_count") == 1
        and report.get("ledger_entry_count") == 9
        and report.get("validation_return_reading_trial_count") == 1
        and report.get("model_fold_validation_return_reads") == 3
        and report.get("survivor_count") == 0
        and report.get("selected_survivor_trial_ids") == []
        and report.get("lockbox_2024_2025_opened") is False
        and (report.get("recovery") or {}).get("fold1_model_refit") is False
        and (report.get("recovery") or {}).get("fold1_training_return_reread") is False
        and (report.get("recovery") or {}).get("fold1_training_metrics_persisted")
        is False
        and report.get("candidate49_ledgers_changed") is False
        and report.get("provider_request_issued") is False
        and report.get("current_scoring_selection_sizing_or_orders_performed") is False
        and report.get("investment_advice") is False
        and survivors.get("selected_survivor_count") == 0
        and survivors.get("selected_lockbox_survivor_trial_ids") == []
        and survivors.get("lockbox_return_fields_read") is False
    ):
        raise Campaign287TerminalVerificationError("terminal report semantics changed")
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign287_terminal_verification",
        "status": "verified_terminal_no_survivor_lockbox_closed",
        "ledger_entry_count": 9,
        "prevalue_concept_attempt_count": 7,
        "infrastructure_failure_attempt_count": 1,
        "model_trial_attempt_count": 1,
        "return_reading_development_trial_count": 1,
        "model_fold_validation_return_read_count": 3,
        "positive_rank_ic_fold_count": 3,
        "survivor_count": 0,
        "fold1_training_return_reread": False,
        "lockbox_2024_2025_opened": False,
        "candidate49_ledgers_changed": False,
        "provider_request_issued": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify",))
    parser.parse_args()
    print(json.dumps(verify(), ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
