from __future__ import annotations

from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign087_features as v1
from scripts import a_share_three_day_walkforward_campaign087_features_v3 as v3
from scripts import a_share_three_day_walkforward_campaign087_features_v4 as v4


def test_v4_inputs_and_published_snapshot_are_immutable() -> None:
    assert v4._sha256(v4.REPAIR_PROTOCOL) == v4.REPAIR_PROTOCOL_SHA256
    assert v4._sha256(v4.V1_RUNNER_PATH) == v4.V1_RUNNER_SHA256
    assert v4._sha256(Path(v3.__file__).resolve()) == v4.V3_RUNNER_SHA256
    assert v4._sha256(v3.DEFAULT_IMPLEMENTATION_FREEZE) == v4.V3_FREEZE_SHA256
    assert v4._sha256(v4.SNAPSHOT_MANIFEST_PATH) == v4.SNAPSHOT_MANIFEST_SHA256


def test_nested_v3_freeze_validation_uses_v1_identity_then_restores() -> None:
    original = v1.__file__
    v1.__file__ = str(Path(v3.__file__).resolve())
    try:
        freeze = v4._load_v3_freeze_with_v1_identity()
        assert (
            freeze["status"]
            == "empty_identity_repair_frozen_before_campaign087_feature_build_retry"
        )
        assert v1.__file__ == str(Path(v3.__file__).resolve())
    finally:
        v1.__file__ = original


def test_v1_verifier_context_exposes_v3_manifest_identity_and_restores() -> None:
    before = {
        "__file__": v1.__file__,
        "DEFAULT_IMPLEMENTATION_FREEZE": v1.DEFAULT_IMPLEMENTATION_FREEZE,
        "_load_implementation_freeze": v1._load_implementation_freeze,
    }
    with v4._patched_v1_verifier():
        assert Path(v1.__file__).resolve() == Path(v3.__file__).resolve()
        assert v1.DEFAULT_IMPLEMENTATION_FREEZE == v3.DEFAULT_IMPLEMENTATION_FREEZE
        assert v1._load_implementation_freeze is v4._load_v3_freeze_with_v1_identity
        assert v1._load_implementation_freeze()["kind"].endswith(
            "feature_implementation_freeze_v3"
        )
    assert v1.__file__ == before["__file__"]
    assert v1.DEFAULT_IMPLEMENTATION_FREEZE == before["DEFAULT_IMPLEMENTATION_FREEZE"]
    assert v1._load_implementation_freeze is before["_load_implementation_freeze"]


def test_status_is_read_only_and_keeps_research_gates_closed() -> None:
    before = v4._sha256(v4.SNAPSHOT_MANIFEST_PATH)
    status = v4.status()
    after = v4._sha256(v4.SNAPSHOT_MANIFEST_PATH)
    assert status["snapshot_manifest_sha256_matches"] is True
    assert status["coverage_or_capacity_metrics_computed_by_status"] is False
    assert status["comparison_values_read_by_status"] is False
    assert before == after == v4.SNAPSHOT_MANIFEST_SHA256
