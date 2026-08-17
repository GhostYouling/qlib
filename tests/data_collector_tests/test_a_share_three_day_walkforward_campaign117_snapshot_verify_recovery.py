from __future__ import annotations

import copy
import json

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign117_snapshot_verify_recovery as recovery,
)


def _manifest() -> dict:
    return json.loads(recovery.MANIFEST_PATH.read_text(encoding="utf-8"))


def test_recovery_accepts_exact_truthful_manifest_metadata() -> None:
    manifest = _manifest()
    recovery.validate_manifest_metadata(manifest)
    assert manifest["weak_order_state_count"] == 13
    assert manifest["positive_total_amount_required"] is True
    assert manifest["comparison_factor_values_read"] is False


def test_recovery_rejects_old_campaign105_state_count_expectation() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["weak_order_state_count"] = 0
    with pytest.raises(recovery.Campaign117SnapshotRecoveryError):
        recovery.validate_manifest_metadata(manifest)


def test_recovery_rejects_false_positive_total_semantics() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["positive_total_amount_required"] = False
    with pytest.raises(recovery.Campaign117SnapshotRecoveryError):
        recovery.validate_manifest_metadata(manifest)


def test_recovery_rejects_any_return_or_comparator_read_flag() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["comparison_factor_values_read"] = True
    with pytest.raises(recovery.Campaign117SnapshotRecoveryError):
        recovery.validate_manifest_metadata(manifest)
