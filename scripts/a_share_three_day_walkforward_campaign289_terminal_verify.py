#!/usr/bin/env python3
"""Read-only terminal verification for Campaign289."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign289 as campaign
from scripts import a_share_three_day_walkforward_campaign289_recovery_v2 as recovery_v2


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = recovery_v2.RECOVERY_V2_OUTPUT_ROOT
FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_289_terminal_verifier_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign289_terminal_verify.py"
)
EXPECTED_ARTIFACT_SHA256 = {
    "development_intent.json": "a3295bb64809cb33f940591ea4a9e58cccce8612b3df56f2dcb5a2aa38d8c66a",
    "development_report.json": "0f9c5b79e65dfe87089b30bda9556ccd52817ab0248c3fcf678fbbeb59c8bf99",
    "development_survivors.json": "74137ce34b4b8a22763e2f2ae2d7941bc3b07579d152d4dab59d6b0a53094846",
    f"fold_1_model/{campaign.TRIAL_ID}.npz": "f6153a1421a900560f6a260b93d0d68fffd9229d1009247aa13680f344c29e4a",
    f"fold_2_model/{campaign.TRIAL_ID}.npz": "745070012aa77ec776ca388130862a46f04f77fbf7ae335fb2721ef3fe17b5bd",
    f"fold_3_model/{campaign.TRIAL_ID}.npz": "ab668aeef9751828475a0ae06b8f42e97250f7cc5bdd8bedee7ca6506ae63821",
    "fold_1_prefit_scores.json": "3ee2c7e6c107a0d54b1c3a45128399053e236a7904efb001bc65722772d18e84",
    "fold_2_prefit_scores.json": "6ed40a004f1422956c8ca97e6a41a368993f95ca5868a2f7c8afbd97ada2ca71",
    "fold_3_prefit_scores.json": "256fafc6265596c5d770e87b596e074aa081cac2727d97262b4abbf4184df396",
    "fold_1_validation_scores.parquet": "fbc092d1f5fa8ea0697d616c2344a79ccdccefb140f850fa2c25e62cc5d07e82",
    "fold_2_validation_scores.parquet": "b34a32325249b31df19949c07d4c45a12af6e836624914c67965122d65643cec",
    "fold_3_validation_scores.parquet": "27e19eab57df021abfe134a190f872ed109cc35bb5605280959529d471341021",
    "fold_1_validation_metrics.json": "5cd8f0ebfb5acad7724dd7811764fae83eea19e9402d5f108d47f4599e897a8a",
    "fold_2_validation_metrics.json": "ee80ae5adfd27009d55c18e1140500ab4bb79ddbaf22c87b392cb854dcb656d6",
    "fold_3_validation_metrics.json": "50f4e448ece8d7be09a66ce8bd9ec9999598e9990abc9e80a3d916e852304435",
    "recovery_v2_intent.json": "71660a7c89eff6a6fa3007134ab8ec3f1168dfdc97759e3e2f203a3ea46d0f9f",
    "trial_ledger.json": "1fa4523341296cb464ca54382d2be66e6f60a6ca742ee1374a5b186649c9e2cd",
    "terminal_trial_ledger.json": "e71f6725de7521e1221ef9cb4269adb594bf8462bc74f9610f1ed9aea75aabac",
    "terminal_development_report.json": "61f31ecdcc5c29b30a0f5eba7bdde5b6d7c3663fa3474e142aaef281447afc5c",
}


class Campaign289TerminalVerificationError(RuntimeError):
    """Fail closed when terminal Campaign289 evidence changes."""


def load_json(path: Path) -> dict[str, Any]:
    value = campaign.load_json(path)
    if not isinstance(value, dict):
        raise Campaign289TerminalVerificationError(f"expected object: {path}")
    return value


def require_file(path: Path, expected: str, label: str) -> None:
    try:
        campaign.require_file(path, expected, label)
    except campaign.Campaign289Error as error:
        raise Campaign289TerminalVerificationError(str(error)) from error


def validate_freeze() -> dict[str, Any]:
    if not FREEZE_PATH.is_file():
        raise Campaign289TerminalVerificationError("terminal verifier freeze missing")
    record = load_json(FREEZE_PATH)
    verifier = record.get("verifier") or {}
    tests = record.get("tests") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign289_terminal_verifier_implementation_freeze"
        and record.get("status") == "frozen_after_terminal_outputs_before_verification"
        and verifier.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and verifier.get("sha256") == campaign.file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == campaign.file_sha256(TEST_PATH)
        and (record.get("terminal_artifacts") or {}) == EXPECTED_ARTIFACT_SHA256
    ):
        raise Campaign289TerminalVerificationError("terminal verifier freeze changed")
    return record


def validate_terminal_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    entries = ledger.get("entries") or []
    if not (
        ledger.get("kind")
        == "a_share_three_day_walkforward_campaign289_terminal_trial_ledger"
        and ledger.get("append_only") is True
        and ledger.get("chain_genesis") == campaign.CHAIN_GENESIS
        and ledger.get("entry_count") == len(entries) == 10
        and ledger.get("prevalue_concept_attempt_count") == 7
        and ledger.get("infrastructure_failure_attempt_count") == 2
        and ledger.get("model_trial_attempt_count") == 1
        and ledger.get("validation_return_fold_count") == 3
        and ledger.get("fold1_training_return_read_count_total") == 3
        and ledger.get("fold1_training_return_reread_count_for_infrastructure_recovery")
        == 2
        and ledger.get("lockbox_2024_2025_opened") is False
        and ledger.get("candidate49_historical_return_read") is False
        and ledger.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign289TerminalVerificationError("terminal ledger semantics changed")
    previous = campaign.CHAIN_GENESIS
    for entry in entries:
        payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
        if not (
            entry.get("previous_entry_sha256") == previous
            and entry.get("entry_sha256") == campaign.engine.value_sha256(payload)
        ):
            raise Campaign289TerminalVerificationError(
                "terminal ledger hash chain changed"
            )
        previous = str(entry["entry_sha256"])
    if ledger.get("chain_tip_sha256") != previous:
        raise Campaign289TerminalVerificationError("terminal ledger chain tip changed")
    failures = [
        entry
        for entry in entries
        if str(entry.get("attempt_id", "")).startswith("c289_infra_")
    ]
    models = [entry for entry in entries if entry.get("trial_id") == campaign.TRIAL_ID]
    if not (
        len(failures) == 2
        and all(entry.get("model_fit_by_failed_attempt") is False for entry in failures)
        and all(
            entry.get("validation_return_read_by_failed_attempt") is False
            for entry in failures
        )
        and len(models) == 1
    ):
        raise Campaign289TerminalVerificationError(
            "terminal attempt accounting changed"
        )
    return models[0]


def verify() -> dict[str, Any]:
    validate_freeze()
    campaign.validate_common()
    recovery_v2.validate_v1_failure_bindings()
    recovery_v2.validate_recovery_v2_freeze()
    for relative, expected in EXPECTED_ARTIFACT_SHA256.items():
        require_file(OUTPUT_ROOT / relative, expected, f"Campaign289 {relative}")
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
        and decision.get("positive_normalized_return_fold_count") == 2
        and decision.get("positive_pilot_10bp_return_fold_count") == 1
        and decision.get("median_validation_mean_rank_ic") == 0.008518343977478105
        and decision.get("median_validation_spread") == 0.0006293885326906018
        and decision.get("median_validation_pilot_10bp_return") == -0.015611472838193308
        and decision.get("worst_validation_normalized_drawdown") == -0.36128117185554043
        and (decision.get("development_aggregate") or {}).get("pilot_20bp_return")
        == -0.08670230043066818
    ):
        raise Campaign289TerminalVerificationError("terminal trial decision changed")
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
        raise Campaign289TerminalVerificationError("terminal report semantics changed")
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign289_terminal_verification",
        "status": "verified_terminal_no_survivor_lockbox_closed",
        "ledger_entry_count": 10,
        "prevalue_concept_attempt_count": 7,
        "infrastructure_failure_attempt_count": 2,
        "model_trial_attempt_count": 1,
        "return_reading_development_trial_count": 1,
        "model_fold_validation_return_read_count": 3,
        "positive_rank_ic_fold_count": 3,
        "positive_pilot_10bp_return_fold_count": 1,
        "survivor_count": 0,
        "fold1_training_return_read_count_total": 3,
        "fold1_training_return_reread_count_for_recovery": 2,
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
