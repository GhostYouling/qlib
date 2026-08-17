from __future__ import annotations

import copy
import json

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign119_snapshot_verify_recovery as recovery,
)


def _manifest() -> dict:
    return json.loads(recovery.MANIFEST_PATH.read_text(encoding="utf-8"))


def test_recovery_accepts_exact_truthful_manifest_metadata() -> None:
    manifest = _manifest()
    recovery.validate_manifest_metadata(manifest)
    assert manifest["range_boundary_direction_state_count"] == 9
    assert manifest["exact_pair_support_required"] is True
    assert manifest["range_magnitude_used_after_state_encoding"] is False
    assert manifest["comparison_factor_values_read"] is False


def test_recovery_rejects_old_campaign105_zero_state_expectation() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["range_boundary_direction_state_count"] = 0
    with pytest.raises(recovery.Campaign119SnapshotRecoveryError):
        recovery.validate_manifest_metadata(manifest)


def test_recovery_rejects_false_exact_pair_support_semantics() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["exact_pair_support_required"] = False
    with pytest.raises(recovery.Campaign119SnapshotRecoveryError):
        recovery.validate_manifest_metadata(manifest)


def test_recovery_rejects_any_return_or_comparator_read_flag() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["comparison_factor_values_read"] = True
    with pytest.raises(recovery.Campaign119SnapshotRecoveryError):
        recovery.validate_manifest_metadata(manifest)
