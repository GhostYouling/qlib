from __future__ import annotations

import copy
import json

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign121_snapshot_verify_recovery as recovery,
)


def _manifest() -> dict:
    return json.loads(recovery.MANIFEST_PATH.read_text(encoding="utf-8"))


def test_recovery_accepts_bound_manifest_and_preserves_discrepancy() -> None:
    manifest = _manifest()
    recovery.validate_manifest_metadata(manifest)
    assert manifest["factor_ranges"][recovery.c121.FACTOR_NAME] == [-1.0, 1.0]
    assert manifest["fixed_denominator"] == 240
    protocol = recovery.c121.load_protocol()
    assert protocol["candidate"]["exact_formula"]["valid_range_inclusive"] == [
        0.0,
        1.0,
    ]


def test_recovery_rejects_rewritten_range_metadata() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["factor_ranges"][recovery.c121.FACTOR_NAME] = [0.0, 1.0]
    with pytest.raises(recovery.Campaign121SnapshotRecoveryError):
        recovery.validate_manifest_metadata(manifest)


def test_recovery_rejects_rewritten_denominator_metadata() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["fixed_denominator"] = 239
    with pytest.raises(recovery.Campaign121SnapshotRecoveryError):
        recovery.validate_manifest_metadata(manifest)


def test_recovery_rejects_any_return_or_comparator_read_flag() -> None:
    for key in ("forward_return_fields_read", "comparison_factor_values_read"):
        manifest = copy.deepcopy(_manifest())
        manifest[key] = True
        with pytest.raises(recovery.Campaign121SnapshotRecoveryError):
            recovery.validate_manifest_metadata(manifest)
