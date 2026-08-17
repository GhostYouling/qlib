#!/usr/bin/env python3
"""Recover Campaign102 after the pre-data isolated-runtime import failure."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from scripts import a_share_three_day_walkforward_campaign102 as campaign

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PYTHON = Path("/Volumes/DIsk/Coding/anaconda3/bin/python3.12")
EXPECTED_PYTHON_SHA256 = "b21ee43bcb627125a1b54b1fceb97bad564afbab38235cb9d72cf1f278d5751c"
EXPECTED_LIBCXX = Path("/Volumes/DIsk/Coding/anaconda3/lib/libc++.1.0.dylib")
EXPECTED_LIBCXX_SHA256 = "1b9318492353b7b7b3b48b9fa458d2b07b356a5eb8c0931952247fc17bf95c21"
SCIENTIFIC_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign102.py"
SCIENTIFIC_RUNNER_SHA256 = "ba298ed23d0675f6fea5de85bbf085dcb7b88ef72e730031b90e1e6b350ca6db"
ORIGINAL_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_development_implementation_freeze_20260807.json"
)
ORIGINAL_FREEZE_SHA256 = "ef7d231ac87dac703b8de97d59b084ffc1de40d74acb131306e867eaaa39849b"
RUNTIME_FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_development_runtime_import_failure_20260807.json"
)
RUNTIME_FAILURE_RECORD_SHA256 = "8f4829afd874620577078b681ee975aaf57e3a30beead2afcdbb11551dab7f0b"
FAILED_ROOT = campaign.DEFAULT_OUTPUT_ROOT
FAILED_INTENT = FAILED_ROOT / "development_intent.json"
FAILED_INTENT_SHA256 = "469be0f056407fd1f4d3c5aeb491d222c34241250a59ddfe97a4c880ff6328fb"
FAILED_RECORD = FAILED_ROOT / "development_failure.json"
FAILED_RECORD_SHA256 = "5bf1c93c153bae6b49848ae328d1999cadacc32c22168edc511fee6e703afbd8"
RECOVERY_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_102/"
    "walkforward_recovery_v1"
)
RECOVERY_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_development_recovery_implementation_freeze_20260807.json"
)
RECOVERY_ACTIVATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_development_recovery_activation_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign102_development_recovery.py"
)


class Campaign102RecoveryError(RuntimeError):
    """Fail closed if recovery broadens, duplicates, or changes the campaign."""


def require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or campaign.file_sha256(path) != expected:
        raise Campaign102RecoveryError(f"{label} changed: {path}")


def validate_failed_state() -> None:
    for path, digest, label in (
        (SCIENTIFIC_RUNNER, SCIENTIFIC_RUNNER_SHA256, "scientific runner"),
        (ORIGINAL_FREEZE, ORIGINAL_FREEZE_SHA256, "original freeze"),
        (RUNTIME_FAILURE_RECORD, RUNTIME_FAILURE_RECORD_SHA256, "failure record"),
        (FAILED_INTENT, FAILED_INTENT_SHA256, "failed intent"),
        (FAILED_RECORD, FAILED_RECORD_SHA256, "failed artifact"),
    ):
        require(path, digest, label)
    failure = campaign.load_json(FAILED_RECORD)
    if not (
        failure.get("status")
        == "failed_preserved_requires_explicit_recovery_revision"
        and failure.get("error_type") == "ImportError"
        and "libc++.1.dylib" in str(failure.get("error"))
        and not any(
            (FAILED_ROOT / name).exists()
            for name in (
                "trial_ledger.json",
                "development_survivors.json",
                "development_report.json",
                "fold_1_prefit_uniqueness.json",
            )
        )
    ):
        raise Campaign102RecoveryError("failed Campaign102 state changed")


def require_exact_runtime() -> None:
    if Path(sys.executable).resolve() != EXPECTED_PYTHON.resolve():
        raise Campaign102RecoveryError(f"recovery requires exact runtime {EXPECTED_PYTHON}")
    require(EXPECTED_PYTHON, EXPECTED_PYTHON_SHA256, "recovery Python")
    require(EXPECTED_LIBCXX, EXPECTED_LIBCXX_SHA256, "recovery libc++")
    from qlib.data import D

    if D is None:
        raise Campaign102RecoveryError("Qlib data import changed")


def load_activation() -> dict[str, Any]:
    validate_failed_state()
    if not RECOVERY_FREEZE.is_file() or not RECOVERY_ACTIVATION.is_file():
        raise Campaign102RecoveryError("recovery freeze or activation is absent")
    freeze = campaign.load_json(RECOVERY_FREEZE)
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign102_development_recovery_implementation_freeze"
        and freeze.get("status")
        == "frozen_after_predata_runtime_failure_before_any_model_fit_or_complete_trial"
        and (freeze.get("recovery_runner") or {}).get("sha256")
        == campaign.file_sha256(Path(__file__).resolve())
        and (freeze.get("tests") or {}).get("sha256")
        == campaign.file_sha256(TEST_PATH)
        and (freeze.get("failed_artifact") or {}).get("sha256")
        == FAILED_RECORD_SHA256
        and freeze.get("complete_development_trial_count_before_recovery") == 0
        and freeze.get("market_rows_or_return_values_read_before_recovery") is False
    ):
        raise Campaign102RecoveryError("recovery implementation freeze changed")
    activation = campaign.load_json(RECOVERY_ACTIVATION)
    if not (
        activation.get("kind")
        == "a_share_three_day_walkforward_campaign102_development_recovery_activation"
        and activation.get("status")
        == "same_three_frozen_trials_reauthorized_after_runtime_only_failure"
        and (activation.get("implementation_freeze") or {}).get("sha256")
        == campaign.file_sha256(RECOVERY_FREEZE)
        and activation.get("remaining_complete_development_trial_count") == 3
        and activation.get("fresh_recovery_output_root") == str(RECOVERY_ROOT)
        and activation.get("lockbox_2024_2025_authorized") is False
        and activation.get("provider_request_authorized") is False
    ):
        raise Campaign102RecoveryError("recovery activation changed")
    return activation


def status() -> dict[str, Any]:
    return {
        "failed_state_preserved": FAILED_INTENT.is_file() and FAILED_RECORD.is_file(),
        "recovery_root": str(RECOVERY_ROOT),
        "recovery_root_exists": RECOVERY_ROOT.exists(),
        "recovery_freeze_exists": RECOVERY_FREEZE.is_file(),
        "recovery_activation_exists": RECOVERY_ACTIVATION.is_file(),
        "market_rows_or_return_values_read_by_status": False,
        "candidate49_ledgers_changed_by_status": False,
        "provider_request_issued_by_status": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "run-development"))
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    if args.command == "status":
        print(json.dumps(status(), ensure_ascii=False, sort_keys=True))
        return 0
    load_activation()
    require_exact_runtime()
    if RECOVERY_ROOT.exists():
        raise Campaign102RecoveryError("recovery output root already exists")
    result = campaign.run_development(
        SimpleNamespace(output_root=str(RECOVERY_ROOT), batch_size=args.batch_size)
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
