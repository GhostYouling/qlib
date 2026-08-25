#!/usr/bin/env python3
"""Read-only terminal verification for the frozen Campaign286 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_286/walkforward_v1"
)
FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_terminal_verifier_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign286_terminal_verify.py"
)
SIGNAL_LEDGER_PATH = Path(
    "/Volumes/DIsk/Disk-Coding/qlib/data/experiments/short_horizon/"
    "candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER_PATH = Path(
    "/Volumes/DIsk/Disk-Coding/qlib/data/experiments/short_horizon/"
    "candidate49_future_execution_ledger.json"
)
EXPECTED_SHA256 = {
    "trial_ledger.json": "1dfceab3ab34e3063f9264096b9dd8c87cd35ffc95dd50215f2e8f76576b69ad",
    "development_survivors.json": "360a263dc7f34807efbf35e06420fb6697ff153b988dae955ced728210b49e44",
    "development_report.json": "448e6165634c85f9a9b0577c9646906cdab3726a4cdb0c902754c35fd71fbd7e",
}
SIGNAL_LEDGER_SHA256 = (
    "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
)
EXECUTION_LEDGER_SHA256 = (
    "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
)
PROTOCOL_SHA256 = (
    "62bc6eccb6d1240f5f08ce895c05fca4ca2231cf9deca7fda0cf7f1af6ca91af"
)
DESIGN_DATASET_SHA256 = (
    "714f4ccbdf4bfbaccfd04f543ec8c6a0bc345d3cc567ab621d01905130c46252"
)
TRIAL_IDS = {
    "wf286_lgb_shallow_158f",
    "wf286_lgb_medium_158f",
    "wf286_lgb_deep_158f",
}


class Campaign286TerminalVerificationError(RuntimeError):
    """Fail closed when Campaign286 terminal evidence changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def value_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise Campaign286TerminalVerificationError(f"expected object: {path}")
    return value


def require_sha256(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise Campaign286TerminalVerificationError(f"missing {label}: {path}")
    actual = file_sha256(path)
    if actual != expected:
        raise Campaign286TerminalVerificationError(
            f"{label} sha256 changed: expected {expected}, got {actual}"
        )


def validate_freeze() -> dict[str, Any]:
    freeze = load_json(FREEZE_PATH)
    verifier = freeze.get("verifier") or {}
    tests = freeze.get("tests") or {}
    artifacts = freeze.get("terminal_artifacts") or {}
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign286_terminal_verifier_implementation_freeze"
        and freeze.get("status") == "frozen_after_terminal_outputs_before_verification"
        and verifier.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and verifier.get("sha256") == file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == file_sha256(TEST_PATH)
        and artifacts == EXPECTED_SHA256
    ):
        raise Campaign286TerminalVerificationError("terminal verifier freeze changed")
    return freeze


def validate_ledger(ledger: dict[str, Any]) -> None:
    entries = ledger.get("entries") or []
    if not (
        ledger.get("kind") == "a_share_three_day_walkforward_campaign286_trial_ledger"
        and ledger.get("append_only") is True
        and ledger.get("chain_genesis") == "0" * 64
        and ledger.get("entry_count") == 16
        and len(entries) == 16
        and ledger.get("prevalue_concept_attempt_count") == 6
        and ledger.get("infrastructure_failure_attempt_count") == 7
        and ledger.get("model_trial_attempt_count") == 3
        and ledger.get("total_model_fold_validation_return_reads") == 9
        and ledger.get("candidate49_historical_return_read") is False
        and ledger.get("candidate49_ledgers_changed") is False
        and (ledger.get("campaign") or {}).get("protocol_sha256") == PROTOCOL_SHA256
        and (ledger.get("campaign") or {}).get("design_dataset_sha256")
        == DESIGN_DATASET_SHA256
    ):
        raise Campaign286TerminalVerificationError("terminal ledger semantics changed")
    previous = "0" * 64
    for entry in entries:
        recorded = entry.get("entry_sha256")
        payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
        if entry.get("previous_entry_sha256") != previous or value_sha256(payload) != recorded:
            raise Campaign286TerminalVerificationError("terminal ledger hash chain changed")
        previous = str(recorded)
    if ledger.get("chain_tip_sha256") != previous:
        raise Campaign286TerminalVerificationError("terminal ledger chain tip changed")
    model_entries = [entry for entry in entries if entry.get("trial_id") in TRIAL_IDS]
    if not (
        len(model_entries) == 3
        and all(entry.get("status") == "development_rejected" for entry in model_entries)
        and all(entry.get("validation_return_fold_count") == 3 for entry in model_entries)
        and all((entry.get("decision") or {}).get("passed") is False for entry in model_entries)
    ):
        raise Campaign286TerminalVerificationError("model trial decisions changed")


def verify() -> dict[str, Any]:
    validate_freeze()
    for name, expected in EXPECTED_SHA256.items():
        require_sha256(OUTPUT_ROOT / name, expected, f"Campaign286 {name}")
    require_sha256(SIGNAL_LEDGER_PATH, SIGNAL_LEDGER_SHA256, "Candidate49 signal ledger")
    require_sha256(
        EXECUTION_LEDGER_PATH, EXECUTION_LEDGER_SHA256, "Candidate49 execution ledger"
    )

    ledger = load_json(OUTPUT_ROOT / "trial_ledger.json")
    survivors = load_json(OUTPUT_ROOT / "development_survivors.json")
    report = load_json(OUTPUT_ROOT / "development_report.json")
    validate_ledger(ledger)
    if not (
        survivors.get("status") == "frozen_no_survivor_lockbox_remains_closed"
        and survivors.get("selected_survivor_count") == 0
        and survivors.get("selected_lockbox_survivor_trial_ids") == []
        and survivors.get("lockbox_return_fields_read") is False
        and survivors.get("candidate49_ledgers_changed") is False
        and set((survivors.get("trial_decisions") or {}).keys()) == TRIAL_IDS
        and all(
            decision.get("passed") is False
            for decision in (survivors.get("trial_decisions") or {}).values()
        )
    ):
        raise Campaign286TerminalVerificationError("survivor decision semantics changed")
    if not (
        report.get("status") == "development_complete_no_survivor_lockbox_closed"
        and report.get("trial_count") == 3
        and report.get("ledger_entry_count") == 16
        and report.get("validation_return_reading_trial_count") == 3
        and report.get("total_model_fold_validation_return_reads") == 9
        and report.get("survivor_count") == 0
        and report.get("selected_survivor_trial_ids") == []
        and report.get("training_metrics_persisted") is False
        and report.get("historical_returns_reread_by_finalizer") is False
        and report.get("model_refit_by_finalizer") is False
        and report.get("lockbox_2024_2025_opened") is False
        and report.get("candidate49_historical_return_read") is False
        and report.get("candidate49_ledgers_changed") is False
        and report.get("provider_request_issued") is False
        and report.get("current_scoring_selection_sizing_or_orders_performed") is False
        and report.get("investment_advice") is False
    ):
        raise Campaign286TerminalVerificationError("terminal report semantics changed")
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_terminal_verification",
        "status": "verified_terminal_no_survivor_lockbox_closed",
        "ledger_entry_count": 16,
        "prevalue_concept_attempt_count": 6,
        "infrastructure_failure_attempt_count": 7,
        "model_trial_attempt_count": 3,
        "return_reading_development_trial_count": 3,
        "model_fold_validation_return_read_count": 9,
        "survivor_count": 0,
        "lockbox_2024_2025_opened": False,
        "candidate49_ledgers_changed": False,
        "historical_returns_reread_by_verifier": False,
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
