from __future__ import annotations

from pathlib import Path

import pytest

from scripts import (
    a_share_three_day_walkforward_campaign146_ordered_uniqueness_recovery as recovery,
)


def test_campaign146_uniqueness_recovery_protocol_is_receipt_only() -> None:
    spec = recovery.load_recovery_protocol()
    correction = spec["allowed_correction"]
    assert correction["defective_expression"] == "len(c136_manifest['files'])"
    assert correction["correct_expression"] == "len(c136_manifest['partitions'])"
    assert (
        correction[
            "formula_direction_sources_order_alignment_gate_output_or_decision_change_allowed"
        ]
        is False
    )


def test_campaign146_uniqueness_recovery_static_receipt_uses_partitions() -> None:
    static = recovery.corrected_validate_static_bindings()
    manifest = recovery.frozen.validate_c136_manifest_metadata()
    assert static["campaign136_partition_count"] == len(manifest["partitions"])
    assert static["receipt_key_correction"] == "files_to_partitions_only"
    assert static["comparator_values_read"] is False


def test_campaign146_uniqueness_recovery_binds_original_runner() -> None:
    assert recovery.frozen.file_sha256(Path(recovery.frozen.__file__)) == (
        recovery.ORIGINAL_RUNNER_SHA256
    )
    assert (
        recovery.frozen.file_sha256(recovery.frozen.IMPLEMENTATION_FREEZE_PATH)
        == recovery.ORIGINAL_FREEZE_SHA256
    )


def test_campaign146_uniqueness_recovery_requires_confirmation() -> None:
    with pytest.raises(recovery.Campaign146OrderedUniquenessRecoveryError):
        recovery.run_ordered_uniqueness(confirm=False)


def test_campaign146_uniqueness_recovery_does_not_rewrite_frozen_data() -> None:
    source = Path(recovery.__file__).read_text(encoding="utf-8")
    assert "unlink(" not in source
    assert "write_text(" not in source
    assert "apply_patch" not in source
    assert "frozen.build_plan = build_plan" in source
