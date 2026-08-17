from __future__ import annotations

import copy
import json

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign116_snapshot_verify_recovery as recovery,
)


def test_campaign116_recovery_protocol_is_narrow_and_bound() -> None:
    spec = recovery.load_recovery_protocol()
    allowed = spec["allowed_recovery"]
    assert allowed["separate_verifier_only"] is True
    assert allowed["original_builder_or_snapshot_modification_allowed"] is False
    assert allowed["comparator_value_use"] is False
    assert allowed["daily_price_or_forward_return_use"] is False


def test_campaign116_published_manifest_passes_corrected_metadata_only() -> None:
    manifest = json.loads(recovery.MANIFEST_PATH.read_text(encoding="utf-8"))
    recovery.validate_manifest_metadata(manifest)
    assert manifest["minimum_group_support"] == 30
    assert manifest["positive_total_activity_required"] is True
    assert manifest["endpoint_amount_used"] is True


def test_campaign116_recovery_rejects_any_other_manifest_change() -> None:
    manifest = json.loads(recovery.MANIFEST_PATH.read_text(encoding="utf-8"))
    changed = copy.deepcopy(manifest)
    changed["comparison_factor_values_read"] = True
    with pytest.raises(recovery.Campaign116SnapshotRecoveryError):
        recovery.validate_manifest_metadata(changed)
