from __future__ import annotations

import copy
import json

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign120_snapshot_verify_recovery as recovery,
)


def _manifest() -> dict:
    return json.loads(recovery.MANIFEST_PATH.read_text(encoding="utf-8"))


def test_recovery_accepts_exact_bound_manifest_and_preserves_discrepancy() -> None:
    manifest = _manifest()
    recovery.validate_manifest_metadata(manifest)
    assert manifest["dictionary_parser_count"] == 0
    assert manifest["exact_symbol_support_required"] is False
    protocol = recovery.c120.load_protocol()
    assert protocol["candidate"]["search_space"]["parser_count"] == 1
    assert "exact consumption" in protocol["candidate"]["exact_formula"]["support"]


def test_recovery_rejects_rewritten_parser_metadata() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["dictionary_parser_count"] = 1
    with pytest.raises(recovery.Campaign120SnapshotRecoveryError):
        recovery.validate_manifest_metadata(manifest)


def test_recovery_rejects_rewritten_support_metadata() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["exact_symbol_support_required"] = True
    with pytest.raises(recovery.Campaign120SnapshotRecoveryError):
        recovery.validate_manifest_metadata(manifest)


def test_recovery_rejects_any_return_or_comparator_read_flag() -> None:
    for key in ("forward_return_fields_read", "comparison_factor_values_read"):
        manifest = copy.deepcopy(_manifest())
        manifest[key] = True
        with pytest.raises(recovery.Campaign120SnapshotRecoveryError):
            recovery.validate_manifest_metadata(manifest)
