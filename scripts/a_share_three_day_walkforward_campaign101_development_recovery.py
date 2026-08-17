#!/usr/bin/env python3
"""Recover Campaign101's unconsumed development trial on the bound Qlib runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from scripts import a_share_three_day_walkforward_campaign101 as campaign

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PYTHON = Path("/Volumes/DIsk/Coding/anaconda3/bin/python3.12")
PREREGISTRATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_preregistration_v2.json"
)
PREREGISTRATION_SHA256 = (
    "5cff18c65510eb01e4771e04f62b54bf038579a25f9ee14ec73863fe43947b36"
)
SCIENTIFIC_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign101.py"
SCIENTIFIC_RUNNER_SHA256 = (
    "8353c819b0c1a0edd98eb0999849a626d5a97c913655e2068ec18fb05b9c9b27"
)
OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_101/walkforward"
)
TRIAL_LEDGER = OUTPUT_ROOT / "trial_ledger.json"
FAILED_LEDGER_SHA256 = (
    "726bb925597461a6fb8eaac2ea073e62b74b221f83849a79683d3ad9ad6acae6"
)
RUNTIME_FAILURE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_development_runtime_import_failure_20260807.json"
)
RUNTIME_FAILURE_SHA256 = (
    "1e922a2e3aa552b19e46edb091fd3cb2a7d79109394ad2ed07172d5344d2b05f"
)
ORIGINAL_DEVELOPMENT_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_development_implementation_freeze_20260807.json"
)
ORIGINAL_DEVELOPMENT_FREEZE_SHA256 = (
    "f1d018c27655f8dee923d0c2f7856fc6ea2b4c38edd3e647ddab513519024e37"
)
ORIGINAL_DEVELOPMENT_ACTIVATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_development_activation_binding_20260807.json"
)
ORIGINAL_DEVELOPMENT_ACTIVATION_SHA256 = (
    "7728e8d8a210ed041fb6a05355b9cd96722a4e637ae95097cc42ef7b943f8a75"
)
RECOVERY_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_development_recovery_implementation_freeze_20260807.json"
)
RECOVERY_ACTIVATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_development_recovery_activation_binding_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign101_development_recovery.py"
)
FROZEN_TRIAL_ID = campaign.FROZEN_TRIAL_ID


class Campaign101DevelopmentRecoveryError(RuntimeError):
    """Fail closed when recovery would broaden or repeat the scientific trial."""


def _sha256(path: Path) -> str:
    return campaign._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign101DevelopmentRecoveryError(f"{label} changed: {path}")


def _validate_failed_ledger(ledger: dict[str, Any]) -> None:
    entries = list(ledger.get("entries") or [])
    campaign_binding = ledger.get("campaign") or {}
    if not (
        ledger.get("kind")
        == "a_share_three_day_historical_walkforward_campaign101_trial_ledger"
        and ledger.get("append_only") is True
        and campaign_binding.get("path") == str(PREREGISTRATION.resolve())
        and campaign_binding.get("sha256") == PREREGISTRATION_SHA256
        and len(entries) == 1
        and entries[0].get("phase") == "infrastructure_failure"
        and entries[0].get("trial_id") == "wf101_infrastructure__development_load_001"
        and (entries[0].get("status_and_rejection_reason") or {}).get("status")
        == "infrastructure_failed"
        and entries[0].get("candidate49_historical_return_read") is False
        and not any(
            item.get("phase") == "development_walkforward_2019_2023" for item in entries
        )
    ):
        raise Campaign101DevelopmentRecoveryError(
            "failed internal ledger semantics changed"
        )


def require_exact_runtime() -> None:
    if Path(sys.executable).resolve() != EXPECTED_PYTHON.resolve():
        raise Campaign101DevelopmentRecoveryError(
            f"recovery requires exact runtime {EXPECTED_PYTHON}"
        )
    from qlib.data import D

    if D is None:
        raise Campaign101DevelopmentRecoveryError("Qlib data import changed")


def load_recovery_activation() -> dict[str, Any]:
    for path, digest, label in (
        (SCIENTIFIC_RUNNER, SCIENTIFIC_RUNNER_SHA256, "scientific runner"),
        (PREREGISTRATION, PREREGISTRATION_SHA256, "preregistration"),
        (TRIAL_LEDGER, FAILED_LEDGER_SHA256, "failed trial ledger"),
        (RUNTIME_FAILURE, RUNTIME_FAILURE_SHA256, "runtime failure record"),
        (
            ORIGINAL_DEVELOPMENT_FREEZE,
            ORIGINAL_DEVELOPMENT_FREEZE_SHA256,
            "original development freeze",
        ),
        (
            ORIGINAL_DEVELOPMENT_ACTIVATION,
            ORIGINAL_DEVELOPMENT_ACTIVATION_SHA256,
            "original development activation",
        ),
    ):
        _require(path, digest, label)
    _validate_failed_ledger(json.loads(TRIAL_LEDGER.read_text(encoding="utf-8")))
    if any(
        (OUTPUT_ROOT / name).exists()
        for name in (
            "development_survivors.json",
            "exposed_stress_open_intent.json",
            "exposed_stress_consumption_record.json",
        )
    ):
        raise Campaign101DevelopmentRecoveryError("survivor or stress state exists")
    _require(
        RECOVERY_IMPLEMENTATION_FREEZE,
        _sha256(RECOVERY_IMPLEMENTATION_FREEZE),
        "recovery implementation freeze",
    )
    freeze = json.loads(RECOVERY_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign101_development_recovery_implementation_freeze"
        and freeze.get("status")
        == "frozen_after_one_runtime_infrastructure_failure_before_any_complete_development_trial"
        and (freeze.get("recovery_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (freeze.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (freeze.get("failed_internal_ledger") or {}).get("sha256")
        == FAILED_LEDGER_SHA256
        and freeze.get("complete_development_trial_count_before_recovery_freeze") == 0
        and freeze.get(
            "development_daily_price_or_forward_return_values_read_before_recovery_freeze"
        )
        is False
        and freeze.get("stress_2024_2025_read_before_recovery_freeze") is False
    ):
        raise Campaign101DevelopmentRecoveryError(
            "recovery implementation freeze changed"
        )
    if not RECOVERY_ACTIVATION.is_file():
        raise Campaign101DevelopmentRecoveryError("recovery activation is absent")
    activation = json.loads(RECOVERY_ACTIVATION.read_text(encoding="utf-8"))
    if not (
        activation.get("kind")
        == "a_share_three_day_walkforward_campaign101_development_recovery_activation_binding"
        and activation.get("status")
        == "same_single_frozen_development_trial_reauthorized_after_runtime_only_failure"
        and (activation.get("implementation_freeze") or {}).get("sha256")
        == _sha256(RECOVERY_IMPLEMENTATION_FREEZE)
        and (activation.get("failed_internal_ledger") or {}).get("sha256")
        == FAILED_LEDGER_SHA256
        and activation.get("remaining_complete_development_trials_authorized") == 1
        and activation.get("stress_2024_2025_authorized") is False
        and activation.get("provider_request_authorized") is False
    ):
        raise Campaign101DevelopmentRecoveryError("recovery activation changed")
    return activation


def _development_args(batch_size: int) -> SimpleNamespace:
    if batch_size < 1:
        raise Campaign101DevelopmentRecoveryError("batch size must be positive")
    return SimpleNamespace(
        campaign=str(PREREGISTRATION),
        output_root=str(OUTPUT_ROOT),
        batch_size=batch_size,
        command="run-development",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "run-development"))
    parser.add_argument("--batch-size", type=int, default=256)
    args = parser.parse_args()
    if args.command == "status":
        print(
            json.dumps(
                {
                    "failed_ledger_exists": TRIAL_LEDGER.is_file(),
                    "recovery_freeze_exists": RECOVERY_IMPLEMENTATION_FREEZE.is_file(),
                    "recovery_activation_exists": RECOVERY_ACTIVATION.is_file(),
                    "development_daily_price_or_forward_return_values_read_by_status": False,
                    "stress_2024_2025_read_by_status": False,
                },
                sort_keys=True,
            )
        )
        return 0
    load_recovery_activation()
    require_exact_runtime()
    result = campaign.run_development(_development_args(args.batch_size))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
