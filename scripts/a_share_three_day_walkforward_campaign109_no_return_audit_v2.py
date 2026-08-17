#!/usr/bin/env python3
"""Run Campaign109 no-return audit through the additive feature-binding recovery."""

from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign109_features_v2 as candidate_v2
from scripts import a_share_three_day_walkforward_campaign109_no_return_audit as base


if base.candidate is not candidate_v2.base:
    raise RuntimeError("Campaign109 recovery candidate module identity changed")

Campaign109NoReturnAuditError = base.Campaign109NoReturnAuditError
candidate = base.candidate
FACTOR_NAME = base.FACTOR_NAME
DEFAULT_DATA_ROOT = base.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = base.DEFAULT_EXPERIMENT_ROOT
SNAPSHOT_MANIFEST_PATH = base.SNAPSHOT_MANIFEST_PATH
SNAPSHOT_BINDING = base.SNAPSHOT_BINDING
AUDIT_ACTIVATION_BINDING = base.AUDIT_ACTIVATION_BINDING
ADAPTER_FREEZE = base.ADAPTER_FREEZE
ADAPTER_FREEZE_SHA256 = base.ADAPTER_FREEZE_SHA256
EXPECTED_ROWS = base.EXPECTED_ROWS
EXPECTED_PARTITIONS = base.EXPECTED_PARTITIONS
EXPECTED_COMPARISON_COUNT = base.EXPECTED_COMPARISON_COUNT
load_protocol = base.load_protocol
verify_static_bindings = base.verify_static_bindings
verify_candidate_snapshot = base.verify_candidate_snapshot
run_no_return_audit = base.run_no_return_audit
status = base.status
main = base.main


if __name__ == "__main__":
    raise SystemExit(main())
