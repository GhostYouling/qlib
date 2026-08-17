#!/usr/bin/env python3
"""Run Campaign092's frozen no-return audit with the binding export repair."""

from __future__ import annotations

from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign092_features_v2 as definitions
from scripts import a_share_three_day_walkforward_campaign092_no_return_audit as v1


REPO_ROOT = Path(__file__).resolve().parents[1]
v1._generated["definitions"] = definitions
v1._generated["__file__"] = str(Path(__file__).resolve())
v1._generated["AUDIT_IMPLEMENTATION_FREEZE"] = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_092_no_return_audit_implementation_freeze_v2_20260807.json"
)
v1._generated["AUDIT_ACTIVATION_BINDING"] = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_092_no_return_audit_activation_binding_v2_20260807.json"
)
v1._generated["TEST_PATH"] = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign092_no_return_audit_v2.py"
)

Campaign092NoReturnAuditError = v1._generated["Campaign092NoReturnAuditError"]
DEFAULT_DATA_ROOT = v1._generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = v1._generated["DEFAULT_EXPERIMENT_ROOT"]
SNAPSHOT_MANIFEST_PATH = v1._generated["SNAPSHOT_MANIFEST_PATH"]
SNAPSHOT_MANIFEST_SHA256 = v1._generated["SNAPSHOT_MANIFEST_SHA256"]
SNAPSHOT_DATASET_SHA256 = v1._generated["SNAPSHOT_DATASET_SHA256"]
SNAPSHOT_BINDING = v1._generated["SNAPSHOT_BINDING"]
SNAPSHOT_BINDING_SHA256 = v1._generated["SNAPSHOT_BINDING_SHA256"]
AUDIT_IMPLEMENTATION_FREEZE = v1._generated["AUDIT_IMPLEMENTATION_FREEZE"]
AUDIT_ACTIVATION_BINDING = v1._generated["AUDIT_ACTIVATION_BINDING"]
TEST_PATH = v1._generated["TEST_PATH"]
FACTOR_NAME = v1._generated["FACTOR_NAME"]
load_protocol = v1._generated["load_protocol"]
verify_static_bindings = v1._generated["verify_static_bindings"]
verify_candidate_snapshot = v1._generated["verify_candidate_snapshot"]
status = v1._generated["status"]
main = v1._generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())

