from __future__ import annotations

import copy
import json

from scripts import a_share_three_day_walkforward_campaign087_features as v1
from scripts import a_share_three_day_walkforward_campaign087_features_v5 as v5


def test_v5_inputs_are_immutable_and_output_is_absent_before_freeze() -> None:
    assert v5._sha256(v5.REPAIR_PROTOCOL) == v5.REPAIR_PROTOCOL_SHA256
    assert v5._sha256(v5.ORIGINAL_MANIFEST_PATH) == v5.ORIGINAL_MANIFEST_SHA256
    assert not v5.REPAIRED_MANIFEST_PATH.exists()


def test_repaired_manifest_changes_only_frozen_metadata_locations() -> None:
    original = json.loads(v5.ORIGINAL_MANIFEST_PATH.read_text(encoding="utf-8"))
    repaired = v5._repaired_manifest(original)
    normalized = copy.deepcopy(original)
    normalized["kind"] = repaired["kind"]
    normalized["protocol"]["sha256"] = repaired["protocol"]["sha256"]
    normalized["dataset_sha256"] = repaired["dataset_sha256"]
    normalized["publication_metadata_repair"] = repaired[
        "publication_metadata_repair"
    ]
    assert normalized == repaired
    assert repaired["protocol"]["sha256"] == v1.PROTOCOL_SHA256
    assert repaired["dataset_sha256"] != original["dataset_sha256"]
    assert repaired["dataset_sha256"] == v1._json_digest(
        v1._dataset_material(repaired)
    )


def test_original_partition_records_match_frozen_v5_byte_order() -> None:
    original = json.loads(v5.ORIGINAL_MANIFEST_PATH.read_text(encoding="utf-8"))
    observed = {
        int(record["year"]): str(record["sha256"])
        for record in original["files"]
    }
    assert observed == v5.EXPECTED_PARTITION_SHA256
    assert original["factor_eligible_rows"][v1.FACTOR_NAME] == 1_328_449


def test_status_is_read_only_and_keeps_gates_closed() -> None:
    before = v5._sha256(v5.ORIGINAL_MANIFEST_PATH)
    status = v5.status()
    after = v5._sha256(v5.ORIGINAL_MANIFEST_PATH)
    assert status["status"] == "repaired_manifest_absent_prepublish"
    assert status["original_manifest_sha256_matches"] is True
    assert status["coverage_or_capacity_metrics_computed_by_status"] is False
    assert status["comparison_values_read_by_status"] is False
    assert before == after == v5.ORIGINAL_MANIFEST_SHA256
