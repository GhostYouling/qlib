#!/usr/bin/env python3
"""Retry Campaign101 after synchronizing one frozen inherited loader constant."""

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
    "a4d13eae152f00b6cb956ecda73c0f0ed22729c20af647d574c03a4efe3b21af"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_development_candidate_loader_namespace_failure_20260807.json"
)
FAILURE_RECORD_SHA256 = (
    "66ddb89300b583bc33b0528113e2616f543aee77a30a4c9a3ae61adce467d1e6"
)
RESEARCH_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_101/research_attempt_ledger_v11.json"
)
RESEARCH_LEDGER_SHA256 = (
    "b88ff7688c0f513a093744c01be8da29c7a2e7ad80349dea6066ec0ecb9531f0"
)
FIRST_RECOVERY_RUNNER = (
    REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign101_development_recovery.py"
)
FIRST_RECOVERY_RUNNER_SHA256 = (
    "8979c9fe8a7c47dd041a006d40a766afe8b295835327a0c03b72442ce6cbe518"
)
FIRST_RECOVERY_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_development_recovery_implementation_freeze_20260807.json"
)
FIRST_RECOVERY_FREEZE_SHA256 = (
    "0f29d351af17df51857ece3af48292de9ee19e29fe3834962bbd824130445a95"
)
FIRST_RECOVERY_ACTIVATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_development_recovery_activation_binding_20260807.json"
)
FIRST_RECOVERY_ACTIVATION_SHA256 = (
    "1aa3be42215c04d6c6e3b132526382367052344d87d8e14b4545d88ba1d66959"
)
CANDIDATE_MANIFEST = campaign.COMPACT_MANIFEST
CANDIDATE_MANIFEST_SHA256 = campaign.COMPACT_MANIFEST_SHA256
CANDIDATE_DATASET_SHA256 = campaign.COMPACT_DATASET_SHA256
EXPECTED_ROWS = 1_331_759
STALE_INHERITED_ELIGIBLE_ROWS = 1_328_449
EXPECTED_ELIGIBLE_ROWS = 1_327_637
RECOVERY_V2_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_development_recovery_v2_implementation_freeze_20260807.json"
)
RECOVERY_V2_ACTIVATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_development_recovery_v2_activation_binding_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign101_development_recovery_v2.py"
)
FROZEN_TRIAL_ID = campaign.FROZEN_TRIAL_ID


class Campaign101DevelopmentRecoveryV2Error(RuntimeError):
    """Fail closed if the retry would change anything beyond one frozen constant."""


def _sha256(path: Path) -> str:
    return campaign._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign101DevelopmentRecoveryV2Error(f"{label} changed: {path}")


def _validate_failed_ledger(ledger: dict[str, Any]) -> None:
    entries = list(ledger.get("entries") or [])
    campaign_binding = ledger.get("campaign") or {}
    expected_ids = [
        "wf101_infrastructure__development_load_001",
        "wf101_infrastructure__development_load_002",
    ]
    if not (
        ledger.get("kind")
        == "a_share_three_day_historical_walkforward_campaign101_trial_ledger"
        and ledger.get("append_only") is True
        and campaign_binding.get("path") == str(PREREGISTRATION.resolve())
        and campaign_binding.get("sha256") == PREREGISTRATION_SHA256
        and len(entries) == 2
        and [item.get("trial_id") for item in entries] == expected_ids
        and all(item.get("phase") == "infrastructure_failure" for item in entries)
        and all(
            (item.get("status_and_rejection_reason") or {}).get("status")
            == "infrastructure_failed"
            for item in entries
        )
        and (entries[1].get("status_and_rejection_reason") or {}).get(
            "rejection_reason"
        )
        == "Campaign101Error: Campaign101 candidate snapshot semantics changed"
        and all(
            item.get("candidate49_historical_return_read") is False for item in entries
        )
        and not any(
            item.get("phase") == "development_walkforward_2019_2023" for item in entries
        )
    ):
        raise Campaign101DevelopmentRecoveryV2Error(
            "two-failure internal ledger semantics changed"
        )


def _candidate_loader_namespace() -> dict[str, Any]:
    return campaign._load_compact_factor_panel.__globals__


def synchronize_frozen_candidate_semantics() -> None:
    """Propagate the already frozen eligible count into the actual loader namespace."""

    _require(CANDIDATE_MANIFEST, CANDIDATE_MANIFEST_SHA256, "candidate manifest")
    manifest = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
    if not (
        manifest.get("dataset_sha256") == CANDIDATE_DATASET_SHA256
        and manifest.get("rows") == EXPECTED_ROWS
        and (manifest.get("factor_eligible_rows") or {}).get(campaign.ADMITTED_FACTOR)
        == EXPECTED_ELIGIBLE_ROWS
        and campaign.EXPECTED_ELIGIBLE_ROWS == EXPECTED_ELIGIBLE_ROWS
    ):
        raise Campaign101DevelopmentRecoveryV2Error(
            "frozen candidate manifest semantics changed"
        )
    namespace = _candidate_loader_namespace()
    observed = namespace.get("EXPECTED_ELIGIBLE_ROWS")
    if observed not in {STALE_INHERITED_ELIGIBLE_ROWS, EXPECTED_ELIGIBLE_ROWS}:
        raise Campaign101DevelopmentRecoveryV2Error(
            "inherited eligible-row constant changed unexpectedly"
        )
    namespace["EXPECTED_ELIGIBLE_ROWS"] = EXPECTED_ELIGIBLE_ROWS
    if namespace.get("EXPECTED_ELIGIBLE_ROWS") != EXPECTED_ELIGIBLE_ROWS:
        raise Campaign101DevelopmentRecoveryV2Error(
            "candidate loader namespace synchronization failed"
        )


def require_exact_runtime() -> None:
    if Path(sys.executable).resolve() != EXPECTED_PYTHON.resolve():
        raise Campaign101DevelopmentRecoveryV2Error(
            f"recovery requires exact runtime {EXPECTED_PYTHON}"
        )
    from qlib.data import D

    if D is None:
        raise Campaign101DevelopmentRecoveryV2Error("Qlib data import changed")


def load_recovery_v2_activation() -> dict[str, Any]:
    for path, digest, label in (
        (SCIENTIFIC_RUNNER, SCIENTIFIC_RUNNER_SHA256, "scientific runner"),
        (PREREGISTRATION, PREREGISTRATION_SHA256, "preregistration"),
        (TRIAL_LEDGER, FAILED_LEDGER_SHA256, "two-failure trial ledger"),
        (FAILURE_RECORD, FAILURE_RECORD_SHA256, "namespace failure record"),
        (RESEARCH_LEDGER, RESEARCH_LEDGER_SHA256, "research attempt ledger"),
        (
            FIRST_RECOVERY_RUNNER,
            FIRST_RECOVERY_RUNNER_SHA256,
            "first recovery runner",
        ),
        (
            FIRST_RECOVERY_FREEZE,
            FIRST_RECOVERY_FREEZE_SHA256,
            "first recovery freeze",
        ),
        (
            FIRST_RECOVERY_ACTIVATION,
            FIRST_RECOVERY_ACTIVATION_SHA256,
            "first recovery activation",
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
        raise Campaign101DevelopmentRecoveryV2Error("survivor or stress state exists")
    if not RECOVERY_V2_FREEZE.is_file():
        raise Campaign101DevelopmentRecoveryV2Error("recovery v2 freeze is absent")
    freeze = json.loads(RECOVERY_V2_FREEZE.read_text(encoding="utf-8"))
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign101_development_recovery_v2_implementation_freeze"
        and freeze.get("status")
        == "frozen_after_loader_namespace_failure_before_any_complete_development_trial"
        and (freeze.get("recovery_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (freeze.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (freeze.get("failed_internal_ledger") or {}).get("sha256")
        == FAILED_LEDGER_SHA256
        and (freeze.get("namespace_repair") or {}).get("from_eligible_rows")
        == STALE_INHERITED_ELIGIBLE_ROWS
        and (freeze.get("namespace_repair") or {}).get("to_eligible_rows")
        == EXPECTED_ELIGIBLE_ROWS
        and freeze.get("complete_development_trial_count_before_freeze") == 0
        and freeze.get("development_daily_price_values_previously_read") is True
        and freeze.get("forward_return_or_fold_metric_previously_computed") is False
        and freeze.get("stress_2024_2025_read_before_freeze") is False
    ):
        raise Campaign101DevelopmentRecoveryV2Error("recovery v2 freeze changed")
    if not RECOVERY_V2_ACTIVATION.is_file():
        raise Campaign101DevelopmentRecoveryV2Error("recovery v2 activation is absent")
    activation = json.loads(RECOVERY_V2_ACTIVATION.read_text(encoding="utf-8"))
    if not (
        activation.get("kind")
        == "a_share_three_day_walkforward_campaign101_development_recovery_v2_activation_binding"
        and activation.get("status")
        == "same_single_frozen_development_trial_reauthorized_after_namespace_only_failure"
        and (activation.get("implementation_freeze") or {}).get("sha256")
        == _sha256(RECOVERY_V2_FREEZE)
        and (activation.get("failed_internal_ledger") or {}).get("sha256")
        == FAILED_LEDGER_SHA256
        and activation.get("remaining_complete_development_trials_authorized") == 1
        and activation.get("stress_2024_2025_authorized") is False
        and activation.get("provider_request_authorized") is False
    ):
        raise Campaign101DevelopmentRecoveryV2Error("recovery v2 activation changed")
    return activation


def _development_args(batch_size: int) -> SimpleNamespace:
    if batch_size < 1:
        raise Campaign101DevelopmentRecoveryV2Error("batch size must be positive")
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
                    "recovery_v2_freeze_exists": RECOVERY_V2_FREEZE.is_file(),
                    "recovery_v2_activation_exists": RECOVERY_V2_ACTIVATION.is_file(),
                    "development_daily_price_values_read_in_prior_failed_attempt": True,
                    "forward_return_or_fold_metric_computed_in_prior_failed_attempt": False,
                    "complete_development_trial_count": 0,
                    "stress_2024_2025_read": False,
                },
                sort_keys=True,
            )
        )
        return 0
    load_recovery_v2_activation()
    require_exact_runtime()
    synchronize_frozen_candidate_semantics()
    result = campaign.run_development(_development_args(args.batch_size))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
