from __future__ import annotations

import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign083_no_return_audit_v3 as v3


def test_v3_protocol_skips_only_runtime_sensitive_frame_hash_recomputation() -> None:
    spec = v3.load_repair_protocol()
    sole = spec["sole_compatibility_repair"]
    assert sole["runtime_sensitive_output_frame_hash_recomputation_skipped"] is True
    assert sole["every_partition_byte_hash_still_required"] is True
    assert sole["every_partition_exact_schema_still_required"] is True
    assert sole["every_partition_frozen_factor_value_semantics_still_required"] is True
    assert sole["original_legacy_runtime_gate_suppression_allowed"] is False
    assert sole["prior_comparator_verifier_change_allowed"] is False


def test_first_failed_partition_passes_compatibility_checks_without_rewrite() -> None:
    manifest = json.loads(v3.v1.SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    item = next(
        entry
        for entry in manifest["files"]
        if entry["relative_path"] == "partitions/sh600000/2019.parquet"
    )
    partition_root = (v3.v1.SNAPSHOT_MANIFEST_PATH.parent / "partitions").resolve()
    rows, eligible = v3._verify_partition_compatible(
        item, partition_root=partition_root
    )
    assert rows == item["rows"] == 244
    assert eligible == 244
    assert v3._sha256(Path(item["path"])) == item["output_byte_sha256"]


def test_candidate_verifier_binding_is_temporary_and_restored() -> None:
    original = v3.v1.candidate.verify_snapshot_files
    with v3._temporary_candidate_verifier_binding():
        assert (
            v3.v1.candidate.verify_snapshot_files
            is v3.verify_candidate_snapshot_compatible
        )
    assert v3.v1.candidate.verify_snapshot_files is original


def test_exact_runtime_and_zero_audit_precondition_hold() -> None:
    assert v3.v2.require_exact_runtime() == {
        "pandas": "2.2.2",
        "pyarrow": "16.1.0",
    }
    status = v3.v1.status()
    assert status["audit_count"] == 0
    assert status["comparison_values_read_by_status"] is False
    assert status["historical_forward_return_fields_read"] is False


def test_v3_implementation_freeze_is_live_when_published() -> None:
    if v3.IMPLEMENTATION_FREEZE.is_file():
        freeze = v3._load_implementation_freeze()
        assert freeze["original_legacy_runtime_gate_suppressed"] is False
        assert freeze["prior_comparator_verifier_changed"] is False
        assert freeze["partial_statistics_reused"] is False
