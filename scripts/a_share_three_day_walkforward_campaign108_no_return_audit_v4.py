#!/usr/bin/env python3
"""Campaign108 generation-depth range-only audit loader recovery."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_IMPLEMENTATION = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign108_no_return_audit.py"
)
BASE_IMPLEMENTATION_SHA256 = (
    "8fd5402b2a492380152efa4f1b0af077f65c1cee2ed6c2f25e1b5ea00a8e20e1"
)
PRESERVED_V3_IMPLEMENTATION = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign108_no_return_audit_v3.py"
)
PRESERVED_V3_IMPLEMENTATION_SHA256 = (
    "d96ddee9bbd89eed12a18d6763b17706b3a72f07b0a456633c0eb5e05dd3adc2"
)
AUDIT_RECOVERY_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_108_no_return_audit_loader_recovery_freeze_v5_20260808.json"
)
RECOVERY_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_108_no_return_audit_activation_binding_v3_20260808.json"
)
RECOVERY_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign108_no_return_audit_v4.py"
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _file_sha256(BASE_IMPLEMENTATION) != BASE_IMPLEMENTATION_SHA256:
    raise RuntimeError("frozen Campaign108 v1 no-return audit changed")
if _file_sha256(PRESERVED_V3_IMPLEMENTATION) != PRESERVED_V3_IMPLEMENTATION_SHA256:
    raise RuntimeError("preserved Campaign108 v3 recovery changed")


_source = BASE_IMPLEMENTATION.read_text(encoding="utf-8")
_candidate_import_old = "a_share_three_day_walkforward_campaign108_features as candidate"
_candidate_import_new = "a_share_three_day_walkforward_campaign108_features_v2 as candidate"
_generation_hook = '_source = BASE_RUNNER.read_text(encoding="utf-8")'
_range_old = "ranges[FACTOR_NAME] = (0.0, 1.0)"
_range_new = "ranges[FACTOR_NAME] = (-1.0, 1.0)"
if _source.count(_candidate_import_old) != 1 or _source.count(_generation_hook) != 1:
    raise RuntimeError("Campaign108 v1 audit generation hooks changed")
_range_injection = "\n".join(
    [
        _generation_hook,
        f'_source = _source.replace("{_range_old}", "{_range_new}")',
    ]
)
_source = _source.replace(_candidate_import_old, _candidate_import_new)
_source = _source.replace(_generation_hook, _range_injection)

_impl: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign108_no_return_audit_v4_generated",
}
exec(compile(_source, str(BASE_IMPLEMENTATION), "exec"), _impl)
_impl["AUDIT_ACTIVATION_BINDING"] = RECOVERY_ACTIVATION_BINDING
_generated_audit_source = _impl["_source"]


Campaign108NoReturnAuditError = _impl["Campaign108NoReturnAuditError"]


def _validate_audit_recovery_freeze() -> dict[str, Any]:
    if not AUDIT_RECOVERY_FREEZE.is_file():
        raise Campaign108NoReturnAuditError("Campaign108 audit recovery freeze is absent")
    record = json.loads(AUDIT_RECOVERY_FREEZE.read_text(encoding="utf-8"))
    failed = record.get("failed_recovery") or {}
    recovered = record.get("recovered_audit") or {}
    boundary = record.get("scientific_boundary") or {}
    tests = record.get("synthetic_tests") or []
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign108_no_return_audit_loader_recovery_freeze"
        and record.get("status")
        == "generation_depth_range_only_recovery_frozen_before_coverage_or_comparator_values"
        and failed.get("sha256")
        == "2030f02b469fe239bc8671e39d36082dc6fb6874726cc42d4740819f874dda67"
        and recovered.get("sha256") == _file_sha256(Path(__file__).resolve())
        and tests
        == [
            {
                "path": str(RECOVERY_TEST_PATH.relative_to(REPO_ROOT)),
                "sha256": _file_sha256(RECOVERY_TEST_PATH),
            }
        ]
        and boundary.get("only_change")
        == "inject candidate loader validation range (0,1) to (-1,1) into the dynamically read Campaign105 audit source"
        and boundary.get(
            "formula_direction_endpoints_transform_snapshot_coverage_uniqueness_comparator_order_cost_fold_or_stress_gate_changed"
        )
        is False
        and boundary.get("coverage_or_capacity_metrics_computed_before_freeze")
        is False
        and boundary.get("comparator_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign108NoReturnAuditError(
            "Campaign108 generation-depth audit recovery freeze changed"
        )
    return record


_base_load_activation_binding = _impl["_load_activation_binding"]


def _load_activation_binding() -> dict[str, Any]:
    _validate_audit_recovery_freeze()
    return _base_load_activation_binding()


_impl["_load_activation_binding"] = _load_activation_binding
_base_run_no_return_audit = _impl["run_no_return_audit"]


def run_no_return_audit(**kwargs: Any) -> Path:
    _validate_audit_recovery_freeze()
    return _base_run_no_return_audit(**kwargs)


_impl["run_no_return_audit"] = run_no_return_audit

FACTOR_NAME = _impl["FACTOR_NAME"]
DEFAULT_DATA_ROOT = _impl["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = _impl["DEFAULT_EXPERIMENT_ROOT"]
SNAPSHOT_MANIFEST_PATH = _impl["SNAPSHOT_MANIFEST_PATH"]
SNAPSHOT_BINDING = _impl["SNAPSHOT_BINDING"]
AUDIT_ACTIVATION_BINDING = RECOVERY_ACTIVATION_BINDING
EXPECTED_ROWS = _impl["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _impl["EXPECTED_PARTITIONS"]
EXPECTED_COMPARISON_COUNT = _impl["EXPECTED_COMPARISON_COUNT"]
load_protocol = _impl["load_protocol"]
verify_static_bindings = _impl["verify_static_bindings"]
verify_candidate_snapshot = _impl["verify_candidate_snapshot"]
status = _impl["status"]
main = _impl["main"]


if __name__ == "__main__":
    raise SystemExit(main())
