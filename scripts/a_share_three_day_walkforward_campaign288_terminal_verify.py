#!/usr/bin/env python3
"""Read-only terminal verification for Campaign288."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign288 as campaign
from scripts import a_share_three_day_walkforward_campaign288_recovery as recovery


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = recovery.RECOVERY_OUTPUT_ROOT
FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_288_terminal_verifier_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign288_terminal_verify.py"
)
EXPECTED_ARTIFACT_SHA256 = {
    "development_intent.json": "d152206f40b3365ec90a41c21d8ab68c75014c2bad37fab6f368686283cb4c38",
    "development_report.json": "07fedff926ea0befd503f1ed97860776d81a00f9d1b63b2a258549a969682c2c",
    "development_survivors.json": "dc502a76e035bddfa5ab1242cf56ab935d8d4822d5fd0b5d479b8d1921be2eff",
    f"fold_1_model/{campaign.TRIAL_ID}.npz": "0402d971a6a0f4c6654c87b9f823a5b616d475930f897abf4788a00c6fab164c",
    f"fold_2_model/{campaign.TRIAL_ID}.npz": "327377ed8833cf006aa3e1033875a3fbf164733bff14a9de04bc2a12ab9b3b58",
    f"fold_3_model/{campaign.TRIAL_ID}.npz": "21b5e217d4a7bc9cab0bfa145669dbd3cc1bb943f2c740c0268cfdaccefa409a",
    "fold_1_prefit_scores.json": "e0a5d8af89f0a9fced30560065d1a2775e9cd53b1530b2a75a26e560995d7a25",
    "fold_2_prefit_scores.json": "fcc4e97f0a7f4d4b3b7c772a168ae0b5f2f0917e102169840b6ddceef6a307ba",
    "fold_3_prefit_scores.json": "dcbce44a5fd9222433b91364b3ca0240d309fc0285626514003ac90db5b0a573",
    "fold_1_validation_scores.parquet": "0be08d9d6bf9741718922dcef887be1fd1698f4c51d59cc378e217eb15dcb4e6",
    "fold_2_validation_scores.parquet": "cdef61b7970d0df578597fb67c18a9c1b0a4e9ab309866e379da4a4da4635298",
    "fold_3_validation_scores.parquet": "dcfb1f6f262807d16ce8172d01d3a54de64bf7a1a2a255f83e3ef872b5a38e2f",
    "fold_1_validation_metrics.json": "249f12f6088442fd9b0b2a3a379a713ce5ab5fc0c3aad0c0502a336e581449fe",
    "fold_2_validation_metrics.json": "c2e1b78786207bb3e02f84860a572d96a39aa3b27b96c617e9ffba629b04fe2a",
    "fold_3_validation_metrics.json": "c4d851f330413723d93e23a83221a3170a86a54fc878e4a61970948893ef615a",
    "recovery_intent.json": "12aaeb36b91f0d67616a1d004ac4f6668ce4674ffde4fd07248f14b9c0222d53",
    "trial_ledger.json": "cb1cdfd602b3452cf3a4d613730aba763596b94378e89d5f2a18462fd1b5914a",
    "terminal_trial_ledger.json": "93a46098d4a3358e0477ea5395240e5bc45957f28d20fe4978984c542592b12b",
    "terminal_development_report.json": "1ebe48d2a6404725b96009cd6842658cd62a9ee6a3709e593a090139120e0740",
}


class Campaign288TerminalVerificationError(RuntimeError):
    """Fail closed when terminal Campaign288 evidence changes."""


def load_json(path: Path) -> dict[str, Any]:
    value = campaign.load_json(path)
    if not isinstance(value, dict):
        raise Campaign288TerminalVerificationError(f"expected object: {path}")
    return value


def require_file(path: Path, expected: str, label: str) -> None:
    try:
        campaign.require_file(path, expected, label)
    except campaign.Campaign288Error as error:
        raise Campaign288TerminalVerificationError(str(error)) from error


def validate_freeze() -> dict[str, Any]:
    if not FREEZE_PATH.is_file():
        raise Campaign288TerminalVerificationError("terminal verifier freeze missing")
    record = load_json(FREEZE_PATH)
    verifier = record.get("verifier") or {}
    tests = record.get("tests") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign288_terminal_verifier_implementation_freeze"
        and record.get("status") == "frozen_after_terminal_outputs_before_verification"
        and verifier.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and verifier.get("sha256") == campaign.file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == campaign.file_sha256(TEST_PATH)
        and (record.get("terminal_artifacts") or {}) == EXPECTED_ARTIFACT_SHA256
    ):
        raise Campaign288TerminalVerificationError("terminal verifier freeze changed")
    return record


def validate_terminal_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    entries = ledger.get("entries") or []
    if not (
        ledger.get("kind")
        == "a_share_three_day_walkforward_campaign288_terminal_trial_ledger"
        and ledger.get("append_only") is True
        and ledger.get("chain_genesis") == campaign.CHAIN_GENESIS
        and ledger.get("entry_count") == len(entries) == 10
        and ledger.get("prevalue_concept_attempt_count") == 8
        and ledger.get("infrastructure_failure_attempt_count") == 1
        and ledger.get("model_trial_attempt_count") == 1
        and ledger.get("validation_return_fold_count") == 3
        and ledger.get("fold1_training_return_reread_count_for_infrastructure_recovery")
        == 1
        and ledger.get("lockbox_2024_2025_opened") is False
        and ledger.get("candidate49_historical_return_read") is False
        and ledger.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign288TerminalVerificationError("terminal ledger semantics changed")
    previous = campaign.CHAIN_GENESIS
    for entry in entries:
        payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
        if not (
            entry.get("previous_entry_sha256") == previous
            and entry.get("entry_sha256") == campaign.engine.value_sha256(payload)
        ):
            raise Campaign288TerminalVerificationError("terminal ledger hash chain changed")
        previous = str(entry["entry_sha256"])
    if ledger.get("chain_tip_sha256") != previous:
        raise Campaign288TerminalVerificationError("terminal ledger chain tip changed")
    failures = [entry for entry in entries if entry.get("attempt_id") == "c288_infra_01"]
    models = [entry for entry in entries if entry.get("trial_id") == campaign.TRIAL_ID]
    if not (
        len(failures) == 1
        and failures[0].get("model_fit_by_failed_attempt") is False
        and failures[0].get("validation_return_read_by_failed_attempt") is False
        and len(models) == 1
    ):
        raise Campaign288TerminalVerificationError("terminal attempt accounting changed")
    return models[0]


def verify() -> dict[str, Any]:
    validate_freeze()
    campaign.validate_common()
    recovery.validate_failure_bindings()
    for relative, expected in EXPECTED_ARTIFACT_SHA256.items():
        require_file(OUTPUT_ROOT / relative, expected, f"Campaign288 {relative}")
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
    terminal_ledger = load_json(OUTPUT_ROOT / "terminal_trial_ledger.json")
    trial = validate_terminal_ledger(terminal_ledger)
    decision = trial.get("decision") or {}
    validations = trial.get("validation_metrics") or []
    if not (
        trial.get("status") == "development_rejected"
        and len(validations) == 3
        and decision.get("passed") is False
        and decision.get("operationally_admissible") is False
        and decision.get("positive_mean_rank_ic_fold_count") == 3
        and decision.get("positive_normalized_return_fold_count") == 0
        and decision.get("positive_pilot_10bp_return_fold_count") == 0
        and decision.get("median_validation_mean_rank_ic") == 0.010013622609836095
        and decision.get("median_validation_spread") == -0.011475951731758745
        and decision.get("median_validation_pilot_10bp_return")
        == -0.05227986804294105
        and decision.get("worst_validation_normalized_drawdown")
        == -0.5523865356328306
        and (decision.get("development_aggregate") or {}).get("pilot_20bp_return")
        == -0.18418712020077055
    ):
        raise Campaign288TerminalVerificationError("terminal trial decision changed")
    report = load_json(OUTPUT_ROOT / "terminal_development_report.json")
    source_report = load_json(OUTPUT_ROOT / "development_report.json")
    survivors = load_json(OUTPUT_ROOT / "development_survivors.json")
    if not (
        report.get("status") == "terminal_no_survivor_lockbox_closed"
        and len(report.get("fold_results") or []) == 3
        and (report.get("attempt_accounting") or {}).get("total_attempt_count") == 10
        and report.get("development_survivor_count") == 0
        and report.get("lockbox_2024_2025_opened") is False
        and report.get("candidate49_ledgers_changed") is False
        and report.get("provider_request_issued") is False
        and report.get("current_scoring_selection_sizing_or_orders_performed") is False
        and report.get("investment_advice") is False
        and source_report.get("model_fold_validation_return_reads") == 3
        and source_report.get("survivor_count") == 0
        and survivors.get("selected_survivor_count") == 0
        and survivors.get("lockbox_return_fields_read") is False
    ):
        raise Campaign288TerminalVerificationError("terminal report semantics changed")
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign288_terminal_verification",
        "status": "verified_terminal_no_survivor_lockbox_closed",
        "ledger_entry_count": 10,
        "prevalue_concept_attempt_count": 8,
        "infrastructure_failure_attempt_count": 1,
        "model_trial_attempt_count": 1,
        "return_reading_development_trial_count": 1,
        "model_fold_validation_return_read_count": 3,
        "positive_rank_ic_fold_count": 3,
        "positive_pilot_10bp_return_fold_count": 0,
        "survivor_count": 0,
        "fold1_training_return_reread_count_for_recovery": 1,
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
