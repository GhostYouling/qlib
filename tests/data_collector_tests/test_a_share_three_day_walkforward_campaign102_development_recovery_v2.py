from __future__ import annotations

import json

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign102 as campaign
from scripts import (
    a_share_three_day_walkforward_campaign102_development_recovery_v2 as recovery,
)


def test_v1_failure_is_preserved_before_any_fit_or_validation() -> None:
    recovery.validate_v1_failed_state()
    failure = json.loads(recovery.V1_FAILED_RECORD.read_text(encoding="utf-8"))
    assert failure["error_type"] == "KeyError"
    assert not (recovery.v1.RECOVERY_ROOT / "fold_1_prefit_uniqueness.json").exists()
    assert not (recovery.v1.RECOVERY_ROOT / "trial_ledger.json").exists()


def test_corrected_statistics_handle_numpy_datetime64_and_are_session_equal() -> None:
    rng = np.random.default_rng(31)
    matrix = rng.uniform(0.1, 1.0, size=(150, 130))
    target = rng.uniform(0.0, 1.0, size=150)
    sessions = np.array(
        [np.datetime64("2019-04-30")] * 50
        + [np.datetime64("2019-05-06")] * 100
    )
    a, b, stats = recovery.corrected_sufficient_statistics(matrix, target, sessions)
    weights = np.r_[np.full(50, 1.0 / (2 * 50)), np.full(100, 1.0 / (2 * 100))]
    expected_a = (matrix * np.sqrt(weights)[:, None]).T @ (
        matrix * np.sqrt(weights)[:, None]
    )
    expected_b = matrix.T @ (weights * target)
    assert np.allclose(a, expected_a)
    assert np.allclose(b, expected_b)
    assert stats["training_sessions"] == 2
    assert np.isclose(stats["session_equal_row_weight_sum"], 1.0)


def test_correction_context_changes_only_helper_and_restores_it() -> None:
    original = campaign.sufficient_statistics
    with recovery.install_correction():
        assert campaign.sufficient_statistics is recovery.corrected_sufficient_statistics
    assert campaign.sufficient_statistics is original


def test_v2_status_is_read_only() -> None:
    payload = recovery.status()
    assert payload["original_and_v1_failures_preserved"] is True
    assert payload["model_fit_count_by_status"] == 0
    assert payload["validation_return_read_count_by_status"] == 0
    assert payload["candidate49_ledgers_changed_by_status"] is False


def test_v2_activation_cannot_open_lockbox() -> None:
    if not recovery.RECOVERY_ACTIVATION.exists():
        pytest.skip("activation is frozen after runner and tests are hashed")
    activation = json.loads(recovery.RECOVERY_ACTIVATION.read_text(encoding="utf-8"))
    assert activation["remaining_complete_development_trial_count"] == 3
    assert activation["lockbox_2024_2025_authorized"] is False
    assert activation["provider_request_authorized"] is False
