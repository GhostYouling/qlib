#!/usr/bin/env python3
"""Recover Campaign102 with the frozen session-count indexing correction."""

from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import numpy as np

from scripts import a_share_three_day_walkforward_campaign102 as campaign
from scripts import a_share_three_day_walkforward_campaign102_development_recovery as v1

REPO_ROOT = Path(__file__).resolve().parents[1]
V1_RUNNER_SHA256 = "13ef2ee41e189cc0fef96a965ede3ce1cdb5b951b79f8214dab45fdc1ce432bd"
V1_ACTIVATION_SHA256 = "da29e0bef7755cedde80aec3410b5676181b728e6680978e498d97b848c119d5"
SESSION_KEY_FAILURE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_development_session_key_failure_20260807.json"
)
SESSION_KEY_FAILURE_SHA256 = "cbf69726689ec5dd1dffa692a642f4972bfbcbc7eded41f60fc4a6aaf57e860c"
V1_FAILED_INTENT = v1.RECOVERY_ROOT / "development_intent.json"
V1_FAILED_INTENT_SHA256 = "9d158530d6e0b0981c695a7a976a83b34b9d03d9680e22adbb097d1339cfb0a9"
V1_FAILED_RECORD = v1.RECOVERY_ROOT / "development_failure.json"
V1_FAILED_RECORD_SHA256 = "c1352638402b4e47fe416d7a0d4696c30e3602b9d316a2d160a0b3e6c2f471f4"
RECOVERY_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_102/"
    "walkforward_recovery_v2"
)
RECOVERY_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_development_recovery_v2_implementation_freeze_20260807.json"
)
RECOVERY_ACTIVATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_development_recovery_v2_activation_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign102_development_recovery_v2.py"
)


class Campaign102RecoveryV2Error(RuntimeError):
    """Fail closed if the v2 recovery changes more than session indexing."""


def corrected_sufficient_statistics(
    matrix: np.ndarray, target: np.ndarray, sessions: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Apply the original formula with representation-safe inverse indexing."""

    x = np.asarray(matrix, dtype=np.float64)
    y = np.asarray(target, dtype=np.float64)
    session_values = np.asarray(sessions)
    valid = np.isfinite(y) & np.isfinite(x).all(axis=1)
    x = x[valid]
    y = y[valid]
    session_values = session_values[valid]
    unique, inverse, counts = np.unique(
        session_values, return_inverse=True, return_counts=True
    )
    if len(unique) == 0 or len(x) < campaign.MIN_SIGNAL_NAMES:
        raise campaign.Campaign102Error("training target has insufficient observations")
    row_weight = 1.0 / (float(len(unique)) * counts[inverse].astype(np.float64))
    weighted = x * np.sqrt(row_weight)[:, None]
    a = weighted.T @ weighted
    b = x.T @ (row_weight * y)
    if not (np.isfinite(a).all() and np.isfinite(b).all()):
        raise campaign.Campaign102Error("training sufficient statistics are nonfinite")
    return a, b, {
        "training_observations": len(x),
        "training_sessions": len(unique),
        "minimum_names_per_training_session": int(counts.min()),
        "maximum_names_per_training_session": int(counts.max()),
        "session_equal_row_weight_sum": float(row_weight.sum()),
        "a_sha256": hashlib.sha256(np.asarray(a, dtype="<f8").tobytes()).hexdigest(),
        "b_sha256": hashlib.sha256(np.asarray(b, dtype="<f8").tobytes()).hexdigest(),
    }


@contextmanager
def install_correction() -> Iterator[None]:
    original = campaign.sufficient_statistics
    if original is corrected_sufficient_statistics:
        raise Campaign102RecoveryV2Error("session correction was preinstalled")
    campaign.sufficient_statistics = corrected_sufficient_statistics
    try:
        yield
    finally:
        campaign.sufficient_statistics = original


def require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or campaign.file_sha256(path) != expected:
        raise Campaign102RecoveryV2Error(f"{label} changed: {path}")


def validate_v1_failed_state() -> None:
    v1.validate_failed_state()
    for path, digest, label in (
        (Path(v1.__file__).resolve(), V1_RUNNER_SHA256, "v1 recovery runner"),
        (v1.RECOVERY_ACTIVATION, V1_ACTIVATION_SHA256, "v1 activation"),
        (SESSION_KEY_FAILURE, SESSION_KEY_FAILURE_SHA256, "session-key failure"),
        (V1_FAILED_INTENT, V1_FAILED_INTENT_SHA256, "v1 failed intent"),
        (V1_FAILED_RECORD, V1_FAILED_RECORD_SHA256, "v1 failed artifact"),
    ):
        require(path, digest, label)
    failure = campaign.load_json(V1_FAILED_RECORD)
    if not (
        failure.get("error_type") == "KeyError"
        and "2019-04-30" in str(failure.get("error"))
        and not any(
            (v1.RECOVERY_ROOT / name).exists()
            for name in (
                "trial_ledger.json",
                "development_survivors.json",
                "development_report.json",
                "fold_1_prefit_uniqueness.json",
            )
        )
    ):
        raise Campaign102RecoveryV2Error("v1 failed state changed")


def load_activation() -> dict[str, Any]:
    validate_v1_failed_state()
    if not RECOVERY_FREEZE.is_file() or not RECOVERY_ACTIVATION.is_file():
        raise Campaign102RecoveryV2Error("v2 freeze or activation is absent")
    freeze = campaign.load_json(RECOVERY_FREEZE)
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign102_development_recovery_v2_implementation_freeze"
        and freeze.get("status")
        == "frozen_after_session_key_failure_before_model_fit_or_validation"
        and (freeze.get("recovery_runner") or {}).get("sha256")
        == campaign.file_sha256(Path(__file__).resolve())
        and (freeze.get("tests") or {}).get("sha256")
        == campaign.file_sha256(TEST_PATH)
        and freeze.get("model_fit_count_before_v2") == 0
        and freeze.get("validation_return_read_count_before_v2") == 0
    ):
        raise Campaign102RecoveryV2Error("v2 recovery freeze changed")
    activation = campaign.load_json(RECOVERY_ACTIVATION)
    if not (
        activation.get("kind")
        == "a_share_three_day_walkforward_campaign102_development_recovery_v2_activation"
        and activation.get("status")
        == "same_three_frozen_trials_reauthorized_with_equivalent_session_index_repair"
        and (activation.get("implementation_freeze") or {}).get("sha256")
        == campaign.file_sha256(RECOVERY_FREEZE)
        and activation.get("remaining_complete_development_trial_count") == 3
        and activation.get("fresh_recovery_output_root") == str(RECOVERY_ROOT)
        and activation.get("lockbox_2024_2025_authorized") is False
    ):
        raise Campaign102RecoveryV2Error("v2 activation changed")
    return activation


def status() -> dict[str, Any]:
    return {
        "original_and_v1_failures_preserved": (
            v1.FAILED_RECORD.is_file() and V1_FAILED_RECORD.is_file()
        ),
        "recovery_root": str(RECOVERY_ROOT),
        "recovery_root_exists": RECOVERY_ROOT.exists(),
        "recovery_freeze_exists": RECOVERY_FREEZE.is_file(),
        "recovery_activation_exists": RECOVERY_ACTIVATION.is_file(),
        "model_fit_count_by_status": 0,
        "validation_return_read_count_by_status": 0,
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
    v1.require_exact_runtime()
    if RECOVERY_ROOT.exists():
        raise Campaign102RecoveryV2Error("v2 recovery output root already exists")
    with install_correction():
        result = campaign.run_development(
            SimpleNamespace(output_root=str(RECOVERY_ROOT), batch_size=args.batch_size)
        )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
